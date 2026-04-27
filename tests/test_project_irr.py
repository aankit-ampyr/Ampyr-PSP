"""
Project IRR Test Suite — 4 test cases from Test/Test runs.xlsx

Validates the consolidated (Solar+BESS+Gas) Project IRR against known
values from the Off-Grid Solution v8.xlsm financial model.

Test cases:
  1. 82MW solar profile, tariff 170 → expected IRR 9.8%
  2. 82MW solar profile, tariff 160 → expected IRR 8.5%
  3. 58MW solar profile, tariff 170 → expected IRR 8.9%
  4. 58MW solar profile, tariff 160 → expected IRR 7.4%

Run:  python tests/test_project_irr.py
  or: python -m pytest tests/test_project_irr.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
import numpy as np

from src.excel_reader import read_model_params
from src.dispatch_energy import compute_monthly_energy
from src.gas_model import GasInputs, run_gas_model, gas_inputs_from_params
from src.financial_model import (
    TariffModelInputs, FinancialResults,
    run_tariff_model, tariff_inputs_from_params,
)
from src.consolidated_model import run_consolidated_irr


# =========================================================================
# CONFIGURATION
# =========================================================================

EXCEL_PATH = Path("Financial Model/Off-Grid Solution v8.xlsm")
SOLAR_82MW = Path("Test/Burton Leonard_Project_VCN_HourlyRes_82MW.CSV")
SOLAR_58MW = Path("Test/Burton Leonard_Project_VCN_HourlyRes_58MW.CSV")

TOLERANCE = 0.005  # +/-0.5% absolute

TEST_CASES = [
    {"name": "Test 1: 82MW, tariff 170", "solar": SOLAR_82MW, "pv_mwp": 82, "tariff": 170, "expected_irr": 0.098},
    {"name": "Test 2: 82MW, tariff 160", "solar": SOLAR_82MW, "pv_mwp": 82, "tariff": 160, "expected_irr": 0.085},
    {"name": "Test 3: 58MW, tariff 170", "solar": SOLAR_58MW, "pv_mwp": 82, "tariff": 170, "expected_irr": 0.089},
    {"name": "Test 4: 58MW, tariff 160", "solar": SOLAR_58MW, "pv_mwp": 82, "tariff": 160, "expected_irr": 0.074},
]


# =========================================================================
# CORE TEST RUNNER
# =========================================================================

def run_single_test(params: dict, test_case: dict) -> dict:
    """
    Run a single Project IRR test case.

    Args:
        params: dict from read_model_params()
        test_case: dict with solar, pv_mwp, tariff, expected_irr

    Returns: dict with computed IRR, expected, delta, pass/fail
    """
    overall = params['overall']
    sb = params['solar_bess']
    gas_p = params['gas']
    tax = params['tax']
    debt = params['debt']
    seasonality = params['seasonality']
    merchant_prices = params['merchant_prices']

    # Override tariff for this test case
    overall_copy = dict(overall)
    overall_copy['tariff_gbp_mwh'] = test_case['tariff']

    # The gas PPA tariff also matches the overall tariff
    gas_p_copy = dict(gas_p)

    # Step 1: Dispatch — compute monthly energy splits from solar profile
    bess_mwh = sb['bess_capacity_mw'] * sb['bess_duration_hrs']
    energy = compute_monthly_energy(
        solar_profile_path=test_case['solar'],
        load_mw=overall['base_load_mw'],
        bess_mwh=bess_mwh,
        bess_mw=sb['bess_capacity_mw'],
    )
    monthly = energy['monthly']

    # Step 2: Solar+BESS model
    sb_inputs = tariff_inputs_from_params(
        sb, overall_copy, tax, debt, seasonality, merchant_prices
    )
    # Override PV capacity for CAPEX if test specifies differently
    if test_case.get('pv_mwp'):
        sb_inputs.solar_capacity_mwp = test_case['pv_mwp']

    sb_results = run_tariff_model(
        sb_inputs,
        monthly['solar_bess_to_dc'],
        monthly['solar_surplus'],
        monthly['solar_gen'],
    )

    # Step 3: Gas model
    gas_inputs = gas_inputs_from_params(gas_p_copy, overall_copy, tax)
    gas_results = run_gas_model(
        gas_inputs,
        monthly['gas_energy'],
        gas_energy_growth_rate=sb['degradation_pct'],  # as solar degrades, gas increases
    )

    # Step 4: Consolidated IRR
    consol = run_consolidated_irr(
        sb_results,
        gas_results.dates,
        gas_results.fcff,
        discount_rate=sb.get('discount_rate', 0.065),
        gas_ownership_share=0.58,  # Calibrated: Consol Cash Flows uses ~58% of Gas FCFF
    )

    computed = consol['overall_irr']
    expected = test_case['expected_irr']
    delta = computed - expected if not np.isnan(computed) else np.nan
    passed = abs(delta) <= TOLERANCE if not np.isnan(delta) else False

    return {
        'name': test_case['name'],
        'computed_irr': computed,
        'expected_irr': expected,
        'delta': delta,
        'passed': passed,
        'sb_irr': consol['sb_irr'],
        'gas_irr': consol['gas_irr'],
        'green_pct': energy['green_pct'],
        'gas_pct': energy['gas_pct'],
        'sb_capex': sb_results.total_capex,
        'gas_capex': gas_results.total_capex,
        'sb_revenue': sb_results.total_revenue_lifetime,
        'gas_revenue': gas_results.total_revenue,
    }


# =========================================================================
# PYTEST-COMPATIBLE TESTS
# =========================================================================

_params_cache = None


def _get_params():
    global _params_cache
    if _params_cache is None:
        _params_cache = read_model_params(EXCEL_PATH)
    return _params_cache


def test_case_1():
    result = run_single_test(_get_params(), TEST_CASES[0])
    _print_result(result)
    assert result['passed'], \
        f"{result['name']}: {result['computed_irr']*100:.2f}% vs {result['expected_irr']*100:.1f}% (delta={result['delta']*100:+.2f}%)"


def test_case_2():
    result = run_single_test(_get_params(), TEST_CASES[1])
    _print_result(result)
    assert result['passed'], \
        f"{result['name']}: {result['computed_irr']*100:.2f}% vs {result['expected_irr']*100:.1f}% (delta={result['delta']*100:+.2f}%)"


def test_case_3():
    result = run_single_test(_get_params(), TEST_CASES[2])
    _print_result(result)
    assert result['passed'], \
        f"{result['name']}: {result['computed_irr']*100:.2f}% vs {result['expected_irr']*100:.1f}% (delta={result['delta']*100:+.2f}%)"


def test_case_4():
    result = run_single_test(_get_params(), TEST_CASES[3])
    _print_result(result)
    assert result['passed'], \
        f"{result['name']}: {result['computed_irr']*100:.2f}% vs {result['expected_irr']*100:.1f}% (delta={result['delta']*100:+.2f}%)"


def _print_result(r):
    status = "PASS" if r['passed'] else "FAIL"
    irr_str = f"{r['computed_irr']*100:.2f}%" if not np.isnan(r['computed_irr']) else "NaN"
    print(f"  {status}: {r['name']}")
    print(f"    Overall IRR: {irr_str} (expected {r['expected_irr']*100:.1f}%, delta={r['delta']*100:+.2f}%)")
    print(f"    Solar+BESS IRR: {r['sb_irr']*100:.2f}%, Gas IRR: {r['gas_irr']*100:.2f}%")
    print(f"    Green: {r['green_pct']*100:.1f}%, Gas: {r['gas_pct']*100:.1f}%")
    print(f"    S+B CAPEX: {r['sb_capex']:,.0f} GBPk, Gas CAPEX: {r['gas_capex']:,.0f} GBPk")


# =========================================================================
# STANDALONE RUNNER
# =========================================================================

def main():
    print("=" * 70)
    print("PROJECT IRR TEST SUITE")
    print(f"Tolerance: +/-{TOLERANCE*100:.1f}%")
    print("=" * 70)

    print("\nLoading parameters from Excel...")
    params = read_model_params(EXCEL_PATH)
    print(f"  PV Capacity: {params['solar_bess']['solar_capacity_mwp']} MWp")
    print(f"  BESS: {params['solar_bess']['bess_capacity_mw']} MW / {params['solar_bess']['bess_duration_hrs']}h")
    print(f"  Gas: {params['gas']['capacity_mw']:.1f} MW")
    print(f"  Base tariff: {params['overall']['tariff_gbp_mwh']} GBP/MWh")

    passed = 0
    failed = 0
    results = []

    for tc in TEST_CASES:
        print(f"\n--- {tc['name']} ---")
        print(f"  Solar profile: {tc['solar']}")
        print(f"  Tariff: {tc['tariff']} GBP/MWh")

        try:
            r = run_single_test(params, tc)
            results.append(r)
            _print_result(r)

            if r['passed']:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(TEST_CASES)}")
    print(f"{'=' * 70}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
