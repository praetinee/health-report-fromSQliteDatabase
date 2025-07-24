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
import performance_tests # Ensure this file exists
import os

# --- Helper Functions (Existing) ---
def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

THAI_MONTHS_GLOBAL = {1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน", 5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม", 9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {"ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2, "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4, "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6, "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8, "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10, "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12}

def normalize_thai_date(date_str):
    if is_empty(date_str): return pd.NA
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()
    if s.lower() in ["ไม่ตรวจ", "นัดทีหลัง", "ไม่ได้เข้ารับการตรวจ", ""]: return pd.NA
    try:
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"
        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})\.?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}"
    except Exception: pass
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            if parsed_dt.year > datetime.now().year + 50:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}"
    except Exception: pass
    return pd.NA

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_sqlite_data():
    tmp_path = None
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
        def clean_hn(hn_val):
            if pd.isna(hn_val): return ""
            s_val = str(hn_val).strip()
            return s_val[:-2] if s_val.endswith('.0') else s_val
        df_loaded['HN'] = df_loaded['HN'].apply(clean_hn)
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- NEW: Data Availability Checkers ---
def has_basic_health_data(person_data):
    """Check for a few key indicators of a basic health checkup."""
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_vision_data(person_data):
    """Check for vision test data."""
    return not is_empty(person_data.get('สายตา')) or not is_empty(person_data.get('ตาบอดสี'))

def has_hearing_data(person_data):
    """Check for hearing test data."""
    return not is_empty(person_data.get('การได้ยิน'))

def has_lung_data(person_data):
    """Check for lung capacity test data."""
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)


# --- UI and Report Rendering Functions (Including refactored headers) ---
# ... (All other interpretation and rendering functions like interpret_bp, render_lab_table_html, etc., remain the same)
# ... (You can copy them from your existing file)
# The following are the NEW or HEAVILY MODIFIED functions for the UI
def interpret_bp(sbp, dbp):
    """Interprets blood pressure readings."""
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"
    except: return "-"

def combined_health_advice(bmi, sbp, dbp):
    """Generates combined advice for BMI and blood pressure."""
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
    
def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def display_report_title(person_data):
    """Displays the main title and hospital info."""
    check_date = person_data.get("วันที่ตรวจ", "ไม่มีข้อมูล")
    st.markdown(f"""<div class="report-header-container" style="text-align: center; margin-bottom: 1rem; margin-top: 1rem;">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p><b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>""", unsafe_allow_html=True)

def display_personal_info(person_data):
    """Displays the patient's personal information."""
    st.markdown(f"""<div class="personal-info-container">
        <hr style="margin-top: 0.5rem; margin-bottom: 1rem;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; margin-bottom: 1rem; text-align: center; line-height: 1.8;">
            <div><b>ชื่อ-สกุล:</b> {person_data.get('ชื่อ-สกุล', '-')}</div>
            <div><b>อายุ:</b> {str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')} ปี</div>
            <div><b>เพศ:</b> {person_data.get('เพศ', '-')}</div>
            <div><b>HN:</b> {str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')}</div>
            <div><b>หน่วยงาน:</b> {person_data.get('หน่วยงาน', '-')}</div>
        </div>
    </div>""", unsafe_allow_html=True)

def display_vitals_summary(person_data):
    """Displays vital signs and the combined BMI/BP advice."""
    try:
        weight_val = float(str(person_data.get("น้ำหนัก", "-")).replace("กก.", "").strip())
        height_val = float(str(person_data.get("ส่วนสูง", "-")).replace("ซม.", "").strip())
        bmi_val = weight_val / ((height_val / 100) ** 2) if height_val > 0 else None
    except: bmi_val = None
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except: sbp_int = dbp_int = None; bp_val = "-"
    bp_desc = interpret_bp(sbp_int, dbp_int) if sbp_int is not None else "-"
    bp_full = f"{bp_val} - {bp_desc}" if bp_desc != "-" else bp_val
    try: pulse_val = int(float(person_data.get("pulse", "-")))
    except: pulse_val = None
    pulse = f"{pulse_val} ครั้ง/นาที" if pulse_val is not None else "-"
    weight_display = f"{person_data.get('น้ำหนัก', '-')} กก." if not is_empty(person_data.get('น้ำหนัก', '-')) else "-"
    height_display = f"{person_data.get('ส่วนสูง', '-')} ซม." if not is_empty(person_data.get('ส่วนสูง', '-')) else "-"
    waist_display = f"{person_data.get('รอบเอว', '-')} ซม." if not is_empty(person_data.get('รอบเอว', '-')) else "-"
    summary_advice = html.escape(combined_health_advice(bmi_val, person_data.get("SBP", ""), person_data.get("DBP", "")))

    st.markdown(f"""
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; margin-bottom: 1.5rem; text-align: center; line-height: 1.8;">
            <div><b>น้ำหนัก:</b> {weight_display}</div>
            <div><b>ส่วนสูง:</b> {height_display}</div>
            <div><b>รอบเอว:</b> {waist_display}</div>
            <div><b>ความดันโลหิต:</b> {bp_full}</div>
            <div><b>ชีพจร:</b> {pulse}</div>
        </div>
        {f"<div style='margin-top: 1rem; text-align: center;'><b>คำแนะนำ:</b> {summary_advice}</div>" if summary_advice else ""}
    """, unsafe_allow_html=True)

def display_performance_report_lung(person_data):
    """Displays the lung capacity report."""
    st.header("รายงานผลการตรวจสมรรถภาพปอด (Spirometry Report)")
    lung_summary, lung_advice, lung_raw_values = performance_tests.interpret_lung_capacity(person_data)
    if lung_summary == "ไม่ได้เข้ารับการตรวจ":
        st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพปอดในปีนี้")
        return
    # ... (The rest of the function remains the same as the last version)
    st.markdown("<h5><b>สรุปผลการตรวจที่สำคัญ</b></h5>", unsafe_allow_html=True)
    def format_val(key):
        val = lung_raw_values.get(key)
        return f"{val:.1f}" if val is not None else "-"
    col1, col2, col3 = st.columns(3)
    col1.metric(label="FVC (% เทียบค่ามาตรฐาน)", value=format_val('FVC %'), help="ความจุของปอดเมื่อหายใจออกเต็มที่ (ควร > 80%)")
    col2.metric(label="FEV1 (% เทียบค่ามาตรฐาน)", value=format_val('FEV1 %'), help="ปริมาตรอากาศที่หายใจออกในวินาทีแรก (ควร > 80%)")
    col3.metric(label="FEV1/FVC Ratio (%)", value=format_val('FEV1/FVC %'), help="สัดส่วนของ FEV1 ต่อ FVC (ควร > 70%)")
    st.markdown("<hr>", unsafe_allow_html=True)
    res_col1, res_col2 = st.columns([2, 3])
    with res_col1:
        st.markdown("<h5><b>ผลการแปลความหมาย</b></h5>", unsafe_allow_html=True)
        if "ปกติ" in lung_summary: bg_color = "background-color: #2e7d32; color: white;"
        elif "ไม่ได้" in lung_summary or "คลาดเคลื่อน" in lung_summary: bg_color = "background-color: #616161; color: white;"
        else: bg_color = "background-color: #c62828; color: white;"
        st.markdown(f'<div style="padding: 1rem; border-radius: 8px; {bg_color} text-align: center;"><h4 style="color: white; margin: 0; font-weight: bold;">{lung_summary}</h4></div>', unsafe_allow_html=True)
        st.markdown("<br><h5><b>คำแนะนำ</b></h5>", unsafe_allow_html=True)
        st.info(lung_advice or "ไม่มีคำแนะนำเพิ่มเติม")
        st.markdown("<h5><b>ผลเอกซเรย์ทรวงอก</b></h5>", unsafe_allow_html=True)
        selected_year = person_data.get("Year")
        cxr_result_interpreted = "ไม่มีข้อมูล"
        if selected_year:
            cxr_col_name = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            cxr_result_interpreted = interpret_cxr(person_data.get(cxr_col_name, ''))
        st.markdown(f'<div style="font-size: 14px; padding: 0.5rem; background-color: rgba(255,255,255,0.05); border-radius: 4px;">{cxr_result_interpreted}</div>', unsafe_allow_html=True)
    with res_col2:
        st.markdown("<h5><b>ตารางแสดงผลโดยละเอียด</b></h5>", unsafe_allow_html=True)
        def format_detail_val(key, format_spec, unit=""):
            val = lung_raw_values.get(key)
            if val is not None and isinstance(val, (int, float)): return f"{val:{format_spec}}{unit}"
            return "-"
        detail_data = {"การทดสอบ (Test)": ["FVC", "FEV1", "FEV1/FVC"],"ค่าที่วัดได้ (Actual)": [format_detail_val('FVC', '.2f', ' L'), format_detail_val('FEV1', '.2f', ' L'),format_detail_val('FEV1/FVC %', '.1f', ' %')],"ค่ามาตรฐาน (Predicted)": [format_detail_val('FVC predic', '.2f', ' L'), format_detail_val('FEV1 predic', '.2f', ' L'),format_detail_val('FEV1/FVC % pre', '.1f', ' %')],"% เทียบค่ามาตรฐาน (% Pred)": [format_detail_val('FVC %', '.1f', ' %'), format_detail_val('FEV1 %', '.1f', ' %'), "-"]}
        df_details = pd.DataFrame(detail_data)
        st.dataframe(df_details, use_container_width=True, hide_index=True)


def display_performance_report(person_data, report_type):
    """Displays various performance test reports."""
    if report_type == 'lung':
        display_performance_report_lung(person_data)
    elif report_type == 'vision':
        st.header("รายงานผลการตรวจสมรรถภาพการมองเห็น (Vision)")
        vision_summary, color_summary, vision_advice = performance_tests.interpret_vision(person_data.get('สายตา'), person_data.get('ตาบอดสี'))
        if vision_summary == "ไม่ได้เข้ารับการตรวจ" and color_summary == "ไม่ได้เข้ารับการตรวจ":
            st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพการมองเห็นในปีนี้")
            return
        v_col1, v_col2 = st.columns(2)
        v_col1.metric("ผลตรวจสายตา", vision_summary)
        v_col2.metric("ผลตรวจตาบอดสี", color_summary)
        if vision_advice: st.info(f"**คำแนะนำ:** {vision_advice}")
    elif report_type == 'hearing':
        st.header("รายงานผลการตรวจสมรรถภาพการได้ยิน (Hearing)")
        hearing_summary, hearing_advice = performance_tests.interpret_hearing(person_data.get('การได้ยิน'))
        if hearing_summary == "ไม่ได้เข้ารับการตรวจ":
            st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพการได้ยินในปีนี้")
            return
        h_col1, h_col2 = st.columns(2)
        h_col1.metric("สรุปผล", hearing_summary)
        if hearing_advice: h_col2.info(f"**คำแนะนำ:** {hearing_advice}")

def display_main_report(person_data):
    """Displays the main health report with all lab sections."""
    # This function remains unchanged. You can copy it from your existing file.
    # It includes rendering for CBC, Blood Chemistry, Urinalysis, Stool, etc.
    st.write("Main Report Display Function Goes Here (Content Unchanged)")


# --- Main Application Logic ---
# Load data once
df = load_sqlite_data()
if df is None:
    st.stop()

# Page config and styles
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, div, span, p, td, th, li, ul, ol, table, h1, h2, h3, h4, h5, h6, label, button, input, select, option, .stButton>button, .stTextInput>div>div>input, .stSelectbox>div>div>div { font-family: 'Sarabun', sans-serif !important; }
    div[data-testid="stSidebarNav"], button[data-testid="stSidebarNavCollapseButton"] { display: none; }
    .stDownloadButton button { width: 100%; }
</style>""", unsafe_allow_html=True)

# Callbacks for search and year selection
def perform_search():
    st.session_state.search_query = st.session_state.search_input
    st.session_state.selected_year = None
    st.session_state.selected_date = None
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    # Set default page to main report, will be re-evaluated
    st.session_state.page = 'main_report' 
    raw_search_term = st.session_state.search_query.strip()
    search_term = re.sub(r'\s+', ' ', raw_search_term)
    if search_term:
        results_df = df[df["HN"] == search_term if search_term.isdigit() else df["ชื่อ-สกุล"] == search_term].copy()
        st.session_state.search_result = results_df if not results_df.empty else pd.DataFrame()
    else:
        st.session_state.search_result = pd.DataFrame()

def handle_year_change():
    st.session_state.selected_year = st.session_state.year_select
    st.session_state.selected_date = None
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    st.session_state.page = 'main_report'

# Initialize session state
if 'search_query' not in st.session_state: st.session_state.search_query = ""
if 'search_input' not in st.session_state: st.session_state.search_input = ""
if 'search_result' not in st.session_state: st.session_state.search_result = pd.DataFrame()
if 'selected_year' not in st.session_state: st.session_state.selected_year = None
if 'selected_date' not in st.session_state: st.session_state.selected_date = None
if 'page' not in st.session_state: st.session_state.page = 'main_report'

# --- UI Layout for Search and Filters ---
st.subheader("ค้นหาและเลือกผลตรวจ")
menu_cols = st.columns([3, 1, 2, 2])
with menu_cols[0]:
    st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input", on_change=perform_search, placeholder="HN หรือ ชื่อ-สกุล", label_visibility="collapsed")
with menu_cols[1]:
    st.button("ค้นหา", use_container_width=True, on_click=perform_search)

# ... (The logic for selecting year and date remains the same)
# You can copy it from your existing file.
results_df = st.session_state.search_result
if not results_df.empty:
    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    if available_years:
        if st.session_state.selected_year not in available_years:
            st.session_state.selected_year = available_years[0]
        year_idx = available_years.index(st.session_state.selected_year)
        with menu_cols[2]:
            st.selectbox("ปี พ.ศ.", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change, label_visibility="collapsed")
        person_year_df = results_df[results_df["Year"] == st.session_state.selected_year]
        date_map_df = pd.DataFrame({'original_date': person_year_df['วันที่ตรวจ'], 'normalized_date': person_year_df['วันที่ตรวจ'].apply(normalize_thai_date)}).drop_duplicates().dropna(subset=['normalized_date'])
        valid_exam_dates_normalized = sorted(date_map_df['normalized_date'].unique().tolist(), reverse=True)
        with menu_cols[3]:
            if valid_exam_dates_normalized:
                if st.session_state.get("selected_date") not in valid_exam_dates_normalized:
                    st.session_state.selected_date = valid_exam_dates_normalized[0]
                date_idx = valid_exam_dates_normalized.index(st.session_state.selected_date)
                selected_normalized_date = st.selectbox("วันที่ตรวจ", options=valid_exam_dates_normalized, index=date_idx, key=f"date_select_{st.session_state.selected_year}", label_visibility="collapsed")
                st.session_state.selected_date = selected_normalized_date
                original_date_to_find = date_map_df[date_map_df['normalized_date'] == selected_normalized_date]['original_date'].iloc[0]
                final_row_df = person_year_df[person_year_df["วันที่ตรวจ"] == original_date_to_find]
                if not final_row_df.empty:
                    st.session_state.person_row = final_row_df.iloc[0].to_dict()
                    st.session_state.selected_row_found = True
            else:
                 st.session_state.pop("person_row", None); st.session_state.pop("selected_row_found", None); st.session_state.pop("selected_date", None)


st.markdown("<hr>", unsafe_allow_html=True)

# --- NEW: Main Report Display Logic ---
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    person_data = st.session_state.person_row
    
    # 1. Check which tests are available for the selected year
    available_tests = {
        'main': has_basic_health_data(person_data),
        'vision': has_vision_data(person_data),
        'hearing': has_hearing_data(person_data),
        'lung': has_lung_data(person_data)
    }
    
    # 2. Dynamically create buttons based on available data
    button_map = {
        'main': 'สุขภาพพื้นฐาน',
        'vision': 'สมรรถภาพการมองเห็น',
        'hearing': 'สมรรถภาพการได้ยิน',
        'lung': 'ความจุปอด'
    }
    
    active_buttons = {k: v for k, v in button_map.items() if available_tests[k]}
    
    if not active_buttons:
        display_report_title(person_data)
        display_personal_info(person_data)
        st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับวันที่และปีที่เลือก")
    else:
        # If the current page is not available, default to the first available one
        if st.session_state.page not in active_buttons:
            st.session_state.page = list(active_buttons.keys())[0]
            
        # Display buttons
        btn_cols = st.columns(len(active_buttons))
        for i, (page_key, page_title) in enumerate(active_buttons.items()):
            with btn_cols[i]:
                if st.button(page_title, use_container_width=True):
                    st.session_state.page = page_key
                    st.rerun()

        # 3. Display headers and the selected page content
        display_report_title(person_data)
        display_personal_info(person_data)
        
        page_to_show = st.session_state.page
        
        if page_to_show == 'main':
            display_vitals_summary(person_data)
            # You need to re-add your full display_main_report function here
            # For now, I'll put a placeholder
            st.success("Displaying Main Health Report...")
            # display_main_report(person_data) 
        
        elif page_to_show == 'vision':
            display_performance_report(person_data, 'vision')
        
        elif page_to_show == 'hearing':
            display_performance_report(person_data, 'hearing')
            
        elif page_to_show == 'lung':
            display_performance_report(person_data, 'lung')

else:
    st.info("กรอก ชื่อ-สกุล หรือ HN เพื่อค้นหาผลการตรวจสุขภาพ")
