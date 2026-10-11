"""
Track B core: proxy QUBO (for QAOA) + true max-coverage baseline (for the
honest comparison in README Section 7), both at candidate-site granularity.

Proxy QUBO: maximize sum(c_i x_i) - sum(Q_ij x_i x_j) - A*(sum(x_i)-k)^2
True max-coverage: treat each candidate site as also a demand point; a
chosen site "covers" a demand point within radius r; maximize total unique
covered weight. This is the real submodular problem -- greedy here actually
has the 1-1/e guarantee, unlike the proxy above.
"""
import itertools
import numpy as np
import pandas as pd

R_METERS = 400.0          # sensor/camera-trap effective detection radius
K_BUDGET = 3               # matches van's existing max-coverage branch
PENALTY_SWEEP = [0.5, 1.0, 2.0, 3.0, 5.0]
EARTH_RADIUS_M = 6_371_000

LAKE_BANZENA_SITE_ID = 7   # README Section 5/6 finding
LANDMARK_BOOST_MIN_CI = 0.5


def haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = (np.radians(x) for x in (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def load_sites(path="data/candidate_sites.csv"):
    df = pd.read_csv(path).sort_values("site_id").reset_index(drop=True)
    df.loc[df["site_id"] == LAKE_BANZENA_SITE_ID, "weight_c_i"] = df.loc[
        df["site_id"] == LAKE_BANZENA_SITE_ID, "weight_c_i"
    ].clip(lower=LANDMARK_BOOST_MIN_CI)
    return df


def distance_matrix(df):
    n = len(df)
    d = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            d[i, j] = haversine_m(df["lat"][i], df["lon"][i], df["lat"][j], df["lon"][j])
    return d


def build_overlap_matrix(d, r=R_METERS, w=1.0):
    return w * np.maximum(0.0, 1.0 - d / r)


def proxy_objective(x, c, Q, k, A):
    x = np.asarray(x, dtype=float)
    coverage = float(c @ x)
    overlap = float(x @ Q @ x) / 2.0  # Q is symmetric; sum_{i<j} = half of x^T Q x (diag is 0)
    penalty = A * (x.sum() - k) ** 2
    return coverage - overlap - penalty


def brute_force_proxy(c, Q, k, A):
    n = len(c)
    best_x, best_val = None, -np.inf
    for bits in itertools.product([0, 1], repeat=n):
        val = proxy_objective(bits, c, Q, k, A)
        if val > best_val:
            best_val, best_x = val, bits
    return np.array(best_x), best_val


def true_coverage(chosen_idx, d, weights, r=R_METERS):
    n = len(weights)
    covered = np.zeros(n, dtype=bool)
    for j in range(n):
        if any(d[i, j] <= r for i in chosen_idx):
            covered[j] = True
    return float(weights[covered].sum()), covered


def exact_max_coverage(d, weights, k=K_BUDGET):
    n = len(weights)
    best_set, best_cov = None, -1.0
    for combo in itertools.combinations(range(n), k):
        cov, _ = true_coverage(combo, d, weights)
        if cov > best_cov:
            best_cov, best_set = cov, combo
    return best_set, best_cov


def greedy_max_coverage(d, weights, k=K_BUDGET):
    n = len(weights)
    chosen = []
    for _ in range(k):
        best_gain, best_i = -1.0, None
        for i in range(n):
            if i in chosen:
                continue
            cov, _ = true_coverage(chosen + [i], d, weights)
            if cov > best_gain:
                best_gain, best_i = cov, i
        chosen.append(best_i)
    cov, _ = true_coverage(chosen, d, weights)
    return chosen, cov


def main():
    df = load_sites()
    n = len(df)
    c = df["weight_c_i"].to_numpy()
    weights_raw = df["n_fixes"].to_numpy(dtype=float)
    d = distance_matrix(df)
    Q = build_overlap_matrix(d)

    print(f"n={n} candidate sites, k={K_BUDGET}, r={R_METERS}m")
    print(df[["site_id", "lat", "lon", "n_fixes", "weight_c_i"]].to_string(index=False))

    print(f"\n--- Proxy QUBO: penalty sweep (target: exactly {K_BUDGET} sites selected) ---")
    chosen_A = None
    for A in PENALTY_SWEEP:
        x, val = brute_force_proxy(c, Q, K_BUDGET, A)
        n_selected = int(x.sum())
        status = "OK" if n_selected == K_BUDGET else f"got {n_selected}, want {K_BUDGET}"
        print(f"A={A}: objective={val:.4f}, sites={np.where(x==1)[0].tolist()}, selected={n_selected} [{status}]")
        if n_selected == K_BUDGET and chosen_A is None:
            chosen_A = A

    if chosen_A is None:
        print("\nWARNING: no tested A hit the exact budget -- widen PENALTY_SWEEP before trusting this QUBO.")
        return

    x_proxy, val_proxy = brute_force_proxy(c, Q, K_BUDGET, chosen_A)
    proxy_sites = df["site_id"].to_numpy()[x_proxy == 1]
    print(f"\nProxy QUBO exact optimum (A={chosen_A}): sites {proxy_sites.tolist()}, objective={val_proxy:.4f}")
    print("^ this is the ceiling QAOA is being asked to approach -- Track C target.")

    print(f"\n--- True max-coverage baseline (site-level granularity, r={R_METERS}m) ---")
    exact_idx, exact_cov = exact_max_coverage(d, weights_raw, K_BUDGET)
    exact_sites = df["site_id"].to_numpy()[list(exact_idx)]
    print(f"Exact optimum: sites {exact_sites.tolist()}, covered weight={exact_cov:.0f} fixes")

    greedy_idx, greedy_cov = greedy_max_coverage(d, weights_raw, K_BUDGET)
    greedy_sites = df["site_id"].to_numpy()[greedy_idx]
    ratio = greedy_cov / exact_cov if exact_cov else float("nan")
    print(f"Greedy (1-1/e guarantee): sites {greedy_sites.tolist()}, covered weight={greedy_cov:.0f} fixes, ratio={ratio:.3f} (guarantee: >= {1-1/np.e:.3f})")

    # Cross-check: how does the proxy QUBO's chosen set perform under the TRUE coverage metric?
    proxy_idx = list(np.where(x_proxy == 1)[0])
    proxy_true_cov, _ = true_coverage(proxy_idx, d, weights_raw)
    gap = proxy_true_cov / exact_cov if exact_cov else float("nan")
    print(f"\nProxy QUBO's chosen sites, evaluated under TRUE coverage: {proxy_true_cov:.0f} fixes ({gap:.1%} of true optimum)")
    print("^ this is the 'what did we give up for the qubit budget' number -- README Section 7.")

    np.save("data/qubo_c.npy", c)
    np.save("data/qubo_Q.npy", Q)
    with open("data/qubo_params.txt", "w") as f:
        f.write(f"k={K_BUDGET}\nr={R_METERS}\nA={chosen_A}\nsite_ids={df['site_id'].tolist()}\n")
    print("\nSaved c, Q, and params to data/ for Track C (QAOA).")


if __name__ == "__main__":
    main()
