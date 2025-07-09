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
from streamlit_js_eval import streamlit_js_eval

def is_empty(val):
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# --- Global Helper Functions: START ---
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
            day, month, year = map(int, s.split('/'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')
        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}".replace('.', '')
    except Exception: pass
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            current_ce_year = datetime.now().year
            if parsed_dt.year > current_ce_year + 50 and parsed_dt.year - 543 > 1900:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}".replace('.', '')
    except Exception: pass
    return s

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
    return f"<div style='background-color: #1b5e20; color: white; text-align: center; padding: 0.8rem 0.5rem; font-weight: bold; border-radius: 8px; margin-top: 2rem; margin-bottom: 1rem; font-size: 14px;'>{full_title}</div>"

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    style = f"""<style>
        .{table_class}-container {{ margin-top: 1rem; }}
        .{table_class} {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 14px; }}
        .{table_class} thead th {{ background-color: var(--secondary-background-color); padding: 2px; text-align: center; font-weight: bold; border: 1px solid transparent; }}
        .{table_class} td {{ padding: 2px; border: 1px solid transparent; text-align: center; }}
        .{table_class}-abn {{ background-color: rgba(255, 64, 64, 0.25); }}
        .{table_class}-row {{ background-color: rgba(255,255,255,0.02); }}
    </style>"""
    header_html = render_section_header(title, subtitle)
    html_content = f"{style}{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    html_content += "<colgroup><col style='width: 33.33%;'><col style='width: 33.33%;'><col style='width: 33.33%;'></colgroup>"
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

# --- (Other helper functions like kidney_summary, fbs_advice, etc. are here) ---
# ... (For brevity, assuming all other helper functions are correctly placed here) ...

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
    div[data-testid="stMarkdown"], div[data-testid="stInfo"], div[data-testid="stSuccess"],
    div[data-testid="stWarning"], div[data-testid="stError"] {
        font-family: 'Sarabun', sans-serif !important;
    }
    body { font-size: 14px !important; }
    .report-header-container h1 { font-size: 1.8rem !important; font-weight: bold; }
    .report-header-container h2 { font-size: 1.2rem !important; color: darkgrey; font-weight: bold; }
    .st-sidebar h3 { font-size: 18px !important; }
    .report-header-container * { line-height: 1.7 !important; margin: 0.2rem 0 !important; padding: 0 !important; }
    @media print {
        [data-testid="stSidebar"] { display: none; }
        section[data-testid="stAppViewContainer"] { left: 0 !important; width: 100% !important; padding: 1rem !important; }
        body, div, section, header, table, tr, td, th {
            background-color: #FFFFFF !important; color: #000000 !important;
            box-shadow: none !important; border: 1px solid #dee2e6 !important;
        }
        .report-header-container, .report-header-container h2 { color: #000000 !important; }
    }
    </style>
""", unsafe_allow_html=True)

# ==================== Search Logic Block (REVISED) ====================
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
st.sidebar.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input_val")

if st.sidebar.button("ค้นหา", key="search_button"):
    search_term = st.session_state.get("search_input_val", "").strip()
    keys_to_clear = [
        "search_result", "person_row", "selected_row_found",
        "selected_year_from_sidebar", "selected_exam_date_from_sidebar",
        "last_selected_year_sidebar", "last_selected_exam_date_sidebar"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    if not search_term:
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล เพื่อค้นหา")
    else:
        query_df = df.copy()
        if search_term.isdigit():
            query_df = query_df[query_df["HN"] == search_term]
        else:
            query_df = query_df[query_df["ชื่อ-สกุล"].str.strip() == search_term]

        if query_df.empty:
            st.sidebar.error("❌ ไม่พบข้อมูล กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง")
        else:
            st.session_state["search_result"] = query_df
            try:
                first_available_year = sorted(query_df["Year"].dropna().unique().astype(int), reverse=True)[0]
                first_person_year_df = query_df[
                    (query_df["Year"] == first_available_year) &
                    (query_df["HN"] == query_df.iloc[0]["HN"])
                ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)

                if not first_person_year_df.empty:
                    st.session_state["person_row"] = first_person_year_df.iloc[0].to_dict()
                    st.session_state["selected_row_found"] = True
                    st.session_state["selected_year_from_sidebar"] = first_available_year
                    st.session_state["selected_exam_date_from_sidebar"] = first_person_year_df.iloc[0]["วันที่ตรวจ"]
                    st.session_state["last_selected_year_sidebar"] = first_available_year
                    st.session_state["last_selected_exam_date_sidebar"] = first_person_year_df.iloc[0]["วันที่ตรวจ"]
                else:
                    st.sidebar.error("❌ พบข้อมูลแต่ไม่สามารถแสดงผลสำหรับปีล่าสุดได้")
            except Exception as e:
                st.sidebar.error(f"เกิดข้อผิดพลาดในการประมวลผลข้อมูล: {e}")

# ==================== SELECT YEAR AND EXAM DATE IN SIDEBAR ====================
if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]
    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)

        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        current_selected_year_index = 0
        if "selected_year_from_sidebar" in st.session_state and st.session_state["selected_year_from_sidebar"] in available_years:
            current_selected_year_index = available_years.index(st.session_state["selected_year_from_sidebar"])
        
        selected_year = st.selectbox(
            "📅 เลือกปีที่ต้องการดูผลตรวจรายงาน",
            options=available_years,
            index=current_selected_year_index,
            format_func=lambda y: f"พ.ศ. {y}",
            key="year_select_sidebar"
        )
        st.session_state.selected_year_from_sidebar = selected_year
        
        person_year_df = results_df[
            (results_df["Year"] == selected_year) & (results_df["HN"] == results_df.iloc[0]["HN"])
        ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)
        
        exam_dates_options = person_year_df["วันที่ตรวจ"].dropna().unique().tolist()
        if exam_dates_options:
            selected_exam_date = st.selectbox("🗓️ เลือกวันที่ตรวจ", options=exam_dates_options, key="exam_date_select_sidebar")
            st.session_state.selected_exam_date_from_sidebar = selected_exam_date
            
            # Update person_row based on selection
            selected_row_df = person_year_df[person_year_df["วันที่ตรวจ"] == selected_exam_date]
            if not selected_row_df.empty:
                st.session_state["person_row"] = selected_row_df.iloc[0].to_dict()
                st.session_state["selected_row_found"] = True

        st.markdown("---")
        if st.button("🖨️ พิมพ์รายงานสุขภาพ", use_container_width=True):
            streamlit_js_eval(js_code="window.print();")

# ==================== Display Health Report (Main Content) ====================
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    person = st.session_state["person_row"]
    # ... (โค้ดส่วนแสดงผลทั้งหมดจะเหมือนเดิมทุกประการ) ...
    # ... (วางโค้ดส่วนแสดงผลทั้งหมดที่นี่) ...
    st.markdown(f"<h1>รายงานผลการตรวจสุขภาพ</h1>", unsafe_allow_html=True) # Example
    # ... The rest of your display code ...
