# BESS Sizing Tool - Output Reports Documentation

## Overview
The BESS sizing tool generates two primary output reports containing simulation results and performance metrics. These reports provide comprehensive insights into battery performance across different sizing configurations.

---

## 1. Summary Report

### Description
The Summary Report provides a high-level overview of simulation results for all tested battery sizes. It includes key performance metrics and identifies the optimal battery configuration based on diminishing returns analysis.

### File Format
- **Type:** CSV (Comma-Separated Values)
- **Encoding:** UTF-8
- **Filename Format:** `bess_summary_report_YYYYMMDD_HHMMSS.csv`
- **Example:** `bess_summary_report_20241122_143052.csv`

### Data Fields

| Column Name | Data Type | Units | Description |
|------------|-----------|-------|-------------|
| `Battery Size (MWh)` | Float | MWh | Battery energy capacity tested |
| `Hours Delivered` | Integer | Hours | Total hours target power was successfully delivered (out of 8,760) |
| `Total Wastage (MWh)` | Float | MWh | Total solar energy wasted (curtailed) when battery is full |
| `Wastage (%)` | Float | % | Percentage of total available solar energy that was wasted |
| `Total Cycles` | Float | Cycles | Total charge-discharge cycles completed in one year |
| `Avg Cycles\Day` | Float | Cycles/Day | Average daily cycling rate (Total Cycles / 365) |
| `Degradation (%)` | Float | % | Estimated capacity degradation based on cycle count |
| `Marginal Hours\MWh` | Float | Hours/MWh | Marginal improvement in delivery hours per MWh increase |


### Key Metrics Explained

#### Hours Delivered
- Number of hours (out of 8,760 annual hours) where the full target power was delivered
- Binary delivery: Either full target power or 0 MW
- Higher values indicate better system performance

#### Wastage Metrics
- **Total Wastage:** Solar energy that couldn't be stored due to battery constraints
- **Wastage %:** Indicates system efficiency in utilizing available solar
- Lower wastage percentages indicate better solar utilization

#### Cycling Metrics
- **Total Cycles:** Annual charge-discharge cycles
- **Avg Cycles/Day:** Daily cycling intensity
- Limited by max_cycles_per_day configuration parameter

#### Marginal Analysis
- **Marginal Hours/MWh:** Additional delivery hours gained per MWh battery increase
- Used to identify diminishing returns point
- Optimal size identified where marginal value < threshold



---

## 2. Hourly Report

### Description
The Hourly Report provides detailed operational data for all 8,760 hours of the year for a selected battery size. It includes power flows, state of charge, delivery status, and system state information.

### File Format
- **Type:** CSV (Comma-Separated Values)
- **Encoding:** UTF-8
- **Filename Format:** `bess_hourly_data_[SIZE]MWh_YYYYMMDD_HHMMSS.csv`
- **Example:** `bess_hourly_data_100MWh_20241122_143052.csv`
- **Rows:** 8,760 (one per hour of the year)

### Data Fields

| Column Name | Data Type | Units | Description |
|------------|-----------|-------|-------------|
| `Date` | String | YYYY-MM-DD | Date of the hour |
| `Hour` | Integer | 0-23 | Hour of the day (24-hour format) |
| `Solar_Generation_MW` | Float | MW | Solar power generation for the hour |
| `BESS_MW` | Float | MW | Battery charge power ( shown by negative sign ) or discharge power(shown by the potivie sign) in the hour |
| `BESS_Charge_MWh` | Float | MWh | Total energy stored in battery (SOC × Capacity) |
| `SOC_%` | Float | % | Battery state of charge percentage |
| `Committed_MW` | Float | MW | Target delivery commitment (constant) |
| `Deficit_MW` | Float | MW | Power deficit (Target - Solar) when positive |
| `Delivery_Hour` | String | Yes/No | Whether target was delivered this hour |
| `Wastage_MWh` | Float | MWh | Solar energy wasted this hour |
| `State` | String | Idle/Charging/Discharing | Battery operational state |

### Column Details

#### Time Columns
- **Date:** Calendar date in ISO format (YYYY-MM-DD)
- **Hour:** Hour of day from 0 (midnight) to 23 (11 PM)

#### Power Flow Columns
- **Solar_Generation_MW:** Actual solar PV output for the hour
- **BESS_MW:** Battery discharge power when supporting delivery
- Battery charge power when charging shown by -ve

- **Deficit_MW:** Shortfall between target and available solar + BESS
  - Positive when solar alone cannot meet target
  - Zero when solar exceeds target

#### Battery Status Columns
- **BESS_Charge_MWh:** Actual energy stored in battery
  - Calculated as: (SOC% / 100) × Battery_Capacity_MWh
  - Represents total stored energy available
- **SOC_%:** State of charge as percentage
  - Range: SOC_min to SOC_max (configured parameters)
  - Indicates battery energy level

#### Delivery Columns
- **Committed_MW:** Fixed target delivery requirement
  - Same value for all 8,760 hours
  - Binary delivery constraint
- **Delivery_Hour:** Success indicator
  - "Yes" = Full target delivered
  - "No" = Could not deliver target

#### System State
- **State:** Battery operational state
  - `IDLE`: Not charging or discharging
  - `CHARGING`: Storing excess solar energy
  - `DISCHARGING`: Providing power to meet target
- **Wastage_MWh:** Curtailed solar energy
  - Occurs when battery full and excess solar available
  - Represents lost opportunity for energy storage

### Data Relationships

#### Power Balance
```
When Delivering:
  Solar_Generation_MW + BESS_MW => Committed_MW

When Not Delivering:
  Solar_Generation_MW + Available_BESS < Committed_MW
```

#### Energy Balance
```
BESS_Charge_MWh = (SOC_% / 100) × Battery_Capacity_MWh
```

#### Deficit Calculation
```
Deficit_MW = MAX(0, Committed_MW - Solar_Generation_MW - BESS_MW)
```
