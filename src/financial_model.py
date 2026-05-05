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


# =============================================================================
# TARIFF-BASED MODEL (Data Centre PPA — Off-Grid Solution v8)
# =============================================================================

@dataclass
class TariffModelInputs:
    """Inputs for tariff-based Solar+BESS financial model (DC PPA mode)."""

    # Timing
    construction_start: date = field(default_factory=lambda: date(2026, 10, 1))
    construction_months: int = 9
    cod_date: date = field(default_factory=lambda: date(2027, 7, 1))
    project_life_years: int = 35

    # Solar
    solar_capacity_mwp: float = 82.0
    yield_p50: float = 967.0
    yield_p75: float = 936.0
    yield_p90: float = 895.0
    generation_selection: str = "P50"
    degradation_pct: float = 0.003  # decimal (0.003 = 0.3%)
    seasonality: list = field(default_factory=lambda: [1/12]*12)

    # BESS
    bess_switch: int = 1
    bess_capacity_mw: float = 62.5
    bess_duration_hrs: float = 4.0
    bess_operating_life: int = 10

    # PPA & Tariff
    tariff_gbp_mwh: float = 170.0
    ppa_tenor_years: int = 10
    tariff_escalation: float = 0.0

    # Merchant (post-PPA solar)
    merchant_prices: dict = field(default_factory=dict)  # {year: GBP/MWh}
    merchant_price_default: float = 67.0

    # REGOs
    rego_switch: int = 1
    rego_price: float = 2.5
    rego_tenor: int = 35

    # Embedded benefits (GBP/MWh, 12 monthly values)
    emb_switch: int = 1
    emb_benefits: list = field(default_factory=lambda: [
        5.38, 6.27, 8.31, 8.19, 9.40, 10.38, 10.78, 10.05, 7.54, 5.95, 5.37, 5.37
    ])
    emb_tenor: int = 15

    # CAPEX (GBP/kWp)
    capex_items_sum: float = 0.0  # pre-computed sum of all line items
    capex_contingency_pct: float = 0.01  # decimal

    # OPEX
    solar_opex_rate: float = 0.0  # GBP/kWp/Yr (pre-computed sum)
    bess_opex_rate: float = 0.0   # GBPk/MW/Yr (pre-computed sum)
    opex_variable_rate: float = 0.0  # GBP/MWh
    land_fixed_lease_annual: float = 0.0  # GBPk/yr
    rev_dep_lease_pct: float = 0.0  # decimal

    # Tax
    corp_tax_rate: float = 0.25
    taxation_month: int = 12

    # Debt (for geared tax)
    gearing: float = 0.80
    interest_rate: float = 0.04  # SWAP + margin
    debt_tenor_years: int = 15

    # Discount
    discount_rate: float = 0.065


def run_tariff_model(
    inputs: TariffModelInputs,
    monthly_solar_bess_to_dc: np.ndarray,
    monthly_surplus: np.ndarray,
    monthly_solar_gen: np.ndarray,
) -> FinancialResults:
    """
    Run Solar+BESS FCFF with tariff-based revenue (Data Centre PPA mode).

    Revenue structure:
    - PPA period: tariff × solar_bess_to_dc + surplus × merchant_price + REGO
    - Post-PPA: net_pv_gen × merchant_price + REGO
    - BESS standalone revenue: zeroed (captured via PPA delivery)

    Tax: geared (after interest deduction from debt).

    Args:
        inputs: TariffModelInputs
        monthly_solar_bess_to_dc: 12-element array (year 1 MWh delivered to DC per month)
        monthly_surplus: 12-element array (year 1 surplus MWh per month)
        monthly_solar_gen: 12-element array (year 1 total solar MWh per month)

    Returns: FinancialResults with FCFF and IRR
    """
    results = FinancialResults()

    # Build timeline
    total_months = _months_between(inputs.construction_start, inputs.cod_date) + \
                   inputs.project_life_years * 12
    dates = []
    d = inputs.construction_start
    for _ in range(total_months):
        dates.append(d)
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)
    dates = np.array(dates)

    is_construction = np.array([
        inputs.construction_start <= d < inputs.cod_date for d in dates
    ])
    is_operations = np.array([d >= inputs.cod_date for d in dates])

    n = len(dates)
    results.dates = dates

    ppa_end = date(inputs.cod_date.year + inputs.ppa_tenor_years,
                   inputs.cod_date.month, 1)
    bess_end = date(inputs.cod_date.year + inputs.bess_operating_life,
                    inputs.cod_date.month, 1)

    # =================================================================
    # CAPEX
    # =================================================================
    capex = np.zeros(n)
    total_capex = inputs.capex_items_sum * inputs.solar_capacity_mwp
    total_capex *= (1 + inputs.capex_contingency_pct)
    constr_count = int(is_construction.sum())
    if constr_count > 0:
        capex[is_construction] = -total_capex / constr_count
    results.capex = capex
    results.total_capex = total_capex

    # =================================================================
    # REVENUE
    # =================================================================
    revenue = np.zeros(n)
    solar_rev = np.zeros(n)
    bess_rev = np.zeros(n)  # zeroed in DC PPA mode

    # Annual base generation = capacity × yield
    yield_map = {"P50": inputs.yield_p50, "P75": inputs.yield_p75, "P90": inputs.yield_p90}
    annual_yield = yield_map.get(inputs.generation_selection, inputs.yield_p50)
    base_annual_gen = inputs.solar_capacity_mwp * annual_yield

    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        ops_year = ops_month // 12
        month_idx = dates[i].month - 1

        # Degradation
        degrad = max(1.0 - inputs.degradation_pct * ops_year, 0.0) if ops_year > 0 else 1.0

        # Tariff escalation
        tariff_esc = (1 + inputs.tariff_escalation) ** ops_year

        if dates[i] < ppa_end:
            # --- PPA period ---
            # Solar+BESS to DC energy (degraded)
            dc_energy = monthly_solar_bess_to_dc[month_idx] * degrad
            ppa_rev = inputs.tariff_gbp_mwh * tariff_esc * dc_energy / 1000

            # Surplus solar × merchant
            surplus = monthly_surplus[month_idx] * degrad
            merchant_price = _get_merchant_price(inputs, dates[i].year)
            surplus_rev = surplus * merchant_price / 1000

            solar_rev[i] = ppa_rev + surplus_rev
        else:
            # --- Post-PPA (merchant period) ---
            # All solar generation at merchant price
            monthly_gen = base_annual_gen * inputs.seasonality[month_idx] * degrad
            merchant_price = _get_merchant_price(inputs, dates[i].year)
            solar_rev[i] = monthly_gen * merchant_price / 1000

        # Monthly generation for REGO and embedded benefits
        monthly_gen_formula = base_annual_gen * inputs.seasonality[month_idx] * degrad

        # REGO revenue (on all solar generation, throughout project life)
        if inputs.rego_switch and ops_year < inputs.rego_tenor:
            solar_rev[i] += monthly_gen_formula * inputs.rego_price / 1000

        # Embedded benefits (11kV) — applied to generation, with tenor limit
        if inputs.emb_switch and ops_year < inputs.emb_tenor and len(inputs.emb_benefits) == 12:
            emb_rate = inputs.emb_benefits[month_idx]  # GBP/MWh
            solar_rev[i] += monthly_gen_formula * emb_rate / 1000

        revenue[i] = solar_rev[i]
        ops_month += 1

    results.revenue = revenue
    results.solar_revenue = solar_rev
    results.bess_revenue = bess_rev
    results.total_revenue_lifetime = revenue.sum()

    # =================================================================
    # OPEX
    # =================================================================
    opex = np.zeros(n)
    solar_opex = np.zeros(n)
    bess_opex = np.zeros(n)

    monthly_solar_opex_base = inputs.solar_opex_rate * inputs.solar_capacity_mwp / 12
    monthly_bess_opex_base = inputs.bess_opex_rate * inputs.bess_capacity_mw / 12

    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        ops_year = ops_month // 12

        # Solar fixed OPEX (no escalation — "real" values per Excel)
        solar_opex[i] = -monthly_solar_opex_base

        # Variable OPEX
        if inputs.opex_variable_rate > 0:
            degrad = max(1.0 - inputs.degradation_pct * ops_year, 0.0) if ops_year > 0 else 1.0
            monthly_gen = base_annual_gen * inputs.seasonality[dates[i].month - 1] * degrad
            solar_opex[i] -= monthly_gen * inputs.opex_variable_rate / 1000

        # BESS OPEX (within operating life)
        if inputs.bess_switch and dates[i] < bess_end:
            bess_opex[i] = -monthly_bess_opex_base

        # Land lease
        if inputs.land_fixed_lease_annual > 0:
            solar_opex[i] -= inputs.land_fixed_lease_annual / 12

        # Revenue-dependent lease
        if inputs.rev_dep_lease_pct > 0 and revenue[i] > 0:
            solar_opex[i] -= revenue[i] * inputs.rev_dep_lease_pct

        opex[i] = solar_opex[i] + bess_opex[i]
        ops_month += 1

    results.opex = opex
    results.solar_opex = solar_opex
    results.bess_opex = bess_opex
    results.total_opex_lifetime = abs(opex.sum())

    # =================================================================
    # EBITDA
    # =================================================================
    ebitda = revenue + opex
    results.ebitda = ebitda

    # =================================================================
    # DEPRECIATION (straight-line over project life)
    # =================================================================
    depreciation = np.zeros(n)
    ops_months_total = inputs.project_life_years * 12
    monthly_depr = total_capex / ops_months_total if total_capex > 0 else 0
    for i in range(n):
        if is_operations[i]:
            depreciation[i] = monthly_depr
    results.depreciation = depreciation

    # =================================================================
    # DEBT (interest for geared tax calculation)
    # =================================================================
    debt_balance = total_capex * inputs.gearing
    debt_months = inputs.debt_tenor_years * 12
    monthly_rate = inputs.interest_rate / 12
    interest_arr = np.zeros(n)

    if debt_balance > 0 and monthly_rate > 0 and debt_months > 0:
        annuity = debt_balance * monthly_rate * (1 + monthly_rate) ** debt_months / \
                  ((1 + monthly_rate) ** debt_months - 1)

        ops_month = 0
        for i in range(n):
            if not is_operations[i]:
                continue
            if ops_month < debt_months and debt_balance > 0:
                int_pmt = debt_balance * monthly_rate
                interest_arr[i] = int_pmt
                debt_balance -= (annuity - int_pmt)
                debt_balance = max(debt_balance, 0)
            ops_month += 1

    # =================================================================
    # TAX (geared — after interest deduction)
    # =================================================================
    tax = np.zeros(n)
    taxable_monthly = ebitda - depreciation - interest_arr
    loss_pool = 0.0
    annual_taxable = 0.0

    for i in range(n):
        if not is_operations[i]:
            continue

        annual_taxable += taxable_monthly[i]

        if dates[i].month == inputs.taxation_month:
            if annual_taxable < 0:
                loss_pool += abs(annual_taxable)
            else:
                if loss_pool > 0:
                    used = min(loss_pool, annual_taxable)
                    annual_taxable -= used
                    loss_pool -= used
                if annual_taxable > 0:
                    tax[i] = -annual_taxable * inputs.corp_tax_rate

            annual_taxable = 0.0

    results.tax = tax

    # =================================================================
    # NWC (simplified)
    # =================================================================
    nwc = np.zeros(n)
    results.nwc = nwc

    # =================================================================
    # FCFF
    # =================================================================
    fcff = revenue + opex + nwc + capex + tax
    results.fcff = fcff
    results.fcff_cumulative = np.cumsum(fcff)

    # Payback
    payback_idx = np.where(results.fcff_cumulative > 0)[0]
    if len(payback_idx) > 0:
        results.payback_month = int(payback_idx[0])

    # XIRR
    results.project_irr = calc_xirr(dates, fcff)

    # XNPV
    results.project_npv = calc_xnpv(dates, fcff, inputs.discount_rate)

    return results


def _get_merchant_price(inputs: TariffModelInputs, year: int) -> float:
    """Get merchant price for a given year from the inputs."""
    if inputs.merchant_prices and year in inputs.merchant_prices:
        return inputs.merchant_prices[year]
    if inputs.merchant_prices:
        years = sorted(inputs.merchant_prices.keys())
        if year < years[0]:
            return inputs.merchant_prices[years[0]]
        if year > years[-1]:
            return inputs.merchant_prices[years[-1]]
        # Interpolate
        for j in range(len(years) - 1):
            if years[j] <= year <= years[j + 1]:
                frac = (year - years[j]) / (years[j + 1] - years[j])
                return inputs.merchant_prices[years[j]] * (1 - frac) + \
                       inputs.merchant_prices[years[j + 1]] * frac
    return inputs.merchant_price_default


def tariff_inputs_from_params(
    sb: dict, overall: dict, tax: dict, debt: dict,
    seasonality: list, merchant_prices: dict,
) -> TariffModelInputs:
    """Create TariffModelInputs from excel_reader parameter dicts."""

    # Sum CAPEX line items (GBP/kWp)
    capex_items = (
        sb['capex_acquisition'] + sb['capex_development'] + sb['capex_discharge'] +
        sb['capex_dd'] + sb['capex_epc'] + sb['capex_grid'] +
        sb['capex_sdlt'] + sb['capex_land_legal'] + sb['capex_other_finance'] +
        sb['capex_other_legal'] + sb['capex_land_purchase'] + sb['capex_ampyr_tech'] +
        sb['capex_success_fee'] + sb['capex_community_capex'] + sb['capex_bess'] +
        sb['capex_landowner_fees'] + sb['capex_insurance_capex'] +
        sb['capex_land_lease_constr'] + sb['capex_asset_adoption'] +
        sb['capex_others'] + sb['capex_misc']
    )

    # Sum Solar OPEX (GBP/kWp/Yr)
    solar_opex = (
        sb['opex_pv_om'] + sb['opex_grid_conn'] + sb['opex_greenkeeping'] +
        sb['opex_community'] + sb['opex_real_estate_tax'] + sb['opex_non_tech_am'] +
        sb['opex_subsidy_loss'] + sb['opex_insurance'] +
        sb['opex_corrective_maint'] + sb['opex_tech_am']
    )

    # Sum BESS OPEX (GBPk/MW/Yr)
    bess_opex = (
        sb['bess_opex_om'] + sb['bess_opex_import'] +
        sb['bess_opex_rates'] + sb['bess_opex_lease']
    )

    # Land lease annual cost (GBPk)
    land_lease = 0.0
    if sb['fixed_lease_switch']:
        land_lease = sb['fixed_lease_price'] * sb['fixed_lease_acres'] / 1000

    # Revenue-dependent lease
    rev_dep = 0.0
    if sb['rev_dep_lease_switch']:
        rev_dep = sb['rev_share_yr1_10']  # already decimal

    return TariffModelInputs(
        construction_start=sb['construction_start'],
        construction_months=sb['construction_months'],
        cod_date=sb['cod_date'],
        project_life_years=sb['project_life_years'],
        solar_capacity_mwp=sb['solar_capacity_mwp'],
        yield_p50=sb['yield_p50'],
        yield_p75=sb['yield_p75'],
        yield_p90=sb['yield_p90'],
        generation_selection=sb['generation_selection'],
        degradation_pct=sb['degradation_pct'],
        seasonality=seasonality,
        bess_switch=sb['bess_switch'],
        bess_capacity_mw=sb['bess_capacity_mw'],
        bess_duration_hrs=sb['bess_duration_hrs'],
        bess_operating_life=sb['bess_operating_life'],
        tariff_gbp_mwh=overall['tariff_gbp_mwh'],
        ppa_tenor_years=overall['ppa_tenor_years'],
        tariff_escalation=overall['tariff_escalation'],
        merchant_prices=merchant_prices,
        rego_switch=sb['rego_switch'],
        rego_price=sb['rego_price'],
        rego_tenor=sb['rego_tenor'],
        emb_switch=sb.get('emb_switch', 1),
        emb_benefits=sb.get('emb_benefits', [5.38, 6.27, 8.31, 8.19, 9.40, 10.38, 10.78, 10.05, 7.54, 5.95, 5.37, 5.37]),
        emb_tenor=sb.get('emb_tenor', 15),
        capex_items_sum=capex_items,
        capex_contingency_pct=sb['capex_contingency_pct'],
        solar_opex_rate=solar_opex,
        bess_opex_rate=bess_opex,
        opex_variable_rate=sb['opex_balancing_cfd'],
        land_fixed_lease_annual=land_lease,
        rev_dep_lease_pct=rev_dep,
        corp_tax_rate=tax['corp_tax_rate_low'],
        taxation_month=tax['taxation_month'],
        gearing=debt['sb_gearing'],
        interest_rate=debt['sb_interest_rate'],
        discount_rate=sb['discount_rate'],
    )


def tariff_inputs_from_wizard_state(
    fin: dict, merchant_prices: dict | None = None,
) -> TariffModelInputs:
    """
    Build TariffModelInputs from wizard_state['financial'].

    Mirrors inputs_from_wizard_state but targets the dispatch-driven tariff
    model (run_tariff_model) used by Step 7. Gearing defaults to 0 so the
    output is the ungeared Project IRR (Excel Equity!E181).
    """
    from datetime import date as dt_date

    def to_date(val, default):
        if isinstance(val, dt_date):
            return val
        if isinstance(val, str):
            p = val.split('-')
            return dt_date(int(p[0]), int(p[1]), int(p[2]))
        return default

    month_names = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    seasonality = [fin.get(f'seasonality_{m}', 1/12) for m in month_names]

    capex_items = sum(float(fin.get(k, 0.0)) for k in [
        'capex_acquisition', 'capex_development', 'capex_discharge', 'capex_dd',
        'capex_epc', 'capex_grid', 'capex_sdlt', 'capex_land_legal',
        'capex_other_finance', 'capex_other_legal', 'capex_land_purchase',
        'capex_ampyr_tech', 'capex_success_fee', 'capex_community',
        'capex_bess', 'capex_landowner_fees', 'capex_insurance',
        'capex_land_lease_constr', 'capex_asset_adoption',
        'capex_others', 'capex_misc',
    ])

    solar_opex = sum(float(fin.get(k, 0.0)) for k in [
        'opex_pv_om', 'opex_grid_conn', 'opex_greenkeeping', 'opex_community',
        'opex_real_estate_tax', 'opex_non_tech_am', 'opex_subsidy_loss',
        'opex_insurance', 'opex_corrective_maint', 'opex_tech_am',
    ])

    bess_opex = sum(float(fin.get(k, 0.0)) for k in [
        'bess_opex_om', 'bess_opex_import', 'bess_opex_rates', 'bess_opex_lease',
    ])

    land_lease = 0.0
    if fin.get('fixed_lease_switch'):
        land_lease = (float(fin.get('fixed_lease_price', 0.0))
                      * float(fin.get('fixed_lease_acres', 0.0)) / 1000)

    rev_dep = 0.0
    if fin.get('rev_dep_lease_switch'):
        rev_dep = float(fin.get('rev_share_yr1_10', 0.0)) / 100

    return TariffModelInputs(
        construction_start=to_date(fin.get('construction_start'), date(2026, 10, 1)),
        construction_months=int(fin.get('construction_months', 9)),
        cod_date=to_date(fin.get('cod_date'), date(2027, 7, 1)),
        project_life_years=int(fin.get('project_life_years', 35)),
        solar_capacity_mwp=float(fin.get('solar_capacity_mwp', 82.0)),
        yield_p50=float(fin.get('yield_p50', 967.0)),
        yield_p75=float(fin.get('yield_p75', 936.0)),
        yield_p90=float(fin.get('yield_p90', 895.0)),
        generation_selection=fin.get('generation_selection', 'P50'),
        degradation_pct=float(fin.get('degradation_pct', 0.3)) / 100,
        seasonality=seasonality,
        bess_switch=int(fin.get('bess_switch', 1)),
        bess_capacity_mw=float(fin.get('bess_capacity_mw', 62.5)),
        bess_duration_hrs=float(fin.get('bess_duration_hrs', 4.0)),
        bess_operating_life=int(fin.get('bess_operating_life', 15)),
        tariff_gbp_mwh=float(fin.get('ppa_tariff_gbp_mwh', 170.0)),
        ppa_tenor_years=int(fin.get('ppa_tenor_years', 10)),
        tariff_escalation=float(fin.get('ppa_escalation_pct', 0.0)) / 100,
        merchant_prices=merchant_prices or {},
        merchant_price_default=float(fin.get('merchant_price_default', 67.0)),
        rego_switch=int(fin.get('rego_switch', 1)),
        rego_price=float(fin.get('rego_price', 5.0)),
        rego_tenor=int(fin.get('rego_tenor_years', 15)),
        emb_switch=int(fin.get('emb_switch', 1)),
        emb_tenor=int(fin.get('emb_tenor', 15)),
        capex_items_sum=capex_items,
        capex_contingency_pct=float(fin.get('capex_contingency_pct', 1.0)) / 100,
        solar_opex_rate=solar_opex,
        bess_opex_rate=bess_opex,
        opex_variable_rate=float(fin.get('opex_balancing_cfd', 0.0)),
        land_fixed_lease_annual=land_lease,
        rev_dep_lease_pct=rev_dep,
        corp_tax_rate=float(fin.get('corp_tax_rate_low', 19.0)) / 100,
        taxation_month=int(fin.get('taxation_month', 12)),
        gearing=float(fin.get('debt_gearing', 0.0)),
        interest_rate=float(fin.get('debt_interest_rate', 0.04)),
        debt_tenor_years=int(fin.get('debt_tenor_years', 15)),
        discount_rate=float(fin.get('project_discount_rate', 8.0)) / 100,
    )
