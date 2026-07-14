# Template 1: Green Priority - Dispatch Logic Specification

**Status:** FINALIZED (SME Reviewed)  
**Version:** 1.3  
**Topology:** C (Solar + BESS + DG, No Grid)  
**Last Updated:** 2025-12-01

---

## 1. Overview

### 1.1 Description

Green-first system with DG backup. Load is served primarily by solar and battery. DG activates only when solar + BESS cannot meet demand. DG is the last resort.

### 1.2 Merit Order

1. Solar direct to load
2. BESS discharge to load
3. DG to load (only if BESS insufficient)
4. Unserved energy (only if all sources exhausted)

### 1.3 Charging Sources

- BESS charges from excess solar (always)
- BESS charges from excess DG (if `dg_charges_bess = Yes`)
- DG charging is reactive only (DG does not turn ON proactively to charge BESS)

### 1.4 Key Characteristics

- No time-based restrictions on DG
- No SoC threshold triggers for DG
- DG runs at Full Capacity when ON
- Simplest DG integration template
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

**Note:** DG runs at Full Capacity when ON. Load-Following mode deferred to V2.

### 2.4 Sizing Mode Behavior (NEW)

In **Sizing Mode**, the simulation engine iterates through multiple configurations:

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

**Simulation Matrix:**

```
total_simulations = capacity_steps × 7_duration_classes × dg_steps
```

---

## 3. Derived Constants (Calculated Once at Initialization)

```
# ═══════════════════════════════════════════════════════════════════
# INITIALIZATION (Run once per simulation configuration)
# ═══════════════════════════════════════════════════════════════════

# BESS Capacity limits (MWh)
usable_capacity = bess_capacity × (bess_max_soc - bess_min_soc) / 100
min_soc_mwh = bess_capacity × bess_min_soc / 100
max_soc_mwh = bess_capacity × bess_max_soc / 100

# BESS Power limits (MW)
# In Fixed Mode: constrained by both rating and C-rate
# In Sizing Mode: power comes directly from duration class
IF sizing_mode:
    charge_power_limit = bess_charge_power      # Already set by duration
    discharge_power_limit = bess_discharge_power
ELSE:
    charge_power_limit = min(bess_charge_power, bess_capacity × bess_charge_c_rate)
    discharge_power_limit = min(bess_discharge_power, bess_capacity × bess_discharge_c_rate)
END IF

# Efficiency factors
charge_efficiency = sqrt(bess_efficiency / 100)
discharge_efficiency = sqrt(bess_efficiency / 100)

# Initial state
soc = bess_capacity × bess_initial_soc / 100
```

---

## 4. State Variables

| Variable | Description | Initial Value | Resets |
| ---------- | ------------- | --------------- | -------- |
| `soc` | Current BESS state of charge (MWh) | `bess_capacity × initial_soc / 100` | Never |
| `daily_discharge` | BESS energy discharged today (MWh) | 0 | Daily |
| `daily_cycles` | BESS cycles consumed today | 0 | Daily |
| `bess_disabled_today` | BESS disabled flag (enforce mode) | False | Daily |
| `current_day` | Day counter (1-365) | 1 | Never |
| `dg_was_running` | DG state in previous hour | False | Never |
| `bess_discharged_this_hour` | BESS discharged flag | False | Hourly |

**Per-Day Tracking Arrays (for Summary Metrics):**

| Variable | Description | Size |
| ---------- | ------------- | ------ |
| `max_daily_cycles_per_day[]` | Peak cycles reached each day | 365 |

---

## 5. Hourly Output Variables

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

## 6. Dispatch Logic (Pseudocode)

```
# ═══════════════════════════════════════════════════════════════════
# MAIN SIMULATION LOOP
# ═══════════════════════════════════════════════════════════════════

FOR t = 1 TO 8760:

    # ───────────────────────────────────────────────────────────────
    # STEP 0: DAILY RESET CHECK
    # ───────────────────────────────────────────────────────────────
    day_of_year = floor((t - 1) / 24) + 1
    
    IF day_of_year > current_day:
        # Save previous day's max cycles before reset
        max_daily_cycles_per_day[current_day] = daily_cycles
        
        # Reset for new day
        current_day = day_of_year
        daily_discharge = 0
        daily_cycles = 0
        bess_disabled_today = False
    END IF

    # ───────────────────────────────────────────────────────────────
    # STEP 1: INITIALIZE HOURLY VARIABLES
    # ───────────────────────────────────────────────────────────────
    load = load_profile[t]
    solar = solar_profile[t]
    
    solar_to_load = 0
    solar_to_bess = 0
    solar_curtailed = 0
    bess_to_load = 0
    dg_to_load = 0
    dg_to_bess = 0
    dg_curtailed = 0
    dg_running = False
    unserved = 0
    
    remaining_load = load
    bess_discharged_this_hour = False
    charge_power_used = 0

    # ───────────────────────────────────────────────────────────────
    # STEP 2: SOLAR DIRECT TO LOAD
    # ───────────────────────────────────────────────────────────────
    solar_to_load = min(solar, remaining_load)
    remaining_load = remaining_load - solar_to_load
    excess_solar = solar - solar_to_load

    # ───────────────────────────────────────────────────────────────
    # STEP 3: CHARGE BESS WITH EXCESS SOLAR
    # ───────────────────────────────────────────────────────────────
    IF excess_solar > 0 AND NOT bess_disabled_today:
        charge_room = max_soc_mwh - soc
        charge_power_available = charge_power_limit - charge_power_used
        
        max_charge = min(
            excess_solar,
            charge_power_available,
            charge_room / charge_efficiency
        )
        
        solar_to_bess = max_charge
        soc = soc + (solar_to_bess × charge_efficiency)
        charge_power_used = charge_power_used + solar_to_bess
        
        solar_curtailed = excess_solar - solar_to_bess
    ELSE:
        solar_curtailed = excess_solar
    END IF

    # ───────────────────────────────────────────────────────────────
    # STEP 4: DISCHARGE BESS TO SERVE REMAINING LOAD
    # ───────────────────────────────────────────────────────────────
    IF remaining_load > 0 AND NOT bess_disabled_today:
        discharge_available = soc - min_soc_mwh
        max_discharge = min(
            remaining_load,
            discharge_power_limit,
            discharge_available × discharge_efficiency
        )
        
        IF max_discharge > 0:
            bess_to_load = max_discharge
            soc = soc - (bess_to_load / discharge_efficiency)
            remaining_load = remaining_load - bess_to_load
            bess_discharged_this_hour = True
            
            # Update cycle tracking
            daily_discharge = daily_discharge + bess_to_load
            daily_cycles = daily_discharge / usable_capacity
            
            # Check cycle limit
            IF bess_enforce_cycle_limit AND bess_daily_cycle_limit IS NOT None:
                IF daily_cycles >= bess_daily_cycle_limit:
                    bess_disabled_today = True
                END IF
            END IF
        END IF
    END IF

    # ───────────────────────────────────────────────────────────────
    # STEP 5: DG ACTIVATION (if load still remaining)
    # ───────────────────────────────────────────────────────────────
    IF remaining_load > 0:
        dg_running = True
        dg_output = dg_capacity  # Full capacity
        
        # Count DG start
        IF NOT dg_was_running:
            total_dg_starts = total_dg_starts + 1
        END IF
        
        # DG serves remaining load
        dg_to_load = min(dg_output, remaining_load)
        remaining_load = remaining_load - dg_to_load
        dg_excess = dg_output - dg_to_load
        
        # DG charges BESS with excess (if enabled and BESS didn't discharge)
        IF dg_charges_bess AND dg_excess > 0 AND NOT bess_discharged_this_hour AND NOT bess_disabled_today:
            charge_room = max_soc_mwh - soc
            charge_power_available = charge_power_limit - charge_power_used
            
            max_dg_charge = min(
                dg_excess,
                charge_power_available,
                charge_room / charge_efficiency
            )
            
            dg_to_bess = max_dg_charge
            soc = soc + (dg_to_bess × charge_efficiency)
            dg_curtailed = dg_excess - dg_to_bess
        ELSE:
            dg_curtailed = dg_excess
        END IF
        
        total_dg_runtime_hours = total_dg_runtime_hours + 1
    END IF
    
    dg_was_running = dg_running

    # ───────────────────────────────────────────────────────────────
    # STEP 6: CALCULATE UNSERVED ENERGY
    # ───────────────────────────────────────────────────────────────
    unserved = remaining_load

    # ───────────────────────────────────────────────────────────────
    # STEP 7: SOC CLAMPING (Numerical Stability)
    # ───────────────────────────────────────────────────────────────
    soc = max(min_soc_mwh, min(soc, max_soc_mwh))

    # ───────────────────────────────────────────────────────────────
    # STEP 8: RECORD HOURLY RESULTS
    # ───────────────────────────────────────────────────────────────
    results[t] = {
        hour: t,
        day: current_day,
        load: load,
        solar: solar,
        solar_to_load: solar_to_load,
        solar_to_bess: solar_to_bess,
        solar_curtailed: solar_curtailed,
        bess_to_load: bess_to_load,
        dg_to_load: dg_to_load,
        dg_to_bess: dg_to_bess,
        dg_curtailed: dg_curtailed,
        dg_running: dg_running,
        unserved: unserved,
        soc: soc,
        daily_cycles: daily_cycles,
        bess_disabled: bess_disabled_today
    }

END FOR
```

---

## 7. Summary Metrics (Calculated After Simulation)

```
# Energy totals (MWh)
total_load = sum(results[t].load for t in 1..8760)
total_solar_generation = sum(results[t].solar for t in 1..8760)
total_solar_to_load = sum(results[t].solar_to_load for t in 1..8760)
total_solar_to_bess = sum(results[t].solar_to_bess for t in 1..8760)
total_solar_curtailed = sum(results[t].solar_curtailed for t in 1..8760)
total_bess_to_load = sum(results[t].bess_to_load for t in 1..8760)
total_dg_to_load = sum(results[t].dg_to_load for t in 1..8760)
total_dg_to_bess = sum(results[t].dg_to_bess for t in 1..8760)
total_dg_curtailed = sum(results[t].dg_curtailed for t in 1..8760)
total_unserved = sum(results[t].unserved for t in 1..8760)

# Delivery metrics
hours_full_delivery = count(results[t] where unserved == 0)
hours_green_delivery = count(results[t] where unserved == 0 AND dg_running == False)
hours_with_dg = count(results[t] where dg_running == True)

# Percentages (with division-by-zero guards)
pct_full_delivery = hours_full_delivery / 8760 × 100
pct_green_delivery = hours_green_delivery / 8760 × 100
pct_load_served = IF total_load > 0 THEN ((total_load - total_unserved) / total_load × 100) ELSE 100
pct_solar_curtailed = IF total_solar_generation > 0 THEN (total_solar_curtailed / total_solar_generation × 100) ELSE 0

# DG metrics
total_dg_generation = total_dg_to_load + total_dg_to_bess + total_dg_curtailed
dg_capacity_factor = IF (dg_capacity × 8760) > 0 THEN (total_dg_generation / (dg_capacity × 8760) × 100) ELSE 0

# BESS metrics
bess_throughput = total_bess_to_load
bess_equivalent_cycles = IF usable_capacity > 0 THEN (bess_throughput / usable_capacity) ELSE 0
```

---

## 8. Sizing Mode Output (NEW)

When run in Sizing Mode, the simulation produces a **comparison table**:

| Column | Description | Unit |
| -------- | ------------- | ------ |
| `capacity` | BESS energy capacity | MWh |
| `duration` | Duration class tested | hours |
| `power` | Calculated charge/discharge power | MW |
| `dg_size` | DG capacity | MW |
| `delivery_pct` | Percentage of hours with 100% delivery | % |
| `green_pct` | Percentage of hours with 100% green delivery | % |
| `unserved_mwh` | Total unserved energy | MWh |
| `curtailed_pct` | Solar curtailment as % of generation | % |
| `dg_runtime_hrs` | Total DG running hours | hours |
| `dg_starts` | Number of DG start events | count |
| `bess_cycles` | Annual equivalent cycles | cycles |
| `is_dominated` | True if another config is strictly better | Boolean |

**Example Output:**

| Capacity | Duration | Power | DG | Delivery % | Green % | Curtailed % | DG Hours |
| ---------- | ---------- | ------- | ----- | ------------ | --------- | ------------- | ---------- |
| 100 MWh | 1-hr | 100 MW | 10 MW | 99.8% | 94.2% | 0.5% | 498 |
| 100 MWh | 2-hr | 50 MW | 10 MW | 99.1% | 92.1% | 1.8% | 692 |
| 100 MWh | 4-hr | 25 MW | 10 MW | 96.4% | 87.3% | 5.2% | 1,105 |
| 100 MWh | 4-hr | 25 MW | 20 MW | 99.2% | 87.3% | 5.0% | 1,098 |

**Interpretation:**

- Lower power (4-hr) → more solar curtailed → BESS depletes faster → more DG hours
- Higher DG capacity → better delivery % but doesn't improve green %

---

## 9. Edge Cases

| Scenario | Expected Behavior |
| ---------- | ------------------- |
| Solar = 0, BESS at min SoC | DG activates to serve load |
| Solar + BESS can meet load | DG stays OFF |
| DG on, BESS at max SoC, dg_charges_bess = Yes | DG excess is curtailed |
| DG on, BESS at max SoC, dg_charges_bess = No | DG excess is curtailed |
| DG capacity < remaining load | DG outputs full capacity, rest is unserved |
| BESS disabled (cycle limit), solar insufficient | DG activates |
| Load = 0 | No dispatch needed, excess solar charges BESS |
| DG runs consecutive hours | Only 1 start counted |
| BESS discharged this hour, DG has excess | DG excess curtailed (BESS cannot charge) |
| BESS did NOT discharge, DG has excess | DG can charge BESS (if enabled) |

---

## 10. Key Definitions and Policies

### 10.1 Daily Cycle Definition

```
daily_cycles = total_bess_discharge_to_load_today / usable_capacity
```

- Only **discharge to load** is counted
- Charging (from solar or DG) is NOT counted toward cycles

### 10.2 Cycle Limit Enforcement Policy

- When `bess_enforce_cycle_limit = True` and limit reached: BESS fully disabled
- When `bess_enforce_cycle_limit = False`: Cycles tracked as warning only

### 10.3 "Green" Delivery Definition (Simplified)

- An hour is "green" if: `unserved == 0 AND dg_running == False`
- All BESS discharge is treated as "green" regardless of charge source

### 10.4 No Simultaneous Charge and Discharge

- If BESS discharges to serve load, it cannot be charged (even if DG has excess)
- Tracked via `bess_discharged_this_hour` flag

---

## 11. Assumptions and Simplifications

| Assumption | Description |
| ------------ | ------------- |
| **Hourly resolution** | Δt = 1 hour; MW values represent MWh |
| **365-day year** | 8760 hours; leap years not handled |
| **No simultaneous charge/discharge** | BESS either charges OR discharges |
| **No DG fuel/emissions** | Fuel consumption not tracked |
| **No DG min runtime** | DG can cycle on/off hourly |
| **Sizing Mode symmetric power** | Charge power = Discharge power |

---

## 12. Limitations (MVP)

- DG runs at full capacity only (no load-following mode)
- No minimum runtime constraint for DG
- No start-up time/ramp rate for DG
- No fuel consumption tracking
- Sizes for Year 1 only (no degradation buffer)
- Hourly resolution only

---

## 13. Developer Acceptance Checklist

Before marking implementation complete, verify:

- [ ] Sizing Mode correctly derives power from capacity and duration
- [ ] All 7 duration classes tested for each capacity × DG combination
- [ ] BESS cannot charge and discharge in same hour
- [ ] SoC clamping applied after all operations each hour
- [ ] Daily cycles calculated as discharge-to-load / usable_capacity
- [ ] Division-by-zero guards on all percentage calculations
- [ ] DG starts counted only on OFF→ON transitions
- [ ] DG excess curtailed when BESS discharged this hour
- [ ] Output comparison table includes all required columns

---

**Document Status: APPROVED FOR IMPLEMENTATION**
