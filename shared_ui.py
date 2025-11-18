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
# --- START: Removed circular imports ---
# from print_report import generate_printable_report # <--- ลบออก
# from print_performance_report import generate_performance_report_html # <--- ลบออก
# from visualization import display_visualization_tab # <--- ลบออก
# --- END: Removed circular imports ---

# --- Helper Functions (ย้ายมาจาก app.py) ---
def is_empty(val):
# ... existing code ...
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
# ... existing code ...
    """จัดการการเว้นวรรคในชื่อ-นามสกุลที่ไม่สม่ำเสมอ"""
    if is_empty(name):
        return ""
    return re.sub(r'\s+', '', str(name).strip())

def get_float(col, person_data):
# ... existing code ...
    """Safely gets a float value from person_data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
# ... existing code ...
    """Formats a lab value and flags it if it's abnormal."""
    try:
        val = float(str(val).replace(",", "").strip())
    except: return "-", False
# ... existing code ...
    return formatted_val, is_abnormal

def render_section_header(title):
# ... existing code ...
    """Renders a new, modern section header."""
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table"):
# ... existing code ...
    """Generates HTML for a lab result table with a new header style."""
    header_html = f"<h5 class='section-subtitle'>{title}</h5>"
    html_content = f"{header_html}<div class='table-container'><table class='{table_class}'><colgroup><col style='width:40%;'><col style='width:20%;'><col style='width:40%;'></colgroup><thead><tr>"
# ... existing code ...
    html_content += "</tbody></table></div>"
    return html_content

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
# ... existing code ...
def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

def parse_range_or_number(val):
# ... existing code ...
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val: return map(float, val.split("-"))
# ... existing code ...
        else: num = float(val); return num, num
    except: return None, None

def interpret_rbc(value):
# ... existing code ...
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
# ... existing code ...
    if high is None: return value
    if high <= 2: return "ปกติ"
    if high <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
# ... existing code ...
    return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    val = str(value or "").strip().lower()
# ... existing code ...
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
# ... existing code ...
    if high <= 5: return "ปกติ"
    if high <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
# ... existing code ...
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]: return False
    if test_name == "กรด-ด่าง (pH)":
# ... existing code ...
        try: return not (5.0 <= float(val) <= 8.0)
        except: return True
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try: return not (1.003 <= float(val) <= 1.030)
# ... existing code ...
        except: return True
    if test_name == "เม็ดเลือดแดง (RBC)": return "พบ" in interpret_rbc(val).lower()
    if test_name == "เม็ดเลือดขาว (WBC)": return "พบ" in interpret_wbc(val).lower()
# ... existing code ...
    if test_name == "น้ำตาล (Sugar)": return val.lower() not in ["negative"]
    if test_name == "โปรตีน (Albumin)": return val.lower() not in ["negative", "trace"]
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
# ... existing code ...
    return False

def render_urine_section(person_data, sex, year_selected):
    """Renders the urinalysis section and returns a summary."""
# ... existing code ...
    urine_data = [("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"), ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"), ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"), ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"), ("อื่นๆ", person_data.get("ORTER", "-"), "-")]
    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    html_content = render_lab_table_html("ผลการตรวจปัสสาวะ (Urinalysis)", ["การตรวจ", "ผล", "ค่าปกติ"], [[(row["การตรวจ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (safe_value(row["ผลตรวจ"]), is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (row["ค่าปกติ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"]))] for _, row in df_urine.iterrows()], table_class="lab-table")
    st.markdown(html_content, unsafe_allow_html=True)
# ... existing code ...
    return any(not is_empty(val) for _, val, _ in urine_data)

def interpret_stool_exam(val):
    """Interprets stool examination results."""
# ... existing code ...
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
# ... existing code ...
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val
def interpret_stool_cs(value):
# ... existing code ...
    """Interprets stool culture and sensitivity results."""
    if is_empty(value): return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
# ... existing code ...
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
# ... existing code ...
    """Renders a self-contained HTML table for stool examination results."""
    html_content = f"""
    <div class="table-container">
        <table class="info-detail-table">
# ... existing code ...
                <tr>
                    <th>ผลตรวจอุจจาระทั่วไป</th>
                    <td>{exam}</td>
                </tr>
                <tr>
# ... existing code ...
                    <th>ผลตรวจอุจจาระเพาะเชื้อ</th>
                    <td>{cs}</td>
                </tr>
            </tbody>
# ... existing code ...
        </table>
    </div>
    """
    return html_content
# ... existing code ...

def get_ekg_col_name(year):
    """Gets the correct EKG column name based on the year."""
    current_thai_year = datetime.now().year + 543
# ... existing code ...
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"
def interpret_ekg(val):
    """Interprets EKG results."""
# ... existing code ...
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
# ... existing code ...
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
# ... existing code ...
    """Generates advice based on Hepatitis B panel results and returns a status."""
    hbsag, hbsab, hbcab = hbsag.lower(), hbsab.lower(), hbcab.lower()
    if "positive" in hbsag:
# ... existing code ...
        return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab and "positive" not in hbsag:
        return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
# ... existing code ...
    if "positive" in hbcab and "positive" not in hbsab:
        return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]):
# ... existing code ...
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

# --- Data Availability Checkers (ย้ายมาจาก app.py) ---
# ... existing code ...
def has_basic_health_data(person_data):
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_vision_data(person_data):
# ... existing code ...
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ', 'ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล',
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)',
# ... existing code ...
        'ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ', 'ป.การจำแนกสี', 'ผ.การจำแนกสี',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน',
        'ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้', 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)',
# ... existing code ...
        'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน',
        'ป.ลานสายตา', 'ผ.ลานสายตา', 'ผ.สายตาเขซ่อนเร้น'
    ]
# ... existing code ...
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
    hearing_keys = [ 'R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k' ]
# ... existing code ...
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
# ... existing code ...
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_visualization_data(history_df):
# ... existing code ...
    """Check if there is enough data to show visualizations (at least 1 year)."""
    return history_df is not None and not history_df.empty


# --- UI and Report Rendering Functions (ย้ายมาจาก app.py) ---
# ... existing code ...
def interpret_bp(sbp, dbp):
    """Interprets blood pressure readings."""
    try:
# ... existing code ...
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
# ... existing code ...
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"
# ... existing code ...
    except: return "-"

def interpret_cxr(val):
    val = str(val or "").strip()
# ... existing code ...
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val
# ... existing code ...

def interpret_bmi(bmi):
    """Interprets BMI value and returns a description string."""
# ... existing code ...
    if bmi is None:
        return ""
    if bmi < 18.5:
# ... existing code ...
        return "น้ำหนักน้อยกว่าเกณฑ์"
    elif 18.5 <= bmi < 23:
        return "น้ำหนักปกติ"
    elif 23 <= bmi < 25:
# ... existing code ...
        return "น้ำหนักเกิน (ท้วม)"
    elif 25 <= bmi < 30:
        return "เข้าเกณฑ์โรคอ้วน"
    elif bmi >= 30:
# ... existing code ...
        return "เข้าเกณฑ์โรคอ้วนอันตราย"
    return ""

def display_common_header(person_data):
# ... existing code ...
    """Displays the new report header with integrated personal info and vitals cards."""
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
# ... existing code ...
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
# ... existing code ...
    check_date = person_data.get("วันที่ตรวจ", "-")
    
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
# ... existing code ...
        bp_val = f"{sbp_int}/{dbp_int}"
        bp_desc = interpret_bp(sbp_int, dbp_int)
    except:
        bp_val = "-"
# ... existing code ...
        bp_desc = "ไม่มีข้อมูล"

    try: pulse_val = f"{int(float(person_data.get('pulse', '-')))}"
    except: pulse_val = "-"
# ... existing code ...

    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight}" if weight is not None else "-"
# ... existing code ...
    height_val = f"{height}" if height is not None else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')}"

    bmi_val_str = "-"
# ... existing code ...
    bmi_desc = ""
    if weight is not None and height is not None and height > 0:
        bmi = weight / ((height / 100) ** 2)
        bmi_val_str = f"{bmi:.1f} kg/m²"
# ... existing code ...
        bmi_desc = interpret_bmi(bmi)

    st.markdown(f"""
    <div class="report-header">
# ... existing code ...
        <div class="header-left">
            <h2>รายงานผลการตรวจสุขภาพ</h2>
            <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
# ... existing code ...
            <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        </div>
        <div class="header-right">
            <div class="info-card">
# ... existing code ...
                <div class="info-card-item"><span>ชื่อ-สกุล:</span> {name}</div>
                <div class="info-card-item"><span>HN:</span> {hn}</div>
                <div class="info-card-item"><span>อายุ:</span> {age} ปี</div>
# ... existing code ...
                <div class="info-card-item"><span>เพศ:</span> {sex}</div>
                <div class="info-card-item"><span>หน่วยงาน:</span> {department}</div>
                <div class="info-card-item"><span>วันที่ตรวจ:</span> {check_date}</div>
# ... existing code ...
            </div>
        </div>
    </div>
# ... existing code ...

    <div class="vitals-grid">
        <div class="vital-card">
            <div class="vital-icon">
# ... existing code ...
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">น้ำหนัก / ส่วนสูง</span>
# ... existing code ...
                <span class="vital-value">{weight_val} kg / {height_val} cm</span>
                <span class="vital-sub-value">BMI: {bmi_val_str} ({bmi_desc})</span>
            </div>
# ... existing code ...
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
# ... existing code ...
            </div>
            <div class="vital-data">
                <span class="vital-label">รอบเอว</span>
                <span class="vital-value">{waist_val} cm</span>
# ... existing code ...
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
# ... existing code ...
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">ความดัน (mmHg)</span>
# ... existing code ...
                <span class="vital-value">{bp_val}</span>
                <span class="vital-sub-value">{bp_desc}</span>
            </div>
# ... existing code ...
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
# ... existing code ...
            </div>
            <div class="vital-data">
                <span class="vital-label">ชีพจร (BPM)</span>
                <span class="vital-value">{pulse_val}</span>
# ... existing code ...
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
# ... existing code ...

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
# ... existing code ...
        :root {
            --abnormal-bg-color: rgba(220, 53, 69, 0.1);
            --abnormal-text-color: #C53030;
# ... existing code ...
            --normal-bg-color: rgba(40, 167, 69, 0.1);
            --normal-text-color: #1E4620;
            --warning-bg-color: rgba(255, 193, 7, 0.1);
# ... existing code ...
            --neutral-bg-color: rgba(108, 117, 125, 0.1);
            --neutral-text-color: #4A5568;
        }
        
# ... existing code ...
        html, body, [class*="st-"], .st-emotion-cache-10trblm, h1, h2, h3, h4, h5, h6 {
            font-family: 'Sarabun', Arial, sans-serif !important; /* สำหรับเนื้อหาหลัก */
        }

        /* --- START: (*** นี่คือจุดที่แก้ไข ***) --- */
        /*
         * (แก้ไขครั้งที่ 4 - ใช้วิธีที่ก้าวร้าวมากขึ้น)
         * ซ่อน *เนื้อหา* ของไอคอนทั้งหมด และแทนที่ด้วย pseudo-element
         */

        /* 1. ซ่อนเนื้อหา (text node) ที่เสียของตัวไอคอน */
        /* ใช้ font-size: 0 เพื่อซ่อนข้อความ 'keyboard_arrow...' */
        [data-testid="stExpanderIcon"],
        [data-testid="stSidebarCollapseButton"]
        {
            font-size: 0 !important; /* ซ่อนข้อความ text node */
            line-height: 0 !important;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            position: relative;
            width: 1.5rem;
            height: 1.5rem;
        }

        /* 2. สร้าง '::before' pseudo-element เพื่อใส่สัญลักษณ์ใหม่ */
        [data-testid="stExpanderIcon"]::before,
        [data-testid="stSidebarCollapseButton"]::before
        {
            position: absolute;
            font-family: 'Sarabun', Arial, sans-serif !important;
            font-weight: bold;
            color: currentColor;
            line-height: 1;
        }

        /* 3. กำหนดสัญลักษณ์สำหรับ Expander (ปุ่มย่อ-ขยาย) */
        
        /* 3.1 สัญลักษณ์เมื่อ Expander 'ปิด' */
        [data-testid="stExpander"][aria-expanded="false"] [data-testid="stExpanderIcon"]::before {
            content: '+';
            font-size: 1.5rem; /* 24px */
        }
        
        /* 3.2 สัญลักษณ์เมื่อ Expander 'เปิด' */
        [data-testid="stExpander"][aria-expanded="true"] [data-testid="stExpanderIcon"]::before {
            content: '−'; /* Minus Sign U+2212 */
            font-size: 1.5rem; /* 24px */
        }
        
        /* 4. กำหนดสัญลักษณ์สำหรับ Sidebar (ปุ่มพับ) */
        
        /* 4.1 สัญลักษณ์เมื่อ Sidebar 'เปิด' */
        [data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"]::before {
            content: '<';
            font-size: 2rem; /* 32px */
            font-weight: 300;
        }
        
        /* 4.2 สัญลักษณ์เมื่อ Sidebar 'ปิด' */
        [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"]::before {
            content: '>';
            font-size: 2rem; /* 32px */
            font-weight: 300;
        }
        
        /* 5. แก้ไขไอคอนทั่วไป (stIcon) - คงไว้เผื่อไอคอนอื่น */
        [data-testid="stIcon"] span
        {
           font-family: 'Material Icons', Arial, sans-serif !important;
           font-weight: normal !important;
           font-style: normal !important;
           font-size: 24px !important; /* บังคับขนาดฟอนต์ */
           line-height: 1 !important;
           letter-spacing: normal !important;
           text-transform: none !important;
           display: inline-block !important;
           white-space: nowrap !important;
           word-wrap: normal !important;
           direction: ltr !important;
           -webkit-font-feature-settings: 'liga' !important;
           -webkit-font-smoothing: antialiased !important;
        }

        /* --- END: (*** นี่คือจุดที่แก้ไข ***) --- */
        
        .main {
# ... existing code ...
             background-color: var(--background-color);
             color: var(--text-color);
        }
        h4 {
# ... existing code ...
            font-size: 1.25rem;
            font-weight: 600;
            border-bottom: 2px solid var(--border-color);
# ... existing code ...
            padding-bottom: 10px;
            margin-top: 40px;
            margin-bottom: 24px;
# ... existing code ...
            color: var(--text-color);
        }
        h5.section-subtitle {
            font-weight: 600;
# ... existing code ...
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--text-color);
            opacity: 0.7;
# ... existing code ...
        }

        [data-testid="stSidebar"] {
            background-color: var(--secondary-background-color);
# ... existing code ...
        }
        [data-testid="stSidebar"] .stTextInput input {
            border-color: var(--border-color);
        }
# ... existing code ...
        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 700;
# ... existing code ...
            color: var(--primary-color);
            margin-bottom: 1rem;
        }
        .stButton>button {
# ... existing code ...
            background-color: #00796B;
            color: white !important;
            border-radius: 8px;
# ... existing code ...
            border: none;
            font-weight: 600;
            width: 100%;
            padding: 0.5rem;
# ... existing code ...
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            transition: background-color 0.2s, transform 0.2s;
        }
        .stButton>button:hover {
# ... existing code ...
            background-color: #00695C;
            color: white !important;
            transform: translateY(-1px);
        }
# ... existing code ...
        .stButton>button:disabled {
            background-color: #BDBDBD;
            color: #757575 !important;
            opacity: 1;
# ... existing code ...
            border: none;
            box-shadow: none;
            cursor: not-allowed;
        }
# ... existing code ...

        .report-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; }
        .header-left h2 { color: var(--text-color); font-size: 2rem; margin-bottom: 0.25rem;}
# ... existing code ...
        .header-left p { color: var(--text-color); opacity: 0.7; margin: 0; }
        .info-card { background-color: var(--secondary-background-color); border-radius: 8px; padding: 1rem; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem 1.5rem; min-width: 400px; border: 1px solid var(--border-color); }
        .info-card-item { font-size: 0.9rem; color: var(--text-color); }
# ... existing code ...
        .info-card-item span { color: var(--text-color); opacity: 0.7; margin-right: 8px; }

        .vitals-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .vital-card { background-color: var(--secondary-background-color); border-radius: 12px; padding: 1rem; display: flex; align-items: center; gap: 1rem; border: 1px solid var(--border-color); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); }
# ... existing code ...
        .vital-icon svg { color: var(--primary-color); }
        .vital-data { display: flex; flex-direction: column; }
        .vital-label { font-size: 0.8rem; color: var(--text-color); opacity: 0.7; }
# ... existing code ...
        .vital-value { font-size: 1.2rem; font-weight: 700; color: var(--text-color); line-height: 1.2; white-space: nowrap;}
        .vital-sub-value { font-size: 0.8rem; color: var(--text-color); opacity: 0.6; }

        div[data-testid="stTabs"] { border-bottom: 2px solid var(--border-color); }
# ... existing code ...
        div[data-testid="stTabs"] button { background-color: transparent; color: var(--text-color); opacity: 0.7; border-radius: 8px 8px 0 0; margin: 0; padding: 10px 20px; border: none; border-bottom: 2px solid transparent; }
        div[data-testid="stTabs"] button[aria-selected="true"] { background-color: var(--secondary-background-color); color: var(--primary-color); font-weight: 600; opacity: 1; border: 2px solid var(--border-color); border-bottom: 2px solid var(--secondary-background-color); margin-bottom: -2px; }
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div.st-emotion-cache-1jicfl2.e1f1d6gn3 > div { background-color: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); }
# ... existing code ...

        .table-container { overflow-x: auto; }
        .lab-table, .info-detail-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .lab-table th, .lab-table td, .info-detail-table th, .info-detail-table td { padding: 12px 15px; border: 1px solid transparent; border-bottom: 1px solid var(--border-color); }
# ... existing code ...
        .lab-table th, .info-detail-table th { font-weight: 600; text-align: left; color: var(--text-color); opacity: 0.7; }
        .lab-table thead th { background-color: rgba(128, 128, 128, 0.1); }
        .lab-table td:nth-child(2) { text-align: center; }
# ... existing code ...
        .lab-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
        .lab-table .abnormal-row { background-color: var(--abnormal-bg-color); color: var(--abnormal-text-color); font-weight: 600; }
        .info-detail-table th { width: 35%; }
# ... existing code ...
        
        .recommendation-container { border-left: 5px solid var(--primary-color); padding: 1.5rem; border-radius: 0 8px 8px 0; background-color: var(--background-color); }
        .recommendation-container ul { padding-left: 20px; }
# ... existing code ...
        .recommendation-container li { margin-bottom: 0.5rem; }

        .status-summary-card { padding: 1rem; border-radius: 8px; text-align: center; height: 100%; }
        .status-normal-bg { background-color: var(--normal-bg-color); }
# ... existing code ...
        .status-abnormal-bg { background-color: var(--abnormal-bg-color); }
        .status-warning-bg { background-color: var(--warning-bg-color); }
        .status-neutral-bg { background-color: var(--neutral-bg-color); }
# ... existing code ...

        .status-summary-card p { margin: 0; color: var(--text-color); }
        .vision-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 1.5rem; }
        .vision-table th, .vision-table td { border: 1px solid var(--border-color); padding: 10px; text-align: left; vertical-align: middle; }
# ... existing code ...
        .vision-table th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; }
        .vision-table .result-cell { text-align: center; width: 180px; }
        .vision-result { display: inline-block; padding: 6px 16px; border-radius: 16px; font-size: 13px; font-weight: bold; border: 1px solid transparent; }
# ... existing code ...
        .vision-normal { background-color: var(--normal-bg-color); color: #2E7D32; }
        .vision-abnormal { background-color: var(--abnormal-bg-color); color: #C62828; }
        .vision-not-tested { background-color: var(--neutral-bg-color); color: #455A64; }
# ... existing code ...
        .styled-df-table { width: 100%; border-collapse: collapse; font-family: 'Sarabun', sans-serif !important; font-size: 14px; }
        .styled-df-table th, .styled-df-table td { border: 1px solid var(--border-color); padding: 10px; text-align: left; }
        .styled-df-table thead th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; text-align: center; vertical-align: middle; }
# ... existing code ...
        .styled-df-table tbody td { text-align: center; }
        .styled-df-table tbody td:first-child { text-align: left; }
        .styled-df-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
# ... existing code ...
        .hearing-table { table-layout: fixed; }
        
        .custom-advice-box { padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid transparent; font-weight: 600; }
# ... existing code ...
        .immune-box { background-color: var(--normal-bg-color); color: #2E7D32; border-color: rgba(40, 167, 69, 0.2); }
        .no-immune-box { background-color: var(--abnormal-bg-color); color: #C62828; border-color: rgba(220, 53, 69, 0.2); }
        .warning-box { background-color: var(--warning-bg-color); color: #AF6C00; border-color: rgba(255, 193, 7, 0.2); }
# ... existing code ...
    </style>
    """, unsafe_allow_html=True)

# --- Functions for displaying specific report sections ---
# ... existing code ...
# (ใส่โค้ดของ display_main_report, display_performance_report และส่วนอื่นๆ ที่เกี่ยวข้องที่นี่)
# ... (โค้ดของ display_main_report และ display_performance_report ไม่ได้แสดงเพื่อความกระชับ) ...

def render_vision_details_table(person_data):
# ... existing code ...
    # ... (โค้ดของ render_vision_details_table) ...
    pass # Placeholder

def display_performance_report_hearing(person_data, all_person_history_df):
# ... existing code ...
    # ... (โค้ดของ display_performance_report_hearing) ...
    pass # Placeholder

def display_performance_report_lung(person_data):
# ... existing code ...
    # ... (โค้ดของ display_performance_report_lung) ...
    pass # Placeholder

def display_performance_report_vision(person_data):
# ... existing code ...
    # ... (โค้ดของ display_performance_report_vision) ...
    pass # Placeholder

def display_performance_report(person_data, report_type, all_person_history_df=None):
# ... existing code ...
    with st.container(border=True):
        if report_type == 'lung':
            display_performance_report_lung(person_data)
# ... existing code ...
        elif report_type == 'vision':
            display_performance_report_vision(person_data)
        elif report_type == 'hearing':
            display_performance_report_hearing(person_data, all_person_history_df)
# ... existing code ...

def display_main_report(person_data, all_person_history_df):
    # ... (โค้ดส่วนใหญ่ของ display_main_report ถูกย้ายไป shared_ui.py) ...
# ... existing code ...
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
# ... existing code ...
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]
# ... existing code ...

    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]
# ... existing code ...

    with st.container(border=True):
        render_section_header("ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)")
        col1, col2 = st.columns(2)
# ... existing code ...
        with col1: st.markdown(render_lab_table_html("ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
        with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    selected_year = person.get("Year", datetime.now().year + 543)
# ... existing code ...

    with st.container(border=True):
        render_section_header("ผลการตรวจอื่นๆ (Other Examinations)")
        col_ua_left, col_ua_right = st.columns(2)
# ... existing code ...
        with col_ua_left:
            render_urine_section(person, sex, selected_year)
            st.markdown("<h5 class='section-subtitle'>ผลตรวจอุจจาระ (Stool Examination)</h5>", unsafe_allow_html=True)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)
# ... existing code ...

        with col_ua_right:
            st.markdown("<h5 class='section-subtitle'>ผลตรวจพิเศษ</h5>", unsafe_allow_html=True)
            cxr_col = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
# ... existing code ...
            ekg_col_name = get_ekg_col_name(selected_year)
            hep_a_value = person.get("Hepatitis A")
            hep_a_display_text = "ไม่ได้ตรวจ" if is_empty(hep_a_value) else safe_text(hep_a_value)
# ... existing code ...

            st.markdown(f"""
            <div class="table-container">
                <table class="info-detail-table">
# ... existing code ...
                    <tbody>
                        <tr><th>ผลเอกซเรย์ (Chest X-ray)</th><td>{interpret_cxr(person.get(cxr_col, ''))}</td></tr>
                        <tr><th>ผลคลื่นไฟฟ้าหัวใจ (EKG)</th><td>{interpret_ekg(person.get(ekg_col_name, ''))}</td></tr>
# ... existing code ...
                        <tr><th>ไวรัสตับอักเสบเอ (Hepatitis A)</th><td>{hep_a_display_text}</td></tr>
                    </tbody>
                </table>
# ... existing code ...
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<h5 class='section-subtitle'>ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)</h5>", unsafe_allow_html=True)
# ... existing code ...
            hbsag, hbsab, hbcab = safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB"))
            st.markdown(f"""<div class="table-container"><table class='lab-table'>
                <thead><tr><th style='text-align: center;'>HBsAg</th><th style='text-align: center;'>HBsAb</th><th style='text-align: center;'>HBcAb</th></tr></thead>
                <tbody><tr><td style='text-align: center;'>{hbsag}</td><td style='text-align: center;'>{hbsab}</td><td style='text-align: center;'>{hbcab}</td></tr></tbody>
# ... existing code ...
            </table></div>""", unsafe_allow_html=True)

            if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)):
                advice, status = hepatitis_b_advice(hbsag, hbsab, hbcab)
# ... existing code ...
                status_class = ""
                if status == 'immune':
                    status_class = 'immune-box'
# ... existing code ...
                elif status == 'no_immune':
                    status_class = 'no-immune-box'
                else: # infection or unclear
                    status_class = 'warning-box'
# ... existing code ...

                st.markdown(f"""
                <div class'custom-advice-box {status_class}'>
                    {advice}
# ... existing code ...
                </div>
                """, unsafe_allow_html=True)

    with st.container(border=True):
# ... existing code ...
        render_section_header("สรุปและคำแนะนำการปฏิบัติตัว (Summary & Recommendations)")
        recommendations_html = generate_comprehensive_recommendations(person_data)
        st.markdown(f"<div class='recommendation-container'>{recommendations_html}</div>", unsafe_allow_html=True)
