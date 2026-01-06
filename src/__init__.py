"""
BESS Simulation Core Modules

This package contains the core simulation engine and data loading utilities
for Battery Energy Storage System (BESS) sizing and optimization.
"""

from .data_loader import load_solar_profile, get_solar_statistics
from .dispatch_engine import run_simulation, SimulationParams, calculate_metrics

__all__ = [
    'load_solar_profile',
    'get_solar_statistics',
    'run_simulation',
    'SimulationParams',
    'calculate_metrics'
]

__version__ = '1.0.0'
