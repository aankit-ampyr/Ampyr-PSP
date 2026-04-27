"""
Dispatch Energy Module — Simplified hourly BESS dispatch for financial model.

Takes an 8760-hour solar profile and produces monthly energy aggregates:
- Solar+BESS energy delivered to DC load
- Gas energy delivered to DC load
- Solar surplus (generation exceeding load + BESS capacity)
- Total solar generation per month

Used to feed the financial model's tariff-based revenue calculation.
"""

import csv
import numpy as np
from datetime import datetime
from pathlib import Path


# Days in each month (non-leap year)
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
HOURS_IN_MONTH = [d * 24 for d in DAYS_IN_MONTH]
MONTH_START_HOUR = [sum(HOURS_IN_MONTH[:m]) for m in range(12)]


def load_solar_profile(csv_path: str | Path) -> np.ndarray:
    """
    Load an 8760-hour solar profile from CSV.

    Expected format: datetime,MW_value (no header)
    Returns: numpy array of 8760 hourly MW values.
    """
    values = []
    with open(csv_path) as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                values.append(float(row[1]))

    profile = np.array(values)
    if len(profile) != 8760:
        raise ValueError(f"Solar profile must have 8760 rows, got {len(profile)}")
    return profile


def run_hourly_dispatch(
    solar_mw: np.ndarray,
    load_mw: float = 25.0,
    bess_mwh: float = 250.0,
    bess_mw: float = 62.5,
    rte: float = 0.87,
    min_soc: float = 0.05,
    max_soc: float = 0.95,
) -> dict:
    """
    Run simplified hourly BESS dispatch for 8760 hours.

    Logic:
    - Each hour: solar serves load first, excess charges BESS
    - If solar < load, discharge BESS to fill the gap
    - Remaining deficit = gas energy
    - BESS has round-trip efficiency, SOC limits, power limits

    Returns dict with 8760-element arrays:
        'solar_to_load', 'bess_to_load', 'gas_to_load',
        'solar_to_bess', 'solar_surplus', 'soc'
    """
    one_way_eff = rte ** 0.5
    n = len(solar_mw)

    solar_to_load = np.zeros(n)
    bess_to_load = np.zeros(n)
    gas_to_load = np.zeros(n)
    solar_to_bess = np.zeros(n)
    solar_surplus = np.zeros(n)
    soc_arr = np.zeros(n)

    soc = min_soc  # start at minimum SOC

    for h in range(n):
        s = solar_mw[h]

        if s >= load_mw:
            # Solar meets full load
            solar_to_load[h] = load_mw
            excess = s - load_mw

            # Charge BESS from excess
            charge_room_mwh = (max_soc - soc) * bess_mwh
            charge_power = min(excess, bess_mw)
            # Energy into battery = charge_power × 1hr × one_way_eff
            charge_energy = min(charge_power, charge_room_mwh / one_way_eff)
            actual_charge = charge_energy * one_way_eff
            soc += actual_charge / bess_mwh

            solar_to_bess[h] = charge_energy
            solar_surplus[h] = excess - charge_energy
        else:
            # Solar < load
            solar_to_load[h] = s
            deficit = load_mw - s

            # Discharge BESS
            usable_mwh = (soc - min_soc) * bess_mwh
            discharge_power = min(deficit, bess_mw)
            # Energy from battery = min(what we need, what's available × eff)
            discharge_from_bess = min(discharge_power, usable_mwh * one_way_eff)
            soc -= (discharge_from_bess / one_way_eff) / bess_mwh

            bess_to_load[h] = discharge_from_bess
            gas_to_load[h] = deficit - discharge_from_bess

        soc_arr[h] = soc

    return {
        'solar_to_load': solar_to_load,
        'bess_to_load': bess_to_load,
        'gas_to_load': gas_to_load,
        'solar_to_bess': solar_to_bess,
        'solar_surplus': solar_surplus,
        'soc': soc_arr,
    }


def aggregate_to_monthly(hourly: dict, solar_mw: np.ndarray) -> dict:
    """
    Aggregate 8760 hourly dispatch results to 12 monthly totals.

    Returns dict with 12-element arrays (one per calendar month):
        'solar_bess_to_dc'  — MWh delivered from solar+BESS
        'gas_energy'        — MWh delivered from gas
        'solar_surplus'     — MWh of excess solar (curtailed/wasted)
        'solar_gen'         — MWh of total solar generation
    """
    solar_bess_to_dc = np.zeros(12)
    gas_energy = np.zeros(12)
    surplus = np.zeros(12)
    solar_gen = np.zeros(12)

    h = 0
    for m in range(12):
        hours = HOURS_IN_MONTH[m]
        for _ in range(hours):
            solar_bess_to_dc[m] += hourly['solar_to_load'][h] + hourly['bess_to_load'][h]
            gas_energy[m] += hourly['gas_to_load'][h]
            surplus[m] += hourly['solar_surplus'][h]
            solar_gen[m] += solar_mw[h]
            h += 1

    return {
        'solar_bess_to_dc': solar_bess_to_dc,
        'gas_energy': gas_energy,
        'solar_surplus': surplus,
        'solar_gen': solar_gen,
    }


def compute_monthly_energy(
    solar_profile_path: str | Path,
    load_mw: float = 25.0,
    bess_mwh: float = 250.0,
    bess_mw: float = 62.5,
    rte: float = 0.87,
    min_soc: float = 0.05,
    max_soc: float = 0.95,
) -> dict:
    """
    High-level function: load solar profile, run dispatch, return monthly splits.

    Returns dict with:
        'monthly'   — 12-element monthly energy arrays
        'annual'    — annual summary totals
        'green_pct' — annual green energy share
        'gas_pct'   — annual gas energy share
    """
    solar_mw = load_solar_profile(solar_profile_path)

    hourly = run_hourly_dispatch(
        solar_mw, load_mw, bess_mwh, bess_mw, rte, min_soc, max_soc
    )

    monthly = aggregate_to_monthly(hourly, solar_mw)

    # Annual totals
    total_demand = load_mw * 8760
    green_total = monthly['solar_bess_to_dc'].sum()
    gas_total = monthly['gas_energy'].sum()

    return {
        'monthly': monthly,
        'annual': {
            'total_demand_mwh': total_demand,
            'green_delivered_mwh': green_total,
            'gas_delivered_mwh': gas_total,
            'solar_generated_mwh': monthly['solar_gen'].sum(),
            'solar_surplus_mwh': monthly['solar_surplus'].sum(),
        },
        'green_pct': green_total / total_demand,
        'gas_pct': gas_total / total_demand,
    }
