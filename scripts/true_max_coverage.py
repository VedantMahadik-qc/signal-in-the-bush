"""Track B: exact and greedy baselines for true maximum coverage.

A ranger site covers every Salif Keita transit fix within 25 km. The goal is
to select at most three sites that cover the most unique fixes.
"""

import json
from pathlib import Path
from statistics import mean, pstdev
import sys
from time import perf_counter_ns

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_pinch_points import (
    DWELL_SPEED_THRESHOLD_KMH,
    INDIVIDUAL_FILTER,
    compute_speed,
    haversine_m,
    load_data,
    split_dwell_transit,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
GPS_PATH = ROOT_DIR / "data/elephant_gps_raw.csv"
SITES_PATH = ROOT_DIR / "data/candidate_sites.csv"
PROXY_RESULTS_PATH = ROOT_DIR / "data/track_b_results.json"
OUTPUT_PATH = ROOT_DIR / "data/true_coverage_results.json"

COVERAGE_RADIUS_KM = 25.0
TEAM_BUDGET = 3
BENCHMARK_RUNS = 30


def build_coverage_sets(sites, fixes):
    """Return the transit-fix indexes covered by each candidate site."""
    coverage_sets = []
    for site in sites.itertuples():
        distances_m = haversine_m(
            site.lat,
            site.lon,
            fixes["location-lat"].to_numpy(),
            fixes["location-long"].to_numpy(),
        )
        coverage_sets.append(set(np.flatnonzero(distances_m <= COVERAGE_RADIUS_KM * 1000)))
    return coverage_sets


def covered_fixes(selected_indexes, coverage_sets):
    covered = set()
    for site_index in selected_indexes:
        covered.update(coverage_sets[site_index])
    return covered


def solve_exact(coverage_sets):
    """Use OR-Tools CP-SAT to solve genuine maximum coverage."""
    model = cp_model.CpModel()
    site_vars = [model.new_bool_var(f"site_{i}") for i in range(len(coverage_sets))]

    covering_sites = {}
    for site_index, covered in enumerate(coverage_sets):
        for fix_index in covered:
            covering_sites.setdefault(fix_index, []).append(site_index)

    covered_vars = {}
    for fix_index, site_indexes in covering_sites.items():
        covered_vars[fix_index] = model.new_bool_var(f"fix_{fix_index}")
        model.add(
            covered_vars[fix_index]
            <= sum(site_vars[site_index] for site_index in site_indexes)
        )

    model.add(sum(site_vars) <= TEAM_BUDGET)
    model.maximize(sum(covered_vars.values()))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    if status != cp_model.OPTIMAL:
        raise RuntimeError("OR-Tools did not prove an optimal solution")

    selected = [
        index for index, variable in enumerate(site_vars) if solver.value(variable)
    ]
    return selected, covered_fixes(selected, coverage_sets)


def solve_greedy(coverage_sets):
    """Repeatedly choose the site that adds the most uncovered fixes."""
    selected = []
    covered = set()

    while len(selected) < TEAM_BUDGET:
        remaining = [i for i in range(len(coverage_sets)) if i not in selected]
        best_site = max(
            remaining,
            key=lambda i: (len(coverage_sets[i] - covered), -i),
        )
        gain = coverage_sets[best_site] - covered
        if not gain:
            break
        selected.append(best_site)
        covered.update(gain)

    return selected, covered


def benchmark(solver, coverage_sets):
    timings_ms = []
    for _ in range(BENCHMARK_RUNS):
        start = perf_counter_ns()
        solver(coverage_sets)
        timings_ms.append((perf_counter_ns() - start) / 1_000_000)
    return {"mean_ms": mean(timings_ms), "std_ms": pstdev(timings_ms)}


def result_for(selected, covered, sites, total_fixes):
    return {
        "selected_site_ids": [int(sites.iloc[i]["site_id"]) for i in selected],
        "covered_transit_fixes": len(covered),
        "coverage_fraction": len(covered) / total_fixes,
    }


def main():
    sites = pd.read_csv(SITES_PATH)
    fixes = load_data(GPS_PATH)
    fixes = fixes[fixes["individual-local-identifier"] == INDIVIDUAL_FILTER].reset_index(
        drop=True
    )
    transit = split_dwell_transit(compute_speed(fixes))
    transit = transit[transit["is_transit"]].reset_index(drop=True)
    coverage_sets = build_coverage_sets(sites, transit)

    exact_selected, exact_covered = solve_exact(coverage_sets)
    greedy_selected, greedy_covered = solve_greedy(coverage_sets)

    proxy_site_ids = json.loads(PROXY_RESULTS_PATH.read_text())["exact"][
        "selected_site_ids"
    ]
    id_to_index = {
        int(site_id): index for index, site_id in enumerate(sites["site_id"])
    }
    proxy_selected = [id_to_index[site_id] for site_id in proxy_site_ids]
    proxy_covered = covered_fixes(proxy_selected, coverage_sets)

    results = {
        "model": "true maximum coverage of transit GPS fixes",
        "assumptions": {
            "individual": INDIVIDUAL_FILTER,
            "transit_speed_kmh": DWELL_SPEED_THRESHOLD_KMH,
            "coverage_radius_km": COVERAGE_RADIUS_KM,
            "team_budget": TEAM_BUDGET,
        },
        "total_transit_fixes": len(transit),
        "coverage_count_by_site": {
            str(int(sites.iloc[i]["site_id"])): len(covered)
            for i, covered in enumerate(coverage_sets)
        },
        "exact": result_for(exact_selected, exact_covered, sites, len(transit)),
        "greedy": result_for(greedy_selected, greedy_covered, sites, len(transit)),
        "proxy_selection": result_for(
            proxy_selected, proxy_covered, sites, len(transit)
        ),
        "timing": {
            "runs": BENCHMARK_RUNS,
            "exact_ortools": benchmark(solve_exact, coverage_sets),
            "greedy": benchmark(solve_greedy, coverage_sets),
        },
    }

    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")

    print("True maximum-coverage result")
    print(f"  Transit fixes: {len(transit)}")
    print(f"  Exact selection: {results['exact']['selected_site_ids']}")
    print(f"  Exact coverage: {results['exact']['coverage_fraction']:.1%}")
    print(f"  Greedy selection: {results['greedy']['selected_site_ids']}")
    print(f"  Proxy selection coverage: {results['proxy_selection']['coverage_fraction']:.1%}")
    print(f"  Results written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
