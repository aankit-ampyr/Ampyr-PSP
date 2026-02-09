"""
Green Energy Optimization Module

Performs 4D sweep of Solar × BESS × Container × DG to find configurations
meeting green energy targets with acceptable wastage.
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Callable
import pandas as pd

from src.dispatch_engine import SimulationParams, run_simulation, calculate_metrics
from src.data_loader import scale_solar_profile, get_base_solar_peak_capacity


def parse_template_id(template_id):
    """Convert template ID from string ('T0'-'T6') or int (0-6) to int.

    Args:
        template_id: Either 'T0'-'T6' (str) or 0-6 (int)

    Returns:
        int: Template ID as integer (0-6), defaults to 0 if invalid

    Examples:
        >>> parse_template_id('T0')
        0
        >>> parse_template_id('T3')
        3
        >>> parse_template_id(5)
        5
        >>> parse_template_id('invalid')
        0
    """
    if isinstance(template_id, int):
        return max(0, min(6, template_id))  # Clamp to valid range
    if isinstance(template_id, str) and template_id.startswith('T'):
        try:
            tid = int(template_id[1:])
            return max(0, min(6, tid))  # Clamp to valid range
        except (ValueError, IndexError):
            return 0
    # Fallback for numeric strings
    try:
        return max(0, min(6, int(template_id)))
    except (ValueError, TypeError):
        return 0


# Container specifications (matching Step 3)
CONTAINER_SPECS = {
    '5mwh_2.5mw': {'energy_mwh': 5, 'power_mw': 2.5, 'duration_hr': 2, 'label': '2-hour (0.5C)'},
    '5mwh_1.25mw': {'energy_mwh': 5, 'power_mw': 1.25, 'duration_hr': 4, 'label': '4-hour (0.25C)'},
}


@dataclass
class GreenEnergyResult:
    """Results for a single Solar-BESS-DG configuration."""
    # Configuration dimensions
    solar_capacity_mw: float
    bess_capacity_mwh: float
    duration_hr: float
    power_mw: float
    containers: int
    dg_capacity_mw: float

    # Delivery metrics
    delivery_pct: float
    green_energy_pct: float      # Energy-based (MWh)
    green_hours_pct: float       # Time-based (hours)
    green_hours_pct_mar_oct: float  # Time-based (hours) for March-October
    wastage_pct: float

    # Hour counts
    delivery_hours: int
    load_hours: int
    green_hours: int
    dg_runtime_hours: int
    dg_starts: int

    # Other metrics
    total_cycles: float
    unserved_mwh: float
    fuel_liters: float

    # Energy totals (GWh)
    total_solar_generated_gwh: float
    total_solar_curtailed_gwh: float
    total_green_delivered_gwh: float
    total_energy_delivered_gwh: float

    # Viability flags
    meets_green_target: bool
    meets_wastage_limit: bool
    is_viable: bool  # Both targets met


@dataclass
class GreenEnergyOptimizationParams:
    """Parameters for green energy optimization."""
    # Solar capacity sweep
    solar_min_mw: float = 50.0
    solar_max_mw: float = 200.0
    solar_step_mw: float = 25.0

    # BESS capacity sweep
    bess_min_mwh: float = 0.0
    bess_max_mwh: float = 300.0
    bess_step_mwh: float = 25.0

    # DG capacity sweep
    dg_enabled: bool = True
    dg_min_mw: float = 0.0
    dg_max_mw: float = 30.0
    dg_step_mw: float = 5.0

    # Container types to iterate
    container_types: List[str] = field(default_factory=lambda: ['5mwh_2.5mw', '5mwh_1.25mw'])

    # Targets and constraints
    green_energy_target_pct: float = 50.0  # Minimum green %
    max_wastage_pct: Optional[float] = 20.0  # Maximum acceptable wastage

    # Dispatch template from Step 2
    dispatch_template: str = 'T0'


def run_green_energy_optimization(
    base_solar_profile: List[float],
    base_solar_capacity_mw: float,
    load_profile: List[float],
    bess_config: Dict,  # From wizard setup (efficiency, SOC limits, etc.)
    dg_config: Dict,  # From wizard setup (DG settings)
    dispatch_rules: Dict,  # From wizard rules
    opt_params: GreenEnergyOptimizationParams,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Run 4D optimization sweep: Solar × BESS × Container × DG.

    Args:
        base_solar_profile: Original solar profile (8760 hours)
        base_solar_capacity_mw: Peak capacity of base profile
        load_profile: Load profile (8760 hours)
        bess_config: BESS configuration from wizard
        dg_config: DG configuration from wizard
        dispatch_rules: Dispatch rules from wizard
        opt_params: Optimization parameters
        progress_callback: Optional function(current, total, message)

    Returns:
        dict: {
            'all_results': List[GreenEnergyResult],
            'viable_configs': List[GreenEnergyResult],
            'summary': dict,
            'optimization_params': dict
        }
    """
    # Generate solar capacity range
    solar_capacities = list(range(
        int(opt_params.solar_min_mw),
        int(opt_params.solar_max_mw) + 1,
        int(opt_params.solar_step_mw)
    ))

    # Generate BESS capacity range
    bess_capacities = list(range(
        int(opt_params.bess_min_mwh),
        int(opt_params.bess_max_mwh) + 1,
        int(opt_params.bess_step_mwh)
    ))

    # Generate DG capacity range
    if opt_params.dg_enabled and opt_params.dg_step_mw > 0:
        dg_capacities = list(range(
            int(opt_params.dg_min_mw),
            int(opt_params.dg_max_mw) + 1,
            int(opt_params.dg_step_mw)
        ))
    else:
        dg_capacities = [0]

    # Container types
    container_types = opt_params.container_types or ['5mwh_2.5mw', '5mwh_1.25mw']

    # Total simulations (4D)
    total_sims = len(solar_capacities) * len(bess_capacities) * len(container_types) * len(dg_capacities)
    current_sim = 0

    all_results = []

    # 4D Sweep: Solar × BESS × Container × DG
    for solar_mw in solar_capacities:
        # Scale solar profile for this capacity
        scaled_solar = scale_solar_profile(
            base_solar_profile,
            base_solar_capacity_mw,
            solar_mw
        )

        solar_results = []

        for bess_mwh in bess_capacities:
            for container_type in container_types:
                spec = CONTAINER_SPECS.get(container_type, CONTAINER_SPECS['5mwh_2.5mw'])
                duration_hr = spec['duration_hr']
                power_mw = bess_mwh / duration_hr if bess_mwh > 0 else 0
                containers = int(bess_mwh / spec['energy_mwh']) if bess_mwh > 0 else 0

                for dg_mw in dg_capacities:
                    current_sim += 1

                    if progress_callback:
                        progress_callback(
                            current_sim,
                            total_sims,
                            f"Solar={solar_mw}MW, BESS={bess_mwh}MWh ({duration_hr}hr), DG={dg_mw}MW"
                        )

                    # Build simulation parameters
                    sim_params = SimulationParams(
                        load_profile=load_profile,
                        solar_profile=scaled_solar,
                        bess_capacity=bess_mwh,
                        bess_charge_power=power_mw,
                        bess_discharge_power=power_mw,
                        bess_efficiency=bess_config.get('bess_efficiency', 87),
                        bess_min_soc=bess_config.get('bess_min_soc', 5),
                        bess_max_soc=bess_config.get('bess_max_soc', 95),
                        bess_initial_soc=bess_config.get('bess_initial_soc', 50),
                        bess_daily_cycle_limit=bess_config.get('bess_daily_cycle_limit', 2.0),
                        bess_enforce_cycle_limit=bess_config.get('bess_enforce_cycle_limit', False),
                        dg_enabled=opt_params.dg_enabled and dg_mw > 0,
                        dg_capacity=dg_mw,
                        dg_charges_bess=dispatch_rules.get('dg_charges_bess', False),
                        dg_load_priority=dispatch_rules.get('dg_load_priority', 'bess_first'),
                        dg_takeover_mode=dispatch_rules.get('dg_takeover_mode', False),
                        night_start_hour=dispatch_rules.get('night_start', 18),
                        night_end_hour=dispatch_rules.get('night_end', 6),
                        day_start_hour=dispatch_rules.get('day_start', 6),
                        day_end_hour=dispatch_rules.get('day_end', 18),
                        blackout_start_hour=dispatch_rules.get('blackout_start', 0),
                        blackout_end_hour=dispatch_rules.get('blackout_end', 0),
                        dg_soc_on_threshold=dispatch_rules.get('soc_on_threshold', 30),
                        dg_soc_off_threshold=dispatch_rules.get('soc_off_threshold', 80),
                        dg_fuel_curve_enabled=dg_config.get('dg_fuel_curve_enabled', False),
                        dg_fuel_f0=dg_config.get('dg_fuel_f0', 0.03),
                        dg_fuel_f1=dg_config.get('dg_fuel_f1', 0.22),
                        dg_fuel_flat_rate=dg_config.get('dg_fuel_flat_rate', 0.25),
                        cycle_charging_enabled=dispatch_rules.get('cycle_charging_enabled', False),
                        cycle_charging_min_load_pct=dispatch_rules.get('cycle_charging_min_load_pct', 70.0),
                        cycle_charging_off_soc=dispatch_rules.get('cycle_charging_off_soc', 80.0),
                    )

                    # Run simulation
                    template_id = parse_template_id(opt_params.dispatch_template)
                    hourly_results = run_simulation(sim_params, template_id, num_hours=8760)
                    metrics = calculate_metrics(hourly_results, sim_params)

                    # Check constraints
                    meets_green_target = metrics.pct_green_energy >= opt_params.green_energy_target_pct

                    if opt_params.max_wastage_pct is not None:
                        meets_wastage_limit = metrics.pct_solar_curtailed <= opt_params.max_wastage_pct
                    else:
                        meets_wastage_limit = True

                    is_viable = meets_green_target and meets_wastage_limit

                    # Create result with all metrics
                    # Note: All metrics fields are guaranteed to exist in SummaryMetrics dataclass
                    result = GreenEnergyResult(
                        # Configuration
                        solar_capacity_mw=solar_mw,
                        bess_capacity_mwh=bess_mwh,
                        duration_hr=duration_hr,
                        power_mw=power_mw,
                        containers=containers,
                        dg_capacity_mw=dg_mw,
                        # Delivery metrics
                        delivery_pct=metrics.pct_full_delivery,
                        green_energy_pct=metrics.pct_green_energy,
                        green_hours_pct=metrics.pct_green_delivery,
                        green_hours_pct_mar_oct=metrics.pct_green_delivery_mar_oct,
                        wastage_pct=metrics.pct_solar_curtailed,
                        # Hour counts
                        delivery_hours=metrics.hours_full_delivery,
                        load_hours=metrics.hours_with_load,
                        green_hours=metrics.hours_green_delivery,
                        dg_runtime_hours=metrics.dg_runtime_hours,
                        dg_starts=metrics.dg_starts,
                        # Other metrics
                        total_cycles=metrics.bess_equivalent_cycles,
                        unserved_mwh=metrics.total_unserved,
                        fuel_liters=metrics.total_fuel_consumed,
                        # Energy totals
                        total_solar_generated_gwh=metrics.total_solar_generation / 1000,
                        total_solar_curtailed_gwh=metrics.total_solar_curtailed / 1000,
                        total_green_delivered_gwh=metrics.total_green_energy_delivered / 1000,
                        total_energy_delivered_gwh=metrics.total_energy_delivered / 1000,
                        # Viability
                        meets_green_target=meets_green_target,
                        meets_wastage_limit=meets_wastage_limit,
                        is_viable=is_viable
                    )

                    all_results.append(result)
                    solar_results.append(result)

    # Filter viable configurations
    viable_configs = [r for r in all_results if r.is_viable]

    # Find minimums
    min_solar_for_target = None
    min_bess_for_target = None
    min_dg_for_target = None

    if viable_configs:
        min_solar_for_target = min(viable_configs, key=lambda r: r.solar_capacity_mw).solar_capacity_mw
        min_bess_for_target = min(viable_configs, key=lambda r: r.bess_capacity_mwh).bess_capacity_mwh
        min_dg_for_target = min(viable_configs, key=lambda r: r.dg_capacity_mw).dg_capacity_mw

    # Summary
    summary = {
        'total_configs_tested': total_sims,
        'viable_count': len(viable_configs),
        'min_solar_for_target': min_solar_for_target,
        'min_bess_for_target': min_bess_for_target,
        'min_dg_for_target': min_dg_for_target,
        'green_target_pct': opt_params.green_energy_target_pct,
        'max_wastage_pct': opt_params.max_wastage_pct,
    }

    return {
        'all_results': all_results,
        'viable_configs': viable_configs,
        'summary': summary,
        'optimization_params': asdict(opt_params)
    }


def create_results_dataframe(results: List[GreenEnergyResult]) -> pd.DataFrame:
    """Convert results to DataFrame for display and export."""
    if not results:
        return pd.DataFrame()

    df = pd.DataFrame([asdict(r) for r in results])

    # Reorder columns to match Step 3 format + Solar MWp
    column_order = [
        # Configuration columns
        'solar_capacity_mw',
        'bess_capacity_mwh',
        'duration_hr',
        'power_mw',
        'containers',
        'dg_capacity_mw',
        # Delivery metrics
        'delivery_pct',
        'green_energy_pct',
        'green_hours_pct',
        'green_hours_pct_mar_oct',
        'wastage_pct',
        # Hour counts
        'delivery_hours',
        'load_hours',
        'green_hours',
        'dg_runtime_hours',
        'dg_starts',
        # Other metrics
        'total_cycles',
        'unserved_mwh',
        'fuel_liters',
        # Viability flags
        'is_viable',
        'meets_green_target',
        'meets_wastage_limit',
        # Energy totals (for detailed export)
        'total_green_delivered_gwh',
        'total_energy_delivered_gwh',
        'total_solar_generated_gwh',
        'total_solar_curtailed_gwh',
    ]

    # Only include columns that exist
    available_columns = [c for c in column_order if c in df.columns]
    return df[available_columns]
