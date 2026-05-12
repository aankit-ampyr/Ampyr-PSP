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
    "CPI": 0.025,
    "RPI": 0.030,
    "PPA Indexation": 0.0,    # PPA indexed at tariff_escalation, set on input
    "BESS Indexation": 0.020,
    "Land Lease RPI": 0.030,
}


def _esc_factor(rates: dict, case: str, ops_year: int) -> float:
    """Escalation factor for the start of operations year `ops_year`.

    Year 0 = 1.0, year y = (1+rate)^y. Matches Excel convention where
    indexation is applied at the start of each operating year, so the year-1
    cash flows carry no escalation.
    """
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
    merchant_prices: dict = field(default_factory=dict)   # {year: GBP/MWh}
    merchant_price_default: float = 67.0

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
    opex_insurance: float = 2.021
    opex_corrective_maint: float = 3.2
    opex_tech_am: float = 0.3
    opex_solar_fixed_indexation: str = "CPI"

    opex_balancing_cfd: float = 2.75    # GBP/MWh of generation
    opex_solar_var_indexation: str = "CPI"

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
    gas_opex_major_maint_annual: float = 685.0
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
    """Returns (dates, is_construction, is_operations, ops_month_idx)."""
    total_months = _months_between(inp.construction_start, inp.cod_date) \
                   + inp.project_life_years * 12

    dates = np.array([_add_months(inp.construction_start, i)
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
                is_construction: np.ndarray) -> tuple[np.ndarray, float]:
    n = len(dates)
    capex = np.zeros(n)

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

    # BESS — scales with BESS MW (D5). 600 GBP/kW × 1000 kW/MW × MW / 1000 → GBPk
    # = 600 GBP/kW × MW (numerically: GBP/kW × MW = GBPk).
    bess_capex = inp.capex_bess_gbp_per_kw_bess * inp.bess_mw  # GBPk

    # Gas — provided as total GBPk
    gas_capex = inp.gas_capex_total_gbpk

    base = solar_capex + bess_capex + gas_capex

    with_contingency = base * (1.0 + inp.capex_contingency_pct)
    total = (with_contingency + inp.capex_idc_gbpk
             + inp.capex_financing_fees_gbpk + inp.capex_dsra_gbpk)

    # Phase evenly over construction months
    cm = int(is_construction.sum())
    if cm > 0:
        capex[is_construction] = -total / cm
    return capex, total


# =============================================================================
# REVENUE STREAMS
# =============================================================================

def _select_yield(inp: PirrInputs) -> float:
    return {"P50": inp.yield_p50, "P75": inp.yield_p75,
            "P90": inp.yield_p90}.get(inp.generation_selection, inp.yield_p50)


def _calc_revenue(inp: PirrInputs, rates: dict, dates: np.ndarray,
                  is_operations: np.ndarray, ops_idx: np.ndarray) -> dict:
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
                                 inp.merchant_price_default)
            out["solar_merchant"][i] = surplus * mp / 1000
        else:
            # Post-PPA: ALL generation merchant (no PPA, no DC delivery split)
            mp = _merchant_price(inp.merchant_prices, d.year,
                                 inp.merchant_price_default)
            out["solar_merchant"][i] = monthly_gen * mp / 1000

        # ---- REGO ----
        if inp.rego_switch and ops_year < inp.rego_tenor_years:
            out["rego"][i] = monthly_gen * inp.rego_price * \
                _esc_factor(rates, inp.rego_indexation, ops_year) / 1000

        # ---- 11kV embedded benefits ----
        if inp.emb_switch and ops_year < inp.emb_tenor_years \
                and len(inp.emb_benefits_monthly) == 12:
            rate = inp.emb_benefits_monthly[m]  # GBP/MWh
            out["embedded"][i] = monthly_gen * rate * \
                _esc_factor(rates, inp.emb_indexation, ops_year) / 1000

        # ---- Capacity Market T-1 ----
        if d >= inp.cm_t1_start:
            cm_t1_year = _months_between(inp.cm_t1_start, d) // 12
            if cm_t1_year < inp.cm_t1_tenor_years:
                out["cm_t1"][i] = (
                    inp.cm_t1_value * inp.cm_t1_derating * inp.bess_mw / 12
                    * _esc_factor(rates, inp.cm_t1_indexation, cm_t1_year)
                )

        # ---- Capacity Market T-4 ----
        if d >= inp.cm_t4_start:
            cm_t4_year = _months_between(inp.cm_t4_start, d) // 12
            if cm_t4_year < inp.cm_t4_tenor_years:
                out["cm_t4"][i] = (
                    inp.cm_t4_value * inp.cm_t4_derating * inp.bess_mw / 12
                    * _esc_factor(rates, inp.cm_t4_indexation, cm_t4_year)
                )

        # ---- BESS floor (net of underwriter rev share) ----
        if inp.bess_floor_switch and ops_year < inp.bess_floor_tenor_years:
            gross = (inp.bess_floor_price * inp.bess_mw / 12
                     * _esc_factor(rates, inp.bess_floor_indexation, ops_year))
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


def _merchant_price(prices: dict, year: int, default: float) -> float:
    """Look up annual merchant price. Zero in the dict means *deliberately
    zero* (Excel uses 0 for years before the curve starts) — return as-is,
    don't fall back to default.
    """
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
               revenue: np.ndarray) -> np.ndarray:
    n = len(dates)
    opex = np.zeros(n)

    # Solar fixed opex — excludes corrective maintenance (handled separately
    # as a level annual charge sized to Excel's 8-event step pattern).
    solar_fixed_per_kwp = (
        inp.opex_pv_om + inp.opex_grid_conn + inp.opex_greenkeeping
        + inp.opex_community + inp.opex_real_estate_tax + inp.opex_non_tech_am
        + inp.opex_subsidy_loss + inp.opex_insurance + inp.opex_tech_am
    )
    monthly_solar_fixed = solar_fixed_per_kwp * inp.solar_dc_mwp / 12
    monthly_corrective = inp.opex_corrective_maint_annual_gbpk / 12

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

        # Solar fixed (escalates CPI)
        opex[i] -= monthly_solar_fixed * \
            _esc_factor(rates, inp.opex_solar_fixed_indexation, ops_year)

        # Corrective maintenance (CPI-escalated, level annual to match Excel)
        opex[i] -= monthly_corrective * \
            _esc_factor(rates, inp.opex_solar_fixed_indexation, ops_year)

        # Solar variable (balancing CfD £/MWh × generation × CPI)
        if inp.opex_balancing_cfd > 0:
            solar_degrad = max(1.0 - inp.solar_degradation_pct * ops_year, 0.0) \
                           if ops_year > 0 else 1.0
            monthly_gen = base_annual_gen_mwh * season * solar_degrad
            opex[i] -= (monthly_gen * inp.opex_balancing_cfd
                        * _esc_factor(rates, inp.opex_solar_var_indexation,
                                      ops_year) / 1000)

        # BESS fixed + step (LTSA / PCS Warranty / Augmentation) — both
        # capped at BESS operating life
        if d < bess_end:
            esc_bess = _esc_factor(rates, inp.bess_opex_indexation, ops_year)
            opex[i] -= monthly_bess_fixed * esc_bess
            opex[i] -= monthly_bess_step * esc_bess

        # Gas fixed/variable — only while gas plant operates (years 1..gas EOL)
        if d < gas_eol:
            gas_esc = (1.0 + inp.gas_opex_inflation) ** ops_year
            opex[i] -= monthly_gas_fixed * gas_esc

            # Major equipment maintenance (escalates with gas inflation)
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

            # UKETS (CO2 cost)
            ukets_gbpk = (gas_mwh * inp.gas_co2_kg_per_mwh
                          * inp.gas_ukets_cost_gbp_per_kg / 1000)
            opex[i] -= ukets_gbpk

            # Gas fixed-cost-per-day (Excel: "Fixed gas cost £/day")
            days = _days_in_month(d)
            opex[i] -= inp.gas_fixed_cost_gbp_day * days * gas_esc / 1000

        # Land lease — Excel uses GREATER of fixed or rev-dependent, not sum.
        # Annual mechanism per Anchal 2026-05-11 (decisions log A18):
        #   Final lease = Fixed lease (monthly) + July adjustment
        #                 where adjustment = max(annual_rev_lease - annual_fixed, 0)
        # Net: when rev_lease > fixed every month, equivalent to monthly max().
        #
        # Note 2026-05-12 (A20): the 2x multiplier I added in A18 (replicating
        # Excel Op r98 doubling) was reverted. Per Anchal's Q4 reply, Excel
        # applies 5% to actual revenue; the 2x observed in Solar&BESS Operation
        # r98 is a workbook artifact (label row summing both base+applied
        # versions of each stream), not a real multiplier. Reverting improved
        # S+B PIRR uniformly by ~0.8 pp across all 4 matrix rows.
        fixed_lease_m = 0.0
        if inp.fixed_lease_switch:
            fixed_lease_m = (
                inp.fixed_lease_price * inp.fixed_lease_acres / 1000 / 12
                * _esc_factor(rates, inp.fixed_lease_indexation, ops_year)
            )
        rev_lease_m = 0.0
        if inp.rev_dep_lease_switch and revenue[i] > 0:
            share = inp.rev_share_yr1_10 if ops_year < 10 \
                else inp.rev_share_yr11_35
            rev_lease_m = revenue[i] * share
        opex[i] -= max(fixed_lease_m, rev_lease_m)

    return opex


# =============================================================================
# DEPRECIATION (SLM single account over project life)
# =============================================================================

def _calc_depreciation(total_capex: float, project_life_years: int,
                        is_operations: np.ndarray) -> np.ndarray:
    n = len(is_operations)
    depr = np.zeros(n)
    if total_capex <= 0:
        return depr
    monthly = total_capex / (project_life_years * 12)
    depr[is_operations] = monthly
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
# TAX (D2: max(0, (EBIT − Interest) × rate); annual loss carry-forward)
# =============================================================================

def _calc_tax(inp: PirrInputs, dates: np.ndarray,
              is_operations: np.ndarray,
              ebitda: np.ndarray, depreciation: np.ndarray,
              interest: np.ndarray) -> np.ndarray:
    n = len(dates)
    tax = np.zeros(n)
    monthly_taxable = ebitda - depreciation - interest

    annual_accum = 0.0
    loss_pool = 0.0

    for i in range(n):
        if not is_operations[i]:
            continue
        annual_accum += monthly_taxable[i]
        if dates[i].month == inp.taxation_month:
            if annual_accum < 0:
                loss_pool += -annual_accum
                annual_accum = 0.0
            else:
                if loss_pool > 0:
                    used = min(loss_pool, annual_accum)
                    annual_accum -= used
                    loss_pool -= used
                if annual_accum > 0:
                    tax[i] = -annual_accum * inp.corp_tax_rate
            annual_accum = 0.0
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

    # Capex first — depreciation, interest, FCFF all depend on total
    capex, total_capex = _calc_capex(inp, dates, is_construction)
    res.capex = capex
    res.total_capex = total_capex

    # Revenue
    rev = _calc_revenue(inp, rates, dates, is_operations, ops_idx)
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
    opex = _calc_opex(inp, rates, dates, is_operations, ops_idx, revenue)
    res.opex = opex
    res.total_opex_lifetime = float(-opex.sum())

    ebitda = revenue + opex
    res.ebitda = ebitda

    depr = _calc_depreciation(total_capex, inp.project_life_years, is_operations)
    res.depreciation = depr

    interest = _calc_interest(inp, total_capex, is_operations)
    res.interest = interest

    tax = _calc_tax(inp, dates, is_operations, ebitda, depr, interest)
    res.tax = tax
    res.total_tax_lifetime = float(-tax.sum())

    nwc_change = _calc_nwc_change(inp, is_operations, revenue, opex)
    res.nwc_change = nwc_change

    # FCFF (ungeared cash) — interest does NOT appear in FCFF (D2)
    fcff = revenue + opex + tax + capex + nwc_change
    res.fcff = fcff

    res.project_irr = xirr(dates, fcff)
    res.project_npv = xnpv(dates, fcff, inp.discount_rate)
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
        corp_tax_rate=f("corp_tax_rate_low", 25.0) / 100.0,
        taxation_month=i("taxation_month", 12),

        # --- Working capital ---
        debtor_days=i("wc_debtors_days", 30),
        creditor_days=i("wc_creditors_days", 30),

        # --- Discount (for NPV reporting) ---
        discount_rate=f("project_discount_rate", 6.5) / 100.0,
    )
