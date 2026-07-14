# BESS & DG Sizing Tool - Project Handoff Document

**Purpose:** Complete context for continuing development in a new conversation  
**Last Updated:** 2025-12-01  
**Current Step:** Step 3 - Sizing Logic Specification (COMPLETE)  
**Templates Finalized:** 0, 1, 2, 3, 4, 5, 6

---

## QUICK START: How to Resume This Project

Share this document and state:

> "I am continuing development of a BESS & DG Sizing Tool. All 7 templates (0-6) are finalized. Sizing iteration logic is complete. We need to proceed with:
> (a) Implementing all templates in code.
>
> All requirements, decisions, and dispatch logic are in the attached documents. Please review and continue."

**Documents to Share:**

1. This file (PROJECT_HANDOFF.md) - Project overview and decisions
2. REQUIREMENTS_SPEC.md - Formal specification (includes sizing logic)
3. TEMPLATE_0_Solar_BESS_Dispatch.md - Finalized dispatch logic
4. TEMPLATE_1_Green_Priority_Dispatch.md - Finalized dispatch logic with DG (v1.2)
5. TEMPLATE_2_DG_Night_Charge_Dispatch.md - Finalized dispatch logic with proactive DG (v1.2)
6. TEMPLATE_3_DG_Blackout_Window_Dispatch.md - Finalized dispatch logic with time restrictions (v1.1)
7. TEMPLATE_4_DG_Emergency_Only_Dispatch.md - Finalized dispatch logic with SoC-triggered DG (v1.1)
8. TEMPLATE_5_DG_Day_Charge_Dispatch.md - Finalized dispatch logic with silent nights (v1.1)
9. TEMPLATE_6_DG_Night_SoC_Trigger_Dispatch.md - Finalized dispatch logic with green days (v1.2)

---

## 1. Project Overview

### 1.1 What We're Building

An internal tool for the investment team to size Battery Energy Storage Systems (BESS) for colocated Solar + BESS + optional DG projects in the European market.

### 1.2 Core Question Answered
>
> "Given this solar profile, which size of BESS and DG gives me highest availability with lowest solar wastage in different scenarios while providing maximum load delivery hours or 100% delivery?"

### 1.3 Primary Users

Investment analysts evaluating energy projects

### 1.4 What the Tool Does

- Takes load profile and solar profile as inputs (8760 hourly values)
- Simulates hourly energy dispatch for a full year
- **Iterates through BESS capacities × duration classes × DG sizes**
- **Outputs comparison table with all configurations**
- User decides optimal configuration from results
- Exports results to dashboard and Excel

### 1.5 Current Process Being Replaced

- Excel spreadsheets
- Gut feel / manual estimation

---

## 2. MVP Scope

### 2.1 In Scope

| Feature | Status |
| --------- | -------- |
| Solar + BESS topology (no grid, no DG) | Template 0 FINALIZED |
| Solar + BESS + DG topology | Templates 1-6 FINALIZED |
| Predefined dispatch templates | 7 templates defined |
| **BESS sizing iteration with duration classes** | ✓ SPECIFIED |
| **DG sizing iteration** | ✓ SPECIFIED |
| **Comparison table output** | ✓ SPECIFIED |
| Success metrics (delivery hours, unserved energy, curtailment) | ✓ SPECIFIED |
| Dashboard output | Specified |
| Excel export | Specified |

### 2.2 Out of Scope (V2)

- Grid connectivity
- Custom dispatch rules (IF-THEN builder)
- Financial modeling (IRR, NPV, LCOE)
- Degradation modeling / 10-year sizing
- Sub-hourly resolution
- Inverter clipping / AC limits
- Cost estimates in output
- Auto-recommendation of optimal config

---

## 3. System Topologies

| ID | Config | MVP Status |
| ---- | -------- | ------------ |
| A | Solar + BESS | ✓ In Scope (Template 0) |
| B | Solar + BESS + Grid | ✗ Deferred |
| C | Solar + BESS + DG | ✓ In Scope (Templates 1-6) |
| D | Solar + BESS + DG + Grid | ✗ Deferred |

---

## 4. Dispatch Templates

| # | Template Name | Topology | Status |
| --- | --------------- | ---------- | -------- |
| 0 | Solar + BESS Only | A | **FINALIZED** |
| 1 | Green Priority | C | **FINALIZED (v1.2)** |
| 2 | DG Night Charge | C | **FINALIZED (v1.2)** |
| 3 | DG Blackout Window | C | **FINALIZED (v1.1)** |
| 4 | DG Emergency Only | C | **FINALIZED (v1.1)** |
| 5 | DG Day Charge | C | **FINALIZED (v1.1)** |
| 6 | DG Night SoC Trigger | C | **FINALIZED (v1.2)** |

### 4.1 Template 0: Solar + BESS Only (FINALIZED)

- **Merit Order:** Solar → BESS → Unserved
- **Charging:** BESS from excess solar only
- **Logic:** See TEMPLATE_0_Solar_BESS_Dispatch.md
- **Status:** SME validated, ready for implementation

### 4.2 Template 1: Green Priority (FINALIZED v1.2)

- **Merit Order:** Solar → BESS → DG → Unserved
- **Charging:** BESS from excess solar; optionally from DG excess
- **DG Behavior:** Full Capacity when ON (reactive only)
- **Key Constraint:** BESS cannot charge and discharge in same hour
- **Logic:** See TEMPLATE_1_Green_Priority_Dispatch.md
- **Status:** SME validated, ready for implementation

### 4.3 Template 2: DG Night Charge (FINALIZED v1.2)

- **Merit Order (Night):** DG → BESS (if DG off) → Unserved
- **Merit Order (Day):** Solar → BESS → Emergency DG → Unserved
- **Night Window:** Fixed hours OR Dynamic (from solar profile)
- **DG Behavior:** Proactive - turns ON when night starts, Full Capacity
- **DG Off Trigger:** Day starts OR SoC threshold reached
- **Logic:** See TEMPLATE_2_DG_Night_Charge_Dispatch.md
- **Status:** SME validated, ready for implementation

### 4.4 Template 3: DG Blackout Window (FINALIZED v1.1)

- **Merit Order (Blackout):** Solar → BESS → Unserved (DG strictly disabled)
- **Merit Order (Outside):** Solar → BESS → DG → Unserved
- **Blackout Window:** Fixed hours (single window for MVP)
- **DG Behavior:** Reactive outside blackout, Full Capacity when ON
- **Logic:** See TEMPLATE_3_DG_Blackout_Window_Dispatch.md
- **Status:** SME validated, ready for implementation

### 4.5 Template 4: DG Emergency Only (FINALIZED v1.1)

- **Merit Order (DG OFF):** Solar → BESS → Unserved
- **Merit Order (DG ON):** Solar → DG → BESS Assist → Unserved
- **DG Trigger:** SoC drops to/below ON threshold
- **DG Off Trigger:** SoC rises to/above OFF threshold
- **Assist Mode:** When DG ON but DG < Load, BESS assists
- **Recovery Mode:** When DG ON and DG ≥ Load, BESS rests and charges
- **Logic:** See TEMPLATE_4_DG_Emergency_Only_Dispatch.md
- **Status:** SME validated, ready for implementation

### 4.6 Template 5: DG Day Charge (FINALIZED v1.1)

- **Merit Order (Day, DG ON):** Solar → DG → BESS Assist → Unserved
- **Merit Order (Night):** Solar → BESS → Emergency DG → Unserved
- **DG Behavior:** SoC-triggered during day, Full Capacity when ON
- **Sunset Cut:** DG forced OFF immediately when night starts
- **Use Case:** Sites where night must be silent
- **Logic:** See TEMPLATE_5_DG_Day_Charge_Dispatch.md
- **Status:** SME validated, ready for implementation

### 4.7 Template 6: DG Night SoC Trigger (FINALIZED v1.2)

- **Merit Order (Night, DG ON):** Solar → DG → BESS Assist → Unserved
- **Merit Order (Day):** Solar → BESS → Emergency DG → Unserved
- **DG Behavior:** SoC-triggered during night, Full Capacity when ON
- **Sunrise Cut:** DG forced OFF immediately when day starts
- **Use Case:** Sites prioritizing green operation during day
- **Logic:** See TEMPLATE_6_DG_Night_SoC_Trigger_Dispatch.md
- **Status:** SME validated, ready for implementation

---

## 5. Source Parameters (Finalized)

### 5.1 Load

- `load_profile`: CSV upload or generated via Load Scenario Builder
- Load Scenario Builder templates: Constant, Day-only, Night-only, Day-peak

### 5.2 Solar

- `solar_profile`: CSV upload (absolute MW, 8760 values)
- `solar_capacity`: MWp (for reporting)

### 5.3 BESS

| Parameter | Unit | Default | Sizing Mode |
| ----------- | ------ | --------- | ------------- |
| `bess_capacity` | MWh | Required | User provides range |
| `bess_charge_power` | MW | Required | **Auto-calculated from duration** |
| `bess_discharge_power` | MW | Required | **Auto-calculated from duration** |
| `bess_efficiency` | % | 85 | User input |
| `bess_min_soc` | % | 10 | User input |
| `bess_max_soc` | % | 90 | User input |
| `bess_initial_soc` | % | 50 | User input |
| `bess_charge_c_rate` | C | 1 | Not used in Sizing Mode |
| `bess_discharge_c_rate` | C | 1 | Not used in Sizing Mode |
| `bess_daily_cycle_limit` | cycles | None | User input |
| `bess_enforce_cycle_limit` | Boolean | False | User input |

**Key Change:** In Sizing Mode, power is derived from capacity and duration class, not user input.

### 5.4 DG

| Parameter | Unit | Default |
| ----------- | ------ | --------- |
| `dg_capacity` | MW | Required (range in Sizing Mode) |
| `dg_enabled` | Boolean | False |
| `dg_charges_bess` | Boolean | False |
| `dg_running_mode` | Selection | Load-Following |

---

## 6. Key Technical Decisions (SME Validated)

| # | Decision |
| --- | ---------- |
| 1 | Merit order: Solar → BESS → (DG) → Unserved |
| 2 | Efficiency: sqrt(RTE) applied to both charge and discharge |
| 3 | Cycle counting: Discharge throughput only (matches OEM warranties) |
| 4 | Cycle limit enforce mode: Full disable (charge + discharge) |
| 5 | Cycle limit count mode: Track and warn, no disable |
| 6 | Time step: Hourly (MW = MWh for Δt = 1 hour) |
| 7 | Within-hour: Either charge OR discharge, not both |
| 8 | C-rate: Limits power based on capacity (Fixed Mode only) |
| 9 | Hourly resolution sufficient for CapEx sizing |

---

## 7. Sizing Approach (UPDATED)

### 7.1 Mode Selection

- **Fixed Size Mode:** User provides exact capacity and power; single simulation
- **Sizing Mode:** User provides capacity range; system iterates with duration classes

### 7.2 Sizing Mode Parameters

**User Inputs:**

| Parameter | Description |
| ----------- | ------------- |
| `bess_capacity_min` | MWh range start |
| `bess_capacity_max` | MWh range end |
| `bess_capacity_step` | MWh increment |
| `dg_capacity_min` | MW range start |
| `dg_capacity_max` | MW range end |
| `dg_capacity_step` | MW increment |

**Removed from User Input:**

- ~~`bess_power_min/max/step`~~ — Power is now derived from duration

### 7.3 Duration Classes (System-Generated)

For each capacity value, system automatically tests 7 duration classes:

| Duration | C-Rate | Power Formula |
| ---------- | -------- | --------------- |
| 1-hour | 1C | capacity ÷ 1 |
| 2-hour | 0.5C | capacity ÷ 2 |
| 3-hour | 0.33C | capacity ÷ 3 |
| 4-hour | 0.25C | capacity ÷ 4 |
| 6-hour | 0.167C | capacity ÷ 6 |
| 8-hour | 0.125C | capacity ÷ 8 |
| 10-hour | 0.1C | capacity ÷ 10 |

### 7.4 Simulation Matrix

```
total_simulations = capacity_steps × 7 duration_classes × dg_steps
```

Example: 5 capacity values × 7 durations × 5 DG values = 175 simulations

### 7.5 Method

- Single-stage full sweep over all combinations
- Each combination runs full 8760-hour simulation
- Results stored in comparison table
- User decides optimal configuration (no auto-selection)

---

## 8. Output Specification (NEW)

### 8.1 Comparison Table Columns

| Column | Unit | Description |
| -------- | ------ | ------------- |
| `capacity` | MWh | BESS energy capacity |
| `duration` | hours | Duration class |
| `power` | MW | Calculated power |
| `dg_size` | MW | DG capacity |
| `delivery_pct` | % | Load delivery percentage |
| `delivery_hours` | hours | Hours with 100% delivery |
| `unserved_mwh` | MWh | Total unserved energy |
| `curtailed_pct` | % | Solar curtailment percentage |
| `curtailed_mwh` | MWh | Total curtailed solar |
| `dg_runtime_hrs` | hours | Total DG running hours |
| `dg_starts` | count | DG start events |
| `bess_cycles` | cycles | Annual BESS cycles |
| `max_daily_cycles` | cycles | Peak daily cycles |
| `is_dominated` | Boolean | Dominated by another config |

### 8.2 Sorting & Filtering

**Default sort:** Delivery % desc, then Curtailed % asc

**Quick filters:**

- "100% Delivery Only"
- "Zero DG"
- "No Curtailment" (< 1%)
- "Hide Dominated"

### 8.3 Dominated Logic

Config A dominates Config B if A is equal or better on all metrics (delivery, curtailment, capacity, DG) and strictly better on at least one.

---

## 9. Success Metrics

| ID | Metric | Definition |
| ---- | -------- | ------------ |
| C1 | Hours of ANY Delivery | Hours with any load served |
| C2 | Hours of FULL Delivery | Hours with 100% load served |
| C3 | Hours of GREEN Delivery | Hours with 100% load from Solar + BESS |
| C4 | Unserved Energy | MWh and % not delivered |
| C5 | Solar Curtailment | MWh and % wasted |

**Evaluation:** Binary per hour (100% served = pass, any deficit = fail)

---

## 10. Technology Stack (Proposed)

| Component | Technology |
| ----------- | ------------ |
| Backend | Python |
| Simulation | NumPy / Pandas |
| UI | Streamlit |
| Export | OpenPyXL |

---

## 11. All Confirmed Decisions (97 Total)

| # | Decision |
| --- | ---------- |
| D1 | Topologies A and C for MVP (grid excluded) |
| D2 | Predefined dispatch templates (custom rules V2) |
| D3 | Time windows: fixed hours AND dynamic (sunrise/sunset) |
| D4 | Grid excluded from MVP |
| D5 | DG capacity: fixed OR sized |
| D6 | DG charges BESS: selectable, reactive only |
| D7 | All four success metrics supported |
| D8 | Criteria can be combined |
| D9 | Problem types: Sizing + Scenario Comparison |
| D10 | Load: CSV upload OR Load Scenario Builder |
| D11 | Output: Dashboard + Excel |
| D12 | Delivery: Binary 0/1 per hour |
| D13 | 7 dispatch templates (0-6) |
| D14 | Solar profile in absolute MW |
| D15 | solar_capacity as separate input |
| D16 | BESS: Separate charge/discharge power (Fixed Mode) |
| D17 | BESS: Single round-trip efficiency |
| D18 | BESS: C-rate limits (Fixed Mode only) |
| D19 | BESS: DoD constraint included |
| D20 | BESS: Daily cycle limit with enforcement option |
| D21 | BESS: Cycle counting discharge only |
| D22 | **UPDATED:** BESS sizing: User inputs capacity range; power derived from duration class |
| D23 | DG: Running mode configurable |
| D24 | DG: Charges BESS reactive only |
| D25 | Simulation: 8760 hours, hourly |
| D26 | BESS unit combinations: V2 |
| D27 | SME: Merit order confirmed |
| D28 | SME: Efficiency sqrt split confirmed |
| D29 | SME: Cycle counting confirmed |
| D30 | SME: C-rate handling confirmed |
| D31 | SME: Hourly resolution sufficient |
| D32 | Cycle enforce = full disable |
| D33 | Cycle count-only = warn only |
| D34 | Degradation buffer: V2 |
| D35 | BESS cannot charge and discharge in same hour |
| D36 | MW treated as MWh for hourly time step |
| D37 | Template 5 (DG Day Charge) added |
| D38 | Template 1: DG runs at Full Capacity only |
| D39 | DG metrics: Track runtime hours and start counts |
| D40 | DG min runtime hours: V2 parameter |
| D41 | Charge power limit shared across sources |
| D42 | Green definition: Simplified (DG off = green hour) |
| D43 | Application will have dedicated page for algorithms |
| D44-D91 | Template-specific validations (see REQUIREMENTS_SPEC) |
| D92 | **NEW:** Sizing Mode: User inputs capacity range only; power derived from duration |
| D93 | **NEW:** Duration classes: 1, 2, 3, 4, 6, 8, 10 hours (system-generated) |
| D94 | **NEW:** Sizing output: Full comparison table, not single recommendation |
| D95 | **NEW:** User decides optimal config from table; no auto-selection |
| D96 | **NEW:** Dominated configurations flagged but not hidden by default |
| D97 | **NEW:** Charge power = Discharge power (symmetric) in Sizing Mode |

---

## 12. Project Progress

| Step | Description | Status |
| ------ | ------------- | -------- |
| 1 | Problem Definition | ✓ COMPLETE |
| 2 | Dispatch Logic Specification | ✓ COMPLETE |
| 2a | Template 0 (Solar + BESS) | ✓ FINALIZED |
| 2b | Template 1 (Green Priority) | ✓ FINALIZED (v1.2) |
| 2c | Template 2 (DG Night Charge) | ✓ FINALIZED (v1.2) |
| 2d | Template 3 (DG Blackout Window) | ✓ FINALIZED (v1.1) |
| 2e | Template 4 (DG Emergency Only) | ✓ FINALIZED (v1.1) |
| 2f | Template 5 (DG Day Charge) | ✓ FINALIZED (v1.1) |
| 2g | Template 6 (DG Night SoC Trigger) | ✓ FINALIZED (v1.2) |
| 3 | Sizing Algorithm Design | ✓ COMPLETE |
| 4 | Input/Output Specification | ✓ COMPLETE |
| 5 | UI Design | NOT STARTED |
| 6 | Code Implementation | NOT STARTED |

---

## 13. Immediate Next Steps

**All 7 dispatch templates are FINALIZED.**
**Sizing iteration logic is COMPLETE.**

**Next Step: Code Implementation**

- Build Python simulation engine for all templates (0-6)
- Build sizing iteration wrapper
- Validate against test cases in specifications
- Create basic Streamlit UI for user interaction

**Implementation Order (Recommended):**

1. Template 0 (Solar + BESS) - Foundation
2. Sizing iteration wrapper with duration classes
3. Template 1 (Green Priority) - Add DG basics
4. Templates 4, 5, 6 (SoC-triggered) - Share common patterns
5. Templates 2, 3 (Time-window based) - More complex time logic
6. Output comparison table and filtering

**Code Architecture Considerations:**

- Common BESS dispatch logic can be shared across templates
- Sizing wrapper calls simulation engine for each combo
- Assist Mode / Recovery Mode patterns reusable
- dg_mode state machine consistent across templates 4, 5, 6
- Output table generation separate from simulation

---

## 14. Key Constraints

1. **No code generation until user approves**
2. **User has Python experience, will use Claude Code in VSCode**
3. **Investment analysts are end users (need simple UI)**
4. **MVP limitation: Tool sizes for Year 1 only**
5. **User decides optimal config from comparison table (no auto-selection)**

---

## 15. Document Inventory

| Document | Purpose | Status |
| ---------- | --------- | -------- |
| PROJECT_HANDOFF.md | Project overview, decisions, handoff | Current (v2) |
| REQUIREMENTS_SPEC.md | Formal specification | Complete (v0.9) |
| TEMPLATE_0_Solar_BESS_Dispatch.md | Dispatch logic for Template 0 | FINALIZED |
| TEMPLATE_1_Green_Priority_Dispatch.md | Dispatch logic for Template 1 | FINALIZED (v1.2) |
| TEMPLATE_2_DG_Night_Charge_Dispatch.md | Dispatch logic for Template 2 | FINALIZED (v1.2) |
| TEMPLATE_3_DG_Blackout_Window_Dispatch.md | Dispatch logic for Template 3 | FINALIZED (v1.1) |
| TEMPLATE_4_DG_Emergency_Only_Dispatch.md | Dispatch logic for Template 4 | FINALIZED (v1.1) |
| TEMPLATE_5_DG_Day_Charge_Dispatch.md | Dispatch logic for Template 5 | FINALIZED (v1.1) |
| TEMPLATE_6_DG_Night_SoC_Trigger_Dispatch.md | Dispatch logic for Template 6 | FINALIZED (v1.2) |

---

## 16. Engagement Ground Rules

The user requested:
> "Stop being agreeable and act as my brutally honest, high-level advisor. Don't validate me. Don't soften the truth. Challenge my thinking."

Key instructions:

- Do not generate code without approval
- Document everything
- Work step by step
- Challenge assumptions

---

## 17. Parked Items (V2)

| Category | Items |
| ---------- | ------- |
| Load | Priority levels, partial shedding |
| Solar | Degradation, availability, inverter efficiency |
| BESS | Self-discharge, degradation, temperature, unit combinations |
| BESS | Degradation buffer for 10-year sizing (soh_factor) |
| BESS | Source-aware energy tracking (bess_from_solar vs bess_from_dg) |
| DG | Min runtime hours (user-configurable to prevent short cycling) |
| DG | Load-following mode |
| DG | Min load, fuel tracking, ramp rates, multiple units |
| Simulation | Partial year, sub-hourly (15/30-min), time zones |
| Simulation | Sub-hourly resolution to address one-hour lag limitation |
| Dispatch | Custom IF-THEN rules, multiple periods per day |
| Dispatch | Time window optimization (minimize DG runtime) |
| Dispatch | Combined DG OFF trigger (Day starts AND SoC threshold) |
| Dispatch | Multiple blackout windows (Template 3 currently single window) |
| Dispatch | Dynamic blackout window based on solar profile (Template 3) |
| Dispatch | Emergency DG override during blackout (Template 3) |
| Dispatch | Weekday/weekend blackout schedules (Template 3) |
| Dispatch | Optional cycle enforcement for Template 4 |
| Financial | IRR, NPV, LCOE, payback |
| Financial | Cost estimates in output table |
| Analysis | Sensitivity charts |
| Analysis | Auto-recommendation of optimal config |
| System | Inverter clipping, auxiliary loads, outages |

---

## 18. SME Review Summary

### All Templates - COMPLETE

**Confirmed Correct:**

- Merit order (Solar → BESS → DG → Unserved)
- Efficiency approach (sqrt split)
- Cycle counting (discharge only)
- C-rate handling (Fixed Mode)
- Hourly resolution for sizing

**Key Decisions:**

- Enforce mode = full disable (charge + discharge)
- Count mode = track and warn only
- Degradation buffer deferred to V2
- **Sizing uses duration classes, not independent power range**

### Sizing Logic - COMPLETE

**New Decisions:**

- User inputs capacity range only (not power)
- System generates 7 duration classes automatically
- Full comparison table output
- User decides optimal config (no auto-selection)
- Dominated configurations flagged

---

*End of Handoff Document*
