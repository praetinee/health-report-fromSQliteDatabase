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
import streamlit.components.v1 as components # เปลี่ยนมาใช้ component ของ streamlit โดยตรง

# --- ALL HELPER FUNCTIONS (No Changes) ---
# โค้ดในส่วนของฟังก์ชันทั้งหมดเหมือนเดิมทุกประการ
def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]
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
    if is_empty(date_str): return "-"
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()
    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]: return s
    try:
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/')); year -= 543 if year > 2500 else 0
            return f"{day} {THAI_MONTHS_GLOBAL[month]} {year + 543}"
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-')); year -= 543 if year > 2500 else 0
            return f"{day} {THAI_MONTHS_GLOBAL[month]} {year + 543}"
        match = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match:
            day, month_str, year = int(match.group('day1')), match.group('month_str').strip('.'), int(match.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num: return f"{day} {THAI_MONTHS_GLOBAL[month_num]} {year}"
    except: pass
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(dt):
            year = dt.year - 543 if dt.year > datetime.now().year + 50 else dt.year
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {year + 543}"
    except: pass
    return str(date_str)
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
    if higher_is_better and low is not None: return f"{val:.1f}", val < low
    if low is not None and val < low: return f"{val:.1f}", True
    if high is not None and val > high: return f"{val:.1f}", True
    return f"{val:.1f}", False
def render_section_header(title, subtitle=None):
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""<div style='background-color: #1b5e20; color: white; text-align: center; padding: 0.8rem 0.5rem; font-weight: bold; border-radius: 8px; margin-top: 2rem; margin-bottom: 1rem; font-size: 14px;'>{full_title}</div>"""
def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    style = f"""<style>
        .{table_class}-container {{ margin-top: 1rem; }}
        .{table_class} {{ width: 100%; border-collapse: collapse; color: var(--text-color); table-layout: fixed; font-size: 14px; }}
        .{table_class} thead th {{ background-color: var(--secondary-background-color); color: var(--text-color); padding: 2px 2px; text-align: center; font-weight: bold; border: 1px solid transparent; }}
        .{table_class} td {{ padding: 2px 2px; border: 1px solid transparent; text-align: center; color: var(--text-color); }}
        .{table_class}-abn {{ background-color: rgba(255, 64, 64, 0.25); }}
        .{table_class}-row {{ background-color: rgba(255,255,255,0.02); }}
    </style>"""
    header_html = render_section_header(title, subtitle)
    html_content = f"{style}{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    html_content += """<colgroup><col style="width: 33.33%;"><col style="width: 33.33%;"><col style="width: 33.33%;"></colgroup>"""
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 or i == 2 else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else f"{table_class}-row"
        html_content += "<tr>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td class='{row_class}'>{row[1][0]}</td>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"
        html_content += "</tr>"
    html_content += "</tbody></table></div>"
    return html_content
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
        alp, sgot, sgpt = float(alp_val), float(sgot_val), float(sgpt_val)
        if alp == 0 or sgot == 0 or sgpt == 0: return "-"
        if alp > 120 or sgot > 36 or sgpt > 40: return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except: return ""
def liver_advice(summary_text):
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย": return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    return "" if summary_text == "ปกติ" else "-"
def uric_acid_advice(value_raw):
    try:
        value = float(value_raw)
        if value > 7.2: return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except: return "-"
def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    try:
        chol, tgl, ldl = float(str(chol_raw).replace(",", "").strip()), float(str(tgl_raw).replace(",", "").strip()), float(str(ldl_raw).replace(",", "").strip())
        if chol == 0 and tgl == 0: return ""
        if chol >= 250 or tgl >= 250 or ldl >= 180: return "ไขมันในเลือดสูง"
        elif chol <= 200 and tgl <= 150: return "ปกติ"
        else: return "ไขมันในเลือดสูงเล็กน้อย"
    except: return ""
def lipids_advice(summary_text):
    if summary_text == "ไขมันในเลือดสูง": return "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
    elif summary_text == "ไขมันในเลือดสูงเล็กน้อย": return "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน และออกกำลังกายเพื่อควบคุมระดับไขมัน"
    return ""
def cbc_advice(hb, hct, wbc, plt, sex="ชาย"):
    advice_parts = []
    try:
        hb_val, hb_ref = float(hb), 13 if sex == "ชาย" else 12
        if hb_val < hb_ref: advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    except: pass
    try:
        hct_val, hct_ref = float(hct), 39 if sex == "ชาย" else 36
        if hct_val < hct_ref: advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
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
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        elif sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80: return "ความดันปกติ"
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
    elif val in ["trace", "1+", "2+"]: return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif val in ["3+", "4+"]: return "พบโปรตีนในปัสสาวะ"
    return "-"
def interpret_sugar(value):
    val = str(value).strip().lower()
    if val == "negative": return "ไม่พบ"
    elif val == "trace": return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif val in ["1+", "2+", "3+", "4+", "5+", "6+"]: return "พบน้ำตาลในปัสสาวะ"
    return "-"
def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val: low, high = map(float, val.split("-")); return low, high
        else: num = float(val); return num, num
    except: return None, None
def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    low, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 2: return "ปกติ"
    elif high <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else: return "พบเม็ดเลือดแดงในปัสสาวะ"
def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    low, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 5: return "ปกติ"
    elif high <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else: return "พบเม็ดเลือดขาวในปัสสาวะ"
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
    if test_name == "น้ำตาล (Sugar)": return interpret_sugar(val).lower() != "ไม่พบ"
    if test_name == "โปรตีน (Albumin)": return interpret_alb(val).lower() != "ไม่พบ"
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False
def render_urine_section(person_data, sex, year_selected):
    urine_data = [("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"),("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"),("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"),("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"),("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"),("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"),("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"),("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"),("อื่นๆ", person_data.get("ORTER", "-"), "-"),]
    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    html_content = render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis") + "<div class='urine-table-container'><table class='urine-table' style='font-size:14px;width:100%;border-collapse:collapse;table-layout:fixed;'><colgroup><col style='width:33.33%;'><col style='width:33.33%;'><col style='width:33.33%;'></colgroup><thead><tr><th style='text-align:left;'>การตรวจ</th><th>ผลตรวจ</th><th style='text-align:left;'>ค่าปกติ</th></tr></thead><tbody>"
    for _, row in df_urine.iterrows():
        is_abn = is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])
        css_class = "urine-abn" if is_abn else "urine-row"
        html_content += f"<tr class='{css_class}'><td style='text-align:left;'>{row['การตรวจ']}</td><td>{safe_value(row['ผลตรวจ'])}</td><td style='text-align:left;'>{row['ค่าปกติ']}</td></tr>"
    html_content += "</tbody></table></div>"
    st.markdown(html_content, unsafe_allow_html=True)
    summary = advice_urine(sex, person_data.get("Alb", "-"), person_data.get("sugar", "-"), person_data.get("RBC1", "-"), person_data.get("WBC1", "-"))
    if any(not is_empty(val) for _, val, _ in urine_data):
        if summary: st.markdown(f"<div style='background-color:rgba(255,255,0,0.2);color:var(--text-color);padding:1rem;border-radius:6px;margin-top:1rem;font-size:14px;'>{summary}</div>", unsafe_allow_html=True)
        else: st.markdown("<div style='background-color:rgba(57,255,20,0.2);color:var(--text-color);padding:1rem;border-radius:6px;margin-top:1rem;font-size:14px;'>ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ</div>", unsafe_allow_html=True)
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
def render_stool_html_table(exam, cs):
    html = "<div class='stool-container' style='margin-top:1rem;'><table class='stool-table' style='width:100%;border-collapse:collapse;table-layout:fixed;font-size:14px;'><colgroup><col style='width:50%;'><col style='width:50%;'></colgroup>"
    html += f"<tr><th style='text-align:left;width:50%;'>ผลตรวจอุจจาระทั่วไป</th><td style='text-align:left;'>{exam if exam != '-' else 'ไม่ได้เข้ารับการตรวจ'}</td></tr>"
    html += f"<tr><th style='text-align:left;width:50%;'>ผลตรวจอุจจาระเพาะเชื้อ</th><td style='text-align:left;'>{cs if cs != '-' else 'ไม่ได้เข้ารับการตรวจ'}</td></tr>"
    html += "</table></div>"
    return html
def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(k in val.lower() for k in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val
def get_ekg_col_name(year):
    return "EKG" if year == datetime.now().year + 543 else f"EKG{str(year)[-2:]}"
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
    output = [f"<b>{title}:</b> {' '.join(list(OrderedDict.fromkeys(msgs)))}" for title, msgs in groups.items() if msgs]
    if not output: return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"
    return "<div style='margin-bottom:0.75rem;'>" + "</div><div style='margin-bottom:0.75rem;'>".join(output) + "</div>"

# --- Data Loading ---
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
        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['HN'] = df_loaded['HN'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, int)) else str(x)).str.strip()
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip()
        df_loaded['Year'] = pd.to_numeric(df_loaded['Year'], errors='coerce').astype('Int64')
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None, np.nan], pd.NA, inplace=True)
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

# --- Main App ---
df = load_sqlite_data()
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# --- CSS Injection (FIXED for FONT and PRINT) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    
    /* 1. Force Sarabun on ALL elements */
    * {
        font-family: 'Sarabun', sans-serif !important;
    }
    
    /* 2. Create a specific exception for the sidebar collapse button icon */
    [data-testid="stSidebarNavCollapseButton"] * {
        font-family: 'sans-serif' !important; /* Revert to a generic font for the icon */
    }

    @media print {
        .no-print { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        section[data-testid="stAppViewContainer"] { left: 0 !important; width: 100% !important; padding: 1rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- Callback Function ---
def update_report_view():
    try:
        results_df = st.session_state["search_result"]
        year = st.session_state.year_select_sidebar
        date = st.session_state.exam_date_select_sidebar
        row_df = results_df[(results_df['Year'] == year) & (results_df['วันที่ตรวจ'] == date)]
        if not row_df.empty:
            st.session_state.person_row = row_df.iloc[0].to_dict()
    except (KeyError, IndexError):
        st.session_state.pop("person_row", None)

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
    st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input_val")

    if st.button("ค้นหา", use_container_width=True):
        search_term = st.session_state.get("search_input_val", "").strip()
        for key in list(st.session_state.keys()):
            if key != 'search_input_val': del st.session_state[key]
        if search_term:
            query_df = df[df["HN"].str.contains(search_term, na=False) | df["ชื่อ-สกุล"].str.contains(search_term, na=False)]
            if query_df.empty:
                st.error("❌ ไม่พบข้อมูล")
            else:
                st.session_state.search_result = query_df.reset_index(drop=True)
                latest_record = st.session_state.search_result.sort_values(by="Year", ascending=False).iloc[0]
                st.session_state.person_row = latest_record.to_dict()
                st.session_state.year_select_sidebar = latest_record["Year"]
                st.session_state.exam_date_select_sidebar = latest_record["วันที่ตรวจ"]
        else:
            st.info("กรุณากรอกข้อมูลเพื่อค้นหา")

    if "search_result" in st.session_state:
        results_df = st.session_state["search_result"]
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)

        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        year_index = available_years.index(st.session_state.year_select_sidebar) if st.session_state.get("year_select_sidebar") in available_years else 0
        st.selectbox("📅 เลือกปีที่ต้องการดูผลตรวจ", available_years, index=year_index, key="year_select_sidebar", format_func=lambda y: f"พ.ศ. {y}", on_change=update_report_view)

        current_year = st.session_state.get("year_select_sidebar", available_years[0])
        person_year_df = results_df[results_df["Year"] == current_year]
        exam_dates_options = sorted(person_year_df["วันที่ตรวจ"].dropna().unique(), key=lambda d: pd.to_datetime(d, dayfirst=True, errors='coerce'), reverse=True)
        
        if exam_dates_options:
            date_index = exam_dates_options.index(st.session_state.exam_date_select_sidebar) if st.session_state.get("exam_date_select_sidebar") in exam_dates_options else 0
            st.selectbox("🗓️ เลือกวันที่ตรวจ", exam_dates_options, index=date_index, key="exam_date_select_sidebar", on_change=update_report_view)
        
        st.markdown("---")
        # --- FIXED PRINT BUTTON ---
        print_button_html = """
        <style>
            .print-button {
                display: inline-flex; align-items: center; justify-content: center;
                font-weight: 400; padding: 0.25rem 0.75rem; border-radius: 0.5rem;
                min-height: 38.4px; margin: 0px; line-height: 1.6;
                color: inherit; width: 100%; user-select: none;
                background-color: var(--secondary-background-color);
                border: 1px solid rgba(49, 51, 63, 0.2);
                cursor: pointer;
            }
            .print-button:hover {
                border-color: var(--primary-color);
                color: var(--primary-color);
            }
            .print-button:active {
                background-color: var(--primary-color);
                color: white;
            }
        </style>
        <button class="print-button" onclick="window.print()">🖨️ พิมพ์รายงานสุขภาพ</button>
        """
        components.html(print_button_html, height=50)

# ==================== Display Health Report (Main Content) ====================
if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    year_display = person.get("Year", "-")
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse_raw = person.get("pulse", "-")
    weight_raw = person.get("น้ำหนัก", "-")
    height_raw = person.get("ส่วนสูง", "-")
    waist_raw = person.get("รอบเอว", "-")
    check_date = person.get("วันที่ตรวจ", "-")

    report_header_html = f"""<div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem;"><h1>รายงานผลการตรวจสุขภาพ</h1><h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2><p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p><p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p><p><b>วันที่ตรวจ:</b> {check_date or "-"}</p></div>"""
    st.markdown(report_header_html, unsafe_allow_html=True)
    
    try:
        weight_val = float(str(weight_raw).replace("กก.", "").strip())
        height_val = float(str(height_raw).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2) if height_val > 0 else None
    except: bmi_val = None
    try:
        sbp_int, dbp_int = int(float(sbp)), int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
        bp_desc = interpret_bp(sbp, dbp)
        bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val
    except: bp_full = "-"
    try: pulse = f"{int(float(pulse_raw))} ครั้ง/นาที"
    except: pulse = "-"
    weight_display = f"{weight_raw} กก." if not is_empty(weight_raw) else "-"
    height_display = f"{height_raw} ซม." if not is_empty(height_raw) else "-"
    waist_display = f"{waist_raw} ซม." if not is_empty(waist_raw) else "-"
    summary_advice = html.escape(combined_health_advice(bmi_val, sbp, dbp) or "")
    
    st.markdown(f"""<div><hr><div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-top: 24px; margin-bottom: 20px; text-align: center;"><div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div><div><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</div><div><b>เพศ:</b> {person.get('เพศ', '-')}</div><div><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</div><div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div></div><div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;"><div><b>น้ำหนัก:</b> {weight_display}</div><div><b>ส่วนสูง:</b> {height_display}</div><div><b>รอบเอว:</b> {waist_display}</div><div><b>ความดันโลหิต:</b> {bp_full}</div><div><b>ชีพจร:</b> {pulse}</div></div>{f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {summary_advice}</div>" if summary_advice else ""}</div>""", unsafe_allow_html=True)

    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    if sex == "หญิง": hb_low, hct_low = 12, 36
    else: hb_low, hct_low = 13, 39

    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [[(label, is_abn), (result, is_abn), (norm, is_abn)] for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]
    
    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106, False), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2, False), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120, False), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37, False), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41, False), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200, False), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150, False), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160, False), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20, False), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17, False), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [[(label, is_abn), (result, is_abn), (norm, is_abn)] for label, col, norm, low, high, higher in blood_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]

    _, col1, col2, _ = st.columns([0.5, 3, 3, 0.5])
    with col1: st.markdown(render_lab_table_html("ผลตรวจ CBC (Complete Blood Count)", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    advice_list = [kidney_advice_from_summary(kidney_summary_gfr_only(person.get("GFR", ""))), fbs_advice(person.get("FBS", "")), liver_advice(summarize_liver(person.get("ALP", ""), person.get("SGOT", ""), person.get("SGPT", ""))), uric_acid_advice(person.get("Uric Acid", "")), lipids_advice(summarize_lipids(person.get("CHOL", ""), person.get("TGL", ""), person.get("LDL", ""))), cbc_advice(person.get("Hb(%)", ""), person.get("HCT", ""), person.get("WBC (cumm)", ""), person.get("Plt (/mm)", ""), sex=sex)]
    _, main_col, _ = st.columns([0.5, 6, 0.5])
    with main_col:
        final_advice_html = merge_final_advice_grouped(advice_list)
        bg_color = "rgba(255, 255, 0, 0.2)" if "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html else "rgba(57, 255, 20, 0.2)"
        st.markdown(f"<div style='background-color:{bg_color}; padding:1rem 2.5rem; border-radius:10px; line-height:1.5; font-size:14px;'>{final_advice_html}</div>", unsafe_allow_html=True)
    
    _, col_ua_left, col_ua_right, _ = st.columns([0.5, 3, 3, 0.5])
    with col_ua_left:
        render_urine_section(person, sex, person.get("Year"))
        st.markdown(render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
        st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)
    with col_ua_right:
        st.markdown(render_section_header("ผลเอกซเรย์ (Chest X-ray)"), unsafe_allow_html=True)
        st.markdown(f"<div style='padding:1.25rem; border-radius:6px; margin-bottom:1.5rem; font-size:14px;'>{interpret_cxr(person.get(get_ekg_col_name(person.get('Year')).replace('EKG', 'CXR'), ''))}</div>", unsafe_allow_html=True)
        st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ (EKG)"), unsafe_allow_html=True)
        st.markdown(f"<div style='padding:1.25rem; border-radius:6px; margin-bottom:1.5rem; font-size:14px;'>{interpret_ekg(person.get(get_ekg_col_name(person.get('Year')), ''))}</div>", unsafe_allow_html=True)
        st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบเอ (Viral hepatitis A)"), unsafe_allow_html=True)
        st.markdown(f"<div style='padding:1rem; border-radius:6px; margin-bottom:1.5rem; font-size:14px;'>{safe_text(person.get('Hepatitis A'))}</div>", unsafe_allow_html=True)
        st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)"), unsafe_allow_html=True)
        hbsag, hbsab, hbcab = safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB"))
        st.markdown(f"<div style='margin-bottom:1rem;'><table style='width:100%;text-align:center;border-collapse:collapse;font-size:14px;'><thead><tr><th>HBsAg</th><th>HBsAb</th><th>HBcAb</th></tr></thead><tbody><tr><td>{hbsag}</td><td>{hbsab}</td><td>{hbcab}</td></tr></tbody></table></div>", unsafe_allow_html=True)
        advice = hepatitis_b_advice(hbsag, hbsab, hbcab)
        bg_hep = "rgba(57, 255, 20, 0.2)" if "มีภูมิคุ้มกัน" in advice else "rgba(255, 255, 0, 0.2)"
        st.markdown(f"<div style='padding:1rem 1.5rem; border-radius:6px; background-color:{bg_hep}; margin-bottom:1.5rem; font-size:14px;'>{advice}</div>", unsafe_allow_html=True)

    _, doctor_col, _ = st.columns([0.5, 6, 0.5])
    with doctor_col:
        doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
        if is_empty(doctor_suggestion): doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"
        st.markdown(f"""
            <div style='background-color:#1b5e20; color:white; padding:1.5rem 2rem; border-radius:8px; margin-top:2rem; margin-bottom:2rem; font-size:14px;'>
                <b>สรุปความเห็นของแพทย์:</b><br>{doctor_suggestion}
            </div>
            <div style='margin-top:7rem; text-align:right; padding-right:1rem;'>
                <div style='display:inline-block; text-align:center; width:340px;'>
                    <div style='border-bottom:1px dotted #ccc; margin-bottom:0.5rem; width:100%;'></div>
                    <div style='white-space:nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
                    <div style='white-space:nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
