"""
D13 audit fixture — frozen inputs from `Off-Grid Solution v8.xlsm`.

Decoupled from the workbook so the audit target is reproducible without
loading Excel. Values dumped via `src/excel_reader.py` on 2026-05-09.

Configuration (per spec D13):
  82 MWp DC / 58.4 MW grid / £170 PPA / 250 MWh BESS /
  25 MW gas / 25 MW load / Burton Leonard 58 MW AC profile.

Excel cell sources annotated next to each value. When a hardcoded value
needs revisiting, regenerate by running:
    python -m src.excel_reader   (or use read_model_params() directly)
"""

from datetime import date
from pathlib import Path

import numpy as np

from src.dispatch_energy import compute_monthly_energy
from src.project_irr import PirrInputs


# Solar profile path (D20: canonical Burton Leonard files)
D13_SOLAR_PROFILE = Path("Inputs/Burton_Leonard_82MWp_DC_58MW_AC.csv")
LARGE_SOLAR_PROFILE = Path("Inputs/Burton_Leonard_115MWp_DC_82MW_AC.csv")


# Excel merchant curve — ACTUAL evaluated monthly prices from `Solar&BESS
# Operation` r66.
#
# Background: Op r66 uses `LOOKUP(date, 'Curves and D&T'!J29:TZ29,
# 'Curves and D&T'!J30:TZ30)`. Curves r29-30 has 6 columns per year (multiple
# scenarios). A naive "first price per year" extract from r30 cherry-picks
# high-scenario values and over-states by 30-60%. The correct values come
# from extracting the LOOKUP results directly per month.
#
# Per A30 discovery (2026-05-14): Excel's curve is QUARTERLY (3 months at the
# same value, 4 distinct prices per year) with Q1 winter peak + Q2 spring
# trough. Solar generation concentrates in Q2-Q3 (low priced quarters), so
# a yearly arithmetic average OVER-states realised merchant revenue by ~7%
# over post-PPA. The yearly dict below is retained for legacy fallback; the
# monthly dict (used preferentially when present) carries the correct curve.
D13_MERCHANT_PRICES = {
    2027: 62.18, 2028: 65.53, 2029: 69.39, 2030: 74.19, 2031: 72.71,
    2032: 69.56, 2033: 69.26, 2034: 70.22, 2035: 73.83, 2036: 77.23,
    2037: 79.91, 2038: 80.91, 2039: 82.58, 2040: 79.10, 2041: 80.43,
    2042: 80.31, 2043: 83.28, 2044: 85.92, 2045: 87.42, 2046: 87.26,
    2047: 89.21, 2048: 89.19, 2049: 92.76, 2050: 92.95, 2051: 96.73,
    2052: 97.27, 2053: 99.56, 2054: 101.15, 2055: 103.96, 2056: 106.05,
    2057: 107.49, 2058: 108.14, 2059: 107.48, 2060: 106.45, 2061: 107.59,
    2062: 109.74, 2063: 111.94, 2064: 114.17, 2065: 116.46, 2066: 118.79,
}

# Full Excel monthly merchant curve — `Solar&BESS Operation!r66` per-month
# (year, month) → price. Captures the Q1-high / Q2-low quarterly seasonality
# that drives ~7% revenue overshoot when averaged to yearly. Extracted via
# diagnostic script; see decisions log A30.
# A32 (2026-05-15): post-PPA merchant balancing rate £/MWh, by engine ops_year
# (0-indexed: ops_year 10 = first month post-PPA). Excel Op r142 carries
# monthly opex (= rate × generation); rate derived by dividing r142 by Op r52
# (Monthly net generation - PV). Time-varying curve from `Baringa and Aurora`
# per the cell-note at `Solar&BESS Inputs!F283`. CfD-period rate (Op r141)
# is flat at £2.75/MWh — captured via the scalar `opex_balancing_cfd`.
D13_BALANCING_MERCHANT_BY_OPS_YEAR = {
    10: 1.3496, 11: 1.4107, 12: 1.4798, 13: 1.5433, 14: 1.5946,
    15: 1.6490, 16: 1.7197, 17: 1.7824, 18: 1.8505, 19: 1.9431,
    20: 2.0281, 21: 2.1374, 22: 2.2336, 23: 2.3140, 24: 2.3736,
    25: 2.4133, 26: 2.4716, 27: 2.5189, 28: 2.5610, 29: 2.5910,
    30: 2.5931, 31: 2.5854, 32: 2.5877, 33: 2.6212, 34: 2.6736,
}


D13_MERCHANT_PRICES_MONTHLY = {
    (2027, 7): 59.0593, (2027, 8): 59.0593, (2027, 9): 59.0593, (2027, 10): 65.3077, (2027, 11): 65.3077, (2027, 12): 65.3077,
    (2028, 1): 77.4835, (2028, 2): 77.4835, (2028, 3): 77.4835, (2028, 4): 54.6514, (2028, 5): 54.6514, (2028, 6): 54.6514, (2028, 7): 60.2819, (2028, 8): 60.2819, (2028, 9): 60.2819, (2028, 10): 69.703, (2028, 11): 69.703, (2028, 12): 69.703,
    (2029, 1): 83.7941, (2029, 2): 83.7941, (2029, 3): 83.7941, (2029, 4): 57.4067, (2029, 5): 57.4067, (2029, 6): 57.4067, (2029, 7): 63.4751, (2029, 8): 63.4751, (2029, 9): 63.4751, (2029, 10): 72.8955, (2029, 11): 72.8955, (2029, 12): 72.8955,
    (2030, 1): 90.0864, (2030, 2): 90.0864, (2030, 3): 90.0864, (2030, 4): 62.4008, (2030, 5): 62.4008, (2030, 6): 62.4008, (2030, 7): 68.3249, (2030, 8): 68.3249, (2030, 9): 68.3249, (2030, 10): 75.9283, (2030, 11): 75.9283, (2030, 12): 75.9283,
    (2031, 1): 91.7475, (2031, 2): 91.7475, (2031, 3): 91.7475, (2031, 4): 59.0969, (2031, 5): 59.0969, (2031, 6): 59.0969, (2031, 7): 66.3316, (2031, 8): 66.3316, (2031, 9): 66.3316, (2031, 10): 73.6547, (2031, 11): 73.6547, (2031, 12): 73.6547,
    (2032, 1): 89.828, (2032, 2): 89.828, (2032, 3): 89.828, (2032, 4): 55.5533, (2032, 5): 55.5533, (2032, 6): 55.5533, (2032, 7): 63.9778, (2032, 8): 63.9778, (2032, 9): 63.9778, (2032, 10): 68.8662, (2032, 11): 68.8662, (2032, 12): 68.8662,
    (2033, 1): 90.3505, (2033, 2): 90.3505, (2033, 3): 90.3505, (2033, 4): 54.3674, (2033, 5): 54.3674, (2033, 6): 54.3674, (2033, 7): 64.2924, (2033, 8): 64.2924, (2033, 9): 64.2924, (2033, 10): 68.0378, (2033, 11): 68.0378, (2033, 12): 68.0378,
    (2034, 1): 93.5069, (2034, 2): 93.5069, (2034, 3): 93.5069, (2034, 4): 53.4171, (2034, 5): 53.4171, (2034, 6): 53.4171, (2034, 7): 65.7401, (2034, 8): 65.7401, (2034, 9): 65.7401, (2034, 10): 68.2228, (2034, 11): 68.2228, (2034, 12): 68.2228,
    (2035, 1): 98.081, (2035, 2): 98.081, (2035, 3): 98.081, (2035, 4): 57.4715, (2035, 5): 57.4715, (2035, 6): 57.4715, (2035, 7): 68.7625, (2035, 8): 68.7625, (2035, 9): 68.7625, (2035, 10): 70.997, (2035, 11): 70.997, (2035, 12): 70.997,
    (2036, 1): 104.3026, (2036, 2): 104.3026, (2036, 3): 104.3026, (2036, 4): 58.0672, (2036, 5): 58.0672, (2036, 6): 58.0672, (2036, 7): 71.8675, (2036, 8): 71.8675, (2036, 9): 71.8675, (2036, 10): 74.7019, (2036, 11): 74.7019, (2036, 12): 74.7019,
    (2037, 1): 109.0422, (2037, 2): 109.0422, (2037, 3): 109.0422, (2037, 4): 60.3262, (2037, 5): 60.3262, (2037, 6): 60.3262, (2037, 7): 74.4492, (2037, 8): 74.4492, (2037, 9): 74.4492, (2037, 10): 75.8142, (2037, 11): 75.8142, (2037, 12): 75.8142,
    (2038, 1): 110.9358, (2038, 2): 110.9358, (2038, 3): 110.9358, (2038, 4): 60.8358, (2038, 5): 60.8358, (2038, 6): 60.8358, (2038, 7): 74.946, (2038, 8): 74.946, (2038, 9): 74.946, (2038, 10): 76.9169, (2038, 11): 76.9169, (2038, 12): 76.9169,
    (2039, 1): 114.3762, (2039, 2): 114.3762, (2039, 3): 114.3762, (2039, 4): 61.0125, (2039, 5): 61.0125, (2039, 6): 61.0125, (2039, 7): 75.7591, (2039, 8): 75.7591, (2039, 9): 75.7591, (2039, 10): 79.1727, (2039, 11): 79.1727, (2039, 12): 79.1727,
    (2040, 1): 111.6062, (2040, 2): 111.6062, (2040, 3): 111.6062, (2040, 4): 56.3761, (2040, 5): 56.3761, (2040, 6): 56.3761, (2040, 7): 72.2371, (2040, 8): 72.2371, (2040, 9): 72.2371, (2040, 10): 76.1644, (2040, 11): 76.1644, (2040, 12): 76.1644,
    (2041, 1): 117.5664, (2041, 2): 117.5664, (2041, 3): 117.5664, (2041, 4): 55.7576, (2041, 5): 55.7576, (2041, 6): 55.7576, (2041, 7): 72.3701, (2041, 8): 72.3701, (2041, 9): 72.3701, (2041, 10): 76.0062, (2041, 11): 76.0062, (2041, 12): 76.0062,
    (2042, 1): 117.5581, (2042, 2): 117.5581, (2042, 3): 117.5581, (2042, 4): 54.8924, (2042, 5): 54.8924, (2042, 6): 54.8924, (2042, 7): 71.9841, (2042, 8): 71.9841, (2042, 9): 71.9841, (2042, 10): 76.8217, (2042, 11): 76.8217, (2042, 12): 76.8217,
    (2043, 1): 125.2632, (2043, 2): 125.2632, (2043, 3): 125.2632, (2043, 4): 56.0758, (2043, 5): 56.0758, (2043, 6): 56.0758, (2043, 7): 73.1522, (2043, 8): 73.1522, (2043, 9): 73.1522, (2043, 10): 78.6138, (2043, 11): 78.6138, (2043, 12): 78.6138,
    (2044, 1): 131.7266, (2044, 2): 131.7266, (2044, 3): 131.7266, (2044, 4): 57.178, (2044, 5): 57.178, (2044, 6): 57.178, (2044, 7): 73.9867, (2044, 8): 73.9867, (2044, 9): 73.9867, (2044, 10): 80.776, (2044, 11): 80.776, (2044, 12): 80.776,
    (2045, 1): 135.2217, (2045, 2): 135.2217, (2045, 3): 135.2217, (2045, 4): 55.4912, (2045, 5): 55.4912, (2045, 6): 55.4912, (2045, 7): 74.5137, (2045, 8): 74.5137, (2045, 9): 74.5137, (2045, 10): 84.4534, (2045, 11): 84.4534, (2045, 12): 84.4534,
    (2046, 1): 137.9664, (2046, 2): 137.9664, (2046, 3): 137.9664, (2046, 4): 54.9327, (2046, 5): 54.9327, (2046, 6): 54.9327, (2046, 7): 72.143, (2046, 8): 72.143, (2046, 9): 72.143, (2046, 10): 83.9924, (2046, 11): 83.9924, (2046, 12): 83.9924,
    (2047, 1): 142.6422, (2047, 2): 142.6422, (2047, 3): 142.6422, (2047, 4): 55.2654, (2047, 5): 55.2654, (2047, 6): 55.2654, (2047, 7): 72.7303, (2047, 8): 72.7303, (2047, 9): 72.7303, (2047, 10): 86.2003, (2047, 11): 86.2003, (2047, 12): 86.2003,
    (2048, 1): 142.7074, (2048, 2): 142.7074, (2048, 3): 142.7074, (2048, 4): 54.9244, (2048, 5): 54.9244, (2048, 6): 54.9244, (2048, 7): 72.3853, (2048, 8): 72.3853, (2048, 9): 72.3853, (2048, 10): 86.7441, (2048, 11): 86.7441, (2048, 12): 86.7441,
    (2049, 1): 151.2051, (2049, 2): 151.2051, (2049, 3): 151.2051, (2049, 4): 57.8262, (2049, 5): 57.8262, (2049, 6): 57.8262, (2049, 7): 72.8914, (2049, 8): 72.8914, (2049, 9): 72.8914, (2049, 10): 89.1344, (2049, 11): 89.1344, (2049, 12): 89.1344,
    (2050, 1): 152.9343, (2050, 2): 152.9343, (2050, 3): 152.9343, (2050, 4): 57.1948, (2050, 5): 57.1948, (2050, 6): 57.1948, (2050, 7): 71.3269, (2050, 8): 71.3269, (2050, 9): 71.3269, (2050, 10): 90.3496, (2050, 11): 90.3496, (2050, 12): 90.3496,
    (2051, 1): 159.459, (2051, 2): 159.459, (2051, 3): 159.459, (2051, 4): 58.4248, (2051, 5): 58.4248, (2051, 6): 58.4248, (2051, 7): 73.7659, (2051, 8): 73.7659, (2051, 9): 73.7659, (2051, 10): 95.2627, (2051, 11): 95.2627, (2051, 12): 95.2627,
    (2052, 1): 160.5916, (2052, 2): 160.5916, (2052, 3): 160.5916, (2052, 4): 58.6052, (2052, 5): 58.6052, (2052, 6): 58.6052, (2052, 7): 73.7523, (2052, 8): 73.7523, (2052, 9): 73.7523, (2052, 10): 96.112, (2052, 11): 96.112, (2052, 12): 96.112,
    (2053, 1): 164.0513, (2053, 2): 164.0513, (2053, 3): 164.0513, (2053, 4): 59.2873, (2053, 5): 59.2873, (2053, 6): 59.2873, (2053, 7): 75.0002, (2053, 8): 75.0002, (2053, 9): 75.0002, (2053, 10): 99.9013, (2053, 11): 99.9013, (2053, 12): 99.9013,
    (2054, 1): 167.7956, (2054, 2): 167.7956, (2054, 3): 167.7956, (2054, 4): 61.6371, (2054, 5): 61.6371, (2054, 6): 61.6371, (2054, 7): 75.6173, (2054, 8): 75.6173, (2054, 9): 75.6173, (2054, 10): 99.5657, (2054, 11): 99.5657, (2054, 12): 99.5657,
    (2055, 1): 173.1969, (2055, 2): 173.1969, (2055, 3): 173.1969, (2055, 4): 64.7808, (2055, 5): 64.7808, (2055, 6): 64.7808, (2055, 7): 76.3203, (2055, 8): 76.3203, (2055, 9): 76.3203, (2055, 10): 101.5434, (2055, 11): 101.5434, (2055, 12): 101.5434,
    (2056, 1): 174.8351, (2056, 2): 174.8351, (2056, 3): 174.8351, (2056, 4): 64.7547, (2056, 5): 64.7547, (2056, 6): 64.7547, (2056, 7): 77.7278, (2056, 8): 77.7278, (2056, 9): 77.7278, (2056, 10): 106.8763, (2056, 11): 106.8763, (2056, 12): 106.8763,
    (2057, 1): 177.8431, (2057, 2): 177.8431, (2057, 3): 177.8431, (2057, 4): 66.5043, (2057, 5): 66.5043, (2057, 6): 66.5043, (2057, 7): 76.8511, (2057, 8): 76.8511, (2057, 9): 76.8511, (2057, 10): 108.7727, (2057, 11): 108.7727, (2057, 12): 108.7727,
    (2058, 1): 179.5994, (2058, 2): 179.5994, (2058, 3): 179.5994, (2058, 4): 66.3181, (2058, 5): 66.3181, (2058, 6): 66.3181, (2058, 7): 77.9497, (2058, 8): 77.9497, (2058, 9): 77.9497, (2058, 10): 108.7075, (2058, 11): 108.7075, (2058, 12): 108.7075,
    (2059, 1): 174.6715, (2059, 2): 174.6715, (2059, 3): 174.6715, (2059, 4): 66.0696, (2059, 5): 66.0696, (2059, 6): 66.0696, (2059, 7): 79.1455, (2059, 8): 79.1455, (2059, 9): 79.1455, (2059, 10): 110.0484, (2059, 11): 110.0484, (2059, 12): 110.0484,
    (2060, 1): 174.9151, (2060, 2): 174.9151, (2060, 3): 174.9151, (2060, 4): 66.2875, (2060, 5): 66.2875, (2060, 6): 66.2875, (2060, 7): 77.4612, (2060, 8): 77.4612, (2060, 9): 77.4612, (2060, 10): 107.1496, (2060, 11): 107.1496, (2060, 12): 107.1496,
    (2061, 1): 172.8417, (2061, 2): 172.8417, (2061, 3): 172.8417, (2061, 4): 71.6513, (2061, 5): 71.6513, (2061, 6): 71.6513, (2061, 7): 76.6663, (2061, 8): 76.6663, (2061, 9): 76.6663, (2061, 10): 109.1947, (2061, 11): 109.1947, (2061, 12): 109.1947,
    (2062, 1): 176.2985, (2062, 2): 176.2985, (2062, 3): 176.2985, (2062, 4): 73.0843, (2062, 5): 73.0843, (2062, 6): 73.0843, (2062, 7): 78.1996, (2062, 8): 78.1996, (2062, 9): 78.1996, (2062, 10): 111.3786, (2062, 11): 111.3786, (2062, 12): 111.3786,
    (2063, 1): 179.8245, (2063, 2): 179.8245, (2063, 3): 179.8245, (2063, 4): 74.546, (2063, 5): 74.546, (2063, 6): 74.546, (2063, 7): 79.7636, (2063, 8): 79.7636, (2063, 9): 79.7636, (2063, 10): 113.6061, (2063, 11): 113.6061, (2063, 12): 113.6061,
    (2064, 1): 183.4209, (2064, 2): 183.4209, (2064, 3): 183.4209, (2064, 4): 76.0369, (2064, 5): 76.0369, (2064, 6): 76.0369, (2064, 7): 81.3589, (2064, 8): 81.3589, (2064, 9): 81.3589, (2064, 10): 115.8783, (2064, 11): 115.8783, (2064, 12): 115.8783,
    (2065, 1): 187.0894, (2065, 2): 187.0894, (2065, 3): 187.0894, (2065, 4): 77.5576, (2065, 5): 77.5576, (2065, 6): 77.5576, (2065, 7): 82.9861, (2065, 8): 82.9861, (2065, 9): 82.9861, (2065, 10): 118.1958, (2065, 11): 118.1958, (2065, 12): 118.1958,
    (2066, 1): 190.8312, (2066, 2): 190.8312, (2066, 3): 190.8312, (2066, 4): 79.1088, (2066, 5): 79.1088, (2066, 6): 79.1088, (2066, 7): 84.6458, (2066, 8): 84.6458, (2066, 9): 84.6458, (2066, 10): 120.5597, (2066, 11): 120.5597, (2066, 12): 120.5597,
}


def d13_inputs(
    solar_dc_mwp: float = 82.0,
    grid_limit_mw: float = 58.4,
    ppa_tariff: float = 170.0,
    solar_profile: Path | None = None,
) -> PirrInputs:
    """Build PirrInputs for the SME reference matrix.

    Defaults to D13 (82 MWp / £170 / 58 MW grid profile). Override
    `solar_dc_mwp` / `ppa_tariff` / `solar_profile` to switch to one of the
    other 3 SME matrix rows.

    Year-1 monthly aggregates come from running the existing dispatch helper
    on the canonical Burton Leonard profile selected for the case.
    """
    if solar_profile is None:
        solar_profile = D13_SOLAR_PROFILE if solar_dc_mwp <= 100 else LARGE_SOLAR_PROFILE

    energy = compute_monthly_energy(
        solar_profile_path=solar_profile,
        load_mw=25.0,
        bess_mwh=250.0,
        bess_mw=62.5,
    )
    monthly = energy["monthly"]

    return PirrInputs(
        # --- Timeline (Solar&BESS Inputs F19/F20/F23/F24) ---
        construction_start=date(2026, 10, 1),
        construction_months=9,
        cod_date=date(2027, 7, 1),
        project_life_years=35,

        # --- Capacity ---
        solar_dc_mwp=solar_dc_mwp,   # F31 (case-parameterised)
        grid_limit_mw=grid_limit_mw, # case-parameterised
        bess_mwh=250.0,              # F116 × F117
        bess_mw=62.5,                # F116
        bess_operating_life_years=10,  # F112
        gas_mw=25.0,                 # Inputs-Gas I14 (effective)
        gas_capacity_mw_gross=28.32, # Inputs-Gas I11 (gross installed, for fixed opex)
        load_mw=25.0,                # Overall Inputs E7

        # --- Solar yield ---
        yield_p50=967.0,             # F34
        yield_p75=936.0,
        yield_p90=895.0,
        generation_selection="P50",  # F66
        seasonality=[
            0.024625, 0.048049, 0.090481, 0.119068, 0.135136, 0.135006,
            0.130144, 0.119599, 0.090190, 0.059662, 0.029606, 0.018434,
        ],
        solar_degradation_pct=0.003,  # F40

        # --- Year-1 monthly aggregates from dispatch ---
        monthly_solar_bess_to_dc=monthly["solar_bess_to_dc"],
        monthly_solar_surplus=monthly["solar_surplus"],
        monthly_gas_mwh=monthly["gas_energy"],

        # --- PPA (Overall Inputs E13/E14) ---
        ppa_tariff_gbp_mwh=ppa_tariff,  # case-parameterised
        ppa_tenor_years=10,
        ppa_indexation="NIL",
        ppa_escalation_rate=0.0,

        # --- Solar merchant ---
        merchant_prices=D13_MERCHANT_PRICES,
        merchant_prices_monthly=D13_MERCHANT_PRICES_MONTHLY,  # A30: monthly takes precedence
        merchant_price_default=0.0,    # Excel uses 0 for pre-curve years; no fallback

        # --- REGOs (F79-82) ---
        rego_switch=1,
        rego_price=2.5,
        rego_indexation="NIL",
        rego_tenor_years=35,

        # --- 11kV embedded benefits (F94-105, F87-89) ---
        emb_switch=1,
        emb_benefits_monthly=[
            5.376, 6.271, 8.308, 8.191, 9.399, 10.384,
            10.782, 10.045, 7.541, 5.951, 5.370, 5.370,
        ],
        emb_indexation="CPI",
        emb_tenor_years=15,

        # --- CM T-1 / CM T-4 / BESS floor: per Excel current snapshot, all
        # BESS revenue evaluates to zero (BESS sheet rows 93-96 → FS r20-23
        # all zero). Likely conditional on a switch the spec hasn't captured;
        # for D13 audit parity we mirror Excel's zero revenue. ---
        cm_t1_value=0.0,
        cm_t1_derating=0.2715,
        cm_t1_tenor_years=3,
        cm_t1_start=date(2026, 10, 1),
        cm_t1_indexation="CPI",
        cm_t4_value=0.0,
        cm_t4_derating=0.2094,
        cm_t4_tenor_years=15,
        cm_t4_start=date(2029, 10, 1),
        cm_t4_indexation="CPI",
        bess_floor_switch=0,
        bess_floor_price=40.0,
        bess_floor_rev_share=0.09,
        bess_floor_tenor_years=10,
        bess_floor_indexation="NIL",

        # --- BESS merchant (F124) — OFF in PPA mode for D13 ---
        bess_merchant_switch=0,

        # --- Gas PPA (Inputs-Gas I19/I20/I16) ---
        # Gas PPA tariff is LINKED to solar PPA in Excel:
        #   Inputs-Gas!I19 formula = 'Overall Inputs'!E13 (= solar PPA tariff)
        # So when solar PPA drops £170 → £160, gas drops too. Mirror the
        # Excel link by setting gas_ppa_tariff = ppa_tariff. (A31, 2026-05-14)
        gas_ppa_tariff=ppa_tariff,
        gas_ppa_tenor_years=10,
        gas_ppa_escalation=0.0,

        # --- Gas merchant (Overall Inputs E17/E18; gas plant life I7) ---
        gas_merchant_tariff=200.0,
        gas_merchant_hours_per_day=9.0,
        gas_merchant_escalation=0.0,        # Excel: gas merchant flat £200
        gas_operations_years=20,            # Inputs-Gas I7

        # --- Solar OPEX (F215-225, F282) ---
        opex_pv_om=5.48,
        opex_grid_conn=0.003,
        opex_greenkeeping=1.5,
        opex_community=0.5,
        opex_real_estate_tax=1.222,
        opex_non_tech_am=1.3,
        opex_subsidy_loss=0.0,
        opex_insurance=2.021,
        opex_corrective_maint=3.2,    # retained for back-compat; engine no longer uses
        opex_tech_am=0.3,
        opex_solar_fixed_indexation="CPI",
        opex_balancing_cfd=2.75,
        # A32: CfD balancing is flat in Excel (F287 active branch = NIL).
        # Merchant balancing follows the time-varying curve below.
        opex_solar_var_indexation="NIL",
        merchant_balancing_rate_by_ops_year=D13_BALANCING_MERCHANT_BY_OPS_YEAR,
        # FS r39 lifetime £525k → level base ≈ £9.83k/yr (CPI Σ=53.4 over 35yr)
        opex_corrective_maint_annual_gbpk=9.83,

        # --- BESS OPEX (F308-311) + step costs from BESS sheet ---
        bess_opex_om=7.063,
        bess_opex_import=0.0,
        bess_opex_rates=3.276,
        bess_opex_lease=1.489,
        bess_opex_indexation="BESS Indexation",
        # FS r51 £3,569k, r52 £395k, r53 £3,125k. BESS Indexation Σ ≈ 10.95 over 10 yr.
        bess_opex_ltsa_annual_gbpk=326.0,
        bess_opex_pcs_warranty_annual_gbpk=36.1,
        bess_opex_augmentation_annual_gbpk=285.5,

        # --- Gas OPEX (Inputs-Gas I32-49, I54) ---
        gas_opex_environmental=10.166,
        gas_opex_om_contract=9.378,
        gas_opex_site_maintenance=1.801,
        gas_opex_other_variable=2.022,
        gas_opex_site_lease=3.900,
        gas_opex_fixed_operating=14.232,
        gas_opex_professional_fees=4.584,
        gas_opex_property_tax=4.0,
        gas_opex_telecom=0.3,
        gas_opex_audit_fees=0.837,
        gas_opex_insurance=3.54,
        gas_opex_legal=0.872,
        gas_opex_inflation=0.020,
        gas_opex_reactive_per_mwh=0.0015,    # Cash Flows-Gas r48 / Inputs-Gas I38
        gas_opex_major_maint_annual=685.0,   # Cash Flows-Gas r44 (£16,650k / Σ inflation factors)
        gas_fuel_price_gbp_mwh=32.51,
        gas_net_efficiency=0.385,
        gas_co2_kg_per_mwh=185.0,
        gas_ukets_cost_gbp_per_kg=0.07,
        gas_fixed_cost_gbp_day=1087.54,
        gas_starts_per_day=4.0,
        gas_start_fuel=0.1,
        gas_fuel_escalation_from_yr4=0.01,

        # --- Land (F172-181) ---
        fixed_lease_switch=1,
        fixed_lease_acres=205.0,
        fixed_lease_price=700.0,
        fixed_lease_indexation="Land Lease RPI",
        rev_dep_lease_switch=1,
        rev_share_yr1_10=0.05,
        rev_share_yr11_35=0.05,

        # --- CAPEX (F335-355, F363) ---
        capex_acquisition=0.0,
        capex_development=2.949,
        capex_discharge=0.983,
        capex_dd=3.775,
        capex_epc=400.0,
        capex_grid=57.858,
        capex_sdlt=0.753,
        capex_land_legal=3.686,
        capex_other_finance=5.0,
        capex_other_legal=0.0,
        capex_land_purchase=0.0,
        capex_ampyr_tech=3.236,
        capex_success_fee=0.0,
        capex_community=0.0,
        capex_landowner_fees=11.597,
        capex_insurance=6.329,
        capex_land_lease_constr=2.457,
        capex_asset_adoption=0.0,
        capex_others=0.0,
        capex_misc=4.916,
        # D5: BESS scales with BESS MW. F349 = 600 GBP/kW_BESS.
        capex_bess_gbp_per_kw_bess=600.0,
        # Inputs-Gas I58
        gas_capex_total_gbpk=21839.4,
        capex_contingency_pct=0.01,
        # IDC / Financing / DSRA — D3 says include. Excel populates these from
        # the debt convergence macro; for the v1 audit they remain 0 here and
        # the engine will under-shoot capex by their amount. To be filled in
        # once the SME-confirmed values are extracted from `Construction!`
        # rows 110-112. See decisions log A16 follow-up.
        capex_idc_gbpk=0.0,
        capex_financing_fees_gbpk=0.0,
        capex_dsra_gbpk=0.0,

        # --- Tax (Curves and D&T E105/E108) ---
        corp_tax_rate=0.25,
        taxation_month=12,

        # --- Working capital (F327/F328) ---
        debtor_days=30,
        creditor_days=30,

        # --- Debt for tax shield (D2 / A15) ---
        gearing=0.80,
        interest_rate=0.04,
        debt_tenor_years=19,
        grace_period_months=36,

        # --- SHL (Solar&BESS Inputs F553 + F556) ---
        shl_switch=1,
        shl_pct_of_unfunded=0.99,   # F556
        shl_rate=0.15,              # F553 (15% p.a.)
        shl_cir_threshold_gbpk=2000.0,
        shl_cir_ebitda_cap_pct=0.30,

        # --- Depreciation (D&T r163-165: Applied=RB at 2/36 p.a.) ---
        depreciation_method="RB",
        depreciation_rate=2.0 / 36.0,   # 5.555%/yr double-declining

        # --- Discount (F590) ---
        discount_rate=0.065,
    )
