"""
Step 2: Dispatch Rules

Define constraints that determine dispatch behavior.
The system infers the appropriate template from user answers.
"""

import streamlit as st

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wizard_state import (
    init_wizard_state, get_wizard_state, update_wizard_state,
    update_wizard_section, set_current_step, mark_step_completed,
    validate_step_2, get_step_status, can_navigate_to_step
)
from src.template_inference import (
    infer_template, get_template_info, get_template_display_card,
    get_valid_triggers_for_timing, TEMPLATES
)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="BESS Sizing - Dispatch Rules",
    page_icon="📋",
    layout="wide"
)

# Initialize wizard state
init_wizard_state()
set_current_step(2)

# Check if can access this step
if not can_navigate_to_step(2):
    st.warning("Please complete Step 1 first.")
    if st.button("Go to Step 1"):
        st.switch_page("pages/8_🚀_Step1_Setup.py")
    st.stop()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_step_indicator():
    """Render the step progress indicator."""
    steps = [
        ("1", "Setup", get_step_status(1)),
        ("2", "Rules", get_step_status(2)),
        ("3", "Sizing", get_step_status(3)),
        ("4", "Results", get_step_status(4)),
        ("5", "Analysis", get_step_status(5)),
    ]

    cols = st.columns(5)
    for i, (num, label, status) in enumerate(steps):
        with cols[i]:
            if status == 'completed':
                st.markdown(f"✅ **Step {num}**: {label}")
            elif status == 'current':
                st.markdown(f"🔵 **Step {num}**: {label}")
            elif status == 'pending':
                st.markdown(f"⚪ Step {num}: {label}")
            else:
                st.markdown(f"🔒 Step {num}: {label}")


def render_template_card(template_id: int, dg_charges_bess: bool = False, dg_load_priority: str = 'bess_first'):
    """Render an informational card showing the inferred template."""
    info = get_template_info(template_id)

    # Color coding based on DG usage
    if not info['dg_enabled']:
        border_color = "#2ecc71"  # Green
        icon = "☀️"
    else:
        border_color = "#3498db"  # Blue
        icon = "⚡"

    # Build merit order based on load priority
    if not info['dg_enabled']:
        merit_order = info['merit_order']
    elif dg_load_priority == 'dg_first':
        merit_order = "Solar → DG → BESS → Unserved"
        if dg_charges_bess:
            merit_order += " + DG→Battery"
    else:  # bess_first
        merit_order = "Solar → BESS → DG → Unserved"
        if dg_charges_bess:
            merit_order += " + DG→Battery"

    # Build description with DG charging note
    description = info['description']
    if info['dg_enabled']:
        if dg_charges_bess:
            description += " (Excess DG charges battery)"
        else:
            description += " (Battery charges from solar only)"

    st.markdown(f"""
    <div style="
        border: 2px solid {border_color};
        border-radius: 10px;
        padding: 15px;
        background-color: rgba(255,255,255,0.05);
    ">
        <h4 style="margin: 0;">{icon} {info['name']}</h4>
        <p style="color: #888; margin: 5px 0;">{merit_order}</p>
        <p style="margin: 5px 0;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("📋 Dispatch Rules")
st.markdown("### Step 2 of 4: Define How Your System Operates")

render_step_indicator()

st.divider()

# Get current state
state = get_wizard_state()
setup = state['setup']
rules = state['rules']

dg_enabled = setup['dg_enabled']


# =============================================================================
# NO DG - SIMPLIFIED VIEW
# =============================================================================

if not dg_enabled:
    st.markdown("### Dispatch Strategy")

    st.info("Your system has no generator. The dispatch strategy is automatically set to **Solar + BESS Only**.")

    render_template_card(0)

    st.markdown("""
    **How it works:**
    1. Solar power serves load directly
    2. Excess solar charges the battery
    3. Battery discharges when solar is insufficient
    4. Any remaining deficit is unserved load
    """)

    # Set template to 0
    update_wizard_state('rules', 'inferred_template', 0)


# =============================================================================
# WITH DG - QUESTION-BASED TEMPLATE INFERENCE
# =============================================================================

else:
    st.markdown("### How should your system operate?")
    st.markdown("Answer the questions below to configure your dispatch strategy.")

    st.markdown("---")

    # Question 1: When can the generator run?
    st.markdown("#### 1. When can the generator run?")

    dg_timing_options = {
        'anytime': "Anytime (no restrictions)",
        'day_only': "Day only (nights must be silent)",
        'night_only': "Night only (days must be green)",
        'custom_blackout': "Custom blackout window",
    }

    dg_timing = st.radio(
        "Select when the generator is allowed to operate:",
        options=list(dg_timing_options.keys()),
        format_func=lambda x: dg_timing_options[x],
        index=list(dg_timing_options.keys()).index(rules['dg_timing']),
        key='dg_timing_radio'
    )
    update_wizard_state('rules', 'dg_timing', dg_timing)

    # Show time window settings if applicable
    if dg_timing == 'day_only':
        col1, col2 = st.columns(2)
        with col1:
            day_start = st.slider(
                "Day starts at",
                min_value=0, max_value=23,
                value=rules['day_start'],
                key='day_start_slider'
            )
            update_wizard_state('rules', 'day_start', day_start)
        with col2:
            day_end = st.slider(
                "Day ends at",
                min_value=0, max_value=23,
                value=rules['day_end'],
                key='day_end_slider'
            )
            update_wizard_state('rules', 'day_end', day_end)

    elif dg_timing == 'night_only':
        col1, col2 = st.columns(2)
        with col1:
            night_start = st.slider(
                "Night starts at",
                min_value=0, max_value=23,
                value=rules['night_start'],
                key='night_start_slider'
            )
            update_wizard_state('rules', 'night_start', night_start)
        with col2:
            night_end = st.slider(
                "Night ends at",
                min_value=0, max_value=23,
                value=rules['night_end'],
                key='night_end_slider'
            )
            update_wizard_state('rules', 'night_end', night_end)

    elif dg_timing == 'custom_blackout':
        col1, col2 = st.columns(2)
        with col1:
            blackout_start = st.slider(
                "Blackout starts at",
                min_value=0, max_value=23,
                value=rules['blackout_start'],
                key='blackout_start_slider'
            )
            update_wizard_state('rules', 'blackout_start', blackout_start)
        with col2:
            blackout_end = st.slider(
                "Blackout ends at",
                min_value=0, max_value=23,
                value=rules['blackout_end'],
                key='blackout_end_slider'
            )
            update_wizard_state('rules', 'blackout_end', blackout_end)
        st.caption(f"Generator cannot run from {blackout_start}:00 to {blackout_end}:00")

    st.markdown("---")

    # Question 2: What triggers the generator?
    st.markdown("#### 2. What triggers the generator to start?")

    # Get valid triggers based on timing
    valid_triggers = get_valid_triggers_for_timing(dg_timing)

    if len(valid_triggers) > 0:
        trigger_options = {t[0]: t[1] for t in valid_triggers}

        # Set default if current selection is not valid
        current_trigger = rules['dg_trigger']
        if current_trigger not in trigger_options:
            current_trigger = list(trigger_options.keys())[0]
            update_wizard_state('rules', 'dg_trigger', current_trigger)

        dg_trigger = st.radio(
            "Select what triggers the generator:",
            options=list(trigger_options.keys()),
            format_func=lambda x: trigger_options[x],
            index=list(trigger_options.keys()).index(current_trigger),
            key='dg_trigger_radio'
        )
        update_wizard_state('rules', 'dg_trigger', dg_trigger)

        # Show SoC thresholds if SoC-based
        if dg_trigger == 'soc_based':
            st.markdown("**SoC Thresholds:**")
            col1, col2 = st.columns(2)
            with col1:
                soc_on = st.slider(
                    "Turn ON when SOC drops below (%)",
                    min_value=int(setup['bess_min_soc']),
                    max_value=int(setup['bess_max_soc']) - 10,
                    value=int(rules['soc_on_threshold']),
                    step=5,
                    key='soc_on_slider'
                )
                update_wizard_state('rules', 'soc_on_threshold', float(soc_on))
            with col2:
                soc_off = st.slider(
                    "Turn OFF when SOC reaches (%)",
                    min_value=soc_on + 10,
                    max_value=int(setup['bess_max_soc']),
                    value=max(int(rules['soc_off_threshold']), soc_on + 10),
                    step=5,
                    key='soc_off_slider'
                )
                update_wizard_state('rules', 'soc_off_threshold', float(soc_off))

            deadband = soc_off - soc_on
            if deadband < 20:
                st.warning(f"⚠️ Small deadband ({deadband}%) may cause frequent DG cycling")

        elif dg_trigger == 'proactive':
            st.info("Generator will start at the beginning of the allowed window and charge the battery proactively.")

    st.markdown("---")

    # Question 3: Can DG charge the battery?
    st.markdown("#### 3. Can the generator charge the battery?")

    dg_charges_bess = st.radio(
        "Can excess generator power charge the battery?",
        options=[False, True],
        format_func=lambda x: "Yes — excess generator power can charge battery" if x else "No — battery charges from solar only",
        index=1 if rules['dg_charges_bess'] else 0,
        key='dg_charges_bess_radio'
    )
    update_wizard_state('rules', 'dg_charges_bess', dg_charges_bess)

    st.markdown("---")

    # Question 4: Load serving priority
    st.markdown("#### 4. When DG runs, how should it serve the load?")

    dg_load_priority = st.radio(
        "Select the load-serving priority:",
        options=['bess_first', 'dg_first'],
        format_func=lambda x: {
            'bess_first': "BESS First — Battery serves load, DG fills remaining gap",
            'dg_first': "DG First — Generator serves load directly, excess charges BESS"
        }[x],
        index=0 if rules.get('dg_load_priority', 'bess_first') == 'bess_first' else 1,
        key='dg_load_priority_radio'
    )
    update_wizard_state('rules', 'dg_load_priority', dg_load_priority)

    if dg_load_priority == 'bess_first':
        st.caption("Merit order: Solar → BESS → DG → Unserved")
    else:
        st.caption("Merit order: Solar → DG → BESS → Unserved")

    st.markdown("---")

    # Question 5: DG Takeover Mode
    st.markdown("#### 5. When DG runs, should it take over full load?")

    dg_takeover_mode = st.radio(
        "Select DG takeover behavior:",
        options=[False, True],
        format_func=lambda x: {
            False: "No — DG fills gap only (standard)",
            True: "Yes — DG serves full load, solar goes to BESS"
        }[x],
        index=1 if rules.get('dg_takeover_mode', False) else 0,
        key='dg_takeover_mode_radio'
    )
    update_wizard_state('rules', 'dg_takeover_mode', dg_takeover_mode)

    if dg_takeover_mode:
        st.caption("When DG runs: DG → Load (full), Solar → BESS. Zero DG curtailment.")
    else:
        st.caption("When DG runs: DG fills gap between (Solar + BESS) and Load.")

    st.markdown("---")

    # Infer and display template
    template_id = infer_template(
        dg_enabled=True,
        dg_timing=dg_timing,
        dg_trigger=rules['dg_trigger']
    )
    update_wizard_state('rules', 'inferred_template', template_id)

    st.markdown("### 📊 Dispatch Strategy Selected")
    render_template_card(template_id, dg_charges_bess, dg_load_priority)


st.divider()


# =============================================================================
# VALIDATION & NAVIGATION
# =============================================================================

is_valid, errors = validate_step_2()

if errors:
    for error in errors:
        if error.startswith("Warning"):
            st.warning(error)
        else:
            st.error(error)

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Back to Setup", width='stretch'):
        st.switch_page("pages/8_🚀_Step1_Setup.py")

with col3:
    if st.button("Next → Sizing Range", type="primary", disabled=not is_valid, width='stretch'):
        mark_step_completed(2)
        st.switch_page("pages/10_📐_Step3_Sizing.py")


# Sidebar summary
with st.sidebar:
    st.markdown("### 📋 Configuration Summary")

    # From Step 1
    st.markdown("**Step 1 - Setup:**")
    st.markdown(f"- Load: {setup['load_mw']} MW")
    st.markdown(f"- Solar: {setup['solar_capacity_mw']} MWp")
    st.markdown(f"- DG: {'Enabled' if dg_enabled else 'Disabled'}")

    st.markdown("---")

    # Step 2
    st.markdown("**Step 2 - Rules:**")
    template_info = get_template_info(rules['inferred_template'])
    st.markdown(f"- Strategy: {template_info['name']}")
    if dg_enabled:
        st.markdown(f"- DG Timing: {rules['dg_timing'].replace('_', ' ').title()}")
        st.markdown(f"- DG Trigger: {rules['dg_trigger'].replace('_', ' ').title()}")
        st.markdown(f"- DG Charges BESS: {'Yes' if rules['dg_charges_bess'] else 'No'}")
        load_priority_display = "BESS First" if rules.get('dg_load_priority', 'bess_first') == 'bess_first' else "DG First"
        st.markdown(f"- Load Priority: {load_priority_display}")
        st.markdown(f"- Takeover Mode: {'Yes' if rules.get('dg_takeover_mode', False) else 'No'}")
