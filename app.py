import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html
import numpy as np
from collections import OrderedDict
from datetime import datetime
import re
import os
import json
from streamlit_js_eval import streamlit_js_eval
# --- Import ฟังก์ชันจากไฟล์อื่น ---
from performance_tests import interpret_audiogram, interpret_lung_capacity, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html


# --- Helper Functions (ที่ยังคงใช้งาน) ---
def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

THAI_MONTHS_GLOBAL = {1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน", 5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม", 9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {"ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2, "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4, "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6, "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8, "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10, "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12}

def normalize_thai_date(date_str):
    if is_empty(date_str): return pd.NA
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()
    if s.lower() in ["ไม่ตรวจ", "นัดทีหลัง", "ไม่ได้เข้ารับการตรวจ", ""]: return pd.NA
    try:
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"
        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})\.?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}"
    except Exception: pass
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            if parsed_dt.year > datetime.now().year + 50:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}"
    except Exception: pass
    return pd.NA

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

# --- START OF CHANGE: Redesigned UI Functions ---

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

# --- END OF CHANGE ---

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
    return "EKG" if year == datetime.now().year + 543 else f"EKG{str(year)[-2:]}"
def interpret_ekg(val):
    """Interprets EKG results."""
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val
def hepatitis_b_advice(hbsag, hbsab, hbcab):
    """Generates advice based on Hepatitis B panel results."""
    hbsag, hbsab, hbcab = hbsag.lower(), hbsab.lower(), hbcab.lower()
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี"
    if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
    if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_sqlite_data():
    tmp_path = None
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        conn = sqlite3.connect(tmp_path)
        df_loaded = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()
        
        df_loaded.columns = df_loaded.columns.str.strip()
        
        def clean_hn(hn_val):
            if pd.isna(hn_val): return ""
            s_val = str(hn_val).strip()
            if s_val.endswith('.0'): return s_val[:-2]
            return s_val
            
        df_loaded['HN'] = df_loaded['HN'].apply(clean_hn)
        
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Data Availability Checkers ---
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

# --- UI and Report Rendering Functions ---
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

# --- START OF CHANGE: Redesigned Header ---
def display_common_header(person_data):
    """Displays the common report header with personal and vital sign info."""
    st.markdown(f"""
    <div class="report-title">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Personal Info
    st.markdown(f"""
    <div class="info-grid">
        <div class="info-item"><span>ชื่อ-สกุล</span>{person_data.get('ชื่อ-สกุล', '-')}</div>
        <div class="info-item"><span>อายุ</span>{str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')} ปี</div>
        <div class="info-item"><span>เพศ</span>{person_data.get('เพศ', '-')}</div>
        <div class="info-item"><span>HN</span>{str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')}</div>
        <div class="info-item"><span>หน่วยงาน</span>{person_data.get('หน่วยงาน', '-')}</div>
        <div class="info-item"><span>วันที่ตรวจ</span>{person_data.get("วันที่ตรวจ", "-")}</div>
    </div>
    """, unsafe_allow_html=True)

    # Vitals as Metric Cards
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
        bp_val = f"{sbp_int}/{dbp_int}"
        bp_desc = interpret_bp(sbp_int, dbp_int)
    except: 
        bp_val = "-"
        bp_desc = "ไม่มีข้อมูล"
    
    try: pulse_val = f"{int(float(person_data.get('pulse', '-')))}"
    except: pulse_val = "-"

    weight_val = f"{person_data.get('น้ำหนัก', '-')}"
    height_val = f"{person_data.get('ส่วนสูง', '-')}"
    waist_val = f"{person_data.get('รอบเอว', '-')}"
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric(label="น้ำหนัก (กก.)", value=weight_val)
    with col2: st.metric(label="ส่วนสูง (ซม.)", value=height_val)
    with col3: st.metric(label="รอบเอว (ซม.)", value=waist_val)
    with col4: st.metric(label="ความดัน (mmHg)", value=bp_val, help=bp_desc)
    with col5: st.metric(label="ชีพจร (ครั้ง/นาที)", value=pulse_val)

    st.markdown("<div style='margin-top: -20px;'></div>", unsafe_allow_html=True) # Adjust space after metrics

# --- END OF CHANGE ---

# --- START OF CHANGE: New Centralized CSS ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        /* --- General & Typography --- */
        html, body, [class*="st-"], .st-emotion-cache-10trblm, h1, h2, h3, h4, h5, h6 {
            font-family: 'Sarabun', sans-serif !important; 
        }
        .main {
             background-color: #0E1117; /* Streamlit's default dark */
        }
        h4 { /* For section headers */
            border-bottom: 2px solid #008080; /* Teal accent */
            padding-bottom: 8px;
            margin-top: 40px;
            margin-bottom: 20px;
            color: #FFFFFF;
        }
        h5.section-subtitle {
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            color: #E0E0E0;
        }

        /* --- Control Panel --- */
        .control-panel {
            background-color: rgba(40, 43, 54, 0.5);
            border: 1px solid #282b36;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 2rem;
        }
        .stButton>button {
            background-color: #008080;
            color: white;
            border-radius: 8px;
            border: none;
            font-weight: 600;
        }
        .stButton>button:hover {
            background-color: #006666;
            color: white;
        }

        /* --- Report Header & Info --- */
        .report-title { text-align: center; margin-bottom: 2rem; }
        .report-title h1 { font-size: 2.2rem; color: #FFFFFF; margin-bottom: 0.25rem; }
        .report-title p { font-size: 1rem; color: #a0a0a0; margin: 0; }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
            background-color: rgba(40, 43, 54, 0.3);
            padding: 1rem;
            border-radius: 8px;
        }
        .info-item {
            font-size: 1rem;
            color: #FFFFFF;
        }
        .info-item span {
            display: block;
            font-size: 0.8rem;
            color: #a0a0a0;
            margin-bottom: 4px;
        }
        div[data-testid="stMetric"] {
            background-color: #282b36;
            border-radius: 8px;
            padding: 15px;
        }
        div[data-testid="stMetric"] > div > div:nth-child(2) { /* Metric value */
            font-size: 1.8rem;
            color: #00BFA5; /* Bright Teal */
        }

        /* --- Lab Result Tables --- */
        .table-container {
            overflow-x: auto;
        }
        .lab-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .lab-table th, .lab-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #282b36;
        }
        .lab-table th {
            background-color: #282b36;
            font-weight: 600;
            text-align: center;
        }
        .lab-table tbody tr:hover {
            background-color: #282b36;
        }
        .lab-table .abnormal-row {
            background-color: rgba(255, 71, 87, 0.15); /* Soft red */
            color: #FF4757;
            font-weight: 600;
        }
        .info-detail-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .info-detail-table th, .info-detail-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #282b36;
            text-align: left;
        }
        .info-detail-table th {
            width: 40%;
            font-weight: 600;
        }
        
        /* --- Performance Report Specific Styles --- */
        .vision-table {
            width: 100%; border-collapse: collapse; font-size: 14px;
            margin-top: 1.5rem; color: var(--text-color);
        }
        .vision-table th, .vision-table td {
            border: 1px solid #282b36; padding: 10px;
            text-align: left; vertical-align: middle;
        }
        .vision-table th { background-color: #282b36; font-weight: bold; }
        .vision-table .result-cell { text-align: center; width: 180px; }
        .vision-result {
            display: inline-block; padding: 6px 16px; border-radius: 16px;
            font-size: 13px; font-weight: bold; color: white; border: 1px solid transparent;
        }
        .vision-normal { background-color: #2e7d32; border-color: #5b9f60; }
        .vision-abnormal { background-color: #c62828; border-color: #e57373; }
        .vision-not-tested { background-color: #4f4f56; border-color: #6a6a71; color: #d1d1d6; }
        .styled-df-table {
            width: 100%; border-collapse: collapse; font-family: 'Sarabun', sans-serif !important;
            font-size: 14px; color: var(--text-color);
        }
        .styled-df-table th, .styled-df-table td { border: 1px solid #282b36; padding: 10px; text-align: left; }
        .styled-df-table thead th { background-color: #282b36; font-weight: bold; text-align: center; vertical-align: middle; }
        .styled-df-table tbody td { text-align: center; }
        .styled-df-table tbody td:first-child { text-align: left; }
        .styled-df-table tbody tr:hover { background-color: #282b36; }
        .hearing-table { table-layout: fixed; }

    </style>
    """, unsafe_allow_html=True)
# --- END OF CHANGE ---

def render_vision_details_table(person_data):
    """
    Renders a clearer, single-column result table for the vision test with corrected logic.
    """
    vision_tests = [
        {'display': '1. การมองด้วย 2 ตา (Binocular vision)', 'type': 'value', 'col': 'ป.การรวมภาพ', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '2. การมองภาพระยะไกลด้วยสองตา (Far vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะไกล', 'abnormal_col': 'ผ.ความชัดของภาพระยะไกล', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '3. การมองภาพระยะไกลด้วยตาขวา (Far vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '4. การมองภาพระยะไกลด้วยตาซ้าย (Far vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '5. การมองภาพ 3 มิติ (Stereo depth)', 'type': 'paired_value', 'normal_col': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'abnormal_col': 'ผ.การกะระยะและมองความชัดลึกของภาพ', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '6. การมองจำแนกสี (Color discrimination)', 'type': 'paired_value', 'normal_col': 'ป.การจำแนกสี', 'abnormal_col': 'ผ.การจำแนกสี', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '9. การมองภาพระยะใกล้ด้วยสองตา (Near vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะใกล้', 'abnormal_col': 'ผ.ความชัดของภาพระยะใกล้', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '10. การมองภาพระยะใกล้ด้วยตาขวา (Near vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '11. การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '13. ลานสายตา (Visual field)', 'type': 'value', 'col': 'ป.ลานสายตา', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '7. ความสมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'related_keyword': 'แนวตั้งระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '8. ความสมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'related_keyword': 'แนวนอนระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '12. ความสมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'related_keyword': 'แนวนอนระยะใกล้', 'outcomes': ['ปกติ', 'ผิดปกติ']}
    ]

    vision_tests.sort(key=lambda x: int(x['display'].split('.')[0]))

    html_parts = []
    html_parts.append('<table class="vision-table">')
    html_parts.append('<thead><tr><th>รายการตรวจ (Vision Test)</th><th class="result-cell">ผลการตรวจ</th></tr></thead>')
    html_parts.append('<tbody>')

    strabismus_val = str(person_data.get('ผ.สายตาเขซ่อนเร้น', '')).strip()

    for test in vision_tests:
        is_normal = False
        is_abnormal = False
        result_text = ""

        if test['type'] == 'value':
            result_value = str(person_data.get(test['col'], '')).strip()
            if not is_empty(result_value):
                result_text = result_value
                if any(keyword.lower() in result_value.lower() for keyword in test['normal_keywords']):
                    is_normal = True
                else:
                    is_abnormal = True 
        
        elif test['type'] == 'paired_value':
            normal_val = str(person_data.get(test['normal_col'], '')).strip()
            abnormal_val = str(person_data.get(test['abnormal_col'], '')).strip()
            if not is_empty(normal_val):
                is_normal = True
                result_text = normal_val
            elif not is_empty(abnormal_val):
                is_abnormal = True
                result_text = abnormal_val
        
        elif test['type'] == 'phoria':
            normal_val = str(person_data.get(test['normal_col'], '')).strip()
            if not is_empty(normal_val):
                is_normal = True
                result_text = normal_val
            elif not is_empty(strabismus_val) and test['related_keyword'] in strabismus_val:
                is_abnormal = True
                result_text = f"สายตาเขซ่อนเร้น ({test['related_keyword']})"

        status_text = ""
        status_class = ""

        if is_normal:
            status_text = test['outcomes'][0] 
            status_class = 'vision-normal'
        elif is_abnormal:
            status_text = test['outcomes'][1]
            status_class = 'vision-abnormal'
        else:
            status_text = "ไม่ได้ตรวจ"
            status_class = 'vision-not-tested'

        html_parts.append('<tr>')
        html_parts.append(f"<td>{test['display']}</td>")
        html_parts.append(f'<td class="result-cell"><span class="vision-result {status_class}">{status_text}</span></td>')
        html_parts.append('</tr>')

    html_parts.append("</tbody></table>")
    return "".join(html_parts)

def display_performance_report_hearing(person_data, all_person_history_df):
    render_section_header("รายงานผลการตรวจสมรรถภาพการได้ยิน (Audiometry Report)")
    
    hearing_results = interpret_audiogram(person_data, all_person_history_df)

    if hearing_results['summary'].get('overall') == "ไม่ได้เข้ารับการตรวจ":
        st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพการได้ยินในปีนี้")
        return

    summary_r_raw = person_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    summary_l_raw = person_data.get('ผลตรวจการได้ยินหูซ้าย', 'N/A')

    def get_summary_color(summary_text):
        if "ปกติ" in summary_text: return "rgba(46, 125, 50, 0.2)"
        elif "N/A" in summary_text or "ไม่ได้" in summary_text: return "rgba(120, 120, 120, 0.2)"
        else: return "rgba(198, 40, 40, 0.2)"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background-color: {get_summary_color(summary_r_raw)}; padding: 1rem; border-radius: 8px; text-align: center; height: 100%;">
            <p style="font-size: 1rem; font-weight: bold; margin: 0; color: var(--text-color);">หูขวา (Right Ear)</p>
            <p style="font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0 0 0; color: var(--text-color);">{summary_r_raw}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color: {get_summary_color(summary_l_raw)}; padding: 1rem; border-radius: 8px; text-align: center; height: 100%;">
            <p style="font-size: 1rem; font-weight: bold; margin: 0; color: var(--text-color);">หูซ้าย (Left Ear)</p>
            <p style="font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0 0 0; color: var(--text-color);">{summary_l_raw}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    advice = hearing_results.get('advice', 'ไม่มีคำแนะนำเพิ่มเติม')
    if hearing_results.get('sts_detected'):
        st.error(f"**⚠️ พบการเปลี่ยนแปลงระดับการได้ยินอย่างมีนัยสำคัญ (STS):** {advice}")
    elif "ผิดปกติ" in hearing_results['summary'].get('overall', ''):
        st.warning(f"**คำแนะนำ:** {advice}")
    else:
        st.success(f"**คำแนะนำ:** {advice}")
    
    st.markdown("<hr style='border-color: #282b36;'>", unsafe_allow_html=True)

    data_col, avg_col = st.columns([3, 2])
    
    with data_col:
        st.markdown("<h5><b>ผลการตรวจโดยละเอียด</b></h5>", unsafe_allow_html=True)
        has_baseline = hearing_results.get('baseline_source') != 'none'
        baseline_year = hearing_results.get('baseline_year')
        freq_order = ['500 Hz', '1000 Hz', '2000 Hz', '3000 Hz', '4000 Hz', '6000 Hz', '8000 Hz']
        
        tbody_html = ""
        for freq in freq_order:
            current = hearing_results.get('raw_values', {}).get(freq, {})
            r_val, l_val = current.get('right', '-'), current.get('left', '-')
            shift_r_text, shift_l_text = '-', '-'
            if has_baseline:
                shift = hearing_results.get('shift_values', {}).get(freq, {})
                shift_r, shift_l = shift.get('right'), shift.get('left')
                if shift_r is not None: shift_r_text = f"+{shift_r}" if shift_r > 0 else str(shift_r)
                if shift_l is not None: shift_l_text = f"+{shift_l}" if shift_l > 0 else str(shift_l)
            tbody_html += f"<tr><td style='text-align: left;'>{freq}</td><td>{r_val}</td><td>{l_val}</td><td>{shift_r_text}</td><td>{shift_l_text}</td></tr>"

        baseline_header_text = f" (พ.ศ. {baseline_year})" if has_baseline else " (ไม่มี Baseline)"
        
        full_table_html = f"""
        <table class="styled-df-table hearing-table">
            <thead>
                <tr>
                    <th rowspan="2" style="vertical-align: middle;">ความถี่ (Hz)</th>
                    <th colspan="2">ผลการตรวจปัจจุบัน (dB)</th>
                    <th colspan="2">การเปลี่ยนแปลงเทียบกับ Baseline{baseline_header_text}</th>
                </tr>
                <tr><th>หูขวา</th><th>หูซ้าย</th><th>Shift ขวา</th><th>Shift ซ้าย</th></tr>
            </thead>
            <tbody>{tbody_html}</tbody>
        </table>
        """
        st.markdown(full_table_html, unsafe_allow_html=True)

    with avg_col:
        st.markdown("<h5><b>ค่าเฉลี่ยการได้ยิน (dB)</b></h5>", unsafe_allow_html=True)
        averages = hearing_results.get('averages', {})
        avg_r_speech, avg_l_speech = averages.get('right_500_2000'), averages.get('left_500_2000')
        avg_r_high, avg_l_high = averages.get('right_3000_6000'), averages.get('left_3000_6000')
        st.markdown(f"""
        <div style='background-color: #282b36; padding: 1rem; border-radius: 8px; line-height: 1.8; height: 100%;'>
            <b>ความถี่เสียงพูด (500-2000 Hz):</b>
            <ul>
                <li>หูขวา: {f'{avg_r_speech:.1f}' if avg_r_speech is not None else 'N/A'}</li>
                <li>หูซ้าย: {f'{avg_l_speech:.1f}' if avg_l_speech is not None else 'N/A'}</li>
            </ul>
            <b>ความถี่สูง (3000-6000 Hz):</b>
            <ul>
                <li>หูขวา: {f'{avg_r_high:.1f}' if avg_r_high is not None else 'N/A'}</li>
                <li>หูซ้าย: {f'{avg_l_high:.1f}' if avg_l_high is not None else 'N/A'}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


def display_performance_report_lung(person_data):
    render_section_header("รายงานผลการตรวจสมรรถภาพปอด (Spirometry Report)")
    lung_summary, lung_advice, lung_raw_values = interpret_lung_capacity(person_data)

    if lung_summary == "ไม่ได้เข้ารับการตรวจ":
        st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพปอดในปีนี้")
        return

    st.markdown("<h5><b>สรุปผลการตรวจที่สำคัญ</b></h5>", unsafe_allow_html=True)
    def format_val(key):
        val = lung_raw_values.get(key)
        return f"{val:.1f}" if val is not None else "-"
    col1, col2, col3 = st.columns(3)
    col1.metric(label="FVC (% เทียบค่ามาตรฐาน)", value=format_val('FVC %'), help="ความจุของปอดเมื่อหายใจออกเต็มที่ (ควร > 80%)")
    col2.metric(label="FEV1 (% เทียบค่ามาตรฐาน)", value=format_val('FEV1 %'), help="ปริมาตรอากาศที่หายใจออกในวินาทีแรก (ควร > 80%)")
    col3.metric(label="FEV1/FVC Ratio (%)", value=format_val('FEV1/FVC %'), help="สัดส่วนของ FEV1 ต่อ FVC (ควร > 70%)")
    st.markdown("<hr style='border-color: #282b36;'>", unsafe_allow_html=True)

    res_col1, res_col2 = st.columns([2, 3])
    with res_col1:
        st.markdown("<h5><b>ผลการแปลความหมาย</b></h5>", unsafe_allow_html=True)
        if "ปกติ" in lung_summary: bg_color = "background-color: #2e7d32; color: white;"
        elif "ไม่ได้" in lung_summary or "คลาดเคลื่อน" in lung_summary: bg_color = "background-color: #616161; color: white;"
        else: bg_color = "background-color: #c62828; color: white;"
        st.markdown(f'<div style="padding: 1rem; border-radius: 8px; {bg_color} text-align: center;"><h4 style="color: white; margin: 0; font-weight: bold; border: none;">{lung_summary}</h4></div>', unsafe_allow_html=True)
        st.markdown("<br><h5><b>คำแนะนำ</b></h5>", unsafe_allow_html=True)
        st.info(lung_advice or "ไม่มีคำแนะนำเพิ่มเติม")
        st.markdown("<h5><b>ผลเอกซเรย์ทรวงอก</b></h5>", unsafe_allow_html=True)
        selected_year = person_data.get("Year")
        cxr_result_interpreted = "ไม่มีข้อมูล"
        if selected_year:
            cxr_col_name = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            cxr_result_interpreted = interpret_cxr(person_data.get(cxr_col_name, ''))
        st.markdown(f'<div style="font-size: 14px; padding: 0.5rem; background-color: #282b36; border-radius: 4px;">{cxr_result_interpreted}</div>', unsafe_allow_html=True)
    with res_col2:
        st.markdown("<h5><b>ตารางแสดงผลโดยละเอียด</b></h5>", unsafe_allow_html=True)
        def format_detail_val(key, format_spec, unit=""):
            val = lung_raw_values.get(key)
            if val is not None and isinstance(val, (int, float)): return f"{val:{format_spec}}{unit}"
            return "-"
        detail_data = {"การทดสอบ (Test)": ["FVC", "FEV1", "FEV1/FVC"],"ค่าที่วัดได้ (Actual)": [format_detail_val('FVC', '.2f', ' L'), format_detail_val('FEV1', '.2f', ' L'), format_detail_val('FEV1/FVC %', '.1f', ' %')],"ค่ามาตรฐาน (Predicted)": [format_detail_val('FVC predic', '.2f', ' L'), format_detail_val('FEV1 predic', '.2f', ' L'), format_detail_val('FEV1/FVC % pre', '.1f', ' %')],"% เทียบค่ามาตรฐาน (% Pred)": [format_detail_val('FVC %', '.1f', ' %'), format_detail_val('FEV1 %', '.1f', ' %'), "-"]}
        df_details = pd.DataFrame(detail_data)
        st.markdown(df_details.to_html(escape=False, index=False, classes="styled-df-table"), unsafe_allow_html=True)

def display_performance_report_vision(person_data):
    render_section_header("รายงานผลการตรวจสมรรถภาพการมองเห็น (Vision Test Report)")
    
    if not has_vision_data(person_data):
        st.warning("ไม่พบข้อมูลผลการตรวจสมรรถภาพการมองเห็นโดยละเอียดในปีนี้")
        vision_advice_summary = person_data.get('สรุปเหมาะสมกับงาน')
        doctor_advice = person_data.get('แนะนำABN EYE')
        if not is_empty(vision_advice_summary) or not is_empty(doctor_advice):
            st.info("หมายเหตุ: ข้อมูลสรุปที่แสดงอาจมาจากผลการตรวจในปีอื่น")
            if not is_empty(vision_advice_summary):
                 st.markdown(f"""
                 <div style='background-color: rgba(64, 128, 255, 0.1); border: 1px solid rgba(64, 128, 255, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                    <div style='flex-shrink: 0;'><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4080FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg></div>
                    <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #A6C8FF;'>สรุปความเหมาะสมกับงาน</h5><p style='margin:0; color: var(--text-color);'>{vision_advice_summary}</p></div>
                 </div>""", unsafe_allow_html=True)
            if not is_empty(doctor_advice):
                 st.markdown(f"""
                 <div style='background-color: rgba(255, 229, 100, 0.1); border: 1px solid rgba(255, 229, 100, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                    <div style='flex-shrink: 0;'><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFE564" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg></div>
                    <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #FFE564;'>คำแนะนำเพิ่มเติมจากแพทย์</h5><p style='margin:0; color: var(--text-color);'>{doctor_advice}</p></div>
                 </div>""", unsafe_allow_html=True)
        return

    vision_advice_summary = person_data.get('สรุปเหมาะสมกับงาน')
    if not is_empty(vision_advice_summary):
        st.markdown(f"""
         <div style='background-color: rgba(64, 128, 255, 0.1); border: 1px solid rgba(64, 128, 255, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
            <div style='flex-shrink: 0;'><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4080FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg></div>
            <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #A6C8FF;'>สรุปความเหมาะสมกับงาน</h5><p style='margin:0; color: var(--text-color);'>{vision_advice_summary}</p></div>
         </div>""", unsafe_allow_html=True)

    abnormality_fields = OrderedDict([('ผ.สายตาเขซ่อนเร้น', 'สายตาเขซ่อนเร้น'), ('ผ.การรวมภาพ', 'การรวมภาพ'), ('ผ.ความชัดของภาพระยะไกล', 'ความชัดของภาพระยะไกล'), ('ผ.การกะระยะและมองความชัดลึกของภาพ', 'การกะระยะ/ความชัดลึก'), ('ผ.การจำแนกสี', 'การจำแนกสี'), ('ผ.ความชัดของภาพระยะใกล้', 'ความชัดของภาพระยะใกล้'), ('ผ.ลานสายตา', 'ลานสายตา')])
    abnormal_topics = [name for col, name in abnormality_fields.items() if not is_empty(person_data.get(col))]
    doctor_advice = person_data.get('แนะนำABN EYE')

    if abnormal_topics or not is_empty(doctor_advice):
        summary_parts = []
        if abnormal_topics: summary_parts.append(f"<b>พบความผิดปกติเกี่ยวกับ:</b> {', '.join(abnormal_topics)}")
        if not is_empty(doctor_advice): summary_parts.append(f"<b>คำแนะนำเพิ่มเติมจากแพทย์:</b> {doctor_advice}")
        st.markdown(f"""
        <div style='background-color: rgba(255, 229, 100, 0.1); border: 1px solid rgba(255, 229, 100, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
            <div style='flex-shrink: 0;'><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFE564" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg></div>
            <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #FFE564;'>สรุปความผิดปกติและคำแนะนำ</h5><p style='margin:0; color: var(--text-color);'>{"<br>".join(summary_parts)}</p></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #282b36;'>", unsafe_allow_html=True)
    st.markdown("<h5><b>ผลการตรวจโดยละเอียด</b></h5>", unsafe_allow_html=True)
    st.markdown(render_vision_details_table(person_data), unsafe_allow_html=True)

def display_performance_report(person_data, report_type, all_person_history_df=None):
    if report_type == 'lung':
        display_performance_report_lung(person_data)
    elif report_type == 'vision':
        display_performance_report_vision(person_data)
    elif report_type == 'hearing':
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
    with col1: st.markdown(render_lab_table_html("ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)
    
    selected_year = person.get("Year", datetime.now().year + 543)
    
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
            <thead><tr><th>HBsAg</th><th>HBsAb</th><th>HBcAb</th></tr></thead>
            <tbody><tr><td>{hbsag}</td><td>{hbsab}</td><td>{hbcab}</td></tr></tbody>
        </table></div>""", unsafe_allow_html=True)
        
        if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)):
            advice = hepatitis_b_advice(hbsag, hbsab, hbcab)
            bg_color = "rgba(57, 255, 20, 0.2)" if "มีภูมิคุ้มกัน" in advice else "rgba(255, 255, 0, 0.2)"
            st.markdown(f"<div style='line-height: 1.6; padding: 0.4rem 1.5rem; border-radius: 6px; background-color: {bg_color}; color: var(--text-color); margin-top: 1rem; font-size: 14px;'>{advice}</div>", unsafe_allow_html=True)
            
    render_section_header("สรุปและคำแนะนำการปฏิบัติตัว (Summary & Recommendations)")
    recommendations_html = generate_comprehensive_recommendations(person_data)
    st.markdown(f"<div class='recommendation-container'>{recommendations_html}</div>", unsafe_allow_html=True)


# --- Main Application Logic ---
df = load_sqlite_data()
if df is None:
    st.stop()

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# --- START OF CHANGE: Inject CSS and Redesign Controls ---
inject_custom_css()

def perform_search():
    st.session_state.search_query = st.session_state.search_input
    st.session_state.selected_year = None
    st.session_state.selected_date = None
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    raw_search_term = st.session_state.search_query.strip()
    search_term = re.sub(r'\s+', ' ', raw_search_term)
    if search_term:
        if search_term.isdigit():
             results_df = df[df["HN"] == search_term].copy()
        else:
             results_df = df[df["ชื่อ-สกุล"] == search_term].copy()

        if results_df.empty:
            st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง")
            st.session_state.search_result = pd.DataFrame()
        else:
            st.session_state.search_result = results_df
    else:
        st.session_state.search_result = pd.DataFrame()

def handle_year_change():
    st.session_state.selected_year = st.session_state.year_select
    st.session_state.selected_date = None
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)

if 'search_query' not in st.session_state: st.session_state.search_query = ""
if 'search_input' not in st.session_state: st.session_state.search_input = ""
if 'search_result' not in st.session_state: st.session_state.search_result = pd.DataFrame()
if 'selected_year' not in st.session_state: st.session_state.selected_year = None
if 'selected_date' not in st.session_state: st.session_state.selected_date = None
if 'print_trigger' not in st.session_state: st.session_state.print_trigger = False
if 'print_performance_trigger' not in st.session_state: st.session_state.print_performance_trigger = False

# --- Top Controls in a Container ---
with st.container():
    st.markdown('<div class="control-panel">', unsafe_allow_html=True)
    
    search_col, year_col, button_col = st.columns([4, 2, 3])

    with search_col:
        st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input", on_change=perform_search, placeholder="ค้นหาด้วย HN หรือ ชื่อ-สกุล...", label_visibility="collapsed")
    
    results_df = st.session_state.search_result
    if not results_df.empty:
        with year_col:
            available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
            if available_years:
                if st.session_state.selected_year not in available_years:
                    st.session_state.selected_year = available_years[0]
                year_idx = available_years.index(st.session_state.selected_year)
                st.selectbox("เลือกปี พ.ศ.", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change, label_visibility="collapsed")
            
                person_year_df = results_df[results_df["Year"] == st.session_state.selected_year]

                if not person_year_df.empty:
                    merged_series = person_year_df.bfill().ffill().iloc[0]
                    st.session_state.person_row = merged_series.to_dict()
                    st.session_state.selected_row_found = True
                else:
                     st.session_state.pop("person_row", None)
                     st.session_state.pop("selected_row_found", None)
    
    with button_col:
        if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
            print_col1, print_col2 = st.columns(2)
            with print_col1:
                if st.button("พิมพ์รายงาน", use_container_width=True):
                     st.session_state.print_trigger = True
            with print_col2:
                if st.button("พิมพ์สมรรถภาพ", use_container_width=True):
                    st.session_state.print_performance_trigger = True

    st.markdown('</div>', unsafe_allow_html=True)

# --- END OF CHANGE ---

# --- Main Page ---
if "person_row" not in st.session_state or not st.session_state.get("selected_row_found", False):
    st.info("กรุณาค้นหาและเลือกผลตรวจจากแผงควบคุมด้านบน")
else:
    person_data = st.session_state.person_row
    all_person_history_df = st.session_state.search_result
    
    available_reports = OrderedDict()
    if has_basic_health_data(person_data): available_reports['สุขภาพพื้นฐาน'] = 'main_report'
    if has_vision_data(person_data): available_reports['สมรรถภาพการมองเห็น'] = 'vision_report'
    if has_hearing_data(person_data): available_reports['สมรรถภาพการได้ยิน'] = 'hearing_report'
    if has_lung_data(person_data): available_reports['สมรรถภาพปอด'] = 'lung_report'
    
    if not available_reports:
        display_common_header(person_data)
        st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับวันที่และปีที่เลือก")
    else:
        tabs = st.tabs(list(available_reports.keys()))
    
        for i, (tab_title, page_key) in enumerate(available_reports.items()):
            with tabs[i]:
                display_common_header(person_data)
                if page_key == 'vision_report':
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
        
        print_component = f"""
        <iframe id="print-iframe" style="display:none;"></iframe>
        <script>
            (function() {{
                const iframe = document.getElementById('print-iframe');
                if (!iframe) return;
                const iframeDoc = iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write({escaped_html});
                iframeDoc.close();
                iframe.onload = function() {{
                    setTimeout(function() {{
                        try {{
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();
                        }} catch (e) {{
                            console.error("Printing failed:", e);
                            alert("Could not open print dialog.");
                        }}
                    }}, 500);
                }};
            }})();
        </script>
        """
        st.components.v1.html(print_component, height=0, width=0)
        st.session_state.print_trigger = False

    if st.session_state.get("print_performance_trigger", False):
        report_html_data = generate_performance_report_html(person_data, all_person_history_df)
        escaped_html = json.dumps(report_html_data)
        
        print_component = f"""
        <iframe id="print-perf-iframe" style="display:none;"></iframe>
        <script>
            (function() {{
                const iframe = document.getElementById('print-perf-iframe');
                if (!iframe) return;
                const iframeDoc = iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write({escaped_html});
                iframeDoc.close();
                iframe.onload = function() {{
                    setTimeout(function() {{
                        try {{
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();
                        }} catch (e) {{
                            console.error("Printing performance report failed:", e);
                            alert("Could not open print dialog for performance report.");
                        }}
                    }}, 500);
                }};
            }})();
        </script>
        """
        st.components.v1.html(print_component, height=0, width=0)
        st.session_state.print_performance_trigger = False
