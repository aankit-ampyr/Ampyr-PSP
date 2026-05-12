# Project IRR Integration — Decisions Log

**Status:** Pre-implementation. Living document — every decision and fork related to the Project IRR module is recorded here.
**Goal:** Add a Project IRR (PIRR) calculation to the operational sweep so the user can rank battery + solar configurations on financial return alongside operational metrics.
**Source of truth for IRR logic:** `Financial Model/Off-Grid Solution v8.xlsm` (the v8 workbook).
**Companion doc:** [Financial_Assumptions_Spec.md](Financial_Assumptions_Spec.md) — current locked state in spec form (what to build). This file (decisions log) — running ADR-style trail with reasoning and reversals.

---

## Update protocol

This document is the canonical record of every decision made about the Project IRR module. Update it whenever:

- A new decision is taken (add an entry to Revisions, add/update the relevant `A*` section)
- A decision is reversed (mark the old text as superseded with a strikethrough, add the replacement, log the reversal in Revisions)
- A fork in the design is taken (record what was chosen and what was rejected, with the reason)
- An open item is resolved (move from Open Items to a numbered decision)
- An assumption from the Excel workbook is questioned, validated, or overridden

Each Revisions entry: date, what changed, why. Each `A*` decision: keep originals visible (don't delete) so the history is recoverable.

---

## Revisions log

| Date | Change | Why |
|---|---|---|
| 2026-04-30 (approx) | **Initial decisions captured** (A1–A10): scope, two sweep modes, full revenue stack, capex scaling rules, IDC/Financing/DSRA exclusion, monthly granularity, audit-first approach. | Pre-SME scoping conversation. |
| 2026-05-05 | **A5 fork resolved:** chose "PIRR column in Step 3 results" (option A) over a separate Step 3b page or running it in Step 7. | User preference for in-place ranking. |
| 2026-05-05 | **Sweep architecture changed:** financial sweep moved out of Step 3 into a new optional Step 3a (between Sizing and Results). Step 7 stays as single-config deep-dive. | Cleaner separation; operational sweep stays cached when financial assumptions change. |
| 2026-05-05 | **Approach simplified:** decided to mirror Excel strictly (no external market checks) and pre-fill ~80 user-editable assumptions with Excel defaults. SME ask trimmed from ~50 questions to 6. | Strict-mirror dividend; faster v1; user-editable inputs handle the "is this market value still current?" question. |
| 2026-05-07 | **A2 superseded:** dispatch re-run inside financial layer rejected. Replaced by Year-1-aggregates-from-Step-3 + analytical degradation in financial layer. | SME confirmed degradation is a financial-layer concern, not a dispatch-layer concern. |
| 2026-05-07 | **A4 partially reversed:** IDC + Financing Fees + pre-funded DSRA now **included** in PIRR capex (was excluded as textbook). | SME directive: align with Excel methodology, not textbook. |
| 2026-05-07 | **A8 corrected (tax shield):** tax in PIRR now `(EBIT − Interest) × tax_rate`, not `EBIT × tax_rate`. PIRR is debt-aware on the tax line even though FCFF is ungeared in cash terms. | SME correction of definition; Ampyr internal convention differs from textbook. |
| 2026-05-07 | **A11–A15 added:** DC vs AC capacity convention, degradation analytics, audit target shift to 8.9% (from 9.23%), canonical reference profiles renamed/relocated, minimal-debt-schedule for tax shield. | All landed during SME review. |
| 2026-05-07 | **Audit target changed:** from `Consol Cash Flows!B9 = 9.23%` (Burton Top-3.8h, 3.8 hr BESS in old Excel snapshot) to **8.9%** for `82 MWp DC / 58.4 MW grid / £170 PPA / 250 MWh BESS`. | SME-supplied 4-row reference matrix supersedes the older Excel cell value. |
| 2026-05-07 | **Reference profiles renamed and moved:** `Inputs/Answers/Burton Leonard_Project_VCN_HourlyRes_*.CSV` → `Inputs/Burton_Leonard_{82,115}MWp_DC_*.csv`. Asset is **Burton Leonard** (real site name); "Burton Top" was the Excel case label. | Naming clarity + accessibility from the data-loader dropdown. |
| 2026-05-07 | **Companion spec doc created:** [Financial_Assumptions_Spec.md](Financial_Assumptions_Spec.md) holds the current locked state in build-ready form. This file remains the running history. | Two complementary roles: spec = "what to build today"; decisions log = "how we got here and what was rejected". |
| 2026-05-07 | **A16 added: A9 Step A audit run; rewrite confirmed.** Existing engine produces 8.46% vs 8.9% target (−44 bps) for D13. All four SME matrix rows breach the 0.1 pp tolerance. `gas_ownership_share=0.58` calibration constant in `consolidated_model.py` violates Guardrail #5. | Triage rule per A9 Step B (>0.1 pp → rewrite). |
| 2026-05-07 | **Old engine parked, not deleted.** `src/financial_model.py` → `src/financial_model_v0.py`; `src/consolidated_model.py` → `src/consolidated_model_v0.py`. Imports updated in 7 consumers (`gas_model`, `Step7_Financial`, `tests/test_project_irr`, `tests/test_financial_regression`, `tests/validate_vs_excel`). Test suite still runs and reproduces 8.46% — audit reproducibility preserved. | User direction. Parking keeps the failure mode auditable while the rewrite proceeds. |
| 2026-05-11 | **A17 added: rewrite scaffold + 6 structural fixes from Excel dumps.** New engine [src/project_irr.py](../src/project_irr.py) (~650 lines, no calibration constants). D13 PIRR trajectory across the session: 19.61% → 13.53% → 12.25% → 10.27%. Structural fixes (each traceable to a specific Excel cell/row): gas PPA→merchant switchover at year 10 + EOL at year 20 (Cash Flows-Gas r21 conditional); gas opex on gross 28.32 MW not effective 25 MW (verified via Insurance back-calc); gas Major Maintenance + Reactive Maintenance per MWh (Cash Flows-Gas r44 + r48); BESS opex tenor 10 yr (Inputs F112); Solar Corrective Maintenance as level annual not full rate (FS r39, 8-event step pattern); BESS LTSA + PCS Warranty + Augmentation step costs (BESS r113-115); land lease `max(fixed, rev_dep)` not sum (Op r147/148/157 logic); BESS revenue zeroed to match Excel snapshot (FS r24 = £0). | Excel dump evidence + Guardrail #5 (no fudge factors). |
| 2026-05-11 | **3 SME questions queued in [docs/Project_IRR_SME_Questions_v2.md](Project_IRR_SME_Questions_v2.md).** Q1: is 8.9% from the current workbook or a different snapshot? Q2: should BESS revenue switches be ON or OFF for the Burton Leonard case (Excel currently shows £0)? Q3: is `max()` a fair approximation of the `Solar&BESS Operation` r155 Lease Adjustment? Engine paused at 10.27% PIRR pending answers. | Excel-side debugging exhausted; remaining 137 bps depends on these answers. |
| 2026-05-11 | **Q4 added to v2 questions:** PPA-tariff sensitivity gap (engine 0.55 pp vs Excel 1.5 pp on £170→£160). | Full SME matrix run revealed structural sensitivity gap on top of magnitude gap. |
| 2026-05-12 | **A20 added: Anchal answered Q1-followup + Q4.** Q1: compare against BOTH `S+B PIRR = 8.9%` and `Combined S+B+Gas PIRR = 9.2%` for D13. Resolves the ambiguity — matrix targets (8.9, 7.4, 9.8, 8.5) are S+B-only PIRRs. Q4: "No tariff-dependent mechanism as such, PPA revenue varies linearly with tariff... only you may check if revenue lease is creating any impact as its linked to revenue." | SME response 2026-05-12. |
| 2026-05-12 | **A19 added: Step 7 migrated to new engine + P0 frontend bug fixes.** Acted on May 9 bug review (3 highest-risk correctness issues). (1) `wizard_state.set_current_step()` cap raised from 5 to 7 — wizard now navigates all real steps. (2) `Step7_Financial.check_prerequisites()` reads from `st.session_state.sizing_results` (Step 3's actual write location, matching Step 4) instead of the unused canonical `wizard['results']['simulation_results']` — surgical fix, architectural unification deferred to P1. (3) Step 7 imports swapped from parked `financial_model_v0` to `project_irr`; hardcoded `target_load_mw = 25.0` replaced with `wizard['setup']['load_mw']` from Step 1; results display now shows all 3 PIRRs (Combined / Solar+BESS / Gas). New adapter `pirr_inputs_from_wizard_state(fin, setup, monthly_aggregates)` bridges wizard state to engine. | May 9 bug review identified Step 7 as shipping a parked engine with hardcoded inputs — production correctness issue. |
| 2026-05-11 | **A18 added: Anchal answered Q1/Q2/Q3, Q1 ambiguous.** Q1 — implicit, reiterated 3-PIRR structure (8.85% S+B, 9.23% Combined, 10.77% Gas). Whether the 8.9% target maps to Solar+BESS-only or Combined remains ambiguous — explicit follow-up sent. Q2 — confirmed: BESS revenue zero for the Burton Leonard case ("solar+BESS together meeting PPA demand, contributing to PPA revenue"); engine matches. Q3 — Final lease = monthly fixed + July adjustment (= max(0, annual rev − annual fixed)); equivalent to annual-level max(fixed, rev_dep); my monthly max() approximation lands same total when rev_dep > fixed in every month (true for D13). Net new finding: Excel's r148 Revenue Lease sums to £30k = ~10% of S+B revenue not 5% (rev_dep_pct or revenue-base discrepancy to investigate). | SME response 2026-05-11. |

---

## Scope

The PIRR engine replicates the **ungeared** Project IRR calculation from the Excel only. Equity IRR, debt sizing, cash sweep, sensitivity tables, and the IC pack are out of scope. Roughly half the Excel workbook (Debt, Equity, Drawdown, Macro, IC, Analysis, Results, Returns, Capex & Funding-Gas, FS, FS (Annual), CFs 1&2, CHECKS, Log, Chart1, Cover, Notes, Copy) is irrelevant to PIRR and will not be ported.

The minimal Excel footprint that PIRR depends on:

| Excel sheet | Role |
|---|---|
| `Solar&BESS Inputs` (rows 1-364 only) | Revenue, opex, capex, working capital, MRA inputs |
| `Inputs-Gas` (rows 1-54 only) | Gas plant inputs (excl. financing rows) |
| `SETUP` | Period / unit / on-off lookups |
| `Curves and D&T`, `Baringa and Aurora`, `Modo Monthly`, `Wasted Solar` | Indexation cases + price curves + curtailment |
| `Phasing`, `Master Profiles` | Capex phasing |
| `Construction`, `Solar&BESS Operation`, `BESS`, `BESS OPEX`, `Insurance`, `D&T` | Engine sheets |
| `Cash Flows-Gas`, `Consol Cash Flows`, `E_Out` | Output / consolidation |
| `Timing` | Monthly date spine |

VBA macros (`Solve_P1`, `Scenario*Solve`, `SensMasterMacro`, `CashflowsSolve`) are **not ported** — they exist for debt sizing convergence and sensitivity automation, neither of which PIRR needs.

---

## Architectural decisions

### A1. Two sweep modes

The PIRR engine must support both:
- **BESS-only sweep:** solar MWp fixed (from Step 1), BESS MWh / duration / DG MW vary.
- **Full sweep:** solar MWp also varies as a sweep dimension.

Engine takes solar MWp as a per-config input rather than a global constant.

### A2. Energy bridge — ~~re-run hourly dispatch inside financial layer~~ → use Step 3 monthly aggregates + analytical degradation

> **SUPERSEDED 2026-05-07** (was: re-run hourly dispatch inside the financial layer per config to produce monthly aggregates).

For each config in the operational sweep, **Step 3 stashes Year 1 monthly aggregates** (MWh delivered, MWh exported, BESS cycles, gas MWh, gas runtime hours) in `st.session_state.sizing_monthly_aggregates`. The financial layer reads these and projects them across 35 years using analytical degradation:

```text
energy_year_y = year_1_energy × (1 − solar_degradation_pct) ^ (y − 1)
```

No dispatch re-run inside the financial sweep. Mirrors Excel — Excel doesn't re-run dispatch for each year either.

**Why changed:** SME confirmed that Step 3 dispatch is on a "usable energy basis" (already post-oversized) and that degradation belongs to the financial layer, not the operational layer.

### A3. Full revenue stack

The PIRR engine implements all Excel revenue streams:
1. PPA revenue (energy delivered to data centre × tariff × indexation)
2. Solar merchant (energy exported, priced against Baringa / Aurora / Blend curves)
3. REGO (renewable energy guarantees of origin)
4. 11kV embedded benefits (12 monthly £/MWh values, indexed)
5. BESS merchant
6. BESS optimiser floor
7. Capacity Market T-1
8. Capacity Market T-4
9. Gas PPA
10. Gas merchant (post-PPA)

Lite / Standard variants rejected — full stack is required to land on the Excel reference number.

### A4. Capex scaling per config — IDC / Financing Fees / DSRA decision REVERSED

| Driver | Lines | Sweep behaviour |
|---|---|---|
| **Solar DC MWp** | EPC, Acquisition Fee, Development, DD costs, Discharge of Conditions, Other costs, Ampyr Tech, Insurance, Misc, Stamp Duty | Scale linearly with **DC** capacity |
| **BESS** | BESS CAPEX | Engine accepts **either** £/MW (Excel convention) **or** £/MWh; whichever the user populates is used |
| **Land area** | Land-Related Legal, Landowner Fees, Land Lease during Construction, Land Purchase, Community Benefit | Scale linearly with solar DC MWp (acres/MWp ratio held constant from Step 1 baseline ≈ 2.5) |
| **Grid connection** | Grid Costs | Scale linearly with solar DC MWp (acknowledged simplification) |
| **Percentage** | Contingency (1%) | Re-applied after all the above |
| ~~**Excluded from PIRR**~~ → **Included per SME directive** | IDC, Financing Fees, Pre-funded Cash/DSRA | **2026-05-07: Reversed.** SME directive: include all three in line with Excel methodology. The Excel total `Solar&BESS Inputs!E361 = £82,026k` (which feeds `Consol Cash Flows!B9`) includes them — so do we. |

> **Original (now superseded) reasoning for excluding IDC/Financing/DSRA:** they exist only because debt exists; standard project-finance textbook treatment excludes them from PIRR. **SME override:** Ampyr's internal convention aligns PIRR with Excel methodology, including these three. Decision logged 2026-05-07.

### A5. Where capex assumptions live in the UI

All capex assumptions (£/kWp solar items, £/MW or £/MWh BESS, contingency %, etc.) are entered on **Step 1** in a collapsed "Financial Assumptions" expander. Step 3a allows in-place override before running, for quick what-if iteration.

### A6. Where the user sees PIRR — REFINED

> **Refined 2026-05-05.** Original choice was "PIRR column directly in Step 3 results table." **Replaced by:** an optional **Step 3a Financial Sweep** between Sizing and Results. Step 4 Results then shows PIRR columns conditionally (only if Step 3a has been run).

Original options considered:

- **A (chosen first, then refined):** PIRR column in Step 3 results table directly
- **B (chosen now):** Optional Step 3a between Sizing and Results, Step 4 augments conditionally
- **C:** Run inside Step 7 (rejected — Step 7 is single-config deep-dive)

Why option B won over A on reflection: separating operational from financial sweep means changing financial assumptions doesn't re-run the (expensive) operational sweep. Operational stays cached; only financial layer recomputes.

### A7. Performance budget

**8–12 seconds for a typical 100-config sweep is the accepted budget.**

Per-config cost estimate: ~80–120 ms. Composed of:

- ~50–80 ms: build 420-month FCFF (revenue + opex + capex + tax + NWC) with per-line-item indexation + degradation projection
- ~10–20 ms: bisection XIRR
- (Note: dispatch re-run no longer included — see A2 supersession)

Larger sweeps (~500 configs) will hit ~30–50 s. If users hit that ceiling regularly, revisit batch vectorisation.

### A8. Engine accuracy choices — TAX TREATMENT CORRECTED

| Lever | Choice | Why |
|---|---|---|
| Time granularity | **Monthly** (420 periods) | Annual rollup loses seasonality, mid-year COD timing, indexation start dates, payment frequency, and BESS LTSA / augmentation step-ups. Most Excel/Python drift originates here. |
| Indexation | **Per-line-item** with own escalation case | Excel has 14 indexation cases (CPI, RPI, NIL, CfD, PPA Indexation, BESS Indexation, Land Lease CPI / RPI, etc.). Lumping them under one CPI is the most common cause of multi-percent IRR drift. |
| Tax | ~~SLM depreciation, tax = EBIT × rate (no interest tax shield)~~ → **`Tax = max(0, (EBIT − Interest) × tax_rate)` (interest tax shield INCLUDED)** | **2026-05-07 SME correction.** PIRR is debt-aware on the tax line even though FCFF is ungeared in cash terms. Engine therefore needs a minimal debt schedule (gearing, rate, tenor) to derive monthly interest expense for the tax calc only — see A15. |
| Working capital | Debtor / creditor days as on Excel | Small but visible. |
| IRR solver | **Bisection XIRR** matching Excel day-count | Newton-Raphson is faster but can fail to converge; bisection matches Excel to 1e-6. |
| Vectorisation | Skipped for now | Adds engineering complexity; only justified if performance budget breaks. |

### A9. Source-of-truth strategy for `src/financial_model.py`

Existing file is 1,547 lines, uncommitted, and contains two parallel models (`run_financial_model` and `run_tariff_model`) — itself a code smell.

**Audit-first approach:**

**Step A — Reproduce the audit case** (per A12 below): drive the existing engine with the canonical inputs and target **PIRR = 8.9%** (was 9.23% — see A12 for revision). Compare:

- Headline PIRR (target: within 0.1 pp)
- Year-by-year FCFF (target: within 1% per year, no systematic drift)
- Total revenue / opex / capex / tax over 35 years (target: within 0.5%)

**Step B — Triage from the diff.**
- Headline matches AND FCFF lines up → **fix in place**, document gaps.
- Headline matches BUT FCFF wanders year-by-year → **structural fix** (likely indexation timing or tax depreciation), still in place.
- Headline off by >0.1 pp OR sign error somewhere → **rewrite from scratch**. Faster than fishing in 1,547 lines for the bug.

**Step C — Lock with regression tests.** End state is `tests/test_project_irr_excel_parity.py` that fails if PIRR drifts more than 10 bps from the audit target. Without this, the engine rots silently.

### A10. Excel parity test cases — UPDATED

> **Updated 2026-05-07.** SME image supplies a 4-row reference matrix replacing the single-cell target.

| Solar DC | Grid lim | Tariff | BESS | Gas | Expected PIRR |
| --- | --- | --- | --- | --- | --- |
| **82 MWp** | **58.4 MW** | **£170** | **250 MWh** | 25 MW | **8.9%** ← primary audit target (A12) |
| 82 MWp | 58.4 MW | £160 | 250 MWh | 25 MW | 7.4% |
| 115 MWp | 81.9 MW | £170 | 250 MWh | 25 MW | 9.8% |
| 115 MWp | 81.9 MW | £160 | 250 MWh | 25 MW | 8.5% |

Each row becomes a regression-test fixture once the primary target is hit. Per SME (Q4), additional non-base scenarios are deferred until v1 passes the primary audit.

### A11. DC vs AC capacity convention (NEW 2026-05-07)

- **`solar_capacity_dc_mwp`** is a user input. It drives all £/kWp capex and opex line items.
- **The hourly solar profile** is AC + grid-limit-capped output (not DC potential). Profile peak = AC peak. Energy in the profile is what's available for PPA / merchant.
- **Grid limit (MW)** is implicit in the profile (its peak), but exposed as a separate user input for visibility.
- When the user uploads a custom profile, they must also specify the DC MWp it represents (since the profile peak is AC).

Standard solar PV finance convention. Made explicit because the SME flagged it during Q6.

### A12. Audit target REVISED (NEW 2026-05-07)

- **Old target:** `Consol Cash Flows!B9 = 9.23%` (Excel snapshot for "Burton Top-3.8h" — 3.8 hr BESS).
- **New target:** **PIRR = 8.9%** for `82 MWp DC / 58.4 MW grid / £170 PPA / 250 MWh BESS / 25 MW gas / 25 MW load / Burton Leonard 58 MW profile`.
- **Tolerance:** 0.1 pp (8.8–9.0%) — confirmed by SME, no relaxation.
- **Reason for change:** SME's reference matrix (image, 2026-05-07) reflects current Ampyr modelling; the 9.23% Excel cell value reflects an older active case.

### A13. Degradation handling (NEW 2026-05-07)

- **Step 3 dispatch** runs on Year 1, usable-energy basis (BESS already post-oversized at 250 MWh from a 230 MWh nameplate).
- **Financial layer** applies **solar degradation analytically year-by-year**: `energy_year_y = energy_year_1 × (1 − 0.3%)^(y − 1)` for y = 1..35.
- **BESS degradation = 0%** in active case (the 250 MWh oversized figure already accounts for it).
- **No multi-year dispatch re-run** required for the financial sweep (independent of Step 5 MultiYear, which serves a different purpose).

### A14. Reference solar profiles — canonical location (NEW 2026-05-07)

| File | Represents |
| --- | --- |
| [Inputs/Burton_Leonard_82MWp_DC_58MW_AC.csv](../Inputs/Burton_Leonard_82MWp_DC_58MW_AC.csv) | Primary audit profile — matches A12 target |
| [Inputs/Burton_Leonard_115MWp_DC_82MW_AC.csv](../Inputs/Burton_Leonard_115MWp_DC_82MW_AC.csv) | Secondary regression — matches A10 row 3 |

Asset is **Burton Leonard** (real UK site name). "Burton Top" was the Excel case label. Both files moved from `Inputs/Answers/` (originals deleted, folder removed). Test/ folder duplicates flagged for cleanup during audit work — see A9.

### A20. Anchal Q1-follow-up + Q4 answers (NEW 2026-05-12)

Both questions answered.

**Q1 follow-up — Compare against BOTH PIRRs.** Anchal: *"You should compare both: S+B PIRR of 8.9% and combined S+B+Gas PIRR of 9.2%."*

This resolves the interpretation ambiguity from A18:

- May 7 matrix targets (8.9, 7.4, 9.8, 8.5) are **Solar+BESS-only PIRRs**.
- Combined Solar+BESS+Gas PIRR for D13 = **9.2%** (separate number, mentioned only for D13).

Engine state vs both targets:

| Case | S+B Engine | S+B Target | ΔS+B | Combined Engine | Comb Target | ΔComb |
| --- | --- | --- | --- | --- | --- | --- |
| 82/170 D13 | 6.66% | 8.9% | -2.24 | 8.42% | 9.2% | -0.78 |
| 82/160 | 6.06% | 7.4% | -1.34 | 7.91% | — | — |
| 115/170 | 7.71% | 9.8% | -2.09 | 8.38% | — | — |
| 115/160 | 7.09% | 8.5% | -1.41 | 7.85% | — | — |

S+B-only is **uniformly under target by 1.3-2.2 pp**. Combined-D13 is closer but my engine's gas IRR (~25%) is 2× Excel's (10.77%), so gas over-contributes to lift Combined. Calibrating gas down to match Excel would drop Combined too (current 8.42% → ~7%), confirming the residual is in the S+B side, not gas.

**Q4 — No tariff-dependent mechanism, but check rev_dep_lease.** Anchal: *"No tariff dependent mechanism as such, PPA revenue varies linearly with tariff... only you may check if revenue lease is creating any impact as its linked to revenue."*

Implication: the PPA-tariff sensitivity gap (engine 0.6 pp vs target ~1.5 pp per £10 tariff cut) isn't explained by a hidden tariff-dependent formula. Anchal's hint is that rev_dep_lease may not be modelled correctly. We applied a 2x base fix per A18 (replicating Excel Op r98 doubling), but the impact on tariff sensitivity is small (<0.05 pp). The bulk of the sensitivity gap remains unexplained.

**Open hypothesis:** my engine may be over-stating tax offsets or under-stating PPA revenue magnitude in some way that flattens the sensitivity response. Worth investigating: (a) revert the 2x rev_lease fix and re-test sensitivity (per Anchal's hint that Excel applies 5%, not 10%), (b) check whether the S+B-only deltas would close if revenue side has missing items.

### A18. Anchal Q1/Q2/Q3 answers + Q1 follow-up (NEW 2026-05-11)

Anchal answered the v2 questions same day. Q2 and Q3 fully clarified; Q1 implicit, follow-up sent.

**Q1 — implicit answer; follow-up pending.** Anchal reiterated the 3-PIRR structure: Solar+BESS PIRR = 8.85% (`Equity!D175`), Combined Solar+BESS+Gas PIRR = 9.23% (`Consol Cash Flows!B9`), Gas PIRR = 10.77% (`Cash Flows-Gas!D84`). The May 7 matrix target of 8.9% sits suspiciously close to the current Solar+BESS PIRR (8.85%), but a 3.8h → 4h BESS upgrade could plausibly shift either PIRR by ~30 bps. Without explicit confirmation, the right comparison target is ambiguous:

| Case | Engine Combined | Engine S+B-only | Target | Δ Combined | Δ S+B-only |
| --- | --- | --- | --- | --- | --- |
| 82/170 (D13) | 10.28% | 7.49% | 8.9% | +1.38 | -1.41 |
| 82/160 | 9.73% | 6.85% | 7.4% | +2.33 | -0.55 |
| 115/170 | 9.97% | 8.58% | 9.8% | +0.17 | -1.22 |
| 115/160 | 9.41% | 7.92% | 8.5% | +0.91 | -0.58 |

Follow-up sent: "should I compare against S+B-only PIRR or Combined?" Engine paused pending answer.

**Q2 — answered: BESS revenue zero is correct.** Direct quote: "BESS revenue separately is zero for this exercise purpose as solar+BESS are together meeting the PPA demand and contributing to PPA revenue, therefore you may ignore the separate CM/floor, etc revenue for BESS separately." Spec §5.2 should be updated to note BESS floor + CM T-1 + CM T-4 are off for the Burton Leonard case (BESS earns its return through PPA contribution, not separate streams). Engine already matches; no code change needed.

**Q3 — answered: lease mechanism explained.** Direct quote: "Final lease that is part of opex = Fixed lease (row 147) + Lease Adjustment (row 155). Row 155 (Lease Adjustment) = max(annual revenue lease row 154 − annual fixed lease row 153). Row 153 and Row 154 are just annualised (sum of last 12 months Aug to July) of row 147 and 148 respectively as these expenses are payable in July only for last 12 months."

Mechanism: each month pay `fixed_lease` (r147); each July pay top-up = `max(0, annual_rev_lease − annual_fixed_lease)`. Net annual ≈ `max(annual_fixed, annual_rev)`. My engine's monthly `max(fixed, rev_dep)` gives same lifetime total when rev_dep > fixed in every month (holds for D13 — rev_dep £15k > fixed £8k always). Approximation acceptable for v1.

**Open from Q3 — investigated 2026-05-11:** Excel r148 (Revenue Lease) lifetime sum = £30,143. At 5% rev-share, that implies revenue base of £602,857. Dumped `Solar&BESS Operation` rows 94–98:

| Row | Op (rev base) | FS (true revenue) | Ratio |
| --- | --- | --- | --- |
| r94 PPA | 254,324 | 127,162 | 2.000 |
| r95 Solar merchant | 310,213 | 155,107 | 2.000 |
| r96 REGO | 13,173 | 6,587 | 2.000 |
| r97 11kV embedded | 25,146 | 12,573 | 2.000 |
| **r98 Total** | **602,857** | **301,428** | **2.000** |

Every revenue line in Solar&BESS Operation is exactly 2× the corresponding FS row. Likely Excel sums a "base" and an "applied" version of each stream into r98. The 5% rev_dep_lease rate × 2x base = effective 10% × actual revenue.

**Engine fix applied:** rev_dep_lease = `0.05 × 2 × revenue` (matches Excel mechanism, not a fudge per Guardrail #5). Magnitude: opex up by ~£15k lifetime; Combined PIRR drops ~1.4 pp for D13 (10.28% → 8.42%). New matrix delta range: -1.42 to +0.51 pp (was +0.17 to +2.33 pp). Combined-interpretation hypothesis now strongly favoured — deltas now bracket target on both sides; S+B-only deltas all under by 1.3-2.2 pp.

### A17. Rewrite scaffold + structural fixes (NEW 2026-05-11)

Following A16 (rewrite confirmed), built a clean engine at [src/project_irr.py](../src/project_irr.py). Architecture matches spec §4.1: unified Solar+BESS+Gas FCFF with no consolidation step, no ownership multipliers, all revenue/opex/capex traceable to specific Excel cells.

**D13 PIRR trajectory (each iteration anchored to a specific Excel dump):**

| Iteration | PIRR | Gap to 8.9% | Source of fix |
| --- | --- | --- | --- |
| Initial (full revenue stack, naive gas) | 19.61% | +10.71 pp | — |
| + gas timing fix (PPA→merchant at yr 10, EOL yr 20) | 13.53% | +4.63 pp | Cash Flows-Gas r21 formula |
| + gas opex (gross MW, major maint, reactive) | 12.25% | +3.35 pp | Cash Flows-Gas r41-r59 lifetime sums |
| + BESS tenor 10 yr + corrective maint step + BESS step costs + lease max + BESS rev zero | **10.27%** | **+1.37 pp** | FS r30-56, BESS r113-115, Op r147-157, FS r20-24 |

**Remaining gap composition** (solar+BESS-only is at 7.56% vs Excel's `Equity!D175 = 8.85%`, so under by 1.29 pp):

- Solar merchant ~£14k under Excel (curve fidelity — pre-2034 fallback)
- Solar+BESS opex ~£9k over Excel (small residuals in variable CfD inflation, BESS rate basis)
- Gas opex ~£35k under Excel (fuel curve / step pattern)

**Step-function approximations introduced (flagged in code, sized to match Excel lifetime totals):**

| Item | Excel pattern | Engine approximation | Excel total | Engine total |
| --- | --- | --- | --- | --- |
| Gas Major Maintenance | 8-event step (CF-Gas r44) | level annual × CPI compounding | £16,650k | £16,646k |
| Solar Corrective Maint | 8-event step (FS r39) | level annual × CPI compounding | £525k | £525k |
| BESS LTSA / PCS / Augmentation | Step pattern (BESS r113-115) | level annual × BESS Indexation | £7,089k | £7,089k |

Within-life *timing* differs; lifetime *magnitude* matches. Effect on IRR estimated ≤10 bps; can be tightened later by importing the year-by-year schedule from Excel if needed.

**Excel sheets dumped (ground truth extracted):**

- `Consol Cash Flows` rows 1-25 (Project IRR formula chain)
- `Equity` rows 100-180 (Solar+BESS FCFF chain + XIRR)
- `FS` rows 1-95 (revenue + opex + capex line items)
- `Solar&BESS Operation` rows 88-175 (revenue + opex + lease mechanism)
- `BESS` rows 88-135 (BESS opex breakdown)
- `Cash Flows-Gas` rows 1-90 (gas FCFF chain, opex breakdown, capex)

No more workbook inspection available — three open questions are now genuinely SME-only and queued in v2 questions doc. Engine paused pending answers.

### A16. Audit outcome — rewrite confirmed (NEW 2026-05-07)

A9 Step A executed. The existing engine (`src/financial_model_v0.py` + `src/consolidated_model_v0.py`) was driven against the SME 4-row matrix via `tests/test_project_irr.py`:

| Row | Expected | Computed | Δ (pp) |
| --- | --- | --- | --- |
| 82 MWp DC (capex base) / £170 | 9.8% | 10.24% | +0.44 |
| 82 MWp DC (capex base) / £160 | 8.5% | 8.87% | +0.37 |
| **D13: 58.4 MW grid / £170 (audit target)** | **8.9%** | **8.46%** | **−0.44** |
| 58.4 MW grid / £160 | 7.4% | 7.20% | −0.20 |

Per A9 Step B the >0.1 pp headline divergence → **rewrite**. Reinforced by:

- **Guardrail-5 violation present.** `tests/test_project_irr.py:120` overrides `gas_ownership_share=0.58` ("Calibrated: Consol Cash Flows uses ~58% of Gas FCFF"). Excel has no 58% multiplier — this was inserted to fudge the headline. Removing it (mandatory under Guardrail 5) shifts the answer the wrong way (S+B IRR 6.44% + Gas IRR 21.47%, unfudged combination ~13%+, far above 8.9%) — confirming structural error in the energy/revenue split.
- **Spec-completeness gaps** also visible in `_v0`: single-rate CPI escalation (vs §D11 — 14 indexation cases); SLM depreciation in one account (vs Excel D&T 3 accounts); incomplete BESS revenue stack in tariff path (no embedded benefits/CM/REGO/floor — vs §5.2); no minimal debt schedule for tax shield (vs A15/D2). These would compound into multi-pp drift even if the gas split were corrected.

**Parking decision:** `financial_model.py` and `consolidated_model.py` renamed to `_v0` suffix, imports updated in all 7 consumer sites, test suite verified to reproduce 8.46% post-rename. Files retained for audit reproducibility; not used for new work. Rewrite proceeds at a fresh module path (TBD — see "Next concrete step").

### A15. Minimal debt schedule for tax-shield only (NEW 2026-05-07)

Required by A8's tax correction. Engine takes these inputs but does NOT produce a debt cash flow:

| Input | Default | Excel cell | Used for |
| --- | --- | --- | --- |
| Gearing ratio | 80% | `Solar&BESS Inputs!F415` | Initial debt principal = gearing × total capex |
| Weighted avg interest rate | ~5.5% | derived from `F445/F453/F500/F508` | Per-period interest expense |
| Debt tenor | 19.5 yr (fixed) / 22 yr (sculpted) | `F431` / `F486` | Amortisation profile |
| Repayment method | Fixed / Sculpted | `F451` / `F506` | Annuity vs equal-principal |
| Grace period | 36 mo | `F432` | Interest-only period start |

Implementation: straight-line amortisation (no DSCR sculpting, no cash sweep), apply weighted interest rate, derive monthly interest expense series. That series feeds the tax calc only (A8). Principal and interest cash flows do **not** appear in FCFF.

---

## Out of scope (explicitly)

- Equity IRR (levered) — even though the Excel calculates it
- Full debt sizing, cash sweep, DSCR sculpting — and the VBA solver that converges them. (Minimal debt schedule for tax-shield is in scope per A15.)
- Sensitivity tables (PPA / EPC / Grid / Yield / Interest)
- Multi-asset / portfolio rollup (Burton Top vs Costock vs Northwold vs portfolio in `Results` sheet)
- IC investment-committee pack
- @Risk / Monte Carlo / StatTools
- Capital IQ data calls
- Excel chart sheets

---

## Open items (parked, not blocking)

- **`Test/` folder duplicates of reference profiles** ([tests/test_project_irr.py:39-40](../tests/test_project_irr.py#L39-L40) references `Test/...82MW.CSV` and `Test/...58MW.CSV`). To be repointed to `Inputs/Burton_Leonard_*` during the audit. Decision deferred per user direction 2026-05-07.

---

## Next concrete step

Audit complete (A16). Rewrite confirmed. Next: scaffold a fresh PIRR engine targeting D13 only (single config, single output number) before extending to the secondary three rows. Key open scope choices to confirm with user before writing code:

1. **New module path** — proposed `src/project_irr.py` (clean name, distinguishes intent from the conflated "financial_model" of the parked engine).
2. **D13-first revenue stack** — minimum lines that get us to 8.9%: PPA, solar merchant, REGO, embedded benefits, CM T-1/T-4, BESS floor, gas PPA, gas merchant. (BESS merchant is parked at zero in the v0 tariff path — confirm whether D13 needs it.)
3. **Input mechanism** — read directly from the Excel `Solar&BESS Inputs` columns via `src/excel_reader.py` (existing infrastructure), or hardcode the D13 fixture in a `tests/fixtures/d13_inputs.py`. Excel-read couples to the workbook; fixture isolates the engine.
4. **Single-row regression test** — `tests/test_project_irr_excel_parity.py::test_d13` as the only locked test for v1; the other three SME rows added once D13 is in tolerance.

Companion docs to consult during the rewrite:

- [Financial_Assumptions_Spec.md](Financial_Assumptions_Spec.md) — the build-ready spec (current locked state)
- [src/financial_config.py](../src/financial_config.py) — Excel cell mappings (`INPUT_CELLS`, `FCFF_ROWS`, `REFERENCE_CASE`)
- [src/financial_model_v0.py](../src/financial_model_v0.py), [src/consolidated_model_v0.py](../src/consolidated_model_v0.py) — parked reference (do not extend)
