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

# ==================== FUNCTION: Normalize HN ====================
def normalize_hn(val):
    if val is None:
        return ""
    try:
        s = str(val).strip()
        if s.lower() in ["", "nan", "none", "-"]:
            return ""
        return str(int(float(s)))
    except:
        return ""

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

df.columns = df.columns.str.strip()

if "HN" in df.columns:
    df["HN"] = df["HN"].apply(normalize_hn)

# ==================== YEAR MAPPING ====================
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

# ==================== SEARCH FORM ====================
with st.form("search_form"):
    col1, col2, col3 = st.columns(3)
    id_card = col1.text_input("เลขบัตรประชาชน")
    hn = col2.text_input("HN")
    full_name = col3.text_input("ชื่อ-สกุล")
    submitted = st.form_submit_button("ค้นหา")

# ==================== SEARCH & DISPLAY ====================
if submitted:
    filtered = df.copy()

    if id_card:
        filtered = filtered[filtered['เลขบัตรประชาชน'].astype(str).str.strip() == id_card.strip()]
    if hn:
        hn = normalize_hn(hn)
        filtered = filtered[filtered["HN"] == hn]
    if full_name:
        filtered = filtered[filtered['ชื่อ-สกุล'].astype(str).str.strip() == full_name.strip()]

    if filtered.empty:
        st.warning("ไม่พบข้อมูลผู้ใช้ตามที่ค้นหา")
        st.session_state["filtered_data"] = None
    else:
        st.session_state["filtered_data"] = filtered

if "filtered_data" in st.session_state and st.session_state["filtered_data"] is not None:
    filtered = st.session_state["filtered_data"]

    years = sorted(filtered["Year"].dropna().unique())[::-1]
    selected_year = st.selectbox("เลือกปี พ.ศ.", years)

    person_records = filtered[filtered["Year"] == selected_year]

    if person_records.empty:
        st.warning(f"ไม่พบข้อมูลการตรวจในปี {selected_year} สำหรับบุคคลนี้")
    else:
        if "วันที่ตรวจ" in person_records.columns:
            try:
                person_records["วันที่ตรวจ"] = pd.to_datetime(person_records["วันที่ตรวจ"], errors="coerce")
                person_records = person_records.sort_values("วันที่ตรวจ")
            except:
                st.warning("⚠️ ไม่สามารถจัดเรียงตามวันที่ตรวจได้")
        else:
            st.info("ℹ️ ไม่มีคอลัมน์วันที่ตรวจ")

        def interpret_bmi(bmi):
            try:
                bmi = float(bmi)
                if bmi > 30:
                    return "อ้วนมาก"
                elif bmi >= 25:
                    return "อ้วน"
                elif bmi >= 23:
                    return "น้ำหนักเกิน"
                elif bmi >= 18.5:
                    return "ปกติ"
                else:
                    return "ผอม"
            except:
                return "-"

        def interpret_bp(sbp, dbp):
            try:
                sbp = float(sbp)
                dbp = float(dbp)
                if sbp == 0 or dbp == 0:
                    return "-"
                if sbp >= 160 or dbp >= 100:
                    return "ความดันสูง"
                elif sbp >= 140 or dbp >= 90:
                    return "ความดันสูงเล็กน้อย"
                elif sbp < 120 and dbp < 80:
                    return "ความดันปกติ"
                else:
                    return "ความดันค่อนข้างสูง"
            except:
                return "-"

        def combined_health_advice(bmi, sbp, dbp):
            try:
                bmi = float(bmi)
            except:
                bmi = None
            try:
                sbp = float(sbp)
                dbp = float(dbp)
            except:
                sbp = dbp = None

            if bmi is None:
                bmi_text = ""
            elif bmi > 30:
                bmi_text = "น้ำหนักเกินมาตรฐานมาก"
            elif bmi >= 25:
                bmi_text = "น้ำหนักเกินมาตรฐาน"
            elif bmi < 18.5:
                bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
            else:
                bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"

            if sbp is None or dbp is None:
                bp_text = ""
            elif sbp >= 160 or dbp >= 100:
                bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
            elif sbp >= 140 or dbp >= 90:
                bp_text = "ความดันโลหิตอยู่ในระดับสูง"
            elif sbp >= 120 or dbp >= 80:
                bp_text = "ความดันโลหิตเริ่มสูง"
            else:
                bp_text = ""

            if not bmi_text and not bp_text:
                return "ไม่พบข้อมูลเพียงพอในการประเมินสุขภาพ"

            if "ปกติ" in bmi_text and not bp_text:
                return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"

            if not bmi_text and bp_text:
                return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"

            if bmi_text and bp_text:
                return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"

            return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"

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
                    sbp = row.get("SBP")
                    dbp = row.get("DBP")

                    bmi = None
                    if height and weight:
                        try:
                            h_m = float(height) / 100
                            bmi = round(float(weight) / (h_m ** 2), 2)
                        except:
                            bmi = None

                    st.markdown(f"**BMI:** {bmi if bmi else '-'} ({interpret_bmi(bmi)})")
                    st.markdown(f"**BP:** {sbp}/{dbp} ({interpret_bp(sbp, dbp)})")
                    st.markdown(f"**คำแนะนำ:** {combined_health_advice(bmi, sbp, dbp)}")
                    st.divider()
