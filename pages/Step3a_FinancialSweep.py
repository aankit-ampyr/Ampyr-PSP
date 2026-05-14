"""
Step 3a: Financial Sweep (Project IRR ranking)

Optional page between Step 3 (Sizing) and Step 4 (Results). Reads the
per-config operational metrics from Step 3 and runs the PIRR engine on
each row, producing a financial ranking on top of the operational one.

Spec: docs/Financial_Assumptions_Spec.md §7 (wizard flow) + §8 (session state).
Decisions log: docs/Project_IRR_Integration_Decisions.md A24 (Phase 1 scope +
dispatch-module mismatch).

Dispatch contract: this page uses `src/dispatch_energy.run_hourly_dispatch`
(solar-first, gas-fills-residual), NOT `src/dispatch_engine.run_simulation`
(cycle-aware operational sweep used by Step 3). See A24 for why.
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import SOLAR_PROFILE_PATH
from src.data_loader import (
    get_active_solar_profile,
    load_solar_profile,
    load_solar_profile_by_name,
)
from src.dispatch_energy import (
    aggregate_to_monthly,
    run_hourly_dispatch,
)
from src.project_irr import (
    PirrResults,
    pirr_inputs_from_wizard_state,
    run_pirr,
)
from src.wizard_state import (
    get_step_status,
    get_wizard_state,
    init_wizard_state,
    mark_step_completed,
)


st.set_page_config(
    page_title="Financial Sweep - Step 3a",
    page_icon="£",
    layout="wide",
)

init_wizard_state()


# =============================================================================
# STEP INDICATOR (matches the 7-step layout used elsewhere, with 3a annotated)
# =============================================================================

def render_step_indicator():
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("3a", "Financial Sweep", "current"),
        ("4", "Results", get_step_status(4)),
        ("5", "Multi-Year", get_step_status(5)),
        ("6", "Green Energy", get_step_status(6)),
        ("7", "Financial", get_step_status(7)),
    ]
    cols = st.columns(len(steps))
    for i, (num, label, status) in enumerate(steps):
        with cols[i]:
            if status == "completed":
                st.markdown(f"✅ **Step {num}**: {label}")
            elif status == "current":
                st.markdown(f"🔵 **Step {num}**: {label}")
            elif status == "pending":
                st.markdown(f"⚪ Step {num}: {label}")
            else:
                st.markdown(f"🔒 Step {num}: {label}")


# =============================================================================
# SOLAR PROFILE LOADER (matches Step 3 / Step 4 logic)
# =============================================================================

def get_solar_profile_array(setup: dict) -> np.ndarray | None:
    """Return the canonical 8760-hour solar profile from wizard state.

    Step 1 owns profile loading; this is a thin wrapper around
    `data_loader.get_active_solar_profile` for backward-compat with the
    existing call site below. Returns None if Step 1 hasn't run yet.

    See decisions log A27 for the migration rationale.
    """
    return get_active_solar_profile(setup)


# =============================================================================
# PIRR PER-CONFIG RUNNER
# =============================================================================

def run_pirr_for_config(
    config: dict,
    solar_mw_unscaled: np.ndarray,
    target_dc_mwp: float,
    profile_ref_mwp: float,
    load_mw: float,
    fin_state: dict,
    setup_state: dict,
    bess_efficiency_decimal: float,
    bess_min_soc: float,
    bess_max_soc: float,
) -> dict:
    """Run dispatch + PIRR for a single sweep config row.

    `config` keys mirror Step 3's sizing_results columns:
      BESS (MWh), Power (MW), DG (MW), Duration (hr), ...

    Returns a flat dict of headline outputs to be merged into the results
    DataFrame.
    """
    # Scale solar profile to target DC MWp (Step 7 uses this same scaling)
    if profile_ref_mwp <= 0:
        profile_ref_mwp = float(solar_mw_unscaled.max() or 1.0)
    solar_mw = solar_mw_unscaled * (target_dc_mwp / profile_ref_mwp)

    bess_mwh = float(config["BESS (MWh)"])
    bess_mw = float(config["Power (MW)"])
    dg_mw = float(config.get("DG (MW)", 0.0))

    # 1. Hourly dispatch (solar-first, BESS fills gap, gas fills remainder)
    hourly = run_hourly_dispatch(
        solar_mw,
        load_mw=load_mw,
        bess_mwh=bess_mwh,
        bess_mw=bess_mw,
        rte=bess_efficiency_decimal,
        min_soc=bess_min_soc,
        max_soc=bess_max_soc,
    )
    monthly = aggregate_to_monthly(hourly, solar_mw)

    # 2. Build PirrInputs from wizard state, then override capacities to match
    #    this config (engine's defaults are D13 = 82 MWp / 250 MWh / 25 MW gas).
    pi = pirr_inputs_from_wizard_state(fin_state, setup_state, monthly)
    pi.solar_dc_mwp = target_dc_mwp
    pi.bess_mwh = bess_mwh
    pi.bess_mw = bess_mw
    pi.gas_mw = dg_mw if dg_mw > 0 else pi.gas_mw

    # 3. PIRR
    results: PirrResults = run_pirr(pi)

    # Payback in years (annual granularity is enough for ranking)
    payback_yrs = float("nan")
    if len(results.fcff) > 0:
        cum = np.cumsum(results.fcff)
        pos = np.where(cum > 0)[0]
        if len(pos) > 0:
            payback_yrs = pos[0] / 12.0

    return {
        "Combined PIRR (%)": _pct(results.project_irr),
        "S+B PIRR (%)": _pct(results.project_irr_solar_bess),
        "Gas PIRR (%)": _pct(results.project_irr_gas),
        "NPV (GBPm)": results.project_npv / 1000.0,
        "Total CAPEX (GBPm)": results.total_capex / 1000.0,
        "Lifetime Revenue (GBPm)": results.total_revenue_lifetime / 1000.0,
        "Payback (yrs)": payback_yrs,
    }


def _pct(decimal: float) -> float:
    if decimal is None:
        return float("nan")
    if np.isnan(decimal):
        return float("nan")
    return decimal * 100.0


# =============================================================================
# MAIN PAGE
# =============================================================================

def main():
    render_step_indicator()
    st.divider()

    st.title("£ Financial Sweep — Project IRR Ranking")
    st.markdown(
        "Run the **Project IRR** engine on each operational config from Step 3 "
        "and rank by financial return alongside operational metrics. "
        "Uses the same engine as Step 7's single-config deep-dive "
        "(`src/project_irr.py`)."
    )

    state = get_wizard_state()
    setup = state.get("setup", {})
    fin = state.get("financial", {})

    # -------------------------------------------------------------------------
    # Prerequisites
    # -------------------------------------------------------------------------
    has_sizing = (
        "sizing_results" in st.session_state
        and st.session_state.sizing_results is not None
        and len(st.session_state.sizing_results) > 0
    )
    if not has_sizing:
        st.warning(
            "**Step 3 (Sizing) has not been run.** Run the operational sweep "
            "first — Step 3a ranks those configs by Project IRR."
        )
        if st.button("← Go to Step 3"):
            st.switch_page("pages/Step3_Sizing.py")
        st.stop()

    if not fin.get("enabled"):
        st.info(
            "Step 7 financial inputs have not been saved yet — the sweep will "
            "use the engine's Excel-anchored defaults (D13 fixture). Open "
            "Step 7 to customise PPA, capex, opex, or tax-shield assumptions "
            "before running."
        )

    sizing_df: pd.DataFrame = st.session_state.sizing_results

    # -------------------------------------------------------------------------
    # Sweep controls
    # -------------------------------------------------------------------------
    st.subheader("Sweep Configuration")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Operational Configs", len(sizing_df))
    with c2:
        load_mw = float(setup.get("load_mw", 25.0))
        st.metric("Load (MW)", f"{load_mw:.0f}")
    with c3:
        target_dc_mwp = float(
            fin.get("solar_capacity_mwp")
            or setup.get("solar_capacity_mw")
            or 82.0
        )
        st.metric("Solar DC (MWp)", f"{target_dc_mwp:.0f}")

    with st.expander("Engine assumptions"):
        st.markdown(
            f"- **Load profile:** flat {load_mw:.0f} MW from Step 1\n"
            f"- **Solar DC capacity:** {target_dc_mwp:.0f} MWp "
            "(Step 7 if set, else Step 1's solar_capacity_mw)\n"
            "- **PIRR engine inputs:** Step 7's saved financial state, falling "
            "back to D13 fixture defaults (PPA £170 × 10 yr, NIL indexation, "
            "RB depreciation, SHL on, UK CIR cap on total interest)\n"
            "- **Dispatch:** `dispatch_energy.run_hourly_dispatch` "
            "(solar-first, BESS fills gap, gas fills remainder). NOT the "
            "same dispatch as Step 3's operational sweep — see decisions log "
            "A24 for why."
        )

    run = st.button(
        "Run Financial Sweep", type="primary", use_container_width=True
    )

    # -------------------------------------------------------------------------
    # Run sweep
    # -------------------------------------------------------------------------
    if run:
        solar_mw_unscaled = get_solar_profile_array(setup)
        if solar_mw_unscaled is None or len(solar_mw_unscaled) < 8760:
            st.error(
                "Could not load an 8760-hour solar profile from Step 1. "
                "Check the Step 1 solar source selection."
            )
            st.stop()

        # Determine the DC MWp the profile represents. Per spec D8, the
        # canonical Burton Leonard CSVs are AC + grid-limit-capped output
        # for the declared DC MWp — they should be used as-is. Default the
        # reference MWp to the user's declared DC MWp → scaling factor = 1.0.
        # Users with a per-unit profile (rare) can still override by setting
        # `profile_reference_mwp` in Step 7's financial inputs. See
        # decisions log A25 (fix landed 2026-05-13 after smoke test §10).
        profile_ref_mwp = float(
            fin.get("profile_reference_mwp")
            or target_dc_mwp
            or solar_mw_unscaled.max()
            or 1.0
        )

        # Soft sanity-check warning: AC profile peak should be roughly
        # 50–110 % of declared DC MWp for a real UK utility-scale plant
        # (typical DC/AC ratio 1.2–1.4, with grid-limit capping in between).
        # Outside this band, the user has likely picked the wrong profile
        # for the declared DC MWp — don't block, but flag.
        profile_peak = float(solar_mw_unscaled.max())
        if target_dc_mwp > 0:
            ratio = profile_peak / target_dc_mwp
            if ratio < 0.5 or ratio > 1.1:
                st.warning(
                    f"Solar profile peak ({profile_peak:.1f} MW) is "
                    f"{ratio*100:.0f}% of declared DC capacity "
                    f"({target_dc_mwp:.0f} MWp). For a real UK utility-scale "
                    "plant, expect 50–110 % (DC/AC ratio 1.2–1.4 + grid cap). "
                    "If the profile is per-unit, set `profile_reference_mwp` "
                    "in Step 7 to its reference MWp."
                )

        # BESS efficiency comes from Step 1 (displayed as %; engine wants decimal)
        bess_eff = float(setup.get("bess_efficiency", 87.0)) / 100.0
        bess_min_soc = float(setup.get("bess_min_soc", 5.0)) / 100.0
        bess_max_soc = float(setup.get("bess_max_soc", 95.0)) / 100.0

        rows = sizing_df.to_dict(orient="records")
        total = len(rows)
        progress = st.progress(0)
        status = st.empty()

        t0 = time.time()
        sweep_results = []
        for i, cfg in enumerate(rows):
            status.text(
                f"Config {i + 1}/{total}: BESS {cfg.get('BESS (MWh)')} MWh "
                f"{cfg.get('Duration (hr)')}-hr, "
                f"DG {cfg.get('DG (MW)', 0.0):.0f} MW"
            )
            try:
                fin_out = run_pirr_for_config(
                    cfg,
                    solar_mw_unscaled,
                    target_dc_mwp=target_dc_mwp,
                    profile_ref_mwp=profile_ref_mwp,
                    load_mw=load_mw,
                    fin_state=fin,
                    setup_state=setup,
                    bess_efficiency_decimal=bess_eff,
                    bess_min_soc=bess_min_soc,
                    bess_max_soc=bess_max_soc,
                )
            except Exception as exc:
                fin_out = {
                    "Combined PIRR (%)": float("nan"),
                    "S+B PIRR (%)": float("nan"),
                    "Gas PIRR (%)": float("nan"),
                    "NPV (GBPm)": float("nan"),
                    "Total CAPEX (GBPm)": float("nan"),
                    "Lifetime Revenue (GBPm)": float("nan"),
                    "Payback (yrs)": float("nan"),
                    "Error": str(exc)[:80],
                }
            merged = {**cfg, **fin_out}
            sweep_results.append(merged)
            progress.progress((i + 1) / total)

        elapsed = time.time() - t0
        status.text(f"Complete. {total} configs in {elapsed:.1f}s.")
        progress.progress(1.0)

        financial_df = pd.DataFrame(sweep_results)
        st.session_state.financial_results = financial_df

        per_config = elapsed / max(total, 1) * 1000
        st.success(
            f"Ran {total} configs in {elapsed:.1f} s ({per_config:.0f} ms/config). "
            f"D16 budget: 8–12 s for 100 configs."
        )

        # --- TEMPORARY DEBUG (§16 smoke test) — remove after diagnosis ---
        _dbg_peak = float(solar_mw_unscaled.max()) if solar_mw_unscaled is not None else -1
        _dbg_fin_keys = sorted(fin.keys()) if fin else []
        _dbg_capex_bess = fin.get("capex_bess", "NOT SET")
        _dbg_enabled = fin.get("enabled", "NOT SET")
        st.warning(
            f"§16 DEBUG: profile_peak={_dbg_peak:.1f} MW, "
            f"fin.enabled={_dbg_enabled}, "
            f"fin.capex_bess={_dbg_capex_bess}, "
            f"fin has {len(_dbg_fin_keys)} keys, "
            f"target_dc_mwp={target_dc_mwp}"
        )

    # -------------------------------------------------------------------------
    # Results table
    # -------------------------------------------------------------------------
    if "financial_results" in st.session_state:
        results_df: pd.DataFrame = st.session_state.financial_results
        st.divider()
        st.subheader("Ranked Results")

        # Filter + sort
        col_a, col_b = st.columns([1, 2])
        with col_a:
            min_delivery = st.slider(
                "Min Delivery %", 0, 100, 0, step=5,
                help="Hide configs with operational delivery below this floor."
            )
        with col_b:
            sort_options = [
                "Combined PIRR (%)", "S+B PIRR (%)", "NPV (GBPm)",
                "Total CAPEX (GBPm)", "Payback (yrs)", "BESS (MWh)",
            ]
            sort_by = st.selectbox(
                "Sort by", sort_options, index=0,
            )

        view = results_df.copy()
        if "Delivery %" in view.columns and min_delivery > 0:
            view = view[view["Delivery %"] >= min_delivery]
        ascending = sort_by in ("Total CAPEX (GBPm)", "Payback (yrs)",
                                 "BESS (MWh)")
        view = view.sort_values(sort_by, ascending=ascending)

        # Headline column order: identity / operational / financial
        identity_cols = [c for c in (
            "BESS (MWh)", "Duration (hr)", "Power (MW)", "DG (MW)",
            "Containers"
        ) if c in view.columns]
        operational_cols = [c for c in (
            "Delivery %", "Green %", "Wastage %", "BESS Cycles"
        ) if c in view.columns]
        financial_cols = [
            "Combined PIRR (%)", "S+B PIRR (%)", "Gas PIRR (%)",
            "NPV (GBPm)", "Total CAPEX (GBPm)", "Payback (yrs)",
        ]
        ordered = identity_cols + operational_cols + financial_cols
        ordered = [c for c in ordered if c in view.columns]
        # Always include any Error column for visibility
        if "Error" in view.columns:
            ordered.append("Error")

        st.dataframe(
            view[ordered],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Combined PIRR (%)": st.column_config.NumberColumn(format="%.2f"),
                "S+B PIRR (%)": st.column_config.NumberColumn(format="%.2f"),
                "Gas PIRR (%)": st.column_config.NumberColumn(format="%.2f"),
                "NPV (GBPm)": st.column_config.NumberColumn(format="%.1f"),
                "Total CAPEX (GBPm)": st.column_config.NumberColumn(format="%.1f"),
                "Payback (yrs)": st.column_config.NumberColumn(format="%.1f"),
                "Delivery %": st.column_config.ProgressColumn(
                    min_value=0, max_value=100, format="%.1f%%"
                ),
                "Green %": st.column_config.ProgressColumn(
                    min_value=0, max_value=100, format="%.1f%%"
                ),
            },
        )

        # Best-config callout (highest Combined PIRR among visible rows)
        valid = view.dropna(subset=["Combined PIRR (%)"])
        if len(valid) > 0:
            best = valid.loc[valid["Combined PIRR (%)"].idxmax()]
            st.success(
                f"**Top by Combined PIRR:** {best.get('BESS (MWh)'):.0f} MWh "
                f"{best.get('Duration (hr)'):.0f}-hr / "
                f"{best.get('DG (MW)', 0.0):.0f} MW DG → "
                f"**{best['Combined PIRR (%)']:.2f}%** Combined "
                f"({best.get('S+B PIRR (%)', float('nan')):.2f}% S+B, "
                f"{best.get('Gas PIRR (%)', float('nan')):.2f}% Gas)"
            )

        # CSV download
        csv = results_df.to_csv(index=False)
        st.download_button(
            "Download financial sweep (CSV)",
            data=csv,
            file_name="financial_sweep.csv",
            mime="text/csv",
        )

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------
    st.divider()
    n1, n2, n3 = st.columns(3)
    with n1:
        if st.button("← Back to Step 3", use_container_width=True):
            st.switch_page("pages/Step3_Sizing.py")
    with n2:
        if st.button("Open single-config Step 7 →", use_container_width=True):
            st.switch_page("pages/Step7_Financial.py")
    with n3:
        if st.button("Next → Step 4 Results", type="primary",
                     use_container_width=True):
            mark_step_completed(3)
            st.switch_page("pages/Step4_Results.py")


main()
