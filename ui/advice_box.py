import streamlit as st

def render_advice_box(text: str):
    if not text or str(text).strip() == "":
        return  # ไม่แสดงอะไรเลย

    st.markdown(
        f"""
        <div style='
            background-color: rgba(255, 255, 0, 0.2);
            padding: 1rem;
            border-radius: 0.5rem;
            margin-top: 1rem;
            border: 1px solid #ff0;
        '>
            <strong>📌 คำแนะนำ:</strong><br>{text}
        </div>
        """,
        unsafe_allow_html=True
    )
