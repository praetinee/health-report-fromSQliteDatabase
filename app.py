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
from streamlit_js_eval import streamlit_js_eval # <-- 1. เพิ่มการ import

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

# (*** โค้ดส่วนของฟังก์ชัน Helper ทั้งหมดจะเหมือนเดิม... ผมจึงขอย่อไว้เพื่อความกระชับ ***)
# ...
# ... (วางฟังก์ชัน Helper ทั้งหมดที่นี่)
# ...

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
# --- (จบส่วนย่อ) ---

@st.cache_data(ttl=600)
def load_sqlite_data():
    # ... โค้ดส่วนนี้เหมือนเดิม ...
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


# --- Load data when the app starts. ---
df = load_sqlite_data()

# ==================== UI Setup and Search Form (Sidebar) ====================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# Inject custom CSS for font, size control, and printing
st.markdown("""
    <style>
    /* Import Sarabun font from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');

    /*
      Apply Sarabun font to all common text elements. This approach is
      more specific and avoids overriding the font for special elements
      like Streamlit's internal icons (e.g., the sidebar collapse button).
    */
    body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td,
    div[data-testid="stMarkdown"],
    div[data-testid="stInfo"],
    div[data-testid="stSuccess"],
    div[data-testid="stWarning"],
    div[data-testid="stError"] {
        font-family: 'Sarabun', sans-serif !important;
    }

    /* Set a base font size for the body */
    body {
        font-size: 14px !important;
    }

    /* --- Styles for Printing --- */
    @media print {
        /* ซ่อนแถบเมนูด้านข้างทั้งหมด (ซึ่งจะซ่อนปุ่มค้นหาและปุ่มพิมพ์ไปด้วย) */
        [data-testid="stSidebar"] {
            display: none;
        }

        /* ทำให้เนื้อหารายงานหลักขยายเต็มความกว้างของหน้ากระดาษ */
        section[data-testid="stAppViewContainer"] {
            left: 0 !important;
            width: 100% !important;
            padding: 1rem !important; /* เพิ่มระยะขอบเล็กน้อย */
        }

        /* ปรับสไตล์พื้นหลังและเงาเพื่อประหยัดหมึกและให้อ่านง่าย */
        body, div, section, header, table, tr, td, th {
            background-color: #FFFFFF !important; /* พื้นหลังขาว */
            color: #000000 !important; /* ตัวอักษรดำ */
            box-shadow: none !important; /* เอาเงาออก */
            border: 1px solid #dee2e6 !important; /* เพิ่มเส้นขอบบางๆ ให้ตาราง */
        }
        
        .report-header-container, .report-header-container h2 {
            color: #000000 !important;
        }
    }

    </style>
""", unsafe_allow_html=True)

# Main search form moved to sidebar
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
search_query = st.sidebar.text_input("กรอก HN หรือ ชื่อ-สกุล")
submitted_sidebar = st.sidebar.button("ค้นหา")


if submitted_sidebar:
    # ... โค้ดส่วนนี้เหมือนเดิม ...
    st.session_state.pop("search_result", None)
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    st.session_state.pop("selected_year_from_sidebar", None)
    st.session_state.pop("selected_exam_date_from_sidebar", None)
    st.session_state.pop("last_selected_year_sidebar", None)
    st.session_state.pop("last_selected_exam_date_sidebar", None)
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
            first_available_year = sorted(query_df["Year"].dropna().unique().astype(int), reverse=True)[0]
            first_person_year_df = query_df[
                (query_df["Year"] == first_available_year) & (query_df["HN"] == query_df.iloc[0]["HN"])
            ].drop_duplicates(subset=["HN", "วันที่ตรวจ"]).sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)
            if not first_person_year_df.empty:
                st.session_state["person_row"] = first_person_year_df.iloc[0].to_dict()
                st.session_state["selected_row_found"] = True
                st.session_state["selected_year_from_sidebar"] = first_available_year
                st.session_state["selected_exam_date_from_sidebar"] = first_person_year_df.iloc[0]["วันที่ตรวจ"]
                st.session_state["last_selected_year_sidebar"] = first_available_year
                st.session_state["last_selected_exam_date_sidebar"] = first_person_year_df.iloc[0]["วันที่ตรวจ"]
            else:
                st.session_state.pop("person_row", None)
                st.session_state.pop("selected_row_found", None)
                st.sidebar.error("❌ พบข้อมูลแต่ไม่สามารถแสดงผลได้ กรุณาลองใหม่")
    else:
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล เพื่อค้นหา")


if "search_result" in st.session_state:
    # ... โค้ดส่วนนี้เหมือนเดิม ...
    results_df = st.session_state["search_result"]
    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)
        # ... (โค้ด selectbox ปี และ วันที่ เหมือนเดิม) ...

        # <-- 2. เพิ่มปุ่มพิมพ์ไว้ที่นี่
        st.markdown("---")
        if st.button("🖨️ พิมพ์รายงานสุขภาพ", use_container_width=True):
            # เรียกใช้ JavaScript `window.print()`
            streamlit_js_eval(js_code="window.print();")


# ==================== Display Health Report (Main Content) ====================
if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
    #
    # *** โค้ดทั้งหมดในการแสดงผลรายงานจะเหมือนเดิมทุกประการ ***
    #
    person = st.session_state["person_row"]
    # ... (วางโค้ดส่วนแสดงผลทั้งหมดที่นี่) ...
    # ...
    # ...
    # สิ้นสุดส่วนแสดงผล
