import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.title("🩺 ระบบรายงานผลตรวจสุขภาพ")

DB_PATH = "SQliteDatabase_AllData.db"  # ← ใช้ชื่อใหม่ตามที่คุณตั้งไว้

# ===== โหลดข้อมูลตัวอย่าง 5 แถว เพื่อเช็กคอลัมน์ =====
@st.cache_data(ttl=300)
def get_preview():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM health_data LIMIT 5", conn)
    conn.close()
    return df

st.subheader("🔎 ตัวอย่างข้อมูล (แถวแรกของตาราง)")
try:
    preview = get_preview()
    st.dataframe(preview)
except Exception as e:
    st.error("ไม่สามารถโหลดข้อมูลตัวอย่างได้ กรุณาตรวจสอบฐานข้อมูล")
    st.exception(e)

# ===== ค้นหาข้อมูลด้วย HN, ชื่อ-สกุล หรือ เลขบัตร =====
st.subheader("ค้นหาผลตรวจสุขภาพ")
search = st.text_input("กรอก HN หรือ ชื่อ-สกุล หรือ เลขบัตรประชาชน")

if search:
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT * FROM health_data
            WHERE [HN] LIKE ? OR [ชื่อ-สกุล] LIKE ? OR [เลขบัตรประชาชน] LIKE ?
        """
        df = pd.read_sql_query(query, conn, params=(f"%{search}%", f"%{search}%", f"%{search}%"))
        conn.close()

        if df.empty:
            st.warning("ไม่พบข้อมูลที่ตรงกับคำค้น")
        else:
            st.success(f"พบข้อมูล {len(df)} รายการที่เกี่ยวข้อง")
            st.dataframe(df)

            # ===== สรุปค่าทั่วไป =====
            st.subheader("📋 สรุปข้อมูลสุขภาพเบื้องต้น")
            cols = ["วันที่ตรวจ", "ชื่อ-สกุล", "เพศ", "อายุ", "น้ำหนัก", "ส่วนสูง", "รอบเอว", "BMI", "SBP", "DBP", "pulse"]
            existing_cols = [col for col in cols if col in df.columns]
            if existing_cols:
                st.table(df[existing_cols].set_index("วันที่ตรวจ") if "วันที่ตรวจ" in df.columns else df[existing_cols])
            else:
                st.info("ไม่พบคอลัมน์ข้อมูลสุขภาพเบื้องต้นในตาราง")
    except Exception as e:
        st.error("เกิดข้อผิดพลาดในการค้นหา")
        st.exception(e)
