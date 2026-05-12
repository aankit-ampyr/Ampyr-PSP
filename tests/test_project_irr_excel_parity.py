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
# Anchal clarified 2026-05-12: target column = Solar+BESS-only PIRR (matches
# Excel `Equity!D175`). Combined Solar+BESS+Gas PIRR also reported when known
# (only D13 has an explicit Combined target).
SME_MATRIX = [
    {"id": "d13",    "solar_mwp": 82.0,  "grid_mw": 58.4, "tariff": 170.0,
     "sb_target": 0.089, "combined_target": 0.092, "primary": True},
    {"id": "m82_160",  "solar_mwp": 82.0,  "grid_mw": 58.4, "tariff": 160.0,
     "sb_target": 0.074, "combined_target": None, "primary": False},
    {"id": "m115_170", "solar_mwp": 115.0, "grid_mw": 81.9, "tariff": 170.0,
     "sb_target": 0.098, "combined_target": None, "primary": False},
    {"id": "m115_160", "solar_mwp": 115.0, "grid_mw": 81.9, "tariff": 160.0,
     "sb_target": 0.085, "combined_target": None, "primary": False},
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
        "combined": result.project_irr,
        "sb_only": result.project_irr_solar_bess,
        "sb_target": case["sb_target"],
        "combined_target": case.get("combined_target"),
        "sb_delta_pp": (result.project_irr_solar_bess - case["sb_target"]) * 100,
        "combined_delta_pp": ((result.project_irr - case["combined_target"]) * 100
                              if case.get("combined_target") is not None else None),
    }


# Primary test — D13 must be within tolerance on the S+B-only target.
# (Combined target also checked for D13, but S+B is the headline.)
def test_d13_audit_solar_bess():
    case = SME_MATRIX[0]
    r = _run_case(case)
    msg = (f"{r['id']} S+B-only: PIRR={r['sb_only']*100:.2f}% vs target "
           f"{r['sb_target']*100:.1f}% (delta={r['sb_delta_pp']:+.2f} pp)")
    print(msg)
    assert abs(r["sb_only"] - r["sb_target"]) <= TOLERANCE_PP, msg


def test_d13_audit_combined():
    case = SME_MATRIX[0]
    r = _run_case(case)
    msg = (f"{r['id']} Combined: PIRR={r['combined']*100:.2f}% vs target "
           f"{r['combined_target']*100:.1f}% (delta={r['combined_delta_pp']:+.2f} pp)")
    print(msg)
    assert abs(r["combined"] - r["combined_target"]) <= TOLERANCE_PP, msg


# Secondary rows — xfail-tracked until D13 passes both targets.
@pytest.mark.xfail(reason="Awaiting calibration — see decisions log A19/A20 for sensitivity gap")
@pytest.mark.parametrize("case", SME_MATRIX[1:], ids=[c["id"] for c in SME_MATRIX[1:]])
def test_secondary_matrix_rows(case):
    r = _run_case(case)
    msg = (f"{r['id']} S+B: {r['sb_only']*100:.2f}% vs target "
           f"{r['sb_target']*100:.1f}% (delta={r['sb_delta_pp']:+.2f} pp)")
    print(msg)
    assert abs(r["sb_only"] - r["sb_target"]) <= TOLERANCE_PP, msg


# Standalone runner — prints all 3 PIRRs against both S+B and Combined targets
def main():
    print("=" * 100)
    print("SME REFERENCE MATRIX — engine vs both targets")
    print("Per Anchal 2026-05-12: target column = S+B-only PIRR. Combined target also given for D13.")
    print("=" * 100)
    print(f"{'Case':<11} {'Tariff':<7} "
          f"{'S+B Eng':<9} {'S+B Tgt':<9} {'ΔS+B':<8}  "
          f"{'Comb Eng':<10} {'Comb Tgt':<10} {'ΔComb':<8} {'Gas Eng':<8}")
    print("-" * 100)

    for case in SME_MATRIX:
        r = _run_case(case)
        comb_tgt_str = (f"{r['combined_target']*100:>5.1f}%"
                        if r['combined_target'] is not None else "  -")
        comb_delta_str = (f"{r['combined_delta_pp']:+5.2f}"
                          if r['combined_delta_pp'] is not None else "  -")
        # Gas IRR
        inputs = d13_inputs(
            solar_dc_mwp=case["solar_mwp"],
            grid_limit_mw=case["grid_mw"],
            ppa_tariff=case["tariff"],
        )
        gas_irr = run_pirr(inputs).project_irr_gas
        gas_str = f"{gas_irr*100:>6.2f}%" if not (gas_irr != gas_irr) else "  nan"

        print(
            f"{case['id']:<11} £{case['tariff']:<6.0f} "
            f"{r['sb_only']*100:>6.2f}%   {r['sb_target']*100:>5.1f}%    "
            f"{r['sb_delta_pp']:+6.2f}    "
            f"{r['combined']*100:>6.2f}%    {comb_tgt_str}     "
            f"{comb_delta_str}    {gas_str}"
        )

    print("-" * 100)
    print()
    print("Excel reference (current snapshot, 3.8h BESS):")
    print("  S+B-only = 8.85% (Equity!D175) | Combined = 9.23% (Consol Cash Flows!B9) | Gas = 10.77% (Cash Flows-Gas!D84)")
    print()
    print("D13 SME targets (4h BESS): S+B = 8.9% | Combined = 9.2%")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
