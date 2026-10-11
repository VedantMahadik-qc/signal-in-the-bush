# Signal in the Bush — Task Split

Four tracks, sized to run in parallel. Full technical detail for every item is in the repo's [`README.md`](README.md) (the technical report) — this file is just the checklist and who-waits-on-whom.

**The unlock: don't go fully sequential.** Track A (data) is the only hard blocker on real numbers, but B, C, and D can all start immediately against **mock data** — a fake list of 10 candidate sites with made-up coordinates and weights — and swap in A's real output once it lands. Waiting on A to finish before starting B/C/D wastes most of the team's remaining time.

## Track A — Data & Corridor Extraction (critical path — start first)
- [ ] Download the primary dataset CSV ([README §3](README.md#3-dataset--verified-this-session)), confirm actual individual/animal count in the data
- [ ] Implement dwell/transit speed split (the demonnslayer fix — [§5](README.md#5-step-1--corridor--pinch-point-extraction))
- [ ] DBSCAN on transit fixes only → 8–15 candidate sites
- [ ] Guard: if >15 clusters, merge down before handing off
- [ ] **Output contract for everyone else:** a CSV/JSON of `{site_id, lat, lon, weight_c_i}` — publish this as soon as you have even a rough version, don't wait for it to be polished

## Track B — QUBO & Classical Baselines
- [ ] Start now against mock candidate sites (10 fake points + fake weights)
- [ ] Build $Q_{overlap}$ from pairwise distance ([§6](README.md#6-step-2--qubo-formulation))
- [ ] Implement the soft-penalty QUBO — **not** `qiskit_optimization`'s inequality→slack converter (reread §6, it's a qubit-budget trap)
- [ ] Exact brute-force / OR-Tools baseline, greedy $1{-}1/e$ baseline, both timed
- [ ] Validate: does the QUBO's own optimum match the real constrained problem's optimum? Fix $A$ before handing off to Track C
- [ ] Swap in Track A's real sites once available; re-validate

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
