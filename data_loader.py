import streamlit as st
import pandas as pd
import sqlite3
import os

@st.cache_data(ttl=600)
def load_sqlite_data():
    # กำหนดชื่อไฟล์ที่โหลดจาก Google Drive
    db_filename = "health_data.sqlite"

    # ตรวจสอบว่าผู้ใช้แนบไฟล์หรือยัง
    uploaded_file = st.file_uploader("📥 อัปโหลดไฟล์ฐานข้อมูล SQLite", type="sqlite")
    if uploaded_file is not None:
        with open(db_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())

    if not os.path.exists(db_filename):
        st.warning("⚠️ กรุณาอัปโหลดไฟล์ฐานข้อมูลก่อน")
        return pd.DataFrame()

    # เชื่อมต่อฐานข้อมูล
    conn = sqlite3.connect(db_filename)
    df = pd.read_sql("SELECT * FROM health_data", conn)
    conn.close()

    # แปลงวันที่ + ล้างข้อมูล
    df["วันที่ตรวจ"] = pd.to_datetime(df["วันที่ตรวจ"], errors="coerce", dayfirst=True)
    df = df.fillna("").replace("nan", "")

    return df
