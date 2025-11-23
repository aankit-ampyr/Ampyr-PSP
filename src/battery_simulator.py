"""
Battery Energy Storage System (BESS) Simulator
Implements state-based battery operation with cycle tracking
"""

import numpy as np
from .config import (
    MIN_SOC, MAX_SOC, ONE_WAY_EFFICIENCY,
    C_RATE_CHARGE, C_RATE_DISCHARGE,
    INITIAL_SOC, TARGET_DELIVERY_MW,
    DEGRADATION_PER_CYCLE, DAYS_PER_YEAR
)


class BatterySystem:
    """
    Battery Energy Storage System with state tracking and cycle counting.
    """

    def __init__(self, capacity_mwh, config=None):
        """
        Initialize battery system.

        Args:
            capacity_mwh: Battery capacity in MWh
            config: Optional configuration dictionary
        """
        self.capacity = capacity_mwh

        # Use provided config or defaults
        if config:
            self.min_soc = config.get('MIN_SOC', MIN_SOC)
            self.max_soc = config.get('MAX_SOC', MAX_SOC)
            self.one_way_efficiency = config.get('ONE_WAY_EFFICIENCY', ONE_WAY_EFFICIENCY)
            self.c_rate_charge = config.get('C_RATE_CHARGE', C_RATE_CHARGE)
            self.c_rate_discharge = config.get('C_RATE_DISCHARGE', C_RATE_DISCHARGE)
            self.initial_soc = config.get('INITIAL_SOC', INITIAL_SOC)
            self.max_daily_cycles = config.get('MAX_DAILY_CYCLES', 2.0)
            self.degradation_per_cycle = config.get('DEGRADATION_PER_CYCLE', DEGRADATION_PER_CYCLE)
        else:
            self.min_soc = MIN_SOC
            self.max_soc = MAX_SOC
            self.one_way_efficiency = ONE_WAY_EFFICIENCY
            self.c_rate_charge = C_RATE_CHARGE
            self.c_rate_discharge = C_RATE_DISCHARGE
            self.initial_soc = INITIAL_SOC
            self.max_daily_cycles = 2.0
            self.degradation_per_cycle = DEGRADATION_PER_CYCLE

        self.soc = self.initial_soc
        self.state = 'IDLE'  # Current state: IDLE, CHARGING, DISCHARGING
        self.previous_state = 'IDLE'
        self.total_cycles = 0.0
        self.daily_cycles = []  # Track cycles per day
        self.current_day_cycles = 0.0
        self.total_energy_charged = 0.0  # Total energy charged (MWh)
        self.total_energy_discharged = 0.0  # Total energy discharged (MWh)

    def get_available_energy(self):
        """Get available energy for discharge (MWh)."""
        return max(0, (self.soc - self.min_soc) * self.capacity)

    def get_charge_headroom(self):
        """Get available headroom for charging (MWh)."""
        return max(0, (self.max_soc - self.soc) * self.capacity)

    def charge(self, energy_mwh):
        """
        Charge the battery.

        Args:
            energy_mwh: Energy to charge (MWh) before efficiency

        Returns:
            float: Actual energy charged (MWh)
        """
        # Apply one-way efficiency
        energy_to_battery = energy_mwh * self.one_way_efficiency

        # Limit by headroom and C-rate
        max_charge = min(
            self.get_charge_headroom(),
            self.capacity * self.c_rate_charge
        )

        actual_charge = min(energy_to_battery, max_charge)

        # Update SOC
        self.soc += actual_charge / self.capacity
        self.soc = min(self.soc, self.max_soc)

        self.total_energy_charged += actual_charge

        return actual_charge / self.one_way_efficiency  # Return AC energy consumed

    def _is_cycle_transition(self, new_state):
        """
        Determine if a state transition would count as a cycle.

        A transition counts as 0.5 cycles when:
        - Transitioning from IDLE/CHARGING to DISCHARGING
        - Transitioning from IDLE/DISCHARGING to CHARGING

        Args:
            new_state: Proposed new state

        Returns:
            bool: True if this transition counts as 0.5 cycles
        """
        if self.state == new_state:
            return False

        return (
            ((self.state == 'IDLE' or self.state == 'CHARGING') and new_state == 'DISCHARGING') or
            ((self.state == 'IDLE' or self.state == 'DISCHARGING') and new_state == 'CHARGING')
        )

    def discharge(self, energy_mwh):
        """
        Discharge the battery.

        Args:
            energy_mwh: Energy to discharge (MWh) after efficiency

        Returns:
            float: Actual energy discharged (MWh) delivered
        """
        # Energy needed from battery (before efficiency)
        energy_from_battery = energy_mwh / self.one_way_efficiency

        # Limit by available energy and C-rate
        max_discharge = min(
            self.get_available_energy(),
            self.capacity * self.c_rate_discharge
        )

        actual_discharge = min(energy_from_battery, max_discharge)

        # Update SOC
        self.soc -= actual_discharge / self.capacity
        self.soc = max(self.soc, self.min_soc)

        self.total_energy_discharged += actual_discharge

        return actual_discharge * self.one_way_efficiency  # Return AC energy delivered

    def update_state_and_cycles(self, new_state, hour):
        """
        Update battery state and track cycles.

        Args:
            new_state: New battery state (IDLE, CHARGING, DISCHARGING)
            hour: Current simulation hour
        """
        # Track state transitions for cycle counting
        if self._is_cycle_transition(new_state):
            self.total_cycles += 0.5
            self.current_day_cycles += 0.5

        # Track daily cycles - reset at start of new day
        if hour > 0 and hour % 24 == 0:  # Start of new day
            self.daily_cycles.append(self.current_day_cycles)
            self.current_day_cycles = 0

        # Update state
        self.previous_state = self.state
        self.state = new_state

    def can_cycle(self, new_state):
        """
        Check if battery can perform a state transition without exceeding daily cycle limit.

        Args:
            new_state: Proposed new state

        Returns:
            bool: True if transition is allowed, False if it would exceed daily limit
        """
        # Check if this transition would add cycles
        if self._is_cycle_transition(new_state):
            # This transition would add 0.5 cycles
            if self.current_day_cycles + 0.5 > self.max_daily_cycles:
                return False  # Would exceed daily limit
        return True

    def get_avg_daily_cycles(self):
        """Calculate average daily cycles over a full year (365 days)."""
        if self.daily_cycles:
            return sum(self.daily_cycles) / DAYS_PER_YEAR
        return 0

    def get_max_daily_cycles(self):
        """Get maximum cycles in any single day."""
        if self.daily_cycles:
            return max(self.daily_cycles)
        return 0

    def get_degradation(self):
        """Calculate total degradation based on cycles."""
        return self.total_cycles * self.degradation_per_cycle


def simulate_bess_year(battery_capacity_mwh, solar_profile, config=None):
    """
    Simulate battery operation for a full year.

    Args:
        battery_capacity_mwh: Battery capacity in MWh
        solar_profile: Array of hourly solar generation (MW)
        config: Optional configuration dictionary

    Returns:
        dict: Simulation results with metrics
    """
    # Initialize battery with config
    battery = BatterySystem(battery_capacity_mwh, config)

    # Get target delivery from config or use default
    target_delivery_mw = config.get('TARGET_DELIVERY_MW', TARGET_DELIVERY_MW) if config else TARGET_DELIVERY_MW

    # Initialize results
    results = {
        'hours_delivered': 0,
        'energy_delivered_mwh': 0,
        'solar_charged_mwh': 0,
        'solar_wasted_mwh': 0,
        'battery_discharged_mwh': 0
    }

    # Hour-by-hour simulation
    hourly_data = []

    for hour in range(len(solar_profile)):
        solar_mw = solar_profile[hour]

        # Check if we can deliver target power
        # Get actual power available from battery (MW), respecting C-rate
        battery_available_mw = min(
            battery.get_available_energy(),  # Energy limit (MWh = MW for 1 hour)
            battery.capacity * battery.c_rate_discharge  # Power limit (MW)
        )

        # Check basic ability to deliver
        can_deliver_resources = (solar_mw + battery_available_mw) >= target_delivery_mw

        # If we have resources but need battery, check cycle limit
        if can_deliver_resources and solar_mw < target_delivery_mw:
            # Would need to discharge - check if allowed
            can_deliver = battery.can_cycle('DISCHARGING')
        else:
            can_deliver = can_deliver_resources

        # Initialize hour data with all required fields
        hour_data = {
            'hour': hour,
            'solar_mw': solar_mw,
            'bess_mw': 0,  # Will be set: positive for discharge, negative for charge
            'bess_charge_mwh': battery.soc * battery.capacity,  # Battery energy content at start of hour
            'soc_percent': battery.soc * 100,  # SOC as percentage
            'usable_energy_mwh': battery_available_mw,  # Usable energy accounting for min SOC
            'committed_mw': target_delivery_mw,  # Always 25 MW - this is the requirement profile
            'deficit_mw': 0,  # Will be calculated
            'delivery': 'Yes' if can_deliver else 'No',
            'bess_state': 'IDLE',  # Will be updated
            'wastage_mwh': 0  # Will be calculated
        }

        if can_deliver:
            # Attempt to deliver target power
            # Note: Will verify actual delivery success below before counting

            if solar_mw >= target_delivery_mw:
                # Solar alone can meet target - delivery successful
                results['hours_delivered'] += 1
                results['energy_delivered_mwh'] += target_delivery_mw
                # Excess solar available - charge battery
                excess_mw = solar_mw - target_delivery_mw
                if excess_mw > 0 and battery.get_charge_headroom() > 0:
                    # Check if we can cycle
                    proposed_state = 'CHARGING' if excess_mw > 0 else 'IDLE'
                    if battery.can_cycle(proposed_state):
                        charged = battery.charge(excess_mw)
                        results['solar_charged_mwh'] += charged
                        hour_data['bess_mw'] = -charged  # Negative for charging
                        new_state = proposed_state if charged > 0 else 'IDLE'

                        # Waste remaining excess
                        waste = excess_mw - charged
                        if waste > 0:
                            results['solar_wasted_mwh'] += waste
                            hour_data['wastage_mwh'] = waste
                    else:
                        # Cannot cycle - stay idle and waste solar
                        new_state = 'IDLE'
                        hour_data['bess_mw'] = 0
                        results['solar_wasted_mwh'] += excess_mw
                        hour_data['wastage_mwh'] = excess_mw
                else:
                    new_state = 'IDLE'
                    hour_data['bess_mw'] = 0
                    if excess_mw > 0:
                        results['solar_wasted_mwh'] += excess_mw
                        hour_data['wastage_mwh'] = excess_mw

                # No deficit when solar covers delivery
                hour_data['deficit_mw'] = 0
            else:
                # Need battery support - check if we can cycle
                if battery.can_cycle('DISCHARGING'):
                    deficit_mw = target_delivery_mw - solar_mw
                    discharged = battery.discharge(deficit_mw)
                    results['battery_discharged_mwh'] += discharged
                    hour_data['bess_mw'] = discharged  # Positive for discharge
                    new_state = 'DISCHARGING'

                    # Calculate actual deficit (if battery couldn't fully support)
                    actual_delivered = solar_mw + discharged
                    hour_data['deficit_mw'] = max(0, target_delivery_mw - actual_delivered)

                    # Only count as delivered if we actually met the target (within small tolerance)
                    if actual_delivered >= target_delivery_mw - 0.01:
                        results['hours_delivered'] += 1
                        results['energy_delivered_mwh'] += target_delivery_mw
                    else:
                        # Couldn't fully deliver
                        hour_data['delivery'] = 'No'
                else:
                    # Cannot cycle - stay idle, cannot deliver
                    new_state = 'IDLE'
                    hour_data['bess_mw'] = 0
                    hour_data['deficit_mw'] = target_delivery_mw - solar_mw
                    hour_data['delivery'] = 'No'
        else:
            # Cannot deliver - charge battery with available solar
            hour_data['deficit_mw'] = target_delivery_mw - (solar_mw + battery_available_mw)

            if solar_mw > 0 and battery.get_charge_headroom() > 0:
                # Check if we can cycle
                if battery.can_cycle('CHARGING'):
                    charged = battery.charge(solar_mw)
                    results['solar_charged_mwh'] += charged
                    hour_data['bess_mw'] = -charged  # Negative for charging
                    new_state = 'CHARGING' if charged > 0 else 'IDLE'

                    # Waste remaining solar
                    waste = solar_mw - charged
                    if waste > 0:
                        results['solar_wasted_mwh'] += waste
                        hour_data['wastage_mwh'] = waste
                else:
                    # Cannot cycle - stay idle and waste solar
                    new_state = 'IDLE'
                    hour_data['bess_mw'] = 0
                    results['solar_wasted_mwh'] += solar_mw
                    hour_data['wastage_mwh'] = solar_mw
            else:
                new_state = 'IDLE'
                hour_data['bess_mw'] = 0
                if solar_mw > 0:
                    results['solar_wasted_mwh'] += solar_mw
                    hour_data['wastage_mwh'] = solar_mw

        # Update battery state and cycles
        battery.update_state_and_cycles(new_state, hour)
        hour_data['bess_state'] = new_state
        hourly_data.append(hour_data)

    # Add final day's cycles if not already added
    if battery.current_day_cycles > 0:
        battery.daily_cycles.append(battery.current_day_cycles)

    # Compile final results
    results['total_cycles'] = battery.total_cycles
    results['avg_daily_cycles'] = battery.get_avg_daily_cycles()
    results['max_daily_cycles'] = battery.get_max_daily_cycles()
    results['degradation_percent'] = battery.get_degradation()
    results['hourly_data'] = hourly_data

    return results