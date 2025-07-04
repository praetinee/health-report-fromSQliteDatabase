import streamlit as st
from utils import get_float, flag
from ui.advice_box import render_advice_box

def render_cbc_section(person):
    wbc = get_float("WBC (cumm)", person)
    hb = get_float("Hb(%)", person)
    hct = get_float("HCT", person)
    plt = get_float("Plt (/mm)", person)

    col1, col2 = st.columns(2)

    with col1:
        _render_value("WBC", wbc, 4.5, 10.5, unit="x10³/µL")
        _render_value("Hb", hb, 12, 16, unit="g/dL")
    with col2:
        _render_value("HCT", hct, 37, 47, unit="%")
        _render_value("Plt", plt, 150, 450, unit="x10³/µL")

    render_advice_box(person.get("คำแนะนำCBC", ""))


def _render_value(label, val, low, high, unit=""):
    if val is None:
        st.markdown(f"**{label}:** -")
        return

    alert = flag(val, low, high)
    style = "background-color: rgba(255,0,0,0.2); padding: 0.2rem;" if alert else ""
    st.markdown(
        f"<div style='{style}'><strong>{label}:</strong> {val} {unit}</div>",
        unsafe_allow_html=True
    )
