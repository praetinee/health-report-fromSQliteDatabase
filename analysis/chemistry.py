import streamlit as st
from utils import get_float, flag
from ui.advice_box import render_advice_box

def render_chemistry_section(person):
    render_fbs(person)
    render_lipid(person)
    render_liver(person)
    render_kidney(person)

    for key in ["คำแนะนำchem1", "คำแนะนำchem2", "คำแนะนำchem3", "คำแนะนำchem4", "คำแนะนำchem5"]:
        render_advice_box(person.get(key, ""))


def render_fbs(person):
    st.subheader("น้ำตาลในเลือด (FBS)")
    fbs = get_float("FBS", person)
    _render_value("FBS", fbs, 70, 100, "mg/dL")


def render_lipid(person):
    st.subheader("ไขมันในเลือด")
    chol = get_float("CHOL", person)
    tgl = get_float("TGL", person)
    hdl = get_float("HDL", person)
    ldl = get_float("LDL", person)

    _render_value("Cholesterol", chol, 0, 200, "mg/dL")
    _render_value("Triglyceride", tgl, 0, 150, "mg/dL")
    _render_value("HDL", hdl, 40, 100, "mg/dL")
    _render_value("LDL", ldl, 0, 130, "mg/dL")


def render_liver(person):
    st.subheader("การทำงานของตับ")
    sgot = get_float("SGOT", person)
    sgpt = get_float("SGPT", person)
    alp = get_float("ALP", person)

    _render_value("SGOT", sgot, 0, 40, "U/L")
    _render_value("SGPT", sgpt, 0, 40, "U/L")
    _render_value("ALP", alp, 40, 130, "U/L")


def render_kidney(person):
    st.subheader("การทำงานของไต")
    bun = get_float("BUN", person)
    cr = get_float("Cr", person)
    gfr = get_float("GFR", person)

    _render_value("BUN", bun, 7, 20, "mg/dL")
    _render_value("Creatinine", cr, 0.5, 1.2, "mg/dL")
    _render_value("GFR", gfr, 90, 120, "mL/min/1.73m²")


def _render_value(label, val, low, high, unit=""):
    if val is None:
        st.markdown(f"**{label}:** -")
        return

    is_alert = flag(val, low, high)
    style = "background-color: rgba(255,0,0,0.2); padding: 0.2rem;" if is_alert else ""
    st.markdown(
        f"<div style='{style}'><strong>{label}:</strong> {val} {unit}</div>",
        unsafe_allow_html=True
    )
