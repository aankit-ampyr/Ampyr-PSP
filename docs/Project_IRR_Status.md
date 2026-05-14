# Project IRR — Session Handover

**Last updated:** 2026-05-16 (post-A37)
**Headline:** Audit unchanged from 2026-05-15 — d13 Combined 8.78% / S+B 8.82% / Gas 14.13%; 4 matrix rows under target by 0.30-0.57 pp; 42 pass + 4 xfail. A37 ran the priority-1 "other lumpy gas opex" diagnostic — **hypothesis rejected for r45 (Contract O&M) and r58 (Insurance)** (both smooth, match Excel within £3k lifetime). **r34 (Fuel cost) found to have a separate 3.8% systematic under-shoot** (engine £201,174k vs Excel £209,037k = -£7,864k lifetime), root cause TBD — likely Excel applies fuel escalation from year 1 (not year 4) or `gas_mwh` varies year-on-year. **No engine changes today.** Direction-of-impact analysis says fixing r34 alone widens the Combined gap (helps Gas-only validation but reduces Combined IRR). Decision: park r34 pending root-cause diagnostic; bump priority-2 (NOL + dep-from-construction) to new priority-1.

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

## What's left, in priority order (post-A37)

| Item | Est. impact | Notes |
| --- | --- | --- |
| **Close residual 0.30-0.57 pp Combined gap — non-opex sources** | — | Opex side closed (engine S+B £89.4k vs Excel £89.2k = +£180k). Remaining gap must be in tax shield, capex line items, depreciation timing, or revenue-side mismatch. |
| **NOL pool + depreciation-from-construction (NEW priority-1)** | 10-25 bps | Unlocks A35 capex phasing. Add NOL carry-forward to `_calc_tax`; move depreciation start to capex-addition month per Excel `D&T!r68`. Then flip A35 default to populated. |
| **r34 fuel cost root-cause diagnostic** (was A36 follow-up) | 0 bps Combined; closes -3.6 pp Gas-only over-shoot | Excel r34 lifetime £209,037k vs engine £201,174k = -£7,864k (-3.8%); systematic across all 20 years, not lumpy. Engine ops_years 1-3 are flat at £12,076k while Excel ramps 1.7%/yr. Two candidate causes: (a) fuel escalation starts year 1 not year 4; (b) `gas_mwh` varies year-on-year (gas degradation). If (b), the same mechanism likely touches gas *revenue* too — could be net-positive on Combined. Worth one Excel-side diagnostic before parking. |
| **A36 follow-up r45/r58 (DONE — null result)** | 0 bps | A37 verified r45 Contract O&M Δ -£3.4k and r58 Insurance Δ -£1.3k both within rounding of Excel. Smooth multiplicative escalation matches engine assumption. No fix needed. |
| Small solar fixed residual (~£1,100k aggregate) | 5-7 bps | 5 CPI lines uniformly 2.3% over + Insurance 3.4% over. Likely indexation timing/anchor-date mismatch (start from `Inputs!r293-304 = 2023-03-01`). |
| Construction insurance + terminal land sale + LoC PPA + decomm bond | 10-30 bps total | Per gap analysis §3.1-3.4. All stubbed/missing. |
| Multi-account depreciation (Excel 3-account vs engine single) | <10 bps | Excel `D&T!r169-178` splits Long-term / Short-term / Financing with per-cohort RB clocks. Engine uses single. |
| Step 3a Phase 2 — Step 4 conditional augmentation | — | Show PIRR/NPV columns in Step 4 results when `financial_results` exists. Not blocked by calibration. |
| Step 3a Phase 2 — Cache invalidation per spec §8 | — | A27 already implemented; needs UI verification. |
| Performance budget verification (D16, 8–12 s/100 configs) | — | A27 measured 2.6 s / 100 configs — within budget. Marked done pending browser confirmation. |
| Browser smoke-test FULL PASS | — | Blocked by Combined audit not passing. Re-run after calibration closes the gap. |
| Doublu handoff prep | — | Per user mandate: blocked until SME validates prototype. SME validation requires audit pass. |

**Suggested order for next session**: r34 root-cause diagnostic (cheap, Excel-side only; might surface a gas-degradation mechanism with revenue-side counterpart); then NOL+dep-from-construction (highest-impact Combined fix, unlocks A35); then solar fixed indexation residual.

## Excel discoveries / debugging traps (May 12-15 sessions)

Useful for future debugging. Full write-up in decisions log A23 + A30 + A31 + A32 + A33 + A34 + A35 + A36.

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

None outstanding. The tariff sensitivity follow-up that was queued earlier (May 13) was resolved internally by A31 — the answer was in Excel itself (`Inputs-Gas!I19` formula link). No further Anchal queries pending as of 2026-05-15.

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

Read [docs/Financial_Assumptions_Spec.md](Financial_Assumptions_Spec.md) first (locked state, D1–D27), then [docs/Project_IRR_Integration_Decisions.md](Project_IRR_Integration_Decisions.md) Revisions log + most recent sections A37 → A36 → A35 → A34 → A33 → A32 (in order of recency) for the 2026-05-15 + 2026-05-16 session activity.

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
| 2026-05-16 (A37) | **-0.42 pp** (engine **8.78%**, no change) | Priority-1 diagnostic — r45/r58 already smooth/matching; r34 has separate 3.8% under-shoot (wrong direction for Combined). No engine changes. |
