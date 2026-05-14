# Template 3: DG Blackout Window - Dispatch Logic Specification

**Status:** FINALIZED (SME Reviewed)  
**Version:** 1.2  
**Topology:** C (Solar + BESS + DG, No Grid)  
**Last Updated:** 2025-12-01

---

## 1. Overview

### 1.1 Description

Time-restricted DG operation. DG is completely disabled during a user-defined blackout window (e.g., business hours for noise/emissions restrictions). Outside the blackout window, system operates like Template 1 (Green Priority) with DG as reactive backup.

### 1.2 Use Case

- Sites with noise restrictions during business hours
- Sites with emissions limits during certain periods
- Industrial sites requiring green-only operation during inspections/audits
- Residential proximity requiring quiet hours

### 1.3 Merit Order

**During Blackout Window:**

1. Solar direct to load
2. BESS discharge to load
3. Unserved energy (DG strictly disabled)

**Outside Blackout Window:**

1. Solar direct to load
2. BESS discharge to load
3. DG to load (reactive - only when Solar + BESS insufficient)
4. Unserved energy

### 1.4 Key Characteristics

- Single blackout window (fixed hours)
- Strict blackout enforcement (no emergency override)
- Outside blackout: identical to Template 1 (Green Priority)
- DG is reactive, not proactive
- BESS cannot charge and discharge in the same hour

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
| `dg_charges_bess` | Can DG charge BESS? | Boolean | False |

**Note:** DG runs at Full Capacity when ON. Load-Following mode not supported in Template 3.

### 2.4 Blackout Window Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `blackout_start_hour` | Blackout begins | Hour (0-23) | 6 |
| `blackout_end_hour` | Blackout ends | Hour (0-23) | 18 |

**Blackout Window Behavior:**

- DG is completely disabled during blackout hours
- No emergency override available (strict enforcement)
- If BESS depleted during blackout → Unserved energy
- If `start == end` → No blackout (0 hours)

### 2.5 Sizing Mode Behavior (NEW)

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

**Note:** Blackout window parameters (`blackout_start_hour`, `blackout_end_hour`) are NOT iterated.

See `SIZING_MODE_SPECIFICATION.md` for full details.

---

## 3. Input Validation (Pre-Simulation)

```
# ═══════════════════════════════════════════════════════════════════
# VALIDATION: Run before simulation starts
# ═══════════════════════════════════════════════════════════════════

# Hour range validation
IF blackout_start_hour < 0 OR blackout_start_hour > 23:
    ERROR "blackout_start_hour must be integer 0-23"
END IF

IF blackout_end_hour < 0 OR blackout_end_hour > 23:
    ERROR "blackout_end_hour must be integer 0-23"
END IF

# Informational warning for edge cases
IF blackout_start_hour == blackout_end_hour:
    WARNING "blackout_start_hour equals blackout_end_hour - no blackout window will be applied"
END IF

# Calculate blackout duration for UI feedback
IF blackout_start_hour < blackout_end_hour:
    blackout_duration = blackout_end_hour - blackout_start_hour
ELSE IF blackout_start_hour > blackout_end_hour:
    blackout_duration = (24 - blackout_start_hour) + blackout_end_hour
ELSE:
    blackout_duration = 0
END IF

IF blackout_duration > 12:
    WARNING "Long blackout window (>12 hours) without proactive pre-charging may result in high unserved energy. Consider increasing battery size."
END IF

# DG running mode validation
IF dg_running_mode != "Full Capacity":
    WARNING "Template 3 only supports Full Capacity mode."
    dg_running_mode = "Full Capacity"
END IF

# Cycle limit enforcement warning
IF bess_enforce_cycle_limit == True:
    WARNING "Enabling cycle limit enforcement may cause unserved energy during blackout window when BESS is disabled but DG is not allowed."
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
# Initial state
# ═══════════════════════════════════════════════════════════════════
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
| `is_blackout` | Whether hour is in blackout window | Boolean |
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
| `blackout_delivery_pct` | Delivery % during blackout hours only | % |
| `unserved_mwh` | Total unserved energy | MWh |
| `curtailed_pct` | Solar curtailment % | % |
| `dg_runtime_hrs` | Total DG running hours | hours |
| `dg_starts` | Number of DG start events | count |
| `bess_cycles` | Annual equivalent cycles | cycles |
| `is_dominated` | True if strictly dominated | Boolean |

**Critical Metric:** `blackout_delivery_pct` is essential for this template since unserved energy during blackout cannot be recovered by DG.

---

## 8. Dispatch Logic

[Core dispatch logic unchanged from v1.1 - refer to original document]

The dispatch logic steps remain identical. Only the initialization of power limits changes based on Sizing Mode vs Fixed Mode as specified in Section 4.

---

## 9. Edge Cases

| Scenario | Expected Behavior |
| ---------- | ------------------- |
| Blackout window, BESS depleted, load present | Unserved energy (DG strictly disabled) |
| Blackout window, solar sufficient | Full delivery, no DG needed |
| Outside blackout, BESS + Solar insufficient | DG activates (reactive) |
| Outside blackout, BESS + Solar sufficient | DG stays OFF |
| Blackout spans midnight (e.g., 22:00-06:00) | Handled correctly by hour check |
| `start == end` | No blackout (0 hours), behaves like Template 1 |
| BESS disabled (cycle limit) during blackout | Unserved energy if solar insufficient |
| BESS disabled (cycle limit) outside blackout | DG takes over |
| BESS discharged this hour, DG has excess | DG excess curtailed (not stored) |

---

## 10. Assumptions and Simplifications

| Assumption | Description |
| ------------ | ------------- |
| **Hourly resolution** | Δt = 1 hour; MW values represent MWh |
| **365-day year** | 8760 hours; leap years not handled |
| **Single blackout window** | Multiple windows deferred to V2 |
| **Strict blackout** | No emergency override during blackout |
| **No simultaneous charge/discharge** | BESS either charges OR discharges |
| **No DG fuel/emissions** | Fuel consumption not tracked |
| **Full capacity only** | DG load-following deferred to V2 |
| **Simplified green metric** | All BESS discharge treated as green |
| **Year 1 sizing** | No degradation buffer |
| **Sizing Mode symmetric power** | Charge power = Discharge power |

---

## 11. Developer Acceptance Checklist

Before marking implementation complete, verify:

**Sizing Mode:**

- [ ] Sizing Mode correctly derives power from capacity and duration
- [ ] All 7 duration classes tested for each capacity × DG combination
- [ ] Output comparison table includes `blackout_delivery_pct`

**Core Logic:**

- [ ] Blackout-hour detection handles `start < end`, `start > end`, and `start == end`
- [ ] `start == end` results in zero blackout hours (no blackout)
- [ ] DG is never allowed to run during blackout hours
- [ ] Outside blackout, DG behavior matches Template 1 (reactive)
- [ ] BESS never charges and discharges in same hour
- [ ] SoC clamping applied after all operations each hour
- [ ] Division-by-zero guards on all percentage calculations

---

**Document Status: APPROVED FOR IMPLEMENTATION**
