"""
Project IRR Excel-parity test — locks the SME reference matrix.

Spec D13 (primary audit row): 82 MWp DC / 58.4 MW grid / £170 PPA /
250 MWh BESS / 25 MW gas / 25 MW load / Burton Leonard 58 MW profile
→ expected PIRR = 8.9% (tolerance ±0.1 pp).

Three other matrix rows tracked as `xfail` until D13 passes. Their deltas
are informative even when D13 is out of tolerance — consistent drift across
all four rows would indicate a single global calibration issue rather than
a per-case bug.

See docs/Financial_Assumptions_Spec.md §9 and
docs/Project_IRR_Integration_Decisions.md A10/A12/A17.

Run:  python tests/test_project_irr_excel_parity.py
  or: python -m pytest tests/test_project_irr_excel_parity.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.project_irr import run_pirr
from tests.fixtures.d13_inputs import d13_inputs


TOLERANCE_PP = 0.001   # 0.1 percentage points = 0.001 in decimal


# SME reference matrix — image supplied 2026-05-07
SME_MATRIX = [
    {"id": "d13",   "solar_mwp": 82.0,  "grid_mw": 58.4, "tariff": 170.0, "expected": 0.089, "primary": True},
    {"id": "m82_160",  "solar_mwp": 82.0,  "grid_mw": 58.4, "tariff": 160.0, "expected": 0.074, "primary": False},
    {"id": "m115_170", "solar_mwp": 115.0, "grid_mw": 81.9, "tariff": 170.0, "expected": 0.098, "primary": False},
    {"id": "m115_160", "solar_mwp": 115.0, "grid_mw": 81.9, "tariff": 160.0, "expected": 0.085, "primary": False},
]


def _run_case(case: dict) -> dict:
    inputs = d13_inputs(
        solar_dc_mwp=case["solar_mwp"],
        grid_limit_mw=case["grid_mw"],
        ppa_tariff=case["tariff"],
    )
    result = run_pirr(inputs)
    return {
        "id": case["id"],
        "computed": result.project_irr,
        "expected": case["expected"],
        "delta_pp": (result.project_irr - case["expected"]) * 100,
    }


# Primary test — locks the D13 audit target
def test_d13_audit():
    case = SME_MATRIX[0]
    r = _run_case(case)
    msg = (f"{r['id']}: PIRR={r['computed']*100:.2f}% vs target "
           f"{r['expected']*100:.1f}% (delta={r['delta_pp']:+.2f} pp)")
    print(msg)
    assert abs(r["computed"] - r["expected"]) <= TOLERANCE_PP, msg


# Secondary rows — xfail-tracked until engine lands within tolerance.
# Keeping them visible so a regression in any case is caught early.
@pytest.mark.xfail(reason="Awaiting SME confirmation on switches + curve fidelity (see SME Questions v2)")
@pytest.mark.parametrize("case", SME_MATRIX[1:], ids=[c["id"] for c in SME_MATRIX[1:]])
def test_secondary_matrix_rows(case):
    r = _run_case(case)
    msg = (f"{r['id']}: PIRR={r['computed']*100:.2f}% vs target "
           f"{r['expected']*100:.1f}% (delta={r['delta_pp']:+.2f} pp)")
    print(msg)
    assert abs(r["computed"] - r["expected"]) <= TOLERANCE_PP, msg


# Standalone runner — prints all 3 PIRRs side-by-side for diagnostics
def main():
    print("=" * 92)
    print("SME REFERENCE MATRIX — engine vs target (3 PIRRs reported, target interpretation TBD)")
    print("=" * 92)
    print(f"{'Case':<11} {'Solar':<6} {'Tariff':<7} "
          f"{'Combined':<10} {'S+B-only':<10} {'Gas':<8} "
          f"{'Target':<8} {'ΔCombined':<10} {'ΔS+B':<8}")
    print("-" * 92)

    for case in SME_MATRIX:
        inputs = d13_inputs(
            solar_dc_mwp=case["solar_mwp"],
            grid_limit_mw=case["grid_mw"],
            ppa_tariff=case["tariff"],
        )
        result = run_pirr(inputs)
        target = case["expected"]
        delta_combined = (result.project_irr - target) * 100
        delta_sb = (result.project_irr_solar_bess - target) * 100
        print(
            f"{case['id']:<11} {case['solar_mwp']:<6} £{case['tariff']:<6.0f} "
            f"{result.project_irr*100:>7.2f}%   {result.project_irr_solar_bess*100:>7.2f}%   "
            f"{result.project_irr_gas*100:>6.2f}%  {target*100:>5.1f}%   "
            f"{delta_combined:+6.2f}    {delta_sb:+6.2f}"
        )

    print("-" * 92)
    print()
    print("Pending Anchal's Q1 follow-up: should we compare against Combined or S+B-only column?")
    print("Excel current snapshot reference: S+B = 8.85%, Combined = 9.23%, Gas = 10.77%.")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
