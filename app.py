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

# --- Helper Functions (Existing) ---
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

def kidney_summary_gfr_only(gfr_raw):
    """Generates a summary for kidney function based on GFR."""
    try:
        gfr = float(str(gfr_raw).replace(",", "").strip())
        if gfr == 0: return ""
        return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย" if gfr < 60 else "ปกติ"
    except: return ""

def kidney_advice_from_summary(summary_text):
    """Generates advice based on kidney summary."""
    if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
        return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
    return ""

def fbs_advice(fbs_raw):
    """Generates advice based on Fasting Blood Sugar (FBS) level."""
    if is_empty(fbs_raw): return ""
    try:
        value = float(str(fbs_raw).replace(",", "").strip())
        if value == 0: return ""
        if 100 <= value < 106: return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
        if 106 <= value < 126: return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
        if value >= 126: return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
        return ""
    except: return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    """Summarizes liver function based on ALP, SGOT, and SGPT."""
    try:
        alp, sgot, sgpt = float(alp_val), float(sgot_val), float(sgpt_val)
        if alp == 0 or sgot == 0 or sgpt == 0: return "-"
        if alp > 120 or sgot > 36 or sgpt > 40: return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except: return ""

def liver_advice(summary_text):
    """Generates advice based on liver function summary."""
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย": return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    return ""

def uric_acid_advice(value_raw):
    """Generates advice based on Uric Acid level."""
    try:
        if float(value_raw) > 7.2: return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except: return "-"

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    """Summarizes lipid profile."""
    try:
        chol, tgl, ldl = float(str(chol_raw).replace(",", "").strip()), float(str(tgl_raw).replace(",", "").strip()), float(str(ldl_raw).replace(",", "").strip())
        if chol == 0 and tgl == 0: return ""
        if chol >= 250 or tgl >= 250 or ldl >= 180: return "ไขมันในเลือดสูง"
        if chol <= 200 and tgl <= 150: return "ปกติ"
        return "ไขมันในเลือดสูงเล็กน้อย"
    except: return ""

def lipids_advice(summary_text):
    """Generates advice based on lipid summary."""
    if summary_text == "ไขมันในเลือดสูง": return "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
    if summary_text == "ไขมันในเลือดสูงเล็กน้อย": return "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน และออกกำลังกายเพื่อควบคุมระดับไขมัน"
    return ""

def cbc_advice(hb, hct, wbc, plt, sex="ชาย"):
    """Generates advice based on Complete Blood Count (CBC) results."""
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

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val
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
def advice_urine(sex, alb, sugar, rbc, wbc):
    alb_t, sugar_t, rbc_t, wbc_t = interpret_alb(alb), interpret_sugar(sugar), interpret_rbc(rbc), interpret_wbc(wbc)
    if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"] for x in [alb_t, sugar_t, rbc_t, wbc_t]): return ""
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "เล็กน้อย" not in sugar_t: return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"
    if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t: return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"
    if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t: return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"
    if "พบเม็ดเลือดขาว" in wbc_t and "เล็กน้อย" not in wbc_t: return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"
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
    summary = advice_urine(sex, person_data.get("Alb", "-"), person_data.get("sugar", "-"), person_data.get("RBC1", "-"), person_data.get("WBC1", "-"))
    return summary, any(not is_empty(val) for _, val, _ in urine_data)

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

def merge_final_advice_grouped(messages):
    """Merges and groups final advice messages."""
    groups = {"FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []}
    for msg in messages:
        if not msg or msg.strip() in ["-", ""]: continue
        if "น้ำตาล" in msg: groups["FBS"].append(msg)
        elif "ไต" in msg: groups["ไต"].append(msg)
        elif "ตับ" in msg: groups["ตับ"].append(msg)
        elif "พิวรีน" in msg or "ยูริค" in msg: groups["ยูริค"].append(msg)
        elif "ไขมัน" in msg: groups["ไขมัน"].append(msg)
        else: groups["อื่นๆ"].append(msg)
    output = [f"<b>{title}:</b> {' '.join(list(OrderedDict.fromkeys(msgs)))}" for title, msgs in groups.items() if msgs]
    return "<br>".join(output) if output else "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

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
    """Check for any vision test data, summary or detailed."""
    summary_keys = ['สายตา', 'ตาบอดสี']
    detailed_keys = [
        'ป.การรวมภาพ', 'ป.ความชัดของภาพระยะไกล', 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)',
        'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'ป.การกะระยะและมองความชัดลึกของภาพ',
        'ป.การจำแนกสี', 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'ป.ความชัดของภาพระยะใกล้',
        'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)',
        'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'ป.ลานสายตา'
    ]
    return any(not is_empty(person_data.get(key)) for key in summary_keys + detailed_keys)


def has_hearing_data(person_data):
    """Check for hearing test data."""
    return not is_empty(person_data.get('การได้ยิน'))

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

def combined_health_advice(bmi, sbp, dbp):
    """Generates combined advice for BMI and blood pressure."""
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
        weight_val = float(str(person_data.get("น้ำหนัก", "-")).replace("กก.", "").strip())
        height_val = float(str(person_data.get("ส่วนสูง", "-")).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2) if height_val > 0 else None
    except: bmi_val = None
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
    summary_advice = html.escape(combined_health_advice(bmi_val, person_data.get("SBP", ""), person_data.get("DBP", "")))
    
    st.markdown(f"""<div class="personal-info-container">
        <hr style="margin-top: 0.5rem; margin-bottom: 1.5rem;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; margin-bottom: 1rem; text-align: center; line-height: 1.8;">
            <div><b>ชื่อ-สกุล:</b> {person_data.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')} ปี</div>
            <div><b>เพศ:</b> {person_data.get('เพศ', '-')}</div>
            <div><b>HN:</b> {str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person_data.get('หน่วยงาน', '-')}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; margin-bottom: 1.5rem; text-align: center; line-height: 1.8;">
            <div><b>น้ำหนัก:</b> {weight_display}</div>
            <div><b>ส่วนสูง:</b> {height_display}</div>
            <div><b>รอบเอว:</b> {waist_display}</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {pulse}</div>
        </div>
        {f"<div style='margin-top: 1rem; text-align: center;'><b>คำแนะนำ:</b> {summary_advice}</div>" if summary_advice else ""}
    </div>""", unsafe_allow_html=True)

# --- NEW: Centralized CSS Injection ---
def inject_custom_css():
    st.markdown("""
    <style>
        .vision-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-top: 1.5rem;
        }
        .vision-table th, .vision-table td {
            border: 1px solid #e0e0e0;
            padding: 8px;
            text-align: left;
            vertical-align: middle;
        }
        .vision-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        .vision-table tr:nth-child(even) {
            background-color: #fafafa;
        }
        .vision-table .result-col {
            text-align: center;
            width: 150px;
        }
        .result-item {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 12px;
            margin: 0 4px;
            border: 1px solid transparent;
        }
        .result-selected {
            font-weight: bold;
            color: white;
        }
        .result-normal { background-color: #2e7d32; } /* Green */
        .result-abnormal { background-color: #c62828; } /* Red */
        .result-not-selected {
            background-color: #e0e0e0;
            color: #616161;
            border: 1px solid #bdbdbd;
        }
    </style>
    """, unsafe_allow_html=True)

# --- REFACTORED: Vision Details Table Renderer ---
def render_vision_details_table(person_data):
    """
    Renders a modern, detailed HTML table for the 13-point vision test.
    CSS is now injected separately. This version builds HTML parts in a list.
    """
    vision_tests = [
        {'display': '1. การมองด้วย 2 ตา (Binocular vision)', 'db_col': 'ป.การรวมภาพ', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '2. การมองภาพระยะไกลด้วยสองตา (Far vision - Both)', 'db_col': 'ป.ความชัดของภาพระยะไกล', 'outcomes': ['ชัดเจน', 'ไม่ชัดเจน']},
        {'display': '3. การมองภาพระยะไกลด้วยตาขวา (Far vision - Right)', 'db_col': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'outcomes': ['ชัดเจน', 'ไม่ชัดเจน']},
        {'display': '4. การมองภาพระยะไกลด้วยตาซ้าย (Far vision - Left)', 'db_col': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'outcomes': ['ชัดเจน', 'ไม่ชัดเจน']},
        {'display': '5. การมองภาพ 3 มิติ (Stereo depth)', 'db_col': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '6. การมองจำแนกสี (Color discrimination)', 'db_col': 'ป.การจำแนกสี', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '7. ความสมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'db_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '8. ความสมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'db_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '9. การมองภาพระยะใกล้ด้วยสองตา (Near vision - Both)', 'db_col': 'ป.ความชัดของภาพระยะใกล้', 'outcomes': ['ชัดเจน', 'ไม่ชัดเจน']},
        {'display': '10. การมองภาพระยะใกล้ด้วยตาขวา (Near vision - Right)', 'db_col': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'outcomes': ['ชัดเจน', 'ไม่ชัดเจน']},
        {'display': '11. การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision - Left)', 'db_col': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'outcomes': ['ชัดเจน', 'ไม่ชัดเจน']},
        {'display': '12. ความสมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'db_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '13. ลานสายตา (Visual field)', 'db_col': 'ป.ลานสายตา', 'outcomes': ['ปกติ', 'ผิดปกติ']}
    ]

    html_parts = []
    html_parts.append("""
    <table class="vision-table">
        <thead>
            <tr>
                <th>รายการตรวจ (Vision Test)</th>
                <th class="result-col">ผลปกติ / ชัดเจน</th>
                <th class="result-col">ผลผิดปกติ / ไม่ชัดเจน</th>
            </tr>
        </thead>
        <tbody>
    """)

    for test in vision_tests:
        result_value = str(person_data.get(test['db_col'], '')).strip()
        abnormal_col_name = "ผ." + test['db_col'][2:] if test['db_col'].startswith("ป.") else "ผิด" + test['db_col']
        if is_empty(result_value):
            result_value = str(person_data.get(abnormal_col_name, '')).strip()

        normal_outcome, abnormal_outcome = test['outcomes']
        
        is_normal = normal_outcome.lower() in result_value.lower()
        is_abnormal = abnormal_outcome.lower() in result_value.lower()

        if not is_normal and not is_abnormal:
            if 'ปกติ' in test['db_col'] and not is_empty(person_data.get(test['db_col'])):
                is_normal = True
            elif 'ผิดปกติ' in test['db_col'] and not is_empty(person_data.get(test['db_col'])):
                is_abnormal = True

        normal_class = "result-selected result-normal" if is_normal else "result-not-selected"
        abnormal_class = "result-selected result-abnormal" if is_abnormal else "result-not-selected"
        
        if not is_normal and not is_abnormal:
            normal_class = "result-not-selected"
            abnormal_class = "result-not-selected"

        html_parts.append(f"""
            <tr>
                <td>{test['display']}</td>
                <td class="result-col"><span class="result-item {normal_class}">{normal_outcome}</span></td>
                <td class="result-col"><span class="result-item {abnormal_class}">{abnormal_outcome}</span></td>
            </tr>
        """)

    html_parts.append("</tbody></table>")
    return "".join(html_parts)

def display_performance_report_lung(person_data):
    """
    แสดงผลรายงานสมรรถภาพปอดในรูปแบบที่ปรับปรุงใหม่
    """
    st.header("รายงานผลการตรวจสมรรถภาพปอด (Spirometry Report)")
    # This function requires performance_tests.py. Ensure it's available and correct.
    try:
        from performance_tests import interpret_lung_capacity
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
        st.markdown("<hr>", unsafe_allow_html=True)

        res_col1, res_col2 = st.columns([2, 3])
        with res_col1:
            st.markdown("<h5><b>ผลการแปลความหมาย</b></h5>", unsafe_allow_html=True)
            if "ปกติ" in lung_summary: bg_color = "background-color: #2e7d32; color: white;"
            elif "ไม่ได้" in lung_summary or "คลาดเคลื่อน" in lung_summary: bg_color = "background-color: #616161; color: white;"
            else: bg_color = "background-color: #c62828; color: white;"
            st.markdown(f'<div style="padding: 1rem; border-radius: 8px; {bg_color} text-align: center;"><h4 style="color: white; margin: 0; font-weight: bold;">{lung_summary}</h4></div>', unsafe_allow_html=True)
            st.markdown("<br><h5><b>คำแนะนำ</b></h5>", unsafe_allow_html=True)
            st.info(lung_advice or "ไม่มีคำแนะนำเพิ่มเติม")
            st.markdown("<h5><b>ผลเอกซเรย์ทรวงอก</b></h5>", unsafe_allow_html=True)
            selected_year = person_data.get("Year")
            cxr_result_interpreted = "ไม่มีข้อมูล"
            if selected_year:
                cxr_col_name = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
                cxr_result_interpreted = interpret_cxr(person_data.get(cxr_col_name, ''))
            st.markdown(f'<div style="font-size: 14px; padding: 0.5rem; background-color: rgba(255,255,255,0.05); border-radius: 4px;">{cxr_result_interpreted}</div>', unsafe_allow_html=True)
        with res_col2:
            st.markdown("<h5><b>ตารางแสดงผลโดยละเอียด</b></h5>", unsafe_allow_html=True)
            def format_detail_val(key, format_spec, unit=""):
                val = lung_raw_values.get(key)
                if val is not None and isinstance(val, (int, float)): return f"{val:{format_spec}}{unit}"
                return "-"
            detail_data = {"การทดสอบ (Test)": ["FVC", "FEV1", "FEV1/FVC"],"ค่าที่วัดได้ (Actual)": [format_detail_val('FVC', '.2f', ' L'), format_detail_val('FEV1', '.2f', ' L'), format_detail_val('FEV1/FVC %', '.1f', ' %')],"ค่ามาตรฐาน (Predicted)": [format_detail_val('FVC predic', '.2f', ' L'), format_detail_val('FEV1 predic', '.2f', ' L'), format_detail_val('FEV1/FVC % pre', '.1f', ' %')],"% เทียบค่ามาตรฐาน (% Pred)": [format_detail_val('FVC %', '.1f', ' %'), format_detail_val('FEV1 %', '.1f', ' %'), "-"]}
            df_details = pd.DataFrame(detail_data)
            st.dataframe(df_details, use_container_width=True, hide_index=True)
    except ImportError:
        st.error("ไม่สามารถโหลดฟังก์ชันการแปลผลปอดจาก performance_tests.py ได้")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการแสดงผลตรวจปอด: {e}")


# --- REWRITTEN FOR STABILITY ---
def display_performance_report(person_data, report_type):
    """Displays various performance test reports (lung, vision, hearing)."""
    if report_type == 'lung':
        display_performance_report_lung(person_data)
        
    elif report_type == 'vision':
        st.header("รายงานผลการตรวจสมรรถภาพการมองเห็น (Vision Test Report)")
        
        if not has_vision_data(person_data):
            st.warning("ไม่พบข้อมูลการตรวจสมรรถภาพการมองเห็นในปีนี้")
            return

        # === INLINED LOGIC FROM performance_tests.interpret_vision ===
        vision_raw = person_data.get('สายตา')
        color_blindness_raw = person_data.get('ตาบอดสี')
        
        vision_summary = "ไม่ได้เข้ารับการตรวจ"
        color_summary = "ไม่ได้เข้ารับการตรวจ"
        advice_parts = []

        if not is_empty(vision_raw):
            vision_lower = str(vision_raw).lower().strip()
            if "ปกติ" in vision_lower:
                vision_summary = "ปกติ"
            elif "ผิดปกติ" in vision_lower or "สั้น" in vision_lower or "ยาว" in vision_lower or "เอียง" in vision_lower:
                vision_summary = "ผิดปกติ"
                advice_parts.append("สายตาผิดปกติ ควรปรึกษาจักษุแพทย์เพื่อตรวจวัดสายตาและพิจารณาตัดแว่น")
            else:
                vision_summary = vision_raw

        if not is_empty(color_blindness_raw):
            color_blindness_lower = str(color_blindness_raw).lower().strip()
            if "ปกติ" in color_blindness_lower:
                color_summary = "ปกติ"
            elif "ผิดปกติ" in color_blindness_lower:
                color_summary = "ผิดปกติ"
                advice_parts.append("ภาวะตาบอดสี ควรหลีกเลี่ยงงานที่ต้องใช้การแยกสีที่สำคัญ")
            else:
                color_summary = color_blindness_raw
        
        vision_advice = " ".join(advice_parts)
        # === END OF INLINED LOGIC ===

        st.markdown("<h5><b>สรุปผลภาพรวม</b></h5>", unsafe_allow_html=True)
        v_col1, v_col2 = st.columns(2)
        v_col1.metric("ผลตรวจสายตา (ทั่วไป)", vision_summary if not is_empty(vision_summary) else "ไม่มีข้อมูลสรุป")
        v_col2.metric("ผลตรวจตาบอดสี", color_summary if not is_empty(color_summary) else "ไม่มีข้อมูลสรุป")
        if vision_advice:
            st.info(f"**คำแนะนำ:** {vision_advice}")

        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.markdown("<h5><b>ผลการตรวจโดยละเอียด</b></h5>", unsafe_allow_html=True)
        detailed_table_html = render_vision_details_table(person_data)
        st.markdown(detailed_table_html, unsafe_allow_html=True)
        
    elif report_type == 'hearing':
        st.header("รายงานผลการตรวจสมรรถภาพการได้ยิน (Hearing)")
        # This function requires performance_tests.py. Ensure it's available and correct.
        try:
            from performance_tests import interpret_hearing
            hearing_summary, hearing_advice = interpret_hearing(person_data.get('การได้ยิน'))
            if hearing_summary == "ไม่ได้เข้ารับการตรวจ":
                st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพการได้ยินในปีนี้")
                return
            h_col1, h_col2 = st.columns(2)
            h_col1.metric("สรุปผล", hearing_summary)
            if hearing_advice: h_col2.info(f"**คำแนะนำ:** {hearing_advice}")
        except ImportError:
            st.error("ไม่สามารถโหลดฟังก์ชันการแปลผลการได้ยินจาก performance_tests.py ได้")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการแสดงผลตรวจการได้ยิน: {e}")


def display_main_report(person_data):
    """Displays the main health report with all lab sections."""
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]
    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]
    left_spacer, col1, col2, right_spacer = st.columns([0.5, 3, 3, 0.5])
    with col1: st.markdown(render_lab_table_html("ผลตรวจ CBC (Complete Blood Count)", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)
    advice_list = [kidney_advice_from_summary(kidney_summary_gfr_only(person.get("GFR", ""))), fbs_advice(person.get("FBS", "")), liver_advice(summarize_liver(person.get("ALP", ""), person.get("SGOT", ""), person.get("SGPT", ""))), uric_acid_advice(person.get("Uric Acid", "")), lipids_advice(summarize_lipids(person.get("CHOL", ""), person.get("TGL", ""), person.get("LDL", ""))), cbc_advice(person.get("Hb(%)", ""), person.get("HCT", ""), person.get("WBC (cumm)", ""), person.get("Plt (/mm)", ""), sex=sex)]
    spacer_l, main_col, spacer_r = st.columns([0.5, 6, 0.5])
    with main_col:
        final_advice_html = merge_final_advice_grouped(advice_list)
        has_general_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
        background_color_general_advice = "rgba(255, 255, 0, 0.2)" if has_general_advice else "rgba(57, 255, 20, 0.2)"
        st.markdown(f'<div style="background-color: {background_color_general_advice}; padding: 0.6rem 2.5rem; border-radius: 10px; line-height: 1.6; color: var(--text-color); font-size: 14px;">{final_advice_html}</div>', unsafe_allow_html=True)
    
    selected_year = person.get("Year", datetime.now().year + 543)
    with st.container():
        left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([0.5, 3, 3, 0.5])
        with col_ua_left:
            urine_summary, has_urine_result = render_urine_section(person, sex, selected_year)
            if has_urine_result:
                bg_color, advice_text = ("rgba(255, 255, 0, 0.2)", f"<b>&emsp;ผลตรวจปัสสาวะ:</b> {urine_summary}") if urine_summary else ("rgba(57, 255, 20, 0.2)", "<b>&emsp;ผลตรวจปัสสาวะ:</b> อยู่ในเกณฑ์ปกติ")
                st.markdown(f'<div style="background-color: {bg_color}; padding: 0.6rem 1.5rem; border-radius: 10px; line-height: 1.6; color: var(--text-color); font-size: 14px; margin-top: 1rem;">{advice_text}</div>', unsafe_allow_html=True)
            
            st.markdown(render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)

        with col_ua_right:
            st.markdown(render_section_header("ผลเอกซเรย์ (Chest X-ray)"), unsafe_allow_html=True)
            cxr_col = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            st.markdown(f"<div style='background-color: var(--background-color); color: var(--text-color); line-height: 1.6; padding: 0.4rem; border-radius: 6px; margin-bottom: 1.5rem; font-size: 14px;'>{interpret_cxr(person.get(cxr_col, ''))}</div>", unsafe_allow_html=True)
            
            st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ (EKG)"), unsafe_allow_html=True)
            st.markdown(f"<div style='background-color: var(--secondary-background-color); color: var(--text-color); line-height: 1.6; padding: 0.4rem; border-radius: 6px; margin-bottom: 1.5rem; font-size: 14px;'>{interpret_ekg(person.get(get_ekg_col_name(selected_year), ''))}</div>", unsafe_allow_html=True)
            
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบเอ (Viral hepatitis A)"), unsafe_allow_html=True)
            st.markdown(f"<div style='padding: 0.4rem; border-radius: 6px; margin-bottom: 1.5rem; background-color: rgba(255,255,255,0.05); font-size: 14px;'>{safe_text(person.get('Hepatitis A'))}</div>", unsafe_allow_html=True)
            
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)"), unsafe_allow_html=True)
            hbsag, hbsab, hbcab = safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB"))
            st.markdown(f"""<div style="margin-bottom: 1rem;"><table style='width: 100%; text-align: center; border-collapse: collapse; min-width: 300px; font-size: 14px;'>
                <thead><tr><th style="padding: 8px; border: 1px solid transparent;">HBsAg</th><th style="padding: 8px; border: 1px solid transparent;">HBsAb</th><th style="padding: 8px; border: 1px solid transparent;">HBcAb</th></tr></thead>
                <tbody><tr><td style="padding: 8px; border: 1px solid transparent;">{hbsag}</td><td style="padding: 8px; border: 1px solid transparent;">{hbsab}</td><td style="padding: 8px; border: 1px solid transparent;">{hbcab}</td></tr></tbody>
            </table></div>""", unsafe_allow_html=True)
            
            hep_check_date, hep_history, hep_vaccine = safe_text(normalize_thai_date(person.get("ปีตรวจHEP"))), safe_text(person.get("สรุปประวัติ Hepb")), safe_text(person.get("วัคซีนhep b 67"))
            st.markdown(f"""<div style='padding: 0.75rem 1rem; background-color: rgba(255,255,255,0.05); border-radius: 6px; margin-bottom: 1.5rem; line-height: 1.8; font-size: 14px;'>
                <b>วันที่ตรวจภูมิคุ้มกัน:</b> {hep_check_date}<br>
                <b>ประวัติโรคไวรัสตับอักเสบบี ปี พ.ศ. {selected_year}:</b> {hep_history}<br>
                <b>ประวัติการได้รับวัคซีนในปี พ.ศ. {selected_year}:</b> {hep_vaccine}
            </div>""", unsafe_allow_html=True)
            advice = hepatitis_b_advice(hbsag, hbsab, hbcab)
            bg_color = "rgba(57, 255, 20, 0.2)" if "มีภูมิคุ้มกัน" in advice else "rgba(255, 255, 0, 0.2)"
            st.markdown(f"<div style='line-height: 1.6; padding: 0.4rem 1.5rem; border-radius: 6px; background-color: {bg_color}; color: var(--text-color); margin-bottom: 1.5rem; font-size: 14px;'>{advice}</div>", unsafe_allow_html=True)
            
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if doctor_suggestion.lower() in ["", "-", "none", "nan", "null"]:
        doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"
    left_spacer3, doctor_col, right_spacer3 = st.columns([0.5, 6, 0.5])
    with doctor_col:
        st.markdown(f"<div style='background-color: #1b5e20; color: white; padding: 0.4rem 2rem; border-radius: 8px; line-height: 1.6; margin-top: 2rem; margin-bottom: 2rem; font-size: 14px;'><b>สรุปความเห็นของแพทย์:</b><br> {doctor_suggestion}</div>", unsafe_allow_html=True)
    
    st.markdown(f"""<div style='margin-top: 7rem; text-align: right; padding-right: 1rem;'>
        <div style='display: inline-block; text-align: center; width: 340px;'>
            <div style='border-bottom: 1px dotted #ccc; margin-bottom: 0.5rem; width: 100%;'></div>
            <div style='white-space: nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style='white-space: nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
        </div>
    </div>""", unsafe_allow_html=True)

# --- Main Application Logic ---
# Load data once
df = load_sqlite_data()
if df is None:
    st.stop()

# Page config and styles
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
inject_custom_css() # Call CSS injection function
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, div, span, p, td, th, li, ul, ol, table, h1, h2, h3, h4, h5, h6, label, button, input, select, option, .stButton>button, .stTextInput>div>div>input, .stSelectbox>div>div>div { font-family: 'Sarabun', sans-serif !important; }
    div[data-testid="stSidebarNav"], button[data-testid="stSidebarNavCollapseButton"] { display: none; }
    .stDownloadButton button { width: 100%; }
</style>""", unsafe_allow_html=True)

# Callbacks for search and year selection
def perform_search():
    st.session_state.search_query = st.session_state.search_input
    st.session_state.selected_year = None
    st.session_state.selected_date = None
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    st.session_state.page = 'main_report' 
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
    st.session_state.page = 'main_report'

# Initialize session state
if 'search_query' not in st.session_state: st.session_state.search_query = ""
if 'search_input' not in st.session_state: st.session_state.search_input = ""
if 'search_result' not in st.session_state: st.session_state.search_result = pd.DataFrame()
if 'selected_year' not in st.session_state: st.session_state.selected_year = None
if 'selected_date' not in st.session_state: st.session_state.selected_date = None
if 'page' not in st.session_state: st.session_state.page = 'main_report'

# --- UI Layout for Search and Filters ---
st.subheader("ค้นหาและเลือกผลตรวจ")
menu_cols = st.columns([3, 1, 2])
with menu_cols[0]:
    st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input", on_change=perform_search, placeholder="HN หรือ ชื่อ-สกุล", label_visibility="collapsed")
with menu_cols[1]:
    st.button("ค้นหา", use_container_width=True, on_click=perform_search)

results_df = st.session_state.search_result
if not results_df.empty:
    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    if not available_years:
        st.warning("ไม่พบข้อมูลปีที่ตรวจสำหรับบุคคลนี้")
    else:
        if st.session_state.selected_year not in available_years:
            st.session_state.selected_year = available_years[0]
        year_idx = available_years.index(st.session_state.selected_year)
        with menu_cols[2]:
            st.selectbox("ปี พ.ศ.", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change, label_visibility="collapsed")
        
        person_year_df = results_df[results_df["Year"] == st.session_state.selected_year]

        if person_year_df.empty:
            st.warning(f"ไม่พบข้อมูลการตรวจสำหรับปี พ.ศ. {st.session_state.selected_year}")
            st.session_state.pop("person_row", None)
            st.session_state.pop("selected_row_found", None)
        else:
            merged_series = person_year_df.bfill().ffill().iloc[0]
            st.session_state.person_row = merged_series.to_dict()
            st.session_state.selected_row_found = True

st.markdown("<hr>", unsafe_allow_html=True)

# Main logic to switch between pages
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    person_data = st.session_state.person_row

    available_reports = {}
    if has_basic_health_data(person_data):
        available_reports['main_report'] = "สุขภาพพื้นฐาน"
    if has_vision_data(person_data):
        available_reports['vision_report'] = "สมรรถภาพการมองเห็น"
    if has_hearing_data(person_data):
        available_reports['hearing_report'] = "สมรรถภาพการได้ยิน"
    if has_lung_data(person_data):
        available_reports['lung_report'] = "ความจุปอด"

    if not available_reports:
        display_common_header(person_data)
        st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับวันที่และปีที่เลือก")
    else:
        if st.session_state.page not in available_reports:
            st.session_state.page = list(available_reports.keys())[0]

        btn_cols = st.columns(len(available_reports) or [1])
        for i, (page_key, page_title) in enumerate(available_reports.items()):
            with btn_cols[i]:
                if st.button(page_title, use_container_width=True):
                    st.session_state.page = page_key
                    st.rerun()

        display_common_header(person_data)
        
        page_to_show = st.session_state.page
        if page_to_show == 'vision_report':
            display_performance_report(person_data, 'vision')
        elif page_to_show == 'hearing_report':
            display_performance_report(person_data, 'hearing')
        elif page_to_show == 'lung_report':
            display_performance_report(person_data, 'lung')
        elif page_to_show == 'main_report':
            display_main_report(person_data)

else:
    st.info("กรอก ชื่อ-สกุล หรือ HN เพื่อค้นหาผลการตรวจสุขภาพ")
