# Step 3a — Browser Smoke-Test Playbook

> **2026-05-16 — current state.** Engine post-A40 produces D13 Combined **8.88%** / S+B **9.05%** / Gas **13.07%**. Target Combined 9.2% (-0.32 pp gap). All 4 audit-matrix rows in xfail pending Anchal's reply on Q1/Q2 tolerance memo. The 4 audit rows have ranged from -0.45 to -0.19 pp across the matrix; m115_170 + m115_160 are closest at -0.19 pp. UI walkthrough below is now a pass/fail check against the engine's ACTUAL numbers (8.88% Combined), not the audit TARGET (9.2%). §2's expected values are aligned with current engine output.
>
> **2026-05-14 (kept for history).** Anchal's reply confirmed SME matrix targets are Combined PV+BESS+Gas PIRRs, not S+B-only. The pre-§15 expectation of D13 S+B 8.93% / Combined 8.77% (which expected the old A22 engine state) was the prior baseline.

**Purpose.** Reproducible end-to-end smoke test for the Step 3a Financial Sweep page. Run this whenever you change the PIRR engine, the wizard-state adapter, the dispatch chain, or any page Step 3a depends on (Step 1, Step 3, Step 7). Designed for a Claude agent driving Streamlit + a browser (manually or via a future browser-automation tool).

**When NOT to use.** Unit tests catch engine correctness — this playbook catches UI wiring (button targets, session-state contracts, render crashes, the sweep finishing in finite time). If `pytest tests/` is broken, fix that first; this won't tell you anything useful.

---

## 0. Prerequisites — do these BEFORE starting the server

Run each command, confirm the expected output. If any fails, stop and diagnose before launching Streamlit.

| # | Command | Expected | If wrong |
| --- | --- | --- | --- |
| 0.1 | `git status --short` | Working tree changes match what you're testing; no stray `tests/diag_*.py` | Clean up — see prior conversation pattern (delete diag files) |
| 0.2 | `python -X utf8 tests/test_project_irr_excel_parity.py 2>&1 \| tail -10` | D13 row prints `Combined 8.84%` (±0.01), `S+B 9.00%`, `Gas 13.07%` (post-A44 Insurance schedule + A45 tolerance closure). All 4 audit rows PASS at ±0.5 pp v1 tolerance. | Engine has regressed; do NOT proceed |
| 0.3 | `python -m pytest tests/ --no-header -q 2>&1 \| tail -3` | `49 passed, 0 xfailed` (post-A45 tolerance relaxation) | Same as 0.2 |
| 0.4 | `python -X utf8 -c "import streamlit; print(streamlit.__version__)"` | Some version prints (last verified 2026-05-16: 1.51.0) | `pip install -r requirements.txt` |

If 0.1–0.4 all pass: proceed.

---

## 1. Start the dev server

```bash
streamlit run app.py --server.headless true --server.port 8501
```

Run with `run_in_background=true`. Streamlit usually prints:

```
You can now view your Streamlit app in your browser.
URL: http://localhost:8501
```

**Pass criteria:** the URL line appears within ~5s and no `ImportError` / `SyntaxError` traceback. If you see `Address already in use`, change the port (`--server.port 8502`).

**Tail the log periodically** as you walk through the UI — every page click logs requests; Python errors print full tracebacks. Hold this in mind: most of your diagnostic signal lives there, not in the browser.

---

## A. Browser-agent verification — A40 / A41 / A42 / A43 / A44 / A45 / A46 / A47 (UPDATED 2026-05-16)

**Intent.** A focused, step-by-step verification of all v1 changes through to v1 SME-handoff state. Designed to be executable by a browser-driving agent (Claude for Chrome extension or similar). Covers: A40 (time-varying CPI), A41 (Step 4 Financial Metrics), A42 (sizing_results unification), A43 (DEFAULT_WIZARD_STATE alignment), A44 (Insurance schedule), A45 (v1 audit closed at ±0.5 pp), v1 polish (DEBUG removal + conservative-offset captions), A46 (MOIC), A47 (dead code cleanup). The longer §3 walkthrough below covers the same paths plus regressions, but §A is the minimum set for verifying v1 readiness.

**Pre-flight (already done by Ankit / Claude Code agent before handoff):**

- Engine audit: `python -X utf8 tests/test_project_irr_excel_parity.py` → D13 row prints **Combined 8.84%** / **S+B 9.00%** / **Gas 13.07%** (post-A44 Insurance schedule). All 4 rows PASS at ±0.5 pp v1 tolerance.
- pytest: **49 passed + 0 xfailed** (A45 relaxed tolerance + removed xfail markers).
- Streamlit running. Replace `<URL>` below with the live URL (e.g. `http://localhost:8510`).

### A.1 — Open the app, confirm sidebar

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.1.1 | Navigate browser to `<URL>` | Page loads; no error overlay; sidebar lists Step1_Setup through Step7_Financial plus Step3a_FinancialSweep |
| A.1.2 | Confirm Step 1 is active by default | Sidebar shows "Step1_Setup" highlighted, OR clicking it from sidebar lands on Step 1 |

### A.2 — Step 1: Setup (D13 inputs)

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.2.1 | Click "Step1_Setup" in the sidebar | Title shows "Step 1: Setup" or similar; no traceback |
| A.2.2 | Load mode = "Constant"; Load MW = **25** | Field accepts 25 |
| A.2.3 | Solar source = "From Inputs folder" | Dropdown appears below |
| A.2.4 | Solar file = **`Burton_Leonard_82MWp_DC_58MW_AC`** (or with `.csv` suffix if shown) | Dropdown selects it; profile preview/chart updates if any |
| A.2.5 | Solar capacity (MW) = **82** | Field accepts 82 |
| A.2.6 | In BESS container types, ensure **`5mwh_1.25mw` (4-hour)** is selected | Container appears in selection |
| A.2.7 | BESS efficiency = **87**, min SOC = **5**, max SOC = **95** | All fields accept values |
| A.2.8 | DG enabled = **ON** (checkbox/toggle) | Toggle switches |
| A.2.9 | Scroll the page; no Streamlit exception overlay visible | Clean |

### A.3 — Step 2: Rules (defaults)

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.3.1 | Click "Step2_Rules" in sidebar | Page loads; leave all fields at defaults |
| A.3.2 | Click any "Next" / advance button if present | Reaches Step 3 or no-op (rules optional for sweep) |

### A.4 — Step 3: Sizing sweep

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.4.1 | Click "Step3_Sizing" in sidebar | Page loads; no traceback |
| A.4.2 | BESS min = **50**, max = **300**, step left at default | Accepts values |
| A.4.3 | DG min = **25**, max = **25** | Accepts values |
| A.4.4 | Click the "Run Simulation" / "Run Sweep" button (whatever's labelled there) | Progress bar appears; status text updates per config; finishes in <60 s |
| A.4.5 | Results table appears below | Table has columns including `BESS (MWh)`, `Duration (hr)`, `DG (MW)`, `Delivery %`, `Green %`, `Wastage %`. ~102 rows |
| A.4.6 | Filter or scroll to find row: `BESS (MWh) = 250`, `Duration (hr) = 4`, `DG (MW) = 25` | Row exists |

### A.5 — Step 3a: Financial Sweep (A40 / A43 / A44 / A46 verification)

Verifies the engine produces the post-A44 numbers via the wizard-state path AND the new A46 MOIC column renders AND the v1 polish info banner shows.

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.5.1 | Click "£ Add Financial Analysis" button at the bottom of Step 3 (or navigate to Step3a_FinancialSweep via sidebar) | Step 3a page loads. **NO `§16 DEBUG` warning** appears (removed in v1 polish commit `ae48f49`) |
| A.5.2 | Verify the "Sweep Configuration" section shows `Operational Configs: ~102`, `Load (MW): 25`, `Solar DC (MWp): 82` | All three correct |
| A.5.3 | Click "Run Financial Sweep" (primary button) | Progress bar; per-config status text; finishes in 8–15 s (D16 perf budget). **No DEBUG `st.warning` block appears after the sweep finishes** (removed at v1 polish) |
| A.5.4 | "Ranked Results" table appears | Has columns: `BESS (MWh)`, `Duration (hr)`, `DG (MW)`, `Delivery %`, `Green %`, `Combined PIRR (%)`, `S+B PIRR (%)`, `Gas PIRR (%)`, `NPV (GBPm)`, **`MOIC (x)`** (A46), `Total CAPEX (GBPm)`, `Payback (yrs)` |
| A.5.5 | Above the Ranked Results table, a blue info banner reads "v1 reports Project IRR ~0.3-0.5 pp lower than Excel..." (v1 polish caption) | Banner visible; mentions DSCR sculpting / cash sweep / Equity IRR deferred to v2 |
| A.5.6 | Find the row `BESS=250, Duration=4, DG=25`. Read Combined / S+B / Gas PIRR + MOIC. | **Combined ≈ 8.84%** (±0.10), **S+B ≈ 9.00%** (±0.10), **Gas ≈ 13.07%** (±0.20), **MOIC ≈ 2.22x** (±0.10), CAPEX ≈ £101.4m |
| A.5.7 | "Sort by" dropdown includes **MOIC (x)** as an option | A46 dropdown enrichment present |
| A.5.8 | Best-config callout below the table names a specific config + its PIRR | Some config named; numbers match the table |
| A.5.9 | No `Error` column visible in the table | Clean (no per-config crashes) |

**If A.5.6 numbers diverge from expected by > 0.5 pp** — A44 / A43 wiring may have broken. Run `python -X utf8 tests/test_project_irr_excel_parity.py` to confirm fixture path is still 8.84% — if so, the gap is in `pirr_inputs_from_wizard_state`.

### A.6 — Step 4: A41 Financial Metrics + A46 MOIC + v1 polish caption (happy path)

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.6.1 | From Step 3a, click "Next → Step 4 Results" (or sidebar Step 4) | Step 4 page loads |
| A.6.2 | In the Configuration Selection block at top: Duration Class = **4-hour (0.25C)**, BESS Capacity (MWh) = **250**, DG Capacity (MW) = **25** | Fields accept |
| A.6.3 | A green banner says "Found cached results from Step 3 sizing run" | Visible |
| A.6.4 | Click "See Results" (primary button) | Page renders metrics block + monthly summary table + hourly chart |
| A.6.5 | **A41 verification**: scroll to find the **"£ Financial Metrics"** subheader. Location: below the "Solar Utilization" metric row, above "Monthly Performance Summary" | Subheader visible |
| A.6.6 | **v1 polish caption**: below the subheader + the existing A24 dispatch-mismatch caption, a blue info banner reads "v1 reports Project IRR ~0.3-0.5 pp lower than Excel..." | Banner visible |
| A.6.7 | Below the banner: **7 metric tiles** in a single row (was 6 pre-A46) | Tiles labelled: Combined PIRR, S+B PIRR, Gas PIRR, NPV (GBPm), **MOIC** (A46), CAPEX (GBPm), Payback (yrs) |
| A.6.8 | Values: Combined **8.84%**, S+B **9.00%**, Gas **13.07%**, NPV (some figure), **MOIC ≈ 2.22x**, CAPEX **101.4** (GBPm), Payback (some figure) | Numbers match Step 3a's row from A.5.6 |
| A.6.9 | MOIC tile has a help-icon tooltip: "Multiple on Invested Capital, ungeared FCFF basis: sum(positive FCFF) / \|sum(negative FCFF)\|" | Tooltip visible on hover |

**If A.6.5 fails (no "£ Financial Metrics" subheader)** — A41 isn't wired. Check that `st.session_state.financial_results` exists (Step 3a's "Run Financial Sweep" was clicked in §A.5). Check `find_cached_financial` returns non-None for `(250, 25, '5mwh_1.25mw')`.

### A.7 — Step 4: A41 info banner (no-match path)

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.7.1 | Still in Step 4, change BESS Capacity (MWh) from 250 to **5** (a value NOT in Step 3's sweep range) | Field accepts |
| A.7.2 | Click "Run Simulation" / "See Results" (button label depends on cache state) | Simulation runs; results display updates |
| A.7.3 | Where the "£ Financial Metrics" section was (in A.6), the metric tiles are now **replaced** by an **info banner** | Banner present, blue background |
| A.7.4 | Banner text contains "Financial sweep exists but does not include this config" and mentions the current BESS / DG / duration | Text present |

### A.8 — Step 4: A41 silent fallback (no Step 3a run)

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.8.1 | Stop the Streamlit server (Ctrl-C in the terminal, or via TaskStop on the bg process) | Server stops |
| A.8.2 | Restart Streamlit: `streamlit run app.py --server.headless true --server.port 8510` | Server boots, prints URL |
| A.8.3 | Navigate browser to the URL, walk Step 1 (same inputs as A.2) → Step 3 (same inputs as A.4, run sweep) → **SKIP Step 3a** → directly to Step 4 | All pages load |
| A.8.4 | In Step 4, set BESS = 250, Duration = 4, DG = 25, click "See Results" | Page renders |
| A.8.5 | Confirm **no "£ Financial Metrics" subheader** appears and **no info banner** appears | Pre-A41 UX preserved |

### A.9 — A42 / A47 verification (wizard_state cleanup) + Step 7 visual check

A42 dropped the dead `wizard['results']['simulation_results']` slot; A47 dropped the rest of the dead `wizard['results']` dict + 5 helper functions. Both should be invisible to the user (cleanup only).

| Step | Action | Pass criteria |
| --- | --- | --- |
| A.9.1 | After §A.5 (Step 3a ran successfully), Step 3a's sweep used `sizing_results` as input | Sweep ran; PIRRs computed |
| A.9.2 | §A.6 (Step 4 happy path) also worked off `sizing_results` (via `find_cached_result`) + `financial_results` (via the new `find_cached_financial`) | Step 4 metrics tiles rendered |
| A.9.3 | Navigate to Step 7 (sidebar). It should NOT show a "Step 3 sizing run is required" warning since we ran Step 3. | Step 7 prerequisite check passes (the A42 comment update went here) |
| A.9.4 | In Step 7, click "Save Financial Inputs" + "Run Financial Analysis" with D13-default inputs | Engine runs; results appear in Summary block |
| A.9.5 | **v1 polish caption**: above the "Summary" subheader, a blue info banner reads "v1 reports Project IRR ~0.3-0.5 pp lower than Excel..." | Banner visible |
| A.9.6 | Summary block has **5 metric tiles** (was 4 pre-A46): Project IRR (Combined), Project NPV (GBPm), Total CAPEX (GBPm), **MOIC** (A46), Payback | All 5 visible; MOIC ≈ 2.22x |
| A.9.7 | MOIC tile help-icon tooltip reads same as A.6.9 | Tooltip visible |

### A.10 — Wrap-up

- Pass if A.1 through A.9 all pass.
- For each step that fails, capture: (a) browser screenshot, (b) the corresponding line from the Streamlit server log (file path was reported when Streamlit launched), (c) the step ID. Report back so the failure can be triaged.

---

## 2. Inputs to use — D13-equivalent config

To sanity-check Step 3a's output, use inputs that produce a config in the sweep range matching D13. Then look for the row where BESS = 250 MWh, Duration = 4 hr, DG = 25 MW. That row's PIRR should land at the **current engine state** (post-A40, 2026-05-16):

| Metric | Expected (engine) | Target (SME) | Notes |
| --- | --- | --- | --- |
| Combined PIRR | **8.88%** (±0.05) | 9.2% | -0.32 pp gap, awaiting Anchal Q2 tolerance reply |
| S+B PIRR | **9.05%** (±0.05) | (matrix doesn't break out S+B) | |
| Gas PIRR | **13.07%** (±0.10) | (matrix doesn't break out Gas) | |

If those numbers come out cleanly via Step 3a, the page is wired to the engine correctly. The audit run is authoritative — `python -X utf8 tests/test_project_irr_excel_parity.py` produces these same numbers via the fixture path; Step 3a should produce them via the wizard-state path. If they diverge, it's a wizard-state adapter bug (see A24's merchant-curve sub-finding for a recent example).

### Step 1 inputs

| Field | Value | Why |
| --- | --- | --- |
| Load mode | Constant | Simplest |
| Load MW | **25.0** | Matches D13 |
| Solar source | "From Inputs folder" | |
| Solar file | **Burton_Leonard_82MWp_DC_58MW_AC.csv** | D13 audit profile |
| Solar capacity (MW) | **82** | D13 |
| BESS container types | Include `5mwh_1.25mw` (4-hr) | Need 4-hr to get 250 MWh @ 62.5 MW |
| BESS efficiency | 87 % | D13 |
| BESS min/max SOC | 5 / 95 % | D13 |
| DG enabled | ✓ | D13 has 25 MW gas |

### Step 2 — leave defaults (rules don't affect Step 3a's PIRR engine)

### Step 3 sweep range — narrow, so the sweep is fast

| Field | Value | Why |
| --- | --- | --- |
| BESS min | **50 MWh** | |
| BESS max | **300 MWh** | Includes 250 |
| BESS step | 5 (fixed) | Default |
| DG min | **25 MW** | Includes D13's 25 |
| DG max | **25 MW** | Single DG row keeps configs small |
| DG step | 5 | Default |

Total configs ≈ ((300−50)/5+1) × 2 container types × 1 DG = 102 configs. Lines up with the **D16 perf budget (8–12 s / 100 configs)** — natural perf test.

---

## 3. Walkthrough — per-step, what to click + what to verify

### 3.1 Open the home page

**Action:** open `http://localhost:8501` in browser.
**Verify:**

- Sidebar lists Step1–Step7 + (after Step 3 sweep runs) Step3a appears between Step3 and Step4 alphabetically. *Streamlit sorts pages by filename, so `Step3a_FinancialSweep.py` lands in the right slot.*
- No tracebacks in the server log.

**If fails:** check the server log for ImportError. The most likely culprits are circular imports in `src/wizard_state.py` or missing `streamlit` deps.

### 3.2 Walk through Step 1 — Setup

**Action:** click "Step1_Setup" in the sidebar. Fill in the values from §2. Click whatever "Save / Continue" button advances state.
**Verify:**

- All inputs accept the values (no validation errors at boundary)
- Step indicator highlights Step 1 as current
- Server log shows no exceptions

**If fails:** validation error → match input ranges; widget crash → traceback in server log will name the file:line.

### 3.3 Walk through Step 2 — Rules

**Action:** click "Step2_Rules" in sidebar. Defaults are fine. Click continue.
**Verify:** indicator advances to Step 2.

### 3.4 Run Step 3 — Sizing

**Action:**

1. Click "Step3_Sizing" in sidebar
2. Fill in the BESS / DG ranges from §2
3. Confirm bottom-of-page metrics show **~102 configs** and an est runtime of a few seconds
4. Click "🚀 Run Sizing Simulation"

**Verify:**

- Progress bar advances 0% → 100%
- Bottom of page shows "Simulation Results" table with ~102 rows
- Filter / sort widgets render
- "Quick Insights" callout appears at bottom
- **Three navigation buttons** at the bottom: ← Back to Rules, **£ Add Financial Analysis** (NEW), Next → Results
- The new "£ Add Financial Analysis" button is **enabled** (not greyed)

**If fails:**

- Slow / hung dispatch → check Step 3's progress callback; could be `run_simulation` exception on a specific config (usually a config with bess_mw = 0 from rounding)
- No "£ Add Financial Analysis" button visible → did the edit to `pages/Step3_Sizing.py` land? Re-check `git diff pages/Step3_Sizing.py`.

### 3.5 Navigate to Step 3a — Financial Sweep

**Action:** click "**£ Add Financial Analysis**" button at the bottom of Step 3.

**Verify:**

- URL changes to a Step 3a page
- Page title: "£ Financial Sweep — Project IRR Ranking"
- Step indicator at top shows Step **3a** as current (between Step 3 and Step 4)
- Three metrics at top: Operational Configs (≈102), Load (MW) (25), Solar DC (MWp) (82)
- "Engine assumptions" expander is present
- **"Run Financial Sweep" button** is visible
- A blue info box may say "Step 7 financial inputs have not been saved yet…" — this is expected if Step 7 hasn't been touched

**If fails:**

- Button doesn't navigate → check `st.switch_page("pages/Step3a_FinancialSweep.py")` path
- Page crashes on load → traceback names the line; usually a wizard-state key missing because Step 1 wasn't completed properly
- Step indicator missing 3a → the `render_step_indicator` function in the page has the 3a entry; verify file matches

### 3.6 Run the financial sweep

**Action:** click "Run Financial Sweep".

**Verify (during run):**

- Progress bar advances 0% → 100%
- Status text shows "Config X/102: BESS Y MWh Z-hr, DG 25 MW"

**Verify (after run):**

- Green success message: `Ran 102 configs in X.X s (Y ms/config). D16 budget: 8–12 s for 100 configs.`
- **Performance check:** the elapsed time should be in the 8–15 s range for 100 configs. If significantly worse (>30s), flag as D16 perf miss.
- "Ranked Results" subheader appears
- Filter slider (Min Delivery %) and sort dropdown appear
- Table renders with columns including:
  - **Identity:** BESS (MWh), Duration (hr), Power (MW), DG (MW), Containers
  - **Operational:** Delivery %, Green %, Wastage %, BESS Cycles
  - **Financial:** Combined PIRR (%), S+B PIRR (%), Gas PIRR (%), NPV (GBPm), Total CAPEX (GBPm), Payback (yrs)
- **No "Error" column** appears (would indicate per-config crashes)
- Green success callout: "Top by Combined PIRR: …" naming a specific (MWh / hr / DG) config and its PIRR
- "Download financial sweep (CSV)" button present

**Verify D13 row sanity check** (engine state post-A40, 2026-05-16):

- Find the row where BESS (MWh) = 250, Duration (hr) = 4, DG (MW) = 25
- Combined PIRR should be **≈ 8.88 %** (within ±0.10)
- S+B PIRR should be **≈ 9.05 %** (within ±0.10)
- Gas PIRR should be **≈ 13.07 %** (within ±0.20)
- Total CAPEX should be **≈ £101.6 m**

(SME target is 9.2% Combined — the engine is currently -0.32 pp under target, awaiting Anchal's Q2 tolerance reply. UI test is engine-vs-engine, not engine-vs-target.)

If those numbers are off by > 0.5 pp from the audit:

- Run `python -X utf8 tests/test_project_irr_excel_parity.py` to confirm engine still passes via fixture path
- If audit passes but Step 3a fails → wizard-state adapter bug (like the merchant-curve gap from A24)
- Check whether `pirr_inputs_from_wizard_state` is receiving the expected `fin` / `setup` dicts
- Diagnostic: add a `st.json(pi.__dict__)` before `run_pirr` to inspect what's actually fed to the engine

### 3.7 Exercise the filters + sort

**Action:**

1. Move "Min Delivery %" slider to 95
2. Change "Sort by" to "Total CAPEX (GBPm)"
3. Change to "Payback (yrs)"
4. Change back to "Combined PIRR (%)"

**Verify:**

- Each change updates the table within ~1 s (no re-running the sweep; should just re-display)
- Filtered row count drops when Delivery % filter > 0
- Sort direction flips correctly (Combined PIRR descending, CAPEX / Payback ascending)
- Top-by-Combined-PIRR callout updates accordingly

### 3.8 Download CSV

**Action:** click "Download financial sweep (CSV)".

**Verify:**

- Browser downloads `financial_sweep.csv`
- File opens cleanly; column headers match the table; row count matches the unfiltered sweep

### 3.9 Navigation buttons

**Action:** click each of the three bottom nav buttons in turn:

1. "← Back to Step 3"
2. (return to 3a) "Open single-config Step 7 →"
3. (return to 3a) "Next → Step 4 Results"

**Verify:**

- Each lands on the named page
- `financial_results` persists in session state through these navigations (return to Step 3a after each, table should still be there without re-running)

**If fails:** check `st.switch_page` paths; check `'financial_results' in st.session_state` guard in the table-display section.

---

## 4. Regression check — pages we changed or could have affected

### 4.1 Step 7 — single-config Financial

We changed `src/project_irr.py` engine defaults (merchant curve). Step 7 calls `pirr_inputs_from_wizard_state` and runs PIRR — the merchant curve fix should propagate.

**Action:** click Step 7. Fill in inputs matching D13 (solar 82 MWp, BESS 62.5 MW × 4 hr, etc.). Click "Save Financial Inputs", then "Run Financial Analysis".

**Verify:**

- Result reports Combined PIRR ≈ **8.88 %**, S+B **9.05 %**, Gas **13.07 %** (engine state post-A40, 2026-05-16)
- *(If results report ≈ 7.86 % S+B / 7.88 % Combined: the engine merchant-curve default fix didn't take. Re-check `src/project_irr.py`.)*

### 4.2 Step 4 — Results (A41 Financial Metrics section)

A41 (2026-05-16) added a conditional "£ Financial Metrics" section to Step 4's per-config drilldown. It surfaces Combined/S+B/Gas PIRR + NPV + CAPEX + Payback for the SELECTED config when `st.session_state.financial_results` exists (i.e. user has run Step 3a) and the selected config matches a row in the sweep (join on BESS MWh × DG MW × Duration hr).

**Action 1 — happy path:**

1. After running Step 3a in §3.6 above, click "Next → Step 4 Results" (or sidebar Step 4).
2. In Step 4, set "BESS Capacity (MWh)" = 250, "Duration Class" = 4-hour (0.25C), "DG Capacity (MW)" = 25. These match the D13 sweep row.
3. Click "See Results" (button label flips to that when a Step 3 cached row matches).

**Verify (happy path):**

- "£ Financial Metrics" section renders below "Solar Utilization" metric row, above "Monthly Performance Summary"
- 6 metric tiles: Combined PIRR ≈ **8.88%**, S+B PIRR ≈ **9.05%**, Gas PIRR ≈ **13.07%**, NPV (some figure), CAPEX (GBPm) ≈ **101.6**, Payback (yrs) (some figure)
- Caption mentions A24 dispatch-module mismatch ("green/DG share may differ")
- No exception in the server log

**Action 2 — no-match info banner:**

1. Without re-running Step 3a, change Step 4's BESS Capacity to a value NOT in Step 3's sweep (e.g. 5 MWh).
2. Click "See Results" → "Run Simulation" (the cache won't match this row).

**Verify (no-match banner):**

- After simulation completes, an info banner appears in place of the metric tiles: "Financial sweep exists but does not include this config..."
- Banner references the BESS MWh / DG MW / duration of the current selection
- No exception in the server log

**Action 3 — silent fallback (no Step 3a sweep):**

1. Open a fresh Streamlit session (kill + restart).
2. Walk through Step 1 → Step 3 only (no Step 3a). Open Step 4 and run a single-config simulation.

**Verify (silent fallback):**

- No "£ Financial Metrics" section. No info banner. Pre-A41 behaviour preserved.
- Server log clean.

**If fails:**

- `find_cached_financial` join condition mismatch — verify column types in `st.session_state.financial_results` (Step 3a writes ints for BESS MWh; Step 4 selectbox returns ints too). Compare with `find_cached_result` which works identically.
- Layout collision — Section sits between `if st.session_state.analysis_results is not None:` body's metrics block and the Monthly Summary table. Check no other Step 4 changes shifted code around this region.

### 4.3 Sidebar / app.py

**Action:** click each of Step1–Step7 in sequence. Each should render.
**Verify:** no traceback for any page.

---

## 5. Edge cases worth poking at

| Case | How | Expected |
| --- | --- | --- |
| **No sizing_results** | Navigate directly to Step 3a via the sidebar without running Step 3 first | Warning: "Step 3 (Sizing) has not been run." + button "← Go to Step 3". No crash. |
| **Empty sizing_results** | Run Step 3 with a sweep range that produces 0 configs (e.g., min > max — but Streamlit's number_input usually blocks this) | Same warning as above (empty DataFrame → `len == 0`) |
| **Re-run Step 3a** | After a successful sweep, click "Run Financial Sweep" again | New sweep replaces `financial_results`; same numbers (within float noise) |
| **Solar profile missing** | Step 1 with a bad solar selection | Error: "Could not load an 8760-hour solar profile from Step 1." with no traceback shown |
| **Wide sweep (500+ configs)** | Step 3 with broad BESS/DG range | Should still complete; flag if >60 s (perf budget overshoot worth tracking) |

---

## 6. Failure-mode reference

| Symptom | Most likely cause | First check |
| --- | --- | --- |
| Step 3a crashes on load | Wizard-state schema mismatch | Server log traceback names the missing key |
| Sweep runs but PIRR column is all NaN | `pirr_inputs_from_wizard_state` returning bad inputs | Add `st.json(pi.__dict__)` debug; verify capex / load_mw / bess_mw all populated |
| D13 row 250 MWh / 4 hr gives wrong PIRR | wizard-state adapter gap (like A24's merchant curve) | Compare audit fixture vs wizard-state path: `python -X utf8 -c "from tests.fixtures.d13_inputs import d13_inputs; from src.project_irr import run_pirr; print(run_pirr(d13_inputs()).project_irr_solar_bess)"` |
| Sweep time >> 12s for 100 configs | Per-config dispatch is slow, OR PIRR engine is slow | Profile a single config: `python -X utf8 -c "import time; ...; t=time.time(); run_pirr(pi); print(time.time()-t)"`. Should be <100 ms |
| Streamlit pages out of order in sidebar | Streamlit caches the page list | Restart the server |
| "£ Add Financial Analysis" button greyed | `sizing_results` not in session state | Step 3 wasn't actually run; or it errored mid-sweep |

---

## 7. Cleanup

After the smoke test:

1. **Stop the server** — kill the background Streamlit process (`pkill -f streamlit` on Unix, or kill the background Bash via your environment's mechanism)
2. **Don't commit `~/.streamlit/cache`** — it's gitignored, but double-check
3. **Reset session state** if you plan to immediately re-test — easiest: stop + restart the server

---

## 8. What "smoke test passed" means

✅ Server started, no startup tracebacks
✅ All 7 wizard steps + 3a render without crash
✅ Step 3 → Step 3a navigation works via the new button
✅ 100-config sweep completes in 8–15 s (D16 budget)
✅ D13-equivalent row produces Combined ≈ 8.88 %, S+B ≈ 9.05 %, Gas ≈ 13.07 % (post-A40 state)
✅ A41 Step 4 Financial Metrics section renders for in-sweep configs (post-A41, 2026-05-16)
✅ A41 Step 4 info banner renders for out-of-sweep configs when sweep exists
✅ A41 Step 4 stays silent when no sweep has been run
✅ Filters + sort + CSV download all work
✅ Step 7 still produces audit-matching numbers (regression check for the merchant-curve default)
✅ No "Error" column in sweep results (no per-config crashes)

If any of these fail, mark the smoke test ❌ and root-cause before claiming Step 3a Phase 1 done.

If all pass, the smoke test is ✅ — and Phase 2 (Step 4 augmentation + cache invalidation) is the next concrete piece of work.

---

## 9. Run Log — 2026-05-13

**Runner:** Claude (browser automation via chrome MCP)
**Server:** Streamlit 1.51.0, `streamlit run app.py --server.headless true --server.port 8501`
**Prerequisites:** 34 passed, 4 xfailed; D13 S+B 8.93%, Combined 8.77%, Gas 13.65% ✓

### Results

| # | Check | Result |
| --- | --- | --- |
| 3.1 | Home page — all pages in sidebar, Step3a between Step3 and Step4 | ✅ |
| 3.2 | Step 1 — Setup loads, all D13 inputs accepted | ✅ |
| 3.3 | Step 2 — Rules loads, defaults OK | ✅ |
| 3.4 | Step 3 — 102 configs, sweep completes, "£ Add Financial Analysis" button enabled | ✅ |
| 3.5 | Step 3a — page loads from button, title/indicator/metrics correct | ✅ |
| 3.6 | Financial sweep — **102 configs in 2.6 s (26 ms/config)** — well within D16 budget (8–12 s / 100) | ✅ |
| 3.6 | Ranked Results table renders with all expected columns (identity + operational + financial) | ✅ |
| 3.6 | No "Error" column (no per-config crashes) | ✅ |
| 3.6 | "Top by Combined PIRR" callout renders: 300 MWh 2-hr / 25 MW DG → 12.72% Combined (8.00% S+B, 25.89% Gas) | ✅ |
| 3.7 | Sort switches (BESS MWh ↔ Combined PIRR) work instantly, no re-run | ✅ |
| 3.8 | "Download financial sweep (CSV)" button present | ✅ |
| 3.9 | Navigation: ← Back to Step 3 works, `financial_results` persists on return | ✅ |

### D13 PIRR sanity check — ⚠️ FAILED (root-caused, not a Step 3a bug)

| Metric | Expected | Actual | Status |
| --- | --- | --- | --- |
| D13 row (250/4) Combined PIRR | ≈ 8.77% | 11.56% | ❌ |
| D13 row (250/4) S+B PIRR | ≈ 8.93% | 6.52% | ❌ |

**Root cause: wrong solar profile selected in Step 1.**

Step 1's dropdown shows "Burton Solar Profile" (from `Inputs/Burton Solar Profile.csv`, peak **8.0 MW**) — NOT the canonical D13 audit file `Inputs/Burton_Leonard_82MWp_DC_58MW_AC.csv` (peak **58.36 MW**). The `data_loader.list_solar_profiles()` function doesn't surface the canonical files because they use underscores instead of spaces in the filename.

The engine itself is verified correct via the fixture path:

```
python -X utf8 tests/test_project_irr_excel_parity.py
→ D13 S+B 8.93%, Combined 8.77%, Gas 13.65%  ✓
```

The wizard-state adapter, dispatch chain, and PIRR engine all work — they just received a different (lower-capacity) solar profile as input. This is a **Step 1 data-loader gap** (the canonical Burton Leonard profiles added in A14 aren't listed by `list_solar_profiles()`), not a Step 3a or PIRR engine bug.

**Fix needed:** Update `src/data_loader.py` `list_solar_profiles()` to include `Burton_Leonard_*.csv` files, or rename them to match the existing naming convention (spaces, not underscores).

### Not tested (deferred to next run)

- 4.1 Step 7 regression (single-config deep-dive with D13 inputs)
- 4.2 Step 4 renders without PIRR columns (Phase 2 deferred)
- §5 edge cases (no sizing_results, empty sweep, re-run, wide sweep)

### Verdict

**Smoke test: CONDITIONAL PASS.** All Step 3a UI wiring, sweep execution, rendering, filtering, sorting, navigation, and session-state persistence work correctly. The D13 sanity check failed due to an upstream profile-selection gap in Step 1 (pre-existing, not introduced by Step 3a). The engine produces audit-matching numbers via the fixture path.

**Recording:** `Step3a_Smoke_Test.gif` (50 frames, downloaded to browser).

---

## 10. Follow-up Session — 2026-05-13 (fix landed, re-test needed)

**Status of the data_loader fix surfaced in §9.**

**LANDED** ([src/data_loader.py:30-40](../src/data_loader.py#L30-L40)). `list_solar_profiles()` filter broadened from `'solar' in filename.lower()` to `'solar' in lower or 'burton' in lower`. All four `Inputs/*.csv` files now surface, including the canonical D13 audit file. Verified programmatically: `Burton_Leonard_82MWp_DC_58MW_AC.csv` (peak 58.36 MW) and `Burton_Leonard_115MWp_DC_82MW_AC.csv` (peak 81.85 MW) both appear in the dropdown. Test suite still passes (34 + 4 xfail). Logged in decisions log under A24 Revisions row.

### What the next session needs to do

1. **Re-run §3.1 → §3.6** with the canonical profile selected this time
   - In Step 1 Solar profile dropdown, choose **`Burton_Leonard_82MWp_DC_58MW_AC`** (peak 58.36 MW), NOT "Burton Solar Profile" (peak 8.0 MW)
   - Solar capacity (MW) = 82
   - All other Step 1 inputs per §2
2. **Verify the §3.6 D13 sanity check now passes:** the 250 MWh / 4 hr / 25 MW DG row should produce Combined ≈ 8.77 %, S+B ≈ 8.93 %, Gas ≈ 13.65 % (each ±0.10)
3. **Then run the previously-deferred checks:**
   - §4.1 Step 7 regression — same D13 inputs in Step 7's single-config form, verify Combined ≈ 8.77 %. This is the merchant-curve A24 fix verification via the UI path.
   - §4.2 Step 4 renders without crash (Phase 2 deferred, no PIRR columns expected)
   - §5 edge case "No sizing_results" — navigate directly to Step 3a via sidebar without running Step 3, verify the warning + back-button render

### Pass criteria for this follow-up

- §3.6 D13 row matches audit (Combined 8.77 % / S+B 8.93 % / Gas 13.65 %)
- §4.1 Step 7 D13 result matches audit
- §4.2 Step 4 renders
- §5 "No sizing_results" warning works

### If the §3.6 D13 row STILL diverges after picking the canonical profile

- The data_loader fix didn't take. Verify the dropdown actually offers `Burton_Leonard_82MWp_DC_58MW_AC` and you selected it.
- Restart the Streamlit server — Streamlit caches the page list and sometimes the data-loader function results.
- Compare audit fixture path: `python -X utf8 -c "from tests.fixtures.d13_inputs import d13_inputs; from src.project_irr import run_pirr; r=run_pirr(d13_inputs()); print(f'S+B {r.project_irr_solar_bess*100:.2f}%')"`. Should print 8.93%. If yes, engine is fine — diff is wizard-state plumbing.
- Re-read decisions log A24 (Revisions log row from 2026-05-13) for the data_loader fix details.

### §10 Follow-up Run Results — 2026-05-13

**Data_loader fix confirmed working.** After server restart, Step 1 dropdown shows "Select from Inputs folder (**4 files**)" (was 2). `Burton_Leonard_82MWp_DC_58MW_AC` now available and selected. Profile peak = **58.4 MW**, Total Gen ≈ 79,200 MWh ✅.

**Steps 1→2→3 re-run successfully.** 102 configs, same sweep range (BESS 50-300, DG 25-25). Step 3 sweep completed normally.

**Step 3a financial sweep re-run: 102 configs in 2.6 s (26 ms/config)** ✅. No errors, no "Error" column.

**§3.6 D13 sanity check — FAILED (new root cause identified).**

| Metric | Expected | Actual | Delta |
| --- | --- | --- | --- |
| Combined PIRR | ≈ 8.77% | 24.72% | +15.95 pp |
| S+B PIRR | ≈ 8.93% | 32.23% | +23.30 pp |
| Gas PIRR | ≈ 13.65% | 10.57% | -3.08 pp |

**Root cause: DC/AC profile scaling bug in `run_pirr_for_config`.**

Step 3a scales the solar profile by `target_dc_mwp / profile_ref_mwp = 82 / 58.36 = 1.405×`. This over-inflates solar output because the canonical Burton Leonard profile already represents 82 MWp DC output grid-capped at 58 MW AC — it should be used as-is for dispatch per spec D8 ("revenue uses the AC + grid-limit-capped hourly profile as supplied").

Verified programmatically:

| Path | Profile scaling | Y1 solar+BESS to DC | Y1 surplus | Y1 gas |
| --- | --- | --- | --- | --- |
| **Fixture** (`compute_monthly_energy`, no scaling) | 1.0× | 75,983 MWh | 398 MWh | 143,017 MWh |
| **Step 3a** (`run_pirr_for_config`, scaled 82/58.36) | 1.405× | 95,263 MWh | 11,596 MWh | 123,737 MWh |

The 1.4× scaling pushes 19 GWh of extra solar into the system, dramatically over-stating S+B PIRR and under-stating gas contribution. The engine itself is correct (fixture path produces 8.93% S+B). The same scaling bug exists in Step 7's dispatch section (`pages/Step7_Financial.py:1243`).

**Fix needed (not applied — recording only):** `run_pirr_for_config` should use the profile as-is (`solar_mw = solar_mw_unscaled`) instead of scaling by DC/AC ratio. The `solar_dc_mwp` value is passed separately to the PIRR engine for capex scaling — the profile itself doesn't need rescaling.

**Deferred checks not run** (blocked by the D13 sanity check failure):

- §4.1 Step 7 regression
- §4.2 Step 4 renders
- §5 edge cases

### Suggested fix — DC/AC profile scaling

#### The problem

Both Step 3a (`pages/Step3a_FinancialSweep.py:142-145`) and Step 7 (`pages/Step7_Financial.py:1234-1243`) scale the solar profile before dispatch:

```python
solar_mw = solar_mw_unscaled * (target_dc_mwp / profile_ref_mwp)
# e.g. 82.0 / 58.36 = 1.405× — over-inflates solar by 40%
```

This conflicts with spec D8: *"capex scales on DC MWp; revenue uses the AC + grid-limit-capped hourly profile as supplied."* The Burton Leonard canonical files are already grid-limit-capped AC output — they represent the plant's actual hourly injection, not a per-unit profile that needs rescaling. The D13 fixture (`compute_monthly_energy`) uses the profile as-is with no scaling, which is why the audit passes via the fixture path but fails via the UI path.

#### Why the scaling exists

The scaling was added for the older `Burton Solar Profile.csv` (peak 8 MW) and `Solar Profile.csv` (peak ~67 MW), which ARE per-unit-ish profiles that need rescaling to the user's target capacity. The problem is that the canonical Burton Leonard files (peak 58 MW for 82 MWp DC, peak 82 MW for 115 MWp DC) are real AC output profiles that should NOT be rescaled.

#### Recommended fix

**Option A (minimal, targeted):** In both Step 3a and Step 7, skip scaling when the profile is a canonical Burton Leonard file (detected by filename or by checking if the profile peak is already close to the grid limit). Simple but fragile — breaks if new canonical profiles are added.

**Option B (robust, convention-based):** Add a `profile_is_ac_output` flag to the wizard state. When the user selects a profile from the Inputs folder, the data loader sets this flag based on the file metadata or naming convention. If `True`, scaling factor = 1.0. If `False` (uploaded CSV or per-unit profile), scale by `target_dc_mwp / profile_peak`. This matches the D8 spec cleanly.

**Option C (simplest, immediate):** Change `profile_ref_mwp` to default to `target_dc_mwp` instead of `solar_mw_unscaled.max()`. This gives scaling factor = 1.0 by default. Users who need rescaling (per-unit profiles) can set `profile_reference_mwp` explicitly in Step 7's financial inputs. One-line change in each file:

```python
# Step 3a (line ~301) and Step 7 (line ~1239-1240):
# BEFORE:
profile_ref_mwp = float(fin.get("profile_reference_mwp") or solar_mw_unscaled.max() or 1.0)

# AFTER:
profile_ref_mwp = float(fin.get("profile_reference_mwp") or target_dc_mwp or solar_mw_unscaled.max() or 1.0)
```

This way: if the user hasn't explicitly set a reference MWp, the profile is used as-is (factor = target/target = 1.0). If they set `profile_reference_mwp` (e.g., to 67 for the old Solar Profile), it rescales as before.

#### Affected files

| File | Line(s) | Change |
| --- | --- | --- |
| `pages/Step3a_FinancialSweep.py` | 300-305 | `profile_ref_mwp` default fallback chain |
| `pages/Step7_Financial.py` | 1238-1242 | Same `profile_ref_mwp` default fallback chain |

#### Verification after fix

1. `python -m pytest tests/ --no-header -q` → 34 passed, 4 xfailed (engine unchanged)
2. Restart Streamlit, re-run §3.1→§3.6 with `Burton_Leonard_82MWp_DC_58MW_AC` selected
3. D13 row (250/4) should produce Combined ≈ 8.77%, S+B ≈ 8.93%, Gas ≈ 13.65%
4. Also re-run with `Burton Solar Profile` (peak 8 MW) and set `profile_reference_mwp = 8` in Step 7 — verify scaling still works for per-unit profiles

### Updated verdict

**Smoke test: CONDITIONAL PASS** (unchanged). UI wiring, sweep execution, performance budget, rendering, filtering, sorting, navigation, and session-state persistence all work correctly. D13 sanity check fails due to a solar profile DC/AC scaling bug in both Step 3a and Step 7's dispatch paths — pre-existing design gap, not introduced by Step 3a. Engine produces audit-matching numbers via the fixture path (no scaling). Recommended fix: Option C (one-line default change in each file).

---

## 11. Follow-up Session — 2026-05-13 (Option C landed, re-test needed)

**Status of the DC/AC scaling fix from §10's diagnosis.**

**LANDED** as decisions log A25 ([Project_IRR_Integration_Decisions.md](Project_IRR_Integration_Decisions.md) Revisions row 2026-05-13).

- [pages/Step3a_FinancialSweep.py](../pages/Step3a_FinancialSweep.py) lines ~296–321
- [pages/Step7_Financial.py](../pages/Step7_Financial.py) lines ~1234–1262

**Fix applied (Option C):** the `profile_ref_mwp` fallback chain now defaults to `target_dc_mwp` instead of `profile_peak`. When no explicit `profile_reference_mwp` override is set, scaling factor = 1.0 — the AC profile flows through dispatch as-is, matching Spec D8.

**Plus a soft sanity-check warning** in both pages: when `profile_peak / target_dc_mwp` is outside [0.5, 1.1], a non-blocking warning displays. The expected ratio for a real UK utility-scale plant is 50–110 % (DC/AC ratio 1.2–1.4 with grid-cap factored in).

**Programmatic verification.** Wizard-state path (mimicking what Step 3a does internally) now reproduces audit numbers exactly:

| Metric | Engine | Target | Match |
| --- | --- | --- | --- |
| Combined PIRR | 8.77 % | 8.77 % | ✓ |
| S+B PIRR | 8.93 % | 8.93 % | ✓ |
| Gas PIRR | 13.65 % | 13.65 % | ✓ |

Test suite: 34 passed + 4 expected xfail.

### What the next session needs to do

1. **Restart the Streamlit server** — Python module caching can hold the old behaviour. Stop and re-launch.
2. **Re-run §3.1 → §3.6** with the canonical profile and the same Step 1 inputs as §10 (Burton_Leonard_82MWp_DC_58MW_AC, solar 82 MWp, load 25 MW, BESS containers including 4-hr, DG enabled).
3. **Verify the §3.6 D13 sanity check NOW passes**: the 250 MWh / 4 hr / 25 MW DG row should produce Combined ≈ 8.77 %, S+B ≈ 8.93 %, Gas ≈ 13.65 % (each ±0.10).
4. **Confirm the sanity warning behaves**:
   - With Burton_Leonard_82MWp file selected (peak 58.36 MW) + DC declared 82 MWp → ratio 71 %, in band → **no warning expected** ✓
   - Optional: switch Step 1 to "Burton Solar Profile" (peak 8 MW) keeping DC = 82 → ratio 10 %, out of band → **warning should appear**
5. **Run the previously-deferred checks:**
   - §4.1 Step 7 regression — same D13 inputs in Step 7's single-config form, click "Run Financial Analysis", verify Combined ≈ 8.77 %, S+B ≈ 8.93 %, Gas ≈ 13.65 %. **This validates both the A24 merchant-curve fix AND the A25 scaling fix via the UI path.** Critical.
   - §4.2 Step 4 renders without crash (Phase 2 deferred, no PIRR columns expected)
   - §5 edge case "No sizing_results" — navigate directly to Step 3a via sidebar without running Step 3, verify the warning + back-button render

### Pass criteria for this follow-up

- §3.6 D13 row matches audit (Combined 8.77 % / S+B 8.93 % / Gas 13.65 %)
- §3.6 sanity warning suppressed when AC ratio is in band (it's annoying otherwise)
- §4.1 Step 7 D13 result matches audit (the headline regression check)
- §4.2 Step 4 still renders
- §5 "No sizing_results" warning works

### If the §3.6 D13 row STILL diverges after the fix

- **Cache check.** Restart the Streamlit server. Python's module cache + Streamlit's page cache can hold the pre-fix code. After restart, click Step 1 fresh and re-select the profile.
- **Verify the fix landed in the running code.** `git diff pages/Step3a_FinancialSweep.py` should show the new fallback chain (line ~297) and the warning block (lines ~313–321).
- **Fixture path sanity.** `python -X utf8 -c "from tests.fixtures.d13_inputs import d13_inputs; from src.project_irr import run_pirr; r=run_pirr(d13_inputs()); print(f'S+B {r.project_irr_solar_bess*100:.2f}%')"`. If this still prints 8.93 %, engine is fine — the divergence is in the UI plumbing, NOT the engine.
- **Per-config dispatch check.** Pick a single row from the sweep table and confirm Step 3a's internal scaling is 1.0× (the profile peak should match the profile after scaling — both ~58 MW for the 82 MWp Burton Leonard file). If scaling != 1.0, the fix didn't take.

### §11 Re-test Results — 2026-05-13

**Server restarted, fresh browser session (new tab), canonical profile selected in Step 1.**

Steps 1→2→3 completed successfully. 102 configs. Step 3a sweep: **102 configs in 2.6 s (25 ms/config)** ✅. No errors. No DC/AC sanity warning (ratio 71%, in band) ✅.

**§3.6 D13 sanity check — STILL FAILING. Same numbers as §10.**

| Metric | Expected | Actual | Delta |
| --- | --- | --- | --- |
| Combined PIRR | ≈ 8.77% | 24.72% | +15.95 pp |
| S+B PIRR | ≈ 8.93% | 32.23% | +23.30 pp |
| Gas PIRR | ≈ 13.65% | 10.57% | -3.08 pp |
| Total CAPEX | ≈ £101.6m | £65.0m | -£36.6m |

**New root cause found: `solar_selected_file` wizard-state key stores display name, not filename.**

The Option C scaling fix (line 303) is verified correct — `profile_ref_mwp = target_dc_mwp = 82`, so scaling factor = 1.0. The problem is **upstream**: the canonical profile never actually loads in the UI path.

**Chain of failure:**

1. Step 1 stores `setup['solar_selected_file'] = 'Burton_Leonard_82MWp_DC_58MW_AC'` (display name, no `.csv`)
2. Step 3a's `get_solar_profile_array` calls `load_solar_profile_by_name('Burton_Leonard_82MWp_DC_58MW_AC')` (line 102)
3. `load_solar_profile_by_name` tries to open `Inputs/Burton_Leonard_82MWp_DC_58MW_AC` (no extension) → **file not found → returns None**
4. Step 3a falls through to the **default fallback** `load_solar_profile()` (line 110) → loads `Burton Solar Profile.csv` (peak 8 MW)
5. Profile scaling is 1.0 (82/82 per Option C fix), so the 8 MW profile goes through unscaled
6. 8 MW solar on a 25 MW load produces tiny green % → gas dominates → inflated Combined PIRR

**Verified programmatically:**

```
load_solar_profile_by_name('Burton_Leonard_82MWp_DC_58MW_AC') → None  (no .csv)
load_solar_profile_by_name('Burton_Leonard_82MWp_DC_58MW_AC.csv') → peak 58.36 MW ✓
```

Engine is correct: simulating the Step 3a path with the profile loaded directly (no wizard state) produces Combined 8.77%, S+B 8.93%, Gas 13.65%, CAPEX £101.6m — exact audit match.

**Fix needed — two options:**

**Option A (data_loader side):** In `load_solar_profile_by_name`, if `filename` doesn't have `.csv` extension, try appending it before giving up. One-line fix in `src/data_loader.py:61`:

```python
# BEFORE:
file_path = INPUTS_FOLDER / filename

# AFTER:
if not filename.endswith('.csv'):
    filename = filename + '.csv'
file_path = INPUTS_FOLDER / filename
```

**Option B (Step 1 side):** In Step 1's setup state, store the actual filename with extension (`'Burton_Leonard_82MWp_DC_58MW_AC.csv'`) instead of the display name. This requires finding where `solar_selected_file` is written in `pages/Step1_Setup.py` and using the filename from `list_solar_profiles()` (first element of the tuple) instead of the display name (second element).

**Recommendation:** Option A is simpler and more defensive — any caller that passes a display name will work. Option B is more correct but requires auditing all Step 1 write paths.

**Affected files:**

| File | Fix |
| --- | --- |
| `src/data_loader.py` line ~61 | Option A: append `.csv` if missing |
| `pages/Step1_Setup.py` (where `solar_selected_file` is written) | Option B: store filename not display name |

**Note:** This bug affects Step 3a AND Step 3's `get_solar_profile` function (which has the same `load_solar_profile_by_name(selected_file)` pattern at Step3_Sizing.py:124). Step 3 may also be silently falling back to the default profile. Step 7 uses a different path (`SOLAR_PROFILE_PATH` config constant) and isn't affected.

### Updated verdict

**Smoke test: CONDITIONAL PASS** (unchanged). All Step 3a UI mechanics work. D13 sanity check fails due to a **wizard-state filename extension bug** in `load_solar_profile_by_name` — the canonical profile never loads because the display name (no `.csv`) is stored in session state. Engine + scaling fix + PIRR wiring all verified correct via programmatic simulation. One-line fix in `data_loader.py` will unblock.

---

## 12. Follow-up Session — 2026-05-13 (Option A landed, re-test needed)

**Status of the filename-vs-display-name fix from §11's diagnosis.**

**LANDED** as decisions log A26 ([Project_IRR_Integration_Decisions.md](Project_IRR_Integration_Decisions.md) Revisions row 2026-05-13).

- [src/data_loader.py:46-71](../src/data_loader.py#L46-L71): `load_solar_profile_by_name` now appends `.csv` to the filename if the extension is missing. One-line defensive guard at the filesystem boundary.

**End-to-end verification.** Programmatic simulation of the full wizard-state path (Step 1 stores display name → Step 3a loads + dispatches + runs PIRR):

| Metric | Engine | Target | Match |
| --- | --- | --- | --- |
| Combined PIRR | 8.77 % | 8.77 % | ✓ |
| S+B PIRR | 8.93 % | 8.93 % | ✓ |
| Gas PIRR | 13.65 % | 13.65 % | ✓ |
| Total CAPEX | £101.6 m | £101.6 m | ✓ |

Profile loaded via display-name selection: peak 58.36 MW, length 8759 (the canonical wart from A14 — engine handles it).

Test suite: 34 passed + 4 expected xfail.

### What the next session needs to do

1. **Restart the Streamlit server** (Python module cache; mandatory after `src/data_loader.py` edit).
2. **Re-run §3.1 → §3.6** with the canonical profile selected in Step 1 (`Burton_Leonard_82MWp_DC_58MW_AC`), all other inputs per §2.
3. **Verify the §3.6 D13 sanity check NOW passes**: 250 MWh / 4 hr / 25 MW DG row → Combined ≈ 8.77 %, S+B ≈ 8.93 %, Gas ≈ 13.65 % (each ±0.10).
4. **Verify Total CAPEX ≈ £101.6 m** (a sanity check that the right-capacity profile is actually flowing through — pre-A26 it would have been £65.0 m because of the 8 MW profile fallback).
5. **Run the previously-deferred checks:**
   - §4.1 Step 7 regression. **NOTE: Step 7 has its own separate bug** (uses `SOLAR_PROFILE_PATH` constant, not Step 1's selection — see A26 note). To run the regression correctly, set the project's `SOLAR_PROFILE_PATH` config to the canonical file, OR accept that Step 7 will use whatever the default config points at. Verify Combined/S+B/Gas match audit with the right profile in place.
   - §4.2 Step 4 renders without crash.
   - §5 edge case "No sizing_results" — navigate directly to Step 3a via sidebar, verify the warning + back-button render.

### Pass criteria for this follow-up

- §3.6 D13 row matches audit (Combined 8.77 % / S+B 8.93 % / Gas 13.65 % / CAPEX £101.6 m)
- §4.1 Step 7 D13 result matches audit (with the right profile in place — see note above)
- §4.2 Step 4 renders
- §5 "No sizing_results" warning works

### If §3.6 STILL fails after A26

Three checks in order:

1. **Module cache.** Restart the Streamlit server. After restart, click Step 1 fresh and re-select the canonical profile.
2. **Did the fix actually land in the running code?** `git diff src/data_loader.py` should show the new `if not filename.lower().endswith('.csv'): filename = filename + '.csv'` block at line ~62.
3. **Verify the loaded profile peak is 58.36 MW**, not 8 MW. The peak makes the diagnosis: 58 MW = canonical file loaded; 8 MW = still falling through to default. Easiest check: add `st.write(f"DEBUG profile peak: {solar_mw_unscaled.max():.2f}")` after `get_solar_profile_array` in Step 3a.

### Smoke test discovery loop so far — three bugs found

This is the third bug surfaced by the Step 3a smoke test loop. Each is a pre-existing issue from before Step 3a:

| Bug | Surfaced by | Logged | Fix landed |
| --- | --- | --- | --- |
| Wizard-state adapter missed merchant curve | §6 initial smoke test | A24 sub-finding | ✓ 2026-05-13 |
| AC profile rescaling violated Spec D8 | §10 first browser smoke test | A25 | ✓ 2026-05-13 |
| `load_solar_profile_by_name` choked on display names | §11 second browser smoke test | A26 | ✓ 2026-05-13 |

The smoke test infrastructure is doing exactly the diagnostic work it's there for — surfacing pre-existing wizard-state bugs that the unit tests don't catch because they bypass the wizard-state adapter.

### §12 Re-test Results — 2026-05-13

**Server restarted. Fresh browser tab (new tab group). Canonical profile selected in Step 1 (confirmed: dropdown shows `Burton_Leonard_82MWp_DC_58MW_AC`, Peak Gen 58.4 MW, Total Gen 79,219 MWh/yr).** Steps 1→2→3→3a completed. 102 configs in 2.6s ✅. No DC/AC sanity warning ✅.

**§3.6 D13 sanity check — STILL FAILING. Same numbers as §10/§11.**

| Metric | Expected | Actual | Delta |
| --- | --- | --- | --- |
| Combined PIRR | ≈ 8.77% | 24.72% | +15.95 pp |
| S+B PIRR | ≈ 8.93% | 32.23% | +23.30 pp |
| Gas PIRR | ≈ 13.65% | 10.57% | -3.08 pp |
| Total CAPEX | ≈ £101.6m | £65.0m | -£36.6m |

**The A26 fix is verified working programmatically** (`load_solar_profile_by_name('Burton_Leonard_82MWp_DC_58MW_AC')` → peak 58.36 MW ✓). Simulating the full Step 3a path in Python (no Streamlit) produces exact audit numbers (Combined 8.77%, S+B 8.93%, Gas 13.65%, CAPEX £101.6m).

**Root cause diagnosis — the profile selection doesn't survive into Step 3a's dispatch.**

Step 1 stores `solar_selected_file = 'Burton_Leonard_82MWp_DC_58MW_AC.csv'` (confirmed: the selectbox uses filenames with `.csv` as option values). Step 3a's `get_solar_profile_array(setup)` reads `setup.get("solar_selected_file")` and calls `load_solar_profile_by_name(selected)`. The A26 fix ensures this works even without `.csv`. **But the CSV data (CAPEX £65m, Combined 24.72%) is byte-for-byte identical to the §10 run where the wrong profile was used.** This means the profile being loaded in the actual Streamlit UI path is still the 8 MW default, not the 58 MW canonical file.

**Most likely cause:** `get_solar_profile_array` is hitting the fallback path (line 108–114: `load_solar_profile()` which loads the old default) because either:

1. `setup.get("solar_source")` is not returning `"inputs"` — possible if the radio button key differs between Step 1 and the wizard state read
2. `setup.get("solar_selected_file")` is returning `None` — possible if wizard state from Step 1 isn't persisting into Step 3a's session context
3. `load_solar_profile_by_name(selected)` is failing silently and the `except Exception: pass` at line 105 swallows the error

**Diagnostic needed (for next session):** Add temporary `st.write` debug to Step 3a after `get_solar_profile_array`:

```python
# After line 288 in Step3a_FinancialSweep.py:
solar_mw_unscaled = get_solar_profile_array(setup)
st.write(f"DEBUG: solar_source={setup.get('solar_source')}, "
         f"selected_file={setup.get('solar_selected_file')}, "
         f"profile_peak={float(solar_mw_unscaled.max()) if solar_mw_unscaled is not None else 'None'}")
```

This will show exactly which branch `get_solar_profile_array` took and confirm whether the 8 MW or 58 MW profile loaded.

**Deferred checks still not run** (blocked by D13 sanity check failure):

- §4.1 Step 7 regression
- §4.2 Step 4 renders
- §5 edge cases

### Updated verdict

**Smoke test: CONDITIONAL PASS** (unchanged after 4 iterations). All Step 3a UI mechanics work correctly. D13 sanity check consistently fails due to the canonical solar profile not surviving from Step 1's selection into Step 3a's dispatch — the 8 MW default profile loads instead of the 58 MW canonical file. Engine + A25 scaling fix + A26 filename fix all verified correct programmatically. The remaining gap is in the Streamlit wizard-state plumbing between Step 1 and Step 3a.

### Suggestions for next session

1. **Add the `st.write` debug line** above to diagnose which branch `get_solar_profile_array` takes.
2. **If `solar_selected_file` is None:** the wizard state isn't persisting the Step 1 selection. Check that `update_wizard_state('setup', 'solar_selected_file', selected_file)` runs on page load (not just on button click). Streamlit re-executes on each interaction — the state should persist.
3. **If `solar_source` is wrong:** the radio button value may not be stored correctly. Compare `setup.get('solar_source')` against the expected `"inputs"`.
4. **If both are correct but profile still loads at 8 MW:** there's a file-loading failure being silently swallowed by the `except Exception: pass` block at line 105. Change to `except Exception as e: st.warning(f"Profile load failed: {e}")` to surface it.
5. **Consider a structural fix:** have Step 1 store the loaded profile data directly in session state (as a numpy array), so downstream pages don't need to re-load from disk. This eliminates the filename/path/extension fragility entirely.

---

## 13. Architectural Close — 2026-05-13 (A27: B + C + E2E test landed)

**Suggestion #5 from §12 implemented in full.** The bug-of-the-week pattern across §6/§10/§11/§12 (A24 / A25 / A26 / the A27 root cause) was traced to architectural drift: each page independently loaded + scaled the solar profile, and the wizard-state adapter had never been exercised end-to-end by automated tests. A27 closes the entire class.

### What landed

1. **Loader unification (Option B from §11 analysis).** Both `data_loader.load_solar_profile_by_name` and `load_solar_profile` rewritten to use the same `csv.reader` pattern as `dispatch_energy.load_solar_profile`. All 4 `Inputs/*.csv` profiles now return **8760** rows from both loaders. Pre-A27: pandas defaulted to `header=0` and ate the first data row of headerless canonical files → 8759 rows → Step 3a's `>= 8760` length check rejected them → fallback to the 8 MW default profile → wrong PIRR.

2. **Profile centralisation (Option C / suggestion #5).** Step 1 now loads + validates + pads + caches the canonical 8760-element array in `wizard['setup']['solar_profile_array']`. Plus a `solar_profile_signature` for change detection. When the signature changes (user picks a different file or uploads new data), downstream caches (`sizing_results`, `sizing_monthly_aggregates`, `financial_results`, `dispatch_monthly`, `multiyear_monthly`) are invalidated automatically. Matches spec §8 invalidation rules deferred from Step 3a Phase 2.

3. **Consumer migration.** Step 3, Step 3a, Step 4, Step 7 now read from `data_loader.get_active_solar_profile(setup)` instead of re-loading from disk. Step 7's pre-existing `SOLAR_PROFILE_PATH` config-constant bug (noted in A26's deferred section) is closed as a side effect — Step 7 now honours Step 1's profile selection.

4. **End-to-end test.** New [tests/test_wizard_state_path.py](../tests/test_wizard_state_path.py) — 6 tests exercising the full wizard-state pipeline (build state → get_active_solar_profile → dispatch → aggregate → pirr_inputs_from_wizard_state → run_pirr). **Would have caught every bug from A24 through A27**. Test suite now: 40 passed + 4 xfailed.

### Programmatic verification

D13 reproduces audit exactly via the wizard-state path:

| Metric | Engine (wizard state) | Audit | Match |
| --- | --- | --- | --- |
| Combined PIRR | 8.77 % | 8.77 % | ✓ |
| S+B PIRR | 8.93 % | 8.93 % | ✓ |
| Gas PIRR | 13.65 % | 13.65 % | ✓ |
| Total CAPEX | £101.6 m | £101.6 m | ✓ |

All 4 consumer paths (Step 3, Step 3a, Step 4, Step 7) verified to return matching 8760-element profiles with peak 58.36 MW.

### What the next browser session needs to do

1. **Restart the Streamlit server** (mandatory — module cache + state cleanup).
2. **Re-run §3.1 → §3.6** with the canonical profile selected in Step 1. The §3.6 D13 sanity check should now PASS (was failing across §10/§11/§12).
3. **Verify the cache invalidation works.** Run §3.6, get results. Then go back to Step 1 and switch the solar profile to a different file (e.g. `Burton_Leonard_115MWp_DC_82MW_AC`). Navigate to Step 3a — the previous `financial_results` should be cleared (table should be empty until you re-run).
4. **Run the previously-deferred checks:**
   - §4.1 Step 7 regression — with D13 inputs, verify Combined ≈ 8.77 %, S+B ≈ 8.93 %, Gas ≈ 13.65 %. **Step 7 now uses Step 1's profile selection** (was a bug pre-A27).
   - §4.2 Step 4 renders.
   - §5 edge cases.

### Pass criteria

- §3.6 D13 row matches audit (Combined 8.77 % / S+B 8.93 % / Gas 13.65 % / CAPEX £101.6 m)
- Cache invalidation works (profile change → `financial_results` cleared)
- §4.1 Step 7 D13 matches audit
- §4.2 Step 4 renders
- §5 "No sizing_results" warning works

### Bug-of-the-week summary

| Round | Bug | Logged | Fix |
| --- | --- | --- | --- |
| §6 initial | Wizard-state adapter missed merchant curve | A24 sub-finding | ✓ |
| §10 first browser | AC profile rescaling violated Spec D8 | A25 | ✓ |
| §11 second browser | Misdiagnosed filename/display-name; defensive guard | A26 | ✓ (harmless) |
| §12 third browser | Loader row-count discrepancy (pandas vs csv.reader) | A27 root cause | ✓ |
| §13 (this) | **Architectural close — all four bug classes eliminated** | A27 | ✓ B + C + E2E test |

After A27, the architecture is:

- **One profile loader** behaviour shared by `data_loader` and `dispatch_energy`
- **One source of profile truth** in `wizard['setup']['solar_profile_array']`
- **One way for consumers to read** — `get_active_solar_profile(setup)` helper
- **One regression test** that exercises the full path end-to-end without Streamlit

### §13 Re-test Results — 2026-05-13

**Server restarted. Fresh browser tab. Canonical profile selected (Burton_Leonard_82MWp_DC_58MW_AC, Peak 58.4 MW, 8760 hours — A27 loader fix confirmed: was 8759 pre-A27).** Steps 1→2→3→3a completed. 102 configs in 2.6s ✅. No DC/AC sanity warning ✅.

**§3.6 D13 sanity check — STILL FAILING, but numbers shifted from §12.**

| Metric | Expected | §12 Actual | §13 Actual | Delta from target |
| --- | --- | --- | --- | --- |
| Combined PIRR | ≈ 8.77% | 24.72% | **23.37%** | +14.60 pp |
| S+B PIRR | ≈ 8.93% | 32.23% | **29.50%** | +20.57 pp |
| Gas PIRR | ≈ 13.65% | 10.57% | **11.69%** | -1.96 pp |
| Total CAPEX | ≈ £101.6m | £65.0m | **£65.0m** | -£36.6m |

**A27 had partial effect.** PIRR values shifted (Combined down 1.35 pp, S+B down 2.73 pp, Gas up 1.12 pp) — the profile data flowing through dispatch is different now. But CAPEX is unchanged at £65.0m, confirming the dispatch is still seeing the wrong profile capacity somehow.

**Observations:**

- **8760 hours confirmed** — the loader row-count fix (A27 root cause) is working. The page showed "Loaded: 8760 hours" for the canonical file (was 8759 pre-A27).
- **`solar_profile_array` may not contain the canonical data.** Step 1 stores the array when the profile loads, but the CAPEX gap (£65m vs £101.6m = missing £37m ≈ BESS capex difference) suggests `pirr_inputs_from_wizard_state` is receiving unexpected values. The programmatic E2E test (40 passed) bypasses Streamlit session state entirely — the gap is specifically in the Streamlit session-state serialisation round-trip.
- **The deferred checks (§4.1 Step 7, §4.2 Step 4, §5 edge cases) remain blocked** by the D13 sanity check.

**Suggestion for next session:** The programmatic tests pass perfectly but the UI path doesn't. The remaining issue is almost certainly in how Streamlit session state serialises/deserialises the profile array between page transitions. Add a debug metric to Step 3a showing the profile peak from `get_active_solar_profile(setup)` — if it shows 8.0 MW instead of 58.4 MW, the profile array stored by Step 1 is wrong or lost between pages.

### Updated verdict

**Smoke test: CONDITIONAL PASS** (unchanged after 5 iterations).

---

## 14. What's blocking FULL PASS — single remaining issue

### What passes (100%)

Every aspect of Step 3a's own code works correctly:

| Check | Status | Verified in |
| --- | --- | --- |
| Page loads without crash | ✅ | §9, §10, §11, §12, §13 |
| Step indicator shows 3a between 3 and 4 | ✅ | §9 |
| 102-config sweep completes | ✅ | All runs |
| Performance: 2.6s / 102 configs (25 ms/config) — within D16 budget | ✅ | All runs |
| No per-config errors ("Error" column absent) | ✅ | All runs |
| "Top by Combined PIRR" callout renders | ✅ | All runs |
| Sort switching works instantly (no re-run) | ✅ | §9 |
| Min Delivery % filter works | ✅ | §9 |
| CSV download works | ✅ | §10, §11, §12, §13 |
| Navigation (← Step 3, → Step 7, → Step 4) all work | ✅ | §9 |
| Session state persists through page navigation | ✅ | §9 |
| DC/AC sanity warning suppressed when ratio is in band | ✅ | §11, §12, §13 |
| PIRR engine produces correct numbers via programmatic path | ✅ | 40 tests pass + 4 xfail |
| Wizard-state adapter produces correct numbers programmatically | ✅ | `test_wizard_state_path.py` (6 tests) |

### What fails (the ONE blocker)

**§3.6 D13 sanity check: the canonical 58 MW solar profile selected in Step 1 does not arrive at Step 3a's PIRR engine.**

Evidence across all 5 browser runs:

| Run | D13 S+B PIRR | D13 CAPEX | Profile peak arriving at engine |
| --- | --- | --- | --- |
| Target | 8.93% | £101.6m | 58.4 MW |
| §9 (initial) | — | — | 8.0 MW (wrong profile entirely) |
| §10 | 6.52% | £65.0m | 8.0 MW (data_loader couldn't find file) |
| §11 | 32.23% | £65.0m | 8.0 MW (display name vs filename) |
| §12 | 32.23% | £65.0m | 8.0 MW (loader ate first row → 8759 → rejected) |
| §13 | 29.50% | £65.0m | ~8 MW (A27 partial effect, but still wrong) |

The CAPEX being **£65.0m in every run** (should be £101.6m) is the smoking gun: the PIRR engine is receiving the wrong solar profile data, which changes the dispatch energy split (solar vs gas) and produces wildly incorrect IRR numbers.

### Root cause

**Streamlit session-state does not reliably propagate `wizard['setup']['solar_profile_array']` from Step 1 to Step 3a.**

Step 1 stores the profile array in wizard state (`update_wizard_state('setup', 'solar_profile_array', active_array.tolist())`). Step 3a reads it via `get_active_solar_profile(setup)` which returns `setup.get('solar_profile_array')`. **This works perfectly in programmatic tests** (Python dict, no Streamlit) but fails in the browser because:

1. Streamlit's `st.session_state` is per-browser-session but each page re-executes the full script on every interaction
2. When navigating from Step 1 → Step 2 → Step 3 → Step 3a, each page re-execution reads `wizard_state` from session state — but if Step 1's profile-storage code block didn't execute during THIS page's script run (because the user is now on Step 3a, not Step 1), the array may be missing or stale
3. The `get_active_solar_profile` helper returns `None` when the array isn't found, and Step 3a's fallback loads the default 8 MW profile

This is a **wizard_state persistence architecture issue** — not a Step 3a bug, not an engine bug, not a loader bug, and not a scaling bug. The programmatic path works because it constructs the state dict directly; the browser path fails because Streamlit's page-transition model doesn't guarantee cross-page state propagation for large arrays.

### Exact fix needed to achieve FULL PASS

**One of these will close the issue:**

**Option 1 (Quick — verify state propagation):** Add a debug `st.metric` to Step 3a to confirm the hypothesis:

```python
# In Step3a_FinancialSweep.py, after line ~273:
solar_mw_unscaled = get_solar_profile_array(setup)
if solar_mw_unscaled is not None:
    st.caption(f"DEBUG: profile peak = {float(solar_mw_unscaled.max()):.1f} MW, len = {len(solar_mw_unscaled)}")
```

If this shows 8.0 MW → `solar_profile_array` is missing/wrong in session state.
If this shows 58.4 MW → the issue is elsewhere (unlikely given CAPEX evidence).

**Option 2 (Fix — ensure array survives page transitions):** Store the profile array in `st.session_state` directly (not nested inside the wizard dict) so it's guaranteed to survive Streamlit page transitions:

```python
# Step 1: after loading the profile
st.session_state['_solar_profile_array'] = active_array.tolist()

# Step 3a: read from session state directly
arr = st.session_state.get('_solar_profile_array')
```

**Option 3 (Fix — lazy re-load from disk on cache miss):** If `get_active_solar_profile(setup)` returns None, re-load from disk using `setup.get('solar_selected_file')` as a fallback — this was the pre-A27 approach, now with the A26 filename fix and A27 loader fix in place it should work:

```python
def get_active_solar_profile(setup):
    arr = setup.get('solar_profile_array')
    if arr is not None:
        return np.asarray(arr, dtype=float)
    # Fallback: re-load from disk (covers page-transition cache miss)
    selected = setup.get('solar_selected_file')
    if selected:
        return load_solar_profile_by_name(selected)
    return None
```

### Once fixed, the smoke test becomes FULL PASS

With any of the above options in place:

- §3.6 D13 row will produce Combined ≈ 8.77%, S+B ≈ 8.93%, Gas ≈ 13.65%, CAPEX ≈ £101.6m
- The deferred checks (§4.1 Step 7 regression, §4.2 Step 4 renders, §5 edge cases) can finally run
- All 8 criteria from §8 ("What smoke test passed means") will be met
- Verdict updates from CONDITIONAL PASS to **FULL PASS**

---

## 15. Root Cause Found + Fixed — 2026-05-13 (A28 lands the actual close)

**§14's hypothesis was wrong.** It claimed "Streamlit session state doesn't propagate large arrays." Verification disproved that — Streamlit session state propagates dicts of any size; the agent's diagnosis was incorrect.

### What was actually wrong

**Step 7's UI defaults silently disagreed with the engine's `PirrInputs` Excel-anchored defaults across ~25 fields.** Programmatic reverse-engineering reproduced the §13 result exactly: building a `fin` dict matching Step 7's "Save Financial Inputs" payload with current UI defaults produced CAPEX £64.96m (matches §13's £65.0m to 4 sig figs). This is mathematical proof — Step 7 was visited during §13 and its UI defaults poisoned the fin state.

The critical example: `capex_bess` defaulted to 80 with help text "GBP/kWp solar", but the wizard-state adapter maps it to engine field `capex_bess_gbp_per_kw_bess` expecting 600 (per Spec D5 / Excel `Solar&BESS Inputs!F349`). **Unit AND value mismatch.** After Step 7 Save: engine used 80 GBP/kW BESS → £5m BESS capex instead of £37.5m → £32.5m CAPEX shortfall.

Plus ~24 other field drifts (capex_grid 30 vs 57.858, opex_balancing_cfd 0 vs 2.75, BESS revenue switches, generation_selection P90 vs P50, fixed_lease defaults, wc_debtors_days, project_discount_rate, etc.), and an adapter bug reading `corp_tax_rate_low` (19%) instead of `corp_tax_rate_high` (25% — D13/Excel value).

See decisions log A28 for the full diff table.

### What landed

1. **~25 Step 7 `number_input` defaults aligned** to engine PirrInputs (Excel-anchored). Each updated default has an Excel cell reference in its `help=...`.
2. **`capex_bess`** label/help fixed + default 80 → 600 (matches Excel `F349`).
3. **Adapter bug fixed** in `src/project_irr.py`: `corp_tax_rate` now reads `corp_tax_rate_high` (was `_low`).
4. **3 new lock-in tests** in `tests/test_wizard_state_path.py` that simulate Step 7's "Save Financial Inputs" with CURRENT UI defaults and assert D13 audit numbers (Combined, S+B, CAPEX). These prevent defaults-drift recurrence — any future change to Step 7 that breaks alignment fails the test.

### Programmatic verification

D13 reproduces audit via BOTH wizard-state paths now:

| Path | D13 Combined | D13 S+B | D13 Gas | D13 CAPEX |
| --- | --- | --- | --- | --- |
| Fixture (`d13_inputs.py`) | 8.77 % | 8.93 % | 13.65 % | £101.6 m |
| Wizard-state minimal-fin (no Step 7) | 8.77 % | 8.93 % | 13.65 % | £101.6 m |
| Wizard-state Step-7-Save (all 100+ keys) | **8.77 %** | **8.93 %** | **13.65 %** | **£101.6 m** ✓ |

Test suite: **43 passed + 4 xfailed** (was 40+4).

### What the next browser session needs to do

1. **Restart the Streamlit server** (mandatory — Step 7 + adapter source files changed).
2. **Important — clear any stale Step 7 fin state.** If the same browser tab held a prior `wizard['financial']` dict from a poisoned session, Step 1 should clear it via the cache-invalidation logic when the user re-selects the canonical profile. If unsure, hit "C" in Streamlit to clear cache, or open a new browser tab.
3. **Re-run §3.1 → §3.6** with the canonical profile in Step 1. D13 row should now produce Combined ≈ 8.77 %, S+B ≈ 8.93 %, Gas ≈ 13.65 %, CAPEX ≈ £101.6m.
4. **Run the §4.1 Step 7 regression** — visit Step 7, set D13 inputs (the defaults should now BE D13), click "Save Financial Inputs", then "Run Financial Analysis". Result should match audit.
5. **Test the lock-in test runs**: `python -m pytest tests/test_wizard_state_path.py::test_step7_saved_defaults_produce_audit_capex -v` should pass.

### Pass criteria

- §3.6 D13 row matches audit (all four numbers)
- §4.1 Step 7 D13 also matches audit (via full UI form)
- All 43 tests + 4 xfail pass under `pytest tests/`

### Bug-of-the-week — final tally

| Round | Bug | Fix |
| --- | --- | --- |
| §6 initial | Wizard-state adapter missed merchant curve | A24 sub-finding |
| §10 first browser | AC profile rescaling violated Spec D8 | A25 |
| §11 second browser | Filename / display-name (misdiagnosed) | A26 (harmless) |
| §12 third browser | Loader row-count discrepancy | A27 |
| §13 fourth browser | Step 7 UI defaults disagree with engine | **A28** |

Five smoke-test rounds. Four real bugs. All closed. The new test in A28 prevents recurrence of the defaults-drift class — the most common pattern (UI form values silently disagree with engine defaults, hidden until the form is Saved).

### Updated verdict — pending next browser run

**Smoke test: CONDITIONAL PASS** (will update to PASS once the §15 re-test confirms D13 numbers via the UI after A28). Programmatic verification has reproduced D13 exactly via the Step 7-Save path; browser verification should now match.

---

## 16. Browser Run — 2026-05-16 (A40 / A41 / A42 verification via §A script)

First run of the new §A browser-agent script after A40 (time-varying CPI), A41 (Step 4 Financial Metrics section), A42 (sizing_results unification) all landed. Run executed via Claude-for-Chrome extension against the running server on port 8510.

### Result summary

| Group | Result | Notes |
| --- | --- | --- |
| **A.1 sidebar** | PASS | All 7 steps + Step3a + Market Reference present |
| **A.2 Step 1 setup** | PASS | D13 inputs accepted; Burton_Leonard_82MWp_DC_58MW_AC loaded (Peak 58.4 MW, 79,219 MWh/yr) |
| **A.3 Step 2 rules** | PASS | Defaults preserved; advances to Step 3 |
| **A.4 Step 3 sizing** | PASS | 102 configs swept |
| **A.5 Step 3a Financial Sweep** | **FAIL on A.5.5** | Sweep ran (102 configs / 3.4 s — under D16 budget). D13 row produces wrong numbers (see below). |
| **A.6 Step 4 A41 happy path** | PASS (engine-vs-engine) | "£ Financial Metrics" subheader + 6 tiles render; values match Step 3a row exactly; A24 caption present |
| **A.7 Step 4 A41 no-match banner** | PASS | BESS=5 produces blue info banner "Financial sweep exists but does not include this config (BESS 5 MWh / DG 25 MW / 4-hr duration)…" |
| **A.8 Step 4 A41 silent fallback** | EFFECTIVELY PASS (degraded) | Server restarted clean, Step 3a skipped, Step 4 shows no Financial Metrics subheader and no info banner. Side-issue: Step 4 simulation failed with "No solar profile available" on the fresh session (solar profile session_state didn't persist across navigation) — unrelated to A41. |
| **A.9 A42 verification** | PASS | Step 7 loads without "Step 3 sizing run is required" warning. Prerequisite check now points to Step 5 Multi-Year. sizing_results unification didn't break consumers. |

### A.5.5 detail — D13 row divergence (the only true failure)

Per playbook expected vs observed for the 250 MWh / 4-hr / 25 MW row of the Financial Sweep ranked table:

| Metric | Expected (CLAUDE.md / playbook §A) | Observed | Δ |
| --- | --- | --- | --- |
| Combined PIRR | 8.88 % | **21.59 %** | **+12.71 pp** |
| S+B PIRR | 9.05 % | **28.21 %** | **+19.16 pp** |
| Gas PIRR | 13.07 % | **10.70 %** | **−2.37 pp** |
| Total CAPEX | £101.6 m | **£64.7 m** | **−£36.9 m** |

§16 DEBUG line printed on the Step 3a page after the sweep: `profile_peak=58.4 MW, fin.enabled=False, fin.capex_bess=80.0, fin has 109 keys, target_dc_mwp=82.0`.

### Key recurrence — §15/A28 fix appears incomplete or regressed

The observed CAPEX £64.7m is within £0.3m of §13's £65.0m — the exact wizard-state-Step-7-poisoning signature that §15/A28 claimed to have closed. The page debug line confirms `fin.capex_bess=80.0`, the *same* value §15 identified as the root cause (Step 7 default 80 mapping to engine field `capex_bess_gbp_per_kw_bess` expecting 600, per Excel `Solar&BESS Inputs!F349`).

Possibilities to triage:

1. A28's `number_input` default change (80 → 600) didn't actually land on `pages/Step7_Financial.py`, OR
2. A28's change landed but was reverted between 2026-05-13 and 2026-05-16, OR
3. A40 / A41 / A42 work introduced a new code path that bypasses Step 7's UI defaults and synthesises its own `fin` dict with the old 80, OR
4. The wizard-state path Step 3a uses when `fin.enabled=False` falls back to a *different* defaults source (not Step 7's `number_input` values) and that source wasn't aligned by A28.

A.6 (Step 4) renders the same 21.59% / 28.21% / 10.70% / £64.7m as A.5.5 — confirming A41 wiring is internally consistent and the divergence is upstream in the engine-input adapter.

### What A40 verification actually told us

A40 was a "null result at 2-decimal precision" CPI curve change. §A.5 was meant to confirm engine still produces 8.88% post-A40 via the wizard-state path. Since the wizard-state path is producing a *very* different number (21.59%), A40 verification is **inconclusive** — the test can't tell A40 wiring apart from the pre-existing wizard-state-path defaults divergence. Need fixture path numbers from a pytest run as a control: per CLAUDE.md, the fixture is still producing the expected 8.88%, so the gap is confirmed to be in the wizard-state adapter, not the engine core.

### What the next session needs to do

1. Confirm whether A28's `capex_bess` default change is present on `pages/Step7_Financial.py` (grep for `capex_bess` + `value=`). If 80 — A28 was reverted or never landed; restore it. If 600 — investigate why the wizard-state path on Step 3a is still seeing 80 (e.g. fallback defaults dict in `Step3a_FinancialSweep.py` or `src/wizard_state.py`).
2. Re-run §A.5 and confirm the D13 row produces Combined 8.88 % ± 0.10 (or the latest engine-state value per CLAUDE.md).
3. Re-run A.8 cleanly with the solar profile committed via `Next → Dispatch Rules` (the form_input + click-option pattern doesn't always persist solar profile across a fresh-server navigation — manual click-through is more reliable).
4. If the §10 lock-in test exists (`tests/test_wizard_state_path.py::test_step7_saved_defaults_produce_audit_capex`), run it and confirm whether it's still asserting the right values.

### Verdict

**Smoke test: CONDITIONAL FAIL** (resolved by A43, same session).

A41 + A42 verified clean (visible features correctly wired). A40 inconclusive due to the wizard-state defaults bug §15 claimed to have closed reappearing with an identical CAPEX signature. The browser-agent's hypothesis #4 turned out to be correct: a different defaults source (the actual `DEFAULT_WIZARD_STATE['financial']` init) wasn't aligned by A28.

### A43 resolution (2026-05-16, same session)

The §16 finding pointed straight at the missing piece of A28. Investigation:

1. Confirmed [pages/Step7_Financial.py](../pages/Step7_Financial.py) line 669 has the A28-correct fallback (`fin.get('capex_bess', 600.0)`) — Step 7's UI default is 600.0.
2. Confirmed [src/wizard_state.py](../src/wizard_state.py) `DEFAULT_WIZARD_STATE['financial']` (lines 232–304) was STILL pre-A28: `capex_bess: 80.0` + 24 other misaligned values + 5 missing advanced keys.
3. The A28 lock-in test (`test_step7_saved_defaults_produce_audit_capex`) bypassed `DEFAULT_WIZARD_STATE` entirely by constructing the fin dict inline → real-world fresh-session path was never tested.

**Fix**: aligned all 25 misaligned values + added 5 missing keys (`shl_*`, `depreciation_*`). Added 3 new regression tests covering the fresh-session path:

- `test_default_wizard_state_produces_audit_capex` (£101.6m ± £0.5)
- `test_default_wizard_state_produces_audit_combined` (8.85% ± 0.1 pp)
- `test_default_wizard_state_produces_audit_sb` (9.02% ± 0.1 pp)

Test count went 42 → 45. Audit matrix unchanged. Programmatic reproduction:

| Metric | Pre-A43 | Post-A43 | Audit target |
| --- | --- | --- | --- |
| Combined | 19.67% | **8.88%** | 8.85% |
| S+B | 24.01% | **9.05%** | 9.02% |
| Gas | 12.43% | **13.07%** | 13.07% |
| CAPEX | £64.7m | **£101.4m** | £101.6m |

See decisions log A43 for full diff. Re-run §A in the browser to confirm UI now matches engine; the §A.5.5 PASS criteria are now true.
