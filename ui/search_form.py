import streamlit as st
import pandas as pd

def render_search_form(df: pd.DataFrame):
    st.sidebar.header("🔍 ค้นหาข้อมูลผู้รับบริการ")

    query = st.sidebar.text_input("กรอกชื่อ, เลขบัตรประชาชน หรือ HN").strip()
    if not query:
        return None

    filtered = df[
        df["ชื่อ-สกุล"].str.contains(query, case=False, na=False) |
        df["เลขบัตรประชาชน"].astype(str).str.contains(query) |
        df["HN"].astype(str).str.contains(query)
    ]

    if filtered.empty:
        st.sidebar.warning("ไม่พบข้อมูล")
        return None

    person_names = sorted(filtered["ชื่อ-สกุล"].unique())
    selected_name = st.sidebar.selectbox("เลือกชื่อ", person_names)

    person_df = filtered[filtered["ชื่อ-สกุล"] == selected_name]

    years = sorted(person_df["Year"].unique(), reverse=True)
    selected_year = st.sidebar.selectbox("เลือกปี", years)

    df_year = person_df[person_df["Year"] == selected_year]

    if len(df_year) > 1:
        index = st.sidebar.selectbox("เลือกครั้งที่ตรวจ", df_year.index, format_func=lambda i: f"ครั้งที่ {i}")
        person = df_year.loc[index]
    else:
        person = df_year.iloc[0]

    return person
