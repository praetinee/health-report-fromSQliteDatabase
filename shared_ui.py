# shared_ui.py
# ฟังก์ชัน UI สำหรับ Streamlit ที่ใช้ฟอนต์ Sarabun ทั่วทั้งหน้า และแก้ปัญหา icon สัญลักษณ์ไม่ขึ้น โดยใช้ font-family fallback

import streamlit as st
import pandas as pd
import re
import html
import numpy as np
from collections import OrderedDict
from datetime import datetime
import json

from performance_tests import interpret_audiogram, interpret_lung_capacity, generate_comprehensive_recommendations

# --- Helper Functions ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
    if is_empty(name): return ""
    return re.sub(r'\s+', '', str(name).strip())

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
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
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table"):
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
    urine_data = [("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"),
                  ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"),
                  ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"),
                  ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"),
                  ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"),
                  ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"),
                  ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"),
                  ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"),
                  ("อื่นๆ", person_data.get("ORTER", "-"), "-")]
    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    html_content = render_lab_table_html(
        "ผลการตรวจปัสสาวะ (Urinalysis)",
        ["การตรวจ", "ผล", "ค่าปกติ"],
        [[(row["การตรวจ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])),
          (safe_value(row["ผลตรวจ"]), is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])),
          (row["ค่าปกติ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"]))]
         for _, row in df_urine.iterrows()],
        table_class="lab-table"
    )
    st.markdown(html_content, unsafe_allow_html=True)
    return any(not is_empty(val) for _, val, _ in urine_data)

def interpret_stool_exam(val):
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    if is_empty(value): return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
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
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
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

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

        html, body, [class*="st-"], .st-emotion-cache-10trblm, h1, h2, h3, h4, h5, h6 {
            font-family: 'Sarabun', Arial, sans-serif !important;
        }

        /* fix icon fallback for expanders and similar Streamlit icons */
        [data-testid="stExpanderIcon"] > span, .st-emotion-cache-p5msec.e1f1d6gn0, .st-emotion-cache-1g8p97v.e1f1d6gn0, [data-testid="stIcon"], span.material-icons, i.material-icons {
            font-family: 'Material Icons', Arial, sans-serif !important;
            font-style: normal !important;
            font-weight: normal !important;
            speak: none !important;
            font-size: inherit !important;
            line-height: 1 !important;
            letter-spacing: normal !important;
            text-transform: none !important;
            display: inline-block !important;
            white-space: nowrap !important;
            direction: ltr !important;
            -webkit-font-feature-settings: 'liga' !important;
            -webkit-font-smoothing: antialiased !important;
        }

        /* ... CSS เดิมทั้งหมด ... */
    </style>
    """, unsafe_allow_html=True)

# ... ส่วนฟังก์ชันที่เหลือ display_common_header, display_main_report ฯลฯ (คงเดิม)
# สามารถ copy มาใช้ต่อได้ เพราะส่วนสำคัญคือ inject_custom_css()
