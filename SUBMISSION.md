# Submission Summary — Signal in the Bush

**Theme:** Quantum Impact

*This effort is supported by Qollab & IonQ.*

## Written Summary (by judging criterion)

### Novelty and Creativity
Quantum hackathons are saturated with job-shop-scheduling and portfolio-optimization QAOA demos. This project instead applies the hybrid quantum/classical pipeline to **conservation**: real GPS-collar elephant movement data, scoped to the Gourma, Mali population (Salif Keita — the longest documented land migration of any African elephant), to choose anti-poaching sensor placements. The combination of real wildlife-tracking data, a correctness-driven pipeline redesign mid-build (see below), and an honest "here's exactly where QAOA stands" framing rather than an overclaimed speedup is the novel contribution — not a new algorithm, but a disciplined application with real data and real constraints.

### Technical Execution
The pipeline is built from verified, real data end to end, not placeholders:
- **Data:** downloaded directly from the Movebank Data Repository's REST API (not the JS-rendered landing page); discovered mid-build that the package secretly bundles two unrelated elephants on different continents (Mali vs. Kenya) and corrected scope to one coherent population.
- **Methodology fix:** a teammate caught that raw GPS-fix density conflates "animal stood here" with "animal passes through here" — fixed via a dwell/transit speed split before clustering, so sensor candidates come from movement corridors, not rest sites.
- **Correctness fix:** a second teammate caught that the QUBO formulation is not literal maximum coverage (true coverage needs a qubit per demand point — infeasible under the <16 qubit cap). Resolved by building two honestly-separate baselines: a true max-coverage classical solver (real $1-1/e$ guarantee) and the qubit-budget proxy QAOA actually solves, then reporting both.
- **QUBO → Ising conversion is numerically validated**, not hand-derived on faith: the script brute-forces every bitstring and checks the Ising Hamiltonian's energy against the QUBO objective before any quantum circuit runs. This caught two real bugs (an unzeroed self-overlap diagonal, and a broken approximation-ratio metric) before they could produce misleading results.
- **QAOA results are reported honestly**: approximation ratio improves from p=1 (-29%, unconverged) to p=2 (65%), then plateaus at p=3. It does not find the true optimum at any tested depth — stated plainly rather than hidden.

### Impact Potential
Anti-poaching resource allocation is a real, current problem: ranger patrols and camera traps are scarce relative to the corridors wildlife actually use. The pipeline is directly extensible to other collared populations and other conservation areas on the same (free, CC0) Movebank data infrastructure. The qubit-budget-respecting proxy formulation technique — approximating coverage via pairwise redundancy penalty instead of per-demand-point indicator variables — generalizes to other small-budget facility-location problems under the same quantum hardware constraints.

### Documentation Quality
The full technical report, QUBO derivation (including the qubit-budget gotcha and how it's avoided), dataset provenance, and an honest accounting of every bug found and fixed during the build are in [`README.md`](README.md). Task breakdown and team division of labor are in [`TASKS.md`](TASKS.md). All code is in [`scripts/`](scripts/), run in this order: `extract_pinch_points.py` → `build_qubo.py` → `run_qaoa.py` → `build_demo_map.py`.

## Disclosure

- **Dataset:** Wall, Wittemyer, LeMay, Douglas-Hamilton & Klinkenberg (2014), Movebank Data Repository, doi:10.5441/001/1.f321pf80, CC0 1.0 Universal. Full citation and license in [`README.md`](README.md#3-dataset--downloaded-and-verified).
- **Libraries:** Qiskit + Qiskit Aer (quantum circuits/simulation), scikit-learn (DBSCAN), pandas/numpy (data processing), folium (demo map), scipy (classical optimization) — all open source, used under their respective licenses, no modification to the libraries themselves.
- **AI tool use:** Claude (Anthropic) was used throughout development — for data pipeline code, the QUBO/Ising derivation and its numerical validation, bug fixes, documentation, and this summary. All quantum-domain decisions (formulation choices, parameter values, interpretation of results) were reviewed by the team; the dwell/transit methodology fix and the max-coverage-vs-proxy correctness fix originated from team members' own review of the work, not from the AI.
- **Team:** built during the Oct 9–11 build window, by the team registered for this hackathon. No prior-existing code reused.

## License

MIT — see [`LICENSE`](LICENSE).
