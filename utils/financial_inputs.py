"""
Shared helpers for the financial-inputs UI.

Extracted from Step 7 in 2026-05-21 wizard reorg (A48). Step 2b (Financial
Setup) is the writer of `wizard['financial']`; Step 7 reads it. Both pages
share these tiny helpers — keeping them here avoids a circular Step 7 ←→
Step 2b import.

Decisions log: docs/Project_IRR_Integration_Decisions.md A48.
"""

from src.wizard_state import get_wizard_state, update_wizard_section


MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def pct_to_display(val):
    """Convert decimal fraction (0.003) to display % (0.3)."""
    if val is not None and val < 1:
        return val * 100
    return val


def display_to_pct(val):
    """Convert display % (0.3) to decimal fraction (0.003)."""
    if val is not None:
        return val / 100
    return val


def get_financial_state():
    """Get the financial section of wizard state."""
    state = get_wizard_state()
    return state.get('financial', {})


def save_financial_inputs(updates: dict):
    """Save financial inputs to wizard state."""
    update_wizard_section('financial', updates)
