# BESS Sizing Tool - Configuration Inputs

## Complete List of Configuration Parameters

This document lists all configuration inputs available in the BESS (Battery Energy Storage System) sizing tool.

---

## 1. Project Parameters

### 1.1 Target Delivery Power (MW)
- **Parameter Name:** `target_delivery_MW`
- **Description:** Fixed power delivery target. The system will deliver either this amount or 0 MW (binary delivery)
- **Default Value:** 25.0 MW
- **Notes:** Binary delivery system - delivers exactly this amount or nothing

### 1.2 Solar PV Capacity (MW)
- **Parameter Name:** `solar_capacity_MW`
- **Description:** Total installed solar PV capacity.
- **Default Value:** 67.0 MW

---

## 2. Battery Technical Parameters

### 2.1 State of Charge (SOC) Limits

#### Minimum SOC (%)
- **Parameter Name:** `SOC_min`
- **Description:** Lower SOC limit to preserve battery life
- **Default Value:** 5.0%
- **Range:** 0.0 - 50.0%
- **Step:** 1.0%

#### Maximum SOC (%)
- **Parameter Name:** `SOC_max`
- **Description:** Upper SOC limit to preserve battery life
- **Default Value:** 95.0%
- **Range:** 50.0 - 100.0%
- **Step:** 1.0%

#### Initial SOC (%)
- **Parameter Name:** `SOC_initial`
- **Description:** Starting SOC at hour 0 of simulation
- **Default Value:** 50.0%
- **Range:** SOC_min - SOC_max
- **Step:** 1.0%
- **Notes:** Must be within the min/max SOC range

### 2.2 Efficiency & Power Rates

#### Round-Trip Efficiency (%)
- **Parameter Name:** `RTE`
- **Description:** AC-to-AC efficiency including all losses (battery, inverter, transformer)
- **Default Value:** 87.0%
- **Range:** 70.0 - 95.0%
- **Step:** 0.5%
- **Notes:** Applied asymmetrically: charging multiplies by RTE, discharging divides by RTE

#### C-Rate Charge
- **Parameter Name:** `c_rate_charge`
- **Description:** Maximum charge rate as fraction of capacity (0.5C = 2 hours to full charge)
- **Default Value:** 1.0
- **Range:** 0.1 - 2.0
- **Step:** 0.1
- **Notes:** Determines max charging power = capacity × c_rate_charge

#### C-Rate Discharge
- **Parameter Name:** `c_rate_discharge`
- **Description:** Maximum discharge rate as fraction of capacity (1.0C = 1 hour to full discharge)
- **Default Value:** 1.0
- **Range:** 0.1 - 2.0
- **Step:** 0.1
- **Notes:** Determines max discharge power = capacity × c_rate_discharge

### 2.3 Cycling & Degradation

#### Max Cycles per Day
- **Parameter Name:** `max_cycles_per_day`
- **Description:** Daily cycle limit to prevent accelerated degradation
- **Default Value:** 2
- **Range:** 1 - 4
- **Step:** 0.5
- **Type:** Integer
- **Notes:** One cycle = charge from low to high, then discharge back to low

#### Degradation per Cycle (%)
- **Parameter Name:** `degradation_per_cycle`
- **Description:** Capacity loss per full cycle
- **Default Value:** 0.0015%

#### Auxiliary Load (%/hr)
- **Parameter Name:** `auxiliary_load_pct`
- **Description:** Parasitic load as % of capacity per hour (HVAC, controls, etc.)
- **Default Value:** 0%
- **Range:** 0.0 - 1.0%
- **Step:** 0.01%
- **Format:** 2 decimal places
- **Notes:** Reduces available solar power every hour

---

## 3. Battery Sizing Range

### 3.1 Minimum Battery Size (MWh)
- **Parameter Name:** `battery_size_min_MWh`
- **Description:** Smallest battery size to test
- **Default Value:** 10.0 MWh
- **Range:** 1.0 - 500.0 MWh
- **Step:** 10.0 MWh
- **Validation:** Must be at least 5 MWh for meaningful contribution

### 3.2 Maximum Battery Size (MWh)
- **Parameter Name:** `battery_size_max_MWh`
- **Description:** Largest battery size to test
- **Default Value:** 500.0 MWh
- **Range:** 1.0 - 500.0 MWh
- **Step:** 5.0 MWh
- **Validation:** Must be greater than minimum battery size

### 3.3 Step Size (MWh)
- **Parameter Name:** `battery_size_step_MWh`
- **Description:** Increment between battery sizes
- **Default Value:** 5.0 MWh
- **Range:** 1.0 - 50.0 MWh
- **Step:** 1.0 MWh
- **Notes:** Determines number of configurations to test

---

## 4. Control Parameters

### 4.1 Minimum Charge Threshold (MW)
- **Parameter Name:** `charge_threshold_MW`
- **Description:** Minimum excess power required to trigger battery charging (creates deadband)
- **Default Value:** 0 MW
- **Range:** 0.0 - 5.0 MW
- **Step:** 0.1 MW
- **Format:** 2 decimal places
- **Notes:** Battery will only charge when excess power > threshold

### 4.2 Marginal Value Threshold (hrs/10MWh)
- **Parameter Name:** `marginal_value_threshold`
- **Description:** Threshold for identifying optimal battery size based on diminishing returns
- **Default Value:** 300.0 hrs/10MWh
- **Range:** 0.0 - 1000.0
- **Step:** 10.0
- **Notes:** Used to identify point where increasing battery size provides limited benefit

---

## 5. Validation Rules

### SOC Validation
1. SOC_min must be less than SOC_max
2. Initial SOC must be between SOC_min and SOC_max
3. Operating window (SOC_max - SOC_min) must be at least 20%

### Battery Size Validation
1. Minimum battery size must be less than maximum
2. Step size must be positive
3. Minimum battery size should be at least 5 MWh

### Efficiency Validation
1. RTE must be between 0 and 100%
2. C-rate charge must be between 0 and 2
3. C-rate discharge must be between 0 and 2

### Solar/Target Ratio Recommendation
- Ratio < 1.2: Warning issued (consider increasing solar capacity)
- Ratio ≥ 1.2: Configuration acceptable

### Number of Configurations Warning
- If testing > 100 configurations: Warning issued (may take a while)

---

## 6. Important Operating Concepts

### Binary Delivery
- System delivers either the full target power or nothing (0 MW)
- No partial delivery allowed

### Battery + Solar Operation
- Battery works **together with solar** to meet delivery target
- Battery does NOT need to deliver full target by itself
- Example: 10 MWh battery (10 MW discharge) + 15 MW solar = 25 MW target ✓

### Cycle Counting (Per PDF Specification)
- IDLE → CHARGING: No cycle increment (just started)
- IDLE → DISCHARGING: No cycle increment (just started)
- CHARGING → DISCHARGING: Add 0.5 cycles
- DISCHARGING → CHARGING: Add 0.5 cycles
- Daily cycles reset at midnight

### Round-Trip Efficiency Application
- Charging: Energy stored = Power × RTE
- Discharging: Energy removed = Power / RTE
- Accounts for all system losses (battery, inverter, transformer)

