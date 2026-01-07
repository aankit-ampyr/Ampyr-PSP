"""
ARCHIVED: Degradation & Sizing Strategy Section
Originally from Step1_Setup.py - to be added back after initial Year 1 sizing is complete.

To use: Copy this section back into the appropriate setup page after the BESS Parameters section.
"""

# =============================================================================
# DEGRADATION & SIZING STRATEGY SECTION
# =============================================================================

# Required imports (already in Step1_Setup.py):
# from src.wizard_state import update_wizard_state

"""
st.divider()

st.subheader("📉 Degradation & Sizing Strategy")

strategy_options = ['standard', 'overbuild', 'augmentation']
current_strategy = setup.get('degradation_strategy', 'standard')
strategy_index = strategy_options.index(current_strategy) if current_strategy in strategy_options else 0

degradation_strategy = st.radio(
    "Battery Sizing Strategy",
    options=strategy_options,
    index=strategy_index,
    format_func=lambda x: {
        'standard': 'Standard — Size for Year 1 performance',
        'overbuild': 'Overbuild — Add capacity buffer for degradation',
        'augmentation': 'Augmentation — Plan mid-life capacity addition'
    }.get(x, x),
    horizontal=True,
    key='degradation_strategy_radio'
)
update_wizard_state('setup', 'degradation_strategy', degradation_strategy)

# Strategy-specific inputs
col1, col2 = st.columns(2)

with col1:
    if degradation_strategy == 'overbuild':
        overbuild_pct = st.slider(
            "Overbuild Factor (%)",
            min_value=10,
            max_value=50,
            value=int(setup.get('overbuild_factor', 0.20) * 100),
            step=5,
            help="Extra capacity to compensate for degradation over project life",
            key='overbuild_factor_slider'
        )
        update_wizard_state('setup', 'overbuild_factor', overbuild_pct / 100)

        st.info(f"Example: 100 MWh required x {1 + overbuild_pct/100:.2f} = {100 * (1 + overbuild_pct/100):.0f} MWh installed")

    elif degradation_strategy == 'augmentation':
        aug_year = st.number_input(
            "Augmentation Year",
            min_value=3,
            max_value=15,
            value=int(setup.get('augmentation_year', 8)),
            step=1,
            help="Year to add replacement capacity to restore performance",
            key='augmentation_year_input'
        )
        update_wizard_state('setup', 'augmentation_year', aug_year)

        st.info(f"Capacity will be restored in Year {aug_year} to maintain target delivery")

    else:
        st.caption("Standard sizing: Battery sized for Year 1 requirements. Performance may degrade over time.")

with col2:
    # Advanced degradation settings
    with st.expander("⚙️ Advanced Degradation Settings"):
        calendar_rate = st.slider(
            "Calendar Degradation (%/year)",
            min_value=0.5,
            max_value=5.0,
            value=float(setup.get('calendar_degradation_rate', 0.02) * 100),
            step=0.5,
            help="Baseline capacity loss per year from calendar aging",
            key='calendar_deg_slider'
        )
        update_wizard_state('setup', 'calendar_degradation_rate', calendar_rate / 100)

        use_rainflow = st.checkbox(
            "Use Rainflow Cycle Counting",
            value=setup.get('use_rainflow_counting', True),
            help="Advanced DoD-weighted cycle counting for more accurate degradation",
            key='use_rainflow_check'
        )
        update_wizard_state('setup', 'use_rainflow_counting', use_rainflow)

        include_calendar = st.checkbox(
            "Include Calendar Aging",
            value=setup.get('include_calendar_aging', True),
            help="Add time-based degradation in addition to cycle degradation",
            key='include_calendar_check'
        )
        update_wizard_state('setup', 'include_calendar_aging', include_calendar)

st.divider()
"""
