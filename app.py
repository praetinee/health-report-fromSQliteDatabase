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
import streamlit.components.v1 as components

# ==============================================================================
# SECTION 1: CORE HELPER FUNCTIONS (UNCHANGED)
# ==============================================================================

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

THAI_MONTHS_GLOBAL = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
}
THAI_MONTH_TO_NUM_GLOBAL = {v: k for k, v in THAI_MONTHS_GLOBAL.items()}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {
    "ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2,
    "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4,
    "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6,
    "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8,
    "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10,
    "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12
}

def normalize_thai_date(date_str):
    """Standardize various Thai date string formats."""
    if is_empty(date_str): return "-"
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()
    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]: return s
    try:
        if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', s):
            s = s.replace('-', '/')
            day, month, year = map(int, s.split('/'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"
        match = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match:
            day = int(match.group('day1'))
            month_str = match.group('month_str').strip().replace('.', '')
            year = int(match.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}"
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            if parsed_dt.year > datetime.now().year + 50 and parsed_dt.year - 543 > 1900:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}"
    except Exception:
        pass
    return s

def get_float(col, person_data):
    """Safely convert a value from person_data to a float."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except:
        return None

def flag(val, low=None, high=None, higher_is_better=False):
    """Format a numeric value and flag it if it's outside the normal range."""
    try:
        val = float(str(val).replace(",", "").strip())
    except:
        return "-", False
    is_abnormal = False
    if higher_is_better:
        if low is not None and val < low: is_abnormal = True
    else:
        if low is not None and val < low: is_abnormal = True
        if high is not None and val > high: is_abnormal = True
    return f"{val:.1f}", is_abnormal

def render_section_header(title, subtitle=None):
    """Render a styled section header."""
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"<div style='background-color: #1b5e20; color: white; text-align: center; padding: 0.8rem 0.5rem; font-weight: bold; border-radius: 8px; margin-top: 2rem; margin-bottom: 1rem; font-size: 14px;'>{full_title}</div>"

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    """Generate HTML for a lab results table."""
    style = f"""<style>
        .{table_class}-container {{ background-color: var(--background-color); margin-top: 1rem; }}
        .{table_class} {{ width: 100%; border-collapse: collapse; color: var(--text-color); table-layout: fixed; font-size: 14px; }}
        .{table_class} thead th {{ background-color: var(--secondary-background-color); color: var(--text-color); padding: 2px; text-align: center; font-weight: bold; border: 1px solid transparent; }}
        .{table_class} td {{ padding: 2px; border: 1px solid transparent; text-align: center; color: var(--text-color); }}
        .{table_class}-abn {{ background-color: rgba(255, 64, 64, 0.25); }}
        .{table_class}-row {{ background-color: rgba(255,255,255,0.02); }}
    </style>"""
    header_html = render_section_header(title, subtitle)
    html_content = f"{style}{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    html_content += "<colgroup><col style='width:33.33%;'><col style='width:33.33%;'><col style='width:33.33%;'></colgroup>"
    html_content += "<thead><tr>"
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

def kidney_summary_gfr_only(gfr_raw):
    """Provide a summary based on GFR value."""
    try:
        gfr = float(str(gfr_raw).replace(",", "").strip())
        if gfr == 0: return ""
        elif gfr < 60: return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        else: return "ปกติ"
    except:
        return ""

def kidney_advice_from_summary(summary_text):
    """Provide advice based on kidney summary."""
    if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
        return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
    return ""

def fbs_advice(fbs_raw):
    """Provide advice based on FBS value."""
    if is_empty(fbs_raw): return ""
    try:
        value = float(str(fbs_raw).replace(",", "").strip())
        if value == 0: return ""
        elif 100 <= value < 106: return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
        elif 106 <= value < 126: return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
        elif value >= 126: return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
        else: return ""
    except:
        return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    """Provide a summary of liver function."""
    try:
        alp, sgot, sgpt = float(alp_val), float(sgot_val), float(sgpt_val)
        if alp == 0 or sgot == 0 or sgpt == 0: return "-"
        if alp > 120 or sgot > 36 or sgpt > 40: return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except:
        return ""

def liver_advice(summary_text):
    """Provide advice based on liver summary."""
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย": return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    return ""

def uric_acid_advice(value_raw):
    """Provide advice based on Uric Acid value."""
    try:
        if float(value_raw) > 7.2: return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
    except: pass
    return ""

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    """Provide a summary of lipid profile."""
    try:
        chol, tgl, ldl = float(str(chol_raw).replace(",", "")), float(str(tgl_raw).replace(",", "")), float(str(ldl_raw).replace(",", ""))
        if chol == 0 and tgl == 0: return ""
        if chol >= 250 or tgl >= 250 or ldl >= 180: return "ไขมันในเลือดสูง"
        elif chol <= 200 and tgl <= 150: return "ปกติ"
        else: return "ไขมันในเลือดสูงเล็กน้อย"
    except:
        return ""

def lipids_advice(summary_text):
    """Provide advice based on lipid summary."""
    if summary_text == "ไขมันในเลือดสูง": return "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
    elif summary_text == "ไขมันในเลือดสูงเล็กน้อย": return "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน และออกกำลังกายเพื่อควบคุมระดับไขมัน"
    return ""

def cbc_advice(hb, hct, wbc, plt, sex="ชาย"):
    """Provide advice based on CBC results."""
    advice_parts = []
    try:
        if float(hb) < (13 if sex == "ชาย" else 12): advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    except: pass
    try:
        if float(hct) < (39 if sex == "ชาย" else 36): advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    except: pass
    try:
        wbc_val = float(wbc)
        if wbc_val < 4000: advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000: advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    except: pass
    try:
        plt_val = float(plt)
        if plt_val < 150000: advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000: advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")
    except: pass
    return " ".join(advice_parts)

def interpret_bp(sbp, dbp):
    """Interpret blood pressure readings."""
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        elif sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80: return "ความดันปกติ"
        else: return "ความดันค่อนข้างสูง"
    except:
        return "-"

def combined_health_advice(bmi, sbp, dbp):
    """Provide combined advice for BMI and blood pressure."""
    if is_empty(bmi) and is_empty(sbp) and is_empty(dbp): return ""
    try: bmi = float(bmi)
    except: bmi = None
    try: sbp, dbp = float(sbp), float(dbp)
    except: sbp, dbp = None, None
    bmi_text = ""
    if bmi is not None:
        if bmi > 30: bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi >= 25: bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5: bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else: bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
    bp_text = ""
    if sbp is not None and dbp is not None:
        if sbp >= 160 or dbp >= 100: bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
        elif sbp >= 140 or dbp >= 90: bp_text = "ความดันโลหิตอยู่ในระดับสูง"
        elif sbp >= 120 or dbp >= 80: bp_text = "ความดันโลหิตเริ่มสูง"
    if bmi is not None and "ปกติ" in bmi_text and not bp_text: return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
    if not bmi_text and bp_text: return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    if bmi_text and bp_text: return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    if bmi_text and not bp_text: return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    return ""

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
def safe_value(val): return "-" if str(val or "").strip().lower() in ["", "nan", "none", "-"] else str(val).strip()

def interpret_alb(value):
    """Interpret albumin in urine results."""
    val = str(value).strip().lower()
    if val == "negative": return "ไม่พบ"
    elif val in ["trace", "1+", "2+"]: return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif val in ["3+", "4+"]: return "พบโปรตีนในปัสสาวะ"
    return "-"

def interpret_sugar(value):
    """Interpret sugar in urine results."""
    val = str(value).strip().lower()
    if val == "negative": return "ไม่พบ"
    elif val == "trace": return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif val in ["1+", "2+", "3+", "4+", "5+", "6+"]: return "พบน้ำตาลในปัสสาวะ"
    return "-"

def parse_range_or_number(val):
    """Parse a string that could be a number or a range (e.g., '2-5')."""
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val: return map(float, val.split("-"))
        else: num = float(val); return num, num
    except:
        return None, None

def interpret_rbc(value):
    """Interpret RBC in urine results."""
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    low, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 2: return "ปกติ"
    elif high <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else: return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    """Interpret WBC in urine results."""
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    low, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 5: return "ปกติ"
    elif high <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else: return "พบเม็ดเลือดขาวในปัสสาวะ"

def advice_urine(sex, alb, sugar, rbc, wbc):
    """Provide advice based on urinalysis results."""
    alb_t, sugar_t, rbc_t, wbc_t = interpret_alb(alb), interpret_sugar(sugar), interpret_rbc(rbc), interpret_wbc(wbc)
    if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"] for x in [alb_t, sugar_t, rbc_t, wbc_t]): return ""
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "เล็กน้อย" not in sugar_t: return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"
    if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t: return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"
    if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t: return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"
    if "พบเม็ดเลือดขาว" in wbc_t and "เล็กน้อย" not in wbc_t: return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"
    return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"

def is_urine_abnormal(test_name, value, normal_range):
    """Check if a urine test result is abnormal."""
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]: return False
    try:
        if "ph" in test_name.lower(): return not (5.0 <= float(val) <= 8.0)
        if "sp.gr" in test_name.lower(): return not (1.003 <= float(val) <= 1.030)
    except: return True
    if "rbc" in test_name.lower(): return "พบ" in interpret_rbc(val).lower()
    if "wbc" in test_name.lower(): return "พบ" in interpret_wbc(val).lower()
    if "sugar" in test_name.lower(): return interpret_sugar(val).lower() != "ไม่พบ"
    if "albumin" in test_name.lower(): return interpret_alb(val).lower() != "ไม่พบ"
    if "colour" in test_name.lower(): return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False

def render_urine_section(person_data, sex, year_selected):
    """Render the entire urinalysis section with table and advice."""
    urine_data = [
        ("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"),
        ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"), ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"),
        ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"),
        ("อื่นๆ", person_data.get("ORTER", "-"), "-"),
    ]
    st.markdown(render_lab_table_html("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], [[(t, is_urine_abnormal(t, r, n)), (safe_value(r), is_urine_abnormal(t, r, n)), (n, is_urine_abnormal(t, r, n))] for t, r, n in urine_data]), unsafe_allow_html=True)
    summary = advice_urine(sex, person_data.get("Alb"), person_data.get("sugar"), person_data.get("RBC1"), person_data.get("WBC1"))
    if not any(not is_empty(r) for _, r, _ in urine_data): pass
    elif summary: st.markdown(f"<div style='background-color:rgba(255,255,0,0.2);color:var(--text-color);padding:1rem;border-radius:6px;margin-top:1rem;font-size:14px;'>{summary}</div>", unsafe_allow_html=True)
    else: st.markdown("<div style='background-color:rgba(57,255,20,0.2);color:var(--text-color);padding:1rem;border-radius:6px;margin-top:1rem;font-size:14px;'>ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ</div>", unsafe_allow_html=True)

def interpret_stool_exam(val):
    """Interpret stool exam results."""
    val = str(val or "").strip().lower()
    if val in ["", "-", "none", "nan"]: return "-"
    if val == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val or "เม็ดเลือดขาว" in val: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    """Interpret stool culture and sensitivity results."""
    value = str(value or "").strip()
    if value in ["", "-", "none", "nan"]: return "-"
    if "ไม่พบ" in value or "ปกติ" in value: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
    """Generate HTML table for stool exam results."""
    return f"""<div class='stool-container' style="margin-top:1rem;"><table class='stool-table' style="width:100%;border-collapse:collapse;color:var(--text-color);font-size:14px;">
        <colgroup><col style="width:50%;"><col style="width:50%;"></colgroup>
        <tr><th style="background-color:var(--secondary-background-color);padding:3px 2px;text-align:left;font-weight:bold;">ผลตรวจอุจจาระทั่วไป</th><td style='text-align:left;padding:3px 2px;'>{exam if exam != "-" else "ไม่ได้เข้ารับการตรวจ"}</td></tr>
        <tr><th style="background-color:var(--secondary-background-color);padding:3px 2px;text-align:left;font-weight:bold;">ผลตรวจอุจจาระเพาะเชื้อ</th><td style='text-align:left;padding:3px 2px;'>{cs if cs != "-" else "ไม่ได้เข้ารับการตรวจ"}</td></tr>
    </table></div>"""

def interpret_cxr(val):
    """Interpret Chest X-ray results."""
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(k in val.lower() for k in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    """Get the correct EKG column name based on the year."""
    return "EKG" if year == (datetime.now().year + 543) else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    """Interpret EKG results."""
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(k in val.lower() for k in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    """Provide advice based on Hepatitis B panel results."""
    hbsag, hbsab, hbcab = hbsag.lower(), hbsab.lower(), hbcab.lower()
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี"
    if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
    if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
    if all(x in ["negative", "-"] for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

def merge_final_advice_grouped(messages):
    """Group and merge all health advice messages."""
    groups = {"FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []}
    for msg in messages:
        if not msg or msg.strip() in ["-", ""]: continue
        if "น้ำตาล" in msg: groups["FBS"].append(msg)
        elif "ไต" in msg: groups["ไต"].append(msg)
        elif "ตับ" in msg: groups["ตับ"].append(msg)
        elif any(k in msg for k in ["พิวรีน", "ยูริค"]): groups["ยูริค"].append(msg)
        elif "ไขมัน" in msg: groups["ไขมัน"].append(msg)
        else: groups["อื่นๆ"].append(msg)
    output = [f"<b>{title}:</b> {' '.join(list(OrderedDict.fromkeys(msgs)))}" for title, msgs in groups.items() if msgs]
    return "<div style='margin-bottom:0.75rem;'>" + "</div><div style='margin-bottom:0.75rem;'>".join(output) + "</div>" if output else "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

# ==============================================================================
# SECTION 2: PRINTING FUNCTIONALITY (REVISED & RE-IMPLEMENTED)
# ==============================================================================

PRINT_CSS = """
<style>
    /* Hide print view by default */
    .print-view { display: none; }

    @media print {
        @page {
            size: A4;
            margin: 0.8cm;
        }
        /* Hide the live view and sidebar/header when printing */
        .main-view, [data-testid="stSidebar"], header[data-testid="stHeader"] {
            display: none !important;
        }
        /* Show the print-specific view */
        .print-view {
            display: block !important;
        }
        /* General print styles */
        * {
            background: transparent !important;
            color: #000 !important;
            box-shadow: none !important;
            text-shadow: none !important;
            print-color-adjust: exact !important;
            font-family: 'Sarabun', sans-serif !important;
        }
        body {
            padding: 0 !important;
            margin: 0 !important;
        }
        h1 { font-size: 14pt !important; font-weight: bold; text-align: center; margin:0; padding:0; }
        h2 { font-size: 11pt !important; text-align: center; margin:0 0 8px 0; padding:0; color: #333 !important; }
        p, div, table, span { font-size: 9pt !important; line-height: 1.3 !important; }
        .patient-info-print { border: 1px solid #000; padding: 5px; margin-bottom: 8px; text-align: left; }
        .patient-info-print b { font-weight: bold; }
        .main-content-flex { display: flex; flex-direction: row; gap: 0.7cm; width: 100%; }
        .column-left { width: 55%; }
        .column-right { width: 45%; }
        .section-header-print {
            background-color: #E0E0E0 !important;
            font-weight: bold;
            text-align: center;
            padding: 3px;
            margin-top: 8px;
            margin-bottom: 4px;
            border-radius: 3px;
        }
        table { width: 100%; border-collapse: collapse; page-break-inside: avoid; }
        th, td { border: 1px solid #ccc; padding: 2px 4px; vertical-align: top; }
        th { font-weight: bold; background-color: #F5F5F5 !important; }
        .lab-table-print .test { width: 45%; }
        .lab-table-print .result { width: 20%; text-align: center; }
        .lab-table-print .norm { width: 35%; }
        .lab-table-abn td { background-color: #F2F2F2 !important; font-weight: bold; }
        .other-results { margin: 0; padding: 3px 4px; border-bottom: 1px dotted #eee; }
        .advice-box { padding: 5px; border: 1px solid #ccc; border-radius: 4px; page-break-inside: avoid; margin-top: 4px; }
        .advice-box b { font-weight: bold; }
        .footer-section {
            position: fixed;
            bottom: 0.8cm;
            left: 0.8cm;
            right: 0.8cm;
            border-top: 1px solid #000;
            padding-top: 5px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .signature-area { text-align: center; }
    }
</style>
"""

def _render_lab_table_for_print(rows):
    """Helper to render a lab table for the print view."""
    html = "<table class='lab-table-print'><thead><tr><th class='test'>การตรวจ</th><th class='result'>ผล</th><th class='norm'>ค่าปกติ</th></tr></thead><tbody>"
    for label, result, norm, is_abn in rows:
        row_class = "lab-table-abn" if is_abn else ""
        html += f"<tr class='{row_class}'><td>{label}</td><td class='result'>{result}</td><td>{norm}</td></tr>"
    html += "</tbody></table>"
    return html

def _render_urine_table_for_print(person_data):
    """Helper to render the urine table for the print view."""
    urine_data = [
        ("สี", person_data.get("Color", "-"), "Yellow"), ("น้ำตาล", person_data.get("sugar", "-"), "Negative"),
        ("โปรตีน", person_data.get("Alb", "-"), "Negative"), ("pH", person_data.get("pH", "-"), "5.0-8.0"),
        ("ถ.พ.", person_data.get("Spgr", "-"), "1.003-1.030"), ("RBC", person_data.get("RBC1", "-"), "0-2"),
        ("WBC", person_data.get("WBC1", "-"), "0-5"),
    ]
    html = "<table class='urine-table-print'><thead><tr><th class='test'>การตรวจ</th><th class='result'>ผล</th><th class='norm'>ค่าปกติ</th></tr></thead><tbody>"
    for test, result, normal in urine_data:
        is_abn = is_urine_abnormal(test, result, normal)
        row_class = "lab-table-abn" if is_abn else ""
        result_display = str(safe_value(result)).replace("negative", "Neg").replace("trace", "Tr")
        html += f"<tr class='{row_class}'><td>{test}</td><td class='result'>{result_display}</td><td>{normal}</td></tr>"
    html += "</tbody></table>"
    return html

def generate_printable_html(person_data):
    """Generates a self-contained HTML string formatted for printing."""
    if not person_data: return ""
    sex = str(person_data.get("เพศ", "ไม่ระบุ")).strip()
    year_selected = int(person_data.get("Year", datetime.now().year + 543))
    try:
        age_str = str(int(float(person_data.get('อายุ', '-'))))
        hn_str = str(int(float(person_data.get('HN', '-'))))
    except (ValueError, TypeError):
        age_str = str(person_data.get('อายุ', '-'))
        hn_str = str(person_data.get('HN', '-'))

    sbp, dbp = person_data.get("SBP", ""), person_data.get("DBP", "")
    bp_val = f"{sbp}/{dbp}" if sbp and dbp else "-"
    bp_interp = interpret_bp(sbp, dbp)
    try:
        bmi_str = f"{float(person_data.get('BMI', 0)):.1f}"
    except (ValueError, TypeError):
        bmi_str = "-"
    
    # --- Data Preparation ---
    lab_configs = [
        ("น้ำตาล (FBS)", "FBS", "74-106", 74, 106, False),
        ("ไต (Creatinine)", "Cr", "0.5-1.17", 0.5, 1.17, False),
        ("ไต (eGFR)", "GFR", ">60", 60, None, True),
        ("เก๊าท์ (Uric Acid)", "Uric Acid", "2.6-7.2", 2.6, 7.2, False),
        ("ไขมัน (Cholesterol)", "CHOL", "<200", None, 200, False),
        ("ไขมัน (Triglyceride)", "TGL", "<150", None, 150, False),
        ("ไขมันดี (HDL)", "HDL", ">40", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "<160", None, 160, False),
        ("ตับ (SGOT)", "SGOT", "<37", None, 37, False),
        ("ตับ (SGPT)", "SGPT", "<41", None, 41, False),
        ("ตับ (ALP)", "ALP", "30-120", 30, 120, False),
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ช>13,ญ>12", 13 if sex=="ชาย" else 12, None, False),
        ("ฮีมาโตคริต (Hct)", "HCT", "ช>39,ญ>36", 39 if sex=="ชาย" else 36, None, False),
        ("เม็ดเลือดขาว (WBC)", "WBC (cumm)", "4-10k", 4000, 10000, False),
        ("เกล็ดเลือด (Plt)", "Plt (/mm)", "150-500k", 150000, 500000, False),
    ]
    lab_rows_data = []
    for label, col, norm, low, high, higher_is_better in lab_configs:
        result, is_abn = flag(get_float(col, person_data), low, high, higher_is_better)
        lab_rows_data.append((label, result, norm, is_abn))

    cxr_result = interpret_cxr(person_data.get(f"CXR{str(year_selected)[-2:]}" if year_selected != (datetime.now().year + 543) else "CXR", ""))
    ekg_result = interpret_ekg(person_data.get(get_ekg_col_name(year_selected), ""))
    hep_b_advice = hepatitis_b_advice(safe_text(person_data.get("HbsAg")), safe_text(person_data.get("HbsAb")), safe_text(person_data.get("HBcAB")))
    
    advice_list = [
        combined_health_advice(bmi_str, sbp, dbp), kidney_advice_from_summary(kidney_summary_gfr_only(person_data.get("GFR"))),
        fbs_advice(person_data.get("FBS")), liver_advice(summarize_liver(person_data.get("ALP"), person_data.get("SGOT"), person_data.get("SGPT"))),
        uric_acid_advice(person_data.get("Uric Acid")), lipids_advice(summarize_lipids(person_data.get("CHOL"), person_data.get("TGL"), person_data.get("LDL"))),
        cbc_advice(person_data.get("Hb(%)"), person_data.get("HCT"), person_data.get("WBC (cumm)"), person_data.get("Plt (/mm)"), sex),
        advice_urine(sex, person_data.get("Alb"), person_data.get("sugar"), person_data.get("RBC1"), person_data.get("WBC1"))
    ]
    final_advice_html = merge_final_advice_grouped([msg for msg in advice_list if msg])
    doctor_suggestion = safe_text(person_data.get("DOCTER suggest", "ไม่มี"))

    # --- HTML Assembly ---
    return f"""
    <div class="report-header-container">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย -</h2>
    </div>
    <div class="patient-info-print">
        <b>ชื่อ-สกุล:</b> {person_data.get('ชื่อ-สกุล', '-')} &nbsp; <b>อายุ:</b> {age_str} ปี &nbsp; <b>เพศ:</b> {sex} &nbsp; <b>HN:</b> {hn_str} &nbsp; <b>วันที่ตรวจ:</b> {person_data.get('วันที่ตรวจ', '-')} <br>
        <b>น้ำหนัก:</b> {person_data.get("น้ำหนัก", "-")} กก. &nbsp; <b>ส่วนสูง:</b> {person_data.get("ส่วนสูง", "-")} ซม. &nbsp; <b>BMI:</b> {bmi_str} &nbsp; <b>ความดัน:</b> {bp_val} ({bp_interp})
    </div>
    <div class="main-content-flex">
        <div class="column-left">{_render_lab_table_for_print(lab_rows_data)}</div>
        <div class="column-right">
            <div class="section-header-print">ผลการตรวจปัสสาวะ</div>{_render_urine_table_for_print(person_data)}
            <div class="section-header-print">ผลการตรวจอื่นๆ</div>
            <p class="other-results"><b>X-Ray:</b> {cxr_result}</p>
            <p class="other-results"><b>EKG:</b> {ekg_result}</p>
            <p class="other-results"><b>Hepatitis B:</b> {hep_b_advice}</p>
            <div class="section-header-print">คำแนะนำเบื้องต้น</div>
            <div class="advice-box">{final_advice_html}</div>
        </div>
    </div>
    <div class="footer-section">
        <div><b>สรุปความเห็นของแพทย์:</b> {doctor_suggestion}</div>
        <div class="signature-area">...........................................................<br><span>(นายแพทย์นพรัตน์ รัชฎาพร) ว.26674</span></div>
    </div>"""

def print_section():
    """Injects JavaScript to trigger the browser's print dialog."""
    components.html('<script>window.print();</script>', height=0)

# ==============================================================================
# SECTION 3: MAIN APP LOGIC
# ==============================================================================

@st.cache_data(ttl=600)
def load_sqlite_data():
    """Load data from a SQLite database file hosted on Google Drive."""
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        response = requests.get(f"https://drive.google.com/uc?export=download&id={file_id}")
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(response.content)
            tmp.flush()
            conn = sqlite3.connect(tmp.name)
            df_loaded = pd.read_sql("SELECT * FROM health_data", conn)
            conn.close()
        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['HN'] = df_loaded['HN'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, int)) else str(x)).str.strip()
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None], pd.NA, inplace=True)
        try:
            weight = pd.to_numeric(df_loaded['น้ำหนัก'], errors='coerce')
            height = pd.to_numeric(df_loaded['ส่วนสูง'], errors='coerce')
            df_loaded['BMI'] = (weight / ((height / 100) ** 2)).round(1)
        except Exception:
            df_loaded['BMI'] = None
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

df = load_sqlite_data()
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# Inject CSS for printing and custom fonts
st.markdown(PRINT_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    :root, body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td, div { font-family: 'Sarabun', sans-serif !important; }
    .report-header-container h1 { font-size: 1.8rem !important; } .report-header-container h2 { font-size: 1.2rem !important; color: darkgrey; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar for search and navigation ---
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
search_query = st.sidebar.text_input("กรอก HN หรือ ชื่อ-สกุล")
if st.sidebar.button("ค้นหา"):
    st.session_state.clear()
    if search_query:
        if search_query.isdigit():
            results = df[df["HN"] == search_query]
        else:
            results = df[df["ชื่อ-สกุล"].str.strip() == search_query]
        if results.empty:
            st.sidebar.error("❌ ไม่พบข้อมูล")
        else:
            st.session_state["search_result"] = results
    else:
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล")

if "search_result" in st.session_state:
    results_df = st.session_state.search_result
    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)
        
        def thai_date_str_to_datetime(date_str):
            try:
                parts = date_str.split()
                if len(parts) != 3: return datetime.min
                day, month_name, year = int(parts[0]), parts[1], int(parts[2])
                month_num = THAI_MONTH_TO_NUM_GLOBAL.get(month_name)
                if month_num: return datetime(year - 543, month_num, day) # Convert BE to CE for sorting
            except (ValueError, IndexError): return datetime.min
            return datetime.min

        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        
        year_index = 0
        if 'selected_year' in st.session_state and st.session_state.selected_year in available_years:
            year_index = available_years.index(st.session_state.selected_year)
        
        selected_year = st.selectbox("📅 เลือกปี", available_years, index=year_index, key="year_select", on_change=lambda: st.session_state.update(selected_year=st.session_state.year_select))
        
        person_year_df = results_df[(results_df["Year"] == selected_year) & (results_df["HN"] == results_df.iloc[0]["HN"])]
        exam_dates_options = sorted(person_year_df["วันที่ตรวจ"].dropna().unique(), key=thai_date_str_to_datetime, reverse=True)
        
        if exam_dates_options:
            date_index = 0
            if 'selected_date' in st.session_state and st.session_state.selected_date in exam_dates_options:
                date_index = exam_dates_options.index(st.session_state.selected_date)

            selected_date = st.selectbox("🗓️ เลือกวันที่", exam_dates_options, index=date_index, key="date_select", on_change=lambda: st.session_state.update(selected_date=st.session_state.date_select))
            
            person_df = person_year_df[person_year_df["วันที่ตรวจ"] == selected_date]
            if not person_df.empty:
                st.session_state["person_row"] = person_df.iloc[0].to_dict()

        if st.session_state.get('person_row'):
            st.markdown("---")
            if st.sidebar.button("🖨️ พิมพ์รายงานนี้"):
                print_section()

# --- Main content area ---
if "person_row" in st.session_state:
    person = st.session_state.person_row
    
    # Generate and inject the hidden printable HTML
    st.markdown(f'<div class="print-view">{generate_printable_html(person)}</div>', unsafe_allow_html=True)
    
    # Start of the live view container
    st.markdown('<div class="main-view">', unsafe_allow_html=True)
    
    # Header Section
    st.markdown(f"""<div class="report-header-container" style="text-align:center; margin-bottom:0.5rem;">
        <h1>รายงานผลการตรวจสุขภาพ</h1><h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        <p><b>วันที่ตรวจ:</b> {person.get("วันที่ตรวจ", "-")}</p></div>""", unsafe_allow_html=True)
    
    # Patient Info and Vitals
    try: bmi_val = float(person.get("BMI", 0))
    except: bmi_val = 0
    sbp, dbp = person.get("SBP", ""), person.get("DBP", "")
    bp_full = f"{sbp}/{dbp} - {interpret_bp(sbp, dbp)}" if sbp and dbp else "-"

    st.markdown(f"""<div><hr>
        <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:32px; margin:24px 0 20px 0; text-align:center;">
            <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {int(get_float('อายุ', person)) if get_float('อายุ', person) else '-'} ปี</div>
            <div><b>เพศ:</b> {person.get('เพศ', '-')}</div><div><b>HN:</b> {person.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div></div>
        <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:32px; margin-bottom:16px; text-align:center;">
            <div><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</div><div><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</div>
            <div><b>รอบเอว:</b> {person.get("รอบเอว", "-")} ซม.</div><div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {int(get_float('pulse', person)) if get_float('pulse', person) else '-'} ครั้ง/นาที</div></div>
        <div style='margin-top:16px; text-align:center;'><b>คำแนะนำ:</b> {html.escape(combined_health_advice(bmi_val, sbp, dbp) or "")}</div>
    </div>""", unsafe_allow_html=True)

    # Blood Test Results
    sex = str(person.get("เพศ", "")).strip() or "ไม่ระบุ"
    hb_low, hct_low = (13, 39) if sex == "ชาย" else (12, 36)
    
    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None),
        ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106, False),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2, False),
        ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120, False),
        ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37, False),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41, False),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200, False),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150, False),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160, False),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20, False),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17, False),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
    ]
    cbc_rows = []
    for l, c, n, lo, hi in cbc_config:
        f = flag(get_float(c, person), lo, hi)
        cbc_rows.append([(l, f[1]), (f[0], f[1]), (n, f[1])])
        
    blood_rows = []
    for l, c, n, lo, hi, hig in blood_config:
        f = flag(get_float(c, person), lo, hi, hig)
        blood_rows.append([(l, f[1]), (f[0], f[1]), (n, f[1])])

    _, c1, c2, _ = st.columns([0.5, 3, 3, 0.5])
    with c1: st.markdown(render_lab_table_html("ผลตรวจ CBC (Complete Blood Count)", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    with c2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)
    
    # General Advice Section
    advice_list = [
        kidney_advice_from_summary(kidney_summary_gfr_only(person.get("GFR"))), fbs_advice(person.get("FBS")),
        liver_advice(summarize_liver(person.get("ALP"), person.get("SGOT"), person.get("SGPT"))),
        uric_acid_advice(person.get("Uric Acid")), lipids_advice(summarize_lipids(person.get("CHOL"), person.get("TGL"), person.get("LDL"))),
        cbc_advice(person.get("Hb(%)"), person.get("HCT"), person.get("WBC (cumm)"), person.get("Plt (/mm)"), sex)
    ]
    final_advice_html = merge_final_advice_grouped(advice_list)
    has_general_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
    bg_color = "rgba(255, 255, 0, 0.2)" if has_general_advice else "rgba(57, 255, 20, 0.2)"
    _, main_col, _ = st.columns([0.5, 6, 0.5])
    with main_col:
        st.markdown(f"<div style='background-color:{bg_color};padding:1rem 2.5rem;border-radius:10px;line-height:1.5;color:var(--text-color);font-size:14px;'>{final_advice_html}</div>", unsafe_allow_html=True)

    # Other Tests Section
    selected_year = st.session_state.get("selected_year", datetime.now().year + 543)
    with st.container():
        _, c_left, c_right, _ = st.columns([0.5, 3, 3, 0.5])
        with c_left:
            render_urine_section(person, sex, selected_year)
            st.markdown(render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)
        with c_right:
            st.markdown(render_section_header("ผลเอกซเรย์ (Chest X-ray)"), unsafe_allow_html=True)
            st.markdown(f"""<div style='background-color:var(--background-color);color:var(--text-color);line-height:1.6;padding:1.25rem;border-radius:6px;margin-bottom:1.5rem;font-size:14px;'>
                {interpret_cxr(person.get(f'CXR{str(selected_year)[-2:]}' if selected_year != (datetime.now().year + 543) else 'CXR', ''))}</div>""", unsafe_allow_html=True)
            st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ (EKG)"), unsafe_allow_html=True)
            st.markdown(f"""<div style='background-color:var(--secondary-background-color);color:var(--text-color);line-height:1.6;padding:1.25rem;border-radius:6px;margin-bottom:1.5rem;font-size:14px;'>
                {interpret_ekg(person.get(get_ekg_col_name(selected_year), ''))}</div>""", unsafe_allow_html=True)
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบเอ (Viral hepatitis A)"), unsafe_allow_html=True)
            st.markdown(f"""<div style='padding:1rem;border-radius:6px;margin-bottom:1.5rem;background-color:rgba(255,255,255,0.05);font-size:14px;'>
                {safe_text(person.get("Hepatitis A"))}</div>""", unsafe_allow_html=True)
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)"), unsafe_allow_html=True)
            st.markdown(f"""<div style="margin-bottom:1rem;"><table style='width:100%;text-align:center;border-collapse:collapse;font-size:14px;'>
                <thead><tr><th style="padding:8px;border:1px solid transparent;">HBsAg</th><th style="padding:8px;border:1px solid transparent;">HBsAb</th><th style="padding:8px;border:1px solid transparent;">HBcAb</th></tr></thead>
                <tbody><tr><td>{safe_text(person.get("HbsAg"))}</td><td>{safe_text(person.get("HbsAb"))}</td><td>{safe_text(person.get("HBcAB"))}</td></tr></tbody>
            </table></div>""", unsafe_allow_html=True)
            st.markdown(f"""<div style='padding:0.75rem 1rem;background-color:rgba(255,255,255,0.05);border-radius:6px;margin-bottom:1.5rem;line-height:1.8;font-size:14px;'>
                <b>วันที่ตรวจภูมิคุ้มกัน:</b> {normalize_thai_date(person.get("ปีตรวจHEP"))}<br>
                <b>ประวัติโรคไวรัสตับอักเสบบี ปี พ.ศ. {selected_year}:</b> {safe_text(person.get("สรุปประวัติ Hepb"))}<br>
                <b>ประวัติการได้รับวัคซีนในปี พ.ศ. {selected_year}:</b> {safe_text(person.get("วัคซีนhep b 67"))}</div>""", unsafe_allow_html=True)
            advice = hepatitis_b_advice(safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB")))
            bg_color_hep = "rgba(57, 255, 20, 0.2)" if advice.strip() == "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี" else "rgba(255, 255, 0, 0.2)"
            st.markdown(f"<div style='line-height:1.6;padding:1rem 1.5rem;border-radius:6px;background-color:{bg_color_hep};color:var(--text-color);margin-bottom:1.5rem;font-size:14px;'>{advice}</div>", unsafe_allow_html=True)

    # Doctor's Suggestion and Signature
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if is_empty(doctor_suggestion): doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"
    _, doc_col, _ = st.columns([0.5, 6, 0.5])
    with doc_col:
        st.markdown(f"""<div style='background-color:#1b5e20;color:white;padding:1.5rem 2rem;border-radius:8px;line-height:1.6;margin:2rem 0;font-size:14px;'>
            <b>สรุปความเห็นของแพทย์:</b><br> {doctor_suggestion}</div>
            <div style='margin-top:7rem;text-align:right;padding-right:1rem;'>
            <div style='display:inline-block;text-align:center;width:340px;'>
            <div style='border-bottom:1px dotted #ccc;margin-bottom:0.5rem;width:100%;'></div>
            <div style='white-space:nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style='white-space:nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
            </div></div>""", unsafe_allow_html=True)
            
    # End of the live view container
    st.markdown('</div>', unsafe_allow_html=True)
