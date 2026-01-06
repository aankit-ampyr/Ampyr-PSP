"""
Configuration parameters for BESS Sizing Tool
"""

# Project Parameters
TARGET_DELIVERY_MW = 25.0  # Binary delivery target in MW
SOLAR_CAPACITY_MW = 67.0   # Maximum solar generation capacity

# Battery Technical Parameters
MIN_SOC = 0.05  # Minimum State of Charge (5%)
MAX_SOC = 0.95  # Maximum State of Charge (95%)
ROUND_TRIP_EFFICIENCY = 0.87  # Round-trip efficiency
ONE_WAY_EFFICIENCY = 0.87 ** 0.5  # One-way efficiency (sqrt of RTE)
C_RATE_CHARGE = 1.0  # Maximum charge rate as fraction of capacity
C_RATE_DISCHARGE = 1.0  # Maximum discharge rate as fraction of capacity

# Battery Sizing Range
MIN_BATTERY_SIZE_MWH = 10  # Minimum battery size to test
MAX_BATTERY_SIZE_MWH = 500  # Maximum battery size to test
BATTERY_SIZE_STEP_MWH = 5  # Step size for battery sizing

# Optimization Parameters
MARGINAL_IMPROVEMENT_THRESHOLD = 300  # Hours per 10 MWh threshold for optimization
MARGINAL_INCREMENT_MWH = 10  # Increment for marginal analysis

# Degradation Parameters
DEGRADATION_PER_CYCLE = 0.0015  # Capacity degradation per cycle (0.15%)

# Simulation Parameters
HOURS_PER_YEAR = 8760  # Hours in a year
DAYS_PER_YEAR = 365  # Days in a year
INITIAL_SOC = 0.5  # Initial state of charge (50%)
MAX_SIMULATIONS = 200  # Maximum simulations for resource limits
SIMULATION_START_YEAR = 2024  # Default year for hourly data timestamps

# Tolerance Parameters
DELIVERY_TOLERANCE_MW = 0.01  # Tolerance for delivery verification
FLOATING_POINT_TOLERANCE = 0.001  # Tolerance for floating point comparisons

# File Paths
SOLAR_PROFILE_PATH = "Inputs/Solar Profile.csv"

# Diesel Generator Parameters
DG_CAPACITY_MW = 25.0  # DG rated capacity (MW)
DG_SOC_ON_THRESHOLD = 0.20  # Start DG when SOC <= 20%
DG_SOC_OFF_THRESHOLD = 0.80  # Stop DG when SOC >= 80%
DG_LOAD_MW = 25.0  # Fixed load for DG scenario (MW)

# =============================================================================
# ADVANCED DEGRADATION PARAMETERS
# =============================================================================

# Calendar aging
CALENDAR_DEGRADATION_RATE = 0.02  # 2% per year baseline

# DoD stress curve for LFP chemistry (maps DoD% to stress factor)
DEFAULT_DOD_STRESS_CURVE = {
    10: 0.3,    # 10% DoD = 0.3x damage vs 80% DoD
    20: 0.5,
    40: 0.7,
    60: 0.85,
    80: 1.0,    # Baseline
    100: 1.2    # Deep discharge = 1.2x damage
}

# Overbuild/Augmentation defaults
DEFAULT_OVERBUILD_FACTOR = 0.20  # 20%
DEFAULT_AUGMENTATION_YEAR = 8

# =============================================================================
# FUEL MODEL PARAMETERS
# =============================================================================

# Willans line fuel model coefficients
DG_FUEL_F0 = 0.03  # L/hr per kW rated (no-load coefficient)
DG_FUEL_F1 = 0.22  # L/kWh output (load coefficient)
DG_FUEL_FLAT_RATE = 0.25  # L/kWh (flat rate when advanced model disabled)
DG_FUEL_PRICE_PER_LITER = 1.50  # Default fuel price

# Cycle charging parameters
CYCLE_CHARGING_MIN_LOAD_PCT = 70.0  # Minimum DG load in cycle charging mode
CYCLE_CHARGING_OFF_SOC = 80.0  # Stop cycle charging at this SOC %

# =============================================================================
# FINANCIAL MODEL PARAMETERS
# =============================================================================

# Capital costs ($/unit)
DEFAULT_BESS_COST_PER_MWH = 300_000  # $/MWh
DEFAULT_BESS_COST_PER_MW = 50_000    # $/MW (power electronics)
DEFAULT_DG_COST_PER_MW = 200_000     # $/MW
DEFAULT_AUGMENTATION_COST_PER_MWH = 250_000  # $/MWh

# Operating costs
DEFAULT_BESS_OM_PER_MWH_YEAR = 5_000  # $/MWh/year
DEFAULT_DG_OM_PER_MW_YEAR = 10_000   # $/MW/year

# Financial parameters
DEFAULT_DISCOUNT_RATE = 0.08  # 8% WACC
PROJECT_LIFE_YEARS = 20
DEFAULT_FUEL_ESCALATION_RATE = 0.025  # 2.5% per year