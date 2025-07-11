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

# ==============================================================================
# 1. HELPER FUNCTIONS
# ==============================================================================

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return str(val).strip().lower() in ["", "-", "none", "nan", "null", "null"]

def get_float(col, person_data):
    """Safely get a float value from person data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def safe_text(val):
    """Helper to safely get text and handle empty values."""
    return "-" if is_empty(val) else str(val).strip()

# --- Date Normalization ---
def normalize_thai_date(date_str):
    """Parses various Thai date formats into a standard "D Month YYYY" format."""
    if is_empty(date_str): return "-"
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()
    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]: return s

    thai_months = {
        1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน", 5: "พฤษภาคม", 6: "มิถุนายน",
        7: "กรกฎาคม", 8: "สิงหาคม", 9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
    }
    thai_month_abbr = {
        "ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2,
        "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4, "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5,
        "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6, "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8,
        "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10, "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11,
        "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12
    }

    try:
        # Try parsing formats like DD/MM/YYYY, DD-MM-YYYY
        if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', s):
            day, month, year = map(int, re.split(r'[/|-]', s))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {thai_months[dt.month]} {dt.year + 543}"

        # Try parsing formats like "8 เมษายน 2565"
        match = re.match(r'^(?P<day>\d{1,2})\s*(?P<month>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match:
            day, month_str, year = match.groups()
            month_num = thai_month_abbr.get(month_str.strip().replace('.', ''))
            if month_num:
                dt = datetime(int(year) - 543, month_num, int(day))
                return f"{dt.day} {thai_months[dt.month]} {int(year)}"
    except Exception:
        pass

    # Fallback for other formats
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            year = parsed_dt.year
            if year > datetime.now().year + 50: year -= 543 # Convert BE to CE
            return f"{parsed_dt.day} {thai_months[parsed_dt.month]} {year + 543}"
    except Exception:
        return s # Return original if all parsing fails
    return s

# ==============================================================================
# 2. DATA LOADING
# ==============================================================================

@st.cache_data(ttl=600)
def load_sqlite_data():
    """Loads and preprocesses data from a SQLite database file on Google Drive."""
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

        # --- Data Cleaning ---
        df_loaded.columns = df_loaded.columns.str.strip()
        for col in ['เลขบัตรประชาชน', 'HN', 'ชื่อ-สกุล']:
            df_loaded[col] = df_loaded[col].astype(str).str.strip()
            if col == 'HN':
                 df_loaded[col] = df_loaded[col].str.replace(r'\.0$', '', regex=True)
        df_loaded['Year'] = pd.to_numeric(df_loaded['Year'], errors='coerce').astype('Int64')
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None, ""], pd.NA, inplace=True)
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return pd.DataFrame()

# ==============================================================================
# 3. HEALTH LOGIC & ADVICE FUNCTIONS
# ==============================================================================

def get_vitals_advice(bmi, sbp, dbp):
    """Provides combined advice for BMI and blood pressure."""
    bmi_text, bp_text = "", ""
    if bmi:
        if bmi > 30: bmi_text = "น้ำหนักเกินมาตรฐานมาก"
        elif bmi >= 25: bmi_text = "น้ำหนักเกินมาตรฐาน"
        elif bmi < 18.5: bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
        else: bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
    if sbp and dbp:
        if sbp >= 160 or dbp >= 100: bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
        elif sbp >= 140 or dbp >= 90: bp_text = "ความดันโลหิตอยู่ในระดับสูง"
        elif sbp >= 120 or dbp >= 80: bp_text = "ความดันโลหิตเริ่มสูง"

    if bmi_text and bp_text: return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
    if bmi_text and not "ปกติ" in bmi_text: return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    if bp_text: return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
    if bmi_text == "น้ำหนักอยู่ในเกณฑ์ปกติ": return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
    return ""

def get_fbs_advice(fbs):
    """Provides advice based on Fasting Blood Sugar (FBS) level."""
    if not fbs or fbs == 0: return ""
    if 100 <= fbs < 106: return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
    if 106 <= fbs < 126: return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
    if fbs >= 126: return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
    return ""

def get_kidney_advice(gfr):
    """Provides advice based on GFR."""
    if gfr and gfr < 60:
        return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
    return ""

def get_liver_advice(alp, sgot, sgpt):
    """Provides advice based on liver enzymes."""
    if (alp and alp > 120) or (sgot and sgot > 36) or (sgpt and sgpt > 41):
        return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    return ""

def get_uric_advice(uric):
    """Provides advice based on Uric Acid level."""
    if uric and uric > 7.2:
        return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
    return ""

def get_lipids_advice(chol, tgl, ldl):
    """Provides advice based on lipid profile."""
    if (chol and chol >= 250) or (tgl and tgl >= 250) or (ldl and ldl >= 180):
        return "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
    if (chol and chol > 200) or (tgl and tgl > 150) or (ldl and ldl > 160):
        return "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน และออกกำลังกายเพื่อควบคุมระดับไขมัน"
    return ""

def get_cbc_advice(hb, hct, wbc, plt, sex):
    """Provides advice based on Complete Blood Count (CBC) results."""
    advice = []
    hb_ref, hct_ref = (13, 39) if sex == "ชาย" else (12, 36)
    if hb and hb < hb_ref: advice.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    if hct and hct < hct_ref: advice.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    if wbc:
        if wbc < 4000: advice.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc > 10000: advice.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    if plt:
        if plt < 150000: advice.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt > 500000: advice.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")
    return " ".join(advice)

def get_hepatitis_b_advice(hbsag, hbsab, hbcab):
    """Provides advice based on Hepatitis B panel results."""
    hbsag, hbsab, hbcab = safe_text(hbsag).lower(), safe_text(hbsab).lower(), safe_text(hbcab).lower()
    if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี"
    if "positive" in hbsab: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
    if "positive" in hbcab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]):
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

def interpret_bp(sbp, dbp):
    """Interprets blood pressure levels."""
    if not sbp or not dbp or sbp == 0 or dbp == 0: return "-"
    if sbp >= 160 or dbp >= 100: return "ความดันสูง"
    if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
    if sbp < 120 and dbp < 80: return "ความดันปกติ"
    return "ความดันค่อนข้างสูง"

def interpret_cxr(val):
    """Interprets Chest X-ray results."""
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    """Determines the correct EKG column name based on the year."""
    if not year: return "EKG"
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    """Interprets EKG results."""
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

# ==============================================================================
# 4. UI RENDERING FUNCTIONS
# ==============================================================================

def render_main_css():
    """Injects custom CSS for styling the app, including Sarabun font."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

    /* Apply Sarabun to all major elements, including Streamlit-specific ones */
    html, body, div, span, applet, object, iframe,
    h1, h2, h3, h4, h5, h6, p, blockquote, pre,
    a, abbr, acronym, address, big, cite, code,
    del, dfn, em, img, ins, kbd, q, s, samp,
    small, strike, strong, sub, sup, tt, var,
    b, u, i, center,
    dl, dt, dd, ol, ul, li,
    fieldset, form, label, legend,
    table, caption, tbody, tfoot, thead, tr, th, td,
    article, aside, canvas, details, embed,
    figure, figcaption, footer, header, hgroup,
    menu, nav, output, ruby, section, summary,
    time, mark, audio, video, button, input, select, textarea,
    div[data-testid="stMarkdown"],
    div[data-testid="stInfo"],
    div[data-testid="stSuccess"],
    div[data-testid="stWarning"],
    div[data-testid="stError"] {
        font-family: 'Sarabun', sans-serif !important;
    }
    body { font-size: 14px !important; }
    .report-header-container h1 { font-size: 1.8rem !important; font-weight: bold; }
    .report-header-container h2 { font-size: 1.2rem !important; color: darkgrey; font-weight: bold; }
    .st-sidebar h3 { font-size: 18px !important; }
    .report-header-container * {
        line-height: 1.7 !important; 
        margin: 0.2rem 0 !important;
        padding: 0 !important;
    }
    .lab-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 14px; }
    .lab-table th, .lab-table td { padding: 2px; border: 1px solid transparent; text-align: center; }
    .lab-table th { font-weight: bold; background-color: var(--secondary-background-color); }
    .lab-abn { background-color: rgba(255, 64, 64, 0.25); }
    </style>
    """, unsafe_allow_html=True)

def render_section_header(title, subtitle=None):
    """Renders a styled section header."""
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    st.markdown(f"<div style='background-color:#1b5e20;color:white;text-align:center;padding:0.8rem 0.5rem;font-weight:bold;border-radius:8px;margin:2rem 0 1rem 0;font-size:14px;'>{full_title}</div>", unsafe_allow_html=True)

def render_lab_table(title, subtitle, headers, rows):
    """Generates and renders a generic lab results table."""
    render_section_header(title, subtitle)
    header_html = "".join(f"<th style='text-align: {'left' if i == 0 or i == 2 else 'center'};'>{h}</th>" for i, h in enumerate(headers))
    rows_html = ""
    for row_data in rows:
        is_abn = any(item[1] for item in row_data)
        row_class = "lab-abn" if is_abn else ""
        rows_html += f"<tr class='{row_class}'>"
        rows_html += f"<td style='text-align: left;'>{row_data[0][0]}</td>"
        rows_html += f"<td>{row_data[1][0]}</td>"
        rows_html += f"<td style='text-align: left;'>{row_data[2][0]}</td>"
        rows_html += "</tr>"

    st.markdown(f"""
    <table class='lab-table'>
        <colgroup><col style="width:40%;"><col style="width:25%;"><col style="width:35%;"></colgroup>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)

def render_summary_box(content, is_abnormal):
    """Renders a colored summary box for advice."""
    if not content or content == "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ":
        bg_color = "rgba(57, 255, 20, 0.2)" # Green
        content = "ผลการตรวจโดยรวมอยู่ในเกณฑ์ปกติ"
    else:
        bg_color = "rgba(255, 255, 0, 0.2)" # Yellow

    st.markdown(f"""
    <div style="background-color:{bg_color};padding:1rem 2.5rem;border-radius:10px;line-height:1.6;font-size:14px;margin-top:1rem;">
        {content}
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 5. MAIN APP LOGIC
# ==============================================================================

# --- App Setup ---
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
render_main_css()
df = load_sqlite_data()

# --- Sidebar for Search and Selection ---
with st.sidebar:
    st.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
    search_query = st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_query")
    
    if st.button("ค้นหา"):
        st.session_state.person_row = None # Reset on new search
        if search_query:
            search_term = search_query.strip()
            mask = (df["HN"] == search_term) if search_term.isdigit() else (df["ชื่อ-สกุล"] == search_term)
            st.session_state.search_result = df[mask]
            if st.session_state.search_result.empty:
                st.error("❌ ไม่พบข้อมูล")
        else:
            st.session_state.search_result = None

    if 'search_result' in st.session_state and not st.session_state.search_result.empty:
        results_df = st.session_state.search_result
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)
        
        available_years = sorted(results_df["Year"].dropna().unique(), reverse=True)
        selected_year = st.selectbox("📅 เลือกปี", available_years, format_func=lambda y: f"พ.ศ. {y}")

        if selected_year:
            exam_dates = sorted(results_df[results_df["Year"] == selected_year]["วันที่ตรวจ"].dropna().unique(), reverse=True)
            if exam_dates:
                selected_date = st.selectbox("🗓️ เลือกวันที่ตรวจ", exam_dates)
                person_row_df = results_df[(results_df["Year"] == selected_year) & (results_df["วันที่ตรวจ"] == selected_date)]
                if not person_row_df.empty:
                    st.session_state.person_row = person_row_df.iloc[0].to_dict()
            else:
                st.info("ไม่พบข้อมูลการตรวจสำหรับปีที่เลือก")
                st.session_state.person_row = None

# --- Main Panel for Health Report Display ---
if 'person_row' in st.session_state and st.session_state.person_row:
    person = st.session_state.person_row

    # --- 1. Report Header ---
    st.markdown(f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem;">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        <p><b>วันที่ตรวจ:</b> {person.get("วันที่ตรวจ", "-")}</p>
    </div>
    """, unsafe_allow_html=True)

    # --- 2. Vitals and Personal Info ---
    weight, height = get_float("น้ำหนัก", person), get_float("ส่วนสูง", person)
    sbp, dbp = get_float("SBP", person), get_float("DBP", person)
    bmi = (weight / ((height / 100) ** 2)) if weight and height else None
    bp_interp = interpret_bp(sbp, dbp)
    
    st.markdown(f"""
    <hr>
    <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:2rem;margin:1.5rem 0;text-align:center;line-height:1.6;">
        <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
        <div><b>อายุ:</b> {int(get_float('อายุ', person) or 0)} ปี</div>
        <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
        <div><b>HN:</b> {person.get('HN', '-')}</div>
        <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
    </div>
    <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:2rem;margin-bottom:1rem;text-align:center;">
        <div><b>น้ำหนัก:</b> {weight or '-'} กก.</div>
        <div><b>ส่วนสูง:</b> {height or '-'} ซม.</div>
        <div><b>รอบเอว:</b> {get_float('รอบเอว', person) or '-'} ซม.</div>
        <div><b>ความดัน:</b> {f'{int(sbp)}/{int(dbp)} ({bp_interp})' if sbp and dbp else '-'}</div>
        <div><b>ชีพจร:</b> {int(get_float('pulse', person) or 0)} ครั้ง/นาที</div>
    </div>
    <div style='text-align:center; margin-bottom:1rem;'><b>คำแนะนำเบื้องต้น:</b> {get_vitals_advice(bmi, sbp, dbp) or "-"}</div>
    """, unsafe_allow_html=True)

    # --- 3. Lab Results (CBC & Blood Chemistry) ---
    sex = person.get("เพศ", "ชาย")
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    
    def flag(val, low, high, higher_is_better=False):
        if val is None: return "-", False
        is_abn = (val < low if low is not None else False) if higher_is_better else (val < low if low is not None else False) or (val > high if high is not None else False)
        return f"{val:.1f}", is_abn

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", f"ชาย > 13, หญิง > 12 g/dl", hb_low, None),
        ("ฮีมาโตคริต (Hct)", "HCT", f"ชาย > 39%, หญิง > 36%", hct_low, None),
        ("เม็ดเลือดขาว (WBC)", "WBC (cumm)", "4,000-10,000 /cu.mm", 4000, 10000),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000-500,000", 150000, 500000),
    ]
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74-106 mg/dl", 74, 106),
        ("การทำงานของไต (Cr)", "Cr", "0.5-1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6-7.2 mg%", 2.6, 7.2),
        ("ไขมัน (CHOL)", "CHOL", "150-200 mg/dl", 150, 200),
        ("ไขมัน (TGL)", "TGL", "35-150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0-160 mg/dl", 0, 160),
        ("เอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("เอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
    ]

    col1, col2 = st.columns(2)
    with col1:
        cbc_rows = [[(label, False), flag(get_float(col, person), low, high), (norm, False)] for label, col, norm, low, high in cbc_config]
        render_lab_table("ผลตรวจความสมบูรณ์ของเลือด (CBC)", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows)
    with col2:
        blood_rows = [[(label, False), flag(get_float(col, person), low, high, opt[0] if opt else False), (norm, False)] for label, col, norm, low, high, *opt in blood_config]
        render_lab_table("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows)

    # --- 4. Overall Advice Section ---
    advice_items = {
        "น้ำตาล": get_fbs_advice(get_float("FBS", person)),
        "ไต": get_kidney_advice(get_float("GFR", person)),
        "ตับ": get_liver_advice(get_float("ALP", person), get_float("SGOT", person), get_float("SGPT", person)),
        "ไขมัน": get_lipids_advice(get_float("CHOL", person), get_float("TGL", person), get_float("LDL", person)),
        "กรดยูริก": get_uric_advice(get_float("Uric Acid", person)),
        "เลือด": get_cbc_advice(get_float("Hb(%)", person), get_float("HCT", person), get_float("WBC (cumm)", person), get_float("Plt (/mm)", person), sex),
    }
    final_advice = "<br>".join(f"<b>{cat}:</b> {adv}" for cat, adv in advice_items.items() if adv)
    render_summary_box(final_advice, bool(final_advice))

    # --- 5. Other Test Sections (Urine, Stool, X-ray, EKG, Hep) ---
    col3, col4 = st.columns(2)
    with col3:
        render_section_header("ผลตรวจปัสสาวะ (Urinalysis)")
        st.info("ส่วนนี้อยู่ระหว่างการพัฒนา") 
        render_section_header("ผลตรวจอุจจาระ (Stool Examination)")
        st.info("ส่วนนี้อยู่ระหว่างการพัฒนา") 

    with col4:
        render_section_header("ผลเอกซเรย์ (Chest X-ray)")
        cxr_col = f"CXR{str(person['Year'])[-2:]}" if person.get('Year') != datetime.now().year + 543 else "CXR"
        st.markdown(f"<div>{interpret_cxr(person.get(cxr_col, ''))}</div>", unsafe_allow_html=True)
        
        render_section_header("ผลคลื่นไฟฟ้าหัวใจ (EKG)")
        ekg_col = get_ekg_col_name(person.get('Year'))
        st.markdown(f"<div>{interpret_ekg(person.get(ekg_col, ''))}</div>", unsafe_allow_html=True)

    # --- 6. Doctor's Suggestion and Signature ---
    render_section_header("สรุปความเห็นของแพทย์")
    doctor_suggestion = person.get("DOCTER suggest", "")
    st.markdown(f"<div style='padding:1rem;background-color:rgba(255,255,255,0.05);border-radius:6px;'>{doctor_suggestion if not is_empty(doctor_suggestion) else '<i>ไม่มีคำแนะนำจากแพทย์</i>'}</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='margin-top:7rem;text-align:right;padding-right:1rem;'>
        <div style='display:inline-block;text-align:center;width:340px;'>
            <div style='border-bottom:1px dotted #ccc;margin-bottom:0.5rem;width:100%;'></div>
            <div style='white-space:nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style='white-space:nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
