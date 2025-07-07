import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html
import numpy as np
from collections import OrderedDict # ตรวจสอบให้แน่ใจว่า import นี้มีอยู่แล้ว

# --- Helper Functions ---
def is_empty(val):
    """Checks if a value is considered empty."""
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

@st.cache_data(ttl=600)
def load_sqlite_data():
    """Loads health data from a SQLite database hosted on Google Drive."""
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr" # Verify this Google Drive ID is correct and accessible
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()

        # Save to a temporary file for sqlite3 to read
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.write(response.content)
        tmp.flush()
        tmp.close()

        conn = sqlite3.connect(tmp.name)
        df = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()

        # Strip spaces and convert important data types
        df.columns = df.columns.str.strip()
        df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
        # Convert HN to integer string, handling NaN by making it empty
        df['HN'] = df['HN'].apply(lambda x: str(int(float(x))) if pd.notna(x) else "").str.strip()
        df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()
        df['Year'] = df['Year'].astype(int)

        # Replace common missing value indicators with Pandas's NA
        df.replace(["-", "None", None, "nan"], pd.NA, inplace=True) # Added "nan" to replacement

        return df
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

def get_numeric_value(data_dict, key, default=None):
    """Safely retrieves and converts a value from a dictionary to float."""
    val = data_dict.get(key)
    if is_empty(val):
        return default
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default

def flag(val, low=None, high=None, higher_is_better=False):
    """
    Flags a numerical value as abnormal based on given thresholds.
    Returns formatted value and a boolean indicating abnormality.
    """
    try:
        val_float = float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return "-", False

    is_abnormal = False
    if higher_is_better:
        if low is not None and val_float < low:
            is_abnormal = True
    else:
        if low is not None and val_float < low:
            is_abnormal = True
        if high is not None and val_float > high:
            is_abnormal = True

    return f"{val_float:.1f}", is_abnormal

def safe_value(val):
    """Returns a cleaned string representation of a value, or '-' if empty."""
    val = str(val or "").strip()
    if val.lower() in ["", "nan", "none", "-", "null"]:
        return "-"
    return val

# --- Health Interpretation Functions ---
def kidney_summary_gfr_only(gfr_raw):
    """Summarizes kidney function based on GFR."""
    gfr = get_numeric_value(gfr_raw, None)
    if gfr is None or gfr == 0:
        return ""
    elif gfr < 60:
        return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย"
    else:
        return "ปกติ"

def kidney_advice_from_summary(summary_text):
    """Provides advice based on kidney summary."""
    if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
        return (
            "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย "
            "ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน "
            "และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
        )
    return ""

def fbs_advice(fbs_raw):
    """Provides advice based on Fasting Blood Sugar (FBS)."""
    value = get_numeric_value(fbs_raw, None)
    if value is None or value == 0:
        return ""
    elif 100 <= value < 106:
        return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
    elif 106 <= value < 126:
        return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
    elif value >= 126:
        return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
    return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    """Summarizes liver function based on ALP, SGOT, SGPT."""
    alp = get_numeric_value(alp_val, None)
    sgot = get_numeric_value(sgot_val, None)
    sgpt = get_numeric_value(sgpt_val, None)

    if alp is None or sgot is None or sgpt is None or alp == 0 or sgot == 0 or sgpt == 0:
        return "-"
    if alp > 120 or sgot > 37 or sgpt > 41: # Adjusted SGOT/SGPT thresholds to match table
        return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
    return "ปกติ"

def liver_advice(summary_text):
    """Provides advice based on liver summary."""
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
        return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    elif summary_text == "ปกติ":
        return ""
    return "-"

def uric_acid_advice(value_raw):
    """Provides advice based on Uric Acid levels."""
    value = get_numeric_value(value_raw, None)
    if value is None:
        return ""
    if value > 7.2:
        return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
    return ""

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    """Summarizes lipid profile based on Cholesterol, Triglycerides, and LDL."""
    chol = get_numeric_value(chol_raw, None)
    tgl = get_numeric_value(tgl_raw, None)
    ldl = get_numeric_value(ldl_raw, None)

    if chol is None or tgl is None or ldl is None:
        return "" # Can't summarize if values are missing

    if (chol == 0 and tgl == 0 and ldl == 0): # All zeroes imply no test or error
        return ""
    
    if chol >= 250 or tgl >= 250 or ldl >= 180: # More severe high levels
        return "ไขมันในเลือดสูง"
    elif (chol > 200 and chol < 250) or (tgl > 150 and tgl < 250) or (ldl > 160 and ldl < 180): # Slightly elevated
        return "ไขมันในเลือดสูงเล็กน้อย"
    elif chol <= 200 and tgl <= 150 and ldl <= 160:
        return "ปกติ"
    else:
        return "" # For cases that don't fit above but are not "normal" yet.

def lipids_advice(summary_text):
    """Provides advice based on lipid summary."""
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
    """Provides advice based on Complete Blood Count (CBC) results."""
    advice_parts = []
    
    hb_val = get_numeric_value(hb, None)
    hct_val = get_numeric_value(hct, None)
    wbc_val = get_numeric_value(wbc, None)
    plt_val = get_numeric_value(plt, None)

    hb_ref = 13 if sex == "ชาย" else 12
    hct_ref = 39 if sex == "ชาย" else 36

    if hb_val is not None and hb_val < hb_ref and hb_val != 0:
        advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")

    if hct_val is not None and hct_val < hct_ref and hct_val != 0:
        advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")

    if wbc_val is not None:
        if wbc_val < 4000 and wbc_val != 0:
            advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000:
            advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")

    if plt_val is not None:
        if plt_val < 150000 and plt_val != 0:
            advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000:
            advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")

    return " ".join(advice_parts)

def interpret_bp(sbp, dbp):
    """Interprets blood pressure values."""
    sbp_val = get_numeric_value(sbp, None)
    dbp_val = get_numeric_value(dbp, None)

    if sbp_val is None or dbp_val is None or sbp_val == 0 or dbp_val == 0:
        return "-"
    if sbp_val >= 160 or dbp_val >= 100:
        return "ความดันสูงมาก"
    elif sbp_val >= 140 or dbp_val >= 90:
        return "ความดันสูง"
    elif sbp_val >= 120 or dbp_val >= 80:
        return "ความดันค่อนข้างสูง"
    else:
        return "ความดันปกติ"

def combined_health_advice(bmi_val, sbp_raw, dbp_raw):
    """Provides combined advice for BMI and Blood Pressure."""
    bp_text = ""
    sbp = get_numeric_value(sbp_raw, None)
    dbp = get_numeric_value(dbp_raw, None)
    
    if sbp is not None and dbp is not None:
        bp_interpretation = interpret_bp(sbp, dbp)
        if bp_interpretation in ["ความดันสูงมาก", "ความดันสูง", "ความดันค่อนข้างสูง"]:
            bp_text = f"ความดันโลหิตอยู่ในระดับ{bp_interpretation.replace('ความดัน', '').strip()}"

    bmi_text = ""
    if bmi_val is not None:
        if bmi_val > 30:
            bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi_val >= 25:
            bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi_val < 18.5:
            bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else:
            bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
    
    if bmi_text and bp_text:
        return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    elif bmi_text:
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    elif bp_text:
        return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    
    if bmi_val is not None and "ปกติ" in bmi_text and not bp_text:
        return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
    
    return ""

def merge_final_advice_grouped(messages):
    """Groups and formats general health advice messages."""
    groups = {
        "น้ำตาล": [], "ไต": [], "ตับ": [], "กรดยูริค": [], "ไขมัน": [], "เม็ดเลือด/เกล็ดเลือด": [], "อื่นๆ": []
    }

    for msg in messages:
        if not msg or msg.strip() in ["-", ""]:
            continue
        if "น้ำตาล" in msg:
            groups["น้ำตาล"].append(msg)
        elif "ไต" in msg:
            groups["ไต"].append(msg)
        elif "ตับ" in msg:
            groups["ตับ"].append(msg)
        elif "พิวรีน" in msg or "ยูริค" in msg:
            groups["กรดยูริค"].append(msg)
        elif "ไขมัน" in msg:
            groups["ไขมัน"].append(msg)
        elif "ฮีโมโกลบิน" in msg or "ฮีมาโตคริต" in msg or "เม็ดเลือดขาว" in msg or "เกล็ดเลือด" in msg:
            groups["เม็ดเลือด/เกล็ดเลือด"].append(msg)
        else:
            groups["อื่นๆ"].append(msg)
            
    output = []
    for title, msgs in groups.items():
        if msgs:
            # Use OrderedDict to preserve order and remove duplicates
            unique_msgs = list(OrderedDict.fromkeys(msgs))
            output.append(f"<b>{title}:</b> {' '.join(unique_msgs)}")
    
    if not output:
        return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

    return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(output) + "</div>"

# --- Urinalysis Interpretation Functions ---
def parse_range_or_number(val_str):
    """Parses string like '0-2' or '5' into (low, high) float values."""
    val_str = str(val_str or "").strip().lower().replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").replace("hpf", "").strip()
    if not val_str:
        return None, None
    try:
        if "-" in val_str:
            low, high = map(float, val_str.split("-"))
            return low, high
        else:
            num = float(val_str)
            return num, num
    except ValueError:
        return None, None

def interpret_alb(value):
    """Interprets Albumin (Protein) in urine."""
    val = str(value).strip().lower()
    if val == "negative":
        return "ไม่พบ"
    elif val in ["trace", "1+", "2+", "+", "++"]:
        return "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif val in ["3+", "4+", "+++", "++++"]:
        return "พบโปรตีนในปัสสาวะ"
    return "-"

def interpret_sugar(value):
    """Interprets Sugar in urine."""
    val = str(value).strip().lower()
    if val == "negative":
        return "ไม่พบ"
    elif val == "trace":
        return "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif val in ["1+", "2+", "3+", "4+", "5+", "6+", "+", "++", "+++", "++++", "+++++"]:
        return "พบน้ำตาลในปัสสาวะ"
    return "-"

def interpret_rbc(value):
    """Interprets Red Blood Cells (RBC) in urine."""
    val_str = str(value or "").strip().lower()
    if is_empty(val_str) or val_str == "ปกติ": # added "ปกติ" for consistency
        return "ปกติ"
    low, high = parse_range_or_number(val_str)
    if high is None:
        return val_str # Return original if parsing fails
    if high <= 2:
        return "ปกติ"
    elif high <= 5: # Some labs might consider 3-5 trace/mild
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    """Interprets White Blood Cells (WBC) in urine."""
    val_str = str(value or "").strip().lower()
    if is_empty(val_str) or val_str == "ปกติ": # added "ปกติ" for consistency
        return "ปกติ"
    low, high = parse_range_or_number(val_str)
    if high is None:
        return val_str # Return original if parsing fails
    if high <= 5:
        return "ปกติ"
    elif high <= 10:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else:
        return "พบเม็ดเลือดขาวในปัสสาวะ"

def urine_analysis_advice(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw):
    """Provides consolidated advice for urinalysis results."""
    alb_t = interpret_alb(alb_raw)
    sugar_t = interpret_sugar(sugar_raw)
    rbc_t = interpret_rbc(rbc_raw)
    wbc_t = interpret_wbc(wbc_raw)

    advice_parts = []

    # Check for "significant" abnormalities first
    if "พบโปรตีนในปัสสาวะ" in alb_t and "เล็กน้อย" not in alb_t:
        advice_parts.append("พบโปรตีนในปัสสาวะ ควรปรึกษาแพทย์เพื่อตรวจเพิ่มเติม")
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "ไม่พบ" not in sugar_t and "เล็กน้อย" not in sugar_t:
        advice_parts.append("พบน้ำตาลในปัสสาวะ ควรลดการบริโภคน้ำตาลและตรวจระดับน้ำตาลในเลือดเพิ่มเติม")
    
    rbc_abnormal = ("พบเม็ดเลือดแดงในปัสสาวะ" in rbc_t and "ปกติ" not in rbc_t and "เล็กน้อย" not in rbc_t)
    wbc_abnormal = ("พบเม็ดเลือดขาวในปัสสาวะ" in wbc_t and "ปกติ" not in wbc_t and "เล็กน้อย" not in wbc_t)

    if rbc_abnormal:
        if sex == "หญิง" and not wbc_abnormal: # Check if female and WBC is normal
            advice_parts.append("อาจมีเม็ดเลือดแดงปนเปื้อนในปัสสาวะ (อาจเกิดจากประจำเดือน), แนะนำให้ตรวจซ้ำ")
        else:
            advice_parts.append("พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม")
    
    if wbc_abnormal:
        advice_parts.append("อาจมีการติดเชื้อหรืออักเสบในระบบทางเดินปัสสาวะ ควรปรึกษาแพทย์")
        
    # Less severe findings or combined advice
    if "พบโปรตีนในปัสสาวะเล็กน้อย" in alb_t:
        advice_parts.append("พบโปรตีนในปัสสาวะเล็กน้อย ควรติดตามผล")
    if "พบน้ำตาลในปัสสาวะเล็กน้อย" in sugar_t:
        advice_parts.append("พบน้ำตาลในปัสสาวะเล็กน้อย ควรระมัดระวังการบริโภคอาหารหวาน")
    if "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย" in rbc_t and not rbc_abnormal:
        advice_parts.append("พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย ควรติดตามผล")
    if "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย" in wbc_t and not wbc_abnormal:
        advice_parts.append("พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย ควรติดตามผล")

    # If no specific advice, return a generic message
    if not advice_parts:
        return "ไม่พบความผิดปกติที่สำคัญจากผลตรวจปัสสาวะ"
    
    # Return unique advice parts joined
    return " ".join(list(OrderedDict.fromkeys(advice_parts)))

# --- Hepatitis B Interpretation Functions ---
def interpret_hbsag(val):
    """Interprets HBsAg result."""
    val_str = str(val or "").strip().lower()
    if val_str == "negative":
        return "ไม่พบเชื้อไวรัสตับอักเสบบี"
    elif val_str == "positive":
        return "พบเชื้อไวรัสตับอักเสบบี"
    return "-"

def interpret_antihbs(val):
    """Interprets Anti-HBs result."""
    val_str = str(val or "").strip().lower()
    if val_str == "negative":
        return "ไม่มีภูมิคุ้มกันไวรัสตับอักเสบบี"
    elif val_str == "positive":
        return "มีภูมิคุ้มกันไวรัสตับอักเสบบี"
    return "-"

def hepatitis_advice(hbsag_raw, antihbs_raw):
    """Provides advice based on Hepatitis B screening results."""
    hbsag_t = interpret_hbsag(hbsag_raw)
    antihbs_t = interpret_antihbs(antihbs_raw)

    advice_parts = []
    if "พบเชื้อไวรัสตับอักเสบบี" in hbsag_t:
        advice_parts.append("พบเชื้อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อตรวจเพิ่มเติมและรับการรักษา")
    elif "ไม่มีภูมิคุ้มกันไวรัสตับอักเสบบี" in antihbs_t and "ไม่พบเชื้อ" in hbsag_t:
        advice_parts.append("ไม่มีภูมิคุ้มกันไวรัสตับอักเสบบี ควรพิจารณาฉีดวัคซีนป้องกัน")
    elif "มีภูมิคุ้มกันไวรัสตับอักเสบบี" in antihbs_t and "ไม่พบเชื้อ" in hbsag_t:
        return "มีภูมิคุ้มกันไวรัสตับอักเสบบี ไม่จำเป็นต้องฉีดวัคซีน"
    
    if not advice_parts:
        return "ไม่พบความผิดปกติที่สำคัญจากผลตรวจไวรัสตับอักเสบ"
    return " ".join(advice_parts)

# --- Reusable Rendering Functions ---
def render_section_header(title, subtitle=None):
    """Renders a styled section header."""
    if subtitle:
        full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>"
    else:
        full_title = title

    return f"""
    <div style='
        background-color: #1b5e20;
        color: white;
        text-align: center;
        padding: 1rem 0.5rem;
        font-size: 20px;
        font-weight: bold;
        font-family: "Segoe UI", sans-serif;
        border-radius: 8px;
        margin-top: 2rem;
        margin-bottom: 1rem;
    '>
        {full_title}
    </div>
    """

def render_advice_box(title, advice_content_html, has_advice=True):
    """
    Renders a styled advice box with conditional background color.
    Green background for 'normal' status, Yellow for 'advice needed'.
    """
    background_color = (
        "rgba(255, 215, 0, 0.15)" if has_advice else "rgba(200, 255, 200, 0.15)"
    )
    text_color = "var(--text-color)" # Use Streamlit's theme text color

    # Escape title to prevent HTML injection if it's potentially user-controlled
    escaped_title = html.escape(title)

    return f"""
    <div style="
        background-color: {background_color};
        padding: 1rem 2.5rem;
        border-radius: 10px;
        font-size: 16px;
        line-height: 1.5;
        color: {text_color};
        margin-top: 2rem;
        margin-bottom: 2rem;
    ">
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 0.5rem;">
            📋 {escaped_title}
        </div>
        {advice_content_html}
    </div>
    """

def render_lab_section(title, subtitle, headers, rows):
    """Renders a styled lab results table."""
    style = """
    <style>
        .lab-container {
            background-color: var(--background-color);
            margin-top: 1rem;
        }
        .lab-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 16px;
            font-family: "Segoe UI", sans-serif;
            color: var(--text-color);
        }
        .lab-table thead th {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 2px 4px;
            text-align: center;
            font-weight: bold;
            border: 1px solid transparent;
        }
        .lab-table td {
            padding: 2px 1px;
            border: 1px solid transparent;
            text-align: center;
        }
        .lab-abn {
            background-color: rgba(255, 64, 64, 0.25); /* Translucent red */
        }
        .lab-row {
            background-color: rgba(255,255,255,0.02);
        }
    </style>
    """
    html_content = f"""
    {render_section_header(title, subtitle)}
    <div class='lab-container'><table class='lab-table'>
    <thead><tr>
    """
    for i, h in enumerate(headers):
        align = "left" if i in [0, 2] else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = "lab-abn" if is_abn else "lab-row"
        
        html_content += f"<tr>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td class='{row_class}'>{row[1][0]}</td>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table></div>"
    return style + html_content

# --- Main Streamlit App Logic ---
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# Apply custom CSS to hide scrollbars as requested
st.markdown("""
    <style>
    /* Disable scrollbar for all markdown containers */
    div.stMarkdown {
        overflow: visible !important;
    }

    /* Disable scrollbar on main Streamlit content area */
    section.main > div {
        overflow-y: visible !important;
    }

    /* Prevent vertical blocks from wrapping scroll containers */
    [data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    /* WebKit (Chrome/Safari) scrollbar hide */
    ::-webkit-scrollbar {
        width: 0px;
        background: transparent;
    }

    /* Hide scrollbars for any specific markdown containers that might overflow */
    div[style*="overflow: auto"], div[style*="overflow-x: auto"], div[style*="overflow-y: auto"] {
        overflow: visible !important;
    }

    .urine-table, .lab-table {
        width: 100%;
        table-layout: fixed;
    }
    .urine-table td, .lab-table td {
        overflow-wrap: break-word; /* Ensures long text wraps */
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

# Load data with a spinner
with st.spinner("กำลังโหลดข้อมูล..."):
    df = load_sqlite_data()

# --- Search Form ---
with st.form("search_form"):
    col1, col2, col3 = st.columns(3)
    id_card = col1.text_input("เลขบัตรประชาชน")
    hn = col2.text_input("HN")
    full_name = col3.text_input("ชื่อ-สกุล")
    submitted = st.form_submit_button("ค้นหา")

if submitted:
    query = df.copy()

    if id_card.strip():
        query = query[query["เลขบัตรประชาชน"] == id_card.strip()]
    if hn.strip():
        # Ensure HN is cleaned before querying (as it's cleaned on load)
        hn_cleaned = str(int(float(hn.strip()))) if hn.strip().replace('.', '', 1).isdigit() else hn.strip()
        query = query[query["HN"] == hn_cleaned]
    if full_name.strip():
        query = query[query["ชื่อ-สกุล"].str.strip() == full_name.strip()]

    # Clear previous selections on new search
    st.session_state.pop("selected_index", None)
    st.session_state.pop("person_row", None) # Clear selected person row too

    if query.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        st.session_state.pop("search_result", None)
    else:
        st.session_state["search_result"] = query

# --- Select Year and Exam Date from Results ---
if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]

    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    selected_year = st.selectbox(
        "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน",
        options=available_years,
        format_func=lambda y: f"พ.ศ. {y}",
        key="year_selector"
    )

    # Filter by selected year and the found HN/ID (assuming one person per search)
    selected_person_df = results_df[
        (results_df["Year"] == selected_year) &
        (results_df["HN"] == results_df.iloc[0]["HN"]) # Use HN of the first found person
    ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]) # Remove duplicates based on HN and Date

    exam_dates = selected_person_df["วันที่ตรวจ"].dropna().unique().tolist()
    
    # Sort dates, assuming they are strings or can be converted to datetime
    try:
        exam_dates.sort(key=lambda x: pd.to_datetime(x, errors='coerce'), reverse=True)
    except:
        pass # Fallback to default sort if date format is inconsistent

    # If there's only one entry for the year, select it automatically
    if len(selected_person_df) == 1:
        st.session_state["person_row"] = selected_person_df.iloc[0].to_dict()
    elif len(exam_dates) > 1:
        st.markdown("##### เลือกวันที่ตรวจ:")
        # Use st.radio for better layout if many dates, or st.select_slider for very many
        selected_date_option = st.radio(
            "เลือกวันที่ตรวจ:",
            options=exam_dates,
            key="exam_date_radio",
            horizontal=True # Display buttons horizontally
        )
        if selected_date_option:
            st.session_state["person_row"] = selected_person_df[
                selected_person_df["วันที่ตรวจ"] == selected_date_option
            ].iloc[0].to_dict()
    elif len(exam_dates) == 1:
        st.session_state["person_row"] = selected_person_df[
            selected_person_df["วันที่ตรวจ"] == exam_dates[0]
        ].iloc[0].to_dict()
    else:
        st.warning("ไม่พบข้อมูลการตรวจสำหรับปีที่เลือก")
        st.session_state.pop("person_row", None) # No data for selected year/person

# --- Display Health Report ---
if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    sex = str(person.get("เพศ", "")).strip()

    # Get and format physical data
    sbp = safe_value(person.get("SBP", "-"))
    dbp = safe_value(person.get("DBP", "-"))
    pulse = safe_value(person.get("pulse", "-"))
    weight = safe_value(person.get("น้ำหนัก", "-"))
    height = safe_value(person.get("ส่วนสูง", "-"))
    waist = safe_value(person.get("รอบเอว", "-"))
    check_date = safe_value(person.get("วันที่ตรวจ", "-"))

    # Calculate BMI
    bmi_val = None
    try:
        weight_val = float(str(weight).replace("กก.", "").strip())
        height_val = float(str(height).replace("ซม.", "").strip())
        if height_val > 0: # Avoid division by zero
            bmi_val = weight_val / ((height_val / 100) ** 2)
    except:
        pass

    # Format BP and Pulse
    sbp_int = int(float(sbp)) if sbp.replace('.', '', 1).isdigit() else None
    dbp_int = int(float(dbp)) if dbp.replace('.', '', 1).isdigit() else None
    
    if sbp_int is not None and dbp_int is not None:
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
        bp_desc = interpret_bp(sbp_int, dbp_int)
        bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val
    else:
        bp_full = "-"

    pulse_val = int(float(pulse)) if pulse.replace('.', '', 1).isdigit() else None
    pulse_display = f"{pulse_val} ครั้ง/นาที" if pulse_val is not None else "-"
    
    weight_display = f"{weight} กก." if weight != "-" else "-"
    height_display = f"{height} ซม." if height != "-" else "-"
    waist_display = f"{waist} ซม." if waist != "-" else "-"


    # Combined summary advice for BMI and BP
    summary_advice_physical = combined_health_advice(bmi_val, sbp, dbp)
    # No need to html.escape here if `combined_health_advice` doesn't produce HTML
    escaped_summary_advice_physical = html.escape(summary_advice_physical) if summary_advice_physical else ""


    st.markdown(f"""
    <div style="font-size: 20px; line-height: 1.8; color: inherit; padding: 24px 8px;">
        <div style="text-align: center; font-size: 29px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
        <div style="text-align: center;">วันที่ตรวจ: {check_date or "-"}</div>
        <div style="text-align: center; margin-top: 10px;">
            โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290<br>
            ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167
        </div>
        <hr style="margin: 24px 0;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {safe_value(person.get('ชื่อ-สกุล', '-'))}</div>
            <div><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else safe_value(person.get('อายุ', '-'))} ปี</div>
            <div><b>เพศ:</b> {sex or '-'}</div>
            <div><b>HN:</b> {safe_value(person.get('HN', '-'))}</div>
            <div><b>หน่วยงาน:</b> {safe_value(person.get('หน่วยงาน', '-'))}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {weight_display}</div>
            <div><b>ส่วนสูง:</b> {height_display}</div>
            <div><b>รอบเอว:</b> {waist_display}</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {pulse_display}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Display combined physical health advice using the reusable box
    if escaped_summary_advice_physical:
        st.markdown(
            render_advice_box(
                "คำแนะนำสุขภาพทั่วไป",
                escaped_summary_advice_physical,
                has_advice=True # Always show as 'has advice' if there's text
            ),
            unsafe_allow_html=True
        )

    # --- CBC and Blood Chemistry Sections ---
    # Determine Hb and Hct reference ranges based on sex
    if sex == "หญิง":
        hb_low_ref = 12
        hct_low_ref = 36
        hb_norm_text = "หญิง > 12 g/dl"
        hct_norm_text = "หญิง > 36%"
    elif sex == "ชาย":
        hb_low_ref = 13
        hct_low_ref = 39
        hb_norm_text = "ชาย > 13 g/dl"
        hct_norm_text = "ชาย > 39%"
    else: # Default if sex is not recognized
        hb_low_ref = 12
        hct_low_ref = 36
        hb_norm_text = "> 12 g/dl"
        hct_norm_text = "> 36%"

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", hb_norm_text, hb_low_ref, None, True), # higher is better for Hb
        ("ฮีมาโทคริต (Hct)", "HCT", hct_norm_text, hct_low_ref, None, True), # higher is better for Hct
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
    ]

    cbc_rows = []
    for label, col, norm, low, high, *opt in cbc_config:
        higher_is_better = opt[0] if opt else False
        val = get_numeric_value(person, col)
        result, is_abn = flag(val, low, high, higher_is_better)
        cbc_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("กรดยูริค (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), # Changed label to Uric Acid
        ("การทำงานของเอนไซม์ตับ (ALP)", "ALP", "30 - 120 U/L", 30, 120),
        ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), # higher is better for HDL
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True), # higher is better for GFR
    ]

    blood_rows = []
    for label, col, norm, low, high, *opt in blood_config:
        higher_is_better = opt[0] if opt else False
        val = get_numeric_value(person, col)
        result, is_abn = flag(val, low, high, higher_is_better)
        blood_rows.append([(label, is_abn), (result, is_abn), (norm, is_abn)])

    left_spacer, col1, col2, right_spacer = st.columns([1, 3, 3, 1])

    with col1:
        st.markdown(render_lab_section("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
        
    with col2:
        st.markdown(render_lab_section("ผลตรวจเคมีเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    # --- Consolidated General Health Advice ---
    gfr_raw = get_numeric_value(person, "GFR")
    fbs_raw = get_numeric_value(person, "FBS")
    alp_raw = get_numeric_value(person, "ALP")
    sgot_raw = get_numeric_value(person, "SGOT")
    sgpt_raw = get_numeric_value(person, "SGPT")
    uric_raw = get_numeric_value(person, "Uric Acid")
    chol_raw = get_numeric_value(person, "CHOL")
    tgl_raw = get_numeric_value(person, "TGL")
    ldl_raw = get_numeric_value(person, "LDL")

    advice_list = []
    
    # Pass original raw values to advice functions that handle parsing
    advice_list.append(kidney_advice_from_summary(kidney_summary_gfr_only(gfr_raw)))
    advice_list.append(fbs_advice(fbs_raw))
    advice_list.append(liver_advice(summarize_liver(alp_raw, sgot_raw, sgpt_raw)))
    advice_list.append(uric_acid_advice(uric_raw))
    advice_list.append(lipids_advice(summarize_lipids(chol_raw, tgl_raw, ldl_raw)))
    advice_list.append(cbc_advice(
        get_numeric_value(person, "Hb(%)"),
        get_numeric_value(person, "HCT"),
        get_numeric_value(person, "WBC (cumm)"),
        get_numeric_value(person, "Plt (/mm)"),
        sex=sex
    ))

    spacer_l_advice, main_col_advice, spacer_r_advice = st.columns([1, 6, 1])

    with main_col_advice:
        final_advice_html = merge_final_advice_grouped(advice_list)
        has_advice_general = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
        
        st.markdown(
            render_advice_box(
                "คำแนะนำจากผลตรวจสุขภาพ",
                final_advice_html, # This is already HTML formatted by merge_final_advice_grouped
                has_advice_general
            ),
            unsafe_allow_html=True
        )

    # --- Urinalysis Section ---
    st.markdown(render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis"), unsafe_allow_html=True)

    # Extract raw urinalysis values
    alb_raw = safe_value(person.get("Alb", "-"))
    sugar_raw = safe_value(person.get("sugar", "-"))
    rbc_raw = safe_value(person.get("RBC1", "-"))
    wbc_raw = safe_value(person.get("WBC1", "-"))

    # Urinalysis data for table display
    urine_data = [
        ("สี (Colour)", safe_value(person.get("Color", "-")), "Yellow, Pale Yellow"),
        ("น้ำตาล (Sugar)", sugar_raw, "Negative"),
        ("โปรตีน (Albumin)", alb_raw, "Negative, trace"),
        ("กรด-ด่าง (pH)", safe_value(person.get("pH", "-")), "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", safe_value(person.get("Spgr", "-")), "1.003 - 1.030"),
        ("เม็ดเลือดแดง (RBC)", rbc_raw, "0 - 2 cell/HPF"),
        ("เม็ดเลือดขาว (WBC)", wbc_raw, "0 - 5 cell/HPF"),
        ("เซลล์เยื่อบุผิว (Squam.epit.)", safe_value(person.get("SQ-epi", "-")), "0 - 10 cell/HPF"),
        ("อื่นๆ", safe_value(person.get("ORTER", "-")), "-"),
    ]

    # Convert urine data to rows format suitable for render_lab_section if needed,
    # or render as a simple table for unique interpretation.
    # For now, let's keep it simple with direct values and then advice.
    
    # Determine if urine result is abnormal for highlight
    def is_urine_abnormal(test_name, value, normal_range):
        val_str = str(value or "").strip().lower()
        if is_empty(val_str): return False

        if test_name == "สี (Colour)":
            return val_str not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
        elif test_name == "น้ำตาล (Sugar)":
            return interpret_sugar(val_str).lower() not in ["ไม่พบ", "-"]
        elif test_name == "โปรตีน (Albumin)":
            return interpret_alb(val_str).lower() not in ["ไม่พบ", "-"]
        elif test_name == "กรด-ด่าง (pH)":
            try: return not (5.0 <= float(val_str) <= 8.0)
            except: return True
        elif test_name == "ความถ่วงจำเพาะ (Sp.gr)":
            try: return not (1.003 <= float(val_str) <= 1.030)
            except: return True
        elif test_name == "เม็ดเลือดแดง (RBC)":
            return interpret_rbc(val_str).lower() not in ["ปกติ", "-"]
        elif test_name == "เม็ดเลือดขาว (WBC)":
            return interpret_wbc(val_str).lower() not in ["ปกติ", "-"]
        # For other tests like Squam.epit. or Others,
        # it depends on specific criteria to flag as abnormal.
        # For now, only flag if it's not empty and not in assumed normal values.
        elif test_name in ["เซลล์เยื่อบุผิว (Squam.epit.)", "อื่นๆ"]:
             low, high = parse_range_or_number(val_str)
             if high is not None and high > 10: # Example threshold
                 return True
        return False


    urine_table_rows = []
    for label, val, norm in urine_data:
        is_abn = is_urine_abnormal(label, val, norm)
        urine_table_rows.append([(label, is_abn), (val, is_abn), (norm, is_abn)])

    left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([1, 3, 3, 1])

    with col_ua_left:
        st.markdown(render_lab_section("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_table_rows), unsafe_allow_html=True)
    
    # --- Urinalysis Advice ---
    with col_ua_right:
        urine_advice_text = urine_analysis_advice(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
        has_urine_advice = "ไม่พบความผิดปกติที่สำคัญ" not in urine_advice_text
        
        st.markdown(
            render_advice_box(
                "คำแนะนำผลตรวจปัสสาวะ",
                html.escape(urine_advice_text), # Escape the advice text
                has_urine_advice
            ),
            unsafe_allow_html=True
        )

    # --- Hepatitis B Screening Section ---
    st.markdown(render_section_header("ผลตรวจไวรัสตับอักเสบบี", "Hepatitis B Screening"), unsafe_allow_html=True)

    hbsag_val = safe_value(person.get("HBsAg", "-")) # Assuming column "HBsAg" exists
    antihbs_val = safe_value(person.get("AntiHBs", "-")) # Assuming column "AntiHBs" exists

    # Hepatitis B data for table display
    hep_data = [
        ("HBsAg", hbsag_val, interpret_hbsag(hbsag_val)),
        ("Anti-HBs", antihbs_val, interpret_antihbs(antihbs_val)),
    ]

    # Helper to determine if Hepatitis result is abnormal for highlight
    def is_hep_abnormal(test_name, interpreted_value):
        if test_name == "HBsAg":
            return interpreted_value == "พบเชื้อไวรัสตับอักเสบบี"
        elif test_name == "Anti-HBs":
            return interpreted_value == "ไม่มีภูมิคุ้มกันไวรัสตับอักเสบบี"
        return False
    
    hep_table_rows = []
    for label, val, interpreted in hep_data:
        is_abn = is_hep_abnormal(label, interpreted)
        hep_table_rows.append([(label, is_abn), (val, is_abn), (interpreted, is_abn)])


    left_spacer_hep_table, col_hep_table, right_spacer_hep_table = st.columns([1, 6, 1])

    with col_hep_table:
        # Reusing render_lab_section for hepatitis results table
        # Headers might need adjustment if "ค่าปกติ" is not applicable as a column
        st.markdown(render_lab_section(
            "", # No main title for table, as section header is already above
            "", # No subtitle for table
            ["การตรวจ", "ผล", "การตีความ"], # Custom headers for this table
            hep_table_rows
        ), unsafe_allow_html=True)

    # --- Hepatitis B Advice ---
    hepatitis_summary = hepatitis_advice(hbsag_val, antihbs_val)
    has_hep_advice = "ไม่พบความผิดปกติที่สำคัญ" not in hepatitis_summary

    left_spacer_hep_advice, col_hep_advice, right_spacer_hep_advice = st.columns([1, 6, 1])
    with col_hep_advice:
        st.markdown(
            render_advice_box(
                "คำแนะนำไวรัสตับอักเสบบี",
                html.escape(hepatitis_summary), # Escape the advice text
                has_hep_advice
            ),
            unsafe_allow_html=True
        )
