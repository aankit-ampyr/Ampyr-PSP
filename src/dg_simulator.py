"""
Solar + BESS + Diesel Generator (DG) Simulator
Implements merit order dispatch with SOC-triggered DG control
"""

import numpy as np
from .battery_simulator import BatterySystem
from .config import (
    DG_CAPACITY_MW, DG_SOC_ON_THRESHOLD, DG_SOC_OFF_THRESHOLD, DG_LOAD_MW
)


class DieselGenerator:
    """
    Diesel Generator with SOC-triggered hysteresis control.

    Control Logic:
        - Turn ON when battery SOC <= soc_on_threshold
        - Turn OFF when battery SOC >= soc_off_threshold
        - Runs at full capacity when ON
    """

    def __init__(self, capacity_mw, config=None):
        """
        Initialize diesel generator.

        Args:
            capacity_mw: DG rated capacity in MW
            config: Optional configuration dictionary
        """
        self.capacity = capacity_mw

        # Use provided config or defaults
        if config:
            self.soc_on_threshold = config.get('DG_SOC_ON_THRESHOLD', DG_SOC_ON_THRESHOLD)
            self.soc_off_threshold = config.get('DG_SOC_OFF_THRESHOLD', DG_SOC_OFF_THRESHOLD)
        else:
            self.soc_on_threshold = DG_SOC_ON_THRESHOLD
            self.soc_off_threshold = DG_SOC_OFF_THRESHOLD

        # State tracking
        self.state = 'OFF'  # 'ON' or 'OFF'
        self.previous_state = 'OFF'

        # Metrics
        self.total_runtime_hours = 0
        self.total_starts = 0
        self.total_energy_generated = 0.0
        self.total_energy_to_load = 0.0
        self.total_energy_to_bess = 0.0

    def update_state(self, battery_soc):
        """
        Update DG state based on battery SOC (hysteresis control).

        Args:
            battery_soc: Current battery state of charge (0-1)
        """
        self.previous_state = self.state

        if self.state == 'OFF' and battery_soc <= self.soc_on_threshold:
            self.state = 'ON'
            self.total_starts += 1
        elif self.state == 'ON' and battery_soc >= self.soc_off_threshold:
            self.state = 'OFF'

    def run(self):
        """
        Run DG for one hour at full capacity.

        Returns:
            float: Energy generated (MWh) - equal to capacity when ON, 0 when OFF
        """
        if self.state == 'ON':
            energy = self.capacity  # Full capacity for 1 hour = capacity MWh
            self.total_runtime_hours += 1
            self.total_energy_generated += energy
            return energy
        return 0.0

    def record_energy_distribution(self, to_load, to_bess):
        """
        Record how DG energy was distributed.

        Args:
            to_load: Energy sent directly to load (MWh)
            to_bess: Energy sent to charge BESS (MWh)
        """
        self.total_energy_to_load += to_load
        self.total_energy_to_bess += to_bess

    def get_metrics(self):
        """
        Get accumulated DG metrics.

        Returns:
            dict: DG performance metrics
        """
        return {
            'dg_runtime_hours': self.total_runtime_hours,
            'dg_starts': self.total_starts,
            'dg_energy_generated_mwh': self.total_energy_generated,
            'dg_to_load_mwh': self.total_energy_to_load,
            'dg_to_bess_mwh': self.total_energy_to_bess
        }

    def reset(self):
        """Reset DG to initial state."""
        self.state = 'OFF'
        self.previous_state = 'OFF'
        self.total_runtime_hours = 0
        self.total_starts = 0
        self.total_energy_generated = 0.0
        self.total_energy_to_load = 0.0
        self.total_energy_to_bess = 0.0


def simulate_solar_bess_dg_year(battery_capacity_mwh, dg_capacity_mw, solar_profile, config=None):
    """
    Simulate Solar + BESS + DG system for one year (8760 hours).

    Merit Order for Load:
        1. Solar (direct to load, always first)
        2. DG (when running, serves load before BESS)
        3. BESS (discharge only if Solar + DG can't meet load)

    BESS Charging Priority:
        1. Excess Solar (after load is met)
        2. Excess DG (when DG is running and has spare capacity)

    DG Control Logic:
        - Turn ON when SOC <= dg_soc_on_threshold
        - Turn OFF when SOC >= dg_soc_off_threshold
        - Runs at full capacity when ON

    Args:
        battery_capacity_mwh: Battery capacity in MWh
        dg_capacity_mw: DG rated capacity in MW
        solar_profile: Array of hourly solar generation (MW)
        config: Optional configuration dictionary

    Returns:
        dict: Simulation results with BESS and DG metrics
    """
    # Initialize components
    battery = BatterySystem(battery_capacity_mwh, config)
    dg = DieselGenerator(dg_capacity_mw, config)

    # Get load from config or use default
    load_mw = config.get('DG_LOAD_MW', DG_LOAD_MW) if config else DG_LOAD_MW

    # Initialize results
    results = {
        # Delivery metrics
        'hours_delivered': 0,
        'energy_delivered_mwh': 0,

        # Solar distribution
        'solar_to_load_mwh': 0,
        'solar_charged_mwh': 0,
        'solar_wasted_mwh': 0,

        # BESS metrics
        'battery_discharged_mwh': 0,
    }

    # Hour-by-hour simulation
    hourly_data = []

    for hour in range(len(solar_profile)):
        solar_mw = solar_profile[hour]

        # Step 1: Update DG state based on current SOC (BEFORE dispatch)
        dg.update_state(battery.soc)

        # Initialize hour tracking
        hour_data = {
            'hour': hour,
            'solar_mw': solar_mw,
            'load_mw': load_mw,
            'solar_to_load_mw': 0,
            'bess_mw': 0,  # +ve discharge, -ve charge
            'bess_to_load_mw': 0,
            'soc_percent': battery.soc * 100,
            'bess_state': 'IDLE',
            'dg_state': dg.state,
            'dg_output_mw': 0,
            'dg_to_load_mw': 0,
            'dg_to_bess_mw': 0,
            'solar_charged_mwh': 0,
            'solar_wasted_mwh': 0,
            'unmet_load_mw': 0,
            'delivery': 'No'
        }

        remaining_load = load_mw

        # Step 2: Merit Order Dispatch for LOAD

        # Priority 1: Solar to Load (always first, no control)
        solar_to_load = min(solar_mw, remaining_load)
        remaining_load -= solar_to_load
        excess_solar = solar_mw - solar_to_load

        hour_data['solar_to_load_mw'] = solar_to_load
        results['solar_to_load_mwh'] += solar_to_load

        # Priority 2: DG to Load (if DG is ON) - DG serves load before BESS
        dg_output = 0
        dg_to_load = 0
        if dg.state == 'ON':
            dg_output = dg.run()  # Full capacity
            dg_to_load = min(dg_output, remaining_load)
            remaining_load -= dg_to_load
            hour_data['dg_output_mw'] = dg_output
            hour_data['dg_to_load_mw'] = dg_to_load

        excess_dg = dg_output - dg_to_load

        # Priority 3: BESS discharge (only if Solar + DG can't meet load)
        bess_to_load = 0
        if remaining_load > 0 and battery.get_available_energy() > 0:
            if battery.can_cycle('DISCHARGING'):
                bess_to_load = battery.discharge(remaining_load)
                remaining_load -= bess_to_load
                results['battery_discharged_mwh'] += bess_to_load
                hour_data['bess_mw'] = bess_to_load
                hour_data['bess_to_load_mw'] = bess_to_load
                hour_data['bess_state'] = 'DISCHARGING'

        # Step 3: Charge BESS (Solar first, then DG excess)
        solar_charged = 0
        dg_charged = 0

        # Charge from excess solar first
        if excess_solar > 0 and battery.get_charge_headroom() > 0:
            if battery.can_cycle('CHARGING'):
                solar_charged = battery.charge(excess_solar)
                results['solar_charged_mwh'] += solar_charged
                hour_data['solar_charged_mwh'] = solar_charged

                # Update BESS state if not already discharging
                if hour_data['bess_state'] != 'DISCHARGING':
                    hour_data['bess_state'] = 'CHARGING'
                    hour_data['bess_mw'] = -solar_charged

        # Charge from excess DG
        if excess_dg > 0 and battery.get_charge_headroom() > 0:
            if battery.can_cycle('CHARGING'):
                dg_charged = battery.charge(excess_dg)
                hour_data['dg_to_bess_mw'] = dg_charged

                # Update BESS state if not already set
                if hour_data['bess_state'] == 'IDLE':
                    hour_data['bess_state'] = 'CHARGING'
                    hour_data['bess_mw'] = -dg_charged
                elif hour_data['bess_state'] == 'CHARGING':
                    hour_data['bess_mw'] -= dg_charged

        # Record DG energy distribution
        if dg.state == 'ON':
            dg.record_energy_distribution(dg_to_load, dg_charged)

        # Step 4: Track wastage (only solar can be wasted, DG turns off when not needed)
        solar_wasted = excess_solar - solar_charged
        if solar_wasted > 0:
            results['solar_wasted_mwh'] += solar_wasted
            hour_data['solar_wasted_mwh'] = solar_wasted

        # Step 5: Delivery tracking
        hour_data['unmet_load_mw'] = remaining_load
        if remaining_load <= 0.001:  # Small tolerance for floating point
            results['hours_delivered'] += 1
            results['energy_delivered_mwh'] += load_mw
            hour_data['delivery'] = 'Yes'

        # Update SOC in hour data (after all operations)
        hour_data['soc_percent'] = battery.soc * 100

        # Update battery state and cycles
        battery.update_state_and_cycles(hour_data['bess_state'], hour)

        hourly_data.append(hour_data)

    # Add final day's cycles if not already added
    if battery.current_day_cycles > 0:
        battery.daily_cycles.append(battery.current_day_cycles)

    # Compile BESS metrics
    results['total_cycles'] = battery.total_cycles
    results['avg_daily_cycles'] = battery.get_avg_daily_cycles()
    results['max_daily_cycles'] = battery.get_max_daily_cycles()
    results['degradation_percent'] = battery.get_degradation()

    # Add DG metrics
    dg_metrics = dg.get_metrics()
    results.update(dg_metrics)

    # Add hourly data
    results['hourly_data'] = hourly_data

    return results


def find_optimal_dg_size(battery_capacity_mwh, solar_profile, config,
                         min_dg_percent=50, max_dg_percent=200, step_percent=10):
    """
    Find optimal DG size for 100% delivery (8760 hours).

    Tests a range of DG sizes and finds the minimum capacity that achieves
    100% delivery for the given BESS configuration.

    Args:
        battery_capacity_mwh: Fixed BESS capacity in MWh
        solar_profile: Hourly solar generation array (MW)
        config: Configuration dict (must include DG_LOAD_MW)
        min_dg_percent: Min DG size as % of load (default 50%)
        max_dg_percent: Max DG size as % of load (default 200%)
        step_percent: Step size as % of load (default 10%)

    Returns:
        dict: {
            'optimal_dg_mw': float - Optimal DG capacity
            'optimal_delivery_hours': int - Delivery hours at optimal size
            'is_100_percent': bool - Whether 100% delivery is achieved
            'all_results': list[dict] - Results for all tested DG sizes
            'reasoning': str - Explanation of optimal choice
        }
    """
    load_mw = config.get('DG_LOAD_MW', DG_LOAD_MW) if config else DG_LOAD_MW

    # Generate DG sizes to test (as % of load)
    dg_sizes = []
    for pct in range(min_dg_percent, max_dg_percent + step_percent, step_percent):
        dg_sizes.append(load_mw * pct / 100)

    all_results = []
    optimal_dg = None

    for dg_mw in dg_sizes:
        # Run simulation for this DG size
        results = simulate_solar_bess_dg_year(
            battery_capacity_mwh, dg_mw, solar_profile, config
        )

        result_entry = {
            'DG (MW)': round(dg_mw, 1),
            '% of Load': round((dg_mw / load_mw) * 100, 0),
            'Delivery Hours': results['hours_delivered'],
            'Delivery Rate (%)': round(results['hours_delivered'] / 87.6, 1),
            'DG Runtime (hrs)': results['dg_runtime_hours'],
            'DG Starts': results['dg_starts'],
            'DG Energy (MWh)': round(results['dg_energy_generated_mwh'], 0)
        }
        all_results.append(result_entry)

        # Track first DG size that achieves 100% delivery
        if optimal_dg is None and results['hours_delivered'] == 8760:
            optimal_dg = result_entry

    # Determine reasoning
    if optimal_dg:
        reasoning = (
            f"Minimum DG size for 100% delivery: {optimal_dg['DG (MW)']} MW "
            f"({int(optimal_dg['% of Load'])}% of load). "
            f"DG runs {optimal_dg['DG Runtime (hrs)']} hours/year with {optimal_dg['DG Starts']} starts."
        )
        is_100_percent = True
    else:
        # Find best achievable if 100% not reached
        best = max(all_results, key=lambda x: x['Delivery Hours'])
        optimal_dg = best
        reasoning = (
            f"100% delivery not achievable in tested range. "
            f"Best: {best['DG (MW)']} MW with {best['Delivery Hours']} hours "
            f"({best['Delivery Rate (%)']}% delivery rate). "
            f"Consider increasing DG search range or BESS size."
        )
        is_100_percent = False

    return {
        'optimal_dg_mw': optimal_dg['DG (MW)'],
        'optimal_delivery_hours': optimal_dg['Delivery Hours'],
        'is_100_percent': is_100_percent,
        'all_results': all_results,
        'reasoning': reasoning
    }
