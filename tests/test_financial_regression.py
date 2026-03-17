"""
Regression tests for financial_model.py (Phase A1 — Core FCFF Chain)

Run:  python tests/test_financial_regression.py
  or: python -m pytest tests/test_financial_regression.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date
import numpy as np
from src.financial_model import (
    FinancialInputs, FinancialResults,
    run_financial_model, calc_xirr, calc_xnpv,
    build_timeline, calc_revenue, calc_opex, calc_capex,
    calc_depreciation, calc_ungeared_tax, calc_nwc,
)


# =============================================================================
# TIMELINE TESTS
# =============================================================================

def test_timeline_total_months():
    inputs = FinancialInputs()
    dates, is_c, is_o = build_timeline(inputs)
    assert len(dates) == 456, f"Expected 456, got {len(dates)}"
    print("PASS: test_timeline_total_months")


def test_timeline_dates():
    inputs = FinancialInputs()
    dates, _, _ = build_timeline(inputs)
    assert dates[0] == date(2024, 7, 1)
    assert dates[-1] == date(2062, 6, 1)
    assert all(d.day == 1 for d in dates)
    print("PASS: test_timeline_dates")


def test_timeline_construction_count():
    inputs = FinancialInputs()
    _, is_c, _ = build_timeline(inputs)
    assert sum(is_c) == 18, f"Expected 18 construction months, got {sum(is_c)}"
    print("PASS: test_timeline_construction_count")


def test_timeline_operations_count():
    inputs = FinancialInputs()
    _, _, is_o = build_timeline(inputs)
    assert sum(is_o) == 420, f"Expected 420 ops months, got {sum(is_o)}"
    print("PASS: test_timeline_operations_count")


def test_timeline_no_overlap():
    inputs = FinancialInputs()
    _, is_c, is_o = build_timeline(inputs)
    assert not any(is_c & is_o), "Construction and operations overlap"
    print("PASS: test_timeline_no_overlap")


# =============================================================================
# UNIT CONVERSION TESTS
# =============================================================================

def test_solar_opex_monthly():
    """UC-1: Solar OPEX monthly = sum of rates × MWp / 12"""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    first_ops = np.where(results.opex != 0)[0][0]
    # Expected: (5.48+1.5+0.5+0+1+1+0+2.02+0+3.2+1.5) * 82 / 12 = 109.37
    expected = (5.48 + 1.5 + 0.5 + 0 + 1.0 + 1.0 + 0 + 2.02 + 0 + 3.2 + 1.5) * 82 / 12
    actual = abs(results.solar_opex[first_ops])
    assert abs(actual - expected) < 0.5, f"Solar OPEX: expected {expected:.2f}, got {actual:.2f}"
    print(f"PASS: test_solar_opex_monthly ({actual:.2f} ~= {expected:.2f})")


def test_bess_opex_monthly():
    """UC-2: BESS OPEX monthly = rate × MW / 12"""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    first_ops = np.where(results.opex != 0)[0][0]
    expected = 7.06 * 62.5 / 12
    actual = abs(results.bess_opex[first_ops])
    assert abs(actual - expected) < 0.5, f"BESS OPEX: expected {expected:.2f}, got {actual:.2f}"
    print(f"PASS: test_bess_opex_monthly ({actual:.2f} ~= {expected:.2f})")


def test_total_capex():
    """UC-3: Total CAPEX = sum items × MWp × (1 + contingency)"""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    items_sum = (400 + 30 + 15 + 0 + 5 + 0 + 0 + 2 + 0 + 2 + 0 + 0 +
                 0 + 0 + 80 + 0 + 3 + 0 + 0 + 0 + 0)
    expected = items_sum * 82 * 1.01
    assert abs(results.total_capex - expected) < 10, \
        f"CAPEX: expected {expected:.0f}, got {results.total_capex:.0f}"
    print(f"PASS: test_total_capex ({results.total_capex:.0f} ~= {expected:.0f})")


def test_capex_phasing():
    """UC-4: CAPEX phased evenly over construction months"""
    inputs = FinancialInputs()
    dates, is_c, _ = build_timeline(inputs)
    capex = calc_capex(inputs, dates, is_c)
    constr_values = capex[is_c]
    assert len(constr_values) == 18
    assert all(v < 0 for v in constr_values), "CAPEX should be negative"
    assert np.allclose(constr_values, constr_values[0]), "CAPEX should be evenly phased"
    print("PASS: test_capex_phasing")


def test_depreciation_total():
    """DP-3: Total depreciation ≈ total CAPEX"""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    depr_total = results.depreciation.sum()
    assert abs(depr_total - results.total_capex) < 1.0, \
        f"Depr total {depr_total:.0f} != CAPEX {results.total_capex:.0f}"
    print(f"PASS: test_depreciation_total ({depr_total:.0f} ~= {results.total_capex:.0f})")


# =============================================================================
# REVENUE TESTS
# =============================================================================

def test_revenue_zero_during_construction():
    inputs = FinancialInputs()
    dates, is_c, _ = build_timeline(inputs)
    rev, _, _ = calc_revenue(inputs, dates, np.zeros(len(dates), dtype=bool))
    # No ops → no revenue
    assert all(rev == 0), "Revenue should be zero when no operations"
    print("PASS: test_revenue_zero_during_construction")


def test_degradation_year2():
    """RV-2: Year 2 solar revenue should be ~0.3% less than year 1 (degradation only)"""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    # Use solar_revenue to isolate degradation effect from BESS/CM tenor changes
    ops_mask = results.solar_revenue > 0
    ops_rev = results.solar_revenue[ops_mask]
    # Compare month 1 vs month 13 (same calendar month in year 2)
    if len(ops_rev) > 13:
        ratio = ops_rev[12] / ops_rev[0]
        # Expected: degradation (0.997) * indexation (1.025^(1/12))^12 ~ 0.997 * 1.025
        expected_ratio = (1 - 0.003) * (1 + inputs.indexation_rate / 100)
        assert abs(ratio - expected_ratio) < 0.02, \
            f"Degradation ratio: {ratio:.4f} vs expected {expected_ratio:.4f}"
    print("PASS: test_degradation_year2")


def test_no_bess_zero_bess_revenue():
    inputs = FinancialInputs(bess_switch=0)
    results = run_financial_model(inputs)
    assert all(results.bess_revenue == 0), "BESS revenue should be zero"
    assert all(results.bess_opex == 0), "BESS OPEX should be zero"
    print("PASS: test_no_bess_zero_bess_revenue")


# =============================================================================
# TAX TESTS
# =============================================================================

def test_tax_only_in_taxation_month():
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    for i in range(len(results.dates)):
        if results.tax[i] != 0:
            assert results.dates[i].month == inputs.taxation_month, \
                f"Tax in month {results.dates[i].month}, expected {inputs.taxation_month}"
    print("PASS: test_tax_only_in_taxation_month")


def test_tax_sign_convention():
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    assert all(results.tax <= 0), "Tax should be ≤ 0 (cash outflow)"
    print("PASS: test_tax_sign_convention")


def test_tax_zero_rates():
    inputs = FinancialInputs(corp_tax_rate_low=0, corp_tax_rate_high=0)
    results = run_financial_model(inputs)
    assert all(results.tax == 0), "Tax should be zero with zero rates"
    print("PASS: test_tax_zero_rates")


# =============================================================================
# FCFF IDENTITY TESTS
# =============================================================================

def test_fcff_identity():
    """FF-1: FCFF = Revenue + OPEX + NWC + CAPEX + Tax"""
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    expected = results.revenue + results.opex + results.nwc + results.capex + results.tax
    assert np.allclose(results.fcff, expected, atol=0.01), "FCFF identity failed"
    print("PASS: test_fcff_identity")


def test_fcff_construction_is_capex():
    """FF-2: During construction, FCFF = CAPEX only"""
    inputs = FinancialInputs()
    dates, is_c, _ = build_timeline(inputs)
    results = run_financial_model(inputs)
    for i in range(len(dates)):
        if is_c[i]:
            assert abs(results.fcff[i] - results.capex[i]) < 0.01, \
                f"Construction FCFF != CAPEX at {dates[i]}"
    print("PASS: test_fcff_construction_is_capex")


# =============================================================================
# XIRR TESTS
# =============================================================================

def test_xirr_known_answer():
    dates = np.array([date(2025, 1, 1), date(2026, 1, 1),
                      date(2027, 1, 1), date(2028, 1, 1), date(2029, 1, 1)])
    cfs = np.array([-1000.0, 300.0, 300.0, 300.0, 300.0])
    irr = calc_xirr(dates, cfs)
    assert abs(irr - 0.0771) < 0.005, f"Expected ~7.71%, got {irr*100:.2f}%"
    print(f"PASS: test_xirr_known_answer ({irr*100:.2f}%)")


def test_xnpv_at_irr_is_zero():
    inputs = FinancialInputs()
    results = run_financial_model(inputs)
    if not np.isnan(results.project_irr):
        npv_at_irr = calc_xnpv(results.dates, results.fcff, results.project_irr)
        assert abs(npv_at_irr) < 1.0, f"NPV at IRR = {npv_at_irr:.4f}, should be ~0"
    print("PASS: test_xnpv_at_irr_is_zero")


def test_xirr_no_cashflows():
    dates = np.array([date(2025, 1, 1), date(2026, 1, 1)])
    cfs = np.array([0.0, 0.0])
    irr = calc_xirr(dates, cfs)
    assert np.isnan(irr), "XIRR of zero cashflows should be NaN"
    print("PASS: test_xirr_no_cashflows")


# =============================================================================
# SENSITIVITY TESTS
# =============================================================================

def test_higher_ppa_higher_irr():
    r1 = run_financial_model(FinancialInputs(ppa_price_gbp_mwh=40))
    r2 = run_financial_model(FinancialInputs(ppa_price_gbp_mwh=60))
    assert r2.project_irr > r1.project_irr, \
        f"PPA 60 IRR ({r2.project_irr:.4f}) should > PPA 40 ({r1.project_irr:.4f})"
    print(f"PASS: test_higher_ppa_higher_irr ({r1.project_irr*100:.2f}% -> {r2.project_irr*100:.2f}%)")


def test_lower_capex_higher_irr():
    r1 = run_financial_model(FinancialInputs(capex_epc=400))
    r2 = run_financial_model(FinancialInputs(capex_epc=350))
    assert r2.project_irr > r1.project_irr, \
        f"EPC 350 IRR ({r2.project_irr:.4f}) should > EPC 400 ({r1.project_irr:.4f})"
    print(f"PASS: test_lower_capex_higher_irr ({r1.project_irr*100:.2f}% -> {r2.project_irr*100:.2f}%)")


def test_longer_life_higher_irr():
    r1 = run_financial_model(FinancialInputs(project_life_years=20))
    r2 = run_financial_model(FinancialInputs(project_life_years=35))
    assert r2.project_irr > r1.project_irr, \
        f"35yr IRR ({r2.project_irr:.4f}) should > 20yr ({r1.project_irr:.4f})"
    print(f"PASS: test_longer_life_higher_irr ({r1.project_irr*100:.2f}% -> {r2.project_irr*100:.2f}%)")


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

def test_zero_solar_capacity():
    inputs = FinancialInputs(solar_capacity_mwp=0, bess_switch=0)
    results = run_financial_model(inputs)
    assert results.total_capex == 0
    assert results.total_revenue_lifetime == 0
    print("PASS: test_zero_solar_capacity")


def test_short_project_life():
    inputs = FinancialInputs(project_life_years=1)
    results = run_financial_model(inputs)
    assert not np.isnan(results.project_irr) or results.project_irr < 0
    print("PASS: test_short_project_life")


def test_long_project_life():
    inputs = FinancialInputs(project_life_years=50)
    results = run_financial_model(inputs)
    assert len(results.dates) == 636  # 36 pre-ops + 600 ops
    print("PASS: test_long_project_life")


def test_negative_irr():
    """Very high CAPEX should give negative IRR"""
    inputs = FinancialInputs(capex_epc=2000)
    results = run_financial_model(inputs)
    assert results.project_irr < 0, f"Expected negative IRR, got {results.project_irr}"
    print(f"PASS: test_negative_irr ({results.project_irr*100:.2f}%)")


# =============================================================================
# PERFORMANCE TEST
# =============================================================================

def test_performance():
    import time
    start = time.time()
    for _ in range(10):
        run_financial_model(FinancialInputs())
    elapsed = time.time() - start
    per_run = elapsed / 10
    assert per_run < 0.5, f"Too slow: {per_run:.3f}s per run"
    print(f"PASS: test_performance ({per_run*1000:.1f}ms per run)")


# =============================================================================
# RUNNER
# =============================================================================

ALL_TESTS = [
    # Timeline
    test_timeline_total_months,
    test_timeline_dates,
    test_timeline_construction_count,
    test_timeline_operations_count,
    test_timeline_no_overlap,
    # Unit conversion
    test_solar_opex_monthly,
    test_bess_opex_monthly,
    test_total_capex,
    test_capex_phasing,
    test_depreciation_total,
    # Revenue
    test_revenue_zero_during_construction,
    test_degradation_year2,
    test_no_bess_zero_bess_revenue,
    # Tax
    test_tax_only_in_taxation_month,
    test_tax_sign_convention,
    test_tax_zero_rates,
    # FCFF
    test_fcff_identity,
    test_fcff_construction_is_capex,
    # XIRR
    test_xirr_known_answer,
    test_xnpv_at_irr_is_zero,
    test_xirr_no_cashflows,
    # Sensitivity
    test_higher_ppa_higher_irr,
    test_lower_capex_higher_irr,
    test_longer_life_higher_irr,
    # Edge cases
    test_zero_solar_capacity,
    test_short_project_life,
    test_long_project_life,
    test_negative_irr,
    # Performance
    test_performance,
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    failures = []

    for t in ALL_TESTS:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
            failures.append(t.__name__)

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(ALL_TESTS)}")
    if failures:
        print(f"Failures: {', '.join(failures)}")
    print(f"{'='*60}")
