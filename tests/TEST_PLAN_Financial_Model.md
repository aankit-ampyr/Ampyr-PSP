# Test Plan — Financial Model Module 1 (Ungeared Project IRR)

**Version**: A1 (Core FCFF Chain)
**Date**: 2026-03-17
**Module Under Test**: `src/financial_model.py`, `pages/Step7_Financial.py`, `src/financial_config.py`, `src/wizard_state.py`
**Excel Reference**: `Financial Model/Off-Grid Solution v8.xlsm` (Burton Top-3.8h, Column J)

---

## 1. Reference Case Definition

All formula cross-checks use the **Burton Top-3.8h** reference case (Column J in Excel):

| Parameter | Value | Unit |
|-----------|-------|------|
| Solar Capacity | 82 | MWp |
| Generation Case | P90 | — |
| P90 Yield | 895 | MWh/MWp/Yr |
| Degradation | 0.3 | %/yr (from year 2) |
| COD | 2027-07-01 | Date |
| Project Life | 35 | Years |
| Construction Start | 2026-01-01 | Date |
| Construction Months | 18 | Months |
| BESS Capacity | 62.5 MW x 4hr = 250 MWh | — |
| BESS Operating Life | 15 | Years |
| BESS Degradation | 2.5 | %/yr |
| BESS Floor Price | 40 | GBP/MW/yr |
| BESS Floor Tenor | 10 | Years |
| CM T-1 Value | 20 | GBPk/MW/Yr |
| CM T-1 De-rating | 27.15 | % |
| CM T-1 Tenor | 1 | Year |
| EPC Cost | 400 | GBP/kWp |
| Contingency | 1 | % |
| PV O&M | 5.48 | GBP/kWp/Yr |
| Insurance | 2.02 | GBP/kWp/Yr |
| Corrective Maint | 3.2 | GBP/kWp/Yr |
| BESS O&M | 7.06 | GBPk/MW/Yr |
| Corp Tax (low) | 19 | % |
| Corp Tax (high) | 25 | % |
| Tax Threshold | 250 | GBPk |
| Discount Rate | 8 | % |
| PPA Price (default) | 50 | GBP/MWh |
| CPI Indexation | 2.5 | %/yr |

---

## 2. Test Categories

### 2.1 Unit Conversion Tests

These verify that the Python engine handles currency/unit conversions correctly.

| # | Test | Formula | Expected | How to Verify |
|---|------|---------|----------|---------------|
| UC-1 | Solar OPEX monthly (GBPk) | `(5.48 + 1.5 + 0.5 + 0 + 1.0 + 1.0 + 0 + 2.02 + 0 + 3.2 + 1.5) * 82 / 12` | **109.37 GBPk/month** (year 1, no escalation) | Run model, check `results.solar_opex` at first ops month. Should be **-109.37** (negative = cost) |
| UC-2 | BESS OPEX monthly (GBPk) | `7.06 * 62.5 / 12` | **36.77 GBPk/month** (year 1) | Check `results.bess_opex` at first ops month. Should be **-36.77** |
| UC-3 | Total CAPEX (GBPk) | Sum of 21 items: `(400+30+15+0+5+0+0+2+0+2+0+0+0+0+80+0+3+0+0+0+0) * 82 * 1.01` | `537 * 82 * 1.01 = 44,474.34 GBPk` | Check `results.total_capex` = **44,474 GBPk** |
| UC-4 | CAPEX per month | `44,474.34 / 18` (construction months) | **2,470.8 GBPk/month** | Check `results.capex` during any construction month |
| UC-5 | Annual solar generation (MWh) | `82 * 895` | **73,390 MWh/yr** (year 1) | Calculate revenue / price: `solar_rev * 1000 / 50` for year 1 total |
| UC-6 | BESS floor monthly (GBPk) | `40 * 62.5 / 12 / 1000` | **0.2083 GBPk** | Check `results.bess_revenue` first ops month |
| UC-7 | CM T-1 monthly (GBPk) | `20 * 0.2715 * 62.5 / 12` | **28.28 GBPk** | Check `results.bess_revenue` first ops month (includes floor + CM) |
| UC-8 | Land lease monthly (GBPk) | `800 * 200 / 12 / 1000` | **13.33 GBPk** | Enable fixed_lease_switch=1, check increase in solar_opex |

**Cross-check with Excel**: Open Excel Column J. Compare:
- `Solar&BESS Inputs` cell values match Python defaults
- `FS` row 44 (Solar Expenses Total) for first ops month ≈ UC-1
- `FS` row 56 (BESS Expenses Total) for first ops month ≈ UC-2
- `Construction` row 97 (Total CAPEX) ≈ UC-3

---

### 2.2 Timeline Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| TL-1 | Total months | `_months_between(2024-07-01, 2027-07-01) + 35*12 = 36 + 420 = 456` | `len(results.dates) == 456` |
| TL-2 | Construction months | 18 months: Jan 2026 – Jun 2027 | `sum(is_construction) == 18` |
| TL-3 | Operations months | 420 months: Jul 2027 – Jun 2062 | `sum(is_operations) == 420` |
| TL-4 | No overlap | Construction and operations never True simultaneously | `assert not any(is_construction & is_operations)` |
| TL-5 | Pre-construction gap | Jul 2024 – Dec 2025 (18 months) have both masks False | Check months 0-17 are neither construction nor ops |
| TL-6 | Dates are 1st of month | Every date in `results.dates` has `.day == 1` | Loop and assert |
| TL-7 | Last date | `2062-06-01` | `results.dates[-1] == date(2062, 6, 1)` |

**Cross-check with Excel**: `Timing` sheet — verify model start, COD, end date match.

---

### 2.3 Revenue Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| RV-1 | Year 1 solar revenue (equal seasonality) | `82 * 895 * (1/12) * 50 / 1000 = 305.85 GBPk/month` | Default seasonality = 1/12. Check first 12 ops months |
| RV-2 | Degradation year 2 | Year 2: `305.85 * (1 - 0.003) = 304.93 GBPk/month` | Check month 13-24 of operations |
| RV-3 | Degradation year 10 | Factor: `1 - 0.003*9 = 0.973`. Revenue: `305.85 * 0.973 = 297.59` | Check month 109-120 |
| RV-4 | Degradation year 35 | Factor: `1 - 0.003*34 = 0.898`. Revenue: `305.85 * 0.898 = 274.65` | Check last 12 ops months |
| RV-5 | Seasonality | With summer-weighted profile (e.g. Jun=0.14, Dec=0.04), Jun revenue should be 3.5× Dec | Set custom seasonality, compare months |
| RV-6 | Price indexation year 5 | Factor: `1.025^4 = 1.1038`. Price: `50 * 1.1038 = 55.19 GBP/MWh` | Check ops year 5 (month 49-60) revenue |
| RV-7 | BESS floor revenue stops at tenor | Floor tenor=10yr. Month 121 (year 11) should have zero floor revenue | Set bess_floor_tenor=10, check |
| RV-8 | BESS floor with degradation | Year 5: BESS MW = `62.5 * (1 - 0.025*4) = 56.25`. Floor = `40 * 56.25 / 12 / 1000 = 0.1875` | Check bess_rev at ops year 5 |
| RV-9 | CM T-1 stops at tenor | CM tenor=1yr. Month 13 (year 2) should have zero CM revenue | Check bess_rev month 13 |
| RV-10 | REGO revenue | Year 1: `73390/12 * 5 / 1000 = 30.58 GBPk/month` | Check solar_rev includes REGO component |
| RV-11 | REGO stops at tenor | tenor=15yr. Month 181 (year 16) should have no REGO | Compare solar_rev month 180 vs 181 |
| RV-12 | BESS switch=0 | All BESS revenue = 0, REGO still works | Set bess_switch=0, verify |
| RV-13 | Outage month | Set outage=1, month=7, days=14. July revenue reduced by `14/31 = 45.2%` | Check July ops months |
| RV-14 | Revenue = 0 during construction | All revenue arrays = 0 during construction months | Verify |
| RV-15 | Revenue = 0 before construction | Pre-construction months have zero revenue | Verify |

**Cross-check with Excel**:
- `FS` row 17 (Total Solar Revenue) — compare first ops year total
- `FS` row 24 (Total BESS Revenue) — compare first ops year total
- `FS` row 27 (Total Revenue) — compare annual totals for years 1, 5, 10, 15, 20, 35
- `Equity` row 150 — should match FS row 27

---

### 2.4 OPEX Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| OX-1 | Year 1 total OPEX | Solar: 109.37 + BESS: 36.77 = **146.14 GBPk/month** | `abs(results.opex[first_ops])` ≈ 146.14 |
| OX-2 | OPEX escalation year 5 | `146.14 * 1.025^4 = 161.31 GBPk/month` | Check month 49-60 |
| OX-3 | BESS OPEX stops at operating life | Year 16 (ops_year=15): BESS OPEX = 0 | Check month 181+ |
| OX-4 | OPEX sign convention | All OPEX values negative (costs) | `assert all(results.opex <= 0)` |
| OX-5 | OPEX = 0 during construction | No OPEX during construction phase | Verify |
| OX-6 | Variable OPEX | Set opex_social_cost=2.0. Extra: `73390/12 * 2 / 1000 = 12.23 GBPk/month` | Compare total OPEX with/without |
| OX-7 | Fixed land lease | Enable, 200 acres @ 800 GBP/acre/yr. Monthly: `200*800/12/1000 = 13.33 GBPk` | Check increase in solar_opex |
| OX-8 | Revenue-dependent lease | Enable, 5% share. If revenue = 305.85, lease = `305.85 * 0.05 = 15.29 GBPk` | Check increase in solar_opex |
| OX-9 | Rev-dep lease year 11+ switch | Year 1-10: 5%, year 11+: 7.5%. Lease should increase at year 11 | Compare month 120 vs 121 |
| OX-10 | All OPEX items at zero | Set all OPEX rates to 0. Total OPEX = 0 | Verify |

**Cross-check with Excel**:
- `FS` row 44 (Solar Expenses) — compare year 1
- `FS` row 56 (BESS Expenses) — compare year 1
- `FS` row 59 (Total Expenses) — compare annual totals
- `Equity` row 151 — should match FS row 59

---

### 2.5 CAPEX Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| CX-1 | Total CAPEX with defaults | 44,474 GBPk (see UC-3) | `results.total_capex` |
| CX-2 | CAPEX phasing | Evenly spread: `44,474 / 18 = 2,470.8 GBPk/month` | Check each construction month |
| CX-3 | CAPEX sign | All CAPEX values negative during construction | `assert all(results.capex[is_construction] < 0)` |
| CX-4 | No CAPEX during operations | `results.capex[is_operations]` all zero | Verify |
| CX-5 | Contingency applied | Set contingency=5%. CAPEX should be `537 * 82 * 1.05 = 46,230.9` | Compare |
| CX-6 | Contingency = 0 | `537 * 82 = 44,034 GBPk` | Compare |
| CX-7 | Construction rent | Enable construction_rent_sw, 200 acres @ 500/acre/yr. Added: `500*200*18/12/1000 = 150 GBPk` | Total CAPEX increases by 150 |
| CX-8 | BESS CAPEX line | Set capex_bess=100. Total per kWp changes from 537 to 557. Total: `557*82*1.01 = 46,118.14` | Check |
| CX-9 | Zero CAPEX | Set all CAPEX items to 0. Total CAPEX = 0 | IRR should be very high |

**Cross-check with Excel**:
- `Construction` row 97 (Total CAPEX) — compare with CX-1
- `FS` rows 69-89 (CAPEX items) — compare phasing pattern
- `FS` row 93 (Total Construction Costs) — compare
- `Equity` row 153 — should match sum of FS rows 69:89

---

### 2.6 Depreciation Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| DP-1 | Straight-line monthly | `44,474 / (35*12) = 105.89 GBPk/month` | `results.depreciation[first_ops]` ≈ 105.89 |
| DP-2 | Constant over project life | All ops months have same depreciation | `np.allclose(results.depreciation[is_operations], 105.89)` |
| DP-3 | Total depreciation = CAPEX | `sum(depreciation) ≈ total_capex` | Within 0.01 GBPk |
| DP-4 | No depreciation during construction | `results.depreciation[is_construction]` all zero | Verify |
| DP-5 | No depreciation pre-construction | `results.depreciation[:18]` all zero | Verify |

**Known simplification**: Excel uses 3 depreciation accounts with different methods. Python A1 uses single straight-line. This will be refined in A3/A4. For now, verify the total is correct even if the timing differs from Excel.

**Cross-check with Excel**:
- `D&T` row 111 + 130 + 149 (3 account totals) — sum should ≈ match Python total depreciation

---

### 2.7 Tax Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| TX-1 | Tax paid only in taxation month | Only month=12 (December) has non-zero tax | Check all other months are 0 |
| TX-2 | Tax sign convention | All tax values ≤ 0 (payment out) | `assert all(results.tax <= 0)` |
| TX-3 | Year 1 taxable income | EBITDA - Depreciation = `(305.85*12 - 146.14*12) - 105.89*12 = 1916.52 - 1753.68 - 1270.68 = -1107.84` | If negative → no tax, loss generated |
| TX-4 | Loss carry-forward | Early years generate losses (high depreciation). Tax should be zero until cumulative income exceeds cumulative losses | Track loss_pool manually |
| TX-5 | Two-tier rate below threshold | Taxable = 200 GBPk. Tax = `200 * 0.19 = 38 GBPk` | Manual calc or isolated test |
| TX-6 | Two-tier rate above threshold | Taxable = 400 GBPk. Tax = `250*0.19 + 150*0.25 = 47.5 + 37.5 = 85 GBPk` | Manual calc or isolated test |
| TX-7 | Loss utilisation | Year with 500 income, 200 loss pool → taxable = 300, loss_pool = 0 | Trace through debugger |
| TX-8 | Partial loss utilisation | Year with 100 income, 200 loss pool → taxable = 0, loss_pool = 100 | Trace |
| TX-9 | No tax before operations | Construction/pre-construction months: tax = 0 | Verify |
| TX-10 | Change taxation month | Set taxation_month=6. Tax should now appear only in June | Verify |
| TX-11 | Zero tax rates | Set both rates to 0%. All tax = 0 | Verify |

**Cross-check with Excel**:
- `D&T` row 265 (Ungeared Tax Paid) — compare annual totals
- `D&T` rows 250-253 (Loss carry-forward) — compare pool balances
- `D&T` row 260 (Tax Payable) — compare
- `Equity` row 155 — should match D&T row 265
- `Curves and D&T` E105-E108 — verify rates match Python inputs

---

### 2.8 NWC (Net Working Capital) Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| NW-1 | First ops month NWC change | Debtors = `305.85*12*45/365 = 452.2`. Creditors = `146.14*12*30/365 = 144.0`. NWC = 308.2. Change = -308.2 | Check first ops month |
| NW-2 | Steady-state NWC | After first month, if revenue/opex are constant, NWC change ≈ 0 | Check months 2-12 of operations |
| NW-3 | NWC with zero WC days | Set debtors=0, creditors=0. All NWC changes = 0 | Verify |
| NW-4 | NWC = 0 during construction | No NWC during construction | Verify |
| NW-5 | NWC sign convention | First month negative (cash tied up). When revenue decreases (degradation), small positive releases | Check trend |

**Cross-check with Excel**:
- `FS` row 61 (NWC Adjustments) — compare first ops year
- `Equity` row 152 — should match FS row 61

---

### 2.9 FCFF Assembly Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| FF-1 | FCFF = Revenue + OPEX + NWC + CAPEX + Tax | For each month, verify the identity holds | `np.allclose(results.fcff, results.revenue + results.opex + results.nwc + results.capex + results.tax)` |
| FF-2 | FCFF during construction | FCFF = CAPEX only (all others zero) | Check construction months |
| FF-3 | FCFF sign during construction | Negative (cash outflow for CAPEX) | Verify |
| FF-4 | FCFF sign during steady operations | Positive (revenue > opex + tax) | Verify after initial NWC |
| FF-5 | Cumulative FCFF shape | Starts negative (CAPEX), grows through operations, crosses zero at payback | Visual check on chart |
| FF-6 | Payback month | `results.payback_month` should be the first month where cumulative FCFF > 0 | Verify manually |

**Cross-check with Excel**:
- `Equity` row 156 (FCFF Total) — compare monthly values for years 1, 5, 10, 20, 35
- `Equity` row 156 should = sum of rows 150:155 for each month

---

### 2.10 XIRR / XNPV Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| XI-1 | Known answer test | Cashflows: [-1000, 300, 300, 300, 300] at annual intervals. XIRR ≈ 7.71% | Standalone call to `calc_xirr()` |
| XI-2 | Zero NPV at IRR | `calc_xnpv(dates, fcff, project_irr) ≈ 0` | Verify within ±1 GBPk |
| XI-3 | NPV at discount rate | `results.project_npv` matches `calc_xnpv(dates, fcff, 0.08)` | Compare |
| XI-4 | Higher PPA → higher IRR | PPA=60 GBP/MWh should give IRR > PPA=50 | Compare two runs |
| XI-5 | Lower CAPEX → higher IRR | EPC=350 vs EPC=400: first should have higher IRR | Compare |
| XI-6 | Longer project life → higher IRR | 35yr vs 20yr: 35yr should be higher (more revenue) | Compare |
| XI-7 | No convergence returns NaN | All-zero cashflows → `np.isnan(results.project_irr)` | Verify |
| XI-8 | Negative IRR | Very high CAPEX, low revenue → IRR < 0 | Set capex_epc=800, verify IRR negative |
| XI-9 | XIRR matches Excel | Run with reference case inputs. Compare `results.project_irr` with Excel `Equity!G162` | **Critical**: should be within ±0.5% initially, ±0.01% after full replication |

**Cross-check with Excel**:
- `Equity` G162 (XIRR of ungeared FCFF) — **primary validation target**
- Note: A1 uses simplified depreciation and default PPA price, so exact match is not expected yet. Document the delta.

---

### 2.11 Sensitivity / Edge Case Tests

| # | Test | Expected | How to Verify |
|---|------|----------|---------------|
| EC-1 | Zero solar capacity | CAPEX=0, Revenue=0, IRR=NaN | Verify no crash |
| EC-2 | No BESS | bess_switch=0. All BESS revenue/OPEX = 0 | Verify |
| EC-3 | 1-year project life | 12 ops months. Model should still compute IRR | Verify |
| EC-4 | 50-year project life | 600 ops months. Should complete without errors | Verify < 1 second |
| EC-5 | Extreme PPA price | PPA=500 GBP/MWh. IRR should be very high | Verify positive |
| EC-6 | All costs zero | CAPEX=0, OPEX=0, Tax=0. FCFF = Revenue. IRR should be very high | Verify |
| EC-7 | All revenue zero | PPA=0, BESS off. FCFF = -CAPEX - OPEX. IRR = NaN or very negative | Verify |
| EC-8 | Construction = 1 month | All CAPEX in single month | Verify |
| EC-9 | COD = model_start | Zero pre-ops months | Verify no crash |
| EC-10 | Seasonality sums to != 1.0 | Model should still run (proportional). Document behavior | Verify |
| EC-11 | 100% degradation | degradation=3.0% for 35yr = 102% → factor clamped to 0 | Revenue should reach 0 by year 34 |

---

## 3. Integration Tests (Step 7 UI)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| UI-1 | Page loads | Navigate to Step 7 in Streamlit | All 11 sections render without errors |
| UI-2 | Default values | Open page fresh | All inputs show Burton Top-3.8h reference values |
| UI-3 | Save inputs | Fill form, click "Save Financial Inputs" | Success message. Wizard state updated |
| UI-4 | Run analysis without save | Click "Run Financial Analysis" without saving | Warning message |
| UI-5 | Run analysis after save | Save, then Run | Summary metrics, charts, and data table appear |
| UI-6 | IRR metric displayed | Run analysis | IRR value shown in metric card (e.g. "4.52%") |
| UI-7 | Annual chart renders | Run analysis | Stacked bar chart with Revenue, OPEX, CAPEX, Tax |
| UI-8 | Cumulative FCFF chart | Run analysis | Line chart showing negative-to-positive crossover |
| UI-9 | Data table | Expand "Detailed Annual Data" | DataFrame with Year, Revenue, OPEX, CAPEX, Tax, FCFF |
| UI-10 | CSV download | Click "Download Annual Data" | CSV file downloads with correct data |
| UI-11 | Step indicator shows 7 steps | Navigate any Step page | All pages show Steps 1-7 |
| UI-12 | Change input and re-run | Change EPC from 400 to 350, Save, Run | IRR should increase |
| UI-13 | Seasonality sum warning | Set seasonality values summing to 0.8 | Warning displayed |
| UI-14 | BESS Energy metric | Set 62.5 MW x 4hr | Metric shows "250 MWh" |
| UI-15 | CAPEX total live update | Change any CAPEX item | Total CAPEX metric updates |
| UI-16 | Solar OPEX total | All 11 items visible | Total Solar OPEX metric correct |
| UI-17 | Excel export section | No xlwings installed | Info message about Windows-only |
| UI-18 | Prerequisite warning | No Step 5 data | Warning about completing Step 5 |

---

## 4. Cross-Check Protocol (Python vs Excel)

This is the most critical test. Run both the Python engine and the Excel model with identical inputs and compare outputs.

### 4.1 Setup

1. Open `Financial Model/Off-Grid Solution v8.xlsm`
2. Select Case 1 (Column J = Burton Top-3.8h)
3. Note the current values in Column J for all input rows
4. Run the Python model with matching inputs

### 4.2 Comparison Table

For each row below, record the Python value, Excel value, and delta:

| Component | Python Source | Excel Source | Year 1 | Year 5 | Year 10 | Year 20 | Year 35 |
|-----------|--------------|--------------|--------|--------|---------|---------|---------|
| Solar Revenue | `results.solar_revenue` sum by year | `FS` row 17 annual sum | | | | | |
| BESS Revenue | `results.bess_revenue` sum by year | `FS` row 24 annual sum | | | | | |
| Total Revenue | `results.revenue` sum by year | `FS` row 27 / `Equity` row 150 | | | | | |
| Solar OPEX | `results.solar_opex` sum by year | `FS` row 44 annual sum | | | | | |
| BESS OPEX | `results.bess_opex` sum by year | `FS` row 56 annual sum | | | | | |
| Total OPEX | `results.opex` sum by year | `FS` row 59 / `Equity` row 151 | | | | | |
| NWC | `results.nwc` sum by year | `FS` row 61 / `Equity` row 152 | | | | | |
| CAPEX | `results.capex` sum by year | `FS` row 93 / `Equity` row 153 | | | | | |
| Depreciation | `results.depreciation` sum by year | `D&T` rows 111+130+149 sum | | | | | |
| Tax | `results.tax` sum by year | `D&T` row 265 / `Equity` row 155 | | | | | |
| FCFF | `results.fcff` sum by year | `Equity` row 156 annual sum | | | | | |
| **Project IRR** | `results.project_irr` | `Equity` G162 | — | — | — | — | — |

### 4.3 Acceptance Criteria

| Metric | A1 Tolerance | After Full Replication |
|--------|-------------|----------------------|
| Revenue (annual) | ±10% | ±1% |
| OPEX (annual) | ±10% | ±1% |
| CAPEX (total) | ±2% | ±0.1% |
| FCFF (annual) | ±15% | ±1% |
| Project IRR | ±2.0 pp | ±0.01 pp |

**Why A1 tolerances are wide**: The A1 engine uses a fixed PPA price (not merchant curves), single-account depreciation (not 3 accounts), and simplified indexation. These simplifications are addressed in A2-A4.

### 4.4 Known A1 Simplifications (Expected Deltas)

| Area | Python A1 | Excel | Impact Direction |
|------|-----------|-------|-----------------|
| PPA Price | Fixed `ppa_price_gbp_mwh` default | Merchant curve from Baringa/Aurora | Revenue will differ |
| Depreciation | Single straight-line over project life | 3 accounts with different methods | Tax timing differs |
| BESS Merchant Revenue | Floor + CM only | Full merchant curve with scenarios | Revenue lower in Python |
| OPEX Escalation | Uniform CPI on all items | Individual escalation per item | Small OPEX difference |
| Embedded Benefits | Not implemented in A1 | 12 monthly GBP/MWh values | Missing revenue stream |
| MRA | Not implemented in A1 | Maintenance reserve accounts | Missing cash flow item |
| DSRA | Not implemented | Debt service reserve | Missing (but N/A for ungeared) |

---

## 5. Performance Tests

| # | Test | Expected |
|---|------|----------|
| PF-1 | Single model run | < 0.5 seconds for 35yr (456 months) |
| PF-2 | 50 sequential runs | < 25 seconds total |
| PF-3 | Memory usage | < 50 MB per model run |
| PF-4 | 50-year project | < 1 second |

---

## 6. Regression Test Script

Run this Python script to execute all automated tests:

```python
"""
Quick regression test for financial_model.py
Run: python -m pytest tests/test_financial_regression.py -v
Or:  python tests/test_financial_regression.py
"""
from datetime import date
import numpy as np
from src.financial_model import (
    FinancialInputs, run_financial_model, calc_xirr, calc_xnpv
)

def test_reference_case():
    """Run with defaults (Burton Top-3.8h) and verify key outputs."""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)

    # Timeline
    assert len(results.dates) == 456, f"Expected 456 months, got {len(results.dates)}"
    assert results.dates[0] == date(2024, 7, 1)
    assert results.dates[-1] == date(2062, 6, 1)

    # CAPEX
    assert abs(results.total_capex - 44474) < 10, f"CAPEX {results.total_capex}"

    # Revenue positive during operations
    assert results.total_revenue_lifetime > 0

    # OPEX positive (stored as abs)
    assert results.total_opex_lifetime > 0

    # IRR is a reasonable number
    assert not np.isnan(results.project_irr)
    assert -0.5 < results.project_irr < 0.5, f"IRR {results.project_irr} out of range"

    # FCFF identity
    expected_fcff = results.revenue + results.opex + results.nwc + results.capex + results.tax
    assert np.allclose(results.fcff, expected_fcff, atol=0.01)

    # Payback exists
    assert results.payback_month > 0

    print(f"PASS: IRR={results.project_irr*100:.2f}%, "
          f"NPV={results.project_npv:.0f} GBPk, "
          f"CAPEX={results.total_capex:.0f} GBPk")


def test_xirr_known_answer():
    """XIRR with known cashflows."""
    dates = np.array([date(2025, 1, 1), date(2026, 1, 1),
                      date(2027, 1, 1), date(2028, 1, 1), date(2029, 1, 1)])
    cfs = np.array([-1000, 300, 300, 300, 300])
    irr = calc_xirr(dates, cfs)
    assert abs(irr - 0.0771) < 0.005, f"Expected ~7.71%, got {irr*100:.2f}%"
    print(f"PASS: XIRR known answer = {irr*100:.2f}%")


def test_xnpv_at_irr_is_zero():
    """NPV at IRR should be approximately zero."""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    npv_at_irr = calc_xnpv(results.dates, results.fcff, results.project_irr)
    assert abs(npv_at_irr) < 1.0, f"NPV at IRR should be ~0, got {npv_at_irr:.2f}"
    print(f"PASS: NPV at IRR = {npv_at_irr:.4f} GBPk")


def test_no_bess():
    """Model runs without BESS."""
    inputs = FinancialInputs(bess_switch=0)
    results = run_financial_model(inputs)
    assert all(results.bess_revenue == 0)
    assert all(results.bess_opex == 0)
    assert not np.isnan(results.project_irr)
    print(f"PASS: No BESS, IRR={results.project_irr*100:.2f}%")


def test_sensitivity_ppa_price():
    """Higher PPA → higher IRR."""
    r1 = run_financial_model(FinancialInputs(ppa_price_gbp_mwh=40))
    r2 = run_financial_model(FinancialInputs(ppa_price_gbp_mwh=60))
    assert r2.project_irr > r1.project_irr, "Higher PPA should give higher IRR"
    print(f"PASS: PPA 40→{r1.project_irr*100:.2f}%, PPA 60→{r2.project_irr*100:.2f}%")


def test_sensitivity_capex():
    """Lower CAPEX → higher IRR."""
    r1 = run_financial_model(FinancialInputs(capex_epc=400))
    r2 = run_financial_model(FinancialInputs(capex_epc=350))
    assert r2.project_irr > r1.project_irr, "Lower EPC should give higher IRR"
    print(f"PASS: EPC 400→{r1.project_irr*100:.2f}%, EPC 350→{r2.project_irr*100:.2f}%")


def test_edge_zero_capacity():
    """Zero solar capacity should not crash."""
    inputs = FinancialInputs(solar_capacity_mwp=0, bess_switch=0)
    results = run_financial_model(inputs)
    assert results.total_capex == 0
    print("PASS: Zero capacity runs without error")


def test_performance():
    """Single run should be fast."""
    import time
    start = time.time()
    for _ in range(10):
        run_financial_model(FinancialInputs())
    elapsed = time.time() - start
    per_run = elapsed / 10
    assert per_run < 0.5, f"Too slow: {per_run:.3f}s per run"
    print(f"PASS: {per_run*1000:.1f}ms per run")


if __name__ == "__main__":
    tests = [
        test_reference_case,
        test_xirr_known_answer,
        test_xnpv_at_irr_is_zero,
        test_no_bess,
        test_sensitivity_ppa_price,
        test_sensitivity_capex,
        test_edge_zero_capacity,
        test_performance,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
```

---

## 7. Test Execution Checklist

| Phase | Owner | Status |
|-------|-------|--------|
| Run regression script (`test_financial_regression.py`) | Tester | [ ] |
| Verify all UC- (unit conversion) tests manually | Tester | [ ] |
| Verify all TL- (timeline) tests | Tester | [ ] |
| Complete Excel cross-check table (Section 4.2) | Tester + Ankit | [ ] |
| Run all UI- tests in Streamlit | Tester | [ ] |
| Document deltas between Python and Excel | Tester | [ ] |
| Run edge case tests (EC-1 through EC-11) | Tester | [ ] |
| Run performance tests | Tester | [ ] |
| Sign-off on A1 tolerances | Ankit | [ ] |

---

## 8. Files Changed in This Release

| File | Action | Lines |
|------|--------|-------|
| `src/financial_model.py` | **Created** | ~600 |
| `src/financial_config.py` | **Created** | ~460 |
| `pages/Step7_Financial.py` | **Created** | ~1300 |
| `src/wizard_state.py` | **Modified** | +140 (financial section expanded) |
| `pages/Step1_Setup.py` | **Modified** | Step indicator (5→7 steps) |
| `pages/Step2_Rules.py` | **Modified** | Step indicator (5→7 steps) |
| `pages/Step3_Sizing.py` | **Modified** | Step indicator (5→7 steps) |
| `pages/Step4_Results.py` | **Modified** | Step indicator (5→7 steps) |
| `pages/Step5_MultiYear.py` | **Modified** | Step indicator (5→7 steps) |
| `_dump_financial_cells.py` | **Created** | ~130 (utility) |
