# Template 4: DG Emergency Only - Dispatch Logic Specification

**Status:** FINALIZED (SME Reviewed)  
**Version:** 1.2  
**Topology:** C (Solar + BESS + DG, No Grid)  
**Last Updated:** 2025-12-01

---

## 1. Overview

### 1.1 Description

SoC-triggered DG backup with no time restrictions. DG acts as a **"Range Extender"** or **"Recovery"** asset. DG is off by default and only activates when BESS SoC drops below a configurable threshold. Once triggered, DG takes priority for serving load to allow BESS recovery, but BESS will **assist** if DG capacity is insufficient ("Assist Mode"). DG runs until SoC recovers to upper threshold. This template minimizes DG runtime while providing reliable backup.

### 1.2 Use Case

- Sites where DG should be true last resort (minimize runtime/fuel)
- Sites with no time-based operational constraints
- Cost-conscious operations (run DG only when absolutely necessary)
- Sites prioritizing green energy but needing reliability guarantee
- Sites with undersized DG that needs BESS assist capability

### 1.3 Key Difference from Template 1

| Aspect | Template 1 (Green Priority) | Template 4 (DG Emergency Only) |
| -------- | ---------------------------- | ------------------------------- |
| DG trigger | Load deficit (BESS at min SoC) | SoC threshold (configurable) |
| DG off trigger | Load met (immediate) | SoC threshold (configurable) |
| Deadband | No (can cycle rapidly) | Yes (prevents short cycling) |
| DG activation point | Only when BESS cannot serve | Before BESS hits minimum |
| DG priority when ON | No - BESS first | Yes - DG first, BESS assists |

### 1.4 Merit Order

**When DG is OFF (normal green operation):**

1. Solar direct to load
2. BESS discharge to load
3. Unserved energy (if BESS depleted)

**When DG is ON (triggered by SoC threshold):**

1. Solar direct to load
2. DG to remaining load (DG takes priority)
3. **IF DG < remaining load:** BESS assists (covers deficit only) — "Assist Mode"
4. **IF DG ≥ remaining load:** BESS rests, excess (solar + DG) charges BESS
5. Unserved energy (only if Solar + DG + BESS all insufficient)

### 1.5 Cycle Limit Policy

**Template 4 does NOT support cycle limit enforcement.**

- `bess_enforce_cycle_limit` is forced to `False` at initialization
- Cycles are tracked and reported (monitor-only mode)
- Days exceeding nominal limit are flagged in metrics
- Rationale: Enforcing cycle limits could cause unserved energy contradicting reliability goal

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

**Note:** `bess_enforce_cycle_limit` is forced to `False` for Template 4. See Section 1.5.

### 2.3 DG Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `dg_capacity` | Rated power output | MW | Required |
| `dg_charges_bess` | Can DG charge BESS? | Boolean | True |

### 2.4 DG SoC Trigger Parameters

| Parameter | Description | Unit | Default |
| ----------- | ------------- | ------ | --------- |
| `dg_soc_on_threshold` | SoC at/below which DG turns ON | % | 30 |
| `dg_soc_off_threshold` | SoC at/above which DG turns OFF | % | 80 |

**Deadband Behavior:**

- DG turns ON when SoC drops to or below `dg_soc_on_threshold`
- DG turns OFF when SoC rises to or above `dg_soc_off_threshold`
- Between thresholds: DG maintains previous state (hysteresis)

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

**Note:** SoC threshold parameters (`dg_soc_on_threshold`, `dg_soc_off_threshold`) are NOT iterated.

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

# ═══════════════════════════════════════════════════════════════════
# WARNINGS (Log and Continue)
# ═══════════════════════════════════════════════════════════════════

# Cycle limit enforcement override
IF bess_enforce_cycle_limit == True:
    WARNING "Template 4 does not support cycle limit enforcement. Setting to False."
    bess_enforce_cycle_limit = False
END IF

# DG running mode validation
IF dg_running_mode != "Full Capacity":
    WARNING "Template 4 only supports Full Capacity mode."
    dg_running_mode = "Full Capacity"
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
| `bess_assisted` | BESS assisted DG this hour | Boolean |
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
| `hours_dg_assist` | Hours where BESS assisted DG | hours |
| `is_dominated` | True if strictly dominated | Boolean |

**Template-Specific Column:** `hours_dg_assist` tracks when BESS had to help undersized DG.

---

## 8. Dispatch Logic

[Core dispatch logic unchanged from v1.1 - refer to original document]

The dispatch logic steps remain identical. Only the initialization of power limits changes based on Sizing Mode vs Fixed Mode as specified in Section 4.

---

## 9. Edge Cases

| Scenario | Expected Behavior |
| ---------- | ------------------- |
| SoC starts above OFF threshold | DG stays OFF, BESS serves load |
| SoC drops to exactly ON threshold | DG turns ON |
| SoC rises to exactly OFF threshold | DG turns OFF |
| SoC between thresholds, DG was OFF | DG stays OFF |
| SoC between thresholds, DG was ON | DG stays ON (deadband) |
| **DG ON, DG < Load** | **BESS assists, no charging** |
| **DG ON, DG ≥ Load** | **BESS rests, excess charges BESS** |
| DG ON, Load = 0 | DG runs (SoC recovery), charges BESS |
| DG capacity < load, BESS at min SoC | Unserved energy (unavoidable) |
| Threshold ON = Threshold OFF | **ERROR** (rejected at validation) |
| dg_charges_bess = False | DG serves load only, solar still charges |

---

## 10. Assumptions and Simplifications

| Assumption | Description |
| ------------ | ------------- |
| **Hourly resolution** | Δt = 1 hour; MW values represent MWh |
| **365-day year** | 8760 hours; leap years not handled |
| **No DG fuel/emissions** | Fuel consumption not tracked |
| **No DG min runtime** | DG can cycle based on SoC (V2) |
| **Full capacity only** | DG outputs 100% when ON |
| **DG priority when ON** | DG serves first, BESS assists if needed |
| **Simplified green metric** | All BESS discharge treated as green |
| **Year 1 sizing** | No degradation buffer |
| **Deadband hysteresis** | Prevents rapid cycling |
| **No cycle enforcement** | Monitor-only for reliability |
| **Sizing Mode symmetric power** | Charge power = Discharge power |

---

## 11. Developer Acceptance Checklist

Before marking implementation complete, verify:

**Sizing Mode:**

- [ ] Sizing Mode correctly derives power from capacity and duration
- [ ] All 7 duration classes tested for each capacity × DG combination
- [ ] Output comparison table includes `hours_dg_assist`

**Core Logic:**

- [ ] Input validation catches threshold ordering errors
- [ ] `bess_enforce_cycle_limit` is forced to `False`
- [ ] Deadband logic correctly maintains DG state between thresholds
- [ ] **Assist Mode:** When DG ON and DG < Load, BESS assists
- [ ] **Recovery Mode:** When DG ON and DG ≥ Load, BESS rests and charges
- [ ] No charging occurs when BESS assisted
- [ ] Charging allocation prioritizes solar over DG
- [ ] SoC clamping applied after all operations each hour
- [ ] Division-by-zero guards on all percentage calculations

---

**Document Status: APPROVED FOR IMPLEMENTATION**
