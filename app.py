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

# ==============================================================================
# 1. HELPER & INTERPRETATION FUNCTIONS (คงเดิมทั้งหมด)
#    - ฟังก์ชันตัวช่วยและการแปลผลทั้งหมดถูกคงไว้เหมือนเดิมเพื่อให้การทำงานเหมือนเดิม 100%
# ==============================================================================

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# Define Thai month mappings (global to these functions)
THAI_MONTHS_GLOBAL = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {
    "ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2,
    "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4,
    "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6,
    "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8,
    "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10,
    "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12
}

def normalize_thai_date(date_str):
    if is_empty(date_str):
        return "-"
    
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()

    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]:
        return s

    try:
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        if re.match(r'^\d{1,2}-\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                try:
                    dt = datetime(year - 543, month_num, day)
                    return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}".replace('.', '')
                except ValueError:
                    pass
    except Exception:
        pass

    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            current_ce_year = datetime.now().year
            if parsed_dt.year > current_ce_year + 50 and parsed_dt.year - 543 > 1900:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}".replace('.', '')
    except Exception:
        pass
    return s

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val):
            return None
        return float(str(val).replace(",", "").strip())
    except:
        return None

def flag(val, low=None, high=None, higher_is_better=False):
    try:
        val = float(str(val).replace(",", "").strip())
    except:
        return "-", False

    if higher_is_better and low is not None:
        return f"{val:.1f}", val < low
    if low is not None and val < low:
        return f"{val:.1f}", True
    if high is not None and val > high:
        return f"{val:.1f}", True
    return f"{val:.1f}", False

# ... (ฟังก์ชัน interpret, advice, summarize ทั้งหมดคงเดิม) ...
def kidney_summary_gfr_only(gfr_raw):
    try:
        gfr = float(str(gfr_raw).replace(",", "").strip())
        if gfr == 0: return ""
        elif gfr < 60: return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        else: return "ปกติ"
    except: return ""

def kidney_advice_from_summary(summary_text):
    if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
        return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
    return ""

def fbs_advice(fbs_raw):
    if is_empty(fbs_raw): return ""
    try:
        value = float(str(fbs_raw).replace(",", "").strip())
        if value == 0: return ""
        elif 100 <= value < 106: return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
        elif 106 <= value < 126: return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
        elif value >= 126: return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
        else: return ""
    except: return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    try:
        alp = float(alp_val); sgot = float(sgot_val); sgpt = float(sgpt_val)
        if alp == 0 or sgot == 0 or sgpt == 0: return "-"
        if alp > 120 or sgot > 36 or sgpt > 40: return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except: return ""

def liver_advice(summary_text):
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย": return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    return ""

def uric_acid_advice(value_raw):
    try:
        if float(value_raw) > 7.2: return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except: return "-"

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    try:
        chol = float(str(chol_raw).replace(",", "").strip())
        tgl = float(str(tgl_raw).replace(",", "").strip())
        ldl = float(str(ldl_raw).replace(",", "").strip())
        if chol == 0 and tgl == 0: return ""
        if chol >= 250 or tgl >= 250 or ldl >= 180: return "ไขมันในเลือดสูง"
        elif chol <= 200 and tgl <= 150: return "ปกติ"
        else: return "ไขมันในเลือดสูงเล็กน้อย"
    except: return ""

def lipids_advice(summary_text):
    if summary_text == "ไขมันในเลือดสูง": return "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
    if summary_text == "ไขมันในเลือดสูงเล็กน้อย": return "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน และออกกำลังกายเพื่อควบคุมระดับไขมัน"
    return ""

def cbc_advice(hb, hct, wbc, plt, sex="ชาย"):
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
    try:
        sbp = float(sbp); dbp = float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        else: return "ความดันค่อนข้างสูง"
    except: return "-"

def combined_health_advice(bmi, sbp, dbp):
    if is_empty(bmi) and is_empty(sbp) and is_empty(dbp): return ""
    try: bmi = float(bmi)
    except: bmi = None
    try: sbp, dbp = float(sbp), float(dbp)
    except: sbp = dbp = None
    
    bmi_text, bp_text = "", ""
    if bmi is not None:
        if bmi > 30: bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi >= 25: bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5: bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else: bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
    
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
def safe_value(val): return "-" if str(val or "").strip().lower() in ["", "nan", "none", "-"] else str(val or "").strip()
def interpret_alb(value):
    val = str(value).strip().lower()
    if val == "negative": return "ไม่พบ"
    if val in ["trace", "1+", "2+"]: return "พบโปรตีนในปัสสาวะเล็กน้อย"
    if val in ["3+", "4+"]: return "พบโปรตีนในปัสสาวะ"
    return "-"
def interpret_sugar(value):
    val = str(value).strip().lower()
    if val == "negative": return "ไม่พบ"
    if val == "trace": return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    if val in ["1+", "2+", "3+", "4+", "5+", "6+"]: return "พบน้ำตาลในปัสสาวะ"
    return "-"
def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").strip().lower()
    try:
        return float(val.split("-")[-1])
    except: return None
def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    h = parse_range_or_number(val)
    if h is None: return value
    if h <= 2: return "ปกติ"
    elif h <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else: return "พบเม็ดเลือดแดงในปัสสาวะ"
def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    h = parse_range_or_number(val)
    if h is None: return value
    if h <= 5: return "ปกติ"
    elif h <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else: return "พบเม็ดเลือดขาวในปัสสาวะ"
def advice_urine(sex, alb, sugar, rbc, wbc):
    results = [interpret_alb(alb), interpret_sugar(sugar), interpret_rbc(rbc), interpret_wbc(wbc)]
    if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"] for x in results): return ""
    if "พบน้ำตาลในปัสสาวะ" in results[1] and "เล็กน้อย" not in results[1]: return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"
    if sex == "หญิง" and "พบเม็ดเลือดแดง" in results[2] and "ปกติ" in results[3]: return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"
    if sex == "ชาย" and "พบเม็ดเลือดแดง" in results[2] and "ปกติ" in results[3]: return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"
    if "พบเม็ดเลือดขาว" in results[3] and "เล็กน้อย" not in results[3]: return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"
    return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"
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
    if test_name == "น้ำตาล (Sugar)": return interpret_sugar(val).lower() != "ไม่พบ"
    if test_name == "โปรตีน (Albumin)": return interpret_alb(val).lower() != "ไม่พบ"
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False
def interpret_stool_exam(val):
    val = str(val or "").strip().lower()
    if val in ["", "-", "none", "nan"]: return "-"
    elif val == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    elif "wbc" in val or "เม็ดเลือดขาว" in val: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val
def interpret_stool_cs(value):
    value = str(value or "").strip()
    if value in ["", "-", "none", "nan"]: return "-"
    if "ไม่พบ" in value or "ปกติ" in value: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"
def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val
def get_ekg_col_name(year):
    return "EKG" if year == (datetime.now().year + 543) else f"EKG{str(year)[-2:]}"
def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val
def hepatitis_b_advice(hbsag, hbsab, hbcab):
    hbsag, hbsab, hbcab = hbsag.lower(), hbsab.lower(), hbcab.lower()
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี"
    elif "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
    elif "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
    elif all(x == "negative" for x in [hbsag, hbsab, hbcab]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"
def merge_final_advice_grouped(messages):
    groups = {"FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []}
    for msg in messages:
        if not msg or msg.strip() in ["-", ""]: continue
        if "น้ำตาล" in msg: groups["FBS"].append(msg)
        elif "ไต" in msg: groups["ไต"].append(msg)
        elif "ตับ" in msg: groups["ตับ"].append(msg)
        elif "พิวรีน" in msg or "ยูริค" in msg: groups["ยูริค"].append(msg)
        elif "ไขมัน" in msg: groups["ไขมัน"].append(msg)
        else: groups["อื่นๆ"].append(msg)
    output = []
    for title, msgs in groups.items():
        if msgs:
            unique_msgs = list(OrderedDict.fromkeys(msgs))
            output.append(f"<b>{title}:</b> {' '.join(unique_msgs)}")
    if not output: return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"
    return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(output) + "</div>"


# ==============================================================================
# 2. REUSABLE RENDERING COMPONENTS (ยุบรวมส่วนที่ซ้ำซ้อน)
#    - ฟังก์ชันสำหรับสร้าง HTML ที่มีการเรียกใช้ซ้ำๆ
# ==============================================================================

def render_section_header(title, subtitle=None):
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div class='section-header'>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    header_html = render_section_header(title, subtitle)
    
    html_content = f"{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    html_content += "<colgroup><col style='width: 33.33%;'><col style='width: 33.33%;'><col style='width: 33.33%;'></colgroup>"
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 or i == 2 else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        # row is a list of tuples e.g. [(value, is_abnormal), (value, is_abnormal), ...]
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else f"{table_class}-row"
        
        html_content += f"<tr>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td class='{row_class}'>{row[1][0]}</td>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table></div>"
    return html_content

def render_urine_section(person_data, sex):
    # Data preparation
    urine_data = [
        ("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"),
        ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"),
        ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"),
        ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"),
        ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"),
        ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"),
        ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"),
        ("อื่นๆ", person_data.get("ORTER", "-"), "-"),
    ]

    # Convert to format needed by render_lab_table_html
    urine_rows = []
    for test, result, norm in urine_data:
        is_abn = is_urine_abnormal(test, result, norm)
        # Use safe_value for display to handle None, nan, etc.
        urine_rows.append([(test, is_abn), (safe_value(result), is_abn), (norm, is_abn)])

    # Render table using the generic function
    html_table = render_lab_table_html("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows, "urine-table")
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Render advice
    summary = advice_urine(sex, person_data.get("Alb"), person_data.get("sugar"), person_data.get("RBC1"), person_data.get("WBC1"))
    has_any_urine_result = any(not is_empty(result) for _, result, _ in urine_data)

    if not has_any_urine_result:
        pass # Do not show any advice box if no data
    elif summary:
        render_advice_box(summary, is_warning=True)
    else:
        render_advice_box("ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ", is_warning=False)

def render_stool_html_table(exam, cs):
    return f"""
    <div class='stool-container'>
        <table class='stool-table'>
            <colgroup><col style="width: 50%;"><col style="width: 50%;"></colgroup>
            <tr>
                <th>ผลตรวจอุจจาระทั่วไป</th>
                <td style='text-align: left;'>{exam if exam != "-" else "ไม่ได้เข้ารับการตรวจ"}</td>
            </tr>
            <tr>
                <th>ผลตรวจอุจจาระเพาะเชื้อ</th>
                <td style='text-align: left;'>{cs if cs != "-" else "ไม่ได้เข้ารับการตรวจ"}</td>
            </tr>
        </table>
    </div>
    """

def render_info_box(title, content, is_warning=False):
    """Reusable function to render a simple box with a title and content."""
    st.markdown(render_section_header(title), unsafe_allow_html=True)
    
    warning_style = "background-color: rgba(255, 64, 64, 0.15);" if is_warning else ""

    st.markdown(f"""
    <div class='info-box' style='{warning_style}'>
        {content}
    </div>
    """, unsafe_allow_html=True)

def render_advice_box(content, is_warning=False):
    """Reusable function for rendering the yellow/green advice boxes."""
    bg_color = "rgba(255, 255, 0, 0.2)" if is_warning else "rgba(57, 255, 20, 0.2)"
    st.markdown(f"""
        <div style='
            background-color: {bg_color};
            color: var(--text-color);
            padding: 1rem;
            border-radius: 6px;
            margin-top: 1rem;
            font-size: 14px;
        '>
            {content}
        </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 3. DATA LOADING & MAIN APP
# ==============================================================================

@st.cache_data(ttl=600)
def load_sqlite_data():
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(response.content)
            db_path = tmp.name
        
        conn = sqlite3.connect(db_path)
        df_loaded = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()

        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['HN'] = df_loaded['HN'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, int)) else str(x)).str.strip()
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None], pd.NA, inplace=True)

        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

# --- Load data when the app starts ---
df = load_sqlite_data()

# ==================== UI Setup and Search Form (Sidebar) ====================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# --- Inject ALL Custom CSS here ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td, div {
        font-family: 'Sarabun', sans-serif !important;
    }
    .report-header-container h1 { font-size: 1.8rem !important; font-weight: bold; }
    .report-header-container h2 { font-size: 1.2rem !important; color: darkgrey; font-weight: bold; }
    .report-header-container * { line-height: 1.7 !important; margin: 0.2rem 0 !important; padding: 0 !important; }
    .section-header {
        background-color: #1b5e20; color: white; text-align: center;
        padding: 0.8rem 0.5rem; font-weight: bold; border-radius: 8px;
        margin-top: 2rem; margin-bottom: 1rem; font-size: 14px;
    }
    /* Lab Table Styles */
    .lab-table, .urine-table {
        width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 14px;
    }
    .lab-table thead th, .urine-table thead th {
        background-color: var(--secondary-background-color); padding: 3px;
        text-align: center; font-weight: bold;
    }
    .lab-table td, .urine-table td { padding: 3px; text-align: center; }
    .lab-table-abn, .urine-table-abn { background-color: rgba(255, 64, 64, 0.25); }

    /* Stool Table Styles */
    .stool-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .stool-table th, .stool-table td { padding: 3px; border: 1px solid transparent; }
    .stool-table th { font-weight: bold; text-align: left; width: 50%; }

    /* Info Box Style */
    .info-box {
        background-color: var(--secondary-background-color); color: var(--text-color);
        line-height: 1.6; padding: 1.25rem; border-radius: 6px; margin-bottom: 1.5rem;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)


# --- Sidebar Search Logic (No change) ---
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
search_query = st.sidebar.text_input("กรอก HN หรือ ชื่อ-สกุล")
submitted_sidebar = st.sidebar.button("ค้นหา")

if submitted_sidebar:
    st.session_state.clear() # Clear all state on new search
    if search_query:
        search_term = search_query.strip()
        mask = (df["HN"] == search_term) if search_term.isdigit() else (df["ชื่อ-สกุล"].str.strip() == search_term)
        query_df = df[mask]
        
        if query_df.empty:
            st.sidebar.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง")
        else:
            st.session_state["search_result"] = query_df
            # Auto-select the most recent record
            most_recent_year = sorted(query_df["Year"].dropna().unique().astype(int), reverse=True)[0]
            year_df = query_df[query_df["Year"] == most_recent_year].sort_values(
                by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False
            )
            if not year_df.empty:
                st.session_state["selected_year"] = most_recent_year
                st.session_state["selected_date"] = year_df.iloc[0]["วันที่ตรวจ"]
            else:
                st.sidebar.error("❌ พบข้อมูลแต่ไม่สามารถแสดงผลได้")
    else:
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล เพื่อค้นหา")

# --- Sidebar Year/Date Selection (Simplified state management) ---
if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]
    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)

        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        
        # Determine index for year selectbox
        year_index = 0
        if "selected_year" in st.session_state and st.session_state["selected_year"] in available_years:
            year_index = available_years.index(st.session_state["selected_year"])

        selected_year = st.selectbox(
            "📅 เลือกปีที่ต้องการดูผลตรวจ",
            options=available_years,
            index=year_index,
            format_func=lambda y: f"พ.ศ. {y}",
            key="year_select"
        )
        st.session_state["selected_year"] = selected_year # Update state

        person_year_df = results_df[results_df["Year"] == selected_year].drop_duplicates(
            subset=["HN", "วันที่ตรวจ"]
        ).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)
        
        exam_dates_options = person_year_df["วันที่ตรวจ"].dropna().unique().tolist()
        
        if exam_dates_options:
            # Determine index for date selectbox
            date_index = 0
            if "selected_date" in st.session_state and st.session_state["selected_date"] in exam_dates_options:
                date_index = exam_dates_options.index(st.session_state["selected_date"])
                
            selected_date = st.selectbox(
                "🗓️ เลือกวันที่ตรวจ",
                options=exam_dates_options,
                index=date_index,
                key="date_select"
            )
            st.session_state["selected_date"] = selected_date # Update state
            
            # Find the row to display
            row_to_display = person_year_df[person_year_df["วันที่ตรวจ"] == selected_date]
            if not row_to_display.empty:
                 st.session_state["person_row"] = row_to_display.iloc[0].to_dict()
        else:
            st.info("ไม่พบข้อมูลการตรวจสำหรับปีที่เลือก")
            if "person_row" in st.session_state:
                del st.session_state["person_row"]


# ==================== Display Health Report (Main Content) ====================
if "person_row" in st.session_state:
    person = st.session_state["person_row"]

    # --- Report Header ---
    st.markdown(f"""
        <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem;">
            <h1>รายงานผลการตรวจสุขภาพ</h1>
            <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
            <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
            <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
            <p><b>วันที่ตรวจ:</b> {person.get("วันที่ตรวจ", "-")}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # --- Personal Info and Vitals ---
    try:
        weight_val = float(str(person.get("น้ำหนัก")).replace("กก.", "").strip())
        height_val = float(str(person.get("ส่วนสูง")).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2) if height_val > 0 else None
    except:
        bmi_val = None

    sbp, dbp = person.get("SBP", ""), person.get("DBP", "")
    try:
        bp_val = f"{int(float(sbp))}/{int(float(dbp))} ม.ม.ปรอท"
    except:
        bp_val = "-"
    
    bp_desc = interpret_bp(sbp, dbp)
    bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val
    advice_text = combined_health_advice(bmi_val, sbp, dbp)

    st.markdown(f"""
        <div><hr>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-top: 24px; margin-bottom: 20px; text-align: center;">
                <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
                <div><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</div>
                <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
                <div><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</div>
                <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
            </div>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
                <div><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</div>
                <div><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</div>
                <div><b>รอบเอว:</b> {person.get("รอบเอว", "-")} ซม.</div>
                <div><b>ความดันโลหิต:</b> {bp_full}</div>
                <div><b>ชีพจร:</b> {str(int(float(person.get('pulse')))) if not is_empty(person.get('pulse')) else '-'} ครั้ง/นาที</div>
            </div>
            {f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {html.escape(advice_text)}</div>" if advice_text else ""}
        </div>
    """, unsafe_allow_html=True)

    # --- Lab Results ---
    sex = str(person.get("เพศ", "ชาย")).strip()
    hb_low, hct_low = (13, 39) if sex == "ชาย" else (12, 36)

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None),
        ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
        ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
    ]

    col1, col2 = st.columns(2)
    with col1:
        cbc_rows = []
        for label, col, norm, low, high in cbc_config:
            result, is_abn = flag(get_float(col, person), low, high)
            cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])
        st.markdown(render_lab_table_html("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    
    with col2:
        blood_rows = []
        for label, col, norm, low, high, *opt in blood_config:
            result, is_abn = flag(get_float(col, person), low, high, opt[0] if opt else False)
            blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])
        st.markdown(render_lab_table_html("ผลตรวจเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    # --- Combined Recommendations ---
    advice_list = [
        kidney_advice_from_summary(kidney_summary_gfr_only(person.get("GFR"))),
        fbs_advice(person.get("FBS")),
        liver_advice(summarize_liver(person.get("ALP"), person.get("SGOT"), person.get("SGPT"))),
        uric_acid_advice(person.get("Uric Acid")),
        lipids_advice(summarize_lipids(person.get("CHOL"), person.get("TGL"), person.get("LDL"))),
        cbc_advice(person.get("Hb(%)"), person.get("HCT"), person.get("WBC (cumm)"), person.get("Plt (/mm)"), sex)
    ]
    final_advice_html = merge_final_advice_grouped(advice_list)
    has_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
    render_advice_box(final_advice_html, is_warning=has_advice)

    # --- Other Test Sections ---
    col3, col4 = st.columns(2)
    with col3:
        # Urinalysis - Use the refactored function
        render_urine_section(person, sex)

        # Stool Section
        st.markdown(render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
        exam_text = interpret_stool_exam(person.get("Stool exam", ""))
        cs_text = interpret_stool_cs(person.get("Stool C/S", ""))
        st.markdown(render_stool_html_table(exam_text, cs_text), unsafe_allow_html=True)

    with col4:
        selected_year_int = int(person.get("Year"))
        
        # X-ray Section - Use the reusable info box
        cxr_col = "CXR" if selected_year_int == (datetime.now().year + 543) else f"CXR{str(selected_year_int)[-2:]}"
        cxr_result = interpret_cxr(person.get(cxr_col, ""))
        render_info_box("ผลเอกซเรย์ (Chest X-ray)", cxr_result, is_warning="⚠️" in cxr_result)

        # EKG Section - Use the reusable info box
        ekg_col = get_ekg_col_name(selected_year_int)
        ekg_result = interpret_ekg(person.get(ekg_col, ""))
        render_info_box("ผลคลื่นไฟฟ้าหัวใจ (EKG)", ekg_result, is_warning="⚠️" in ekg_result)

        # Hepatitis B
        st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี", "Viral hepatitis B"), unsafe_allow_html=True)
        hbsag, hbsab, hbcab = safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB"))
        st.markdown(f"""
            <table class='lab-table' style='margin-bottom: 1rem;'>
                <thead><tr><th>HBsAg</th><th>HBsAb</th><th>HBcAb</th></tr></thead>
                <tbody><tr><td>{hbsag}</td><td>{hbsab}</td><td>{hbcab}</td></tr></tbody>
            </table>
        """, unsafe_allow_html=True)
        
        hep_b_advice = hepatitis_b_advice(hbsag, hbsab, hbcab)
        if not is_empty(hep_b_advice):
            is_hep_b_ok = "มีภูมิคุ้มกัน" in hep_b_advice
            render_advice_box(hep_b_advice, is_warning=not is_hep_b_ok)

    # --- Doctor's Summary ---
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if is_empty(doctor_suggestion):
        doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"
        
    st.markdown(f"""
        <div style='
            background-color: #1b5e20; color: white; padding: 1.5rem 2rem;
            border-radius: 8px; line-height: 1.6; margin-top: 2rem; font-size: 14px;'>
            <b>สรุปความเห็นของแพทย์:</b><br> {doctor_suggestion}
        </div>
        <div style='margin-top: 7rem; text-align: right; padding-right: 1rem;'>
            <div style='display: inline-block; text-align: center; width: 340px;'>
                <div style='border-bottom: 1px dotted #ccc; margin-bottom: 0.5rem; width: 100%;'></div>
                <div style='white-space: nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
                <div style='white-space: nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
