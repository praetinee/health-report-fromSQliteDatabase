import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html
import numpy as np
from collections import OrderedDict

# --- Utility Functions ---
def is_empty(val):
    """Checks if a value is considered empty."""
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

@st.cache_data(ttl=600)
def load_sqlite_data():
    """Loads health data from a SQLite database stored on Google Drive."""
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()

        # Save to a temporary file for sqlite3
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.write(response.content)
        tmp.flush()
        tmp.close()

        conn = sqlite3.connect(tmp.name)
        df = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()

        # Strip whitespace from column names and clean data
        df.columns = df.columns.str.strip()
        df['เลขบัตรประชาชน'] = df['เลขบัตรประชาชน'].astype(str).str.strip()
        df['HN'] = df['HN'].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip().replace('.', '', 1).isdigit() else "").str.strip()
        df['ชื่อ-สกุล'] = df['ชื่อ-สกุล'].astype(str).str.strip()
        df['Year'] = df['Year'].astype(int)

        # Replace missing value indicators with pandas NA
        df.replace(["-", "None", None, "nan"], pd.NA, inplace=True)

        return df
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

def get_float(col, person_data):
    """Safely converts a column value to a float, returning None if empty or invalid."""
    val = person_data.get(col, "")
    if is_empty(val):
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return None

def flag(val, low=None, high=None, higher_is_better=False):
    """Formats a value and determines if it's outside normal range."""
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
    
    # Check for cases where the value is zero but not truly abnormal based on bounds (e.g., in liver tests)
    # This might need more specific handling based on context if 0 is a valid normal result
    if val_float == 0 and not is_abnormal: # If 0 is given but not flagged by low/high, assume it's like missing or unknown
         return "-", False

    return f"{val_float:.1f}", is_abnormal

def render_section_header(title, subtitle=None):
    """Renders a styled section header."""
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
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

def format_person_data_for_display(person):
    """Extracts and formats key person data for display."""
    check_date = person.get("วันที่ตรวจ", "-")

    sbp = get_float("SBP", person)
    dbp = get_float("DBP", person)
    
    if sbp is not None and dbp is not None:
        bp_val = f"{int(sbp)}/{int(dbp)} ม.ม.ปรอท"
        bp_desc = interpret_bp(sbp, dbp)
        bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val
    else:
        bp_full = "-"

    pulse_val = get_float("pulse", person)
    pulse = f"{int(pulse_val)} ครั้ง/นาที" if pulse_val is not None else "-"
    
    weight_val = get_float("น้ำหนัก", person)
    weight = f"{weight_val:.1f} กก." if weight_val is not None else "-"
    
    height_val = get_float("ส่วนสูง", person)
    height = f"{height_val:.1f} ซม." if height_val is not None else "-"
    
    waist_val = get_float("รอบเอว", person)
    waist = f"{waist_val:.1f} ซม." if waist_val is not None else "-"

    try:
        bmi_val = weight_val / ((height_val / 100) ** 2) if weight_val and height_val else None
    except ZeroDivisionError:
        bmi_val = None

    advice_text = combined_health_advice(bmi_val, sbp, dbp)
    summary_advice = html.escape(advice_text) if advice_text else ""

    return {
        "check_date": check_date,
        "bp_full": bp_full,
        "pulse": pulse,
        "weight": weight,
        "height": height,
        "waist": waist,
        "summary_advice": summary_advice,
        "hn": str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-'),
        "age": str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-'),
        "sex": person.get('เพศ', '-'),
        "name": person.get('ชื่อ-สกุล', '-'),
        "department": person.get('หน่วยงาน', '-'),
    }

# --- Health Interpretation Functions ---
def interpret_bp(sbp, dbp):
    """Interprets blood pressure values."""
    if sbp is None or dbp is None or sbp == 0 or dbp == 0:
        return "-"
    if sbp >= 160 or dbp >= 100:
        return "ความดันสูง"
    elif sbp >= 140 or dbp >= 90:
        return "ความดันสูงเล็กน้อย"
    elif sbp < 120 and dbp < 80:
        return "ความดันปกติ"
    else:
        return "ความดันค่อนข้างสูง"

def combined_health_advice(bmi, sbp, dbp):
    """Provides combined health advice based on BMI and BP."""
    if is_empty(bmi) and is_empty(sbp) and is_empty(dbp):
        return ""
        
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
    if bmi_text and not bp_text: # This covers cases where only BMI has issues but BP is fine or not available
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    return "" # No advice if all values are normal or missing

def kidney_summary_gfr_only(gfr_raw):
    """Summarizes kidney function based on GFR."""
    gfr = get_float(None, {"gfr": gfr_raw}) # Use get_float for robustness
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
    """Provides advice for Fasting Blood Sugar (FBS)."""
    fbs_val = get_float(None, {"fbs": fbs_raw})
    if fbs_val is None or fbs_val == 0:
        return ""
    elif 100 <= fbs_val < 106:
        return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
    elif 106 <= fbs_val < 126:
        return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
    elif fbs_val >= 126:
        return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
    else:
        return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    """Summarizes liver function."""
    alp = get_float(None, {"alp": alp_val})
    sgot = get_float(None, {"sgot": sgot_val})
    sgpt = get_float(None, {"sgpt": sgpt_val})

    if (alp is None or alp == 0) or \
       (sgot is None or sgot == 0) or \
       (sgpt is None or sgpt == 0):
        return "-"
    
    if alp > 120 or sgot > 37 or sgpt > 41: # Adjusted SGOT/SGPT thresholds based on config
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
    """Provides advice for Uric Acid."""
    value = get_float(None, {"value": value_raw})
    if value is None:
        return "-"
    if value > 7.2:
        return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
    return ""

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    """Summarizes lipid profile."""
    chol = get_float(None, {"chol": chol_raw})
    tgl = get_float(None, {"tgl": tgl_raw})
    ldl = get_float(None, {"ldl": ldl_raw})

    if (chol is None or chol == 0) and (tgl is None or tgl == 0) and (ldl is None or ldl == 0):
        return ""

    if (chol is not None and chol >= 250) or \
       (tgl is not None and tgl >= 250) or \
       (ldl is not None and ldl >= 180):
        return "ไขมันในเลือดสูง"
    elif (chol is not None and chol <= 200) and \
         (tgl is not None and tgl <= 150) and \
         (ldl is not None and ldl <= 160): # LDL upper limit based on config
        return "ปกติ"
    else:
        # This covers cases where some values are elevated but not critically high
        # Or if HDL is low (not directly checked here, but generally falls under "slightly high" if other values are fine)
        return "ไขมันในเลือดสูงเล็กน้อย"

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
    """Provides advice for Complete Blood Count (CBC)."""
    advice_parts = []

    hb_val = get_float(None, {"hb": hb})
    hct_val = get_float(None, {"hct": hct})
    wbc_val = get_float(None, {"wbc": wbc})
    plt_val = get_float(None, {"plt": plt})

    hb_ref = 13 if sex == "ชาย" else 12
    if hb_val is not None and hb_val < hb_ref:
        advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")

    hct_ref = 39 if sex == "ชาย" else 36
    if hct_val is not None and hct_val < hct_ref:
        advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")

    if wbc_val is not None:
        if wbc_val < 4000:
            advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000:
            advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")

    if plt_val is not None:
        if plt_val < 150000:
            advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000:
            advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")

    return " ".join(advice_parts)

# --- Urinalysis Interpretation Functions ---
def interpret_alb(value):
    """Interprets Albumin (protein) in urine."""
    val = str(value or "").strip().lower()
    if val == "negative":
        return "ไม่พบ", False
    elif val in ["trace", "1+", "2+"]:
        return "พบโปรตีนในปัสสาวะเล็กน้อย", True
    elif val in ["3+", "4+"]:
        return "พบโปรตีนในปัสสาวะ", True
    return "-", False

def interpret_sugar(value):
    """Interprets Sugar in urine."""
    val = str(value or "").strip().lower()
    if val == "negative":
        return "ไม่พบ", False
    elif val == "trace":
        return "พบน้ำตาลในปัสสาวะเล็กน้อย", True
    elif val in ["1+", "2+", "3+", "4+", "5+", "6+"]:
        return "พบน้ำตาลในปัสสาวะ", True
    return "-", False

def parse_range_or_number(val_str):
    """Parses a string like '0-2' or '5' into a (low, high) tuple."""
    val = str(val_str).replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val:
            low, high = map(float, val.split("-"))
            return low, high
        else:
            num = float(val)
            return num, num
    except (ValueError, TypeError):
        return None, None

def interpret_rbc(value):
    """Interprets Red Blood Cells (RBC) in urine."""
    val = str(value or "").strip().lower()
    if is_empty(val):
        return "-", False
    
    low, high = parse_range_or_number(val)
    if high is None: # If parsing failed, return original value as is, but not abnormal
        return value, False
    
    if high <= 2:
        return "ปกติ", False
    elif high <= 5:
        return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย", True
    else:
        return "พบเม็ดเลือดแดงในปัสสาวะ", True

def interpret_wbc(value):
    """Interprets White Blood Cells (WBC) in urine."""
    val = str(value or "").strip().lower()
    if is_empty(val):
        return "-", False
    
    low, high = parse_range_or_number(val)
    if high is None: # If parsing failed, return original value as is, but not abnormal
        return value, False
    
    if high <= 5:
        return "ปกติ", False
    elif high <= 10:
        return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย", True
    else:
        return "พบเม็ดเลือดขาวในปัสสาวะ", True

def advice_urine(sex, alb, sugar, rbc, wbc):
    """Provides advice based on urinalysis results."""
    alb_t, alb_abn = interpret_alb(alb)
    sugar_t, sugar_abn = interpret_sugar(sugar)
    rbc_t, rbc_abn = interpret_rbc(rbc)
    wbc_t, wbc_abn = interpret_wbc(wbc)

    # If all are normal or empty, return no advice
    if not (alb_abn or sugar_abn or rbc_abn or wbc_abn) and \
       all(x in ["-", "ปกติ", "ไม่พบ"] for x in [alb_t, sugar_t, rbc_t, wbc_t]):
        return ""
    
    advice_parts = []
    
    if "พบน้ำตาลในปัสสาวะ" in sugar_t and "เล็กน้อย" not in sugar_t:
        advice_parts.append("ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม")
    
    if "พบเม็ดเลือดแดง" in rbc_t and "ปกติ" in wbc_t:
        if sex == "หญิง":
            advice_parts.append("อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ")
        else: # sex == "ชาย"
            advice_parts.append("พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม")
    
    if "พบเม็ดเลือดขาว" in wbc_t and "เล็กน้อย" not in wbc_t:
        advice_parts.append("อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ")

    if not advice_parts: # If no specific advice, but some abnormality exists
        return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"

    return " ".join(advice_parts)

# --- Streamlit Application ---
df = load_sqlite_data()

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# Consolidated CSS
st.markdown("""
    <style>
    /* Global scrollbar control */
    body {
        overflow: auto !important;
    }
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
    div[style*="overflow: auto"], div[style*="overflow-x: auto"], div[style*="overflow-y: auto"] {
        overflow: visible !important;
    }

    /* Lab table specific styles */
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
        overflow-wrap: break-word; /* Ensure text wraps within cells */
    }
    .lab-abn {
        background-color: rgba(255, 64, 64, 0.25); /* Translucent red for abnormal */
    }
    .lab-row {
        background-color: rgba(255,255,255,0.02); /* Slightly visible row background */
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;'>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม รพ.สันทราย -</h4>", unsafe_allow_html=True)

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
        hn_cleaned = str(int(float(hn.strip()))) if hn.strip().replace('.', '', 1).isdigit() else ""
        query = query[query["HN"] == hn_cleaned]
    if full_name.strip():
        query = query[query["ชื่อ-สกุล"].str.strip() == full_name.strip()]

    # Reset previously selected year/data on new search
    st.session_state.pop("selected_index", None)
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    
    if query.empty:
        st.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบอีกครั้ง")
        st.session_state.pop("search_result", None)
    else:
        st.session_state["search_result"] = query

# --- Select Year and Date from Results ---
if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]

    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    selected_year = st.selectbox(
        "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน",
        options=available_years,
        format_func=lambda y: f"พ.ศ. {y}"
    )

    # Get HN of the first person found (assuming one person per search)
    selected_hn_for_year_filter = results_df.iloc[0]["HN"] 

    person_year_df = results_df[
        (results_df["Year"] == selected_year) &
        (results_df["HN"] == selected_hn_for_year_filter)
    ]
    person_year_df = person_year_df.drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", ascending=False)

    if len(person_year_df) > 1:
        st.markdown("---")
        st.markdown("**เลือกวันที่ตรวจที่ต้องการดูรายงาน:**")
        cols = st.columns(min(len(person_year_df), 5)) # Display buttons in up to 5 columns
        for idx, row in person_year_df.iterrows():
            label = str(row["วันที่ตรวจ"]).strip() if pd.notna(row["วันที่ตรวจ"]) else f"ครั้งที่ {idx+1}"
            with cols[idx % len(cols)]: # Cycle through columns
                if st.button(label, key=f"checkup_{idx}"):
                    st.session_state["person_row"] = row.to_dict()
                    st.session_state["selected_row_found"] = True
    elif len(person_year_df) == 1:
        st.session_state["person_row"] = person_year_df.iloc[0].to_dict()
        st.session_state["selected_row_found"] = True

# --- Display Health Report ---
if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    formatted_person_data = format_person_data_for_display(person)

    st.markdown(f"""
    <div style="font-size: 20px; line-height: 1.8; color: inherit; padding: 24px 8px;">
        <div style="text-align: center; font-size: 29px; font-weight: bold;">รายงานผลการตรวจสุขภาพ</div>
        <div style="text-align: center;">วันที่ตรวจ: {formatted_person_data['check_date'] or "-"}</div>
        <div style="text-align: center; margin-top: 10px;">
            โรงพยาบาลสันทราย 201 หมู่ที่ 11 ถนน เชียงใหม่ - พร้าว ตำบลหนองหาร อำเภอสันทราย เชียงใหม่ 50290<br>
            ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167
        </div>
        <hr style="margin: 24px 0;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 20px; text-align: center;">
            <div><b>ชื่อ-สกุล:</b> {formatted_person_data['name']}</div>
            <div><b>อายุ:</b> {formatted_person_data['age']} ปี</div>
            <div><b>เพศ:</b> {formatted_person_data['sex']}</div>
            <div><b>HN:</b> {formatted_person_data['hn']}</div>
            <div><b>หน่วยงาน:</b> {formatted_person_data['department']}</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-bottom: 16px; text-align: center;">
            <div><b>น้ำหนัก:</b> {formatted_person_data['weight']}</div>
            <div><b>ส่วนสูง:</b> {formatted_person_data['height']}</div>
            <div><b>รอบเอว:</b> {formatted_person_data['waist']}</div>
            <div><b>ความดันโลหิต:</b> {formatted_person_data['bp_full']}</div>
            <div><b>ชีพจร:</b> {formatted_person_data['pulse']}</div>
        </div>
        {f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {formatted_person_data['summary_advice']}</div>" if formatted_person_data['summary_advice'] else ""}
    </div>
    """, unsafe_allow_html=True)

    # --- Lab Results Sections (CBC & Blood Chemistry) ---
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]:
        st.warning("⚠️ เพศไม่ถูกต้องหรือไม่มีข้อมูล กำลังใช้ค่าอ้างอิงเริ่มต้น (หญิง)")
        sex = "หญิง" # Default to female if sex is not recognized

    hb_low = 13 if sex == "ชาย" else 12
    hct_low = 39 if sex == "ชาย" else 36

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", f"ชาย > {hb_low}, หญิง > {hb_low} g/dl", hb_low, None, True),
        ("ฮีมาโทคริต (Hct)", "HCT", f"ชาย > {hct_low}%, หญิง > {hct_low}%", hct_low, None, True),
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

    def render_lab_table_html(headers, rows):
        """Generates HTML for a lab results table."""
        html_str = "<div class='lab-container'><table class='lab-table'>"
        html_str += "<thead><tr>"
        for i, h in enumerate(headers):
            align = "left" if i in [0, 2] else "center"
            html_str += f"<th style='text-align: {align};'>{h}</th>"
        html_str += "</tr></thead><tbody>"
        
        for row in rows:
            # row format: [(label, is_abn), (result, is_abn), (norm, is_abn)]
            any_abnormal_in_row = any(flag for _, flag in row)
            row_class = "lab-abn" if any_abnormal_in_row else "lab-row"
            
            html_str += f"<tr>"
            html_str += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>" # Test name
            html_str += f"<td class='{row_class}'>{row[1][0]}</td>" # Result
            html_str += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>" # Normal range
            html_str += f"</tr>"
        html_str += "</tbody></table></div>"
        return html_str

    cbc_rows = []
    for label, col, norm, low, high, *opt in cbc_config:
        higher_is_better = opt[0] if opt else False
        val = get_float(col, person)
        result_str, is_abnormal = flag(val, low, high, higher_is_better)
        cbc_rows.append([(label, is_abnormal), (result_str, is_abnormal), (norm, False)]) # Norm is never 'abnormal' itself

    blood_rows = []
    for label, col, norm, low, high, *opt in blood_config:
        higher_is_better = opt[0] if opt else False
        val = get_float(col, person)
        result_str, is_abnormal = flag(val, low, high, higher_is_better)
        blood_rows.append([(label, is_abnormal), (result_str, is_abnormal), (norm, False)])

    left_spacer, col1, col2, right_spacer = st.columns([1, 3, 3, 1])

    with col1:
        st.markdown(render_section_header("ผลตรวจ CBC", "Complete Blood Count"), unsafe_allow_html=True)
        st.markdown(render_lab_table_html(["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_section_header("ผลตรวจเคมีเลือด", "Blood Chemistry"), unsafe_allow_html=True)
        st.markdown(render_lab_table_html(["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)

    # --- Combined Advice Section ---
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
    advice_list.append(kidney_advice_from_summary(kidney_summary_gfr_only(gfr_raw)))
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
        """Groups and formats the final health advice."""
        groups = OrderedDict([ # Use OrderedDict to maintain insertion order
            ("น้ำตาลในเลือด", []), 
            ("การทำงานของไต", []), 
            ("การทำงานของตับ", []), 
            ("กรดยูริค", []), 
            ("ไขมันในเลือด", []), 
            ("เม็ดเลือดและอื่นๆ", [])
        ])

        for msg in messages:
            if not msg or msg.strip() in ["-", "ไม่พบ", "ปกติ"]:
                continue
            if "น้ำตาล" in msg:
                groups["น้ำตาลในเลือด"].append(msg)
            elif "ไต" in msg:
                groups["การทำงานของไต"].append(msg)
            elif "ตับ" in msg:
                groups["การทำงานของตับ"].append(msg)
            elif "พิวรีน" in msg or "ยูริค" in msg:
                groups["กรดยูริค"].append(msg)
            elif "ไขมัน" in msg:
                groups["ไขมันในเลือด"].append(msg)
            else:
                groups["เม็ดเลือดและอื่นๆ"].append(msg) # Catch all remaining CBC advice

        output = []
        for title, msgs in groups.items():
            if msgs:
                unique_msgs = list(OrderedDict.fromkeys(msgs)) # Remove duplicates while preserving order
                output.append(f"<b>{title}:</b> {' '.join(unique_msgs)}")
        
        if not output:
            return "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"

        return "<div style='margin-bottom: 0.75rem;'>" + "</div><div style='margin-bottom: 0.75rem;'>".join(output) + "</div>"

    spacer_l, main_col, spacer_r = st.columns([1, 6, 1])

    with main_col:
        final_advice_html = merge_final_advice_grouped(advice_list)
        has_advice = "ไม่พบคำแนะนำเพิ่มเติม" not in final_advice_html
        background_color = (
            "rgba(255, 215, 0, 0.15)" if has_advice else "rgba(200, 255, 200, 0.15)"
        )
        
        st.markdown(f"""
        <div style="
            background-color: {background_color};
            padding: 1rem 2.5rem;
            border-radius: 10px;
            font-size: 16px;
            line-height: 1.5;
            color: var(--text-color);
        ">
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 0.5rem;">
                📋 คำแนะนำจากผลตรวจสุขภาพ
            </div>
            {final_advice_html}
        </div>
        """, unsafe_allow_html=True)

    # --- Urinalysis Section ---
    left_spacer_ua, col_ua_left, col_ua_right, right_spacer_ua = st.columns([1, 3, 3, 1])
    
    with col_ua_left:
        st.markdown(render_section_header("ผลการตรวจปัสสาวะ", "Urinalysis"), unsafe_allow_html=True)
        
        alb_raw = person.get("Alb", "-")
        sugar_raw = person.get("sugar", "-")
        rbc_raw = person.get("RBC1", "-")
        wbc_raw = person.get("WBC1", "-")

        urine_data_config = [
            ("สี (Colour)", "Color", "Yellow, Pale Yellow", 
             lambda val: (str(val or "").strip().lower(), str(val or "").strip().lower() not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"])),
            ("น้ำตาล (Sugar)", "sugar", "Negative", interpret_sugar),
            ("โปรตีน (Albumin)", "Alb", "Negative, trace", interpret_alb),
            ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0", 
             lambda val: (str(val or "-"), not (5.0 <= get_float(None, {"val": val}) <= 8.0) if get_float(None, {"val": val}) is not None else False)),
            ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030", 
             lambda val: (str(val or "-"), not (1.003 <= get_float(None, {"val": val}) <= 1.030) if get_float(None, {"val": val}) is not None else False)),
            ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2 cell/HPF", interpret_rbc),
            ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5 cell/HPF", interpret_wbc),
            ("เซลล์เยื่อบุผิว (Squam.epit.)", "SQ-epi", "0 - 10 cell/HPF", 
             lambda val: (str(val or "-"), parse_range_or_number(str(val or ""))[1] is not None and parse_range_or_number(str(val or ""))[1] > 10)), # Assuming >10 is abnormal
            ("อื่นๆ", "ORTER", "-", lambda val: (str(val or "-"), not is_empty(val) and str(val).strip().lower() not in ["none", "-"])), # Flag if not empty/none
        ]

        urine_rows = []
        for label, col_name, norm_range, interpret_func in urine_data_config:
            raw_value = person.get(col_name, "")
            
            # interpret_func should return (display_string, is_abnormal_boolean)
            display_value, is_abnormal = interpret_func(raw_value)
            
            urine_rows.append([
                (label, is_abnormal), 
                (display_value, is_abnormal), 
                (norm_range, False) # Normal range is just text, not abnormal
            ])
        
        st.markdown(render_lab_table_html(["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows), unsafe_allow_html=True)
    
    with col_ua_right:
        st.markdown(render_section_header("สรุปและคำแนะนำ", "ผลตรวจปัสสาวะ"), unsafe_allow_html=True)
        urine_advice_text = advice_urine(sex, alb_raw, sugar_raw, rbc_raw, wbc_raw)
        
        urine_advice_html = f"""
        <div style="
            background-color: {'rgba(255, 215, 0, 0.15)' if urine_advice_text else 'rgba(200, 255, 200, 0.15)'};
            padding: 1rem 1.5rem;
            border-radius: 10px;
            font-size: 16px;
            line-height: 1.5;
            color: var(--text-color);
            margin-top: 1rem; /* Align with left column table */
            min-height: 250px; /* Ensure consistent height for visual balance */
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            {f"<div style='font-weight: bold;'>คำแนะนำ:</div><div>{urine_advice_text}</div>" if urine_advice_text else "ไม่มีคำแนะนำเพิ่มเติมจากผลตรวจปัสสาวะ"}
        </div>
        """
        st.markdown(urine_advice_html, unsafe_allow_html=True)
