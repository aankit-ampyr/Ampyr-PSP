# BESS Sizing Tool - Automated Testing Guide

## Overview

This document provides comprehensive guidance for implementing an automated test suite for the BESS (Battery Energy Storage System) Sizing Tool. The testing strategy covers unit tests, integration tests, validation tests, performance benchmarks, and CI/CD integration.

**Current Status:** No automated tests (as of v1.1.0)
**Target Coverage:** ≥80% overall, ≥95% for core simulation engine
**Estimated Implementation Effort:** 14-22 hours

---

## Table of Contents

1. [Testing Framework & Dependencies](#1-testing-framework--dependencies)
2. [Directory Structure](#2-directory-structure)
3. [Critical Test Cases](#3-critical-test-cases)
4. [Test Data Requirements](#4-test-data-requirements)
5. [Fixture Definitions](#5-fixture-definitions)
6. [Example Test Implementations](#6-example-test-implementations)
7. [Coverage Requirements](#7-coverage-requirements)
8. [Performance Benchmarks](#8-performance-benchmarks)
9. [CI/CD Integration](#9-cicd-integration)
10. [Implementation Checklist](#10-implementation-checklist)

---

## 1. Testing Framework & Dependencies

### Core Testing Dependencies

Add to `requirements.txt`:

```txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-benchmark==4.0.0
```

### Optional Advanced Testing Tools

```txt
hypothesis==6.92.0  # Property-based testing for edge cases
freezegun==1.4.0    # Time mocking for hour-based simulations
```

### Installation

```bash
pip install -r requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov=utils --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_battery_system.py

# Run tests matching pattern
pytest -k "test_cycle"

# Run with verbose output
pytest -v

# Run performance benchmarks
pytest tests/performance/ --benchmark-only
```

---

## 2. Directory Structure

```
tests/
├── __init__.py
├── conftest.py                      # Shared fixtures and configuration
│
├── test_data/                       # Test data files
│   ├── solar_profile_full.csv       # Valid 8760-hour profile
│   ├── solar_profile_short.csv      # Invalid (< 8760 hours)
│   ├── solar_profile_invalid.csv    # Negative/out-of-range values
│   ├── solar_profile_flat_30mw.csv  # Constant 30 MW
│   ├── solar_profile_zero.csv       # All zeros
│   └── test_configs.json            # Test configuration sets
│
├── unit/                            # Unit tests (single function/class)
│   ├── __init__.py
│   ├── test_battery_system.py       # BatterySystem class tests (30+ tests)
│   ├── test_config.py               # Configuration defaults
│   ├── test_validators.py           # Validation logic (12+ tests)
│   ├── test_metrics.py              # Metrics calculations (15+ tests)
│   ├── test_config_manager.py       # Config state management
│   └── test_data_loader.py          # Solar profile loading (10+ tests)
│
├── integration/                     # Integration tests (multi-component)
│   ├── __init__.py
│   ├── test_simulation.py           # Full year simulation (20+ tests)
│   ├── test_optimization.py         # Optimization algorithms
│   └── test_end_to_end.py           # Complete workflows
│
└── performance/                     # Performance benchmarks
    ├── __init__.py
    └── test_benchmarks.py           # Speed and memory tests
```

**Total Test Files:** 12
**Expected Test Count:** ~87 tests minimum

---

## 3. Critical Test Cases

### 3.1 Unit Tests: BatterySystem Class

**File:** `tests/unit/test_battery_system.py`
**Source:** `src/battery_simulator.py`
**Test Count:** 30+ tests

#### 3.1.1 Initialization Tests (5 tests)

| Test Case | Verification |
|-----------|-------------|
| `test_valid_initialization` | Capacity, SOC, state, cycles set correctly |
| `test_initial_soc_within_bounds` | 0.05 ≤ initial_soc ≤ 0.95 |
| `test_zero_capacity_raises_error` | ValueError raised for capacity ≤ 0 |
| `test_negative_capacity_raises_error` | ValueError raised for negative capacity |
| `test_invalid_initial_soc_raises_error` | ValueError for SOC < 0 or SOC > 1 |

#### 3.1.2 Cycle Counting Tests (8 tests)

**CRITICAL:** Cycle counting is state-transition based, not charge/discharge event based.

| Test Case | Expected Cycles |
|-----------|----------------|
| `test_idle_to_charging_half_cycle` | IDLE → CHARGING = 0.5 |
| `test_charging_to_idle_full_cycle` | CHARGING → IDLE = 1.0 total |
| `test_idle_to_discharging_half_cycle` | IDLE → DISCHARGING = 0.5 |
| `test_discharging_to_idle_full_cycle` | DISCHARGING → IDLE = 1.0 total |
| `test_full_charge_discharge_cycle` | IDLE → CHARGE → IDLE → DISCHARGE → IDLE = 2.0 |
| `test_idle_to_idle_no_cycle` | IDLE → IDLE = 0.0 cycles |
| `test_charging_to_charging_no_cycle` | CHARGING → CHARGING = 0.0 cycles |
| `test_cycle_limit_blocks_transition` | can_cycle() returns False at 2.0 cycles |

**Example Scenario:**
```
Hour 0: IDLE (0.0 cycles)
Hour 6: IDLE → CHARGING (0.5 cycles)
Hour 10: CHARGING → IDLE (1.0 cycles)
Hour 12: IDLE → DISCHARGING (1.5 cycles)
Hour 16: DISCHARGING → IDLE (2.0 cycles - LIMIT REACHED)
Hour 18: IDLE → DISCHARGING blocked (already at 2.0)
```

#### 3.1.3 Daily Cycle Reset Test (1 test)

| Test Case | Verification |
|-----------|-------------|
| `test_daily_cycle_reset` | Cycles reset to 0.0 at hour % 24 == 0 |

#### 3.1.4 Charging Logic Tests (6 tests)

| Test Case | Verification |
|-----------|-------------|
| `test_charge_applies_efficiency` | Energy stored = input × 0.933 |
| `test_charge_updates_soc_correctly` | ΔSOC = (energy_stored / capacity) × 100 |
| `test_charge_limited_by_headroom` | Cannot exceed MAX_SOC (95%) |
| `test_charge_limited_by_c_rate` | Power ≤ capacity × c_rate_charge |
| `test_charge_returns_actual_energy` | Returns energy actually charged |
| `test_charge_at_max_soc_no_change` | No change when SOC = 95% |

**Efficiency Formula:**
```
energy_to_battery = input_energy × 0.933
delta_soc = (energy_to_battery / capacity) × 100
```

#### 3.1.5 Discharging Logic Tests (6 tests)

| Test Case | Verification |
|-----------|-------------|
| `test_discharge_applies_efficiency` | Battery energy used = output / 0.933 |
| `test_discharge_updates_soc_correctly` | ΔSOC = (energy_from_battery / capacity) × 100 |
| `test_discharge_limited_by_available_energy` | Cannot go below MIN_SOC (5%) |
| `test_discharge_limited_by_c_rate` | Power ≤ capacity × c_rate_discharge |
| `test_discharge_returns_actual_energy` | Returns energy actually discharged |
| `test_discharge_at_min_soc_no_change` | No discharge when SOC = 5% |

**Efficiency Formula:**
```
energy_from_battery = output_energy / 0.933
delta_soc = (energy_from_battery / capacity) × 100
```

#### 3.1.6 SOC Calculation Tests (4 tests)

| Test Case | Verification |
|-----------|-------------|
| `test_get_available_energy` | (SOC - 0.05) × capacity |
| `test_get_charge_headroom` | (0.95 - SOC) × capacity |
| `test_available_energy_at_min_soc` | 0.0 MWh when SOC = 5% |
| `test_charge_headroom_at_max_soc` | 0.0 MWh when SOC = 95% |

---

### 3.2 Integration Tests: simulate_bess_year()

**File:** `tests/integration/test_simulation.py`
**Source:** `src/battery_simulator.py`
**Test Count:** 20+ tests

#### 3.2.1 Binary Delivery Logic Tests (4 tests)

| Scenario | Solar | Battery | Expected Delivery |
|----------|-------|---------|-------------------|
| Excess solar | ≥25 MW | Any | 25 MW (charge excess) |
| Partial solar + battery | <25 MW | Sufficient | 25 MW (discharge deficit) |
| Insufficient resources | <25 MW | Insufficient | 0 MW (no delivery) |
| Cycle limit reached | <25 MW | Sufficient | 0 MW (blocked by cycles) |

**Critical Test:**
```python
def test_binary_delivery_no_partial():
    """Verify delivery is ALWAYS 0 MW or 25 MW, never partial"""
    results = simulate_bess_year(battery_capacity, solar_profile, config)
    delivered_values = results['committed_mw'].unique()
    assert set(delivered_values).issubset({0.0, 25.0})
```

#### 3.2.2 Full Year Scenario Tests (5 tests)

| Scenario | Battery Size | Expected Behavior |
|----------|--------------|-------------------|
| Zero battery (0 MWh) | 0 | Solar-only delivery, no cycling |
| Small battery (25 MWh) | 25 | Limited cycle extension |
| Medium battery (100 MWh) | 100 | Significant hour increase |
| Large battery (200 MWh) | 200 | Approaching maximum hours |
| Optimal battery (from algorithm) | Variable | ≥95% of max performance |

#### 3.2.3 Energy Conservation Tests (3 tests)

**CRITICAL:** Verify energy balance throughout simulation.

| Test Case | Verification |
|-----------|-------------|
| `test_energy_balance` | Solar = Charged + Wasted + Direct_Delivery |
| `test_efficiency_losses` | Energy_out ≤ Energy_in (accounting for 87% RT efficiency) |
| `test_no_energy_creation` | Battery never creates energy |

**Energy Balance Formula:**
```
solar_generated = solar_charged + solar_wasted + solar_direct_to_load
battery_discharged × 0.933 = battery_charged (round-trip efficiency)
```

#### 3.2.4 Operational Constraint Tests (4 tests)

| Test Case | Constraint | Verification |
|-----------|-----------|-------------|
| `test_soc_never_below_min` | SOC ≥ 5% | All 8760 hours |
| `test_soc_never_above_max` | SOC ≤ 95% | All 8760 hours |
| `test_daily_cycles_never_exceed_max` | Cycles ≤ 2.0 | All 365 days |
| `test_delivery_always_binary` | Delivery ∈ {0, 25} MW | All 8760 hours |

#### 3.2.5 Edge Case Day Tests (4 tests)

| Scenario | Description | Expected Behavior |
|----------|-------------|-------------------|
| All-night day | Zero solar 24 hours | No delivery, no charging |
| Peak solar day | 60+ MW all day | Maximum charging, high delivery |
| Cycle limit day | 2.0 cycles reached early | No further discharge |
| Low solar day | 5-10 MW average | Minimal delivery |

---

### 3.3 Validation Tests

**File:** `tests/unit/test_validators.py`
**Source:** `utils/validators.py`
**Test Count:** 12+ tests

#### Configuration Validation Tests

| Test Case | Invalid Config | Expected Error |
|-----------|---------------|---------------|
| `test_min_soc_greater_than_max_soc` | MIN_SOC = 0.9, MAX_SOC = 0.1 | Validation failure |
| `test_soc_out_of_range` | MIN_SOC = -0.1 or MAX_SOC = 1.5 | Validation failure |
| `test_negative_battery_size` | MIN_BATTERY_SIZE = -10 | Validation failure |
| `test_min_battery_greater_than_max` | MIN = 500, MAX = 100 | Validation failure |
| `test_zero_battery_step` | BATTERY_SIZE_STEP = 0 | Validation failure |
| `test_efficiency_out_of_range` | ROUND_TRIP_EFFICIENCY = 1.2 | Validation failure |
| `test_negative_c_rate` | C_RATE_CHARGE = -0.5 | Validation failure |
| `test_initial_soc_out_of_bounds` | INITIAL_SOC = 0.02 (below MIN) | Validation failure |
| `test_negative_degradation` | DEGRADATION_PER_CYCLE = -0.01 | Validation failure |
| `test_zero_target_delivery` | TARGET_DELIVERY_MW = 0 | Validation failure |
| `test_negative_solar_capacity` | SOLAR_CAPACITY_MW = -67 | Validation failure |
| `test_valid_config_passes` | All defaults | Validation success |

---

### 3.4 Metrics Calculation Tests

**File:** `tests/unit/test_metrics.py`
**Source:** `utils/metrics.py`
**Test Count:** 15+ tests

#### 3.4.1 Wastage Calculation Tests (CRITICAL - Bug #1 Fix)

**WRONG Formula (Old):**
```python
wastage_percent = (wasted / (charged + wasted + delivered)) × 100
```

**CORRECT Formula (Fixed in v1.0):**
```python
wastage_percent = (wasted / (charged + wasted)) × 100
```

| Test Case | Charged | Wasted | Expected Wastage % |
|-----------|---------|--------|-------------------|
| `test_wastage_zero` | 1000 | 0 | 0% |
| `test_wastage_fifty_percent` | 500 | 500 | 50% |
| `test_wastage_all_wasted` | 0 | 1000 | 100% |
| `test_wastage_excludes_delivered` | 500 | 500 | 50% (NOT 33.3%) |

#### 3.4.2 Delivery Metrics Tests (4 tests)

| Test Case | Calculation |
|-----------|------------|
| `test_delivery_hours_count` | Count where hourly_delivery == 'Yes' |
| `test_delivery_rate_percentage` | (delivery_hours / 8760) × 100 |
| `test_energy_delivered_gwh` | 25 MW × delivery_hours / 1000 |
| `test_zero_delivery_hours` | Correctly handles 0 deliveries |

#### 3.4.3 Cycling Metrics Tests (3 tests)

| Test Case | Calculation |
|-----------|------------|
| `test_total_cycles_sum` | Sum of all daily_cycles |
| `test_average_daily_cycles` | total_cycles / 365 |
| `test_max_daily_cycles` | max(daily_cycles for all days) |

#### 3.4.4 Degradation Tests (2 tests)

| Test Case | Calculation |
|-----------|------------|
| `test_degradation_calculation` | total_cycles × 0.15% |
| `test_degradation_zero_cycles` | 0 cycles → 0% degradation |

#### 3.4.5 Solar Utilization Tests (2 tests)

| Test Case | Calculation |
|-----------|------------|
| `test_solar_utilization` | (charged + direct_delivery) / generated × 100 |
| `test_utilization_bounds` | 0% ≤ utilization ≤ 100% |

---

### 3.5 Data Loader Tests

**File:** `tests/unit/test_data_loader.py`
**Source:** `src/data_loader.py`
**Test Count:** 10+ tests

#### Solar Profile Loading Tests

| Test Case | Scenario | Expected Behavior |
|-----------|----------|-------------------|
| `test_load_valid_8760_profile` | Valid CSV, 8760 rows | Loads successfully |
| `test_column_detection_solar` | Column named 'Solar_MW' | Detects correctly |
| `test_column_detection_generation` | Column named 'Generation' | Detects correctly |
| `test_column_detection_fallback` | No keyword match | Uses column index 1 |
| `test_warning_on_short_profile` | 8000 rows | Warning issued |
| `test_warning_on_long_profile` | 9000 rows | Warning issued |
| `test_negative_values_rejected` | Contains -10 MW | Error or warning |
| `test_out_of_range_values` | Contains 200 MW (>67) | Warning issued |
| `test_missing_file_handling` | File doesn't exist | Error raised |
| `test_path_traversal_prevention` | Path = '../../../etc/passwd' | Rejected (security) |

#### Solar Statistics Tests

| Test Case | Calculation |
|-----------|------------|
| `test_statistics_max_mw` | Maximum value in profile |
| `test_statistics_mean_mw` | Average value |
| `test_statistics_capacity_factor` | mean_mw / 67.0 |
| `test_statistics_zero_hours` | Count of 0 MW hours |

---

## 4. Test Data Requirements

### 4.1 Solar Profile Test Files

#### solar_profile_full.csv (Valid Profile)

**Requirements:**
- Exactly 8760 rows (+ 1 header row = 8761 lines)
- Format: `timestamp,Solar_Generation_MW`
- Values: 0 to 67 MW (realistic bounds)
- Pattern: Day/night cycle with parabolic daytime curve

**Sample Structure:**
```csv
timestamp,Solar_Generation_MW
2024-01-01 00:00,0.0
2024-01-01 01:00,0.0
2024-01-01 02:00,0.0
2024-01-01 03:00,0.0
2024-01-01 04:00,0.0
2024-01-01 05:00,0.0
2024-01-01 06:00,5.2
2024-01-01 07:00,15.8
2024-01-01 08:00,28.4
2024-01-01 09:00,42.1
2024-01-01 10:00,53.8
2024-01-01 11:00,61.2
2024-01-01 12:00,64.5
2024-01-01 13:00,61.2
2024-01-01 14:00,53.8
2024-01-01 15:00,42.1
2024-01-01 16:00,28.4
2024-01-01 17:00,15.8
2024-01-01 18:00,5.2
2024-01-01 19:00,0.0
...
(repeat for 365 days)
```

**Generation Pattern:**
- Night (20:00-06:00): 0 MW
- Morning ramp (06:00-12:00): 0 → 65 MW (parabolic)
- Afternoon ramp (12:00-18:00): 65 → 0 MW (parabolic)
- Peak hours (10:00-14:00): 50-65 MW

#### solar_profile_flat_30mw.csv (Constant Solar)

```csv
timestamp,Solar_Generation_MW
2024-01-01 00:00,30.0
2024-01-01 01:00,30.0
...
(all 8760 rows = 30.0 MW)
```

**Use Cases:**
- Testing binary delivery logic (30 MW > 25 MW target)
- Verifying excess charging behavior
- Simplifying energy balance calculations

#### solar_profile_zero.csv (No Solar)

```csv
timestamp,Solar_Generation_MW
2024-01-01 00:00,0.0
2024-01-01 01:00,0.0
...
(all 8760 rows = 0.0 MW)
```

**Use Cases:**
- Testing battery-only scenarios
- Verifying no delivery when no resources
- SOC depletion behavior

#### solar_profile_short.csv (Invalid - Too Few Rows)

```csv
timestamp,Solar_Generation_MW
2024-01-01 00:00,0.0
...
(only 1000 rows)
```

**Use Cases:**
- Testing validation warnings
- Error handling for incomplete data

#### solar_profile_invalid.csv (Invalid - Bad Values)

```csv
timestamp,Solar_Generation_MW
2024-01-01 00:00,-5.0
2024-01-01 01:00,150.0
2024-01-01 02:00,NaN
...
```

**Use Cases:**
- Testing data validation
- Negative value rejection
- Out-of-range detection

---

### 4.2 Test Configuration Sets

**File:** `tests/test_data/test_configs.json`

```json
{
  "minimal_valid": {
    "TARGET_DELIVERY_MW": 25.0,
    "SOLAR_CAPACITY_MW": 67.0,
    "MIN_SOC": 0.05,
    "MAX_SOC": 0.95,
    "ROUND_TRIP_EFFICIENCY": 0.87,
    "C_RATE_CHARGE": 1.0,
    "C_RATE_DISCHARGE": 1.0,
    "MIN_BATTERY_SIZE_MWH": 10,
    "MAX_BATTERY_SIZE_MWH": 500,
    "BATTERY_SIZE_STEP_MWH": 5,
    "MAX_DAILY_CYCLES": 2.0,
    "INITIAL_SOC": 0.5,
    "DEGRADATION_PER_CYCLE": 0.0015,
    "MARGINAL_IMPROVEMENT_THRESHOLD": 300,
    "MARGINAL_INCREMENT_MWH": 10
  },

  "extreme_battery": {
    "MIN_BATTERY_SIZE_MWH": 10,
    "MAX_BATTERY_SIZE_MWH": 1000,
    "BATTERY_SIZE_STEP_MWH": 50
  },

  "high_efficiency": {
    "ROUND_TRIP_EFFICIENCY": 0.95,
    "C_RATE_CHARGE": 2.0,
    "C_RATE_DISCHARGE": 2.0
  },

  "low_efficiency": {
    "ROUND_TRIP_EFFICIENCY": 0.75,
    "C_RATE_CHARGE": 0.5,
    "C_RATE_DISCHARGE": 0.5
  },

  "invalid_soc_range": {
    "MIN_SOC": 0.95,
    "MAX_SOC": 0.05
  },

  "invalid_negative_battery": {
    "MIN_BATTERY_SIZE_MWH": -10,
    "MAX_BATTERY_SIZE_MWH": 500
  },

  "invalid_efficiency": {
    "ROUND_TRIP_EFFICIENCY": 1.2
  }
}
```

---

## 5. Fixture Definitions

**File:** `tests/conftest.py`

```python
"""
Shared pytest fixtures for BESS Sizing Tool tests.

This module provides reusable fixtures for:
- Battery system instances with various initial states
- Solar profile data (realistic, flat, zero)
- Configuration dictionaries (valid and invalid)
- Simulation results for integration testing
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json

from src.battery_simulator import BatterySystem, simulate_bess_year
from src.config import (
    TARGET_DELIVERY_MW,
    SOLAR_CAPACITY_MW,
    MIN_SOC,
    MAX_SOC,
    ROUND_TRIP_EFFICIENCY,
    C_RATE_CHARGE,
    C_RATE_DISCHARGE,
    MIN_BATTERY_SIZE_MWH,
    MAX_BATTERY_SIZE_MWH,
    BATTERY_SIZE_STEP_MWH,
    MAX_DAILY_CYCLES,
    INITIAL_SOC,
    DEGRADATION_PER_CYCLE,
    MARGINAL_IMPROVEMENT_THRESHOLD,
    MARGINAL_INCREMENT_MWH
)


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def default_config():
    """Default configuration dictionary with all parameters."""
    return {
        'TARGET_DELIVERY_MW': TARGET_DELIVERY_MW,
        'SOLAR_CAPACITY_MW': SOLAR_CAPACITY_MW,
        'MIN_SOC': MIN_SOC,
        'MAX_SOC': MAX_SOC,
        'ROUND_TRIP_EFFICIENCY': ROUND_TRIP_EFFICIENCY,
        'ONE_WAY_EFFICIENCY': np.sqrt(ROUND_TRIP_EFFICIENCY),
        'C_RATE_CHARGE': C_RATE_CHARGE,
        'C_RATE_DISCHARGE': C_RATE_DISCHARGE,
        'MIN_BATTERY_SIZE_MWH': MIN_BATTERY_SIZE_MWH,
        'MAX_BATTERY_SIZE_MWH': MAX_BATTERY_SIZE_MWH,
        'BATTERY_SIZE_STEP_MWH': BATTERY_SIZE_STEP_MWH,
        'MAX_DAILY_CYCLES': MAX_DAILY_CYCLES,
        'INITIAL_SOC': INITIAL_SOC,
        'DEGRADATION_PER_CYCLE': DEGRADATION_PER_CYCLE,
        'MARGINAL_IMPROVEMENT_THRESHOLD': MARGINAL_IMPROVEMENT_THRESHOLD,
        'MARGINAL_INCREMENT_MWH': MARGINAL_INCREMENT_MWH
    }


@pytest.fixture
def test_configs():
    """Load test configuration sets from JSON file."""
    config_path = Path(__file__).parent / 'test_data' / 'test_configs.json'
    with open(config_path, 'r') as f:
        return json.load(f)


# =============================================================================
# Battery System Fixtures
# =============================================================================

@pytest.fixture
def battery_system_50mwh():
    """Standard 50 MWh battery at 50% SOC (midpoint)."""
    return BatterySystem(capacity=50.0, initial_soc=0.5)


@pytest.fixture
def battery_system_100mwh():
    """Standard 100 MWh battery at 50% SOC."""
    return BatterySystem(capacity=100.0, initial_soc=0.5)


@pytest.fixture
def battery_system_empty():
    """Battery at minimum SOC (5%) - almost empty."""
    return BatterySystem(capacity=100.0, initial_soc=0.05)


@pytest.fixture
def battery_system_full():
    """Battery at maximum SOC (95%) - almost full."""
    return BatterySystem(capacity=100.0, initial_soc=0.95)


@pytest.fixture
def battery_system_small():
    """Small 25 MWh battery at 50% SOC."""
    return BatterySystem(capacity=25.0, initial_soc=0.5)


@pytest.fixture
def battery_system_large():
    """Large 200 MWh battery at 50% SOC."""
    return BatterySystem(capacity=200.0, initial_soc=0.5)


# =============================================================================
# Solar Profile Fixtures
# =============================================================================

@pytest.fixture
def solar_profile_flat_30mw():
    """Flat 30 MW solar for all 8760 hours (above 25 MW target)."""
    return pd.Series([30.0] * 8760, name='Solar_Generation_MW')


@pytest.fixture
def solar_profile_flat_20mw():
    """Flat 20 MW solar for all 8760 hours (below 25 MW target)."""
    return pd.Series([20.0] * 8760, name='Solar_Generation_MW')


@pytest.fixture
def solar_profile_zero():
    """Zero solar for all 8760 hours (nighttime scenario)."""
    return pd.Series([0.0] * 8760, name='Solar_Generation_MW')


@pytest.fixture
def solar_profile_realistic():
    """
    Realistic solar profile with day/night cycles.

    Pattern:
    - Night (20:00-06:00): 0 MW
    - Morning ramp (06:00-12:00): Parabolic increase to ~65 MW
    - Afternoon ramp (12:00-18:00): Parabolic decrease to 0 MW
    - Peak hours (10:00-14:00): 50-65 MW
    """
    hours = []
    for day in range(365):
        for hour in range(24):
            if 6 <= hour <= 18:
                # Daytime: parabolic curve peaking at noon
                # Formula: solar = peak × (1 - ((hour - 12) / 6)^2)
                solar = 65.0 * (1 - ((hour - 12) / 6) ** 2)
            else:
                solar = 0.0
            hours.append(solar)

    return pd.Series(hours, name='Solar_Generation_MW')


@pytest.fixture
def solar_profile_cloudy():
    """
    Cloudy day pattern with reduced generation.

    Similar to realistic but only 50% of normal generation.
    """
    hours = []
    for day in range(365):
        for hour in range(24):
            if 6 <= hour <= 18:
                solar = 32.5 * (1 - ((hour - 12) / 6) ** 2)  # 50% of normal
            else:
                solar = 0.0
            hours.append(solar)

    return pd.Series(hours, name='Solar_Generation_MW')


@pytest.fixture
def solar_profile_high_variance():
    """
    High variance solar profile with random fluctuations.

    Simulates intermittent cloud cover.
    """
    np.random.seed(42)  # Reproducible randomness
    hours = []
    for day in range(365):
        for hour in range(24):
            if 6 <= hour <= 18:
                base = 65.0 * (1 - ((hour - 12) / 6) ** 2)
                # Add ±30% random variation
                solar = base * (1 + np.random.uniform(-0.3, 0.3))
                solar = max(0, solar)  # No negative values
            else:
                solar = 0.0
            hours.append(solar)

    return pd.Series(hours, name='Solar_Generation_MW')


# =============================================================================
# Simulation Result Fixtures
# =============================================================================

@pytest.fixture
def simulation_results_50mwh(solar_profile_realistic, default_config):
    """Pre-computed simulation results for 50 MWh battery."""
    return simulate_bess_year(
        battery_capacity=50.0,
        solar_profile=solar_profile_realistic,
        config=default_config
    )


@pytest.fixture
def simulation_results_100mwh(solar_profile_realistic, default_config):
    """Pre-computed simulation results for 100 MWh battery."""
    return simulate_bess_year(
        battery_capacity=100.0,
        solar_profile=solar_profile_realistic,
        config=default_config
    )


# =============================================================================
# Test Data Path Fixtures
# =============================================================================

@pytest.fixture
def test_data_dir():
    """Path to test_data directory."""
    return Path(__file__).parent / 'test_data'


@pytest.fixture
def solar_profile_full_path(test_data_dir):
    """Path to full valid solar profile CSV."""
    return test_data_dir / 'solar_profile_full.csv'


@pytest.fixture
def solar_profile_short_path(test_data_dir):
    """Path to short (invalid) solar profile CSV."""
    return test_data_dir / 'solar_profile_short.csv'


@pytest.fixture
def solar_profile_invalid_path(test_data_dir):
    """Path to invalid (negative values) solar profile CSV."""
    return test_data_dir / 'solar_profile_invalid.csv'
```

---

## 6. Example Test Implementations

### 6.1 Battery System Unit Tests

**File:** `tests/unit/test_battery_system.py`

```python
"""
Unit tests for BatterySystem class.

Tests cover:
- Initialization and validation
- Cycle counting (state transition based)
- Charging logic and efficiency
- Discharging logic and efficiency
- SOC calculations and boundaries
- Edge cases and error handling
"""

import pytest
import numpy as np
from src.battery_simulator import BatterySystem


class TestBatterySystemInitialization:
    """Tests for BatterySystem initialization."""

    def test_valid_initialization(self):
        """Battery initializes with correct attributes."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        assert battery.capacity == 100.0
        assert battery.soc == 0.5
        assert battery.state == 'IDLE'
        assert battery.total_cycles == 0.0
        assert battery.daily_cycles == 0.0
        assert battery.one_way_efficiency == pytest.approx(0.933, rel=0.001)

    def test_initial_soc_within_bounds(self):
        """Initial SOC must be within operational bounds."""
        battery = BatterySystem(capacity=50.0, initial_soc=0.5)

        assert battery.MIN_SOC <= battery.soc <= battery.MAX_SOC
        assert battery.soc >= 0.05
        assert battery.soc <= 0.95

    def test_zero_capacity_raises_error(self):
        """Zero capacity battery should raise ValueError."""
        with pytest.raises(ValueError, match="Capacity must be positive"):
            BatterySystem(capacity=0.0, initial_soc=0.5)

    def test_negative_capacity_raises_error(self):
        """Negative capacity should raise ValueError."""
        with pytest.raises(ValueError, match="Capacity must be positive"):
            BatterySystem(capacity=-50.0, initial_soc=0.5)

    def test_invalid_initial_soc_too_low(self):
        """Initial SOC below 0 should raise ValueError."""
        with pytest.raises(ValueError, match="Initial SOC"):
            BatterySystem(capacity=100.0, initial_soc=-0.1)

    def test_invalid_initial_soc_too_high(self):
        """Initial SOC above 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="Initial SOC"):
            BatterySystem(capacity=100.0, initial_soc=1.5)


class TestCycleCounting:
    """
    Tests for cycle counting logic.

    CRITICAL: Cycles are counted based on STATE TRANSITIONS, not charge/discharge events.
    Each transition from/to idle counts as 0.5 cycles.
    """

    def test_idle_to_charging_half_cycle(self):
        """IDLE → CHARGING transition adds 0.5 cycles."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.update_state_and_cycles('CHARGING', hour=1)

        assert battery.daily_cycles == 0.5
        assert battery.state == 'CHARGING'

    def test_charging_to_idle_full_cycle(self):
        """CHARGING → IDLE transition completes 1.0 cycle."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.update_state_and_cycles('CHARGING', hour=1)  # 0.5
        battery.update_state_and_cycles('IDLE', hour=2)       # 1.0

        assert battery.daily_cycles == 1.0
        assert battery.state == 'IDLE'

    def test_idle_to_discharging_half_cycle(self):
        """IDLE → DISCHARGING transition adds 0.5 cycles."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.update_state_and_cycles('DISCHARGING', hour=1)

        assert battery.daily_cycles == 0.5
        assert battery.state == 'DISCHARGING'

    def test_discharging_to_idle_full_cycle(self):
        """DISCHARGING → IDLE transition completes 1.0 cycle."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.update_state_and_cycles('DISCHARGING', hour=1)  # 0.5
        battery.update_state_and_cycles('IDLE', hour=2)         # 1.0

        assert battery.daily_cycles == 1.0
        assert battery.state == 'IDLE'

    def test_full_charge_discharge_cycle(self):
        """Complete charge/discharge cycle = 2.0 cycles."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.update_state_and_cycles('CHARGING', hour=1)     # 0.5
        battery.update_state_and_cycles('IDLE', hour=2)         # 1.0
        battery.update_state_and_cycles('DISCHARGING', hour=3)  # 1.5
        battery.update_state_and_cycles('IDLE', hour=4)         # 2.0

        assert battery.daily_cycles == 2.0

    def test_idle_to_idle_no_cycle(self):
        """IDLE → IDLE transition adds no cycles."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.update_state_and_cycles('IDLE', hour=1)
        battery.update_state_and_cycles('IDLE', hour=2)

        assert battery.daily_cycles == 0.0

    def test_charging_to_charging_no_cycle(self):
        """CHARGING → CHARGING (staying in state) adds no cycles."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.update_state_and_cycles('CHARGING', hour=1)  # 0.5
        battery.update_state_and_cycles('CHARGING', hour=2)  # Still 0.5

        assert battery.daily_cycles == 0.5

    def test_cycle_limit_blocks_transition(self):
        """can_cycle() returns False when at 2.0 cycles."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        # Manually set to cycle limit
        battery.daily_cycles = 2.0

        assert battery.can_cycle('DISCHARGING') == False
        assert battery.can_cycle('CHARGING') == False

    def test_cycle_limit_allows_transition_below_max(self):
        """can_cycle() returns True when below 2.0 cycles."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.daily_cycles = 1.5

        assert battery.can_cycle('DISCHARGING') == True
        assert battery.can_cycle('CHARGING') == True

    def test_daily_cycle_reset(self):
        """Cycles reset to 0.0 at day boundary (hour % 24 == 0)."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.daily_cycles = 1.5
        battery.update_state_and_cycles('IDLE', hour=24)  # New day

        assert battery.daily_cycles == 0.0


class TestChargingLogic:
    """Tests for battery charging with efficiency and limits."""

    def test_charge_applies_efficiency(self):
        """Charging applies 93.3% one-way efficiency."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)
        initial_soc = battery.soc

        charged = battery.charge(10.0)  # 10 MWh input

        # Expected: 10.0 × 0.933 = 9.33 MWh stored
        expected_stored = 10.0 * 0.933
        soc_increase = expected_stored / 100.0

        assert abs(battery.soc - (initial_soc + soc_increase)) < 0.001
        assert charged == pytest.approx(10.0, rel=0.01)

    def test_charge_updates_soc_correctly(self):
        """SOC increases by (energy_stored / capacity) × 100."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.charge(10.0)

        # Energy stored = 10.0 × 0.933 = 9.33 MWh
        # ΔSOC = 9.33 / 100 = 0.0933 (9.33%)
        expected_soc = 0.5 + 0.0933

        assert battery.soc == pytest.approx(expected_soc, rel=0.001)

    def test_charge_limited_by_headroom(self):
        """Charging stops at MAX_SOC (95%)."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.93)

        # Headroom = (0.95 - 0.93) × 100 = 2 MWh
        # After efficiency: Can accept ~2.14 MWh input
        charged = battery.charge(10.0)

        assert charged < 10.0  # Cannot charge full amount
        assert battery.soc <= 0.95  # Doesn't exceed MAX_SOC

    def test_charge_limited_by_c_rate(self):
        """Charging power limited by C-rate × capacity."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)
        battery.c_rate_charge = 0.5  # Max 50 MW

        charged = battery.charge(100.0)  # Try to charge 100 MWh in 1 hour

        assert charged <= 50.0  # Limited by C-rate

    def test_charge_returns_actual_energy(self):
        """charge() returns actual energy charged, not requested."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.93)

        charged = battery.charge(10.0)

        assert charged < 10.0  # Headroom limited
        assert charged > 0  # Some charging occurred

    def test_charge_at_max_soc_no_change(self):
        """No charging occurs when SOC = MAX_SOC."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.95)

        charged = battery.charge(10.0)

        assert charged == 0.0
        assert battery.soc == 0.95


class TestDischargingLogic:
    """Tests for battery discharging with efficiency and limits."""

    def test_discharge_applies_efficiency(self):
        """Discharging requires battery_energy = output / 0.933."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)
        initial_soc = battery.soc

        discharged = battery.discharge(10.0)  # Want 10 MWh output

        # Battery energy needed = 10.0 / 0.933 = 10.72 MWh
        battery_energy_used = 10.0 / 0.933
        soc_decrease = battery_energy_used / 100.0

        assert abs((initial_soc - battery.soc) - soc_decrease) < 0.001
        assert discharged == pytest.approx(10.0, rel=0.01)

    def test_discharge_updates_soc_correctly(self):
        """SOC decreases by (battery_energy / capacity) × 100."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        battery.discharge(10.0)

        # Battery energy = 10.0 / 0.933 = 10.72 MWh
        # ΔSOC = 10.72 / 100 = 0.1072 (10.72%)
        expected_soc = 0.5 - 0.1072

        assert battery.soc == pytest.approx(expected_soc, rel=0.001)

    def test_discharge_limited_by_available_energy(self):
        """Discharging stops at MIN_SOC (5%)."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.06)

        # Available = (0.06 - 0.05) × 100 = 1 MWh
        # Can output ~0.933 MWh
        discharged = battery.discharge(10.0)

        assert discharged < 10.0
        assert battery.soc >= 0.05  # Doesn't go below MIN_SOC

    def test_discharge_limited_by_c_rate(self):
        """Discharging power limited by C-rate × capacity."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)
        battery.c_rate_discharge = 0.5  # Max 50 MW

        discharged = battery.discharge(100.0)  # Try to discharge 100 MWh in 1 hour

        assert discharged <= 50.0  # Limited by C-rate

    def test_discharge_returns_actual_energy(self):
        """discharge() returns actual energy delivered, not requested."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.06)

        discharged = battery.discharge(10.0)

        assert discharged < 10.0  # Energy limited
        assert discharged > 0  # Some discharge occurred

    def test_discharge_at_min_soc_no_change(self):
        """No discharging occurs when SOC = MIN_SOC."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.05)

        discharged = battery.discharge(10.0)

        assert discharged == 0.0
        assert battery.soc == 0.05


class TestSOCCalculations:
    """Tests for SOC-related calculations."""

    def test_get_available_energy(self):
        """Available energy = (SOC - MIN_SOC) × capacity."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        available = battery.get_available_energy()
        expected = (0.5 - 0.05) * 100.0  # 45 MWh

        assert available == pytest.approx(expected, rel=0.001)

    def test_get_charge_headroom(self):
        """Charge headroom = (MAX_SOC - SOC) × capacity."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.5)

        headroom = battery.get_charge_headroom()
        expected = (0.95 - 0.5) * 100.0  # 45 MWh

        assert headroom == pytest.approx(expected, rel=0.001)

    def test_available_energy_at_min_soc(self):
        """Available energy = 0 when SOC = MIN_SOC."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.05)

        available = battery.get_available_energy()

        assert available == pytest.approx(0.0, abs=0.01)

    def test_charge_headroom_at_max_soc(self):
        """Charge headroom = 0 when SOC = MAX_SOC."""
        battery = BatterySystem(capacity=100.0, initial_soc=0.95)

        headroom = battery.get_charge_headroom()

        assert headroom == pytest.approx(0.0, abs=0.01)
```

---

### 6.2 Integration Tests - Binary Delivery

**File:** `tests/integration/test_simulation.py`

```python
"""
Integration tests for simulate_bess_year() function.

Tests cover:
- Binary delivery logic (25 MW or 0 MW)
- Energy conservation
- Operational constraints (SOC, cycles)
- Full year scenarios
- Edge cases
"""

import pytest
import pandas as pd
import numpy as np
from src.battery_simulator import simulate_bess_year


class TestBinaryDeliveryLogic:
    """Tests for binary delivery constraint (25 MW or 0 MW)."""

    def test_delivery_always_binary(self, solar_profile_realistic, default_config):
        """Delivery must always be 0 MW or 25 MW, never partial."""
        results = simulate_bess_year(
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        # Check committed_mw column
        delivered_values = results['committed_mw'].unique()

        # Should only contain 0.0 and 25.0
        assert set(delivered_values).issubset({0.0, 25.0})

        # Verify no partial delivery
        assert 0.0 < delivered_values.min() or delivered_values.min() == 0.0
        assert delivered_values.max() <= 25.0

    def test_excess_solar_delivers_and_charges(
        self,
        solar_profile_flat_30mw,
        default_config
    ):
        """
        When solar ≥ 25 MW, should:
        1. Deliver 25 MW
        2. Charge battery with excess (30 - 25 = 5 MW)
        """
        results = simulate_bess_year(
            battery_capacity=50.0,
            solar_profile=solar_profile_flat_30mw,
            config=default_config
        )

        # All hours should deliver
        assert (results['delivery'] == 'Yes').all()
        assert (results['committed_mw'] == 25.0).all()

        # Battery should be charging (negative bess_mw)
        charging_hours = (results['bess_mw'] < 0).sum()
        assert charging_hours > 0  # Should charge when excess solar

    def test_insufficient_resources_no_delivery(
        self,
        solar_profile_flat_20mw,
        default_config
    ):
        """
        When solar + battery < 25 MW, should not deliver.

        Scenario: 20 MW solar, 10 MWh battery
        - Max from battery: 10 MWh in 1 hour = 10 MW
        - Total available: 20 + 10 = 30 MW (sufficient)
        - But battery depletes quickly, then insufficient
        """
        results = simulate_bess_year(
            battery_capacity=10.0,  # Small battery
            solar_profile=solar_profile_flat_20mw,  # Below target
            config=default_config
        )

        # Should have some hours with no delivery
        no_delivery_hours = (results['delivery'] == 'No').sum()
        assert no_delivery_hours > 0

        # Deficit should be recorded when not delivering
        deficit_recorded = results[results['delivery'] == 'No']['deficit_mw'].sum()
        assert deficit_recorded > 0

    def test_cycle_limit_blocks_delivery(
        self,
        solar_profile_realistic,
        default_config
    ):
        """
        When cycle limit (2.0) reached, cannot discharge even if resources available.

        This tests that operational constraints override resource availability.
        """
        results = simulate_bess_year(
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        # Group by day and check for cycle-limited hours
        results['day'] = results['hour'] // 24

        daily_cycles = results.groupby('day').apply(
            lambda df: df['daily_cycles'].max()
        )

        # Find days that hit cycle limit
        max_cycle_days = daily_cycles[daily_cycles >= 1.9].index

        if len(max_cycle_days) > 0:
            # On days with high cycles, verify no delivery after limit
            for day in max_cycle_days:
                day_data = results[results['day'] == day]

                # Find hour when cycles hit ~2.0
                limit_hour = day_data[day_data['daily_cycles'] >= 1.9]['hour'].min()

                if not pd.isna(limit_hour):
                    # After limit, should not discharge
                    after_limit = day_data[day_data['hour'] > limit_hour]
                    if len(after_limit) > 0:
                        # If solar insufficient, should not deliver
                        insufficient_solar = after_limit[after_limit['solar_mw'] < 25.0]
                        if len(insufficient_solar) > 0:
                            assert (insufficient_solar['delivery'] == 'No').any()


class TestEnergyConservation:
    """Tests for energy balance and conservation laws."""

    def test_energy_balance(self, solar_profile_realistic, default_config):
        """
        Energy balance: Solar generated = Charged + Wasted + Direct delivery

        Total solar must equal sum of:
        1. Solar charged to battery
        2. Solar wasted (unused)
        3. Solar directly to load (when solar ≥ 25 MW)
        """
        results = simulate_bess_year(
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        # Calculate components
        total_solar = results['solar_mw'].sum()

        # Solar charged (when bess_mw < 0, battery is charging)
        solar_charged = abs(results[results['bess_mw'] < 0]['bess_mw'].sum())

        # Solar wasted
        solar_wasted = results['wastage_mwh'].sum()

        # Direct solar delivery (when solar ≥ 25 and delivering)
        direct_delivery_mask = (results['solar_mw'] >= 25.0) & (results['delivery'] == 'Yes')
        direct_solar = 25.0 * direct_delivery_mask.sum()  # 25 MW per hour

        # Battery discharge should not count (it's stored solar)

        # Total solar usage
        total_usage = solar_charged + solar_wasted + direct_solar

        # Allow small tolerance for numerical precision
        assert total_solar == pytest.approx(total_usage, rel=0.01)

    def test_no_energy_creation(self, solar_profile_realistic, default_config):
        """Battery never creates energy - output ≤ input (with efficiency loss)."""
        results = simulate_bess_year(
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        # Total energy charged to battery
        total_charged = abs(results[results['bess_mw'] < 0]['bess_mw'].sum())

        # Total energy discharged from battery
        total_discharged = results[results['bess_mw'] > 0]['bess_mw'].sum()

        # Round-trip efficiency = 87%, so:
        # total_discharged ≤ total_charged × 0.87
        max_expected_discharge = total_charged * 0.87

        assert total_discharged <= max_expected_discharge * 1.01  # 1% tolerance


class TestOperationalConstraints:
    """Tests for SOC and cycle limit constraints."""

    def test_soc_never_below_min(self, solar_profile_realistic, default_config):
        """SOC must never go below MIN_SOC (5%) for all 8760 hours."""
        results = simulate_bess_year(
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        min_soc = results['soc_percent'].min()

        assert min_soc >= 5.0  # MIN_SOC = 5%

        # Verify no violations
        violations = (results['soc_percent'] < 5.0).sum()
        assert violations == 0

    def test_soc_never_above_max(self, solar_profile_realistic, default_config):
        """SOC must never exceed MAX_SOC (95%) for all 8760 hours."""
        results = simulate_bess_year(
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        max_soc = results['soc_percent'].max()

        assert max_soc <= 95.0  # MAX_SOC = 95%

        # Verify no violations
        violations = (results['soc_percent'] > 95.0).sum()
        assert violations == 0

    def test_daily_cycles_never_exceed_max(
        self,
        solar_profile_realistic,
        default_config
    ):
        """Daily cycles must never exceed MAX_DAILY_CYCLES (2.0) for all 365 days."""
        results = simulate_bess_year(
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        # Group by day
        results['day'] = results['hour'] // 24
        daily_max_cycles = results.groupby('day')['daily_cycles'].max()

        # Check all days
        max_cycles = daily_max_cycles.max()

        assert max_cycles <= 2.0  # MAX_DAILY_CYCLES = 2.0

        # Verify no days exceed limit
        violations = (daily_max_cycles > 2.0).sum()
        assert violations == 0
```

---

## 7. Coverage Requirements

### Target Coverage Metrics

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| `src/battery_simulator.py` | ≥95% | CRITICAL |
| `src/data_loader.py` | ≥80% | High |
| `src/config.py` | ≥90% | Medium |
| `utils/validators.py` | ≥90% | High |
| `utils/metrics.py` | ≥85% | High |
| `utils/config_manager.py` | ≥80% | Medium |
| `utils/logger.py` | ≥70% | Low |
| **Overall Project** | **≥80%** | **Target** |

### Running Coverage Reports

```bash
# Terminal report
pytest --cov=src --cov=utils --cov-report=term

# HTML report (detailed)
pytest --cov=src --cov=utils --cov-report=html

# XML report (for CI/CD)
pytest --cov=src --cov=utils --cov-report=xml

# Missing lines report
pytest --cov=src --cov=utils --cov-report=term-missing
```

### Coverage Report Interpretation

**HTML Report Location:** `htmlcov/index.html`

**Key Metrics:**
- **Statements:** Total lines of executable code
- **Missing:** Lines not covered by tests
- **Branch:** Decision points (if/else) coverage
- **Partial:** Branches only partially covered

**Example Output:**
```
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
src/battery_simulator.py            285     12    96%   45-47, 123
src/data_loader.py                  145     25    83%   67-72, 89-95
src/config.py                        42      0   100%
utils/validators.py                 111      8    93%   78-82
utils/metrics.py                    198     22    89%   145-152, 187
utils/config_manager.py              87     15    83%   45-51
---------------------------------------------------------------
TOTAL                               868     82    91%
```

---

## 8. Performance Benchmarks

### 8.1 Performance Test Suite

**File:** `tests/performance/test_benchmarks.py`

```python
"""
Performance benchmarks for BESS simulation.

Benchmarks:
- Single simulation speed (target: <5 seconds)
- Optimization scan speed (target: <90 seconds for 100 simulations)
- Memory usage
- Scalability tests
"""

import pytest
from src.battery_simulator import simulate_bess_year


class TestSimulationPerformance:
    """Performance tests for single simulations."""

    def test_single_simulation_speed(
        self,
        benchmark,
        solar_profile_realistic,
        default_config
    ):
        """
        Single simulation should complete in <5 seconds.

        Benchmark: 100 MWh battery, realistic solar, full year (8760 hours)
        """
        result = benchmark(
            simulate_bess_year,
            battery_capacity=100.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        # Check performance
        assert benchmark.stats['mean'] < 5.0  # seconds
        assert len(result) == 8760  # Verify full year

    def test_small_battery_simulation(
        self,
        benchmark,
        solar_profile_realistic,
        default_config
    ):
        """Small battery (25 MWh) should be fast."""
        result = benchmark(
            simulate_bess_year,
            battery_capacity=25.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        assert benchmark.stats['mean'] < 3.0  # seconds

    def test_large_battery_simulation(
        self,
        benchmark,
        solar_profile_realistic,
        default_config
    ):
        """Large battery (500 MWh) should still be reasonable."""
        result = benchmark(
            simulate_bess_year,
            battery_capacity=500.0,
            solar_profile=solar_profile_realistic,
            config=default_config
        )

        assert benchmark.stats['mean'] < 8.0  # seconds


class TestOptimizationPerformance:
    """Performance tests for optimization scans."""

    def test_optimization_scan_100_sizes(
        self,
        benchmark,
        solar_profile_realistic,
        default_config
    ):
        """
        100 simulations (10-500 MWh, 5 MWh step) should complete in <90 seconds.

        This represents a full optimization scan.
        """
        def run_optimization_scan():
            results = []
            for size in range(10, 510, 5):  # 10, 15, 20, ..., 505
                result = simulate_bess_year(
                    battery_capacity=size,
                    solar_profile=solar_profile_realistic,
                    config=default_config
                )
                results.append(result)
            return results

        results = benchmark(run_optimization_scan)

        assert benchmark.stats['mean'] < 90.0  # seconds
        assert len(results) == 100  # Verify all simulations ran

    def test_parallel_potential(
        self,
        benchmark,
        solar_profile_realistic,
        default_config
    ):
        """
        Measure baseline for potential parallel execution.

        Sequential execution of 10 simulations.
        """
        def run_10_sequential():
            results = []
            for size in [25, 50, 75, 100, 125, 150, 175, 200, 225, 250]:
                result = simulate_bess_year(
                    battery_capacity=size,
                    solar_profile=solar_profile_realistic,
                    config=default_config
                )
                results.append(result)
            return results

        results = benchmark(run_10_sequential)

        # Document baseline for future parallel implementation
        print(f"\nBaseline 10 simulations: {benchmark.stats['mean']:.2f}s")
```

### 8.2 Performance Targets

| Operation | Target | Measured | Status |
|-----------|--------|----------|--------|
| Single simulation (100 MWh) | <5s | TBD | ⏳ |
| Optimization scan (100 sizes) | <90s | TBD | ⏳ |
| Small battery (25 MWh) | <3s | TBD | ⏳ |
| Large battery (500 MWh) | <8s | TBD | ⏳ |

**Running Benchmarks:**
```bash
pytest tests/performance/ --benchmark-only
pytest tests/performance/ --benchmark-only --benchmark-verbose
pytest tests/performance/ --benchmark-save=baseline
```

---

## 9. CI/CD Integration

### 9.1 GitHub Actions Workflow

**File:** `.github/workflows/tests.yml`

```yaml
name: Automated Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:  # Allow manual triggering

jobs:
  test:
    name: Run Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10', '3.11']

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-mock pytest-benchmark

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src --cov=utils --cov-report=xml --cov-report=term

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: false

    - name: Generate coverage badge
      if: matrix.python-version == '3.10'
      run: |
        coverage-badge -o coverage.svg -f

    - name: Archive test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-results-${{ matrix.python-version }}
        path: |
          htmlcov/
          coverage.xml
          .coverage

  performance:
    name: Performance Benchmarks
    runs-on: ubuntu-latest
    needs: test  # Only run if tests pass

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python 3.10
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-benchmark

    - name: Run performance benchmarks
      run: |
        pytest tests/performance/ --benchmark-only --benchmark-json=benchmark.json

    - name: Store benchmark results
      uses: benchmark-action/github-action-benchmark@v1
      with:
        name: Python Benchmark
        tool: 'pytest'
        output-file-path: benchmark.json
        github-token: ${{ secrets.GITHUB_TOKEN }}
        auto-push: true
```

### 9.2 Pre-commit Hooks (Optional)

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest
        entry: pytest tests/unit/ tests/integration/
        language: system
        pass_filenames: false
        always_run: true
```

**Installation:**
```bash
pip install pre-commit
pre-commit install
```

---

## 10. Implementation Checklist

### Phase 1: Foundation (2-4 hours)

- [ ] Create `tests/` directory structure
- [ ] Add pytest dependencies to `requirements.txt`
- [ ] Create `conftest.py` with basic fixtures
- [ ] Generate test solar profiles:
  - [ ] `solar_profile_full.csv` (8760 hours, realistic)
  - [ ] `solar_profile_flat_30mw.csv` (constant 30 MW)
  - [ ] `solar_profile_zero.csv` (all zeros)
  - [ ] `solar_profile_short.csv` (invalid, <8760)
  - [ ] `solar_profile_invalid.csv` (negative values)
- [ ] Create `test_configs.json` with test configuration sets
- [ ] Verify pytest installation: `pytest --version`

### Phase 2: Unit Tests - BatterySystem (6-8 hours)

- [ ] Create `tests/unit/test_battery_system.py`
- [ ] Implement initialization tests (5 tests)
- [ ] Implement cycle counting tests (8 tests) - CRITICAL
- [ ] Implement daily cycle reset test (1 test)
- [ ] Implement charging logic tests (6 tests)
- [ ] Implement discharging logic tests (6 tests)
- [ ] Implement SOC calculation tests (4 tests)
- [ ] Run tests: `pytest tests/unit/test_battery_system.py -v`
- [ ] Achieve ≥95% coverage on `battery_simulator.py`

### Phase 3: Unit Tests - Other Modules (4-6 hours)

- [ ] Create `tests/unit/test_validators.py`
  - [ ] 12+ validation tests
- [ ] Create `tests/unit/test_metrics.py`
  - [ ] Wastage calculation tests (CRITICAL - Bug #1 fix verification)
  - [ ] Delivery metrics tests (4 tests)
  - [ ] Cycling metrics tests (3 tests)
  - [ ] Degradation tests (2 tests)
  - [ ] Solar utilization tests (2 tests)
- [ ] Create `tests/unit/test_data_loader.py`
  - [ ] Solar profile loading tests (8 tests)
  - [ ] Statistics calculation tests (4 tests)
- [ ] Create `tests/unit/test_config_manager.py`
  - [ ] Configuration get/update tests
- [ ] Run all unit tests: `pytest tests/unit/ -v`

### Phase 4: Integration Tests (4-6 hours)

- [ ] Create `tests/integration/test_simulation.py`
- [ ] Implement binary delivery logic tests (4 tests) - CRITICAL
- [ ] Implement full year scenario tests (5 tests)
- [ ] Implement energy conservation tests (3 tests)
- [ ] Implement operational constraint tests (4 tests)
- [ ] Implement edge case day tests (4 tests)
- [ ] Create `tests/integration/test_optimization.py`
  - [ ] High-Yield Knee algorithm tests
  - [ ] Marginal Improvement algorithm tests
- [ ] Run integration tests: `pytest tests/integration/ -v`

### Phase 5: Performance & CI/CD (2-4 hours)

- [ ] Create `tests/performance/test_benchmarks.py`
- [ ] Implement simulation speed benchmarks (3 tests)
- [ ] Implement optimization scan benchmark (1 test)
- [ ] Run benchmarks: `pytest tests/performance/ --benchmark-only`
- [ ] Create `.github/workflows/tests.yml` (GitHub Actions)
- [ ] Configure Codecov integration
- [ ] Test CI/CD pipeline with dummy commit
- [ ] Set up coverage badge in README

### Phase 6: Documentation & Finalization (1-2 hours)

- [ ] Update `README.md` with testing instructions
- [ ] Add testing section to `PROJECT_DOCUMENTATION.md`
- [ ] Document any discovered bugs in `bug_report_analysis.md`
- [ ] Create `TESTING_GUIDE.md` (this document)
- [ ] Generate final coverage report
- [ ] Review and close any testing gaps
- [ ] Tag release with testing infrastructure

---

## Summary

### Minimum Viable Test Suite

**Test Count:** ~87 tests minimum

| Category | Test Count | Files |
|----------|-----------|-------|
| BatterySystem Unit Tests | 30+ | `test_battery_system.py` |
| Validation Tests | 12+ | `test_validators.py` |
| Metrics Tests | 15+ | `test_metrics.py` |
| Data Loader Tests | 10+ | `test_data_loader.py` |
| Integration Tests | 20+ | `test_simulation.py`, `test_optimization.py` |
| **Total** | **~87+** | **6 test files** |

### Coverage Targets

- **Overall:** ≥80%
- **Core Simulation:** ≥95%
- **Validators:** ≥90%
- **Metrics:** ≥85%

### Estimated Effort

| Phase | Hours | Priority |
|-------|-------|----------|
| Phase 1: Foundation | 2-4 | High |
| Phase 2: BatterySystem Unit Tests | 6-8 | Critical |
| Phase 3: Other Unit Tests | 4-6 | High |
| Phase 4: Integration Tests | 4-6 | High |
| Phase 5: Performance & CI/CD | 2-4 | Medium |
| Phase 6: Documentation | 1-2 | Low |
| **Total** | **19-30** | - |

### Critical Tests (Must Have)

1. ✅ Cycle counting (state transition based)
2. ✅ Binary delivery logic (no partial delivery)
3. ✅ Efficiency calculations (93.3% one-way)
4. ✅ SOC boundaries (5%-95%)
5. ✅ Wastage calculation (Bug #1 fix verification)
6. ✅ Energy conservation
7. ✅ Operational constraints (cycles, SOC)

---

## Next Steps

**To begin implementation:**

1. **Create test directory structure**
   ```bash
   mkdir -p tests/unit tests/integration tests/performance tests/test_data
   touch tests/__init__.py
   touch tests/unit/__init__.py
   touch tests/integration/__init__.py
   touch tests/performance/__init__.py
   ```

2. **Install test dependencies**
   ```bash
   pip install pytest pytest-cov pytest-mock pytest-benchmark
   ```

3. **Create first test file**
   ```bash
   # Start with battery_system tests (most critical)
   touch tests/unit/test_battery_system.py
   ```

4. **Run initial tests**
   ```bash
   pytest tests/ -v
   ```

**Ready to implement the complete test suite!**
