import streamlit as st
from ui.advice_box import render_advice_box

def render_hepatitis_section(person):
    st.subheader("ไวรัสตับอักเสบ A")
    st.markdown(f"**ผล Hepatitis A:** {person.get('HEPATITIS A', '-')}")

    st.subheader("ไวรัสตับอักเสบ B")
    st.markdown(f"**ผล Hepatitis B:** {person.get('HEPATITIS B', '-')}")
    st.markdown(f"**HbsAg:** {person.get('HbsAg', '-')}")
    st.markdown(f"**HbsAb:** {person.get('HbsAb', '-')}")
    st.markdown(f"**HBcAB:** {person.get('HBcAB', '-')}")

    # คำแนะนำหรือสรุปที่เกี่ยวข้องกับการตรวจไวรัสตับ
    render_advice_box(person.get("สรุปประวัติ Hepb", ""))
