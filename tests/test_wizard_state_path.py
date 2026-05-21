"""End-to-end test of the wizard-state path through the PIRR engine.

The fixture audit (`test_project_irr_excel_parity.py`) loads D13 inputs
directly into `PirrInputs` via `d13_inputs.py`. That bypasses the wizard-
state adapter `pirr_inputs_from_wizard_state` — so it can pass while the
adapter silently drops fields, mis-types inputs, or misroutes data.

Four pre-existing UI bugs surfaced by the Step 3a smoke-test loop
(A24 merchant-curve gap; A25 DC/AC rescaling; A26 filename mismatch;
A27 loader row-count discrepancy + per-page loader fragmentation) would
all have been caught by this kind of test had it existed earlier.

This module constructs the same wizard state Step 1 produces, calls the
same downstream functions Step 3a + Step 7 call, and asserts the PIRR
output matches the D13 audit numbers within tolerance.

Three end-to-end paths are exercised:

1. **Minimal-fin path** — Step 1 + an almost-empty `financial` dict; the
   engine adapter fills the rest from its own defaults.
2. **Step 2b-saved path** (A48) — the user walks Step 1 → Step 2 →
   Step 2b → clicks "Save Financial Inputs" → Step 3 → Step 3a. The
   `fin` dict matches what Step 2b's save block writes. Pre-A48 this
   was Step 7's path; the test was renamed when the save button moved.
3. **Fresh-session / DEFAULT_WIZARD_STATE path** (A43) — the user never
   visits Step 2b at all; the adapter receives the financial dict as
   initialized by `DEFAULT_WIZARD_STATE`.

All three paths must produce the same D13 audit numbers; any drift means
either the wizard-state defaults, Step 2b's save payload, or the engine
adapter has shifted out of sync with the engine's Excel-anchored defaults.

See decisions log A27, A28, A43, A48.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_loader import get_active_solar_profile, load_solar_profile_by_name
from src.dispatch_energy import aggregate_to_monthly, run_hourly_dispatch
from src.project_irr import pirr_inputs_from_wizard_state, run_pirr


TOLERANCE_PP = 0.001   # 0.1 percentage points

# D13 expected values via the wizard-state path (must match fixture path).
# Re-baselined 2026-05-16 after A44 (Insurance discrete schedule per Anchal
# Q1 reply). Pre-A44: 0.0885 / 0.0902 / 0.1307. Post-A44: 0.0884 / 0.0900 /
# 0.1307. The schedule replaces the pre-A44 per-kWp × CPI mechanism with the
# Excel-faithful Op r168 chain (lifetime £8,807k preserved). Audit drops
# 3-4 bps uniformly because the pre-A44 mechanism had a fortuitous
# cancellation (under-shot early years, over-shot late years); the schedule
# front-loads costs into the construction premium years (1-2) where NPV
# weighting is highest. Per Anchal Q2 ("unless it is happening because of
# gearing or debt sizing not built currently"), the residual gap is the
# pre-acknowledged structural carve-out, not a calibration error.
EXPECTED_COMBINED = 0.0884
EXPECTED_SB = 0.0900
EXPECTED_GAS = 0.1307


def _build_d13_wizard_state() -> tuple[dict, dict]:
    """Construct the wizard state Step 1 would produce for D13 inputs.

    Mirrors the storage pattern in `pages/Step1_Setup.py` after A27:
      setup['solar_profile_array'] = canonical 8760-element list
      setup['solar_selected_file']  = filename Step 1 selected
      setup['solar_source']          = 'inputs'
      setup['load_mw']               = D13 load
    """
    profile = load_solar_profile_by_name('Burton_Leonard_82MWp_DC_58MW_AC.csv')
    assert profile is not None, "Canonical D13 profile failed to load"
    arr = np.asarray(profile, dtype=float)
    assert len(arr) == 8760, f"Profile length wrong: {len(arr)}"

    setup = {
        'load_mw': 25.0,
        'solar_source': 'inputs',
        'solar_selected_file': 'Burton_Leonard_82MWp_DC_58MW_AC.csv',
        'solar_profile_array': arr.tolist(),
    }
    fin = {
        'enabled': True,
        'solar_capacity_mwp': 82.0,
    }
    return setup, fin


def _run_d13_via_wizard_state() -> dict:
    """Execute the full wizard-state pipeline (Step 3a-style) for D13."""
    setup, fin = _build_d13_wizard_state()

    # Step 3a / Step 7 read the profile from wizard state via this helper
    raw = get_active_solar_profile(setup)
    assert raw is not None, "get_active_solar_profile returned None"
    assert len(raw) == 8760, f"Profile from wizard state has wrong length: {len(raw)}"
    assert abs(float(raw.max()) - 58.36) < 0.01, (
        f"Profile peak wrong — got {raw.max():.2f}, expected 58.36"
    )

    # Per spec D8 / A25: profile is AC + grid-capped, no rescaling
    target_dc_mwp = float(fin['solar_capacity_mwp'])
    profile_ref_mwp = target_dc_mwp  # Option C default
    solar_mw = raw * (target_dc_mwp / profile_ref_mwp)

    # Step 3a dispatch contract
    hourly = run_hourly_dispatch(
        solar_mw,
        load_mw=float(setup['load_mw']),
        bess_mwh=250.0,
        bess_mw=62.5,
        rte=0.87,
    )
    monthly = aggregate_to_monthly(hourly, solar_mw)

    pi = pirr_inputs_from_wizard_state(fin, setup, monthly)
    # Apply per-config overrides matching D13
    pi.solar_dc_mwp = 82.0
    pi.bess_mwh = 250.0
    pi.bess_mw = 62.5

    res = run_pirr(pi)
    return {
        'combined': res.project_irr,
        'sb': res.project_irr_solar_bess,
        'gas': res.project_irr_gas,
        'total_capex_gbpk': res.total_capex,
    }


def test_wizard_state_d13_combined():
    """Combined PIRR via wizard-state path matches audit."""
    r = _run_d13_via_wizard_state()
    msg = (f"Combined PIRR via wizard state: {r['combined']*100:.2f}% vs "
           f"expected {EXPECTED_COMBINED*100:.2f}% "
           f"(delta {(r['combined'] - EXPECTED_COMBINED)*100:+.2f} pp)")
    print(msg)
    assert abs(r['combined'] - EXPECTED_COMBINED) <= TOLERANCE_PP, msg


def test_wizard_state_d13_sb():
    """Solar+BESS-only PIRR via wizard-state path matches audit."""
    r = _run_d13_via_wizard_state()
    msg = (f"S+B PIRR via wizard state: {r['sb']*100:.2f}% vs "
           f"expected {EXPECTED_SB*100:.2f}% "
           f"(delta {(r['sb'] - EXPECTED_SB)*100:+.2f} pp)")
    print(msg)
    assert abs(r['sb'] - EXPECTED_SB) <= TOLERANCE_PP, msg


def test_wizard_state_d13_gas():
    """Gas-only PIRR via wizard-state path matches audit."""
    r = _run_d13_via_wizard_state()
    msg = (f"Gas PIRR via wizard state: {r['gas']*100:.2f}% vs "
           f"expected {EXPECTED_GAS*100:.2f}% "
           f"(delta {(r['gas'] - EXPECTED_GAS)*100:+.2f} pp)")
    print(msg)
    assert abs(r['gas'] - EXPECTED_GAS) <= 0.002, msg   # gas tolerance slightly looser per A22


def test_wizard_state_d13_capex():
    """Total CAPEX via wizard-state path matches audit (£101.6m)."""
    r = _run_d13_via_wizard_state()
    capex_m = r['total_capex_gbpk'] / 1000
    msg = f"Total CAPEX: £{capex_m:.1f}m vs expected £101.6m"
    print(msg)
    assert abs(capex_m - 101.6) < 0.5, msg


def test_get_active_solar_profile_returns_none_when_missing():
    """get_active_solar_profile gracefully returns None for empty setup."""
    assert get_active_solar_profile({}) is None
    assert get_active_solar_profile({'load_mw': 25.0}) is None


def test_get_active_solar_profile_returns_numpy_array():
    """get_active_solar_profile returns a numpy array (not a list)."""
    setup, _ = _build_d13_wizard_state()
    arr = get_active_solar_profile(setup)
    assert isinstance(arr, np.ndarray)
    assert arr.dtype == np.float64
    assert len(arr) == 8760


# =============================================================================
# STEP 2b "SAVE FINANCIAL INPUTS" SIMULATION (A28 lock-in, A48-renamed)
# =============================================================================
# A48 (2026-05-21): the save-button writer moved from Step 7 to Step 2b. The
# payload shape is identical (Step 2b was built by lifting sections 1-9 of
# Step 7 verbatim), so the lock-in test below still validates the same
# regression class — it now guards Step 2b's defaults rather than Step 7's.

def _step2b_saved_fin_with_current_defaults() -> dict:
    """Construct the exact fin state Step 2b's 'Save Financial Inputs' button
    would write with current Step 2b UI defaults (no user modifications).

    Mirrors the `financial_data` payload built in
    `pages/Step2b_FinancialSetup.py` (previously `pages/Step7_Financial.py`
    pre-A48). This test variant locks the alignment between Step 2b's UI
    defaults and the engine's D13-correct defaults — added after A28 to
    catch the regression class where the save-page defaults silently
    disagreed with the engine (smoke test §13's £65m CAPEX bug).

    If Step 2b's UI defaults drift away from engine defaults again, this
    test fails because the engine's D13 numbers no longer reproduce.
    """
    return {
        'enabled': True,
        # Timing
        'project_life_years': 35,
        # Solar
        'solar_capacity_mwp': 82.0,
        'generation_selection': 'P50',  # A28: aligned to D13
        'yield_p50': 967.0, 'yield_p75': 936.0, 'yield_p90': 895.0,
        'degradation_pct': 0.3,  # display %
        # BESS
        'bess_switch': 1,
        'bess_capacity_mw': 62.5,
        'bess_duration_hrs': 4.0,
        'bess_operating_life': 10,  # A28: 15 → 10
        'bess_merchant_switch': 1,
        'bess_scenario': 1,
        'bess_merchant_discount': 5.0,
        # PPA
        'ppa_selection': 1,
        'ppa_flex_pct': 0.0,
        'ppa_indexation': 'CPI',  # adapter doesn't read; harmless
        # REGOs (A28-aligned)
        'rego_switch': 1,
        'rego_price': 2.5,   # was 5.0
        'rego_indexation': 'NIL',
        'rego_tenor_years': 35,  # was 15
        # Capacity Market (A28: D13 OFF)
        'cm_t1_value': 0.0,  # was 20
        'cm_t1_derating': 27.15, 'cm_t1_tenor': 3,  # was 1
        'cm_t4_value': 0.0, 'cm_t4_derating': 20.94, 'cm_t4_tenor': 15,
        # Embedded Benefits (A28: D13 ON)
        'emb_benefits_switch': 1,  # was 0
        'emb_benefits_tenor': 15,
        # BESS Floor (A28: D13 OFF)
        'bess_floor_switch': 0,  # was 1
        'bess_floor_price': 40.0,
        'bess_floor_rev_share': 9.0,  # was 10
        'bess_floor_tenor': 10,
        # CAPEX (A28: aligned to engine PirrInputs)
        'capex_epc': 400.0,
        'capex_grid': 57.858,  # was 30
        'capex_development': 2.949,  # was 15
        'capex_acquisition': 0.0,
        'capex_dd': 3.775,  # was 5
        'capex_discharge': 0.983,  # was 0
        'capex_sdlt': 0.753,  # was 0
        'capex_land_legal': 3.686,  # was 2
        'capex_other_finance': 5.0,  # was 0
        'capex_other_legal': 0.0,  # was 2
        'capex_land_purchase': 0.0,
        'capex_ampyr_tech': 3.236,  # was 0
        'capex_success_fee': 0.0, 'capex_community': 0.0,
        'capex_bess': 600.0,  # was 80 (unit was wrong)
        'capex_landowner_fees': 11.597,  # was 0
        'capex_insurance': 6.329,  # was 3
        'capex_land_lease_constr': 2.457,  # was 0
        'capex_asset_adoption': 0.0, 'capex_others': 0.0,
        'capex_misc': 4.916,  # was 0
        'capex_contingency_pct': 1.0,  # display %
        # Solar OPEX (A28: aligned to engine)
        'opex_pv_om': 5.48,
        'opex_grid_conn': 0.003,  # was 1.5
        'opex_greenkeeping': 1.5,  # was 0.5
        'opex_community': 0.5,  # was 0
        'opex_real_estate_tax': 1.222,  # was 1.0
        'opex_non_tech_am': 1.3,  # was 1.0
        'opex_subsidy_loss': 0.0,
        'opex_insurance': 2.021,
        'opex_fixed_lease': 0.0,
        'opex_corrective_maint': 3.2,
        'opex_tech_am': 0.3,  # was 1.5
        'opex_social_cost': 0.0,
        'opex_balancing_cfd': 2.75,  # was 0
        # BESS OPEX (A28: aligned)
        'bess_opex_om': 7.063,
        'bess_opex_import': 0.0,
        'bess_opex_rates': 3.276,  # was 0
        'bess_opex_lease': 1.489,  # was 0
        # Land (A28: D13 ON, 205 acres, £700, 5%/5%)
        'fixed_lease_switch': 1,  # was 0
        'fixed_lease_acres': 205.0,  # was 200
        'fixed_lease_price': 700.0,  # was 800
        'rev_dep_lease_switch': 1,  # was 0
        'rev_share_yr1_10': 5.0,
        'rev_share_yr11_35': 5.0,  # was 7.5
        'land_purchase_switch': 0,
        # Tax (A28: engine adapter now reads corp_tax_rate_high)
        'corp_tax_rate_low': 19.0,
        'corp_tax_rate_high': 25.0,
        'corp_tax_threshold': 250.0,
        'taxation_month': 12,
        # Working Capital + Discount
        'wc_debtors_days': 30,  # was 45
        'wc_creditors_days': 30,
        'project_discount_rate': 6.5,  # was 8.0
        # Advanced
        'shl_switch': 1,
        'shl_pct_of_unfunded': 99.0,
        'shl_rate': 15.0,
        'depreciation_method': 'RB',
        'depreciation_rate': 100.0 * 2.0 / 36.0,
    }


def _run_d13_with_step2b_saved_state() -> dict:
    """End-to-end: simulate user walked Step 1 → Step 2 → Step 2b (clicked
    Save Financial Inputs) → Step 3 → Step 3a, inspected 250/4 row. Per A48,
    Step 2b is the save-button page; pre-A48 this was Step 7."""
    setup, _ = _build_d13_wizard_state()
    fin = _step2b_saved_fin_with_current_defaults()

    raw = get_active_solar_profile(setup)
    target_dc_mwp = float(fin['solar_capacity_mwp'])
    solar_mw = raw * (target_dc_mwp / target_dc_mwp)

    hourly = run_hourly_dispatch(
        solar_mw,
        load_mw=float(setup['load_mw']),
        bess_mwh=250.0, bess_mw=62.5, rte=0.87,
    )
    monthly = aggregate_to_monthly(hourly, solar_mw)

    pi = pirr_inputs_from_wizard_state(fin, setup, monthly)
    pi.solar_dc_mwp = 82.0
    pi.bess_mwh = 250.0
    pi.bess_mw = 62.5

    res = run_pirr(pi)
    return {
        'combined': res.project_irr,
        'sb': res.project_irr_solar_bess,
        'gas': res.project_irr_gas,
        'capex_gbpm': res.total_capex / 1000.0,
    }


def test_step2b_saved_defaults_produce_audit_capex():
    """With Step 2b's CURRENT UI defaults, total CAPEX matches D13 audit.

    Pre-A28: save-page defaults gave CAPEX £65.0m (capex_bess unit mismatch,
    plus many silent capex_* drifts). After A28 alignment: £101.6m, matching
    D13 audit. A48 (2026-05-21) moved the save button from Step 7 to Step
    2b; the lock-in shape is unchanged.
    """
    r = _run_d13_with_step2b_saved_state()
    msg = f"Step 2b-saved CAPEX: £{r['capex_gbpm']:.2f}m vs expected £101.6m"
    print(msg)
    assert abs(r['capex_gbpm'] - 101.6) < 0.5, msg


def test_step2b_saved_defaults_produce_audit_sb_pirr():
    """With Step 2b's CURRENT UI defaults, S+B PIRR matches D13 audit (9.00%).

    Pre-A28: S+B PIRR drifted to ~30% (wrong tax rate, wrong BESS revenue
    switches, etc.). After A28 alignment + A44 Insurance schedule: 9.00%,
    matching D13 audit.
    """
    r = _run_d13_with_step2b_saved_state()
    msg = (f"Step 2b-saved S+B: {r['sb']*100:.2f}% vs expected "
           f"{EXPECTED_SB*100:.2f}% (delta {(r['sb']-EXPECTED_SB)*100:+.2f} pp)")
    print(msg)
    assert abs(r['sb'] - EXPECTED_SB) <= TOLERANCE_PP, msg


def test_step2b_saved_defaults_produce_audit_combined_pirr():
    """With Step 2b's CURRENT UI defaults, Combined PIRR matches D13 audit."""
    r = _run_d13_with_step2b_saved_state()
    msg = (f"Step 2b-saved Combined: {r['combined']*100:.2f}% vs expected "
           f"{EXPECTED_COMBINED*100:.2f}% "
           f"(delta {(r['combined']-EXPECTED_COMBINED)*100:+.2f} pp)")
    print(msg)
    assert abs(r['combined'] - EXPECTED_COMBINED) <= TOLERANCE_PP, msg


def _run_d13_via_default_wizard_state() -> dict:
    """Fresh-session path: user opens app, walks Step 1 + Step 3, then opens
    Step 3a without visiting Step 7. The engine adapter receives
    `state['financial']` as initialized by `DEFAULT_WIZARD_STATE` (no
    Step-7-Save overrides). Pre-A43, this path produced CAPEX £64.7m and
    Combined PIRR ~19.7% because `DEFAULT_WIZARD_STATE['financial']` carried
    pre-A28 defaults (capex_bess=80, opex_balancing_cfd=0, etc.). Post-A43,
    those defaults are aligned with Step 7's UI defaults and the engine's
    Excel-anchored D13 values.
    """
    from copy import deepcopy
    from src.wizard_state import DEFAULT_WIZARD_STATE

    setup, _ = _build_d13_wizard_state()
    # Take the financial section EXACTLY as DEFAULT_WIZARD_STATE provides it,
    # then flip 'enabled' on (Step 1 typically does this when the user starts
    # walking the wizard, but the adapter doesn't gate on it).
    fin = deepcopy(DEFAULT_WIZARD_STATE['financial'])
    fin['enabled'] = True

    raw = get_active_solar_profile(setup)
    target_dc_mwp = float(fin['solar_capacity_mwp'])
    solar_mw = raw * (target_dc_mwp / target_dc_mwp)

    hourly = run_hourly_dispatch(
        solar_mw,
        load_mw=float(setup['load_mw']),
        bess_mwh=250.0, bess_mw=62.5, rte=0.87,
    )
    monthly = aggregate_to_monthly(hourly, solar_mw)

    pi = pirr_inputs_from_wizard_state(fin, setup, monthly)
    pi.solar_dc_mwp = 82.0
    pi.bess_mwh = 250.0
    pi.bess_mw = 62.5

    res = run_pirr(pi)
    return {
        'combined': res.project_irr,
        'sb': res.project_irr_solar_bess,
        'gas': res.project_irr_gas,
        'capex_gbpm': res.total_capex / 1000.0,
    }


def test_default_wizard_state_produces_audit_capex():
    """Fresh-session path (no Step 7 visit) produces D13 audit CAPEX.

    Locks the A43 fix: DEFAULT_WIZARD_STATE['financial'] must stay aligned
    with Step 7's UI defaults and the engine's Excel-anchored values. If
    someone reverts a value in `src/wizard_state.py` financial section, this
    test catches it. Pre-A43 the path gave £64.7m (browser smoke test §16).
    """
    r = _run_d13_via_default_wizard_state()
    msg = (f"Fresh-session CAPEX: £{r['capex_gbpm']:.2f}m vs expected ~£101.6m. "
           "If this fails, DEFAULT_WIZARD_STATE['financial'] drifted from "
           "Step 7's UI defaults — re-align via the diff in A43.")
    print(msg)
    assert abs(r['capex_gbpm'] - 101.6) < 0.5, msg


def test_default_wizard_state_produces_audit_combined():
    """Fresh-session Combined PIRR matches the audit. Same lock-in as the
    CAPEX test above, but on the IRR side — catches opex / land / tax-shield
    misalignments that don't show in the CAPEX line."""
    r = _run_d13_via_default_wizard_state()
    msg = (f"Fresh-session Combined: {r['combined']*100:.2f}% vs expected "
           f"{EXPECTED_COMBINED*100:.2f}% "
           f"(delta {(r['combined']-EXPECTED_COMBINED)*100:+.2f} pp)")
    print(msg)
    assert abs(r['combined'] - EXPECTED_COMBINED) <= TOLERANCE_PP, msg


def test_default_wizard_state_produces_audit_sb():
    """Fresh-session S+B PIRR matches the audit."""
    r = _run_d13_via_default_wizard_state()
    msg = (f"Fresh-session S+B: {r['sb']*100:.2f}% vs expected "
           f"{EXPECTED_SB*100:.2f}% "
           f"(delta {(r['sb']-EXPECTED_SB)*100:+.2f} pp)")
    print(msg)
    assert abs(r['sb'] - EXPECTED_SB) <= TOLERANCE_PP, msg


# =============================================================================
# A48 WIZARD-STATE SCHEMA GUARDS (price-curve placeholder keys)
# =============================================================================

def test_default_wizard_state_has_price_curve_keys():
    """DEFAULT_WIZARD_STATE['setup'] must carry the A48 price-curve keys.

    Step 1's Market Price Curve panel reads/writes
    `setup['merchant_price_curve_source']` (radio state) and
    `setup['merchant_price_curve']` (uploaded curve dict, or None when
    using the engine default). If these keys are removed accidentally,
    Step 1's panel will KeyError on first interaction.
    """
    from src.wizard_state import DEFAULT_WIZARD_STATE
    setup_defaults = DEFAULT_WIZARD_STATE['setup']
    assert 'merchant_price_curve_source' in setup_defaults, (
        "Missing wizard-state key 'merchant_price_curve_source' — A48 panel "
        "in Step 1 will break. Re-add to DEFAULT_WIZARD_STATE['setup'] in "
        "src/wizard_state.py."
    )
    assert setup_defaults['merchant_price_curve_source'] == 'default', (
        f"Unexpected default for 'merchant_price_curve_source': "
        f"{setup_defaults['merchant_price_curve_source']!r} (expected 'default')"
    )
    assert 'merchant_price_curve' in setup_defaults, (
        "Missing wizard-state key 'merchant_price_curve' — A48 panel in "
        "Step 1 will break."
    )
    assert setup_defaults['merchant_price_curve'] is None, (
        "Default 'merchant_price_curve' must be None (engine uses its "
        "locked Burton Leonard curve until user uploads)."
    )


if __name__ == "__main__":
    r = _run_d13_via_wizard_state()
    print("D13 via wizard-state path (minimal fin):")
    print(f"  Combined: {r['combined']*100:.2f}% (expected {EXPECTED_COMBINED*100:.2f}%)")
    print(f"  S+B:      {r['sb']*100:.2f}% (expected {EXPECTED_SB*100:.2f}%)")
    print(f"  Gas:      {r['gas']*100:.2f}% (expected {EXPECTED_GAS*100:.2f}%)")
    print(f"  CAPEX:    £{r['total_capex_gbpk']/1000:.1f}m (expected £101.6m)")
    print()
    r2 = _run_d13_with_step2b_saved_state()
    print("D13 via Step 2b 'Save Financial Inputs' path (A28 alignment, A48 rename):")
    print(f"  Combined: {r2['combined']*100:.2f}% (expected {EXPECTED_COMBINED*100:.2f}%)")
    print(f"  S+B:      {r2['sb']*100:.2f}% (expected {EXPECTED_SB*100:.2f}%)")
    print(f"  Gas:      {r2['gas']*100:.2f}% (expected {EXPECTED_GAS*100:.2f}%)")
    print(f"  CAPEX:    £{r2['capex_gbpm']:.1f}m (expected £101.6m)")
    print()
    r3 = _run_d13_via_default_wizard_state()
    print("D13 via DEFAULT_WIZARD_STATE path (fresh session, no Step 2b visit):")
    print(f"  Combined: {r3['combined']*100:.2f}% (expected {EXPECTED_COMBINED*100:.2f}%)")
    print(f"  S+B:      {r3['sb']*100:.2f}% (expected {EXPECTED_SB*100:.2f}%)")
    print(f"  Gas:      {r3['gas']*100:.2f}% (expected {EXPECTED_GAS*100:.2f}%)")
    print(f"  CAPEX:    £{r3['capex_gbpm']:.1f}m (expected £101.6m)")
