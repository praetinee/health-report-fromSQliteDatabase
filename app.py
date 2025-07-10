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

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# --- Global Helper Functions: START ---

# Define Thai month mappings (global to these functions)
THAI_MONTHS_GLOBAL = {
    1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
    5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
    9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {
    "ม.ค.": 1, "ม.ค": 1, "มกราคม": 1,
    "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2,
    "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3,
    "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4,
    "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5,
    "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6,
    "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7,
    "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8,
    "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9,
    "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10,
    "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11,
    "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12
}

# Function to normalize and convert Thai dates
def normalize_thai_date(date_str):
    if is_empty(date_str):
        return "-"
    
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()

    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]:
        return s

    try:
        # Format: DD/MM/YYYY (e.g., 29/04/2565)
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: # Assume Thai Buddhist year if year > 2500
                year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        # Format: DD-MM-YYYY (e.g., 29-04-2565)
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: # Assume Thai Buddhist year if year > 2500
                year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        # Format: DD MonthNameYYYY (e.g., 8 เมษายน 2565) or DD-DD MonthNameYYYY (e.g., 15-16 กรกฎาคม 2564)
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

    # Fallback to pandas for robust parsing if other specific regex fail
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

def render_section_header(title, subtitle=None):
    if subtitle:
        full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>"
    else:
        full_title = title

    return f"""
    <div style='
        background-color: #1b5e20;
        color: white;
        text-align: center;
        padding: 0.8rem 0.5rem;
        font-weight: bold;
        border-radius: 8px;
        margin-top: 2rem;
        margin-bottom: 1rem;
        font-size: 14px;
    '>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    style = f"""
    <style>
        .{table_class}-container {{
            background-color: var(--background-color);
            margin-top: 1rem;
        }}
        .{table_class} {{
            width: 100%;
            border-collapse: collapse;
            color: var(--text-color);
            table-layout: fixed; /* Ensures column widths are respected */
            font-size: 14px;
        }}
        .{table_class} thead th {{
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 2px 2px; /* Adjusted padding to make columns closer */
            text-align: center;
            font-weight: bold;
            border: 1px solid transparent;
        }}
        .{table_class} td {{
            padding: 2px 2px; /* Adjusted padding to make columns closer */
            border: 1px solid transparent;
            text-align: center;
            color: var(--text-color);
        }}
        .{table_class}-abn {{
            background-color: rgba(255, 64, 64, 0.25); /* Translucent red */
        }}
        .{table_class}-row {{
            background-color: rgba(255,255,255,0.02);
        }}
    </style>
    """
    
    header_html = render_section_header(title, subtitle)
    
    html_content = f"{style}{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    html_content += """
        <colgroup>
            <col style="width: 33.33%;"> <col style="width: 33.33%;"> <col style="width: 33.33%;"> </colgroup>
    """
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 else ("left" if i == 2 else "center") # 'การตรวจ' and 'ค่าปกติ' left-aligned, 'ผล' center-aligned
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else f"{table_class}-row"
        
        html_content += f"<tr>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td class='{row_class}'>{row[1][0]}</td>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table></div>"
    return html_content

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

def kidney_advice_from_summary(summary_text):
    if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
        return (
            "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย "
            "ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน "
            "และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
        )
    return ""

def fbs_advice(fbs_raw):
    if is_empty(fbs_raw):
        return ""
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
        return ""

def liver_advice(summary_text):
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
        return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    elif summary_text == "ปกติ":
        return ""
    return "-"

def uric_acid_advice(value_raw):
    try:
        value = float(value_raw)
        if value > 7.2:
            return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except:
        return "-"

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

def cbc_advice(hb, hct, wbc, plt, sex="ชาย"):
    advice_parts = []

    try:
        hb_val = float(hb)
        hb_ref = 13 if sex == "ชาย" else 12
        if hb_val < hb_ref:
            advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    except:
        pass

    try:
        hct_val = float(hct)
        hct_ref = 39 if sex == "ชาย" else 36
        if hct_val < hct_ref:
            advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    except:
        pass

    try:
        wbc_val = float(wbc)
        if wbc_val < 4000:
            advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000:
            advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    except:
        pass

    try:
        plt_val = float(plt)
        if plt_val < 150000:
            advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000:
            advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")
    except:
        pass

    return " ".join(advice_parts)

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
    except:
        return "-"

def combined_health_advice(bmi, sbp, dbp):
    if is_empty(bmi) and is_empty(sbp) and is_empty(dbp):
        return ""
    
    try:
        bmi = float(bmi)
    except:
        bmi = None
    try:
        sbp = float(sbp)
        dbp = float(dbp)
    except:
        sbp = dbp = None
    
    bmi_text = ""
    bp_text = ""
    
    if bmi is not None:
        if bmi > 30:
            bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi >= 25:
            bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5:
            bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else:
            bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
    
    if sbp is not None and dbp is not None:
        if sbp >= 160 or dbp >= 100:
            bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
        elif sbp >= 140 or dbp >= 90:
            bp_text = "ความดันโลหิตอยู่ในระดับสูง"
        elif sbp >= 120 or dbp >= 80:
            bp_text = "ความดันโลหิตเริ่มสูง"
    
    if bmi is not None and "ปกติ" in bmi_text and not bp_text:
        return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
    if not bmi_text and bp_text:
        return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    if bmi_text and bp_text:
        return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    if bmi_text and not bp_text:
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    return ""

def safe_text(val):
    """Helper to safely get text and handle empty values."""
    return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()

def safe_value(val):
    val = str(val or "").strip()
    if val.lower() in ["", "nan", "none", "-"]:
        return "-"
    return val
    
def interpret_alb(value):
    val = str(value).strip().lower()
    if val == "negative":
        return "ไม่พบ"
    elif val in ["trace", "1+", "2+"]:
        return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif val in ["3+", "4+"]:
        return "พบโปรตีนในปัสสาวะ"
    return "-"
    
def interpret_sugar(value):
    val = str(value).strip().lower()
    if val == "negative":
        return "ไม่พบ"
    elif val == "trace":
        return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif val in ["1+", "2+", "3+", "4+", "5+", "6+"]:
        return "พบน้ำตาลในปัสสาวะ"
    return "-"
    
def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val:
            low, high = map(float, val.split("-"))
            return low, high
        else:
            num = float(val)
            return num, num
    except:
        return None, None
    
def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]:
        return "-"
    low, high = parse_range_or_number(val)
    if high is None:
        return value
    if high <= 2:
        return "ปกติ"
    elif high <= 5:
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดแดงในปัสสาวะ"
    
def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]:
        return "-"
    low, high = parse_range_or_number(val)
    if high is None:
        return value
    if high <= 5:
        return "ปกติ"
    elif high <= 10:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดขาวในปัสสาวะ"
    
def advice_urine(sex, alb, sugar, rbc, wbc):
    alb_t = interpret_alb(alb)
    sugar_t = interpret_sugar(sugar)
    rbc_t = interpret_rbc(rbc)
    wbc_t = interpret_wbc(wbc)
    
    if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"]
                     for x in [alb_t, sugar_t, rbc_t, wbc_t]):
        return ""
    
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "เล็กน้อย" not in sugar_t:
        return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"
    
    if sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t:
        return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"
    
    if sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t:
        return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"
    
    if "พบเม็ดเลือดขาว" in wbc_t and "เล็กน้อย" not in wbc_t:
        return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"
    
    return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"
    
def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]:
        return False
    
    if test_name == "กรด-ด่าง (pH)":
        try:
            return not (5.0 <= float(val) <= 8.0)
        except:
            return True
    
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try:
            return not (1.003 <= float(val) <= 1.030)
        except:
            return True
    
    if test_name == "เม็ดเลือดแดง (RBC)":
        return "พบ" in interpret_rbc(val).lower()
    
    if test_name == "เม็ดเลือดขาว (WBC)":
        return "พบ" in interpret_wbc(val).lower()
    
    if test_name == "น้ำตาล (Sugar)":
        return interpret_sugar(val).lower() != "ไม่พบ"
    
    if test_name == "โปรตีน (Albumin)":
        return interpret_alb(val).lower() != "ไม่พบ"
    
    if test_name == "สี (Colour)":
        return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    
    return False

def render_urine_section(person_data, sex, year_selected):
    alb_raw = person_data.get("Alb", "-")
    sugar_raw = person_data.get("sugar", "-")
    rbc_raw = person_data.get("RBC1", "-")
    wbc_raw = person_data.get("WBC1", "-")

    urine_data = [
        ("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"),
        ("น้ำตาล (Sugar)", sugar_raw, "Negative"),
        ("โปรตีน (Albumin)", alb_raw, "Negative, trace"),
        ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"),
        ("เม็ดเลือดแดง (RBC)", rbc_raw, "0 - 2 cell/HPF"),
        ("เม็ดเลือดขาว (WBC)", wbc_raw, "0 - 5 cell/HPF"),
        ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"),
        ("อื่นๆ", person_data.get("ORTER", "-"), "-"),
    ]

    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    
    style = """
    <style>
        .urine-table-container {
            background-color: var(--background-color);
            margin-top: 1rem;
        }
        .urine-table {
            width: 100%;
            border-collapse: collapse;
            color: var(--text-color);
            table-layout: fixed; /* Ensures column widths are respected */
            font-size: 14px;
        }
        .urine-table thead th {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 3px 2px; /* Adjusted padding to make columns closer */
            text-align: center;
            font-weight: bold;
            border: 1px solid transparent;
        }
        .urine-table td {
            padding: 3px 2px; /* Adjusted padding to make columns closer */
            border: 1px solid transparent;
            text-align: center;
            color: var(--text-color);
        }
        .urine-abn {
            background-color: rgba(255, 64, 64, 0.25);
        }
        .urine-row {
            background-color: rgba(255,255,255,0.02);
        }
    </style>
    """
    html_content = style + render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis")
    html_content += "<div class='urine-table-container'><table class='urine-table'>"
    html_content += """
        <colgroup>
            <col style="width: 33.33%;"> <col style="width: 33.33%;"> <col style="width: 33.33%;"> </colgroup>
    """
    html_content += "<thead><tr>"
    html_content += "<th style='text-align: left;'>การตรวจ</th>"
    html_content += "<th>ผลตรวจ</th>"
    html_content += "<th style='text-align: left;'>ค่าปกติ</th>"
    html_content += "</tr></thead><tbody>"
    
    for _, row in df_urine.iterrows():
        is_abn = is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])
        css_class = "urine-abn" if is_abn else "urine-row"
        html_content += f"<tr class='{css_class}'>"
        html_content += f"<td style='text-align: left;'>{row['การตรวจ']}</td>"
        html_content += f"<td>{safe_value(row['ผลตรวจ'])}</td>"
        html_content += f"<td style='text-align: left;'>{row['ค่าปกติ']}</td>"
        html_content += "</tr>"
    html_content += "</tbody></table></div>"
    st.markdown(html_content, unsafe_allow_html=True)
    
    summary = advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
    
    has_any_urine_result = any(not is_empty(val) for _, val, _ in urine_data)

    if not has_any_urine_result:
        pass
    elif summary:
        st.markdown(f"""
            <div style='
                background-color: rgba(255, 255, 0, 0.2);
                color: var(--text-color);
                padding: 1rem;
                border-radius: 6px;
                margin-top: 1rem;
                font-size: 14px;
            '>
                {summary}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='
                background-color: rgba(57, 255, 20, 0.2);
                color: var(--text-color);
                padding: 1rem;
                border-radius: 6px;
                margin-top: 1rem;
                font-size: 14px;
            '>
                ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ
            </div>
        """, unsafe_allow_html=True)


def interpret_stool_exam(val):
    val = str(val or "").strip().lower()
    if val in ["", "-", "none", "nan"]:
        return "-"
    elif val == "normal":
        return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    elif "wbc" in val or "เม็ดเลือดขาว" in val:
        return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    value = str(value or "").strip()
    if value in ["", "-", "none", "nan"]:
        return "-"
    if "ไม่พบ" in value or "ปกติ" in value:
        return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
    style = """
    <style>
        .stool-container {
            background-color: var(--background-color);
            margin-top: 1rem;
        }
        .stool-table {
            width: 100%;
            border-collapse: collapse;
            color: var(--text-color);
            table-layout: fixed; /* Ensures column widths are respected */
            font-size: 14px;
        }
        .stool-table th {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 3px 2px; /* Adjusted padding to make columns closer */
            text-align: left;
            width: 50%; /* Equal width for 2 columns */
            font-weight: bold;
            border: 1px solid transparent;
        }
        .stool-table td {
            padding: 3px 2px; /* Adjusted padding to make columns closer */
            border: 1px solid transparent;
            width: 50%; /* Equal width for 2 columns */
            color: var(--text-color);
        }
    </style>
    """
    html_content = f"""
    <div class='stool-container'>
        <table class='stool-table'>
            <colgroup>
                <col style="width: 50%;"> <col style="width: 50%;"> </colgroup>
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
    return style + html_content

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

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
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

def merge_final_advice_grouped(messages):
    groups = {
        "FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []
    }

    for msg in messages:
        if not msg or msg.strip() in ["-", ""]:
            continue
        if "น้ำตาล" in msg:
            groups["FBS"].append(msg)
        elif "ไต" in msg:
            groups["ไต"].append(msg)
        elif "ตับ" in msg:
            groups["ตับ"].append(msg)
        elif "พิวรีน" in msg or "ยูริค" in msg:
            groups["ยูริค"].append(msg)
        elif "ไขมัน" in msg:
            groups["ไขมัน"].append(msg)
        else:
            groups["อื่นๆ"].append(msg)
            
    output = []
    for title, msgs in groups.items():
        if msgs:
            unique_msgs = list(OrderedDict.fromkeys(msgs))
            output.append(f"<b>{title}:</b> {' '.join(unique_msgs)}")
            
    if not output:
        return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

    return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(output) + "</div>"

# --- Global Helper Functions: END ---

@st.cache_data(ttl=600)
def load_sqlite_data():
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
        os.unlink(tmp_path) # Clean up the temporary file

        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        
        # Convert HN from potentially REAL type to integer string, stripping extra decimals
        df_loaded['HN'] = df_loaded['HN'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, int)) else str(x)).str.strip()

        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)

        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None], pd.NA, inplace=True)

        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

# --- Load data when the app starts. ---
df = load_sqlite_data()

# ==================== UI Setup and Search Form (Sidebar) ====================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# Inject custom CSS for font, size control, and NEW printing rules
st.markdown("""
    <style>
    /* --- General Styles (Your original styles remain here) --- */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td,
    div[data-testid="stMarkdown"],
    div[data-testid="stInfo"],
    div[data-testid="stSuccess"],
    div[data-testid="stWarning"],
    div[data-testid="stError"] {
        font-family: 'Sarabun', sans-serif !important;
    }
    body {
        font-size: 14px !important;
    }
    .report-header-container h1 {
        font-size: 1.8rem !important;
        font-weight: bold;
    }
    .report-header-container h2 {
        font-size: 1.2rem !important;
        color: darkgrey;
        font-weight: bold;
    }
    .st-sidebar h3 {
        font-size: 18px !important;
    }
    .report-header-container * {
        line-height: 1.7 !important; 
        margin: 0.2rem 0 !important;
        padding: 0 !important;
    }
    
    /* --- ⭐ NEW & IMPROVED: Print-Specific Styles ⭐ --- */
    @media print {
        /* Hide elements that shouldn't be printed */
        [data-testid="stSidebar"], 
        header[data-testid="stHeader"], 
        .stButton {
            display: none !important;
        }

        /* Ensure main content uses the full page width with proper margins */
        .main .block-container {
            padding: 1cm 1.5cm !important; /* Top/Bottom 1cm, Left/Right 1.5cm for A4 */
            width: 100% !important;
            margin: 0 !important;
        }
        
        /* Reset body for printing */
        body {
            font-size: 10pt !important; /* Smaller font size for print */
            margin: 0 !important;
            padding: 0 !important;
            background: #fff !important; 
            color: #000 !important;
        }
        
        /* Force Streamlit's column containers to stack vertically instead of side-by-side */
        div[data-testid="stHorizontalBlock"] {
            display: block !important;
        }
        
        /* Make all sections compact */
        div, p, h1, h2, table, th, td {
            page-break-inside: avoid !important; /* Try to prevent elements from splitting across pages */
            margin-top: 2px !important;
            margin-bottom: 2px !important;
            padding-top: 1px !important;
            padding-bottom: 1px !important;
            line-height: 1.3 !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT REFACTOR START ---

# Initialize state keys if they don't exist
if 'current_search_term' not in st.session_state:
    st.session_state.current_search_term = ""
if 'search_results_df' not in st.session_state:
    st.session_state.search_results_df = None
if 'person_row' not in st.session_state:
    st.session_state.person_row = None

# Sidebar UI
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
with st.sidebar.form(key='search_form'):
    search_query = st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input")
    submitted = st.form_submit_button("ค้นหา")

if submitted:
    st.session_state.current_search_term = search_query
    # Clear all dependent state to force a full refresh
    keys_to_clear = ['search_results_df', 'person_row', 'selected_year', 'selected_date']
    for key in keys_to_clear:
        st.session_state.pop(key, None)


# Main logic controller
if st.session_state.current_search_term:
    # Step 1: Perform the search if results are not yet in state
    if st.session_state.get('search_results_df') is None:
        search_term = st.session_state.current_search_term.strip()
        if search_term:
            if search_term.isdigit():
                results = df[df["HN"] == search_term]
            else:
                results = df[df["ชื่อ-สกุล"].str.strip() == search_term]
            
            if results.empty:
                st.sidebar.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง")
                st.session_state.current_search_term = "" # Reset search term to prevent loop
            else:
                st.session_state.search_results_df = results
        else:
            st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล เพื่อค้นหา")

    # Step 2: Display selectors if we have search results
    if st.session_state.get('search_results_df') is not None:
        results_df = st.session_state.search_results_df
        with st.sidebar:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)

            available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
            
            selected_year = st.selectbox(
                "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน",
                options=available_years,
                key="selected_year"
            )

            # Date selector logic
            if selected_year:
                year_df = results_df[results_df["Year"] == selected_year]
                available_dates = sorted(year_df["วันที่ตรวจ"].dropna().unique(), key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), reverse=True)

                if available_dates:
                    selected_date = st.selectbox(
                        "🗓️ เลือกวันที่ตรวจ",
                        options=available_dates,
                        key="selected_date"
                    )

                    # Step 3: Select the final row to display
                    if selected_date:
                        final_row_df = year_df[year_df["วันที่ตรวจ"] == selected_date]
                        if not final_row_df.empty:
                            st.session_state.person_row = final_row_df.iloc[0].to_dict()
                        else:
                             st.session_state.person_row = None # Should not happen
                else:
                    st.sidebar.warning(f"ไม่พบวันที่ตรวจสำหรับปี พ.ศ. {selected_year}")
                    st.session_state.person_row = None
            else:
                 st.session_state.person_row = None
            
            # Add Print Button
            if st.session_state.get('person_row'):
                st.markdown("---")
                if st.sidebar.button("🖨️ พิมพ์รายงานนี้"):
                    # Inject JavaScript to trigger the browser's print dialog
                    st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
else:
    st.info("เริ่มต้นใช้งานโดยการค้นหา HN หรือ ชื่อ-สกุล จากเมนูด้านซ้าย")

# --- STATE MANAGEMENT REFACTOR END ---


# ==================== Display Health Report (Main Content) ====================
if st.session_state.get('person_row'):
    person = st.session_state.person_row
    year_display = person.get("Year", "-")

    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse_raw = person.get("pulse", "-")
    weight_raw = person.get("น้ำหนัก", "-")
    height_raw = person.get("ส่วนสูง", "-")
    waist_raw = person.get("รอบเอว", "-")
    check_date = person.get("วันที่ตรวจ", "-")

    # --- NEW: Unified Header Block (MODIFIED) ---
    report_header_html = f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem;">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        <p><b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>
    """
    st.markdown(report_header_html, unsafe_allow_html=True)
    
    # --- The rest of the report starts here ---
    try:
        weight_val = float(str(weight_raw).replace("กก.", "").strip())
        height_val = float(str(height_raw).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2) if height_val > 0 else None
    except:
        bmi_val = None

    try:
        sbp_int = int(float(sbp))
        dbp_int = int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except:
        sbp_int = dbp_int = None
        bp_val = "-"
    
    if sbp_int is None or dbp_int is None:
        bp_desc = "-"
        bp_full = "-"
    else:
        bp_desc = interpret_bp(sbp, dbp)
        bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val

    try:
        pulse_val = int(float(pulse_raw))
    except:
        pulse_val = None

    pulse = f"{pulse_val} ครั้ง/นาที" if pulse_val is not None else "-"
    weight_display = f"{weight_raw} กก." if not is_empty(weight_raw) else "-"
    height_display = f"{height_raw} ซม." if not is_empty(height_raw) else "-"
    waist_display = f"{waist_raw} ซม." if not is_empty(waist_raw) else "-"

    advice_text = combined_health_advice(bmi_val, sbp, dbp)
    summary_advice = html.escape(advice_text) if advice_text else ""
    
    # This block now only contains personal info, not the header.
    st.markdown(f"""
    <div>
        <hr>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-top: 24px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</div>
            <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
            <div><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {weight_display}</div>
            <div><b>ส่วนสูง:</b> {height_display}</div>
            <div><b>รอบเอว:</b> {waist_display}</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {pulse}</div>
        </div>
        {f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {summary_advice}</div>" if summary_advice else ""}
    </div>
    """, unsafe_allow_html=True)

    sex = str(person.get("เพศ", "")).strip()

    if sex not in ["ชาย", "หญิง"]:
        st.warning("⚠️ เพศไม่ถูกต้องหรือไม่มีข้อมูล กำลังใช้ค่าอ้างอิงเริ่มต้น")
        sex = "ไม่ระบุ"

    if sex == "หญิง":
        hb_low = 12
        hct_low = 36
    elif sex == "ชาย":
        hb_low = 13
        hct_low = 39
    else: # Default for "ไม่ระบุ" or invalid sex
        hb_low = 12
        hct_low = 36

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

    cbc_rows = []
    for label, col, norm, low, high in cbc_config:
        val = get_float(col, person)
        result, is_abn = flag(val, low, high)
        cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
        ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120),
        ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
    ]

    blood_rows = []
    for label, col, norm, low, high, *opt in blood_config:
        higher = opt[0] if opt else False
        val = get_float(col, person)
        result, is_abn = flag(val, low, high, higher)
        blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    left_spacer, col1, col2, right_spacer = st.columns([0.5, 3, 3, 0.5])

    with col1:
        st.markdown(render_lab_table_html("ผลตรวจ CBC (Complete Blood Count)", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    # ==================== Combined Recommendations ====================
    gfr_raw = person.get("GFR", "")
    fbs_raw = person.get("FBS", "")
    alp_raw = person.get("ALP", "")
    sgot_raw = person.get("SGOT", "")
    sgpt_raw = person.get("SGPT", "")
    uric_raw = person.get("Uric Acid", "")
    chol_raw = person.get("CHOL", "")
    tgl_raw = person.get("TGL", "")
    ldl_raw = person.get("LDL", "")

    advice_list = []
    kidney_summary = kidney_summary_gfr_only(gfr_raw)
    advice_list.append(kidney_advice_from_summary(kidney_summary))
    advice_list.append(fbs_advice(fbs_raw))
    advice_list.append(liver_advice(summarize_liver(alp_raw, sgot_raw, sgpt_raw)))
    advice_list.append(uric_acid_advice(uric_raw))
    advice_list.append(lipids_advice(summarize_lipids(chol_raw, tgl_raw, ldl_raw)))
    advice_list.append(cbc_advice(
        person.get("Hb(%)", ""), 
        person.get("HCT", ""), 
        person.get("WBC (cumm)", ""), 
        person.get("Plt (/mm)", ""),
        sex=sex
    ))

    spacer_l, main_col, spacer_r = st.columns([0.5, 6, 0.5])

    with main_col:
        final_advice_html = merge_final_advice_grouped(advice_list)
        has_general_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
        
        background_color_general_advice = (
            "rgba(255, 255, 0, 0.2)" if has_general_advice else "rgba(57, 255, 20, 0.2)"
        )

        st.markdown(f"""
        <div style="
            background-color: {background_color_general_advice};
            padding: 1rem 2.5rem;
            border-radius: 10px;
            line-height: 1.5;
            color: var(--text-color);
            font-size: 14px;
        ">
            {final_advice_html}
        </div>
        """, unsafe_allow_html=True)

    # ==================== Urinalysis Section ====================
    selected_year = st.session_state.get("selected_year", datetime.now().year + 543)

    with st.container():
        left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([0.5, 3, 3, 0.5])
        
        with col_ua_left:
            render_urine_section(person, sex, selected_year)

            # ==================== Stool Section ====================
            st.markdown(render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
            
            stool_exam_raw = person.get("Stool exam", "")
            stool_cs_raw = person.get("Stool C/S", "")
            
            exam_text = interpret_stool_exam(stool_exam_raw)
            cs_text = interpret_stool_cs(stool_cs_raw)
            
            st.markdown(render_stool_html_table(exam_text, cs_text), unsafe_allow_html=True)

        with col_ua_right:
            # ============ X-ray Section ============
            st.markdown(render_section_header("ผลเอกซเรย์ (Chest X-ray)"), unsafe_allow_html=True)
            
            selected_year_int = int(selected_year)
            cxr_col = "CXR" if selected_year_int == (datetime.now().year + 543) else f"CXR{str(selected_year_int)[-2:]}"
            cxr_raw = person.get(cxr_col, "")
            cxr_result = interpret_cxr(cxr_raw)
            
            st.markdown(f"""
            <div style='
                background-color: var(--background-color);
                color: var(--text-color);
                line-height: 1.6;
                padding: 1.25rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                font-size: 14px;
            '>
                {cxr_result}
            </div>
            """, unsafe_allow_html=True)

            # ==================== EKG Section ====================
            st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ (EKG)"), unsafe_allow_html=True)

            ekg_col = get_ekg_col_name(selected_year_int)
            ekg_raw = person.get(ekg_col, "")
            ekg_result = interpret_ekg(ekg_raw)

            st.markdown(f"""
            <div style='
                background-color: var(--secondary-background-color);
                color: var(--text-color);
                line-height: 1.6;
                padding: 1.25rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                font-size: 14px;
            '>
                {ekg_result}
            </div>
            """, unsafe_allow_html=True)

            # ==================== Section: Hepatitis A ====================
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบเอ (Viral hepatitis A)"), unsafe_allow_html=True)
            
            hep_a_raw = safe_text(person.get("Hepatitis A"))
            st.markdown(f"""
            <div style='
                padding: 1rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                background-color: rgba(255,255,255,0.05);
                font-size: 14px;
            '>
                {hep_a_raw}
            </div>
            """, unsafe_allow_html=True)
            
            # ================ Section: Hepatitis B =================
            hep_check_date_raw = person.get("ปีตรวจHEP")
            hep_check_date = normalize_thai_date(hep_check_date_raw)
            
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)"), unsafe_allow_html=True)
            
            hbsag_raw = safe_text(person.get("HbsAg"))
            hbsab_raw = safe_text(person.get("HbsAb"))
            hbcab_raw = safe_text(person.get("HBcAB"))
            
            st.markdown(f"""
            <div style="margin-bottom: 1rem;">
            <table style='
                width: 100%;
                text-align: center;
                border-collapse: collapse;
                min-width: 300px;
                font-size: 14px;
            '>
                <thead>
                    <tr>
                        <th style="padding: 8px; border: 1px solid transparent;">HBsAg</th>
                        <th style="padding: 8px; border: 1px solid transparent;">HBsAb</th>
                        <th style="padding: 8px; border: 1px solid transparent;">HBcAb</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 8px; border: 1px solid transparent;">{hbsag_raw}</td>
                        <td style="padding: 8px; border: 1px solid transparent;">{hbsab_raw}</td>
                        <td style="padding: 8px; border: 1px solid transparent;">{hbcab_raw}</td>
                    </tr>
                </tbody>
            </table>
            </div>
            """, unsafe_allow_html=True)
            
            hep_history = safe_text(person.get("สรุปประวัติ Hepb"))
            hep_vaccine = safe_text(person.get("วัคซีนhep b 67"))

            st.markdown(f"""
            <div style='
                padding: 0.75rem 1rem;
                background-color: rgba(255,255,255,0.05);
                border-radius: 6px;
                margin-bottom: 1.5rem;
                line-height: 1.8;
                font-size: 14px;
            '>
                <b>วันที่ตรวจภูมิคุ้มกัน:</b> {hep_check_date}<br>
                <b>ประวัติโรคไวรัสตับอักเสบบี ปี พ.ศ. {selected_year}:</b> {hep_history}<br>
                <b>ประวัติการได้รับวัคซีนในปี พ.ศ. {selected_year}:</b> {hep_vaccine}
            </div>
            """, unsafe_allow_html=True)
            
            advice = hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw)
            
            if advice.strip() == "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี":
                bg_color = "rgba(57, 255, 20, 0.2)"
            else:
                bg_color = "rgba(255, 255, 0, 0.2)"

            st.markdown(f"""
            <div style='
                line-height: 1.6;
                padding: 1rem 1.5rem;
                border-radius: 6px;
                background-color: {bg_color};
                color: var(--text-color);
                margin-bottom: 1.5rem;
                font-size: 14px;
            '>
                {advice}
            </div>
            """, unsafe_allow_html=True)
            
    #=========================== ความเห็นแพทย์ =======================
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if doctor_suggestion.lower() in ["", "-", "none", "nan", "null"]:
        doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"

    left_spacer3, main_col_doc, right_spacer3 = st.columns([0.5, 6, 0.5])

    with main_col_doc:
        st.markdown(f"""
        <div style='
            background-color: #1b5e20;
            color: white;
            padding: 1.5rem 2rem;
            border-radius: 8px;
            line-height: 1.6;
            margin-top: 2rem;
            margin-bottom: 2rem;
            font-size: 14px;
        '>
            <b>สรุปความเห็นของแพทย์:</b><br> {doctor_suggestion}
        </div>
        """, unsafe_allow_html=True)

    # Doctor's Signature
    left_spacer4, signature_col, right_spacer4 = st.columns([0.5, 6, 0.5])
    with signature_col:
        st.markdown(f"""
        <div style='
            margin-top: 7rem;
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
