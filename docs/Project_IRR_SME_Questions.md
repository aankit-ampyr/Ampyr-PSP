# Project IRR Integration — SME Review Questions

**Audience:** Project finance / renewables financial-modelling SME.
**What we're asking for:** A sanity check on our scoping, assumptions, and simplifications before we wire a Project IRR (PIRR) calculator into a Python sizing tool.
**Time investment:** ~45 minutes if you read sections 1–2 and skim the rest; ~90 minutes for a full pass.
**How to respond:** Free-text against each numbered question is fine. Please flag any "this is wrong" with high confidence vs "this is a judgement call".

---

## 1. Context

### 1.1 What we're building

We have a Python web app (the **Project Sizing Platform / PSP**) that lets a user configure a dispatch strategy for a solar + BESS + DG hybrid, then sweeps across battery sizes (and optionally solar sizes / DG sizes) running an 8760-hour simulation per configuration. Today the sweep produces only **operational metrics** per config — delivery %, green %, wastage %, BESS cycles, fuel litres, etc.

We want to add a **Project IRR column** to that sweep so the user can rank configurations on financial return alongside the operational metrics.

### 1.2 The Excel we're porting from

`Off-Grid Solution v8.xlsm` — a 38-sheet, ~12 MB project-finance model built for the **Burton Top** asset (82 MWp solar + 62.5 MW × 4h BESS + ~28 MW gas peaker, supplying a 25 MW base load to a UK data centre under PPA). The headline PIRR on `Consol Cash Flows!B9` is **9.23%**.

We're porting **only the ungeared FCFF / Project IRR pathway**. Everything debt-, equity-, and IC-related is out of scope (Debt sheet, Equity sheet, Drawdown, Macro, IC, Analysis, Results, Returns, FS, sensitivity tables, all VBA macros). Roughly half the workbook drops out.

### 1.3 What we ask the SME

We have made a series of scoping decisions. We want you to tell us where we are wrong, where we are oversimplifying in ways that will distort the ranking, and what we are missing.

---

## 2. The big-picture questions (most important)

These are the ones we most need a sanity check on.

**Q2.1** — *Convention of "Project IRR".* We are defining PIRR as the **ungeared, post-tax IRR on Free Cash Flow to the Firm (FCFF)** — i.e. revenue − opex − tax − capex − ΔWC, with no debt service and no equity injections, where tax is computed as if 100 % equity-funded (no interest tax shield). This matches `Consol Cash Flows!B9` in the Excel. **Is this what Ampyr internally means by "Project IRR"?** Some sponsors mean post-tax post-debt, some mean pre-tax, some mean ATCF on a different basis. We want to confirm we are calculating the same number you do.

**Q2.2** — *Is PIRR even the right ranking metric for a sizing sweep?* When the user sweeps BESS MWh from 100 to 500, we expect:
- BESS capex rises linearly with MWh
- Energy delivered to load rises with diminishing returns
- BESS opex (LTSA, augmentation) rises with cycles
- **Therefore PIRR should have a clear maximum at the "right" BESS size.**

Is that what you would expect to see in practice, or does PIRR typically decline monotonically as BESS gets bigger (i.e. smallest BESS is always best on PIRR)? If the latter, **PIRR is the wrong sizing metric** — we should rank on NPV-at-WACC or some constrained-optimisation objective instead. Your view?

**Q2.3** — *Sizing decisions in real life.* When you actually size a BESS for an asset like Burton Top, what financial metric do you optimise on? PIRR? Levered EIRR? MOIC at exit? NPV at WACC? Some weighted blend? We want to know whether putting "PIRR" on the screen will align with how Investment Committee actually thinks about sizing, or whether it will mislead.

---

## 3. Revenue stack — which streams apply?

The Excel has ~10 revenue streams. We default to porting all of them. Please flag any that **do not actually apply** to a UK off-grid solar + BESS + gas hybrid feeding a data centre under PPA, and any we are **missing**.

| # | Stream | Excel value (active Burton Top case) | Our intent | SME — please confirm |
|---|---|---|---|---|
| 1 | **Solar PPA revenue** (energy delivered to data centre × tariff) | £170/MWh, 10-year PPA, 0 % indexation | Include | Q3.1 — Is the PPA energy-based (£/MWh delivered) or capacity-based (£/MW availability), and what happens during solar/BESS outages? Does the data centre still pay if we cannot deliver? |
| 2 | **Solar merchant** (energy exported / wasted) | Priced against Baringa / Aurora / Blend curves, 5 % discount | Include | Q3.2 — On an "off-grid" hybrid, can wasted solar actually be sold to merchant, or is it curtailed and earns nothing? The Excel name "Off-Grid Solution" implies the latter, but the model includes a non-zero merchant revenue. Which is correct for Burton Top? |
| 3 | **REGO** | £2.5/MWh, 35-year tenor, switch on | Include | Q3.3 — Is REGO revenue genuine recurring revenue or a one-off uplift on the PPA? Does the £2.5/MWh hold for 35 years, or do we need a price curve? |
| 4 | **11kV embedded benefits** | 12 monthly £/MWh values (£5–£11/MWh), 15-year tenor, CPI-indexed | Include | Q3.4 — Embedded benefits are TNUoS/DUoS avoidance for distribution-connected generators. Does this apply when feeding a data centre directly off-grid, or are the embedded benefits actually grid export? |
| 5 | **BESS merchant** | Burton Top scenario, 5 % curve discount | Include | Q3.5 — Under the 10-year PPA, the BESS is dispatched to support delivering the 25 MW base load. Does it earn merchant revenue **simultaneously**, or only **post-PPA** (after 2037)? |
| 6 | **BESS optimiser floor** | £40/MWh floor, 9 % underwriter share, 10-year tenor | Include | Q3.6 — Is the floor revenue stacked with merchant (whichever is higher) or instead-of? Is the 9 % underwriter share an opex line or a revenue haircut? |
| 7 | **Capacity Market T-1** | £20k/MW/yr, 27.15 % de-rating, 3-year tenor from 2026 | Include | Q3.7 — Is the BESS in this asset actually CM-eligible while it is contracted to deliver firm power to the data centre under PPA? Some PPAs are exclusive. |
| 8 | **Capacity Market T-4** | £60k/MW/yr, 20.94 % de-rating, 15-year tenor from 2029 | Include | Q3.8 — Same question. Also, is £60k/MW/yr realistic for a co-located BESS T-4 contract today, or has it shifted? |
| 9 | **Gas PPA revenue** | £170/MWh PPA, then £200/MWh merchant post-PPA | Include | Q3.9 — Confirm the gas plant operates under the same PPA as solar+BESS (single tariff to data centre), or does it have a separate offtake? |
| 10 | **Gas merchant (post-PPA)** | £200/MWh, 9 hours/day operational | Include | Q3.10 — Is 9 hours/day realistic for a post-PPA tail, given UK power market dynamics? |

**Q3.11** — Are there any revenue streams **the Excel is missing** that we should be including? E.g. ancillary services (frequency response, FFR / DC / DM), balancing mechanism revenue, BSUoS avoidance, T&Cs charging benefits, contract-for-difference. The Excel has placeholder lines for "Balancing Services" but only as a cost.

**Q3.12** — Is the "off-grid" framing accurate? Burton Top has a grid connection cost line (£57.86/kWp = £4.7m), which suggests it is grid-connected. Is "off-grid" referring to (a) the data centre being islanded from the grid or (b) the asset being islanded from the grid? This determines whether merchant export is even physically possible.

---

## 4. Capex — what scales with what in the sweep

The user can run two sweep modes:
- **Mode A (BESS-only sweep):** solar MWp fixed, BESS MWh / duration / DG MW vary.
- **Mode B (full sweep):** solar MWp also varies as a sweep dimension.

For each capex line, we need to know what drives it. Our current rules below — please correct.

### 4.1 Solar-driven capex (scales linearly with solar MWp)

| Line | Excel £/kWp | Our rule | SME — please confirm |
|---|---|---|---|
| EPC Cost | 400 | Linear with solar MWp | Q4.1.1 — Does EPC really scale linearly across the 50–150 MWp range, or are there step functions for larger inverter sizes / transformer counts? |
| Acquisition Fee | 0 | Linear with solar MWp | Q4.1.2 — Or is this a fixed lump sum per project? |
| Development Costs | 2.95 | Linear with solar MWp | |
| Discharge of Conditions | 0.98 | Linear with solar MWp | |
| DD Costs | 3.77 | Linear with solar MWp | |
| Other Cost (Financing etc.) | 5 | Linear with solar MWp | Q4.1.3 — Is this really £/kWp or is it a fixed lump? "Financing etc." is suspicious for a £/kWp line — is it actually IDC-adjacent and therefore something we should drop? |
| Ampyr Tech | 3.24 | Linear with solar MWp | Q4.1.4 — Is "Ampyr Tech" an internal cross-charge? Should it stay in PIRR or come out? |
| Insurance | 6.33 | Linear with solar MWp | Q4.1.5 — Is this construction insurance (a one-off capitalised cost) or annual insurance miscategorised? |
| Misc | 4.92 | Linear with solar MWp | |
| Stamp Duty Land Tax | 0.75 | Linear with solar MWp | Q4.1.6 — SDLT is on the land transaction value, not on solar MWp. Do you scale it that way in practice for sizing studies, or is the £/kWp figure just a back-of-envelope? |

### 4.2 BESS-driven capex

The Excel labels BESS capex as "£/kWp" but the value of 600 only makes sense as **£/kW of BESS power** (62.5 MW × £600/kW = £37.5m matches the £k total).

**Q4.2.1** — Confirm the convention is £/kW of BESS power (not £/kW of solar, not £/kWh of BESS energy). Our engine will accept **either £/MW or £/MWh** as input and use whichever is populated.

**Q4.2.2** — On a 4-hour BESS, £600/kW = £150/kWh. **Is £150/kWh the right BESS capex assumption today?** The Excel was built earlier; cell-and-EPC bids have moved. What is the right number to default the engine to?

**Q4.2.3** — BESS capex on a 2-hour BESS is not just half of a 4-hour BESS. Power conversion stays constant; only energy storage changes. So £/kWh-only scaling overstates the cost of short-duration batteries, and £/kW-only scaling understates them. The right model is `cost = (£/MW × MW) + (£/MWh × MWh)`, with separate PCS and energy components. **Should we move to a two-component capex model**, or keep the single-driver simplification?

**Q4.2.4** — Augmentation: the Excel has BESS Augmentation as a step-function **opex** (£3.125m every ~5 years on a £37.5m base = 8.3 % of original BESS capex per cycle). Should this scale linearly with BESS MWh in the sweep, or with cycles delivered, or stay step-function?

### 4.3 Land-driven capex

Active case: 205 acres for 82 MWp = 2.5 acres/MWp.

**Q4.3.1** — Does the 2.5 acres/MWp ratio hold across solar sizes, or does land utilisation get more efficient at scale (single-axis tracker rows have setbacks, etc.)?

**Q4.3.2** — When the user runs a Mode B sweep with solar MWp varying, should we hold acres constant (use the original 205 acres regardless of solar size — only valid if solar shrinks) or scale linearly (assume more land available at the same £/acre)? In real life, land is fixed.

### 4.4 Grid connection

Active case: £4.7m grid costs on 82 MWp ≈ £57.86/kWp.

**Q4.4.1** — Real grid connections step-function up by transformer band. £/kWp linear scaling will be wrong for a Mode B sweep that crosses a transformer threshold. Is this oversimplification acceptable for screening, or material enough that we need a step-function model? If the latter, what are the typical UK distribution thresholds (e.g. 33 kV thresholds at 10 / 20 / 50 MW)?

**Q4.4.2** — Is the connection size pegged to solar MWp, BESS MW, or the **maximum coincident export**? On a hybrid, the connection is sized for whichever component dominates at peak.

### 4.5 Excluded from PIRR

We exclude these three from the PIRR capex stack:

| Line | Excel value (Burton Top) | Why we exclude |
|---|---|---|
| IDC (Interest During Construction) | £1,000k | Interest on construction debt; only exists if there is debt. Project IRR is ungeared — no debt, no IDC. |
| Financing Fees (Arrangement + Commitment + Structuring) | £1,248k | Lender fees. Same logic. |
| Pre-funded Cash / DSRA | £200k | Lender protection cash buffer; released to equity at debt maturity. Lender artefact. |

Excluding these lifts PIRR by ~30–50 bps on Burton Top.

**Q4.5.1** — Does Ampyr's internal PIRR convention also exclude these three? Some sponsors include IDC in PIRR despite the textbook view, on the grounds that "any sponsor will have to fund construction one way or another". Important to align.

**Q4.5.2** — What about the **commitment fee on undrawn debt during construction**? It is in the Excel as a 1.8 % p.a. line. Same logic — drop?

**Q4.5.3** — Should we keep **Contingency** (1 % of base capex)? It is a real project cost (technical contingency, not financial). Our current decision: keep it. Confirm.

---

## 5. Tax and depreciation

The Excel uses two depreciation schedules — Depreciation (SLM) for accounting and Depreciation (Tax) for the tax base — both expressed as "p.a." over the project life.

**Q5.1** — UK tax depreciation for solar+BESS plant: **what is the correct treatment?** Capital Allowances regime — first-year allowance (FYA, formerly super-deduction at 130 %, now 100 % full expensing on main-rate plant for companies)? Writing-down allowance at 18 % main-rate or 6 % special-rate pool? Long-life asset rules? AIA?

**Q5.2** — Is the BESS treated as plant & machinery (eligible for full expensing) or as a long-life asset (special-rate pool, 6 % reducing balance)? This materially changes early-year cash flow and PIRR.

**Q5.3** — Excel uses a single corporate tax rate (`Inputs-Gas!A69`). UK corporation tax stepped from 19 % to 25 % in April 2023, with marginal relief between £50k–£250k of profits. For a project of this size, profits will exceed £250k, so the 25 % rate applies. Does Ampyr use 25 % flat for modelling, or simulate the marginal relief?

**Q5.4** — Are there **carry-forward losses** in the early years (revenue ramp-up + accelerated depreciation = large losses)? Without carry-forward, we under-state tax shield. Confirm Excel handling.

**Q5.5** — Is there any **business rates relief / capital allowance relief** specific to renewables / storage that we should bake in?

---

## 6. Granularity and accuracy choices

**Q6.1** — *Monthly vs annual.* We chose 420 monthly periods (35 yr × 12 mo) over 35 annual periods. Excel is monthly. Annual is ~12× faster to compute but loses seasonality, mid-year COD timing, indexation start dates, opex payment frequency. **Is monthly required for the rank-ordering you would trust, or is annual good enough for a screening tool?**

**Q6.2** — *Per-line-item indexation.* Excel has 14 indexation cases (CPI, RPI, NIL, Flat 0 %, CPI − CfD, PPA Indexation, BESS Indexation, Land Lease CPI, Land Lease RPI, CPI + 3.1 %, etc.) each with its own start date. We are porting all of them. **Are all 14 actually material, or can we collapse to 3–4 (CPI / RPI / NIL / fixed) without breaking PIRR ordering?**

**Q6.3** — *Hourly dispatch re-run inside financial model.* Per config, we re-run the 8760-hour dispatch in Python (NumPy, ~30–50 ms) to produce monthly aggregates of MWh delivered, MWh exported, BESS cycles. Alternative is to take Step 3's annual operational metrics and apply 12 monthly fractions. **Is the seasonality actually material for PIRR ordering, or is annual + seasonality fractions enough?**

**Q6.4** — *XIRR vs IRR.* We use XIRR (actual day count, matches Excel's XIRR function) rather than IRR (period-based). On a 420-period monthly model with mid-year COD, the difference is small but non-zero. Confirm XIRR is right.

**Q6.5** — *Project life.* 35 years. Beyond ~25 years, FCFF is small and discounted heavily. **Is the marginal information from years 25–35 worth carrying, or do you screen on shorter horizons (e.g. 25 years + terminal value)?**

---

## 7. Gas plant treatment in the sweep

This is the biggest open question on our side and we particularly need your guidance.

The Excel has the gas peaker (~28 MW) consolidated with solar+BESS into a single Project IRR (9.23 %). Per-stream PIRRs: Solar+BESS = 8.85 %, Gas = 10.77 %.

When the user sweeps BESS sizes in the PSP, the **gas plant fills the residual gap** — whatever the BESS+solar cannot deliver to the 25 MW base load, the gas covers. So gas size is a **derived output** of each config, not a sweep dimension.

**Q7.1** — Is that the right framing? When BESS gets bigger, gas runs less hours / less capacity needed; when BESS gets smaller, gas runs more. Should gas capacity (MW) **stay fixed at the original 28 MW** in the Excel, or **scale down** as BESS gets bigger?

**Q7.2** — Should the **gas IRR be included in the headline PIRR** that ranks configs, or should the user see two separate columns ("Solar+BESS PIRR", "Gas PIRR")? An IC member who sees a single 9.23 % may not realise it's a blended number across two very different assets.

**Q7.3** — If gas capacity scales, gas capex scales too. £/MW for gas peaker is implied somewhere in `Inputs-Gas` and `12 MW CAPEX Estimate-Gas`. **What is the right £/MW for a 12–28 MW gas peaker today, and does it scale linearly or step-function?**

**Q7.4** — Gas opex: the Excel has fuel + CCL + UKETS + start fuel + cycles + fixed gas cost + £/day + variable O&M. Should the Python engine port all of these, or is "fuel × hours + £k/MW/yr fixed" a sufficient approximation for screening?

**Q7.5** — UKETS price was £75/tonne CO₂ in Excel. Spot is volatile. **What price should we default to**, and should we make it a user input?

---

## 8. Audit / validation approach

We have an existing Python implementation (`src/financial_model.py`, ~1,500 lines) that was an earlier port of the Excel. Before extending it, we plan to **drive it with the Burton Top base-case inputs and compare PIRR vs Excel's 9.23 %**.

- Headline tolerance: within **0.1 pp** (i.e. between 9.13 % and 9.33 %)
- Year-by-year FCFF tolerance: within **1 % per year**, no systematic drift
- Total revenue / opex / capex / tax over 35 years tolerance: within **0.5 %**

If the Python diverges from Excel by more than this, we rewrite from scratch rather than chase the bug.

**Q8.1** — Are these tolerances appropriate? **0.1 pp on PIRR** is tight — if the Excel itself has multiple `#REF!` errors and broken named ranges (which it does), the "correct" answer is fuzzy. Looser tolerance (0.5 pp) might be more honest.

**Q8.2** — Can you supply an **Excel "answer key" for one or two non-base scenarios**? E.g. P75 yield instead of P50, BESS off (solar-only), 50 % EPC haircut. Each gives us a regression-test row. If you cannot, base case alone is fine.

**Q8.3** — Do you have other reference models (Costock, Northwold, Albrighton) that we could use as additional validation points? The Burton Top base case alone is a single data point and may not catch structural bugs.

---

## 9. Things we may have missed

**Q9.1** — Anything you would expect to see in a Project IRR calculator that we have not mentioned in this document? Reserves (MRA / Major Maintenance Reserve), decommissioning provisions, residual value at end of life, salvage value of land?

**Q9.2** — The Excel models a **single asset**. Ampyr's portfolio is multi-asset (Burton Top, Costock, Northwold, Albrighton, Oakley). For the PSP, are we right to assume the user runs one asset at a time, or do we need portfolio rollup logic in scope? (Currently out of scope.)

**Q9.3** — **Currency.** Excel is in GBP (active Burton Top case) but several cells label "EUR k" inconsistently. Confirm GBP throughout for UK assets.

**Q9.4** — **Inflation framing.** The Excel mixes real and nominal cash flows in places (`Solar&BESS Inputs` has a "Fixed costs (real)" header, but PPA tariff appears nominal with explicit indexation). For the Python engine: **do we model nominal end-to-end** (escalate everything explicitly with CPI / RPI / etc.) and **discount with a nominal discount rate**, or **real end-to-end**? Excel appears nominal — confirm.

**Q9.5** — **Discount rate.** PIRR does not need a discount rate (it solves for the rate). But if we add NPV-at-WACC as a secondary metric, we need a WACC assumption. Excel uses 7.0 % cost of capital and 6.5 % project discount rate. **What is the right WACC for ranking purposes?**

**Q9.6** — **Anything else we should know** about how Ampyr uses these models in practice? Are there conventions, internal "rules of thumb", or known traps we are likely to walk into?

---

## 10. Summary of our current decisions (for SME quick reference)

| # | Decision |
|---|---|
| 1 | PIRR = ungeared post-tax IRR on FCFF (matches Excel `Consol Cash Flows!B9` = 9.23 % for Burton Top base case) |
| 2 | Two sweep modes: BESS-only (solar fixed) and full (solar + BESS swept) |
| 3 | Per-config dispatch re-run inside financial layer, monthly aggregation |
| 4 | All ~10 Excel revenue streams in scope |
| 5 | Solar-driven capex scales linearly with solar MWp |
| 6 | BESS capex accepts £/MW or £/MWh |
| 7 | Land area scales linearly with solar MWp |
| 8 | Grid costs scale linearly with solar MWp (acknowledged simplification) |
| 9 | Exclude IDC, Financing Fees, Pre-funded DSRA from PIRR capex |
| 10 | 420 monthly periods, per-line-item indexation, XIRR with actual day count |
| 11 | 8–12 s for a 100-config sweep is the accepted performance budget |
| 12 | Audit existing `financial_model.py` against Excel before extending vs rewriting |
| 13 | Gas plant: capacity fills residual gap (derived per config); included in headline PIRR |

---

**Thanks for the review.** Even partial answers help — please flag the ones you cannot answer rather than skipping them, so we know which need a second source.
