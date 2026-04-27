"""
Excel Parameter Reader — Off-Grid Solution v8.xlsm

Reads all financial model parameters from the master Excel workbook.
Returns structured dictionaries for Solar+BESS, Gas, and Overall inputs.
"""

from pathlib import Path
from datetime import date, datetime
from typing import Any

import openpyxl


MASTER_EXCEL = Path("Financial Model/Off-Grid Solution v8.xlsm")


def _to_date(val, default: date = date(2027, 7, 1)) -> date:
    """Convert Excel datetime to Python date."""
    if val is None:
        return default
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return default


def _float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _int(val, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def read_model_params(workbook_path: Path = MASTER_EXCEL) -> dict:
    """
    Read all financial model parameters from Off-Grid Solution v8.xlsm.

    Returns dict with keys:
        'overall'        — tariff, PPA, merchant assumptions
        'solar_bess'     — Solar+BESS timing, capacity, CAPEX, OPEX, tax
        'gas'            — Gas plant timing, capacity, CAPEX, OPEX, fuel
        'seasonality'    — 12-element list of monthly fractions
        'merchant_prices'— dict {year: GBP/MWh} blend nominal prices
        'tax'            — corporate tax config
    """
    wb = openpyxl.load_workbook(str(workbook_path), data_only=True, read_only=True)

    overall = _read_overall_inputs(wb)
    solar_bess = _read_solar_bess_inputs(wb)
    gas = _read_gas_inputs(wb)
    seasonality = _read_seasonality(wb)
    merchant = _read_merchant_prices(wb)
    tax = _read_tax_config(wb)
    debt = _read_debt_params(wb)

    wb.close()

    return {
        'overall': overall,
        'solar_bess': solar_bess,
        'gas': gas,
        'seasonality': seasonality,
        'merchant_prices': merchant,
        'tax': tax,
        'debt': debt,
    }


# =========================================================================
# OVERALL INPUTS
# =========================================================================

def _read_overall_inputs(wb) -> dict:
    ws = wb['Overall Inputs']
    return {
        'pv_capacity_mwp': _float(ws['E2'].value, 82),
        'bess_capacity_mw': _float(ws['E3'].value, 62.5),
        'bess_duration_hrs': _float(ws['E4'].value, 4),
        'gas_capacity_mw': _float(ws['E5'].value, 28.32),
        'base_load_mw': _float(ws['E7'].value, 25),
        'ppa_start': _to_date(ws['E10'].value),
        'ppa_tenor_years': _int(ws['E11'].value, 10),
        'ppa_end': _to_date(ws['E12'].value),
        'tariff_gbp_mwh': _float(ws['E13'].value, 170),
        'tariff_escalation': _float(ws['E14'].value, 0),
        'gas_merchant_tariff': _float(ws['E17'].value, 200),
        'gas_merchant_hours_per_day': _float(ws['E18'].value, 9),
        'solar_merchant_tariff': _float(ws['E21'].value, 0),
    }


# =========================================================================
# SOLAR & BESS INPUTS
# =========================================================================

def _read_solar_bess_inputs(wb) -> dict:
    ws = wb['Solar&BESS Inputs']

    def f(col, row):
        return _float(ws[f'{col}{row}'].value)

    # Use column F (selected case) as primary, fall back to J (Case 1)
    def fv(row, default=0.0):
        v = ws[f'F{row}'].value
        if v is None:
            v = ws[f'J{row}'].value
        return _float(v, default)

    return {
        # Timing
        'model_start': _to_date(ws['F16'].value, date(2023, 1, 1)),
        'dev_start': _to_date(ws['F17'].value, date(2025, 3, 1)),
        'dev_months': _int(ws['F18'].value, 19),
        'construction_start': _to_date(ws['F19'].value, date(2026, 10, 1)),
        'construction_months': _int(ws['F20'].value, 9),
        'cod_date': _to_date(ws['F23'].value, date(2027, 7, 1)),
        'project_life_years': _int(ws['F24'].value, 35),

        # Solar
        'solar_capacity_mwp': _float(ws['F31'].value, 82),
        'yield_p50': _float(ws['F34'].value, 967),
        'yield_p75': _float(ws['F35'].value, 936),
        'yield_p90': _float(ws['F36'].value, 895),
        'generation_selection': ws['F66'].value or 'P50',
        'degradation_pct': _float(ws['F40'].value, 0.003),  # decimal
        'outage_selection': _int(ws['F43'].value, 0),
        'outage_month': ws['F44'].value or 'December',
        'outage_days': _int(ws['F45'].value, 10),

        # BESS
        'bess_switch': _int(ws['F109'].value, 1),
        'bess_operating_life': _int(ws['F112'].value, 10),
        'bess_capacity_mw': _float(ws['F116'].value, 62.5),
        'bess_duration_hrs': _float(ws['F117'].value, 4),
        'bess_degradation_pct': _float(ws['F120'].value, 0),  # decimal

        # BESS revenue (zeroed for data centre PPA mode)
        'bess_merchant_switch': _int(ws['F124'].value, 1),
        'bess_floor_switch': _int(ws['F131'].value, 1),
        'bess_floor_price': _float(ws['F132'].value, 40),
        'bess_floor_rev_share': _float(ws['F133'].value, 0.09),
        'bess_floor_tenor': _int(ws['F134'].value, 10),

        # Capacity Market T-1
        'cm_t1_value': _float(ws['F140'].value, 20),
        'cm_t1_derating': _float(ws['F141'].value, 0.2715),
        'cm_t1_tenor': _int(ws['F142'].value, 3),
        'cm_t1_start': _to_date(ws['F143'].value, date(2026, 10, 1)),
        # T-4
        'cm_t4_value': _float(ws['F148'].value, 60),
        'cm_t4_derating': _float(ws['F149'].value, 0.2094),
        'cm_t4_tenor': _int(ws['F150'].value, 15),
        'cm_t4_start': _to_date(ws['F151'].value, date(2029, 10, 1)),

        # REGOs
        'rego_switch': _int(ws['F79'].value, 1),
        'rego_price': _float(ws['F80'].value, 2.5),
        'rego_indexation': ws['F81'].value or 'NIL INDEXATION',
        'rego_tenor': _int(ws['F82'].value, 35),

        # Embedded benefits
        'emb_switch': _int(ws['F87'].value, 1),
        'emb_indexation': ws['F88'].value or 'CPI',
        'emb_tenor': _int(ws['F89'].value, 15),
        'emb_benefits': [
            _float(ws[f'F{r}'].value, 0) for r in range(94, 106)
        ],

        # Land
        'fixed_lease_switch': _int(ws['F172'].value, 1),
        'fixed_lease_acres': _float(ws['F173'].value, 205),
        'fixed_lease_price': _float(ws['F174'].value, 700),
        'rev_dep_lease_switch': _int(ws['F178'].value, 1),
        'rev_dep_lease_acres': _float(ws['F179'].value, 205),
        'rev_share_yr1_10': _float(ws['F180'].value, 0.05),
        'rev_share_yr11_35': _float(ws['F181'].value, 0.05),
        'construction_rent_switch': _int(ws['F184'].value, 0),
        'construction_rent': _float(ws['F185'].value, 0),

        # Solar OPEX (GBP/kWp/Yr)
        'opex_pv_om': _float(ws['F215'].value, 5.48),
        'opex_grid_conn': _float(ws['F216'].value, 0.003),
        'opex_greenkeeping': _float(ws['F217'].value, 1.5),
        'opex_community': _float(ws['F218'].value, 0.5),
        'opex_real_estate_tax': _float(ws['F219'].value, 1.22),
        'opex_non_tech_am': _float(ws['F220'].value, 1.3),
        'opex_subsidy_loss': _float(ws['F221'].value, 0),
        'opex_insurance': _float(ws['F222'].value, 2.02),
        'opex_corrective_maint': _float(ws['F224'].value, 3.2),
        'opex_tech_am': _float(ws['F225'].value, 0.3),
        'opex_social_cost': _float(ws['F281'].value, 0),
        'opex_balancing_cfd': _float(ws['F282'].value, 2.75),

        # BESS OPEX (GBPk/MW/Yr)
        'bess_opex_om': _float(ws['F308'].value, 7.06),
        'bess_opex_import': _float(ws['F309'].value, 0),
        'bess_opex_rates': _float(ws['F310'].value, 3.276),
        'bess_opex_lease': _float(ws['F311'].value, 1.489),

        # Working capital
        'wc_debtors_days': _int(ws['F327'].value, 30),
        'wc_creditors_days': _int(ws['F328'].value, 30),

        # CAPEX (GBP/kWp)
        'capex_phasing': _int(ws['F332'].value, 2),
        'capex_acquisition': fv(335),
        'capex_development': fv(336),
        'capex_discharge': fv(337),
        'capex_dd': fv(338),
        'capex_epc': fv(339, 400),
        'capex_grid': fv(340),
        'capex_sdlt': fv(341),
        'capex_land_legal': fv(342),
        'capex_other_finance': fv(343),
        'capex_other_legal': fv(344),
        'capex_land_purchase': fv(345),
        'capex_ampyr_tech': fv(346),
        'capex_success_fee': fv(347),
        'capex_community_capex': fv(348),
        'capex_bess': fv(349, 600),
        'capex_landowner_fees': fv(350),
        'capex_insurance_capex': fv(351),
        'capex_land_lease_constr': fv(352),
        'capex_asset_adoption': fv(353),
        'capex_others': fv(354),
        'capex_misc': fv(355),
        'capex_contingency_pct': _float(ws['F363'].value, 0.01),  # decimal

        # Financial
        'cost_of_capital': _float(ws['F589'].value, 0.07),
        'discount_rate': _float(ws['F590'].value, 0.065),
    }


# =========================================================================
# GAS INPUTS
# =========================================================================

def _read_gas_inputs(wb) -> dict:
    ws = wb['Inputs-Gas']

    def fv(row, default=0.0):
        return _float(ws[f'I{row}'].value, default)

    return {
        # Timing
        'construction_start': _to_date(ws['I3'].value, date(2026, 1, 1)),
        'construction_months': _int(ws['I4'].value, 18),
        'cod_date': _to_date(ws['I6'].value, date(2027, 7, 1)),
        'operations_years': _int(ws['I7'].value, 20),

        # Capacity
        'capacity_mw': fv(11, 28.32),
        'active_capacity_mw': fv(12, 26.32),
        'availability': fv(13, 0.95),
        'effective_capacity_mw': fv(14, 25),

        # PPA
        'ppa_start': _to_date(ws['I15'].value, date(2027, 7, 1)),
        'ppa_tenor_years': _int(ws['I16'].value, 10),
        'fuel_passthrough': ws['I18'].value or 'No',
        'ppa_tariff': fv(19, 170),
        'tariff_escalation': fv(20, 0),
        'merchant_tariff': fv(21, 200),
        'merchant_hours_per_day': fv(22, 9),

        # Fuel
        'net_efficiency': fv(24, 0.385),
        'fuel_price_gbp_mwh': fv(25, 32.51),
        'fuel_escalation_from_yr4': fv(26, 0.01),
        'fixed_gas_cost_gbp_day': fv(27, 1087.54),
        'start_fuel_consumption': fv(28, 0.1),
        'starts_per_day': fv(29, 4),
        'start_time_minutes': fv(30, 10),

        # Emissions
        'co2_kg_per_mwh': fv(51, 185),
        'ukets_cost_gbp_per_kg': fv(52, 0.07),

        # OPEX (GBPk/MW/Yr)
        'opex_environmental_levies': fv(32, 10.17),
        'opex_om_contract': fv(35, 9.38),
        'opex_site_maintenance': fv(36, 1.80),
        'opex_other_variable': fv(37, 2.02),
        'opex_reactive_maint_per_mwh': fv(38, 0.0015),
        'opex_site_lease': fv(40, 3.90),
        'opex_fixed_operating': fv(41, 14.23),
        'opex_professional_fees': fv(42, 4.584),
        'opex_property_tax': fv(43, 4.0),
        'opex_telecom': fv(44, 0.3),
        'opex_audit_fees': fv(46, 0.84),
        'opex_contingency': fv(47, 0),
        'opex_insurance': fv(48, 3.54),
        'opex_legal': fv(49, 0.872),
        'opex_inflation': fv(54, 0.02),

        # CAPEX
        'capex_per_mw': fv(57, 771.28),
        'total_capex_excl_idc': fv(58, 21839.43),

        # Depreciation
        'depreciation_slm': fv(66, 0.05),
        'depreciation_tax': fv(67, 0.10),
        'corp_tax_rate': fv(69, 0.25),

        # Debt
        'gearing': fv(61, 0.85),
        'dscr': fv(62, 1.2),
        'interest_rate': fv(63, 0.0675),
        'debt_tenor_years': _int(ws['I64'].value, 10),
    }


# =========================================================================
# SEASONALITY
# =========================================================================

def _read_seasonality(wb) -> list:
    ws = wb['Solar&BESS Inputs']
    seasonality = []
    for r in range(51, 63):
        v = ws[f'F{r}'].value
        if v is None:
            v = ws[f'J{r}'].value
        seasonality.append(_float(v, 1 / 12))
    return seasonality


# =========================================================================
# MERCHANT PRICES (Baringa Blend nominal)
# =========================================================================

def _read_merchant_prices(wb) -> dict:
    """Read yearly Baringa blend nominal merchant prices."""
    ws = wb['Baringa and Aurora']
    prices = {}

    # Row 12 has years, row 131 has Applied nominal blend prices
    for col_idx in range(6, 55):  # columns F through BC
        yr = ws.cell(row=12, column=col_idx).value
        val = ws.cell(row=131, column=col_idx).value
        if yr is not None and val is not None:
            prices[int(yr)] = float(val)

    # If no blend prices found, use Baringa base monthly (row 114)
    if not prices:
        for col_idx in range(6, 55):
            yr = ws.cell(row=12, column=col_idx).value
            val = ws.cell(row=114, column=col_idx).value
            if yr is not None and val is not None:
                prices[int(yr)] = float(val)

    return prices


# =========================================================================
# TAX CONFIG
# =========================================================================

def _read_tax_config(wb) -> dict:
    ws = wb['Curves and D&T']
    return {
        'corp_tax_rate_low': _float(ws['E105'].value, 0.25),
        'corp_tax_rate_high': _float(ws['E106'].value, 0.25),
        'corp_tax_threshold': _float(ws['E107'].value, 0),
        'taxation_month': _int(ws['E108'].value, 12),
    }


# =========================================================================
# DEBT PARAMS (Solar+BESS)
# =========================================================================

def _read_debt_params(wb) -> dict:
    ws = wb['Debt']
    ws_inp = wb['Solar&BESS Inputs']
    return {
        'sb_gearing': _float(ws_inp['H6'].value, 0.80),
        'sb_swap_rate': _float(ws['E88'].value, 0.037),
        'sb_swap_margin': _float(ws['E89'].value, 0.003),
        'sb_interest_rate': _float(ws['E88'].value, 0.037) + _float(ws['E89'].value, 0.003),
        'sb_dscr': _float(ws_inp['G7'].value, 1.2),
    }


# =========================================================================
# CONVENIENCE: get a flat merchant price for a given year
# =========================================================================

def get_merchant_price(merchant_prices: dict, year: int, default: float = 67.0) -> float:
    """Get the blend merchant price for a given year, with interpolation."""
    if year in merchant_prices:
        return merchant_prices[year]

    # Use nearest available year
    years = sorted(merchant_prices.keys())
    if not years:
        return default
    if year < years[0]:
        return merchant_prices[years[0]]
    if year > years[-1]:
        return merchant_prices[years[-1]]

    # Linear interpolation between surrounding years
    for i in range(len(years) - 1):
        if years[i] <= year <= years[i + 1]:
            frac = (year - years[i]) / (years[i + 1] - years[i])
            return merchant_prices[years[i]] * (1 - frac) + merchant_prices[years[i + 1]] * frac
    return default
