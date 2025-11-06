# shared_ui.py
# ไฟล์นี้เก็บฟังก์ชันที่ใช้ร่วมกันระหว่าง app.py และ admin_panel.py

import streamlit as st
import pandas as pd
import re
import html
import numpy as np
from collections import OrderedDict
from datetime import datetime
import json

# --- Import ฟังก์ชันจากไฟล์อื่นที่จำเป็น ---
# (จำเป็นต้อง import มาที่นี่ เพราะฟังก์ชันที่ย้ายมาอาจต้องใช้)
from performance_tests import interpret_audiogram, interpret_lung_capacity, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
from visualization import display_visualization_tab # Import display_visualization_tab มาที่นี่

# --- Helper Functions (ย้ายมาจาก app.py) ---
def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
    """จัดการการเว้นวรรคในชื่อ-นามสกุลที่ไม่สม่ำเสมอ"""
    if is_empty(name):
        return ""
    return re.sub(r'\s+', '', str(name).strip())

def get_float(col, person_data):
    """Safely gets a float value from person_data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
    """Formats a lab value and flags it if it's abnormal."""
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

def render_section_header(title):
    """Renders a new, modern section header."""
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table"):
    """Generates HTML for a lab result table with a new header style."""
    header_html = f"<h5 class='section-subtitle'>{title}</h5>"
    html_content = f"{header_html}<div class='table-container'><table class='{table_class}'><colgroup><col style='width:40%;'><col style='width:20%;'><col style='width:40%;'></colgroup><thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i in [0, 2] else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"abnormal-row" if is_abn else ""
        html_content += f"<tr class='{row_class}'><td style='text-align: left;'>{row[0][0]}</td><td>{row[1][0]}</td><td style='text-align: left;'>{row[2][0]}</td></tr>"
    html_content += "</tbody></table></div>"
    return html_content

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

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
    """Renders the urinalysis section and returns a summary."""
    urine_data = [("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"), ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"), ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"), ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"), ("อื่นๆ", person_data.get("ORTER", "-"), "-")]
    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    html_content = render_lab_table_html("ผลการตรวจปัสสาวะ (Urinalysis)", ["การตรวจ", "ผล", "ค่าปกติ"], [[(row["การตรวจ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (safe_value(row["ผลตรวจ"]), is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (row["ค่าปกติ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"]))] for _, row in df_urine.iterrows()], table_class="lab-table")
    st.markdown(html_content, unsafe_allow_html=True)
    return any(not is_empty(val) for _, val, _ in urine_data)

def interpret_stool_exam(val):
    """Interprets stool examination results."""
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val
def interpret_stool_cs(value):
    """Interprets stool culture and sensitivity results."""
    if is_empty(value): return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
    """Renders a self-contained HTML table for stool examination results."""
    html_content = f"""
    <div class="table-container">
        <table class="info-detail-table">
            <tbody>
                <tr>
                    <th>ผลตรวจอุจจาระทั่วไป</th>
                    <td>{exam}</td>
                </tr>
                <tr>
                    <th>ผลตรวจอุจจาระเพาะเชื้อ</th>
                    <td>{cs}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    return html_content

def get_ekg_col_name(year):
    """Gets the correct EKG column name based on the year."""
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"
def interpret_ekg(val):
    """Interprets EKG results."""
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    """Generates advice based on Hepatitis B panel results and returns a status."""
    hbsag, hbsab, hbcab = hbsag.lower(), hbsab.lower(), hbcab.lower()
    if "positive" in hbsag:
        return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab and "positive" not in hbsag:
        return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab and "positive" not in hbsab:
        return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]):
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

# --- Data Availability Checkers (ย้ายมาจาก app.py) ---
def has_basic_health_data(person_data):
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_vision_data(person_data):
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ', 'ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล',
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)',
        'ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ', 'ป.การจำแนกสี', 'ผ.การจำแนกสี',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน',
        'ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้', 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)',
        'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน',
        'ป.ลานสายตา', 'ผ.ลานสายตา', 'ผ.สายตาเขซ่อนเร้น'
    ]
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
    hearing_keys = [ 'R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k' ]
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_visualization_data(history_df):
    """Check if there is enough data to show visualizations (at least 1 year)."""
    return history_df is not None and not history_df.empty


# --- UI and Report Rendering Functions (ย้ายมาจาก app.py) ---
def interpret_bp(sbp, dbp):
    """Interprets blood pressure readings."""
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
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def interpret_bmi(bmi):
    """Interprets BMI value and returns a description string."""
    if bmi is None:
        return ""
    if bmi < 18.5:
        return "น้ำหนักน้อยกว่าเกณฑ์"
    elif 18.5 <= bmi < 23:
        return "น้ำหนักปกติ"
    elif 23 <= bmi < 25:
        return "น้ำหนักเกิน (ท้วม)"
    elif 25 <= bmi < 30:
        return "เข้าเกณฑ์โรคอ้วน"
    elif bmi >= 30:
        return "เข้าเกณฑ์โรคอ้วนอันตราย"
    return ""

def display_common_header(person_data):
    """Displays the new report header with integrated personal info and vitals cards."""
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
        bmi_val_str = f"{bmi:.1f} kg/m²"
        bmi_desc = interpret_bmi(bmi)

    st.markdown(f"""
    <div class="report-header">
        <div class="header-left">
            <h2>รายงานผลการตรวจสุขภาพ</h2>
            <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
            <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        </div>
        <div class="header-right">
            <div class="info-card">
                <div class="info-card-item"><span>ชื่อ-สกุล:</span> {name}</div>
                <div class="info-card-item"><span>HN:</span> {hn}</div>
                <div class="info-card-item"><span>อายุ:</span> {age} ปี</div>
                <div class="info-card-item"><span>เพศ:</span> {sex}</div>
                <div class="info-card-item"><span>หน่วยงาน:</span> {department}</div>
                <div class="info-card-item"><span>วันที่ตรวจ:</span> {check_date}</div>
            </div>
        </div>
    </div>

    <div class="vitals-grid">
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">น้ำหนัก / ส่วนสูง</span>
                <span class="vital-value">{weight_val} kg / {height_val} cm</span>
                <span class="vital-sub-value">BMI: {bmi_val_str} ({bmi_desc})</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">รอบเอว</span>
                <span class="vital-value">{waist_val} cm</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">ความดัน (mmHg)</span>
                <span class="vital-value">{bp_val}</span>
                <span class="vital-sub-value">{bp_desc}</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">ชีพจร (BPM)</span>
                <span class="vital-value">{pulse_val}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        :root {
            --abnormal-bg-color: rgba(220, 53, 69, 0.1);
            --abnormal-text-color: #C53030;
            --normal-bg-color: rgba(40, 167, 69, 0.1);
            --normal-text-color: #1E4620;
            --warning-bg-color: rgba(255, 193, 7, 0.1);
            --neutral-bg-color: rgba(108, 117, 125, 0.1);
            --neutral-text-color: #4A5568;
        }
        
        html, body, [class*="st-"], .st-emotion-cache-10trblm, h1, h2, h3, h4, h5, h6 {
            font-family: 'Sarabun', sans-serif !important;
        }
        .main {
             background-color: var(--background-color);
             color: var(--text-color);
        }
        h4 {
            font-size: 1.25rem;
            font-weight: 600;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            margin-top: 40px;
            margin-bottom: 24px;
            color: var(--text-color);
        }
        h5.section-subtitle {
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--text-color);
            opacity: 0.7;
        }

        [data-testid="stSidebar"] {
            background-color: var(--secondary-background-color);
        }
        [data-testid="stSidebar"] .stTextInput input {
            border-color: var(--border-color);
        }
        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 1rem;
        }
        .stButton>button {
            background-color: #00796B;
            color: white !important;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            width: 100%;
            padding: 0.5rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            transition: background-color 0.2s, transform 0.2s;
        }
        .stButton>button:hover {
            background-color: #00695C;
            color: white !important;
            transform: translateY(-1px);
        }
        .stButton>button:disabled {
            background-color: #BDBDBD;
            color: #757575 !important;
            opacity: 1;
            border: none;
            box-shadow: none;
            cursor: not-allowed;
        }

        .report-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; }
        .header-left h2 { color: var(--text-color); font-size: 2rem; margin-bottom: 0.25rem;}
        .header-left p { color: var(--text-color); opacity: 0.7; margin: 0; }
        .info-card { background-color: var(--secondary-background-color); border-radius: 8px; padding: 1rem; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem 1.5rem; min-width: 400px; border: 1px solid var(--border-color); }
        .info-card-item { font-size: 0.9rem; color: var(--text-color); }
        .info-card-item span { color: var(--text-color); opacity: 0.7; margin-right: 8px; }

        .vitals-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .vital-card { background-color: var(--secondary-background-color); border-radius: 12px; padding: 1rem; display: flex; align-items: center; gap: 1rem; border: 1px solid var(--border-color); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); }
        .vital-icon svg { color: var(--primary-color); }
        .vital-data { display: flex; flex-direction: column; }
        .vital-label { font-size: 0.8rem; color: var(--text-color); opacity: 0.7; }
        .vital-value { font-size: 1.2rem; font-weight: 700; color: var(--text-color); line-height: 1.2; white-space: nowrap;}
        .vital-sub-value { font-size: 0.8rem; color: var(--text-color); opacity: 0.6; }

        div[data-testid="stTabs"] { border-bottom: 2px solid var(--border-color); }
        div[data-testid="stTabs"] button { background-color: transparent; color: var(--text-color); opacity: 0.7; border-radius: 8px 8px 0 0; margin: 0; padding: 10px 20px; border: none; border-bottom: 2px solid transparent; }
        div[data-testid="stTabs"] button[aria-selected="true"] { background-color: var(--secondary-background-color); color: var(--primary-color); font-weight: 600; opacity: 1; border: 2px solid var(--border-color); border-bottom: 2px solid var(--secondary-background-color); margin-bottom: -2px; }
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div.st-emotion-cache-1jicfl2.e1f1d6gn3 > div { background-color: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); }

        .table-container { overflow-x: auto; }
        .lab-table, .info-detail-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .lab-table th, .lab-table td, .info-detail-table th, .info-detail-table td { padding: 12px 15px; border: 1px solid transparent; border-bottom: 1px solid var(--border-color); }
        .lab-table th, .info-detail-table th { font-weight: 600; text-align: left; color: var(--text-color); opacity: 0.7; }
        .lab-table thead th { background-color: rgba(128, 128, 128, 0.1); }
        .lab-table td:nth-child(2) { text-align: center; }
        .lab-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
        .lab-table .abnormal-row { background-color: var(--abnormal-bg-color); color: var(--abnormal-text-color); font-weight: 600; }
        .info-detail-table th { width: 35%; }
        
        .recommendation-container { border-left: 5px solid var(--primary-color); padding: 1.5rem; border-radius: 0 8px 8px 0; background-color: var(--background-color); }
        .recommendation-container ul { padding-left: 20px; }
        .recommendation-container li { margin-bottom: 0.5rem; }

        .status-summary-card { padding: 1rem; border-radius: 8px; text-align: center; height: 100%; }
        .status-normal-bg { background-color: var(--normal-bg-color); }
        .status-abnormal-bg { background-color: var(--abnormal-bg-color); }
        .status-warning-bg { background-color: var(--warning-bg-color); }
        .status-neutral-bg { background-color: var(--neutral-bg-color); }

        .status-summary-card p { margin: 0; color: var(--text-color); }
        .vision-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 1.5rem; }
        .vision-table th, .vision-table td { border: 1px solid var(--border-color); padding: 10px; text-align: left; vertical-align: middle; }
        .vision-table th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; }
        .vision-table .result-cell { text-align: center; width: 180px; }
        .vision-result { display: inline-block; padding: 6px 16px; border-radius: 16px; font-size: 13px; font-weight: bold; border: 1px solid transparent; }
        .vision-normal { background-color: var(--normal-bg-color); color: #2E7D32; }
        .vision-abnormal { background-color: var(--abnormal-bg-color); color: #C62828; }
        .vision-not-tested { background-color: var(--neutral-bg-color); color: #455A64; }
        .styled-df-table { width: 100%; border-collapse: collapse; font-family: 'Sarabun', sans-serif !important; font-size: 14px; }
        .styled-df-table th, .styled-df-table td { border: 1px solid var(--border-color); padding: 10px; text-align: left; }
        .styled-df-table thead th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; text-align: center; vertical-align: middle; }
        .styled-df-table tbody td { text-align: center; }
        .styled-df-table tbody td:first-child { text-align: left; }
        .styled-df-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
        .hearing-table { table-layout: fixed; }
        
        .custom-advice-box { padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid transparent; font-weight: 600; }
        .immune-box { background-color: var(--normal-bg-color); color: #2E7D32; border-color: rgba(40, 167, 69, 0.2); }
        .no-immune-box { background-color: var(--abnormal-bg-color); color: #C62828; border-color: rgba(220, 53, 69, 0.2); }
        .warning-box { background-color: var(--warning-bg-color); color: #AF6C00; border-color: rgba(255, 193, 7, 0.2); }
    </style>
    """, unsafe_allow_html=True)

# --- Functions for displaying specific report sections ---
# (ใส่โค้ดของ display_main_report, display_performance_report และส่วนอื่นๆ ที่เกี่ยวข้องที่นี่)
# ... (โค้ดของ display_main_report และ display_performance_report ไม่ได้แสดงเพื่อความกระชับ) ...

def render_vision_details_table(person_data):
    # ... (โค้ดของ render_vision_details_table) ...
    pass # Placeholder

def display_performance_report_hearing(person_data, all_person_history_df):
    # ... (โค้ดของ display_performance_report_hearing) ...
    pass # Placeholder

def display_performance_report_lung(person_data):
    # ... (โค้ดของ display_performance_report_lung) ...
    pass # Placeholder

def display_performance_report_vision(person_data):
    # ... (โค้ดของ display_performance_report_vision) ...
    pass # Placeholder

def display_performance_report(person_data, report_type, all_person_history_df=None):
    with st.container(border=True):
        if report_type == 'lung':
            display_performance_report_lung(person_data)
        elif report_type == 'vision':
            display_performance_report_vision(person_data)
        elif report_type == 'hearing':
            display_performance_report_hearing(person_data, all_person_history_df)

def display_main_report(person_data, all_person_history_df):
    # ... (โค้ดส่วนใหญ่ของ display_main_report ถูกย้ายไป shared_ui.py) ...
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]

    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]

    with st.container(border=True):
        render_section_header("ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)")
        col1, col2 = st.columns(2)
        with col1: st.markdown(render_lab_table_html("ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
        with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    selected_year = person.get("Year", datetime.now().year + 543)

    with st.container(border=True):
        render_section_header("ผลการตรวจอื่นๆ (Other Examinations)")
        col_ua_left, col_ua_right = st.columns(2)
        with col_ua_left:
            render_urine_section(person, sex, selected_year)
            st.markdown("<h5 class='section-subtitle'>ผลตรวจอุจจาระ (Stool Examination)</h5>", unsafe_allow_html=True)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)

        with col_ua_right:
            st.markdown("<h5 class='section-subtitle'>ผลตรวจพิเศษ</h5>", unsafe_allow_html=True)
            cxr_col = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            ekg_col_name = get_ekg_col_name(selected_year)
            hep_a_value = person.get("Hepatitis A")
            hep_a_display_text = "ไม่ได้ตรวจ" if is_empty(hep_a_value) else safe_text(hep_a_value)

            st.markdown(f"""
            <div class="table-container">
                <table class="info-detail-table">
                    <tbody>
                        <tr><th>ผลเอกซเรย์ (Chest X-ray)</th><td>{interpret_cxr(person.get(cxr_col, ''))}</td></tr>
                        <tr><th>ผลคลื่นไฟฟ้าหัวใจ (EKG)</th><td>{interpret_ekg(person.get(ekg_col_name, ''))}</td></tr>
                        <tr><th>ไวรัสตับอักเสบเอ (Hepatitis A)</th><td>{hep_a_display_text}</td></tr>
                    </tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<h5 class='section-subtitle'>ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)</h5>", unsafe_allow_html=True)
            hbsag, hbsab, hbcab = safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB"))
            st.markdown(f"""<div class="table-container"><table class='lab-table'>
                <thead><tr><th style='text-align: center;'>HBsAg</th><th style='text-align: center;'>HBsAb</th><th style='text-align: center;'>HBcAb</th></tr></thead>
                <tbody><tr><td style='text-align: center;'>{hbsag}</td><td style='text-align: center;'>{hbsab}</td><td style='text-align: center;'>{hbcab}</td></tr></tbody>
            </table></div>""", unsafe_allow_html=True)

            if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)):
                advice, status = hepatitis_b_advice(hbsag, hbsab, hbcab)
                status_class = ""
                if status == 'immune':
                    status_class = 'immune-box'
                elif status == 'no_immune':
                    status_class = 'no-immune-box'
                else: # infection or unclear
                    status_class = 'warning-box'

                st.markdown(f"""
                <div class'custom-advice-box {status_class}'>
                    {advice}
                </div>
                """, unsafe_allow_html=True)

    with st.container(border=True):
        render_section_header("สรุปและคำแนะนำการปฏิบัติตัว (Summary & Recommendations)")
        recommendations_html = generate_comprehensive_recommendations(person_data)
        st.markdown(f"<div class='recommendation-container'>{recommendations_html}</div>", unsafe_allow_html=True)



# --- Main Application Logic Wrapper ---
def main_app(df):
    """
    This function contains the main application logic for displaying health reports.
    It's called after the user has successfully logged in and accepted the PDPA consent.
    """
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

    inject_custom_css()

    if 'user_hn' not in st.session_state:
        st.error("เกิดข้อผิดพลาด: ไม่พบข้อมูลผู้ใช้")
        st.stop()

    user_hn = st.session_state['user_hn']
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    def handle_year_change():
        st.session_state.selected_year = st.session_state.year_select
        st.session_state.selected_date = None
        st.session_state.pop("person_row", None)
        st.session_state.pop("selected_row_found", None)

    if 'selected_year' not in st.session_state: st.session_state.selected_year = None
    if 'print_trigger' not in st.session_state: st.session_state.print_trigger = False
    if 'print_performance_trigger' not in st.session_state: st.session_state.print_performance_trigger = False

    with st.sidebar:
        st.markdown(f"<div class='sidebar-title'>ยินดีต้อนรับ</div><h3>{st.session_state.get('user_name', '')}</h3>", unsafe_allow_html=True)
        st.markdown(f"**HN:** {st.session_state.get('user_hn', '')}")
        st.markdown("---")
        
        if not results_df.empty:
            available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
            if available_years:
                if st.session_state.selected_year not in available_years:
                    st.session_state.selected_year = available_years[0]
                
                year_idx = available_years.index(st.session_state.selected_year)
                st.selectbox("เลือกปี พ.ศ. ที่ต้องการดูผลตรวจ", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change)
            
                person_year_df = results_df[results_df["Year"] == st.session_state.selected_year]

                if not person_year_df.empty:
                    merged_series = person_year_df.bfill().ffill().iloc[0]
                    st.session_state.person_row = merged_series.to_dict()
                    st.session_state.selected_row_found = True
                else:
                     st.session_state.pop("person_row", None)
                     st.session_state.pop("selected_row_found", None)
        
        st.markdown("---")
        st.markdown('<div class="sidebar-title" style="font-size: 1.2rem; margin-top: 1rem;">พิมพ์รายงาน</div>', unsafe_allow_html=True)
        if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
            if st.button("พิมพ์รายงานสุขภาพ", use_container_width=True):
                 st.session_state.print_trigger = True
            if st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True):
                st.session_state.print_performance_trigger = True
        else:
            st.button("พิมพ์รายงานสุขภาพ", use_container_width=True, disabled=True)
            st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True, disabled=True)

        st.markdown("---")
        if st.button("ออกจากระบบ (Logout)", use_container_width=True):
            keys_to_clear = [
                'authenticated', 'pdpa_accepted', 'user_hn', 'user_name',
                'search_result', 'selected_year', 'person_row', 
                'selected_row_found', 'auth_step', 'is_admin'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # --- Main Page Content ---
    if "person_row" not in st.session_state or not st.session_state.get("selected_row_found", False):
        st.info("กรุณาเลือกปีที่ต้องการดูผลตรวจจากเมนูด้านข้าง")
    else:
        person_data = st.session_state.person_row
        all_person_history_df = st.session_state.search_result
        
        available_reports = OrderedDict()
        if has_visualization_data(all_person_history_df): available_reports['ภาพรวมสุขภาพ (Graphs)'] = 'visualization_report'
        if has_basic_health_data(person_data): available_reports['สุขภาพพื้นฐาน'] = 'main_report'
        if has_vision_data(person_data): available_reports['สมรรถภาพการมองเห็น'] = 'vision_report'
        if has_hearing_data(person_data): available_reports['สมรรถภาพการได้ยิน'] = 'hearing_report'
        if has_lung_data(person_data): available_reports['สมรรถภาพปอด'] = 'lung_report'
        
        if not available_reports:
            display_common_header(person_data)
            st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับปีที่เลือก")
        else:
            display_common_header(person_data)
            tabs = st.tabs(list(available_reports.keys()))
        
            for i, (tab_title, page_key) in enumerate(available_reports.items()):
                with tabs[i]:
                    if page_key == 'visualization_report':
                        display_visualization_tab(person_data, all_person_history_df)
                    elif page_key == 'vision_report':
                        display_performance_report(person_data, 'vision')
                    elif page_key == 'hearing_report':
                        display_performance_report(person_data, 'hearing', all_person_history_df=all_person_history_df)
                    elif page_key == 'lung_report':
                        display_performance_report(person_data, 'lung')
                    elif page_key == 'main_report':
                        display_main_report(person_data, all_person_history_df)

        # --- Print Logic ---
        if st.session_state.get("print_trigger", False):
            report_html_data = generate_printable_report(person_data, all_person_history_df)
            escaped_html = json.dumps(report_html_data)
            iframe_id = f"print-iframe-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            print_component = f"""
            <iframe id="{iframe_id}" style="display:none;"></iframe>
            <script>
                (function() {{ /* Print logic */ }})();
            </script>
            """ # Simplified for brevity
            st.components.v1.html(print_component, height=0, width=0)
            st.session_state.print_trigger = False

        if st.session_state.get("print_performance_trigger", False):
            report_html_data = generate_performance_report_html(person_data, all_person_history_df)
            escaped_html = json.dumps(report_html_data)
            iframe_id = f"print-perf-iframe-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            print_component = f"""
            <iframe id="{iframe_id}" style="display:none;"></iframe>
            <script>
                (function() {{ /* Print performance logic */ }})();
            </script>
            """ # Simplified for brevity
            st.components.v1.html(print_component, height=0, width=0)
            st.session_state.print_performance_trigger = False

# --- Main Logic to control page flow ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state:
    st.session_state['pdpa_accepted'] = False

df = load_sqlite_data()
if df is None:
    st.error("ไม่สามารถโหลดฐานข้อมูลได้ กรุณาลองอีกครั้งในภายหลัง")
    st.stop()

if not st.session_state['authenticated']:
    authentication_flow(df)
elif not st.session_state['pdpa_accepted']:
    if st.session_state.get('is_admin', False):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
    else:
        pdpa_consent_page()
else:
    if st.session_state.get('is_admin', False):
        display_admin_panel(df)
    else:
        main_app(df)

"
