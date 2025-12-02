# BESS Power Delivery Scenarios - Technical Reference

**Document Version:** 1.0
**Project Version:** 1.1.1
**Last Updated:** November 24, 2025
**Purpose:** Technical reference for power delivery logic and foundation for system extensions

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Constraints & Parameters](#2-system-constraints--parameters)
3. [Master Decision Tree](#3-master-decision-tree)
4. [Core Delivery Scenarios](#4-core-delivery-scenarios)
5. [Hour-by-Hour Walkthrough Examples](#5-hour-by-hour-walkthrough-examples)
6. [State Machine Documentation](#6-state-machine-documentation)
7. [Mathematical Formulas Reference](#7-mathematical-formulas-reference)
8. [Code Integration Points](#8-code-integration-points)
9. [Extension Framework](#9-extension-framework-adding-third-power-source)
10. [Troubleshooting & Edge Cases](#10-troubleshooting--edge-cases)

---

## 1. Executive Summary

### 1.1 Overview

The BESS (Battery Energy Storage System) Sizing Tool implements a **binary power delivery system** that either delivers the full target power (25 MW) or delivers nothing. This all-or-nothing approach ensures consistent power quality and simplifies grid integration planning.

The system operates with **two power sources**:
- **Primary Source:** Solar PV generation (up to 67 MW capacity)
- **Secondary Source:** Battery Energy Storage System (variable capacity, 10-500 MWh)

**Key Design Principle:** The battery charges ONLY from solar energy (no grid charging), making this a true solar+storage system.

### 1.2 Document Purpose

This document serves as:

1. **Technical Reference:** Complete specification of all power delivery scenarios
2. **Extension Foundation:** Base for adding third power source (grid, wind, etc.)
3. **Business Logic Documentation:** What happens in each scenario (not how it's implemented)
4. **Decision Support:** Understanding trade-offs and constraints

### 1.3 How to Use This Document

- **For Understanding Current System:** Read Sections 2-7
- **For Adding Third Power Source:** Focus on Sections 3, 8, and 9
- **For Troubleshooting:** Reference Section 10
- **For Implementation:** Use Section 8 code references

---

## 2. System Constraints & Parameters

### 2.1 Core Constraints

#### 2.1.1 Binary Delivery Constraint

**Rule:** Deliver exactly 25 MW or deliver nothing (0 MW).

**Rationale:**
- Ensures consistent power quality
- Simplifies grid integration
- Avoids partial delivery penalties
- Clear success/failure criteria

**Mathematical Expression:**
```
Delivery ∈ {0 MW, 25 MW}
Delivery ∉ (0 MW, 25 MW)
```

**Business Logic:**
```
IF (Available Power ≥ 25 MW) AND (Constraints Satisfied) THEN
    Deliver = 25 MW
ELSE
    Deliver = 0 MW
END IF
```

#### 2.1.2 SOC (State of Charge) Limits

**Operational Range:** 5% ≤ SOC ≤ 95%

**Rationale:**
- Protects battery health
- Extends battery lifetime
- Prevents deep discharge damage
- Avoids overcharging risks

**Impact on Delivery:**
```
Usable Energy = (SOC - MIN_SOC) × Capacity
Usable Energy = (SOC - 0.05) × Capacity

Charge Headroom = (MAX_SOC - SOC) × Capacity
Charge Headroom = (0.95 - SOC) × Capacity
```

#### 2.1.3 Cycle Limit Constraint

**Rule:** Maximum 2.0 cycles per day

**Rationale:**
- Manages battery degradation
- Extends asset lifetime
- Controls operational costs
- Ensures predictable performance

**Cycle Counting Method:** State-transition based (see Section 6.2)

**Impact on Delivery:** If daily cycles ≥ 2.0, no further battery discharge allowed that day

#### 2.1.4 Efficiency Model

**Round-Trip Efficiency:** 87%

**One-Way Efficiency:** √0.87 = 93.3%

**Charging Process:**
```
Energy Stored = Energy Input × 0.933
Example: 10 MWh input → 9.33 MWh stored (0.67 MWh loss)
```

**Discharging Process:**
```
Energy from Battery = Energy Output / 0.933
Example: 10 MWh output requires 10.72 MWh from battery (0.72 MWh loss)
```

**Round-Trip Verification:**
```
Charge → Discharge: 10 MWh × 0.933 × 0.933 = 8.7 MWh (87% efficiency)
```

#### 2.1.5 C-Rate Power Constraints

**Charge Rate (C-Rate):** 1.0 (can charge at power = capacity)
**Discharge Rate (C-Rate):** 1.0 (can discharge at power = capacity)

**Power Limitations:**
```
Max Charge Power = Capacity × C_Rate_Charge = Capacity × 1.0
Max Discharge Power = Capacity × C_Rate_Discharge = Capacity × 1.0

Example: 100 MWh battery
- Max charge power: 100 MW
- Max discharge power: 100 MW
```

**Impact:** Even if battery has energy, power delivery limited by C-rate

#### 2.1.6 Solar-Only Charging Rule

**Rule:** Battery charges ONLY from solar energy, never from grid

**Rationale:**
- True renewable energy storage
- No grid dependency for charging
- Maximizes solar utilization
- Reduces operational costs

**Impact:** Battery can only charge when solar > delivery requirement

### 2.2 System Parameters

| Parameter | Value | Unit | Description |
|-----------|-------|------|-------------|
| Target Delivery | 25 | MW | Binary delivery target |
| Solar Capacity | 67 | MW | Maximum PV generation |
| Battery Range | 10-500 | MWh | Optimization search space |
| MIN_SOC | 5 | % | Minimum state of charge |
| MAX_SOC | 95 | % | Maximum state of charge |
| Round-Trip Efficiency | 87 | % | Full charge/discharge cycle |
| One-Way Efficiency | 93.3 | % | Single direction |
| C-Rate (both) | 1.0 | - | Power rate limit |
| Max Daily Cycles | 2.0 | cycles/day | Degradation management |
| Initial SOC | 50 | % | Starting condition |
| Degradation Rate | 0.15 | %/cycle | Capacity loss per cycle |

---

## 3. Master Decision Tree

### 3.1 Hourly Decision Process

This is the master logic executed every hour (8,760 times per year):

```
START (Every Hour)
    │
    ├─→ Read Current State
    │   ├─ Solar Generation (MW)
    │   ├─ Battery SOC (%)
    │   ├─ Battery State (IDLE/CHARGING/DISCHARGING)
    │   └─ Daily Cycles Count
    │
    ├─→ Calculate Available Resources
    │   ├─ Solar Available = Current Solar Generation
    │   ├─ Battery Available Energy = (SOC - 0.05) × Capacity
    │   ├─ Battery Available Power = min(Available Energy, Capacity × C_Rate)
    │   └─ Total Available = Solar + Battery Available Power
    │
    ├─→ Check Deliverability
    │   │
    │   ├─→ [Total Available < 25 MW]?
    │   │   └─→ YES → Go to SCENARIO 3: Insufficient Resources
    │   │
    │   ├─→ [Solar ≥ 25 MW]?
    │   │   └─→ YES → Go to SCENARIO 1: Excess Solar
    │   │
    │   ├─→ [Solar < 25 MW AND Total ≥ 25 MW]?
    │   │   │
    │   │   ├─→ [Daily Cycles ≥ 2.0]?
    │   │   │   └─→ YES → Go to SCENARIO 4: Cycle Limit Reached
    │   │   │
    │   │   ├─→ [Can Transition to DISCHARGING]?
    │   │   │   ├─→ YES → Go to SCENARIO 2: Solar + Battery Support
    │   │   │   └─→ NO → Go to SCENARIO 4: Cycle Limit Reached
    │   │
    │   └─→ Otherwise → Go to SCENARIO 3: Insufficient Resources
    │
    ├─→ Execute Scenario Logic
    │   └─ (See Section 4 for detailed scenario logic)
    │
    ├─→ Update System State
    │   ├─ Record Delivery (0 or 25 MW)
    │   ├─ Update Battery SOC
    │   ├─ Update Battery State (IDLE/CHARGING/DISCHARGING)
    │   ├─ Update Cycle Count
    │   └─ Record Wastage (if any)
    │
    └─→ END (Proceed to Next Hour)
```

### 3.2 Decision Tree Summary Table

| Condition | Solar | Battery | Cycles | Action | Scenario |
|-----------|-------|---------|--------|--------|----------|
| Solar ≥ 25 MW | ≥25 MW | Any | Any | Deliver 25, charge excess | 1 |
| Total ≥ 25, Solar < 25 | <25 MW | Sufficient | <2.0 | Deliver 25, discharge battery | 2 |
| Total < 25 MW | <25 MW | Insufficient | Any | No delivery, charge if solar available | 3 |
| Resources OK but cycles | <25 MW | Sufficient | ≥2.0 | No delivery, charge if solar available | 4 |
| At SOC boundaries | Any | At 5% or 95% | Any | Constrained operation | 5 |
| Zero solar | 0 MW | Any | Any | No delivery, no charging | 6 |

---

## 4. Core Delivery Scenarios

### 4.1 Scenario 1: Excess Solar (Solar ≥ 25 MW)

**Trigger Condition:** Solar generation meets or exceeds delivery target

**Business Logic:**
1. Deliver 25 MW from solar to load
2. Calculate excess solar: `Excess = Solar - 25 MW`
3. Attempt to charge battery with excess
4. Record any remaining wastage

**Decision Tree:**
```
Solar ≥ 25 MW
    │
    ├─→ Deliver 25 MW from Solar
    │
    ├─→ Calculate Excess = Solar - 25
    │
    ├─→ Can Charge Battery?
    │   │
    │   ├─→ [SOC < 95%]?
    │   │   │
    │   │   ├─→ YES: Charge Battery
    │   │   │   ├─ Available Headroom = (0.95 - SOC) × Capacity
    │   │   │   ├─ Max Charge Power = min(Excess, Capacity × C_Rate)
    │   │   │   ├─ Actual Charge = min(Max Charge Power, Available Headroom / 0.933)
    │   │   │   ├─ Energy Stored = Actual Charge × 0.933
    │   │   │   ├─ Update SOC = SOC + (Energy Stored / Capacity)
    │   │   │   ├─ Update State to CHARGING (if from IDLE)
    │   │   │   └─ Remaining Excess = Excess - Actual Charge
    │   │   │
    │   │   └─→ NO: Battery Full
    │   │       └─ Wastage = Excess
    │   │
    │   └─→ Record Wastage (if any excess not charged)
    │
    └─→ Record: Delivery = 25 MW, Source = Solar
```

**Mathematical Formulas:**

1. **Excess Solar:**
   ```
   Excess_Solar = Solar_MW - 25
   ```

2. **Charge Headroom:**
   ```
   Headroom = (MAX_SOC - Current_SOC) × Capacity
   Headroom = (0.95 - SOC) × Capacity
   ```

3. **Actual Charge (limited by headroom and C-rate):**
   ```
   Max_Charge_Power = min(Excess_Solar, Capacity × 1.0)
   Max_Energy_Input = min(Max_Charge_Power, Headroom / 0.933)
   Actual_Charge = Max_Energy_Input
   ```

4. **Energy Stored (after efficiency loss):**
   ```
   Energy_Stored = Actual_Charge × 0.933
   ```

5. **SOC Update:**
   ```
   Δ_SOC = Energy_Stored / Capacity
   New_SOC = Old_SOC + Δ_SOC
   ```

6. **Wastage:**
   ```
   Wastage = Excess_Solar - Actual_Charge
   ```

**Numerical Example:**

**Initial Conditions:**
- Solar: 35 MW
- Battery: 100 MWh capacity
- Current SOC: 60% (60 MWh stored)
- State: IDLE
- Daily Cycles: 0.5

**Step-by-Step Calculation:**

1. **Delivery:**
   ```
   Solar (35 MW) ≥ 25 MW → Can Deliver
   Delivery = 25 MW
   ```

2. **Excess Solar:**
   ```
   Excess = 35 - 25 = 10 MW
   ```

3. **Charge Headroom:**
   ```
   Headroom = (0.95 - 0.60) × 100 = 35 MWh
   ```

4. **Charge Limits:**
   ```
   Max_Charge_Power = min(10 MW, 100 MWh × 1.0) = 10 MW
   Max_Energy_Input = min(10 MWh, 35 / 0.933) = 10 MWh
   ```

5. **Energy Stored:**
   ```
   Energy_Stored = 10 × 0.933 = 9.33 MWh
   ```

6. **SOC Update:**
   ```
   Δ_SOC = 9.33 / 100 = 9.33%
   New_SOC = 60% + 9.33% = 69.33%
   ```

7. **State Update:**
   ```
   Old State: IDLE
   New State: CHARGING (transition adds 0.5 cycles)
   Daily Cycles: 0.5 + 0.5 = 1.0
   ```

8. **Wastage:**
   ```
   Wastage = 10 - 10 = 0 MW (all excess charged)
   ```

**Code Reference:** `src/battery_simulator.py:240-260`

```python
# Scenario 1: Solar exceeds delivery target
if solar_mw >= target_delivery_mw:
    # Deliver from solar
    delivery_this_hour = 'Yes'

    # Calculate excess solar
    excess_solar = solar_mw - target_delivery_mw

    # Try to charge battery with excess
    if excess_solar > 0 and battery.state != 'DISCHARGING':
        charged = battery.charge(excess_solar)
        # Update state to CHARGING if successful
        if charged > 0 and battery.state == 'IDLE':
            battery.update_state_and_cycles('CHARGING', hour)
        wastage = excess_solar - charged
    else:
        wastage = excess_solar
```

---

### 4.2 Scenario 2: Solar + Battery Support (Solar < 25 MW, Total Sufficient)

**Trigger Condition:** Solar alone insufficient, but solar + battery can meet target

**Business Logic:**
1. Check if daily cycles < 2.0
2. Check if can transition to DISCHARGING state
3. Calculate deficit: `Deficit = 25 - Solar`
4. Discharge battery to cover deficit
5. Deliver 25 MW total

**Decision Tree:**
```
Solar < 25 MW AND (Solar + Battery_Available) ≥ 25 MW
    │
    ├─→ Calculate Deficit = 25 - Solar
    │
    ├─→ Check Cycle Limit
    │   │
    │   ├─→ [Daily Cycles < 2.0]?
    │   │   │
    │   │   ├─→ YES: Can Proceed
    │   │   │   │
    │   │   │   ├─→ Check State Transition
    │   │   │   │   │
    │   │   │   │   ├─→ [Can Transition to DISCHARGING]?
    │   │   │   │   │   │
    │   │   │   │   │   ├─→ YES: Discharge Battery
    │   │   │   │   │   │   ├─ Required Output = Deficit
    │   │   │   │   │   │   ├─ Battery Energy Needed = Deficit / 0.933
    │   │   │   │   │   │   ├─ Available Energy = (SOC - 0.05) × Capacity
    │   │   │   │   │   │   ├─ Max Discharge Power = Capacity × C_Rate
    │   │   │   │   │   │   ├─ Actual Discharge = min(Required, Available, Max Power)
    │   │   │   │   │   │   ├─ Update SOC = SOC - (Energy Used / Capacity)
    │   │   │   │   │   │   ├─ Update State to DISCHARGING
    │   │   │   │   │   │   ├─ Deliver 25 MW (Solar + Battery)
    │   │   │   │   │   │   └─ Update Cycle Count (if state transition)
    │   │   │   │   │   │
    │   │   │   │   │   └─→ NO: Cycle Limit Blocks
    │   │   │   │   │       └─ Go to Scenario 4
    │   │   │   │   │
    │   │   └─→ NO: Cycle Limit Reached
    │   │       └─ Go to Scenario 4
    │   │
    └─→ Record: Delivery = 25 MW, Source = Solar + Battery
```

**Mathematical Formulas:**

1. **Deficit Calculation:**
   ```
   Deficit = 25 - Solar_MW
   ```

2. **Battery Energy Required (accounting for efficiency):**
   ```
   Battery_Energy_Needed = Deficit / 0.933
   ```

3. **Available Battery Energy:**
   ```
   Available_Energy = (SOC - MIN_SOC) × Capacity
   Available_Energy = (SOC - 0.05) × Capacity
   ```

4. **Maximum Discharge Power:**
   ```
   Max_Discharge_Power = min(Available_Energy, Capacity × C_Rate)
   ```

5. **Actual Discharge:**
   ```
   Actual_Discharge = min(Deficit, Max_Discharge_Power)
   ```

6. **Battery Energy Used:**
   ```
   Battery_Energy_Used = Actual_Discharge / 0.933
   ```

7. **SOC Update:**
   ```
   Δ_SOC = Battery_Energy_Used / Capacity
   New_SOC = Old_SOC - Δ_SOC
   ```

**Numerical Example:**

**Initial Conditions:**
- Solar: 15 MW
- Battery: 100 MWh capacity
- Current SOC: 50% (50 MWh stored)
- State: IDLE
- Daily Cycles: 1.0

**Step-by-Step Calculation:**

1. **Check Deliverability:**
   ```
   Solar (15 MW) < 25 MW → Need battery support
   Available_Energy = (0.50 - 0.05) × 100 = 45 MWh
   Max_Discharge_Power = min(45, 100 × 1.0) = 45 MW
   Total_Available = 15 + 45 = 60 MW
   60 MW ≥ 25 MW → Can deliver
   ```

2. **Check Cycle Limit:**
   ```
   Daily_Cycles = 1.0 < 2.0 → Can proceed
   ```

3. **Calculate Deficit:**
   ```
   Deficit = 25 - 15 = 10 MW
   ```

4. **Battery Energy Needed:**
   ```
   Battery_Energy_Needed = 10 / 0.933 = 10.72 MWh
   ```

5. **Check Availability:**
   ```
   Available_Energy = 45 MWh ≥ 10.72 MWh → Sufficient
   Max_Discharge_Power = 45 MW ≥ 10 MW → Sufficient
   ```

6. **Discharge Battery:**
   ```
   Actual_Discharge = 10 MW (deficit covered)
   Battery_Energy_Used = 10.72 MWh
   ```

7. **SOC Update:**
   ```
   Δ_SOC = 10.72 / 100 = 10.72%
   New_SOC = 50% - 10.72% = 39.28%
   ```

8. **State Update:**
   ```
   Old State: IDLE
   New State: DISCHARGING (transition adds 0.5 cycles)
   Daily Cycles: 1.0 + 0.5 = 1.5
   ```

9. **Delivery:**
   ```
   Delivery = 25 MW (15 MW solar + 10 MW battery)
   ```

**Code Reference:** `src/battery_simulator.py:262-285`

```python
# Scenario 2: Need battery support
elif can_deliver_resources:
    # Check if we can discharge (cycle limit)
    deficit = target_delivery_mw - solar_mw

    if battery.can_cycle('DISCHARGING'):
        # Discharge battery for deficit
        discharged = battery.discharge(deficit)

        if discharged >= deficit:
            delivery_this_hour = 'Yes'
            # Update state to DISCHARGING
            if battery.state != 'DISCHARGING':
                battery.update_state_and_cycles('DISCHARGING', hour)
        else:
            # Insufficient battery power
            delivery_this_hour = 'No'
            deficit_mw = target_delivery_mw - (solar_mw + discharged)
    else:
        # Cycle limit blocks discharge
        delivery_this_hour = 'No'
        deficit_mw = deficit
```

---

### 4.3 Scenario 3: Insufficient Resources (Total < 25 MW)

**Trigger Condition:** Combined solar + battery cannot meet 25 MW target

**Business Logic:**
1. Cannot deliver (resources insufficient)
2. Attempt to charge battery with available solar
3. Record deficit for tracking
4. Battery state goes to IDLE or stays CHARGING

**Decision Tree:**
```
(Solar + Battery_Available) < 25 MW
    │
    ├─→ Cannot Deliver
    │   └─ Delivery = 0 MW
    │
    ├─→ Calculate Deficit
    │   └─ Deficit = 25 - (Solar + Battery_Available)
    │
    ├─→ Attempt to Charge Battery with Available Solar
    │   │
    │   ├─→ [Solar > 0]?
    │   │   │
    │   │   ├─→ YES: Charge Battery
    │   │   │   ├─ Available Solar = Solar_MW
    │   │   │   ├─ Charge Headroom = (0.95 - SOC) × Capacity
    │   │   │   ├─ Max Charge Power = min(Solar, Capacity × C_Rate)
    │   │   │   ├─ Actual Charge = min(Max Charge Power, Headroom / 0.933)
    │   │   │   ├─ Energy Stored = Actual Charge × 0.933
    │   │   │   ├─ Update SOC
    │   │   │   ├─ Update State to CHARGING (if from IDLE)
    │   │   │   └─ Wastage = Solar - Actual Charge
    │   │   │
    │   │   └─→ NO: No Solar Available
    │   │       └─ No Charging Possible
    │   │
    │   └─→ [State == DISCHARGING]?
    │       └─→ YES: Transition to IDLE (adds 0.5 cycles)
    │
    └─→ Record: Delivery = 0 MW, Deficit = calculated
```

**Mathematical Formulas:**

1. **Deficit Calculation:**
   ```
   Total_Available = Solar_MW + Battery_Available_Power
   Deficit = 25 - Total_Available
   ```

2. **Battery Available Power:**
   ```
   Available_Energy = (SOC - 0.05) × Capacity
   Max_Discharge_Power = Capacity × C_Rate
   Battery_Available_Power = min(Available_Energy, Max_Discharge_Power)
   ```

3. **Charging (if solar available):**
   ```
   Charge_Headroom = (0.95 - SOC) × Capacity
   Max_Charge_Power = min(Solar_MW, Capacity × C_Rate)
   Actual_Charge = min(Max_Charge_Power, Headroom / 0.933)
   Energy_Stored = Actual_Charge × 0.933
   ```

**Numerical Example 1: Low Solar, Empty Battery**

**Initial Conditions:**
- Solar: 5 MW
- Battery: 100 MWh capacity
- Current SOC: 10% (10 MWh stored)
- State: IDLE
- Daily Cycles: 0.0

**Step-by-Step Calculation:**

1. **Check Deliverability:**
   ```
   Available_Energy = (0.10 - 0.05) × 100 = 5 MWh
   Battery_Available_Power = min(5, 100) = 5 MW
   Total_Available = 5 + 5 = 10 MW
   10 MW < 25 MW → Cannot deliver
   ```

2. **Delivery:**
   ```
   Delivery = 0 MW
   ```

3. **Calculate Deficit:**
   ```
   Deficit = 25 - 10 = 15 MW
   ```

4. **Attempt Charging:**
   ```
   Solar = 5 MW > 0 → Can charge
   Charge_Headroom = (0.95 - 0.10) × 100 = 85 MWh
   Max_Charge_Power = min(5, 100) = 5 MW
   Actual_Charge = 5 MW (5 MWh in 1 hour)
   Energy_Stored = 5 × 0.933 = 4.665 MWh
   ```

5. **SOC Update:**
   ```
   Δ_SOC = 4.665 / 100 = 4.665%
   New_SOC = 10% + 4.665% = 14.665%
   ```

6. **State Update:**
   ```
   Old State: IDLE
   New State: CHARGING
   Daily Cycles: 0.0 + 0.5 = 0.5
   ```

**Numerical Example 2: Nighttime (Zero Solar)**

**Initial Conditions:**
- Solar: 0 MW
- Battery: 100 MWh capacity
- Current SOC: 40% (40 MWh stored)
- State: IDLE
- Daily Cycles: 1.5

**Step-by-Step Calculation:**

1. **Check Deliverability:**
   ```
   Available_Energy = (0.40 - 0.05) × 100 = 35 MWh
   Battery_Available_Power = min(35, 100) = 35 MW
   Total_Available = 0 + 35 = 35 MW
   35 MW ≥ 25 MW → Theoretically can deliver
   ```

2. **Check Cycle Limit:**
   ```
   Daily_Cycles = 1.5 < 2.0 → Can cycle
   BUT: Solar = 0, so no source to support delivery
   ```

3. **Delivery:**
   ```
   Delivery = 0 MW (nighttime, no delivery scheduled)
   ```

4. **No Charging:**
   ```
   Solar = 0 → Cannot charge
   State remains IDLE
   ```

**Code Reference:** `src/battery_simulator.py:287-305`

```python
# Scenario 3: Insufficient resources
else:
    # Cannot deliver
    delivery_this_hour = 'No'
    deficit_mw = target_delivery_mw - (solar_mw + battery_available_mw)

    # Try to charge with available solar
    if solar_mw > 0 and battery.state != 'DISCHARGING':
        charged = battery.charge(solar_mw)
        if charged > 0 and battery.state == 'IDLE':
            battery.update_state_and_cycles('CHARGING', hour)
        wastage = solar_mw - charged
    else:
        # No solar or in wrong state
        if battery.state == 'DISCHARGING':
            battery.update_state_and_cycles('IDLE', hour)
```

---

### 4.4 Scenario 4: Cycle Limit Reached (Resources Available but Blocked)

**Trigger Condition:**
- Solar + Battery ≥ 25 MW (resources sufficient)
- Solar < 25 MW (need battery)
- Daily Cycles ≥ 2.0 (limit reached)

**Business Logic:**
1. Cannot discharge battery (cycle limit)
2. Cannot deliver (need battery but can't use it)
3. Attempt to charge with available solar
4. Battery state must go to IDLE or CHARGING only

**Decision Tree:**
```
(Solar + Battery) ≥ 25 MW AND Solar < 25 MW AND Daily_Cycles ≥ 2.0
    │
    ├─→ Cannot Discharge Battery
    │   └─ Reason: Cycle limit reached (2.0 cycles/day)
    │
    ├─→ Cannot Deliver
    │   └─ Delivery = 0 MW
    │
    ├─→ Calculate Deficit
    │   └─ Deficit = 25 - Solar (battery cannot help)
    │
    ├─→ Attempt to Charge Battery
    │   │
    │   ├─→ [Solar > 0]?
    │   │   │
    │   │   ├─→ YES: Charge Battery
    │   │   │   ├─ Available Solar = Solar_MW
    │   │   │   ├─ Note: Charging does NOT add cycles
    │   │   │   ├─ Charge normally (see Scenario 1 charging logic)
    │   │   │   └─ Wastage = Solar - Charged
    │   │   │
    │   │   └─→ NO: No Solar
    │   │       └─ No charging possible
    │   │
    │   └─→ [State == DISCHARGING]?
    │       └─→ YES: Must transition to IDLE
    │           └─ Note: This would add 0.5 cycles, but already at 2.0
    │               Decision: Stay in current state or force IDLE?
    │               Current Implementation: Force IDLE
    │
    └─→ Record: Delivery = 0 MW, Reason = Cycle Limit
```

**Key Point:** Cycle counting only applies to **transitions involving DISCHARGING**. Charging does not consume cycles in the same way.

**Mathematical Formulas:**

1. **Theoretical Capability:**
   ```
   Battery_Available_Power = min((SOC - 0.05) × Capacity, Capacity × C_Rate)
   Total_Available = Solar_MW + Battery_Available_Power
   ```

2. **Actual Capability (with cycle constraint):**
   ```
   IF Daily_Cycles ≥ 2.0 THEN
       Battery_Available_Power = 0  (blocked by cycles)
       Total_Available = Solar_MW
   END IF
   ```

3. **Deficit:**
   ```
   Deficit = 25 - Solar_MW
   ```

**Numerical Example:**

**Initial Conditions:**
- Solar: 20 MW
- Battery: 100 MWh capacity
- Current SOC: 60% (60 MWh stored)
- State: IDLE
- Daily Cycles: 2.0 (limit reached)

**Step-by-Step Calculation:**

1. **Check Resources (Theoretical):**
   ```
   Available_Energy = (0.60 - 0.05) × 100 = 55 MWh
   Battery_Power = min(55, 100) = 55 MW
   Total_Theoretical = 20 + 55 = 75 MW ≥ 25 MW
   ```

2. **Check Cycle Limit:**
   ```
   Daily_Cycles = 2.0 ≥ 2.0 → LIMIT REACHED
   Can_Cycle('DISCHARGING') = FALSE
   ```

3. **Actual Available Power:**
   ```
   Battery_Available = 0 MW (blocked by cycle limit)
   Total_Actual = 20 + 0 = 20 MW
   20 MW < 25 MW → Cannot deliver
   ```

4. **Delivery:**
   ```
   Delivery = 0 MW
   Reason: Cycle limit prevents battery use
   ```

5. **Deficit:**
   ```
   Deficit = 25 - 20 = 5 MW
   Note: Battery has 55 MW available but cannot use
   ```

6. **Attempt Charging:**
   ```
   Solar = 20 MW > 0 → Can charge
   Headroom = (0.95 - 0.60) × 100 = 35 MWh
   Max_Charge = min(20, 100) = 20 MW
   Actual_Charge = 20 MW
   Energy_Stored = 20 × 0.933 = 18.66 MWh
   ```

7. **SOC Update:**
   ```
   Δ_SOC = 18.66 / 100 = 18.66%
   New_SOC = 60% + 18.66% = 78.66%
   ```

8. **State Update:**
   ```
   Old State: IDLE
   New State: CHARGING
   Note: IDLE → CHARGING adds 0.5 cycles
   BUT: Already at 2.0 cycles
   Current Implementation: Allow charging without adding cycles
   (Only DISCHARGING transitions count toward limit)
   Daily Cycles: 2.0 (unchanged)
   ```

**Code Reference:** `src/battery_simulator.py:270-275`

```python
# Check if we can discharge (cycle limit)
if battery.can_cycle('DISCHARGING'):
    # Can proceed with discharge
    discharged = battery.discharge(deficit)
    # ... discharge logic
else:
    # Cycle limit blocks discharge
    delivery_this_hour = 'No'
    deficit_mw = deficit
    # Try to charge instead
    if solar_mw > 0:
        charged = battery.charge(solar_mw)
```

---

### 4.5 Scenario 5: SOC Boundary Conditions

**Trigger Condition:**
- SOC at or near minimum (5%) or maximum (95%)
- Affects charging/discharging capability

**Business Logic:**

#### 4.5.1 At Minimum SOC (5%)

**Impact:**
- Cannot discharge further
- Must charge before delivering

**Decision Tree:**
```
SOC ≤ 5%
    │
    ├─→ Available Energy = 0 MWh
    │   └─ Cannot discharge
    │
    ├─→ [Solar ≥ 25 MW]?
    │   │
    │   ├─→ YES: Deliver from solar only
    │   │   └─ Charge excess to battery
    │   │
    │   └─→ NO: Cannot deliver
    │       └─ Charge battery if solar available
    │
    └─→ Must charge before battery can support delivery
```

**Mathematical Formula:**
```
Available_Energy = max(0, (SOC - MIN_SOC) × Capacity)
Available_Energy = max(0, (0.05 - 0.05) × Capacity) = 0 MWh
```

**Numerical Example:**

**Initial Conditions:**
- Solar: 30 MW
- Battery: 100 MWh capacity
- Current SOC: 5% (minimum)
- State: IDLE
- Daily Cycles: 1.0

**Calculation:**

1. **Check Battery Availability:**
   ```
   Available_Energy = (0.05 - 0.05) × 100 = 0 MWh
   Battery cannot support delivery
   ```

2. **Check Solar:**
   ```
   Solar = 30 MW ≥ 25 MW → Can deliver from solar alone
   ```

3. **Delivery:**
   ```
   Delivery = 25 MW (from solar)
   ```

4. **Charge Excess:**
   ```
   Excess = 30 - 25 = 5 MW
   Headroom = (0.95 - 0.05) × 100 = 90 MWh
   Charge = 5 MW
   Energy_Stored = 5 × 0.933 = 4.665 MWh
   New_SOC = 5% + 4.665% = 9.665%
   ```

#### 4.5.2 At Maximum SOC (95%)

**Impact:**
- Cannot charge further
- Any excess solar is wasted
- Can discharge normally

**Decision Tree:**
```
SOC ≥ 95%
    │
    ├─→ Charge Headroom = 0 MWh
    │   └─ Cannot charge
    │
    ├─→ Can Discharge Normally
    │   └─ Available Energy = (0.95 - 0.05) × Capacity = 90% of capacity
    │
    ├─→ [Solar > 0 AND No charging possible]?
    │   └─→ YES: Excess Solar = Wastage
    │
    └─→ Delivery depends on solar + discharge capability
```

**Mathematical Formula:**
```
Charge_Headroom = max(0, (MAX_SOC - SOC) × Capacity)
Charge_Headroom = max(0, (0.95 - 0.95) × Capacity) = 0 MWh
```

**Numerical Example:**

**Initial Conditions:**
- Solar: 40 MW
- Battery: 100 MWh capacity
- Current SOC: 95% (maximum)
- State: IDLE
- Daily Cycles: 0.5

**Calculation:**

1. **Check Charging Capability:**
   ```
   Headroom = (0.95 - 0.95) × 100 = 0 MWh
   Cannot charge
   ```

2. **Delivery:**
   ```
   Solar = 40 MW ≥ 25 MW → Deliver 25 MW
   ```

3. **Excess Solar:**
   ```
   Excess = 40 - 25 = 15 MW
   Cannot charge → All excess wasted
   Wastage = 15 MW
   ```

4. **Battery State:**
   ```
   State remains IDLE
   No charging occurred
   ```

---

### 4.6 Scenario 6: Nighttime Operation (Zero Solar)

**Trigger Condition:** Solar = 0 MW (nighttime hours)

**Business Logic:**
1. No solar available
2. Cannot charge battery
3. Could theoretically discharge, but not standard operation
4. Delivery = 0 MW (nighttime, no scheduled delivery)

**Decision Tree:**
```
Solar = 0 MW
    │
    ├─→ No Solar Available
    │   └─ Cannot charge battery
    │
    ├─→ Battery Available?
    │   │
    │   ├─→ Theoretical Capability:
    │   │   └─ Could discharge up to (SOC - 0.05) × Capacity
    │   │
    │   └─→ Operational Decision:
    │       └─ Nighttime = No scheduled delivery
    │
    ├─→ Delivery = 0 MW
    │   └─ Reason: Nighttime (not cycle limit or resource issue)
    │
    └─→ Battery State
        └─ State = IDLE (or maintain previous state)
```

**Mathematical Formulas:**

1. **Available Resources:**
   ```
   Solar = 0 MW
   Battery_Available = (SOC - 0.05) × Capacity
   Total_Available = 0 + Battery_Available
   ```

2. **Theoretical Capability:**
   ```
   IF Battery_Available ≥ 25 MW AND Daily_Cycles < 2.0 THEN
       Theoretically_Can_Deliver = TRUE
   ELSE
       Theoretically_Can_Deliver = FALSE
   END IF
   ```

**Numerical Example:**

**Initial Conditions:**
- Solar: 0 MW (nighttime)
- Battery: 100 MWh capacity
- Current SOC: 70% (70 MWh stored)
- State: IDLE
- Daily Cycles: 1.5
- Time: 02:00 (2 AM)

**Calculation:**

1. **Check Resources:**
   ```
   Solar = 0 MW
   Available_Energy = (0.70 - 0.05) × 100 = 65 MWh
   Battery_Power = min(65, 100) = 65 MW
   Total_Available = 0 + 65 = 65 MW ≥ 25 MW
   ```

2. **Check Cycles:**
   ```
   Daily_Cycles = 1.5 < 2.0 → Could cycle if needed
   ```

3. **Operational Decision:**
   ```
   Time = Nighttime (02:00)
   Standard_Operation = No delivery at night
   Delivery = 0 MW
   ```

4. **Battery State:**
   ```
   State remains IDLE
   No charging (no solar)
   No discharging (no delivery scheduled)
   ```

**Note:** System could theoretically deliver 25 MW from battery at night, but standard operation doesn't schedule deliveries during nighttime hours.

---

### 4.7 Scenario 7: State Transition Scenarios

**Trigger Condition:** Battery changes operational state

**Business Logic:** State transitions trigger cycle counting

#### 4.7.1 State Definitions

- **IDLE:** Battery neither charging nor discharging
- **CHARGING:** Battery accepting energy from solar
- **DISCHARGING:** Battery providing energy to load

#### 4.7.2 Valid Transitions

| From State | To State | Cycle Impact | Trigger |
|------------|----------|--------------|---------|
| IDLE | CHARGING | +0.5 cycles | Excess solar available |
| IDLE | DISCHARGING | +0.5 cycles | Need battery support |
| CHARGING | IDLE | +0.5 cycles | No more excess solar |
| DISCHARGING | IDLE | +0.5 cycles | No more discharge needed |
| CHARGING | DISCHARGING | +1.0 cycles | Direct transition (rare) |
| DISCHARGING | CHARGING | +1.0 cycles | Direct transition (rare) |
| IDLE | IDLE | 0 cycles | No change |
| CHARGING | CHARGING | 0 cycles | Continue charging |
| DISCHARGING | DISCHARGING | 0 cycles | Continue discharging |

**Decision Tree:**
```
State Transition Required?
    │
    ├─→ [New State == Old State]?
    │   └─→ YES: No cycle impact
    │       └─ Continue operation
    │
    ├─→ [New State != Old State]?
    │   │
    │   ├─→ Calculate Cycle Impact
    │   │   ├─ Direct transitions (CHARGING ↔ DISCHARGING): +1.0 cycles
    │   │   └─ Other transitions: +0.5 cycles
    │   │
    │   ├─→ Check Daily Cycle Limit
    │   │   │
    │   │   ├─→ [Daily_Cycles + Impact ≤ 2.0]?
    │   │   │   │
    │   │   │   ├─→ YES: Allow transition
    │   │   │   │   ├─ Update State
    │   │   │   │   └─ Add cycle impact
    │   │   │   │
    │   │   │   └─→ NO: Block transition
    │   │   │       └─ Maintain current state
    │   │
    │   └─→ Record transition
    │
    └─→ Continue with scenario logic
```

**Numerical Example: Multiple Transitions in One Day**

**Day Profile:**

| Hour | Solar | Action | State Change | Cycles |
|------|-------|--------|--------------|--------|
| 00:00 | 0 MW | Start | IDLE | 0.0 |
| 06:00 | 10 MW | Charge | IDLE → CHARGING | 0.5 |
| 07:00 | 15 MW | Charge | CHARGING | 0.5 |
| 08:00 | 20 MW | Charge | CHARGING | 0.5 |
| 09:00 | 30 MW | Deliver+Charge | CHARGING | 0.5 |
| 10:00 | 35 MW | Deliver+Charge | CHARGING | 0.5 |
| 11:00 | 30 MW | Deliver+Charge | CHARGING | 0.5 |
| 12:00 | 28 MW | Deliver+Charge | CHARGING | 0.5 |
| 13:00 | 25 MW | Deliver | CHARGING → IDLE | 1.0 |
| 14:00 | 20 MW | Discharge | IDLE → DISCHARGING | 1.5 |
| 15:00 | 18 MW | Discharge | DISCHARGING | 1.5 |
| 16:00 | 15 MW | Discharge | DISCHARGING | 1.5 |
| 17:00 | 10 MW | Cannot deliver | DISCHARGING → IDLE | 2.0 |
| 18:00 | 5 MW | Cannot deliver | IDLE | 2.0 |
| 19:00 | 0 MW | Night | IDLE | 2.0 |
| 20:00-23:00 | 0 MW | Night | IDLE | 2.0 |

**Key Transitions:**
1. **Hour 06:00:** IDLE → CHARGING (+0.5 cycles)
2. **Hour 13:00:** CHARGING → IDLE (+0.5 cycles, total 1.0)
3. **Hour 14:00:** IDLE → DISCHARGING (+0.5 cycles, total 1.5)
4. **Hour 17:00:** DISCHARGING → IDLE (+0.5 cycles, total 2.0)
5. **Hour 18:00+:** Cannot cycle further (limit reached)

**Code Reference:** `src/battery_simulator.py:90-115` (BatterySystem.update_state_and_cycles)

```python
def update_state_and_cycles(self, new_state, hour):
    """
    Update battery state and track cycles.
    Each state transition counts as 0.5 cycles.
    """
    # Reset cycles at start of new day
    if hour % 24 == 0:
        self.daily_cycles = 0.0

    # Count cycle if state changes
    if new_state != self.state:
        # Transition between charging and discharging = 1.0 cycle
        if (self.state == 'CHARGING' and new_state == 'DISCHARGING') or \
           (self.state == 'DISCHARGING' and new_state == 'CHARGING'):
            self.daily_cycles += 1.0
        # Any other transition = 0.5 cycles
        elif self.state != 'IDLE' or new_state != 'IDLE':
            self.daily_cycles += 0.5

    # Update state
    self.state = new_state
    self.total_cycles = self.daily_cycles
```

---

## 5. Hour-by-Hour Walkthrough Examples

### 5.1 Example 1: Typical Day (Complete 24-Hour Cycle)

**System Configuration:**
- Battery: 150 MWh capacity
- Initial SOC: 50% (75 MWh stored)
- Initial State: IDLE
- Initial Daily Cycles: 0.0
- Solar Profile: Typical sunny day with parabolic generation curve

**Hour-by-Hour Analysis:**

| Hour | Time | Solar (MW) | SOC Start | State Start | Cycles Start | Action | Delivery | Battery Action | SOC End | State End | Cycles End |
|------|------|------------|-----------|-------------|--------------|--------|----------|----------------|---------|-----------|------------|
| 0 | 00:00 | 0 | 50.0% | IDLE | 0.0 | Night | 0 MW | None | 50.0% | IDLE | 0.0 |
| 1 | 01:00 | 0 | 50.0% | IDLE | 0.0 | Night | 0 MW | None | 50.0% | IDLE | 0.0 |
| 2 | 02:00 | 0 | 50.0% | IDLE | 0.0 | Night | 0 MW | None | 50.0% | IDLE | 0.0 |
| 3 | 03:00 | 0 | 50.0% | IDLE | 0.0 | Night | 0 MW | None | 50.0% | IDLE | 0.0 |
| 4 | 04:00 | 0 | 50.0% | IDLE | 0.0 | Night | 0 MW | None | 50.0% | IDLE | 0.0 |
| 5 | 05:00 | 0 | 50.0% | IDLE | 0.0 | Night | 0 MW | None | 50.0% | IDLE | 0.0 |
| 6 | 06:00 | 8 | 50.0% | IDLE | 0.0 | Charge | 0 MW | Charge 8 MW | 54.99% | CHARGING | 0.5 |
| 7 | 07:00 | 18 | 54.99% | CHARGING | 0.5 | Charge | 0 MW | Charge 18 MW | 66.19% | CHARGING | 0.5 |
| 8 | 08:00 | 32 | 66.19% | CHARGING | 0.5 | Del+Chg | 25 MW | Charge 7 MW | 70.54% | CHARGING | 0.5 |
| 9 | 09:00 | 45 | 70.54% | CHARGING | 0.5 | Del+Chg | 25 MW | Charge 20 MW | 82.99% | CHARGING | 0.5 |
| 10 | 10:00 | 55 | 82.99% | CHARGING | 0.5 | Del+Chg | 25 MW | Charge 30 MW | 95.0% | CHARGING | 0.5 |
| 11 | 11:00 | 60 | 95.0% | CHARGING | 0.5 | Del+Waste | 25 MW | Full (waste 35) | 95.0% | IDLE | 1.0 |
| 12 | 12:00 | 62 | 95.0% | IDLE | 1.0 | Del+Waste | 25 MW | Full (waste 37) | 95.0% | IDLE | 1.0 |
| 13 | 13:00 | 60 | 95.0% | IDLE | 1.0 | Del+Waste | 25 MW | Full (waste 35) | 95.0% | IDLE | 1.0 |
| 14 | 14:00 | 55 | 95.0% | IDLE | 1.0 | Del+Waste | 25 MW | Full (waste 30) | 95.0% | IDLE | 1.0 |
| 15 | 15:00 | 45 | 95.0% | IDLE | 1.0 | Del+Waste | 25 MW | Full (waste 20) | 95.0% | IDLE | 1.0 |
| 16 | 16:00 | 32 | 95.0% | IDLE | 1.0 | Del+Chg | 25 MW | Charge 7 MW | 95.0% | IDLE | 1.0 |
| 17 | 17:00 | 18 | 95.0% | IDLE | 1.0 | Del+Disch | 25 MW | Discharge 7 MW | 90.01% | DISCHARGING | 1.5 |
| 18 | 18:00 | 8 | 90.01% | DISCHARGING | 1.5 | Del+Disch | 25 MW | Discharge 17 MW | 78.77% | DISCHARGING | 1.5 |
| 19 | 19:00 | 2 | 78.77% | DISCHARGING | 1.5 | Del+Disch | 25 MW | Discharge 23 MW | 63.27% | DISCHARGING | 1.5 |
| 20 | 20:00 | 0 | 63.27% | DISCHARGING | 1.5 | No Del | 0 MW | To IDLE | 63.27% | IDLE | 2.0 |
| 21 | 21:00 | 0 | 63.27% | IDLE | 2.0 | Night | 0 MW | None | 63.27% | IDLE | 2.0 |
| 22 | 22:00 | 0 | 63.27% | IDLE | 2.0 | Night | 0 MW | None | 63.27% | IDLE | 2.0 |
| 23 | 23:00 | 0 | 63.27% | IDLE | 2.0 | Night | 0 MW | None | 63.27% | IDLE | 2.0 |

**Summary:**
- **Delivery Hours:** 14 hours (hours 8-19)
- **No Delivery Hours:** 10 hours (hours 0-7, 20-23)
- **Total Energy Delivered:** 14 × 25 = 350 MWh
- **Total Solar Generated:** Sum of solar column ≈ 600 MWh
- **Battery Net Change:** 50% → 63.27% (+13.27% = +19.9 MWh stored)
- **Solar Wasted:** Hours 11-15 (total ≈ 157 MWh)
- **Total Cycles:** 2.0 (limit reached)
- **Final State:** IDLE (ready for next day)

**Key Observations:**
1. Battery charged during morning (hours 6-10)
2. Battery full at hour 10, causing wastage (hours 11-15)
3. Battery discharged in evening (hours 17-19)
4. Cycle limit reached at hour 20, preventing further discharge
5. Battery ended with more charge than start (+13.27%)

---

### 5.2 Example 2: High Solar Day (Excess Charging)

**Scenario:** Very sunny day with high solar generation
**Battery:** 100 MWh, starting at 30% SOC

**Key Hours:**

**Hour 8:** Peak Solar Begins
```
Solar: 55 MW
SOC: 30%
State: CHARGING

Delivery: 25 MW from solar
Excess: 55 - 25 = 30 MW
Charge: 30 MW for 1 hour = 30 MWh input
Energy Stored: 30 × 0.933 = 27.99 MWh
ΔSOC: 27.99 / 100 = 27.99%
New SOC: 30% + 27.99% = 57.99%
```

**Hour 10:** Battery Approaching Full
```
Solar: 65 MW
SOC: 85%
State: CHARGING

Delivery: 25 MW
Excess: 40 MW
Headroom: (95% - 85%) × 100 = 10 MWh
Max Input: 10 / 0.933 = 10.72 MW
Actual Charge: 10.72 MW
Energy Stored: 10 MWh (fills to 95%)
Wastage: 40 - 10.72 = 29.28 MW
New SOC: 95% (full)
```

**Hour 11-14:** Battery Full - Peak Wastage
```
Solar: 67 MW (peak capacity)
SOC: 95%
State: IDLE

Delivery: 25 MW
Excess: 42 MW
Cannot Charge: Battery full
Wastage: 42 MW per hour
Total Wastage (4 hours): 168 MWh
```

**Daily Summary:**
- Battery charged rapidly in morning
- Reached full capacity by hour 10
- Significant solar wastage during peak hours (11-14)
- Battery remained full for afternoon delivery support
- Total wastage: ~200 MWh
- Recommendation: Larger battery or additional load

---

### 5.3 Example 3: Low Solar Day (Heavy Battery Reliance)

**Scenario:** Cloudy day with reduced solar generation
**Battery:** 200 MWh, starting at 70% SOC

**Key Hours:**

**Hour 9:** Limited Solar, Need Battery
```
Solar: 15 MW
SOC: 70%
State: IDLE
Cycles: 0.0

Total Available: 15 + min(130, 200) = 215 MW
Can Deliver: YES

Deficit: 25 - 15 = 10 MW
Battery Discharge: 10 MW
Battery Energy Used: 10 / 0.933 = 10.72 MWh
ΔSOC: 10.72 / 200 = 5.36%
New SOC: 70% - 5.36% = 64.64%
State: IDLE → DISCHARGING (+0.5 cycles)
Delivery: 25 MW
```

**Hour 15:** Continued Battery Support
```
Solar: 12 MW
SOC: 45%
State: DISCHARGING
Cycles: 1.5

Deficit: 13 MW
Battery Discharge: 13 MW
Battery Energy Used: 13.93 MWh
ΔSOC: 6.97%
New SOC: 45% - 6.97% = 38.03%
Delivery: 25 MW
```

**Hour 18:** Approaching Cycle Limit
```
Solar: 8 MW
SOC: 28%
State: DISCHARGING
Cycles: 1.5

Deficit: 17 MW
Available: (28% - 5%) × 200 = 46 MWh
Can Discharge: 17 MW
Cycles After: 1.5 (still discharging, no transition)
New SOC: 28% - 8.5% = 19.5%
Delivery: 25 MW
```

**Hour 19:** Cycle Limit Risk
```
Solar: 5 MW
SOC: 19.5%
State: DISCHARGING
Cycles: 1.5

Deficit: 20 MW
Available: (19.5% - 5%) × 200 = 29 MWh
Theoretically Can: YES

Discharge: 20 MW
If transitions to IDLE after: Cycles = 2.0 (limit)
Decision: Discharge but monitor for next hour
New SOC: 9.3%
Delivery: 25 MW
```

**Hour 20:** Cycle Limit Reached
```
Solar: 2 MW
SOC: 9.3%
State: DISCHARGING → IDLE (+0.5 cycles)
Cycles: 2.0

Cannot discharge further (cycle limit)
Cannot deliver
Minimal solar for charging: 2 MW
Charge: 2 MW
New SOC: 9.3% + 1.24% = 10.54%
Delivery: 0 MW
```

**Daily Summary:**
- Heavy reliance on battery throughout day
- SOC dropped from 70% to 10.54% (-59.46%)
- Cycle limit reached by evening
- Low solar prevented battery recharging
- Risk: Low SOC for next day
- Recommendation: Consider load curtailment on cloudy days

---

### 5.4 Example 4: Cycle Limit Day (2.0 Cycles Reached Early)

**Scenario:** Multiple charge/discharge cycles deplete daily limit
**Battery:** 150 MWh, starting at 50% SOC

**Critical Hours:**

**Hour 6-10:** Morning Charge Cycle
```
State Progression: IDLE → CHARGING (0.5) → ... → CHARGING → IDLE (1.0)
SOC: 50% → 85%
```

**Hour 12-16:** Afternoon Discharge Cycle
```
State Progression: IDLE → DISCHARGING (1.5) → ... → DISCHARGING → IDLE (2.0)
SOC: 85% → 55%
Cycle Limit Reached at Hour 16
```

**Hour 17:** Resources Available but Blocked
```
Solar: 18 MW
SOC: 55%
Cycles: 2.0
State: IDLE

Deficit: 7 MW
Available Energy: (55% - 5%) × 150 = 75 MWh
Available Power: min(75, 150) = 75 MW
Total Available: 18 + 75 = 93 MW ≥ 25 MW

BUT: Daily Cycles = 2.0 (LIMIT)
can_cycle('DISCHARGING') = FALSE

Result:
  Delivery: 0 MW (blocked by cycle limit)
  Charge: 18 MW with available solar
  New SOC: 55% + 11.2% = 66.2%
  State: IDLE → CHARGING (would add 0.5 cycles)

Implementation Decision:
  Allow charging without cycle counting
  (Only discharge transitions count toward limit)
```

**Hour 18-23:** Remaining Hours
```
State: CHARGING (continue charging with available solar)
Action: Cannot discharge (cycle limit)
Result: Battery charges but cannot support delivery
```

**Lessons Learned:**
1. Cycle limit constrains operational flexibility
2. Battery has energy but cannot use it
3. Solar charging still possible (doesn't count toward discharge limit)
4. System "locks out" battery discharge for rest of day
5. Trade-off: Battery protection vs. delivery capability

---

## 6. State Machine Documentation

### 6.1 State Definitions

#### 6.1.1 IDLE State

**Definition:** Battery is neither charging nor discharging

**Characteristics:**
- No energy flow in or out
- SOC remains constant
- Can transition to CHARGING or DISCHARGING
- Default/resting state

**Entry Conditions:**
- System startup
- Completed charging session
- Completed discharging session
- No solar or load requirements

**Exit Conditions:**
- Solar available for charging
- Battery needed for discharge

#### 6.1.2 CHARGING State

**Definition:** Battery is accepting energy from solar

**Characteristics:**
- Energy flows INTO battery
- SOC increases over time
- Efficiency: 93.3% (7% loss)
- Limited by C-rate and headroom

**Entry Conditions:**
- Excess solar available
- SOC < 95%
- Previous state: IDLE or continuing

**Exit Conditions:**
- No more excess solar
- SOC reaches 95%
- Battery needed for discharge

#### 6.1.3 DISCHARGING State

**Definition:** Battery is providing energy to load

**Characteristics:**
- Energy flows OUT of battery
- SOC decreases over time
- Efficiency: Output requires battery_energy / 0.933
- Limited by C-rate and available energy

**Entry Conditions:**
- Solar insufficient for delivery
- Solar + battery ≥ 25 MW
- SOC > 5%
- Daily cycles < 2.0
- Previous state: IDLE or continuing

**Exit Conditions:**
- No longer needed for delivery
- SOC reaches 5%
- Daily cycle limit reached

### 6.2 Cycle Counting Methodology

#### 6.2.1 Core Principle

**Cycles are counted based on STATE TRANSITIONS, not energy throughput**

**Rule:** Each transition between states counts as 0.5 cycles

**Rationale:**
- Tracks physical stress on battery
- Correlates with degradation
- Independent of energy amount
- Simple to implement and understand

#### 6.2.2 Cycle Counting Rules

| Transition | From State | To State | Cycle Count |
|------------|------------|----------|-------------|
| Start Charge | IDLE | CHARGING | +0.5 |
| Stop Charge | CHARGING | IDLE | +0.5 |
| Start Discharge | IDLE | DISCHARGING | +0.5 |
| Stop Discharge | DISCHARGING | IDLE | +0.5 |
| Direct Switch | CHARGING | DISCHARGING | +1.0 |
| Direct Switch | DISCHARGING | CHARGING | +1.0 |
| No Change | Any | Same | 0 |

**Complete Cycle Examples:**

**Example 1: Charge-Discharge Cycle**
```
IDLE → CHARGING → IDLE → DISCHARGING → IDLE
 0.0      0.5        1.0       1.5        2.0 cycles
```

**Example 2: Multiple Charge Sessions**
```
IDLE → CHARGING → IDLE → CHARGING → IDLE
 0.0      0.5        1.0       1.5        2.0 cycles
```

**Example 3: Direct Transition (Rare)**
```
IDLE → CHARGING → DISCHARGING → IDLE
 0.0      0.5           1.5        2.0 cycles
```

#### 6.2.3 Daily Reset Logic

**Reset Rule:** Cycles reset to 0.0 at start of each day (hour % 24 == 0)

**Implementation:**
```python
if hour % 24 == 0:
    daily_cycles = 0.0
```

**Example:**
```
Hour 23: State = IDLE, Cycles = 2.0
Hour 24 (Day 2, Hour 0): Cycles reset to 0.0
```

#### 6.2.4 Cycle Limit Enforcement

**Maximum:** 2.0 cycles per day

**Check Before Transition:**
```python
def can_cycle(new_state):
    if new_state == current_state:
        return True  # No transition

    # Calculate potential cycle addition
    if (current_state == 'CHARGING' and new_state == 'DISCHARGING') or \
       (current_state == 'DISCHARGING' and new_state == 'CHARGING'):
        cycle_addition = 1.0
    else:
        cycle_addition = 0.5

    # Check if would exceed limit
    if daily_cycles + cycle_addition > 2.0:
        return False

    return True
```

**Impact of Limit:**
- Prevents further transitions once 2.0 reached
- Battery may have energy but cannot discharge
- Protects battery from excessive cycling
- Forces operational planning

### 6.3 State Transition Diagram

```
                    START
                      │
                      ↓
                  [IDLE]
                   │  │  │
      Excess Solar│  │  │Need Battery
                   ↓  │  ↓
             [CHARGING]│[DISCHARGING]
                   │  │  │
    No More Solar │  │  │No More Need
           Battery│  │  │or Limit
              Full│  │  │Reached
                   ↓  ↓  ↓
                  [IDLE]
                      │
                      ↓
                 (Continue)
```

**Detailed Transitions:**

```
IDLE State
    │
    ├──→ [Excess Solar AND SOC < 95%]
    │    └──→ CHARGING State (+0.5 cycles)
    │
    ├──→ [Need Battery AND SOC > 5% AND Cycles < 2.0]
    │    └──→ DISCHARGING State (+0.5 cycles)
    │
    └──→ [No Action Needed]
         └──→ Remain IDLE (0 cycles)

CHARGING State
    │
    ├──→ [No More Excess OR SOC = 95%]
    │    └──→ IDLE State (+0.5 cycles, total 1.0)
    │
    ├──→ [Continue Excess Solar]
    │    └──→ Remain CHARGING (0 cycles)
    │
    └──→ [Need Battery Immediately]
         └──→ DISCHARGING State (+1.0 cycles, rare)

DISCHARGING State
    │
    ├──→ [No More Need OR SOC = 5% OR Cycles = 2.0]
    │    └──→ IDLE State (+0.5 cycles, total may = 2.0)
    │
    ├──→ [Continue Discharge Need]
    │    └──→ Remain DISCHARGING (0 cycles)
    │
    └──→ [Excess Solar Available]
         └──→ CHARGING State (+1.0 cycles, rare)
```

### 6.4 State Machine Examples

#### Example 1: Standard Day Progression

```
Hour | Solar | Need | State | Action | Cycles
-----|-------|------|-------|--------|-------
00   | 0     | No   | IDLE  | None   | 0.0
06   | 10    | No   | IDLE→CHARGING | Charge | 0.5
07   | 20    | No   | CHARGING | Charge | 0.5
10   | 30    | Yes  | CHARGING | Del+Chg | 0.5
12   | 25    | Yes  | CHARGING→IDLE | Deliver | 1.0
14   | 20    | Yes  | IDLE→DISCHARGING | Del+Disch | 1.5
17   | 5     | No   | DISCHARGING→IDLE | Stop | 2.0
20   | 0     | No   | IDLE  | None   | 2.0
```

#### Example 2: Rapid Transitions

```
Hour | Solar | Need | State | Action | Cycles
-----|-------|------|-------|--------|-------
08   | 26    | Yes  | IDLE→CHARGING | Del+Chg | 0.5
09   | 24    | Yes  | CHARGING→DISCHARGING | Del+Disch | 1.5
10   | 26    | Yes  | DISCHARGING→CHARGING | Del+Chg | 2.5 ERROR!
```

**Error:** Transition from DISCHARGING to CHARGING adds 1.0 cycles, exceeding limit
**Solution:** Must go through IDLE state or avoid rapid reversals

---

## 7. Mathematical Formulas Reference

### 7.1 Resource Availability Calculations

#### 7.1.1 Solar Availability
```
Solar_Available_MW = Current_Solar_Generation_MW
Range: [0, 67] MW
```

#### 7.1.2 Battery Energy Availability
```
Battery_Usable_Energy_MWh = (Current_SOC - MIN_SOC) × Battery_Capacity_MWh
Battery_Usable_Energy_MWh = (SOC - 0.05) × Capacity

Where:
  Current_SOC ∈ [0.05, 0.95]
  Battery_Capacity_MWh ∈ [10, 500]

Example:
  SOC = 60%, Capacity = 100 MWh
  Usable = (0.60 - 0.05) × 100 = 55 MWh
```

#### 7.1.3 Battery Power Availability
```
Battery_Power_MW = min(Battery_Usable_Energy_MWh, Battery_Capacity_MWh × C_Rate_Discharge)

Where:
  C_Rate_Discharge = 1.0 (can discharge at 1C rate)

Example:
  Usable Energy = 55 MWh
  Max Power = min(55, 100 × 1.0) = 55 MW

Edge Case (Low SOC):
  Usable Energy = 2 MWh
  Max Power = min(2, 100 × 1.0) = 2 MW (energy limited)
```

#### 7.1.4 Total Available Power
```
Total_Available_MW = Solar_Available_MW + Battery_Power_MW

Deliverability_Check:
  IF Total_Available_MW ≥ 25 MW THEN Can_Deliver = TRUE
  ELSE Can_Deliver = FALSE
```

### 7.2 Efficiency Calculations

#### 7.2.1 Charging Efficiency (Solar → Battery)

**One-Way Efficiency:** 93.3% (0.933)

**Energy Stored Calculation:**
```
Energy_Input_MWh = Solar_Excess_MW × 1_hour
Energy_Stored_MWh = Energy_Input_MWh × η_charge
Energy_Stored_MWh = Energy_Input_MWh × 0.933

Energy_Loss_MWh = Energy_Input_MWh × (1 - η_charge)
Energy_Loss_MWh = Energy_Input_MWh × 0.067

Example:
  Input = 10 MWh
  Stored = 10 × 0.933 = 9.33 MWh
  Loss = 10 × 0.067 = 0.67 MWh
  Verification: 9.33 + 0.67 = 10 ✓
```

#### 7.2.2 Discharging Efficiency (Battery → Load)

**One-Way Efficiency:** 93.3% (0.933)

**Battery Energy Required:**
```
Energy_Output_Required_MWh = Load_Deficit_MW × 1_hour
Battery_Energy_Needed_MWh = Energy_Output_Required_MWh / η_discharge
Battery_Energy_Needed_MWh = Energy_Output_Required_MWh / 0.933

Energy_Loss_MWh = Battery_Energy_Needed_MWh - Energy_Output_Required_MWh

Example:
  Required Output = 10 MWh
  Battery Energy Needed = 10 / 0.933 = 10.72 MWh
  Loss = 10.72 - 10 = 0.72 MWh
```

#### 7.2.3 Round-Trip Efficiency Verification

**Round-Trip Efficiency:** 87% (0.87)

**Complete Cycle:**
```
Charge Then Discharge:
  Input → Battery: E_in × 0.933 = E_stored
  Battery → Output: E_stored × 0.933 = E_out

  E_out = (E_in × 0.933) × 0.933
  E_out = E_in × 0.933²
  E_out = E_in × 0.8705 ≈ E_in × 0.87

Example:
  Store 100 MWh:
    Charge: 100 × 0.933 = 93.3 MWh stored
    Discharge: 93.3 × 0.933 = 87 MWh output
  Round-trip: 87 / 100 = 87% ✓
```

### 7.3 SOC Impact Calculations

#### 7.3.1 SOC Increase (Charging)
```
Energy_Stored_MWh = Energy_Input_MWh × 0.933
Δ_SOC_Percent = (Energy_Stored_MWh / Battery_Capacity_MWh) × 100
New_SOC_Percent = Old_SOC_Percent + Δ_SOC_Percent

Constraint: New_SOC_Percent ≤ 95%

Example:
  Input = 20 MWh, Capacity = 100 MWh, Old SOC = 50%
  Stored = 20 × 0.933 = 18.66 MWh
  Δ_SOC = (18.66 / 100) × 100 = 18.66%
  New SOC = 50% + 18.66% = 68.66%
```

#### 7.3.2 SOC Decrease (Discharging)
```
Energy_Output_MWh = Deficit_MW × 1_hour
Battery_Energy_Used_MWh = Energy_Output_MWh / 0.933
Δ_SOC_Percent = (Battery_Energy_Used_MWh / Battery_Capacity_MWh) × 100
New_SOC_Percent = Old_SOC_Percent - Δ_SOC_Percent

Constraint: New_SOC_Percent ≥ 5%

Example:
  Output = 15 MWh, Capacity = 100 MWh, Old SOC = 60%
  Used = 15 / 0.933 = 16.08 MWh
  Δ_SOC = (16.08 / 100) × 100 = 16.08%
  New SOC = 60% - 16.08% = 43.92%
```

#### 7.3.3 Headroom Calculation (Maximum Chargeable)
```
Headroom_MWh = (MAX_SOC - Current_SOC) × Battery_Capacity_MWh
Headroom_MWh = (0.95 - SOC) × Capacity

Max_Input_MWh = Headroom_MWh / η_charge
Max_Input_MWh = Headroom_MWh / 0.933

Example:
  SOC = 80%, Capacity = 100 MWh
  Headroom = (0.95 - 0.80) × 100 = 15 MWh
  Max Input = 15 / 0.933 = 16.08 MWh
```

### 7.4 Power Constraint Calculations

#### 7.4.1 Charge Power Limit
```
Max_Charge_Power_MW = Battery_Capacity_MWh × C_Rate_Charge
Max_Charge_Power_MW = Capacity × 1.0

Effective_Charge_MW = min(Solar_Excess_MW, Max_Charge_Power_MW, Headroom_Limited_MW)

Where:
  Headroom_Limited_MW = Headroom_MWh / η_charge / 1_hour

Example:
  Capacity = 100 MWh, Excess = 150 MW, Headroom = 10 MWh
  Max Charge Power = 100 × 1.0 = 100 MW
  Headroom Limited = 10 / 0.933 / 1 = 10.72 MW
  Effective = min(150, 100, 10.72) = 10.72 MW
```

#### 7.4.2 Discharge Power Limit
```
Max_Discharge_Power_MW = Battery_Capacity_MWh × C_Rate_Discharge
Max_Discharge_Power_MW = Capacity × 1.0

Effective_Discharge_MW = min(Deficit_MW, Max_Discharge_Power_MW, Available_Energy_Limited_MW)

Where:
  Available_Energy_Limited_MW = Available_Energy_MWh / 1_hour

Example:
  Capacity = 100 MWh, Deficit = 30 MW, Available = 5 MWh
  Max Discharge Power = 100 × 1.0 = 100 MW
  Energy Limited = 5 / 1 = 5 MW
  Effective = min(30, 100, 5) = 5 MW (energy limited)
```

### 7.5 Cycle Counting Formulas

#### 7.5.1 Cycle Addition
```
IF State_New ≠ State_Old THEN
    IF (State_Old = 'CHARGING' AND State_New = 'DISCHARGING') OR
       (State_Old = 'DISCHARGING' AND State_New = 'CHARGING') THEN
        Cycle_Addition = 1.0  (direct reversal)
    ELSE IF State_Old ≠ 'IDLE' OR State_New ≠ 'IDLE' THEN
        Cycle_Addition = 0.5  (normal transition)
    ELSE
        Cycle_Addition = 0  (no transition)
    END IF

    Daily_Cycles_New = Daily_Cycles_Old + Cycle_Addition
ELSE
    Daily_Cycles_New = Daily_Cycles_Old  (no change)
END IF

Constraint: Daily_Cycles_New ≤ 2.0
```

#### 7.5.2 Can Cycle Check
```
FUNCTION can_cycle(target_state):
    IF target_state = current_state THEN
        RETURN TRUE  (no transition needed)
    END IF

    # Calculate potential cycle addition
    IF (current_state = 'CHARGING' AND target_state = 'DISCHARGING') OR
       (current_state = 'DISCHARGING' AND target_state = 'CHARGING') THEN
        potential_addition = 1.0
    ELSE
        potential_addition = 0.5
    END IF

    # Check if would exceed limit
    IF daily_cycles + potential_addition > 2.0 THEN
        RETURN FALSE  (would exceed limit)
    ELSE
        RETURN TRUE  (within limit)
    END IF
END FUNCTION
```

### 7.6 Degradation Calculation
```
Total_Lifetime_Cycles = Σ(Daily_Cycles) over all days
Degradation_Percent = Total_Lifetime_Cycles × Degradation_Per_Cycle
Degradation_Percent = Total_Lifetime_Cycles × 0.15%

Effective_Capacity_MWh = Nominal_Capacity_MWh × (1 - Degradation_Percent / 100)

Example:
  Total Cycles = 730 (2 years @ 1 cycle/day average)
  Degradation = 730 × 0.15% = 109.5%... ERROR!

Note: Degradation model needs review for long-term accuracy
```

---

## 8. Code Integration Points

### 8.1 Core Simulation Function

**File:** `src/battery_simulator.py`
**Function:** `simulate_bess_year(battery_capacity, solar_profile, config)`
**Lines:** ~203-360

**Purpose:** Main simulation loop that processes 8,760 hours

**Key Sections:**

#### 8.1.1 Initialization (Lines 203-220)
```python
def simulate_bess_year(battery_capacity, solar_profile, config):
    """
    Simulate battery operation for full year (8760 hours).

    Args:
        battery_capacity: Battery size in MWh
        solar_profile: Pandas Series of solar generation (8760 values)
        config: Configuration dictionary

    Returns:
        DataFrame with hourly results
    """
    # Create battery system
    battery = BatterySystem(
        capacity=battery_capacity,
        initial_soc=config['INITIAL_SOC']
    )

    # Initialize tracking
    results = []
    target_delivery_mw = config['TARGET_DELIVERY_MW']
```

#### 8.1.2 Resource Availability Check (Lines 221-235)
```python
# Calculate battery available power
battery_available_mw = min(
    battery.get_available_energy(),  # Energy constraint
    battery.capacity * battery.c_rate_discharge  # Power constraint
)

# Check if can deliver
can_deliver_resources = (solar_mw + battery_available_mw) >= target_delivery_mw
```

**Integration Point for Third Source:**
```python
# MODIFICATION for third source (e.g., grid):
third_source_mw = get_third_source_power(hour)  # New function
total_available_mw = solar_mw + battery_available_mw + third_source_mw
can_deliver_resources = total_available_mw >= target_delivery_mw
```

#### 8.1.3 Scenario 1: Excess Solar (Lines 240-260)
```python
# Scenario 1: Solar exceeds delivery target
if solar_mw >= target_delivery_mw:
    delivery_this_hour = 'Yes'

    # Calculate excess
    excess_solar = solar_mw - target_delivery_mw

    # Try to charge battery
    if excess_solar > 0 and battery.state != 'DISCHARGING':
        charged = battery.charge(excess_solar)
        if charged > 0 and battery.state == 'IDLE':
            battery.update_state_and_cycles('CHARGING', hour)
        wastage = excess_solar - charged
```

**Integration Point:**
```python
# MODIFICATION for third source:
# Priority: Solar → Battery → Third Source
if solar_mw >= target_delivery_mw:
    delivery_source = 'solar'
    excess = solar_mw - target_delivery_mw
elif (solar_mw + battery_available_mw) >= target_delivery_mw:
    delivery_source = 'solar+battery'
    # ... existing battery logic
elif (solar_mw + battery_available_mw + third_source_mw) >= target_delivery_mw:
    delivery_source = 'solar+battery+third'
    # ... new third source logic
```

#### 8.1.4 Scenario 2: Battery Support (Lines 262-285)
```python
# Scenario 2: Need battery support
elif can_deliver_resources:
    deficit = target_delivery_mw - solar_mw

    if battery.can_cycle('DISCHARGING'):
        discharged = battery.discharge(deficit)

        if discharged >= deficit:
            delivery_this_hour = 'Yes'
            if battery.state != 'DISCHARGING':
                battery.update_state_and_cycles('DISCHARGING', hour)
```

**Integration Point:**
```python
# MODIFICATION for third source:
elif can_deliver_resources:
    deficit = target_delivery_mw - solar_mw

    # Try battery first
    if battery.can_cycle('DISCHARGING') and battery_available_mw > 0:
        discharged_battery = battery.discharge(min(deficit, battery_available_mw))
        remaining_deficit = deficit - discharged_battery
    else:
        discharged_battery = 0
        remaining_deficit = deficit

    # Use third source for remaining deficit
    if remaining_deficit > 0 and third_source_mw > 0:
        discharged_third = min(remaining_deficit, third_source_mw)
        record_third_source_usage(discharged_third)

    # Check if total meets requirement
    if discharged_battery + discharged_third >= deficit:
        delivery_this_hour = 'Yes'
```

### 8.2 Battery System Class

**File:** `src/battery_simulator.py`
**Class:** `BatterySystem`
**Lines:** ~15-200

**Key Methods:**

#### 8.2.1 Charge Method (Lines 45-70)
```python
def charge(self, energy_mwh):
    """
    Charge battery with given energy.

    Args:
        energy_mwh: Energy to charge (MWh)

    Returns:
        Actual energy charged (may be less due to constraints)
    """
    # Check headroom
    headroom = self.get_charge_headroom()

    # Apply efficiency
    energy_stored = min(energy_mwh * self.one_way_efficiency, headroom)

    # Apply C-rate limit
    max_power = self.capacity * self.c_rate_charge
    energy_stored = min(energy_stored, max_power)

    # Update SOC
    self.soc += energy_stored / self.capacity

    return energy_mwh if energy_stored == energy_mwh * self.one_way_efficiency else energy_stored / self.one_way_efficiency
```

**Extension Note:** No modification needed for third source (battery charging logic independent of source)

#### 8.2.2 Discharge Method (Lines 72-95)
```python
def discharge(self, energy_mwh):
    """
    Discharge battery to provide energy.

    Args:
        energy_mwh: Energy requested (MWh output)

    Returns:
        Actual energy discharged (may be less due to constraints)
    """
    # Check available energy
    available = self.get_available_energy()

    # Calculate battery energy needed (accounting for efficiency)
    battery_energy_needed = energy_mwh / self.one_way_efficiency

    # Apply constraints
    energy_used = min(battery_energy_needed, available)

    # Apply C-rate limit
    max_power = self.capacity * self.c_rate_discharge
    energy_used = min(energy_used, max_power)

    # Update SOC
    self.soc -= energy_used / self.capacity

    return energy_used * self.one_way_efficiency
```

**Extension Note:** No modification needed (battery discharge independent of load source)

#### 8.2.3 State & Cycle Management (Lines 90-115)
```python
def update_state_and_cycles(self, new_state, hour):
    """
    Update battery state and track cycles.

    Args:
        new_state: Target state (IDLE/CHARGING/DISCHARGING)
        hour: Current hour (for daily reset)
    """
    # Reset cycles at start of day
    if hour % 24 == 0:
        self.daily_cycles = 0.0

    # Count cycles on state change
    if new_state != self.state:
        if (self.state == 'CHARGING' and new_state == 'DISCHARGING') or \
           (self.state == 'DISCHARGING' and new_state == 'CHARGING'):
            self.daily_cycles += 1.0
        elif self.state != 'IDLE' or new_state != 'IDLE':
            self.daily_cycles += 0.5

    self.state = new_state
    self.total_cycles += self.daily_cycles
```

**Extension Note:** Cycle counting remains tied to battery state only

### 8.3 Decision Logic Entry Points

**File:** `src/battery_simulator.py`
**Function:** `simulate_bess_year`

**Modification Points for Third Source:**

1. **Line ~215:** Add third source availability calculation
2. **Line ~230:** Modify total available power calculation
3. **Line ~265:** Add third source discharge logic
4. **Line ~300:** Track third source usage in results

**Pseudo-code for Integration:**

```python
# After line 215 - Add third source
third_source_mw = get_third_source_power(hour, config)
third_source_available = third_source_mw > 0

# Modify line 230 - Total available
total_available_mw = solar_mw + battery_available_mw + third_source_mw

# After line 265 - Priority discharge
deficit = target_delivery_mw - solar_mw
sources_used = []

# Priority 1: Battery
if battery.can_cycle('DISCHARGING') and deficit > 0:
    from_battery = battery.discharge(min(deficit, battery_available_mw))
    deficit -= from_battery
    sources_used.append(('battery', from_battery))

# Priority 2: Third Source
if third_source_available and deficit > 0:
    from_third = min(deficit, third_source_mw)
    deficit -= from_third
    sources_used.append(('third', from_third))

# Check delivery success
if deficit <= 0:
    delivery_this_hour = 'Yes'
```

---

## 9. Extension Framework (Adding Third Power Source)

### 9.1 System Architecture for Third Source

**Design Principles:**
1. **Modularity:** Third source as independent component
2. **Priority System:** Define clear dispatch order
3. **Constraint Management:** Each source has own constraints
4. **State Independence:** Third source doesn't affect battery cycles
5. **Backward Compatibility:** Existing logic remains functional

### 9.2 Third Source Types & Characteristics

#### 9.2.1 Grid Connection

**Characteristics:**
- Always available (high reliability)
- Unlimited power (within connection limit)
- Cost per MWh (operating expense)
- No storage component
- No efficiency loss
- Instant response

**Parameters:**
```python
GRID_CONFIG = {
    'available': True,
    'max_power_mw': 50,  # Connection limit
    'cost_per_mwh': 80,  # $/MWh
    'availability_factor': 0.99,  # 99% uptime
    'response_time_hours': 0,  # Instant
    'constraints': ['cost_limit', 'daily_energy_cap']
}
```

#### 9.2.2 Wind Generation

**Characteristics:**
- Variable availability (weather dependent)
- No fuel cost
- Intermittent like solar
- No storage
- Forecasting uncertainty
- Complementary to solar (often peaks at night)

**Parameters:**
```python
WIND_CONFIG = {
    'capacity_mw': 40,
    'capacity_factor': 0.35,  # Average
    'profile_data': wind_hourly_profile,  # 8760 values
    'forecasting_error': 0.15,  # ±15%
    'curtailment_allowed': True
}
```

#### 9.2.3 Diesel Generator

**Characteristics:**
- On-demand availability
- High fuel cost
- Startup time required
- Maintenance cycles
- Emissions constraints
- Backup/emergency use

**Parameters:**
```python
DIESEL_CONFIG = {
    'capacity_mw': 30,
    'fuel_cost_per_mwh': 150,
    'startup_time_hours': 0.25,  # 15 minutes
    'min_run_time_hours': 2,
    'max_starts_per_day': 3,
    'emissions_limit_kg_co2': 50000  # Daily
}
```

### 9.3 Modified Decision Tree (3-Source System)

```
START (Every Hour)
    │
    ├─→ Read All Source States
    │   ├─ Solar Generation (MW)
    │   ├─ Battery SOC & State
    │   ├─ Battery Daily Cycles
    │   └─ Third Source Availability & Power
    │
    ├─→ Calculate Total Available Resources
    │   ├─ Solar Available = Current Solar
    │   ├─ Battery Available = min(Usable Energy, C-Rate Power)
    │   ├─ Third Source Available = get_third_source_power()
    │   └─ Total Available = Solar + Battery + Third Source
    │
    ├─→ Check Deliverability
    │   │
    │   ├─→ [Total Available < 25 MW]?
    │   │   └─→ YES → SCENARIO A: Insufficient Resources (all sources)
    │   │
    │   ├─→ [Solar ≥ 25 MW]?
    │   │   └─→ YES → SCENARIO 1: Excess Solar (unchanged)
    │   │
    │   ├─→ [Solar + Battery ≥ 25 MW]?
    │   │   │
    │   │   ├─→ [Daily Cycles < 2.0]?
    │   │   │   └─→ YES → SCENARIO 2: Solar + Battery (unchanged)
    │   │   │   └─→ NO → Check Third Source
    │   │   │
    │   │   └─→ Cannot use battery → Check Third Source
    │   │
    │   ├─→ [Solar + Battery + Third ≥ 25 MW]?
    │   │   └─→ YES → SCENARIO B: Multi-Source Delivery
    │   │
    │   └─→ Otherwise → SCENARIO A: Insufficient Resources
    │
    ├─→ Execute Delivery with Source Priority
    │   │
    │   └─→ Priority Order:
    │       1. Solar (free, zero emissions)
    │       2. Battery (stored solar, no cost)
    │       3. Third Source (cost/emissions consideration)
    │
    ├─→ Update All System States
    │   ├─ Record Delivery & Sources Used
    │   ├─ Update Battery SOC & State
    │   ├─ Update Battery Cycles
    │   ├─ Record Third Source Usage
    │   ├─ Track Costs & Emissions
    │   └─ Record Wastage (if any)
    │
    └─→ END (Proceed to Next Hour)
```

### 9.4 New Scenarios with Third Source

#### 9.4.1 Scenario A: Insufficient Resources (All Sources)

**Trigger:** Solar + Battery + Third Source < 25 MW

**Business Logic:**
```
Total_Available = Solar + Battery_Available + Third_Source_Available

IF Total_Available < 25 MW THEN
    Delivery = 0 MW
    Deficit = 25 - Total_Available

    # Attempt charging if solar available
    IF Solar > 0 THEN
        Charge_Battery(Solar)
    END IF

    # Third source remains unused
    Record_Deficit(Deficit, "Insufficient total resources")
END IF
```

**Example:**
```
Solar: 5 MW
Battery: 3 MW available (low SOC)
Grid: 15 MW available
Total: 5 + 3 + 15 = 23 MW < 25 MW

Result: No delivery, charge battery with 5 MW solar
```

#### 9.4.2 Scenario B: Multi-Source Delivery

**Trigger:** Need multiple sources to meet 25 MW target

**Priority Dispatch Logic:**
```
Deficit = 25 MW
Sources_Used = []

# Step 1: Use all available solar
From_Solar = min(Solar_MW, Deficit)
Deficit -= From_Solar
IF From_Solar > 0 THEN
    Sources_Used.append(('Solar', From_Solar))
END IF

# Step 2: Use battery if needed and available
IF Deficit > 0 AND Battery_Can_Cycle AND Battery_Available > 0 THEN
    From_Battery = min(Deficit, Battery_Available)
    Battery.discharge(From_Battery)
    Deficit -= From_Battery
    Sources_Used.append(('Battery', From_Battery))
END IF

# Step 3: Use third source if still needed
IF Deficit > 0 AND Third_Source_Available > 0 THEN
    From_Third = min(Deficit, Third_Source_Available)
    Use_Third_Source(From_Third)
    Deficit -= From_Third
    Sources_Used.append(('Third', From_Third))
END IF

# Step 4: Check delivery success
IF Deficit == 0 THEN
    Delivery = 25 MW
    Record_Sources(Sources_Used)
ELSE
    Delivery = 0 MW
    Record_Failure("Dispatch error")
END IF
```

**Example 1: Solar + Grid**
```
Solar: 15 MW
Battery: 20 MW available, BUT cycles = 2.0 (blocked)
Grid: 50 MW available
Target: 25 MW

Dispatch:
  From Solar: 15 MW
  From Battery: 0 MW (cycle limit)
  From Grid: 10 MW
  Total: 25 MW ✓

Cost: 10 MWh × $80/MWh = $800
```

**Example 2: Solar + Battery + Grid**
```
Solar: 10 MW
Battery: 8 MW available, cycles = 1.5
Grid: 50 MW available
Target: 25 MW

Dispatch:
  From Solar: 10 MW
  From Battery: 8 MW (uses remaining capacity)
  From Grid: 7 MW
  Total: 25 MW ✓

Battery:
  State: IDLE → DISCHARGING (+0.5 cycles = 2.0)
  Next hour cannot use battery (limit reached)

Cost: 7 MWh × $80/MWh = $560
```

**Example 3: Solar + Battery (Third Not Needed)**
```
Solar: 12 MW
Battery: 20 MW available, cycles = 0.5
Grid: 50 MW available
Target: 25 MW

Dispatch:
  From Solar: 12 MW
  From Battery: 13 MW
  From Grid: 0 MW (not needed)
  Total: 25 MW ✓

Cost: $0 (no grid usage)
Note: Existing Scenario 2 logic, third source not activated
```

### 9.5 Implementation Checklist

**Phase 1: Configuration**
- [ ] Add third source parameters to `config.py`
- [ ] Define source priority order
- [ ] Set cost/emission limits
- [ ] Configure availability constraints

**Phase 2: Data Sources**
- [ ] Create third source profile (if variable like wind)
- [ ] Implement `get_third_source_power(hour, config)` function
- [ ] Add availability checking logic
- [ ] Handle forecasting/uncertainty

**Phase 3: Decision Logic**
- [ ] Modify resource availability calculation (Line ~230)
- [ ] Implement priority dispatch algorithm
- [ ] Add third source discharge logic
- [ ] Update delivery success criteria

**Phase 4: Tracking & Reporting**
- [ ] Add third source columns to results DataFrame
- [ ] Track source contribution per hour
- [ ] Calculate costs and emissions
- [ ] Update metrics calculations

**Phase 5: Constraints**
- [ ] Implement cost limits (daily/annual)
- [ ] Add emission constraints
- [ ] Handle startup/shutdown rules (if applicable)
- [ ] Enforce energy caps

**Phase 6: Testing**
- [ ] Test each scenario with third source
- [ ] Verify priority dispatch order
- [ ] Validate cost calculations
- [ ] Check edge cases (source failures)

### 9.6 Code Template for Third Source

**File:** `src/third_source.py` (new file)

```python
"""
Third Power Source Module
Supports grid, wind, diesel, or other power sources
"""

class ThirdPowerSource:
    def __init__(self, source_type, config):
        """
        Initialize third power source.

        Args:
            source_type: 'grid', 'wind', 'diesel', etc.
            config: Source-specific configuration
        """
        self.source_type = source_type
        self.config = config
        self.daily_usage = 0
        self.daily_cost = 0
        self.daily_starts = 0

    def get_available_power(self, hour):
        """
        Get available power from source at given hour.

        Args:
            hour: Hour of year (0-8759)

        Returns:
            Available power in MW
        """
        if self.source_type == 'grid':
            return self._get_grid_power(hour)
        elif self.source_type == 'wind':
            return self._get_wind_power(hour)
        elif self.source_type == 'diesel':
            return self._get_diesel_power(hour)
        else:
            return 0

    def use_power(self, power_mw, hour):
        """
        Use power from source and track usage.

        Args:
            power_mw: Power to use (MW)
            hour: Current hour

        Returns:
            Actual power used and cost
        """
        # Check availability
        available = self.get_available_power(hour)
        actual_power = min(power_mw, available)

        # Calculate cost
        cost = actual_power * self.config['cost_per_mwh']

        # Track usage
        self.daily_usage += actual_power
        self.daily_cost += cost

        # Reset daily counters at midnight
        if hour % 24 == 0:
            self.daily_usage = 0
            self.daily_cost = 0
            self.daily_starts = 0

        return actual_power, cost

    def _get_grid_power(self, hour):
        """Get available grid power."""
        max_power = self.config['max_power_mw']
        availability = self.config['availability_factor']

        # Simple availability check (could be enhanced with outage modeling)
        import random
        if random.random() < availability:
            return max_power
        else:
            return 0

    def _get_wind_power(self, hour):
        """Get available wind power from profile."""
        profile = self.config['profile_data']
        return profile[hour % 8760]  # Handle multi-year simulation

    def _get_diesel_power(self, hour):
        """Get available diesel power with constraints."""
        if self.daily_starts >= self.config['max_starts_per_day']:
            return 0  # Reached daily start limit

        return self.config['capacity_mw']
```

**Integration into simulate_bess_year:**

```python
# In simulate_bess_year function initialization
if config.get('THIRD_SOURCE_ENABLED', False):
    third_source = ThirdPowerSource(
        source_type=config['THIRD_SOURCE_TYPE'],
        config=config['THIRD_SOURCE_CONFIG']
    )
else:
    third_source = None

# In hourly loop, after battery calculations
if third_source:
    third_source_mw = third_source.get_available_power(hour)
    total_available_mw = solar_mw + battery_available_mw + third_source_mw
else:
    third_source_mw = 0
    total_available_mw = solar_mw + battery_available_mw

# In delivery logic, after battery discharge
if deficit > 0 and third_source:
    from_third, cost_third = third_source.use_power(deficit, hour)
    deficit -= from_third
    # Record third source usage
    third_source_usage = from_third
    third_source_cost = cost_third
else:
    third_source_usage = 0
    third_source_cost = 0
```

### 9.7 Metrics Extensions

**New Metrics to Track:**

1. **Source Contribution:**
   ```
   Solar_Contribution_Percent = (Energy_From_Solar / Total_Energy_Delivered) × 100
   Battery_Contribution_Percent = (Energy_From_Battery / Total_Energy_Delivered) × 100
   Third_Source_Contribution_Percent = (Energy_From_Third / Total_Energy_Delivered) × 100
   ```

2. **Operating Costs:**
   ```
   Total_Operating_Cost = Σ(Third_Source_Usage_MWh × Cost_Per_MWh)
   Cost_Per_Delivered_MWh = Total_Operating_Cost / Total_Delivered_MWh
   ```

3. **Emissions:**
   ```
   Total_Emissions_kg_CO2 = Third_Source_Usage_MWh × Emission_Factor_kg_CO2_per_MWh
   Emission_Intensity = Total_Emissions / Total_Delivered_MWh
   ```

4. **Renewable Fraction:**
   ```
   Renewable_Fraction = (Solar + Battery) / (Solar + Battery + Third_Source)
   ```

---

## 10. Troubleshooting & Edge Cases

### 10.1 Common Issues

#### 10.1.1 No Delivery Despite Available Resources

**Symptom:** System shows resources available but doesn't deliver

**Possible Causes:**

1. **Cycle Limit Reached**
   ```
   Check: Daily_Cycles ≥ 2.0
   Solution: Wait for next day reset
   Verification: Check can_cycle('DISCHARGING') returns FALSE
   ```

2. **SOC at Minimum**
   ```
   Check: SOC ≤ 5%
   Solution: Charge battery before delivering
   Verification: Available_Energy = 0
   ```

3. **State Transition Blocked**
   ```
   Check: Battery in wrong state
   Solution: Transition through IDLE first
   Verification: Check state transition would add >0.5 cycles
   ```

#### 10.1.2 Excessive Solar Wastage

**Symptom:** High wastage percentage (>20%)

**Possible Causes:**

1. **Battery Too Small**
   ```
   Check: Battery reaches 95% SOC early in day
   Solution: Increase battery capacity in optimization
   Analysis: Review SOC profile, identify when full
   ```

2. **Battery Already Full**
   ```
   Check: SOC = 95% during peak solar hours
   Solution: Discharge battery earlier (if possible)
   Alternative: Add third power sink or larger load
   ```

3. **Insufficient Load**
   ```
   Check: Solar > 25 MW for many hours, no battery headroom
   Solution: Increase delivery target or add additional loads
   ```

#### 10.1.3 Rapid SOC Depletion

**Symptom:** SOC drops quickly, approaching 5% limit

**Possible Causes:**

1. **Low Solar Day**
   ```
   Check: Solar profile shows low generation
   Solution: Expected behavior, system working correctly
   Prevention: Ensure adequate battery size for cloudy days
   ```

2. **Efficiency Losses**
   ```
   Check: Verify efficiency calculations (93.3% one-way)
   Issue: Each discharge uses Energy / 0.933 from battery
   Example: 10 MW output requires 10.72 MWh from battery
   ```

3. **Excessive Discharge**
   ```
   Check: Multiple discharge hours without recharge
   Solution: Reduce delivery hours or increase battery size
   ```

#### 10.1.4 Cycle Limit Reached Too Early

**Symptom:** Daily cycles = 2.0 before evening, missing delivery opportunities

**Possible Causes:**

1. **Multiple Charge/Discharge Cycles**
   ```
   Check: Count state transitions in day
   Example:
     IDLE → CHARGING (0.5)
     CHARGING → IDLE (1.0)
     IDLE → DISCHARGING (1.5)
     DISCHARGING → IDLE (2.0) ← Limit reached
   Solution: Optimize cycle usage, avoid unnecessary transitions
   ```

2. **Direct State Reversals**
   ```
   Check: CHARGING → DISCHARGING or reverse (1.0 cycles)
   Issue: Rare but possible, consumes 1.0 cycles at once
   Solution: Go through IDLE state to use 0.5 + 0.5
   ```

3. **Battery Size Too Small**
   ```
   Check: Small battery depletes quickly, requires multiple cycles
   Solution: Increase battery capacity
   Analysis: Larger battery = fewer cycles needed per day
   ```

### 10.2 Edge Case Scenarios

#### 10.2.1 Zero Solar for Extended Period (Multi-Day Cloudy)

**Scenario:**
- Days with minimal/zero solar
- Battery cannot recharge
- SOC gradually depletes

**System Behavior:**
```
Day 1:
  Start SOC: 70%
  No solar, no delivery
  End SOC: 70% (unchanged)

Day 2:
  Start SOC: 70%
  Minimal solar (5 MW), some charging
  End SOC: 72%

Day 3:
  Start SOC: 72%
  No solar, no delivery
  End SOC: 72%
```

**Outcome:** System enters low-delivery mode until solar returns

**Mitigation with Third Source:**
- Grid backup ensures delivery continuity
- Higher operating costs during cloudy period
- Battery charges when solar returns

#### 10.2.2 Constant High Solar (Summer Peak)

**Scenario:**
- Extended period of high solar generation
- Battery stays at 95% SOC
- Significant wastage

**System Behavior:**
```
Hour 8-16: Solar 55-65 MW
  Delivery: 25 MW
  Excess: 30-40 MW
  Battery: Full (95%)
  Wastage: 30-40 MW per hour

Daily Wastage: ~280 MWh
Weekly Wastage: ~2,000 MWh
```

**Solutions:**
1. Larger battery (more headroom)
2. Additional loads during peak hours
3. Curtail solar generation
4. Export excess to grid (if third source = grid connection)

#### 10.2.3 SOC at Boundary During Critical Hour

**Scenario:** SOC exactly at 5% or 95% when needed

**At 5% Minimum:**
```
Hour 18:
  Solar: 15 MW
  SOC: 5.0% (exactly at minimum)
  Deficit: 10 MW
  Available Energy: (5% - 5%) × Capacity = 0 MWh

Result: Cannot discharge, no delivery
```

**At 95% Maximum:**
```
Hour 11:
  Solar: 40 MW
  SOC: 95.0% (exactly at maximum)
  Excess: 15 MW
  Headroom: (95% - 95%) × Capacity = 0 MWh

Result: Cannot charge, 15 MW wasted
```

**Handling:** System correctly enforces boundaries, no special logic needed

#### 10.2.4 Cycle Limit at 1.9 Cycles

**Scenario:** Daily cycles at 1.9, need one more discharge

**Analysis:**
```
Current State: IDLE
Daily Cycles: 1.9
Need: Discharge for delivery

Transition: IDLE → DISCHARGING = +0.5 cycles
Result: 1.9 + 0.5 = 2.4 > 2.0 (BLOCKED)

System Response: Cannot discharge, no delivery
```

**Design Decision:** Enforce strict 2.0 limit, don't allow 2.4

**Alternative Design:** Could allow "partial" cycle (0.1 instead of 0.5)
- Pro: Better resource utilization
- Con: Complex cycle accounting, not accurate to physical reality

**Current Implementation:** Strict 2.0 limit preferred for simplicity

#### 10.2.5 Simultaneous Charging and Discharging Need

**Scenario:** Have both excess solar AND need discharge (shouldn't happen normally)

**Example:**
```
Solar: 30 MW
Load: 25 MW
Excess: 5 MW

Simultaneously:
  Need to deliver 25 MW
  Have 5 MW excess to charge
```

**System Behavior:**
```
Step 1: Deliver 25 MW from solar
Step 2: Charge battery with 5 MW excess
State: CHARGING
Result: Delivery + Charging simultaneously
```

**State:** CHARGING (reflects current action)

**Note:** This is normal Scenario 1 behavior, not an edge case

**Actual Edge Case:** Need discharge while actively charging
```
Hour N:
  State: CHARGING
  Solar: 30 MW
  Delivering 25 MW, charging 5 MW

Hour N+1:
  State: CHARGING
  Solar: 20 MW
  Need: 5 MW from battery

Problem: CHARGING → DISCHARGING = 1.0 cycles
```

**System Response:**
- Must transition to DISCHARGING
- Costs 1.0 cycles (significant)
- Rare in practice due to solar variability patterns

### 10.3 Validation Checks

**System Integrity Checks to Implement:**

#### 10.3.1 Energy Conservation
```python
def validate_energy_conservation(results):
    """Verify energy balance over full year."""
    total_solar = results['solar_mw'].sum()
    total_charged = results[results['bess_mw'] < 0]['bess_mw'].abs().sum()
    total_discharged = results[results['bess_mw'] > 0]['bess_mw'].sum()
    total_delivered = results['committed_mw'].sum()
    total_wasted = results['wastage_mwh'].sum()

    # Solar = Charged + Wasted + Direct Delivery
    solar_disposition = total_charged + total_wasted + direct_to_load

    assert abs(total_solar - solar_disposition) < 1.0, "Energy balance error"

    # Battery output ≤ Battery input × efficiency
    max_discharge = total_charged * 0.87
    assert total_discharged <= max_discharge * 1.01, "Efficiency violation"
```

#### 10.3.2 SOC Boundaries
```python
def validate_soc_boundaries(results):
    """Verify SOC stays within 5%-95%."""
    min_soc = results['soc_percent'].min()
    max_soc = results['soc_percent'].max()

    assert min_soc >= 5.0, f"SOC dropped below 5%: {min_soc}%"
    assert max_soc <= 95.0, f"SOC exceeded 95%: {max_soc}%"

    # Check for violations
    violations_low = (results['soc_percent'] < 5.0).sum()
    violations_high = (results['soc_percent'] > 95.0).sum()

    if violations_low > 0 or violations_high > 0:
        raise ValueError(f"SOC violations: {violations_low} low, {violations_high} high")
```

#### 10.3.3 Cycle Limits
```python
def validate_cycle_limits(results):
    """Verify daily cycles never exceed 2.0."""
    results['day'] = results['hour'] // 24
    daily_max_cycles = results.groupby('day')['daily_cycles'].max()

    violations = daily_max_cycles[daily_max_cycles > 2.0]

    if len(violations) > 0:
        raise ValueError(f"Cycle limit violations on {len(violations)} days")

    # Check that cycles reset daily
    day_starts = results[results['hour'] % 24 == 0]['daily_cycles']
    if not (day_starts == 0.0).all():
        raise ValueError("Daily cycles not resetting properly")
```

#### 10.3.4 Binary Delivery
```python
def validate_binary_delivery(results):
    """Verify all deliveries are 0 or 25 MW."""
    delivered_values = results['committed_mw'].unique()

    valid_values = {0.0, 25.0}
    invalid = set(delivered_values) - valid_values

    if invalid:
        raise ValueError(f"Invalid delivery values found: {invalid}")

    # Check delivery flag consistency
    yes_delivery = results[results['delivery'] == 'Yes']['committed_mw']
    if not (yes_delivery == 25.0).all():
        raise ValueError("Delivery='Yes' but committed_mw != 25")

    no_delivery = results[results['delivery'] == 'No']['committed_mw']
    if not (no_delivery == 0.0).all():
        raise ValueError("Delivery='No' but committed_mw != 0")
```

### 10.4 Debugging Guide

**Step-by-Step Debugging Process:**

1. **Identify Hour with Issue**
   ```python
   problem_hour = 4567
   hour_data = results[results['hour'] == problem_hour]
   print(hour_data)
   ```

2. **Check Previous State**
   ```python
   previous_hour = problem_hour - 1
   prev_data = results[results['hour'] == previous_hour]
   print(f"Previous SOC: {prev_data['soc_percent'].values[0]}%")
   print(f"Previous State: {prev_data['bess_state'].values[0]}")
   print(f"Previous Cycles: {prev_data['daily_cycles'].values[0]}")
   ```

3. **Verify Resource Calculation**
   ```python
   solar = hour_data['solar_mw'].values[0]
   soc = prev_data['soc_percent'].values[0] / 100
   capacity = battery_capacity

   available_energy = (soc - 0.05) * capacity
   battery_power = min(available_energy, capacity * 1.0)
   total_available = solar + battery_power

   print(f"Solar: {solar} MW")
   print(f"Battery Energy: {available_energy} MWh")
   print(f"Battery Power: {battery_power} MW")
   print(f"Total: {total_available} MW")
   print(f"Can Deliver: {total_available >= 25}")
   ```

4. **Check Constraints**
   ```python
   cycles = prev_data['daily_cycles'].values[0]
   print(f"Daily Cycles: {cycles}")
   print(f"Can Cycle: {cycles < 2.0}")
   print(f"SOC Valid: {5 <= prev_data['soc_percent'].values[0] <= 95}")
   ```

5. **Trace State Transitions**
   ```python
   # Get full day context
   day_num = problem_hour // 24
   day_data = results[results['hour'] // 24 == day_num]

   print("\nFull Day State Transitions:")
   for idx, row in day_data.iterrows():
        print(f"Hour {row['hour']}: State={row['bess_state']}, "
              f"Cycles={row['daily_cycles']:.1f}, "
              f"Delivery={row['delivery']}")
   ```

---

## Document End

**Version:** 1.0
**Last Updated:** November 24, 2025
**Status:** Complete
**Next Review:** Upon addition of third power source or major system modification

---

For questions or clarifications about power delivery scenarios, refer to:
- **Technical Implementation:** `src/battery_simulator.py`
- **Configuration:** `src/config.py`
- **Project Documentation:** `PROJECT_PLAN.md`
- **Bug Fixes & Changes:** `CHANGELOG.md`
