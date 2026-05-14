# Template 2: DG Night Charge - Dispatch Logic Specification

**Status:** FINALIZED (SME Reviewed)  
**Version:** 1.3  
**Topology:** C (Solar + BESS + DG, No Grid)  
**Last Updated:** 2025-12-01

---

## 1. Overview

### 1.1 Description

Proactive night charging strategy. DG automatically turns ON when night window begins to serve load and charge BESS. During day, DG is disabled to maximize green energy usage. BESS is sized to cover daytime load with solar support.

### 1.2 Use Case

- Sites with cheap/available fuel at night
- Sites requiring green-only operation during business hours
- Maximizing solar utilization during day

### 1.3 Merit Order

**Night Hours:**

1. DG to load (proactive - ON at night start)
2. DG excess to BESS
3. BESS discharge (if DG off due to SoC threshold)
4. Unserved energy

**Day Hours:**

1. Solar direct to load
2. BESS discharge to load
3. Emergency DG (if enabled and SoC critical)
4. Unserved energy

### 1.4 Key Characteristics

- DG turns ON proactively at night start (not reactive to load deficit)
- DG runs at Full Capacity when ON
- DG turns OFF based on user selection: Day starts OR SoC threshold reached
- Day is strictly green unless emergency override enabled

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

### 2.5 DG Control Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `dg_off_trigger` | What turns DG off | Day_Start / SoC_Threshold | Day_Start |
| `dg_soc_on_threshold` | SoC below which DG turns ON (if SoC_Threshold mode) | % | 30 |
| `dg_soc_off_threshold` | SoC above which DG turns OFF (if SoC_Threshold mode) | % | 80 |
| `allow_emergency_dg_day` | Allow DG during day if SoC critical? | Boolean | False |
| `emergency_soc_threshold` | SoC below which emergency DG activates | % | 15 |

### 2.6 Sizing Mode Behavior (NEW)

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

**Note:** Time window parameters (`night_start_hour`, `night_end_hour`, etc.) and SoC thresholds are NOT iterated. User sets these as fixed values.

See `SIZING_MODE_SPECIFICATION.md` for full details.

---

## 3. Input Validation (Pre-Simulation)

```
# ═══════════════════════════════════════════════════════════════════
# VALIDATION: Run before simulation starts
# ═══════════════════════════════════════════════════════════════════

# Threshold ordering validation (CRITICAL)
IF dg_soc_on_threshold >= dg_soc_off_threshold:
    ERROR "DG ON threshold must be strictly less than OFF threshold to prevent short-cycling"
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

# Validate threshold ordering: min_soc ≤ emergency < dg_on < dg_off ≤ max_soc
IF emergency_soc_threshold >= dg_soc_on_threshold:
    WARNING "Emergency threshold is above DG ON threshold - emergency may never trigger"
END IF

# DG running mode validation (Template 2 only supports Full Capacity)
IF dg_running_mode != "Full Capacity":
    WARNING "Template 2 only supports Full Capacity mode. Ignoring dg_running_mode setting."
    dg_running_mode = "Full Capacity"
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
# DG SoC Thresholds (All in MWh)
# ═══════════════════════════════════════════════════════════════════
dg_soc_on_mwh = bess_capacity × dg_soc_on_threshold / 100
dg_soc_off_mwh = bess_capacity × dg_soc_off_threshold / 100
emergency_soc_mwh = bess_capacity × emergency_soc_threshold / 100

# Dynamic night window (if mode = Dynamic)
IF night_window_mode == "Dynamic":
    daylight_hours = set()
    FOR t = 1 TO 8760:
        hour_of_day = (t - 1) MOD 24
        IF solar_profile[t] > 0.01:  # Epsilon filter
            daylight_hours.add(hour_of_day)
    END FOR
    
    dynamic_day_start = min(daylight_hours)
    dynamic_day_end = max(daylight_hours) + 1
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
| `hours_day_green` | Day hours without DG | hours |
| `is_dominated` | True if strictly dominated | Boolean |

---

## 8. Dispatch Logic

[Core dispatch logic unchanged from v1.2 - refer to original document]

The dispatch logic steps (0-10) remain identical. Only the initialization of power limits changes based on Sizing Mode vs Fixed Mode as specified in Section 4.

---

## 9. Summary Metrics

[Unchanged from v1.2 - refer to original document]

---

## 10. Edge Cases

[Unchanged from v1.2 - refer to original document]

---

## 11. Assumptions and Simplifications

| Assumption | Description |
| ------------ | ------------- |
| **Hourly resolution** | Δt = 1 hour; MW values represent MWh |
| **No simultaneous charge/discharge** | BESS either charges OR discharges in any hour |
| **365-day year** | 8760 hours; leap years not handled |
| **No DG fuel/emissions** | Fuel consumption not tracked |
| **No DG min runtime** | DG can cycle on/off hourly (V2) |
| **Full capacity only** | DG outputs 100% when ON |
| **Simplified green metric** | All BESS discharge treated as green |
| **Year 1 sizing** | No degradation buffer |
| **Sizing Mode symmetric power** | Charge power = Discharge power |

---

## 12. Developer Acceptance Checklist

Before marking implementation complete, verify:

**Sizing Mode:**

- [ ] Sizing Mode correctly derives power from capacity and duration
- [ ] All 7 duration classes tested for each capacity × DG combination
- [ ] Output comparison table includes all required columns

**Core Logic:**

- [ ] Night vs day classification (fixed/dynamic) working as specified
- [ ] Pre-simulation validation catches invalid threshold ordering
- [ ] DG ON/OFF follows SoC deadband hysteresis
- [ ] DG runs at night when `bess_disabled_today = True` and load present
- [ ] BESS cannot charge and discharge in same hour
- [ ] SoC clamping applied after all operations each hour
- [ ] Daily cycles calculated as discharge-to-load / usable_capacity
- [ ] Division-by-zero guards on all percentage calculations

---

**Document Status: APPROVED FOR IMPLEMENTATION**
