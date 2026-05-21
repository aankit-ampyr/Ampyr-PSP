# Template 5: DG Day Charge - Dispatch Logic Specification

**Status:** FINALIZED (SME Reviewed)  
**Version:** 1.2  
**Topology:** C (Solar + BESS + DG, No Grid)  
**Last Updated:** 2025-12-01

---

## 1. Overview

### 1.1 Description

SoC-triggered day charging strategy with silent nights. DG is **disabled** during night hours to maintain quiet operation (residential areas, noise restrictions). During day, DG activates when BESS SoC drops below threshold, serving load and charging BESS alongside solar. This is the **inverse of Template 6** (which has reactive DG at night, disabled during day).

**Critical Design Note:** DG is **SoC-triggered, not load-triggered**. DG will run to recover BESS even during zero-load periods if SoC is below the ON threshold.

### 1.2 Use Case

- Sites near residential areas requiring silent night operation
- Sites with daytime noise tolerance (industrial neighbors, remote)
- Sites where solar alone cannot maintain SoC during cloudy days
- Maximizing green operation at night (BESS only)

### 1.3 Merit Order

**Day Hours (DG Allowed):**

*When DG is OFF:*

1. Solar direct to load
2. BESS discharge to load
3. Unserved energy (triggers DG if SoC drops to threshold)

*When DG is ON (SoC triggered):*

1. Solar direct to load
2. DG to remaining load (DG takes priority)
3. **IF DG < remaining load:** BESS assists — "Assist Mode"
4. **IF DG ≥ remaining load:** BESS rests, excess charges BESS
5. Unserved energy (only if all insufficient)

**Night Hours (DG Disabled):**

1. Solar direct to load (minimal/zero at night)
2. BESS discharge to load
3. Emergency DG (if enabled and SoC critical)
4. Unserved energy

### 1.4 Cycle Limit Policy

**Template 5 uses monitor-only cycle counting.**

- `bess_enforce_cycle_limit` is forced to `False`
- Cycles are tracked and reported
- Rationale: Night blackout is predictable; users can size BESS appropriately

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
| `bess_enforce_cycle_limit` | Enforce limit? | Boolean | **False** | **Forced False** | **Forced False** |

### 2.3 DG Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `dg_capacity` | Rated power output | MW | Required |
| `dg_charges_bess` | Can DG charge BESS? | Boolean | True |

### 2.4 Time Window Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `day_window_mode` | How day is defined | Fixed / Dynamic | Fixed |
| `day_start_hour` | Day begins (if Fixed) | Hour (0-23) | 6 |
| `day_end_hour` | Day ends (if Fixed) | Hour (0-23) | 18 |

**Day Window Modes:**

- **Fixed:** User specifies start/end hours (e.g., 06:00 - 18:00)
- **Dynamic:** Day = hours within the solar production window

### 2.5 DG SoC Trigger Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `dg_soc_on_threshold` | SoC at/below which DG turns ON | % | 30 |
| `dg_soc_off_threshold` | SoC at/above which DG turns OFF | % | 80 |

### 2.6 Emergency DG Parameters (Night)

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `allow_emergency_dg_night` | Allow DG during night if SoC critical? | Boolean | False |
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

**Note:** Day window and SoC threshold parameters are NOT iterated.

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
IF day_start_hour < 0 OR day_start_hour > 23:
    ERROR "Day start hour must be between 0 and 23"
END IF

IF day_end_hour < 0 OR day_end_hour > 23:
    ERROR "Day end hour must be between 0 and 23"
END IF

# ═══════════════════════════════════════════════════════════════════
# WARNINGS (Log and Continue)
# ═══════════════════════════════════════════════════════════════════

# Cycle limit enforcement override
IF bess_enforce_cycle_limit == True:
    WARNING "Template 5 uses monitor-only cycle counting. Setting enforce to False."
    bess_enforce_cycle_limit = False
END IF

# Zero day window
IF day_start_hour == day_end_hour:
    WARNING "Day window is 0 hours. DG will be disabled at all times."
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

# Day window pre-calculation
# Build is_day_hour[0..23] array for quick lookup
IF day_window_mode == "Dynamic":
    # Calculate from solar profile
    daylight_hours = set()
    FOR t = 1 TO 8760:
        hour_of_day = (t - 1) MOD 24
        IF solar_profile[t] > 0.01:
            daylight_hours.add(hour_of_day)
    END FOR
    dynamic_day_start = min(daylight_hours)
    dynamic_day_end = max(daylight_hours) + 1
    # Build array using dynamic values
    ...
ELSE:
    # Use fixed values
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
| `is_day` | Whether hour is in day window | Boolean |
| `unserved` | Load not served | MWh |
| `soc` | End-of-hour BESS state of charge | MWh |
| `daily_cycles` | Cumulative BESS cycles for the day | cycles |

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
| `hours_emergency_dg` | Emergency DG hours during night | hours |
| `pct_night_silent` | % of night hours with DG off | % |
| `is_dominated` | True if strictly dominated | Boolean |

**Template-Specific Columns:**

- `hours_emergency_dg` — Night hours where emergency DG ran
- `pct_night_silent` — Key metric for noise-sensitive sites

---

## 8. Dispatch Logic

[Core dispatch logic unchanged from v1.1 - refer to original document]

The dispatch logic steps remain identical. Only the initialization of power limits changes based on Sizing Mode vs Fixed Mode as specified in Section 4.

---

## 9. Edge Cases

| Scenario | Expected Behavior |
| ---------- | ------------------- |
| Day start == Day end | No day window (0 hours), DG always disabled |
| Day spans midnight (e.g., 22-06) | Handled by is_day_hour[] logic |
| Solar available at night | Rare but handled - solar serves load |
| **DG ON, DG < Load (day)** | **BESS assists, no charging** |
| **DG ON, DG ≥ Load (day)** | **BESS rests, excess charges BESS** |
| **Zero load, low SoC (day)** | **DG runs for proactive charging** |
| **Sunset Cut** | **DG forced OFF immediately when night starts** |
| **Morning Carryover** | **Emergency DG transitions to Normal mode** |
| Emergency DG disabled, SoC critical at night | Unserved energy |

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
| **Monitor-only cycles** | Cycles counted but not enforced |
| **SoC-only trigger** | DG runs for proactive charging even with zero load |
| **Sizing Mode symmetric power** | Charge power = Discharge power |

---

## 11. Developer Acceptance Checklist

Before marking implementation complete, verify:

**Sizing Mode:**

- [ ] Sizing Mode correctly derives power from capacity and duration
- [ ] All 7 duration classes tested for each capacity × DG combination
- [ ] Output comparison table includes `hours_emergency_dg` and `pct_night_silent`

**Time Window Handling:**

- [ ] Time window calculation handles all cases (normal, midnight crossing, no window)
- [ ] `is_day_hour[]` array pre-calculated correctly
- [ ] Dynamic window uses epsilon (0.01 MW) to filter noise

**Day Hours Logic:**

- [ ] DG triggers on SoC threshold (SoC-triggered, not load-triggered)
- [ ] DG runs even with zero load if SoC below ON threshold
- [ ] Deadband hysteresis prevents rapid cycling

**Night Hours Logic:**

- [ ] DG strictly disabled at night (unless emergency)
- [ ] Emergency DG only activates when enabled AND SoC ≤ emergency threshold

**Transitions:**

- [ ] **Sunset Cut:** DG forced OFF immediately when night starts
- [ ] **Morning Carryover:** Emergency DG transitions to NORMAL mode

**Assist Mode & Recovery Mode:**

- [ ] **Assist Mode:** When DG ON and DG < Load, BESS assists
- [ ] **Recovery Mode:** When DG ON and DG ≥ Load, BESS rests and charges
- [ ] BESS never charges and discharges in same hour

---

**Document Status: APPROVED FOR IMPLEMENTATION**
