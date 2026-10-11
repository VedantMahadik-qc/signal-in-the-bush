# Signal in the Bush — Technical Report
### Quantum-Optimized Anti-Poaching Sensor Placement
Qollab × IonQ Hackathon — Quantum Impact Track

*This effort is supported by Qollab & IonQ.*

## 0. Status

This project was selected through the team's internal decision-matrix process (18.0/20, winner over three other candidates including a job-shop-scheduling proposal) — that ideation process lives in the team's separate planning workspace, not in this repo.

**Submission deadline is today:** Sunday, Oct 11, 7:00 PM ET.

Task breakdown for the team: [`TASKS.md`](TASKS.md).

## 1. Executive Summary

Anti-poaching teams can only cover a handful of the many corridor pinch-points — river fords, fence gaps, trail junctions — where wildlife repeatedly cross. We extract real high-traffic pinch-points from GPS-collar elephant movement data, formulate camera-trap/ranger placement as a budget-constrained max-coverage problem, solve the compact combinatorial core (8–14 binary site decisions) with QAOA on the IonQ simulator via Qollab, and use a classical solver to validate and repair the result. The deliverable is an honest, working hybrid pipeline on real conservation data with a visually and emotionally strong demo — not a speed claim.

## 2. Why Quantum Here, Stated Honestly

At 8–14 binary variables, the search space is at most $2^{14} = 16{,}384$ states — a classical computer enumerates that exactly in microseconds. No speed advantage exists to chase at this size, and none has ever been empirically demonstrated for QAOA over classical methods on standard combinatorial optimization problems *at any size*. The hackathon's own mandate (bounded to <16 qubits, "to avoid execution timeouts on the simulator queue") confirms this is a methodology demo, not a performance claim.

So the honest pitch is: this is an end-to-end hybrid pipeline — real conservation data → corridor extraction → QUBO → QAOA → classical feasibility repair → validated decision — proven to work, with data showing *where QAOA stands* (approximation ratio vs. depth $p$, vs. the exact classical optimum) rather than an overclaimed "quantum beats classical" result. Lead with the real-data pipeline and the conservation framing; let the benchmark numbers be exactly as good (or modest) as they actually are.

## 3. Dataset — Verified This Session

**Primary: Movebank Data Repository — Wall et al. 2014, African elephant tracking (source: Save the Elephants)**
- URL: https://datarepository.movebank.org/entities/datapackage/38e05433-0a6f-49c4-ab77-0511e716786c
- License: **CC0 1.0 Universal** (public domain)
- Access: **no account or login required** — direct bitstream download links on the page
- Format/size: main tracking data as CSV (~6.9 MB), a small reference-data CSV, and a `README.txt`
- This is a citable, DOI-backed public dataset, satisfying hackathon mandate #1 ("must use a recognized public dataset").

**Caveat (verify on download, don't assume):** search evidence converging on this same Wall et al. 2014 / Save the Elephants study independently describes a Samburu National Reserve, Kenya program with 23,494 GPS fixes at 1-hour intervals, 9 elephants collared but only **2 published** to the public Movebank record — while a direct fetch of the dataset's own landing page read it as a single individual. Both could be describing the same package inconsistently (page-summarization artifacts, not a confirmed contradiction). **Action:** download the CSV first thing and check the individual-ID column yourself — don't build the demo narrative on an unconfirmed animal count.

**Why this doesn't break the plan either way:** with 1–2 individuals, "pinch point" should be framed as *a location this animal/herd repeatedly revisits* (watering hole, river crossing, migration bottleneck) rather than *where multiple animals' paths cross* — which is still ecologically correct and still exactly where a ranger would want a camera trap. Reframe the demo copy accordingly rather than overstating multi-animal convergence.

**Backup, not yet verified:** [`ThermochronTracking Elephants Kruger 2007`](https://datarepository.movebank.org/items/34c4e37d-9989-473e-aa5a-187e35205d85) (Slotow, Thaker, Vanak) is on the same repository. Its page is JS-rendered and didn't yield details to an automated fetch this session — if the primary dataset turns out too sparse for a convincing corridor map, this is a two-minute manual check, not a research detour.

## 4. Pipeline

```
GPS CSV (Movebank)
   │  DBSCAN clustering (haversine)
   ▼
8–15 candidate pinch-points (centroid + crossing-density weight)
   │  QUBO formulation (Section 6)
   ▼
QAOA on IonQ simulator (Qollab, Qiskit 2.x SamplerV2)  ◄──┐ compare
   │  bitstring candidates                                │
   ▼                                                       │
Classical feasibility repair (trim/fill to budget k)       │
   │                                                       │
   ▼                                                       │
Final sensor placement ───────────────────────────► Exact classical optimum
                                                      + greedy (1-1/e) baseline
```

## 5. Step 1 — Corridor / Pinch-Point Extraction

**Team catch (credit: demonnslayer) — fixed below:** raw GPS-fix density is the wrong signal on its own. A cluster of many fixes in one place usually means the animal *stood there a long time* (a waterhole, shade, grazing) — ecologically real, but not what an ambush sensor wants. A corridor bottleneck is about *path geometry* (many transits funnel through a narrow spot), which can show up even with low dwell time. Conflating the two risks placing sensors at rest sites instead of actual crossing points.

**Fix — split dwell from transit before clustering:**
- Load the CSV; keep `individual-local-identifier`, `timestamp`, `location-lat`, `location-long`.
- Sort each individual's fixes by time. For each consecutive pair, compute step speed $v_t = \text{haversine}(p_t, p_{t+1}) / \Delta t$.
- Classify each fix as **dwell** (speed below a threshold — start with the individual's own median speed, or a fixed ecologically-reasoned cutoff like <0.5 km/h) or **transit** (above it).
- Cluster **transit fixes only** with DBSCAN, **haversine metric**, `eps` in meters-equivalent radians, tuned so cluster count lands at **8–15** (this directly becomes qubit count — see Section 6's qubit-budget constraint).
  - `sklearn.cluster.DBSCAN(metric='haversine')` expects radians; convert lat/long first, and convert `eps` from meters by dividing by Earth's radius (~6,371,000 m).
- Per transit cluster: centroid (mean lat/long of members) = candidate site location; member-fix count (optionally time-decayed or revisit-count weighted) = coverage weight $c_i$. Dwell clusters are computed too (they're good for the demo map as "known rest/water sites" context layer) but are **excluded from the sensor-placement candidate set** — say this distinction out loud in the demo narrative, it's the direct answer if a judge asks the same question demonnslayer asked.
- **Guard explicitly for the qubit cap:** if DBSCAN yields >15 transit clusters, either raise `eps`/`min_samples` or merge the lowest-weight clusters into their nearest neighbor until $n \le 15$. Don't discover this after the QUBO is built.

**Stretch goal, not required (demonnslayer's literal suggestion):** corroborate transit clusters against independently-known landmarks via OpenStreetMap's free, keyless Overpass API — query the study bounding box for `waterway=river`, `natural=water`, `barrier=fence`. Annotate each candidate site with distance to the nearest such feature ("this cluster sits 80m from a mapped river crossing") for demo credibility. This is corroborating evidence for the pitch, not a change to the QUBO itself — skip it under time pressure; the dwell/transit split above is the required fix, this is polish.

## 6. Step 2 — QUBO Formulation

Variables:
- $n$ candidate sites (8–14 target, hard cap 15), $x_i \in \{0,1\}$: sensor/team placed at site $i$.
- $c_i \ge 0$: normalized coverage weight (crossing density) of site $i$.
- $d_{ij}$: haversine distance between centroids $i,j$.
- $r$: assumed sensor/camera-trap effective detection radius (pick a defensible domain value, e.g. 300–500 m, and state the assumption in the writeup).
- $Q_{ij} = w \cdot \max(0,\, 1 - d_{ij}/r)$: redundancy weight between sites within range of each other (tunable scale $w$).
- $k$: sensor/ranger-team budget.

$$\text{maximize} \quad f(x) \;=\; \sum_i c_i x_i \;-\; \sum_{i<j} Q_{ij}\, x_i x_j \;-\; A\left(\sum_i x_i - k\right)^2$$

Qiskit minimizes, so the cost Hamiltonian is $C(x) = -f(x)$, mapped to Pauli-$Z$ via $x_i = (1-z_i)/2$.

**The qubit-budget gotcha (read this before using `qiskit_optimization`'s converters):** the textbook path — model $\sum_i x_i \le k$ as an inequality constraint in a `QuadraticProgram` and let `InequalityToEquality` + `LinearEqualityToPenalty` handle it — adds a binary-encoded **slack variable** (roughly $\lceil\log_2(k+1)\rceil$ extra qubits) to turn $\le$ into $=$. At $n=14$ candidate sites that can push you to ~18 qubits, **over** the mandate's <16 cap.

The formulation above avoids this entirely: $(\sum_i x_i - k)^2$ is a **soft** quadratic penalty centered at $k$, not an exact constraint, so it expands directly into linear and quadratic terms in the existing $x_i$ (using $x_i^2 = x_i$ for binary variables) with **zero new variables**. Qubit count stays exactly equal to candidate-site count — comfortably inside budget with headroom to spare.

Tradeoff to know about: this penalty softly biases toward using *exactly* $k$ sites rather than *up to* $k$. That's fine here because unused budget is (almost) never better left unused when $c_i \ge 0$, and it's fully covered by the repair step below regardless. Tune $A$ empirically — start around $A \approx \max_i c_i$ and sweep (e.g. $0.5\times$ to $5\times$) — and **validate the QUBO against the exact classical solver before spending IonQ simulator queue time on it**: if the exact optimum of your QUBO doesn't match the exact optimum of the real constrained problem, fix $A$ first, don't debug it on the quantum side.

## 7. Step 3 — Classical Baselines

1. **Exact:** at $n \le 15$, this is literally brute-forceable ($2^{15}=32{,}768$ states) in microseconds, or solve the equivalent ILP via OR-Tools CP-SAT / PuLP for a cleaner comparison story. This is the ground truth, not just "a strong heuristic" — the proposal's own framing undersells it slightly.
2. **Greedy:** the classical $1-1/e$ provable-approximation max-coverage heuristic — a real theoretical baseline, not ad hoc.

**Timing methodology (mandate #2 — must be "rigorously timed"):** same machine, same problem instance, wall-clock time, mean ± std over multiple runs/seeds for both classical methods. Report this alongside the QAOA numbers even though at this $n$ classical is trivially faster — say so plainly rather than burying it.

## 8. Step 4 — Quantum Pipeline

- Map $C(x)$ to a `SparsePauliOp` Ising Hamiltonian.
- Run QAOA at depth $p \in \{1, 2, 3\}$ via Qiskit 2.x primitives (`SamplerV2`) on the IonQ simulator through Qollab.
- Record shot count, depth, and wall-clock per run — these are the actual "quantum parameters" metrics called for below, and the thing worth plotting against approximation ratio.

## 9. Step 5 — Classical Feasibility Repair

Extend the proposal's repair step slightly:
- **Over budget** ($\sum x_i > k$): greedily trim the lowest-marginal-coverage site first until feasible (as proposed).
- **Under budget** ($\sum x_i < k$): greedily *add* the highest-marginal-value remaining site until budget is used or no positive-marginal site remains — cheap, strictly improves coverage, and cleans up the soft-penalty's occasional under-shoot.

## 10. Evaluation Metrics

| Category | Metric |
|---|---|
| Solution quality | Expected interception coverage (%), redundancy wasted, budget utilization |
| Computational | Wall-clock to best feasible solution, approximation ratio vs. exact optimum |
| Quantum parameters | Approximation ratio vs. depth $p$, vs. shot count |

Plot approximation ratio vs. $p$ and vs. shot count — crossover/plateau behavior is a more interesting result than a single final number, and gives you something honest to say if the numbers are modest.

## 11. Demo & Visualization

- Interactive map (Folium or Plotly Mapbox): real elephant GPS trail as a glowing corridor, pinch-points pulsing as candidates, sensors flipping on as the optimizer runs, ending on a before/after coverage heatmap.
- 2-minute video pitch: ~45s problem framing, ~45s live map demo, ~30s benchmark metrics + IonQ execution proof (screenshot/log of the actual Qollab/IonQ job, not just local simulation — judges will ask).

## 12. Hackathon Compliance Checklist

| Mandate | Status |
|---|---|
| Recognized public dataset | ✅ Movebank Data Repository, CC0, DOI-backed (Section 3) |
| Classical baseline rigorously timed vs. hybrid | ⬜ Plan defined (Section 7) — not yet run |
| Quantum problem **under 16 qubits** (i.e. ≤15) | ✅ by construction if Section 5's cluster-count guard is enforced |
| Repo MIT-licensed | ✅ Root [`LICENSE`](LICENSE) |
| Mandatory attribution string present | ✅ At the top of this file |

## 13. Execution Plan (time-budget-resilient)

Phases are relative, not clock-anchored, since I don't know how many hours are actually left — tell me and I'll tighten this. Each phase has a cut line for what to skip if you're short on time.

1. **Data + corridor extraction** — download CSV, verify individual count (Section 3), DBSCAN to 8–15 pinch-points.
   *Cut line: if clustering is fighting you, hardcode a reasonable `eps` from a quick histogram of pairwise distances rather than tuning it perfectly.*
2. **QUBO + classical baselines** — build $Q$, run exact + greedy, sanity-check the QUBO's own optimum matches the real problem's optimum (Section 6).
   *Cut line: this step is not optional — it's your mandate #2 deliverable and your QAOA correctness check. Don't skip to save time; everything downstream depends on it.*
3. **QAOA on IonQ/Qollab** — run $p \in \{1,2,3\}$, log shots/timing.
   *Cut line: if the simulator queue is slow, run $p=1$ only and say so honestly in the writeup rather than waiting on a queue past your deadline.*
4. **Repair + metrics table** — apply Section 9's repair, assemble the metrics table (Section 10).
5. **Demo map** — Folium/Plotly map (compliance items in Section 12 are already done).
   *Cut line: a static before/after map image beats no visual. A live interactive map is the stretch goal, not the floor.*
6. **Video pitch** — record last, from whatever actually works by then.

## 14. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Dataset has fewer individuals than hoped, weak "corridor" narrative | Reframe as single-animal revisitation hotspots (Section 3) — still ecologically valid |
| DBSCAN yields >15 clusters, blows qubit budget | Explicit merge/guard step before QUBO construction (Section 5) |
| Automatic QP→QUBO slack variables push past 16 qubits | Use the hand-rolled soft-penalty formulation (Section 6), not the library's inequality converter |
| IonQ/Qollab simulator queue latency eats the clock on deadline day | Run $p=1$ first and bank a result immediately; add $p=2,3$ only if time remains |
| Judges ask "why quantum for 14 variables" | Section 2's honest framing — have it memorized, don't get caught flat-footed |
| Repo missing LICENSE/attribution at submission time | Fixed — see Section 12 |
| High-density GPS cluster is a rest/water site, not a transit bottleneck (caught by demonnslayer) | Dwell/transit speed split before clustering (Section 5) — candidate sites come from transit clusters only |

## 15. Immediate Next Steps

1. ~~Add root `LICENSE` (MIT) + attribution string~~ — done.
2. Download the primary dataset CSV and confirm individual count (unblocks everything else).
3. Scaffold the dwell/transit split + DBSCAN corridor-extraction script.
4. Build the QUBO + classical baselines, validate QUBO optimum against real-problem optimum before touching IonQ.

See [`TASKS.md`](TASKS.md) for how this splits across the team.

---

## Sources

- [Movebank Data Repository — Wall et al. 2014 African elephant dataset (primary, verified: CC0, no login, CSV)](https://datarepository.movebank.org/entities/datapackage/38e05433-0a6f-49c4-ab77-0511e716786c)
- [ThermochronTracking Elephants Kruger 2007 (backup, not yet verified)](https://datarepository.movebank.org/items/34c4e37d-9989-473e-aa5a-187e35205d85)
- [Movebank Data Repository — no-account-required CC0 policy](https://datarepository.movebank.org/help/faq)
