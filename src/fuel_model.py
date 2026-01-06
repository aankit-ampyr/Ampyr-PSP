"""
Fuel Model Module - Non-Linear Genset Fuel Curve

Implements the Willans line fuel model for diesel/gas generators:
    fuel_rate = F0 × P_rated + F1 × P_actual

Where:
    - F0: No-load coefficient (L/hr per kW of rated capacity)
    - F1: Load coefficient (L/kWh of actual output)
    - P_rated: DG rated capacity (kW)
    - P_actual: Actual power output (kW)

This model captures the non-linear relationship between load and efficiency,
showing that partial loading is significantly less efficient than full loading.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


# =============================================================================
# DEFAULT PARAMETERS
# =============================================================================

# Default fuel curve coefficients (typical diesel generator)
DEFAULT_F0 = 0.03   # L/hr per kW rated (no-load coefficient)
DEFAULT_F1 = 0.22   # L/kWh output (load coefficient)
DEFAULT_FLAT_RATE = 0.25  # L/kWh (flat rate when advanced model disabled)


@dataclass
class FuelConfig:
    """Configuration for fuel calculations."""
    enabled: bool = False          # Use advanced fuel curve model
    f0: float = DEFAULT_F0         # No-load coefficient (L/hr/kW)
    f1: float = DEFAULT_F1         # Load coefficient (L/kWh)
    flat_rate: float = DEFAULT_FLAT_RATE  # Flat rate (L/kWh)
    fuel_price_per_liter: float = 1.50    # Cost per liter


@dataclass
class FuelResult:
    """Results from fuel calculation."""
    fuel_consumed_liters: float = 0.0
    fuel_rate_lph: float = 0.0           # Liters per hour
    specific_consumption_lpkwh: float = 0.0  # Liters per kWh
    efficiency_kwh_per_liter: float = 0.0
    fuel_cost: float = 0.0


# =============================================================================
# CORE FUEL CALCULATIONS
# =============================================================================

def calculate_fuel_rate(
    p_rated_mw: float,
    p_actual_mw: float,
    f0: float = DEFAULT_F0,
    f1: float = DEFAULT_F1
) -> float:
    """
    Calculate instantaneous fuel consumption rate using Willans line model.

    Args:
        p_rated_mw: DG rated capacity in MW
        p_actual_mw: Actual power output in MW
        f0: No-load coefficient (L/hr per kW rated)
        f1: Load coefficient (L/kWh output)

    Returns:
        Fuel rate in L/hr

    Example:
        100 kW DG at 50% load:
        fuel_rate = 0.03 × 100 + 0.22 × 50 = 14 L/hr
        specific = 14/50 = 0.28 L/kWh (inefficient)

        100 kW DG at 100% load:
        fuel_rate = 0.03 × 100 + 0.22 × 100 = 25 L/hr
        specific = 25/100 = 0.25 L/kWh (efficient)
    """
    if p_actual_mw <= 0:
        return 0.0

    p_rated_kw = p_rated_mw * 1000
    p_actual_kw = p_actual_mw * 1000

    # Willans line: fuel_rate = F0 × P_rated + F1 × P_actual
    fuel_rate = f0 * p_rated_kw + f1 * p_actual_kw

    return fuel_rate


def calculate_fuel_consumption(
    p_rated_mw: float,
    p_actual_mw: float,
    hours: float,
    f0: float = DEFAULT_F0,
    f1: float = DEFAULT_F1
) -> float:
    """
    Calculate fuel consumed over a period using advanced model.

    Args:
        p_rated_mw: DG rated capacity in MW
        p_actual_mw: Actual power output in MW
        hours: Duration in hours
        f0: No-load coefficient
        f1: Load coefficient

    Returns:
        Fuel consumed in liters
    """
    rate = calculate_fuel_rate(p_rated_mw, p_actual_mw, f0, f1)
    return rate * hours


def calculate_fuel_flat_rate(
    p_actual_mw: float,
    hours: float,
    flat_rate: float = DEFAULT_FLAT_RATE
) -> float:
    """
    Calculate fuel using simple flat rate model.

    Args:
        p_actual_mw: Actual power output in MW
        hours: Duration in hours
        flat_rate: L/kWh

    Returns:
        Fuel consumed in liters
    """
    if p_actual_mw <= 0:
        return 0.0

    energy_kwh = p_actual_mw * 1000 * hours
    return energy_kwh * flat_rate


def calculate_fuel(
    p_rated_mw: float,
    p_actual_mw: float,
    hours: float = 1.0,
    config: FuelConfig = None
) -> float:
    """
    Calculate fuel consumption based on configuration.

    Args:
        p_rated_mw: DG rated capacity in MW
        p_actual_mw: Actual power output in MW
        hours: Duration in hours
        config: Fuel configuration

    Returns:
        Fuel consumed in liters
    """
    if config is None:
        config = FuelConfig()

    if config.enabled:
        return calculate_fuel_consumption(
            p_rated_mw, p_actual_mw, hours,
            config.f0, config.f1
        )
    else:
        return calculate_fuel_flat_rate(
            p_actual_mw, hours, config.flat_rate
        )


# =============================================================================
# EFFICIENCY ANALYSIS
# =============================================================================

def calculate_efficiency_at_load(
    p_rated_mw: float,
    load_pct: float,
    f0: float = DEFAULT_F0,
    f1: float = DEFAULT_F1
) -> Dict:
    """
    Calculate fuel efficiency metrics at a specific load level.

    Args:
        p_rated_mw: DG rated capacity in MW
        load_pct: Load percentage (0-100)
        f0: No-load coefficient
        f1: Load coefficient

    Returns:
        Dict with efficiency metrics
    """
    p_actual_mw = p_rated_mw * (load_pct / 100)
    fuel_rate = calculate_fuel_rate(p_rated_mw, p_actual_mw, f0, f1)

    # Avoid division by zero
    p_actual_kw = p_actual_mw * 1000
    if p_actual_kw > 0 and fuel_rate > 0:
        specific_consumption = fuel_rate / p_actual_kw  # L/kWh
        efficiency = 1 / specific_consumption  # kWh/L
    else:
        specific_consumption = float('inf') if p_actual_kw == 0 else 0
        efficiency = 0

    return {
        'load_pct': load_pct,
        'output_mw': p_actual_mw,
        'output_kw': p_actual_kw,
        'fuel_rate_lph': fuel_rate,
        'specific_consumption_lpkwh': specific_consumption,
        'energy_efficiency_kwhpl': efficiency
    }


def get_efficiency_table(
    p_rated_mw: float,
    load_levels: List[float] = None,
    f0: float = DEFAULT_F0,
    f1: float = DEFAULT_F1
) -> List[Dict]:
    """
    Generate efficiency table at multiple load levels.

    Args:
        p_rated_mw: DG rated capacity in MW
        load_levels: List of load percentages to calculate
        f0: No-load coefficient
        f1: Load coefficient

    Returns:
        List of efficiency dicts at each load level
    """
    if load_levels is None:
        load_levels = [25, 50, 75, 100]

    return [
        calculate_efficiency_at_load(p_rated_mw, load, f0, f1)
        for load in load_levels
    ]


def compare_flat_vs_advanced(
    p_rated_mw: float,
    p_actual_mw: float,
    hours: float,
    f0: float = DEFAULT_F0,
    f1: float = DEFAULT_F1,
    flat_rate: float = DEFAULT_FLAT_RATE
) -> Dict:
    """
    Compare fuel consumption between flat rate and advanced model.

    Args:
        p_rated_mw: DG rated capacity in MW
        p_actual_mw: Actual power output in MW
        hours: Duration in hours
        f0: No-load coefficient
        f1: Load coefficient
        flat_rate: Flat rate (L/kWh)

    Returns:
        Dict comparing both models
    """
    fuel_advanced = calculate_fuel_consumption(p_rated_mw, p_actual_mw, hours, f0, f1)
    fuel_flat = calculate_fuel_flat_rate(p_actual_mw, hours, flat_rate)

    load_pct = (p_actual_mw / p_rated_mw * 100) if p_rated_mw > 0 else 0

    return {
        'load_pct': load_pct,
        'fuel_advanced_liters': fuel_advanced,
        'fuel_flat_liters': fuel_flat,
        'difference_liters': fuel_advanced - fuel_flat,
        'difference_pct': ((fuel_advanced - fuel_flat) / fuel_flat * 100) if fuel_flat > 0 else 0
    }


# =============================================================================
# ANNUAL FUEL ANALYSIS
# =============================================================================

def calculate_annual_fuel_summary(
    hourly_outputs: List[float],
    p_rated_mw: float,
    config: FuelConfig = None
) -> Dict:
    """
    Calculate annual fuel consumption from hourly DG output data.

    Args:
        hourly_outputs: List of 8760 hourly DG output values (MW)
        p_rated_mw: DG rated capacity in MW
        config: Fuel configuration

    Returns:
        Dict with annual fuel summary
    """
    if config is None:
        config = FuelConfig()

    total_fuel = 0.0
    total_energy_mwh = 0.0
    running_hours = 0

    for output in hourly_outputs:
        if output > 0:
            running_hours += 1
            total_energy_mwh += output

            if config.enabled:
                total_fuel += calculate_fuel_consumption(
                    p_rated_mw, output, 1.0,
                    config.f0, config.f1
                )
            else:
                total_fuel += calculate_fuel_flat_rate(
                    output, 1.0, config.flat_rate
                )

    # Calculate averages
    avg_load_pct = (total_energy_mwh / (running_hours * p_rated_mw) * 100) if running_hours > 0 and p_rated_mw > 0 else 0
    avg_fuel_rate = total_fuel / running_hours if running_hours > 0 else 0
    specific_consumption = total_fuel / (total_energy_mwh * 1000) if total_energy_mwh > 0 else 0

    return {
        'total_fuel_liters': total_fuel,
        'total_energy_mwh': total_energy_mwh,
        'running_hours': running_hours,
        'avg_load_pct': avg_load_pct,
        'avg_fuel_rate_lph': avg_fuel_rate,
        'specific_consumption_lpkwh': specific_consumption,
        'fuel_cost': total_fuel * config.fuel_price_per_liter,
        'capacity_factor_pct': (running_hours / 8760) * 100
    }


# =============================================================================
# CYCLE CHARGING FUEL SAVINGS
# =============================================================================

def estimate_cycle_charging_savings(
    baseline_fuel: float,
    baseline_avg_load_pct: float,
    cycle_charging_load_pct: float = 70.0,
    p_rated_mw: float = 25.0,
    f0: float = DEFAULT_F0,
    f1: float = DEFAULT_F1
) -> Dict:
    """
    Estimate fuel savings from cycle charging mode.

    Cycle charging runs the DG at higher load (more efficient) for shorter time,
    instead of following load at partial (inefficient) loading.

    Args:
        baseline_fuel: Baseline fuel consumption (liters)
        baseline_avg_load_pct: Average load % in baseline mode
        cycle_charging_load_pct: Target load % in cycle charging mode
        p_rated_mw: DG rated capacity
        f0: No-load coefficient
        f1: Load coefficient

    Returns:
        Dict with savings estimates
    """
    # Get efficiency at both load levels
    baseline_eff = calculate_efficiency_at_load(p_rated_mw, baseline_avg_load_pct, f0, f1)
    cycle_eff = calculate_efficiency_at_load(p_rated_mw, cycle_charging_load_pct, f0, f1)

    # Estimate savings based on specific consumption difference
    if baseline_eff['specific_consumption_lpkwh'] > 0:
        efficiency_improvement = 1 - (cycle_eff['specific_consumption_lpkwh'] /
                                      baseline_eff['specific_consumption_lpkwh'])
    else:
        efficiency_improvement = 0

    estimated_savings = baseline_fuel * efficiency_improvement

    return {
        'baseline_specific_lpkwh': baseline_eff['specific_consumption_lpkwh'],
        'cycle_charging_specific_lpkwh': cycle_eff['specific_consumption_lpkwh'],
        'efficiency_improvement_pct': efficiency_improvement * 100,
        'estimated_fuel_savings_liters': estimated_savings,
        'estimated_fuel_savings_pct': efficiency_improvement * 100
    }
