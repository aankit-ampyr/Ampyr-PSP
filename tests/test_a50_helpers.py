"""Unit tests for the A50b raw-curve pipeline helpers.

Covers:
  - `_apply_inflation_to_real_curve`: real → nominal conversion mechanics
  - `_select_raw_curve`: Baringa / Aurora / average selector logic

Both helpers are pure functions in `src/project_irr.py` — testable without any
Streamlit or wizard-state context.

Also verifies the bundled Baringa + Aurora defaults loaded cleanly from
`src/_baringa_aurora_defaults.py` and have plausible shape.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.project_irr import (
    _apply_inflation_to_real_curve,
    _select_raw_curve,
    _DEFAULT_BARINGA_CURVE_REAL,
    _DEFAULT_AURORA_CURVE_REAL,
    _DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR,
)


# =============================================================================
# _apply_inflation_to_real_curve
# =============================================================================

def test_apply_inflation_identity_at_base_year():
    """Anchor: nominal(base_year) == real(base_year). All months in the base
    year should equal the input value (factor = 1.0)."""
    real = {(2024, 1): 100.0, (2024, 6): 100.0, (2024, 12): 100.0}
    out = _apply_inflation_to_real_curve(real, {2025: 0.05}, 0.020, base_year=2024)
    for k, v in real.items():
        assert abs(out[k] - v) < 1e-9, f"Identity broken at {k}: {out[k]} vs {v}"


def test_apply_inflation_compounds_forward():
    """Year-by-year compounding: real=100 at base + 5% in 2025 + 4% in 2026
    → nominal 100, 105, 109.20."""
    real = {(2024, 6): 100.0, (2025, 6): 100.0, (2026, 6): 100.0}
    out = _apply_inflation_to_real_curve(
        real, {2025: 0.05, 2026: 0.04}, 0.020, base_year=2024,
    )
    assert abs(out[(2024, 6)] - 100.00) < 1e-6
    assert abs(out[(2025, 6)] - 105.00) < 1e-6
    assert abs(out[(2026, 6)] - 109.20) < 1e-6


def test_apply_inflation_uses_steady_state_outside_curve():
    """Years past the curve fall back to steady-state."""
    real = {(2024, 1): 100.0, (2030, 1): 100.0}
    # Curve covers 2025-2026 only; 2027-2030 → steady-state 2% each
    out = _apply_inflation_to_real_curve(
        real, {2025: 0.05, 2026: 0.04}, 0.020, base_year=2024,
    )
    # 2030 factor: 1 * 1.05 * 1.04 * 1.02 * 1.02 * 1.02 * 1.02
    expected_factor = 1.05 * 1.04 * (1.02 ** 4)
    assert abs(out[(2030, 1)] - 100.0 * expected_factor) < 1e-6


def test_apply_inflation_empty_curve_returns_empty():
    """Empty real curve → empty result."""
    assert _apply_inflation_to_real_curve({}, {2025: 0.02}, 0.020, 2024) == {}


def test_apply_inflation_with_empty_cpi_uses_steady_state():
    """No curve data → every year uses steady-state."""
    real = {(2024, 1): 100.0, (2026, 1): 100.0}
    out = _apply_inflation_to_real_curve(real, {}, 0.025, base_year=2024)
    # 2026 = 100 * 1.025^2 = 105.0625
    assert abs(out[(2026, 1)] - 105.0625) < 1e-6


# =============================================================================
# _select_raw_curve
# =============================================================================

def _synthetic_curve(value: float) -> dict:
    """Build a tiny 3-key synthetic curve for blending tests."""
    return {(2030, 1): value, (2030, 2): value, (2030, 3): value}


def test_select_baringa_returns_baringa():
    b = _synthetic_curve(100.0)
    a = _synthetic_curve(120.0)
    out = _select_raw_curve(b, a, 'baringa')
    assert out == b


def test_select_aurora_returns_aurora():
    b = _synthetic_curve(100.0)
    a = _synthetic_curve(120.0)
    out = _select_raw_curve(b, a, 'aurora')
    assert out == a


def test_select_average_is_elementwise_mean():
    b = _synthetic_curve(100.0)
    a = _synthetic_curve(120.0)
    out = _select_raw_curve(b, a, 'average')
    expected = {(2030, 1): 110.0, (2030, 2): 110.0, (2030, 3): 110.0}
    assert out == expected


def test_select_baringa_falls_back_to_aurora_when_baringa_none():
    a = _synthetic_curve(120.0)
    assert _select_raw_curve(None, a, 'baringa') == a


def test_select_aurora_falls_back_to_baringa_when_aurora_none():
    b = _synthetic_curve(100.0)
    assert _select_raw_curve(b, None, 'aurora') == b


def test_select_average_with_one_missing_uses_the_other():
    """Average with only Baringa → returns Baringa as-is (no averaging)."""
    b = _synthetic_curve(100.0)
    assert _select_raw_curve(b, None, 'average') == b
    a = _synthetic_curve(120.0)
    assert _select_raw_curve(None, a, 'average') == a


def test_select_unknown_selector_returns_none():
    b = _synthetic_curve(100.0)
    a = _synthetic_curve(120.0)
    assert _select_raw_curve(b, a, 'nonsense') is None


# =============================================================================
# Bundled defaults sanity (lightweight — full Excel-fidelity round-trip is CP4)
# =============================================================================

def test_default_baringa_curve_loaded():
    assert len(_DEFAULT_BARINGA_CURVE_REAL) > 400, (
        f"Baringa default has only {len(_DEFAULT_BARINGA_CURVE_REAL)} entries — "
        "expected ~500. Re-run extraction from Excel."
    )
    # Keys are (year, month) tuples; values are positive floats
    sample_key = next(iter(_DEFAULT_BARINGA_CURVE_REAL.keys()))
    assert isinstance(sample_key, tuple) and len(sample_key) == 2
    sample_val = _DEFAULT_BARINGA_CURVE_REAL[sample_key]
    assert isinstance(sample_val, float) and sample_val > 0


def test_default_aurora_curve_loaded():
    assert len(_DEFAULT_AURORA_CURVE_REAL) > 400, (
        f"Aurora default has only {len(_DEFAULT_AURORA_CURVE_REAL)} entries — "
        "expected ~500. Re-run extraction from Excel."
    )


def test_default_curves_overlap_with_engine_window():
    """Both vendor defaults must cover the post-PPA window the engine uses
    (Jul 2037 through Dec 2061 for D13). Otherwise computed-mode pipelines
    would silently use stale defaults for missing months."""
    required_years = set(range(2037, 2062))  # 2037-2061 inclusive
    baringa_years = {y for (y, _) in _DEFAULT_BARINGA_CURVE_REAL.keys()}
    aurora_years = {y for (y, _) in _DEFAULT_AURORA_CURVE_REAL.keys()}
    assert required_years.issubset(baringa_years), (
        f"Baringa default missing years: {required_years - baringa_years}"
    )
    assert required_years.issubset(aurora_years), (
        f"Aurora default missing years: {required_years - aurora_years}"
    )


def test_apply_inflation_to_baringa_default_produces_reasonable_nominal():
    """Sanity: apply the default CPI curve to the default Baringa real curve
    → resulting nominal values should be ≥ real values (since CPI > 0 past
    base year) and roughly in the same order-of-magnitude as
    `_DEFAULT_MERCHANT_PRICES_MONTHLY` (which came from `Solar&BESS Operation!r66`).
    """
    nominal = _apply_inflation_to_real_curve(
        _DEFAULT_BARINGA_CURVE_REAL,
        _DEFAULT_CPI_CURVE_BY_CALENDAR_YEAR,
        steady_state_rate=0.020,
        base_year=2024,
    )
    # Same key set
    assert set(nominal.keys()) == set(_DEFAULT_BARINGA_CURVE_REAL.keys())
    # Nominal > real for any year past base (inflation factor > 1)
    for (y, m), real_v in _DEFAULT_BARINGA_CURVE_REAL.items():
        if y > 2024:
            assert nominal[(y, m)] >= real_v, (
                f"Inflated value {nominal[(y, m)]:.2f} < real {real_v:.2f} at ({y},{m})"
            )
    # Order of magnitude sanity: 2040 nominal should be in [£50, £300]/MWh range
    samples_2040 = [v for (y, m), v in nominal.items() if y == 2040]
    if samples_2040:
        mean_2040 = sum(samples_2040) / len(samples_2040)
        assert 50 <= mean_2040 <= 300, (
            f"Mean 2040 nominal £{mean_2040:.1f}/MWh looks implausible — "
            "expected £50-300 range for UK merchant electricity."
        )
