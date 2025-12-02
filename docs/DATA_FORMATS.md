# BESS Sizing Tool - Data Formats Reference

**Document Version:** 1.0
**Last Updated:** December 2025
**Purpose:** Complete reference for all input parameters and output report formats

---

## Table of Contents

1. [Configuration Inputs](#1-configuration-inputs)
2. [Output Reports](#2-output-reports)
3. [Validation Rules](#3-validation-rules)
4. [Operating Concepts](#4-operating-concepts)

---

# 1. Configuration Inputs

## 1.1 Project Parameters

### Target Delivery Power (MW)
- **Parameter Name:** `target_delivery_MW`
- **Description:** Fixed power delivery target. The system will deliver either this amount or 0 MW (binary delivery)
- **Default Value:** 25.0 MW
- **Notes:** Binary delivery system - delivers exactly this amount or nothing

### Solar PV Capacity (MW)
- **Parameter Name:** `solar_capacity_MW`
- **Description:** Total installed solar PV capacity.
- **Default Value:** 67.0 MW

---

## 1.2 Battery Technical Parameters

### State of Charge (SOC) Limits

| Parameter | Name | Default | Range | Step | Description |
|-----------|------|---------|-------|------|-------------|
| Minimum SOC | `SOC_min` | 5.0% | 0-50% | 1% | Lower SOC limit to preserve battery life |
| Maximum SOC | `SOC_max` | 95.0% | 50-100% | 1% | Upper SOC limit to preserve battery life |
| Initial SOC | `SOC_initial` | 50.0% | min-max | 1% | Starting SOC at hour 0 |

### Efficiency & Power Rates

| Parameter | Name | Default | Range | Step | Description |
|-----------|------|---------|-------|------|-------------|
| Round-Trip Efficiency | `RTE` | 87.0% | 70-95% | 0.5% | AC-to-AC efficiency including all losses |
| C-Rate Charge | `c_rate_charge` | 1.0 | 0.1-2.0 | 0.1 | Max charge rate as fraction of capacity |
| C-Rate Discharge | `c_rate_discharge` | 1.0 | 0.1-2.0 | 0.1 | Max discharge rate as fraction of capacity |

### Cycling & Degradation

| Parameter | Name | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| Max Cycles/Day | `max_cycles_per_day` | 2 | 1-4 | Daily cycle limit |
| Degradation/Cycle | `degradation_per_cycle` | 0.0015% | - | Capacity loss per full cycle |
| Auxiliary Load | `auxiliary_load_pct` | 0% | 0-1% | Parasitic load as % of capacity/hour |

---

## 1.3 Battery Sizing Range

| Parameter | Name | Default | Range | Step | Description |
|-----------|------|---------|-------|------|-------------|
| Minimum Size | `battery_size_min_MWh` | 10.0 MWh | 1-500 | 10 MWh | Smallest battery size to test |
| Maximum Size | `battery_size_max_MWh` | 500.0 MWh | 1-500 | 5 MWh | Largest battery size to test |
| Step Size | `battery_size_step_MWh` | 5.0 MWh | 1-50 | 1 MWh | Increment between sizes |

---

## 1.4 Control Parameters

| Parameter | Name | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| Charge Threshold | `charge_threshold_MW` | 0 MW | 0-5 MW | Minimum excess power to trigger charging |
| Marginal Threshold | `marginal_value_threshold` | 300 hrs/10MWh | 0-1000 | Threshold for optimal size detection |

---

# 2. Output Reports

## 2.1 Summary Report

### File Format
- **Type:** CSV (Comma-Separated Values)
- **Encoding:** UTF-8
- **Filename:** `bess_summary_report_YYYYMMDD_HHMMSS.csv`

### Data Fields

| Column Name | Data Type | Units | Description |
|------------|-----------|-------|-------------|
| `Battery Size (MWh)` | Float | MWh | Battery energy capacity tested |
| `Hours Delivered` | Integer | Hours | Total hours target was delivered (out of 8,760) |
| `Total Wastage (MWh)` | Float | MWh | Solar energy wasted when battery full |
| `Wastage (%)` | Float | % | Percentage of solar energy wasted |
| `Total Cycles` | Float | Cycles | Charge-discharge cycles in one year |
| `Avg Cycles/Day` | Float | Cycles/Day | Average daily cycling rate |
| `Degradation (%)` | Float | % | Estimated capacity degradation |
| `Marginal Hours/MWh` | Float | Hours/MWh | Marginal improvement per MWh increase |

---

## 2.2 Hourly Report

### File Format
- **Type:** CSV (Comma-Separated Values)
- **Encoding:** UTF-8
- **Filename:** `bess_hourly_data_[SIZE]MWh_YYYYMMDD_HHMMSS.csv`
- **Rows:** 8,760 (one per hour of the year)

### Data Fields

| Column Name | Data Type | Units | Description |
|------------|-----------|-------|-------------|
| `Date` | String | YYYY-MM-DD | Date of the hour |
| `Hour` | Integer | 0-23 | Hour of the day |
| `Solar_Generation_MW` | Float | MW | Solar power generation |
| `BESS_MW` | Float | MW | Battery power (-ve charge, +ve discharge) |
| `BESS_Charge_MWh` | Float | MWh | Energy stored in battery |
| `SOC_%` | Float | % | Battery state of charge |
| `Committed_MW` | Float | MW | Target delivery commitment |
| `Deficit_MW` | Float | MW | Power deficit when positive |
| `Delivery_Hour` | String | Yes/No | Whether target was delivered |
| `Wastage_MWh` | Float | MWh | Solar energy wasted this hour |
| `State` | String | - | Battery state (Idle/Charging/Discharging) |

### Data Relationships

**Power Balance (when delivering):**
```
Solar_Generation_MW + BESS_MW >= Committed_MW
```

**Energy Balance:**
```
BESS_Charge_MWh = (SOC_% / 100) × Battery_Capacity_MWh
```

**Deficit Calculation:**
```
Deficit_MW = MAX(0, Committed_MW - Solar_Generation_MW - BESS_MW)
```

---

# 3. Validation Rules

## SOC Validation
1. `SOC_min` must be less than `SOC_max`
2. Initial SOC must be between `SOC_min` and `SOC_max`
3. Operating window (`SOC_max - SOC_min`) must be at least 20%

## Battery Size Validation
1. Minimum battery size must be less than maximum
2. Step size must be positive
3. Minimum battery size should be at least 5 MWh

## Efficiency Validation
1. RTE must be between 0 and 100%
2. C-rate charge must be between 0 and 2
3. C-rate discharge must be between 0 and 2

## Warnings
- **Solar/Target Ratio < 1.2:** Consider increasing solar capacity
- **Configurations > 100:** Simulation may take longer

---

# 4. Operating Concepts

## Binary Delivery
- System delivers either the full target power (25 MW) or nothing (0 MW)
- No partial delivery allowed

## Battery + Solar Operation
- Battery works **together with solar** to meet delivery target
- Battery does NOT need to deliver full target alone
- Example: 10 MWh battery (10 MW discharge) + 15 MW solar = 25 MW target

## Cycle Counting (State-Transition Based)
| Transition | Cycle Increment |
|------------|-----------------|
| IDLE → CHARGING | No increment |
| IDLE → DISCHARGING | No increment |
| CHARGING → DISCHARGING | +0.5 cycles |
| DISCHARGING → CHARGING | +0.5 cycles |

Daily cycles reset at midnight.

## Round-Trip Efficiency Application
- **Charging:** Energy stored = Power × RTE
- **Discharging:** Energy removed = Power / RTE
- Accounts for all system losses (battery, inverter, transformer)

---

*Combined from Inputs.md and outputs.md - December 2025*
