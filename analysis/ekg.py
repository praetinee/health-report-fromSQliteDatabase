import streamlit as st
from ui.advice_box import render_advice_box

def render_ekg_section(person):
    st.subheader("ผลตรวจคลื่นไฟฟ้าหัวใจ (EKG)")

    result = person.get("EKG", "-")
    st.markdown(f"**ผล EKG:** {result}")

    # ถ้ามีคำแนะนำเกี่ยวกับ EKG แสดงกล่องคำแนะนำ
    render_advice_box(person.get("DOCTER suggest", ""))
