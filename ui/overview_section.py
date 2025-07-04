import streamlit as st
from utils import convert_to_bmi, safe_text

def render_overview(person):
    name = safe_text(person["ชื่อ-สกุล"])
    sex = safe_text(person["เพศ"])
    age = safe_text(person["อายุ"])
    hn = safe_text(person["HN"])
    weight = person.get("น้ำหนัก", "")
    height = person.get("ส่วนสูง", "")
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse = person.get("pulse", "")

    bmi = convert_to_bmi(weight, height)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"**ชื่อ:** {name}")
        st.markdown(f"**เพศ:** {sex}")
        st.markdown(f"**อายุ:** {age} ปี")

    with col2:
        st.markdown(f"**HN:** {hn}")
        st.markdown(f"**น้ำหนัก:** {weight} กก.")
        st.markdown(f"**ส่วนสูง:** {height} ซม.")

    with col3:
        st.markdown(f"**BMI:** {bmi if bmi else '-'}")
        st.markdown(f"**ความดัน:** {sbp} / {dbp} mmHg")
        st.markdown(f"**ชีพจร:** {pulse} bpm")
