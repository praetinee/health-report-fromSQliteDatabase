import numpy as np
import streamlit as st
import pandas as pd
import json
import html

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

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


# ==================== STYLE ====================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch&display=swap');
    html, body, [class*="css"] {
        font-family: 'Chakra Petch', sans-serif !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== LOAD SHEET ====================
import sqlite3
import requests

@st.cache_data(ttl=600)
def load_data_from_db():
    db_url = "https://drive.google.com/uc?export=download&id=1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
    db_path = "/tmp/temp_data.db"

    # ดาวน์โหลดไฟล์จาก Google Drive
    with requests.get(db_url, stream=True) as r:
        with open(db_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # อ่านข้อมูลจาก SQLite
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM health_data", conn)  # 🔁 เปลี่ยนชื่อ table ตรงนี้
    conn.close()

    return df

df = load_data_from_db()
df.columns = df.columns.str.strip()
df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
df['HN'] = df['HN'].astype(str).str.strip()
df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()

# ==================== YEAR MAPPING ====================
years = list(range(61, 69))
columns_by_year = {
    y: {
        "weight": f"น้ำหนัก{y}" if y != 68 else "น้ำหนัก",
        "height": f"ส่วนสูง{y}" if y != 68 else "ส่วนสูง",
        "waist": f"รอบเอว{y}" if y != 68 else "รอบเอว",
        "sbp": f"SBP{y}" if y != 68 else "SBP",
        "dbp": f"DBP{y}" if y != 68 else "DBP",
        "pulse": f"pulse{y}" if y != 68 else "pulse",
    }
    for y in years
}

# ==================== INTERPRET FUNCTIONS ====================
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
    except (ValueError, TypeError):
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
    except (ValueError, TypeError):
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

    # วิเคราะห์ BMI
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

    # วิเคราะห์ความดัน
    if sbp is None or dbp is None:
        bp_text = ""
    elif sbp >= 160 or dbp >= 100:
        bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
    elif sbp >= 140 or dbp >= 90:
        bp_text = "ความดันโลหิตอยู่ในระดับสูง"
    elif sbp >= 120 or dbp >= 80:
        bp_text = "ความดันโลหิตเริ่มสูง"
    else:
        bp_text = ""  # ❗ ถ้าปกติ = ไม่ต้องพูดถึง

    # สร้างคำแนะนำรวม
    if not bmi_text and not bp_text:
        return "ไม่พบข้อมูลเพียงพอในการประเมินสุขภาพ"

    if "ปกติ" in bmi_text and not bp_text:
        return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"

    if not bmi_text and bp_text:
        return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"

    if bmi_text and bp_text:
        return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"

    return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"

# ==================== UI FORM ====================
st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2, col3 = st.columns(3)
    id_card = col1.text_input("เลขบัตรประชาชน")
    hn = col2.text_input("HN")
    full_name = col3.text_input("ชื่อ-สกุล")
    submitted = st.form_submit_button("ค้นหา")

# ==================== BLOOD COLUMN MAPPING ====================
blood_columns_by_year = {
    y: {
        "FBS": f"FBS{y}",
        "Uric": f"Uric Acid{y}",
        "ALK": f"ALP{y}",
        "SGOT": f"SGOT{y}",
        "SGPT": f"SGPT{y}",
        "Cholesterol": f"CHOL{y}",
        "TG": f"TGL{y}",
        "HDL": f"HDL{y}",
        "LDL": f"LDL{y}",
        "BUN": f"BUN{y}",
        "Cr": f"Cr{y}",
        "GFR": f"GFR{y}",
    }
    for y in years
}

if submitted:
    query = df.copy()
    if id_card.strip():
        query = query[query["เลขบัตรประชาชน"] == id_card.strip()]
    if hn.strip():
        query = query[query["HN"] == hn.strip()]
    if full_name.strip():
        query = query[query["ชื่อ-สกุล"].str.strip() == full_name.strip()]
    if query.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        st.session_state.pop("person", None)
    else:
        st.session_state["person"] = query.iloc[0]

from collections import defaultdict

cbc_columns_by_year = defaultdict(dict)

for year in range(61, 69):
    cbc_columns_by_year[year] = {
        "hb": f"Hb(%)" + str(year),
        "hct": f"HCT" + str(year),
        "wbc": f"WBC (cumm)" + str(year),
        "plt": f"Plt (/mm)" + str(year),
    }

    if year == 68:
        cbc_columns_by_year[year].update({
            "ne": "Ne (%)68",
            "ly": "Ly (%)68",
            "eo": "Eo68",
            "mo": "M68",
            "ba": "BA68",
            "rbc": "RBCmo68",
            "mcv": "MCV68",
            "mch": "MCH68",
            "mchc": "MCHC",
        })

def interpret_alb(value):
    value = str(value).strip().lower()
    if value == "negative":
        return "ไม่พบ"
    elif value in ["trace", "1+", "2+"]:
        return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif value == "3+":
        return "พบโปรตีนในปัสสาวะ"
    return "-"

def interpret_sugar(value):
    value = str(value).strip().lower()
    if value == "negative":
        return "ไม่พบ"
    elif value == "trace":
        return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif value in ["1+", "2+", "3+", "4+", "5+", "6+"]:
        return "พบน้ำตาลในปัสสาวะ"
    return "-"

def interpret_rbc(value):
    value = str(value).strip().lower()
    if value in ["0-1", "negative", "1-2", "2-3", "3-5"]:
        return "ปกติ"
    elif value in ["5-10", "10-20"]:
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    value = str(value).strip().lower()
    if value in ["0-1", "negative", "1-2", "2-3", "3-5"]:
        return "ปกติ"
    elif value in ["5-10", "10-20"]:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def advice_urine(sex, alb, sugar, rbc, wbc):
    alb_text = interpret_alb(alb)
    sugar_text = interpret_sugar(sugar)
    rbc_text = interpret_rbc(rbc)
    wbc_text = interpret_wbc(wbc)

    if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"]
           for x in [alb_text, sugar_text, rbc_text, wbc_text]):
        return ""

    if "พบน้ำตาลในปัสสาวะ" in sugar_text and "เล็กน้อย" not in sugar_text:
        return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"

    if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_text and "ปกติ" in wbc_text:
        return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"

    if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_text and "ปกติ" in wbc_text:
        return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"

    if "พบเม็ดเลือดขาวในปัสสาวะ" in wbc_text and "เล็กน้อย" not in wbc_text:
        return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"

    return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"

def interpret_stool_exam(value):
    if not value or value.strip() == "":
        return "-"
    if "ปกติ" in value:
        return "ปกติ"
    elif "เม็ดเลือดแดง" in value:
        return "พบเม็ดเลือดแดงในอุจจาระ นัดตรวจซ้ำ"
    elif "เม็ดเลือดขาว" in value:
        return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return value.strip()

def interpret_stool_cs(value):
    if not value or value.strip() == "":
        return "-"
    if "ไม่พบ" in value or "ปกติ" in value:
        return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

# ==================== DISPLAY ====================
if "person" in st.session_state:
    person = st.session_state["person"]

    selected_year = st.selectbox(
        "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน", 
        options=sorted(years, reverse=True),
        format_func=lambda y: f"พ.ศ. {y + 2500}"
    )


    selected_cols = columns_by_year[selected_year]

    def render_health_report(person, year_cols):
        sbp = person.get(year_cols["sbp"], "")
        dbp = person.get(year_cols["dbp"], "")
        pulse = person.get(year_cols["pulse"], "-")
        weight = person.get(year_cols["weight"], "-")
        height = person.get(year_cols["height"], "-")
        waist = person.get(year_cols["waist"], "-")
    
        bp_result = "-"
        if sbp and dbp:
            bp_val = f"{sbp}/{dbp} ม.ม.ปรอท"
            bp_desc = interpret_bp(sbp, dbp)
            bp_result = f"{bp_val} - {bp_desc}"
    
        pulse = f"{pulse} ครั้ง/นาที" if pulse != "-" else "-"
        weight = f"{weight} กก." if weight else "-"
        height = f"{height} ซม." if height else "-"
        waist = f"{waist} ซม." if waist else "-"
    
        try:
            weight_val = float(weight.replace(" กก.", "").strip())
            height_val = float(height.replace(" ซม.", "").strip())
            bmi_val = weight_val / ((height_val / 100) ** 2)
        except Exception as e:
            st.warning(f"❌ ไม่สามารถคำนวณ BMI ได้: {e}")
            bmi_val = None
    
        summary_advice = html.escape(combined_health_advice(bmi_val, sbp, dbp))
    
        return f"""
        <div style="font-size: 18px; line-height: 1.8; color: inherit; padding: 24px 8px;">
            <div style="text-align: center; font-size: 22px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
            <div style="text-align: center;">วันที่ตรวจ: {person.get('วันที่ตรวจ', '-')}</div>
            <div style="text-align: center; margin-top: 10px;">
                โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว<br>
                ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290 โทร 053 921 199 ต่อ 167
            </div>
            <hr style="margin: 24px 0;">
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
                <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
                <div><b>อายุ:</b> {person.get('อายุ', '-')} ปี</div>
                <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
                <div><b>HN:</b> {person.get('HN', '-')}</div>
                <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
            </div>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
                <div><b>น้ำหนัก:</b> {weight}</div>
                <div><b>ส่วนสูง:</b> {height}</div>
                <div><b>รอบเอว:</b> {waist}</div>
                <div><b>ความดันโลหิต:</b> {bp_result}</div>
                <div><b>ชีพจร:</b> {pulse}</div>
            </div>
            <div style="margin-top: 16px; text-align: center;">
                <b>คำแนะนำ:</b> {summary_advice}
            </div>
        </div>
        """

    st.markdown(render_health_report(person, selected_cols), unsafe_allow_html=True)

    # ================== CBC / BLOOD TEST DISPLAY ==================

    
    cbc_cols = cbc_columns_by_year[selected_year]
    blood_cols = blood_columns_by_year[selected_year]
    
    # ✅ ฟังก์ชันช่วยให้แสดงค่า และ flag ว่าผิดปกติหรือไม่
    def flag_value(raw, low=None, high=None, higher_is_better=False):
        try:
            val = float(str(raw).replace(",", "").strip())
            if higher_is_better:
                return f"{val:.1f}", val < low
            if (low is not None and val < low) or (high is not None and val > high):
                return f"{val:.1f}", True
            return f"{val:.1f}", False
        except:
            return "-", False
    
    # ✅ CBC config
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
    
    # ✅ BLOOD config
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", blood_cols["FBS"], "74 - 106 mg/dl", 74, 106),
        ("กรดยูริคสาเหตุโรคเก๊าท์ (Uric acid)", blood_cols["Uric"], "2.6 - 7.2 mg%", 2.6, 7.2),
        ("การทำงานของเอนไซม์ตับ ALK.POS", blood_cols["ALK"], "30 - 120 U/L", 30, 120),
        ("การทำงานของเอนไซม์ตับ SGOT", blood_cols["SGOT"], "&lt; 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ SGPT", blood_cols["SGPT"], "&lt; 41 U/L", None, 41),
        ("คลอเรสเตอรอล (Cholesterol)", blood_cols["Cholesterol"], "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (Triglyceride)", blood_cols["TG"], "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", blood_cols["HDL"], "&gt; 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", blood_cols["LDL"], "0 - 160 mg/dl", 0, 160),
        ("การทำงานของไต (BUN)", blood_cols["BUN"], "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", blood_cols["Cr"], "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", blood_cols["GFR"], "&gt; 60 mL/min", 60, None, True),
    ]
    
    blood_rows = []
    for name, col, normal, low, high, *opt in blood_config:
        higher_is_better = opt[0] if opt else False
        raw = person.get(col, "-")
        result, is_abnormal = flag_value(raw, low, high, higher_is_better=higher_is_better)
        blood_rows.append([(name, is_abnormal), (result, is_abnormal), (normal, is_abnormal)])
    
    # ✅ Styled table renderer
    def styled_result_table(headers, rows):
        header_html = "".join([f"<th>{h}</th>" for h in headers])
        html = f"""
        <style>
            .styled-wrapper {{
                max-width: 820px;
                margin: 0 auto;
            }}
            .styled-result {{
                width: 100%;
                border-collapse: collapse;
            }}
            .styled-result th {{
                background-color: #111;
                color: white;
                padding: 6px 12px;
                text-align: center;
            }}
            .styled-result td {{
                padding: 6px 12px;
                vertical-align: middle;
            }}
            .styled-result td:nth-child(2) {{
                text-align: center;
            }}
            .abn {{
                background-color: rgba(255, 0, 0, 0.15);
            }}
        </style>
        <div class="styled-wrapper">
            <table class='styled-result'>
                <thead><tr>{header_html}</tr></thead>
                <tbody>
        """
        for row in rows:
            row_html = ""
            for cell, is_abn in row:
                css = " class='abn'" if is_abn else ""
                row_html += f"<td{css}>{cell}</td>"
            html += f"<tr>{row_html}</tr>"
        html += "</tbody></table></div>"
        return html

    def flag_urine_value(val, normal_range=None):
        val_str = str(val).strip()
        if val_str.upper() in ["N/A", "-", ""]:
            return "-", False
        val_clean = val_str.lower()
    
        if normal_range == "Yellow, Pale Yellow":
            return val_str, val_clean not in ["yellow", "pale yellow"]
        if normal_range == "Negative":
            return val_str, val_clean != "negative"
        if normal_range == "Negative, trace":
            return val_str, val_clean not in ["negative", "trace"]
        if normal_range == "5.0 - 8.0":
            try:
                num = float(val_str)
                return val_str, not (5.0 <= num <= 8.0)
            except:
                return val_str, True
        if normal_range == "1.003 - 1.030":
            try:
                num = float(val_str)
                return val_str, not (1.003 <= num <= 1.030)
            except:
                return val_str, True
        if "cell/HPF" in normal_range:
            try:
                # ดึง upper จากช่วงค่าปกติ เช่น "0 - 5 cell/HPF"
                upper = int(normal_range.split("-")[1].split()[0])
                # ถ้า value เป็นช่วง เช่น "2-3"
                if "-" in val_str:
                    left, right = map(int, val_str.split("-"))
                    return val_str, right > upper
                else:
                    num = int(val_str)
                    return val_str, num > upper
            except:
                return val_str, True
    
        return val_str, False

    def render_section_header(title):
        return f"""
        <div style="
            background-color: #1B5E20;
            padding: 20px 24px;
            border-radius: 6px;
            font-size: 18px;
            font-weight: bold;
            color: white;
            text-align: center;
            line-height: 1.4;
            margin: 2rem 0 1rem 0;
        ">
            {title}
        </div>
        """
    
    # ✅ Render ทั้งสองตาราง
    left_spacer, col1, col2, right_spacer = st.columns([1, 3, 3, 1])
    
    with col1:
        st.markdown(render_section_header("ผลการตรวจความสมบูรณ์ของเม็ดเลือด (Complete Blood Count)"), unsafe_allow_html=True)
        st.markdown(styled_result_table(["ชื่อการตรวจ", "ผลตรวจ", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_section_header("ผลตรวจเลือด (Blood Test)"), unsafe_allow_html=True)
        st.markdown(styled_result_table(["ชื่อการตรวจ", "ผลตรวจ", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    import re
    
    # 📌 ฟังก์ชันรวมคำแนะนำแบบไม่ซ้ำซ้อน
    def merge_similar_sentences(messages):
        if len(messages) == 1:
            return messages[0]
    
        merged = []
        seen_prefixes = {}
    
        for msg in messages:
            prefix = re.match(r"^(ควรพบแพทย์เพื่อตรวจหา(?:และติดตาม)?(?:[^,]*)?)", msg)
            if prefix:
                key = "ควรพบแพทย์เพื่อตรวจหา"
                rest = msg[len(prefix.group(1)):].strip()
                phrase = prefix.group(1)[len(key):].strip()
    
                # 🔧 รวม phrase และ rest → แล้วลบ "และ" ที่ขึ้นต้น
                full_detail = f"{phrase} {rest}".strip()
                full_detail = re.sub(r"^และ\s+", "", full_detail)
    
                if key in seen_prefixes:
                    seen_prefixes[key].append(full_detail)
                else:
                    seen_prefixes[key] = [full_detail]
            else:
                merged.append(msg)
    
        for key, endings in seen_prefixes.items():
            endings = [e.strip() for e in endings if e]
            if endings:
                if len(endings) == 1:
                    merged.append(f"{key} {endings[0]}")
                else:
                    body = " ".join(endings[:-1]) + " และ " + endings[-1]
                    merged.append(f"{key} {body}")
            else:
                merged.append(key)
    
        return "<br>".join(merged)
    
    cbc_messages = {
        2:  "ดูแลสุขภาพ ออกกำลังกาย ทานอาหารมีประโยชน์ ติดตามผลเลือดสม่ำเสมอ",
        4:  "ควรพบแพทย์เพื่อตรวจหาสาเหตุเกล็ดเลือดต่ำ เพื่อเฝ้าระวังอาการผิดปกติ",
        6:  "ควรตรวจซ้ำเพื่อติดตามเม็ดเลือดขาว และดูแลสุขภาพร่างกายให้แข็งแรง",
        8:  "ควรพบแพทย์เพื่อตรวจหาสาเหตุภาวะโลหิตจาง เพื่อรักษาตามนัด",
        9:  "ควรพบแพทย์เพื่อตรวจหาและติดตามภาวะโลหิตจางร่วมกับเม็ดเลือดขาวผิดปกติ",
        10: "ควรพบแพทย์เพื่อตรวจหาสาเหตุเกล็ดเลือดสูง เพื่อพิจารณาการรักษา",
        13: "ควรดูแลสุขภาพ ติดตามภาวะโลหิตจางและเม็ดเลือดขาวผิดปกติอย่างใกล้ชิด",
    }
    
    def interpret_wbc(wbc):
        try:
            wbc = float(wbc)
            if wbc == 0:
                return "-"
            elif 4000 <= wbc <= 10000:
                return "ปกติ"
            elif 10000 < wbc < 13000:
                return "สูงกว่าเกณฑ์เล็กน้อย"
            elif wbc >= 13000:
                return "สูงกว่าเกณฑ์"
            elif 3000 < wbc < 4000:
                return "ต่ำกว่าเกณฑ์เล็กน้อย"
            elif wbc <= 3000:
                return "ต่ำกว่าเกณฑ์"
        except:
            return "-"
        return "-"
    
    def interpret_hb(hb, sex):
        try:
            hb = float(hb)
            if sex == "ชาย":
                if hb < 12:
                    return "พบภาวะโลหิตจาง"
                elif 12 <= hb < 13:
                    return "พบภาวะโลหิตจางเล็กน้อย"
                else:
                    return "ปกติ"
            elif sex == "หญิง":
                if hb < 11:
                    return "พบภาวะโลหิตจาง"
                elif 11 <= hb < 12:
                    return "พบภาวะโลหิตจางเล็กน้อย"
                else:
                    return "ปกติ"
        except:
            return "-"
        return "-"
    
    def interpret_plt(plt):
        try:
            plt = float(plt)
            if plt == 0:
                return "-"
            elif 150000 <= plt <= 500000:
                return "ปกติ"
            elif 500000 < plt < 600000:
                return "สูงกว่าเกณฑ์เล็กน้อย"
            elif plt >= 600000:
                return "สูงกว่าเกณฑ์"
            elif 100000 <= plt < 150000:
                return "ต่ำกว่าเกณฑ์เล็กน้อย"
            elif plt < 100000:
                return "ต่ำกว่าเกณฑ์"
        except:
            return "-"
        return "-"
    
    def cbc_advice(hb_result, wbc_result, plt_result):
        message_ids = []
    
        if all(x in ["", "-", None] for x in [hb_result, wbc_result, plt_result]):
            return "-"
    
        if hb_result == "พบภาวะโลหิตจาง":
            if wbc_result == "ปกติ" and plt_result == "ปกติ":
                message_ids.append(8)
            elif wbc_result in ["ต่ำกว่าเกณฑ์", "ต่ำกว่าเกณฑ์เล็กน้อย", "สูงกว่าเกณฑ์เล็กน้อย", "สูงกว่าเกณฑ์"]:
                message_ids.append(9)
        elif hb_result == "พบภาวะโลหิตจางเล็กน้อย":
            if wbc_result == "ปกติ" and plt_result == "ปกติ":
                message_ids.append(2)
            elif wbc_result in ["ต่ำกว่าเกณฑ์", "ต่ำกว่าเกณฑ์เล็กน้อย", "สูงกว่าเกณฑ์เล็กน้อย", "สูงกว่าเกณฑ์"]:
                message_ids.append(13)
    
        if wbc_result in ["ต่ำกว่าเกณฑ์", "ต่ำกว่าเกณฑ์เล็กน้อย", "สูงกว่าเกณฑ์เล็กน้อย", "สูงกว่าเกณฑ์"] and hb_result == "ปกติ":
            message_ids.append(6)
    
        if plt_result == "สูงกว่าเกณฑ์":
            message_ids.append(10)
        elif plt_result in ["ต่ำกว่าเกณฑ์", "ต่ำกว่าเกณฑ์เล็กน้อย"]:
            message_ids.append(4)
    
        if not message_ids and hb_result == "ปกติ" and wbc_result == "ปกติ" and plt_result == "ปกติ":
            return ""
    
        if not message_ids:
            return "ควรพบแพทย์เพื่อตรวจเพิ่มเติม"
    
        # รวมข้อความจากหลาย id
        raw_msgs = [cbc_messages[i] for i in sorted(set(message_ids))]
        return merge_similar_sentences(raw_msgs)
    
    # 🔧 ยึดปีจาก selectbox
    suffix = str(selected_year)
    sex = person.get("เพศ", "").strip()
    
    # 🔍 ดึงค่าตามปีที่เลือก
    hb_raw = str(person.get(f"Hb(%)" + suffix, "")).strip()
    wbc_raw = str(person.get(f"WBC (cumm)" + suffix, "")).strip()
    plt_raw = str(person.get(f"Plt (/mm)" + suffix, "")).strip()
    
    # 🧠 แปลผล
    hb_result = interpret_hb(hb_raw, sex)
    wbc_result = interpret_wbc(wbc_raw)
    plt_result = interpret_plt(plt_raw)
    
    # 🩺 คำแนะนำ
    recommendation = cbc_advice(hb_result, wbc_result, plt_result)
    
    def summarize_liver(alp_val, sgot_val, sgpt_val):
        try:
            alp = float(alp_val)
            sgot = float(sgot_val)
            sgpt = float(sgpt_val)
            if alp == 0 or sgot == 0 or sgpt == 0:
                return "-"
            if alp > 120 or sgot > 36 or sgpt > 40:
                return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
            return "ปกติ"
        except:
            return "-"
    
    def liver_advice(summary_text):
        if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
            return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
        elif summary_text == "ปกติ":
            return ""
        return "-"
    
    # ✅ ใช้ปีที่เลือกจาก dropdown
    y = selected_year
    y_label = "" if y == 2568 else str(y % 100)
    
    alp_raw = str(person.get(f"ALP{y_label}", "") or "").strip()
    sgot_raw = str(person.get(f"SGOT{y_label}", "") or "").strip()
    sgpt_raw = str(person.get(f"SGPT{y_label}", "") or "").strip()
    
    summary = summarize_liver(alp_raw, sgot_raw, sgpt_raw)
    advice_liver = liver_advice(summary)
    
    def uric_acid_advice(value_raw):
        try:
            value = float(value_raw)
            if value > 7.2:
                return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
            return ""
        except:
            return "-"
    
    # ✅ ปีที่เลือกจาก dropdown
    y = selected_year
    y_label = "" if y == 2568 else str(y % 100)
    col_name = f"Uric Acid{y_label}"
    
    raw_value = str(person.get(col_name, "") or "").strip()
    advice_uric = uric_acid_advice(raw_value)
    
    # 🧪 แปลผลการทำงานของไตจาก GFR
    def kidney_summary_gfr_only(gfr_raw):
        try:
            gfr = float(str(gfr_raw).replace(",", "").strip())
            if gfr == 0:
                return ""
            elif gfr < 60:
                return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย"
            else:
                return "ปกติ"
        except:
            return ""
    
    # 📌 คำแนะนำเมื่อพบค่าผิดปกติ
    def kidney_advice_from_summary(summary_text):
        if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
            return (
                "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย "
                "ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน "
                "และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
            )
        return ""
    # ✅ ดึงค่าจาก person ตามปีที่เลือก
    gfr_raw = str(person.get(f"GFR{y_label}", "") or "").strip()
    
    # ✅ วิเคราะห์ผลการทำงานของไต และให้คำแนะนำ
    kidney_summary = kidney_summary_gfr_only(gfr_raw)
    advice_kidney = kidney_advice_from_summary(kidney_summary)
    
    # ===============================
    # ✅ คำแนะนำผลน้ำตาลในเลือด (FBS)
    # ===============================
    
    def fbs_advice(fbs_raw):
        try:
            value = float(str(fbs_raw).replace(",", "").strip())
            if value == 0:
                return ""
            elif 100 <= value < 106:
                return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
            elif 106 <= value < 126:
                return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
            elif value >= 126:
                return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
            else:
                return ""
        except:
            return ""
    
    # ใช้ปีที่เลือกจาก dropdown
    y = selected_year
    y_label = str(y)
    col_name = f"FBS{y_label}"
    raw_value = str(person.get(col_name, "") or "").strip()
    advice_fbs = fbs_advice(raw_value)
    
    # 🧪 ฟังก์ชันสรุปผลไขมันในเลือด
    def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
        try:
            chol = float(str(chol_raw).replace(",", "").strip())
            tgl = float(str(tgl_raw).replace(",", "").strip())
            ldl = float(str(ldl_raw).replace(",", "").strip())
    
            if chol == 0 and tgl == 0:
                return ""
            if chol >= 250 or tgl >= 250 or ldl >= 180:
                return "ไขมันในเลือดสูง"
            elif chol <= 200 and tgl <= 150:
                return "ปกติ"
            else:
                return "ไขมันในเลือดสูงเล็กน้อย"
        except:
            return ""
    
    # 📝 ฟังก์ชันให้คำแนะนำ
    def lipids_advice(summary_text):
        if summary_text == "ไขมันในเลือดสูง":
            return (
                "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ "
                "ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
            )
        elif summary_text == "ไขมันในเลือดสูงเล็กน้อย":
            return (
                "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน "
                "และออกกำลังกายเพื่อควบคุมระดับไขมัน"
            )
        return ""
    
    # ✅ ดึงค่าตามปีที่เลือก
    y = selected_year
    y_label = str(y)  # ควรใช้ str(y) เช่น "68", "67"
    
    chol_raw = str(person.get(f"CHOL{y_label}", "") or "").strip()
    tgl_raw = str(person.get(f"TGL{y_label}", "") or "").strip()
    ldl_raw = str(person.get(f"LDL{y_label}", "") or "").strip()
    
    summary = summarize_lipids(chol_raw, tgl_raw, ldl_raw)
    advice = lipids_advice(summary)
    
    # ✅ รวมคำแนะนำทุกหมวด
    all_advices = []
    
    if advice_fbs:
        all_advices.append(advice_fbs)
    
    if advice_kidney:
        all_advices.append(advice_kidney)
    
    if advice_liver:
        all_advices.append(advice_liver)
    
    if advice_uric:
        all_advices.append(advice_uric)
    
    if advice:
        all_advices.append(advice)  # คำแนะนำไขมันในเลือด
    
    if recommendation and recommendation != "-":
        all_advices.append(recommendation)

   
    # ✅ ฟังก์ชันรวมคำแนะนำทั้งหมด (ไม่ให้ซ้ำ)
    from collections import OrderedDict
    
    def merge_final_advice_grouped(messages):
        groups = {
            "FBS": [],
            "ไต": [],
            "ตับ": [],
            "ยูริค": [],
            "ไขมัน": [],
            "CBC": [],
        }
    
        for msg in messages:
            if "น้ำตาล" in msg:
                groups["FBS"].append(msg)
            elif "ไต" in msg:
                groups["ไต"].append(msg)
            elif "ตับ" in msg:
                groups["ตับ"].append(msg)
            elif "ยูริค" in msg or "พิวรีน" in msg:
                groups["ยูริค"].append(msg)
            elif "ไขมัน" in msg:
                groups["ไขมัน"].append(msg)
            else:
                groups["CBC"].append(msg)
    
        section_texts = []
        for title, msgs in groups.items():
            if msgs:
                icon = {
                    "FBS": "🍬", "ไต": "💧", "ตับ": "🫀",
                    "ยูริค": "🦴", "ไขมัน": "🧈", "CBC": "🩸"
                }.get(title, "📝")
                merged_msgs = [m for m in msgs if m.strip() != "-"]
                if not merged_msgs:
                    continue  # ข้ามหมวดนี้ไปเลย
                merged = " ".join(OrderedDict.fromkeys(merged_msgs))
                section = f"<b>{icon} {title}:</b> {merged}"
                section_texts.append(section)
    
        if not section_texts:
            return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"
    
        return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(section_texts) + "</div>"
        
    # ✅ แสดงผลรวม
    final_advice = merge_final_advice_grouped(all_advices)
    
    left_spacer, center_col, right_spacer = st.columns([1, 6, 1])
    
    with center_col:
        st.markdown(f"""
        <div style="
            background-color: rgba(33, 150, 243, 0.15);
            padding: 2rem 2.5rem;
            border-radius: 10px;
            font-size: 16px;
            line-height: 1.5;
            color: inherit;
        ">
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 1.5rem;">
                📋 คำแนะนำสรุปผลตรวจสุขภาพ ปี {2500 + selected_year}
            </div>
            {final_advice}
        </div>
        """, unsafe_allow_html=True)

    # ==================== Urinalysis & Additional Tests ====================
    left_spacer2, left_col, right_col, right_spacer2 = st.columns([1, 3, 3, 1])
    
    with left_col:
        # 📌 Render: หัวข้อปัสสาวะ
        st.markdown(render_section_header("ผลการตรวจปัสสาวะ (Urinalysis)"), unsafe_allow_html=True)
        
        y = selected_year
        y_label = str(y)
        sex = person.get("เพศ", "").strip()
        
        if y == 68:
            # 🔎 ปี 68 มีรายละเอียดครบ
            urine_config = [
                ("สี (Colour)", person.get("Color68", "N/A"), "Yellow, Pale Yellow"),
                ("น้ำตาล (Sugar)", person.get("sugar68", "N/A"), "Negative"),
                ("โปรตีน (Albumin)", person.get("Alb68", "N/A"), "Negative, trace"),
                ("กรด-ด่าง (pH)", person.get("pH68", "N/A"), "5.0 - 8.0"),
                ("ความถ่วงจำเพาะ (Sp.gr)", person.get("Spgr68", "N/A"), "1.003 - 1.030"),
                ("เม็ดเลือดแดง (RBC)", person.get("RBC168", "N/A"), "0 - 2 cell/HPF"),
                ("เม็ดเลือดขาว (WBC)", person.get("WBC168", "N/A"), "0 - 5 cell/HPF"),
                ("เซลล์เยื่อบุผิว (Squam.epit.)", person.get("SQ-epi68", "N/A"), "0 - 10 cell/HPF"),
                ("อื่นๆ", person.get("ORTER68", "N/A"), "-"),
            ]
            
            urine_rows = []
            for name, value, normal in urine_config:
                val_text, is_abn = flag_urine_value(value, normal)
                urine_rows.append([(name, is_abn), (val_text, is_abn), (normal, is_abn)])
            
            st.markdown(styled_result_table(["ชื่อการตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows), unsafe_allow_html=True)
        
            # ✅ คำแนะนำ
            alb_raw = person.get("Alb68", "").strip()
            sugar_raw = person.get("sugar68", "").strip()
            rbc_raw = person.get("RBC168", "").strip()
            wbc_raw = person.get("WBC168", "").strip()
        
            urine_advice = advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
            if urine_advice:
                st.markdown(f"""
                <div style='
                    background-color: rgba(255, 215, 0, 0.2);
                    padding: 1rem;
                    border-radius: 6px;
                    margin-top: 1rem;
                    font-size: 16px;
                '>
                    <div style='font-size: 18px; font-weight: bold;'>📌 คำแนะนำจากผลตรวจปัสสาวะ ปี 2568</div>
                    <div style='margin-top: 0.5rem;'>{urine_advice}</div>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            # 🔎 ปี < 68 → ใช้ข้อมูลสรุปจากฟิลด์ "ผลปัสสาวะ<ปี>"
            urine_text = person.get(f"ผลปัสสาวะ{y_label}", "").strip()
        
            if urine_text:
                st.markdown(f"""
                <div style='
                    margin-top: 1rem;
                    font-size: 16px;
                    line-height: 1.7;
                '>{urine_text}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='
                    margin-top: 1rem;
                    padding: 1rem;
                    background-color: rgba(255,255,255,0.05);
                    font-size: 16px;
                    line-height: 1.7;
                '>ไม่พบข้อมูลผลตรวจปัสสาวะในปีนี้</div>
                """, unsafe_allow_html=True)
    
        # ✅ ผลตรวจอุจจาระ + คำแนะนำ
        def safe_get(person, key):
            if isinstance(person, (dict, pd.Series)) and key in person and pd.notna(person[key]):
                return str(person[key]).strip()
            return ""

        stool_exam_key = "Stool exam" if y == 68 else f"Stool exam{y_label}"
        stool_cs_key = "Stool C/S" if y == 68 else f"Stool C/S{y_label}"

        if person is None:
            st.warning("ไม่พบข้อมูลของ HN นี้ในระบบ")
        else:
            stool_exam_raw = safe_get(person, stool_exam_key)
            stool_cs_raw = safe_get(person, stool_cs_key)
        
            exam_text = interpret_stool_exam(stool_exam_raw)
            cs_text = interpret_stool_cs(stool_cs_raw)
        
            st.markdown(render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
            st.markdown(f"""
            <p style='font-size: 16px; line-height: 1.7; margin-bottom: 1rem;'>
                <b>ผลตรวจอุจจาระทั่วไป:</b> {exam_text}<br>
                <b>ผลตรวจอุจจาระเพาะเชื้อ:</b> {cs_text}
            </p>
            """, unsafe_allow_html=True)
                
                stool_exam_raw = safe_get(person, stool_exam_key)
                stool_cs_raw = safe_get(person, stool_cs_key)
        
            
                exam_text = interpret_stool_exam(stool_exam_raw)
                cs_text = interpret_stool_cs(stool_cs_raw)
            
                st.markdown(render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
                st.markdown(f"""
                <p style='font-size: 16px; line-height: 1.7; margin-bottom: 1rem;'>
                    <b>ผลตรวจอุจจาระทั่วไป:</b> {exam_text}<br>
                    <b>ผลตรวจอุจจาระเพาะเชื้อ:</b> {cs_text}
                </p>
                """, unsafe_allow_html=True)
    
    with right_col:
        st.markdown(render_section_header("ผลเอกซเรย์ (Chest X-ray)"), unsafe_allow_html=True)
    
        def get_cxr_col_name(year):
            return "CXR" if year == 2568 else f"CXR{str(year)[-2:]}"
    
        def interpret_cxr(value):
            if not value or str(value).strip() == "":
                return "-"
            return str(value).strip()
    
        cxr_col = get_cxr_col_name(2500 + selected_year)
        cxr_raw = person.get(cxr_col, "")
        cxr_result = interpret_cxr(cxr_raw)
    
        st.markdown(f"""
        <div style='
            font-size: 16px;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1.5rem;
        '>{cxr_result}</div>
        """, unsafe_allow_html=True)
    
        # ----------------------------

        st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ (EKG)"), unsafe_allow_html=True)
        
        def get_ekg_col_name(year):
            return "EKG" if year == 2568 else f"EKG{str(year)[-2:]}"
        
        def interpret_ekg(value):
            if not value or str(value).strip() == "":
                return "-"
            return str(value).strip()
        
        ekg_col = get_ekg_col_name(2500 + selected_year)
        ekg_raw = person.get(ekg_col, "")
        ekg_result = interpret_ekg(ekg_raw)
        
        st.markdown(f"""
        <div style='
            font-size: 16px;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1.5rem;
        '>{ekg_result}</div>
        """, unsafe_allow_html=True)
        
        # ✅ Hepatitis Section (A & B)
        y_label = str(selected_year)
        
        hep_a_col = f"Hepatitis A{y_label}"
        hep_b_col = f"Hepatitis B{y_label}"
        
        def interpret_hep(value):
            if not value or str(value).strip() == "":
                return "-"
            return str(value).strip()
        
        hep_a_raw = interpret_hep(person.get(hep_a_col))
        hep_b_raw = interpret_hep(person.get(hep_b_col))
        
        # 👉 หัวข้อ Hepatitis A
        st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบเอ (Viral hepatitis A)"), unsafe_allow_html=True)
        st.markdown(f"""
        <div style='
            text-align: left;
            font-size: 16px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border-radius: 6px;
        '>
        {hep_a_raw}
        </div>
        """, unsafe_allow_html=True)
        
        # 👉 หัวข้อ Hepatitis B (ใหม่: รวมตาราง HBsAg/HBsAb/HBcAb)
        st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)"), unsafe_allow_html=True)
        
        # ดึงค่าจาก DataFrame
        hbsag_raw = person.get("HbsAg", "N/A").strip()
        hbsab_raw = person.get("HbsAb", "N/A").strip()
        hbcab_raw = person.get("HBcAB", "N/A").strip()

        # แสดงผลแบบไม่มีพื้นหลังสีในแถวหัวตาราง
        hepb_table = f"""
        <table style='width:100%; font-size:16px; text-align:center; border-collapse: collapse; margin-bottom: 1rem;'>
            <thead>
                <tr style='font-weight:bold; border-bottom: 1px solid #ccc;'>
                    <th>HBsAg</th>
                    <th>HBsAb</th>
                    <th>HBcAb</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{hbsag_raw}</td>
                    <td>{hbsab_raw}</td>
                    <td>{hbcab_raw}</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(hepb_table, unsafe_allow_html=True)

        def hepatitis_b_advice(hbsag, hbsab, hbcab):
            hbsag = hbsag.lower()
            hbsab = hbsab.lower()
            hbcab = hbcab.lower()
        
            if "positive" in hbsag:
                return "ติดเชื้อไวรัสตับอักเสบบี"
            elif "positive" in hbsab and "positive" not in hbsag:
                return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
            elif "positive" in hbcab and "positive" not in hbsab:
                return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
            elif all(x == "negative" for x in [hbsag, hbsab, hbcab]):
                return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
            else:
                return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"
        
        # แสดงคำแนะนำ
        st.markdown(f"""
        <div style="font-size: 16px; padding: 1rem; background-color: rgba(255, 215, 0, 0.2); border-radius: 6px;">
        {hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw)}
        </div>
        """, unsafe_allow_html=True)

    left_spacer3, doctor_col, right_spacer3 = st.columns([1, 6, 1])
    
    with doctor_col:
        st.markdown(f"""
        <div style='
            background-color: #1B5E20;
            padding: 20px 24px;
            border-radius: 6px;
            font-size: 18px;
            line-height: 1.6;
            margin: 1.5rem 0;
            color: inherit;
        '>
            <b>สรุปความเห็นของแพทย์ :</b> (ยังไม่ได้เชื่อมคอลัมน์)
        </div>
    
        <div style='
            margin-top: 3rem;
            text-align: right;
            padding-right: 1rem;
        '>
            <div style='
                display: inline-block;
                text-align: center;
                width: 340px;
            '>
                <div style='
                    border-bottom: 1px dotted #ccc;
                    margin-bottom: 0.5rem;
                    width: 100%;
                '></div>
                <div style='white-space: nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
                <div style='white-space: nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

