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
INITIAL_SOC = 0.5  # Initial state of charge (50%)

# File Paths
SOLAR_PROFILE_PATH = "Inputs/Solar Profile.csv"

# Diesel Generator Parameters
DG_CAPACITY_MW = 25.0  # DG rated capacity (MW)
DG_SOC_ON_THRESHOLD = 0.20  # Start DG when SOC <= 20%
DG_SOC_OFF_THRESHOLD = 0.80  # Stop DG when SOC >= 80%
DG_LOAD_MW = 25.0  # Fixed load for DG scenario (MW)