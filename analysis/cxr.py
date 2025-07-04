import streamlit as st
from ui.advice_box import render_advice_box

def render_cxr_section(person):
    st.subheader("ผลการตรวจ X-ray ปอด")

    result = person.get("CXR", "-")
    st.markdown(f"**ผล X-ray:** {result}")

    # ถ้ามีคำแนะนำเฉพาะด้าน X-ray ให้ใส่ตรงนี้
    render_advice_box(person.get("คำแนะนำXray", ""))
