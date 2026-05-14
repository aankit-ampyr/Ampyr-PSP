# BESS & DG Sizing Tool - Algorithm Specification

**Version:** 1.0  
**Status:** APPROVED FOR IMPLEMENTATION  
**Last Updated:** 2025-12-02  
**Purpose:** Single consolidated reference for all dispatch algorithms

---

## Table of Contents

1. [Execution Flow Overview](#1-execution-flow-overview)
2. [Phase 1: Input Validation](#2-phase-1-input-validation)
3. [Phase 2: Initialization](#3-phase-2-initialization)
4. [Phase 3: Hourly Dispatch Loop](#4-phase-3-hourly-dispatch-loop)
5. [Phase 4: Summary Metrics](#5-phase-4-summary-metrics)
6. [Phase 5: Sizing Mode Wrapper](#6-phase-5-sizing-mode-wrapper)
7. [Template-Specific Logic](#7-template-specific-logic)
8. [Data Structures](#8-data-structures)

---

## 1. Execution Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│  - Load profile (8760 values)                                   │
│  - Solar profile (8760 values)                                  │
│  - BESS parameters (capacity, efficiency, SoC limits)           │
│  - DG parameters (capacity, charges_bess)                       │
│  - Template selection (0-6)                                     │
│  - Mode: Fixed Size OR Sizing Mode                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 1: INPUT VALIDATION                      │
│  - Check parameter bounds                                        │
│  - Validate threshold ordering (template-specific)              │
│  - Calculate simulation count (if Sizing Mode)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│      FIXED MODE         │     │         SIZING MODE              │
│  Single configuration   │     │  Loop: capacity × duration × DG  │
└─────────────────────────┘     └─────────────────────────────────┘
              │                               │
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 2: INITIALIZATION (per config)                │
│  - Calculate derived constants                                   │
│  - Set power limits                                             │
│  - Initialize state variables                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 3: HOURLY DISPATCH LOOP                       │
│  FOR t = 1 TO 8760:                                             │
│    Step 0: Daily reset check                                    │
│    Step 1: Initialize hourly variables                          │
│    Step 2: Solar direct to load                                 │
│    Step 3: BESS charging (template-specific timing)             │
│    Step 4: BESS discharging                                     │
│    Step 5: DG dispatch (template-specific logic)                │
│    Step 6: Calculate unserved                                   │
│    Step 7: SoC clamping                                         │
│    Step 8: Record hourly results                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 4: SUMMARY METRICS                            │
│  - Aggregate energy totals                                      │
│  - Calculate delivery percentages                               │
│  - Calculate BESS and DG metrics                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│      FIXED MODE         │     │         SIZING MODE              │
│  Return single result   │     │  Append to comparison table     │
│                         │     │  Loop to next configuration     │
│                         │     │  Flag dominated configs         │
└─────────────────────────┘     └─────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUT                                   │
│  Fixed: Single simulation results + hourly data                 │
│  Sizing: Comparison table + optional hourly data per config     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: Input Validation

### 2.1 Common Validation (All Templates)

```python
def validate_common_inputs(params):
    errors = []
    warnings = []
    
    # ═══════════════════════════════════════════════════════════════
    # PROFILE VALIDATION
    # ═══════════════════════════════════════════════════════════════
    
    if len(params.load_profile) != 8760:
        errors.append("Load profile must have exactly 8760 values")
    
    if len(params.solar_profile) != 8760:
        errors.append("Solar profile must have exactly 8760 values")
    
    if any(v < 0 for v in params.load_profile):
        errors.append("Load profile cannot contain negative values")
    
    if any(v < 0 for v in params.solar_profile):
        errors.append("Solar profile cannot contain negative values")
    
    # ═══════════════════════════════════════════════════════════════
    # BESS PARAMETER VALIDATION
    # ═══════════════════════════════════════════════════════════════
    
    if params.bess_capacity <= 0:
        errors.append("BESS capacity must be positive")
    
    if params.bess_efficiency <= 0 or params.bess_efficiency > 100:
        errors.append("BESS efficiency must be between 0 and 100")
    
    if params.bess_min_soc < 0 or params.bess_min_soc >= 100:
        errors.append("BESS min_soc must be between 0 and 100")
    
    if params.bess_max_soc <= 0 or params.bess_max_soc > 100:
        errors.append("BESS max_soc must be between 0 and 100")
    
    if params.bess_min_soc >= params.bess_max_soc:
        errors.append("BESS min_soc must be less than max_soc")
    
    if params.bess_initial_soc < params.bess_min_soc:
        errors.append("BESS initial_soc cannot be below min_soc")
    
    if params.bess_initial_soc > params.bess_max_soc:
        errors.append("BESS initial_soc cannot exceed max_soc")
    
    # ═══════════════════════════════════════════════════════════════
    # FIXED MODE ONLY: Power and C-rate validation
    # ═══════════════════════════════════════════════════════════════
    
    if not params.sizing_mode:
        if params.bess_charge_power <= 0:
            errors.append("BESS charge power must be positive")
        
        if params.bess_discharge_power <= 0:
            errors.append("BESS discharge power must be positive")
        
        if params.bess_charge_c_rate <= 0:
            errors.append("BESS charge C-rate must be positive")
        
        if params.bess_discharge_c_rate <= 0:
            errors.append("BESS discharge C-rate must be positive")
    
    # ═══════════════════════════════════════════════════════════════
    # SIZING MODE VALIDATION
    # ═══════════════════════════════════════════════════════════════
    
    if params.sizing_mode:
        if params.bess_capacity_min <= 0:
            errors.append("BESS capacity_min must be positive")
        
        if params.bess_capacity_max < params.bess_capacity_min:
            errors.append("BESS capacity_max must be >= capacity_min")
        
        if params.bess_capacity_step <= 0:
            errors.append("BESS capacity_step must be positive")
        
        # Calculate simulation count
        capacity_steps = ((params.bess_capacity_max - params.bess_capacity_min) 
                          // params.bess_capacity_step) + 1
        duration_classes = 7
        dg_steps = 1  # Will be updated if DG enabled
        
        if params.dg_enabled:
            if params.dg_capacity_min < 0:
                errors.append("DG capacity_min cannot be negative")
            
            if params.dg_capacity_max < params.dg_capacity_min:
                errors.append("DG capacity_max must be >= capacity_min")
            
            if params.dg_capacity_step <= 0:
                errors.append("DG capacity_step must be positive")
            
            dg_steps = ((params.dg_capacity_max - params.dg_capacity_min) 
                        // params.dg_capacity_step) + 1
        
        total_simulations = capacity_steps * duration_classes * dg_steps
        
        if total_simulations > 50000:
            errors.append(f"Too many simulations ({total_simulations}). "
                         "Reduce range or increase step size. Max: 50,000")
        elif total_simulations > 10000:
            warnings.append(f"Large simulation set ({total_simulations}). "
                           "May take longer to complete.")
    
    # ═══════════════════════════════════════════════════════════════
    # DG VALIDATION (if enabled)
    # ═══════════════════════════════════════════════════════════════
    
    if params.dg_enabled and not params.sizing_mode:
        if params.dg_capacity <= 0:
            errors.append("DG capacity must be positive")
    
    return errors, warnings
```

### 2.2 Template-Specific Validation

```python
def validate_template_specific(template_id, params):
    errors = []
    warnings = []
    
    # ═══════════════════════════════════════════════════════════════
    # TEMPLATES 2, 4, 5, 6: SoC Threshold Validation
    # ═══════════════════════════════════════════════════════════════
    
    if template_id in [2, 4, 5, 6]:
        # Threshold ordering (CRITICAL)
        if params.dg_soc_on_threshold >= params.dg_soc_off_threshold:
            errors.append("DG ON threshold must be strictly less than OFF threshold")
        
        # Threshold bounds
        if params.dg_soc_on_threshold < params.bess_min_soc:
            errors.append("DG ON threshold cannot be below BESS min SoC")
        
        if params.dg_soc_off_threshold > params.bess_max_soc:
            errors.append("DG OFF threshold cannot exceed BESS max SoC")
        
        # Deadband warning
        deadband = params.dg_soc_off_threshold - params.dg_soc_on_threshold
        if deadband < 20:
            warnings.append("Small deadband (<20%) may result in frequent DG cycling")
    
    # ═══════════════════════════════════════════════════════════════
    # TEMPLATES 2, 5, 6: Emergency SoC Validation
    # ═══════════════════════════════════════════════════════════════
    
    if template_id in [2, 5, 6]:
        if params.emergency_soc_threshold < params.bess_min_soc:
            errors.append("Emergency SoC threshold cannot be below BESS min SoC")
        
        if params.emergency_soc_threshold >= params.dg_soc_on_threshold:
            warnings.append("Emergency threshold >= DG ON threshold - "
                          "emergency may never trigger")
    
    # ═══════════════════════════════════════════════════════════════
    # TEMPLATES 2, 5, 6: Time Window Validation
    # ═══════════════════════════════════════════════════════════════
    
    if template_id == 2:  # Night Charge
        if params.night_start_hour < 0 or params.night_start_hour > 23:
            errors.append("Night start hour must be between 0 and 23")
        if params.night_end_hour < 0 or params.night_end_hour > 23:
            errors.append("Night end hour must be between 0 and 23")
        if params.night_start_hour == params.night_end_hour:
            warnings.append("Night window is 0 hours - no night charging will occur")
    
    if template_id == 5:  # Day Charge
        if params.day_start_hour < 0 or params.day_start_hour > 23:
            errors.append("Day start hour must be between 0 and 23")
        if params.day_end_hour < 0 or params.day_end_hour > 23:
            errors.append("Day end hour must be between 0 and 23")
        if params.day_start_hour == params.day_end_hour:
            warnings.append("Day window is 0 hours - DG will be disabled at all times")
    
    if template_id == 6:  # Night SoC Trigger
        if params.night_start_hour < 0 or params.night_start_hour > 23:
            errors.append("Night start hour must be between 0 and 23")
        if params.night_end_hour < 0 or params.night_end_hour > 23:
            errors.append("Night end hour must be between 0 and 23")
        if params.night_start_hour == params.night_end_hour:
            warnings.append("Night window is 0 hours - DG will be disabled at all times")
    
    # ═══════════════════════════════════════════════════════════════
    # TEMPLATE 3: Blackout Window Validation
    # ═══════════════════════════════════════════════════════════════
    
    if template_id == 3:
        if params.blackout_start_hour < 0 or params.blackout_start_hour > 23:
            errors.append("Blackout start hour must be between 0 and 23")
        if params.blackout_end_hour < 0 or params.blackout_end_hour > 23:
            errors.append("Blackout end hour must be between 0 and 23")
        if params.blackout_start_hour == params.blackout_end_hour:
            warnings.append("Blackout window is 0 hours - behaves like Template 1")
        
        # Calculate blackout duration
        if params.blackout_start_hour < params.blackout_end_hour:
            blackout_duration = params.blackout_end_hour - params.blackout_start_hour
        elif params.blackout_start_hour > params.blackout_end_hour:
            blackout_duration = (24 - params.blackout_start_hour) + params.blackout_end_hour
        else:
            blackout_duration = 0
        
        if blackout_duration > 12:
            warnings.append("Long blackout window (>12 hours) may result in high "
                          "unserved energy. Consider increasing battery size.")
    
    # ═══════════════════════════════════════════════════════════════
    # CYCLE LIMIT ENFORCEMENT OVERRIDES
    # ═══════════════════════════════════════════════════════════════
    
    if template_id == 4:  # Emergency Only - forced to monitor-only
        if params.bess_enforce_cycle_limit:
            warnings.append("Template 4 does not support cycle limit enforcement. "
                          "Setting to False.")
            params.bess_enforce_cycle_limit = False
    
    if template_id == 5:  # Day Charge - forced to monitor-only
        if params.bess_enforce_cycle_limit:
            warnings.append("Template 5 uses monitor-only cycle counting. "
                          "Setting enforce to False.")
            params.bess_enforce_cycle_limit = False
    
    return errors, warnings
```

---

## 3. Phase 2: Initialization

```python
def initialize_simulation(params, sizing_config=None):
    """
    Initialize simulation for a single configuration.
    
    Args:
        params: User input parameters
        sizing_config: Optional dict with {capacity, duration, power, dg_size}
                      Only provided in Sizing Mode
    
    Returns:
        SimulationState object with all derived constants and initial state
    """
    
    state = SimulationState()
    
    # ═══════════════════════════════════════════════════════════════
    # DETERMINE BESS CAPACITY AND POWER
    # ═══════════════════════════════════════════════════════════════
    
    if sizing_config:
        # Sizing Mode: Use values from iteration
        state.bess_capacity = sizing_config['capacity']
        state.bess_charge_power = sizing_config['power']
        state.bess_discharge_power = sizing_config['power']
        state.dg_capacity = sizing_config['dg_size']
        state.duration = sizing_config['duration']
    else:
        # Fixed Mode: Use user inputs
        state.bess_capacity = params.bess_capacity
        state.bess_charge_power = params.bess_charge_power
        state.bess_discharge_power = params.bess_discharge_power
        state.dg_capacity = params.dg_capacity if params.dg_enabled else 0
        state.duration = state.bess_capacity / state.bess_discharge_power
    
    # ═══════════════════════════════════════════════════════════════
    # BESS CAPACITY LIMITS (MWh)
    # ═══════════════════════════════════════════════════════════════
    
    state.usable_capacity = (state.bess_capacity * 
                             (params.bess_max_soc - params.bess_min_soc) / 100)
    state.min_soc_mwh = state.bess_capacity * params.bess_min_soc / 100
    state.max_soc_mwh = state.bess_capacity * params.bess_max_soc / 100
    
    # ═══════════════════════════════════════════════════════════════
    # BESS POWER LIMITS (MW)
    # ═══════════════════════════════════════════════════════════════
    
    if sizing_config:
        # Sizing Mode: Power already set by duration class
        state.charge_power_limit = state.bess_charge_power
        state.discharge_power_limit = state.bess_discharge_power
    else:
        # Fixed Mode: Apply C-rate constraint
        state.charge_power_limit = min(
            state.bess_charge_power,
            state.bess_capacity * params.bess_charge_c_rate
        )
        state.discharge_power_limit = min(
            state.bess_discharge_power,
            state.bess_capacity * params.bess_discharge_c_rate
        )
    
    # ═══════════════════════════════════════════════════════════════
    # EFFICIENCY FACTORS
    # ═══════════════════════════════════════════════════════════════
    
    state.charge_efficiency = math.sqrt(params.bess_efficiency / 100)
    state.discharge_efficiency = math.sqrt(params.bess_efficiency / 100)
    
    # ═══════════════════════════════════════════════════════════════
    # SOC THRESHOLDS (MWh) - For templates with SoC triggers
    # ═══════════════════════════════════════════════════════════════
    
    if hasattr(params, 'dg_soc_on_threshold'):
        state.dg_soc_on_mwh = state.bess_capacity * params.dg_soc_on_threshold / 100
        state.dg_soc_off_mwh = state.bess_capacity * params.dg_soc_off_threshold / 100
    
    if hasattr(params, 'emergency_soc_threshold'):
        state.emergency_soc_mwh = state.bess_capacity * params.emergency_soc_threshold / 100
    
    # ═══════════════════════════════════════════════════════════════
    # TIME WINDOW PRE-CALCULATION
    # ═══════════════════════════════════════════════════════════════
    
    if hasattr(params, 'night_window_mode'):
        state.is_night_hour = build_night_hour_array(params)
    
    if hasattr(params, 'day_window_mode'):
        state.is_day_hour = build_day_hour_array(params)
    
    if hasattr(params, 'blackout_start_hour'):
        state.is_blackout_hour = build_blackout_hour_array(params)
    
    # ═══════════════════════════════════════════════════════════════
    # INITIAL STATE VARIABLES
    # ═══════════════════════════════════════════════════════════════
    
    state.soc = state.bess_capacity * params.bess_initial_soc / 100
    state.daily_discharge = 0
    state.daily_cycles = 0
    state.bess_disabled_today = False
    state.current_day = 1
    state.dg_was_running = False
    
    # Counters for summary metrics
    state.total_dg_starts = 0
    state.total_dg_runtime_hours = 0
    
    # Per-day tracking
    state.max_daily_cycles_per_day = [0] * 365
    
    return state


def build_night_hour_array(params):
    """Build boolean array [0..23] indicating which hours are night."""
    is_night = [False] * 24
    
    if params.night_window_mode == "Dynamic":
        # Determine from solar profile
        daylight_hours = set()
        for t in range(8760):
            hour_of_day = t % 24
            if params.solar_profile[t] > 0.01:  # Epsilon filter
                daylight_hours.add(hour_of_day)
        
        for h in range(24):
            is_night[h] = (h not in daylight_hours)
    else:
        # Fixed window
        start = params.night_start_hour
        end = params.night_end_hour
        
        if start < end:
            # Night does not span midnight (unusual)
            for h in range(start, end):
                is_night[h] = True
        elif start > end:
            # Night spans midnight (typical: 18-6)
            for h in range(start, 24):
                is_night[h] = True
            for h in range(0, end):
                is_night[h] = True
        # If start == end, no night hours (is_night remains all False)
    
    return is_night


def build_day_hour_array(params):
    """Build boolean array [0..23] indicating which hours are day."""
    is_day = [False] * 24
    
    if params.day_window_mode == "Dynamic":
        # Determine from solar profile
        for t in range(8760):
            hour_of_day = t % 24
            if params.solar_profile[t] > 0.01:
                is_day[hour_of_day] = True
    else:
        # Fixed window
        start = params.day_start_hour
        end = params.day_end_hour
        
        if start < end:
            # Normal day window (e.g., 6-18)
            for h in range(start, end):
                is_day[h] = True
        elif start > end:
            # Day spans midnight (unusual)
            for h in range(start, 24):
                is_day[h] = True
            for h in range(0, end):
                is_day[h] = True
        # If start == end, no day hours
    
    return is_day


def build_blackout_hour_array(params):
    """Build boolean array [0..23] indicating which hours are blackout."""
    is_blackout = [False] * 24
    
    start = params.blackout_start_hour
    end = params.blackout_end_hour
    
    if start < end:
        # Blackout does not span midnight
        for h in range(start, end):
            is_blackout[h] = True
    elif start > end:
        # Blackout spans midnight
        for h in range(start, 24):
            is_blackout[h] = True
        for h in range(0, end):
            is_blackout[h] = True
    # If start == end, no blackout hours
    
    return is_blackout
```

---

## 4. Phase 3: Hourly Dispatch Loop

### 4.1 Main Loop Structure

```python
def run_simulation(params, state, template_id):
    """
    Execute 8760-hour simulation.
    
    Args:
        params: User input parameters
        state: Initialized SimulationState
        template_id: Which template (0-6) to run
    
    Returns:
        List of 8760 HourlyResult objects
    """
    
    results = []
    
    for t in range(8760):
        
        # ═══════════════════════════════════════════════════════════
        # STEP 0: DAILY RESET CHECK
        # ═══════════════════════════════════════════════════════════
        
        day_of_year = (t // 24) + 1
        
        if day_of_year > state.current_day:
            # Save previous day's max cycles
            state.max_daily_cycles_per_day[state.current_day - 1] = state.daily_cycles
            
            # Reset for new day
            state.current_day = day_of_year
            state.daily_discharge = 0
            state.daily_cycles = 0
            state.bess_disabled_today = False
        
        # ═══════════════════════════════════════════════════════════
        # STEP 1: INITIALIZE HOURLY VARIABLES
        # ═══════════════════════════════════════════════════════════
        
        hour = HourlyResult()
        hour.t = t + 1  # 1-indexed for output
        hour.day = day_of_year
        hour.hour_of_day = t % 24
        
        hour.load = params.load_profile[t]
        hour.solar = params.solar_profile[t]
        
        # Initialize all flows to zero
        hour.solar_to_load = 0
        hour.solar_to_bess = 0
        hour.solar_curtailed = 0
        hour.bess_to_load = 0
        hour.dg_to_load = 0
        hour.dg_to_bess = 0
        hour.dg_curtailed = 0
        hour.dg_running = False
        hour.dg_mode = "OFF"
        hour.bess_assisted = False
        hour.unserved = 0
        
        remaining_load = hour.load
        bess_discharged_this_hour = False
        charge_power_used = 0
        
        # ═══════════════════════════════════════════════════════════
        # STEP 2: SOLAR DIRECT TO LOAD
        # ═══════════════════════════════════════════════════════════
        
        hour.solar_to_load = min(hour.solar, remaining_load)
        remaining_load -= hour.solar_to_load
        excess_solar = hour.solar - hour.solar_to_load
        
        # ═══════════════════════════════════════════════════════════
        # STEPS 3-5: TEMPLATE-SPECIFIC DISPATCH
        # ═══════════════════════════════════════════════════════════
        
        if template_id == 0:
            remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used = \
                dispatch_template_0(params, state, hour, remaining_load, excess_solar)
        
        elif template_id == 1:
            remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used = \
                dispatch_template_1(params, state, hour, remaining_load, excess_solar)
        
        elif template_id == 2:
            remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used = \
                dispatch_template_2(params, state, hour, remaining_load, excess_solar)
        
        elif template_id == 3:
            remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used = \
                dispatch_template_3(params, state, hour, remaining_load, excess_solar)
        
        elif template_id == 4:
            remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used = \
                dispatch_template_4(params, state, hour, remaining_load, excess_solar)
        
        elif template_id == 5:
            remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used = \
                dispatch_template_5(params, state, hour, remaining_load, excess_solar)
        
        elif template_id == 6:
            remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used = \
                dispatch_template_6(params, state, hour, remaining_load, excess_solar)
        
        # ═══════════════════════════════════════════════════════════
        # STEP 6: CALCULATE UNSERVED ENERGY
        # ═══════════════════════════════════════════════════════════
        
        hour.unserved = remaining_load
        
        # ═══════════════════════════════════════════════════════════
        # STEP 7: SOC CLAMPING (Numerical Stability)
        # ═══════════════════════════════════════════════════════════
        
        state.soc = max(state.min_soc_mwh, min(state.soc, state.max_soc_mwh))
        
        # ═══════════════════════════════════════════════════════════
        # STEP 8: RECORD HOURLY RESULTS
        # ═══════════════════════════════════════════════════════════
        
        hour.soc = state.soc
        hour.daily_cycles = state.daily_cycles
        hour.bess_disabled = state.bess_disabled_today
        
        results.append(hour)
        
        # Update DG state for next hour
        state.dg_was_running = hour.dg_running
    
    # Save final day's cycles
    state.max_daily_cycles_per_day[state.current_day - 1] = state.daily_cycles
    
    return results
```

### 4.2 Common Helper Functions

```python
def charge_bess(state, params, energy_available, charge_power_used):
    """
    Attempt to charge BESS with available energy.
    
    Args:
        state: Current simulation state
        params: User parameters
        energy_available: MW available for charging
        charge_power_used: MW of charge power already used this hour
    
    Returns:
        (energy_charged, new_charge_power_used)
    """
    
    if energy_available <= 0 or state.bess_disabled_today:
        return 0, charge_power_used
    
    charge_room = state.max_soc_mwh - state.soc
    charge_power_available = state.charge_power_limit - charge_power_used
    
    max_charge = min(
        energy_available,
        charge_power_available,
        charge_room / state.charge_efficiency
    )
    
    if max_charge <= 0:
        return 0, charge_power_used
    
    # Apply charge
    energy_stored = max_charge * state.charge_efficiency
    state.soc += energy_stored
    
    return max_charge, charge_power_used + max_charge


def discharge_bess(state, params, energy_needed):
    """
    Attempt to discharge BESS to serve load.
    
    Args:
        state: Current simulation state
        params: User parameters
        energy_needed: MW of load to serve
    
    Returns:
        (energy_discharged, bess_discharged_flag)
    """
    
    if energy_needed <= 0 or state.bess_disabled_today:
        return 0, False
    
    discharge_available = state.soc - state.min_soc_mwh
    
    max_discharge = min(
        energy_needed,
        state.discharge_power_limit,
        discharge_available * state.discharge_efficiency
    )
    
    if max_discharge <= 0:
        return 0, False
    
    # Apply discharge
    energy_withdrawn = max_discharge / state.discharge_efficiency
    state.soc -= energy_withdrawn
    
    # Update cycle tracking
    state.daily_discharge += max_discharge
    state.daily_cycles = state.daily_discharge / state.usable_capacity
    
    # Check cycle limit (if enforced)
    if params.bess_enforce_cycle_limit and params.bess_daily_cycle_limit:
        if state.daily_cycles >= params.bess_daily_cycle_limit:
            state.bess_disabled_today = True
    
    return max_discharge, True


def activate_dg(state, params, hour, remaining_load, bess_discharged_this_hour, 
                charge_power_used, mode="NORMAL"):
    """
    Activate DG and handle its output.
    
    Args:
        state: Current simulation state
        params: User parameters
        hour: Current HourlyResult being built
        remaining_load: Load still to be served
        bess_discharged_this_hour: Whether BESS already discharged
        charge_power_used: Charge power already used
        mode: "NORMAL" or "EMERGENCY"
    
    Returns:
        (remaining_load, charge_power_used)
    """
    
    hour.dg_running = True
    hour.dg_mode = mode
    
    # Count DG start
    if not state.dg_was_running:
        state.total_dg_starts += 1
    
    state.total_dg_runtime_hours += 1
    
    # DG output (Full Capacity mode)
    dg_output = state.dg_capacity
    
    # DG serves remaining load
    hour.dg_to_load = min(dg_output, remaining_load)
    remaining_load -= hour.dg_to_load
    dg_excess = dg_output - hour.dg_to_load
    
    # DG charges BESS with excess (if enabled and BESS didn't discharge)
    if (params.dg_charges_bess and dg_excess > 0 and 
        not bess_discharged_this_hour and not state.bess_disabled_today):
        
        hour.dg_to_bess, charge_power_used = charge_bess(
            state, params, dg_excess, charge_power_used
        )
        hour.dg_curtailed = dg_excess - hour.dg_to_bess
    else:
        hour.dg_curtailed = dg_excess
    
    return remaining_load, charge_power_used
```

---

## 5. Phase 4: Summary Metrics

```python
def calculate_summary_metrics(results, state, params):
    """
    Calculate summary metrics after simulation completes.
    
    Args:
        results: List of 8760 HourlyResult objects
        state: Final simulation state
        params: User parameters
    
    Returns:
        SummaryMetrics object
    """
    
    metrics = SummaryMetrics()
    
    # ═══════════════════════════════════════════════════════════════
    # ENERGY TOTALS (MWh)
    # ═══════════════════════════════════════════════════════════════
    
    metrics.total_load = sum(r.load for r in results)
    metrics.total_solar_generation = sum(r.solar for r in results)
    metrics.total_solar_to_load = sum(r.solar_to_load for r in results)
    metrics.total_solar_to_bess = sum(r.solar_to_bess for r in results)
    metrics.total_solar_curtailed = sum(r.solar_curtailed for r in results)
    metrics.total_bess_to_load = sum(r.bess_to_load for r in results)
    metrics.total_dg_to_load = sum(r.dg_to_load for r in results)
    metrics.total_dg_to_bess = sum(r.dg_to_bess for r in results)
    metrics.total_dg_curtailed = sum(r.dg_curtailed for r in results)
    metrics.total_unserved = sum(r.unserved for r in results)
    
    # ═══════════════════════════════════════════════════════════════
    # DELIVERY METRICS
    # ═══════════════════════════════════════════════════════════════
    
    metrics.hours_full_delivery = sum(1 for r in results if r.unserved == 0)
    metrics.hours_any_delivery = sum(1 for r in results if r.load > 0 and r.unserved < r.load)
    metrics.hours_green_delivery = sum(1 for r in results 
                                       if r.unserved == 0 and not r.dg_running)
    metrics.hours_with_dg = sum(1 for r in results if r.dg_running)
    
    # ═══════════════════════════════════════════════════════════════
    # PERCENTAGES (with division-by-zero guards)
    # ═══════════════════════════════════════════════════════════════
    
    metrics.pct_full_delivery = metrics.hours_full_delivery / 8760 * 100
    metrics.pct_green_delivery = metrics.hours_green_delivery / 8760 * 100
    
    if metrics.total_load > 0:
        metrics.pct_load_served = ((metrics.total_load - metrics.total_unserved) 
                                   / metrics.total_load * 100)
        metrics.pct_unserved = metrics.total_unserved / metrics.total_load * 100
    else:
        metrics.pct_load_served = 100
        metrics.pct_unserved = 0
    
    if metrics.total_solar_generation > 0:
        metrics.pct_solar_curtailed = (metrics.total_solar_curtailed 
                                       / metrics.total_solar_generation * 100)
    else:
        metrics.pct_solar_curtailed = 0
    
    # ═══════════════════════════════════════════════════════════════
    # DG METRICS
    # ═══════════════════════════════════════════════════════════════
    
    metrics.dg_runtime_hours = state.total_dg_runtime_hours
    metrics.dg_starts = state.total_dg_starts
    
    metrics.total_dg_generation = (metrics.total_dg_to_load + 
                                   metrics.total_dg_to_bess + 
                                   metrics.total_dg_curtailed)
    
    if state.dg_capacity > 0:
        metrics.dg_capacity_factor = (metrics.total_dg_generation 
                                      / (state.dg_capacity * 8760) * 100)
    else:
        metrics.dg_capacity_factor = 0
    
    # ═══════════════════════════════════════════════════════════════
    # BESS METRICS
    # ═══════════════════════════════════════════════════════════════
    
    metrics.bess_throughput = metrics.total_bess_to_load
    
    if state.usable_capacity > 0:
        metrics.bess_equivalent_cycles = metrics.bess_throughput / state.usable_capacity
    else:
        metrics.bess_equivalent_cycles = 0
    
    metrics.max_daily_cycles = max(state.max_daily_cycles_per_day)
    metrics.avg_daily_cycles = sum(state.max_daily_cycles_per_day) / 365
    
    if params.bess_daily_cycle_limit:
        metrics.days_exceeding_cycle_limit = sum(
            1 for c in state.max_daily_cycles_per_day 
            if c > params.bess_daily_cycle_limit
        )
    else:
        metrics.days_exceeding_cycle_limit = 0
    
    # ═══════════════════════════════════════════════════════════════
    # TEMPLATE-SPECIFIC METRICS
    # ═══════════════════════════════════════════════════════════════
    
    # Hours where BESS assisted DG (Templates 4, 5, 6)
    metrics.hours_bess_assisted = sum(1 for r in results if r.bess_assisted)
    
    # Emergency DG hours (Templates 2, 5, 6)
    metrics.hours_emergency_dg = sum(1 for r in results if r.dg_mode == "EMERGENCY")
    
    # Blackout window delivery (Template 3)
    if hasattr(state, 'is_blackout_hour'):
        blackout_hours = [r for r in results if state.is_blackout_hour[r.hour_of_day]]
        if blackout_hours:
            metrics.blackout_delivery_pct = (sum(1 for r in blackout_hours if r.unserved == 0) 
                                             / len(blackout_hours) * 100)
        else:
            metrics.blackout_delivery_pct = 100
    
    # Night/Day specific metrics (Templates 5, 6)
    if hasattr(state, 'is_night_hour'):
        night_hours = [r for r in results if state.is_night_hour[r.hour_of_day]]
        if night_hours:
            metrics.pct_night_silent = (sum(1 for r in night_hours if not r.dg_running) 
                                        / len(night_hours) * 100)
    
    if hasattr(state, 'is_day_hour'):
        day_hours = [r for r in results if state.is_day_hour[r.hour_of_day]]
        if day_hours:
            metrics.pct_day_green = (sum(1 for r in day_hours 
                                         if r.unserved == 0 and not r.dg_running) 
                                     / len(day_hours) * 100)
    
    return metrics
```

---

## 6. Phase 5: Sizing Mode Wrapper

```python
# ═══════════════════════════════════════════════════════════════════════════
# SIZING MODE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DURATION_CLASSES = [1, 2, 3, 4, 6, 8, 10]  # hours


def run_sizing_mode(params, template_id):
    """
    Execute sizing mode: iterate through all configurations.
    
    Args:
        params: User parameters including sizing ranges
        template_id: Which template (0-6) to run
    
    Returns:
        ComparisonTable with all configurations and metrics
    """
    
    comparison_table = []
    
    # ═══════════════════════════════════════════════════════════════
    # GENERATE CAPACITY VALUES
    # ═══════════════════════════════════════════════════════════════
    
    capacity_values = []
    capacity = params.bess_capacity_min
    while capacity <= params.bess_capacity_max:
        capacity_values.append(capacity)
        capacity += params.bess_capacity_step
    
    # ═══════════════════════════════════════════════════════════════
    # GENERATE DG VALUES
    # ═══════════════════════════════════════════════════════════════
    
    if params.dg_enabled:
        dg_values = []
        dg = params.dg_capacity_min
        while dg <= params.dg_capacity_max:
            dg_values.append(dg)
            dg += params.dg_capacity_step
    else:
        dg_values = [0]  # No DG
    
    # ═══════════════════════════════════════════════════════════════
    # ITERATE THROUGH ALL COMBINATIONS
    # ═══════════════════════════════════════════════════════════════
    
    total_configs = len(capacity_values) * len(DURATION_CLASSES) * len(dg_values)
    config_count = 0
    
    for capacity in capacity_values:
        for duration in DURATION_CLASSES:
            power = capacity / duration
            
            for dg_size in dg_values:
                config_count += 1
                
                # Progress callback (optional)
                # on_progress(config_count, total_configs)
                
                # Build sizing config
                sizing_config = {
                    'capacity': capacity,
                    'duration': duration,
                    'power': power,
                    'dg_size': dg_size
                }
                
                # Initialize simulation
                state = initialize_simulation(params, sizing_config)
                
                # Run 8760-hour simulation
                results = run_simulation(params, state, template_id)
                
                # Calculate metrics
                metrics = calculate_summary_metrics(results, state, params)
                
                # Build comparison row
                row = ComparisonRow(
                    capacity=capacity,
                    duration=duration,
                    power=power,
                    dg_size=dg_size,
                    delivery_pct=metrics.pct_full_delivery,
                    delivery_hours=metrics.hours_full_delivery,
                    green_pct=metrics.pct_green_delivery,
                    green_hours=metrics.hours_green_delivery,
                    unserved_mwh=metrics.total_unserved,
                    unserved_pct=metrics.pct_unserved,
                    curtailed_mwh=metrics.total_solar_curtailed,
                    curtailed_pct=metrics.pct_solar_curtailed,
                    dg_runtime_hrs=metrics.dg_runtime_hours,
                    dg_starts=metrics.dg_starts,
                    bess_cycles=metrics.bess_equivalent_cycles,
                    max_daily_cycles=metrics.max_daily_cycles,
                    # Template-specific
                    hours_bess_assisted=metrics.hours_bess_assisted,
                    hours_emergency_dg=metrics.hours_emergency_dg,
                    blackout_delivery_pct=getattr(metrics, 'blackout_delivery_pct', None),
                    pct_night_silent=getattr(metrics, 'pct_night_silent', None),
                    pct_day_green=getattr(metrics, 'pct_day_green', None),
                )
                
                comparison_table.append(row)
    
    # ═══════════════════════════════════════════════════════════════
    # FLAG DOMINATED CONFIGURATIONS
    # ═══════════════════════════════════════════════════════════════
    
    flag_dominated_configurations(comparison_table)
    
    return comparison_table


def flag_dominated_configurations(table):
    """
    Flag configurations that are dominated by others.
    
    A configuration is dominated if another exists that is:
    - Equal or better on delivery_pct
    - Equal or better on curtailed_pct (lower is better)
    - Equal or smaller on capacity
    - Equal or smaller on dg_size
    - Strictly better on at least one metric
    """
    
    for i, row_a in enumerate(table):
        row_a.is_dominated = False
        
        for j, row_b in enumerate(table):
            if i == j:
                continue
            
            # Check if row_b dominates row_a
            b_equal_or_better_delivery = row_b.delivery_pct >= row_a.delivery_pct
            b_equal_or_better_curtail = row_b.curtailed_pct <= row_a.curtailed_pct
            b_equal_or_smaller_capacity = row_b.capacity <= row_a.capacity
            b_equal_or_smaller_dg = row_b.dg_size <= row_a.dg_size
            
            b_strictly_better = (
                row_b.delivery_pct > row_a.delivery_pct or
                row_b.curtailed_pct < row_a.curtailed_pct or
                row_b.capacity < row_a.capacity or
                row_b.dg_size < row_a.dg_size
            )
            
            if (b_equal_or_better_delivery and 
                b_equal_or_better_curtail and
                b_equal_or_smaller_capacity and
                b_equal_or_smaller_dg and
                b_strictly_better):
                
                row_a.is_dominated = True
                break
```

---

## 7. Template-Specific Logic

### 7.1 Template 0: Solar + BESS Only

```python
def dispatch_template_0(params, state, hour, remaining_load, excess_solar):
    """
    Template 0: Solar + BESS Only
    Merit Order: Solar → BESS → Unserved
    No DG.
    """
    
    bess_discharged_this_hour = False
    charge_power_used = 0
    
    # ─────────────────────────────────────────────────────────────
    # STEP 3: CHARGE BESS WITH EXCESS SOLAR
    # ─────────────────────────────────────────────────────────────
    
    if excess_solar > 0:
        hour.solar_to_bess, charge_power_used = charge_bess(
            state, params, excess_solar, charge_power_used
        )
        hour.solar_curtailed = excess_solar - hour.solar_to_bess
    else:
        hour.solar_curtailed = 0
    
    # ─────────────────────────────────────────────────────────────
    # STEP 4: DISCHARGE BESS TO SERVE REMAINING LOAD
    # ─────────────────────────────────────────────────────────────
    
    if remaining_load > 0:
        hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
            state, params, remaining_load
        )
        remaining_load -= hour.bess_to_load
    
    # No DG in Template 0
    
    return remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used
```

### 7.2 Template 1: Green Priority

```python
def dispatch_template_1(params, state, hour, remaining_load, excess_solar):
    """
    Template 1: Green Priority
    Merit Order: Solar → BESS → DG → Unserved
    DG is reactive (only when BESS insufficient).
    """
    
    bess_discharged_this_hour = False
    charge_power_used = 0
    
    # ─────────────────────────────────────────────────────────────
    # STEP 3: CHARGE BESS WITH EXCESS SOLAR
    # ─────────────────────────────────────────────────────────────
    
    if excess_solar > 0 and not state.bess_disabled_today:
        hour.solar_to_bess, charge_power_used = charge_bess(
            state, params, excess_solar, charge_power_used
        )
        hour.solar_curtailed = excess_solar - hour.solar_to_bess
    else:
        hour.solar_curtailed = excess_solar
    
    # ─────────────────────────────────────────────────────────────
    # STEP 4: DISCHARGE BESS TO SERVE REMAINING LOAD
    # ─────────────────────────────────────────────────────────────
    
    if remaining_load > 0 and not state.bess_disabled_today:
        hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
            state, params, remaining_load
        )
        remaining_load -= hour.bess_to_load
    
    # ─────────────────────────────────────────────────────────────
    # STEP 5: DG ACTIVATION (if load still remaining)
    # ─────────────────────────────────────────────────────────────
    
    if remaining_load > 0 and state.dg_capacity > 0:
        remaining_load, charge_power_used = activate_dg(
            state, params, hour, remaining_load, 
            bess_discharged_this_hour, charge_power_used
        )
    
    return remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used
```

### 7.3 Template 2: DG Night Charge

```python
def dispatch_template_2(params, state, hour, remaining_load, excess_solar):
    """
    Template 2: DG Night Charge
    Night: DG proactively ON, charges BESS
    Day: Solar + BESS only (DG disabled except emergency)
    """
    
    bess_discharged_this_hour = False
    charge_power_used = 0
    
    is_night = state.is_night_hour[hour.hour_of_day]
    hour.is_night = is_night
    
    # ─────────────────────────────────────────────────────────────
    # DETERMINE DG STATE BASED ON TIME AND SOC
    # ─────────────────────────────────────────────────────────────
    
    dg_should_run = False
    dg_mode = "OFF"
    
    if is_night:
        # Night: DG follows SoC-based control
        if params.dg_off_trigger == "SoC_Threshold":
            # SoC-based on/off with deadband
            if state.soc <= state.dg_soc_on_mwh:
                dg_should_run = True
            elif state.soc >= state.dg_soc_off_mwh:
                dg_should_run = False
            else:
                # In deadband: maintain previous state
                dg_should_run = state.dg_was_running
        else:
            # Day_Start trigger: DG runs all night
            dg_should_run = True
        
        dg_mode = "NORMAL"
    else:
        # Day: DG disabled unless emergency
        if (params.allow_emergency_dg_day and 
            state.soc <= state.emergency_soc_mwh):
            dg_should_run = True
            dg_mode = "EMERGENCY"
    
    # ─────────────────────────────────────────────────────────────
    # NIGHT DISPATCH (DG Priority when ON)
    # ─────────────────────────────────────────────────────────────
    
    if is_night and dg_should_run:
        # DG runs and takes priority
        remaining_load, charge_power_used = activate_dg(
            state, params, hour, remaining_load, 
            bess_discharged_this_hour, charge_power_used, dg_mode
        )
        
        # Excess solar also charges BESS
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(
                state, params, excess_solar, charge_power_used
            )
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar
    
    elif is_night and not dg_should_run:
        # Night, DG off (SoC threshold reached): BESS serves load
        
        # Charge with excess solar first
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(
                state, params, excess_solar, charge_power_used
            )
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar
        
        # Discharge BESS to serve load
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                state, params, remaining_load
            )
            remaining_load -= hour.bess_to_load
    
    # ─────────────────────────────────────────────────────────────
    # DAY DISPATCH (Green Operation)
    # ─────────────────────────────────────────────────────────────
    
    else:
        # Day: Solar → BESS → Emergency DG → Unserved
        
        # Charge BESS with excess solar
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(
                state, params, excess_solar, charge_power_used
            )
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar
        
        # Discharge BESS to serve load
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                state, params, remaining_load
            )
            remaining_load -= hour.bess_to_load
        
        # Emergency DG (if enabled and triggered)
        if dg_should_run and remaining_load > 0:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, 
                bess_discharged_this_hour, charge_power_used, "EMERGENCY"
            )
    
    return remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used
```

### 7.4 Template 3: DG Blackout Window

```python
def dispatch_template_3(params, state, hour, remaining_load, excess_solar):
    """
    Template 3: DG Blackout Window
    During blackout: DG strictly disabled
    Outside blackout: Behaves like Template 1 (Green Priority)
    """
    
    bess_discharged_this_hour = False
    charge_power_used = 0
    
    is_blackout = state.is_blackout_hour[hour.hour_of_day]
    hour.is_blackout = is_blackout
    
    # ─────────────────────────────────────────────────────────────
    # STEP 3: CHARGE BESS WITH EXCESS SOLAR (always allowed)
    # ─────────────────────────────────────────────────────────────
    
    if excess_solar > 0 and not state.bess_disabled_today:
        hour.solar_to_bess, charge_power_used = charge_bess(
            state, params, excess_solar, charge_power_used
        )
        hour.solar_curtailed = excess_solar - hour.solar_to_bess
    else:
        hour.solar_curtailed = excess_solar
    
    # ─────────────────────────────────────────────────────────────
    # STEP 4: DISCHARGE BESS TO SERVE REMAINING LOAD
    # ─────────────────────────────────────────────────────────────
    
    if remaining_load > 0 and not state.bess_disabled_today:
        hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
            state, params, remaining_load
        )
        remaining_load -= hour.bess_to_load
    
    # ─────────────────────────────────────────────────────────────
    # STEP 5: DG ACTIVATION (only outside blackout)
    # ─────────────────────────────────────────────────────────────
    
    if not is_blackout and remaining_load > 0 and state.dg_capacity > 0:
        remaining_load, charge_power_used = activate_dg(
            state, params, hour, remaining_load, 
            bess_discharged_this_hour, charge_power_used
        )
    
    # During blackout: remaining_load becomes unserved (no DG allowed)
    
    return remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used
```

### 7.5 Template 4: DG Emergency Only

```python
def dispatch_template_4(params, state, hour, remaining_load, excess_solar):
    """
    Template 4: DG Emergency Only
    DG is SoC-triggered with deadband (no time restrictions).
    When DG ON: DG takes priority, BESS assists if needed.
    """
    
    bess_discharged_this_hour = False
    charge_power_used = 0
    
    # ─────────────────────────────────────────────────────────────
    # DETERMINE DG STATE (SoC-based with deadband)
    # ─────────────────────────────────────────────────────────────
    
    if state.soc <= state.dg_soc_on_mwh:
        dg_should_run = True
    elif state.soc >= state.dg_soc_off_mwh:
        dg_should_run = False
    else:
        # In deadband: maintain previous state (hysteresis)
        dg_should_run = state.dg_was_running
    
    # ─────────────────────────────────────────────────────────────
    # DG OFF: Normal green operation
    # ─────────────────────────────────────────────────────────────
    
    if not dg_should_run:
        # Charge BESS with excess solar
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(
                state, params, excess_solar, charge_power_used
            )
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar
        
        # Discharge BESS to serve load
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                state, params, remaining_load
            )
            remaining_load -= hour.bess_to_load
    
    # ─────────────────────────────────────────────────────────────
    # DG ON: DG takes priority, BESS assists or recovers
    # ─────────────────────────────────────────────────────────────
    
    else:
        hour.dg_running = True
        hour.dg_mode = "NORMAL"
        
        # Count DG start
        if not state.dg_was_running:
            state.total_dg_starts += 1
        state.total_dg_runtime_hours += 1
        
        dg_output = state.dg_capacity
        
        # DG serves remaining load (after solar)
        hour.dg_to_load = min(dg_output, remaining_load)
        remaining_load -= hour.dg_to_load
        dg_excess = dg_output - hour.dg_to_load
        
        # ─────────────────────────────────────────────────────────
        # ASSIST MODE: BESS helps DG if DG < Load
        # ─────────────────────────────────────────────────────────
        
        if remaining_load > 0 and not state.bess_disabled_today:
            # BESS assists - covers deficit only
            hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                state, params, remaining_load
            )
            remaining_load -= hour.bess_to_load
            hour.bess_assisted = True
            
            # No charging when BESS assisted
            hour.solar_curtailed = excess_solar
            hour.dg_curtailed = dg_excess
        
        # ─────────────────────────────────────────────────────────
        # RECOVERY MODE: BESS rests, charges from excess
        # ─────────────────────────────────────────────────────────
        
        else:
            # BESS rests, can charge from excess
            total_excess = excess_solar + dg_excess
            
            if total_excess > 0 and not state.bess_disabled_today:
                # Solar charges first
                if excess_solar > 0:
                    hour.solar_to_bess, charge_power_used = charge_bess(
                        state, params, excess_solar, charge_power_used
                    )
                    hour.solar_curtailed = excess_solar - hour.solar_to_bess
                
                # Then DG excess (if dg_charges_bess enabled)
                if dg_excess > 0 and params.dg_charges_bess:
                    hour.dg_to_bess, charge_power_used = charge_bess(
                        state, params, dg_excess, charge_power_used
                    )
                    hour.dg_curtailed = dg_excess - hour.dg_to_bess
                else:
                    hour.dg_curtailed = dg_excess
            else:
                hour.solar_curtailed = excess_solar
                hour.dg_curtailed = dg_excess
    
    return remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used
```

### 7.6 Template 5: DG Day Charge

```python
def dispatch_template_5(params, state, hour, remaining_load, excess_solar):
    """
    Template 5: DG Day Charge
    Day: SoC-triggered DG with assist/recovery modes
    Night: DG disabled (silent operation), optional emergency
    """
    
    bess_discharged_this_hour = False
    charge_power_used = 0
    
    is_day = state.is_day_hour[hour.hour_of_day]
    hour.is_day = is_day
    
    # ─────────────────────────────────────────────────────────────
    # DETERMINE DG STATE
    # ─────────────────────────────────────────────────────────────
    
    dg_should_run = False
    dg_mode = "OFF"
    
    if is_day:
        # Day: SoC-triggered with deadband
        if state.soc <= state.dg_soc_on_mwh:
            dg_should_run = True
        elif state.soc >= state.dg_soc_off_mwh:
            dg_should_run = False
        else:
            dg_should_run = state.dg_was_running
        
        dg_mode = "NORMAL"
    else:
        # Night: DG disabled unless emergency
        # SUNSET CUT: Force DG OFF when transitioning to night
        if (params.allow_emergency_dg_night and 
            state.soc <= state.emergency_soc_mwh):
            dg_should_run = True
            dg_mode = "EMERGENCY"
    
    # ─────────────────────────────────────────────────────────────
    # DAY DISPATCH (when DG allowed)
    # ─────────────────────────────────────────────────────────────
    
    if is_day:
        if dg_should_run:
            # DG ON: Same logic as Template 4 (assist/recovery modes)
            hour.dg_running = True
            hour.dg_mode = dg_mode
            
            if not state.dg_was_running:
                state.total_dg_starts += 1
            state.total_dg_runtime_hours += 1
            
            dg_output = state.dg_capacity
            hour.dg_to_load = min(dg_output, remaining_load)
            remaining_load -= hour.dg_to_load
            dg_excess = dg_output - hour.dg_to_load
            
            # Assist mode
            if remaining_load > 0 and not state.bess_disabled_today:
                hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                    state, params, remaining_load
                )
                remaining_load -= hour.bess_to_load
                hour.bess_assisted = True
                hour.solar_curtailed = excess_solar
                hour.dg_curtailed = dg_excess
            
            # Recovery mode
            else:
                if excess_solar > 0 and not state.bess_disabled_today:
                    hour.solar_to_bess, charge_power_used = charge_bess(
                        state, params, excess_solar, charge_power_used
                    )
                    hour.solar_curtailed = excess_solar - hour.solar_to_bess
                else:
                    hour.solar_curtailed = excess_solar
                
                if dg_excess > 0 and params.dg_charges_bess and not state.bess_disabled_today:
                    hour.dg_to_bess, charge_power_used = charge_bess(
                        state, params, dg_excess, charge_power_used
                    )
                    hour.dg_curtailed = dg_excess - hour.dg_to_bess
                else:
                    hour.dg_curtailed = dg_excess
        
        else:
            # DG OFF: Normal green operation
            if excess_solar > 0 and not state.bess_disabled_today:
                hour.solar_to_bess, charge_power_used = charge_bess(
                    state, params, excess_solar, charge_power_used
                )
                hour.solar_curtailed = excess_solar - hour.solar_to_bess
            else:
                hour.solar_curtailed = excess_solar
            
            if remaining_load > 0 and not state.bess_disabled_today:
                hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                    state, params, remaining_load
                )
                remaining_load -= hour.bess_to_load
    
    # ─────────────────────────────────────────────────────────────
    # NIGHT DISPATCH (DG disabled, silent operation)
    # ─────────────────────────────────────────────────────────────
    
    else:
        # Charge with any solar (rare at night)
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(
                state, params, excess_solar, charge_power_used
            )
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar
        
        # Discharge BESS
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                state, params, remaining_load
            )
            remaining_load -= hour.bess_to_load
        
        # Emergency DG
        if dg_should_run and remaining_load > 0:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, 
                bess_discharged_this_hour, charge_power_used, "EMERGENCY"
            )
    
    return remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used
```

### 7.7 Template 6: DG Night SoC Trigger

```python
def dispatch_template_6(params, state, hour, remaining_load, excess_solar):
    """
    Template 6: DG Night SoC Trigger
    Night: SoC-triggered DG with assist/recovery modes
    Day: DG disabled (green operation), optional emergency
    
    Note: DG trigger does NOT check bess_disabled_today (DG-BESS independence)
    """
    
    bess_discharged_this_hour = False
    charge_power_used = 0
    
    is_night = state.is_night_hour[hour.hour_of_day]
    hour.is_night = is_night
    
    # ─────────────────────────────────────────────────────────────
    # DETERMINE DG STATE
    # Note: DG trigger is independent of bess_disabled_today
    # ─────────────────────────────────────────────────────────────
    
    dg_should_run = False
    dg_mode = "OFF"
    
    if is_night:
        # Night: SoC-triggered with deadband
        if state.soc <= state.dg_soc_on_mwh:
            dg_should_run = True
        elif state.soc >= state.dg_soc_off_mwh:
            dg_should_run = False
        else:
            dg_should_run = state.dg_was_running
        
        dg_mode = "NORMAL"
    else:
        # Day: DG disabled unless emergency
        # SUNRISE CUT: Force DG OFF when transitioning to day
        if (params.allow_emergency_dg_day and 
            state.soc <= state.emergency_soc_mwh):
            dg_should_run = True
            dg_mode = "EMERGENCY"
    
    # ─────────────────────────────────────────────────────────────
    # NIGHT DISPATCH (when DG allowed)
    # ─────────────────────────────────────────────────────────────
    
    if is_night:
        if dg_should_run:
            # DG ON: assist/recovery modes
            hour.dg_running = True
            hour.dg_mode = dg_mode
            
            if not state.dg_was_running:
                state.total_dg_starts += 1
            state.total_dg_runtime_hours += 1
            
            dg_output = state.dg_capacity
            hour.dg_to_load = min(dg_output, remaining_load)
            remaining_load -= hour.dg_to_load
            dg_excess = dg_output - hour.dg_to_load
            
            # Assist mode (gated by bess_disabled_today)
            if remaining_load > 0 and not state.bess_disabled_today:
                hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                    state, params, remaining_load
                )
                remaining_load -= hour.bess_to_load
                hour.bess_assisted = True
                hour.solar_curtailed = excess_solar
                hour.dg_curtailed = dg_excess
            
            # BESS disabled + DG < Load: remaining is unserved
            elif remaining_load > 0 and state.bess_disabled_today:
                hour.solar_curtailed = excess_solar
                hour.dg_curtailed = dg_excess
                # remaining_load stays as unserved
            
            # Recovery mode
            else:
                if excess_solar > 0 and not state.bess_disabled_today:
                    hour.solar_to_bess, charge_power_used = charge_bess(
                        state, params, excess_solar, charge_power_used
                    )
                    hour.solar_curtailed = excess_solar - hour.solar_to_bess
                else:
                    hour.solar_curtailed = excess_solar
                
                if dg_excess > 0 and params.dg_charges_bess and not state.bess_disabled_today:
                    hour.dg_to_bess, charge_power_used = charge_bess(
                        state, params, dg_excess, charge_power_used
                    )
                    hour.dg_curtailed = dg_excess - hour.dg_to_bess
                else:
                    hour.dg_curtailed = dg_excess
        
        else:
            # DG OFF: BESS serves load
            if excess_solar > 0 and not state.bess_disabled_today:
                hour.solar_to_bess, charge_power_used = charge_bess(
                    state, params, excess_solar, charge_power_used
                )
                hour.solar_curtailed = excess_solar - hour.solar_to_bess
            else:
                hour.solar_curtailed = excess_solar
            
            if remaining_load > 0 and not state.bess_disabled_today:
                hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                    state, params, remaining_load
                )
                remaining_load -= hour.bess_to_load
    
    # ─────────────────────────────────────────────────────────────
    # DAY DISPATCH (DG disabled, green operation)
    # ─────────────────────────────────────────────────────────────
    
    else:
        # Charge with excess solar
        if excess_solar > 0 and not state.bess_disabled_today:
            hour.solar_to_bess, charge_power_used = charge_bess(
                state, params, excess_solar, charge_power_used
            )
            hour.solar_curtailed = excess_solar - hour.solar_to_bess
        else:
            hour.solar_curtailed = excess_solar
        
        # Discharge BESS
        if remaining_load > 0 and not state.bess_disabled_today:
            hour.bess_to_load, bess_discharged_this_hour = discharge_bess(
                state, params, remaining_load
            )
            remaining_load -= hour.bess_to_load
        
        # Emergency DG
        if dg_should_run and remaining_load > 0:
            remaining_load, charge_power_used = activate_dg(
                state, params, hour, remaining_load, 
                bess_discharged_this_hour, charge_power_used, "EMERGENCY"
            )
    
    return remaining_load, excess_solar, bess_discharged_this_hour, charge_power_used
```

---

## 8. Data Structures

### 8.1 Input Parameters

```python
@dataclass
class SimulationParams:
    # Profiles
    load_profile: List[float]        # 8760 values (MW)
    solar_profile: List[float]       # 8760 values (MW)
    
    # Mode
    sizing_mode: bool = False
    
    # BESS parameters (Fixed Mode)
    bess_capacity: float = 0         # MWh
    bess_charge_power: float = 0     # MW
    bess_discharge_power: float = 0  # MW
    bess_efficiency: float = 85      # %
    bess_min_soc: float = 10         # %
    bess_max_soc: float = 90         # %
    bess_initial_soc: float = 50     # %
    bess_charge_c_rate: float = 1    # C
    bess_discharge_c_rate: float = 1 # C
    bess_daily_cycle_limit: Optional[float] = None
    bess_enforce_cycle_limit: bool = False
    
    # BESS sizing parameters (Sizing Mode)
    bess_capacity_min: float = 0
    bess_capacity_max: float = 0
    bess_capacity_step: float = 0
    
    # DG parameters
    dg_enabled: bool = False
    dg_capacity: float = 0           # MW
    dg_charges_bess: bool = False
    
    # DG sizing parameters (Sizing Mode)
    dg_capacity_min: float = 0
    dg_capacity_max: float = 0
    dg_capacity_step: float = 0
    
    # Template-specific: Time windows
    night_window_mode: str = "Fixed"     # Fixed or Dynamic
    night_start_hour: int = 18
    night_end_hour: int = 6
    day_window_mode: str = "Fixed"
    day_start_hour: int = 6
    day_end_hour: int = 18
    blackout_start_hour: int = 6
    blackout_end_hour: int = 18
    
    # Template-specific: SoC thresholds
    dg_soc_on_threshold: float = 30      # %
    dg_soc_off_threshold: float = 80     # %
    emergency_soc_threshold: float = 15  # %
    
    # Template-specific: Flags
    allow_emergency_dg_day: bool = False
    allow_emergency_dg_night: bool = False
    dg_off_trigger: str = "Day_Start"    # Day_Start or SoC_Threshold
```

### 8.2 Simulation State

```python
@dataclass
class SimulationState:
    # Configuration
    bess_capacity: float = 0
    bess_charge_power: float = 0
    bess_discharge_power: float = 0
    dg_capacity: float = 0
    duration: float = 0
    
    # Derived constants
    usable_capacity: float = 0
    min_soc_mwh: float = 0
    max_soc_mwh: float = 0
    charge_power_limit: float = 0
    discharge_power_limit: float = 0
    charge_efficiency: float = 0
    discharge_efficiency: float = 0
    
    # SoC thresholds (MWh)
    dg_soc_on_mwh: float = 0
    dg_soc_off_mwh: float = 0
    emergency_soc_mwh: float = 0
    
    # Time window arrays
    is_night_hour: List[bool] = None
    is_day_hour: List[bool] = None
    is_blackout_hour: List[bool] = None
    
    # State variables
    soc: float = 0
    daily_discharge: float = 0
    daily_cycles: float = 0
    bess_disabled_today: bool = False
    current_day: int = 1
    dg_was_running: bool = False
    
    # Counters
    total_dg_starts: int = 0
    total_dg_runtime_hours: int = 0
    
    # Per-day tracking
    max_daily_cycles_per_day: List[float] = None
```

### 8.3 Hourly Result

```python
@dataclass
class HourlyResult:
    t: int = 0                      # Hour index (1-8760)
    day: int = 0                    # Day of year (1-365)
    hour_of_day: int = 0            # Hour of day (0-23)
    
    load: float = 0                 # MW
    solar: float = 0                # MW
    
    solar_to_load: float = 0        # MWh
    solar_to_bess: float = 0        # MWh
    solar_curtailed: float = 0      # MWh
    
    bess_to_load: float = 0         # MWh
    
    dg_to_load: float = 0           # MWh
    dg_to_bess: float = 0           # MWh
    dg_curtailed: float = 0         # MWh
    dg_running: bool = False
    dg_mode: str = "OFF"            # OFF, NORMAL, EMERGENCY
    
    bess_assisted: bool = False     # BESS helped DG
    
    unserved: float = 0             # MWh
    
    soc: float = 0                  # MWh (end of hour)
    daily_cycles: float = 0
    bess_disabled: bool = False
    
    # Template-specific flags
    is_night: bool = False
    is_day: bool = False
    is_blackout: bool = False
```

### 8.4 Summary Metrics

```python
@dataclass
class SummaryMetrics:
    # Energy totals (MWh)
    total_load: float = 0
    total_solar_generation: float = 0
    total_solar_to_load: float = 0
    total_solar_to_bess: float = 0
    total_solar_curtailed: float = 0
    total_bess_to_load: float = 0
    total_dg_to_load: float = 0
    total_dg_to_bess: float = 0
    total_dg_curtailed: float = 0
    total_dg_generation: float = 0
    total_unserved: float = 0
    
    # Delivery metrics
    hours_full_delivery: int = 0
    hours_any_delivery: int = 0
    hours_green_delivery: int = 0
    hours_with_dg: int = 0
    
    # Percentages
    pct_full_delivery: float = 0
    pct_green_delivery: float = 0
    pct_load_served: float = 0
    pct_unserved: float = 0
    pct_solar_curtailed: float = 0
    
    # DG metrics
    dg_runtime_hours: int = 0
    dg_starts: int = 0
    dg_capacity_factor: float = 0
    
    # BESS metrics
    bess_throughput: float = 0
    bess_equivalent_cycles: float = 0
    max_daily_cycles: float = 0
    avg_daily_cycles: float = 0
    days_exceeding_cycle_limit: int = 0
    
    # Template-specific
    hours_bess_assisted: int = 0
    hours_emergency_dg: int = 0
    blackout_delivery_pct: float = 0
    pct_night_silent: float = 0
    pct_day_green: float = 0
```

### 8.5 Comparison Table Row

```python
@dataclass
class ComparisonRow:
    # Configuration
    capacity: float = 0             # MWh
    duration: int = 0               # hours
    power: float = 0                # MW
    dg_size: float = 0              # MW
    
    # Delivery metrics
    delivery_pct: float = 0         # %
    delivery_hours: int = 0
    green_pct: float = 0            # %
    green_hours: int = 0
    
    # Energy metrics
    unserved_mwh: float = 0
    unserved_pct: float = 0
    curtailed_mwh: float = 0
    curtailed_pct: float = 0
    
    # Operational metrics
    dg_runtime_hrs: int = 0
    dg_starts: int = 0
    bess_cycles: float = 0
    max_daily_cycles: float = 0
    
    # Template-specific
    hours_bess_assisted: int = 0
    hours_emergency_dg: int = 0
    blackout_delivery_pct: Optional[float] = None
    pct_night_silent: Optional[float] = None
    pct_day_green: Optional[float] = None
    
    # Optimization flag
    is_dominated: bool = False
```

---

## Appendix A: Quick Reference - Template Differences

| Template | DG Trigger | Time Restriction | BESS Assist | Cycle Enforce |
| ---------- | ------------ | ------------------ | ------------- | --------------- |
| 0 | N/A (no DG) | None | N/A | User choice |
| 1 | Load deficit | None | No | User choice |
| 2 | Proactive (night) | Night only | No | User choice |
| 3 | Load deficit | Outside blackout | No | User choice |
| 4 | SoC threshold | None | Yes | Forced OFF |
| 5 | SoC threshold | Day only | Yes | Forced OFF |
| 6 | SoC threshold | Night only | Yes | User choice |

---

## Appendix B: Duration Class Reference

| Duration | C-Rate | Power Formula | Typical Use Case |
| ---------- | -------- | --------------- | ------------------ |
| 1 hour | 1C | capacity ÷ 1 | Frequency response |
| 2 hours | 0.5C | capacity ÷ 2 | Most common utility |
| 3 hours | 0.33C | capacity ÷ 3 | Transitional |
| 4 hours | 0.25C | capacity ÷ 4 | Capacity contracts |
| 6 hours | 0.167C | capacity ÷ 6 | Long duration |
| 8 hours | 0.125C | capacity ÷ 8 | Extended storage |
| 10 hours | 0.1C | capacity ÷ 10 | Maximum duration |

---

**Document Status: APPROVED FOR IMPLEMENTATION**
