"""
Track A: corridor/pinch-point extraction (see README.md Section 5).

Splits GPS fixes into dwell (resting/feeding/watering) vs transit (moving
through) before clustering, so candidate sensor sites come from actual
movement corridors rather than places an elephant just stood still.

Output contract for Tracks B/C/D: data/candidate_sites.csv with
{site_id, lat, lon, weight_c_i, n_fixes, n_individuals, individuals}.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

EARTH_RADIUS_M = 6_371_000
DWELL_SPEED_THRESHOLD_KMH = 0.5
MIN_CLUSTERS = 8
MAX_CLUSTERS = 15

# This data package bundles two elephants from unrelated populations thousands
# of km apart (Salif Keita: Gourma, Mali; Habiba: central Kenya) -- the Wall et
# al. 2014 paper used them as separate method examples, not a shared habitat.
# Mixing them into one sensor-placement problem is not ecologically meaningful,
# so we scope to one coherent population. Salif Keita has ~24x the transit fixes
# (richer corridor signal) and dedicated literature on this exact population's
# movement drivers (Wall et al. 2013, Biological Conservation).
INDIVIDUAL_FILTER = "Salif Keita"


def haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(x) for x in (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def load_data(path):
    df = pd.read_csv(path)
    df = df[df["visible"].astype(str).str.lower() == "true"].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["individual-local-identifier", "timestamp"]).reset_index(drop=True)
    return df


def compute_speed(df):
    grouped = df.groupby("individual-local-identifier")
    df["prev_lat"] = grouped["location-lat"].shift(1)
    df["prev_lon"] = grouped["location-long"].shift(1)
    df["prev_time"] = grouped["timestamp"].shift(1)
    dist_m = haversine_m(df["prev_lat"], df["prev_lon"], df["location-lat"], df["location-long"])
    dt_h = (df["timestamp"] - df["prev_time"]).dt.total_seconds() / 3600.0
    df["speed_kmh"] = (dist_m / 1000.0) / dt_h
    return df


def split_dwell_transit(df):
    df["is_transit"] = (df["speed_kmh"] > DWELL_SPEED_THRESHOLD_KMH).fillna(False)
    return df


def run_dbscan(points_df, eps_m, min_samples=5):
    coords = np.column_stack([
        np.radians(points_df["location-lat"].values),
        np.radians(points_df["location-long"].values),
    ])
    labels = DBSCAN(eps=eps_m / EARTH_RADIUS_M, min_samples=min_samples, metric="haversine").fit(coords).labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    return labels, n_clusters


def tune_eps_for_cluster_count(points_df, min_clusters, max_clusters, start_eps_m=1500.0, min_samples=5, max_attempts=25):
    eps_m = start_eps_m
    labels, n_clusters = run_dbscan(points_df, eps_m, min_samples)
    for _ in range(max_attempts):
        if min_clusters <= n_clusters <= max_clusters:
            return labels, eps_m, n_clusters
        eps_m *= 1.3 if n_clusters > max_clusters else 0.75
        labels, n_clusters = run_dbscan(points_df, eps_m, min_samples)
    return labels, eps_m, n_clusters  # best effort — caller should check the count


def build_candidate_table(points_df, labels):
    tagged = points_df.copy()
    tagged["cluster"] = labels
    clustered = tagged[tagged["cluster"] != -1]
    rows = []
    for cluster_id, group in clustered.groupby("cluster"):
        rows.append({
            "site_id": int(cluster_id),
            "lat": group["location-lat"].mean(),
            "lon": group["location-long"].mean(),
            "n_fixes": len(group),
            "n_individuals": group["individual-local-identifier"].nunique(),
            "individuals": ",".join(sorted(group["individual-local-identifier"].unique())),
        })
    table = pd.DataFrame(rows).sort_values("n_fixes", ascending=False).reset_index(drop=True)
    if len(table):
        table["weight_c_i"] = (table["n_fixes"] / table["n_fixes"].max()).round(4)
    return table


def main():
    df = load_data("data/elephant_gps_raw.csv")
    if INDIVIDUAL_FILTER:
        df = df[df["individual-local-identifier"] == INDIVIDUAL_FILTER].reset_index(drop=True)
        print(f"Filtered to individual: {INDIVIDUAL_FILTER}")
    df = compute_speed(df)
    df = split_dwell_transit(df)

    transit = df[df["is_transit"]]
    dwell = df[~df["is_transit"]]
    print(f"Total fixes: {len(df)}")
    print(f"Transit fixes: {len(transit)} ({len(transit) / len(df):.1%})")
    print(f"Dwell fixes:   {len(dwell)} ({len(dwell) / len(df):.1%})")

    labels, eps_m, n_clusters = tune_eps_for_cluster_count(transit, MIN_CLUSTERS, MAX_CLUSTERS)
    status = "OK" if MIN_CLUSTERS <= n_clusters <= MAX_CLUSTERS else "OUT OF RANGE — needs manual guard per README Section 5"
    print(f"\nDBSCAN converged at eps={eps_m:.0f}m -> {n_clusters} transit clusters [{status}]")

    candidates = build_candidate_table(transit, labels)
    candidates.to_csv("data/candidate_sites.csv", index=False)
    print(f"\nCandidate sensor sites (-> data/candidate_sites.csv):\n{candidates.to_string(index=False)}")

    dwell_labels, dwell_n = run_dbscan(dwell, eps_m)  # same spatial scale, no qubit constraint
    dwell_sites = build_candidate_table(dwell, dwell_labels)
    dwell_sites.to_csv("data/dwell_sites_context.csv", index=False)
    print(f"\nDwell/rest sites (demo-map context only, NOT sensor candidates): {len(dwell_sites)} found -> data/dwell_sites_context.csv")


if __name__ == "__main__":
    main()
