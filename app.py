import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html
import numpy as np
from collections import OrderedDict

# --- Configuration Constants ---

# Mapping for advice based on summary text to reduce if/elif chains
KIDNEY_ADVICE_MAP = {
    "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย": (
        "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย "
        "ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน "
        "และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
    )
}

LIVER_ADVICE_MAP = {
    "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย": "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
}

LIPIDS_ADVICE_MAP = {
    "ไขมันในเลือดสูง": (
        "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ "
        "ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
    ),
    "ไขมันในเลือดสูงเล็กน้อย": (
        "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน "
        "และออกกำลังกายเพื่อควบคุมระดับไขมัน"
    )
}


# --- Utility Functions ---

def is_empty(val):
    """Checks if a value is considered empty (None, NaN, empty string, or placeholder)."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def safe_float(value):
    """Safely converts a value to a float, returning None if empty or invalid."""
    if is_empty(value):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def _clean_numeric_str(series):
    """Helper to clean string columns that should be integers."""
    return series.apply(
        lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip().replace('.', '', 1).isdigit() else ""
    ).str.strip()


@st.cache_data(ttl=600)
def load_sqlite_data():
    """Loads health data from a SQLite database, cleans it, and returns a DataFrame."""
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(response.content)
            db_path = tmp.name

        conn = sqlite3.connect(db_path)
        df = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()

        # --- Data Cleaning ---
        df.columns = df.columns.str.strip()
        
        for col in ['เลขบัตรประชาชน', 'ชื่อ-สกุล']:
            df[col] = df[col].astype(str).str.strip()
            
        df['HN'] = _clean_numeric_str(df['HN'])
        df['อายุ'] = _clean_numeric_str(df['อายุ'])
        
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype('Int64')

        df.replace(["-", "None", None, "nan", "null", ""], pd.NA, inplace=True)

        return df
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()


def flag(val, low=None, high=None, higher_is_better=False):
    """
    Formats a numeric value and flags it as abnormal if it falls outside the given range.
    Returns (formatted_string, is_abnormal_boolean).
    """
    val_float = safe_float(val)
    if val_float is None:
        return "-", False
    
    if val_float == 0 and (low is None or low > 0):
        return "-", False

    is_abnormal = False
    if higher_is_better:
        is_abnormal = (low is not None and val_float < low)
    else:
        is_abnormal = (low is not None and val_float < low) or \
                      (high is not None and val_float > high)

    return f"{val_float:.1f}", is_abnormal


def render_section_header(title, subtitle=None):
    """Renders a styled section header using HTML."""
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div style='
        background-color: #1b5e20; color: white; text-align: center;
        padding: 1rem 0.5rem; font-size: 20px; font-weight: bold;
        font-family: "Segoe UI", sans-serif; border-radius: 8px;
        margin-top: 2rem; margin-bottom: 1rem;
    '>
        {full_title}
    </div>
    """

# --- Health Interpretation Functions (Restored to match original output) ---

def interpret_bp(sbp, dbp):
    """Interprets blood pressure values and returns a descriptive string."""
    if sbp is None or dbp is None or sbp == 0 or dbp == 0:
        return "-"
    if sbp >= 160 or dbp >= 100: return "ความดันสูง"
    if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
    if sbp < 120 and dbp < 80: return "ความดันปกติ"
    return "ความดันค่อนข้างสูง"

def combined_health_advice(bmi, sbp, dbp):
    """Provides combined health advice based on BMI and BP (Original Logic)."""
    if is_empty(bmi) and is_empty(sbp) and is_empty(dbp): return ""
    
    bmi_text = ""
    bp_text = ""
    
    if bmi is not None:
        if bmi > 30: bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi >= 25: bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5: bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else: bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
            
    if sbp is not None and dbp is not None:
        if sbp >= 160 or dbp >= 100: bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
        elif sbp >= 140 or dbp >= 90: bp_text = "ความดันโลหิตอยู่ในระดับสูง"
        elif sbp >= 120 or dbp >= 80: bp_text = "ความดันโลหิตเริ่มสูง"
            
    if bmi is not None and "ปกติ" in bmi_text and not bp_text:
        return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
    if not bmi_text and bp_text:
        return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    if bmi_text and bp_text:
        return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    if bmi_text and not bp_text:
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    return ""

def kidney_summary_gfr_only(gfr_raw):
    """Summarizes kidney function based on GFR."""
    gfr = safe_float(gfr_raw)
    if gfr is None or gfr == 0: return ""
    return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย" if gfr < 60 else "ปกติ"

def fbs_advice(fbs_raw):
    """Provides advice for Fasting Blood Sugar (FBS)."""
    fbs_val = safe_float(fbs_raw)
    if fbs_val is None or fbs_val == 0: return ""
    if fbs_val >= 126: return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
    if 106 <= fbs_val < 126: return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
    if 100 <= fbs_val < 106: return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
    return ""

def summarize_liver(alp_raw, sgot_raw, sgpt_raw):
    """Summarizes liver function."""
    alp, sgot, sgpt = safe_float(alp_raw), safe_float(sgot_raw), safe_float(sgpt_raw)
    if any(v is None or v == 0 for v in [alp, sgot, sgpt]): return "-"
    if alp > 120 or sgot > 37 or sgpt > 41: return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
    return "ปกติ"

def uric_acid_advice(uric_raw):
    """Provides advice for Uric Acid."""
    value = safe_float(uric_raw)
    if value is not None and value > 7.2:
        return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
    return ""

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    """Summarizes lipid profile."""
    chol, tgl, ldl = safe_float(chol_raw), safe_float(tgl_raw), safe_float(ldl_raw)
    if all(v is None or v == 0 for v in [chol, tgl, ldl]): return ""
    
    if (chol is not None and chol >= 250) or \
       (tgl is not None and tgl >= 250) or \
       (ldl is not None and ldl >= 180):
        return "ไขมันในเลือดสูง"
    
    if (chol is not None and chol <= 200) and \
       (tgl is not None and tgl <= 150) and \
       (ldl is not None and ldl <= 160):
        return "ปกติ"
        
    return "ไขมันในเลือดสูงเล็กน้อย"

def cbc_advice(hb_raw, hct_raw, wbc_raw, plt_raw, sex="ชาย"):
    """Provides advice for Complete Blood Count (CBC)."""
    advice_parts = []
    hb, hct, wbc, plt = safe_float(hb_raw), safe_float(hct_raw), safe_float(wbc_raw), safe_float(plt_raw)

    hb_ref, hct_ref = (13, 39) if sex == "ชาย" else (12, 36)
    if hb is not None and hb < hb_ref: advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    if hct is not None and hct < hct_ref: advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    if wbc is not None:
        if wbc < 4000: advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc > 10000: advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    if plt is not None:
        if plt < 150000: advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt > 500000: advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")

    return " ".join(advice_parts)

# --- Urinalysis Interpretation ---

def parse_range_or_number(val_str):
    """Parses a string like '0-2' or '5' into a (low, high) tuple of floats."""
    if is_empty(val_str): return None, None
    val = str(val_str).replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val:
            low, high = map(float, val.split("-"))
            return low, high
        num = float(val)
        return num, num
    except (ValueError, TypeError):
        return None, None

def interpret_urine_text(value, positive_terms, slight_positive_terms, negative_term="negative"):
    """Generic interpreter for urine text results like Albumin and Sugar."""
    val = str(value or "").strip().lower()
    if is_empty(val) or val == negative_term: return "ไม่พบ", False
    if val in slight_positive_terms: return f"พบ{positive_terms[0]}ในปัสสาวะเล็กน้อย", True
    if any(term in val for term in positive_terms): return f"พบ{positive_terms[0]}ในปัสสาวะ", True
    return str(value or "-"), False

def interpret_urine_cells(value, normal_high, slight_high, name):
    """Generic interpreter for urine cell counts like RBC and WBC."""
    if is_empty(value): return "-", False
    _, high = parse_range_or_number(value)
    if high is None: return str(value), False
    if high <= normal_high: return "ปกติ", False
    if high <= slight_high: return f"พบ{name}ในปัสสาวะเล็กน้อย", True
    return f"พบ{name}ในปัสสาวะ", True

def advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw):
    """Provides advice based on urinalysis results (Original Logic)."""
    alb_t, alb_abn = interpret_urine_text(alb_raw, ["โปรตีน", "3+", "4+"], ["trace", "1+", "2+"])
    sugar_t, sugar_abn = interpret_urine_text(sugar_raw, ["น้ำตาล", "1+", "2+", "3+", "4+", "5+", "6+"], ["trace"])
    rbc_t, rbc_abn = interpret_urine_cells(rbc_raw, 2, 5, "เม็ดเลือดแดง")
    wbc_t, wbc_abn = interpret_urine_cells(wbc_raw, 5, 10, "เม็ดเลือดขาว")

    if not any([alb_abn, sugar_abn, rbc_abn, wbc_abn]): return ""

    advice_parts = []
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "เล็กน้อย" not in sugar_t:
        advice_parts.append("ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม")
    if "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t:
        advice_parts.append("อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ" if sex == "หญิง" else "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม")
    if "พบเม็ดเลือดขาว" in wbc_t and "เล็กน้อย" not in wbc_t:
        advice_parts.append("อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ")

    return " ".join(advice_parts) or "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"

# --- Data Processing and Display Logic ---

def format_person_data_for_display(person):
    """Extracts and formats key person data into a dictionary for display."""
    weight_val = safe_float(person.get("น้ำหนัก"))
    height_val = safe_float(person.get("ส่วนสูง"))
    sbp = safe_float(person.get("SBP"))
    dbp = safe_float(person.get("DBP"))

    try:
        bmi_val = weight_val / ((height_val / 100) ** 2) if weight_val and height_val else None
    except ZeroDivisionError:
        bmi_val = None

    bp_desc = interpret_bp(sbp, dbp)
    bp_full = f"{int(sbp)}/{int(dbp)} ม.ม.ปรอท - {bp_desc}" if sbp and dbp and bp_desc != "-" else (f"{int(sbp)}/{int(dbp)} ม.ม.ปรอท" if sbp and dbp else "-")


    return {
        "check_date": person.get("วันที่ตรวจ", "-"),
        "name": person.get('ชื่อ-สกุล', '-'),
        "age": person.get('อายุ', '-'),
        "sex": person.get('เพศ', '-'),
        "hn": person.get('HN', '-'),
        "department": person.get('หน่วยงาน', '-'),
        "weight": f"{weight_val:.1f} กก." if weight_val else "-",
        "height": f"{height_val:.1f} ซม." if height_val else "-",
        "waist": f"{safe_float(person.get('รอบเอว')):.1f} ซม." if not is_empty(person.get('รอบเอว')) else "-",
        "pulse": f"{int(p)} ครั้ง/นาที" if (p := safe_float(person.get('pulse'))) else "-",
        "bp_full": bp_full,
        "summary_advice": html.escape(combined_health_advice(bmi_val, sbp, dbp)),
    }

def process_lab_config(config, person_data, sex):
    """Processes a lab configuration list and returns rows for the HTML table."""
    rows = []
    for label, col_key, norm_range, low, high, *opt in config:
        higher_is_better = opt[0] if opt else False
        
        if "Hb" in label: low = 13 if sex == "ชาย" else 12
        if "Hct" in label: low = 39 if sex == "ชาย" else 36
        
        val = person_data.get(col_key)
        result_str, is_abnormal = flag(val, low, high, higher_is_better)
        rows.append([(label, is_abnormal), (result_str, is_abnormal), (norm_range, False)])
    return rows

def render_lab_table_html(headers, rows):
    """Generates HTML for a lab results table."""
    header_html = "".join([f"<th style='text-align: {'left' if i != 1 else 'center'};'>{h}</th>" for i, h in enumerate(headers)])
    
    rows_html = ""
    for row_data in rows:
        row_class = "lab-abn" if any(is_abn for _, is_abn in row_data) else "lab-row"
        rows_html += f"""
        <tr>
            <td class='{row_class}' style='text-align: left;'>{row_data[0][0]}</td>
            <td class='{row_class}'>{row_data[1][0]}</td>
            <td class='{row_class}' style='text-align: left;'>{row_data[2][0]}</td>
        </tr>
        """
    return f"<div class='lab-container'><table class='lab-table'><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table></div>"

def merge_final_advice_grouped(messages):
    """Groups and formats the final health advice list into themed HTML (Original Logic)."""
    groups = OrderedDict([
        ("น้ำตาลในเลือด", []), ("การทำงานของไต", []), ("การทำงานของตับ", []),
        ("กรดยูริค", []), ("ไขมันในเลือด", []), ("เม็ดเลือดและอื่นๆ", [])
    ])

    for msg in messages:
        if not msg or msg.strip() in ["-", "ไม่พบ", "ปกติ"]: continue
        if "น้ำตาล" in msg: groups["น้ำตาลในเลือด"].append(msg)
        elif "ไต" in msg: groups["การทำงานของไต"].append(msg)
        elif "ตับ" in msg: groups["การทำงานของตับ"].append(msg)
        elif "พิวรีน" in msg or "ยูริค" in msg: groups["กรดยูริค"].append(msg)
        elif "ไขมัน" in msg: groups["ไขมันในเลือด"].append(msg)
        else: groups["เม็ดเลือดและอื่นๆ"].append(msg)

    output = [f"<b>{title}:</b> {' '.join(list(OrderedDict.fromkeys(msgs)))}" for title, msgs in groups.items() if msgs]
    
    if not output: return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"
    return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(output) + "</div>"

# --- Streamlit UI Functions ---

def display_person_header(data):
    """Renders the main patient information header."""
    st.markdown(f"""
    <div style="font-size: 20px; line-height: 1.8; color: inherit; padding: 24px 8px;">
        <div style="text-align: center; font-size: 29px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
        <div style="text-align: center;">วันที่ตรวจ: {data['check_date']}</div>
        <div style="text-align: center; margin-top: 10px;">
            โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290<br>
            ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167
        </div>
        <hr style="margin: 24px 0;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {data['name']}</div>
            <div><b>อายุ:</b> {data['age']} ปี</div>
            <div><b>เพศ:</b> {data['sex']}</div>
            <div><b>HN:</b> {data['hn']}</div>
            <div><b>หน่วยงาน:</b> {data['department']}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {data['weight']}</div>
            <div><b>ส่วนสูง:</b> {data['height']}</div>
            <div><b>รอบเอว:</b> {data['waist']}</div>
            <div><b>ความดันโลหิต:</b> {data['bp_full']}</div>
            <div><b>ชีพจร:</b> {data['pulse']}</div>
        </div>
        {f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {data['summary_advice']}</div>" if data['summary_advice'] else ""}
    </div>
    """, unsafe_allow_html=True)

def display_lab_results(person, sex):
    """Renders the CBC and Blood Chemistry lab result tables."""
    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", f"ชาย > 13, หญิง > 12 g/dl", 13, None, True),
        ("ฮีมาโทคริต (Hct)", "HCT", f"ชาย > 39, หญิง > 36 %", 39, None, True),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("กรดยูริค (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
        ("เอนไซม์ตับ (ALP)", "ALP", "30 - 120 U/L", 30, 120),
        ("เอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("เอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
    ]

    cbc_rows = process_lab_config(cbc_config, person, sex)
    blood_rows = process_lab_config(blood_config, person, sex)
    
    _, col1, col2, _ = st.columns([1, 3, 3, 1])
    with col1:
        st.markdown(render_section_header("ผลตรวจ CBC", "Complete Blood Count"), unsafe_allow_html=True)
        st.markdown(render_lab_table_html(["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    with col2:
        st.markdown(render_section_header("ผลตรวจเคมีเลือด", "Blood Chemistry"), unsafe_allow_html=True)
        st.markdown(render_lab_table_html(["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

def display_final_advice(person, sex):
    """Gathers all advice, formats it, and displays it in a styled box."""
    advice_list = [
        KIDNEY_ADVICE_MAP.get(kidney_summary_gfr_only(person.get("GFR"))),
        fbs_advice(person.get("FBS")),
        LIVER_ADVICE_MAP.get(summarize_liver(person.get("ALP"), person.get("SGOT"), person.get("SGPT"))),
        uric_acid_advice(person.get("Uric Acid")),
        LIPIDS_ADVICE_MAP.get(summarize_lipids(person.get("CHOL"), person.get("TGL"), person.get("LDL"))),
        cbc_advice(person.get("Hb(%)"), person.get("HCT"), person.get("WBC (cumm)"), person.get("Plt (/mm)"), sex),
    ]
    
    final_advice_html = merge_final_advice_grouped(advice_list)
    has_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
    bg_color = "rgba(255, 215, 0, 0.15)" if has_advice else "rgba(200, 255, 200, 0.15)"

    _, main_col, _ = st.columns([1, 6, 1])
    with main_col:
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 1rem 2.5rem; border-radius: 10px;
                    font-size: 16px; line-height: 1.5; color: var(--text-color);">
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 0.5rem;">📋 คำแนะนำจากผลตรวจสุขภาพ</div>
            {final_advice_html}
        </div>
        """, unsafe_allow_html=True)

def display_urinalysis_results(person, sex):
    """Renders the Urinalysis results table and its specific advice."""
    urine_config = [
        ("สี (Colour)", "Color", "Yellow, Pale Yellow", lambda v: (str(v or "-"), str(v or "").lower() not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"])),
        ("น้ำตาล (Sugar)", "sugar", "Negative", lambda v: interpret_urine_text(v, ["น้ำตาล"], ["trace", "1+", "2+", "3+", "4+", "5+", "6+"])),
        ("โปรตีน (Albumin)", "Alb", "Negative, trace", lambda v: interpret_urine_text(v, ["โปรตีน"], ["trace", "1+", "2+", "3+", "4+"])),
        ("กรด-ด่าง (pH)", "pH", "5.0-8.0", lambda v: (str(v or "-"), not (5.0 <= (f_v:=safe_float(v)) <= 8.0) if f_v is not None else False)),
        ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003-1.030", lambda v: (str(v or "-"), not (1.003 <= (f_v:=safe_float(v)) <= 1.030) if f_v is not None else False)),
        ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2 cell/HPF", lambda v: interpret_urine_cells(v, 2, 5, "เม็ดเลือดแดง")),
        ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5 cell/HPF", lambda v: interpret_urine_cells(v, 5, 10, "เม็ดเลือดขาว")),
        ("เซลล์เยื่อบุผิว (Squam.epit.)", "SQ-epi", "0 - 10 cell/HPF", lambda v: (str(v or "-"), (h_val := parse_range_or_number(str(v or ""))[1]) is not None and h_val > 10)),
        ("อื่นๆ", "ORTER", "-", lambda v: (str(v or "-"), not is_empty(v) and str(v).strip().lower() not in ["none", "-"])),
    ]
    
    urine_rows = []
    for label, key, norm, interpreter_func in urine_config:
        val = person.get(key)
        result_str, is_abnormal = interpreter_func(val)
        urine_rows.append([(label, is_abnormal), (result_str, is_abnormal), (norm, False)])

    _, col_ua_left, col_ua_right, _ = st.columns([1, 3, 3, 1])
    
    with col_ua_left:
        st.markdown(render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis"), unsafe_allow_html=True)
        st.markdown(render_lab_table_html(["การตรวจ", "ผล", "ค่าปกติ"], urine_rows), unsafe_allow_html=True)
    
    with col_ua_right:
        st.markdown(render_section_header("คำแนะนำผลตรวจปัสสาวะ"), unsafe_allow_html=True)
        ua_advice = advice_urine(sex, person.get("Alb"), person.get("sugar"), person.get("RBC1"), person.get("WBC1"))
        if ua_advice:
            st.info(ua_advice)
        else:
            st.success("ผลการตรวจปัสสาวะอยู่ในเกณฑ์ปกติ")

def display_additional_info(person):
    """Renders additional results (CXR, EKG, Hepatitis) and the doctor's comment."""
    
    # Use a single container for better alignment and spacing
    with st.container():
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        _, main_col, _ = st.columns([1, 6, 1])
        
        with main_col:
            # --- CXR and EKG in two columns ---
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(render_section_header("ผลตรวจเอ็กซเรย์ปอด", "CXR"), unsafe_allow_html=True)
                # Assuming 'CXR' is the column name
                cxr_result = person.get("CXR", "-") 
                st.markdown(f"<div style='padding: 1rem; background-color: rgba(0,0,0,0.03); border-radius: 8px; text-align: center; min-height: 80px; display: flex; align-items: center; justify-content: center;'>{html.escape(str(cxr_result))}</div>", unsafe_allow_html=True)

            with col2:
                st.markdown(render_section_header("ผลตรวจคลื่นไฟฟ้าหัวใจ", "EKG"), unsafe_allow_html=True)
                # Assuming 'EKG' is the column name
                ekg_result = person.get("EKG", "-")
                st.markdown(f"<div style='padding: 1rem; background-color: rgba(0,0,0,0.03); border-radius: 8px; text-align: center; min-height: 80px; display: flex; align-items: center; justify-content: center;'>{html.escape(str(ekg_result))}</div>", unsafe_allow_html=True)

            # --- Hepatitis Panel ---
            st.markdown(render_section_header("ผลตรวจไวรัสตับอักเสบ", "Hepatitis Panel"), unsafe_allow_html=True)
            hep_col1, hep_col2 = st.columns(2)
            with hep_col1:
                st.markdown("<p style='text-align: center; font-weight: bold;'>HBsAg (ไวรัสตับอักเสบ บี)</p>", unsafe_allow_html=True)
                # Assuming 'HBsAg' is the column name
                hbsag_result = person.get("HBsAg", "-")
                st.markdown(f"<p style='text-align: center;'>{html.escape(str(hbsag_result))}</p>", unsafe_allow_html=True)
            with hep_col2:
                st.markdown("<p style='text-align: center; font-weight: bold;'>Anti-HAV (ไวรัสตับอักเสบ เอ)</p>", unsafe_allow_html=True)
                # Assuming 'Anti-HAV' is the column name
                hav_result = person.get("Anti-HAV", "-")
                st.markdown(f"<p style='text-align: center;'>{html.escape(str(hav_result))}</p>", unsafe_allow_html=True)

            # --- Doctor's Comment ---
            # Assuming 'แพทย์ผู้ตรวจ' is the column name for the comment
            comment = person.get("แพทย์ผู้ตรวจ", "")
            if not is_empty(comment):
                st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="
                    background-color: rgba(240, 248, 255, 0.7); 
                    padding: 1.5rem 2rem; 
                    border-radius: 10px;
                    border-left: 5px solid #4682B4;
                ">
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 0.75rem; color: #2E86C1;">
                        🩺 ความคิดเห็นและคำแนะนำจากแพทย์
                    </div>
                    <p style="color: var(--text-color); margin: 0; line-height: 1.7;">{html.escape(str(comment))}</p>
                </div>
                """, unsafe_allow_html=True)


# --- Main Streamlit Application ---

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

    st.markdown("""
    <style>
        body { overflow: auto !important; }
        ::-webkit-scrollbar { width: 0px; background: transparent; }
        .lab-table {
            width: 100%; border-collapse: collapse; font-size: 16px;
            font-family: "Segoe UI", sans-serif; color: var(--text-color);
        }
        .lab-table thead th {
            background-color: var(--secondary-background-color); padding: 4px;
            font-weight: bold; border: 1px solid transparent; text-align: center;
        }
        .lab-table td {
            padding: 4px; border: 1px solid transparent; text-align: center;
            overflow-wrap: break-word;
        }
        .lab-abn { background-color: rgba(255, 64, 64, 0.25); }
        .lab-row { background-color: rgba(255,255,255,0.02); }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center; color:gray;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

    df = load_sqlite_data()

    with st.form("search_form"):
        col1, col2, col3 = st.columns(3)
        id_card = col1.text_input("เลขบัตรประชาชน")
        hn = col2.text_input("HN")
        full_name = col3.text_input("ชื่อ-สกุล")
        submitted = st.form_submit_button("ค้นหา")

    if submitted:
        query_parts = []
        if id_card.strip(): query_parts.append(f"`เลขบัตรประชาชน` == '{id_card.strip()}'")
        if hn.strip(): query_parts.append(f"HN == '{hn.strip()}'")
        if full_name.strip(): query_parts.append(f"`ชื่อ-สกุล` == '{full_name.strip()}'")
        
        for key in ["search_result", "person_row"]: st.session_state.pop(key, None)

        if not query_parts:
            st.warning("⚠️ กรุณากรอกข้อมูลเพื่อค้นหาอย่างน้อย 1 อย่าง")
        else:
            search_query = " & ".join(query_parts)
            results = df.query(search_query)
            if results.empty:
                st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
            else:
                st.session_state["search_result"] = results

    if "search_result" in st.session_state:
        results_df = st.session_state["search_result"]
        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        
        if not available_years:
            st.warning("ไม่พบข้อมูลปีที่ตรวจสำหรับบุคคลนี้")
            return

        selected_year = st.selectbox(
            "📅 เลือกปีที่ต้องการดูผลตรวจ",
            options=available_years,
            format_func=lambda y: f"พ.ศ. {y}"
        )

        person_year_df = results_df[results_df["Year"] == selected_year].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", ascending=False)

        if len(person_year_df) > 1:
            st.markdown("---")
            st.markdown("**เลือกวันที่ตรวจจากหลายรายการในปีนี้:**")
            dates = person_year_df["วันที่ตรวจ"].unique()
            cols = st.columns(min(len(dates), 5))
            for i, date in enumerate(dates):
                with cols[i % len(cols)]:
                    if st.button(str(date), key=f"checkup_{i}"):
                        st.session_state["person_row"] = person_year_df[person_year_df["วันที่ตรวจ"] == date].iloc[0].to_dict()
                        st.rerun()
        elif len(person_year_df) == 1:
            st.session_state["person_row"] = person_year_df.iloc[0].to_dict()

    if "person_row" in st.session_state:
        person = st.session_state["person_row"]
        sex = str(person.get("เพศ", "")).strip()
        if sex not in ["ชาย", "หญิง"]:
            st.warning("⚠️ ไม่พบข้อมูลเพศ, ใช้ค่าอ้างอิงสำหรับ 'หญิง' เป็นค่าเริ่มต้น")
            sex = "หญิง"

        formatted_data = format_person_data_for_display(person)
        
        display_person_header(formatted_data)
        display_final_advice(person, sex)
        display_lab_results(person, sex)
        display_urinalysis_results(person, sex)
        display_additional_info(person)

if __name__ == "__main__":
    main()
