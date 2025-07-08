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

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# --- Global Helper Functions: START ---
# Moved to global scope to prevent NameError

# Function to normalize and convert Thai dates
def normalize_thai_date(date_str):
    if is_empty(date_str):
        return "-" # Or "ไม่ระบุ"
    
    s = str(date_str).strip()

    # Aggressive initial cleaning of punctuation and specific text patterns
    s_cleaned_punc_temp = s.replace('.', '').replace('พ.ศ.', '').replace('พศ.', '').strip()
    s_cleaned_punc_temp = s_cleaned_punc_temp.replace('-', '').replace('/', '').replace(' ', '').strip() # Remove all spaces/hyphens/slashes/dots temporarily for parsing
    
    # Handle specific non-date strings after basic cleaning
    if str(date_str).strip().lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]:
        return str(date_str).strip() # Return original non-date string if matched

    # Define Thai month mappings (local to this function for clarity)
    thai_months = {
        1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
        5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
        9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
    }
    thai_month_abbr_to_num = {
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

    # --- Step 1: Try to parse with pandas (most robust for various formats with separators) ---
    try:
        # Use the original string for pandas.to_datetime first, it's very robust with separators.
        # errors='coerce' will turn unparsable dates into NaT (Not a Time).
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')

        if pd.notna(parsed_dt): # Check if pandas successfully parsed it
            # Adjust for Buddhist Era year interpretation if needed
            if parsed_dt.year > datetime.now().year + 50: # Heuristic for BE year
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            
            # Reconstruct the string with guaranteed space
            return " ".join([str(parsed_dt.day), thai_months[parsed_dt.month], str(parsed_dt.year + 543)])
    except Exception:
        pass # Fall through to regex attempts if pandas fails

    # --- Step 2: Try specific regex patterns on the aggressively cleaned string ('s_cleaned_punc') ---
    # These patterns are for cases where pandas might fail due to lack of separators, but structure is fixed.

    # Regex for DDMonthNameYYYY without explicit spaces (because s_cleaned_punc has no spaces)
    # Example: "5กุมภาพันธ์2568"
    match_thai_text_date_no_space = re.match(r'^(?P<day1>\d{1,2})(?P<month_str>[ก-ฮ]+)(?P<year>\d{4})$', s_cleaned_punc_temp)
    if match_thai_text_date_no_space:
        try:
            day = int(match_thai_text_date_no_space.group('day1'))
            month_str = match_thai_text_date_no_space.group('month_str')
            year = int(match_thai_text_date_no_space.group('year'))
            
            month_num = thai_month_abbr_to_num.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return " ".join([str(day), thai_months[dt.month], str(year)])
        except (ValueError, KeyError):
            pass

    # Fallback if nothing else works
    return s # Final fallback, returns the original string 's' if all parsing fails.


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
    if bmi_text and not bp_text: # Added this case
         return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    return "" # Default return if no specific advice is generated

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
        return "พบเม็ดเลือดขาวในปัส saliva.น้อย"
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
    
    # HTML for urine table (similar to render_lab_table_html, but with custom styling for urine table)
    style = """
    <style>
        .urine-table-container {
            background-color: var(--background-color);
            margin-top: 1rem;
        }
        .urine-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 18px; /* Adjusted font size */
            font-family: "Sarabun", sans-serif;
            color: var(--text-color);
            table-layout: fixed; /* Ensures column widths are respected */
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
    html = style + render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis")
    html += "<div class='urine-table-container'><table class='urine-table'>"
    # Add colgroup for explicit column widths (equal distribution for 3 columns)
    html += """
        <colgroup>
            <col style="width: 33.33%;"> <col style="width: 33.33%;"> <col style="width: 33.33%;"> </colgroup>
    """
    html += "<thead><tr>"
    html += "<th style='text-align: left;'>การตรวจ</th>"
    html += "<th>ผลตรวจ</th>"
    html += "<th style='text-align: left;'>ค่าปกติ</th>"
    html += "</tr></thead><tbody>"
    
    for _, row in df_urine.iterrows():
        is_abn = is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])
        css_class = "urine-abn" if is_abn else "urine-row"
        html += f"<tr class='{css_class}'>"
        html += f"<td style='text-align: left;'>{row['การตรวจ']}</td>"
        html += f"<td>{safe_value(row['ผลตรวจ'])}</td>"
        html += f"<td style='text-align: left;'>{row['ค่าปกติ']}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)
    
    summary = advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
    
    # Determine if any of the key urine results are actually present (not empty)
    # This will prevent showing 'normal' advice if there's truly no data.
    has_any_urine_result = any(not is_empty(val) for _, val, _ in urine_data)

    if not has_any_urine_result:
        # If no urine results at all, do not render the advice box.
        pass
    elif summary: # There is an actual advice due to abnormality
        st.markdown(f"""
            <div style='
                background-color: rgba(255, 255, 0, 0.2); /* Vibrant translucent yellow for advice/abnormal */
                color: var(--text-color);
                padding: 1rem;
                border-radius: 6px;
                margin-top: 1rem;
                font-size: 18px; /* Adjusted font size */
                font-family: "Sarabun", sans-serif;
            '>
                {summary}
            </div>
        """, unsafe_allow_html=True)
    else: # No specific advice, meaning results are normal
        st.markdown(f"""
            <div style='
                background-color: rgba(57, 255, 20, 0.2); /* Vibrant translucent green for normal */
                color: var(--text-color);
                padding: 1rem;
                border-radius: 6px;
                margin-top: 1rem;
                font-size: 18px; /* Adjusted font size */
                font-family: "Sarabun", sans-serif;
            '>
                ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ
            </div>
        """, unsafe_allow_html=True)

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    return "EKG" if year == 2568 else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

# === Helper: Prevent empty values
def safe_text(val):
    return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()

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
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

# --- Global Helper Functions: END ---


# ==================== UI SEARCH FORM (Moved to Sidebar) ====================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.markdown("""
    <style>
    /* Import Sarabun font from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

    /* Apply Sarabun font globally */
    html, body, [class*="st-emotion"], [class*="css-"] { /* Target Streamlit elements */
        font-family: "Sarabun", sans-serif;
    }

    /* Override specific elements if needed, for example the main text */
    div.stMarkdown, div.stText, p {
        font-family: "Sarabun", sans-serif;
    }

    /* Adjust font for inputs/select boxes if they don't inherit automatically */
    .stTextInput > div > div > input, .stSelectbox > div > div > div > div {
        font-family: "Sarabun", sans-serif;
    }


    /* Original scrollbar CSS */
    div.stMarkdown {
        overflow: visible !important;
    }

    section.main > div {
        overflow-y: visible !important;
    }

    [data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    ::-webkit-scrollbar {
        width: 0px;
        background: transparent;
    }

    div[style*="overflow: auto"] {
        overflow: visible !important;
    }

    div[style*="overflow-x: auto"] {
        overflow-x: visible !important;
    }

    div[style*="overflow-y: auto"] {
        overflow-y: visible !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; font-family: \"Sarabun\", sans-serif;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray; font-family: \"Sarabun\", sans-serif;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

# Main search form moved to sidebar (already done above)

# ==================== SELECT YEAR AND EXAM DATE IN SIDEBAR (Logic from previous turns) ====================
# This block already exists conditionally based on search_result
# It will be displayed in the sidebar after a successful search

# ==================== Display Health Report (Main Content) ====================
# This entire section will only render if person_row and selected_row_found are true
# All helper functions are now defined globally above
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    person = st.session_state["person_row"]
    year_display = person.get("Year", "-")

    # ===== Fetch main data =====
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse_raw = person.get("pulse", "-")
    weight = person.get("น้ำหนัก", "-")
    height = person.get("ส่วนสูง", "-")
    waist = person.get("รอบเอว", "-")
    check_date = person.get("วันที่ตรวจ", "-")

    try:
        weight_val = float(str(weight).replace("กก.", "").strip())
        height_val = float(str(height).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2)
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
    weight = f"{weight} กก." if not is_empty(weight) else "-"
    height = f"{height} ซม." if not is_empty(height) else "-"
    waist = f"{waist} ซม." if not is_empty(waist) else "-"

    advice_text = combined_health_advice(bmi_val, sbp, dbp)
    summary_advice = html.escape(advice_text) if advice_text else ""
    
    # ===== Display General Information Section =====
    st.markdown(f"""
    <div style="font-size: 18px; line-height: 1.8; color: inherit; padding: 24px 8px; font-family: \"Sarabun\", sans-serif;">
        <div style="text-align: center; font-size: 29px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
        <div style="text-align: center;">วันที่ตรวจ: {check_date or "-"}</div>
        <div style="text-align: center; margin-top: 10px;">
            โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290<br>
            ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167
        </div>
        <hr style="margin: 24px 0;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</div>
            <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
            <div><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {weight}</div>
            <div><b>ส่วนสูง:</b> {height}</div>
            <div><b>รอบเอว:</b> {waist}</div>
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
        ("ฮีมาโทคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
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
        ("น้ำตาลในเลือด (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
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

    left_spacer, col1, col2, right_spacer = st.columns([0.5, 3, 3, 0.5]) # Adjusted spacer ratio

    with col1:
        st.markdown(render_lab_table_html("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_lab_table_html("ผลตรวจเคมีเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

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

    spacer_l, main_col, spacer_r = st.columns([0.5, 6, 0.5]) # Adjusted spacer ratio

    with main_col:
        final_advice_html = merge_final_advice_grouped(advice_list)
        # Determine if there's any *actual* advice for general health (i.e., not just "no advice")
        has_general_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
        
        # Set background color based on whether there's advice
        background_color_general_advice = (
            "rgba(255, 255, 0, 0.2)" if has_general_advice else "rgba(57, 255, 20, 0.2)" # Vibrant translucent yellow if advice, vibrant translucent green if normal
        )

        st.markdown(f"""
        <div style="
            background-color: {background_color_general_advice};
            padding: 1rem 2.5rem;
            border-radius: 10px;
            font-size: 18px; /* Adjusted font size */
            line-height: 1.5;
            color: var(--text-color);
            font-family: "Sarabun", sans-serif;
        ">
            {final_advice_html}
        </div>
        """, unsafe_allow_html=True)

    # ==================== Urinalysis Section ====================
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
            return "พบเม็ดเลือดขาวในปัส saliva.น้อย"
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
        
        # HTML for urine table (similar to render_lab_table_html, but with custom styling for urine table)
        style = """
        <style>
            .urine-table-container {
                background-color: var(--background-color);
                margin-top: 1rem;
            }
            .urine-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 18px; /* Adjusted font size */
                font-family: "Sarabun", sans-serif;
                color: var(--text-color);
                table-layout: fixed; /* Ensures column widths are respected */
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
        html = style + render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis")
        html += "<div class='urine-table-container'><table class='urine-table'>"
        # Add colgroup for explicit column widths (equal distribution for 3 columns)
        html += """
            <colgroup>
                <col style="width: 33.33%;"> <col style="width: 33.33%;"> <col style="width: 33.33%;"> </colgroup>
        """
        html += "<thead><tr>"
        html += "<th style='text-align: left;'>การตรวจ</th>"
        html += "<th>ผลตรวจ</th>"
        html += "<th style='text-align: left;'>ค่าปกติ</th>"
        html += "</tr></thead><tbody>"
        
        for _, row in df_urine.iterrows():
            is_abn = is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])
            css_class = "urine-abn" if is_abn else "urine-row"
            html += f"<tr class='{css_class}'>"
            html += f"<td style='text-align: left;'>{row['การตรวจ']}</td>"
            html += f"<td>{safe_value(row['ผลตรวจ'])}</td>"
            html += f"<td style='text-align: left;'>{row['ค่าปกติ']}</td>"
            html += "</tr>"
        html += "</tbody></table></div>"
        st.markdown(html, unsafe_allow_html=True)
        
        summary = advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
        
        # Determine if any of the key urine results are actually present (not empty)
        # This will prevent showing 'normal' advice if there's truly no data.
        has_any_urine_result = any(not is_empty(val) for _, val, _ in urine_data)

        if not has_any_urine_result:
            # If no urine results at all, do not render the advice box.
            pass
        elif summary: # There is an actual advice due to abnormality
            st.markdown(f"""
                <div style='
                    background-color: rgba(255, 255, 0, 0.2); /* Vibrant translucent yellow for advice/abnormal */
                    color: var(--text-color);
                    padding: 1rem;
                    border-radius: 6px;
                    margin-top: 1rem;
                    font-size: 18px; /* Adjusted font size */
                    font-family: "Sarabun", sans-serif;
                '>
                    {summary}
                </div>
            """, unsafe_allow_html=True)
        else: # No specific advice, meaning results are normal
            st.markdown(f"""
                <div style='
                    background-color: rgba(57, 255, 20, 0.2); /* Vibrant translucent green for normal */
                    color: var(--text-color);
                    padding: 1rem;
                    border-radius: 6px;
                    margin-top: 1rem;
                    font-size: 18px; /* Adjusted font size */
                    font-family: "Sarabun", sans-serif;
                '>
                    ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ
                </div>
            """, unsafe_allow_html=True)

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    return "EKG" if year == 2568 else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val):
        return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

# === Helper: Prevent empty values
def safe_text(val):
    return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()

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
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

# --- Global Helper Functions: END ---


# ==================== Main Application Layout ====================

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.markdown("""
    <style>
    /* Import Sarabun font from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

    /* Apply Sarabun font globally */
    html, body, [class*="st-emotion"], [class*="css-"] { /* Target Streamlit elements */
        font-family: "Sarabun", sans-serif;
    }

    /* Override specific elements if needed, for example the main text */
    div.stMarkdown, div.stText, p {
        font-family: "Sarabun", sans-serif;
    }

    /* Adjust font for inputs/select boxes if they don't inherit automatically */
    .stTextInput > div > div > input, .stSelectbox > div > div > div > div {
        font-family: "Sarabun", sans-serif;
    }


    /* Original scrollbar CSS */
    div.stMarkdown {
        overflow: visible !important;
    }

    section.main > div {
        overflow-y: visible !important;
    }

    [data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }

    ::-webkit-scrollbar {
        width: 0px;
        background: transparent;
    }

    div[style*="overflow: auto"] {
        overflow: visible !important;
    }

    div[style*="overflow-x: auto"] {
        overflow-x: visible !important;
    }

    div[style*="overflow-y: auto"] {
        overflow-y: visible !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center; font-family: \"Sarabun\", sans-serif;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray; font-family: \"Sarabun\", sans-serif;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

# Main search form in sidebar (defined above, executed here)
# ... (search form definition and logic) ...

# This part needs to be outside the sidebar form, but can be in the main content area or its own container
# It uses 'submitted_sidebar' from the form above
# ... (search result processing and dropdowns) ...

# ==================== Main Content Area ====================
# This section will only render if person_row and selected_row_found are true
# All helper functions used here are defined globally above
with st.container():
    if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
        person = st.session_state["person_row"]
        year_display = person.get("Year", "-")

        # ===== Fetch main data =====
        sbp = person.get("SBP", "")
        dbp = person.get("DBP", "")
        pulse_raw = person.get("pulse", "-")
        weight = person.get("น้ำหนัก", "-")
        height = person.get("ส่วนสูง", "-")
        waist = person.get("รอบเอว", "-")
        check_date = person.get("วันที่ตรวจ", "-")

        try:
            weight_val = float(str(weight).replace("กก.", "").strip())
            height_val = float(str(height).replace("ซม.", "").strip())
            bmi_val = weight_val / ((height_val / 100) ** 2)
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
        weight = f"{weight} กก." if not is_empty(weight) else "-"
        height = f"{height} ซม." if not is_empty(height) else "-"
        waist = f"{waist} ซม." if not is_empty(waist) else "-"

        advice_text = combined_health_advice(bmi_val, sbp, dbp)
        summary_advice = html.escape(advice_text) if advice_text else ""
        
        # ===== Display General Information Section =====
        st.markdown(f"""
        <div style="font-size: 18px; line-height: 1.8; color: inherit; padding: 24px 8px; font-family: \"Sarabun\", sans-serif;">
            <div style="text-align: center; font-size: 29px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
            <div style="text-align: center;">วันที่ตรวจ: {check_date or "-"}</div>
            <div style="text-align: center; margin-top: 10px;">
                โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290<br>
                ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167
            </div>
            <hr style="margin: 24px 0;">
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
                <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
                <div><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</div>
                <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
                <div><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</div>
                <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
            </div>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
                <div><b>น้ำหนัก:</b> {weight}</div>
                <div><b>ส่วนสูง:</b> {height}</div>
                <div><b>รอบเอว:</b> {waist}</div>
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
            ("ฮีมาโทคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None),
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
            ("น้ำตาลในเลือด (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
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

        left_spacer, col1, col2, right_spacer = st.columns([0.5, 3, 3, 0.5]) # Adjusted spacer ratio

        with col1:
            st.markdown(render_lab_table_html("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
        
        with col2:
            st.markdown(render_lab_table_html("ผลตรวจเคมีเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

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

        spacer_l, main_col, spacer_r = st.columns([0.5, 6, 0.5]) # Adjusted spacer ratio

        with main_col:
            final_advice_html = merge_final_advice_grouped(advice_list)
            # Determine if there's any *actual* advice for general health (i.e., not just "no advice")
            has_general_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
            
            # Set background color based on whether there's advice
            background_color_general_advice = (
                "rgba(255, 255, 0, 0.2)" if has_general_advice else "rgba(57, 255, 20, 0.2)" # Vibrant translucent yellow if advice, vibrant translucent green if normal
            )

            st.markdown(f"""
            <div style="
                background-color: {background_color_general_advice};
                padding: 1rem 2.5rem;
                border-radius: 10px;
                font-size: 18px; /* Adjusted font size */
                line-height: 1.5;
                color: var(--text-color);
                font-family: "Sarabun", sans-serif;
            ">
                {final_advice_html}
            </div>
            """, unsafe_allow_html=True)

        # ==================== Urinalysis Section ====================
        # This function definition is moved to global scope
        
        with st.container(): # This was 'with col_ua_left:', now it's a general container
            left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([0.5, 3, 3, 0.5]) # Adjusted spacer ratio
            
            with col_ua_left:
                render_urine_section(person, sex, selected_year)

                # ==================== Stool Section ====================
                st.markdown(render_section_header("ผลตรวจอุจจาระ", "Stool Examination"), unsafe_allow_html=True)
                
                def render_stool_html_table(exam, cs): # This function definition is moved to global scope
                    style = """
                    <style>
                        .stool-container {
                            background-color: var(--background-color);
                            margin-top: 1rem;
                        }
                        .stool-table {
                            width: 100%;
                            border-collapse: collapse;
                            font-size: 18px; /* Adjusted font size */
                            font-family: "Sarabun", sans-serif;
                            table-layout: fixed; /* Ensure column widths are respected */
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
                    html = f"""
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
                    return style + html
                
                stool_exam_raw = person.get("Stool exam", "")
                stool_cs_raw = person.get("Stool C/S", "")
                exam_text = interpret_stool_exam(stool_exam_raw)
                cs_text = interpret_stool_cs(stool_cs_raw)
                st.markdown(render_stool_html_table(exam_text, cs_text), unsafe_allow_html=True)

        with col_ua_right:
            # ============ X-ray Section ============
            st.markdown(render_section_header("ผลเอกซเรย์", "Chest X-ray"), unsafe_allow_html=True)
            
            selected_year_int = int(selected_year)
            cxr_col = "CXR" if selected_year_int == 2568 else f"CXR{str(selected_year_int)[-2:]}"
            cxr_raw = person.get(cxr_col, "")
            cxr_result = interpret_cxr(cxr_raw)
            
            st.markdown(f"""
            <div style='
                background-color: var(--background-color);
                color: var(--text-color);
                font-size: 18px; /* Adjusted font size */
                line-height: 1.6;
                padding: 1.25rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                font-family: "Sarabun", sans-serif;
            '>
                {cxr_result}
            </div>
            """, unsafe_allow_html=True)

            # ==================== EKG Section ====================
            st.markdown(render_section_header("ผลคลื่นไฟฟ้าหัวใจ", "EKG"), unsafe_allow_html=True)

            ekg_col = get_ekg_col_name(selected_year_int)
            ekg_raw = person.get(ekg_col, "")
            ekg_result = interpret_ekg(ekg_raw)

            st.markdown(f"""
            <div style='
                background-color: var(--secondary-background-color);
                color: var(--text-color);
                font-size: 18px; /* Adjusted font size */
                line-height: 1.6;
                padding: 1.25rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                font-family: "Sarabun", sans-serif;
            '>
                {ekg_result}
            </div>
            """, unsafe_allow_html=True)

            # === Helper: Prevent empty values
            # This function definition is moved to global scope
            
            # ==================== Section: Hepatitis A ====================
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบเอ (Viral hepatitis A)"), unsafe_allow_html=True)
            
            hep_a_raw = safe_text(person.get("Hepatitis A"))
            st.markdown(f"""
            <div style='
                font-size: 18px; /* Adjusted font size */
                padding: 1rem;
                border-radius: 6px;
                margin-bottom: 1.5rem;
                background-color: rgba(255,255,255,0.05);
                font-family: "Sarabun", sans-serif;
            '>
                {hep_a_raw}
            </div>
            """, unsafe_allow_html=True)
            
            # ================ Section: Hepatitis B =================

            # normalize_date_for_display is defined globally now
            
            hep_check_date_raw = person.get("ปีตรวจHEP")
            hep_check_date = normalize_date_for_display(hep_check_date_raw) # Use the new normalization function here
            
            st.markdown(render_section_header("ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)"), unsafe_allow_html=True)
            
            hbsag_raw = safe_text(person.get("HbsAg"))
            hbsab_raw = safe_text(person.get("HbsAb"))
            hbcab_raw = safe_text(person.get("HBcAB"))
            
            st.markdown(f"""
            <div style="margin-bottom: 1rem;">
            <table style='
                width: 100%;
                font-size: 18px; /* Adjusted font size */
                text-align: center;
                border-collapse: collapse;
                min-width: 300px;
                font-family: "Sarabun", sans-serif;
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
                font-size: 18px; /* Adjusted font size */
                padding: 0.75rem 1rem;
                background-color: rgba(255,255,255,0.05);
                border-radius: 6px;
                margin-bottom: 1.5rem;
                line-height: 1.8;
                font-family: "Sarabun", sans-serif;
            '>
                <b>วันที่ตรวจภูมิคุ้มกัน:</b> {hep_check_date}<br>
                <b>ประวัติโรคไวรัสตับอักเสบบี ปี พ.ศ. {selected_year}:</b> {hep_history}<br>
                <b>ประวัติการได้รับวัคซีนในปี พ.ศ. {selected_year}:</b> {hep_vaccine}
            </div>
            """, unsafe_allow_html=True)
            
            # hepatitis_b_advice is defined globally now
            
            advice = hepatitis_b_advice(hbsag_raw, hbsab_raw, hbcab_raw)
            
            # 🌈 Set background color based on advice
            if advice.strip() == "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี":
                bg_color = "rgba(57, 255, 20, 0.2)"  # Vibrant translucent green
            else:
                bg_color = "rgba(255, 255, 0, 0.2)" # Vibrant translucent yellow

            st.markdown(f"""
            <div style='
                font-size: 18px; /* Adjusted font size */
                line-height: 1.6;
                padding: 1rem 1.5rem;
                border-radius: 6px;
                background-color: {bg_color};
                color: var(--text-color);
                margin-bottom: 1.5rem;
                font-family: "Sarabun", sans-serif;
            '>
                {advice}
            </div>
            """, unsafe_allow_html=True)
                
#=========================== ความเห็นแพทย์ =======================
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    person = st.session_state["person_row"]
    doctor_suggestion = str(person.get("DOCTER suggest", "")).strip()
    if doctor_suggestion.lower() in ["", "-", "none", "nan", "null"]:
        doctor_suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"

    left_spacer3, doctor_col, right_spacer3 = st.columns([0.5, 6, 0.5]) # Adjusted spacer ratio

    with doctor_col:
        st.markdown(f"""
        <div style='
            background-color: #1b5e20;
            color: white;
            padding: 1.5rem 2rem;
            border-radius: 8px;
            font-size: 18px; /* Adjusted font size */
            line-height: 1.6;
            margin-top: 2rem;
            margin-bottom: 2rem;
            font-family: "Sarabun", sans-serif;
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
