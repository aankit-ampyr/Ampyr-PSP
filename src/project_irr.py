"""
Project IRR Engine — clean rewrite per Financial_Assumptions_Spec.md.

Replaces the parked `financial_model_v0` + `consolidated_model_v0` after
the A9 audit confirmed −44 bps drift at the D13 target and a Guardrail-5
calibration constant in the consolidated layer.

Scope (v1, D13-first):
  - Ungeared FCFF IRR (XIRR) — single config
  - Unified Solar+BESS+Gas FCFF (no separate consolidation step)
  - Monthly granularity, 420 periods (35 yr × 12)
  - Per-line-item indexation (5 named cases + NIL)
  - Minimal debt schedule for tax shield (D2)
  - All ~10 revenue streams from spec §5.2

All calculations in GBP thousands (GBPk). Currency unit is consistent
throughout — multiply by 1000 only at the GBP/MWh × MWh boundary.

Excel source workbook: `Financial Model/Off-Grid Solution v8.xlsm`.
Spec: `docs/Financial_Assumptions_Spec.md`.
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import numpy as np


# =============================================================================
# INDEXATION
# =============================================================================
# Spec D11: per-line-item indexation. Excel has 14 cases; the 5 below cover
# every revenue/opex line in the D13 fixture. NIL = no escalation.

DEFAULT_ESCALATION_RATES = {
    "NIL": 0.0,
    # A39 (2026-05-16): CPI 2.5%→2.0% per Excel `Curves and D&T!r10` steady-state
    # rate from 2027 onward. The curve is "Variable" per Excel but stabilises at
    # 2.0% from ops year 0 (2027) onward (earlier years: 2022=3.1%, 2023=2.5%,
    # 2024-25=2.2%, 2026=2.1% — pre-COD inflation handled via base values).
    "CPI": 0.020,
    "RPI": 0.030,
    "PPA Indexation": 0.0,    # PPA indexed at tariff_escalation, set on input
    "BESS Indexation": 0.020,
    "Land Lease RPI": 0.030,
    "Flat 0%": 0.0,
    # "O&M - Year 3 Onwards" is non-geometric — handled specially in
    # _esc_factor: factor = 1.0 for ops_year < 3, then 1.02^(ops_year-2)
    # from year 3 onwards. Excel `Solar&BESS Inputs!r267` = PV O&M escalation.
    "O&M - Year 3 Onwards": 0.020,
}


# Excel-evaluated merchant curve from `Solar&BESS Operation!r66`, averaged per
# year. This is the Burton Leonard locked default — the curve `Solar&BESS
# Operation!r66 = LOOKUP(date, 'Curves and D&T'!J29:TZ29, J30:TZ30)` evaluates
# to (after correcting for the multi-scenario column structure; see decisions
# log A22-era commit a001fd3). Without these defaults, the wizard-state
# adapter falls back to a flat fallback price, which under/over-states
# merchant revenue across the 2027-2066 lifetime.
#
# Tests/fixtures/d13_inputs.py keeps its own copy (so the fixture remains a
# frozen snapshot independent of engine defaults) — both should stay in sync
# until the merchant curve is plumbed through wizard state proper.
_DEFAULT_MERCHANT_PRICES_NOMINAL = {
    2027: 62.18, 2028: 65.53, 2029: 69.39, 2030: 74.19, 2031: 72.71,
    2032: 69.56, 2033: 69.26, 2034: 70.22, 2035: 73.83, 2036: 77.23,
    2037: 79.91, 2038: 80.91, 2039: 82.58, 2040: 79.10, 2041: 80.43,
    2042: 80.31, 2043: 83.28, 2044: 85.92, 2045: 87.42, 2046: 87.26,
    2047: 89.21, 2048: 89.19, 2049: 92.76, 2050: 92.95, 2051: 96.73,
    2052: 97.27, 2053: 99.56, 2054: 101.15, 2055: 103.96, 2056: 106.05,
    2057: 107.49, 2058: 108.14, 2059: 107.48, 2060: 106.45, 2061: 107.59,
    2062: 109.74, 2063: 111.94, 2064: 114.17, 2065: 116.46, 2066: 118.79,
}


# A30 (2026-05-14): post-PPA monthly merchant price curve £/MWh. Excel
# `Solar&BESS Operation!r66` is quarterly seasonal (Q1 winter peak, Q2 spring
# trough). Yearly average over-states realised merchant revenue by ~7% (solar
# concentrates in Q2-Q3 low-price quarters). Burton-Leonard-locked default —
# wizard state can override; non-D13 sites need their own monthly curve.
# Kept in sync with `tests/fixtures/d13_inputs.D13_MERCHANT_PRICES_MONTHLY`.
_DEFAULT_MERCHANT_PRICES_MONTHLY = {
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


# A35 (2026-05-15): per-month capex phasing curves. Excel deploys capex
# non-uniformly across an 18-month window (Jan 2026-Jun 2027) — 9 months of
# development phase (mostly gas, pre-construction) plus 9 months of
# S-curve construction. Engine had been using uniform 9-month distribution
# Oct 2026-Jun 2027 (no development phase). Extracted from Excel
# `Consol Cash Flows!r5` (Solar+BESS FCFF) and `r6` (Gas FCFF) by summing
# negative pre-COD values, divided by per-stream construction total.
#
# Burton-Leonard-locked defaults. Non-D13 sites would need their own curves
# (gap analysis §3.12). Empty dict in PirrInputs → falls back to uniform
# 9-month distribution within construction window.

# A36 (2026-05-15): Gas major equipment maintenance discrete-event schedule.
# Excel `Cash Flows-Gas!r44` shows 8 lumpy events concentrated in years 1, 3,
# 4, 6, 7, 9, 12, 15. Year 15 alone is £7,928k (47% of lifetime). Engine had
# been using level-annual £685/yr × 20yr × 2% inflation. Totals match
# (£16,650k) but timing differs dramatically — drove the 2042 FCFF anomaly
# identified in the year-by-year diagnostic.
#
# Values are NOMINAL (already inflated). Engine applies directly without
# additional escalation when schedule is populated.
_DEFAULT_GAS_MAJOR_MAINT_SCHEDULE = {
    1:  283.16,    # 2029 (calendar via dates near year-end)
    3:  2_265.26,  # 2030
    4:  679.58,    # 2032
    6:  2_265.26,  # 2033
    7:  283.16,    # 2035
    9:  2_661.68,  # 2036
    12: 283.16,    # 2039
    15: 7_928.42,  # 2042 — single biggest event, drives the FCFF anomaly
}


_DEFAULT_CAPEX_PHASING_SB_BY_MONTH = {
    (2026, 6): 0.018203,  (2026, 7): 0.004077,
    (2026, 9): 0.021500,  (2026, 10): 0.151948,
    (2026, 11): 0.019920, (2026, 12): 0.089909,
    (2027, 1): 0.002019,  (2027, 2): 0.181777,
    (2027, 3): 0.227198,  (2027, 4): 0.091608,
    (2027, 5): 0.070391,  (2027, 6): 0.121451,
}

_DEFAULT_CAPEX_PHASING_GAS_BY_MONTH = {
    (2026, 1): 0.334589,  (2026, 2): 0.000956,
    (2026, 3): 0.001064,  (2026, 4): 0.001035,
    (2026, 5): 0.001076,  (2026, 6): 0.128509,
    (2026, 7): 0.129281,  (2026, 8): 0.130022,
    (2026, 9): 0.003199,  (2026, 10): 0.003324,
    (2026, 11): 0.003235, (2026, 12): 0.003361,
    (2027, 1): 0.003380,  (2027, 2): 0.003071,
    (2027, 3): 0.003417,  (2027, 4): 0.082990,
    (2027, 5): 0.083577,  (2027, 6): 0.083914,
}


# A38 (2026-05-16, Phase A): per-account depreciation parameters per Excel
# `D&T!r51-r165`. Each account has its own monthly RB rate, monthly SL rate,
# and nominal life. Tax depreciation uses RB per `D&T!r146/r165 = "RB"`;
# accounting depreciation uses SL per `D&T!r69/r88 = "SL"` (engine FCFF uses
# tax dep, so SL only matters if `depreciation_method = "SLM"` is set).
#
# Capex line item → account routing per Excel `Construction!B76:B112` SUMIF
# tag (per-line "Choice" in `Curves and D&T!r71-r112`):
#   - 'long_term' (30 yr, RB 2/360 monthly): bulk capex — solar EPC, BESS,
#     grid, land, insurance, acquisition, dev, DD, etc. (rows 76-96)
#   - 'short_term' (8 yr, RB 2/96 monthly): no D13 routing
#   - 'financing'  (3 yr, RB 2/36 monthly): IDC + Financing fees (rows 111-112)
_DEPRECIATION_ACCOUNTS = {
    'long_term':  {'monthly_rb': 2.0/360.0, 'monthly_sl': 1.0/360.0, 'life_months': 360},
    'short_term': {'monthly_rb': 2.0/96.0,  'monthly_sl': 1.0/96.0,  'life_months': 96},
    'financing':  {'monthly_rb': 2.0/36.0,  'monthly_sl': 1.0/36.0,  'life_months': 36},
}


# A40 (2026-05-16): time-varying CPI curve per Excel `Curves and D&T!r10`.
# Values are calendar-year rates (not cumulative). Engine convention:
# factor(ops_year=0) = 1.0, factor(y) = factor(y-1) × (1 + cpi[cod_year + y]).
# Years not in the dict fall back to `cpi_steady_state_rate` (2.0% per Excel
# steady-state from 2030 onwards). Replaces engine's flat rate from A39.
_DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR = {
    2024: 0.000,
    2025: 0.031,
    2026: 0.025,
    2027: 0.022,
    2028: 0.022,
    2029: 0.021,
    # 2030+ falls back to 2.0% (cpi_steady_state_rate)
}


def _build_cpi_factor_lookup(curve: dict[int, float],
                              steady_state: float,
                              cod_year: int,
                              n_ops_years: int) -> list[float]:
    """Precompute `factor(ops_year)` for ops_year in [0, n_ops_years).

    Convention: `factor(0) = 1.0` (engine baseline = no escalation at COD);
    `factor(y) = factor(y-1) × (1 + curve[cod_year + y])`. Falls back to
    `steady_state` rate for calendar years not in the curve.
    """
    out = [1.0]
    for y in range(1, n_ops_years):
        cal_year = cod_year + y
        rate = curve.get(cal_year, steady_state) if curve else steady_state
        out.append(out[-1] * (1.0 + rate))
    return out


# A32 (2026-05-15): post-PPA merchant balancing rate £/MWh by engine ops_year.
# Derived from Excel Op r142 (monthly opex GBPk) / Op r52 (net gen MWh). The
# underlying source is the `Baringa and Aurora` curve referenced by `Solar&BESS
# Inputs!F283`. Burton-Leonard-locked default; non-D13 sites will need their
# own curve plumbed via wizard state.
_DEFAULT_MERCHANT_BALANCING_BY_OPS_YEAR = {
    10: 1.3496, 11: 1.4107, 12: 1.4798, 13: 1.5433, 14: 1.5946,
    15: 1.6490, 16: 1.7197, 17: 1.7824, 18: 1.8505, 19: 1.9431,
    20: 2.0281, 21: 2.1374, 22: 2.2336, 23: 2.3140, 24: 2.3736,
    25: 2.4133, 26: 2.4716, 27: 2.5189, 28: 2.5610, 29: 2.5910,
    30: 2.5931, 31: 2.5854, 32: 2.5877, 33: 2.6212, 34: 2.6736,
}


# A44 (2026-05-16, per Anchal Q1 reply): Insurance on Plant & Machinery is
# NOT a per-kWp × CPI line — it's a discrete year-by-year schedule extracted
# from Excel `Insurance` sheet + summarised in `Solar&BESS Operation!r168`.
# Lifetime £8,806.63k matches Anchal's memo. Years 1-2 carry a construction-
# tail premium (~£280-287k); year 3 drops to ~£205k as a 30% discount kicks
# in; years 5-10 alternate 0%/5% discount; year 11+ grows at 2%/yr compound
# from a £206.27k anchor (verified: 206.27 × 1.02^24 = 331.8, matches year 35
# Excel value 331.76).
#
# Index convention: ENGINE 0-INDEXED ops_year. Excel `Solar&BESS Operation!r17`
# uses 1-indexed (Excel oy=1 starts at COD month — verified by probing
# r17 transitions: oy=1 first appears at column 66 = 2027-07-01 = COD).
# So Excel oy=1 → engine ops_year=0, Excel oy=2 → engine ops_year=1, etc.
# Matches A36 `_DEFAULT_GAS_MAJOR_MAINT_SCHEDULE` convention (engine direct).
#
# Reference scaling: schedule was extracted for D13 = 82 MWp DC. For non-D13
# configs, engine scales linearly by `solar_dc_mwp / reference_mwp` per
# Anchal Q1 "rough estimate or hardcode yearly nos as per excel" — we
# combine both options: hardcode the schedule + per-MW scale to other configs.
_DEFAULT_INSURANCE_SCHEDULE_GBPK = {
    0: 281.94, 1: 287.58, 2: 205.33, 3: 209.44, 4: 202.94,
    5: 207.00, 6: 200.59, 7: 204.60, 8: 198.26, 9: 202.22,
    # engine ops_year 10+ (Excel year 11+) derived via
    #   _DEFAULT_INSURANCE_YR11_BASE × (1 + growth)^(ops_year - 10)
}
_DEFAULT_INSURANCE_YR11_BASE = 206.27   # engine ops_year 10 (= Excel year 11)
_DEFAULT_INSURANCE_YR11_GROWTH = 0.02
_DEFAULT_INSURANCE_REFERENCE_MWP = 82.0


def _esc_factor(rates: dict, case: str, ops_year: int,
                cpi_factor_lookup: list[float] | None = None) -> float:
    """Escalation factor for the start of operations year `ops_year`.

    Year 0 = 1.0, year y = (1+rate)^y. Matches Excel convention where
    indexation is applied at the start of each operating year, so the year-1
    cash flows carry no escalation.

    Special cases:
      "O&M - Year 3 Onwards" — non-geometric. Excel applies escalation only
      from operating year 3 onwards; ops_years 0-2 stay at base. PV O&M is
      the only D13 line using this case. Verified against Excel Op r117
      year-by-year totals (A34, 2026-05-15).

      "CPI" — if `cpi_factor_lookup` is provided, use the precomputed
      per-ops-year cumulative product from the variable curve in Excel
      `Curves and D&T!r10` (A40, 2026-05-16). Falls back to the flat
      `rates["CPI"]` value when not provided (backward-compatible).
    """
    if case == "O&M - Year 3 Onwards":
        if ops_year < 3:
            return 1.0
        rate = rates.get(case, 0.020)
        return (1.0 + rate) ** (ops_year - 2)
    if case == "CPI" and cpi_factor_lookup is not None:
        if 0 <= ops_year < len(cpi_factor_lookup):
            return cpi_factor_lookup[ops_year]
        # ops_year out of range: extend with steady-state rate
        return cpi_factor_lookup[-1] * \
            (1.0 + rates.get("CPI", 0.020)) ** (ops_year - (len(cpi_factor_lookup) - 1))
    return (1.0 + rates.get(case, 0.0)) ** ops_year


# =============================================================================
# INPUTS
# =============================================================================

@dataclass
class PirrInputs:
    """All inputs needed for the unified PIRR calculation.

    Defaults are set to the D13 audit configuration. Overridable from the
    frontend via wizard-state mapping (see `from_wizard_state`).
    """

    # --- Timeline ---
    construction_start: date = field(default_factory=lambda: date(2026, 10, 1))
    construction_months: int = 9
    cod_date: date = field(default_factory=lambda: date(2027, 7, 1))
    project_life_years: int = 35

    # --- Capacity (D8: solar in DC MWp, profile is AC + grid-capped) ---
    solar_dc_mwp: float = 82.0
    grid_limit_mw: float = 58.4         # implicit in profile peak; for visibility
    bess_mwh: float = 250.0
    bess_mw: float = 62.5
    bess_operating_life_years: int = 10   # BESS opex / merchant tenor (Excel F112)
    gas_mw: float = 25.0                # effective (post-availability) — used for revenue + variable opex
    gas_capacity_mw_gross: float = 28.32  # gross installed — used for fixed opex (Excel convention)
    load_mw: float = 25.0

    # --- Solar yield (for post-PPA merchant — Year-1 in-PPA energies come
    # from the dispatch monthly aggregates, not from yield) ---
    yield_p50: float = 967.0
    yield_p75: float = 936.0
    yield_p90: float = 895.0
    generation_selection: str = "P50"   # Excel selects P50 for D13
    seasonality: list = field(default_factory=lambda: [
        0.0246, 0.0480, 0.0905, 0.1191, 0.1351, 0.1350,
        0.1301, 0.1196, 0.0902, 0.0597, 0.0296, 0.0184,
    ])
    solar_degradation_pct: float = 0.003   # decimal — 0.3%/yr from year 2

    # --- Year-1 monthly energy aggregates (from dispatch — see §4.3) ---
    # Caller fills these from src.dispatch_energy.compute_monthly_energy().
    monthly_solar_bess_to_dc: np.ndarray = field(
        default_factory=lambda: np.zeros(12)
    )
    monthly_solar_surplus: np.ndarray = field(
        default_factory=lambda: np.zeros(12)
    )
    monthly_gas_mwh: np.ndarray = field(default_factory=lambda: np.zeros(12))

    # --- PPA (solar+BESS) ---
    ppa_tariff_gbp_mwh: float = 170.0
    ppa_tenor_years: int = 10
    ppa_indexation: str = "NIL"
    ppa_escalation_rate: float = 0.0    # writes into rates dict if non-zero

    # --- Solar merchant (post-PPA) ---
    # Default is the Excel-evaluated Burton Leonard curve (`Solar&BESS
    # Operation!r66`, averaged per year). Used unless overridden by an
    # explicit fixture or wizard state. See `_DEFAULT_MERCHANT_PRICES_NOMINAL`.
    merchant_prices: dict = field(
        default_factory=lambda: dict(_DEFAULT_MERCHANT_PRICES_NOMINAL)
    )
    # Out-of-curve fallback. Excel uses 0 for years outside the curve range;
    # this matches that. (Was 67.0 — pre-A24 default that the wizard-state
    # adapter accidentally locked in because it didn't pass the curve through.)
    merchant_price_default: float = 0.0
    # Optional monthly resolution — dict[(year, month), price]. When present,
    # takes precedence over the yearly `merchant_prices` dict. Excel's curve
    # is quarterly (3 months/value, 4 distinct values per year) with Q1 winter
    # peak + Q2 spring trough. Solar generates in Q2-Q3 (low) so yearly avg
    # over-states by ~7% over post-PPA — see A30. Populate this dict from
    # `Solar&BESS Operation!r66` to match Excel exactly.
    # Defaults to the Burton-Leonard monthly curve (A30 fix). Empty dict
    # would fall back to yearly arithmetic average which over-states
    # realised revenue by ~7% post-PPA.
    merchant_prices_monthly: dict = field(
        default_factory=lambda: dict(_DEFAULT_MERCHANT_PRICES_MONTHLY)
    )

    # --- REGOs ---
    rego_switch: int = 1
    rego_price: float = 2.5
    rego_indexation: str = "NIL"
    rego_tenor_years: int = 35

    # --- 11 kV embedded benefits ---
    emb_switch: int = 1
    emb_benefits_monthly: list = field(default_factory=lambda: [
        5.376, 6.271, 8.308, 8.191, 9.399, 10.384,
        10.782, 10.045, 7.541, 5.951, 5.370, 5.370,
    ])
    emb_indexation: str = "CPI"
    emb_tenor_years: int = 15

    # --- Capacity Market T-1 ---
    cm_t1_value: float = 20.0           # GBPk/MW/yr
    cm_t1_derating: float = 0.2715
    cm_t1_tenor_years: int = 3
    cm_t1_start: date = field(default_factory=lambda: date(2026, 10, 1))
    cm_t1_indexation: str = "CPI"

    # --- Capacity Market T-4 ---
    cm_t4_value: float = 60.0           # GBPk/MW/yr
    cm_t4_derating: float = 0.2094
    cm_t4_tenor_years: int = 15
    cm_t4_start: date = field(default_factory=lambda: date(2029, 10, 1))
    cm_t4_indexation: str = "CPI"

    # --- BESS floor ---
    bess_floor_switch: int = 1
    bess_floor_price: float = 40.0      # GBPk/MW/yr
    bess_floor_rev_share: float = 0.09  # underwriter share (decimal)
    bess_floor_tenor_years: int = 10
    bess_floor_indexation: str = "NIL"

    # --- BESS merchant (parked off in PPA mode for D13) ---
    bess_merchant_switch: int = 0

    # --- Gas PPA (capacity contracted to data centre) ---
    gas_ppa_tariff: float = 170.0
    gas_ppa_tenor_years: int = 10
    gas_ppa_escalation: float = 0.0

    # --- Gas merchant (REPLACES gas PPA from year 11 onward, parked-model
    # convention; gas plant only operates for `gas_operations_years`) ---
    gas_merchant_tariff: float = 200.0
    gas_merchant_hours_per_day: float = 9.0
    gas_merchant_escalation: float = 0.0      # Excel: gas merchant doesn't escalate
    gas_operations_years: int = 20            # Inputs-Gas I7 — shorter than project life

    # --- Solar OPEX (GBP/kWp/yr unless noted) ---
    opex_pv_om: float = 5.48
    opex_grid_conn: float = 0.003
    opex_greenkeeping: float = 1.5
    opex_community: float = 0.5
    opex_real_estate_tax: float = 1.222
    opex_non_tech_am: float = 1.3
    opex_subsidy_loss: float = 0.0
    # A44 (2026-05-16): legacy per-kWp Insurance field, used only when
    # `opex_insurance_schedule` is empty. Per Anchal Q1 reply
    # (memo 2026-05-16), Excel does NOT use this £/kWp × CPI mechanism for
    # Insurance — the actual line is a discrete year-by-year schedule
    # (construction premium tail years 1-2, post-construction baseline year
    # 3+ with discount alternation, 2%/yr growth from year 11+). Kept for
    # backward compatibility / non-D13 sites that haven't extracted their
    # own schedule yet.
    opex_insurance: float = 2.021
    # A44 (2026-05-16): explicit per-year Insurance schedule
    # (Solar&BESS Operation!r168 source). When populated (default), engine
    # uses schedule[ops_year] / 12 per month, scaled by
    # `solar_dc_mwp / opex_insurance_reference_mwp`. When empty {}, falls
    # back to the legacy per-kWp × CPI calc above.
    # Years 1-10: explicit values; years 11+: derived as
    #   _DEFAULT_INSURANCE_YR11_BASE * (1 + _DEFAULT_INSURANCE_YR11_GROWTH)^(y-11)
    # See decisions log A44.
    opex_insurance_schedule: dict = field(
        default_factory=lambda: dict(_DEFAULT_INSURANCE_SCHEDULE_GBPK)
    )
    opex_insurance_yr11_base_gbpk: float = _DEFAULT_INSURANCE_YR11_BASE
    opex_insurance_yr11_growth: float = _DEFAULT_INSURANCE_YR11_GROWTH
    opex_insurance_reference_mwp: float = _DEFAULT_INSURANCE_REFERENCE_MWP

    opex_corrective_maint: float = 3.2
    opex_tech_am: float = 0.3
    opex_solar_fixed_indexation: str = "CPI"
    # A34 (2026-05-15): PV O&M uses its OWN escalation case in Excel —
    # "O&M - Year 3 Onwards" (Solar&BESS Inputs!r267). The other 8 solar
    # fixed lines use the bundled `opex_solar_fixed_indexation`.
    opex_pv_om_indexation: str = "O&M - Year 3 Onwards"
    # A40 (2026-05-16): time-varying CPI curve per Excel `Curves and D&T!r10`.
    # Calendar-year keyed dict; falls back to `cpi_steady_state_rate` for
    # years not in the dict (Excel curve has explicit values 2024-2029, then
    # 2.0% from 2030 onwards). Replaces A39's flat 2.0% — variable curve
    # captures the higher early-year inflation (2.2% in 2027-28, 2.1% in 2029)
    # that the steady-state rate alone underweights.
    cpi_curve_by_calendar_year: dict = field(
        default_factory=lambda: dict(_DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR)
    )
    cpi_steady_state_rate: float = 0.020

    opex_balancing_cfd: float = 2.75    # GBP/MWh of generation, PPA period
    opex_solar_var_indexation: str = "NIL"  # Excel F287 (active branch) — flat CfD
    # Merchant-period balancing rate by ops_year (engine 0-indexed).
    # Per Excel `Solar&BESS Inputs!F283` note: "calculated differently in the
    # Baringa & Aurora tab" — the merchant rate is a time-varying £/MWh curve
    # looked up per period from `Baringa and Aurora!F` (Op r142 = rate × gen).
    # Engine: applies this rate only when ops_year >= ppa_tenor_years.
    # Defaults to the Burton-Leonard curve; wizard/fixture can override.
    # See decisions log A32 (2026-05-15).
    merchant_balancing_rate_by_ops_year: dict = field(
        default_factory=lambda: dict(_DEFAULT_MERCHANT_BALANCING_BY_OPS_YEAR)
    )

    # Corrective maintenance — Excel models as an 8-event step pattern across
    # the project life (FS r39, £525k lifetime, 8 active months). We mirror as
    # a level annual charge sized so base × Σ(CPI factors over 35 yr) = £525.
    # For 2.5% CPI over 35 yr, Σ ≈ 53.4 → base = ~£9.83k/yr.
    opex_corrective_maint_annual_gbpk: float = 9.83

    # --- BESS OPEX (GBPk/MW/yr unless noted) ---
    bess_opex_om: float = 7.063
    bess_opex_import: float = 0.0
    bess_opex_rates: float = 3.276
    bess_opex_lease: float = 1.489
    bess_opex_indexation: str = "BESS Indexation"
    # Step-function BESS opex from BESS sheet (level-annual approximations
    # sized so base × Σ(BESS Indexation factors over BESS life) = Excel total).
    # For 2% BESS Indexation over 10 yr, Σ ≈ 10.95 → base = lifetime/10.95.
    bess_opex_ltsa_annual_gbpk: float = 326.0       # FS r51 £3,569k / 10.95
    bess_opex_pcs_warranty_annual_gbpk: float = 36.1   # FS r52 £395k / 10.95
    bess_opex_augmentation_annual_gbpk: float = 285.5   # FS r53 £3,125k / 10.95

    # --- Gas OPEX (GBPk/MW/yr unless noted) ---
    gas_opex_environmental: float = 10.166      # CPS levy
    gas_opex_om_contract: float = 9.378
    gas_opex_site_maintenance: float = 1.801
    gas_opex_other_variable: float = 2.022      # GBPk/MW/yr
    gas_opex_site_lease: float = 3.900
    gas_opex_fixed_operating: float = 14.232
    gas_opex_professional_fees: float = 4.584
    gas_opex_property_tax: float = 4.0
    gas_opex_telecom: float = 0.3
    gas_opex_audit_fees: float = 0.837
    gas_opex_insurance: float = 3.54
    gas_opex_legal: float = 0.872
    gas_opex_inflation: float = 0.020   # decimal
    # Reactive maintenance — per MWh of gas output (Cash Flows-Gas row 48)
    gas_opex_reactive_per_mwh: float = 0.0015
    # Major equipment maintenance — Excel uses a step-function flag, we
    # approximate as a level base × gas inflation. Base sized so that
    # base × Σ(1.02^i for i=0..19) = £16,650k → base = £685k/yr.
    # Legacy fallback; superseded by `gas_major_maint_schedule` (A36) when
    # the latter is populated.
    gas_opex_major_maint_annual: float = 685.0
    # A36: discrete event schedule from Excel `Cash Flows-Gas!r44`.
    # dict[ops_year, GBPk nominal]. Defaults to Burton-Leonard curve;
    # spreads each yearly amount across 12 months evenly.
    gas_major_maint_schedule: dict = field(
        default_factory=lambda: dict(_DEFAULT_GAS_MAJOR_MAINT_SCHEDULE)
    )

    gas_fuel_price_gbp_mwh: float = 32.51
    gas_net_efficiency: float = 0.385
    gas_co2_kg_per_mwh: float = 185.0
    gas_ukets_cost_gbp_per_kg: float = 0.07
    gas_fixed_cost_gbp_day: float = 1087.54
    gas_starts_per_day: float = 4.0
    gas_start_fuel: float = 0.1                 # MWh fuel per start
    gas_fuel_escalation_from_yr4: float = 0.01  # decimal

    # --- Land ---
    fixed_lease_switch: int = 1
    fixed_lease_acres: float = 205.0
    fixed_lease_price: float = 700.0    # GBP/acre/yr
    fixed_lease_indexation: str = "Land Lease RPI"
    rev_dep_lease_switch: int = 1
    rev_share_yr1_10: float = 0.05
    rev_share_yr11_35: float = 0.05

    # --- CAPEX (GBP/kWp DC unless noted) ---
    # Solar items (linear with DC MWp)
    capex_acquisition: float = 0.0
    capex_development: float = 2.949
    capex_discharge: float = 0.983
    capex_dd: float = 3.775
    capex_epc: float = 400.0
    capex_grid: float = 57.858
    capex_sdlt: float = 0.753
    capex_land_legal: float = 3.686
    capex_other_finance: float = 5.0
    capex_other_legal: float = 0.0
    capex_land_purchase: float = 0.0
    capex_ampyr_tech: float = 3.236
    capex_success_fee: float = 0.0
    capex_community: float = 0.0
    capex_landowner_fees: float = 11.597
    capex_insurance: float = 6.329
    capex_land_lease_constr: float = 2.457
    capex_asset_adoption: float = 0.0
    capex_others: float = 0.0
    capex_misc: float = 4.916

    # BESS — D5: scales with BESS MW (NOT solar MWp). Excel F349 = 600 GBP/kW_BESS.
    capex_bess_gbp_per_kw_bess: float = 600.0

    # Gas (separate — total capex pre-IDC is fixture-based)
    gas_capex_total_gbpk: float = 21839.4

    # Contingency / financing
    capex_contingency_pct: float = 0.01
    capex_idc_gbpk: float = 0.0          # IDC — placeholder, populated from debt model
    capex_financing_fees_gbpk: float = 0.0
    capex_dsra_gbpk: float = 0.0

    # A35 (2026-05-15): per-month capex phasing curves. Each dict maps
    # (year, month) → fraction of that stream's total capex. Should sum to 1.0.
    # Empty dict → engine falls back to uniform 9-month distribution within
    # construction window (legacy behavior). When populated, engine extends
    # the timeline backward to cover any pre-construction-start months.
    # S+B capex includes solar + BESS (combined stream).
    #
    # A38 (2026-05-16): defaults flipped from empty to the Burton-Leonard
    # curves now that paired Phase C (dep-from-construction in
    # `_calc_depreciation` per `D&T!r68`) is in place. Pre-A38 phasing-only
    # regressed audit by ~11 bps; with Phase C the construction-period
    # depreciation generates NOL pool entries that absorb against early
    # ops-year income, flipping the sign positive.
    capex_phasing_sb: dict = field(
        default_factory=lambda: dict(_DEFAULT_CAPEX_PHASING_SB_BY_MONTH)
    )
    capex_phasing_gas: dict = field(
        default_factory=lambda: dict(_DEFAULT_CAPEX_PHASING_GAS_BY_MONTH)
    )

    # --- Tax ---
    corp_tax_rate: float = 0.25
    taxation_month: int = 12

    # --- Working Capital ---
    debtor_days: int = 30
    creditor_days: int = 30

    # --- Minimal debt schedule (D2 / A15 — for tax shield only) ---
    gearing: float = 0.80
    interest_rate: float = 0.04
    debt_tenor_years: int = 19
    grace_period_months: int = 36

    # --- Shareholder Loan (SHL) — Excel Solar&BESS Inputs F553/F556 ---
    # SHL is the equity-side debt instrument used to fund the unfunded portion
    # of capex. Excel treats SHL interest as tax-deductible (D&T r197), capped
    # by UK CIR (max(£2m, 30% × EBITDA) annually). For v1 we model SHL as a
    # simple interest-only loan over the project life; CIR cap is implemented
    # as an EBITDA-proportional ceiling (matches Excel D&T r210-r212).
    #
    # Per Solar&BESS Inputs F556: SHL = 99% × (1 − senior_gearing) × total_capex
    # Per Solar&BESS Inputs F553: SHL rate = 15% p.a.
    # Excel lifetime SHL interest (cash, r109) = £189.5k; tax-deductible (r197,
    # post-CIR cap) = £96.6k. Without modelling distributable-cash gating,
    # accrued SHL interest converges on the higher figure; CIR cap brings the
    # deductible portion down to Excel's £96.6k.
    shl_switch: int = 1
    shl_pct_of_unfunded: float = 0.99
    shl_rate: float = 0.15
    shl_cir_threshold_gbpk: float = 2000.0    # de minimis £2m
    shl_cir_ebitda_cap_pct: float = 0.30      # 30% EBITDA

    # --- Depreciation method (D&T r163-165: SLM 1/36, RB 2/36, Applied=RB) ---
    # Excel uses Reducing Balance with annual rate = 2/36 = 5.555% (double-
    # declining over a nominal 36-year life). Final-month true-up writes off
    # the residual book value, ensuring lifetime depreciation = total capex
    # (matches Excel r194 total = -£81.8k vs capex £82k = 99.8%).
    depreciation_method: str = "RB"     # "RB" or "SLM"
    depreciation_rate: float = 2.0 / 36.0   # annual rate for RB

    # --- Discount rate (for NPV reporting) ---
    discount_rate: float = 0.065


@dataclass
class PirrResults:
    """Output of the unified PIRR calculation.

    Excel reports 3 distinct PIRRs (per Anchal's 2026-05-11 clarification):
    - Solar+BESS PIRR (`Equity!D175 = 8.85%` in current snapshot)
    - Combined Solar+BESS+Gas PIRR (`Consol Cash Flows!B9 = 9.23%`)
    - Gas PIRR (`Cash Flows-Gas!D84 = 10.77%`)

    `project_irr` is the Combined number (matches `Consol Cash Flows!B9`).
    `project_irr_solar_bess` is the Solar+BESS-only number (matches
    `Equity!D175`). `project_irr_gas` is the gas-only number.
    """
    # Combined Solar+BESS+Gas PIRR (matches Consol Cash Flows!B9)
    project_irr: float = float("nan")
    # Solar+BESS-only PIRR (matches Equity!D175). Computed by running the
    # engine with gas zeroed; useful for direct comparison against the SME's
    # May 7 matrix if that turned out to target S+B-only.
    project_irr_solar_bess: float = float("nan")
    # Gas-only PIRR (matches Cash Flows-Gas!D84). Computed by running the
    # engine with solar+BESS zeroed.
    project_irr_gas: float = float("nan")

    project_npv: float = 0.0
    total_capex: float = 0.0
    total_revenue_lifetime: float = 0.0
    total_opex_lifetime: float = 0.0
    total_tax_lifetime: float = 0.0
    # MOIC (Multiple on Invested Capital) — ungeared FCFF basis.
    # = sum(positive FCFF months) / |sum(negative FCFF months)|.
    # For a project with positive Project IRR, MOIC > 1.0; typical 35-year
    # infrastructure assets with 8-10% IRR land in the 2.5-3.5x range.
    # Returns NaN if no negative cash flows (degenerate). See Spec §7 + A46.
    moic: float = float("nan")

    dates: np.ndarray = field(default_factory=lambda: np.array([]))
    revenue: np.ndarray = field(default_factory=lambda: np.array([]))
    opex: np.ndarray = field(default_factory=lambda: np.array([]))
    capex: np.ndarray = field(default_factory=lambda: np.array([]))
    ebitda: np.ndarray = field(default_factory=lambda: np.array([]))
    depreciation: np.ndarray = field(default_factory=lambda: np.array([]))
    interest: np.ndarray = field(default_factory=lambda: np.array([]))
    tax: np.ndarray = field(default_factory=lambda: np.array([]))
    nwc_change: np.ndarray = field(default_factory=lambda: np.array([]))
    fcff: np.ndarray = field(default_factory=lambda: np.array([]))

    # Revenue breakdown
    rev_ppa: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_solar_merchant: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_rego: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_embedded: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_cm_t1: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_cm_t4: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_bess_floor: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_gas_ppa: np.ndarray = field(default_factory=lambda: np.array([]))
    rev_gas_merchant: np.ndarray = field(default_factory=lambda: np.array([]))


# =============================================================================
# TIMELINE
# =============================================================================

def _months_between(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _add_months(d: date, n: int) -> date:
    total = d.month - 1 + n
    return date(d.year + total // 12, total % 12 + 1, 1)


def _build_timeline(inp: PirrInputs):
    """Returns (dates, is_construction, is_operations, ops_month_idx).

    A35: timeline may extend backwards before `construction_start` when a
    capex phasing dict contains earlier months (development phase). The
    `is_construction` flag still covers only the construction window
    (`construction_start` → `cod_date`); pre-construction months show
    `is_construction=False` and `is_operations=False`.
    """
    # Find earliest month referenced anywhere (capex phasing dicts may
    # specify development-phase months before construction_start).
    timeline_start = inp.construction_start
    for d in (inp.capex_phasing_sb, inp.capex_phasing_gas):
        if d:
            ym = min(d.keys())
            phase_start = date(ym[0], ym[1], 1)
            if phase_start < timeline_start:
                timeline_start = phase_start

    total_months = _months_between(timeline_start, inp.cod_date) \
                   + inp.project_life_years * 12

    dates = np.array([_add_months(timeline_start, i)
                      for i in range(total_months)])
    is_construction = np.array([
        inp.construction_start <= d < inp.cod_date for d in dates
    ])
    is_operations = np.array([d >= inp.cod_date for d in dates])

    # 0-based index within ops period (-1 outside)
    ops_idx = np.full(len(dates), -1, dtype=int)
    counter = 0
    for i, op in enumerate(is_operations):
        if op:
            ops_idx[i] = counter
            counter += 1
    return dates, is_construction, is_operations, ops_idx


# =============================================================================
# CAPEX (D3: includes IDC, Financing, DSRA — all phased over construction)
# =============================================================================

def _calc_capex(inp: PirrInputs, dates: np.ndarray,
                is_construction: np.ndarray
                ) -> tuple[np.ndarray, float, dict[str, np.ndarray]]:
    """Compute monthly capex outflows + per-month additions by depreciation
    account (A38 Phase A multi-account routing per Excel `Construction!B76:B112`).

    Returns:
        (capex, total_capex, additions_by_account)
        - capex: monthly cash outflow array (negative, GBPk)
        - total_capex: lifetime sum (positive, GBPk)
        - additions_by_account: dict keyed by account name, with monthly
          positive depreciable-base additions per account.

    Account routing (D13 baseline; same rule for all configs):
        - 'long_term': solar + BESS + contingency + ALL gas capex
        - 'financing': IDC + Financing fees only
        - 'short_term': nothing (zero for all current configs)
        - NOT depreciated: DSRA (pre-funded cash reserve, returns at EOL)

    Excel routing source: `Construction!B76:B112` SUMIFs against
    `Curves and D&T!r71-r112` per-line "Choice" tags. All construction
    line items tagged "1" (Long term) except IDC + Financing fees tagged
    "3" (Financing).
    """
    n = len(dates)
    capex = np.zeros(n)
    additions_by_account: dict[str, np.ndarray] = {
        'long_term':  np.zeros(n),
        'short_term': np.zeros(n),
        'financing':  np.zeros(n),
    }

    # Solar items (linear with DC MWp), GBP/kWp × MWp = GBPk
    solar_items_per_kwp = (
        inp.capex_acquisition + inp.capex_development + inp.capex_discharge
        + inp.capex_dd + inp.capex_epc + inp.capex_grid + inp.capex_sdlt
        + inp.capex_land_legal + inp.capex_other_finance + inp.capex_other_legal
        + inp.capex_land_purchase + inp.capex_ampyr_tech + inp.capex_success_fee
        + inp.capex_community + inp.capex_landowner_fees + inp.capex_insurance
        + inp.capex_land_lease_constr + inp.capex_asset_adoption
        + inp.capex_others + inp.capex_misc
    )
    solar_capex = solar_items_per_kwp * inp.solar_dc_mwp  # GBPk

    # BESS — scales with BESS MW (D5).
    bess_capex = inp.capex_bess_gbp_per_kw_bess * inp.bess_mw  # GBPk

    # Gas — provided as total GBPk
    gas_capex = inp.gas_capex_total_gbpk

    sb_base = solar_capex + bess_capex
    sb_with_contingency = sb_base * (1.0 + inp.capex_contingency_pct)

    # A38 Phase A — split SB stream into depreciable accounts:
    #   long_term: physical assets (solar + BESS + contingency)
    #   financing: IDC + Fin Fees (Excel Account 3)
    #   not depreciated (cash only): DSRA
    sb_long_term = sb_with_contingency
    sb_financing = inp.capex_idc_gbpk + inp.capex_financing_fees_gbpk
    sb_dsra      = inp.capex_dsra_gbpk
    sb_total = sb_long_term + sb_financing + sb_dsra  # full cash outflow

    gas_total = gas_capex                              # all to long_term
    total = sb_total + gas_total

    # A35: per-stream monthly phasing curves. Falls back to uniform 9-month
    # distribution within construction window if curves not provided.
    use_phasing = bool(inp.capex_phasing_sb) and bool(inp.capex_phasing_gas)

    if use_phasing:
        ym_to_idx = {(d.year, d.month): i for i, d in enumerate(dates)}
        for ym, pct in inp.capex_phasing_sb.items():
            idx = ym_to_idx.get(ym)
            if idx is None:
                continue
            capex[idx] -= sb_total * pct
            additions_by_account['long_term'][idx] += sb_long_term * pct
            additions_by_account['financing'][idx] += sb_financing * pct
            # DSRA: cash outflow, no depreciation entry
        for ym, pct in inp.capex_phasing_gas.items():
            idx = ym_to_idx.get(ym)
            if idx is None:
                continue
            capex[idx] -= gas_total * pct
            additions_by_account['long_term'][idx] += gas_total * pct
    else:
        # Legacy: uniform across construction months
        cm = int(is_construction.sum())
        if cm > 0:
            sb_long_per_mo = sb_long_term / cm
            sb_fin_per_mo  = sb_financing / cm
            gas_per_mo     = gas_total / cm
            total_per_mo   = total / cm
            cm_indices = np.where(is_construction)[0]
            for idx in cm_indices:
                capex[idx] -= total_per_mo
                additions_by_account['long_term'][idx] += sb_long_per_mo + gas_per_mo
                additions_by_account['financing'][idx] += sb_fin_per_mo
                # DSRA: cash only

    return capex, total, additions_by_account


# =============================================================================
# REVENUE STREAMS
# =============================================================================

def _select_yield(inp: PirrInputs) -> float:
    return {"P50": inp.yield_p50, "P75": inp.yield_p75,
            "P90": inp.yield_p90}.get(inp.generation_selection, inp.yield_p50)


def _calc_revenue(inp: PirrInputs, rates: dict, dates: np.ndarray,
                  is_operations: np.ndarray, ops_idx: np.ndarray,
                  cpi_factor_lookup: list[float] | None = None) -> dict:
    n = len(dates)
    out = {k: np.zeros(n) for k in [
        "ppa", "solar_merchant", "rego", "embedded",
        "cm_t1", "cm_t4", "bess_floor", "gas_ppa", "gas_merchant"
    ]}

    annual_yield = _select_yield(inp)
    base_annual_gen_mwh = inp.solar_dc_mwp * annual_yield
    cod = inp.cod_date
    ppa_end = _add_months(cod, inp.ppa_tenor_years * 12)

    # Sum of monthly aggregates → reused for projections
    total_dc_y1 = float(np.sum(inp.monthly_solar_bess_to_dc))
    total_surplus_y1 = float(np.sum(inp.monthly_solar_surplus))
    total_gas_y1 = float(np.sum(inp.monthly_gas_mwh))

    for i in range(n):
        if not is_operations[i]:
            continue
        ops_year = ops_idx[i] // 12
        d = dates[i]
        m = d.month - 1
        season = inp.seasonality[m] if len(inp.seasonality) == 12 else 1.0/12

        # Solar degradation: year 1 = 1.0, then linear
        solar_degrad = max(1.0 - inp.solar_degradation_pct * ops_year, 0.0) \
                       if ops_year > 0 else 1.0

        # Total monthly solar generation (used for REGO and embedded benefits)
        monthly_gen = base_annual_gen_mwh * season * solar_degrad

        # ---- PPA: Year-1 monthly DC delivery × tariff × indexation ----
        if d < ppa_end:
            dc_energy = inp.monthly_solar_bess_to_dc[m] * solar_degrad
            ppa_factor = (1.0 + inp.ppa_escalation_rate) ** ops_year
            out["ppa"][i] = dc_energy * inp.ppa_tariff_gbp_mwh * ppa_factor / 1000

            # Solar surplus during PPA → merchant
            surplus = inp.monthly_solar_surplus[m] * solar_degrad
            mp = _merchant_price(inp.merchant_prices, d.year,
                                 inp.merchant_price_default,
                                 month=d.month,
                                 monthly_prices=inp.merchant_prices_monthly)
            out["solar_merchant"][i] = surplus * mp / 1000
        else:
            # Post-PPA: ALL generation merchant (no PPA, no DC delivery split)
            mp = _merchant_price(inp.merchant_prices, d.year,
                                 inp.merchant_price_default,
                                 month=d.month,
                                 monthly_prices=inp.merchant_prices_monthly)
            out["solar_merchant"][i] = monthly_gen * mp / 1000

        # ---- REGO ----
        if inp.rego_switch and ops_year < inp.rego_tenor_years:
            out["rego"][i] = monthly_gen * inp.rego_price * \
                _esc_factor(rates, inp.rego_indexation, ops_year,
                            cpi_factor_lookup) / 1000

        # ---- 11kV embedded benefits ----
        if inp.emb_switch and ops_year < inp.emb_tenor_years \
                and len(inp.emb_benefits_monthly) == 12:
            rate = inp.emb_benefits_monthly[m]  # GBP/MWh
            out["embedded"][i] = monthly_gen * rate * \
                _esc_factor(rates, inp.emb_indexation, ops_year,
                            cpi_factor_lookup) / 1000

        # ---- Capacity Market T-1 ----
        if d >= inp.cm_t1_start:
            cm_t1_year = _months_between(inp.cm_t1_start, d) // 12
            if cm_t1_year < inp.cm_t1_tenor_years:
                out["cm_t1"][i] = (
                    inp.cm_t1_value * inp.cm_t1_derating * inp.bess_mw / 12
                    * _esc_factor(rates, inp.cm_t1_indexation, cm_t1_year,
                                  cpi_factor_lookup)
                )

        # ---- Capacity Market T-4 ----
        if d >= inp.cm_t4_start:
            cm_t4_year = _months_between(inp.cm_t4_start, d) // 12
            if cm_t4_year < inp.cm_t4_tenor_years:
                out["cm_t4"][i] = (
                    inp.cm_t4_value * inp.cm_t4_derating * inp.bess_mw / 12
                    * _esc_factor(rates, inp.cm_t4_indexation, cm_t4_year,
                                  cpi_factor_lookup)
                )

        # ---- BESS floor (net of underwriter rev share) ----
        if inp.bess_floor_switch and ops_year < inp.bess_floor_tenor_years:
            gross = (inp.bess_floor_price * inp.bess_mw / 12
                     * _esc_factor(rates, inp.bess_floor_indexation, ops_year,
                                   cpi_factor_lookup))
            out["bess_floor"][i] = gross * (1.0 - inp.bess_floor_rev_share)

        # ---- Gas: PPA (year 1-10) THEN merchant (year 11 → gas EOL) ----
        # Parked-model convention: gas merchant REPLACES PPA, doesn't stack.
        gas_ppa_end = _add_months(cod, inp.gas_ppa_tenor_years * 12)
        gas_eol = _add_months(cod, inp.gas_operations_years * 12)
        if d < gas_ppa_end:
            gas_factor = (1.0 + inp.gas_ppa_escalation) ** ops_year
            out["gas_ppa"][i] = (
                inp.monthly_gas_mwh[m] * inp.gas_ppa_tariff * gas_factor / 1000
            )
        elif d < gas_eol:
            days = _days_in_month(d)
            yr_post_ppa = ops_year - inp.gas_ppa_tenor_years
            esc = (1.0 + inp.gas_merchant_escalation) ** max(yr_post_ppa, 0)
            out["gas_merchant"][i] = (
                inp.gas_mw * inp.gas_merchant_hours_per_day * days
                * inp.gas_merchant_tariff * esc / 1000
            )

    return out


def _merchant_price(prices: dict, year: int, default: float,
                    month: int | None = None,
                    monthly_prices: dict | None = None) -> float:
    """Look up merchant price for a given year (and month, if provided).

    Excel's `Solar&BESS Operation!r66` carries a *quarterly* price pattern —
    3 months at the same value, 4 distinct values per year, with Q1 winter
    peak and Q2 spring trough. Solar generation concentrates in Q2-Q3 (low
    price), so a yearly arithmetic average over-states the volume-weighted
    realised merchant revenue by ~7% over the post-PPA period — driving the
    A30-era D13 Combined PIRR gap.

    Resolution order:
      1. monthly_prices[(year, month)] if both provided and key exists
      2. yearly prices[year]
      3. linear interpolation between bracketing years in `prices`
      4. `default` (Excel uses 0 for years outside the curve range)

    Zero in either dict means *deliberately zero* — don't fall back.
    """
    # Prefer monthly resolution when available
    if monthly_prices and month is not None and (year, month) in monthly_prices:
        return monthly_prices[(year, month)]

    if not prices:
        return default
    if year in prices:
        return prices[year]
    keys = sorted(prices.keys())
    if year < keys[0] or year > keys[-1]:
        # Outside the curve range entirely → use default (no extrapolation)
        return default
    # Interpolate between bracketing years
    for j in range(len(keys) - 1):
        if keys[j] <= year <= keys[j + 1]:
            f = (year - keys[j]) / (keys[j + 1] - keys[j])
            return prices[keys[j]] * (1 - f) + prices[keys[j + 1]] * f
    return default


def _days_in_month(d: date) -> int:
    nm = _add_months(date(d.year, d.month, 1), 1)
    return (nm - date(d.year, d.month, 1)).days


# =============================================================================
# OPEX (negative GBPk)
# =============================================================================

def _calc_opex(inp: PirrInputs, rates: dict, dates: np.ndarray,
               is_operations: np.ndarray, ops_idx: np.ndarray,
               revenue: np.ndarray,
               cpi_factor_lookup: list[float] | None = None) -> np.ndarray:
    n = len(dates)
    opex = np.zeros(n)

    # Annual accumulators for the A33 land-lease top-up (applied at year-end)
    from collections import defaultdict
    _annual_fixed_lease = defaultdict(float)
    _annual_rev_lease = defaultdict(float)
    _last_month_idx_of_year: dict = {}

    # Solar fixed opex — excludes corrective maintenance (handled separately
    # as a level annual charge sized to Excel's 8-event step pattern).
    # PV O&M is also separated (A34): Excel applies "O&M - Year 3 Onwards"
    # escalation specifically to PV O&M, distinct from CPI on the other 8.
    # Insurance is also separated (A44): Excel uses a discrete year-by-year
    # schedule (Op r168), not per-kWp × CPI.
    solar_fixed_excl_pv_excl_ins_per_kwp = (
        inp.opex_grid_conn + inp.opex_greenkeeping
        + inp.opex_community + inp.opex_real_estate_tax + inp.opex_non_tech_am
        + inp.opex_subsidy_loss + inp.opex_tech_am
    )
    monthly_solar_fixed = solar_fixed_excl_pv_excl_ins_per_kwp * inp.solar_dc_mwp / 12
    monthly_pv_om = inp.opex_pv_om * inp.solar_dc_mwp / 12
    monthly_corrective = inp.opex_corrective_maint_annual_gbpk / 12

    # A44: Insurance MW scaling factor — schedule was extracted for D13 = 82 MWp;
    # other configs scale linearly by solar_dc_mwp / reference.
    ins_mw_scale = (
        inp.solar_dc_mwp / inp.opex_insurance_reference_mwp
        if inp.opex_insurance_reference_mwp > 0 else 1.0
    )

    bess_fixed_per_mw = (
        inp.bess_opex_om + inp.bess_opex_import
        + inp.bess_opex_rates + inp.bess_opex_lease
    )
    monthly_bess_fixed = bess_fixed_per_mw * inp.bess_mw / 12
    monthly_bess_step = (
        inp.bess_opex_ltsa_annual_gbpk
        + inp.bess_opex_pcs_warranty_annual_gbpk
        + inp.bess_opex_augmentation_annual_gbpk
    ) / 12

    gas_fixed_per_mw = (
        inp.gas_opex_environmental + inp.gas_opex_om_contract
        + inp.gas_opex_site_maintenance + inp.gas_opex_other_variable
        + inp.gas_opex_site_lease + inp.gas_opex_fixed_operating
        + inp.gas_opex_professional_fees + inp.gas_opex_property_tax
        + inp.gas_opex_telecom + inp.gas_opex_audit_fees
        + inp.gas_opex_insurance + inp.gas_opex_legal
    )
    # Excel scales fixed opex on GROSS installed capacity, not effective MW
    monthly_gas_fixed = gas_fixed_per_mw * inp.gas_capacity_mw_gross / 12
    monthly_gas_major_maint = inp.gas_opex_major_maint_annual / 12

    annual_yield = _select_yield(inp)
    base_annual_gen_mwh = inp.solar_dc_mwp * annual_yield

    bess_end = _add_months(inp.cod_date, 12 * inp.bess_operating_life_years)
    gas_eol = _add_months(inp.cod_date, inp.gas_operations_years * 12)
    gas_ppa_end = _add_months(inp.cod_date, inp.gas_ppa_tenor_years * 12)

    for i in range(n):
        if not is_operations[i]:
            continue
        ops_year = ops_idx[i] // 12
        d = dates[i]
        m = d.month - 1
        season = inp.seasonality[m] if len(inp.seasonality) == 12 else 1.0/12

        # Solar fixed (excl. PV O&M): bundled CPI escalation per Excel
        # `Inputs!r268-r277` (most lines use CPI in the active branch).
        opex[i] -= monthly_solar_fixed * \
            _esc_factor(rates, inp.opex_solar_fixed_indexation, ops_year,
                        cpi_factor_lookup)

        # PV O&M — own indexation case ("O&M - Year 3 Onwards") per A34.
        opex[i] -= monthly_pv_om * \
            _esc_factor(rates, inp.opex_pv_om_indexation, ops_year,
                        cpi_factor_lookup)

        # Corrective maintenance (CPI-escalated, level annual to match Excel)
        opex[i] -= monthly_corrective * \
            _esc_factor(rates, inp.opex_solar_fixed_indexation, ops_year,
                        cpi_factor_lookup)

        # Insurance on Plant & Machinery — A44 (per Anchal Q1 reply, memo
        # 2026-05-16). Excel uses a discrete year-by-year schedule (Op r168
        # source), not £/kWp × CPI. Construction premium tail in years 0-1
        # (engine 0-indexed; = Excel years 1-2); -30% discount kicks in at
        # engine year 2; years 4-9 alternate 0%/5% discount; year 10+ grows
        # at 2%/yr compound from £206.27k anchor. Per-MW linear scaling for
        # non-D13 configs (Anchal: "rough estimate"). Schedule values are
        # NOMINAL (already escalated) — do NOT apply CPI factor here.
        if inp.opex_insurance_schedule:
            if ops_year in inp.opex_insurance_schedule:
                ins_yearly = inp.opex_insurance_schedule[ops_year]
            elif ops_year >= 10:
                ins_yearly = inp.opex_insurance_yr11_base_gbpk * (
                    (1.0 + inp.opex_insurance_yr11_growth) ** (ops_year - 10)
                )
            else:
                ins_yearly = 0.0
            opex[i] -= (ins_yearly * ins_mw_scale) / 12
        else:
            # Legacy fallback: per-kWp × CPI (pre-A44 mechanism). Only used
            # when caller explicitly empties opex_insurance_schedule.
            opex[i] -= (inp.opex_insurance * inp.solar_dc_mwp / 12) * \
                _esc_factor(rates, inp.opex_solar_fixed_indexation, ops_year,
                            cpi_factor_lookup)

        # Solar variable (balancing services £/MWh × generation).
        # A32 (2026-05-15): split CfD vs Merchant per Excel FS r42/r43.
        # CfD (`Solar&BESS Inputs!F282 = 2.75`) applies during PPA tenor only,
        # NIL indexation (Excel F287 active branch). Post-PPA, Excel switches
        # to a time-varying merchant rate looked up from `Baringa and Aurora`
        # (see `Solar&BESS Inputs!F283` cell note). Engine consumes that
        # curve via `merchant_balancing_rate_by_ops_year`.
        solar_degrad = max(1.0 - inp.solar_degradation_pct * ops_year, 0.0) \
                       if ops_year > 0 else 1.0
        monthly_gen = base_annual_gen_mwh * season * solar_degrad
        if ops_year < inp.ppa_tenor_years:
            if inp.opex_balancing_cfd > 0:
                opex[i] -= (monthly_gen * inp.opex_balancing_cfd
                            * _esc_factor(rates, inp.opex_solar_var_indexation,
                                          ops_year, cpi_factor_lookup) / 1000)
        else:
            mrch_rate = inp.merchant_balancing_rate_by_ops_year.get(ops_year, 0.0)
            if mrch_rate > 0:
                opex[i] -= monthly_gen * mrch_rate / 1000

        # BESS fixed + step (LTSA / PCS Warranty / Augmentation) — both
        # capped at BESS operating life
        if d < bess_end:
            esc_bess = _esc_factor(rates, inp.bess_opex_indexation, ops_year,
                                   cpi_factor_lookup)
            opex[i] -= monthly_bess_fixed * esc_bess
            opex[i] -= monthly_bess_step * esc_bess

        # Gas fixed/variable — only while gas plant operates (years 1..gas EOL)
        if d < gas_eol:
            gas_esc = (1.0 + inp.gas_opex_inflation) ** ops_year
            opex[i] -= monthly_gas_fixed * gas_esc

            # Major equipment maintenance — A36: discrete-event schedule
            # takes precedence over level-annual when populated. Excel
            # `Cash Flows-Gas!r44` shows lumpy events concentrated in
            # years 1, 3, 4, 6, 7, 9, 12, 15. Engine's prior level-annual
            # approximation totalled correctly but mis-distributed timing
            # (drove the 2042 FCFF anomaly).
            if inp.gas_major_maint_schedule:
                event_gbpk = inp.gas_major_maint_schedule.get(ops_year, 0.0)
                # Spread the yearly amount evenly across 12 months;
                # values are nominal (already inflated) — do NOT apply gas_esc.
                opex[i] -= event_gbpk / 12
            else:
                opex[i] -= monthly_gas_major_maint * gas_esc

            # Gas energy this month: dispatch-derived during PPA, capacity-based
            # post-PPA (matches parked gas_model and the revenue side above)
            if d < gas_ppa_end:
                gas_mwh = inp.monthly_gas_mwh[m]
            else:
                days = _days_in_month(d)
                gas_mwh = (inp.gas_mw * inp.gas_merchant_hours_per_day * days)

            # Reactive maintenance — per MWh of gas output (Cash Flows-Gas r48)
            opex[i] -= gas_mwh * inp.gas_opex_reactive_per_mwh

            # Fuel = MWh_thermal × £/MWh, MWh_thermal = MWh_elec / efficiency
            fuel_esc = (1.0 + inp.gas_fuel_escalation_from_yr4) ** max(0, ops_year - 3)
            fuel_cost_gbpk = gas_mwh / max(inp.gas_net_efficiency, 0.001) \
                * inp.gas_fuel_price_gbp_mwh * fuel_esc / 1000
            opex[i] -= fuel_cost_gbpk

            # UKETS (CO2 cost on FUEL CONSUMED — thermal MWh, not electric).
            # Excel Cash Flows-Gas r38 sums on thermal basis: CO2 emissions
            # are generated per unit of gas burned, not per unit of power
            # delivered. Halved-line check: Excel r38/2 ≈ £78k vs electric
            # MWh basis £29k. Thermal basis matches Excel.
            thermal_mwh = gas_mwh / max(inp.gas_net_efficiency, 0.001)
            ukets_gbpk = (thermal_mwh * inp.gas_co2_kg_per_mwh
                          * inp.gas_ukets_cost_gbp_per_kg / 1000)
            opex[i] -= ukets_gbpk

            # Gas fixed-cost-per-day (Excel: "Fixed gas cost £/day")
            days = _days_in_month(d)
            opex[i] -= inp.gas_fixed_cost_gbp_day * days * gas_esc / 1000

        # Land lease — fixed (monthly) is always paid; the revenue-dependent
        # top-up is applied ANNUALLY. Anchal Q3 (decisions log A18):
        #   Final lease = Σ fixed (monthly) + max(0, annual_rev - annual_fixed)
        #   where annual_rev = 5% of annual operating revenue.
        # The previous engine took max(fixed_m, rev_m) per month — equivalent
        # to the annual formula only when rev_m > fixed_m in EVERY month, which
        # is false for D13 (seasonal revenue dips below fixed in winter). The
        # monthly-max over-charges land lease by ~£1.0M lifetime. A33 fixes
        # this by accumulating annual totals in the loop and applying the
        # annual top-up post-loop.
        fixed_lease_m = 0.0
        if inp.fixed_lease_switch:
            fixed_lease_m = (
                inp.fixed_lease_price * inp.fixed_lease_acres / 1000 / 12
                * _esc_factor(rates, inp.fixed_lease_indexation, ops_year,
                              cpi_factor_lookup)
            )
        rev_lease_m = 0.0
        if inp.rev_dep_lease_switch and revenue[i] > 0:
            share = inp.rev_share_yr1_10 if ops_year < 10 \
                else inp.rev_share_yr11_35
            rev_lease_m = revenue[i] * share
        opex[i] -= fixed_lease_m
        _annual_fixed_lease[ops_year] += fixed_lease_m
        _annual_rev_lease[ops_year] += rev_lease_m
        _last_month_idx_of_year[ops_year] = i  # track for top-up placement

    # Apply the annual revenue-dependent top-up: extra cost paid only when
    # annual_rev > annual_fixed. Placed at the LAST operating month of each
    # ops_year (Excel structures it as a July adjustment — last month of
    # the ops year roll; for COD 2027-07-01 the ops year runs Jul-Jun, so
    # last_month_idx_of_year[ops_year] is June of the calendar year after
    # COD-year-shift). IRR effect of within-year placement is negligible
    # versus single-shot at year boundary.
    for oy, idx in _last_month_idx_of_year.items():
        topup = max(0.0, _annual_rev_lease[oy] - _annual_fixed_lease[oy])
        if topup > 0:
            opex[idx] -= topup

    return opex


# =============================================================================
# DEPRECIATION (D&T r163-165: SLM or Reducing Balance; Excel uses RB)
# =============================================================================

def _calc_depreciation(inp: "PirrInputs",
                       additions_by_account: dict[str, np.ndarray],
                       dates: np.ndarray) -> np.ndarray:
    """Compute monthly tax depreciation matching Excel `D&T!r194/r216`.

    A38 (Phase A multi-account + Phase C dep-from-construction):

    - 3 parallel depreciation chains per `_DEPRECIATION_ACCOUNTS`
      (long_term 30 yr, short_term 8 yr, financing 3 yr). Each account
      has its own monthly RB rate from Excel `D&T!r68/r87/r106` (and
      monthly SL rate from `D&T!r67/r86/r105`).
    - Each month's addition within an account starts its own chain in
      the addition month and runs forward for that account's `life_months`
      (or until timeline end). Mirrors Excel `D&T!r62 "Entering
      depreciation base"` per-month-per-account.

    Within each chain (RB method): book × monthly_rb_rate per month, with
    SLM-on-remaining crossover so lifetime depreciation = addition base.
    The crossover kicks in at the addition-specific tail (chain_len ≥
    life_months when timeline is long enough; for tail additions where
    chain_len < life_months the crossover ensures full depreciation
    inside the truncated chain — preserves engine pre-A38 behaviour).

    Args:
      additions_by_account: keyed by account name; per-month positive
        depreciable base (GBPk). Comes from `_calc_capex` Phase A routing.
      dates: timeline. Chain length per addition capped at `n - addition_month`.
    """
    n = len(dates)
    depr = np.zeros(n)
    if not additions_by_account:
        return depr

    method = inp.depreciation_method.upper()

    for account_name, additions in additions_by_account.items():
        if account_name not in _DEPRECIATION_ACCOUNTS:
            continue
        cfg = _DEPRECIATION_ACCOUNTS[account_name]
        life_months = cfg['life_months']
        monthly_rate = cfg['monthly_rb'] if method == "RB" else cfg['monthly_sl']

        for m in range(n):
            base = float(additions[m])
            if base <= 0:
                continue
            chain_len = min(life_months, n - m)

            if method == "SLM":
                monthly = base / life_months
                tail = min(chain_len, life_months)
                for k in range(tail):
                    depr[m + k] += monthly
                continue

            # Reducing Balance with SLM crossover (per addition chain)
            book = base
            for k in range(chain_len):
                remaining = chain_len - k
                rb_amount = book * monthly_rate
                slm_amount = book / remaining
                d = max(rb_amount, slm_amount)
                d = min(d, book)
                depr[m + k] += d
                book -= d
                if book <= 0:
                    break

    return depr


# =============================================================================
# MINIMAL DEBT SCHEDULE (D2 / A15 — for tax shield only, no FCFF cash flows)
# =============================================================================

def _calc_interest(inp: PirrInputs, total_capex: float,
                   is_operations: np.ndarray) -> np.ndarray:
    n = len(is_operations)
    interest = np.zeros(n)

    principal = total_capex * inp.gearing
    if principal <= 0:
        return interest

    monthly_rate = inp.interest_rate / 12
    grace_months = inp.grace_period_months
    amort_months = max(inp.debt_tenor_years * 12 - grace_months, 1)

    # Annuity over post-grace amortising portion
    if monthly_rate > 0:
        annuity = principal * monthly_rate * (1 + monthly_rate) ** amort_months \
                  / ((1 + monthly_rate) ** amort_months - 1)
    else:
        annuity = principal / amort_months

    balance = principal
    op_idx = 0
    for i in range(n):
        if not is_operations[i]:
            continue
        if op_idx < grace_months:
            interest[i] = balance * monthly_rate
            # interest-only during grace
        elif op_idx < grace_months + amort_months and balance > 0:
            int_pmt = balance * monthly_rate
            principal_pmt = annuity - int_pmt
            interest[i] = int_pmt
            balance = max(balance - principal_pmt, 0.0)
        # else: debt fully repaid
        op_idx += 1
    return interest


# =============================================================================
# SHL INTEREST (Excel Solar&BESS Inputs F553 + F556; D&T r197)
# =============================================================================

def _calc_shl_interest(inp: PirrInputs, total_capex: float,
                       is_operations: np.ndarray) -> np.ndarray:
    """SHL interest expense per month — feeds tax shield only (ungeared FCFF
    doesn't include SHL principal or interest as cash). Interest-only on the
    initial SHL principal at the SHL rate, held constant across operations.

    SHL applies to **solar+BESS capex only** — gas plant has its own separate
    financing chain in Excel (`Cash Flows-Gas`), with no SHL. To mirror this,
    we subtract gas capex from the SHL base.
    """
    n = len(is_operations)
    shl_int = np.zeros(n)
    if not inp.shl_switch or total_capex <= 0:
        return shl_int

    # Exclude gas portion — Excel's SHL is on solar+BESS capex only.
    sb_capex_base = max(total_capex - inp.gas_capex_total_gbpk, 0.0)
    if sb_capex_base <= 0:
        return shl_int

    unfunded = sb_capex_base * (1.0 - inp.gearing)
    principal = unfunded * inp.shl_pct_of_unfunded
    monthly_rate = inp.shl_rate / 12.0
    shl_int[is_operations] = principal * monthly_rate
    return shl_int


# =============================================================================
# TAX (D2: max(0, (EBIT − Interest) × rate); annual loss carry-forward)
# UK CIR cap applied to SHL portion: deductible SHL ≤ max(£2m, 30% × EBITDA)
# =============================================================================

def _calc_tax(inp: PirrInputs, dates: np.ndarray,
              is_active: np.ndarray,
              ebitda: np.ndarray, depreciation: np.ndarray,
              interest_senior: np.ndarray,
              interest_shl: np.ndarray) -> np.ndarray:
    """Annual taxable income chain matching Excel `D&T!r193-r200, r210-r212,
    r221-r228`.

    Per-year mechanics (taxation month = December):
      Taxable_y          = EBITDA_y − Depr_y − DeductibleInterest_y
      tax_loss_generated = max(0, -Taxable_y)
      tax_loss_utilised  = min(loss_pool_BOP, max(0, Taxable_y))
      net_taxable_y      = max(0, Taxable_y − tax_loss_utilised)
      Tax_y              = net_taxable_y × rate
      loss_pool_EOP      = loss_pool_BOP + generated − utilised

    UK CIR cap (`D&T!r210-r212`): total deductible interest (senior + SHL)
    is capped at `max(£2m, 30% × EBITDA_y)`. Senior interest is prioritised
    (always deducted up to the cap); SHL fills any remaining headroom.
    Excess interest is non-deductible.

    A38 (Phase C — dep-from-construction): `is_active` covers all months
    from first capex addition forward (pre-A38: `is_operations` only).
    During construction, EBITDA = 0 + depreciation > 0 + interest = 0
    (pre-COD interest is in IDC capex, not interest_senior) so
    Taxable_y < 0 → loss_pool accumulates. When operations start, the
    accumulated pool reduces early ops-year tax.
    """
    n = len(dates)
    tax = np.zeros(n)

    annual_ebitda = 0.0
    annual_depr = 0.0
    annual_senior = 0.0
    annual_shl = 0.0
    loss_pool = 0.0

    for i in range(n):
        if not is_active[i]:
            continue
        annual_ebitda += ebitda[i]
        annual_depr += depreciation[i]
        annual_senior += interest_senior[i]
        annual_shl += interest_shl[i]

        if dates[i].month == inp.taxation_month:
            cap = max(inp.shl_cir_threshold_gbpk,
                      inp.shl_cir_ebitda_cap_pct * max(annual_ebitda, 0.0))
            deductible_senior = min(annual_senior, cap)
            remaining_cap = max(cap - deductible_senior, 0.0)
            deductible_shl = min(annual_shl, remaining_cap)

            taxable = (annual_ebitda - annual_depr
                       - deductible_senior - deductible_shl)
            if taxable < 0:
                loss_pool += -taxable
                taxable = 0.0
            else:
                if loss_pool > 0:
                    used = min(loss_pool, taxable)
                    taxable -= used
                    loss_pool -= used
            if taxable > 0:
                tax[i] = -taxable * inp.corp_tax_rate

            annual_ebitda = 0.0
            annual_depr = 0.0
            annual_senior = 0.0
            annual_shl = 0.0
    return tax


# =============================================================================
# NWC (debtor/creditor days; ΔNWC is a cash effect)
# =============================================================================

def _calc_nwc_change(inp: PirrInputs, is_operations: np.ndarray,
                     revenue: np.ndarray, opex: np.ndarray) -> np.ndarray:
    n = len(is_operations)
    out = np.zeros(n)
    if inp.debtor_days == 0 and inp.creditor_days == 0:
        return out
    prev = 0.0
    for i in range(n):
        if not is_operations[i]:
            continue
        # Annualise the period to estimate balance
        debtors = revenue[i] * 12 * inp.debtor_days / 365
        creditors = abs(opex[i]) * 12 * inp.creditor_days / 365
        cur = debtors - creditors
        out[i] = -(cur - prev)
        prev = cur
    return out


# =============================================================================
# XIRR — bisection (Excel-compatible day count)
# =============================================================================

def xirr(dates: np.ndarray, cashflows: np.ndarray,
         tol: float = 1e-7) -> float:
    mask = cashflows != 0
    if mask.sum() < 2:
        return float("nan")
    cf = cashflows[mask]
    dt = dates[mask]
    d0 = dt[0]
    day_fracs = np.array([(d - d0).days / 365.0 for d in dt])

    def npv(rate):
        if rate <= -1:
            return float("inf")
        # Avoid float overflow at extreme negative rates by capping
        result = float(np.sum(cf / (1 + rate) ** day_fracs))
        return result if np.isfinite(result) else float("inf") * (1 if cf.sum() > 0 else -1)

    # Bracket narrowed to [-0.5, 2.0] — well wide enough for any realistic
    # project IRR but avoids overflow at extreme negative rates. If sign
    # doesn't change in this range, widen step-wise rather than going huge.
    lo, hi = -0.5, 2.0
    f_lo, f_hi = npv(lo), npv(hi)
    # Widen on either side if no sign change yet
    if f_lo * f_hi > 0:
        for wider_lo, wider_hi in [(-0.9, 2.0), (-0.5, 5.0), (-0.9, 10.0)]:
            f_lo, f_hi = npv(wider_lo), npv(wider_hi)
            if f_lo * f_hi <= 0:
                lo, hi = wider_lo, wider_hi
                break
        else:
            return float("nan")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        f_mid = npv(mid)
        if abs(f_mid) < tol or (hi - lo) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid
    return 0.5 * (lo + hi)


def xnpv(dates: np.ndarray, cashflows: np.ndarray, rate: float) -> float:
    if len(dates) == 0:
        return 0.0
    d0 = dates[0]
    day_fracs = np.array([(d - d0).days / 365.0 for d in dates])
    return float(np.sum(cashflows / (1 + rate) ** day_fracs))


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def run_pirr(inp: PirrInputs) -> PirrResults:
    """Run the full PIRR calculation and report all three IRR variants.

    Internally:
    1. Combined run (gas + S+B) → primary result, stored as project_irr.
    2. S+B-only run (gas zeroed) → project_irr_solar_bess.
    3. Gas-only run (S+B zeroed) → project_irr_gas.

    Per Anchal's 2026-05-11 reply, Excel reports these as 3 separate
    numbers and the SME matrix target may map to any of them — see A18.
    """
    res = _run_pirr_core(inp)
    # Solar+BESS-only — gas off
    inp_sb = _disable_gas(inp)
    res.project_irr_solar_bess = _run_pirr_core(inp_sb).project_irr
    # Gas-only — S+B off
    inp_gas = _disable_solar_bess(inp)
    res.project_irr_gas = _run_pirr_core(inp_gas).project_irr
    return res


def _disable_gas(inp: PirrInputs) -> PirrInputs:
    import dataclasses as _dc
    return _dc.replace(
        inp,
        gas_operations_years=0,
        gas_capex_total_gbpk=0.0,
        monthly_gas_mwh=np.zeros(12),
    )


def _disable_solar_bess(inp: PirrInputs) -> PirrInputs:
    """Zero the Solar+BESS economics to isolate gas-only PIRR.

    Capex, revenue (PPA, merchant, REGO, embedded, CM, BESS floor), and
    OPEX (solar fixed, solar var, BESS fixed, BESS step, land) all keyed
    off solar_dc_mwp / bess_mw / monthly aggregates — zero those, plus the
    capex per-kWp items, to leave only the gas economics in FCFF.
    """
    import dataclasses as _dc
    return _dc.replace(
        inp,
        solar_dc_mwp=0.0,
        bess_mw=0.0,
        bess_mwh=0.0,
        monthly_solar_bess_to_dc=np.zeros(12),
        monthly_solar_surplus=np.zeros(12),
        fixed_lease_switch=0,
        rev_dep_lease_switch=0,
        bess_floor_switch=0,
        cm_t1_value=0.0,
        cm_t4_value=0.0,
        rego_switch=0,
        emb_switch=0,
        opex_balancing_cfd=0.0,
        opex_corrective_maint_annual_gbpk=0.0,
        bess_opex_ltsa_annual_gbpk=0.0,
        bess_opex_pcs_warranty_annual_gbpk=0.0,
        bess_opex_augmentation_annual_gbpk=0.0,
    )


def _run_pirr_core(inp: PirrInputs) -> PirrResults:
    """Single-pass PIRR computation. Used internally by run_pirr() for
    each of the 3 variants. Returns a full PirrResults but only fills
    project_irr (the combined-style number for whatever inputs are given).
    """
    res = PirrResults()
    rates = dict(DEFAULT_ESCALATION_RATES)
    if inp.ppa_escalation_rate:
        rates["PPA Indexation"] = inp.ppa_escalation_rate

    dates, is_construction, is_operations, ops_idx = _build_timeline(inp)
    n = len(dates)
    res.dates = dates

    # Capex first — depreciation, interest, FCFF all depend on total.
    # A38 Phase A: capex also returns per-account additions for multi-account dep.
    capex, total_capex, additions_by_account = _calc_capex(
        inp, dates, is_construction)
    res.capex = capex
    res.total_capex = total_capex

    # A40 (2026-05-16): precompute the variable-CPI cumulative factor per
    # ops_year using Excel `Curves and D&T!r10` curve. Replaces flat A39 rate
    # at all "CPI"-cased line items in _calc_revenue and _calc_opex. Steady-
    # state fallback (years not in the curve) uses `rates["CPI"]` (2.0%).
    cpi_factor_lookup = _build_cpi_factor_lookup(
        inp.cpi_curve_by_calendar_year,
        rates["CPI"],
        inp.cod_date.year,
        inp.project_life_years,
    )

    # Revenue
    rev = _calc_revenue(inp, rates, dates, is_operations, ops_idx,
                        cpi_factor_lookup)
    revenue = sum(rev.values())  # numpy element-wise sum
    res.revenue = revenue
    res.total_revenue_lifetime = float(revenue.sum())
    res.rev_ppa = rev["ppa"]
    res.rev_solar_merchant = rev["solar_merchant"]
    res.rev_rego = rev["rego"]
    res.rev_embedded = rev["embedded"]
    res.rev_cm_t1 = rev["cm_t1"]
    res.rev_cm_t4 = rev["cm_t4"]
    res.rev_bess_floor = rev["bess_floor"]
    res.rev_gas_ppa = rev["gas_ppa"]
    res.rev_gas_merchant = rev["gas_merchant"]

    # Opex (depends on revenue for rev-dep lease)
    opex = _calc_opex(inp, rates, dates, is_operations, ops_idx, revenue,
                      cpi_factor_lookup)
    res.opex = opex
    res.total_opex_lifetime = float(-opex.sum())

    ebitda = revenue + opex
    res.ebitda = ebitda

    # A38 (Phase A + C): per-account, per-month additions feed multi-account
    # depreciation chains. Excel D&T r51-r178: 3 accounts with own RB/SL
    # rates and lifetimes (long_term 30 yr / short_term 8 yr / financing 3 yr).
    depr = _calc_depreciation(inp, additions_by_account, dates)
    res.depreciation = depr

    interest = _calc_interest(inp, total_capex, is_operations)
    res.interest = interest

    shl_interest = _calc_shl_interest(inp, total_capex, is_operations)

    # A38 (Phase C): tax computation spans the entire timeline so that
    # depreciation in development + construction months generates NOL pool
    # entries that absorb against early ops-year income. The timeline is
    # already bounded `[timeline_start, ops_end]` by `_build_timeline`,
    # and ebitda/interest are zero pre-COD by construction (no revenue/opex
    # nor senior/SHL interest pre-COD; IDC is in capex), so making the
    # tax loop unconditional is safe.
    is_active = np.ones(n, dtype=bool)
    tax = _calc_tax(inp, dates, is_active, ebitda, depr,
                    interest, shl_interest)
    res.tax = tax
    res.total_tax_lifetime = float(-tax.sum())

    nwc_change = _calc_nwc_change(inp, is_operations, revenue, opex)
    res.nwc_change = nwc_change

    # FCFF (ungeared cash) — interest does NOT appear in FCFF (D2)
    fcff = revenue + opex + tax + capex + nwc_change
    res.fcff = fcff

    res.project_irr = xirr(dates, fcff)
    res.project_npv = xnpv(dates, fcff, inp.discount_rate)

    # MOIC (A46): split FCFF by sign. Distributions = positive months
    # (operating returns); Contributions = absolute value of negative months
    # (construction capex + any net operating losses + terminal outflows).
    # Ungeared basis — matches the FCFF-level IRR.
    distributions = float(fcff[fcff > 0].sum())
    contributions = float(-fcff[fcff < 0].sum())
    res.moic = (
        distributions / contributions if contributions > 0 else float("nan")
    )

    return res


# =============================================================================
# WIZARD STATE ADAPTER
# =============================================================================

def pirr_inputs_from_wizard_state(
    fin: dict,
    setup: dict | None = None,
    monthly_aggregates: dict | None = None,
) -> PirrInputs:
    """Build PirrInputs from wizard_state['financial'] + Step 1 setup + dispatch monthly aggregates.

    Strategy: start from PirrInputs() defaults (which are the D13 fixture
    values), override with whatever scalar fields the wizard state provides.
    Arrays (merchant curve, embedded benefits, seasonality) keep the engine
    defaults unless explicitly overridden — wizard state doesn't carry them
    today and the D13 defaults are SME-confirmed.

    Args:
        fin: wizard_state['financial'] dict
        setup: wizard_state['setup'] dict (for load_mw — D8 / Step 1 contract)
        monthly_aggregates: dict from dispatch_energy.compute_monthly_energy()
            with keys 'solar_bess_to_dc', 'solar_surplus', 'gas_energy'

    Returns: PirrInputs ready to feed run_pirr()
    """
    setup = setup or {}
    monthly_aggregates = monthly_aggregates or {}

    def f(key, default):
        v = fin.get(key)
        return float(v) if v is not None else float(default)

    def i(key, default):
        v = fin.get(key)
        return int(v) if v is not None else int(default)

    bess_mw = f("bess_capacity_mw", 62.5)
    bess_duration = f("bess_duration_hrs", 4.0)

    # Convert display-% inputs (wizard convention) to decimal (engine convention)
    degradation_decimal = f("degradation_pct", 0.3) / 100.0

    # Defaults for monthly arrays: use zeros if dispatch hasn't run yet
    z = np.zeros(12)
    return PirrInputs(
        # --- Capacity (D8: DC MWp for capex, AC profile peak ≈ grid limit) ---
        solar_dc_mwp=f("solar_capacity_mwp", 82.0),
        grid_limit_mw=f("grid_limit_mw", 58.4),
        bess_mw=bess_mw,
        bess_mwh=bess_mw * bess_duration,
        bess_operating_life_years=i("bess_operating_life", 10),
        gas_mw=f("gas_mw", 25.0),
        gas_capacity_mw_gross=f("gas_capacity_mw_gross", 28.32),
        load_mw=float(setup.get("load_mw", 25.0)),

        # --- Solar yield ---
        yield_p50=f("yield_p50", 967.0),
        yield_p75=f("yield_p75", 936.0),
        yield_p90=f("yield_p90", 895.0),
        generation_selection=str(fin.get("generation_selection", "P50")),
        solar_degradation_pct=degradation_decimal,

        # --- Year-1 monthly aggregates from dispatch ---
        monthly_solar_bess_to_dc=np.asarray(
            monthly_aggregates.get("solar_bess_to_dc", z)),
        monthly_solar_surplus=np.asarray(
            monthly_aggregates.get("solar_surplus", z)),
        monthly_gas_mwh=np.asarray(monthly_aggregates.get("gas_energy", z)),

        # --- PPA ---
        ppa_tariff_gbp_mwh=f("ppa_tariff_gbp_mwh", 170.0),
        ppa_tenor_years=i("ppa_tenor_years", 10),
        ppa_escalation_rate=f("ppa_escalation_pct", 0.0) / 100.0,

        # --- REGOs ---
        rego_switch=i("rego_switch", 1),
        rego_price=f("rego_price", 2.5),
        rego_tenor_years=i("rego_tenor_years", 35),

        # --- 11kV embedded benefits ---
        emb_switch=i("emb_benefits_switch", 1),
        emb_tenor_years=i("emb_benefits_tenor", 15),

        # --- BESS revenue switches (defaults: OFF per Anchal Q2 2026-05-11)
        # — user can override in wizard if running a non-Burton-Leonard case
        bess_floor_switch=i("bess_floor_switch", 0),
        bess_floor_price=f("bess_floor_price", 40.0),
        bess_floor_rev_share=f("bess_floor_rev_share", 9.0) / 100.0,
        bess_floor_tenor_years=i("bess_floor_tenor", 10),
        cm_t1_value=f("cm_t1_value", 0.0),
        cm_t1_derating=f("cm_t1_derating", 27.15) / 100.0,
        cm_t1_tenor_years=i("cm_t1_tenor", 3),
        cm_t4_value=f("cm_t4_value", 0.0),
        cm_t4_derating=f("cm_t4_derating", 20.94) / 100.0,
        cm_t4_tenor_years=i("cm_t4_tenor", 15),

        # --- Solar OPEX (GBP/kWp/yr) ---
        opex_pv_om=f("opex_pv_om", 5.48),
        opex_grid_conn=f("opex_grid_conn", 0.003),
        opex_greenkeeping=f("opex_greenkeeping", 1.5),
        opex_community=f("opex_community", 0.5),
        opex_real_estate_tax=f("opex_real_estate_tax", 1.222),
        opex_non_tech_am=f("opex_non_tech_am", 1.3),
        opex_subsidy_loss=f("opex_subsidy_loss", 0.0),
        opex_insurance=f("opex_insurance", 2.021),
        opex_corrective_maint=f("opex_corrective_maint", 3.2),
        opex_tech_am=f("opex_tech_am", 0.3),
        opex_balancing_cfd=f("opex_balancing_cfd", 2.75),
        # A32: post-PPA merchant balancing rate curve (£/MWh by ops_year).
        # Wizard state can supply a dict here; otherwise fall back to the
        # Burton-Leonard locked default so the wizard-state path produces
        # the same answer as the audit fixture.
        merchant_balancing_rate_by_ops_year=fin.get(
            "merchant_balancing_rate_by_ops_year"
        ) or dict(_DEFAULT_MERCHANT_BALANCING_BY_OPS_YEAR),

        # --- BESS OPEX (GBPk/MW/yr) ---
        bess_opex_om=f("bess_opex_om", 7.063),
        bess_opex_import=f("bess_opex_import", 0.0),
        bess_opex_rates=f("bess_opex_rates", 3.276),
        bess_opex_lease=f("bess_opex_lease", 1.489),

        # --- Land ---
        fixed_lease_switch=i("fixed_lease_switch", 1),
        fixed_lease_acres=f("fixed_lease_acres", 205.0),
        fixed_lease_price=f("fixed_lease_price", 700.0),
        rev_dep_lease_switch=i("rev_dep_lease_switch", 1),
        rev_share_yr1_10=f("rev_share_yr1_10", 5.0) / 100.0,
        rev_share_yr11_35=f("rev_share_yr11_35", 5.0) / 100.0,

        # --- CAPEX (GBP/kWp solar items) ---
        capex_acquisition=f("capex_acquisition", 0.0),
        capex_development=f("capex_development", 2.949),
        capex_discharge=f("capex_discharge", 0.983),
        capex_dd=f("capex_dd", 3.775),
        capex_epc=f("capex_epc", 400.0),
        capex_grid=f("capex_grid", 57.858),
        capex_sdlt=f("capex_sdlt", 0.753),
        capex_land_legal=f("capex_land_legal", 3.686),
        capex_other_finance=f("capex_other_finance", 5.0),
        capex_other_legal=f("capex_other_legal", 0.0),
        capex_land_purchase=f("capex_land_purchase", 0.0),
        capex_ampyr_tech=f("capex_ampyr_tech", 3.236),
        capex_success_fee=f("capex_success_fee", 0.0),
        capex_community=f("capex_community", 0.0),
        capex_landowner_fees=f("capex_landowner_fees", 11.597),
        capex_insurance=f("capex_insurance", 6.329),
        capex_land_lease_constr=f("capex_land_lease_constr", 2.457),
        capex_asset_adoption=f("capex_asset_adoption", 0.0),
        capex_others=f("capex_others", 0.0),
        capex_misc=f("capex_misc", 4.916),
        capex_bess_gbp_per_kw_bess=f("capex_bess", 600.0),
        capex_contingency_pct=f("capex_contingency_pct", 1.0) / 100.0,

        # --- Tax ---
        # UK has two corporate tax rates (small profits 19% / main rate 25%).
        # Excel D13 / Curves and D&T E108 = 25% (the main rate). Projects in
        # this engine's scope are well above the £250k profit threshold, so
        # the main rate is the binding one. Pre-A28 this read
        # `corp_tax_rate_low` and silently applied 19% — see decisions log A28.
        corp_tax_rate=f("corp_tax_rate_high", 25.0) / 100.0,
        taxation_month=i("taxation_month", 12),

        # --- Working capital ---
        debtor_days=i("wc_debtors_days", 30),
        creditor_days=i("wc_creditors_days", 30),

        # --- SHL + Depreciation method (Step 7 Advanced expander) ---
        shl_switch=i("shl_switch", 1),
        shl_pct_of_unfunded=f("shl_pct_of_unfunded", 99.0) / 100.0,
        shl_rate=f("shl_rate", 15.0) / 100.0,
        depreciation_method=str(fin.get("depreciation_method", "RB")),
        depreciation_rate=f("depreciation_rate", 5.555) / 100.0,

        # --- Discount (for NPV reporting) ---
        discount_rate=f("project_discount_rate", 6.5) / 100.0,
    )
