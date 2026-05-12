# Project IRR — SME Follow-up Questions (v2)

**To:** Anchal
**From:** Ankit
**Context:** Follow-up after the May 7 review. I've been digitising the PIRR pathway from `Off-Grid Solution v8.xlsm` into Python. The engine is close to your 8.9% target on three of the four matrix rows, but four narrow Excel mechanics need your input to close the residual gap and explain a PPA-tariff sensitivity pattern. All narrow.

**Status 2026-05-12:** All four questions answered. Q1 follow-up + Q4 answered today. See decisions log A20 for engine state vs both targets (S+B 8.9%, Combined 9.2%).

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

## Q4. PPA-tariff sensitivity in your matrix

I've now run the engine against all four rows of your May 7 matrix. Current state:

| Case             | Engine | Your target | Delta      |
|------------------|--------|-------------|------------|
| 82 MWp / £170    | 10.28% | 8.9%        | +1.38 pp   |
| 82 MWp / £160    | 9.73%  | 7.4%        | +2.33 pp   |
| 115 MWp / £170   | 9.97%  | 9.8%        | +0.17 pp   |
| 115 MWp / £160   | 9.41%  | 8.5%        | +0.91 pp   |

When PPA drops £170 → £160, my engine drops by ~0.55 pp on both solar sizes. Your matrix drops by ~1.5 pp. About 3x more sensitive in Excel.

My PPA revenue base looks right — £127k lifetime for the 82/£170 case matches `FS!B13` exactly. So the gap isn't in how I'm computing the £170 case. Something downstream of PPA tariff must be more sensitive in Excel than in my model.

Two possibilities and either answer is useful:

(a) Is there a tariff-dependent mechanism I'm missing — escalation, derating, clawback, anything that scales nonlinearly with PPA price? If yes, I keep hunting.

(b) Or was the £160 column run with different switches than the £170 column? Different BESS state, different gas merchant assumption, different snapshot? If yes, that explains the asymmetry and I stop hunting for mechanism (a).

---

## What we've done ourselves (so you don't have to)

For context: everything answerable directly from the workbook, we've already extracted. Dumps cover:

- `Consol Cash Flows` rows 5-7 (FCFF chain, formulas)
- `Equity` rows 150-175 (Solar+BESS FCFF and IRR formula)
- `Cash Flows-Gas` rows 12-88 (gas FCFF chain, opex breakdown, capex)
- `FS` rows 12-93 (FCFF inputs)
- `Solar&BESS Operation` rows 88-175 (revenue, opex, lease mechanism)
- `BESS` rows 88-135 (BESS opex breakdown)

Engine state: 10.28% PIRR for D13 (started at 19.61% before I audited the old engine and rewrote it). Capex matches Excel exactly at £79,578k. Gas timing structure matches. 115 MWp / £170 case now within 0.17 pp of target after the Baringa curve fix. Remaining gap is the four open questions above — the PPA-tariff one (Q4) is the dominant lever.

Thanks!
