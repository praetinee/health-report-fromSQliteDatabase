import streamlit as st
from utils import get_float
from ui.advice_box import render_advice_box

def render_urine_section(person):
    st.subheader("ค่าพื้นฐานในปัสสาวะ")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**สี (Color):** {person.get('Color', '-')}")
        st.markdown(f"**pH:** {person.get('pH', '-')}")
        st.markdown(f"**Alb (Albumin):** {person.get('Alb', '-')}")
    with col2:
        st.markdown(f"**Sugar:** {person.get('sugar', '-')}")
        st.markdown(f"**RBC:** {person.get('RBC1', '-')}")
        st.markdown(f"**WBC:** {person.get('WBC1', '-')}")

    st.subheader("ผลการแปลผลเบื้องต้น")
    st.markdown(f"**Albumin:** {person.get('ผลAlb.UA', '-')}")
    st.markdown(f"**Sugar:** {person.get('ผลSugar.UA', '-')}")
    st.markdown(f"**RBC:** {person.get('ผลRBC.UA', '-')}")
    st.markdown(f"**WBC:** {person.get('ผลWBC.UA', '-')}")

    render_advice_box(person.get("คำแนะนำปัสสาวะ", ""))
