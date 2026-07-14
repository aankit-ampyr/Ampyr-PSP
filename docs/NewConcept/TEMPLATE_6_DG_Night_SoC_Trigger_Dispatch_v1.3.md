# Template 6: DG Night SoC Trigger - Dispatch Logic Specification

**Status:** FINALIZED (SME Reviewed)  
**Version:** 1.3  
**Topology:** C (Solar + BESS + DG, No Grid)  
**Last Updated:** 2025-12-01

---

## 1. Overview

### 1.1 Description

SoC-triggered night charging strategy with green days. DG is **disabled** during day hours to maintain green operation (solar + BESS only). During night, DG activates when BESS SoC drops below threshold, serving load and charging BESS. This is the **inverse of Template 5** (which has reactive DG during day, disabled at night).

**Critical Design Note:** DG is **SoC-triggered, not load-triggered**. DG will run to recover BESS even during zero-load periods if SoC is below the ON threshold.

### 1.2 Use Case

- Sites requiring green operation during daylight hours (emissions/permit restrictions)
- Sites where DG should only run as backup, not routine charging
- Minimizing DG runtime while maintaining reliability
- Cost-conscious operations (run DG only when necessary)

### 1.3 Key Difference from Other Templates

| Aspect | Template 2 (Night Charge) | Template 5 (Day Charge) | Template 6 (Night SoC Trigger) |
| -------- | --------------------------- | ------------------------- | ------------------------------- |
| DG allowed | Night | Day | **Night** |
| DG disabled | Day | Night | **Day** |
| DG trigger | Proactive (night starts) | Reactive (SoC threshold) | **Reactive (SoC threshold)** |
| Use case | Scheduled charging | Silent nights | **Minimize DG, green days** |
| Emergency override | Day (optional) | Night (optional) | **Day (optional)** |

### 1.4 Merit Order

**Night Hours (DG Allowed):**

*When DG is OFF:*

1. Solar direct to load (minimal at night)
2. BESS discharge to load
3. Unserved energy (triggers DG if SoC drops to threshold)

*When DG is ON (SoC triggered):*

1. Solar direct to load
2. DG to remaining load (DG takes priority)
3. **IF DG < remaining load:** BESS assists — "Assist Mode"
4. **IF DG ≥ remaining load:** BESS rests, excess charges BESS
5. Unserved energy (only if all insufficient)

**Day Hours (DG Disabled):**

1. Solar direct to load
2. BESS discharge to load
3. Emergency DG (if enabled and SoC critical)
4. Unserved energy

### 1.5 Cycle Limit Policy

**Template 6 allows cycle limit enforcement.**

- Cycles are tracked and reported
- If `bess_enforce_cycle_limit = True`, BESS is disabled when limit reached
- Rationale: Day operation is predictable (solar available)

---

## 2. Input Parameters

### 2.1 Profiles (8760 hourly values)

| Parameter | Description | Unit |
| ----------- | ------------- | ------ |
| `load_profile[t]` | Hourly load demand | MW |
| `solar_profile[t]` | Hourly solar generation | MW |

### 2.2 BESS Parameters

| Parameter | Description | Unit | Default | Fixed Mode | Sizing Mode |
| ----------- | ------------- | ------ | --------- | ------------ | ------------- |
| `bess_capacity` | Total energy capacity | MWh | Required | User input | Iterated (range) |
| `bess_charge_power` | Max charge rate | MW | Required | User input | **Auto-calculated** |
| `bess_discharge_power` | Max discharge rate | MW | Required | User input | **Auto-calculated** |
| `bess_efficiency` | Round-trip efficiency | % | 85 | User input | User input |
| `bess_min_soc` | Minimum SoC floor | % | 10 | User input | User input |
| `bess_max_soc` | Maximum SoC ceiling | % | 90 | User input | User input |
| `bess_initial_soc` | Starting SoC | % | 50 | User input | User input |
| `bess_charge_c_rate` | Max charge C-rate | C | 1 | User input | Not used |
| `bess_discharge_c_rate` | Max discharge C-rate | C | 1 | User input | Not used |
| `bess_daily_cycle_limit` | Max cycles per day | cycles | None | User input | User input |
| `bess_enforce_cycle_limit` | Enforce limit? | Boolean | False | User input | User input |

### 2.3 DG Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `dg_capacity` | Rated power output | MW | Required |
| `dg_charges_bess` | Can DG charge BESS? | Boolean | True |

### 2.4 Time Window Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `night_window_mode` | How night is defined | Fixed / Dynamic | Fixed |
| `night_start_hour` | Night begins (if Fixed) | Hour (0-23) | 18 |
| `night_end_hour` | Night ends (if Fixed) | Hour (0-23) | 6 |

**Night Window Modes:**

- **Fixed:** User specifies start/end hours (e.g., 18:00 - 06:00)
- **Dynamic:** Night = hours outside the solar production window
  - Uses epsilon (0.01 MW) to filter noise

### 2.5 DG SoC Trigger Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `dg_soc_on_threshold` | SoC at/below which DG turns ON | % | 30 |
| `dg_soc_off_threshold` | SoC at/above which DG turns OFF | % | 80 |

### 2.6 Emergency DG Parameters (Day)

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `allow_emergency_dg_day` | Allow DG during day if SoC critical? | Boolean | False |
| `emergency_soc_threshold` | SoC at/below which emergency DG activates | % | 15 |

### 2.7 Sizing Mode Behavior (NEW)

In **Sizing Mode**, the simulation engine iterates through multiple configurations.

**User Inputs (Sizing Mode):**

- `bess_capacity_min`, `bess_capacity_max`, `bess_capacity_step` (MWh range)
- `dg_capacity_min`, `dg_capacity_max`, `dg_capacity_step` (MW range)

**System-Generated Duration Classes:**
For each BESS capacity value, the system automatically tests 7 duration classes:

| Duration | C-Rate | Power Calculation |
| ---------- | -------- | ------------------- |
| 1-hour | 1C | `power = capacity ÷ 1` |
| 2-hour | 0.5C | `power = capacity ÷ 2` |
| 3-hour | 0.33C | `power = capacity ÷ 3` |
| 4-hour | 0.25C | `power = capacity ÷ 4` |
| 6-hour | 0.167C | `power = capacity ÷ 6` |
| 8-hour | 0.125C | `power = capacity ÷ 8` |
| 10-hour | 0.1C | `power = capacity ÷ 10` |

**Power Derivation:**

```
bess_charge_power = bess_capacity ÷ duration_hours
bess_discharge_power = bess_capacity ÷ duration_hours
```

**Note:** Night window and SoC threshold parameters are NOT iterated.

See `SIZING_MODE_SPECIFICATION.md` for full details.

---

## 3. Input Validation (Pre-Simulation)

```
# ═══════════════════════════════════════════════════════════════════
# ERRORS (Block Simulation)
# ═══════════════════════════════════════════════════════════════════

# Threshold ordering validation (CRITICAL)
IF dg_soc_on_threshold >= dg_soc_off_threshold:
    ERROR "DG ON threshold must be strictly less than OFF threshold"
END IF

# Threshold bounds validation
IF dg_soc_on_threshold < bess_min_soc:
    ERROR "DG ON threshold cannot be below BESS min SoC"
END IF

IF dg_soc_off_threshold > bess_max_soc:
    ERROR "DG OFF threshold cannot exceed BESS max SoC"
END IF

IF emergency_soc_threshold < bess_min_soc:
    ERROR "Emergency SoC threshold cannot be below BESS min SoC"
END IF

# Time window validation
IF night_start_hour < 0 OR night_start_hour > 23:
    ERROR "Night start hour must be between 0 and 23"
END IF

IF night_end_hour < 0 OR night_end_hour > 23:
    ERROR "Night end hour must be between 0 and 23"
END IF

# ═══════════════════════════════════════════════════════════════════
# WARNINGS (Log and Continue)
# ═══════════════════════════════════════════════════════════════════

# Zero night window
IF night_start_hour == night_end_hour:
    WARNING "Night window is 0 hours. DG will be disabled at all times (except emergency)."
END IF

# Small deadband warning
deadband_size = dg_soc_off_threshold - dg_soc_on_threshold
IF deadband_size < 20:
    WARNING "Small deadband (<20%) may result in frequent DG cycling"
END IF
```

---

## 4. Derived Constants (Calculated Once at Initialization)

```
# ═══════════════════════════════════════════════════════════════════
# BESS Capacity limits (MWh)
# ═══════════════════════════════════════════════════════════════════
usable_capacity = bess_capacity × (bess_max_soc - bess_min_soc) / 100
min_soc_mwh = bess_capacity × bess_min_soc / 100
max_soc_mwh = bess_capacity × bess_max_soc / 100

# ═══════════════════════════════════════════════════════════════════
# BESS Power limits (MW)
# In Fixed Mode: constrained by both rating and C-rate
# In Sizing Mode: power comes directly from duration class
# ═══════════════════════════════════════════════════════════════════
IF sizing_mode:
    charge_power_limit = bess_charge_power
    discharge_power_limit = bess_discharge_power
ELSE:
    charge_power_limit = min(bess_charge_power, bess_capacity × bess_charge_c_rate)
    discharge_power_limit = min(bess_discharge_power, bess_capacity × bess_discharge_c_rate)
END IF

# ═══════════════════════════════════════════════════════════════════
# Efficiency factors
# ═══════════════════════════════════════════════════════════════════
charge_efficiency = sqrt(bess_efficiency / 100)
discharge_efficiency = sqrt(bess_efficiency / 100)

# ═══════════════════════════════════════════════════════════════════
# DG SoC Thresholds (in MWh)
# ═══════════════════════════════════════════════════════════════════
dg_soc_on_mwh = bess_capacity × dg_soc_on_threshold / 100
dg_soc_off_mwh = bess_capacity × dg_soc_off_threshold / 100
emergency_soc_mwh = bess_capacity × emergency_soc_threshold / 100

# Night window pre-calculation
# Build is_night_hour[0..23] array for quick lookup
IF night_window_mode == "Dynamic":
    daylight_hours = set()
    FOR t = 1 TO 8760:
        hour_of_day = (t - 1) MOD 24
        IF solar_profile[t] > 0.01:
            daylight_hours.add(hour_of_day)
    END FOR
    # Night = hours NOT in daylight_hours
    ...
END IF

# Initial state
soc = bess_capacity × bess_initial_soc / 100
```

---

## 5. State Variables

| Variable | Description | Initial Value | Resets |
| ---------- | ------------- | --------------- | -------- |
| `soc` | Current BESS state of charge (MWh) | `bess_capacity × initial_soc / 100` | Never |
| `daily_discharge` | BESS energy discharged today (MWh) | 0 | Daily |
| `daily_cycles` | BESS cycles consumed today | 0 | Daily |
| `bess_disabled_today` | BESS disabled flag (enforce mode) | False | Daily |
| `current_day` | Day counter (1-365) | 1 | Never |
| `dg_was_running` | DG state in previous hour | False | Never |
| `bess_discharged_this_hour` | BESS discharged flag | False | Hourly |
| `dg_mode` | Current DG mode | "OFF" | Never |

**Per-Day Tracking Arrays:**

| Variable | Description | Size |
| ---------- | ------------- | ------ |
| `max_daily_cycles_per_day[]` | Peak cycles reached each day | 365 |

---

## 6. Hourly Output Variables

| Variable | Description | Unit |
| ---------- | ------------- | ------ |
| `solar_to_load` | Solar energy serving load directly | MWh |
| `solar_to_bess` | Solar energy charging BESS | MWh |
| `solar_curtailed` | Excess solar wasted | MWh |
| `bess_to_load` | BESS energy serving load | MWh |
| `dg_to_load` | DG energy serving load | MWh |
| `dg_to_bess` | DG energy charging BESS | MWh |
| `dg_curtailed` | Excess DG wasted | MWh |
| `dg_running` | DG on/off status this hour | Boolean |
| `dg_mode` | "OFF" / "NORMAL" / "EMERGENCY" | String |
| `bess_assisted` | BESS assisted DG this hour | Boolean |
| `is_night` | Whether hour is in night window | Boolean |
| `unserved` | Load not served | MWh |
| `soc` | End-of-hour BESS state of charge | MWh |
| `daily_cycles` | Cumulative BESS cycles for the day | cycles |
| `bess_disabled` | BESS disabled due to cycle limit | Boolean |

---

## 7. Sizing Mode Output (NEW)

When run in Sizing Mode, the simulation produces a **comparison table**:

| Column | Description | Unit |
| -------- | ------------- | ------ |
| `capacity` | BESS energy capacity | MWh |
| `duration` | Duration class | hours |
| `power` | Calculated charge/discharge power | MW |
| `dg_size` | DG capacity | MW |
| `delivery_pct` | Hours with 100% delivery ÷ 8760 | % |
| `green_pct` | Hours with 100% green delivery | % |
| `unserved_mwh` | Total unserved energy | MWh |
| `curtailed_pct` | Solar curtailment % | % |
| `dg_runtime_hrs` | Total DG running hours | hours |
| `dg_starts` | Number of DG start events | count |
| `bess_cycles` | Annual equivalent cycles | cycles |
| `hours_emergency_dg` | Emergency DG hours during day | hours |
| `pct_day_green` | % of day hours with no DG | % |
| `is_dominated` | True if strictly dominated | Boolean |

**Template-Specific Columns:**

- `hours_emergency_dg` — Day hours where emergency DG ran
- `pct_day_green` — Key metric for emissions/permit-restricted sites

---

## 8. Dispatch Logic

[Core dispatch logic unchanged from v1.2 - refer to original document]

The dispatch logic steps remain identical. Only the initialization of power limits changes based on Sizing Mode vs Fixed Mode as specified in Section 4.

**Critical Bug Fix (v1.2):** DG trigger logic does NOT check `bess_disabled_today`. DG runs independent of BESS cycle limit state to maintain reliability.

---

## 9. Edge Cases

| Scenario | Expected Behavior |
| ---------- | ------------------- |
| Night start == Night end | No night window (0 hours), DG always disabled |
| Night spans midnight (e.g., 18-06) | Handled by is_night_hour[] logic |
| **DG ON, DG < Load (night)** | **BESS assists, no charging** |
| **DG ON, DG ≥ Load (night)** | **BESS rests, excess charges BESS** |
| **Zero load, low SoC (night)** | **DG runs for proactive charging** |
| **Sunrise Cut** | **DG forced OFF immediately when day starts** |
| **Evening Carryover** | **Emergency DG transitions to Normal mode** |
| Emergency DG disabled, SoC critical during day | Unserved energy |
| Cycle limit reached (enforce mode) | BESS disabled, DG unaffected |
| **BESS disabled, DG triggered** | **DG serves load, cannot assist with BESS** |
| **BESS disabled, DG < Load** | **Remaining load is unserved** |

---

## 10. Assumptions and Simplifications

| Assumption | Description |
| ------------ | ------------- |
| **Hourly resolution** | Δt = 1 hour; MW values represent MWh |
| **365-day year** | 8760 hours; leap years not handled |
| **No DG fuel/emissions** | Fuel consumption not tracked |
| **Full capacity only** | DG outputs 100% when ON |
| **DG priority when ON** | DG serves first, BESS assists if needed |
| **Simplified green metric** | All BESS discharge treated as green |
| **Year 1 sizing** | No degradation buffer |
| **Deadband hysteresis** | Prevents rapid cycling |
| **SoC-only trigger** | DG runs for proactive charging even with zero load |
| **DG-BESS Independence** | DG runs even when BESS disabled |
| **Sizing Mode symmetric power** | Charge power = Discharge power |

---

## 11. Developer Acceptance Checklist

Before marking implementation complete, verify:

**Sizing Mode:**

- [ ] Sizing Mode correctly derives power from capacity and duration
- [ ] All 7 duration classes tested for each capacity × DG combination
- [ ] Output comparison table includes `hours_emergency_dg` and `pct_day_green`

**Time Window Handling:**

- [ ] Time window calculation handles all cases (midnight crossing, no window)
- [ ] `is_night_hour[]` array pre-calculated correctly
- [ ] Dynamic window uses epsilon (0.01 MW) to filter noise

**Night Hours Logic:**

- [ ] DG triggers on SoC threshold (SoC-triggered, not load-triggered)
- [ ] DG runs even with zero load if SoC below ON threshold
- [ ] Deadband hysteresis prevents rapid cycling

**Day Hours Logic:**

- [ ] DG strictly disabled during day (unless emergency)
- [ ] Emergency DG only activates when enabled AND SoC ≤ emergency threshold

**Transitions:**

- [ ] **Sunrise Cut:** DG forced OFF immediately when day starts
- [ ] **Evening Carryover:** Emergency DG transitions to NORMAL mode

**DG-BESS Independence (Bug Fix v1.2):**

- [ ] DG trigger logic does NOT check `bess_disabled_today`
- [ ] DG runs to serve load even when BESS is disabled
- [ ] BESS assist is gated by `NOT bess_disabled_today`
- [ ] When BESS disabled + DG < Load: remaining load is unserved

**Assist Mode & Recovery Mode:**

- [ ] **Assist Mode:** When DG ON and DG < Load, BESS assists
- [ ] **Recovery Mode:** When DG ON and DG ≥ Load, BESS rests and charges
- [ ] BESS never charges and discharges in same hour

**State Management:**

- [ ] SoC clamping applied after all operations each hour
- [ ] Cycle limit enforcement works correctly when enabled
- [ ] `bess_disabled_today` blocks both charge and discharge

---

**Document Status: APPROVED FOR IMPLEMENTATION**
