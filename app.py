import streamlit as st
import pandas as pd
import sqlite3
import requests

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# ==================== FONT ====================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch&display=swap');
    html, body, [class*="css"] {
        font-family: 'Chakra Petch', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== STYLE ====================
st.markdown("""
<style>
    .doctor-section {
        font-size: 16px;
        line-height: 1.8;
        margin-top: 2rem;
    }

    .summary-box {
        background-color: #dcedc8;
        padding: 12px 18px;
        font-weight: bold;
        border-radius: 6px;
        margin-bottom: 1.5rem;
    }

    .appointment-box {
        background-color: #ffcdd2;
        padding: 12px 18px;
        border-radius: 6px;
        margin-bottom: 1.5rem;
    }

    .remark {
        font-weight: bold;
        margin-top: 2rem;
    }

    .footer {
        display: flex;
        justify-content: space-between;
        margin-top: 3rem;
        font-size: 16px;
    }

    .footer .right {
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# ==================== LOAD DATABASE FROM GOOGLE DRIVE ====================
@st.cache_data
def load_database():
    file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    output_path = "health_data.db"

    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
    else:
        st.error("ไม่สามารถโหลดไฟล์ฐานข้อมูลจาก Google Drive ได้")
        st.stop()

    conn = sqlite3.connect(output_path)
    df = pd.read_sql_query("SELECT * FROM health_data", conn)
    conn.close()
    return df

# ==================== MAIN ====================
st.title("📊 ระบบรายงานสุขภาพ")

with st.spinner("กำลังโหลดข้อมูล..."):
    df = load_database()

st.success("โหลดข้อมูลเรียบร้อยแล้ว!")

st.dataframe(df, use_container_width=True)

# ==================== CLEAN & TRANSFORM DATA ====================
df.columns = df.columns.str.strip()

# ตรวจสอบว่าคอลัมน์มีอยู่ก่อนแปลงชนิดข้อมูล
expected_columns = ['เลขบัตรประชาชน', 'HN', 'ชื่อ-สกุล']
for col in expected_columns:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    else:
        st.warning(f"⚠️ ไม่พบคอลัมน์ '{col}' ในฐานข้อมูล SQLite")

# แสดงตาราง
st.dataframe(df, use_container_width=True)

