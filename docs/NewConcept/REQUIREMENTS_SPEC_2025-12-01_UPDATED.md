# BESS & DG Sizing Tool - Requirements Specification

**Document Version:** 0.9  
**Status:** Step 2 - Dispatch Logic Specification (COMPLETE) + Sizing Logic (COMPLETE)  
**Last Updated:** 2025-12-01  
**Purpose:** Formal specification for development handoff to Claude Code

---

## 1. Executive Summary

### 1.1 Objective

Build a tool that allows users to define custom energy system scenarios (Solar + BESS + optional DG), select from predefined dispatch templates, and run simulations to determine optimal BESS and DG sizing based on user-defined success criteria.

### 1.2 Core Question Answered
>
> "Given this solar profile, which size of BESS and DG gives me highest availability with lowest solar wastage in different scenarios while providing maximum load delivery hours or 100% delivery?"

### 1.3 Primary Users

Investment analysts evaluating energy projects

### 1.4 Primary Use Cases

- Comparing system configurations across multiple duration classes
- Creating product offerings for the European market
- Sizing BESS and DG for specific load/solar profiles
- Evaluating trade-offs between delivery %, solar curtailment, and system size

### 1.5 MVP Scope Boundaries

- **In Scope:** Solar + BESS + DG configurations (grid excluded from MVP)
- **Out of Scope for MVP:** Grid connectivity, financial modeling, custom rule builder

---

## 2. System Components

### 2.1 Component Matrix

| Component | Required? | Role | User Input |
| ----------- | ----------- | ------ | ------------ |
| **Solar PV** | Yes | Primary generation source | Profile (8760 hourly values) |
| **BESS** | Yes | Energy storage | Capacity range to be sized OR fixed input |
| **DG/Gas Generator** | Optional | Backup generation | To be sized OR fixed input |
| **Load** | Yes | Demand to be served | Profile (8760 hourly values) |
| **Grid** | No | Excluded from MVP | - |

### 2.2 Supported Topologies (MVP)

| Config ID | Solar | BESS | DG | Description |
| ----------- | ------- | ------ | ----- | ------------- |
| **A** | ✓ | ✓ | ✗ | Off-grid, pure green |
| **C** | ✓ | ✓ | ✓ | Off-grid with DG backup |

**Note:** Grid-connected topologies (B, D) deferred to future version.

---

## 3. Source Parameters

### 3.1 Load Parameters

| Parameter | Description | Unit | Required? | Default | MVP |
| ----------- | ------------- | ------ | ----------- | --------- | ----- |
| `load_profile` | Hourly demand for full year | MW (8760 values) | Yes | - | ✓ |
| `load_name` | Identifier for the load | Text | Optional | "Load" | ✓ |

**Load Profile Input Options (MVP):**

1. **CSV Upload:** User uploads custom 8760-hour profile
2. **Load Scenario Builder:** User selects from templates:
   - Constant flat load (e.g., 25 MW 24/7)
   - Day only (e.g., 06:00-18:00)
   - Night only (e.g., 18:00-06:00)
   - Day peak (higher during day, lower at night)
   - Custom time windows with MW values

The Load Scenario Builder generates an 8760-hour profile based on user selections.

**Parked for Future Versions:**

- Load priority (critical vs. non-critical portions)
- Partial load shedding logic
- Multiple load profiles in single simulation

---

### 3.2 Solar PV Parameters

| Parameter | Description | Unit | Required? | Default | MVP |
| ----------- | ------------- | ------ | ----------- | --------- | ----- |
| `solar_profile` | Hourly generation for full year | MW (8760 values) | Yes | - | ✓ |
| `solar_capacity` | Installed capacity | MWp | Yes | - | ✓ |

**Notes:**

- Solar profile is provided in absolute MW output (not capacity factor)
- `solar_capacity` used for reporting and validation

**Parked for Future Versions:**

- Solar degradation rate (% per year)
- Availability factor (%)
- Curtailment limits
- Inverter efficiency
- DC/AC ratio

---

### 3.3 BESS Parameters

| Parameter | Description | Unit | Required? | Default | Sizing Mode | MVP |
| ----------- | ------------- | ------ | ----------- | --------- | ------------- | ----- |
| `bess_capacity` | Total energy capacity | MWh | Yes | - | User provides range | ✓ |
| `bess_charge_power` | Max charge rate | MW | Fixed Mode only | - | Auto-calculated | ✓ |
| `bess_discharge_power` | Max discharge rate | MW | Fixed Mode only | - | Auto-calculated | ✓ |
| `bess_efficiency` | Round-trip efficiency | % | Optional | 85 | User input | ✓ |
| `bess_min_soc` | Minimum SoC floor | % | Optional | 10 | User input | ✓ |
| `bess_max_soc` | Maximum SoC ceiling | % | Optional | 90 | User input | ✓ |
| `bess_initial_soc` | Starting SoC | % | Optional | 50 | User input | ✓ |
| `bess_charge_c_rate` | Max charge C-rate | C | Optional | 1 | Not used (duration sets effective C-rate) | ✓ |
| `bess_discharge_c_rate` | Max discharge C-rate | C | Optional | 1 | Not used (duration sets effective C-rate) | ✓ |
| `bess_daily_cycle_limit` | Max cycles per day | cycles | Optional | None | User input | ✓ |
| `bess_enforce_cycle_limit` | Enforce limit? | Boolean | Optional | False | User input | ✓ |

**Sizing Mode vs Fixed Mode:**

- **Fixed Mode:** User provides exact capacity and power values; tool runs single simulation
- **Sizing Mode:** User provides capacity range; power is auto-calculated from duration classes

**Power Calculation in Sizing Mode:**

```
bess_charge_power = bess_capacity ÷ duration_hours
bess_discharge_power = bess_capacity ÷ duration_hours
```

**Assumption:** Charge power = Discharge power (symmetric) in Sizing Mode.

**C-Rate Note:**

- In Sizing Mode, C-rate is implicitly set by duration class (e.g., 2-hour = 0.5C)
- The `bess_charge_c_rate` and `bess_discharge_c_rate` parameters are not used in Sizing Mode
- In Fixed Mode, C-rate constraints still apply

**Cycle Calculation Method:**

- Cycles = Total energy discharged ÷ Usable capacity
- Only discharge throughput is counted (industry standard per OEM warranties)
- Cycle count resets daily at midnight

**Daily Cycle Limit Behavior:**

| Mode | `bess_enforce_cycle_limit` | Behavior |
| ------ | --------------------------- | ---------- |
| **Count-Only** | No | Cycles are tracked and reported. BESS continues operating. Output includes "Days exceeding cycle limit" as a warning metric. |
| **Enforce** | Yes | When daily cycle limit is reached, BESS is fully disabled (no charge, no discharge) for remainder of that day. Resets at midnight. |

**CRITICAL: DG-BESS Independence (D91):**

- When BESS is disabled due to cycle limit, **DG continues to operate normally** based on its own triggers.
- DG serves load directly; excess DG is curtailed (cannot charge disabled BESS).
- BESS cannot assist DG when disabled (remaining deficit becomes unserved).
- This ensures DG protects load even when BESS is warranty-constrained.

**Time Step Assumption:**

- Simulation uses hourly time steps (Δt = 1 hour)
- MW values are treated as MWh for each hour
- Within each hour, either charging OR discharging occurs (not both)

**Duration Calculation (Output):**

- Duration (hours) = bess_capacity ÷ bess_discharge_power
- This is calculated/reported as part of output

**Parked for Future Versions:**

- Self-discharge rate (% per hour)
- Calendar degradation
- Cycle-based degradation
- Degradation buffer / State of Health factor (for 10-year sizing)
- Temperature effects
- BESS unit combinations (1×100 MW vs 4×25 MW)
- Charge and discharge within same hour (requires sub-hourly resolution)

---

### 3.4 DG Parameters

| Parameter | Description | Unit | Required? | Default | MVP |
| ----------- | ------------- | ------ | ----------- | --------- | ----- |
| `dg_capacity` | Rated power output | MW | Yes (if DG enabled) | - | ✓ |
| `dg_enabled` | Is DG included in topology? | Yes/No | Yes | No | ✓ |
| `dg_charges_bess` | Can DG charge BESS when running? | Yes/No | Optional | No | ✓ |
| `dg_running_mode` | How DG outputs power | Selection | Optional | Load-Following | ✓ |

**DG Running Modes:**

1. **Full Capacity:** DG outputs 100% of rated capacity when ON
2. **Load-Following:** DG outputs only what is needed (up to capacity)

**DG Charges BESS Behavior:**

- Only applies when DG is already running to serve load
- DG does NOT turn on proactively to charge BESS
- Excess DG output (in Full Capacity mode) or additional headroom (in Load-Following mode) can charge BESS

**Behavior Matrix:**

| dg_running_mode | dg_charges_bess | Behavior |
| ----------------- | ----------------- | ---------- |
| Full Capacity | No | DG outputs 100% when ON. Excess beyond load is wasted. |
| Full Capacity | Yes | DG outputs 100% when ON. Excess charges BESS, remainder wasted. |
| Load-Following | No | DG outputs only what load needs (up to capacity). |
| Load-Following | Yes | DG outputs load need + BESS charging need (up to capacity). |

**Parked for Future Versions:**

- `dg_min_load` - Minimum stable operating point (%)
- `dg_fuel_type` - Diesel or Gas
- `dg_fuel_consumption` - Fuel rate (L/MWh)
- `dg_min_run_time` - Minimum run time once started
- `dg_max_daily_runtime` - Maximum hours per day
- `dg_start_cost` - Cost per start event
- `dg_ramp_rate` - Ramp up/down rate
- Multiple DG units

---

### 3.5 Simulation Parameters

| Parameter | Description | Unit | Value | MVP |
| ----------- | ------------- | ------ | ------- | ----- |
| `simulation_hours` | Total simulation length | hours | 8760 (fixed) | ✓ |
| `time_step` | Resolution | hours | 1 (fixed) | ✓ |

**Parked for Future Versions:**

- Partial year simulations
- Sub-hourly resolution (15-min, 5-min)
- Time zone handling
- Daylight saving adjustments

---

### 3.6 Sizing Parameters

**Mode Selection:**
User chooses between:

1. **Fixed Size Mode:** User provides exact BESS capacity, power, and DG size; tool runs single simulation
2. **Sizing Mode:** User provides capacity and DG ranges; tool iterates across all duration classes

**Sizing Mode Inputs:**

| Parameter | Description | Unit | Required |
| ----------- | ------------- | ------ | ---------- |
| `bess_capacity_min` | Start of capacity range | MWh | Yes |
| `bess_capacity_max` | End of capacity range | MWh | Yes |
| `bess_capacity_step` | Capacity increment | MWh | Yes |
| `dg_capacity_min` | Start of DG range | MW | Yes (if DG enabled) |
| `dg_capacity_max` | End of DG range | MW | Yes (if DG enabled) |
| `dg_capacity_step` | DG increment | MW | Yes (if DG enabled) |

**Note:** Power range inputs (`bess_power_min/max/step`) are NOT used in Sizing Mode. Power is derived from duration classes.

---

### 3.7 Sizing Iteration Logic (NEW)

#### 3.7.1 Duration Classes (System-Generated)

The system automatically tests 7 standard duration classes for each capacity value:

| Duration | C-Rate | Power Formula | Market Term |
| ---------- | -------- | --------------- | ------------- |
| 1-hour | 1C | capacity ÷ 1 | Short-duration, frequency response |
| 2-hour | 0.5C | capacity ÷ 2 | Most common utility-scale |
| 3-hour | 0.33C | capacity ÷ 3 | Transitional |
| 4-hour | 0.25C | capacity ÷ 4 | Growing market, capacity contracts |
| 6-hour | 0.167C | capacity ÷ 6 | Long-duration emerging |
| 8-hour | 0.125C | capacity ÷ 8 | Long-duration storage |
| 10-hour | 0.1C | capacity ÷ 10 | Extended duration |

**Why Multiple Durations Matter:**

- Same capacity with different power ratings performs differently
- Lower power (longer duration) = cheaper but may curtail solar (can't absorb spikes)
- Higher power (shorter duration) = more expensive but handles variable loads better
- Tool shows all options; user decides based on project economics

#### 3.7.2 Simulation Matrix

For each combination of:

- Each capacity value in range
- Each duration class (7 values)
- Each DG size in range

System runs a full 8760-hour simulation and records all metrics.

**Example:**

User inputs:

- Capacity: 50-150 MWh, step 50 MWh → 3 values (50, 100, 150)
- DG: 0-10 MW, step 5 MW → 3 values (0, 5, 10)
- Duration classes: 7 (system-generated)

Total simulations: 3 × 7 × 3 = **63 simulations**

Each simulation = 8,760 hourly calculations
Total calculations: 63 × 8,760 = **551,880 calculations**

Estimated runtime: **< 5 seconds** on modern hardware

#### 3.7.3 Simulation Count Formula

```
capacity_steps = ((bess_capacity_max - bess_capacity_min) ÷ bess_capacity_step) + 1
dg_steps = ((dg_capacity_max - dg_capacity_min) ÷ dg_capacity_step) + 1
duration_classes = 7

total_simulations = capacity_steps × duration_classes × dg_steps
total_calculations = total_simulations × 8760
```

#### 3.7.4 Validation Rules

| Rule | Action |
| ------ | -------- |
| `bess_capacity_min` ≤ 0 | ERROR: Capacity must be positive |
| `bess_capacity_max` < `bess_capacity_min` | ERROR: Max must be ≥ min |
| `bess_capacity_step` ≤ 0 | ERROR: Step must be positive |
| `dg_capacity_min` < 0 | ERROR: DG capacity cannot be negative |
| `dg_capacity_max` < `dg_capacity_min` | ERROR: Max must be ≥ min |
| `dg_capacity_step` ≤ 0 (when DG enabled) | ERROR: Step must be positive |
| Total simulations > 10,000 | WARNING: "Large simulation set, may take longer" |
| Total simulations > 50,000 | ERROR: "Reduce range or increase step size" |

---

## 4. Dispatch Logic

### 4.1 Dispatch Approach

**Decision:** Predefined templates with customizable parameters (Option A)

Custom IF-THEN rule builder deferred to V2.

### 4.2 Dispatch Templates (MVP)

#### Template 0: Solar + BESS Only (FINALIZED)

**Description:** Pure green system with no DG. Topology A only.

**Merit Order:**

1. Solar direct to load
2. BESS discharge to load
3. Unserved (if BESS depleted)

**Charging:**

- BESS charges from excess solar only
- If BESS full, excess solar is curtailed

**Parameters:**

- BESS min SoC (%) - floor for discharge
- BESS max SoC (%) - ceiling for charge

**Use Case:** Sites with reliable solar and no backup generation required

**Outputs:**

- Standard BESS metrics (SoC, cycles, throughput)
- Unserved energy hours
- No DG-related outputs

---

#### Template 1: Green Priority (FINALIZED v1.2)

**Description:** Maximize green energy delivery. DG is last resort.

**Merit Order:**

1. Solar direct to load
2. BESS discharge to load
3. DG to load (if enabled and BESS depleted)

**Excess Energy:**

- Excess solar charges BESS
- If BESS full, excess solar is curtailed

**Parameters:**

- BESS min SoC (%) - floor for discharge
- BESS max SoC (%) - ceiling for charge
- DG min stable load (%)

---

#### Template 2: DG Night Charge (FINALIZED v1.2)

**Description:** DG runs at night to charge BESS. Solar + BESS only during day.

**Behavior:**

*Night Hours (user-defined, e.g., 18:00 - 06:00):*

- DG ON: serves load, excess charges BESS
- DG switches OFF when BESS SoC reaches upper threshold
- Merit order: DG → BESS discharge (if DG off)

*Day Hours (user-defined, e.g., 06:00 - 18:00):*

- DG DISABLED (not allowed to run)
- Merit order: Solar → BESS
- BESS must be sized to cover day with solar

**Parameters:**

- Night start hour
- Night end hour
- SoC upper threshold to turn DG OFF (%)
- SoC lower threshold - emergency DG ON (%) [optional]
- Allow emergency DG during day (Yes/No)
- BESS min SoC (%)
- BESS max SoC (%)
- DG min stable load (%)

---

#### Template 3: DG Blackout Window (FINALIZED v1.1)

**Description:** DG not allowed during specified hours (noise/emissions restrictions).

**Behavior:**

*Blackout Window (user-defined):*

- DG DISABLED
- Merit order: Solar → BESS
- If BESS depleted during blackout window → unserved energy

*Outside Blackout Window:*

- Merit order: Solar → BESS → DG
- DG can charge BESS (if enabled)

**Parameters:**

- Blackout start hour
- Blackout end hour
- DG charges BESS outside blackout (Yes/No)
- BESS min SoC (%)
- BESS max SoC (%)
- DG min stable load (%)

---

#### Template 4: DG Emergency Only (FINALIZED v1.1)

**Description:** SoC-triggered DG backup with no time restrictions. DG acts as a "Range Extender" asset.

**Behavior:**

*Normal Operation (DG OFF):*

- Merit order: Solar → BESS → Unserved
- DG stays OFF as long as SoC is above lower threshold
- BESS charges from excess solar

*Emergency Operation (DG ON):*

- DG turns ON when SoC drops to/below lower threshold
- DG takes priority for serving load (allows BESS to recover)
- **Assist Mode:** If DG < remaining load, BESS assists (covers deficit only)
- **Recovery Mode:** If DG ≥ remaining load, BESS rests and charges from excess
- DG turns OFF when SoC reaches upper threshold

**Key Design Features:**

- **Deadband Hysteresis:** Separate ON/OFF thresholds prevent rapid cycling
- **Assist Mode:** Prevents artificial blackouts when DG undersized
- **No Time Restrictions:** DG can run anytime (unlike Templates 2, 6)
- **Cycle Limit Policy:** Enforcement disabled (monitor-only) for reliability

**Parameters:**

- `dg_soc_on_threshold`: SoC at/below which DG turns ON (%, default 30)
- `dg_soc_off_threshold`: SoC at/above which DG turns OFF (%, default 80)
- `dg_charges_bess`: Can DG charge BESS? (Yes/No, default Yes)
- `bess_min_soc`: Minimum SoC floor (%)
- `bess_max_soc`: Maximum SoC ceiling (%)

**Validation Rules:**

- ERROR: `dg_soc_on_threshold >= dg_soc_off_threshold`
- ERROR: `dg_soc_on_threshold < bess_min_soc`
- ERROR: `dg_soc_off_threshold > bess_max_soc`
- WARNING: `bess_enforce_cycle_limit = True` (forced to False)
- WARNING: Deadband < 20% (may cause frequent cycling)

**Outputs (New):**

- `bess_assisted`: Boolean flag per hour (BESS discharged while DG running)
- `hours_dg_assist`: Count of hours where DG ran but BESS had to help

---

#### Template 5: DG Day Charge (FINALIZED v1.1)

**Description:** SoC-triggered day charging strategy with silent nights. Inverse of Template 6.

**Behavior:**

*Day Hours (DG Allowed - SoC triggered):*

- DG is SoC-triggered, not load-triggered
- DG turns ON when SoC ≤ ON threshold (e.g., 30%)
- DG turns OFF when SoC ≥ OFF threshold (e.g., 80%)
- **Assist Mode:** If DG < remaining load, BESS assists (covers deficit only)
- **Recovery Mode:** If DG ≥ remaining load, BESS rests and charges
- DG will run for proactive charging even with zero load
- Merit order: Solar → DG (if triggered) → BESS → Unserved

*Night Hours (DG Disabled - Silent):*

- DG strictly DISABLED
- Merit order: Solar → BESS → Emergency DG (if enabled) → Unserved
- Emergency DG optional when SoC critical

**Key Design Features:**

- **Sunset Cut:** DG forced OFF immediately when night starts
- **Morning Carryover:** Emergency DG transitions to Normal mode when day starts
- **Deadband Hysteresis:** Separate ON/OFF thresholds prevent rapid cycling
- **Cycle Limit Policy:** Monitor-only (enforcement disabled)

**Parameters:**

- `day_start_hour`: Day begins (Hour 0-23, default 6)
- `day_end_hour`: Day ends (Hour 0-23, default 18)
- `day_window_mode`: Fixed / Dynamic (from solar profile)
- `dg_soc_on_threshold`: SoC at/below which DG turns ON (%, default 30)
- `dg_soc_off_threshold`: SoC at/above which DG turns OFF (%, default 80)
- `allow_emergency_dg_night`: Allow DG during night if SoC critical? (Boolean)
- `emergency_soc_threshold`: SoC at/below which emergency DG activates (%, default 15)
- `dg_charges_bess`: Can DG charge BESS? (Yes/No, default Yes)

**Validation Rules:**

- ERROR: `dg_soc_on_threshold >= dg_soc_off_threshold`
- ERROR: `dg_soc_on_threshold < bess_min_soc`
- ERROR: `dg_soc_off_threshold > bess_max_soc`
- WARNING: `bess_enforce_cycle_limit = True` (forced to False)
- WARNING: `emergency_soc_threshold >= dg_soc_on_threshold`
- WARNING: Deadband < 20% (may cause frequent cycling)

**Use Case:** Sites where night must be silent (residential nearby)

**Outputs (New):**

- `dg_mode`: "OFF" / "NORMAL" / "EMERGENCY" per hour
- `bess_assisted`: Boolean flag per hour
- `hours_dg_assist`: Count of hours where DG ran but BESS had to help
- `hours_emergency_dg`: Count of emergency DG hours at night

---

#### Template 6: DG Night SoC Trigger (FINALIZED v1.2)

**Description:** SoC-triggered night charging strategy with green days. Inverse of Template 5.

**Behavior:**

*Night Hours (DG Allowed - SoC triggered):*

- DG is SoC-triggered, not load-triggered
- DG turns ON when SoC ≤ ON threshold (e.g., 30%)
- DG turns OFF when SoC ≥ OFF threshold (e.g., 80%)
- **Assist Mode:** If DG < remaining load, BESS assists (covers deficit only)
- **Recovery Mode:** If DG ≥ remaining load, BESS rests and charges
- DG will run for proactive charging even with zero load
- Merit order: Solar → DG (if triggered) → BESS → Unserved

*Day Hours (DG Disabled - Green):*

- DG strictly DISABLED
- Merit order: Solar → BESS → Emergency DG (if enabled) → Unserved
- Emergency DG optional when SoC critical

**Key Design Features:**

- **Sunrise Cut:** DG forced OFF immediately when day starts
- **Evening Carryover:** Emergency DG transitions to Normal mode when night starts
- **Deadband Hysteresis:** Separate ON/OFF thresholds prevent rapid cycling
- **Cycle Limit Policy:** Enforcement allowed (green day is predictable)
- **DG-BESS Independence:** DG runs even when BESS disabled (cycle limit); only BESS operations blocked

**Parameters:**

- `night_start_hour`: Night begins (Hour 0-23, default 18)
- `night_end_hour`: Night ends (Hour 0-23, default 6)
- `night_window_mode`: Fixed / Dynamic (from solar profile)
- `dg_soc_on_threshold`: SoC at/below which DG turns ON (%, default 30)
- `dg_soc_off_threshold`: SoC at/above which DG turns OFF (%, default 80)
- `allow_emergency_dg_day`: Allow DG during day if SoC critical? (Boolean)
- `emergency_soc_threshold`: SoC at/below which emergency DG activates (%, default 15)
- `dg_charges_bess`: Can DG charge BESS? (Yes/No, default Yes)

**Validation Rules:**

- ERROR: `dg_soc_on_threshold >= dg_soc_off_threshold`
- ERROR: `dg_soc_on_threshold < bess_min_soc`
- ERROR: `dg_soc_off_threshold > bess_max_soc`
- ERROR: `emergency_soc_threshold < bess_min_soc`
- WARNING: `emergency_soc_threshold >= dg_soc_on_threshold`
- WARNING: Deadband < 20% (may cause frequent cycling)
- WARNING: Night window < 6 hours (limited charging time)
- WARNING: `night_start_hour == night_end_hour` (0 night hours, DG always disabled)

**Use Case:** Sites prioritizing green operation during day; DG for night recharge only

**Outputs (New):**

- `dg_mode`: "OFF" / "NORMAL" / "EMERGENCY" per hour
- `bess_assisted`: Boolean flag per hour
- `hours_dg_assist`: Count of hours where DG ran but BESS had to help
- `hours_emergency_dg`: Count of emergency DG hours during day
- `pct_day_green`: Percentage of day hours with no DG and no unserved

### 4.3 Time Window Definition

**Decision:** Support both options:

- Fixed hours (user inputs start/end time)
- Dynamic (sunrise/sunset derived from solar profile - when solar > 0)

---

### 4.4 BESS Charging Sources

| Source | Allowed? | User Configurable |
| -------- | ---------- | ------------------- |
| Excess Solar | Always | No (always on) |
| DG Excess | Template-dependent | Yes (per template) |
| Grid | No | N/A (grid excluded from MVP) |

---

### 4.5 DG Behavior Parameters

| Parameter | Description | User Input |
| ----------- | ------------- | ------------ |
| DG Capacity | Rated power (MW) | Fixed input OR to be sized |
| Min Stable Load | Minimum operating point (% of capacity) | User input (default 30%) |
| DG Charges BESS | Can excess DG charge BESS? | Selectable (Yes/No) |
| Start-up Time | Time to reach stable operation | Deferred to V2 |

---

## 5. Success Criteria / Objective Functions

### 5.1 Supported Metrics (MVP)

| ID | Metric | Definition | Binary? |
| ---- | -------- | ------------ | --------- |
| **C1** | Hours of ANY Delivery | Hours where load receives any power (even partial) | No |
| **C2** | Hours of FULL Delivery | Hours where 100% of load is served | Yes |
| **C3** | Hours of GREEN Delivery | Hours where 100% of load served by Solar + BESS only | Yes |
| **C4** | Hours of FULL Delivery (source-agnostic) | Hours where 100% load served, any source mix | Yes |

### 5.2 Delivery Evaluation

**Decision:** Binary (0/1) evaluation per hour

- Each hour is either PASS (100% load served) or FAIL (any unserved energy)
- No partial credit for 90% delivery

### 5.3 Combining Criteria

**Decision:** Users can combine criteria

- Example: "Maximize green hours, subject to zero blackout constraint"
- Implementation: Primary objective + constraints

---

## 6. Problem Types (MVP)

| Type | Description | In MVP? |
| ------ | ------------- | --------- |
| **Sizing Optimization** | Find minimum BESS (and DG) size to meet target | ✓ |
| **Scenario Comparison** | Run multiple configurations, compare results | ✓ |
| Feasibility Check | Given fixed size, can load be served? | Implicit in above |
| Sensitivity Analysis | Curves showing metric vs. size | Deferred to V2 |

---

## 7. Inputs Specification

### 7.1 Data Inputs

| Input | Format | Resolution | Required |
| ------- | -------- | ------------ | ---------- |
| Load Profile | CSV upload | Hourly (8760 values) | Yes |
| Solar Profile | CSV upload | Hourly (8760 values) | Yes |

**CSV Format (assumed):**

```
hour,value_mw
1,25.0
2,25.0
...
8760,25.0
```

### 7.2 Configuration Inputs

| Input | Type | Options/Range |
| ------- | ------ | --------------- |
| Topology | Selection | A (Solar+BESS) or C (Solar+BESS+DG) |
| Dispatch Template | Selection | Templates 0-6 |
| Template Parameters | Numeric/Boolean | Per template (see Section 4.2) |

### 7.3 BESS Inputs

**Fixed Size Mode:**

| Parameter | Type | Unit | Notes |
| ----------- | ------ | ------ | ------- |
| BESS Capacity | Fixed | MWh | Single value |
| BESS Charge Power | Fixed | MW | Single value |
| BESS Discharge Power | Fixed | MW | Single value |
| Round-trip Efficiency | Fixed | % | Default 85% |
| Min SoC | Fixed | % | Default 10% |
| Max SoC | Fixed | % | Default 90% |
| Initial SoC | Fixed | % | Default 50% |

**Sizing Mode:**

| Parameter | Type | Unit | Notes |
| ----------- | ------ | ------ | ------- |
| BESS Capacity Min | Range start | MWh | Required |
| BESS Capacity Max | Range end | MWh | Required |
| BESS Capacity Step | Increment | MWh | Required |
| Round-trip Efficiency | Fixed | % | Default 85% |
| Min SoC | Fixed | % | Default 10% |
| Max SoC | Fixed | % | Default 90% |
| Initial SoC | Fixed | % | Default 50% |

**Note:** In Sizing Mode, BESS Power is NOT a user input. Power is automatically calculated from capacity and duration class.

### 7.4 DG Inputs (if enabled)

| Parameter | Type | Unit | Notes |
| ----------- | ------ | ------ | ------- |
| DG Capacity Min | Range start | MW | If sizing DG |
| DG Capacity Max | Range end | MW | If sizing DG |
| DG Capacity Step | Increment | MW | If sizing DG |
| Min Stable Load | Fixed | % | Default 30% |
| Fuel Consumption Rate | Fixed | L/MWh | Optional (for V2 financials) |

---

## 8. Outputs Specification

### 8.1 Sizing Results (Comparison Table)

In Sizing Mode, output is a **comparison table** with all tested configurations:

| Column | Description | Unit |
| -------- | ------------- | ------ |
| `capacity` | BESS energy capacity | MWh |
| `duration` | Duration class | hours |
| `power` | Charge/discharge power (calculated) | MW |
| `dg_size` | DG capacity | MW |
| `delivery_pct` | Load delivery percentage | % |
| `delivery_hours` | Hours with 100% load served | hours |
| `unserved_mwh` | Total unserved energy | MWh |
| `unserved_pct` | Unserved as % of total load | % |
| `curtailed_mwh` | Total curtailed solar | MWh |
| `curtailed_pct` | Curtailment as % of solar generation | % |
| `dg_runtime_hrs` | Total DG running hours | hours |
| `dg_starts` | Number of DG start events | count |
| `bess_cycles` | Total BESS cycles (annual) | cycles |
| `max_daily_cycles` | Highest single-day cycle count | cycles |
| `green_hours` | Hours with 100% green delivery | hours |
| `green_pct` | Green delivery percentage | % |
| `is_dominated` | Configuration is dominated by another | Boolean |

**Example Output Table:**

| Capacity | Duration | Power | DG | Delivery % | Curtailed % | DG Hours | Cycles |
| ---------- | ---------- | ------- | ----- | ------------ | ------------- | ---------- | -------- |
| 100 MWh | 1-hr | 100 MW | 0 | 97.2% | 0.8% | 0 | 245 |
| 100 MWh | 2-hr | 50 MW | 0 | 96.1% | 2.4% | 0 | 231 |
| 100 MWh | 4-hr | 25 MW | 0 | 93.8% | 6.9% | 0 | 198 |
| 100 MWh | 10-hr | 10 MW | 0 | 84.2% | 22.1% | 0 | 112 |
| 100 MWh | 2-hr | 50 MW | 10 | 99.8% | 1.9% | 156 | 218 |
| 150 MWh | 4-hr | 37.5 MW | 0 | 98.4% | 3.1% | 0 | 156 |
| 200 MWh | 4-hr | 50 MW | 0 | 99.7% | 1.4% | 0 | 121 |

### 8.2 Sorting & Filtering (UI)

**Default sort:** Delivery % descending, then Curtailed % ascending

**Quick filters:**

| Filter | Logic |
| -------- | ------- |
| "100% Delivery" | Show only rows where `delivery_pct` = 100% |
| "Zero DG" | Show only rows where `dg_size` = 0 |
| "No Curtailment" | Show only rows where `curtailed_pct` < 1% |
| "Hide Dominated" | Hide rows where `is_dominated` = True |

**Column sorting:** User can click any column header to sort ascending/descending

### 8.3 Dominated Configuration Logic

A configuration is **dominated** if another configuration exists that is:

- Equal or better on `delivery_pct`
- Equal or better on `curtailed_pct` (lower is better)
- Equal or smaller on `capacity`
- Equal or smaller on `dg_size`
- **Strictly better** on at least one of the above metrics

Dominated rows are flagged with `is_dominated = True`.

**UI Default:** Dominated rows shown but can be hidden via filter.

### 8.4 Performance Metrics (Per Configuration)

| Output | Unit | Description |
| -------- | ------ | ------------- |
| Hours of ANY Delivery | hours, % | Per metric C1 |
| Hours of FULL Delivery | hours, % | Per metric C2 |
| Hours of GREEN Delivery | hours, % | Per metric C3 |
| Unserved Energy | MWh, % | Total energy not delivered |

### 8.5 Energy Flow Summary (Per Configuration)

| Output | Unit | Description |
| -------- | ------ | ------------- |
| Total Load | MWh | Annual load |
| Solar to Load | MWh | Direct solar consumption |
| Solar to BESS | MWh | Solar used to charge BESS |
| Solar Curtailed | MWh | Excess solar wasted |
| BESS Discharged | MWh | Energy delivered from BESS |
| DG to Load | MWh | Direct DG consumption |
| DG to BESS | MWh | DG used to charge BESS |
| DG Total Generation | MWh | Total DG output |

### 8.6 Operational Metrics (Per Configuration)

| Output | Unit | Description |
| -------- | ------ | ------------- |
| BESS Cycles | count | Equivalent full cycles |
| BESS Throughput | MWh | Total energy through BESS |
| DG Runtime | hours | Total hours DG operated |
| DG Starts | count | Number of start events |

### 8.7 Output Formats

**Decision:** Both dashboard and Excel export

- **Dashboard:** Interactive table with sorting, filtering, column selection
- **Excel Export:** Full comparison table plus detailed hourly data (optional)

---

## 9. Technical Approach

### 9.1 Simulation Method

- Hourly time-step simulation (8760 hours)
- Sequential dispatch logic per template
- State tracking: BESS SoC, DG status (on/off)

### 9.2 Sizing Method

- **Single-stage full sweep** over all combinations
- For each capacity × duration class × DG size: run full simulation
- Record all metrics per configuration
- Return comparison table for user decision

### 9.3 Technology Stack (Proposed)

- **Backend:** Python
- **Simulation Engine:** NumPy/Pandas
- **UI (MVP):** Streamlit
- **Export:** OpenPyXL for Excel

---

## 10. Decisions Log

| # | Decision | Date |
| --- | ---------- | ------ |
| D1 | Four topologies defined (A, B, C, D); MVP includes only A and C (grid excluded) | Current |
| D2 | Dispatch via predefined templates (Option A); custom rules deferred to V2 | Current |
| D3 | Time windows: support both fixed hours and dynamic (sunrise/sunset) | Current |
| D4 | Grid excluded from MVP entirely | Current |
| D5 | DG capacity: can be fixed input OR sized by tool (user choice) | Current |
| D6 | DG charges BESS: selectable option per template | Current |
| D7 | Success criteria: all four metrics (C1-C4) supported | Current |
| D8 | Criteria can be combined (objective + constraints) | Current |
| D9 | MVP problem types: Sizing Optimization, Scenario Comparison | Current |
| D10 | Load/Solar profiles: custom CSV upload only (plus Load Scenario Builder) | Current |
| D11 | Output: dashboard + Excel export | Current |
| D12 | Delivery evaluation: binary (0/1) per hour | Current |
| D13 | Seven dispatch templates for MVP (0-6) | Current |
| D14 | Load Profile: CSV upload OR Load Scenario Builder | Current |
| D15 | Solar profile in absolute MW; solar_capacity as separate input | Current |
| D16 | BESS: separate charge/discharge power limits (in Fixed Mode) | Current |
| D17 | BESS: single round-trip efficiency (not separate charge/discharge) | Current |
| D18 | BESS: C-rate limits included with default of 1C (Fixed Mode only) | Current |
| D19 | BESS: DoD constraint included | Current |
| D20 | BESS: Daily cycle limit with optional enforcement | Current |
| D21 | BESS: Cycle counting uses discharge throughput only | Current |
| D22 | **UPDATED:** BESS Sizing: User inputs capacity range only; power derived from duration class | Current |
| D23 | DG: Running mode (Full Capacity or Load-Following) configurable | Current |
| D24 | DG: Charges BESS configurable (Yes/No), only when already running for load | Current |
| D25 | Simulation: 8760 hours (full year), hourly resolution, fixed for MVP | Current |
| D26 | SME Confirmed: Merit order Solar → BESS → Unserved is correct | Current |
| D27 | SME Confirmed: Efficiency split sqrt(RTE) for charge and discharge is industry standard | Current |
| D28 | SME Confirmed: Cycle counting uses discharge throughput only (matches OEM warranties) | Current |
| D29 | SME Confirmed: C-rate handling is correct | Current |
| D30 | SME Confirmed: Hourly resolution sufficient for CapEx sizing | Current |
| D31 | Cycle limit enforce mode: Full disable (charge AND discharge) when limit hit | Current |
| D32 | Cycle limit count-only mode: Track and report, no disabling | Current |
| D33 | Degradation buffer: Documented for future, not in MVP (tool sizes for Year 1) | Current |
| D34 | BESS cannot charge and discharge in same hour | Current |
| D35 | MW treated as MWh for hourly time step (Δt = 1 hour) | Current |
| D36 | Template 5 (DG Day Charge) added | Current |
| D37 | Template 1: DG runs at Full Capacity only (Load-Following deferred to V2) | Current |
| D38 | DG metrics: Track runtime hours and start counts as outputs | Current |
| D39 | DG min runtime hours: V2 parameter | Current |
| D40 | Charge power limit shared across all charging sources within same hour | Current |
| D41 | Green definition: Simplified (DG off = green hour), source-aware tracking in V2 | Current |
| D42 | Application will have dedicated page for algorithms, concepts, formulas | Current |
| D43-D91 | Template-specific validations and behaviors (see individual templates) | Current |
| D92 | **NEW:** Sizing Mode: User inputs capacity range only; power derived from duration | Current |
| D93 | **NEW:** Duration classes: 1, 2, 3, 4, 6, 8, 10 hours (system-generated) | Current |
| D94 | **NEW:** Sizing output: Full comparison table, not single recommendation | Current |
| D95 | **NEW:** User decides optimal config from table; no auto-selection | Current |
| D96 | **NEW:** Dominated configurations flagged but not hidden by default | Current |
| D97 | **NEW:** Charge power = Discharge power (symmetric) in Sizing Mode | Current |

---

## 11. Open Items (Still To Be Defined)

| Item | Description | Status |
| ------ | ------------- | -------- |
| Template 0 dispatch logic | Solar + BESS only | ✓ COMPLETE |
| Template 1 dispatch logic | Green Priority with DG | ✓ COMPLETE (v1.2) |
| Template 2 dispatch logic | DG Night Charge | ✓ COMPLETE (v1.2) |
| Template 3 dispatch logic | DG Blackout Window | ✓ COMPLETE (v1.1) |
| Template 4 dispatch logic | DG Emergency Only | ✓ COMPLETE (v1.1) |
| Template 5 dispatch logic | DG Day Charge | ✓ COMPLETE (v1.1) |
| Template 6 dispatch logic | DG Night SoC Trigger | ✓ COMPLETE (v1.2) |
| Input validation rules | Acceptable ranges, error handling | ✓ COMPLETE |
| **Sizing iteration logic** | How to iterate and compare sizes | ✓ COMPLETE |
| **Output table structure** | Columns, sorting, filtering | ✓ COMPLETE |
| Scenario comparison logic | How to run and rank multiple scenarios | Pending |
| UI wireframes | Screen layouts and user flow | Pending |
| Edge cases | What happens in specific failure modes | Partial |

---

## 12. Out of Scope (Deferred)

| Feature | Deferred To |
| --------- | ------------- |
| Grid connectivity (import/export) | V2 |
| Custom IF-THEN dispatch rules | V2 |
| Financial modeling (IRR, NPV, LCOE) | V2 |
| Battery degradation modeling | V2 |
| Degradation buffer / SoH factor for 10-year sizing | V2 |
| Sub-hourly resolution (15-min, 30-min) | V2 |
| Sensitivity analysis charts | V2 |
| Multiple time periods per day | V2 |
| Multiple blackout windows (Template 3) | V2 |
| Dynamic blackout window (based on solar profile) | V2 |
| Emergency DG override during blackout | V2 |
| DG start-up time modeling | V2 |
| DG min load constraint | V2 |
| DG fuel consumption tracking | V2 |
| DG emissions tracking | V2 |
| DG min runtime hours (prevent short cycling) | V2 |
| DG ramp rates | V2 |
| DG load-following mode | V2 |
| Multiple DG units | V2 |
| BESS self-discharge | V2 |
| BESS unit combinations (1×100 MW vs 4×25 MW) | V2 |
| BESS source-aware energy tracking | V2 |
| Load priority / partial shedding | V2 |
| Solar degradation, availability | V2 |
| Partial year simulations | V2 |
| Time zone handling | V2 |
| Inverter/AC clipping limits | V2 |
| Auxiliary/BOP consumption | V2 |
| Asset availability / forced outages | V2 |
| Time window optimization (minimize DG runtime) | V2 |
| Combined DG OFF trigger (Day starts AND SoC threshold) | V2 |
| Optional cycle enforcement for Template 4 | V2 |
| Cost estimates in output table | V2 |
| Recommended configuration auto-selection | V2 |

**MVP Limitation (Documented):**

- Tool sizes for Year 1 conditions only
- Users should apply manual degradation factor for long-term projects until V2
- One-hour lag in DG decisions (sub-hourly resolution in V2)

---

## Appendix A: Glossary

| Term | Definition |
| ------ | ------------ |
| BESS | Battery Energy Storage System |
| DG | Diesel/Gas Generator |
| SoC | State of Charge (% of BESS capacity) |
| Merit Order | Priority sequence for dispatching energy sources |
| Unserved Energy | Load demand that could not be met |
| Curtailment | Excess generation that is wasted |
| Green Energy | Energy from Solar or BESS (charged by solar) |
| Duration | Hours to fully discharge at max power (Capacity ÷ Power) |
| C-Rate | Power relative to capacity (1C = full charge/discharge in 1 hour) |
| Dominated | A configuration where another exists that is equal or better on all metrics |

---

## Appendix B: Duration Class Reference

| Duration | C-Rate | Example: 100 MWh | Use Case |
| ---------- | -------- | ------------------ | ---------- |
| 1-hour | 1C | 100 MW power | Frequency response, high variability |
| 2-hour | 0.5C | 50 MW power | Most common utility-scale |
| 3-hour | 0.33C | 33.3 MW power | Transitional applications |
| 4-hour | 0.25C | 25 MW power | Capacity contracts, arbitrage |
| 6-hour | 0.167C | 16.7 MW power | Long-duration emerging |
| 8-hour | 0.125C | 12.5 MW power | Extended storage |
| 10-hour | 0.1C | 10 MW power | Maximum duration tested |

**Trade-offs:**

| Shorter Duration (1-2 hr) | Longer Duration (6-10 hr) |
| --------------------------- | --------------------------- |
| Higher power per MWh | Lower power per MWh |
| Better at absorbing solar spikes | May curtail solar (power-limited) |
| Better at serving load spikes | May not serve peak load |
| More expensive per MWh | Less expensive per MWh |
| Smaller footprint per MW | Larger footprint per MWh |

---

*End of Requirements Specification*
