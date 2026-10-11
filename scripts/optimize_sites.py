"""Track B: choose a small set of ranger monitoring sites.

The model is deliberately compact:

    site value - redundancy between nearby selected sites

Each candidate uses one binary decision, so the eight candidates produced by
Track A become an eight-qubit QUBO for Track C.
"""

from itertools import product
import json
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from statistics import mean, pstdev
from time import perf_counter_ns

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT_DIR / "data/candidate_sites.csv"
OUTPUT_PATH = ROOT_DIR / "data/track_b_results.json"

# Assumptions for the demo. This is a ranger-team operational radius, not a
# claim about the physical detection range of a camera.
TEAM_BUDGET = 3
OPERATIONAL_RADIUS_KM = 25.0
REDUNDANCY_SCALE = 0.25

# Lake Banzena is an independently documented dry-season water source. Raw GPS
# frequency underrates this location, so its minimum value is stated openly.
LANDMARK_MINIMUM_WEIGHTS = {7: 0.5}

QUBO_PENALTIES = (0.5, 1.0, 2.0, 5.0)
BENCHMARK_RUNS = 100
EARTH_RADIUS_KM = 6_371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Return the great-circle distance between two coordinates."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def load_sites(path):
    sites = pd.read_csv(path)
    required = {"site_id", "lat", "lon", "weight_c_i"}
    missing = required - set(sites.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")

    sites = sites.copy()
    sites["model_weight"] = sites["weight_c_i"].astype(float)
    for site_id, minimum in LANDMARK_MINIMUM_WEIGHTS.items():
        mask = sites["site_id"] == site_id
        sites.loc[mask, "model_weight"] = np.maximum(
            sites.loc[mask, "model_weight"], minimum
        )
    return sites


def build_distance_matrix(sites):
    n = len(sites)
    distances = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            distance = haversine_km(
                sites.iloc[i]["lat"],
                sites.iloc[i]["lon"],
                sites.iloc[j]["lat"],
                sites.iloc[j]["lon"],
            )
            distances[i, j] = distances[j, i] = distance
    return distances


def build_redundancy_matrix(weights, distances):
    """Estimate duplicated value for pairs inside the operational radius."""
    n = len(weights)
    redundancy = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            proximity = max(0.0, 1.0 - distances[i, j] / OPERATIONAL_RADIUS_KM)
            duplicated_value = (
                REDUNDANCY_SCALE * min(weights[i], weights[j]) * proximity
            )
            redundancy[i, j] = redundancy[j, i] = duplicated_value
    return redundancy


def site_score(bits, weights, redundancy):
    value = sum(weights[i] * bits[i] for i in range(len(bits)))
    duplicated = sum(
        redundancy[i, j] * bits[i] * bits[j]
        for i in range(len(bits))
        for j in range(i + 1, len(bits))
    )
    return value - duplicated


def solve_exact(weights, redundancy):
    """Check every feasible selection and return the true proxy optimum."""
    best_bits = None
    best_score = float("-inf")
    for bits in product((0, 1), repeat=len(weights)):
        if sum(bits) <= TEAM_BUDGET:
            score = site_score(bits, weights, redundancy)
            if score > best_score:
                best_bits, best_score = bits, score
    return best_bits, best_score


def solve_greedy(weights, redundancy):
    """Add the site with the largest positive marginal value each round."""
    bits = [0] * len(weights)
    current_score = 0.0
    while sum(bits) < TEAM_BUDGET:
        choices = []
        for i in range(len(weights)):
            if bits[i]:
                continue
            candidate = bits.copy()
            candidate[i] = 1
            choices.append((site_score(candidate, weights, redundancy), i))

        next_score, next_site = max(choices)
        if next_score <= current_score:
            break
        bits[next_site] = 1
        current_score = next_score
    return tuple(bits), current_score


def build_qubo(weights, redundancy, penalty):
    """Expand cost = -score + penalty * (number_selected - budget)^2."""
    n = len(weights)
    linear = -weights + penalty * (1 - 2 * TEAM_BUDGET)
    quadratic = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            quadratic[i, j] = redundancy[i, j] + 2 * penalty
    constant = penalty * TEAM_BUDGET**2
    return constant, linear, quadratic


def qubo_cost(bits, constant, linear, quadratic):
    cost = constant + sum(linear[i] * bits[i] for i in range(len(bits)))
    cost += sum(
        quadratic[i, j] * bits[i] * bits[j]
        for i in range(len(bits))
        for j in range(i + 1, len(bits))
    )
    return cost


def solve_qubo(constant, linear, quadratic):
    """Check every bitstring and return the true unconstrained QUBO minimum."""
    best_bits = None
    best_cost = float("inf")
    for bits in product((0, 1), repeat=len(linear)):
        cost = qubo_cost(bits, constant, linear, quadratic)
        if cost < best_cost:
            best_bits, best_cost = bits, cost
    return best_bits, best_cost


def benchmark(solver, *args):
    timings_ms = []
    for _ in range(BENCHMARK_RUNS):
        start = perf_counter_ns()
        solver(*args)
        timings_ms.append((perf_counter_ns() - start) / 1_000_000)
    return {"mean_ms": mean(timings_ms), "std_ms": pstdev(timings_ms)}


def selected_ids(bits, sites):
    return [int(sites.iloc[i]["site_id"]) for i, selected in enumerate(bits) if selected]


def main():
    sites = load_sites(INPUT_PATH)
    weights = sites["model_weight"].to_numpy()
    distances = build_distance_matrix(sites)
    redundancy = build_redundancy_matrix(weights, distances)

    exact_bits, exact_score = solve_exact(weights, redundancy)
    greedy_bits, greedy_score = solve_greedy(weights, redundancy)

    validated_qubo = None
    for penalty in QUBO_PENALTIES:
        constant, linear, quadratic = build_qubo(weights, redundancy, penalty)
        qubo_bits, qubo_minimum = solve_qubo(constant, linear, quadratic)
        if qubo_bits == exact_bits:
            validated_qubo = {
                "penalty_A": penalty,
                "constant": constant,
                "linear": linear.tolist(),
                "quadratic_upper_triangle": quadratic.tolist(),
                "selected_site_ids": selected_ids(qubo_bits, sites),
                "bits": list(qubo_bits),
                "minimum_cost": qubo_minimum,
            }
            break

    if validated_qubo is None:
        raise RuntimeError("No tested QUBO penalty reproduced the exact solution")

    results = {
        "model": "budget-constrained weighted site selection with pairwise redundancy",
        "assumptions": {
            "team_budget": TEAM_BUDGET,
            "operational_radius_km": OPERATIONAL_RADIUS_KM,
            "redundancy_scale": REDUNDANCY_SCALE,
            "landmark_minimum_weights": LANDMARK_MINIMUM_WEIGHTS,
        },
        "site_order": [int(site_id) for site_id in sites["site_id"]],
        "raw_weights": sites["weight_c_i"].astype(float).tolist(),
        "model_weights": weights.tolist(),
        "distance_matrix_km": distances.tolist(),
        "redundancy_matrix": redundancy.tolist(),
        "exact": {
            "selected_site_ids": selected_ids(exact_bits, sites),
            "bits": list(exact_bits),
            "score": exact_score,
        },
        "greedy": {
            "selected_site_ids": selected_ids(greedy_bits, sites),
            "bits": list(greedy_bits),
            "score": greedy_score,
        },
        "qubo": validated_qubo,
        "timing": {
            "runs": BENCHMARK_RUNS,
            "exact": benchmark(solve_exact, weights, redundancy),
            "greedy": benchmark(solve_greedy, weights, redundancy),
        },
    }

    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")

    print("Track B result")
    print(f"  Model: {results['model']}")
    print(f"  Candidate sites: {len(sites)}")
    print(f"  Ranger-team budget: {TEAM_BUDGET}")
    print(f"  Exact selection: {results['exact']['selected_site_ids']}")
    print(f"  Greedy selection: {results['greedy']['selected_site_ids']}")
    print(f"  Validated QUBO penalty A: {results['qubo']['penalty_A']}")
    print(f"  Results written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
