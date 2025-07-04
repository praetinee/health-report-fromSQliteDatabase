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

    # ✅ แปลงวันที่จากหลายรูปแบบให้กลายเป็น datetime
    def parse_thai_date(text):
        if pd.isna(text) or not isinstance(text, str):
            return pd.NaT

        text = text.strip()
        try:
            # กรณี dd/mm/yyyy
            if "/" in text and text.count("/") == 2:
                d, m, y = text.split("/")
                y = str(int(y) - 543) if int(y) > 2400 else y
                return pd.to_datetime(f"{d}/{m}/{y}", format="%d/%m/%Y", errors="coerce")

            # กรณี dd. เดือน พ.ศ.
            if "." in text and " " in text:
                d_part, m_part, y_part = text.replace(".", "").split(" ")
                y_part = str(int(y_part) - 543) if int(y_part) > 2400 else y_part
                return pd.to_datetime(f"{d_part} {m_part} {y_part}", format="%d %B %Y", errors="coerce")

            # กรณี dd เดือน พ.ศ.
            if " " in text:
                d_part, m_part, y_part = text.split(" ")
                y_part = str(int(y_part) - 543) if int(y_part) > 2400 else y_part
                return pd.to_datetime(f"{d_part} {m_part} {y_part}", format="%d %B %Y", errors="coerce")
        except:
            return pd.NaT

        return pd.NaT

    df["วันที่ตรวจ"] = df["วันที่ตรวจ"].apply(parse_thai_date)

    df = df.fillna("").replace("nan", "")
    return df
