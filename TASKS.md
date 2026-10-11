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
Split in two, after van's correctness catch ([README §6-7](README.md#6-step-2--qubo-formulation)) — this is **not** literal max-coverage, it's a pairwise-penalty proxy, for qubit-budget reasons. Don't conflate the two baselines below.

- [x] **True max-coverage baseline — van's branch.** Real coverage sets (fixes within radius $r$ of each site), exact ILP + greedy with the real $1{-}1/e$ guarantee, $k=3$. Van hit a push permission error on their branch — check their GitHub collaborator role is set to **Write** (not Read/Triage) in repo Settings → Collaborators, then merge it in.
- [ ] **Proxy QUBO baseline — demonnslayer.** Build $Q_{overlap}$ from pairwise distance against the real `data/candidate_sites.csv` (not mock data — Track A is done)
- [ ] Implement the soft-penalty QUBO — **not** `qiskit_optimization`'s inequality→slack converter (reread §6, it's a qubit-budget trap)
- [ ] Apply the Lake Banzena landmark boost to $c_i$ (§5/§6) before finalizing weights
- [ ] Exact brute-force optimum of the proxy QUBO itself, timed — this validates/tunes $A$, it is not the true-coverage baseline above
- [ ] At the end: report QAOA-vs-proxy-optimum **and** proxy-result-vs-true-coverage-optimum as two separate numbers (§7) — don't collapse them

## Track C — QAOA / Qollab / IonQ Execution
- [ ] Start now building the Qiskit harness against a toy random QUBO — don't wait on Track B
- [ ] `SparsePauliOp` construction, QAOA ansatz, `SamplerV2` call against the IonQ simulator on Qollab
- [ ] Get $p=1$ working and banked **first** — this is the result you can't afford to not have
- [ ] Then $p=2, 3$ if the queue and clock allow
- [ ] Log shots, depth, wall-clock for every run (feeds the metrics table, [§10](README.md#10-evaluation-metrics))
- [ ] Swap in Track B's real QUBO once validated

## Track D — Demo, Repo Hygiene, Video
- [x] Root `LICENSE` (MIT) + mandatory attribution string — done
- [ ] Folium/Plotly map — build against mock sites first, swap to real data last
- [ ] Before/after coverage heatmap
- [ ] Assemble the metrics table from B + C's numbers
- [ ] 2-min video pitch — record **last**, once something real is on screen
- [ ] Final pass: confirm repo README, attribution string, and dataset citation are all still accurate after everyone's merged

## Dependencies at a glance

```
A (data) ──► swap-in ──► B (QUBO/classical) ──► swap-in ──► C (QAOA)
                                                               │
mock data ──► B starts immediately                            │
mock data ──► C starts immediately ◄───────────────────────────
mock sites ──► D starts immediately, swaps in real results from B+C/A last
```

Claim a track in the group chat before starting so two people don't build the same mock harness.
