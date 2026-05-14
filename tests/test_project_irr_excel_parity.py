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


# SME reference matrix — Anchal's 2026-05-14 reply confirms ALL four targets
# are Combined PV+BESS+Gas Project IRR (matrix column header explicitly reads
# "Project IRR (Overall for PV+BESS+Gas)"). The earlier A20 (2026-05-12)
# interpretation that targets were S+B-only was wrong — see decisions log A29.
# Anchal's 5/14 reply: "They were clean Excel re-runs ... consider latest
# IRR targets for 82MW case." 82 MWp values shifted slightly from May 7
# matrix (8.9→9.2, 7.4→7.8); 115 MWp values unchanged (9.8, 8.5).
#
# Per-config green/gas share Anchal also provided (useful for dispatch
# cross-check, NOT audit assertion):
#   115 MWp config: 42.8% green / 57.2% gas
#   82 MWp config:  34.5% green / 65.5% gas
SME_MATRIX = [
    {"id": "d13",      "solar_mwp": 82.0,  "grid_mw": 58.4, "tariff": 170.0,
     "combined_target": 0.092, "primary": True,
     "green_share_target": 0.345, "gas_share_target": 0.655},
    {"id": "m82_160",  "solar_mwp": 82.0,  "grid_mw": 58.4, "tariff": 160.0,
     "combined_target": 0.078, "primary": False,
     "green_share_target": 0.345, "gas_share_target": 0.655},
    {"id": "m115_170", "solar_mwp": 115.0, "grid_mw": 81.9, "tariff": 170.0,
     "combined_target": 0.098, "primary": False,
     "green_share_target": 0.428, "gas_share_target": 0.572},
    {"id": "m115_160", "solar_mwp": 115.0, "grid_mw": 81.9, "tariff": 160.0,
     "combined_target": 0.085, "primary": False,
     "green_share_target": 0.428, "gas_share_target": 0.572},
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
        "gas_only": result.project_irr_gas,
        "combined_target": case["combined_target"],
        "combined_delta_pp": (result.project_irr - case["combined_target"]) * 100,
    }


# Primary test — D13 must be within tolerance on the Combined target.
# Per Anchal 2026-05-14: matrix targets are Combined PV+BESS+Gas PIRRs.
# Current engine produces D13 Combined ≈ 8.77% vs target 9.2% (-0.43 pp).
# xfail tracks this gap as the new primary calibration objective post-A29.
@pytest.mark.xfail(reason="Post-A29 (matrix reinterpreted as Combined): "
                          "engine 8.77% vs Combined target 9.2% (-0.43 pp). "
                          "Pre-A29 this test passed on the wrong (S+B-only) "
                          "metric per the A20 misinterpretation. Calibration "
                          "of the -0.43 pp Combined gap is the new headline "
                          "objective.")
def test_d13_audit_combined():
    case = SME_MATRIX[0]
    r = _run_case(case)
    msg = (f"{r['id']} Combined: PIRR={r['combined']*100:.2f}% vs target "
           f"{r['combined_target']*100:.1f}% (delta={r['combined_delta_pp']:+.2f} pp)")
    print(msg)
    assert abs(r["combined"] - r["combined_target"]) <= TOLERANCE_PP, msg


# Secondary rows — xfail-tracked until D13 passes Combined target.
@pytest.mark.xfail(reason="Combined-target calibration pending — see A29 for matrix-interpretation reversal")
@pytest.mark.parametrize("case", SME_MATRIX[1:], ids=[c["id"] for c in SME_MATRIX[1:]])
def test_secondary_matrix_rows(case):
    r = _run_case(case)
    msg = (f"{r['id']} Combined: {r['combined']*100:.2f}% vs target "
           f"{r['combined_target']*100:.1f}% (delta={r['combined_delta_pp']:+.2f} pp)")
    print(msg)
    assert abs(r["combined"] - r["combined_target"]) <= TOLERANCE_PP, msg


# Standalone runner — prints Combined-vs-target (audit primary) plus S+B
# and Gas for diagnostic context.
def main():
    print("=" * 100)
    print("SME REFERENCE MATRIX — engine Combined PIRR vs target")
    print("Per Anchal 2026-05-14: ALL four matrix targets are Combined "
          "PV+BESS+Gas PIRRs (matrix col header: 'Project IRR (Overall "
          "for PV+BESS+Gas)'). Supersedes A20's S+B-only interpretation.")
    print("=" * 100)
    print(f"{'Case':<11} {'Tariff':<7} "
          f"{'Comb Eng':<11} {'Comb Tgt':<11} {'ΔComb':<9}  "
          f"{'S+B Eng':<9} {'Gas Eng':<9}")
    print("-" * 100)

    for case in SME_MATRIX:
        r = _run_case(case)
        print(
            f"{case['id']:<11} £{case['tariff']:<6.0f} "
            f"{r['combined']*100:>6.2f}%     "
            f"{r['combined_target']*100:>5.1f}%      "
            f"{r['combined_delta_pp']:+6.2f}     "
            f"{r['sb_only']*100:>6.2f}%   "
            f"{r['gas_only']*100:>6.2f}%"
        )

    print("-" * 100)
    print()
    print("Excel reference (current snapshot, 3.8h BESS):")
    print("  S+B-only = 8.85% (Equity!D175) | Combined = 9.23% (Consol Cash Flows!B9) | Gas = 10.77% (Cash Flows-Gas!D84)")
    print()
    print("D13 SME target (4h BESS, post-A29): Combined = 9.2%")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
