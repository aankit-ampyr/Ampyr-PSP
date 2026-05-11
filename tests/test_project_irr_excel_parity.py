"""
Project IRR Excel-parity test — locks the D13 audit target.

Spec D13: 82 MWp DC / 58.4 MW grid / £170 PPA / 250 MWh BESS /
          25 MW gas / 25 MW load / Burton Leonard 58 MW profile
          → expected PIRR = 8.9% (tolerance ±0.1 pp).

Other three SME rows from the matrix are wired in but currently xfailed
until D13 lands. See docs/Financial_Assumptions_Spec.md §9.

Run:  python tests/test_project_irr_excel_parity.py
  or: python -m pytest tests/test_project_irr_excel_parity.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.project_irr import run_pirr
from tests.fixtures.d13_inputs import d13_inputs


D13_TARGET = 0.089
TOLERANCE_PP = 0.001   # 0.1 percentage points = 0.001 in decimal


def test_d13_audit():
    """D13 audit row: 8.9% ± 0.1 pp."""
    inputs = d13_inputs()
    result = run_pirr(inputs)
    pirr = result.project_irr

    delta_pp = (pirr - D13_TARGET) * 100
    msg = (f"D13 PIRR = {pirr*100:.2f}% (target {D13_TARGET*100:.1f}%, "
           f"delta = {delta_pp:+.2f} pp)")
    print(msg)

    assert abs(pirr - D13_TARGET) <= TOLERANCE_PP, msg


def main():
    """Standalone runner with breakdown for diagnostics during iteration."""
    inputs = d13_inputs()
    result = run_pirr(inputs)
    pirr = result.project_irr
    delta_pp = (pirr - D13_TARGET) * 100

    print("=" * 70)
    print("D13 AUDIT")
    print("=" * 70)
    print(f"  PIRR computed   = {pirr*100:.3f}%")
    print(f"  PIRR target     = {D13_TARGET*100:.1f}%")
    print(f"  Delta           = {delta_pp:+.3f} pp")
    print(f"  Tolerance       = ±{TOLERANCE_PP*100:.1f} pp")
    print(f"  Pass            = {abs(pirr - D13_TARGET) <= TOLERANCE_PP}")
    print()
    print("HEADLINES (lifetime, GBPk)")
    print(f"  Total CAPEX           = {result.total_capex:>14,.0f}")
    print(f"  Total revenue         = {result.total_revenue_lifetime:>14,.0f}")
    print(f"  Total OPEX            = {result.total_opex_lifetime:>14,.0f}")
    print(f"  Total tax paid        = {result.total_tax_lifetime:>14,.0f}")
    print()
    print("REVENUE BREAKDOWN (lifetime, GBPk)")
    for label, arr in [
        ("PPA",                  result.rev_ppa),
        ("Solar merchant",       result.rev_solar_merchant),
        ("REGO",                 result.rev_rego),
        ("11 kV embedded",       result.rev_embedded),
        ("CM T-1",               result.rev_cm_t1),
        ("CM T-4",               result.rev_cm_t4),
        ("BESS floor",           result.rev_bess_floor),
        ("Gas PPA",              result.rev_gas_ppa),
        ("Gas merchant",         result.rev_gas_merchant),
    ]:
        print(f"  {label:<22s}= {arr.sum():>14,.0f}")

    return abs(pirr - D13_TARGET) <= TOLERANCE_PP


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
