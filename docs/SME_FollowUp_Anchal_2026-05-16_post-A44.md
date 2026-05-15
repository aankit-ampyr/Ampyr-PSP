# PSP — Follow-up to Anchal (2026-05-16)

> **2026-05-16 — DECISION TAKEN.** Ankit chose **Path 1** (accept ±0.5 pp for v1; queue DSCR sculpting + Equity IRR for v2). v1 audit CLOSED. Engine reproduces Excel within ±0.5 pp across all 4 audit rows; residual 0.3-0.5 pp pessimism documented as the structural carve-out per Anchal Q2 reply. v1 use case: pre-IC screening, what-ifs, sizing comparisons. Excel remains source-of-truth for IC-pack headline IRR. See decisions log A45 + Spec §9/§10. Anchal Teams confirmation to follow.

---

**For:** Anchal Gupta
**From:** Ankit Agarwal
**Date:** 2026-05-16
**Re:** Q1 (Insurance) + Q2 (audit tolerance) — implementation outcome

---

## Q1 — Insurance: implemented per your reply

Took the second option ("hardcode yearly nos as per excel") combined with linear per-MW scaling for the 115 MWp configs in the audit matrix.

Source: `Solar&BESS Operation!r168` (Insurance on Plant & Machinery, lifetime £8,806.63k). Schedule extracted column-by-column from Excel.

| Ops year | £k | Pattern |
| ---: | ---: | --- |
| 1 | 281.94 | construction premium tail (Marine Cargo + CAR + MCDSU + DSU + TPL still active) |
| 2 | 287.58 | construction premium tail |
| 3 | 205.33 | -30% discount kicks in, baseline drops |
| 4 | 209.44 | |
| 5–10 | ~200–207 | alternating 0% / 5% discount |
| 11 | 206.27 | anchor |
| 12–35 | 210.4 → 331.8 | 2% / yr compound from year 11 base |

Engine reproduces £8,806.79k lifetime vs your £8,806.63k Excel — perfect match to £0.16k.

## Q2 — Audit outcome after Q1 fix

Counter-intuitive but the Insurance fix moved the audit AWAY from target, not towards it. Pre-fix, the engine used 2.021 £/kWp × CPI which had a fortuitous cancellation: it under-shot the construction premium years (1–2) and over-shot the late years, with lifetimes close to balanced. The schedule front-loads cost into the construction-premium years where NPV weighting is highest, so removing the cancellation revealed a wider structural gap.

| Case | Pre-A44 Combined | Post-A44 Combined | Δ (pp) |
| ---: | ---: | ---: | ---: |
| d13 (82 / £170 / 250 MWh) | 8.88% | 8.84% | -0.04 |
| m82_160 (82 / £160 / 250 MWh) | 7.35% | 7.32% | -0.03 |
| m115_170 (115 / £170 / 250 MWh) | 9.61% | 9.57% | -0.04 |
| m115_160 (115 / £160 / 250 MWh) | 8.31% | 8.27% | -0.04 |

Engine is now Excel-faithful on Insurance.

## Tolerance — your conditional offer

You wrote:

> "Pl bring the tolerance level in +/- 0.2 if possible **unless it is happening because of gearing or debt sizing not built currently** which may impact the tax shield, hence IRR"

The Insurance fix confirms your second clause: the residual gap *is* the structural carve-out. We don't yet model DSCR-driven gearing convergence (Excel reduces senior gearing below the 80% target via the cash sweep, raising the effective SHL principal — that mechanism feeds the CIR cap with more headroom, increasing the tax shield). Equity-IRR feedback isn't in v1 either.

State vs each tolerance level:

| Tolerance | Rows passing |
| ---: | --- |
| ±0.1 pp | 0 of 4 |
| ±0.2 pp | 0 of 4 (m115 rows at -0.23 — just outside) |
| ±0.3 pp | **2 of 4** (m115_170, m115_160) |
| ±0.5 pp | **4 of 4** |

## Two options for closing v1

1. **Accept ±0.5 pp for v1**, given the structural exclusions are documented (Spec §6 "engine logic that does not become user input" + decisions log A44 / A21 / A22). 4 of 4 rows pass. Production Doublu handoff unblocked.
2. **Add DSCR convergence to v1 scope**. ~1–2 weeks engineering: iterate senior gearing down until `min(DSCR over schedule) ≥ 1.40`, recompute SHL principal, re-run CIR cap. Brings audit rows within ±0.1 pp (best estimate). Adds equity-IRR computation as a free byproduct. Defers v1 closure by 2 weeks.

My recommendation: option 1 for v1; queue option 2 for v1.1 if the equity-IRR view becomes a stakeholder ask. Happy to discuss either way.

— Ankit
