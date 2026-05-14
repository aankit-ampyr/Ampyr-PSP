# Template 0: Solar + BESS Only - Dispatch Logic Specification

**Status:** FINALIZED (SME Validated)  
**Version:** 1.1  
**Topology:** A (Solar + BESS, No Grid, No DG)  
**Last Updated:** 2025-12-01

---

## 1. Overview

### 1.1 Description

Pure green off-grid system. Load is served only by solar generation and battery storage. Any unmet demand is recorded as unserved energy.

### 1.2 Merit Order

1. Solar direct to load
2. BESS discharge to load
3. Unserved energy

### 1.3 Charging Sources

- BESS charges from excess solar only
- No grid or DG charging available

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

### 2.3 Sizing Mode Behavior (NEW)

In **Sizing Mode**, the simulation engine iterates through multiple configurations:

**User Inputs (Sizing Mode):**

- `bess_capacity_min`, `bess_capacity_max`, `bess_capacity_step` (MWh range)

**System-Generated:**
For each capacity value, the system automatically tests 7 duration classes:

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

**Assumption:** Charge power = Discharge power (symmetric) in Sizing Mode.

**Why Duration Matters:**

- Same capacity with different power ratings produces different results
- Lower power (longer duration) = may curtail solar (can't absorb spikes fast enough)
- Higher power (shorter duration) = better load following but more expensive
- Simulation shows all options; user decides based on project economics

---

## 3. Derived Constants (Calculated Once at Initialization)

```
# ═══════════════════════════════════════════════════════════════════
# INITIALIZATION (Run once per simulation configuration)
# ═══════════════════════════════════════════════════════════════════

# Capacity limits (MWh)
usable_capacity = bess_capacity × (bess_max_soc - bess_min_soc) / 100
min_soc_mwh = bess_capacity × bess_min_soc / 100
max_soc_mwh = bess_capacity × bess_max_soc / 100

# Power limits (MW)
# In Fixed Mode: constrained by both rating and C-rate
# In Sizing Mode: power comes directly from duration class
IF sizing_mode:
    charge_power_limit = bess_charge_power      # Already set by duration
    discharge_power_limit = bess_discharge_power
ELSE:
    charge_power_limit = min(bess_charge_power, bess_capacity × bess_charge_c_rate)
    discharge_power_limit = min(bess_discharge_power, bess_capacity × bess_discharge_c_rate)
END IF

# Efficiency factors (sqrt split of round-trip efficiency)
charge_efficiency = sqrt(bess_efficiency / 100)
discharge_efficiency = sqrt(bess_efficiency / 100)

# Initial state
soc = bess_capacity × bess_initial_soc / 100
```

---

## 4. State Variables

| Variable | Description | Initial Value | Resets |
| ---------- | ------------- | --------------- | -------- |
| `soc` | Current state of charge (MWh) | `bess_capacity × initial_soc / 100` | Never |
| `daily_discharge` | Energy discharged today (MWh) | 0 | Daily |
| `daily_cycles` | Cycles consumed today | 0 | Daily |
| `bess_disabled_today` | BESS disabled flag (enforce mode) | False | Daily |
| `current_day` | Day counter (1-365) | 1 | Never |

---

## 5. Hourly Output Variables

| Variable | Description | Unit |
| ---------- | ------------- | ------ |
| `solar_to_load` | Solar energy serving load directly | MWh |
| `solar_to_bess` | Solar energy charging BESS | MWh |
| `solar_curtailed` | Excess solar wasted | MWh |
| `bess_to_load` | BESS energy serving load | MWh |
| `unserved` | Load not served | MWh |
| `soc` | End-of-hour state of charge | MWh |
| `daily_cycles` | Cumulative cycles for the day | cycles |

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
    unserved = 0
    
    remaining_load = load

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
        
        # Calculate maximum possible charge
        charge_room = max_soc_mwh - soc
        max_charge = min(
            excess_solar,                      # Available solar
            charge_power_limit,                # Power rating limit
            charge_room / charge_efficiency    # Capacity limit (accounting for losses)
        )
        
        # Apply charge
        solar_to_bess = max_charge
        soc = soc + (solar_to_bess × charge_efficiency)
        
        # Remaining solar is curtailed
        solar_curtailed = excess_solar - solar_to_bess
        
    ELSE:
        solar_curtailed = excess_solar
    END IF

    # ───────────────────────────────────────────────────────────────
    # STEP 4: DISCHARGE BESS TO SERVE REMAINING LOAD
    # ───────────────────────────────────────────────────────────────
    IF remaining_load > 0 AND NOT bess_disabled_today:
        
        # Calculate maximum possible discharge
        discharge_available = soc - min_soc_mwh
        max_discharge = min(
            remaining_load,                           # What's needed
            discharge_power_limit,                    # Power rating limit
            discharge_available × discharge_efficiency # Available energy (accounting for losses)
        )
        
        # Apply discharge
        bess_to_load = max_discharge
        soc = soc - (bess_to_load / discharge_efficiency)
        remaining_load = remaining_load - bess_to_load
        
        # Update cycle tracking (discharge throughput only)
        daily_discharge = daily_discharge + bess_to_load
        daily_cycles = daily_discharge / usable_capacity
        
        # Check cycle limit (enforce mode only)
        IF bess_enforce_cycle_limit AND bess_daily_cycle_limit IS NOT None:
            IF daily_cycles >= bess_daily_cycle_limit:
                bess_disabled_today = True
            END IF
        END IF
        
    END IF

    # ───────────────────────────────────────────────────────────────
    # STEP 5: CALCULATE UNSERVED ENERGY
    # ───────────────────────────────────────────────────────────────
    unserved = remaining_load

    # ───────────────────────────────────────────────────────────────
    # STEP 6: SOC CLAMPING (Numerical Stability)
    # ───────────────────────────────────────────────────────────────
    soc = max(min_soc_mwh, min(soc, max_soc_mwh))

    # ───────────────────────────────────────────────────────────────
    # STEP 7: RECORD HOURLY RESULTS
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
total_unserved = sum(results[t].unserved for t in 1..8760)

# Delivery metrics
hours_full_delivery = count(results[t] where unserved == 0)
hours_with_unserved = count(results[t] where unserved > 0)

# Percentages (with division-by-zero guards)
pct_full_delivery = hours_full_delivery / 8760 × 100
pct_load_served = IF total_load > 0 THEN ((total_load - total_unserved) / total_load × 100) ELSE 100
pct_solar_curtailed = IF total_solar_generation > 0 THEN (total_solar_curtailed / total_solar_generation × 100) ELSE 0

# BESS metrics
total_bess_cycles = sum(max daily_cycles for each day)
avg_daily_cycles = total_bess_cycles / 365
days_exceeding_cycle_limit = count(days where max_daily_cycles > bess_daily_cycle_limit)

# BESS utilization
bess_throughput = total_bess_to_load  # Total energy discharged
bess_equivalent_cycles = IF usable_capacity > 0 THEN (bess_throughput / usable_capacity) ELSE 0
```

---

## 8. Sizing Mode Output (NEW)

When run in Sizing Mode, the simulation produces a **comparison table** with one row per configuration:

| Column | Description | Unit |
| -------- | ------------- | ------ |
| `capacity` | BESS energy capacity | MWh |
| `duration` | Duration class tested | hours |
| `power` | Calculated charge/discharge power | MW |
| `delivery_pct` | Percentage of hours with 100% delivery | % |
| `delivery_hours` | Count of hours with 100% delivery | hours |
| `unserved_mwh` | Total unserved energy | MWh |
| `unserved_pct` | Unserved as % of total load | % |
| `curtailed_mwh` | Total solar curtailed | MWh |
| `curtailed_pct` | Curtailment as % of solar generation | % |
| `bess_cycles` | Annual equivalent cycles | cycles |
| `max_daily_cycles` | Peak daily cycle count | cycles |
| `is_dominated` | True if another config is strictly better | Boolean |

**Example Output:**

| Capacity | Duration | Power | Delivery % | Curtailed % | Cycles |
| ---------- | ---------- | ------- | ------------ | ------------- | -------- |
| 50 MWh | 1-hr | 50 MW | 92.1% | 1.2% | 312 |
| 50 MWh | 2-hr | 25 MW | 89.4% | 4.8% | 298 |
| 50 MWh | 4-hr | 12.5 MW | 82.3% | 12.6% | 245 |
| 100 MWh | 1-hr | 100 MW | 97.8% | 0.4% | 198 |
| 100 MWh | 2-hr | 50 MW | 96.2% | 1.1% | 187 |
| 100 MWh | 4-hr | 25 MW | 93.1% | 3.4% | 156 |

**Interpretation:**

- Same 50 MWh capacity with 1-hr duration (50 MW power) delivers 92.1% with only 1.2% curtailment
- Same 50 MWh with 4-hr duration (12.5 MW power) delivers only 82.3% with 12.6% curtailment
- The 4-hr system can't absorb solar spikes fast enough → more curtailment
- The 4-hr system can't serve load spikes → lower delivery %

---

## 9. Validation Test Case

### 9.1 Test Parameters

| Parameter | Value |
| ----------- | ------- |
| Load | 10 MW constant (all hours) |
| Solar | 15 MW (hours 8-17), 0 MW (other hours) |
| BESS Capacity | 20 MWh |
| BESS Power | 10 MW (charge and discharge) |
| Efficiency | 85% (charge_eff = discharge_eff = 0.922) |
| Min SoC | 10% (2 MWh) |
| Max SoC | 90% (18 MWh) |
| Initial SoC | 50% (10 MWh) |
| Usable Capacity | 16 MWh |
| Cycle Limit | Not enforced |

### 9.2 Expected Results for Hours 1-3

**Hour 1 (Night, Solar = 0)**

| Variable | Expected Value | Calculation |
| ---------- | ---------------- | ------------- |
| solar_to_load | 0 | min(0, 10) |
| remaining_load | 10 | 10 - 0 |
| discharge_available | 8 | 10 - 2 |
| max_discharge | 7.38 | min(10, 10, 8 × 0.922) |
| bess_to_load | 7.38 | |
| soc_withdrawn | 8.0 | 7.38 / 0.922 |
| new_soc | 2.0 | 10 - 8 |
| unserved | 2.62 | 10 - 7.38 |

**Hour 2 (Night, Solar = 0, SoC = 2 MWh at minimum)**

| Variable | Expected Value | Calculation |
| ---------- | ---------------- | ------------- |
| solar_to_load | 0 | |
| discharge_available | 0 | 2 - 2 |
| bess_to_load | 0 | No energy available |
| unserved | 10 | Full load unserved |

**Hour 8 (Day starts, Solar = 15)**

| Variable | Expected Value | Calculation |
| ---------- | ---------------- | ------------- |
| solar_to_load | 10 | min(15, 10) |
| remaining_load | 0 | 10 - 10 |
| excess_solar | 5 | 15 - 10 |
| charge_room | 16 | 18 - 2 |
| max_charge | 5 | min(5, 10, 16/0.922) |
| solar_to_bess | 5 | |
| energy_stored | 4.61 | 5 × 0.922 |
| new_soc | 6.61 | 2 + 4.61 |
| unserved | 0 | |

---

## 10. Edge Cases

| Scenario | Expected Behavior |
| ---------- | ------------------- |
| Solar = 0, BESS at min SoC | Full load is unserved |
| Solar > Load, BESS at max SoC | Excess solar curtailed |
| Solar = Load exactly | No BESS action, no curtailment |
| BESS power limit < remaining load | Partial discharge, some unserved |
| BESS power limit < excess solar | Partial charge, some curtailed |
| Cycle limit reached (enforce mode) | BESS disabled for rest of day |
| Cycle limit reached (count mode) | Warning logged, BESS continues |

---

## 11. Implementation Notes

1. **Time Step:** MW values represent MWh for each hour (Δt = 1 hour)
2. **Efficiency:** Applied as sqrt(RTE) to both charge and discharge
3. **Cycle Counting:** Discharge throughput only, resets daily
4. **SoC Bounds:** Hard limits - never below min or above max
5. **Within-Hour Behavior:** Either charge OR discharge, not both
6. **Sizing Mode:** Power derived from capacity ÷ duration; C-rate not used

---

## 12. Limitations (MVP)

- Sizes for Year 1 only (no degradation)
- Hourly resolution only (no sub-hourly dynamics)
- No inverter clipping or AC limits
- No auxiliary consumption
- No charge + discharge in same hour

---

## 13. Developer Acceptance Checklist

Before marking implementation complete, verify:

- [ ] Sizing Mode correctly derives power from capacity and duration
- [ ] All 7 duration classes tested for each capacity value
- [ ] SoC clamping applied after all operations each hour
- [ ] Daily cycles calculated as discharge-to-load / usable_capacity
- [ ] Division-by-zero guards on all percentage calculations
- [ ] Cycle limit enforcement fully disables BESS (charge + discharge)
- [ ] Output comparison table generated with all required columns

---

**Document Status: APPROVED FOR IMPLEMENTATION**
