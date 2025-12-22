import streamlit as st
import pandas as pd
import re
import html
import numpy as np
import textwrap
from collections import OrderedDict
from datetime import datetime
import json

# --- Import ฟังก์ชันจากไฟล์อื่นที่จำเป็น ---
from performance_tests import interpret_audiogram, interpret_lung_capacity, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
from visualization import display_visualization_tab

# --- Helper Functions ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
    if is_empty(name):
        return ""
    return re.sub(r'\s+', '', str(name).strip())

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
    try:
        val = float(str(val).replace(",", "").strip())
    except: return "-", False
    formatted_val = f"{int(val):,}" if val == int(val) else f"{val:,.1f}"
    is_abnormal = False
    if higher_is_better:
        if low is not None and val < low: is_abnormal = True
    else:
        if low is not None and val < low: is_abnormal = True
        if high is not None and val > high: is_abnormal = True
    return formatted_val, is_abnormal

def clean_html_string(html_str):
    """
    ฟังก์ชันล้างช่องว่างนำหน้าบรรทัด (Indentation) ทั้งหมด
    เพื่อป้องกันไม่ให้ Streamlit ตีความ HTML เป็น Code Block
    """
    if not html_str: return ""
    return "\n".join([line.strip() for line in html_str.split('\n') if line.strip()])

def render_section_header(title):
    # ปรับ Header ให้สวยงามขึ้น มีแถบสีด้านซ้าย
    st.markdown(clean_html_string(f"""
    <div class="section-header-styled">
        {title}
    </div>
    """), unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table"):
    header_html = f"<div class='table-title'>{title}</div>"
    
    # สร้างส่วนหัวตาราง
    thead = "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i in [0, 2] else "center"
        thead += f"<th style='text-align: {align};'>{h}</th>"
    thead += "</tr></thead>"

    # สร้างส่วนเนื้อหาตาราง
    tbody = "<tbody>"
    for row in rows:
        # ตรวจสอบว่าแถวนี้มีค่าผิดปกติหรือไม่ (เช็คจาก flag ที่ส่งมาใน tuple ตัวที่ 2)
        # row structure: [(text, is_abn), (text, is_abn), (text, is_abn)]
        is_row_abnormal = any(item[1] for item in row)
        row_class = "abnormal-row" if is_row_abnormal else ""
        
        tbody += f"<tr class='{row_class}'>"
        tbody += f"<td style='text-align: left; font-weight: 500;'>{row[0][0]}</td>" # ชื่อการตรวจ
        
        # ค่าผลตรวจ (ถ้าผิดปกติ ให้ใส่สีแดงเข้ม)
        val_class = "text-danger" if row[1][1] else ""
        tbody += f"<td class='{val_class}' style='text-align: center; font-weight: bold;'>{row[1][0]}</td>"
        
        tbody += f"<td style='text-align: left; color: #666;'>{row[2][0]}</td>" # ค่าปกติ
        tbody += "</tr>"
    tbody += "</tbody>"

    html_content = clean_html_string(f"""
    <div class="card-container">
        {header_html}
        <div class='table-responsive'>
            <table class='{table_class}'>
                <colgroup>
                    <col style='width:40%;'>
                    <col style='width:20%;'>
                    <col style='width:40%;'>
                </colgroup>
                {thead}
                {tbody}
            </table>
        </div>
    </div>
    """)
    return html_content

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

# ... (other helpers) ...
def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val: return map(float, val.split("-"))
        else: num = float(val); return num, num
    except: return None, None

def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 2: return "ปกติ"
    if high <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 5: return "ปกติ"
    if high <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]: return False
    if test_name == "กรด-ด่าง (pH)":
        try: return not (5.0 <= float(val) <= 8.0)
        except: return True
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try: return not (1.003 <= float(val) <= 1.030)
        except: return True
    if test_name == "เม็ดเลือดแดง (RBC)": return "พบ" in interpret_rbc(val).lower()
    if test_name == "เม็ดเลือดขาว (WBC)": return "พบ" in interpret_wbc(val).lower()
    if test_name == "น้ำตาล (Sugar)": return val.lower() not in ["negative"]
    if test_name == "โปรตีน (Albumin)": return val.lower() not in ["negative", "trace"]
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False

def render_urine_section(person_data, sex, year_selected):
    urine_data = [("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"), ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"), ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"), ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"), ("อื่นๆ", person_data.get("ORTER", "-"), "-")]
    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    html_content = render_lab_table_html("ผลการตรวจปัสสาวะ (Urinalysis)", ["การตรวจ", "ผล", "ค่าปกติ"], [[(row["การตรวจ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (safe_value(row["ผลตรวจ"]), is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (row["ค่าปกติ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"]))] for _, row in df_urine.iterrows()], table_class="lab-table")
    st.markdown(html_content, unsafe_allow_html=True)
    return any(not is_empty(val) for _, val, _ in urine_data)

def interpret_stool_exam(val):
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    if is_empty(value): return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
    # ใช้การ์ดและตารางแบบใหม่
    html_content = clean_html_string(f"""
    <div class="card-container">
        <div class="table-title">ผลตรวจอุจจาระ (Stool Examination)</div>
        <table class="info-detail-table">
            <tbody>
                <tr><th width="40%">ผลตรวจอุจจาระทั่วไป</th><td>{exam}</td></tr>
                <tr><th>ผลตรวจอุจจาระเพาะเชื้อ</th><td>{cs}</td></tr>
            </tbody>
        </table>
    </div>
    """)
    return html_content

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"<span class='text-danger'>{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม</span>"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    hbsag, hbsab, hbcab = str(hbsag).lower(), str(hbsab).lower(), str(hbcab).lower()
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

# --- UI Functions ---
def interpret_bp(sbp, dbp):
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"
    except: return "-"

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"<span class='text-danger'>{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม</span>"
    return val

def interpret_bmi(bmi):
    if bmi is None: return ""
    if bmi < 18.5: return "น้ำหนักน้อยกว่าเกณฑ์"
    elif 18.5 <= bmi < 23: return "น้ำหนักปกติ"
    elif 23 <= bmi < 25: return "น้ำหนักเกิน (ท้วม)"
    elif 25 <= bmi < 30: return "เข้าเกณฑ์โรคอ้วน"
    elif bmi >= 30: return "เข้าเกณฑ์โรคอ้วนอันตราย"
    return ""

def display_common_header(person_data):
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
        bp_val = f"{sbp_int}/{dbp_int}"
        bp_desc = interpret_bp(sbp_int, dbp_int)
    except:
        bp_val = "-"
        bp_desc = "ไม่มีข้อมูล"

    try: pulse_val = f"{int(float(person_data.get('pulse', '-')))}"
    except: pulse_val = "-"

    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight}" if weight is not None else "-"
    height_val = f"{height}" if height is not None else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')}"

    bmi_val_str = "-"
    bmi_desc = ""
    if weight is not None and height is not None and height > 0:
        bmi = weight / ((height / 100) ** 2)
        bmi_val_str = f"{bmi:.1f}"
        bmi_desc = interpret_bmi(bmi)

    # แก้ไข: เปลี่ยนจาก Emoji กลับเป็น SVG Icons (Minimal Style)
    # ใช้ SVG มาตรฐาน (Feather Icons Style) ที่มีความคมชัดและดูเป็นทางการ
    
    # 1. Profile Icon (User)
    icon_profile = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>"""
    
    # 2. Body/Scale Icon (User Body)
    icon_body = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>"""
    
    # 3. Waist Icon (Circle with diameter/measure) - Using 'Disc' or 'Circle' concept
    icon_waist = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M8 12h8"></path></svg>"""
    
    # 4. BP Icon (Heart)
    icon_heart = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>"""
    
    # 5. Pulse Icon (Activity)
    icon_pulse = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>"""

    html_content = clean_html_string(f"""
    <div class="report-header-container">
        <div class="header-main">
            <div class="patient-profile">
                <div class="profile-icon">{icon_profile}</div>
                <div class="profile-details">
                    <div class="patient-name">{name}</div>
                    <div class="patient-meta">
                        <span>HN: {hn}</span> | 
                        <span>เพศ: {sex}</span> | 
                        <span>อายุ: {age} ปี</span>
                    </div>
                    <div class="patient-dept">หน่วยงาน: {department}</div>
                </div>
            </div>
            <div class="report-meta">
                <div class="meta-date">วันที่ตรวจ: {check_date}</div>
                <div class="hospital-brand">
                    <div class="hosp-name">คลินิกตรวจสุขภาพ</div>
                    <div class="hosp-dept">อาชีวเวชกรรม</div>
                    <div class="hosp-sub">รพ.สันทราย</div>
                </div>
            </div>
        </div>
    </div>

    <div class="vitals-grid-container">
        <div class="vital-card">
            <div class="vital-icon-box color-blue">
                {icon_body}
            </div>
            <div class="vital-content">
                <div class="vital-label">สัดส่วนร่างกาย</div>
                <div class="vital-value">{weight_val} <span class="unit">kg</span> / {height_val} <span class="unit">cm</span></div>
                <div class="vital-sub">BMI: {bmi_val_str} <br><span class="badge badge-bmi">{bmi_desc}</span></div>
            </div>
        </div>
        
        <div class="vital-card">
            <div class="vital-icon-box color-green">
                {icon_waist}
            </div>
            <div class="vital-content">
                <div class="vital-label">รอบเอว</div>
                <div class="vital-value">{waist_val} <span class="unit">cm</span></div>
            </div>
        </div>

        <div class="vital-card">
            <div class="vital-icon-box color-red">
                {icon_heart}
            </div>
            <div class="vital-content">
                <div class="vital-label">ความดันโลหิต</div>
                <div class="vital-value">{bp_val} <span class="unit">mmHg</span></div>
                <div class="vital-sub">{bp_desc}</div>
            </div>
        </div>

        <div class="vital-card">
            <div class="vital-icon-box color-orange">
                {icon_pulse}
            </div>
            <div class="vital-content">
                <div class="vital-label">ชีพจร</div>
                <div class="vital-value">{pulse_val} <span class="unit">bpm</span></div>
            </div>
        </div>
    </div>
    """)
    st.markdown(html_content, unsafe_allow_html=True)

def inject_custom_css():
    # แก้ไข: ปรับ CSS ให้รองรับ SVG และยังคงความสวยงาม (Modern Clean Look)
    css_content = clean_html_string("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary: #00796B;
            --primary-light: #B2DFDB;
            --bg-light: #F8F9FA;
            --text-dark: #2C3E50;
            --text-grey: #607D8B;
            --danger-bg: #FFEBEE;
            --danger-text: #C62828;
            --success-bg: #E8F5E9;
            --success-text: #2E7D32;
            --border-color: #E0E0E0;
            --card-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, div, span, th, td {
            font-family: 'Sarabun', sans-serif !important;
        }

        /* Section Header */
        .section-header-styled {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary);
            border-left: 5px solid var(--primary);
            padding-left: 15px;
            margin-top: 30px;
            margin-bottom: 20px;
            background: linear-gradient(90deg, rgba(0,121,107,0.05) 0%, rgba(255,255,255,0) 100%);
            padding-top: 10px;
            padding-bottom: 10px;
            border-radius: 0 8px 8px 0;
        }
        
        .section-subtitle {
            font-weight: 600;
            color: #455A64;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
        }

        /* Card Container Styles */
        .card-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-color);
            margin-bottom: 20px;
        }

        .table-title {
            font-weight: 700;
            color: var(--text-dark);
            margin-bottom: 15px;
            font-size: 1.1rem;
            border-bottom: 2px solid #F0F0F0;
            padding-bottom: 10px;
        }

        /* Modern Tables */
        .table-responsive {
            overflow-x: auto;
        }
        
        .lab-table, .info-detail-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        .lab-table th, .info-detail-table th {
            background-color: #F5F7F9;
            color: #546E7A;
            font-weight: 600;
            padding: 12px 15px;
            text-transform: uppercase;
            font-size: 0.85rem;
            border-bottom: 2px solid #CFD8DC;
        }
        
        .lab-table td, .info-detail-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #ECEFF1;
            color: #37474F;
        }
        
        .lab-table tr:last-child td {
            border-bottom: none;
        }
        
        .lab-table tr:hover {
            background-color: #FAFAFA;
        }

        /* Abnormal Rows */
        .abnormal-row {
            background-color: #FFEBEE !important;
        }
        .abnormal-row td {
            border-bottom: 1px solid #FFCDD2;
        }
        .text-danger {
            color: #D32F2F !important;
            font-weight: bold;
        }

        /* Header Layout */
        .report-header-container {
            background-color: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-color);
            margin-bottom: 25px;
        }
        
        .header-main {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .patient-profile {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .profile-icon {
            width: 60px;
            height: 60px;
            background-color: var(--primary-light);
            color: var(--primary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .profile-icon svg {
            width: 32px;
            height: 32px;
        }
        
        .patient-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-dark);
            line-height: 1.2;
        }
        
        .patient-meta {
            color: var(--text-grey);
            font-size: 0.95rem;
            margin-top: 5px;
        }
        
        .patient-dept {
            background-color: #ECEFF1;
            color: #455A64;
            display: inline-block;
            padding: 2px 10px;
            border-radius: 4px;
            font-size: 0.85rem;
            margin-top: 5px;
            font-weight: 500;
        }
        
        .report-meta {
            text-align: right;
        }
        
        .hospital-brand .hosp-name {
            font-weight: 700;
            color: var(--primary);
            font-size: 1.1rem;
            line-height: 1.2;
        }
        
        .hospital-brand .hosp-dept {
            font-size: 1rem;
            color: #455A64;
            font-weight: 600;
            line-height: 1.2;
        }
        
        .hospital-brand .hosp-sub {
            font-size: 0.9rem;
            color: #78909C;
            line-height: 1.2;
        }
        
        /* Vitals Grid */
        .vitals-grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .vital-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: var(--card-shadow);
            border: 1px solid var(--border-color);
            transition: transform 0.2s;
        }
        
        .vital-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.1);
        }
        
        .vital-icon-box {
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 5px;
        }
        
        .vital-icon-box svg {
            width: 36px;
            height: 36px;
        }
        
        /* Remove background colors for icons */
        .color-blue { background: transparent; color: #1976D2; }
        .color-green { background: transparent; color: #388E3C; }
        .color-red { background: transparent; color: #D32F2F; }
        .color-orange { background: transparent; color: #F57C00; }
        
        .vital-content {
            flex: 1;
        }
        
        .vital-label {
            font-size: 0.85rem;
            color: #78909C;
            font-weight: 500;
        }
        
        .vital-value {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-dark);
            line-height: 1.2;
        }
        
        .unit {
            font-size: 0.9rem;
            color: #90A4AE;
            font-weight: 400;
        }
        
        .vital-sub {
            font-size: 0.8rem;
            color: #78909C;
            margin-top: 2px;
        }
        
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-bmi { background-color: #ECEFF1; color: #455A64; }

        /* Advice Boxes */
        .recommendation-container {
            background-color: white;
            border-radius: 12px;
            padding: 25px;
            border-left: 6px solid var(--primary);
            box-shadow: var(--card-shadow);
        }
        
        .custom-advice-box {
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            border: 1px solid transparent;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .custom-advice-box::before { content: "💡"; font-size: 1.2rem; }
        
        .immune-box { background-color: #E8F5E9; color: #2E7D32; border-color: #C8E6C9; }
        .no-immune-box { background-color: #FFEBEE; color: #C62828; border-color: #FFCDD2; }
        .warning-box { background-color: #FFF8E1; color: #F57F17; border-color: #FFE082; }
        
        /* Vision Table Specifics */
        .vision-table th { background-color: #F5F5F5; }
        .vision-result {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .vision-normal { background-color: #E8F5E9; color: #2E7D32; }
        .vision-abnormal { background-color: #FFEBEE; color: #C62828; }
        .vision-not-tested { background-color: #ECEFF1; color: #90A4AE; }

    </style>""")
    st.markdown(css_content, unsafe_allow_html=True)

# ... (Functions for displaying specific report sections) ...

def render_vision_details_table(person_data):
    # ปรับปรุง: สร้าง Config เพื่อ map ชื่อคอลัมน์ที่เป็นไปได้หลายๆ แบบ
    vision_config = [
        {
            'id': 'V_R_Far', 
            'label': 'ตาขวา ไกล (Right Far)', 
            'keys': ['V_R_Far', 'R_Far', 'Far_R', 'Right Far', 'Far Vision Right', 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'R-Far']
        },
        {
            'id': 'V_L_Far', 
            'label': 'ตาซ้าย ไกล (Left Far)', 
            'keys': ['V_L_Far', 'L_Far', 'Far_L', 'Left Far', 'Far Vision Left', 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'L-Far']
        },
        {
            'id': 'V_R_Near', 
            'label': 'ตาขวา ใกล้ (Right Near)', 
            'keys': ['V_R_Near', 'R_Near', 'Near_R', 'Right Near', 'Near Vision Right', 'R-Near']
        },
        {
            'id': 'V_L_Near', 
            'label': 'ตาซ้าย ใกล้ (Left Near)', 
            'keys': ['V_L_Near', 'L_Near', 'Near_L', 'Left Near', 'Near Vision Left', 'L-Near']
        },
        {
            'id': 'Color_Blind', 
            'label': 'ตาบอดสี (Color Blindness)', 
            'keys': ['Color_Blind', 'ColorBlind', 'Ishihara', 'Color Vision', 'ตาบอดสี', 'Color']
        }
    ]
    
    def check_vision(val, test_type):
        if is_empty(val): return "Not Tested", "vision-not-tested"
        val_str = str(val).strip().lower()
        
        if test_type == 'Color_Blind':
            if val_str in ['normal', 'ปกติ', 'pass', 'ผ่าน']: return "ปกติ", "vision-normal"
            else: return "ผิดปกติ", "vision-abnormal"
        else:
            # กรณีระบุค่าสายตา (เช่น 20/20) หรือระบุผล
            if val_str in ['normal', 'ปกติ']: return "ปกติ", "vision-normal"
            elif val_str in ['abnormal', 'ผิดปกติ']: return "ผิดปกติ", "vision-abnormal"
            return str(val), "vision-normal" # แสดงค่าจริงถ้าไม่ใช่ ปกติ/ผิดปกติ

    # สร้าง HTML Rows
    html_rows = ""
    has_data = False
    
    for item in vision_config:
        # วนหาค่าจาก keys ที่เป็นไปได้
        val = None
        for key in item['keys']:
            if not is_empty(person_data.get(key)):
                val = person_data.get(key)
                break
        
        # ถ้ามีค่า ให้แสดงผล (หรือถ้าต้องการแสดงแถวว่าง ก็เอาเงื่อนไข if val is not None ออกได้ แต่ปกติไม่ควรแสดงถ้าไม่มีข้อมูล)
        if val is not None:
            has_data = True
            res_text, res_class = check_vision(val, item['id'])
            html_rows += f"<tr><td>{item['label']}</td><td class='result-cell' style='text-align:center;'><span class='vision-result {res_class}'>{res_text}</span></td></tr>"
    
    html_content = clean_html_string(f"""<div class='card-container'><div class='table-title'>ผลการตรวจสายตา</div><table class='vision-table'><thead><tr><th>รายการทดสอบ</th><th style='text-align: center;'>ผลการตรวจ</th></tr></thead><tbody>{html_rows}</tbody></table></div>""")
    
    if has_data:
        st.markdown(html_content, unsafe_allow_html=True)
    else:
        st.info("ไม่พบข้อมูลการตรวจสายตา")

def display_performance_report_hearing(person_data, all_person_history_df):
    results = interpret_audiogram(person_data, all_person_history_df)
    
    # แก้ไข: เพิ่ม function ดึงข้อมูลหูที่ครอบคลุมหลายรูปแบบ (R250, R_250, R_250Hz, etc.)
    freqs = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
    
    def get_hearing_val(side, freq):
        # สร้าง candidate keys ที่เป็นไปได้ทั้งหมด
        suffixes = [str(freq)]
        if freq >= 1000: suffixes.append(f"{freq//1000}k") # 1k, 2k
        
        candidates = []
        for s in suffixes:
            candidates.append(f"{side}{s}")      # R250
            candidates.append(f"{side}_{s}")     # R_250
            candidates.append(f"{side}_{s}Hz")   # R_250Hz
            candidates.append(f"{side}{s}Hz")    # R250Hz
            
        for k in candidates:
            val = person_data.get(k)
            if not is_empty(val): return val
        return "-"

    # ดึงค่าตาม Map
    r_vals = [get_hearing_val('R', f) for f in freqs]
    l_vals = [get_hearing_val('L', f) for f in freqs]
    
    # New Table Layout
    table_html = clean_html_string(f"""
    <div class='card-container'>
        <div class='table-title'>ตารางระดับการได้ยิน (dB)</div>
        <div class='table-responsive'>
            <table class='lab-table'>
                <thead>
                    <tr><th>ความถี่ (Hz)</th>{"".join([f"<th>{f}</th>" for f in freqs])}</tr>
                </thead>
                <tbody>
                    <tr><td><b>หูขวา (Right)</b></td>{"".join([f"<td style='text-align:center;'>{v}</td>" for v in r_vals])}</tr>
                    <tr><td><b>หูซ้าย (Left)</b></td>{"".join([f"<td style='text-align:center;'>{v}</td>" for v in l_vals])}</tr>
                </tbody>
            </table>
        </div>
    </div>
    """)
    
    st.markdown(table_html, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1: 
        st.markdown(f"<div class='card-container'><b>สรุปผลหูขวา:</b><br>{results['summary']['right']}</div>", unsafe_allow_html=True)
    with col2: 
        st.markdown(f"<div class='card-container'><b>สรุปผลหูซ้าย:</b><br>{results['summary']['left']}</div>", unsafe_allow_html=True)
    
    if results['advice']:
        st.warning(f"คำแนะนำ: {results['advice']}")

def display_performance_report_lung(person_data):
    summary, advice, raw_data = interpret_lung_capacity(person_data)
    
    lung_items = [
        ("FVC (ความจุรอดชีวิต)", raw_data['FVC predic'], raw_data['FVC'], raw_data['FVC %']),
        ("FEV1 (ปริมาตรหายใจออกใน 1 วินาทีแรก)", raw_data['FEV1 predic'], raw_data['FEV1'], raw_data['FEV1 %']),
        ("FEV1/FVC Ratio", "-", raw_data['FEV1/FVC %'], "-")
    ]
    
    # แก้ไข: ใช้ clean_html_string
    html_content = clean_html_string("""
    <div class='card-container'>
    <div class='table-title'>ข้อมูลสมรรถภาพปอด</div>
    <table class='lab-table'>
        <thead>
            <tr>
                <th style='width: 40%;'>รายการ (Parameter)</th>
                <th>ค่ามาตรฐาน (Predicted)</th>
                <th>ค่าที่วัดได้ (Actual)</th>
                <th>ร้อยละ (% Predicted)</th>
            </tr>
        </thead>
        <tbody>
    """)
    for label, pred, act, per in lung_items:
        html_content += f"<tr><td>{label}</td><td style='text-align:center;'>{pred}</td><td style='text-align:center;'>{act}</td><td style='text-align:center;'>{per}</td></tr>"
    html_content += "</tbody></table></div>"
    
    st.markdown(html_content, unsafe_allow_html=True)
    st.markdown(f"<div class='card-container'><b>สรุปผล:</b> {summary}<br><br><b>คำแนะนำ:</b> {advice}</div>", unsafe_allow_html=True)

def display_performance_report_vision(person_data):
    render_vision_details_table(person_data)

def display_performance_report(person_data, report_type, all_person_history_df=None):
    if report_type == 'lung':
        render_section_header("ผลตรวจสมรรถภาพปอด (Lung Function Test)")
        display_performance_report_lung(person_data)
    elif report_type == 'vision':
        render_section_header("ผลตรวจการมองเห็น (Vision Test)")
        display_performance_report_vision(person_data)
    elif report_type == 'hearing':
        render_section_header("ผลตรวจการได้ยิน (Audiometry)")
        display_performance_report_hearing(person_data, all_person_history_df)

def display_main_report(person_data, all_person_history_df):
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]

    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]

    render_section_header("ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)")
    col1, col2 = st.columns(2)
    with col1: st.markdown(render_lab_table_html("ความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    with col2: st.markdown(render_lab_table_html("เคมีคลินิก (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    selected_year = person.get("Year", datetime.now().year + 543)

    render_section_header("ผลการตรวจอื่นๆ (Other Examinations)")
    col_ua_left, col_ua_right = st.columns(2)
    with col_ua_left:
        render_urine_section(person, sex, selected_year)
        st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)

    with col_ua_right:
        cxr_col = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
        ekg_col_name = get_ekg_col_name(selected_year)
        hep_a_value = person.get("Hepatitis A")
        hep_a_display_text = "ไม่ได้ตรวจ" if is_empty(hep_a_value) else safe_text(hep_a_value)

        # แก้ไข: ใช้ clean_html_string เพื่อลบ Indentation
        st.markdown(clean_html_string(f"""
        <div class="card-container">
            <div class="table-title">ผลตรวจพิเศษ</div>
            <table class="info-detail-table">
                <tbody>
                    <tr><th width="40%">เอกซเรย์ (Chest X-ray)</th><td>{interpret_cxr(person.get(cxr_col, ''))}</td></tr>
                    <tr><th>คลื่นไฟฟ้าหัวใจ (EKG)</th><td>{interpret_ekg(person.get(ekg_col_name, ''))}</td></tr>
                    <tr><th>ไวรัสตับอักเสบเอ</th><td>{hep_a_display_text}</td></tr>
                </tbody>
            </table>
        </div>
        """), unsafe_allow_html=True)

        # --- Logic to get correct Hepatitis B columns based on year ---
        hbsag_col = "HbsAg"
        hbsab_col = "HbsAb"
        hbcab_col = "HBcAB"
        
        # 1. Determine columns based on history
        current_thai_year = datetime.now().year + 543
        if selected_year != current_thai_year:
            suffix = str(selected_year)[-2:]
            if f"HbsAg{suffix}" in person: hbsag_col = f"HbsAg{suffix}"
            if f"HbsAb{suffix}" in person: hbsab_col = f"HbsAb{suffix}"
            if f"HBcAB{suffix}" in person: hbcab_col = f"HBcAB{suffix}"

        # 2. Determine Header Suffix (Display Year)
        hep_year_rec = str(person.get("ปีตรวจHEP", "")).strip()
        header_suffix = ""
        if not is_empty(hep_year_rec):
                header_suffix = f" (ตรวจเมื่อ: {hep_year_rec})"
        elif selected_year and selected_year != current_thai_year:
                header_suffix = f" (พ.ศ. {selected_year})"

        hbsag = safe_text(person.get(hbsag_col))
        hbsab = safe_text(person.get(hbsab_col))
        hbcab = safe_text(person.get(hbcab_col))
        
        # แก้ไข: ใช้ clean_html_string เพื่อลบ Indentation
        st.markdown(clean_html_string(f"""
        <div class="card-container">
            <div class="table-title">ไวรัสตับอักเสบบี (Hepatitis B){header_suffix}</div>
            <table class='lab-table'>
                <thead><tr><th style='text-align: center;'>HBsAg</th><th style='text-align: center;'>HBsAb</th><th style='text-align: center;'>HBcAb</th></tr></thead>
                <tbody><tr><td style='text-align: center;'>{hbsag}</td><td style='text-align: center;'>{hbsab}</td><td style='text-align: center;'>{hbcab}</td></tr></tbody>
            </table>
        </div>
        """), unsafe_allow_html=True)

        if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)):
            advice, status = hepatitis_b_advice(hbsag, hbsab, hbcab)
            status_class = ""
            if status == 'immune':
                status_class = 'immune-box'
            elif status == 'no_immune':
                status_class = 'no-immune-box'
            else:
                status_class = 'warning-box'
            
            # แก้ไข: ใช้ clean_html_string เพื่อลบ Indentation
            st.markdown(clean_html_string(f"""
            <div class='custom-advice-box {status_class}'>
                {advice}
            </div>
            """), unsafe_allow_html=True)

    render_section_header("สรุปและคำแนะนำการปฏิบัติตัว (Summary & Recommendations)")
    recommendations_html = generate_comprehensive_recommendations(person_data)
    st.markdown(f"<div class='recommendation-container'>{recommendations_html}</div>", unsafe_allow_html=True)
