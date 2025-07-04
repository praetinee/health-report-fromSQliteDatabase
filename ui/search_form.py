import streamlit as st
import pandas as pd

def render_search_form(df: pd.DataFrame):
    st.sidebar.header("🔍 ค้นหาข้อมูลผู้รับบริการ")

    # ✅ เตรียม HN แบบไม่มีทศนิยมไว้ก่อน
    df["HN_clean"] = df["HN"].apply(lambda x: str(int(float(x))) if str(x).strip() != "" else "")

    query = st.sidebar.text_input("กรอกชื่อ, เลขบัตรประชาชน หรือ HN").strip()
    if not query:
        return None

    # ✅ ลองค้นหาแบบ exact HN ก่อน
    exact_match = df[df["HN_clean"] == query]
    if not exact_match.empty:
        filtered = exact_match
    else:
        # ✅ fallback ถ้าไม่ตรงเป๊ะ → ใช้ contains แบบเดิม
        filtered = df[
            df["ชื่อ-สกุล"].str.contains(query, case=False, na=False) |
            df["เลขบัตรประชาชน"].astype(str).str.contains(query, na=False) |
            df["HN_clean"].astype(str).str.contains(query, na=False)
        ]

    if filtered.empty:
        st.sidebar.warning("ไม่พบข้อมูล")
        return None

    # 🧠 ส่วนที่เหลือเหมือนเดิม
    person_names = sorted(filtered["ชื่อ-สกุล"].unique())
    selected_name = st.sidebar.selectbox("เลือกชื่อ", person_names)
    if not selected_name:
        return None

    person_df = filtered[filtered["ชื่อ-สกุล"] == selected_name]
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
