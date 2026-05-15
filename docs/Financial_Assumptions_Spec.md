# Financial Sweep — Specification

**Status:** Pre-implementation. Spec to drive Step 3a Financial Sweep build.
**Supersedes:** [Project_IRR_Integration_Decisions.md](Project_IRR_Integration_Decisions.md) — that earlier log captured decisions made *before* SME review; several were corrected. This document is now the source of truth.
**Reference Excel:** `Financial Model/Off-Grid Solution v8.xlsm` (the v8 workbook). Excel cell references throughout point at this file unless stated.

---

## 1. Purpose

Add a Project IRR (PIRR) ranking dimension to the operational sizing sweep, so the user can finalise a configuration on financial return alongside operational metrics (delivery %, green %, wastage %, etc.).

## 2. Scope

In scope:

- **Ungeared Project IRR** (XIRR on FCFF) replicating Excel `Consol Cash Flows!B9` for the Burton Leonard base case
- **Debt-aware tax line** — interest tax shield is captured via `(EBIT − Interest) × tax_rate` (Ampyr internal convention; see §4.1)
- All ~10 Excel revenue streams (PPA, solar merchant, REGO, 11kV embedded benefits, BESS merchant, BESS floor, Capacity Market T-1/T-4, gas PPA, gas merchant)
- Per-line-item indexation matching Excel's 14 indexation cases
- 420 monthly periods (35-year project life × 12)
- Multi-config sweep producing PIRR per configuration

Out of scope (explicitly):

- Equity IRR / Levered IRR
- Debt sizing convergence, cash sweep, DSCR sculpting (the Excel's `Solve_P1` macro)
- DSRA mechanics beyond the pre-funded amount
- Sensitivity tables (PPA / EPC / Grid / Yield / Interest sensitivity matrices on `IC` sheet)
- Multi-asset / portfolio rollup
- @Risk / Monte Carlo / StatTools
- All VBA macros

---

## 3. Locked decisions

| # | Decision | Source |
| --- | --- | --- |
| D1 | PIRR = ungeared FCFF IRR matching `Consol Cash Flows!B9`. Same definition Ampyr uses internally. | SME Q1 |
| D2 | Tax computed as `(EBIT − Interest) × tax_rate` — interest tax shield IS included even though FCFF is ungeared in cash terms. Engine therefore needs minimal debt inputs (gearing, rate, tenor) for the tax calc. | SME Q1 correction |
| D3 | Capex includes IDC, Financing Fees, and pre-funded DSRA (all in the Excel total `Solar&BESS Inputs!E361 = £82,026k`) — align with Excel methodology, not textbook. | SME Q2 |
| D4 | Solar capex (£/kWp items) scales linearly with **DC capacity (MWp)**. | Excel + SME Q1-followup |
| D5 | BESS capex accepts either **£/MW** (Excel: 600 = `Solar&BESS Inputs!F349`) or **£/kWh** (= £150 implied on the 4 hr active case). Engine uses whichever is populated. | Excel convention |
| D6 | Land area scales linearly with solar MWp at the Burton Leonard ratio (205 acres / 82 MWp ≈ 2.5 acres/MWp). | Earlier conversation |
| D7 | Grid costs scale linearly with solar MWp (acknowledged simplification — real grid connections step-function up by transformer band). | Earlier conversation |
| D8 | **DC vs AC capacity convention:** capex scales on **DC MWp**; revenue uses the **AC + grid-limit-capped hourly profile** as supplied. The user inputs DC MWp directly; AC peak is implicit in the loaded profile. | SME Q6 |
| D9 | **Degradation handling:** Step 3 dispatch produces **Year 1 monthly aggregates on a usable-energy basis** (BESS is already post-oversized at 250 MWh from a 230 MWh nameplate). The financial layer applies solar degradation analytically year-by-year (`× (1 − 0.3%)^(year − 1)`). No dispatch re-run inside the financial sweep. | SME Q2-followup |
| D10 | **Time granularity:** 420 monthly periods (35 yr × 12 mo). Annual rejected. | Earlier — keeps Excel parity |
| D11 | **Indexation:** per-line-item with own escalation case + start date, mirroring Excel's 14 indexation cases (`Curves and D&T`). | Earlier |
| D12 | **IRR solver:** XIRR via bisection (Excel-compatible day count). | Earlier |
| D13 | **Audit target:** **Combined PV+BESS+Gas PIRR = 9.2%** for `82 MWp DC / 58.4 MW grid / £170 PPA / 250 MWh BESS / 25 MW gas / 25 MW load / Burton Leonard 58 MW profile`. Tolerance: **0.1 pp** (9.1–9.3%). Year-by-year FCFF within 1%; 35-year totals within 0.5%. **Per Anchal 2026-05-14 reply**: the matrix column is explicitly "Project IRR (Overall for PV+BESS+Gas)" — Combined, not S+B-only. Supersedes the A20 misinterpretation. See decisions log A29. | SME 2026-05-14 |
| D14 | **Audit reference is the SME's 2026-05-14 matrix**, not Excel `Consol Cash Flows!B9 = 9.23%` (older Burton Top-3.8h snapshot). New 82 MWp values are slightly different from the May 7 image ("minor change in 82MW configuration" — 8.9→9.2 Combined for £170, 7.4→7.8 for £160). 115 MWp values unchanged (9.8 / 8.5). All four matrix rows are Combined PIRR. Per-config green/gas share also given as dispatch cross-check (82 MWp: 34.5/65.5; 115 MWp: 42.8/57.2). | SME 2026-05-14 |
| D15 | **Wizard layout:** new optional **Step 3a Financial Sweep** between Step 3 Sizing and Step 4 Results. Existing Step 7 stays as single-config financial deep-dive. | User decision |
| D16 | **Performance budget:** 8–12 s for a 100-config financial sweep (operational sweep stays cached). | Earlier |
| D17 | **`#REF!` errors in the Excel** (broken named ranges `BESS_Hrs`, `BESS_MW`, `gearing_actual`, `Energy_copy`, `EBITDA_Val`, `PV_Val`, `Hours_output`, `No_projects`, `ProjectID`, plus `IC!C150:C158` opex rows) are confirmed by SME to be **outside the PIRR calc chain** — ignore. Flag any new `#REF!` discovered to be inside the chain. | SME Q3 |
| D18 | **Validation cases:** Burton Leonard base case only for v1. Multi-case validation deferred to a later iteration. | SME Q4 |
| D19 | **Existing `src/financial_model.py` (1,547 lines):** ~~treat as earlier attempt; audit-first.~~ **2026-05-07: Audit run, rewrite confirmed.** Engine produced 8.46% vs 8.9% (−44 bps; all 4 SME rows breach 0.1 pp tolerance) plus a `gas_ownership_share=0.58` calibration constant violating Guardrail #5. Parked as `src/financial_model_v0.py` and `src/consolidated_model_v0.py`; imports updated in 7 consumer sites. See decisions log A16. | Earlier + SME Q3 + A16 audit |
| D20 | **Reference solar profiles** (canonical):<br>• `Inputs/Burton_Leonard_82MWp_DC_58MW_AC.csv` — primary audit profile (matches D13)<br>• `Inputs/Burton_Leonard_115MWp_DC_82MW_AC.csv` — secondary regression (SME image row 1) | SME-supplied |
| D21 | **Tax depreciation = Reducing Balance with SLM crossover.** Excel `D&T!E165` Applied = "RB"; rate = `D&T!E164 = 2/36` (5.556% p.a., double-declining over a 36-year nominal life). Crossover to SLM-on-remaining when SLM ≥ RB amount, ensuring lifetime depreciation = total capex (smooth taper, no end-of-life spike). | Excel D&T r163-165 |
| D22 | **Shareholder Loan (SHL) tax shield in scope.** SHL principal = `shl_pct_of_unfunded` × (1 − senior_gearing) × total_capex (Excel `Solar&BESS Inputs!F556 = 0.99`). Annual interest at `shl_rate = 15%` p.a. (`F553`). Deductible interest subject to UK CIR cap = max(£2m, 30% × EBITDA) on **total** interest (senior + SHL), senior prioritised, SHL fills remaining headroom. Mirrors Excel `D&T!r197/r210-r212`. | Excel D&T + Solar&BESS Inputs F553/F556 |
| D23 | **Solar balancing services split** (A32): CfD rate £2.75/MWh flat (NIL indexation per Excel `Inputs!F287` active branch) during PPA tenor only; merchant rate (time-varying £1.35→£2.67/MWh £/MWh curve derived from `Op r142 / Op r52`) post-PPA. Excel sources `Solar&BESS Inputs!F282` (CfD rate, scalar) and `Baringa and Aurora!F1:...` (merchant rate, lookup curve referenced from F283 cell-note). Engine field `merchant_balancing_rate_by_ops_year: dict`. | Excel Op r141/r142 + Inputs F282/F283/F287 |
| D24 | **Land lease formula is annual, not monthly** (A33): `total_lease = Σ fixed_m + max(0, annual_rev_lease - annual_fixed_lease)`. Pre-A33 engine took `Σ max(fixed_m, rev_m)` — wrong when seasonal revenue dips below fixed in some months. | Anchal Q3 (A18) + 2026-05-15 implementation |
| D25 | **PV O&M escalation = "O&M - Year 3 Onwards" not CPI** (A34): flat for ops_years 0-2, then 2%/yr from year 3 onwards. Excel `Solar&BESS Inputs!r267`. Engine has its own field `opex_pv_om_indexation` (separate from the bundled `opex_solar_fixed_indexation = "CPI"` for the other 8 solar fixed lines). | Excel `Inputs!r267` + Op r117 year-by-year verification |
| D26 | **Capex per-month phasing infrastructure available, default OFF** (A35): engine `_calc_capex` supports `capex_phasing_sb` / `capex_phasing_gas` dicts keyed by `(year, month)`. Burton-Leonard curves stored as `_DEFAULT_CAPEX_PHASING_*_BY_MONTH`. Defaults empty — phasing-only fix regresses audit by 11 bps because Excel pairs it with (i) depreciation starting at capex-addition month per `D&T!r68`, (ii) UK NOL carry-forward of pre-COD losses. Activate when paired mechanisms land. | A35 diagnostic + gap analysis §3.12/§3.13 |
| D27 | **Gas major maintenance is a discrete-event schedule, not level annual** (A36): Excel `Cash Flows-Gas!r44` has 8 events concentrated in ops_years 1, 3, 4, 6, 7, 9, 12, 15 totaling £16,650k nominal. Year 15 alone is £7,928k (47% of lifetime). Engine field `gas_major_maint_schedule: dict` defaults to `_DEFAULT_GAS_MAJOR_MAINT_SCHEDULE`. Values applied without additional escalation (already nominal). Empty dict falls back to legacy `gas_opex_major_maint_annual = 685.0` × gas inflation. | Excel `Cash Flows-Gas!r44` extracted 2026-05-15 |
| D28 | **Tax depreciation uses 3 parallel accounts** (A38 Phase A): per Excel `D&T!r51-r178`. Account 1 "Long term" (360 mo / 30 yr, monthly RB rate 2/360 = 0.5556%/mo) takes physical assets — solar EPC, BESS, grid, land, insurance + all gas capex. Account 3 "Financing" (36 mo / 3 yr, monthly RB rate 2/36 = 5.56%/mo) takes IDC + Financing Fees only. Account 2 "Short term" (96 mo / 8 yr) carries no D13 routing. DSRA is cash-only (returns at EOL, not depreciated). Engine constant `_DEPRECIATION_ACCOUNTS`. Capex line item → account mapping per Excel `Construction!B76:B112` SUMIF against `Curves and D&T!r71-r112` per-line "Choice" tags. | Excel `Construction!B76:B112` + `D&T!r51-r178` extracted 2026-05-16 |
| D30 | **CPI escalation uses time-varying curve, not flat rate** (A40): Excel `Curves and D&T!r10` is "Variable" with per-calendar-year rates (2025=3.1%, 2026=2.5%, 2027=2.2%, 2028=2.2%, 2029=2.1%, 2030+=2.0% steady-state). Engine constant `_DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR` mirrors the Burton-Leonard active branch; `_build_cpi_factor_lookup` precomputes per-ops-year cumulative factor; `_esc_factor` consumes the lookup for "CPI" case. Convention: `factor(ops_year=0) = 1.0` (no pre-COD anchor inflation in engine — the Excel-input base values are assumed to already be in COD-year prices). Years not in the curve fall back to `rates["CPI"]` (engine flat 2.0% from A39). PirrInputs field `cpi_curve_by_calendar_year: dict` (defaulted). | A40 (2026-05-16): Excel `Curves and D&T!r10` extracted. A39's flat 2.0% missed the early-year detail; A40 adds the full curve but IRR delta is sub-bp because early years' deviation is small (0.1-0.2 pp from steady-state). |
| D29 | **Depreciation begins at capex-addition month, not COD** (A38 Phase C): per Excel `D&T!r62` "Entering depreciation base" — additions in any month start their own depreciation chain in that month. Engine `_calc_depreciation(inp, additions_by_account, dates)` runs one chain per non-zero addition. Combined with the (pre-existing) NOL pool in `_calc_tax`, this lets construction-period depreciation generate tax losses that absorb against early ops-year income. Pre-A38 the engine started a single chain at COD; the NOL pool had nothing to absorb pre-ops. A38 also flips `capex_phasing_sb/gas` defaults from empty `{}` to the Burton-Leonard curves (`_DEFAULT_CAPEX_PHASING_*_BY_MONTH`), which previously caused -11 bps regression in isolation but combined with multi-account dep + dep-from-construction now yields +0.07 pp Combined uplift. | Excel `D&T!r62` + `Construction!r5/r6` capex phasing |

---

## 4. Engine architecture

### 4.1 The PIRR formula

For each configuration `c` in the operational sweep:

```
For each month t in 1..420:
    Revenue_c[t] = sum over revenue streams (see §5)
    Opex_c[t]    = sum over opex line items (see §5)
    Capex_c[t]   = phasing-driven capex draw (see §5)
    
    EBITDA_c[t]  = Revenue_c[t] - Opex_c[t]
    Depreciation_c[t] = SLM-based on construction-period capex (see Excel D&T)
    EBIT_c[t]    = EBITDA_c[t] - Depreciation_c[t]
    Interest_c[t] = derived from minimal debt schedule (see §4.2)
    Tax_c[t]     = max(0, (EBIT_c[t] - Interest_c[t]) * tax_rate)
    
    NWC_change_c[t] = (debtor_days × revenue rate) - (creditor_days × opex rate), differenced
    
    FCFF_c[t]    = EBITDA_c[t] - Tax_c[t] - Capex_c[t] - NWC_change_c[t]

PIRR_c = XIRR(dates[1..420], FCFF_c[1..420])
```

**Note D2:** The interest line is a tax-shield input only; it does **not** appear in FCFF as a cash flow.

### 4.2 Minimal debt schedule (for tax shield only)

The engine takes these inputs but does not produce a debt cash flow:

| Input | Excel default | Excel cell | Used for |
| --- | --- | --- | --- |
| Gearing ratio | 80% | `Solar&BESS Inputs!F415` | Initial debt principal = gearing × total capex |
| Weighted avg interest rate | ~5.5% | derived from `F445/F453/F500/F508` | Per-period interest expense |
| Debt tenor | 19.5 yr (fixed) / 22 yr (sculpted) | `F431` / `F486` | Amortisation profile |
| Repayment method | Fixed / Sculpted | `F451` / `F506` | Annuity vs equal-principal interest decline |
| Grace period | 36 mo | `F432` | Interest-only period start |

Implementation: compute a single straight-line amortisation schedule (no DSCR sculpting, no cash sweep), apply weighted interest rate, derive monthly interest expense series. That series feeds the tax calc only.

### 4.3 Engine-level inputs from the operational sweep

For each configuration `c`, the financial layer receives:

| From operational sweep (per config) | Used as |
| --- | --- |
| `monthly_mwh_delivered[12]` | PPA revenue base |
| `monthly_mwh_exported[12]` | Solar merchant revenue base |
| `monthly_bess_cycles[12]` | BESS LTSA / augmentation triggers |
| `monthly_gas_mwh_delivered[12]` | Gas PPA revenue base |
| `monthly_gas_runtime_hrs[12]` | Gas variable opex (fuel) base |
| `bess_capacity_mwh` | BESS capex |
| `bess_power_mw` | BESS capex (alt unit) |
| `dg_capacity_mw` | Gas / DG capex |
| `solar_dc_mwp` | All solar £/kWp capex + opex items |

These are the **Year 1** values. Degradation, indexation, and 35-year projection are applied by the financial layer.

---

## 5. User-editable assumptions catalog (~80 entries)

All values pre-filled from Excel; user can override via the Step 1 Financial Assumptions panel. Each entry has the structure: `name | unit | Excel default | Excel source cell | valid range | description`.

The full enumeration lives in [src/financial_config.py](../src/financial_config.py) under `INPUT_CELLS` — that mapping already encodes Excel cell references for ~70 of these inputs and will be extended to cover the rest.

### 5.1 Capex (~22 lines)

**Solar (£/kWp DC):** EPC, Acquisition Fee, Development, DD costs, Discharge of Conditions, Other Cost, Ampyr Tech, Insurance, Misc, Stamp Duty, Asset Adoption, Community Benefit, Other Legal, Success Fee.

**BESS:** £/MW (default 600) or £/kWh (default 150) — engine uses whichever is populated.

**Land (linear with solar MWp):** Land Purchase, Landowner Fees, Land-Related Legal, Land Lease during Construction.

**Grid (linear with solar MWp):** Grid Costs (default 57.86 £/kWp).

**Financing-related (included per D3):** IDC, Financing Fees (Arrangement + Commitment + Structuring), Pre-funded Cash / DSRA.

**Percentage:** Contingency (default 1%).

### 5.2 Revenue (~25 lines)

**Solar PPA:** tariff (£170/MWh), tenor (10 yr), indexation case (NIL), price flex %.

**REGO:** switch (on), price (£2.5/MWh), tenor (35 yr), indexation, tenor start date.

**11kV embedded benefits:** switch, 12 monthly £/MWh values (£5–£11/MWh), tenor (15 yr), indexation (CPI).

**Solar merchant:** curve case (Baringa / Aurora / Blend), price flex %, generation case (P50/P75/P90).

**BESS merchant:** switch, scenario, curve discount (5%), offtake %, indexation.

**BESS optimiser floor:** switch, floor price (£40/MWh), underwriter rev share (9%), tenor (10 yr).

**Capacity Market T-1:** £20k/MW/yr, 27.15% derating, 3-yr tenor, indexation (CPI).

**Capacity Market T-4:** £60k/MW/yr, 20.94% derating, 15-yr tenor, indexation (CPI).

**Gas PPA:** £170/MWh, tenor 10 yr, escalation %.

**Gas merchant:** £200/MWh, operational hours/day (9), escalation from year 4 %.

### 5.3 Opex (~20 lines)

**Solar fixed (£/kWp/yr):** PV Plant O&M (5.48), Grid Connection (0.0032), Greenkeeping (1.5), Community Benefit (0.5), Real Estate Taxes (1.22), Non-Technical AM (1.3), Insurance on P&M (2.02), Corrective Maintenance (3.2), Technical AM (0.3), Landowner Subsidy Loss (0).

**Solar variable (£/MWh):** Social/Local Participation (0), Balancing Services for CfD (2.75), Balancing Services for Merchant (calculated).

**BESS (£k/MW/yr):** BESS O&M (7.06), Import Charges (0), Business Rates (3.28), BESS Lease (1.49).

**BESS step-functions (from `BESS OPEX` sheet):** LTSA, PCS Extended Warranty, Augmentation — keyed by BESS scenario + cycles.

**Land:** Fixed lease (£700/acre/yr), Revenue share Y1-10 (5%), Revenue share Y11-35 (5%).

**Gas (from `Inputs-Gas`):** fuel + CCL (£/MWh), CPS environmental levy (£k/MW/yr), contract O&M (£k/MW/yr), other variable, fixed gas cost (£/day), start fuel + cycles, UKETS price + CO2 emissions, opex inflation %, audit fees, insurance, legal.

### 5.4 Tax & financial (~12 lines)

| Input | Default | Excel cell |
| --- | --- | --- |
| Corporate tax rate | 25% | `Inputs-Gas!F69` (or override) |
| Project life | 35 yr | `Solar&BESS Inputs!F24` |
| Solar degradation | 0.3% / yr from Y2 | `Solar&BESS Inputs!F40` |
| BESS degradation | 0% (post-oversized basis) | `Solar&BESS Inputs!F120` |
| Debtor days | 30 | `Solar&BESS Inputs!F327` |
| Creditor days | 30 | `Solar&BESS Inputs!F328` |
| Tax depreciation life (SLM) | per Excel | `Inputs-Gas!F66:F67` |
| Working-capital switch | on | — |
| **For tax-shield (D2):** gearing | 80% | `Solar&BESS Inputs!F415` |
| weighted interest rate | ~5.5% | derived |
| debt tenor | 19.5 / 22 yr | `F431` / `F486` |
| grace period | 36 mo | `F432` |
| **SHL (D22)**: % of unfunded | 99% | `Solar&BESS Inputs!F556` |
| SHL rate | 15% p.a. | `Solar&BESS Inputs!F553` |
| CIR de minimis threshold | £2m | `D&T!D210` |
| CIR EBITDA cap | 30% | `D&T!E210` |
| **Depreciation method (D21)** | Reducing Balance | `D&T!E165` |
| Depreciation rate | 5.556% p.a. (2/36) | `D&T!E164` |

### 5.5 Indexation rates (~5 lines)

CPI rate, RPI rate, BESS Indexation rate, PPA Indexation rate, Land Lease RPI rate. Defaults from `Curves and D&T`.

### 5.6 Land/site (~3 lines)

Acres/MWp ratio (2.5), total acres override (optional), days/year (365).

---

## 6. Engine logic that does **not** become user input

These stay hard-coded in the Python engine because they're function shapes, not values:

- Capex scaling rule (linear with DC MWp / BESS MW or MWh / land area derived from MWp)
- Tax depreciation method (SLM vs reducing balance — SLM mirrored from Excel)
- Indexation timing (which line item uses which case — mapped from Excel, not user-set)
- BESS step-function timings (LTSA / PCS warranty / augmentation triggers from `BESS OPEX`)
- Interest schedule shape (straight-line amortisation — no DSCR sculpting in our engine)
- Day-count convention for XIRR (actual/365)
- Whether BESS earns merchant revenue during the PPA period (engine logic determined by BESS dispatch and PPA mode)

---

## 7. Wizard flow

```
Step 1 Setup
    Asset basics + Financial Assumptions panel (collapsed expander, ~80 inputs)
        ↓
Step 2 Rules
    Dispatch strategy
        ↓
Step 3 Sizing
    Operational sweep (8760-h dispatch per config)
    NEW: stash monthly aggregates per config in session state
        ↓
   ┌───────────────────────────────────────────────┐
   │  Choice point (UI: two buttons at end of S3):  │
   │   "View Results"     →  Step 4                 │
   │   "Add Financial Analysis" → Step 3a (NEW)     │
   └───────────────────────────────────────────────┘
        ↓                                  ↓
Step 4 Results                       Step 3a Financial Sweep (NEW)
                                       Reads cached monthly aggregates
                                       Reads financial assumptions
                                       Runs PIRR per config (XIRR)
                                       Stores financial_results
                                          ↓
                                     Step 4 Results
                                       (now augmented with PIRR/NPV/MOIC columns)
        ↓
Step 5 MultiYear   (unchanged, operational extension)
        ↓
Step 6 Green Energy   (unchanged)
        ↓
Step 7 Financial   (unchanged — single-config deep-dive on a chosen row)
```

Key UX rules:

- Step 3a is **optional** — user can skip and go straight to Step 4
- Financial assumptions live in Step 1 (collapsed by default); Step 3a allows in-place override before running, for quick what-if iteration
- Step 4's results table is **data-driven** — shows PIRR columns only if `financial_results` exists in session state
- Re-running Step 3a (e.g. after changing tariff) is **cheap** — operational sweep stays cached; only the financial layer recomputes (~8-12 s for 100 configs)

---

## 8. Session state schema

```
st.session_state.sizing_results              # DataFrame — operational metrics per config (existing)
st.session_state.sizing_monthly_aggregates   # NEW — dict[config_id → {mwh_delivered[12], mwh_exported[12], bess_cycles[12], gas_mwh[12], gas_runtime[12]}]
st.session_state.financial_assumptions       # NEW — dict mirroring §5 catalog, populated from financial_config defaults + user overrides
st.session_state.financial_results           # NEW — DataFrame — PIRR, NPV, MOIC, headline FCFF totals per config
```

### Cache invalidation rules

| Trigger | Effect |
| --- | --- |
| User changes Step 1/2 (setup, rules) → re-runs Step 3 | All three financial caches cleared |
| User changes financial assumptions only (no operational change) → reruns Step 3a | `financial_results` cleared; `sizing_results` and `sizing_monthly_aggregates` preserved |
| User uploads a new solar profile → re-runs Step 3 | All caches cleared (profile change invalidates everything) |

---

## 9. Audit success criteria (v1)

**Primary test:** drive the engine with the configuration in D13 and reproduce **Combined PV+BESS+Gas PIRR = 9.2 ± 0.1 pp** (i.e. 9.1–9.3%).

**Secondary tests** (free, derived from SME's 2026-05-14 matrix — see D14 + decisions log A29):

| Solar DC | Grid | Tariff | BESS | Expected Combined PIRR | Green / Gas Share |
| --- | --- | --- | --- | --- | --- |
| 82 MWp | 58.4 MW | £170 | 250 MWh | **9.2%** (primary, D13) | 34.5% / 65.5% |
| 82 MWp | 58.4 MW | £160 | 250 MWh | 7.8% | 34.5% / 65.5% |
| 115 MWp | 81.9 MW | £170 | 250 MWh | 9.8% | 42.8% / 57.2% |
| 115 MWp | 81.9 MW | £160 | 250 MWh | 8.5% | 42.8% / 57.2% |

Each becomes a `tests/test_project_irr_excel_parity.py` row. CI fails if any drifts more than 10 bps. **All four targets are Combined PV+BESS+Gas PIRRs** per Anchal's 2026-05-14 reply (matrix column header explicitly reads "Project IRR (Overall for PV+BESS+Gas)"). The per-config Green/Gas share targets serve as a dispatch cross-check (engine currently matches to ±0.7 pp).

**Audit plan:**

1. Import inputs from Excel via the existing `src/financial_config.py` `INPUT_CELLS` mapping — extend if any values are missing.
2. Run the existing `src/financial_model.py` engine with the audit config.
3. Compute headline PIRR + monthly FCFF.
4. Diff against Excel `Consol Cash Flows` row 7 (Total FCFF) — extract those values once into a fixture.
5. **Triage:**
   - Within 0.1 pp on PIRR AND year-by-year within 1% → fix in place, document gaps
   - Within 0.1 pp on PIRR BUT year-by-year wanders → structural fix (likely indexation timing or tax depreciation)
   - >0.1 pp on PIRR OR sign error → rewrite from scratch
6. Lock with regression tests (D13 + 3 secondary cases above).

---

## 10. Deferred to v2

- Equity IRR
- Multi-asset / portfolio rollup
- Sensitivity tables (PPA / EPC / Grid / Yield / Interest)
- Step-function grid connection costs
- Two-component BESS capex (PCS £/MW + storage £/MWh)
- Real grid step-function thresholds for capex scaling beyond linear
- Carry-forward losses
- Capital allowances (UK-specific tax treatment)

These were eliminated from v1 by the strict-mirror approach. Each gets re-evaluated when v1 is in users' hands and we have feedback on which simplifications hurt.

---

## 11. Open housekeeping items

- The two reference profiles also exist as duplicates in `Test/` (`Burton Leonard_Project_VCN_HourlyRes_58MW.CSV` and `_82MW.CSV`) and are referenced by [tests/test_project_irr.py:39-40](../tests/test_project_irr.py). When the test file is reworked alongside the engine audit (D19), the path references should point at the new canonical location in `Inputs/`.
- `docs/Project_IRR_Integration_Decisions.md` is now stale (its A2 / A4 / audit-target decisions were corrected by SME review). Either delete it or add a "SUPERSEDED — see Financial_Assumptions_Spec.md" header at the top.
