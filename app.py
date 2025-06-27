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

# ==================== YEAR MAPPING (Dynamic & Flexible) ====================
years = sorted(df["Year"].dropna().unique())

columns_by_year = {
    y: {
        "weight": "น้ำหนัก",
        "height": "ส่วนสูง",
        "waist": "รอบเอว",
        "sbp": "SBP",
        "dbp": "DBP",
        "pulse": "pulse",
    }
    for y in years
}

# ==================== SEARCH AND DISPLAY ====================
if submitted:
    filtered = df.copy()
    if id_card:
        filtered = filtered[filtered['เลขบัตรประชาชน'].astype(str).str.strip() == id_card.strip()]
    if hn:
        filtered = filtered[filtered['HN'].astype(str).str.strip() == hn.strip()]
    if full_name:
        filtered = filtered[filtered['ชื่อ-สกุล'].astype(str).str.strip() == full_name.strip()]

    if filtered.empty:
        st.warning("ไม่พบข้อมูลผู้ใช้ตามที่ค้นหา")
    else:
        all_years = sorted(df["Year"].dropna().unique())
        selected_year = st.selectbox("เลือกปี พ.ศ.", all_years[::-1])  # แสดงปีใหม่ก่อน

        person_records = filtered[filtered["Year"] == selected_year]

        if person_records.empty:
            st.warning(f"ไม่พบข้อมูลการตรวจในปี {selected_year} สำหรับบุคคลนี้")
        else:
            # จัดเรียงลำดับตามวันที่ตรวจ (หากมี)
            if "วันที่ตรวจ" in person_records.columns:
                try:
                    person_records["วันที่ตรวจ"] = pd.to_datetime(person_records["วันที่ตรวจ"], errors="coerce")
                    person_records = person_records.sort_values("วันที่ตรวจ")
                except:
                    st.warning("⚠️ ไม่สามารถจัดเรียงตามวันที่ตรวจได้ — จะเรียงตามลำดับข้อมูลเดิมแทน")
            else:
                st.info("ℹ️ ไม่มีคอลัมน์วันที่ตรวจ — จะแสดงลำดับตามข้อมูล")

            num_visits = len(person_records)

            if num_visits == 1:
                row = person_records.iloc[0]
                st.info(f"พบการตรวจ 1 ครั้งในปี {selected_year}")
                st.write(row)
            else:
                st.success(f"พบการตรวจ {num_visits} ครั้งในปี {selected_year}")
                for idx, (_, row) in enumerate(person_records.iterrows(), start=1):
                    with st.expander(f"ครั้งที่ {idx}"):
                        weight = row.get("น้ำหนัก")
                        height = row.get("ส่วนสูง")
                        waist = row.get("รอบเอว")
                        sbp = row.get("SBP")
                        dbp = row.get("DBP")
                        pulse = row.get("pulse")

                        bmi = None
                        if height and weight:
                            try:
                                h_m = float(height) / 100
                                bmi = round(float(weight) / (h_m ** 2), 2)
                            except:
                                bmi = None

                        st.markdown(f"**BMI:** {bmi if bmi else '-'}  ({interpret_bmi(bmi)})")
                        st.markdown(f"**BP:** {sbp}/{dbp}  ({interpret_bp(sbp, dbp)})")
                        st.markdown(f"**คำแนะนำ:** {combined_health_advice(bmi, sbp, dbp)}")
                        st.divider()
