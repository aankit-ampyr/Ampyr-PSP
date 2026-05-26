# Project IRR — Session Handover

**Last updated:** 2026-05-26 (A51 — PPA tariff / tenor / escalation surfaced in Step 2b UI)

**Status: v1 AUDIT CLOSED + A48 + A49 + A50 + A51 LANDED.** Engine state unchanged on the default path — d13 still **8.84%** / S+B **9.00%** / Gas **13.07%** / CAPEX **£101.4m** post-A44+A45. **74 tests pass** (was 73 — A51 added 1 e2e regression for the new PPA tariff override). 4-row SME audit matrix unchanged at ±0.5 pp v1 tolerance. A48 + A49 + A50 committed and pushed to `origin/Financial` (last push `d73824d`). A51 is the **current uncommitted work** on branch `Financial`.

## A51 (this session — 2026-05-26)

User asked "where is the tariff input configured" during A50 follow-up. Diagnosed a pre-existing legacy gap: the PIRR adapter reads `ppa_tariff_gbp_mwh` / `ppa_tenor_years` / `ppa_escalation_pct` directly from `wizard['financial']`, but no UI widget wrote them. The Step 2b PPA expander had 3 unrelated widgets (`ppa_selection`, `ppa_flex_pct`, `ppa_indexation`) that were vestiges of a pre-engine-wiring "case-table lookup" design that never landed.

**Closed in A51**: 3 new `st.number_input` widgets at the top of the Step 2b PPA expander surface the primary engine-driving values. Legacy widgets kept (labelled "— legacy") for backwards compatibility. Save payload extended. Test fixture aligned. New e2e regression (`test_ppa_tariff_override_lifts_pirr`) proves the override flows through the adapter.

**Files changed:**
- `pages/Step2b_FinancialSetup.py` — 3 new primary widgets + caption + legacy labelling + save payload (~+45 lines)
- `tests/test_wizard_state_path.py` — fixture extension + 1 new test (~+35 lines)
- `docs/Project_IRR_Integration_Decisions.md` — A51 entry + Revisions row
- `docs/Project_IRR_Status.md` — this rewrite

## A50 (this session — 2026-05-25)

Closes the v2 ambition archived in `docs/future_improvements/v2_price_and_inflation_curves.md`. User-directed restructure of Step 1 + real→nominal pipeline with two vendor slots.

**Phased into A50a (UI reorg) + A50b (pipeline). Both verified across 4 checkpoints with agent review at each:**

| Checkpoint | Scope | Status |
|---|---|---|
| CP1 (A50a) | Step 1 grouped under `## ⚙️ Operational` + `## 💼 Commercial` headers; solar profile default switched to `Solar Profile.csv`; Nominal Merchant Curve panel relocated from mid-Operational to end-of-Step-1 under Commercial | ✅ verified |
| CP2 (A50b engine) | `_apply_inflation_to_real_curve` + `_select_raw_curve` helpers added to `src/project_irr.py`; `_DEFAULT_BARINGA_CURVE_REAL` (506 entries) + `_DEFAULT_AURORA_CURVE_REAL` (519) extracted from Excel `Baringa and Aurora!r114 / r194` (Applied FT); 16 unit tests in `tests/test_a50_helpers.py` | ✅ verified |
| CP3 (A50b UI) | Wizard state schema: +5 setup keys + 3 financial keys; Step 1 Commercial expanded with 📈 Raw Price Curve (Baringa + Aurora panels in expanders + 3-way selector), 💸 Inflation Curve (default/upload + steady-state), 💰 Nominal Merchant Curve extended to 3 modes (default/computed/upload); Step 2b gets read-only CPI banner | ✅ verified |
| CP4 (A50b adapter) | `pirr_inputs_from_wizard_state` extended to 3-mode price-source handling; uploaded CPI now flows engine-wide (opex/tax + computed-mode merchant); 5 new e2e tests in `tests/test_wizard_state_path.py` covering computed-baringa / computed-aurora / computed-average / higher-cpi-lifts-pirr / cpi-flows-engine-wide | ✅ verified |

**Files changed (uncommitted):**

| File | Change |
|---|---|
| `src/project_irr.py` | +2 pure helpers (~80 lines), +2 dataclass-default imports from new defaults module, adapter extended for 3-mode price source + engine-wide CPI override (~50 lines). Engine core untouched. |
| `src/_baringa_aurora_defaults.py` | **NEW** — locked vendor defaults extracted from Excel (~1025 entries combined). |
| `src/wizard_state.py` | +5 setup keys + 3 financial keys for the pipeline. Schema additive only. |
| `pages/Step1_Setup.py` | Operational header added; Nominal Merchant Curve section moved from mid-page to end; Commercial subsections added (Raw + Inflation + extended Nominal). ~+500 lines net. |
| `pages/Step2b_FinancialSetup.py` | Read-only CPI banner above OPEX section (~+20 lines). |
| `tests/test_a50_helpers.py` | **NEW** — 16 unit tests for helpers + bundled defaults. |
| `tests/test_wizard_state_path.py` | +5 e2e tests + `_run_d13_with_computed_curve` helper (~+140 lines). |
| `docs/Project_IRR_Integration_Decisions.md` | A50 entry + Revisions row. |
| `docs/Project_IRR_Status.md` | This rewrite. |

**Out of scope** (preserved for follow-up): vendor scenarios (Reference / Low / High), tracker types (FT / SAT), API-based retrieval, DSCR sculpting (still v2 per A45).

## A49 (this session — 2026-05-21)

Closes the A48 placeholder. Step 1's price-curve panel now drives `PirrInputs.merchant_prices_monthly` through the engine adapter `pirr_inputs_from_wizard_state`. Re-labelled to **"💰 Nominal Merchant Curve"** to make the units explicit — uploaded values are passed verbatim to `_merchant_price`, must already be inflated to match Excel `Solar&BESS Operation!row 66` convention. No transformation, no calibration constant (G5).

**Files changed (5)**:

| File | Change |
|---|---|
| `src/project_irr.py` | +15 lines in `pirr_inputs_from_wizard_state` — single adapter branch reading `setup['merchant_price_curve_source']` + `setup['merchant_price_curve']`. Engine core untouched. |
| `pages/Step1_Setup.py` | Panel relabel + 2 new helper functions (`_compute_post_ppa_range`, `_validate_curve_coverage`). Coverage validator rejects uploads missing months in the post-PPA window. Placeholder caption replaced with v2 forward-pointer. |
| `tests/test_wizard_state_path.py` | +2 tests: `test_default_curve_preserves_d13_audit` (locks default branch) + `test_uploaded_nominal_curve_feeds_engine` (doubled-curve sanity that proves wiring). |
| `docs/Project_IRR_Integration_Decisions.md` | A49 Revisions row + full `### A49.` section above A47. |
| `docs/Project_IRR_Status.md` | This rewrite. |

**Out of scope** — preserved in [docs/future_improvements/v2_price_and_inflation_curves.md](future_improvements/v2_price_and_inflation_curves.md) (committed in `5fa5e5f`):

- Real-terms uploads with a base-year picker
- Uploadable CPI curve on Step 2b
- Real→nominal transformation in the adapter (`_apply_inflation_to_real_curve`)
- 3-line preview chart (uploaded curve / inflation factor / resulting nominal)
- Future API integration

A separate focused session lands all five. Estimated 1-2 days.

## A48 (prior session — 2026-05-21, committed `5fa5e5f`)

Architectural fix for the A28/A43 fresh-session bug class — by moving financial setup *before* Step 3a (Financial Sweep), users naturally configure assumptions in flow rather than discovering Step 7 after their sweep runs with broken defaults.

**Files changed (16 — net -890 lines):**

| File | Change |
|---|---|
| `pages/Step2b_FinancialSetup.py` | **NEW** — sections 1-9 (Timing/Solar/BESS/Revenue/CAPEX/OPEX/Land/Tax/WorkingCapital) + "Save Financial Inputs" button. Lifted verbatim from Step 7's pre-A48 input UI. |
| `pages/Step7_Financial.py` | Slimmed 1605 → 539 lines. Outputs only (Section 10 Results + Section 11 Excel Export). Reader-only banner points to Step 2b. |
| `pages/Step1_Setup.py` | New "💰 Market Price Curve" panel (between Solar Profile and Storable Solar Analysis). Viz of engine's default `_DEFAULT_MERCHANT_PRICES_MONTHLY` + CSV upload widget. **Placeholder** — engine wiring deferred. |
| `pages/Step1-Step5 + Step3a` | Step indicator: 7 cells → 9 cells (1, 2, 2b, 3, 3a, 4, 5, 6, 7). Stale "Step X of 4" labels fixed to "Step X of 7" on Step 1 + Step 2. |
| `utils/financial_inputs.py` | **NEW** — shared helpers (`pct_to_display`, `display_to_pct`, `get_financial_state`, `save_financial_inputs`, `MONTH_NAMES`). Used by Step 2b (writer) and Step 7 (reader). |
| `src/wizard_state.py` | Added `merchant_price_curve_source` + `merchant_price_curve` to `DEFAULT_WIZARD_STATE['setup']`. No financial defaults touched. |
| `tests/test_wizard_state_path.py` | Renamed 3 `test_step7_saved_*` → `test_step2b_saved_*` + their helpers. Module docstring + `__main__` block updated. **New test**: `test_default_wizard_state_has_price_curve_keys`. 12 → 13 tests. |
| `docs/Project_IRR_Integration_Decisions.md` | A48 entry added to Revisions log (Guardrail 6). |
| `docs/Step3a_Smoke_Test_Playbook.md` | §A.9 updated — A.9.4 (no Save button in Step 7), A.9.8/9 (Step 2b walk), A.9.10/11 (price curve panel). |

**Architecture (A48)**: Step 2b = WRITER of `wizard['financial']`; Step 3a + Step 7 = READERS. `DEFAULT_WIZARD_STATE['financial']` (A43-aligned) is the audit-correct fallback. **No engine changes** — `src/project_irr.py` untouched.

**E2E verification — three paths produce identical D13 numbers:**

```
                              Combined    S+B     Gas    CAPEX
Minimal-fin (Step 1 only):    8.84%       9.00%   13.07%  £101.4m
Step 2b-saved (full UI flow): 8.84%       9.00%   13.07%  £101.4m
Fresh-session (no Step 2b):   8.84%       9.00%   13.07%  £101.4m
```

That's the architectural property A48 was meant to deliver: the save-button location is independent of the data path.

## v1 audit state (unchanged since A45)

- d13 Combined **8.84%** / S+B **9.00%** / Gas **13.07%** vs target 9.20% — gap **-0.36 pp** (within ±0.5 pp v1 tolerance)
- m82_160 **-0.48 pp** / m115_170 **-0.23 pp** / m115_160 **-0.23 pp** — all within ±0.5 pp
- Tests: **50 pass, 0 xfail** (was 49 — A48 added `test_default_wizard_state_has_price_curve_keys`)
- v1 framing: pre-IC screening, what-ifs, sizing comparisons. Excel remains source-of-truth IRR for IC-pack.
- v1 captions on Step 3a + Step 4 + Step 7: "v1 reports IRR ~0.3-0.5 pp lower than Excel" disclosure.

## v2 — COMMITTED, not deferred

±0.5 pp tolerance is a v1 carve-out, NOT a permanent settlement. v2 work (DSCR-driven gearing convergence + cash sweep + Equity IRR + gearing-as-sweep-dimension) is required to close the audit to ±0.1 pp and let the engine replace Excel as source-of-truth. Estimated 1-2 weeks engineering. Anchal acknowledged this framing.

## Next session start — pick up from here

**A. Commit + push A50** (current session work — uncommitted on branch `Financial`)

A50 closes the v2 price-curve ambition. Files changed: see the A50 table in the header above. **73 pass / 0 xfail.** D13 invariant preserved on the `'default'` path. Verified across 4 checkpoints with agent review at each.

Suggested commit structure — **one bundled commit** (the pipeline is internally consistent and the 4 checkpoints landed sequentially, each green):

```
PSP A50: Step 1 restructure (Operational + Commercial) + Baringa/Aurora → Nominal Merchant pipeline
```

Or split into two commits if the user prefers: A50a (UI reorg + solar default) then A50b (engine + pipeline + tests).

After commit, push to `origin/Financial` and (per A49 pattern) merge Financial into Prototype via worktree + push.

**B. Browser walk-through** (recommended before commit)

The four agent reviews verified static correctness, but the live Streamlit on http://localhost:8512 should be exercised to confirm:
- Step 1 visually groups Operational and Commercial correctly
- Solar Profile.csv is the new first-time default (fresh session)
- Baringa / Aurora panels render with default curves; uploading a CSV works
- Switching the curve selector between baringa / aurora / average changes the Computed preview
- Switching Nominal Merchant Curve mode between default / computed / upload changes what's shown
- Step 2b OPEX banner shows the active CPI configuration

**C. Future v2 — Vendor scenarios + tracker types** (deferred per A50 scope)

If you want to expose the full Excel scenario matrix (Reference / Low / High × FT / SAT per vendor) instead of the user pre-selecting the "Applied" row in Excel before upload, that's an additive UI layer — per-panel scenario + tracker selectors that pick the right row from the uploaded vendor file. ~3-5 days work; not currently planned.

**D. v2 — DSCR sculpting + Equity IRR** (separate session, ~1-2 weeks)

1. **DSCR-driven gearing convergence** — iterate senior gearing down until `min(DSCR over debt schedule) ≥ 1.40`, recompute SHL principal as `(1 − senior_effective) × total_capex`, re-run CIR cap. Excel does this via `Solve_P1` VBA. v1 holds senior at 80% flat. **Primary v2 deliverable.**
2. **Cash sweep mechanism** — excess cash above DSCR-required level amortises debt early.
3. **Equity IRR computation** — ungeared FCFF − net debt service = equity FCF; XIRR gives Equity IRR (typically 12-18% on 9% Project IRR). Free byproduct once DSCR sculpting lands.
4. **Gearing as a sweep dimension** — currently fixed PirrInputs field; v2 makes iterable.

## Remaining v1 loose ends (unchanged since 2026-05-16)

- **Ankit's TODO**: send Anchal the handoff message (drafted at end of session, not yet sent).
- **Skipped intentionally**: browser smoke test §A re-run pre-handoff — Anchal's SME testing will surface any UI bugs. Playbook §A is current through A48 (A49 is engine wiring, no new UI smoke surface beyond the panel relabel + validator error path).

## State at handover

- d13 Combined **8.88%** / S+B 9.05% / Gas 13.07% — gap **-0.32 pp** vs target 9.20%
- m115_170 + m115_160 at **-0.19 pp** each (closest to ±0.1 pp tolerance, within 2×)
- m82_160 at **-0.45 pp**
- 42 pass + 4 xfail (the 4 xfails are the matrix rows)
- Working tree clean. A40 shipped across two commits: scaffolding `5fb4648` then full wiring `38599df`. `.claude/settings.local.json` modified locally only.

## Next session start — pick up from here

**A. Anchal has replied — apply her answers**

- If she confirms Q2 ±0.3 pp tolerance → 4/4 rows pass, audit closes, unblock Doublu handoff. Re-baseline test xfails to pass (change `SME_MATRIX` tolerance from 0.001 to 0.003 in `tests/test_project_irr_excel_parity.py` and convert the 4 `xfail` markers to plain asserts). Log as A41 in decisions log.
- If she clarifies Q1 (Insurance is actually CPI/RPI-indexed or has a P&M-coverage growth mechanism) → implement the split: separate `opex_insurance_indexation` field, decouple Insurance from the bundled CPI escalation. The A40 lookup pattern can be replicated per-line if Insurance needs its own curve. ~1-2 hr including tests. Expected +5-8 bps Combined. Log as A41 in decisions log + Spec D31.

**B. Anchal hasn't replied yet — queued engineering**

A40 is now committed and the IRR delta was null at 2-decimal precision (mechanism is Excel-faithful, but the early-year curve detail only spans 4 of 35 ops years against a 2.0% steady state). No further calibration work is queued — the residual gap is now an SME-judgement / tolerance question, not an engineering question. Reasonable next moves while waiting:

- **Step 3a Phase 2 — Step 4 conditional PIRR/NPV column augmentation** (per Spec D15). Cache invalidation already implemented (A27); needs UI verification. ~2-3 hr.
- **Browser smoke-test FULL PASS** — was blocked by audit; may be unblockable depending on Anchal's tolerance answer. ~2-3 hr per the 15-iteration playbook in `docs/Step3a_Smoke_Test_Playbook.md`.
- **Unify `sizing_results` vs canonical `wizard['results']['simulation_results']`** (P1 cleanup per A19). ~2 hr.

**A39 mechanism (for ref)**: 1-line fix — Excel `Curves and D&T!r10` is "Variable" CPI; steady-state from ops_year 3 onward is 2.0%, not the engine's old 2.5%. Lifetime CPI-sum gap closed on 5 fixed solar lines (greenkeeping, community, real_estate_tax, non_tech_am, tech_am). Insurance over-shoot remains a separate mechanism (open question to Anchal).

A39 was a 1-line Excel-mechanism fix: Excel `Curves and D&T!r10` is "Variable" CPI; the steady-state rate from ops_year 0 (2027) onward is 2.0%, not the engine's 2.5%. Lifetime CPI-sum gap closed on 5 fixed solar lines (greenkeeping, community, real_estate_tax, non_tech_am, tech_am). Insurance over-shoot remains a separate mechanism (construction premium + NIL indexation per Inputs!r274 + ~2% growth observed in Op r168).

**Prior session (A38)** landed multi-account dep + dep-from-construction + A35 phasing, +0.07-0.09 pp uniform on Combined. NOL pool activated from dormant A21 state.

**A38 details (kept for context):**

A38 landed — multi-account dep (3 accounts: long_term/short_term/financing) + dep-from-construction + A35 capex phasing activated. d13 Combined 8.78% → **8.85%** (+0.07 pp). All 4 matrix rows lifted +0.07-0.09 pp; gap closed from -0.30/-0.57 to **-0.21/-0.49 pp**. m115_170 closest to target at -0.21 pp. 42 pass + 4 xfail (matrix rows). The NOL pool that A21 added is now actually active (was lying dormant pre-A38 because `_calc_tax` mask was `is_operations` only — construction-period depreciation never fed the pool). Phase A (multi-account) was critical: the Financing account's 5.56%/mo RB rate on £2.2M IDC + Fin Fees generates £1.4M of pre-COD depreciation → £350k tax shield in early ops years, flipping A35 phasing from -0.15 pp regression (Phase C+D alone) to net positive +0.07 pp.

**Prior sessions**: A29-A37 closed the S+B opex over-shoot (£9.4k → £180k), resolved the 2042 FCFF anomaly, and confirmed r34 fuel cost root cause but parked the fix (wrong direction for Combined).

**Prior session (2026-05-15) shipped A32-A36** — five Excel-mechanism fixes that closed the S+B opex over-shoot (£9.4k → £180k) and resolved the 2042 FCFF anomaly. Cumulative uplift A32+A33+A34+A36: ~0.32 pp uniform on Combined PIRR. A35 capex phasing infrastructure shipped default-OFF pending paired NOL + dep-from-construction mechanisms.

**A30 + A31 fixes landed 2026-05-14 (Guardrail 5 — both replicate Excel mechanisms):**

- A30: Monthly merchant prices (quarterly seasonal pattern) replaced yearly arithmetic avg
- A31: Gas PPA tariff linked to solar PPA tariff (Excel `I19 = 'Overall Inputs'!E13`)

**A32 + A33 + A34 + A35 + A36 fixes landed 2026-05-15 (all Excel-mechanism replications):**

- A32: Solar balancing split — CfD £2.75/MWh flat (NIL escalation) during PPA tenor only; merchant time-varying curve (Baringa & Aurora) post-PPA. Engine balancing £11,277k → £6,062k (matches Excel).
- A33: Annual land-lease formula `Σ fixed + max(0, annual_rev - annual_fixed)` replaces engine's monthly `Σ max(fixed_m, rev_m)`. Engine land lease £16,123k → £15,140k (Excel £15,092k).
- A34: PV O&M uses "O&M - Year 3 Onwards" escalation (flat years 0-2, then 2%/yr) per Excel `Inputs!r267`, not CPI 2.5% from year 0. Engine PV O&M £24,683k → £21,664k (matches Excel).
- A35: Capex per-month phasing infrastructure shipped (`capex_phasing_sb` / `capex_phasing_gas` dicts + `_DEFAULT_CAPEX_PHASING_*` curves). **Default empty** — phasing-only regresses by 11 bps in isolation; needs paired depreciation-from-construction + UK NOL carry-forward. Activate when paired fix lands.
- A36: Gas major maintenance discrete-event schedule replaces level-annual approximation. Excel has 8 lumpy events at ops_years 1, 3, 4, 6, 7, 9, 12, 15 totaling £16,650k nominal; year 15 alone is £7,928k. Engine `gas_major_maint_schedule: dict` default = Burton-Leonard curve.

**Dispatch + UI stable:** Green/gas share matches Anchal ±0.7 pp on both configs (A29). UI work (A24–A28) correct.

## Where things are now

### Test status (run `python -m pytest tests/`)

- 42 tests pass
- 4 expected xfails (all Combined-target post-A29):
  - `test_d13_audit_combined` — uniform level residual (-0.42 pp post-A36)
  - 3 secondary matrix rows — all under target by 0.30-0.57 pp; uniform offset (not a sensitivity issue post-A31)

### Audit matrix — post-A36 (2026-05-15)

| Case | Combined Eng | Combined Tgt | ΔComb | Green % Eng | Green % Tgt | S+B Eng | Gas Eng |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **d13** (82/170) | 8.78% | 9.2% | **-0.42** | 34.7% | 34.5% | 8.82% | 14.13% |
| m82_160 (82/160) | 7.23% | 7.8% | **-0.57** | 34.7% | 34.5% | 8.17% | 8.59% |
| m115_170 (115/170) | 9.50% | 9.8% | **-0.30** | 43.5% | 42.8% | 10.22% | 10.44% |
| m115_160 (115/160) | 8.18% | 8.5% | **-0.32** | 43.5% | 42.8% | 9.53% | 5.93% |

**S+B opex over-shoot CLOSED.** Engine S+B opex lifetime now £89,380k vs Excel `FS!r59` £89,200k (Δ +£180k, was +£9,444k pre-session). Line items:

| Line | Engine | Excel | Δ |
| --- | --- | --- | --- |
| Solar PV O&M | 21,664k | 21,664k | 0 (was +3,019) |
| Solar Balancing (CfD + Merchant) | 6,062k | 6,062k | 0 (was +5,215) |
| Solar Fixed Lease | 15,140k | 15,092k | +48 (was +1,031) |
| Other solar fixed (5 CPI lines) | varies | varies | +800k uniform |
| Insurance | 9,103k | 8,807k | +296 |
| BESS step | 7,091k | 7,089k | +2 |

**Remaining 0.30-0.57 pp Combined gap is NOT opex-driven**. The opex correction lifted IRR by ~0.25 pp (less than the naive £9.4k → 0.6-0.7 pp estimate suggested — tax shield CIR cap partially absorbs the savings). A36's gas major maintenance schedule added another ~0.07 pp uplift (event-timing fix). The remaining gap must be in: depreciation timing (single-account vs multi-account, COD-start vs construction-start), tax shield mechanism (UK NOL carry-forward missing), capex line items (construction insurance, terminal land sale, LoC PPA, decomm bond all stubbed), or other lumpy gas opex line items (fuel cost r34, contract O&M r45, insurance r58 — same Excel discrete-event pattern as r44).

Excel reference (3.8h BESS snapshot, older case): S+B 8.85% (`Equity!D175`) / Combined 9.23% (`Consol Cash Flows!B9`) / Gas 10.77% (`Cash Flows-Gas!D84`). The 2026-05-14 matrix (4h BESS) is the live target.

## Engine architecture

[src/project_irr.py](../src/project_irr.py) — clean rewrite, replaces parked `financial_model_v0.py` + `consolidated_model_v0.py`.

Key dataclasses:

- `PirrInputs` — all engine inputs with D13 defaults
- `PirrResults` — 3 PIRRs (combined / solar+BESS-only / gas-only) + monthly chains

Key functions:

- `run_pirr(inp)` — top-level; runs combined + gas-disabled + S+B-disabled for the 3 PIRRs
- `_calc_revenue`, `_calc_opex`, `_calc_capex`, `_calc_depreciation`, `_calc_interest`, `_calc_shl_interest`, `_calc_tax`, `_calc_nwc_change`
- `pirr_inputs_from_wizard_state(fin, setup, monthly_aggregates)` — wizard-state bridge

Mechanics added across May 12–15 sessions — see decisions log A21 + A22 + A30 + A31 + A32 + A33 + A34 + A35 + A36:

1. **RB depreciation with SLM crossover** (`D&T!E165` = "RB", rate 2/36 p.a.)
2. **Shareholder Loan tax shield** — principal = 99% × (1 − senior_gearing) × **solar+BESS capex only**, rate 15% p.a.
3. **UK CIR cap** = max(£2m, 30% × EBITDA) on **total** interest (senior + SHL), senior prioritised
4. **UKETS uses thermal MWh** (= electric / efficiency)
5. **SHL excludes gas capex** — Excel structures gas as separate financing chain
6. **Monthly merchant prices (A30)** — quarterly seasonal pattern from `Solar&BESS Operation!r66`; replaces yearly arithmetic avg
7. **Gas PPA tariff linked to solar (A31)** — `Inputs-Gas!I19 = 'Overall Inputs'!E13`; tariff sensitivity now matches Excel
8. **Solar balancing CfD/Merchant split (A32)** — CfD flat £2.75/MWh during PPA tenor only (NIL escalation); merchant time-varying Baringa curve post-PPA. New `merchant_balancing_rate_by_ops_year` field
9. **Annual land lease formula (A33)** — replaces monthly `max(fixed_m, rev_m)` with annual `Σ fixed + max(0, annual_rev - annual_fixed)`. Per Anchal Q3
10. **PV O&M "O&M - Year 3 Onwards" escalation (A34)** — flat years 0-2, then 2%/yr from year 3. Engine `_esc_factor` extended with non-geometric branch. PV O&M split out of bundled solar fixed indexation
11. **Capex per-month phasing infrastructure (A35) — DEFAULT OFF.** `capex_phasing_sb` / `capex_phasing_gas` dicts + `_DEFAULT_CAPEX_PHASING_*` curves available. `_build_timeline` extends backwards if phasing dicts have pre-construction months. `_calc_capex` per-stream phasing when populated; uniform-9-month fallback when empty. **In isolation regresses by 11 bps**; needs paired depreciation-from-construction + UK NOL carry-forward.
12. **Gas major maintenance discrete-event schedule (A36)** — `gas_major_maint_schedule: dict[ops_year, GBPk]` replaces level-annual. 8 lumpy events; year 15 is £7,928k (47% of lifetime). Values nominal, no additional escalation.

## UI integration (Step 7)

[pages/Step7_Financial.py](../pages/Step7_Financial.py) migrated to new engine.

- Reads `wizard['setup']['load_mw']` (no hardcode)
- Shows all 3 PIRRs (Combined / S+B / Gas)
- "8b. Advanced — Tax Shield Methodology" expander exposes SHL switch/pct/rate + depreciation method/rate with Excel defaults locked

## Key files

| Path | Role |
| --- | --- |
| [src/project_irr.py](../src/project_irr.py) | Engine |
| [src/dispatch_energy.py](../src/dispatch_energy.py) | Year-1 monthly aggregates from hourly dispatch |
| [src/excel_reader.py](../src/excel_reader.py) | Excel parameter reader |
| [tests/fixtures/d13_inputs.py](../tests/fixtures/d13_inputs.py) | D13 fixture (parameterised) |
| [tests/test_project_irr_excel_parity.py](../tests/test_project_irr_excel_parity.py) | SME matrix regression test |
| [pages/Step7_Financial.py](../pages/Step7_Financial.py) | Single-config deep-dive UI |
| [docs/Financial_Assumptions_Spec.md](Financial_Assumptions_Spec.md) | Locked spec (D1–D27) |
| [docs/Project_IRR_Integration_Decisions.md](Project_IRR_Integration_Decisions.md) | Running decisions log (A1–A36) |

## What's left, in priority order (post-A39)

| Item | Est. impact | Notes |
| --- | --- | --- |
| **SME tolerance conversation with Anchal** | Closes 3 of 4 rows at ±0.3 pp | m115_170 and m115_160 at -0.19 pp; d13 -0.32; m82_160 -0.45. ±0.3 pp tolerance accepts 3/4. 15-min call could resolve the credibility/handover concern. |
| Variable CPI curve refactor | 0-1 bp | Three-quarters fix already in place via flat 2.0%. Marginal value. |
| Insurance construction premium (Op r124) | 1-2 bps | Excel has £287k yrs 0-1 dropping to £205k yr 2+. Engine flat at £166k. Mechanism unclear from Op r124 reference. |
| **Solar fixed indexation residual (DONE — A39)** | +0.02-0.04 pp delivered | CPI rate 2.5% → 2.0% (Excel `Curves and D&T!r10` steady-state). 5 of 6 CPI-indexed lines now within 0.5% of Excel; Insurance still off due to separate construction-premium mechanism. |
| **NOL pool + depreciation-from-construction (DONE — A38)** | +0.07-0.09 pp delivered | NOL pool activated by widening `_calc_tax` mask + dep-from-construction + multi-account dep + A35 phasing on. Delivered toward low end of 10-25 bps est. |
| **r34 fuel cost root cause (DONE — parked)** | 0 bps Combined; would close -3.6 pp Gas-only over-shoot if ever needed | Root cause CONFIRMED: (1) fuel-price escalation off-by-one (engine flat period is 4 years, Excel is 3 years — change `(1.01)^max(0, oy-3)` to `max(0, oy-2)`); (2) heat-rate degradation between major-maintenance events (Excel r29 ramps ~1.5%/yr, resets at maint events; engine uses fixed 0.385). r16 (electric MWh) is flat in Excel — heat-rate degradation affects fuel consumption only, no revenue-side counterpart. Both fixes would widen the Combined gap → **parked indefinitely for Combined audit**. Can be revisited if Gas-only IRR alignment becomes a separate SME requirement. |
| **A36 follow-up r45/r58 (DONE — null result)** | 0 bps | A37 verified r45 Contract O&M Δ -£3.4k and r58 Insurance Δ -£1.3k both within rounding of Excel. Smooth multiplicative escalation matches engine assumption. No fix needed. |
| Small solar fixed residual (~£1,100k aggregate) | 5-7 bps | 5 CPI lines uniformly 2.3% over + Insurance 3.4% over. Likely indexation timing/anchor-date mismatch (start from `Inputs!r293-304 = 2023-03-01`). |
| Construction insurance + terminal land sale + LoC PPA + decomm bond | 10-30 bps total | Per gap analysis §3.1-3.4. All stubbed/missing. |
| Multi-account depreciation (Excel 3-account vs engine single) | <10 bps | Excel `D&T!r169-178` splits Long-term / Short-term / Financing with per-cohort RB clocks. Engine uses single. |
| Step 3a Phase 2 — Step 4 conditional augmentation | — | Show PIRR/NPV columns in Step 4 results when `financial_results` exists. Not blocked by calibration. |
| Step 3a Phase 2 — Cache invalidation per spec §8 | — | A27 already implemented; needs UI verification. |
| Performance budget verification (D16, 8–12 s/100 configs) | — | A27 measured 2.6 s / 100 configs — within budget. Marked done pending browser confirmation. |
| Browser smoke-test FULL PASS | — | Was blocked by Combined audit; may be unblockable once Anchal confirms tolerance (Branch A). |
| Doublu handoff prep | — | Per user mandate: blocked until SME validates prototype. SME validation pending on the Q1/Q2 memo. |

**Suggested order for next session**: gated on Anchal's reply to the Q1/Q2 memo (see "Next session start" section above). All engine-side audit work that can be done without SME input has landed through A40 — residual gap is now an SME-judgement / tolerance question, not an engineering question.

## Excel discoveries / debugging traps (May 12-16 sessions)

Useful for future debugging. Full write-up in decisions log A23 + A30 + A31 + A32 + A33 + A34 + A35 + A36 + A40.

- **Gas PPA tariff is hard-linked to solar PPA tariff (A31).** Excel `Inputs-Gas!I19` is a formula: `='Overall Inputs'!E13`. When you change the solar PPA, gas changes too. This is what closed the tariff sensitivity gap (engine response went from -0.55 pp/£10 to -1.54 pp/£10 vs target -1.4). Anchal's earlier hint "PPA varies linearly with tariff... check revenue lease" was a red herring; the real mechanism was hidden in the gas inputs.
- **Merchant prices are quarterly seasonal (A30).** `Solar&BESS Operation!r66` carries 4 distinct values per year (3 months at each): Q1 winter peak, Q2 spring trough, Q3-Q4 mid. Solar generates in Q2-Q3 (low-priced quarters), so volume-weighted realised price is ~7% below arithmetic yearly avg. Engine now uses `merchant_prices_monthly: dict[(year, month), price]`.
- **CIR cap is on TOTAL interest, not SHL alone.** Excel `D&T!r210-r212` caps deductibility at max(£2m, 30% × EBITDA) applied to senior + SHL combined. Senior is prioritised; SHL fills remaining headroom. Applying the cap to SHL alone gave 9.45% S+B (over by 0.55 pp) — total-interest cap gave 8.93% (in tolerance).
- **UKETS uses thermal MWh, not electric output.** Excel `Cash Flows-Gas!r38` computes CO2 cost on fuel-input MWh (= electric / efficiency). The electric-MWh basis under-states UKETS by 5×.
- **SHL applies to solar+BESS capex only, not gas.** Excel structures gas as a separate financing chain in `Cash Flows-Gas` with no SHL. Engine had been over-attributing £23k phantom SHL interest to the gas-only run.
- **Excel `Cash Flows-Gas` line-item rows appear doubled (debugging trap).** Individual rows like r34 (fuel cost), r38 (UKETS), r41-r59 (fixed opex) sum to ~2× the corresponding line items in the engine. The summary chain at r66-r82 is the trustworthy reference — match against those, not the granular rows.
- **115 MWp gas IRR as structural validator.** Post-fix gas-only PIRR for 115 MWp cases = 10.10% vs Excel 10.77% — essentially matches. The 82 MWp residual (13.65%, +2.88 pp over) is a fixture-specific tail, almost certainly fuel-escalation profile. Don't chase it as structural.
- **SHL principal: engine vs Excel.** Engine SHL = (1 − 0.80) × £80k × 0.99 ≈ £15.8k. Excel `Equity!r108` Shareholder drawdowns = £32,482 — roughly 2× ours. Implied "effective senior gearing" in Excel ≈ 67% after DSCR convergence reduces senior below 80% target. We don't model DSCR convergence; under-modelling of SHL principal is partly compensated by the CIR cap (which Excel hits more often).
- **Excel has multi-account depreciation; we use single.** Excel `D&T!r169-178` has three accounts (Long-term/Short-term/Financing) with per-cohort RB clocks from construction additions. We use single-account RB+SLM crossover. Lifetime matches; within-year timing differs (~10 bps IRR effect). Excel also uses different methods per asset class (RB for S+B, SLM for gas via `Inputs-Gas!F66`). Single method engine-side explains some residual Combined gap.
- **Excel deploys capex over 18 months, not 9 (A35).** Construction Start in `Solar&BESS Inputs!F19 = 2026-10-01` but Excel has pre-construction "development phase" (Inputs `r18` = 19 months development time). 33.5% of gas capex deploys in Jan 2026 alone. S+B is S-curved with peak in Mar 2027 (22.7%). Engine uses uniform-9-month. Phasing-only fix regresses IRR by 11 bps because Excel pairs phasing with depreciation-from-capex-addition + UK NOL — both missing in engine.
- **Gas Major Maintenance is 8 discrete events, not level annual (A36).** Excel `Cash Flows-Gas!r44` has events at ops_years 1, 3, 4, 6, 7, 9, 12, 15. The year-15 event alone is £7,928k (47% of £16,650k lifetime). Engine had been level-annualising; lifetime matched but the year-15 spike caused a -£6,274k FCFF anomaly in 2042.
- **Gas opex line items may share the lumpy pattern.** A36 only fixed r44. r34 (fuel), r45 (contract O&M), r58 (insurance) likely show similar discrete-event timing in Excel. To be investigated next session as A36 follow-up.
- **"O&M - Year 3 Onwards" escalation case (A34).** Excel has 14 indexation cases in `Curves and D&T`; engine handles 5 geometric + 2 non-geometric ("O&M - Year 3 Onwards", "Flat 0%"). PV O&M is the D13 line that uses the non-geometric case. Other 9 escalation cases (Flat 0%, CPI - CfD, CPI + 0.5%, CPI + 3.1%, etc.) not yet implemented — needed for non-D13 configs per gap analysis §1.2.

## Open SME questions

Two open with Anchal Gupta as of 2026-05-16 — memo at [docs/SME_Memo_Anchal_2026-05-16.md](SME_Memo_Anchal_2026-05-16.md):

- **Q1 — Insurance NIL contradiction**: `Solar&BESS Inputs!r274` selection reads "NIL INDEXATION" but Op r168 lifetime £8,807k implies ~2.35% effective escalation. What's actually being applied (CPI/RPI/capex-growth uplift on P&M coverage)?
- **Q2 — Audit tolerance**: ±0.1 pp accepts 0/4 rows; ±0.3 pp accepts 4/4 rows today. Is ±0.3 pp an acceptable audit tolerance given v1 scope exclusions (no DSCR sculpting, no gas-chain depreciation refinement, no equity-IRR feedback)?

Earlier tariff sensitivity follow-up (May 13) was resolved internally by A31 — answer was in Excel itself (`Inputs-Gas!I19` formula link).

## Guardrails that govern this work

(From project `CLAUDE.md`)

- **Guardrail 5**: No calibration constants, ownership multipliers, or invented adjustments. If Python diverges from Excel, fix by replicating an Excel mechanism — never a fudge factor.
- **Guardrail 6**: Every PIRR decision/fork/reversal logged in `Project_IRR_Integration_Decisions.md` at the time it's made.

## Quick re-orientation commands for a new session

```bash
# Run the audit
python -X utf8 tests/test_project_irr_excel_parity.py

# Run all tests
python -m pytest tests/ --no-header

# Launch the dashboard
streamlit run app.py
```

Read [docs/Financial_Assumptions_Spec.md](Financial_Assumptions_Spec.md) first (locked state, D1–D30), then [docs/Project_IRR_Integration_Decisions.md](Project_IRR_Integration_Decisions.md) Revisions log + most recent sections A40 → A39 → A38 → A37 → A36 → A35 → A34 → A33 → A32 (in order of recency) for the 2026-05-15 + 2026-05-16 session activity.

## Session-by-session uplift summary

| Session | Combined IRR Δ (d13) | Engine state |
| --- | --- | --- |
| 2026-05-12 (A21/A22) | structural — gas calibrated, S+B in tolerance under old A20 reading | Pre-A29: thought audit passed via S+B 8.93% vs (wrong) 8.9% target |
| 2026-05-14 (A29) | -0.43 pp (target shifted to Combined 9.2%, engine 8.77%) | Audit headline reversed; tariff sensitivity gap exposed |
| 2026-05-14 (A30) | -0.74 pp (engine 8.46%) | Monthly merchant prices over-shoot fixed; level fell uniformly |
| 2026-05-14 (A31) | -0.74 pp (engine 8.46%) | Gas PPA tariff link resolved tariff sensitivity (level unchanged) |
| 2026-05-15 (A32+A33+A34) | -0.49 pp (engine 8.71%) | S+B opex over-shoot closed (£9.4k → £180k) |
| 2026-05-15 (A35) | infrastructure shipped, default off | Phasing-only would regress by 11 bps; await paired dep/NOL |
| 2026-05-15 (A36) | -0.42 pp (engine 8.78%) | Gas major maint discrete events; 2042 anomaly resolved |
| 2026-05-16 (A37) | -0.42 pp (engine 8.78%, no change) | Priority-1 diagnostic — r45/r58 already smooth/matching; r34 has separate 3.8% under-shoot (wrong direction for Combined). No engine changes. |
| 2026-05-16 (A37 root cause) | -0.42 pp (engine 8.78%, no change) | r34 root cause CONFIRMED via decomposition — fuel-esc off-by-one + heat-rate degradation between maint events. r16 (electric MWh) flat → no revenue-side counterpart. Both fixes wrong-direction for Combined → parked indefinitely. NOL+dep-from-construction promoted to priority-1. |
| 2026-05-16 (A38) | -0.35 pp (engine 8.85%, +0.07 pp) | Multi-account dep + dep-from-construction + A35 phasing on. NOL pool activated (was dormant pre-A38). 4 matrix rows lifted +0.07-0.09 pp uniform. Tests re-baselined: Combined 8.85% / S+B 9.02% / Gas 13.07%. |
| 2026-05-16 (A39) | **-0.32 pp** (engine **8.88%**, +0.03 pp) | CPI rate 2.5% → 2.0% per Excel `Curves and D&T!r10` steady-state. 5 CPI-indexed lines uplifted uniformly. m115_170 and m115_160 now at -0.19 pp gap each (closest to ±0.1 pp tolerance). |
| 2026-05-16 (A40) | **-0.32 pp** (engine **8.88%**, null result) | Time-varying CPI curve wired into `_esc_factor` (Excel `Curves and D&T!r10` per-year rates 2025-2029; 2.0% steady from 2030). Excel-faithful per Guardrail 5; IRR unchanged at 2-decimal precision because early-year curve detail spans only 4 of 35 ops years against the 2.0% steady-state tail. Curve infrastructure unlocks per-line CPI overrides for any future SME-clarified case (e.g. Insurance). Tests: 42 pass + 4 xfail unchanged. |
| 2026-05-16 (A41) | engine unchanged | Step 4 conditional Financial Metrics section (Step 3a Phase 2). Visible UI feature; engine untouched. |
| 2026-05-16 (A42) | engine unchanged | sizing_results unification — dropped the dead `wizard['results']['simulation_results']` slot. Top-level `st.session_state.sizing_results` is canonical per Spec §8. |
| 2026-05-16 (A43) | engine unchanged; UI path **fixed** | Browser smoke test §16 caught fresh-session path producing wrong PIRR (19.67%) + CAPEX (£64.7m) for D13. Root cause: A28 fixed Step 7 UI defaults + added a lock-in test, but `DEFAULT_WIZARD_STATE['financial']` was still pre-A28. A43 aligned all 25 misaligned values + added 5 missing keys + 3 new regression tests covering the fresh-session path. Tests: 45 pass + 4 xfail. Audit matrix unchanged. |
| 2026-05-16 (A44) | **-0.36 pp** (engine **8.84%**, -0.04 pp) | Insurance discrete-year schedule per Anchal Q1 reply. Excel `Solar&BESS Operation!r168` schedule (years 1-2 construction premium £282/£288k, year 3 drop to £205k with 30% discount, years 4-10 alternating discount, year 11+ 2%/yr growth from £206.27k anchor). Lifetime £8,806.79k matches Excel £8,806.63k. **IRR went DOWN, not up**: pre-A44 had a fortuitous per-kWp × CPI cancellation that under-shot early years + over-shot late years; A44 front-loads cost into construction-premium years (years 1-2) where NPV weighting is highest. The mechanism is now Excel-faithful (Guardrail 5); the residual gap is the structural carve-out Anchal pre-acknowledged in Q2 ("gearing or debt sizing not built"). Tests: 45 pass + 4 xfail; wizard-state baselines re-locked. |
| 2026-05-16 (A45) | **v1 CLOSED** at ±0.5 pp tolerance | Path 1 decision (Ankit). Tolerance relaxed 0.001 → 0.005 in `test_project_irr_excel_parity.py`; 4 xfail markers removed; 49 pass + 0 xfail. Residual ~0.3-0.5 pp gap is **temporary v1 carve-out**, NOT permanent: v2 will close it via DSCR sculpting (committed, not optional). v1 use cases: pre-IC screening / what-ifs / sizing comparisons. Excel remains source-of-truth for IC-pack headline IRR until v2 lands. Production Doublu handoff unblocked. |
| 2026-05-16 (v1 polish, `ae48f49`) | engine unchanged | SME-handoff polish: removed §16 DEBUG `st.warning` block in Step 3a (was raw state printout from A43 diagnostic); added "v1 reports Project IRR ~0.3-0.5 pp lower than Excel" info banner on Step 3a + Step 4 + Step 7 so testers see the v1 conservatism disclosure in-context. Tests 49 pass; Streamlit boots clean. |
| 2026-05-16 (A46) | engine unchanged | MOIC computation + UI surface. Spec §7 v1 deliverable, deferred at A41 because engine didn't compute it. New `PirrResults.moic` = `sum(fcff > 0) / abs(sum(fcff < 0))` (ungeared FCFF basis). D13 audit MOIC = 2.22x. Surfaced in Step 3a (new column + sort option), Step 4 (7th metric tile), Step 7 (5th metric tile). Tests 49 pass. |
| 2026-05-16 (A47) | engine unchanged | Dead-code cleanup. Removed `wizard['results']` dict (7 keys) + 5 helper functions (`add_comparison_config` etc.) from `src/wizard_state.py`. None imported by any page. Net -50 lines. Tests 49 pass; Streamlit boots clean. |
| 2026-05-16 (handoff state) | engine unchanged | Anchal acknowledged path 1 via Teams. SME handoff message drafted; awaiting Streamlit Cloud redeploy. v1 audit thread complete. |
