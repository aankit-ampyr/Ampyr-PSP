# Project IRR — SME Follow-up Questions (v2)

**To:** Anchal
**From:** Ankit
**Context:** Follow-up after the May 7 review. I've been digitising the PIRR pathway from `Off-Grid Solution v8.xlsm` into Python. The engine is close to your 8.9% target but three specific Excel mechanics need your input to close the last 137 bps. All narrow.

---

## Q1. Source of the 8.9% number

Quick refresher on what 8.9% is. On May 7 you sent a 4-row reference matrix as an image — PIRR values for four variants of the Burton Leonard case (82 vs 115 MWp DC × £170 vs £160 PPA, all with 250 MWh BESS / 25 MW gas / 58.4 MW grid limit). The 82 MWp / £170 / 250 MWh row showed **PIRR = 8.9%**, and we've been using that as the audit target for v1 of the Python engine.

Question: did 8.9% come from the current `Off-Grid Solution v8.xlsm` with those inputs swapped into the active column, or did you run it from a different snapshot of the workbook?

Reason for asking: the current workbook shows 9.23% on `Consol Cash Flows!B9` for the 3.8h Burton Top case. A 0.33 pp shift to 8.9% feels right for the 3.8h→4h BESS change alone, so most likely you ran it on the same workbook and we're calibrated to the same Excel. But if it was a different snapshot, some switches might have differed and that changes what we're aiming at. Worth a quick yes/no before we burn another iteration chasing the gap.

---

## Q2. BESS revenue switches for the Burton Leonard case

In the current workbook, all BESS revenue lines evaluate to zero. `FS!B20:B23` (BESS Merchant 1/2/3 + BESS CM) all show £0 lifetime, and `FS!B24` Total BESS Revenue = £0. The corresponding switch cells on Solar&BESS Inputs (`F124` BESS merchant, `F131` BESS floor) are set to 1, so the zero output is coming from a downstream condition we haven't reverse-engineered yet.

For the Burton Leonard case (82 MWp / £170 / 250 MWh): is BESS floor + CM T-1 + CM T-4 revenue meant to be on or off in your 8.9% reference?

It's a £37k lifetime revenue swing. If they're meant to be on, our engine has a switch-modelling gap and we'll go hunt for the right conditional. If off, we already match.

---

## Q3. `Solar&BESS Operation` row 155 ("Lease Adjustment")

We see r155 = £6,512 lifetime but can't reverse-engineer the mechanism from the formulas alone. Our engine currently treats land lease as `max(fixed_lease, rev_dep_lease × revenue)` and that lands close to Excel's final lease (r157 = £30,184), but doesn't replicate the r155 adjustment exactly.

Is `max()` a fair approximation of what r155 is doing? Or is something else going on — annual-then-monthly true-up, CPI-vs-revenue reconciliation, etc.?

One sentence is enough. If `max()` is wrong I'll port the full logic; if it's fine I'll leave it.

---

## What we've done ourselves (so you don't have to)

For context: everything answerable directly from the workbook, we've already extracted. Dumps cover:

- `Consol Cash Flows` rows 5-7 (FCFF chain, formulas)
- `Equity` rows 150-175 (Solar+BESS FCFF and IRR formula)
- `Cash Flows-Gas` rows 12-88 (gas FCFF chain, opex breakdown, capex)
- `FS` rows 12-93 (FCFF inputs)
- `Solar&BESS Operation` rows 88-175 (revenue, opex, lease mechanism)
- `BESS` rows 88-135 (BESS opex breakdown)

Engine state: 10.27% PIRR (started at 19.61% before I audited the old engine and rewrote it). Capex matches Excel exactly at £79,578k. Gas timing structure matches. Remaining 137 bps is the solar merchant curve fidelity plus the three open questions above.

Thanks!
