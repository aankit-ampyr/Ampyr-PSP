# Future v2 — Real-terms price curves + variable CPI curve

> **Status: deferred to v2.** Original v1 ambition reduced to nominal-curve
> upload only (see A49 / current `Step 1 Nominal Merchant Curve` work). This
> document preserves the full real→nominal + uploadable-CPI plan as a
> roadmap reference. Drafted 2026-05-21; not yet scheduled.

## Context

Beyond v1's nominal-only upload, the longer-term ambition is to mirror the
**full Excel chain** that `_DEFAULT_MERCHANT_PRICES_MONTHLY` collapses:

```
Baringa and Aurora (raw forecaster data, real £/MWh)
   └─ Curves and D&T!r30  (applies inflation indexation: real × (1+CPI)^(yr-base))
        └─ Solar&BESS Operation!r66  (final nominal curve consumed by IRR — v1)
```

Users should be able to:
1. Upload custom price curves in **real terms** (what Aurora / Baringa
   actually publish — typically today's pounds).
2. Upload a custom inflation/CPI curve, with the engine's
   `_DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR` as default.
3. Have the engine apply the inflation curve to convert real → nominal
   before computing PIRR.
4. (Eventually) plug an API for forecast retrieval instead of manual
   upload.

## Decisions locked in 2026-05-21 session

| # | Question | Decision |
|---|---|---|
| 1 | CPI curve UI lives where? | **Step 2b only.** Step 1's price panel reads it cross-page for the preview. |
| 2 | What if upload covers only some months? | **Reject incomplete uploads with an error.** Required coverage = every month from `cod_year + ppa_tenor_years` through `cod_year + project_life_years − 1` (the post-PPA window the engine actually consults). |
| 3 | Future API placeholder? | **Drop entirely.** Sources stay `'default'` \| `'upload'`. No dead UI, no reserved enum value. |
| 4 | Where does real→nominal conversion happen? | **In the adapter** (`pirr_inputs_from_wizard_state`). Engine A30 contract unchanged. |
| 5 | Default base year for real-terms uploads? | **2024** — earliest year in `_DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR`, conventionally `factor = 1.0`. User can override. |

## Files changed (estimates)

| File | Status | Approx change |
|---|---|---|
| `src/wizard_state.py` | edit | +2 keys in `setup`, +3 keys in `financial`. ~10 lines. |
| `src/project_irr.py` | edit | +1 helper (`_apply_inflation_to_real_curve`), +~40 lines in `pirr_inputs_from_wizard_state`. Engine core untouched. |
| `pages/Step1_Setup.py` | edit | Modify panel: + real/nominal radio + base-year input + 3-line preview chart + coverage validator + cross-page note. ~+90 lines. |
| `pages/Step2b_FinancialSetup.py` | edit | +1 new expander "Inflation (CPI) Curve" with default/upload radio, data-editor + CSV upload, viz, steady-state input. +3 keys in save payload. ~+120 lines. |
| `tests/test_wizard_state_path.py` | edit | +4 tests covering the new paths. ~+100 lines. |
| `tests/test_project_irr.py` | edit | +3 unit tests for `_apply_inflation_to_real_curve`. ~+50 lines. |
| `docs/Project_IRR_Integration_Decisions.md` | edit | +1 new section (the v2 entry) + Revisions log row. ~+40 lines. |
| `docs/Project_IRR_Status.md` | edit | Header rewrite for v2 handover state. ~+15 lines. |

## Engine + adapter behaviour

### New helper: `_apply_inflation_to_real_curve`

In `src/project_irr.py`, add near the existing `_build_cpi_factor_lookup`
(around line 232):

```python
def _apply_inflation_to_real_curve(
    real_curve: dict[tuple[int, int], float],
    cpi_curve: dict[int, float],
    steady_state_rate: float,
    base_year: int,
) -> dict[tuple[int, int], float]:
    """Convert {(year, month): real_£/MWh} to nominal by year-by-year
    compounding. Anchor: nominal(base_year) = real(base_year). For each year y,
    nominal_factor[y] = product over k in (base_year, y] of (1 + cpi[k]),
    using `steady_state_rate` for k not present in `cpi_curve`. Replicates
    Excel `Curves and D&T!r30 = real × (1 + cpi)^(year − base)`. G5-compliant.
    """
```

Pure function, no streamlit deps, fully unit-testable. Anchored at calendar
year (NOT ops_year — that's a separate convention used by
`_build_cpi_factor_lookup`).

### Adapter changes in `pirr_inputs_from_wizard_state`

Add a block immediately before the `PirrInputs(...)` constructor that:

1. Reads `setup.get('merchant_price_curve_source', 'default')`,
   `setup.get('merchant_price_curve')`,
   `setup.get('merchant_price_curve_terms', 'nominal')`,
   `setup.get('merchant_price_curve_base_year', 2024)`.
2. Reads `fin.get('cpi_curve_source', 'default')`,
   `fin.get('cpi_curve_by_calendar_year')`,
   `fin.get('cpi_steady_state_rate')`.
3. Resolves the effective CPI curve and steady-state rate.
4. Resolves the effective merchant curve via the pass-through matrix:

| price source | terms | inflation source | engine receives |
|---|---|---|---|
| default | (forced nominal) | default | engine defaults (D13 invariant) |
| default | (forced nominal) | upload | nominal default curve; uploaded CPI for opex/tax only |
| upload | nominal | default | uploaded curve verbatim; default CPI |
| upload | nominal | upload | uploaded curve verbatim; uploaded CPI for opex/tax |
| upload | real | default | uploaded curve × default CPI cumulative factors |
| upload | real | upload | uploaded curve × uploaded CPI cumulative factors |

5. Passes `merchant_prices_monthly`, `cpi_curve_by_calendar_year`,
   `cpi_steady_state_rate` into `PirrInputs(...)`.

## UI changes

### Step 1 modifications

1. **Terms radio** (when source = `'upload'`): "In real terms — apply
   inflation curve from base year" (default) / "Already in nominal terms"
2. **Base-year input** (when terms = `'real'`): `st.number_input("Base
   year", min=2020, max=2030, value=2024)`
3. **3-line preview chart**:
   - Line 1: uploaded real-terms curve — blue
   - Line 2: cumulative nominal factor — dotted grey, secondary axis
   - Line 3: resulting nominal curve (line 1 × line 2) — red, solid, bold
4. **Cross-page note**: `st.info("Inflation curve used for the
   real→nominal conversion is configured in Step 2b → Inflation (CPI)
   Curve. Default = Excel `Curves and D&T!r10`...")`

### Step 2b new expander — "Inflation (CPI) Curve"

- Source radio: `'default'` / `'upload'`
- If `'default'`: read-only table + bar chart of
  `_DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR` + 2.0% steady-state caption
- If `'upload'`: inline `st.data_editor` (year, rate_pct) OR CSV upload
- Steady-state rate input (default 2.0%) → `fin['cpi_steady_state_rate']`
- Preview chart: bar (annual rates) + line (cumulative factor since 2024)
- Save payload addition: 3 new keys (`cpi_curve_source`,
  `cpi_curve_by_calendar_year`, `cpi_steady_state_rate`)

## Wizard state additions

**`DEFAULT_WIZARD_STATE['setup']`** — add 2 keys:

```python
'merchant_price_curve_terms': 'nominal',           # 'nominal' | 'real'
'merchant_price_curve_base_year': 2024,            # int, used only if terms == 'real'
```

**`DEFAULT_WIZARD_STATE['financial']`** — add 3 keys:

```python
'cpi_curve_source': 'default',                     # 'default' | 'upload'
'cpi_curve_by_calendar_year': None,                # dict[int, float (decimal)] when uploaded
'cpi_steady_state_rate': None,                     # float (decimal) when customised
```

All additive — no renames, no removals.

## Tests

### New unit tests in `tests/test_project_irr.py`

1. `test_apply_inflation_identity_at_base_year`
2. `test_apply_inflation_compounds_forward` — `{2025: 0.05, 2026: 0.04}`,
   base=2024 ⇒ nominal `{2024: 100, 2025: 105, 2026: 109.2}`
3. `test_apply_inflation_uses_steady_state_outside_curve`

### New / extended tests in `tests/test_wizard_state_path.py`

1. `test_default_curves_produce_d13_audit_invariant`
2. `test_upload_nominal_curve_passes_through_to_engine`
3. `test_upload_real_curve_with_default_inflation_matches_manual_calc`
4. `test_upload_curve_with_partial_coverage_rejected`

## Decisions log entry

Will be filed as the next-available A-number when v2 lands. Key claim:
"transformation replicates Excel `Curves and D&T!r30 = real × (1 + cpi)^(year
− base)` — no invented calibration factor (G5 honoured). Engine core
unchanged; all transformation lives in the adapter."

## Verification

1. Pytest baseline ⇒ all tests pass with PIRR identical to v1.
2. D13 invariant — both defaults: Combined 8.84% / S+B 9.00% / Gas 13.07% /
   CAPEX £101.4m.
3. **Round-trip — real-terms re-derivation**: create a CSV by dividing each
   value in `_DEFAULT_MERCHANT_PRICES_MONTHLY` by the cumulative CPI factor
   from 2024. Upload as real-terms, base_year=2024, CPI default. Engine
   reconverges to D13 audit within ±0.01 pp.
4. Pass-through — nominal: upload `_DEFAULT_MERCHANT_PRICES_MONTHLY`
   verbatim, terms=`'nominal'`. D13 reproduces identically.
5. Coverage rejection: upload only 2040-2055 ⇒ error, no state written.
6. CPI customisation: 5% flat → PIRR shifts visibly upward.

## Risks / gotchas

1. **Base-year semantics**. `_build_cpi_factor_lookup` anchors at
   `cod_year`; `_apply_inflation_to_real_curve` anchors at user's
   `base_year`. Don't reuse the wrong helper.
2. **2024 CPI = 0.0 trap**. Default curve has `2024: 0.000`. Help text:
   *"base year = the year these real prices represent (1 real £ = 1
   nominal £ at this year)"*.
3. **Cross-page state coupling**. Step 1 preview falls back to
   `_DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR` if Step 2b never visited.
4. **D13 fixture drift**. `tests/fixtures/d13_inputs.py` bypasses the
   adapter. Don't route it through.
5. **Coverage validator depends on financial state**. Render required
   range explicitly in error message.
6. **Step 2b save payload sync**. Add 3 new keys to the existing flat
   payload dict.
7. **CSV format**: user supplies `rate_pct` (display %), engine stores
   decimal. Convert at parse time.
