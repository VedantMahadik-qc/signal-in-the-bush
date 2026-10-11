# Demo Video Script (~2 min, not scored on production quality)

Record screen + voice. Rough timing, adjust live — a slightly-too-long honest take beats a rushed one.

## 1. Problem (0:00–0:30)
*Show: nothing fancy needed — just talk, maybe the README title.*

> "Anti-poaching teams have way more corridor pinch-points than they have rangers or camera traps to cover them. We used real GPS-collar data from a wild elephant — Salif Keita, part of the Gourma population in Mali, famous for the longest documented land migration of any African elephant — to find out where sensors should actually go, using a hybrid quantum-classical pipeline."

## 2. The data and the fix (0:30–1:00)
*Show: `demo/map.html` — zoom out to show the full trail, then zoom into the clustered sites.*

> "This is six years of real hourly GPS data. The naive approach — cluster by how often the elephant visits a spot — has a problem: it can't tell a water hole from a river crossing. A teammate caught this, so we split the data into 'dwell' fixes, where the elephant is just standing still, and 'transit' fixes, where it's actually moving through — and only cluster the transit fixes into candidate sensor sites."
>
> *(point at the gold-highlighted site near Lake Banzena)* "This gold site is Lake Banzena — the documented primary dry-season water source for this entire elephant population. It only had a handful of GPS fixes, so raw frequency would have missed it. We manually corrected for that."

## 3. QUBO → QAOA (1:00–1:30)
*Show: terminal output of `run_qaoa.py`, or the results table.*

> "We formulate sensor placement as a budget-constrained optimization — pick 3 sites out of 8, maximizing coverage while penalizing redundant nearby picks. A second catch from the team: this isn't literal maximum coverage — that would need a qubit per GPS fix, way over the hackathon's qubit cap — so it's a proxy formulation that fits in 8 qubits. We validated that proxy numerically against the real max-coverage problem before trusting it, and against our own Ising-Hamiltonian math before running anything quantum.
>
> We ran QAOA at depth 1 through 3 on [Qollab's IonQ simulator / local Aer — update once confirmed]. Approximation ratio goes from -29% at p=1 to 65% at p=2, then plateaus — it never finds the full 3-site optimum. We're reporting that honestly rather than cherry-picking a better run."

## 4. Result (1:30–1:50)
*Show: map again, highlighting the 3 gold sites.*

> "The final recommended placement: these three sites, including Lake Banzena. Both our classical ground-truth solver and the QAOA-compatible proxy agree on the same answer here — a good sign the simplification needed for the qubit budget isn't costing us anything at this scale."

## 5. Close (1:50–2:00)

> "Full pipeline, real data, two real bugs caught and fixed by the team along the way, and an honest account of where quantum actually helps and where it doesn't yet. Code's all on GitHub and Qollab, links below."

---

**Before recording:** confirm what's actually true by then — whether QAOA ran on Qollab's simulator specifically (say so) or only validated locally on Aer (say that instead, it's still a legitimate result, just say it accurately).
