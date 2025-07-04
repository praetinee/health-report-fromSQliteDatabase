import streamlit as st
import pandas as pd
import sqlite3
import requests
import os

@st.cache_data(ttl=900)
def load_sqlite_data():
    db_path = "health_data.sqlite"
    file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
    gdrive_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    if not os.path.exists(db_path):
        with st.spinner("🔄 กำลังดาวน์โหลดฐานข้อมูลจาก Google Drive..."):
            with requests.get(gdrive_url, stream=True) as r:
                if r.status_code != 200:
                    st.error("❌ ไม่สามารถโหลดไฟล์จาก Google Drive ได้")
                    return pd.DataFrame()
                with open(db_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM health_data", conn)
    conn.close()

    # === ฟังก์ชันแปลงวันที่แบบไทย ===
    def parse_thai_date(text):
        try:
            if pd.isna(text) or str(text).strip() == "":
                return pd.NaT

            text = str(text).replace(".", "").strip()

            # กรณีเช่น 13 มกราคม 2564
            if " " in text and any(thai_month in text for thai_month in ["มกราคม", "กุมภาพันธ์", "มีนาคม"]):
                thai_months = {
                    "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03", "เมษายน": "04",
                    "พฤษภาคม": "05", "มิถุนายน": "06", "กรกฎาคม": "07", "สิงหาคม": "08",
                    "กันยายน": "09", "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12"
                }
                parts = text.split()
                if len(parts) == 3:
                    day, month_th, year_th = parts
                    month = thai_months.get(month_th, "01")
                    year = int(year_th) - 543
                    return pd.to_datetime(f"{year}-{month}-{int(day):02}", errors="coerce")

            # กรณี 06/07/2565
            if "/" in text:
                day, month, year = text.split("/")
                year = int(year)
                if year > 2400:
                    year -= 543
                return pd.to_datetime(f"{year}-{int(month):02}-{int(day):02}", errors="coerce")

        except:
            return pd.NaT

        return pd.NaT

    # === ใช้งานฟังก์ชันแปลงวันที่ ===
    df["วันที่ตรวจ"] = df["วันที่ตรวจ"].apply(parse_thai_date)

    df = df.fillna("").replace("nan", "")
    return df
