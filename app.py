import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.title("ระบบรายงานผลตรวจสุขภาพ")

DB_PATH = "SQliteDatabase รวมทุกปี.db"

@st.cache_data(ttl=300)
def load_data_from_db(citizen_or_name):
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT * FROM health_data
        WHERE "เลขที่ ว." = ? OR "ชื่อ-สกุล" LIKE ?
    """
    df = pd.read_sql_query(query, conn, params=(citizen_or_name, f"%{citizen_or_name}%"))
    conn.close()
    return df

user_input = st.text_input("กรอกเลขที่ ว. หรือ ชื่อ-สกุล")

if user_input:
    df = load_data_from_db(user_input)

    if df.empty:
        st.warning("ไม่พบข้อมูลที่ตรงกับที่กรอก")
    else:
        st.success(f"พบข้อมูลจำนวน {len(df)} รายการ")
        st.dataframe(df)

        st.subheader("สรุปค่าทั่วไป")
        basic_cols = ["วันที่ตรวจ", "ชื่อ-สกุล", "เพศ", "อายุ", "น้ำหนัก", "ส่วนสูง", "รอบเอว", "BMI", "SBP", "DBP", "pulse"]
        summary = df[basic_cols].copy()
        st.table(summary.set_index("วันที่ตรวจ"))
