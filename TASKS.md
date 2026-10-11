# Signal in the Bush — Task Split

Four tracks, sized to run in parallel. Full technical detail for every item is in the repo's [`README.md`](README.md) (the technical report) — this file is just the checklist and who-waits-on-whom.

**The unlock: don't go fully sequential.** Track A (data) is the only hard blocker on real numbers, but B, C, and D can all start immediately against **mock data** — a fake list of 10 candidate sites with made-up coordinates and weights — and swap in A's real output once it lands. Waiting on A to finish before starting B/C/D wastes most of the team's remaining time.

## Track A — Data & Corridor Extraction (critical path — start first)
- [x] Download the primary dataset CSV ([README §3](README.md#3-dataset--downloaded-and-verified)) — done; discovered it bundles 2 unrelated elephants (Mali + Kenya), scoped to Salif Keita (Mali/Gourma) only
- [x] Implement dwell/transit speed split (the demonnslayer fix — [§5](README.md#5-step-1--corridor--pinch-point-extraction)) — `scripts/extract_pinch_points.py`
- [x] DBSCAN on transit fixes only → 8–15 candidate sites — converged at 8 clusters, `data/candidate_sites.csv`
- [x] Guard: if >15 clusters, merge down before handing off — not needed this run (landed at 8 on first convergence)
- [x] **Output contract for everyone else:** `data/candidate_sites.csv` with `{site_id, lat, lon, weight_c_i, n_fixes, n_individuals, individuals}` — ready for Track B
- [x] Sanity-check against Wall et al. 2013 / external sources — **finding, not just a check:** `site_id=7` (65 fixes) sits ~8km from Lake Banzena, the documented primary dry-season water source for this entire elephant population (one of only two lakes that don't dry up; "elephants and humans rely heavily on it"). The *dominant* cluster `site_id=0` (6,603 fixes) is a different, unidentified location ~50km away. **Implication for Track B:** pure fix-count weighting underrates Banzena (currently weight 0.0098) relative to its real ecological importance — exactly the failure mode demonnslayer flagged, now confirmed in real data. Track B should consider a known-landmark boost, not just raw `n_fixes`, before finalizing $c_i$.

## Track B — QUBO & Classical Baselines
Split in two, after van's correctness catch ([README §6-7](README.md#6-step-2--qubo-formulation)) — this is **not** literal maximum coverage. Don't collapse the two baselines.

- [x] **True GPS-fix max coverage — van.** `scripts/true_max_coverage.py`. Each site covers Salif Keita transit fixes within a 25 km ranger-team radius. Exact OR-Tools and greedy both select sites **0, 2, 5** (1,179 of 7,066 fixes, 16.7%). Proxy sites 0, 2, 7 cover 1,125 fixes (15.9%). Results: `data/true_coverage_results.json`.
- [x] **Proxy QUBO — `scripts/build_qubo.py` and `scripts/optimize_sites.py`.** Pairwise redundancy, Lake Banzena boost, soft-penalty QUBO, no slack qubits. Exact/greedy proxy select sites **0, 2, 7**. $A=0.5$ is validated. Track C coefficients stay in `data/qubo_*.npy`; timed proxy results are in `data/track_b_results.json`.
- [x] Report QAOA-vs-proxy optimum (Track C) and proxy-vs-true-GPS-coverage optimum as separate numbers (§7)

## Track C — QAOA / Qollab / IonQ Execution
- [ ] Start now building the Qiskit harness against a toy random QUBO — don't wait on Track B
- [x] `SparsePauliOp` construction, QAOA ansatz, `SamplerV2` — `scripts/run_qaoa.py`, run on local Aer
- [x] $p=1,2,3$ all run and banked — 65% approximation ratio plateau from $p=2$ ([README §8](README.md#8-step-4--quantum-pipeline))
- [x] Shots/depth/wall-clock logged (`data/qaoa_result_p*.txt`)
- [x] Ran against the real QUBO (not mock)
- [ ] **Still open: run on Qollab's actual IonQ simulator**, not just local Aer — needs whoever has Qollab access

## Track D — Demo, Repo Hygiene, Video
- [x] Root `LICENSE` (MIT) + mandatory attribution string — done
- [x] Interactive map — `demo/map.html`, real data, no mock swap needed (Track A finished first)
- [x] Metrics table assembled from B + C's real numbers ([README §10](README.md#10-evaluation-metrics))
- [x] Written summary + disclosures + theme tag — `SUBMISSION.md` (required by the official rules, separate from README)
- [ ] 2-min video pitch — script ready (`demo/VIDEO_SCRIPT.md`), **not yet recorded**
- [ ] **Publish to Qollab.xyz itself** — separate requirement from the GitHub repo; needs a Qollab project page with the SUBMISSION.md content
- [ ] Final pass: open the published Qollab project from a logged-out browser before the deadline and confirm it runs start to finish (official rules, Submission requirements)

## Dependencies at a glance

```
A (data) ──► swap-in ──► B (QUBO/classical) ──► swap-in ──► C (QAOA)
                                                               │
mock data ──► B starts immediately                            │
mock data ──► C starts immediately ◄───────────────────────────
mock sites ──► D starts immediately, swaps in real results from B+C/A last
```

Claim a track in the group chat before starting so two people don't build the same mock harness.
