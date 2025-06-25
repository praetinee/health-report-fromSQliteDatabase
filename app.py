import streamlit as st
import sqlite3
import pandas as pd
import requests
import os

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.title("🩺 ระบบรายงานผลตรวจสุขภาพ (โหลดจาก Google Drive)")

# ===== ดาวน์โหลดไฟล์ SQLite จาก Google Drive =====
@st.cache_resource
def download_db_from_drive():
    file_id = "1A1LM3f07oJ-8rsnGpBRkNsJFlhjMd89E"
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    output_path = "temp_db.db"

    if not os.path.exists(output_path):
        response = requests.get(url)
        with open(output_path, "wb") as f:
            f.write(response.content)

    return output_path

DB_PATH = download_db_from_drive()

# ===== แสดงตัวอย่างข้อมูล =====
@st.cache_data(ttl=300)
def get_preview():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM health_data LIMIT 5", conn)
    conn.close()
    return df

st.subheader("🔍 ตัวอย่างข้อมูลจากฐานข้อมูล")
try:
    preview = get_preview()
    st.dataframe(preview)
except Exception as e:
    st.error("ไม่สามารถโหลดข้อมูลตัวอย่างได้")
    st.exception(e)

# ===== ค้นหาผลตรวจด้วย HN / ชื่อ-สกุล / เลขบัตร =====
st.subheader("ค้นหาข้อมูลสุขภาพ")
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
            st.warning("ไม่พบข้อมูล")
        else:
            st.success(f"พบข้อมูล {len(df)} รายการ")
            st.dataframe(df)

            # ===== สรุปผลตรวจเบื้องต้น =====
            st.subheader("📋 ข้อมูลสุขภาพเบื้องต้น")
            basic_cols = ["วันที่ตรวจ", "ชื่อ-สกุล", "เพศ", "อายุ", "น้ำหนัก", "ส่วนสูง", "รอบเอว", "BMI", "SBP", "DBP", "pulse"]
            available_cols = [col for col in basic_cols if col in df.columns]
            if "วันที่ตรวจ" in available_cols:
                st.table(df[available_cols].set_index("วันที่ตรวจ"))
            else:
                st.table(df[available_cols])
    except Exception as e:
        st.error("เกิดข้อผิดพลาดในการดึงข้อมูล")
        st.exception(e)
