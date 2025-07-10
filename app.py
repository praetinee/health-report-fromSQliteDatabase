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
import streamlit.components.v1 as components # เพิ่ม Library สำหรับปุ่มพิมพ์

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
            table-layout: fixed; /* Ensure column widths are respected */
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

# ==================== PRINTING FUNCTIONALITY: START ====================

def _render_lab_table_for_print(title, subtitle, headers, rows):
    """Helper function to generate an HTML string for a lab table, for printing purposes."""
    full_title = f"{title}"
    if subtitle:
        full_title += f" ({subtitle})"

    html = f"<div class='section-header'>{full_title}</div>"
    html += "<table class='lab-table-print' style='width: 100%; border-collapse: collapse;'>"
    html += "<colgroup><col style='width:33.33%;'><col style='width:33.33%;'><col style='width:33.33%;'></colgroup>"
    html += "<thead><tr>"
    html += f"<th style='text-align: left; font-weight: bold;'>{headers[0]}</th>"
    html += f"<th style='text-align: center; font-weight: bold;'>{headers[1]}</th>"
    html += f"<th style='text-align: left; font-weight: bold;'>{headers[2]}</th>"
    html += "</tr></thead><tbody>"

    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = "lab-table-abn" if is_abn else ""
        html += f"<tr class='{row_class}'>"
        html += f"<td style='text-align: left;'>{row[0][0]}</td>"
        html += f"<td style='text-align: center;'>{row[1][0]}</td>"
        html += f"<td style='text-align: left;'>{row[2][0]}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html

def _render_urine_table_for_print(person_data, sex):
    """Generates an HTML string for the urine table for printing."""
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
    html = "<div class='section-header'>ผลการตรวจปัสสาวะ (Urinalysis)</div>"
    html += "<table class='urine-table-print' style='width: 100%; border-collapse: collapse;'>"
    html += "<thead><tr><th style='text-align:left; font-weight:bold;'>การตรวจ</th><th style='text-align:center; font-weight:bold;'>ผลตรวจ</th><th style='text-align:left; font-weight:bold;'>ค่าปกติ</th></tr></thead><tbody>"
    for test, result, normal in urine_data:
        is_abn = is_urine_abnormal(test, result, normal)
        row_class = "urine-abn" if is_abn else ""
        html += f"<tr class='{row_class}'><td>{test}</td><td style='text-align:center;'>{safe_value(result)}</td><td>{normal}</td></tr>"
    html += "</tbody></table>"
    return html


def generate_print_view_html(person_data):
    """
    Generates a self-contained HTML string of the entire report,
    formatted specifically for printing.
    """
    if not person_data:
        return ""

    # --- Re-fetch and calculate all necessary values ---
    sex = str(person_data.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    hb_low = 13 if sex == "ชาย" else 12
    hct_low = 39 if sex == "ชาย" else 36

    # CBC Data
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
        val = get_float(col, person_data)
        result, is_abn = flag(val, low, high)
        cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    # Blood Chemistry Data
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
        val = get_float(col, person_data)
        result, is_abn = flag(val, low, high, higher)
        blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    # General Advice
    advice_list = []
    advice_list.append(kidney_advice_from_summary(kidney_summary_gfr_only(person_data.get("GFR", ""))))
    advice_list.append(fbs_advice(person_data.get("FBS", "")))
    advice_list.append(liver_advice(summarize_liver(person_data.get("ALP", ""), person_data.get("SGOT", ""), person_data.get("SGPT", ""))))
    advice_list.append(uric_acid_advice(person_data.get("Uric Acid", "")))
    advice_list.append(lipids_advice(summarize_lipids(person_data.get("CHOL", ""), person_data.get("TGL", ""), person_data.get("LDL", ""))))
    advice_list.append(cbc_advice(person_data.get("Hb(%)", ""), person_data.get("HCT", ""), person_data.get("WBC (cumm)", ""), person_data.get("Plt (/mm)", ""), sex=sex))
    final_advice = merge_final_advice_grouped(advice_list)
    has_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice

    # --- Build the HTML string ---
    html_out = ""

    # Header
    html_out += f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 10px;">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p style="margin: 0;">ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p style="margin: 0;">ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
    </div>
    """

    # Patient Info
    try:
        age_str = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
        hn_str = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    except:
        age_str = person_data.get('อายุ', '-')
        hn_str = person_data.get('HN', '-')

    html_out += f"""
    <div class="patient-info-print" style="border: 1px solid #000; padding: 5px; margin-bottom: 5px;">
        <p><b>วันที่ตรวจ:</b> {person_data.get('วันที่ตรวจ', '-')} &nbsp;&nbsp;&nbsp; <b>ชื่อ-สกุล:</b> {person_data.get('ชื่อ-สกุล', '-')} &nbsp;&nbsp;&nbsp; <b>อายุ:</b> {age_str} ปี &nbsp;&nbsp;&nbsp; <b>เพศ:</b> {sex} &nbsp;&nbsp;&nbsp; <b>HN:</b> {hn_str} &nbsp;&nbsp;&nbsp; <b>หน่วยงาน:</b> {person_data.get('หน่วยงาน', '-')}</p>
    </div>
    """

    # Lab Results in two columns
    html_out += "<div style='display: flex; flex-direction: row; gap: 1rem; width: 100%;'>"
    html_out += "<div style='width: 50%;'>"
    html_out += _render_lab_table_for_print("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows)
    html_out += "</div>"
    html_out += "<div style='width: 50%;'>"
    html_out += _render_lab_table_for_print("ผลตรวจเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows)
    html_out += "</div>"
    html_out += "</div>"
    
    # Combined Advice
    if has_advice:
        html_out += f"<div class='advice-box'>{final_advice}</div>"

    # Other tests in two columns
    html_out += "<div style='display: flex; flex-direction: row; gap: 1rem; width: 100%; margin-top: 5px;'>"
    
    # Left Column (Urine, Stool)
    html_out += "<div style='width: 50%;'>"
    html_out += _render_urine_table_for_print(person_data, sex)
    
    urine_advice = advice_urine(sex, person_data.get("Alb", "-"), person_data.get("sugar", "-"), person_data.get("RBC1", "-"), person_data.get("WBC1", "-"))
    if urine_advice:
        html_out += f"<div class='advice-box' style='font-size: 8pt !important;'><b>คำแนะนำผลปัสสาวะ:</b> {urine_advice}</div>"

    html_out += "<div class='section-header' style='margin-top: 5px;'>ผลตรวจอุจจาระ (Stool Examination)</div>"
    stool_exam = interpret_stool_exam(person_data.get("Stool exam", ""))
    stool_cs = interpret_stool_cs(person_data.get("Stool C/S", ""))
    html_out += f"<p><b>ผลตรวจทั่วไป:</b> {stool_exam if stool_exam != '-' else 'ไม่ได้เข้ารับการตรวจ'}</p>"
    html_out += f"<p><b>ผลเพาะเชื้อ:</b> {cs_text if cs_text != '-' else 'ไม่ได้เข้ารับการตรวจ'}</p>"
    html_out += "</div>" # End Left Column

    # Right Column (X-Ray, EKG, Hepatitis)
    html_out += "<div style='width: 50%;'>"
    year_selected = int(person_data.get("Year", datetime.now().year + 543))
    cxr_col = "CXR" if year_selected == (datetime.now().year + 543) else f"CXR{str(year_selected)[-2:]}"
    cxr_result = interpret_cxr(person_data.get(cxr_col, ""))
    html_out += f"<div class='section-header'>ผลเอกซเรย์ (Chest X-ray)</div><p>{cxr_result}</p>"
    
    ekg_col = get_ekg_col_name(year_selected)
    ekg_result = interpret_ekg(person_data.get(ekg_col, ""))
    html_out += f"<div class='section-header' style='margin-top: 5px;'>ผลคลื่นไฟฟ้าหัวใจ (EKG)</div><p>{ekg_result}</p>"

    hep_a_result = safe_text(person_data.get("Hepatitis A"))
    html_out += f"<div class='section-header' style='margin-top: 5px;'>ผลตรวจไวรัสตับอักเสบเอ (Hepatitis A)</div><p>{hep_a_result}</p>"

    hbsag = safe_text(person_data.get("HbsAg"))
    hbsab = safe_text(person_data.get("HbsAb"))
    hbcab = safe_text(person_data.get("HBcAB"))
    hep_b_advice = hepatitis_b_advice(hbsag, hbsab, hbcab)
    html_out += f"<div class='section-header' style='margin-top: 5px;'>ผลตรวจไวรัสตับอักเสบบี (Hepatitis B)</div>"
    html_out += f"<p>HBsAg: {hbsag}, HBsAb: {hbsab}, HBcAb: {hbcab}</p>"
    html_out += f"<div class='advice-box' style='font-size: 8pt !important;'><b>สรุปผล:</b> {hep_b_advice}</div>"
    html_out += "</div>" # End Right Column

    html_out += "</div>" # End two-column layout

    # Doctor's Suggestion and Signature
    doctor_suggestion = str(person_data.get("DOCTER suggest", "")).strip()
    if doctor_suggestion.lower() in ["", "-", "none", "nan", "null"]:
        doctor_suggestion = "ไม่มีคำแนะนำจากแพทย์"

    html_out += f"""
    <div style='background-color: #f0f2f6 !important; border: 1px solid #000; padding: 5px; margin-top: 10px;'>
        <b>สรุปความเห็นของแพทย์:</b><br>{doctor_suggestion}
    </div>
    <div style='margin-top: 4rem; text-align: right; padding-right: 1rem;'>
        <div style='display: inline-block; text-align: center; width: 300px;'>
            <div style='border-bottom: 1px dotted #000; margin-bottom: 0.5rem; width: 100%;'></div>
            <div style='white-space: nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style='white-space: nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
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
        
        # Convert HN from potentially REAL type to integer string, stripping extra decimals
        df_loaded['HN'] = df_loaded['HN'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, int)) else str(x)).str.strip()

        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)

        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None], pd.NA, inplace=True)

        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

# --- Load data when the app starts. This line MUST be here and not inside any function or if block ---
df = load_sqlite_data()

# ==================== UI Setup and Search Form (Sidebar) ====================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# Inject custom CSS for font and size control (MODIFIED)
st.markdown("""
    <style>
    /* Import Sarabun font from Google Fonts */
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

    /* --- START: PRINT-SPECIFIC CSS --- */
    /* ซ่อน view สำหรับพิมพ์ในหน้าจอปกติ */
    .print-view { display: none; }

    @media print {
        @page {
            size: A4;
            margin: 0.8cm;
        }

        /* ซ่อน view ของหน้าเว็บ และแสดง view สำหรับพิมพ์ */
        .live-view { display: none !important; }
        .print-view { display: block !important; }

        /* ซ่อน Sidebar และ Header ของ Streamlit */
        [data-testid="stSidebar"], 
        header[data-testid="stHeader"] {
            display: none !important;
        }

        /* ตั้งค่า Layout หลัก */
        body, .main { margin: 0 !important; padding: 0 !important; }
        .main .block-container { padding: 0 !important; margin: 0 !important; width: 100% !important; max-width: 100% !important; }

        /* บังคับสีพื้นหลังและสีตัวอักษรสำหรับ Dark Mode */
        * {
            background: transparent !important;
            color: #000000 !important;
            box-shadow: none !important;
            text-shadow: none !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        /* จัดการ Layout คอลัมน์และระยะห่าง */
        div, p, table, th, td {
            page-break-inside: avoid !important;
            margin: 0 !important;
            padding: 1.5px !important;
            line-height: 1.25 !important;
            font-size: 8.5pt !important;
        }
        
        /* จัดการ Font และการจัดวางของ Header */
        h1, h2, .report-header-container p { text-align: center; }
        h1 { font-size: 14pt !important; margin-bottom: 2px !important; font-weight: bold; }
        h2 { font-size: 10pt !important; margin-bottom: 2px !important; }
        .report-header-container p { font-size: 8pt !important; line-height: 1.2 !important; margin-bottom: 1px !important; }
        .patient-info-print p { font-size: 9pt !important; text-align: left; margin-bottom: 3px !important; }
        hr { display: none !important; }
        
        /* บังคับให้แสดงสีพื้นหลังในส่วนที่กำหนด */
        .section-header, .advice-box, .lab-table-abn, .urine-abn {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        .section-header { background-color: #dddddd !important; color: black !important; border-radius: 4px; font-size: 9.5pt !important; padding: 3px !important; margin-top: 5px !important; margin-bottom: 3px !important; text-align: center; font-weight: bold; border: 1px solid #999 !important; }
        .advice-box { background-color: #f0f0f0 !important; padding: 4px !important; border-radius: 4px; margin-top: 5px !important; border: 1px solid #ccc !important; text-align: left !important; }
        .lab-table-abn td, .urine-abn td { background-color: #e0e0e0 !important; font-weight: bold; }
        .lab-table-print, .urine-table-print { border: 1px solid #ccc !important; }
        .lab-table-print td, .lab-table-print th, .urine-table-print td, .urine-table-print th { border: 1px solid #ccc !important; padding: 2px 4px !important; }

    }
    /* --- END: PRINT-SPECIFIC CSS --- */
    </style>
""", unsafe_allow_html=True)

# Main search form moved to sidebar
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
search_query = st.sidebar.text_input("กรอก HN หรือ ชื่อ-สกุล")
submitted_sidebar = st.sidebar.button("ค้นหา")


if submitted_sidebar:
    st.session_state.pop("search_result", None)
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    st.session_state.pop("selected_year_from_sidebar", None)
    st.session_state.pop("selected_exam_date_from_sidebar", None)
    st.session_state.pop("last_selected_year_sidebar", None) # Reset this on new search
    st.session_state.pop("last_selected_exam_date_sidebar", None) # Reset this on new search


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
            
            # Select the most recent year/date from the found results for a person
            first_available_year = sorted(query_df["Year"].dropna().unique().astype(int), reverse=True)[0]
            
            first_person_year_df = query_df[
                (query_df["Year"] == first_available_year) &
                (query_df["HN"] == query_df.iloc[0]["HN"]) # Use original HN for selecting row
            ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)
            
            if not first_person_year_df.empty:
                st.session_state["person_row"] = first_person_year_df.iloc[0].to_dict()
                st.session_state["selected_row_found"] = True
                st.session_state["selected_year_from_sidebar"] = first_available_year
                st.session_state["selected_exam_date_from_sidebar"] = first_person_year_df.iloc[0]["วันที่ตรวจ"]
                st.session_state["last_selected_year_sidebar"] = first_available_year # Initialize for subsequent year changes
                st.session_state["last_selected_exam_date_sidebar"] = first_person_year_df.iloc[0]["วันที่ตรวจ"] # Initialize
            else:
                st.session_state.pop("person_row", None)
                st.session_state.pop("selected_row_found", None)
                st.sidebar.error("❌ พบข้อมูลแต่ไม่สามารถแสดงผลได้ กรุณาลองใหม่")
    else:
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล เพื่อค้นหา")


# ==================== SELECT YEAR AND EXAM DATE IN SIDEBAR ====================

def update_year_selection():
    """Callback for year selectbox to ensure immediate update."""
    new_year = st.session_state["year_select_sidebar"]
    if st.session_state.get("last_selected_year_sidebar") != new_year:
        st.session_state["selected_year_from_sidebar"] = new_year
        st.session_state["last_selected_year_sidebar"] = new_year
        st.session_state.pop("selected_exam_date_from_sidebar", None)
        st.session_state.pop("person_row", None)
        st.session_state.pop("selected_row_found", None)

def update_exam_date_selection():
    """Callback for exam date selectbox to update person_row immediately."""
    new_exam_date = st.session_state["exam_date_select_sidebar"]
    if st.session_state.get("last_selected_exam_date_sidebar") != new_exam_date:
        st.session_state["selected_exam_date_from_sidebar"] = new_exam_date
        st.session_state["last_selected_exam_date_sidebar"] = new_exam_date


if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]

    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)

        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        
        current_selected_year_index = 0
        if "selected_year_from_sidebar" in st.session_state and st.session_state["selected_year_from_sidebar"] in available_years:
            current_selected_year_index = available_years.index(st.session_state["selected_year_from_sidebar"])
        
        selected_year_from_sidebar = st.selectbox(
            "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน",
            options=available_years,
            index=current_selected_year_index,
            format_func=lambda y: f"พ.ศ. {y}",
            key="year_select_sidebar",
            on_change=update_year_selection
        )

        if selected_year_from_sidebar:
            selected_hn = results_df.iloc[0]["HN"]

            person_year_df = results_df[
                (results_df["Year"] == selected_year_from_sidebar) &
                (results_df["HN"] == selected_hn)
            ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)

            exam_dates_options = person_year_df["วันที่ตรวจ"].dropna().unique().tolist()
            
            if exam_dates_options:
                if len(exam_dates_options) == 1:
                    st.session_state["selected_exam_date_from_sidebar"] = exam_dates_options[0]
                    st.session_state["person_row"] = person_year_df[
                        person_year_df["วันที่ตรวจ"] == st.session_state["selected_exam_date_from_sidebar"]
                    ].iloc[0].to_dict()
                    st.session_state["selected_row_found"] = True
                    st.sidebar.info(f"ผลตรวจวันที่: **{exam_dates_options[0]}**")
                else:
                    current_selected_exam_date_index = 0
                    if "selected_exam_date_from_sidebar" in st.session_state and st.session_state["selected_exam_date_from_sidebar"] in exam_dates_options:
                        current_selected_exam_date_index = exam_dates_options.index(st.session_state["selected_exam_date_from_sidebar"])
                    
                    selected_exam_date_from_sidebar = st.selectbox(
                        "🗓️ เลือกวันที่ตรวจ",
                        options=exam_dates_options,
                        index=current_selected_exam_date_index,
                        key="exam_date_select_sidebar",
                        on_change=update_exam_date_selection
                    )
                    
                    st.session_state["person_row"] = person_year_df[
                        person_year_df["วันที่ตรวจ"] == selected_exam_date_from_sidebar
                    ].iloc[0].to_dict()
                    st.session_state["selected_row_found"] = True
            else:
                st.info("ไม่พบข้อมูลการตรวจสำหรับปีที่เลือก")
                st.session_state.pop("person_row", None)
                st.session_state.pop("selected_row_found", None)
        
        # --- START: PRINT BUTTON LOGIC ---
        # ปุ่มจะแสดงก็ต่อเมื่อมีข้อมูล person_row พร้อมแล้ว
        if st.session_state.get('person_row'):
            st.markdown("---")
            
            print_button_html = """
                <!DOCTYPE html><html><head><style>
                body { margin: 0; font-family: 'Sarabun', sans-serif; }
                #print-btn { 
                    display: inline-flex; align-items: center; justify-content: center; 
                    font-weight: 400; padding: .25rem .75rem; border-radius: .5rem; 
                    min-height: 38.4px; margin: 0; line-height: 1.6; 
                    color: #31333F; width: 100%; user-select: none; 
                    background-color: #FFFFFF; border: 1px solid rgba(49, 51, 63, 0.2); 
                    box-sizing: border-box; cursor: pointer; 
                }
                #print-btn:hover { border: 1px solid #FF4B4B; color: #FF4B4B; }
                </style></head><body>
                  <button id="print-btn">🖨️ พิมพ์รายงานนี้</button>
                  <script>
                    document.getElementById('print-btn').addEventListener('click', () => window.parent.print());
                  </script>
                </body></html>
            """
            components.html(print_button_html, height=40)
        # --- END: PRINT BUTTON LOGIC ---


# ==================== Display Health Report (Main Content) ====================
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    
    # --- START: PRINT VIEW GENERATION ---
    # สร้าง HTML สำหรับการพิมพ์และเก็บไว้ในตัวแปร (จะถูกแสดงใน div ที่ซ่อนไว้)
    person = st.session_state["person_row"]
    print_html_content = generate_print_view_html(person)
    st.markdown(f'<div class="print-view">{print_html_content}</div>', unsafe_allow_html=True)
    # --- END: PRINT VIEW GENERATION ---

    # --- START: LIVE VIEW WRAPPER ---
    # ครอบการแสดงผลปกติด้วย div class "live-view" เพื่อให้ซ่อนได้ตอนพิมพ์
    st.markdown('<div class="live-view">', unsafe_allow_html=True)
    
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
    selected_year = st.session_state.get("selected_year_from_sidebar", None)
    if selected_year is None:
        selected_year = datetime.now().year + 543

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
    # if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    # person = st.session_state["person_row"]
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if doctor_suggestion.lower() in ["", "-", "none", "nan", "null"]:
        doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"

    left_spacer3, doctor_col, right_spacer3 = st.columns([0.5, 6, 0.5])

    with doctor_col:
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
    
    # --- END: LIVE VIEW WRAPPER ---
    # ปิด div ของ live-view
    st.markdown('</div>', unsafe_allow_html=True)
