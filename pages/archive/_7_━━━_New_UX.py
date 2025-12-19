"""
Separator page - redirects to the new wizard
"""
import streamlit as st

st.set_page_config(
    page_title="New UX Section",
    page_icon="━",
    layout="wide"
)

st.markdown("## 🆕 New Sizing Wizard")
st.markdown("---")
st.markdown("""
The new wizard provides a streamlined 5-step process for BESS & DG sizing:

1. **Setup** - Define load, solar, and battery parameters
2. **Rules** - Configure dispatch strategy through simple questions
3. **Sizing** - Set capacity ranges and duration classes
4. **Results** - Analyze, filter, and compare configurations
5. **Analysis** - Detailed hourly dispatch visualization

""")

if st.button("🚀 Start New Sizing Wizard", type="primary", width='stretch'):
    st.switch_page("pages/8_🚀_Step1_Setup.py")

st.markdown("---")
st.caption("The pages below (0-6) contain the original advanced interface.")
