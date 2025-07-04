import streamlit as st

def render_section_header(title: str, subtitle: str = None):
    st.markdown(f"## 🟦 {title}")
    if subtitle:
        st.markdown(f"#### {subtitle}")
