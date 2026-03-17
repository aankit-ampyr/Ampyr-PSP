"""
Financial Model Engine — Iteration A1: Core FCFF Chain

Replicates the ungeared Project IRR calculation from Off-Grid Solution v8.xlsm.
Pure Python implementation for fast screening of 50+ configurations.

FCFF chain (Equity sheet rows 150-162):
  Revenue (FS!27) - OPEX (FS!59) ± NWC (FS!61) - CAPEX (FS!69:89)
  - Tax (D&T!265) = FCFF -> XIRR

Currency: GBP thousands (GBPk) throughout all calculations.
Monthly granularity, up to 420 periods (35yr × 12mo).
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
import numpy as np


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FinancialInputs:
    """All inputs needed for the ungeared Project IRR calculation."""

    # --- Timing ---
    model_start: date = field(default_factory=lambda: date(2024, 7, 1))
    construction_start: date = field(default_factory=lambda: date(2026, 1, 1))
    construction_months: int = 18
    cod_date: date = field(default_factory=lambda: date(2027, 7, 1))
    project_life_years: int = 35

    # --- Solar ---
    solar_capacity_mwp: float = 82.0
    yield_p50: float = 967.0         # MWh/MWp/Yr
    yield_p75: float = 936.0
    yield_p90: float = 895.0
    generation_selection: str = "P90"
    degradation_pct: float = 0.3     # display % (0.3 means 0.3%/yr)
    seasonality: list = field(default_factory=lambda: [1/12]*12)

    # Outage
    outage_selection: int = 0        # 0=no, 1=yes
    outage_month: int = 1            # 1-12
    outage_length_days: int = 14

    # --- BESS ---
    bess_switch: int = 1
    bess_capacity_mw: float = 62.5
    bess_duration_hrs: float = 4.0
    bess_operating_life: int = 15
    bess_degradation_pct: float = 2.5  # display %/yr

    # BESS revenue
    bess_merchant_switch: int = 1
    bess_scenario: int = 1
    bess_merchant_discount: float = 5.0  # display %
    bess_floor_switch: int = 1
    bess_floor_price: float = 40.0       # GBP/MW/yr
    bess_floor_rev_share: float = 10.0   # display %
    bess_floor_tenor: int = 10

    # --- PPA ---
    ppa_selection: int = 1
    ppa_price_gbp_mwh: float = 50.0     # GBP/MWh (default estimate)
    ppa_indexation: str = "CPI"
    ppa_flex_pct: float = 0.0

    # --- REGOs ---
    rego_switch: int = 1
    rego_price: float = 5.0             # GBP/MWh
    rego_indexation: str = "CPI"
    rego_tenor_years: int = 15

    # --- Capacity Market ---
    cm_t1_value: float = 20.0           # GBPk/MW/Yr
    cm_t1_derating: float = 27.15       # display %
    cm_t1_tenor: int = 1
    cm_t4_value: float = 0.0
    cm_t4_derating: float = 0.0
    cm_t4_tenor: int = 0

    # --- CAPEX (GBP/kWp) ---
    capex_epc: float = 400.0
    capex_grid: float = 30.0
    capex_development: float = 15.0
    capex_acquisition: float = 0.0
    capex_dd: float = 5.0
    capex_discharge: float = 0.0
    capex_sdlt: float = 0.0
    capex_land_legal: float = 2.0
    capex_other_finance: float = 0.0
    capex_other_legal: float = 2.0
    capex_land_purchase: float = 0.0
    capex_ampyr_tech: float = 0.0
    capex_success_fee: float = 0.0
    capex_community: float = 0.0
    capex_bess: float = 80.0
    capex_landowner_fees: float = 0.0
    capex_insurance: float = 3.0
    capex_land_lease_constr: float = 0.0
    capex_asset_adoption: float = 0.0
    capex_others: float = 0.0
    capex_misc: float = 0.0
    capex_contingency_pct: float = 1.0  # display %

    # --- Solar OPEX (GBP/kWp/Yr) ---
    opex_pv_om: float = 5.48
    opex_grid_conn: float = 1.5
    opex_greenkeeping: float = 0.5
    opex_community: float = 0.0
    opex_real_estate_tax: float = 1.0
    opex_non_tech_am: float = 1.0
    opex_subsidy_loss: float = 0.0
    opex_insurance: float = 2.02
    opex_fixed_lease: float = 0.0
    opex_corrective_maint: float = 3.2
    opex_tech_am: float = 1.5
    opex_social_cost: float = 0.0      # GBP/MWh (variable)
    opex_balancing_cfd: float = 0.0    # GBP/MWh (variable)

    # --- BESS OPEX (GBPk/MW/Yr) ---
    bess_opex_om: float = 7.06
    bess_opex_import: float = 0.0
    bess_opex_rates: float = 0.0
    bess_opex_lease: float = 0.0

    # --- Land ---
    fixed_lease_switch: int = 0
    fixed_lease_acres: float = 200.0
    fixed_lease_price: float = 800.0     # GBP/Acre/Yr
    rev_dep_lease_switch: int = 0
    rev_share_yr1_10: float = 5.0        # display %
    rev_share_yr11_35: float = 7.5       # display %
    construction_rent_sw: int = 0
    construction_rent: float = 500.0     # GBP/Acre/Yr

    # --- Tax ---
    corp_tax_rate_low: float = 19.0      # display %
    corp_tax_rate_high: float = 25.0     # display %
    corp_tax_threshold: float = 250.0    # GBPk
    taxation_month: int = 12             # 1-12

    # --- Working Capital ---
    wc_debtors_days: int = 45
    wc_creditors_days: int = 30

    # --- Financial ---
    project_discount_rate: float = 8.0   # display %
    cost_of_capital: float = 6.0         # display %

    # --- Indexation rate (default CPI assumption) ---
    indexation_rate: float = 2.5         # display % annual CPI


@dataclass
class FinancialResults:
    """Output of the financial model calculation."""

    # Summary metrics
    project_irr: float = np.nan          # XIRR result (decimal, e.g. 0.085 = 8.5%)
    project_npv: float = np.nan          # XNPV at discount rate (GBPk)
    total_capex: float = 0.0             # Total CAPEX (GBPk)
    total_revenue_lifetime: float = 0.0  # Sum of all revenue (GBPk)
    total_opex_lifetime: float = 0.0     # Sum of all OPEX (GBPk)
    payback_month: int = 0               # Month when cumulative FCFF turns positive

    # Monthly arrays (all in GBPk)
    dates: np.ndarray = field(default_factory=lambda: np.array([]))
    revenue: np.ndarray = field(default_factory=lambda: np.array([]))
    opex: np.ndarray = field(default_factory=lambda: np.array([]))
    capex: np.ndarray = field(default_factory=lambda: np.array([]))
    depreciation: np.ndarray = field(default_factory=lambda: np.array([]))
    ebitda: np.ndarray = field(default_factory=lambda: np.array([]))
    tax: np.ndarray = field(default_factory=lambda: np.array([]))
    nwc: np.ndarray = field(default_factory=lambda: np.array([]))
    fcff: np.ndarray = field(default_factory=lambda: np.array([]))
    fcff_cumulative: np.ndarray = field(default_factory=lambda: np.array([]))

    # Component breakdown
    solar_revenue: np.ndarray = field(default_factory=lambda: np.array([]))
    bess_revenue: np.ndarray = field(default_factory=lambda: np.array([]))
    solar_opex: np.ndarray = field(default_factory=lambda: np.array([]))
    bess_opex: np.ndarray = field(default_factory=lambda: np.array([]))


# =============================================================================
# TIMELINE
# =============================================================================

def build_timeline(inputs: FinancialInputs) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build monthly date array from model_start through end of project life.

    Returns:
        dates: array of date objects (1st of each month)
        is_construction: boolean array (True during construction)
        is_operations: boolean array (True during operations)
    """
    total_months = _months_between(inputs.model_start, inputs.cod_date) + \
                   inputs.project_life_years * 12

    dates = []
    d = inputs.model_start
    for _ in range(total_months):
        dates.append(d)
        # Advance to next month
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)

    dates = np.array(dates)

    # Boolean masks
    is_construction = np.array([
        inputs.construction_start <= d < inputs.cod_date for d in dates
    ])
    is_operations = np.array([
        d >= inputs.cod_date for d in dates
    ])

    return dates, is_construction, is_operations


def _months_between(d1: date, d2: date) -> int:
    """Number of months between two dates."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _operations_month_index(dates: np.ndarray, is_operations: np.ndarray) -> np.ndarray:
    """For each date, return the 0-based operations month (or -1 if not in ops)."""
    indices = np.full(len(dates), -1, dtype=int)
    counter = 0
    for i in range(len(dates)):
        if is_operations[i]:
            indices[i] = counter
            counter += 1
    return indices


# =============================================================================
# REVENUE
# =============================================================================

def calc_revenue(inputs: FinancialInputs, dates: np.ndarray,
                 is_operations: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate monthly revenue (GBPk).

    Solar revenue = generation (MWh) × price (GBP/MWh) / 1000
    BESS revenue = floor price or merchant revenue

    Returns: (total_revenue, solar_revenue, bess_revenue) arrays in GBPk
    """
    n = len(dates)
    solar_rev = np.zeros(n)
    bess_rev = np.zeros(n)

    # Selected yield
    yield_map = {"P50": inputs.yield_p50, "P75": inputs.yield_p75, "P90": inputs.yield_p90}
    annual_yield = yield_map.get(inputs.generation_selection, inputs.yield_p90)

    # Annual generation (MWh) = capacity (MWp) × yield (MWh/MWp/Yr)
    base_annual_gen = inputs.solar_capacity_mwp * annual_yield

    # PPA price estimate (GBP/MWh) - using a reasonable default
    # In full implementation, this would come from merchant curves
    ppa_price = inputs.ppa_price_gbp_mwh

    # BESS capacity
    bess_mwh = inputs.bess_capacity_mw * inputs.bess_duration_hrs if inputs.bess_switch else 0

    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        # Operations year (0-based)
        ops_year = ops_month // 12

        # --- Solar degradation ---
        if ops_year == 0:
            degrad_factor = 1.0
        else:
            degrad_factor = 1.0 - (inputs.degradation_pct / 100) * ops_year

        degrad_factor = max(degrad_factor, 0.0)

        # --- Monthly generation (MWh) ---
        month_idx = dates[i].month - 1  # 0-based month
        seasonality_factor = inputs.seasonality[month_idx] if len(inputs.seasonality) == 12 else 1/12
        monthly_gen = base_annual_gen * seasonality_factor * degrad_factor

        # --- Outage adjustment ---
        if inputs.outage_selection and (dates[i].month == inputs.outage_month):
            days_in_month = _days_in_month(dates[i])
            outage_fraction = min(inputs.outage_length_days / days_in_month, 1.0)
            monthly_gen *= (1.0 - outage_fraction)

        # --- Price indexation ---
        indexation_factor = (1 + inputs.indexation_rate / 100) ** ops_year

        # --- Solar revenue (GBPk) ---
        solar_price = ppa_price * indexation_factor
        solar_rev[i] = monthly_gen * solar_price / 1000  # GBP -> GBPk

        # --- BESS revenue (GBPk) ---
        if inputs.bess_switch:
            bess_ops_year = ops_year
            bess_degrad = max(1.0 - (inputs.bess_degradation_pct / 100) * bess_ops_year, 0.0)
            effective_bess_mw = inputs.bess_capacity_mw * bess_degrad

            # Within BESS operating life?
            if bess_ops_year < inputs.bess_operating_life:
                # Floor revenue: GBP/MW/yr × MW / 12 / 1000
                if inputs.bess_floor_switch and bess_ops_year < inputs.bess_floor_tenor:
                    floor_rev = (inputs.bess_floor_price * effective_bess_mw / 12 / 1000)
                    bess_rev[i] += floor_rev

                # Capacity market T-1
                if inputs.cm_t1_value > 0 and bess_ops_year < inputs.cm_t1_tenor:
                    # GBPk/MW/Yr × de-rating × MW / 12
                    cm_rev = (inputs.cm_t1_value * (inputs.cm_t1_derating / 100)
                              * effective_bess_mw / 12)
                    bess_rev[i] += cm_rev

                # Capacity market T-4
                if inputs.cm_t4_value > 0 and bess_ops_year < inputs.cm_t4_tenor:
                    cm4_rev = (inputs.cm_t4_value * (inputs.cm_t4_derating / 100)
                               * effective_bess_mw / 12)
                    bess_rev[i] += cm4_rev

                # REGO revenue on solar generation
                if inputs.rego_switch and bess_ops_year < inputs.rego_tenor_years:
                    rego_rev = monthly_gen * inputs.rego_price * indexation_factor / 1000
                    solar_rev[i] += rego_rev

        ops_month += 1

    total_rev = solar_rev + bess_rev
    return total_rev, solar_rev, bess_rev


def _days_in_month(d: date) -> int:
    """Return number of days in the month of the given date."""
    if d.month == 12:
        next_month = date(d.year + 1, 1, 1)
    else:
        next_month = date(d.year, d.month + 1, 1)
    return (next_month - date(d.year, d.month, 1)).days


# =============================================================================
# OPEX
# =============================================================================

def calc_opex(inputs: FinancialInputs, dates: np.ndarray,
              is_operations: np.ndarray, revenue: np.ndarray
              ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate monthly OPEX (GBPk, expressed as negative values).

    Solar OPEX = sum of fixed costs (GBP/kWp/Yr) × MWp × 1000 / 12 / 1000
               = GBP/kWp/Yr × MWp / 12  (already in GBPk)
    BESS OPEX = sum of costs (GBPk/MW/Yr) × MW / 12

    Returns: (total_opex, solar_opex, bess_opex) as negative GBPk arrays
    """
    n = len(dates)
    solar_opex = np.zeros(n)
    bess_opex = np.zeros(n)

    # Solar fixed OPEX total (GBP/kWp/Yr)
    solar_opex_rate = (
        inputs.opex_pv_om + inputs.opex_grid_conn + inputs.opex_greenkeeping +
        inputs.opex_community + inputs.opex_real_estate_tax + inputs.opex_non_tech_am +
        inputs.opex_subsidy_loss + inputs.opex_insurance + inputs.opex_fixed_lease +
        inputs.opex_corrective_maint + inputs.opex_tech_am
    )

    # Monthly solar fixed OPEX (GBPk) = GBP/kWp/Yr × MWp / 12
    # Because: GBP/kWp/Yr × (MWp × 1000 kWp/MWp) / 12 / 1000 = GBP/kWp/Yr × MWp / 12
    monthly_solar_opex_base = solar_opex_rate * inputs.solar_capacity_mwp / 12

    # BESS OPEX total (GBPk/MW/Yr)
    bess_opex_rate = (
        inputs.bess_opex_om + inputs.bess_opex_import +
        inputs.bess_opex_rates + inputs.bess_opex_lease
    )

    # Monthly BESS OPEX (GBPk) = GBPk/MW/Yr × MW / 12
    monthly_bess_opex_base = bess_opex_rate * inputs.bess_capacity_mw / 12 if inputs.bess_switch else 0

    # Variable OPEX rate (GBP/MWh)
    variable_opex_rate = inputs.opex_social_cost + inputs.opex_balancing_cfd

    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        ops_year = ops_month // 12

        # OPEX escalation (matches revenue indexation)
        escalation = (1 + inputs.indexation_rate / 100) ** ops_year

        # Fixed solar OPEX
        solar_opex[i] = -monthly_solar_opex_base * escalation

        # Variable solar OPEX — based on generation (approximate from revenue)
        # Variable OPEX is small relative to fixed; use monthly gen estimate
        if variable_opex_rate > 0:
            yield_map = {"P50": inputs.yield_p50, "P75": inputs.yield_p75,
                         "P90": inputs.yield_p90}
            annual_yield = yield_map.get(inputs.generation_selection, inputs.yield_p90)
            month_idx = dates[i].month - 1
            season = inputs.seasonality[month_idx] if len(inputs.seasonality) == 12 else 1/12
            degrad = max(1.0 - (inputs.degradation_pct / 100) * ops_year, 0.0)
            monthly_gen = inputs.solar_capacity_mwp * annual_yield * season * degrad
            solar_opex[i] -= monthly_gen * variable_opex_rate * escalation / 1000

        # BESS OPEX (within operating life)
        if inputs.bess_switch and ops_year < inputs.bess_operating_life:
            bess_opex[i] = -monthly_bess_opex_base * escalation

        # Land lease OPEX
        if inputs.fixed_lease_switch:
            # GBP/Acre/Yr × Acres / 12 / 1000 -> GBPk
            land_fixed = inputs.fixed_lease_price * inputs.fixed_lease_acres / 12 / 1000
            solar_opex[i] -= land_fixed * escalation

        if inputs.rev_dep_lease_switch and revenue[i] > 0:
            # Revenue-dependent lease: % of revenue
            rev_share = inputs.rev_share_yr1_10 / 100 if ops_year < 10 else inputs.rev_share_yr11_35 / 100
            solar_opex[i] -= revenue[i] * rev_share

        ops_month += 1

    total_opex = solar_opex + bess_opex
    return total_opex, solar_opex, bess_opex


# =============================================================================
# CAPEX
# =============================================================================

def calc_capex(inputs: FinancialInputs, dates: np.ndarray,
               is_construction: np.ndarray) -> np.ndarray:
    """
    Calculate monthly CAPEX (GBPk, negative values during construction).

    Total CAPEX = sum of all line items (GBP/kWp) × solar_capacity (MWp)
                  × (1 + contingency%)
    Phased evenly over construction months.

    Returns: CAPEX array (negative GBPk)
    """
    n = len(dates)
    capex = np.zeros(n)

    # Sum all CAPEX line items (GBP/kWp)
    capex_per_kwp = (
        inputs.capex_epc + inputs.capex_grid + inputs.capex_development +
        inputs.capex_acquisition + inputs.capex_dd + inputs.capex_discharge +
        inputs.capex_sdlt + inputs.capex_land_legal + inputs.capex_other_finance +
        inputs.capex_other_legal + inputs.capex_land_purchase + inputs.capex_ampyr_tech +
        inputs.capex_success_fee + inputs.capex_community + inputs.capex_bess +
        inputs.capex_landowner_fees + inputs.capex_insurance +
        inputs.capex_land_lease_constr + inputs.capex_asset_adoption +
        inputs.capex_others + inputs.capex_misc
    )

    # Total CAPEX (GBPk) = GBP/kWp × MWp × 1000 kWp/MWp / 1000 GBP->GBPk
    #                     = GBP/kWp × MWp
    total_capex = capex_per_kwp * inputs.solar_capacity_mwp
    total_capex *= (1 + inputs.capex_contingency_pct / 100)

    # Construction rent
    if inputs.construction_rent_sw and inputs.fixed_lease_acres > 0:
        constr_rent_total = (inputs.construction_rent * inputs.fixed_lease_acres *
                             inputs.construction_months / 12 / 1000)
        total_capex += constr_rent_total

    # Phase evenly over construction months
    construction_month_count = int(is_construction.sum())
    if construction_month_count > 0:
        monthly_capex = total_capex / construction_month_count
        capex[is_construction] = -monthly_capex

    return capex


# =============================================================================
# DEPRECIATION
# =============================================================================

def calc_depreciation(inputs: FinancialInputs, dates: np.ndarray,
                      is_operations: np.ndarray, capex: np.ndarray) -> np.ndarray:
    """
    Calculate monthly tax depreciation (GBPk).

    Uses straight-line depreciation over project life for the total CAPEX.
    The Excel model has 3 accounts; for A1 we use a single-account simplification.

    Returns: Monthly depreciation charge (positive values)
    """
    n = len(dates)
    depreciation = np.zeros(n)

    total_capex = abs(capex.sum())  # Positive value
    if total_capex <= 0:
        return depreciation

    # Straight-line over project life
    ops_months = inputs.project_life_years * 12
    monthly_depr = total_capex / ops_months

    for i in range(n):
        if is_operations[i]:
            depreciation[i] = monthly_depr

    return depreciation


# =============================================================================
# TAX
# =============================================================================

def calc_ungeared_tax(inputs: FinancialInputs, dates: np.ndarray,
                      is_operations: np.ndarray,
                      ebitda: np.ndarray, depreciation: np.ndarray) -> np.ndarray:
    """
    Calculate ungeared corporate tax (GBPk, negative = tax paid).

    Two-tier UK corporate tax:
      - Low rate on taxable income up to threshold
      - High rate on excess above threshold
    Tax loss carry-forward: losses offset future taxable income.
    Tax paid in the taxation month (cashflow basis).

    Mirrors D&T sheet rows 242-265.

    Returns: Monthly tax paid array (negative GBPk, paid in taxation_month)
    """
    n = len(dates)
    tax_paid = np.zeros(n)

    rate_low = inputs.corp_tax_rate_low / 100
    rate_high = inputs.corp_tax_rate_high / 100
    threshold = inputs.corp_tax_threshold  # GBPk (annual)
    tax_month = inputs.taxation_month  # 1-12

    # Monthly taxable income = EBITDA - depreciation
    monthly_taxable = ebitda - depreciation

    # Accumulate annual taxable income and apply tax with loss carry-forward
    loss_pool = 0.0  # Accumulated tax losses
    annual_taxable_accum = 0.0
    current_fiscal_year_start = None

    for i in range(n):
        if not is_operations[i]:
            continue

        d = dates[i]

        # Track fiscal year (April to March for UK, but we use calendar year
        # aligned to taxation_month for simplicity matching Excel)
        if current_fiscal_year_start is None:
            current_fiscal_year_start = d

        annual_taxable_accum += monthly_taxable[i]

        # Tax is assessed and paid in the taxation month
        if d.month == tax_month:
            # Net taxable after loss utilisation
            if annual_taxable_accum < 0:
                # Generate loss
                loss_pool += abs(annual_taxable_accum)
                annual_taxable_accum = 0.0
            else:
                # Use losses
                if loss_pool > 0:
                    loss_used = min(loss_pool, annual_taxable_accum)
                    annual_taxable_accum -= loss_used
                    loss_pool -= loss_used

                # Two-tier tax calculation (annual basis)
                if annual_taxable_accum > 0:
                    if annual_taxable_accum <= threshold:
                        tax_amount = annual_taxable_accum * rate_low
                    else:
                        tax_amount = (threshold * rate_low +
                                      (annual_taxable_accum - threshold) * rate_high)
                    tax_paid[i] = -tax_amount

            # Reset annual accumulator
            annual_taxable_accum = 0.0
            current_fiscal_year_start = None

    return tax_paid


# =============================================================================
# NET WORKING CAPITAL
# =============================================================================

def calc_nwc(inputs: FinancialInputs, dates: np.ndarray,
             is_operations: np.ndarray,
             revenue: np.ndarray, opex: np.ndarray) -> np.ndarray:
    """
    Calculate net working capital adjustment (GBPk).

    NWC = Debtors (receivables) - Creditors (payables)
    Change in NWC affects cash flow: increase in NWC = cash outflow.

    Debtors = revenue × debtors_days / 365
    Creditors = |opex| × creditors_days / 365

    Returns: Monthly NWC change array (negative = cash outflow)
    """
    n = len(dates)
    nwc_change = np.zeros(n)

    if inputs.wc_debtors_days == 0 and inputs.wc_creditors_days == 0:
        return nwc_change

    prev_nwc = 0.0
    for i in range(n):
        if not is_operations[i]:
            continue

        # Annualise current month to estimate NWC balance
        debtors = revenue[i] * 12 * inputs.wc_debtors_days / 365
        creditors = abs(opex[i]) * 12 * inputs.wc_creditors_days / 365
        current_nwc = debtors - creditors

        # Change in NWC (increase = cash outflow = negative)
        nwc_change[i] = -(current_nwc - prev_nwc)
        prev_nwc = current_nwc

    return nwc_change


# =============================================================================
# XIRR SOLVER
# =============================================================================

def calc_xirr(dates: np.ndarray, cashflows: np.ndarray,
              guess: float = 0.1, tol: float = 1e-8,
              max_iter: int = 200) -> float:
    """
    Calculate XIRR (extended IRR with irregular dates).

    Uses Newton's method (no scipy dependency).
    Matches Excel XIRR function behavior.

    Args:
        dates: Array of date objects
        cashflows: Array of cashflows (GBPk)
        guess: Initial rate guess
        tol: Convergence tolerance
        max_iter: Maximum iterations

    Returns: IRR as decimal (e.g. 0.085 = 8.5%), or NaN if non-convergent
    """
    # Filter to non-zero cashflows for efficiency
    mask = cashflows != 0
    if mask.sum() < 2:
        return np.nan

    cf = cashflows[mask]
    dt = dates[mask]

    # Day fractions from first date
    d0 = dt[0]
    day_fracs = np.array([(d - d0).days / 365.25 for d in dt])

    def npv_func(rate):
        if rate <= -1:
            return np.inf
        return np.sum(cf / (1 + rate) ** day_fracs)

    def npv_deriv(rate):
        if rate <= -1:
            return np.inf
        return np.sum(-day_fracs * cf / (1 + rate) ** (day_fracs + 1))

    # Newton's method
    rate = guess
    for _ in range(max_iter):
        f_val = npv_func(rate)
        f_deriv = npv_deriv(rate)

        if abs(f_deriv) < 1e-14:
            # Try bisection fallback
            return _xirr_bisection(cf, day_fracs, tol)

        new_rate = rate - f_val / f_deriv

        # Bound check
        if new_rate <= -1:
            new_rate = -0.99

        if abs(new_rate - rate) < tol:
            return new_rate

        rate = new_rate

    # Newton didn't converge, try bisection
    return _xirr_bisection(cf, day_fracs, tol)


def _xirr_bisection(cashflows: np.ndarray, day_fracs: np.ndarray,
                     tol: float = 1e-8) -> float:
    """Bisection fallback for XIRR when Newton fails."""
    def npv_at(rate):
        if rate <= -1:
            return np.inf
        return np.sum(cashflows / (1 + rate) ** day_fracs)

    lo, hi = -0.99, 10.0

    f_lo = npv_at(lo)
    f_hi = npv_at(hi)

    if f_lo * f_hi > 0:
        return np.nan  # No sign change — no root in bracket

    for _ in range(500):
        mid = (lo + hi) / 2
        f_mid = npv_at(mid)

        if abs(f_mid) < tol or (hi - lo) / 2 < tol:
            return mid

        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    return (lo + hi) / 2


def calc_xnpv(dates: np.ndarray, cashflows: np.ndarray, rate: float) -> float:
    """
    Calculate XNPV (extended NPV with irregular dates).

    Args:
        dates: Array of date objects
        cashflows: Array of cashflows (GBPk)
        rate: Discount rate (decimal, e.g. 0.08 = 8%)

    Returns: NPV in GBPk
    """
    if len(dates) == 0:
        return 0.0

    d0 = dates[0]
    day_fracs = np.array([(d - d0).days / 365.25 for d in dates])

    return np.sum(cashflows / (1 + rate) ** day_fracs)


# =============================================================================
# MAIN ENGINE
# =============================================================================

def run_financial_model(inputs: FinancialInputs) -> FinancialResults:
    """
    Run the complete ungeared Project IRR calculation.

    FCFF chain (mirrors Equity sheet rows 150-162):
      Row 150: Revenue (FS!row27)
      Row 151: OPEX (FS!row59)
      Row 152: NWC adjustment (FS!row61)
      Row 153: CAPEX (FS!rows69:89)
      Row 154: MRA (FS!row144) — deferred to iteration A4
      Row 155: Ungeared Tax (D&T!row265)
      Row 156: FCFF = sum(150:155)
      Row 162: XIRR(FCFF, dates)

    Returns: FinancialResults with all monthly arrays and summary metrics
    """
    results = FinancialResults()

    # 1. Build timeline
    dates, is_construction, is_operations = build_timeline(inputs)
    n = len(dates)
    results.dates = dates

    # 2. CAPEX (during construction)
    capex = calc_capex(inputs, dates, is_construction)
    results.capex = capex
    results.total_capex = abs(capex.sum())

    # 3. Revenue (during operations)
    revenue, solar_rev, bess_rev = calc_revenue(inputs, dates, is_operations)
    results.revenue = revenue
    results.solar_revenue = solar_rev
    results.bess_revenue = bess_rev
    results.total_revenue_lifetime = revenue.sum()

    # 4. OPEX (during operations)
    opex, solar_opex, bess_opex = calc_opex(inputs, dates, is_operations, revenue)
    results.opex = opex
    results.solar_opex = solar_opex
    results.bess_opex = bess_opex
    results.total_opex_lifetime = abs(opex.sum())

    # 5. EBITDA = Revenue + OPEX (OPEX is negative)
    ebitda = revenue + opex
    results.ebitda = ebitda

    # 6. Depreciation
    depreciation = calc_depreciation(inputs, dates, is_operations, capex)
    results.depreciation = depreciation

    # 7. Tax
    tax = calc_ungeared_tax(inputs, dates, is_operations, ebitda, depreciation)
    results.tax = tax

    # 8. NWC
    nwc = calc_nwc(inputs, dates, is_operations, revenue, opex)
    results.nwc = nwc

    # 9. FCFF = Revenue + OPEX + NWC + CAPEX + Tax
    # (OPEX, CAPEX, Tax are already negative; NWC can be +/-)
    fcff = revenue + opex + nwc + capex + tax
    results.fcff = fcff
    results.fcff_cumulative = np.cumsum(fcff)

    # 10. Payback month
    cumulative = results.fcff_cumulative
    payback_indices = np.where(cumulative > 0)[0]
    if len(payback_indices) > 0:
        results.payback_month = int(payback_indices[0])

    # 11. XIRR
    results.project_irr = calc_xirr(dates, fcff)

    # 12. XNPV
    discount_rate = inputs.project_discount_rate / 100
    results.project_npv = calc_xnpv(dates, fcff, discount_rate)

    return results


# =============================================================================
# HELPER: Create inputs from wizard state
# =============================================================================

def inputs_from_wizard_state(fin: dict) -> FinancialInputs:
    """
    Convert wizard_state financial section dict to FinancialInputs dataclass.

    Handles date conversion, seasonality array construction, etc.
    """
    from datetime import date as dt_date

    def to_date(val, default):
        if val is None:
            return default
        if isinstance(val, dt_date):
            return val
        if isinstance(val, str):
            parts = val.split('-')
            return dt_date(int(parts[0]), int(parts[1]), int(parts[2]))
        return default

    # Build seasonality array
    month_names = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    seasonality = [fin.get(f'seasonality_{m}', 1/12) for m in month_names]

    inputs = FinancialInputs(
        # Timing
        model_start=to_date(fin.get('model_start'), date(2024, 7, 1)),
        construction_start=to_date(fin.get('construction_start'), date(2026, 1, 1)),
        construction_months=int(fin.get('construction_months', 18)),
        cod_date=to_date(fin.get('cod_date'), date(2027, 7, 1)),
        project_life_years=int(fin.get('project_life_years', 35)),

        # Solar
        solar_capacity_mwp=float(fin.get('solar_capacity_mwp', 82.0)),
        yield_p50=float(fin.get('yield_p50', 967.0)),
        yield_p75=float(fin.get('yield_p75', 936.0)),
        yield_p90=float(fin.get('yield_p90', 895.0)),
        generation_selection=fin.get('generation_selection', 'P90'),
        degradation_pct=float(fin.get('degradation_pct', 0.3)),
        seasonality=seasonality,
        outage_selection=int(fin.get('outage_selection', 0)),
        outage_month=int(fin.get('outage_month_idx', 0)) + 1,
        outage_length_days=int(fin.get('outage_length_days', 14)),

        # BESS
        bess_switch=int(fin.get('bess_switch', 1)),
        bess_capacity_mw=float(fin.get('bess_capacity_mw', 62.5)),
        bess_duration_hrs=float(fin.get('bess_duration_hrs', 4.0)),
        bess_operating_life=int(fin.get('bess_operating_life', 15)),
        bess_degradation_pct=float(fin.get('bess_degradation_pct', 2.5)),
        bess_merchant_switch=int(fin.get('bess_merchant_switch', 1)),
        bess_scenario=int(fin.get('bess_scenario', 1)),
        bess_merchant_discount=float(fin.get('bess_merchant_discount', 5.0)),
        bess_floor_switch=int(fin.get('bess_floor_switch', 1)),
        bess_floor_price=float(fin.get('bess_floor_price', 40.0)),
        bess_floor_rev_share=float(fin.get('bess_floor_rev_share', 10.0)),
        bess_floor_tenor=int(fin.get('bess_floor_tenor', 10)),

        # PPA
        ppa_selection=int(fin.get('ppa_selection', 1)),
        ppa_indexation=fin.get('ppa_indexation', 'CPI'),
        ppa_flex_pct=float(fin.get('ppa_flex_pct', 0.0)),

        # REGOs
        rego_switch=int(fin.get('rego_switch', 1)),
        rego_price=float(fin.get('rego_price', 5.0)),
        rego_indexation=fin.get('rego_indexation', 'CPI'),
        rego_tenor_years=int(fin.get('rego_tenor_years', 15)),

        # CM
        cm_t1_value=float(fin.get('cm_t1_value', 20.0)),
        cm_t1_derating=float(fin.get('cm_t1_derating', 27.15)),
        cm_t1_tenor=int(fin.get('cm_t1_tenor', 1)),
        cm_t4_value=float(fin.get('cm_t4_value', 0.0)),
        cm_t4_derating=float(fin.get('cm_t4_derating', 0.0)),
        cm_t4_tenor=int(fin.get('cm_t4_tenor', 0)),

        # CAPEX
        capex_epc=float(fin.get('capex_epc', 400.0)),
        capex_grid=float(fin.get('capex_grid', 30.0)),
        capex_development=float(fin.get('capex_development', 15.0)),
        capex_acquisition=float(fin.get('capex_acquisition', 0.0)),
        capex_dd=float(fin.get('capex_dd', 5.0)),
        capex_discharge=float(fin.get('capex_discharge', 0.0)),
        capex_sdlt=float(fin.get('capex_sdlt', 0.0)),
        capex_land_legal=float(fin.get('capex_land_legal', 2.0)),
        capex_other_finance=float(fin.get('capex_other_finance', 0.0)),
        capex_other_legal=float(fin.get('capex_other_legal', 2.0)),
        capex_land_purchase=float(fin.get('capex_land_purchase', 0.0)),
        capex_ampyr_tech=float(fin.get('capex_ampyr_tech', 0.0)),
        capex_success_fee=float(fin.get('capex_success_fee', 0.0)),
        capex_community=float(fin.get('capex_community', 0.0)),
        capex_bess=float(fin.get('capex_bess', 80.0)),
        capex_landowner_fees=float(fin.get('capex_landowner_fees', 0.0)),
        capex_insurance=float(fin.get('capex_insurance', 3.0)),
        capex_land_lease_constr=float(fin.get('capex_land_lease_constr', 0.0)),
        capex_asset_adoption=float(fin.get('capex_asset_adoption', 0.0)),
        capex_others=float(fin.get('capex_others', 0.0)),
        capex_misc=float(fin.get('capex_misc', 0.0)),
        capex_contingency_pct=float(fin.get('capex_contingency_pct', 1.0)),

        # Solar OPEX
        opex_pv_om=float(fin.get('opex_pv_om', 5.48)),
        opex_grid_conn=float(fin.get('opex_grid_conn', 1.5)),
        opex_greenkeeping=float(fin.get('opex_greenkeeping', 0.5)),
        opex_community=float(fin.get('opex_community', 0.0)),
        opex_real_estate_tax=float(fin.get('opex_real_estate_tax', 1.0)),
        opex_non_tech_am=float(fin.get('opex_non_tech_am', 1.0)),
        opex_subsidy_loss=float(fin.get('opex_subsidy_loss', 0.0)),
        opex_insurance=float(fin.get('opex_insurance', 2.02)),
        opex_fixed_lease=float(fin.get('opex_fixed_lease', 0.0)),
        opex_corrective_maint=float(fin.get('opex_corrective_maint', 3.2)),
        opex_tech_am=float(fin.get('opex_tech_am', 1.5)),
        opex_social_cost=float(fin.get('opex_social_cost', 0.0)),
        opex_balancing_cfd=float(fin.get('opex_balancing_cfd', 0.0)),

        # BESS OPEX
        bess_opex_om=float(fin.get('bess_opex_om', 7.06)),
        bess_opex_import=float(fin.get('bess_opex_import', 0.0)),
        bess_opex_rates=float(fin.get('bess_opex_rates', 0.0)),
        bess_opex_lease=float(fin.get('bess_opex_lease', 0.0)),

        # Land
        fixed_lease_switch=int(fin.get('fixed_lease_switch', 0)),
        fixed_lease_acres=float(fin.get('fixed_lease_acres', 200.0)),
        fixed_lease_price=float(fin.get('fixed_lease_price', 800.0)),
        rev_dep_lease_switch=int(fin.get('rev_dep_lease_switch', 0)),
        rev_share_yr1_10=float(fin.get('rev_share_yr1_10', 5.0)),
        rev_share_yr11_35=float(fin.get('rev_share_yr11_35', 7.5)),
        construction_rent_sw=int(fin.get('construction_rent_sw', 0)),
        construction_rent=float(fin.get('construction_rent', 500.0)),

        # Tax
        corp_tax_rate_low=float(fin.get('corp_tax_rate_low', 19.0)),
        corp_tax_rate_high=float(fin.get('corp_tax_rate_high', 25.0)),
        corp_tax_threshold=float(fin.get('corp_tax_threshold', 250.0)),
        taxation_month=int(fin.get('taxation_month', 12)),

        # Working Capital
        wc_debtors_days=int(fin.get('wc_debtors_days', 45)),
        wc_creditors_days=int(fin.get('wc_creditors_days', 30)),

        # Financial
        project_discount_rate=float(fin.get('project_discount_rate', 8.0)),
        cost_of_capital=float(fin.get('cost_of_capital', 6.0)),
    )

    return inputs
