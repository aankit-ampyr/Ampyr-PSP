"""
Financial Model Module - 20-Year NPV Projection

Provides financial analysis for BESS+DG systems including:
- Net Present Value (NPV) calculations
- Internal Rate of Return (IRR)
- Levelized Cost of Storage (LCOS)
- Year-by-year projections with degradation
- Augmentation cost modeling
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class FinancialConfig:
    """Financial modeling parameters."""

    # Capital costs
    bess_cost_per_mwh: float = 300_000       # $/MWh installed
    bess_cost_per_mw: float = 50_000         # $/MW (power electronics)
    dg_cost_per_mw: float = 200_000          # $/MW installed
    augmentation_cost_per_mwh: float = 250_000  # $/MWh (future battery)
    installation_pct: float = 0.15           # 15% of equipment cost

    # Operating costs
    bess_fixed_om_per_mwh_year: float = 5_000   # $/MWh/year
    dg_fixed_om_per_mw_year: float = 10_000     # $/MW/year
    dg_variable_om_per_mwh: float = 5           # $/MWh generated
    fuel_price_per_liter: float = 1.50          # $/L
    fuel_escalation_rate: float = 0.025         # 2.5% per year

    # Financial parameters
    discount_rate: float = 0.08              # 8% WACC
    project_life_years: int = 20
    tax_rate: float = 0.25                   # 25% corporate tax
    depreciation_years: int = 10             # Straight-line depreciation

    # Revenue/Value parameters
    delivery_value_per_mwh: float = 100      # $/MWh delivered
    penalty_per_unserved_hour: float = 500   # $/hr when load not met
    capacity_payment_per_mw_year: float = 0  # $/MW/year (if applicable)

    # Degradation
    annual_degradation_pct: float = 2.0      # 2% per year
    end_of_life_capacity_pct: float = 70.0   # Replace when below 70%

    # Strategy
    augmentation_enabled: bool = False
    augmentation_year: int = 8
    overbuild_factor: float = 0.0            # 0 = no overbuild


@dataclass
class YearlyFinancials:
    """Financial results for a single year."""
    year: int

    # Capacity
    installed_capacity_mwh: float = 0
    effective_capacity_mwh: float = 0
    capacity_retention_pct: float = 100

    # Performance
    delivery_hours: int = 0
    delivery_pct: float = 0
    unserved_hours: int = 0
    dg_runtime_hours: int = 0
    fuel_consumed_liters: float = 0

    # Revenue
    delivery_revenue: float = 0
    capacity_payment: float = 0
    total_revenue: float = 0

    # Costs
    bess_om: float = 0
    dg_om: float = 0
    fuel_cost: float = 0
    unserved_penalty: float = 0
    augmentation_cost: float = 0
    total_opex: float = 0

    # Financial
    ebitda: float = 0
    depreciation: float = 0
    ebt: float = 0
    tax: float = 0
    net_income: float = 0
    cash_flow: float = 0
    discounted_cash_flow: float = 0
    cumulative_npv: float = 0


@dataclass
class FinancialSummary:
    """Summary of 20-year financial projection."""

    # Investment
    total_capex: float = 0
    bess_capex: float = 0
    dg_capex: float = 0
    installation_cost: float = 0

    # Returns
    npv: float = 0
    irr: float = 0
    payback_years: float = 0
    roi_pct: float = 0

    # Levelized metrics
    lcos_per_mwh: float = 0           # Levelized Cost of Storage
    lcoe_per_mwh: float = 0           # Levelized Cost of Energy

    # Totals over project life
    total_revenue: float = 0
    total_opex: float = 0
    total_fuel_cost: float = 0
    total_delivery_mwh: float = 0
    total_fuel_liters: float = 0

    # Augmentation
    augmentation_cost: float = 0
    augmentation_year: int = 0

    # Yearly details
    yearly_results: List[YearlyFinancials] = field(default_factory=list)


# =============================================================================
# CAPEX CALCULATIONS
# =============================================================================

def calculate_capex(
    bess_capacity_mwh: float,
    bess_power_mw: float,
    dg_capacity_mw: float = 0,
    config: FinancialConfig = None
) -> Dict[str, float]:
    """
    Calculate total capital expenditure.

    Args:
        bess_capacity_mwh: Battery energy capacity
        bess_power_mw: Battery power capacity
        dg_capacity_mw: Diesel generator capacity
        config: Financial configuration

    Returns:
        Dict with CAPEX breakdown
    """
    if config is None:
        config = FinancialConfig()

    # BESS costs
    bess_energy_cost = bess_capacity_mwh * config.bess_cost_per_mwh
    bess_power_cost = bess_power_mw * config.bess_cost_per_mw
    bess_total = bess_energy_cost + bess_power_cost

    # DG costs
    dg_total = dg_capacity_mw * config.dg_cost_per_mw

    # Installation
    equipment_total = bess_total + dg_total
    installation = equipment_total * config.installation_pct

    # Total
    total_capex = equipment_total + installation

    return {
        'bess_energy_cost': bess_energy_cost,
        'bess_power_cost': bess_power_cost,
        'bess_total': bess_total,
        'dg_total': dg_total,
        'installation': installation,
        'total_capex': total_capex
    }


# =============================================================================
# OPEX CALCULATIONS
# =============================================================================

def calculate_annual_opex(
    bess_capacity_mwh: float,
    dg_capacity_mw: float,
    dg_energy_mwh: float,
    fuel_liters: float,
    year: int,
    config: FinancialConfig = None
) -> Dict[str, float]:
    """
    Calculate annual operating expenditure.

    Args:
        bess_capacity_mwh: Battery capacity
        dg_capacity_mw: DG capacity
        dg_energy_mwh: DG energy generated in year
        fuel_liters: Fuel consumed in year
        year: Project year (for fuel escalation)
        config: Financial configuration

    Returns:
        Dict with OPEX breakdown
    """
    if config is None:
        config = FinancialConfig()

    # Fixed O&M
    bess_om = bess_capacity_mwh * config.bess_fixed_om_per_mwh_year
    dg_fixed_om = dg_capacity_mw * config.dg_fixed_om_per_mw_year
    dg_variable_om = dg_energy_mwh * config.dg_variable_om_per_mwh

    # Fuel cost with escalation
    escalated_fuel_price = config.fuel_price_per_liter * ((1 + config.fuel_escalation_rate) ** (year - 1))
    fuel_cost = fuel_liters * escalated_fuel_price

    total_opex = bess_om + dg_fixed_om + dg_variable_om + fuel_cost

    return {
        'bess_om': bess_om,
        'dg_fixed_om': dg_fixed_om,
        'dg_variable_om': dg_variable_om,
        'fuel_cost': fuel_cost,
        'total_opex': total_opex
    }


# =============================================================================
# NPV & IRR CALCULATIONS
# =============================================================================

def calculate_npv(
    cash_flows: List[float],
    discount_rate: float
) -> float:
    """
    Calculate Net Present Value.

    Args:
        cash_flows: List of cash flows, starting with year 0 (initial investment)
        discount_rate: Discount rate (e.g., 0.08 for 8%)

    Returns:
        NPV value
    """
    npv = 0.0
    for t, cf in enumerate(cash_flows):
        npv += cf / ((1 + discount_rate) ** t)
    return npv


def calculate_irr(
    cash_flows: List[float],
    max_iterations: int = 100,
    tolerance: float = 0.0001
) -> Optional[float]:
    """
    Calculate Internal Rate of Return using Newton-Raphson method.

    Args:
        cash_flows: List of cash flows (year 0 should be negative for investment)
        max_iterations: Maximum iterations
        tolerance: Convergence tolerance

    Returns:
        IRR as decimal (e.g., 0.12 for 12%) or None if not found
    """
    # Initial guess
    rate = 0.10

    for _ in range(max_iterations):
        # Calculate NPV and derivative
        npv = 0.0
        npv_derivative = 0.0

        for t, cf in enumerate(cash_flows):
            npv += cf / ((1 + rate) ** t)
            if t > 0:
                npv_derivative -= t * cf / ((1 + rate) ** (t + 1))

        # Check convergence
        if abs(npv) < tolerance:
            return rate

        # Newton-Raphson update
        if abs(npv_derivative) < 1e-10:
            break

        rate = rate - npv / npv_derivative

        # Bounds check
        if rate < -0.99 or rate > 10:
            break

    return None


def calculate_payback_period(
    cash_flows: List[float]
) -> Optional[float]:
    """
    Calculate payback period.

    Args:
        cash_flows: List of cash flows (year 0 = initial investment)

    Returns:
        Payback period in years, or None if never pays back
    """
    cumulative = 0.0

    for year, cf in enumerate(cash_flows):
        prev_cumulative = cumulative
        cumulative += cf

        if cumulative >= 0 and prev_cumulative < 0:
            # Linear interpolation within the year
            if cf != 0:
                fraction = -prev_cumulative / cf
                return (year - 1) + fraction
            return float(year)

    return None


# =============================================================================
# LEVELIZED COST CALCULATIONS
# =============================================================================

def calculate_lcos(
    total_capex: float,
    total_opex_npv: float,
    total_energy_delivered_mwh: float,
    discount_rate: float = 0.08
) -> float:
    """
    Calculate Levelized Cost of Storage.

    Args:
        total_capex: Initial capital expenditure
        total_opex_npv: NPV of all operating costs
        total_energy_delivered_mwh: Total energy delivered over project life
        discount_rate: Discount rate

    Returns:
        LCOS in $/MWh
    """
    if total_energy_delivered_mwh <= 0:
        return float('inf')

    total_cost = total_capex + total_opex_npv
    lcos = total_cost / total_energy_delivered_mwh

    return lcos


# =============================================================================
# 20-YEAR PROJECTION
# =============================================================================

class FinancialProjection:
    """20-year financial projection engine."""

    def __init__(
        self,
        bess_capacity_mwh: float,
        bess_power_mw: float,
        dg_capacity_mw: float = 0,
        config: FinancialConfig = None
    ):
        """
        Initialize projection.

        Args:
            bess_capacity_mwh: Initial battery capacity
            bess_power_mw: Battery power rating
            dg_capacity_mw: DG capacity
            config: Financial configuration
        """
        self.initial_capacity_mwh = bess_capacity_mwh
        self.bess_power_mw = bess_power_mw
        self.dg_capacity_mw = dg_capacity_mw
        self.config = config or FinancialConfig()

        # Apply overbuild
        if self.config.overbuild_factor > 0:
            self.installed_capacity_mwh = bess_capacity_mwh * (1 + self.config.overbuild_factor)
        else:
            self.installed_capacity_mwh = bess_capacity_mwh

        # Calculate CAPEX
        self.capex = calculate_capex(
            self.installed_capacity_mwh,
            self.bess_power_mw,
            self.dg_capacity_mw,
            self.config
        )

        self.yearly_results: List[YearlyFinancials] = []

    def project_capacity(self, year: int) -> Tuple[float, float, bool]:
        """
        Project effective capacity for a given year.

        Returns:
            (installed_mwh, effective_mwh, was_augmented)
        """
        installed = self.installed_capacity_mwh
        degradation_rate = self.config.annual_degradation_pct / 100

        # Compound degradation
        retention = (1 - degradation_rate) ** year
        effective = installed * retention

        augmented = False

        # Check augmentation
        if self.config.augmentation_enabled and year >= self.config.augmentation_year:
            # Calculate capacity loss
            capacity_loss = installed - effective

            # Add augmentation (restore to initial)
            if year == self.config.augmentation_year:
                augmented = True

            # After augmentation, capacity is restored
            years_after_aug = year - self.config.augmentation_year
            aug_retention = (1 - degradation_rate) ** years_after_aug
            effective = self.initial_capacity_mwh * aug_retention
            installed = self.initial_capacity_mwh

        return installed, effective, augmented

    def simulate_year(
        self,
        year: int,
        delivery_hours: int = 8000,
        dg_runtime_hours: int = 500,
        fuel_liters: float = 5000,
        delivery_mwh: float = 0
    ) -> YearlyFinancials:
        """
        Simulate financial results for one year.

        Args:
            year: Project year (1-20)
            delivery_hours: Hours of successful delivery
            dg_runtime_hours: DG runtime hours
            fuel_liters: Fuel consumed
            delivery_mwh: Total energy delivered

        Returns:
            YearlyFinancials for the year
        """
        result = YearlyFinancials(year=year)

        # Capacity
        installed, effective, augmented = self.project_capacity(year)
        result.installed_capacity_mwh = installed
        result.effective_capacity_mwh = effective
        result.capacity_retention_pct = (effective / self.initial_capacity_mwh) * 100

        # Performance
        result.delivery_hours = delivery_hours
        result.delivery_pct = (delivery_hours / 8760) * 100
        result.unserved_hours = 8760 - delivery_hours
        result.dg_runtime_hours = dg_runtime_hours
        result.fuel_consumed_liters = fuel_liters

        # Revenue
        if delivery_mwh <= 0:
            delivery_mwh = delivery_hours * 25 / 1000  # Estimate if not provided
        result.delivery_revenue = delivery_mwh * self.config.delivery_value_per_mwh
        result.capacity_payment = self.bess_power_mw * self.config.capacity_payment_per_mw_year
        result.total_revenue = result.delivery_revenue + result.capacity_payment

        # OPEX
        dg_energy_mwh = dg_runtime_hours * self.dg_capacity_mw if self.dg_capacity_mw > 0 else 0
        opex = calculate_annual_opex(
            effective, self.dg_capacity_mw, dg_energy_mwh,
            fuel_liters, year, self.config
        )

        result.bess_om = opex['bess_om']
        result.dg_om = opex['dg_fixed_om'] + opex['dg_variable_om']
        result.fuel_cost = opex['fuel_cost']
        result.unserved_penalty = result.unserved_hours * self.config.penalty_per_unserved_hour

        # Augmentation cost
        if augmented:
            aug_capacity = self.initial_capacity_mwh - (self.installed_capacity_mwh *
                          ((1 - self.config.annual_degradation_pct/100) ** self.config.augmentation_year))
            result.augmentation_cost = max(0, aug_capacity) * self.config.augmentation_cost_per_mwh

        result.total_opex = (result.bess_om + result.dg_om + result.fuel_cost +
                            result.unserved_penalty + result.augmentation_cost)

        # EBITDA
        result.ebitda = result.total_revenue - result.total_opex

        # Depreciation (straight-line)
        if year <= self.config.depreciation_years:
            result.depreciation = self.capex['total_capex'] / self.config.depreciation_years
        else:
            result.depreciation = 0

        # Taxes
        result.ebt = result.ebitda - result.depreciation
        result.tax = max(0, result.ebt * self.config.tax_rate)
        result.net_income = result.ebt - result.tax

        # Cash flow (add back depreciation)
        result.cash_flow = result.net_income + result.depreciation

        # Discounted cash flow
        result.discounted_cash_flow = result.cash_flow / ((1 + self.config.discount_rate) ** year)

        return result

    def run_projection(
        self,
        yearly_performance: List[Dict] = None
    ) -> FinancialSummary:
        """
        Run full 20-year projection.

        Args:
            yearly_performance: Optional list of dicts with yearly performance data
                               (delivery_hours, dg_runtime_hours, fuel_liters)

        Returns:
            FinancialSummary with complete results
        """
        summary = FinancialSummary()

        # CAPEX
        summary.total_capex = self.capex['total_capex']
        summary.bess_capex = self.capex['bess_total']
        summary.dg_capex = self.capex['dg_total']
        summary.installation_cost = self.capex['installation']

        # Build cash flows
        cash_flows = [-summary.total_capex]  # Year 0: investment
        cumulative_npv = -summary.total_capex

        # Simulate each year
        for year in range(1, self.config.project_life_years + 1):
            # Get performance data
            if yearly_performance and year <= len(yearly_performance):
                perf = yearly_performance[year - 1]
                yearly = self.simulate_year(
                    year,
                    perf.get('delivery_hours', 8000),
                    perf.get('dg_runtime_hours', 500),
                    perf.get('fuel_liters', 5000),
                    perf.get('delivery_mwh', 0)
                )
            else:
                # Default performance (degrade delivery hours with capacity)
                _, effective, _ = self.project_capacity(year)
                capacity_ratio = effective / self.initial_capacity_mwh
                base_delivery = 8000
                degraded_delivery = int(base_delivery * capacity_ratio)

                yearly = self.simulate_year(
                    year,
                    degraded_delivery,
                    500,
                    5000
                )

            # Update cumulative
            cumulative_npv += yearly.discounted_cash_flow
            yearly.cumulative_npv = cumulative_npv

            # Add to results
            self.yearly_results.append(yearly)
            cash_flows.append(yearly.cash_flow)

            # Accumulate totals
            summary.total_revenue += yearly.total_revenue
            summary.total_opex += yearly.total_opex
            summary.total_fuel_cost += yearly.fuel_cost
            summary.total_fuel_liters += yearly.fuel_consumed_liters
            summary.total_delivery_mwh += yearly.delivery_hours * 25 / 1000  # Estimate

            if yearly.augmentation_cost > 0:
                summary.augmentation_cost = yearly.augmentation_cost
                summary.augmentation_year = year

        # Calculate financial metrics
        summary.npv = calculate_npv(cash_flows, self.config.discount_rate)
        summary.irr = calculate_irr(cash_flows)
        summary.payback_years = calculate_payback_period(cash_flows)

        if summary.total_capex > 0:
            summary.roi_pct = ((summary.total_revenue - summary.total_opex - summary.total_capex)
                              / summary.total_capex) * 100

        # Levelized costs
        opex_npv = sum(y.discounted_cash_flow for y in self.yearly_results) + summary.total_capex
        if summary.total_delivery_mwh > 0:
            summary.lcos_per_mwh = (summary.total_capex + opex_npv) / summary.total_delivery_mwh

        summary.yearly_results = self.yearly_results

        return summary


# =============================================================================
# COMPARISON UTILITIES
# =============================================================================

def compare_strategies(
    bess_capacity_mwh: float,
    bess_power_mw: float,
    dg_capacity_mw: float = 0,
    base_config: FinancialConfig = None
) -> Dict[str, FinancialSummary]:
    """
    Compare different sizing strategies (standard, overbuild, augmentation).

    Args:
        bess_capacity_mwh: Required battery capacity
        bess_power_mw: Battery power rating
        dg_capacity_mw: DG capacity
        base_config: Base financial configuration

    Returns:
        Dict mapping strategy name to FinancialSummary
    """
    if base_config is None:
        base_config = FinancialConfig()

    results = {}

    # Standard strategy
    config_standard = FinancialConfig(**{
        **base_config.__dict__,
        'overbuild_factor': 0,
        'augmentation_enabled': False
    })
    proj_standard = FinancialProjection(
        bess_capacity_mwh, bess_power_mw, dg_capacity_mw, config_standard
    )
    results['standard'] = proj_standard.run_projection()

    # Overbuild strategy (20%)
    config_overbuild = FinancialConfig(**{
        **base_config.__dict__,
        'overbuild_factor': 0.20,
        'augmentation_enabled': False
    })
    proj_overbuild = FinancialProjection(
        bess_capacity_mwh, bess_power_mw, dg_capacity_mw, config_overbuild
    )
    results['overbuild_20pct'] = proj_overbuild.run_projection()

    # Augmentation strategy (year 8)
    config_augment = FinancialConfig(**{
        **base_config.__dict__,
        'overbuild_factor': 0,
        'augmentation_enabled': True,
        'augmentation_year': 8
    })
    proj_augment = FinancialProjection(
        bess_capacity_mwh, bess_power_mw, dg_capacity_mw, config_augment
    )
    results['augmentation_yr8'] = proj_augment.run_projection()

    return results
