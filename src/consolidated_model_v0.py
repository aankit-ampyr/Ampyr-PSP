"""
Consolidated Financial Model — Combines Solar+BESS and Gas FCFFs.

PARKED 2026-05-07. Audit (A9 Step A) showed −0.44 pp at the D13 target;
the `gas_ownership_share` calibration constant violates Guardrail #5.
Retained for audit reproducibility only — do not use for new work.
See docs/Project_IRR_Integration_Decisions.md A16 for details.

Merges the two independent FCFF streams onto a common date grid,
sums them, and computes the Overall Project IRR via XIRR.

Mirrors the 'Consol Cash Flows' sheet in Off-Grid Solution v8.xlsm.
"""

from datetime import date
import numpy as np

from src.financial_model_v0 import FinancialResults, calc_xirr, calc_xnpv


def run_consolidated_irr(
    sb_results: FinancialResults,
    gas_dates: np.ndarray,
    gas_fcff: np.ndarray,
    discount_rate: float = 0.065,
    gas_ownership_share: float = 0.5,
) -> dict:
    """
    Combine Solar+BESS and Gas FCFF streams into an overall Project IRR.

    Args:
        sb_results: FinancialResults from run_tariff_model
        gas_dates: date array from GasResults
        gas_fcff: FCFF array from GasResults
        discount_rate: for XNPV calculation

    Returns dict with:
        'overall_irr'   — XIRR of combined FCFF
        'overall_npv'   — XNPV at discount_rate
        'sb_irr'        — Solar+BESS component IRR
        'gas_irr'       — Gas component IRR
        'dates'         — combined date array
        'fcff'          — combined FCFF array
        'sb_fcff'       — Solar+BESS FCFF on combined grid
        'gas_fcff'      — Gas FCFF on combined grid
    """
    # Build union of all dates
    all_dates = set()
    for d in sb_results.dates:
        all_dates.add(d)
    for d in gas_dates:
        all_dates.add(d)

    all_dates = sorted(all_dates)
    all_dates = np.array(all_dates)
    n = len(all_dates)

    # Map each component to the common grid
    sb_on_grid = np.zeros(n)
    gas_on_grid = np.zeros(n)

    # Create lookup dicts for O(1) access
    sb_lookup = {}
    for i, d in enumerate(sb_results.dates):
        sb_lookup[d] = sb_results.fcff[i]

    gas_lookup = {}
    for i, d in enumerate(gas_dates):
        gas_lookup[d] = gas_fcff[i]

    for i, d in enumerate(all_dates):
        if d in sb_lookup:
            sb_on_grid[i] = sb_lookup[d]
        if d in gas_lookup:
            gas_on_grid[i] = gas_lookup[d] * gas_ownership_share

    combined = sb_on_grid + gas_on_grid

    # Compute IRRs
    overall_irr = calc_xirr(all_dates, combined)
    overall_npv = calc_xnpv(all_dates, combined, discount_rate)

    sb_irr = calc_xirr(sb_results.dates, sb_results.fcff)
    gas_irr = calc_xirr(gas_dates, gas_fcff)

    return {
        'overall_irr': overall_irr,
        'overall_npv': overall_npv,
        'sb_irr': sb_irr,
        'gas_irr': gas_irr,
        'dates': all_dates,
        'fcff': combined,
        'sb_fcff': sb_on_grid,
        'gas_fcff': gas_on_grid,
    }
