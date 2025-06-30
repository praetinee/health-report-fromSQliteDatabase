import sqlite3
import requests
import pandas as pd
from io import BytesIO

@st.cache_data(ttl=600)
def load_sqlite_from_drive():
    try:
        # ดาวน์โหลด SQLite DB จาก Google Drive แบบตรง (ใช้ file ID)
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?id={file_id}"

        response = requests.get(download_url)
        response.raise_for_status()

        # โหลดเป็น SQLite จาก BytesIO
        with open("/tmp/health_data.db", "wb") as f:
            f.write(response.content)

        conn = sqlite3.connect("/tmp/health_data.db")
        df = pd.read_sql_query("SELECT * FROM health_data", conn)

        df.columns = df.columns.str.strip()
        df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
        df['HN'] = df['HN'].astype(str).str.strip()
        df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()

        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลจาก Google Drive: {e}")
        st.stop()

df = load_sqlite_from_drive()
