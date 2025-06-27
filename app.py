import streamlit as st
import pandas as pd
import sqlite3
import requests

# ==================== FUNCTION: Check Missing Values ====================
def is_missing(value):
    if pd.isna(value):
        return True
    value = str(value).strip().lower()
    return value in {"", "-", "nan", "none", "null"}

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

# ==================== INITIAL LOAD ====================
with st.spinner("กำลังโหลดข้อมูล..."):
    df = load_database()

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

# ==================== SEARCH & SESSION STATE ====================
if submitted:
    filtered = df.copy()

    if id_card:
        filtered = filtered[filtered["เลขบัตรประชาชน"].astype(str).str.strip() == id_card.strip()]
    if hn:
        hn = normalize_hn(hn)
        filtered = filtered[filtered["HN"] == hn]
    if full_name:
        filtered = filtered[filtered["ชื่อ-สกุล"].astype(str).str.strip() == full_name.strip()]

    if filtered.empty:
        st.warning("ไม่พบข้อมูลผู้ใช้ตามที่ค้นหา")
        st.session_state["filtered_data"] = None
    else:
        st.session_state["filtered_data"] = filtered

# ==================== FUNCTION: DISPLAY HEALTH REPORT ====================
def render_health_report(person, selected_year):
    def get_val(key):
        val = person.get(key)
        return "-" if is_missing(val) else str(val).strip()

    sbp = get_val("SBP")
    dbp = get_val("DBP")
    pulse = get_val("pulse")
    weight = get_val("น้ำหนัก")
    height = get_val("ส่วนสูง")
    waist = get_val("รอบเอว")

    bp_result = "-"
    if not is_missing(sbp) and not is_missing(dbp):
        bp_val = f"{sbp}/{dbp} ม.ม.ปรอท"
        bp_desc = interpret_bp(sbp, dbp)
        bp_result = f"{bp_val} - {bp_desc}"

    pulse_display = f"{pulse} ครั้ง/นาที" if not is_missing(pulse) else "-"
    weight_display = f"{weight} กก." if not is_missing(weight) else "-"
    height_display = f"{height} ซม." if not is_missing(height) else "-"
    waist_display = f"{waist} ซม." if not is_missing(waist) else "-"

    try:
        weight_val = float(weight)
        height_val = float(height)
        bmi_val = weight_val / ((height_val / 100) ** 2)
    except:
        bmi_val = None

    summary_advice = combined_health_advice(bmi_val, sbp, dbp)
    bmi_text = f"{round(bmi_val, 2)} ({interpret_bmi(bmi_val)})" if bmi_val else "-"

    return f"""
    <div style="font-size: 18px; line-height: 1.8; color: inherit; padding: 24px 8px;">
        <div style="text-align: center; font-size: 22px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
        <div style="text-align: center;">วันที่ตรวจ: {get_val('วันที่ตรวจ')}</div>
        <div style="text-align: center; margin-top: 10px;">
            โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว<br>
            ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290 โทร 053 921 199 ต่อ 167
        </div>
        <hr style="margin: 24px 0;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {get_val('ชื่อ-สกุล')}</div>
            <div><b>อายุ:</b> {get_val('อายุ')} ปี</div>
            <div><b>เพศ:</b> {get_val('เพศ')}</div>
            <div><b>HN:</b> {get_val('HN')}</div>
            <div><b>หน่วยงาน:</b> {get_val('หน่วยงาน')}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {weight_display}</div>
            <div><b>ส่วนสูง:</b> {height_display}</div>
            <div><b>รอบเอว:</b> {waist_display}</div>
            <div><b>ความดันโลหิต:</b> {bp_result}</div>
            <div><b>ชีพจร:</b> {pulse_display}</div>
            <div><b>BMI:</b> {bmi_text}</div>
        </div>
        <div style="margin-top: 16px; text-align: center;">
            <b>คำแนะนำ:</b> {summary_advice}
        </div>
    </div>
    """

# ==================== INTERPRETATION HELPERS ====================
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
    if is_missing(sbp) or is_missing(dbp):
        return "-"
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
    bmi_text = ""
    bp_text = ""

    if not is_missing(bmi):
        try:
            bmi = float(bmi)
            if bmi > 30:
                bmi_text = "น้ำหนักเกินมาตรฐานมาก"
            elif bmi >= 25:
                bmi_text = "น้ำหนักเกินมาตรฐาน"
            elif bmi < 18.5:
                bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
            else:
                bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
        except:
            bmi_text = ""

    if not is_missing(sbp) and not is_missing(dbp):
        try:
            sbp = float(sbp)
            dbp = float(dbp)
            if sbp >= 160 or dbp >= 100:
                bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
            elif sbp >= 140 or dbp >= 90:
                bp_text = "ความดันโลหิตอยู่ในระดับสูง"
            elif sbp >= 120 or dbp >= 80:
                bp_text = "ความดันโลหิตเริ่มสูง"
        except:
            pass

    if not bmi_text and not bp_text:
        return "ไม่พบข้อมูลเพียงพอในการประเมินสุขภาพ"
    if "ปกติ" in bmi_text and not bp_text:
        return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
    if not bmi_text and bp_text:
        return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    if bmi_text and bp_text:
        return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"

# ==================== BLOOD COLUMN MAPPING (Dynamic) ====================
blood_columns_by_year = {
    y: {
        "FBS": "FBS",
        "Uric": "Uric Acid",
        "ALK": "ALP",
        "SGOT": "SGOT",
        "SGPT": "SGPT",
        "Cholesterol": "CHOL",
        "TG": "TGL",
        "HDL": "HDL",
        "LDL": "LDL",
        "BUN": "BUN",
        "Cr": "Cr",
        "GFR": "GFR",
    }
    for y in df["Year"].dropna().unique()
}

# ==================== CBC COLUMN MAPPING (Dynamic) ====================
from collections import defaultdict

cbc_columns_by_year = defaultdict(dict)
for y in df["Year"].dropna().unique():
    cbc_columns_by_year[y] = {
        "hb": "Hb(%)",
        "hct": "HCT",
        "wbc": "WBC (cumm)",
        "plt": "Plt (/mm)",
    }
    if y == 2568:
        cbc_columns_by_year[y].update({
            "ne": "Ne (%)",
            "ly": "Ly (%)",
            "eo": "Eo",
            "mo": "M",
            "ba": "BA",
            "rbc": "RBCmo",
            "mcv": "MCV",
            "mch": "MCH",
            "mchc": "MCHC",
        })

# ==================== GET PERSON FROM SESSION ====================
if "person" in st.session_state:
    filtered = st.session_state.get("filtered_data")
    selected_year = st.session_state.get("selected_year")

    if filtered is not None and selected_year:
        person_records = filtered[filtered["Year"] == selected_year]
        if not person_records.empty:
            person = person_records.iloc[0]
        else:
            st.warning("ไม่พบข้อมูลผู้ใช้ในปีที่เลือก")
            st.stop()
    else:
        st.warning("ไม่พบข้อมูลที่กรองหรือปีที่เลือก")
        st.stop()

# ==================== CBC / BLOOD TEST DISPLAY ====================

cbc_cols = cbc_columns_by_year.get(selected_year, {})
blood_cols = blood_columns_by_year.get(selected_year, {})

def flag_value(raw, low=None, high=None, higher_is_better=False):
    try:
        val = float(str(raw).replace(",", "").strip())
        if higher_is_better:
            return f"{val:.1f}", val < low if low is not None else False
        if (low is not None and val < low) or (high is not None and val > high):
            return f"{val:.1f}", True
        return f"{val:.1f}", False
    except:
        return "-", False

sex = person.get("เพศ", "").strip()
hb_low = 12 if sex == "หญิง" else 13
hct_low = 36 if sex == "หญิง" else 39

cbc_config = [
    ("ฮีโมโกลบิน (Hb)", cbc_cols.get("hb"), "ชาย > 13, หญิง > 12 g/dl", hb_low, None),
    ("ฮีมาโทคริต (Hct)", cbc_cols.get("hct"), "ชาย > 39%, หญิง > 36%", hct_low, None),
    ("เม็ดเลือดขาว (wbc)", cbc_cols.get("wbc"), "4,000 - 10,000 /cu.mm", 4000, 10000),
    ("นิวโทรฟิล (Neutrophil)", cbc_cols.get("ne"), "43 - 70%", 43, 70),
    ("ลิมโฟไซต์ (Lymphocyte)", cbc_cols.get("ly"), "20 - 44%", 20, 44),
    ("โมโนไซต์ (Monocyte)", cbc_cols.get("mo"), "3 - 9%", 3, 9),
    ("อีโอซิโนฟิล (Eosinophil)", cbc_cols.get("eo"), "0 - 9%", 0, 9),
    ("เบโซฟิล (Basophil)", cbc_cols.get("ba"), "0 - 3%", 0, 3),
    ("เกล็ดเลือด (Platelet)", cbc_cols.get("plt"), "150,000 - 500,000 /cu.mm", 150000, 500000),
]

cbc_rows = []
for name, col, normal, low, high in cbc_config:
    raw = person.get(col, "-")
    result, is_abnormal = flag_value(raw, low, high)
    cbc_rows.append([(name, is_abnormal), (result, is_abnormal), (normal, is_abnormal)])

blood_config = [
    ("น้ำตาลในเลือด (FBS)", blood_cols.get("FBS"), "74 - 106 mg/dl", 74, 106),
    ("กรดยูริคสาเหตุโรคเก๊าท์ (Uric acid)", blood_cols.get("Uric"), "2.6 - 7.2 mg%", 2.6, 7.2),
    ("การทำงานของเอนไซม์ตับ ALK.POS", blood_cols.get("ALK"), "30 - 120 U/L", 30, 120),
    ("การทำงานของเอนไซม์ตับ SGOT", blood_cols.get("SGOT"), "< 37 U/L", None, 37),
    ("การทำงานของเอนไซม์ตับ SGPT", blood_cols.get("SGPT"), "< 41 U/L", None, 41),
    ("คลอเรสเตอรอล (Cholesterol)", blood_cols.get("Cholesterol"), "150 - 200 mg/dl", 150, 200),
    ("ไตรกลีเซอไรด์ (Triglyceride)", blood_cols.get("TG"), "35 - 150 mg/dl", 35, 150),
    ("ไขมันดี (HDL)", blood_cols.get("HDL"), "> 40 mg/dl", 40, None, True),
    ("ไขมันเลว (LDL)", blood_cols.get("LDL"), "0 - 160 mg/dl", 0, 160),
    ("การทำงานของไต (BUN)", blood_cols.get("BUN"), "7.9 - 20 mg/dl", 7.9, 20),
    ("การทำงานของไต (Cr)", blood_cols.get("Cr"), "0.5 - 1.17 mg/dl", 0.5, 1.17),
    ("ประสิทธิภาพการกรองของไต (GFR)", blood_cols.get("GFR"), "> 60 mL/min", 60, None, True),
]

blood_rows = []
for name, col, normal, low, high, *opt in blood_config:
    higher_is_better = opt[0] if opt else False
    raw = person.get(col, "-")
    result, is_abnormal = flag_value(raw, low, high, higher_is_better=higher_is_better)
    blood_rows.append([(name, is_abnormal), (result, is_abnormal), (normal, is_abnormal)])
