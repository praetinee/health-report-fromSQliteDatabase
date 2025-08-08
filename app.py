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
# --- แก้ไข: Import ฟังก์ชันใหม่ และลบ import ที่ไม่ใช้แล้ว ---
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

def render_section_header(title, subtitle=None):
    """Renders a styled section header."""
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"<div style='background-color: #1b5e20; color: white; text-align: center; padding: 0.4rem 0.5rem; font-weight: bold; border-radius: 8px; margin-top: 2rem; margin-bottom: 1rem; font-size: 14px;'>{full_title}</div>"

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    """Generates HTML for a lab result table."""
    style = f"""<style>
        .{table_class}-container {{ margin-top: 1rem; }}
        .{table_class} {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 14px; }}
        .{table_class} thead th {{ background-color: var(--secondary-background-color); padding: 2px; text-align: center; font-weight: bold; border: 1px solid transparent; }}
        .{table_class} td {{ padding: 2px; border: 1px solid transparent; text-align: center; }}
        .{table_class}-abn {{ background-color: rgba(255, 64, 64, 0.25); }}
        .{table_class}-row {{ background-color: rgba(255,255,255,0.02); }}
    </style>"""
    header_html = render_section_header(title, subtitle)
    html_content = f"{style}{header_html}<div class='{table_class}-container'><table class='{table_class}'><colgroup><col style='width:33.33%;'><col style='width:33.33%;'><col style='width:33.33%;'></colgroup><thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i in [0, 2] else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else f"{table_class}-row"
        html_content += f"<tr><td class='{row_class}' style='text-align: left;'>{row[0][0]}</td><td class='{row_class}'>{row[1][0]}</td><td class='{row_class}' style='text-align: left;'>{row[2][0]}</td></tr>"
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
    html_content = render_lab_table_html("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผล", "ค่าปกติ"], [[(row["การตรวจ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (safe_value(row["ผลตรวจ"]), is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (row["ค่าปกติ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"]))] for _, row in df_urine.iterrows()], table_class="urine-table")
    st.markdown(html_content, unsafe_allow_html=True)
    # --- แก้ไข: ไม่ต้องคืนค่า summary เพราะจะถูกรวมในคำแนะนำหลัก ---
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
    <div style="margin-top: 1rem;">
        <table style="width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 14px;">
            <colgroup>
                <col style="width: 50%;">
                <col style="width: 50%;">
            </colgroup>
            <tbody>
                <tr>
                    <th style="background-color: var(--secondary-background-color); padding: 3px 2px; text-align: left; font-weight: bold; border: 1px solid transparent;">ผลตรวจอุจจาระทั่วไป</th>
                    <td style="padding: 3px 2px; border: 1px solid transparent; text-align: left;">{exam}</td>
                </tr>
                <tr>
                    <th style="background-color: var(--secondary-background-color); padding: 3px 2px; text-align: left; font-weight: bold; border: 1px solid transparent;">ผลตรวจอุจจาระเพาะเชื้อ</th>
                    <td style="padding: 3px 2px; border: 1px solid transparent; text-align: left;">{cs}</td>
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
        # This should point to your actual database file or URL
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr" # Example Google Drive ID
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
    """Check for a few key indicators of a basic health checkup."""
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_vision_data(person_data):
    """Check for any ACTUAL vision test data, ignoring summary/advice fields."""
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ',
        'ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล',
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)',
        'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)',
        'ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ',
        'ป.การจำแนกสี', 'ผ.การจำแนกสี',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน',
        'ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้',
        'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)',
        'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)',
        'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน',
        'ป.ลานสายตา', 'ผ.ลานสายตา',
        'ผ.สายตาเขซ่อนเร้น'
    ]
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)


def has_hearing_data(person_data):
    """Check for detailed hearing (audiogram) data."""
    hearing_keys = [ 'R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k' ]
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)


def has_lung_data(person_data):
    """Check for lung capacity test data."""
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

# --- ลบฟังก์ชัน combined_health_advice ที่ไม่ได้ใช้งานแล้ว ---
    
def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def display_common_header(person_data):
    """Displays the common report header with personal and vital sign info."""
    check_date = person_data.get("วันที่ตรวจ", "ไม่มีข้อมูล")
    st.markdown(f"""<div class="report-header-container" style="text-align: center; margin-bottom: 2rem; margin-top: 2rem;">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        <p><b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>""", unsafe_allow_html=True)
    
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except: sbp_int = dbp_int = None; bp_val = "-"
    bp_desc = interpret_bp(sbp_int, dbp_int) if sbp_int is not None else "-"
    bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val
    try: pulse_val = int(float(person_data.get("pulse", "-")))
    except: pulse_val = None
    pulse = f"{pulse_val} ครั้ง/นาที" if pulse_val is not None else "-"
    weight_display = f"{person_data.get('น้ำหนัก', '-')} กก." if not is_empty(person_data.get('น้ำหนัก', '-')) else "-"
    height_display = f"{person_data.get('ส่วนสูง', '-')} ซม." if not is_empty(person_data.get('ส่วนสูง', '-')) else "-"
    waist_display = f"{person_data.get('รอบเอว', '-')} ซม." if not is_empty(person_data.get('รอบเอว', '-')) else "-"
    
    html_parts = []
    html_parts.append('<div class="personal-info-container">')
    html_parts.append('<hr style="margin-top: 0.5rem; margin-bottom: 1.5rem;">')
    html_parts.append('<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; margin-bottom: 1rem; text-align: center; line-height: 1.8;">')
    html_parts.append(f"<div><b>ชื่อ-สกุล:</b> {person_data.get('ชื่อ-สกุล', '-')}</div>")
    html_parts.append(f"<div><b>อายุ:</b> {str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')} ปี</div>")
    html_parts.append(f"<div><b>เพศ:</b> {person_data.get('เพศ', '-')}</div>")
    html_parts.append(f"<div><b>HN:</b> {str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')}</div>")
    html_parts.append(f"<div><b>หน่วยงาน:</b> {person_data.get('หน่วยงาน', '-')}</div>")
    html_parts.append('</div>')
    html_parts.append('<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; margin-bottom: 1.5rem; text-align: center; line-height: 1.8;">')
    html_parts.append(f"<div><b>น้ำหนัก:</b> {weight_display}</div>")
    html_parts.append(f"<div><b>ส่วนสูง:</b> {height_display}</div>")
    html_parts.append(f"<div><b>รอบเอว:</b> {waist_display}</div>")
    html_parts.append(f"<div><b>ความดันโลหิต:</b> {bp_full}</div>")
    html_parts.append(f"<div><b>ชีพจร:</b> {pulse}</div>")
    html_parts.append('</div>')
    # --- นำบรรทัดคำแนะนำในส่วนหัวออก ---
    html_parts.append('</div>')
    
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def inject_custom_css():
    st.markdown("""
    <style>
        .vision-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-top: 1.5rem;
            color: var(--text-color); /* Use Streamlit's text color variable */
        }
        .vision-table th, .vision-table td {
            border: 1px solid var(--secondary-background-color); /* Use theme's secondary bg for borders */
            padding: 10px; /* Increased padding for readability */
            text-align: left;
            vertical-align: middle;
        }
        .vision-table th {
            background-color: var(--secondary-background-color); /* Use theme's secondary bg for header */
            font-weight: bold;
        }
        .vision-table .result-cell {
            text-align: center;
            width: 180px;
        }
        .vision-result {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 16px;
            font-size: 13px;
            font-weight: bold;
            color: white;
            border: 1px solid transparent;
        }
        .vision-normal {
            background-color: #2e7d32; /* Green */
            border-color: #5b9f60;
        }
        .vision-abnormal {
            background-color: #c62828; /* Red */
            border-color: #e57373;
        }
        .vision-not-tested {
            background-color: #4f4f56; /* Grey */
            border-color: #6a6a71;
            color: #d1d1d6;
        }
        /* New styles for HTML tables generated from dataframes */
        .styled-df-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Sarabun', sans-serif !important;
            font-size: 14px;
            color: var(--text-color);
        }
        .styled-df-table th, .styled-df-table td {
            border-bottom: 1px solid var(--secondary-background-color);
            padding: 10px;
            text-align: center; /* Center align all cells */
        }
        .styled-df-table td:first-child {
            text-align: left; /* Left align the first column */
        }
        .styled-df-table thead th {
            background-color: var(--secondary-background-color);
            font-weight: bold;
            vertical-align: middle;
        }
        .styled-df-table tbody tr:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)

def render_vision_details_table(person_data):
    """
    Renders a clearer, single-column result table for the vision test with corrected logic.
    """
    vision_tests = [
        # Tests with a single column where the value determines the outcome
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
        
        # Phoria tests with complex relationship to 'ผ.สายตาเขซ่อนเร้น'
        {'display': '7. ความสมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'related_keyword': 'แนวตั้งระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '8. ความสมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'related_keyword': 'แนวนอนระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '12. ความสมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'related_keyword': 'แนวนอนระยะใกล้', 'outcomes': ['ปกติ', 'ผิดปกติ']}
    ]

    # Sort the list by display name to ensure order
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
    """
    แสดงผลรายงานสมรรถภาพการได้ยิน (Audiogram) ในรูปแบบใหม่
    """
    st.markdown("<h2 style='text-align: center;'>รายงานผลการตรวจสมรรถภาพการได้ยิน (Audiometry Report)</h2>", unsafe_allow_html=True)
    
    hearing_results = interpret_audiogram(person_data, all_person_history_df)

    if hearing_results['summary'].get('overall') == "ไม่ได้เข้ารับการตรวจ":
        st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพการได้ยินในปีนี้")
        return

    def format_hearing_summary(summary_text, severity_text):
        if is_empty(summary_text) or "N/A" in summary_text:
            return f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0 0 0; color: var(--text-color);">N/A</p>'
        
        if "ปกติ" in summary_text:
            return f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0 0 0; color: var(--text-color);">{summary_text}</p>'

        main_status = severity_text if not is_empty(severity_text) and "ข้อมูลไม่เพียงพอ" not in severity_text else "การได้ยินลดลง"
        freq_str = ""
        if "ที่ระดับความถี่" in summary_text:
            parts = summary_text.split(',', 1)
            freq_str = parts[1].strip() if len(parts) > 1 else ""
        elif "การได้ยินลดลง" in summary_text:
             parts = summary_text.split(',', 1)
             freq_str = parts[1].strip() if len(parts) > 1 else ""

        if not freq_str:
            return f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0; color: var(--text-color);">{main_status}</p>'

        freqs = [f.strip().lower() for f in freq_str.split(',') if f.strip()]
        low_tones, speech_tones, high_tones = [], [], []

        for f in freqs:
            if '500' in f: low_tones.append('500 Hz')
            elif '1k' in f: speech_tones.append('1 kHz')
            elif '2k' in f: speech_tones.append('2 kHz')
            elif '3k' in f: high_tones.append('3 kHz')
            elif '4k' in f: high_tones.append('4 kHz')
            elif '6k' in f: high_tones.append('6 kHz')
            elif '8k' in f: high_tones.append('8 kHz')

        html_output = f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0; color: var(--text-color);">{main_status}</p>'
        details_parts = []
        if speech_tones: details_parts.append(f'เสียงพูด ({", ".join(speech_tones)})')
        if high_tones: details_parts.append(f'เสียงแหลม ({", ".join(high_tones)})')
        if low_tones: details_parts.append(f'เสียงทุ้ม ({", ".join(low_tones)})')

        if details_parts:
            html_output += f'<p style="font-size: 0.8rem; margin: 0.25rem 0 0 0; color: var(--text-color);">กระทบความถี่: {", ".join(details_parts)}</p>'

        return html_output.strip()

    st.markdown("<h5><b>สรุปผลการตรวจ</b></h5>", unsafe_allow_html=True)
    summary_r_raw = person_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    summary_l_raw = person_data.get('ผลตรวจการได้ยินหูซ้าย', 'N/A')
    severity_r = person_data.get('ระดับการได้ยินหูขวา', 'N/A')
    severity_l = person_data.get('ระดับการได้ยินหูซ้าย', 'N/A')

    def get_summary_color(summary_text):
        if "ปกติ" in summary_text: return "rgba(46, 125, 50, 0.2)"
        elif "N/A" in summary_text or "ไม่ได้" in summary_text: return "rgba(120, 120, 120, 0.2)"
        else: return "rgba(198, 40, 40, 0.2)"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background-color: {get_summary_color(summary_r_raw)}; padding: 1rem; border-radius: 8px; text-align: center; height: 100%;">
            <p style="font-size: 0.9rem; font-weight: bold; margin: 0; color: var(--text-color);">ระดับการได้ยินหูขวา</p>
            {format_hearing_summary(summary_r_raw, severity_r)}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background-color: {get_summary_color(summary_l_raw)}; padding: 1rem; border-radius: 8px; text-align: center; height: 100%;">
            <p style="font-size: 0.9rem; font-weight: bold; margin: 0; color: var(--text-color);">ระดับการได้ยินหูซ้าย</p>
            {format_hearing_summary(summary
