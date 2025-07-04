import streamlit as st
from ui.advice_box import render_advice_box

def render_stool_section(person):
    st.subheader("ผลตรวจอุจจาระ")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**ลักษณะ (StoolCharactor):** {person.get('StoolCharactor', '-')}")
        st.markdown(f"**สี (StoolColor):** {person.get('StoolColor', '-')}")
        st.markdown(f"**เม็ดเลือดแดง (StoolRBC):** {person.get('StoolRBC', '-')}")
    with col2:
        st.markdown(f"**เม็ดเลือดขาว (StoolWBC):** {person.get('StoolWBC', '-')}")
        st.markdown(f"**Parasite:** {person.get('StoolParasite', '-')}")
        st.markdown(f"**Protozoa:** {person.get('StoolProtozoa', '-')}")

    st.markdown(f"**ผลรวม (Stool exam):** {person.get('Stool exam', '-')}")

    # แสดงคำแนะนำอุจจาระ ถ้ามี (ถ้าใช้ column นี้)
    render_advice_box(person.get("คำแนะนำอุจจาระ", ""))
