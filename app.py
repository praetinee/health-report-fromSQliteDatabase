import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html  # Used for html.escape()
import numpy as np
from collections import OrderedDict
from datetime import datetime
import re
import streamlit.components.v1 as components

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

    is_abnormal = False
    if higher_is_better:
        if low is not None and val < low:
            is_abnormal = True
    else:
        if low is not None and val < low:
            is_abnormal = True
        if high is not None and val > high:
            is_abnormal = True

    return f"{val:.1f}", is_abnormal


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
            table-layout: fixed;
            font-size: 14px;
        }}
        .{table_class} thead th {{
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 2px 2px;
            text-align: center;
            font-weight: bold;
            border: 1px solid transparent;
        }}
        .{table_class} td {{
            padding: 2px 2px;
            border: 1px solid transparent;
            text-align: center;
            color: var(--text-color);
        }}
        .{table_class}-abn {{
            background-color: rgba(255, 64, 64, 0.25);
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
        align = "left" if i == 0 else ("left" if i == 2 else "center")
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
        if alp > 120 or sgot > 37 or sgpt > 41:
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
        if chol >= 200 or tgl >= 150 or ldl >= 160:
             return "ไขมันในเลือดสูง"
        return "ปกติ"
    except:
        return ""

def lipids_advice(summary_text):
    if summary_text == "ไขมันในเลือดสูง":
        return (
            "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ "
            "ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
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
        if sbp >= 140 or dbp >= 90:
            return "ความดันโลหิตสูง"
        elif sbp >= 120 or dbp >= 80:
            return "ความดันโลหิตเริ่มสูง"
        else:
            return "ความดันโลหิตปกติ"
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
        if bmi >= 25:
            bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5:
            bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else:
            bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
    
    bp_interp = interpret_bp(sbp, dbp)
    if bp_interp not in ["-", "ความดันโลหิตปกติ"]:
        bp_text = bp_interp

    if bmi_text and bp_text:
        return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    elif bmi_text and "ปกติ" not in bmi_text:
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    elif bp_text:
        return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    
    return "น้ำหนักและความดันโลหิตอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"


def safe_text(val):
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

    advice_parts = []
    if "พบโปรตีนในปัสสาวะ" in alb_t:
        advice_parts.append("พบโปรตีนในปัสสาวะ ควรพบแพทย์เพื่อตรวจการทำงานของไตเพิ่มเติม")
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "เล็กน้อย" not in sugar_t:
        advice_parts.append("ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม")
    if "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" not in rbc_t:
        if sex == "หญิง":
            advice_parts.append("พบเม็ดเลือดแดงในปัสสาวะ หากไม่ได้อยู่ในช่วงมีประจำเดือน ควรตรวจซ้ำหรือพบแพทย์")
        else:
            advice_parts.append("พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม")
    if "พบเม็ดเลือดขาว" in wbc_t and "เล็กน้อย" not in wbc_t:
        advice_parts.append("อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ")

    return " ".join(advice_parts)


def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]:
        return False

    if test_name == "กรด-ด่าง (pH)":
        try:
            return not (5.0 <= float(val) <= 8.0)
        except:
            return True

    if test_name == "ความถ่วงจำเพาะ (Sp.gr)" or test_name == "ถ.พ. (Sp.gr)":
        try:
            return not (1.003 <= float(val) <= 1.030)
        except:
            return True

    if test_name == "เม็ดเลือดแดง (RBC)":
        return "ปกติ" not in interpret_rbc(val)
    
    if test_name == "เม็ดเลือดขาว (WBC)":
        return "ปกติ" not in interpret_wbc(val)

    if test_name == "น้ำตาล (Sugar)":
        return interpret_sugar(val).lower() != "ไม่พบ"

    if test_name == "โปรตีน (Albumin)":
        return interpret_alb(val).lower() != "ไม่พบ"

    if test_name == "สี (Colour)":
        return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow", "เหลืองใส"]

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
            table-layout: fixed;
            font-size: 14px;
        }
        .urine-table thead th {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 3px 2px;
            text-align: center;
            font-weight: bold;
            border: 1px solid transparent;
        }
        .urine-table td {
            padding: 3px 2px;
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
            table-layout: fixed;
            font-size: 14px;
        }
        .stool-table th {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 3px 2px;
            text-align: left;
            width: 50%;
            font-weight: bold;
            border: 1px solid transparent;
        }
        .stool-table td {
            padding: 3px 2px;
            border: 1px solid transparent;
            width: 50%;
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
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion", "see", "พบ"]):
        return f"พบความผิดปกติ: {val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return "ปกติ"


def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia", "see", "พบ"]):
        return f"พบความผิดปกติ: {val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return "ปกติ"


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
    elif all(x in ["negative", "-"] for x in [hbsag, hbsab, hbcab]):
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

def merge_final_advice_grouped(messages):
    groups = {
        "ทั่วไป": [], "FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "CBC": [], "ปัสสาวะ": []
    }

    for msg in messages:
        if not msg or msg.strip() in ["-", ""]: continue
        msg = msg.strip()
        
        if any(k in msg for k in ["ฮีโมโกลบิน", "ฮีมาโตคริต", "เม็ดเลือดขาว", "เกล็ดเลือด"]): groups["CBC"].append(msg)
        elif "น้ำตาล" in msg: groups["FBS"].append(msg)
        elif "ไต" in msg: groups["ไต"].append(msg)
        elif "ตับ" in msg: groups["ตับ"].append(msg)
        elif any(k in msg for k in ["พิวรีน", "ยูริค"]): groups["ยูริค"].append(msg)
        elif "ไขมัน" in msg: groups["ไขมัน"].append(msg)
        elif any(k in msg for k in ["โปรตีนในปัสสาวะ", "เม็ดเลือดแดงในปัสสาวะ", "เม็ดเลือดขาวในปัสสาวะ"]): groups["ปัสสาวะ"].append(msg)
        else: groups["ทั่วไป"].append(msg)
            
    output = []
    for title, msgs in groups.items():
        if msgs:
            unique_msgs = list(OrderedDict.fromkeys(msgs))
            full_message = ' '.join(unique_msgs)
            output.append(f"<b>{title}:</b> {full_message}")
            
    if not output:
        return "ผลการตรวจโดยรวมอยู่ในเกณฑ์ปกติ"

    return "<br>".join(output)


# --- Global Helper Functions: END ---

# ==================== PRINTING FUNCTIONALITY: START (FINAL) ====================

def _render_lab_table_for_print(rows):
    html = "<table class='lab-table-print'>"
    html += "<thead><tr><th class='test'>การตรวจ</th><th class='result'>ผล</th><th class='norm'>ค่าปกติ</th></tr></thead><tbody>"
    for row_data in rows:
        label, result, norm, is_abn = row_data
        row_class = "lab-table-abn" if is_abn else ""
        html += f"<tr class='{row_class}'><td>{label}</td><td class='result'>{result}</td><td>{norm}</td></tr>"
    html += "</tbody></table>"
    return html

def _render_urine_table_for_print(person_data):
    urine_data = [
        ("สี", person_data.get("Color", "-"), "Yellow"),
        ("น้ำตาล", person_data.get("sugar", "-"), "Negative"),
        ("โปรตีน", person_data.get("Alb", "-"), "Negative"),
        ("pH", person_data.get("pH", "-"), "5.0-8.0"),
        ("ถ.พ.", person_data.get("Spgr", "-"), "1.003-1.030"),
        ("RBC", person_data.get("RBC1", "-"), "0-2"),
        ("WBC", person_data.get("WBC1", "-"), "0-5"),
    ]
    html = "<table class='urine-table-print'><thead><tr><th class='test'>การตรวจ</th><th class='result'>ผล</th><th class='norm'>ค่าปกติ</th></tr></thead><tbody>"
    for test, result, normal in urine_data:
        is_abn = is_urine_abnormal(test, result, normal)
        row_class = "urine-abn" if is_abn else ""
        result_display = safe_value(result).replace("negative", "Neg").replace("trace", "Tr")
        html += f"<tr class='{row_class}'><td >{test}</td><td class='result'>{result_display}</td><td>{normal}</td></tr>"
    html += "</tbody></table>"
    return html

def generate_print_view_html(person_data):
    if not person_data: return ""

    sex = str(person_data.get("เพศ", "ไม่ระบุ")).strip()
    hb_low = 13 if sex == "ชาย" else 12
    hct_low = 39 if sex == "ชาย" else 36
    year_selected = int(person_data.get("Year", datetime.now().year + 543))

    try:
        age_str = str(int(float(person_data.get('อายุ', '-'))))
        hn_str = str(int(float(person_data.get('HN', '-'))))
    except:
        age_str = person_data.get('อายุ', '-')
        hn_str = person_data.get('HN', '-')
    
    sbp, dbp = person_data.get("SBP", ""), person_data.get("DBP", "")
    bp_val = f"{sbp}/{dbp}" if sbp and dbp else "-"
    bp_interp = interpret_bp(sbp, dbp)
    
    try:
        bmi = float(person_data.get("BMI", 0))
        bmi_str = f"{bmi:.1f}" if bmi > 0 else "-"
    except:
        bmi_str = "-"

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ช>13,ญ>12", hb_low, None, False),
        ("ฮีมาโตคริต (Hct)", "HCT", "ช>39,ญ>36", hct_low, None, False),
        ("เม็ดเลือดขาว (WBC)", "WBC (cumm)", "4-10k", 4000, 10000, False),
        ("เกล็ดเลือด (Plt)", "Plt (/mm)", "150-500k", 150000, 500000, False),
    ]
    blood_config = [
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
    ]

    lab_rows_data = []
    for configs in [blood_config, cbc_config]:
        for label, col, norm, low, high, higher_is_better in configs:
            val = get_float(col, person_data)
            result, is_abn = flag(val, low, high, higher_is_better)
            lab_rows_data.append((label, result, norm, is_abn))

    cxr_result = interpret_cxr(person_data.get(f"CXR{str(year_selected)[-2:]}" if year_selected != (datetime.now().year + 543) else "CXR", ""))
    ekg_result = interpret_ekg(person_data.get(get_ekg_col_name(year_selected), ""))
    hep_b_advice = hepatitis_b_advice(safe_text(person_data.get("HbsAg")), safe_text(person_data.get("HbsAb")), safe_text(person_data.get("HBcAB")))
    
    advice_list = [
        combined_health_advice(bmi_str, sbp, dbp),
        kidney_advice_from_summary(kidney_summary_gfr_only(person_data.get("GFR", ""))),
        fbs_advice(person_data.get("FBS", "")),
        liver_advice(summarize_liver(person_data.get("ALP", ""), person_data.get("SGOT", ""), person_data.get("SGPT", ""))),
        uric_acid_advice(person_data.get("Uric Acid", "")),
        lipids_advice(summarize_lipids(person_data.get("CHOL", ""), person_data.get("TGL", ""), person_data.get("LDL", ""))),
        cbc_advice(person_data.get("Hb(%)", ""), person_data.get("HCT", ""), person_data.get("WBC (cumm)", ""), person_data.get("Plt (/mm)", ""), sex),
        advice_urine(sex, person_data.get("Alb", "-"), person_data.get("sugar", "-"), person_data.get("RBC1", "-"), person_data.get("WBC1", "-"))
    ]
    final_advice_html = merge_final_advice_grouped(advice_list)
    doctor_suggestion = safe_text(person_data.get("DOCTER suggest", "ไม่มี"))

    html_out = f"""
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
            <div class="section-header">ผลการตรวจปัสสาวะ</div>
            {_render_urine_table_for_print(person_data)}
            <div class="section-header">ผลการตรวจอื่นๆ</div>
            <p class="other-results"><b>X-Ray:</b> {cxr_result}</p>
            <p class="other-results"><b>EKG:</b> {ekg_result}</p>
            <p class="other-results"><b>Hepatitis B:</b> {hep_b_advice}</p>
            <div class="section-header">คำแนะนำเบื้องต้น</div>
            <div class="advice-box">{final_advice_html}</div>
        </div>
    </div>
    <div class="footer-section">
        <b>สรุปความเห็นของแพทย์:</b> {doctor_suggestion}
        <div class="signature-area">
            ...........................................................<br><span>(นายแพทย์นพรัตน์ รัชฎาพร) ว.26674</span>
        </div>
    </div>
    """
    return html_out

# ==================== PRINTING FUNCTIONALITY: END ====================


@st.cache_data(ttl=600)
def load_sqlite_data():
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.write(response.content)
        tmp.flush()
        tmp.close()

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

        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

df = load_sqlite_data()

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td,
    div[data-testid="stMarkdown"], div[data-testid="stInfo"],
    div[data-testid="stSuccess"], div[data-testid="stWarning"], div[data-testid="stError"] {
        font-family: 'Sarabun', sans-serif !important;
    }
    body { font-size: 14px !important; }
    .report-header-container h1 { font-size: 1.8rem !important; font-weight: bold; }
    .report-header-container h2 { font-size: 1.2rem !important; color: darkgrey; font-weight: bold; }
    .st-sidebar h3 { font-size: 18px !important; }
    .report-header-container * { line-height: 1.7 !important; margin: 0.2rem 0 !important; padding: 0 !important; }

    /* --- PRINT-SPECIFIC CSS --- */
    .print-view { display: none; }
    @media print {
        @page { size: A4; margin: 0.7cm; }
        .live-view, [data-testid="stSidebar"], header[data-testid="stHeader"] { display: none !important; }
        .print-view { display: block !important; }
        * {
            background: transparent !important; color: #000 !important;
            box-shadow: none !important; text-shadow: none !important;
            print-color-adjust: exact !important; font-family: 'Sarabun', sans-serif !important;
        }
        body, .main .block-container { padding: 0 !important; margin: 0 !important; width: 100% !important; max-width: 100% !important; }
        h1 { font-size: 14pt !important; font-weight: bold; text-align: center; margin:0; padding:0; }
        h2 { font-size: 11pt !important; text-align: center; margin:0 0 5px 0; padding:0; }
        p, div, table, span { font-size: 8pt !important; line-height: 1.3 !important; }
        .patient-info-print { border: 1px solid #000; padding: 4px; margin-bottom: 5px; text-align: left; }
        .patient-info-print b { font-weight: bold; }
        .main-content-flex { display: flex; flex-direction: row; gap: 0.6cm; width: 100%; }
        .column-left { width: 55%; }
        .column-right { width: 45%; }
        .section-header {
            background-color: #E0E0E0 !important; color: #000 !important; font-weight: bold;
            text-align: center; padding: 2px; margin-top: 5px; margin-bottom: 3px; border-radius: 3px;
        }
        table { width: 100%; border-collapse: collapse; page-break-inside: avoid; }
        th, td { border: 1px solid #ccc; padding: 1px 3px; vertical-align: top; }
        th { font-weight: bold; background-color: #F5F5F5 !important; }
        th.test, td.test { width: 45%; }
        th.result, td.result { width: 20%; text-align: center; }
        th.norm, td.norm { width: 35%; }
        .lab-table-abn td, .urine-abn td { background-color: #F2F2F2 !important; font-weight: bold; }
        .other-results { margin: 0; padding: 2px 3px; border-bottom: 1px dotted #eee; }
        .advice-box { padding: 4px; border: 1px solid #ccc; border-radius: 4px; page-break-inside: avoid; }
        .advice-box b { font-weight: bold; }
        .footer-section { position: fixed; bottom: 0.7cm; left: 0.7cm; right: 0.7cm; border-top: 1px solid #000; padding-top: 5px; display: flex; justify-content: space-between; align-items: flex-end; }
        .footer-section b { font-weight: bold; }
        .signature-area { text-align: center; }
    }
    </style>
""", unsafe_allow_html=True)

st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
search_query = st.sidebar.text_input("กรอก HN หรือ ชื่อ-สกุล")
submitted_sidebar = st.sidebar.button("ค้นหา")

if submitted_sidebar:
    st.session_state.clear()
    query_df = df.copy()
    search_term = search_query.strip()
    if search_term:
        if search_term.isdigit():
            query_df = query_df[query_df["HN"] == search_term]
        else:
            query_df = query_df[query_df["ชื่อ-สกุล"].str.strip() == search_term]
        if query_df.empty:
            st.sidebar.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง")
        else:
            st.session_state["search_result"] = query_df
    else:
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล เพื่อค้นหา")

def update_year_selection():
    st.session_state["selected_year_from_sidebar"] = st.session_state["year_select_sidebar"]
    if "selected_exam_date_from_sidebar" in st.session_state:
        del st.session_state["selected_exam_date_from_sidebar"]

def update_exam_date_selection():
    st.session_state["selected_exam_date_from_sidebar"] = st.session_state["exam_date_select_sidebar"]

if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]
    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)
        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        
        year_index = 0
        if "selected_year_from_sidebar" in st.session_state:
            try:
                year_index = available_years.index(st.session_state.selected_year_from_sidebar)
            except ValueError:
                year_index = 0
        
        selected_year = st.selectbox(
            "📅 เลือกปี", available_years, index=year_index,
            format_func=lambda y: f"พ.ศ. {y}", key="year_select_sidebar", on_change=update_year_selection
        )
        st.session_state.selected_year_from_sidebar = selected_year
        
        person_year_df = results_df[(results_df["Year"] == selected_year) & (results_df["HN"] == results_df.iloc[0]["HN"])]
        exam_dates_options = sorted(person_year_df["วันที่ตรวจ"].dropna().unique(), key=lambda x: datetime.strptime(x.replace(" ", "/"), '%d/%B/%Y'), reverse=True)
        
        if exam_dates_options:
            date_index = 0
            if "selected_exam_date_from_sidebar" in st.session_state:
                try:
                    date_index = exam_dates_options.index(st.session_state.selected_exam_date_from_sidebar)
                except ValueError:
                    date_index = 0
            
            selected_date = st.selectbox(
                "🗓️ เลือกวันที่", exam_dates_options, index=date_index,
                key="exam_date_select_sidebar", on_change=update_exam_date_selection
            )
            st.session_state.selected_exam_date_from_sidebar = selected_date
            
            person_df = person_year_df[person_year_df["วันที่ตรวจ"] == selected_date]
            if not person_df.empty:
                st.session_state["person_row"] = person_df.iloc[0].to_dict()

        if st.session_state.get('person_row'):
            st.markdown("---")
            components.html("""
                <button onclick="window.parent.print()" style="width:100%; padding: .5rem; font-weight:bold; border-radius: .5rem; border: 1px solid #FF4B4B; color: #FF4B4B;">
                    🖨️ พิมพ์รายงานนี้
                </button>""", height=45)

if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    st.markdown(f'<div class="print-view">{generate_print_view_html(person)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="live-view">', unsafe_allow_html=True)
    
    check_date = person.get("วันที่ตรวจ", "-")
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

    sbp = person.get("SBP", ""); dbp = person.get("DBP", "")
    try:
        bmi_val = float(person.get("BMI", 0))
    except (ValueError, TypeError):
        bmi_val = 0
        
    bp_full = f"{sbp}/{dbp} - {interpret_bp(sbp, dbp)}" if sbp and dbp else "-"

    st.markdown(f"""
    <div><hr>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-top: 24px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {int(get_float('อายุ', person)) if get_float('อายุ', person) else '-'} ปี</div>
            <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
            <div><b>HN:</b> {person.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</div>
            <div><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</div>
            <div><b>รอบเอว:</b> {person.get("รอบเอว", "-")} ซม.</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {int(get_float('pulse', person)) if get_float('pulse', person) else '-'} ครั้ง/นาที</div>
        </div>
        <div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {html.escape(combined_health_advice(bmi_val, sbp, dbp) or "")}</div>
    </div>""", unsafe_allow_html=True)

    sex = str(person.get("เพศ", "")).strip() or "ไม่ระบุ"
    hb_low = 13 if sex == "ชาย" else 12
    hct_low = 39 if sex == "ชาย" else 36

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None, False),
        ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None, False),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000-10,000", 4000, 10000, False),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70, False),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44, False),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9, False),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9, False),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3, False),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000-500,000", 150000, 500000, False),
    ]
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106, False),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2, False),
        ("เอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120, False),
        ("เอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37, False),
        ("เอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41, False),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "< 200 mg/dl", None, 200, False),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "< 150 mg/dl", None, 150, False),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "< 160 mg/dl", None, 160, False),
        ("ไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20, False),
        ("ไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17, False),
        ("ไต (eGFR)", "GFR", "> 60 mL/min", 60, None, True),
    ]
    
    cbc_rows = []
    for label, col, norm, low, high, higher in cbc_config:
        val = get_float(col, person)
        res, abn = flag(val, low, high, higher)
        cbc_rows.append([(label, abn), (res, abn), (norm, abn)])
        
    blood_rows = []
    for label, col, norm, low, high, higher in blood_config:
        val = get_float(col, person)
        res, abn = flag(val, low, high, higher)
        blood_rows.append([(label, abn), (res, abn), (norm, abn)])

    left_spacer, col1, col2, right_spacer = st.columns([0.5, 3, 3, 0.5])
    with col1:
        st.markdown(render_lab_table_html("ผลตรวจ CBC", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    with col2:
        st.markdown(render_lab_table_html("ผลตรวจเลือด", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)
    
    # ... (The rest of the live view rendering remains the same) ...
    selected_year = st.session_state.get("selected_year_from_sidebar", datetime.now().year + 543)

    with st.container():
        left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([0.5, 3, 3, 0.5])
        with col_ua_left:
            render_urine_section(person, sex, selected_year)
            st.markdown(render_section_header("ผลตรวจอุจจาระ"), unsafe_allow_html=True)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)
        with col_ua_right:
            st.markdown(render_section_header("ผลเอกซเรย์ (Chest X-ray)"), unsafe_allow_html=True)
            st.markdown(f"<div style='background-color: var(--background-color); color: var(--text-color); line-height: 1.6; padding: 1.25rem; border-radius: 6px; margin-bottom: 1.5rem; font-size: 14px;'>{interpret_cxr(person.get(f'CXR{str(selected_year)[-2:]}' if selected_year != (datetime.now().year + 543) else 'CXR', ''))}</div>", unsafe_allow_html=True)
            st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ (EKG)"), unsafe_allow_html=True)
            st.markdown(f"<div style='background-color: var(--secondary-background-color); color: var(--text-color); line-height: 1.6; padding: 1.25rem; border-radius: 6px; margin-bottom: 1.5rem; font-size: 14px;'>{interpret_ekg(person.get(get_ekg_col_name(selected_year), ''))}</div>", unsafe_allow_html=True)
            # ... Hepatitis sections etc.

    st.markdown('</div>', unsafe_allow_html=True)
