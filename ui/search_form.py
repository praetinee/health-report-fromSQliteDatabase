import streamlit as st
import pandas as pd

def render_search_form(df: pd.DataFrame):
    st.sidebar.header("🔍 ค้นหาข้อมูลผู้รับบริการ")

    query = st.sidebar.text_input("กรอกชื่อ, เลขบัตรประชาชน หรือ HN").strip()
    if not query:
        return None

    # ✅ ล้างช่องว่างและ .0 ที่ติดมาใน HN เพื่อความแม่นยำ
    df["HN_clean"] = (
        df["HN"]
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
    )
    query_clean = query.strip()

    # ✅ เงื่อนไขกรอง: HN ต้องเป๊ะ, ชื่อ/เลขบัตรใช้ contains ได้
    filtered = df[
        df["ชื่อ-สกุล"].str.contains(query_clean, case=False, na=False) |
        df["เลขบัตรประชาชน"].astype(str).str.contains(query_clean, na=False) |
        (df["HN_clean"] == query_clean)
    ]

    if filtered.empty:
        st.sidebar.warning("ไม่พบข้อมูล")
        return None

    # ✅ ถ้ามีมากกว่า 1 รายการ ให้เลือกชื่อ
    if len(filtered) > 1:
        person_names = sorted(filtered["ชื่อ-สกุล"].unique())
        selected_name = st.sidebar.selectbox("เลือกชื่อ", person_names)
        if not selected_name:
            return None
        person_df = filtered[filtered["ชื่อ-สกุล"] == selected_name]
    else:
        person_df = filtered

    if person_df.empty:
        return None

    years = sorted(person_df["Year"].dropna().unique(), reverse=True)
    if not years:
        return None

    selected_year = st.sidebar.selectbox("เลือกปี", years)
    df_year = person_df[person_df["Year"] == selected_year]

    if df_year.empty:
        return None

    if len(df_year) > 1:
        index = st.sidebar.selectbox("เลือกครั้งที่ตรวจ", df_year.index, format_func=lambda i: f"ครั้งที่ {i}")
        if index not in df_year.index:
            return None
        person = df_year.loc[index]
    else:
        person = df_year.iloc[0]

    return person
