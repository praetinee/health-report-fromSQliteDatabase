import streamlit as st
import pandas as pd
import sqlite3
import requests
import os

from utils import parse_date_thai  # ✅ ฟังก์ชันแปลงวันที่จาก utils.py

@st.cache_data(ttl=900)
def load_sqlite_data():
    db_path = "health_data.sqlite"
    file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
    gdrive_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    # ✅ ถ้าไฟล์ยังไม่มี ให้โหลดจาก Google Drive
    if not os.path.exists(db_path):
        with st.spinner("🔄 กำลังดาวน์โหลดฐานข้อมูลจาก Google Drive..."):
            with requests.get(gdrive_url, stream=True) as r:
                if r.status_code != 200:
                    st.error("❌ ไม่สามารถโหลดไฟล์จาก Google Drive ได้")
                    return pd.DataFrame()
                with open(db_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

    # ✅ อ่านข้อมูลจาก SQLite
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM health_data", conn)
    conn.close()

    # ✅ แปลงคอลัมน์ "วันที่ตรวจ" ให้เป็น datetime (จาก utils)
    df["วันที่ตรวจ"] = df["วันที่ตรวจ"].apply(parse_date_thai)

    # ✅ เติมค่า missing ให้เรียบร้อย
    df = df.fillna("").replace("nan", "")
    return df
