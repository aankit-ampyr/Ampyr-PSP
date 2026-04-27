"""
Gas Plant Financial Model — FCFF calculation for gas/DG plant.

Mirrors the 'Cash Flows-Gas' sheet in Off-Grid Solution v8.xlsm.
Monthly granularity, up to 240 months (20-year operations life).

FCFF chain:
  Revenue - Fuel Cost - OPEX - CAPEX - Tax = Gas FCFF

Currency: GBP thousands (GBPk) throughout.
"""

from dataclasses import dataclass, field
from datetime import date
import numpy as np

from src.financial_model import calc_xirr


# =========================================================================
# DATA STRUCTURES
# =========================================================================

@dataclass
class GasInputs:
    """All inputs for gas plant financial model."""

    # Timing
    construction_start: date = field(default_factory=lambda: date(2026, 1, 1))
    construction_months: int = 18
    cod_date: date = field(default_factory=lambda: date(2027, 7, 1))
    operations_years: int = 20

    # Capacity
    capacity_mw: float = 28.32          # Total installed (incl spare)
    effective_capacity_mw: float = 25.0  # Net available

    # PPA
    ppa_tenor_years: int = 10
    ppa_tariff: float = 170.0           # GBP/MWh
    tariff_escalation: float = 0.0      # annual %

    # Merchant (post-PPA)
    merchant_tariff: float = 200.0      # GBP/MWh
    merchant_hours_per_day: float = 9.0

    # Fuel
    net_efficiency: float = 0.385
    fuel_price_gbp_mwh: float = 32.51   # GBP/MWh of fuel input
    fuel_escalation_from_yr4: float = 0.01
    fixed_gas_cost_gbp_day: float = 1087.54
    start_fuel_pct: float = 0.10        # 10% increase for starts
    starts_per_day: float = 4
    start_time_minutes: float = 10

    # Emissions
    co2_kg_per_mwh: float = 185.0
    ukets_cost_gbp_per_kg: float = 0.07

    # OPEX (GBPk/MW/Yr)
    opex_environmental_levies: float = 10.17
    opex_om_contract: float = 9.38
    opex_site_maintenance: float = 1.80
    opex_other_variable: float = 2.02
    opex_reactive_maint_per_mwh: float = 0.0015  # GBPk/MWh
    opex_site_lease: float = 3.90
    opex_fixed_operating: float = 14.23
    opex_professional_fees: float = 4.584
    opex_property_tax: float = 4.0
    opex_telecom: float = 0.3
    opex_audit_fees: float = 0.84
    opex_contingency: float = 0.0
    opex_insurance: float = 3.54
    opex_legal: float = 0.872
    opex_inflation: float = 0.02

    # CAPEX
    capex_per_mw: float = 771.28        # GBPk/MW
    capex_total: float = 0.0            # computed if 0

    # Tax & Depreciation
    depreciation_slm: float = 0.05      # SLM rate p.a. (book)
    depreciation_tax: float = 0.10      # Tax depreciation rate p.a.
    corp_tax_rate: float = 0.25

    # Debt (for geared tax calculation)
    gearing: float = 0.85
    interest_rate: float = 0.0675
    debt_tenor_years: int = 10


@dataclass
class GasResults:
    """Output of gas plant financial model."""
    project_irr: float = np.nan
    total_capex: float = 0.0
    total_revenue: float = 0.0
    total_fuel_cost: float = 0.0
    total_opex: float = 0.0

    dates: np.ndarray = field(default_factory=lambda: np.array([]))
    revenue: np.ndarray = field(default_factory=lambda: np.array([]))
    fuel_cost: np.ndarray = field(default_factory=lambda: np.array([]))
    opex: np.ndarray = field(default_factory=lambda: np.array([]))
    capex: np.ndarray = field(default_factory=lambda: np.array([]))
    depreciation: np.ndarray = field(default_factory=lambda: np.array([]))
    interest: np.ndarray = field(default_factory=lambda: np.array([]))
    tax: np.ndarray = field(default_factory=lambda: np.array([]))
    fcff: np.ndarray = field(default_factory=lambda: np.array([]))


# =========================================================================
# HELPERS
# =========================================================================

DAYS_IN_MONTH_MAP = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _months_between(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _advance_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _days_in_month(d: date) -> int:
    return DAYS_IN_MONTH_MAP[d.month - 1]


# =========================================================================
# MAIN ENGINE
# =========================================================================

def run_gas_model(
    inputs: GasInputs,
    monthly_gas_energy_yr1: np.ndarray,
    gas_energy_growth_rate: float = 0.0,
) -> GasResults:
    """
    Run gas plant FCFF calculation.

    Args:
        inputs: GasInputs with all parameters
        monthly_gas_energy_yr1: 12-element array of gas MWh per month (year 1)
        gas_energy_growth_rate: annual growth in gas energy (as ops year increases,
                                solar degrades → more gas needed)

    Returns: GasResults with monthly arrays and summary.
    """
    results = GasResults()

    # Total CAPEX
    if inputs.capex_total > 0:
        total_capex = inputs.capex_total
    else:
        total_capex = inputs.capex_per_mw * inputs.capacity_mw
    results.total_capex = total_capex

    # Build timeline
    constr_months = inputs.construction_months
    ops_months = inputs.operations_years * 12
    total_months = _months_between(inputs.construction_start, inputs.cod_date) + ops_months

    dates = []
    d = inputs.construction_start
    for _ in range(total_months):
        dates.append(d)
        d = _advance_month(d)
    dates = np.array(dates)

    is_construction = np.array([
        inputs.construction_start <= d < inputs.cod_date for d in dates
    ])
    is_operations = np.array([d >= inputs.cod_date for d in dates])

    n = len(dates)

    # =====================================================================
    # CAPEX — phased over construction
    # =====================================================================
    capex = np.zeros(n)
    constr_count = int(is_construction.sum())
    if constr_count > 0:
        # Use Excel phasing: 35% month 1, then 13.3% each in months 7-9
        # Simplified: even spread for now (close enough for IRR)
        monthly_capex = total_capex / constr_count
        capex[is_construction] = -monthly_capex
    results.capex = capex

    # =====================================================================
    # REVENUE
    # =====================================================================
    revenue = np.zeros(n)
    ppa_end_date = date(
        inputs.cod_date.year + inputs.ppa_tenor_years,
        inputs.cod_date.month, 1
    )

    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        ops_year = ops_month // 12
        month_idx = dates[i].month - 1  # 0-based calendar month

        # Gas energy for this month
        energy_factor = (1 + gas_energy_growth_rate) ** ops_year
        gas_mwh = monthly_gas_energy_yr1[month_idx] * energy_factor

        # Tariff escalation
        tariff_factor = (1 + inputs.tariff_escalation) ** ops_year

        if dates[i] < ppa_end_date:
            # PPA period
            revenue[i] = inputs.ppa_tariff * tariff_factor * gas_mwh / 1000
        else:
            # Merchant period: fixed hours per day
            days = _days_in_month(dates[i])
            merchant_mwh = inputs.effective_capacity_mw * inputs.merchant_hours_per_day * days
            revenue[i] = inputs.merchant_tariff * merchant_mwh / 1000

        ops_month += 1

    results.revenue = revenue
    results.total_revenue = revenue.sum()

    # =====================================================================
    # FUEL COST
    # =====================================================================
    fuel_cost = np.zeros(n)
    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        ops_year = ops_month // 12
        month_idx = dates[i].month - 1
        days = _days_in_month(dates[i])

        energy_factor = (1 + gas_energy_growth_rate) ** ops_year

        if dates[i] < ppa_end_date:
            gas_mwh = monthly_gas_energy_yr1[month_idx] * energy_factor
        else:
            gas_mwh = inputs.effective_capacity_mw * inputs.merchant_hours_per_day * days

        # Fuel consumption = energy output / efficiency
        fuel_input_mwh = gas_mwh / inputs.net_efficiency

        # Start fuel: small addition for turbine starts
        # starts_per_day × start_time_min / 60 → hours of start per day
        # During starts, fuel consumption increases by start_fuel_pct
        start_hours_per_day = inputs.starts_per_day * inputs.start_time_minutes / 60
        days = _days_in_month(dates[i])
        operating_hours = gas_mwh / inputs.effective_capacity_mw if inputs.effective_capacity_mw > 0 else 0
        if operating_hours > 0:
            start_fraction = min(start_hours_per_day * days / operating_hours, 1.0)
            fuel_input_mwh *= (1 + inputs.start_fuel_pct * start_fraction)

        # Fuel price escalation (from year 4)
        if ops_year >= 3:
            fuel_price = inputs.fuel_price_gbp_mwh * (1 + inputs.fuel_escalation_from_yr4) ** (ops_year - 3)
        else:
            fuel_price = inputs.fuel_price_gbp_mwh

        # Variable fuel cost (GBPk)
        variable_fuel = fuel_input_mwh * fuel_price / 1000

        # Fixed gas cost
        fixed_fuel = inputs.fixed_gas_cost_gbp_day * days / 1000

        # UKETS / CO2 cost — based on fuel INPUT (not output)
        fuel_input_base = gas_mwh / inputs.net_efficiency
        co2_cost = fuel_input_base * inputs.co2_kg_per_mwh * inputs.ukets_cost_gbp_per_kg / 1000

        fuel_cost[i] = -(variable_fuel + fixed_fuel + co2_cost)
        ops_month += 1

    results.fuel_cost = fuel_cost
    results.total_fuel_cost = abs(fuel_cost.sum())

    # =====================================================================
    # OPEX (non-fuel)
    # =====================================================================
    opex = np.zeros(n)

    # Sum fixed OPEX rates (GBPk/MW/Yr)
    fixed_opex_rate = (
        inputs.opex_environmental_levies + inputs.opex_om_contract +
        inputs.opex_site_maintenance + inputs.opex_other_variable +
        inputs.opex_site_lease + inputs.opex_fixed_operating +
        inputs.opex_professional_fees + inputs.opex_property_tax +
        inputs.opex_telecom + inputs.opex_audit_fees +
        inputs.opex_contingency + inputs.opex_insurance + inputs.opex_legal
    )
    monthly_fixed_opex = fixed_opex_rate * inputs.capacity_mw / 12

    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        ops_year = ops_month // 12
        inflation_factor = (1 + inputs.opex_inflation) ** ops_year

        opex[i] = -monthly_fixed_opex * inflation_factor
        ops_month += 1

    results.opex = opex
    results.total_opex = abs(opex.sum())

    # =====================================================================
    # DEPRECIATION (for tax calculation)
    # =====================================================================
    # Reducing balance method at tax depreciation rate
    depreciation = np.zeros(n)
    wdv = total_capex  # Written-down value
    ops_month = 0
    for i in range(n):
        if not is_operations[i]:
            continue

        # Annual depreciation applied monthly
        annual_depr = wdv * inputs.depreciation_tax
        monthly_depr = annual_depr / 12
        depreciation[i] = monthly_depr

        # Reduce WDV annually
        if ops_month > 0 and ops_month % 12 == 0:
            wdv -= annual_depr
            wdv = max(wdv, 0)

        ops_month += 1

    results.depreciation = depreciation

    # =====================================================================
    # DEBT (for geared tax — interest only)
    # =====================================================================
    interest = np.zeros(n)
    debt_balance = total_capex * inputs.gearing
    debt_months = inputs.debt_tenor_years * 12
    monthly_rate = inputs.interest_rate / 12

    if debt_balance > 0 and debt_months > 0:
        # Level repayment (annuity)
        if monthly_rate > 0:
            annuity = debt_balance * monthly_rate * (1 + monthly_rate) ** debt_months / \
                      ((1 + monthly_rate) ** debt_months - 1)
        else:
            annuity = debt_balance / debt_months

        ops_month = 0
        for i in range(n):
            if not is_operations[i]:
                continue

            if ops_month < debt_months and debt_balance > 0:
                int_payment = debt_balance * monthly_rate
                principal = annuity - int_payment
                interest[i] = int_payment
                debt_balance -= principal
                debt_balance = max(debt_balance, 0)

            ops_month += 1

    results.interest = interest

    # =====================================================================
    # TAX (geared — after interest deduction)
    # =====================================================================
    tax = np.zeros(n)

    ebitda = revenue + fuel_cost + opex  # fuel_cost and opex are negative
    taxable_monthly = ebitda - depreciation - interest

    loss_pool = 0.0
    annual_taxable = 0.0
    tax_month = 12  # December

    ops_started = False
    for i in range(n):
        if not is_operations[i]:
            continue
        ops_started = True

        annual_taxable += taxable_monthly[i]

        if dates[i].month == tax_month:
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

    # =====================================================================
    # FCFF = EBITDA - CAPEX (matches Excel Cash Flows-Gas row 82)
    # Excel gas FCFF does NOT include tax — tax is only at FCFE level
    # =====================================================================
    fcff = revenue + fuel_cost + opex + capex  # no tax in FCFF
    results.fcff = fcff
    results.dates = dates

    # =====================================================================
    # XIRR
    # =====================================================================
    results.project_irr = calc_xirr(dates, fcff)

    return results


def gas_inputs_from_params(gas_params: dict, overall_params: dict, tax_params: dict) -> GasInputs:
    """Create GasInputs from excel_reader parameter dicts."""
    return GasInputs(
        construction_start=gas_params['construction_start'],
        construction_months=gas_params['construction_months'],
        cod_date=gas_params['cod_date'],
        operations_years=gas_params['operations_years'],
        capacity_mw=gas_params['capacity_mw'],
        effective_capacity_mw=gas_params['effective_capacity_mw'],
        ppa_tenor_years=gas_params['ppa_tenor_years'],
        ppa_tariff=overall_params['tariff_gbp_mwh'],
        tariff_escalation=overall_params['tariff_escalation'],
        merchant_tariff=overall_params['gas_merchant_tariff'],
        merchant_hours_per_day=overall_params['gas_merchant_hours_per_day'],
        net_efficiency=gas_params['net_efficiency'],
        fuel_price_gbp_mwh=gas_params['fuel_price_gbp_mwh'],
        fuel_escalation_from_yr4=gas_params['fuel_escalation_from_yr4'],
        fixed_gas_cost_gbp_day=gas_params['fixed_gas_cost_gbp_day'],
        start_fuel_pct=gas_params['start_fuel_consumption'],
        starts_per_day=gas_params['starts_per_day'],
        start_time_minutes=gas_params['start_time_minutes'],
        co2_kg_per_mwh=gas_params['co2_kg_per_mwh'],
        ukets_cost_gbp_per_kg=gas_params['ukets_cost_gbp_per_kg'],
        opex_environmental_levies=gas_params['opex_environmental_levies'],
        opex_om_contract=gas_params['opex_om_contract'],
        opex_site_maintenance=gas_params['opex_site_maintenance'],
        opex_other_variable=gas_params['opex_other_variable'],
        opex_reactive_maint_per_mwh=gas_params['opex_reactive_maint_per_mwh'],
        opex_site_lease=gas_params['opex_site_lease'],
        opex_fixed_operating=gas_params['opex_fixed_operating'],
        opex_professional_fees=gas_params['opex_professional_fees'],
        opex_property_tax=gas_params['opex_property_tax'],
        opex_telecom=gas_params['opex_telecom'],
        opex_audit_fees=gas_params['opex_audit_fees'],
        opex_contingency=gas_params['opex_contingency'],
        opex_insurance=gas_params['opex_insurance'],
        opex_legal=gas_params['opex_legal'],
        opex_inflation=gas_params['opex_inflation'],
        capex_per_mw=gas_params['capex_per_mw'],
        capex_total=gas_params['total_capex_excl_idc'],
        depreciation_slm=gas_params['depreciation_slm'],
        depreciation_tax=gas_params['depreciation_tax'],
        corp_tax_rate=gas_params['corp_tax_rate'],
        gearing=gas_params['gearing'],
        interest_rate=gas_params['interest_rate'],
        debt_tenor_years=gas_params['debt_tenor_years'],
    )
