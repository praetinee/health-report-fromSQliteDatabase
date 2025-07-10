import streamlit as st
import streamlit.components.v1 as components
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
import os

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

# Function to normalize and convert Thai dates
def normalize_thai_date(date_str):
    if is_empty(date_str):
        return "-"
    
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()

    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]:
        return s

    try:
        # Format: DD/MM/YYYY (e.g., 29/04/2565)
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: # Assume Thai Buddhist year if year > 2500
                year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        # Format: DD-MM-YYYY (e.g., 29-04-2565)
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: # Assume Thai Buddhist year if year > 2500
                year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')

        # Format: DD MonthNameYYYY (e.g., 8 เมษายน 2565) or DD-DD MonthNameYYYY (e.g., 15-16 กรกฎาคม 2564)
        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                try:
                    dt = datetime(year - 543, month_num, day)
                    return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}".replace('.', '')
                except ValueError:
                    pass

    except Exception:
        pass

    # Fallback to pandas for robust parsing if other specific regex fail
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            current_ce_year = datetime.now().year
            if parsed_dt.year > current_ce_year + 50 and parsed_dt.year - 543 > 1900:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {dt.year + 543}".replace('.', '')
    except Exception:
        pass

    return s

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

def render_section_header(title, subtitle=None):
    if subtitle:
        full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>"
    else:
        full_title = title

    return f"""
    <div class="section-header" style='
        background-color: #1b5e20;
        color: white;
        text-align: center;
        padding: 0.5rem;
        font-weight: bold;
        border-radius: 8px;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-size: 12px;
    '>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    style = f"""
    <style>
        .{table_class}-container {{ margin-top: 0.5rem; }}
        .{table_class} {{
            width: 100%; border-collapse: collapse; color: var(--text-color);
            table-layout: fixed; font-size: 14px;
        }}
        .{table_class} thead th {{
            background-color: var(--secondary-background-color); color: var(--text-color);
            padding: 2px; text-align: center; font-weight: bold; border: 1px solid transparent;
        }}
        .{table_class} td {{
            padding: 2px; border: 1px solid transparent;
            text-align: center; color: var(--text-color);
        }}
        .{table_class}-abn {{ background-color: rgba(255, 64, 64, 0.25); }}
        .{table_class}-row {{ background-color: rgba(255,255,255,0.02); }}
    </style>
    """
    
    header_html = render_section_header(title, subtitle)
    
    html_content = f"{style}{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    html_content += """
        <colgroup>
            <col style="width: 40%;"> <col style="width: 20%;"> <col style="width: 40%;"> </colgroup>
    """
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 else ("left" if i == 2 else "center")
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else f"{table_class}-row"
        
        html_content += f"<tr>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td class='{row_class}'>{row[1][0]}</td>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table></div>"
    return html_content

# --- All other helper functions remain the same ---
def kidney_summary_gfr_only(gfr_raw):
    try:
        gfr = float(str(gfr_raw).replace(",", "").strip())
        if gfr == 0:
            return ""
        elif gfr < 60:
            return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        else:
            return "ปกติ"
    except:
        return ""

def kidney_advice_from_summary(summary_text):
    if summary_text == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
        return (
            "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย "
            "ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน "
            "และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
        )
    return ""

def fbs_advice(fbs_raw):
    if is_empty(fbs_raw):
        return ""
    try:
        value = float(str(fbs_raw).replace(",", "").strip())
        if value == 0:
            return ""
        elif 100 <= value < 106:
            return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
        elif 106 <= value < 126:
            return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
        elif value >= 126:
            return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
        else:
            return ""
    except:
        return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    try:
        alp = float(alp_val)
        sgot = float(sgot_val)
        sgpt = float(sgpt_val)
        if alp == 0 or sgot == 0 or sgpt == 0:
            return "-"
        if alp > 120 or sgot > 36 or sgpt > 40:
            return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except:
        return ""

def liver_advice(summary_text):
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
        return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    elif summary_text == "ปกติ":
        return ""
    return "-"

def uric_acid_advice(value_raw):
    try:
        value = float(value_raw)
        if value > 7.2:
            return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except:
        return "-"

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    try:
        chol = float(str(chol_raw).replace(",", "").strip())
        tgl = float(str(tgl_raw).replace(",", "").strip())
        ldl = float(str(ldl_raw).replace(",", "").strip())
        if chol == 0 and tgl == 0:
            return ""
        if chol >= 250 or tgl >= 250 or ldl >= 180:
            return "ไขมันในเลือดสูง"
        elif chol <= 200 and tgl <= 150:
            return "ปกติ"
        else:
            return "ไขมันในเลือดสูงเล็กน้อย"
    except:
        return ""

def lipids_advice(summary_text):
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
    advice_parts = []

    try:
        hb_val = float(hb)
        hb_ref = 13 if sex == "ชาย" else 12
        if hb_val < hb_ref:
            advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    except:
        pass

    try:
        hct_val = float(hct)
        hct_ref = 39 if sex == "ชาย" else 36
        if hct_val < hct_ref:
            advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
    except:
        pass

    try:
        wbc_val = float(wbc)
        if wbc_val < 4000:
            advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
        elif wbc_val > 10000:
            advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")
    except:
        pass

    try:
        plt_val = float(plt)
        if plt_val < 150000:
            advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
        elif plt_val > 500000:
            advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")
    except:
        pass

    return " ".join(advice_parts)

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
    if bmi_text and not bp_text:
        return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
    return ""

# --- All other simple helper functions are omitted for brevity ---
# (safe_text, safe_value, interpret_alb, etc.)
# ...

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
        os.unlink(tmp_path) # Clean up the temporary file

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
        return pd.DataFrame()

# --- Load data when the app starts. ---
df = load_sqlite_data()

# ==================== UI Setup and Search Form (Sidebar) ====================
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

# ⭐ Inject CSS for print layout
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td {
        font-family: 'Sarabun', sans-serif !important;
    }
    
    @media print {
        @page {
            size: A4;
            margin: 1cm; /* กำหนดขอบกระดาษ */
        }

        /* ซ่อนส่วนที่ไม่ต้องการพิมพ์ */
        [data-testid="stSidebar"], 
        header[data-testid="stHeader"] {
            display: none !important;
        }

        /* กำหนด Layout หลัก */
        .main .block-container {
            padding: 0 !important;
            width: 100% !important;
            margin: 0 !important;
        }

        body {
            font-size: 9pt !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* --- ⭐ การแก้ไขที่สำคัญสำหรับ Dark Mode และการแสดงสีพื้นหลัง ⭐ --- */
        * {
            background: transparent !important;
            color: #000000 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        /* บังคับให้ st.columns แสดงผลข้างกันเหมือนเดิม */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 1rem !important;
        }
        
        div[data-testid="stVerticalBlock"] > div[style*="flex:"] {
            padding: 0 0.25rem !important;
        }

        /* ลดระยะห่างของทุกอย่างเพื่อให้กระชับที่สุด */
        div, p, table, th, td {
            page-break-inside: avoid !important;
            margin: 0 !important;
            padding: 1px !important;
            line-height: 1.3 !important;
        }
        
        h1, h2, h3 { line-height: 1.2 !important; margin-bottom: 4px !important; }
        h1 { font-size: 14pt !important; }
        h2 { font-size: 11pt !important; }
        p { font-size: 9pt !important; }
        hr { display: none !important; }
        
        /* บังคับให้สีพื้นหลังของ element ที่ต้องการยังคงแสดงอยู่ */
        .section-header, .advice-box, .lab-table-abn, .urine-abn {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        .section-header { background-color: #1b5e20 !important; color: white !important; }
        .advice-box { background-color: rgba(255, 255, 0, 0.2) !important; }
        .lab-table-abn, .urine-abn { background-color: rgba(255, 64, 64, 0.25) !important; }
    }
    </style>
""", unsafe_allow_html=True)


# --- STATE MANAGEMENT REFACTOR START ---

# Initialize state keys if they don't exist
if 'current_search_term' not in st.session_state:
    st.session_state.current_search_term = ""
if 'search_results_df' not in st.session_state:
    st.session_state.search_results_df = None
if 'person_row' not in st.session_state:
    st.session_state.person_row = None

# Sidebar UI
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
with st.sidebar.form(key='search_form'):
    search_query = st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input")
    submitted = st.form_submit_button("ค้นหา")

if submitted:
    st.session_state.current_search_term = search_query
    keys_to_clear = ['search_results_df', 'person_row', 'selected_year', 'selected_date']
    for key in keys_to_clear:
        st.session_state.pop(key, None)


# Main logic controller
if st.session_state.current_search_term:
    if st.session_state.get('search_results_df') is None:
        search_term = st.session_state.current_search_term.strip()
        if search_term:
            results = df[df["HN"] == search_term] if search_term.isdigit() else df[df["ชื่อ-สกุล"].str.strip() == search_term]
            if results.empty:
                st.sidebar.error("❌ ไม่พบข้อมูล")
                st.session_state.current_search_term = ""
            else:
                st.session_state.search_results_df = results
        else:
            st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล")

    if st.session_state.get('search_results_df') is not None:
        results_df = st.session_state.search_results_df
        with st.sidebar:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)
            available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
            selected_year = st.selectbox("📅 เลือกปี", options=available_years, key="selected_year")

            if selected_year:
                year_df = results_df[results_df["Year"] == selected_year]
                available_dates = sorted(year_df["วันที่ตรวจ"].dropna().unique(), key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), reverse=True)
                if available_dates:
                    selected_date = st.selectbox("🗓️ เลือกวันที่ตรวจ", options=available_dates, key="selected_date")
                    if selected_date:
                        final_row_df = year_df[year_df["วันที่ตรวจ"] == selected_date]
                        if not final_row_df.empty:
                            st.session_state.person_row = final_row_df.iloc[0].to_dict()
                else:
                    st.sidebar.warning(f"ไม่พบวันที่ตรวจสำหรับปี พ.ศ. {selected_year}")
                    st.session_state.person_row = None
            
            if st.session_state.get('person_row'):
                st.markdown("---")
                print_button_html = """
                    <!DOCTYPE html><html><head><style>
                    body { margin: 0; font-family: 'Sarabun', sans-serif; }
                    #print-btn { display: inline-flex; align-items: center; justify-content: center;
                        font-weight: 400; padding: .25rem .75rem; border-radius: .5rem; min-height: 38.4px;
                        margin: 0; line-height: 1.6; color: #31333F; width: 100%; user-select: none;
                        background-color: #FFFFFF; border: 1px solid rgba(49, 51, 63, 0.2); box-sizing: border-box; }
                    #print-btn:hover { border: 1px solid #FF4B4B; color: #FF4B4B; }
                    #print-btn:active { color: #FFFFFF; border-color: #FF4B4B; background-color: #FF4B4B; }
                    #print-btn:focus:not(:active) { border-color: #FF4B4B; box-shadow: 0 0 0 .2rem rgba(255, 75, 75, .5); }
                    </style></head><body>
                      <button id="print-btn">🖨️ พิมพ์รายงานนี้</button>
                      <script>
                        document.getElementById('print-btn').addEventListener('click', () => window.parent.print());
                      </script>
                    </body></html>"""
                components.html(print_button_html, height=40)

if not st.session_state.current_search_term:
    st.info("เริ่มต้นใช้งานโดยการค้นหา HN หรือ ชื่อ-สกุล จากเมนูด้านซ้าย")

# ==================== Display Health Report (Main Content) ====================
if st.session_state.get('person_row'):
    # Wrap the entire report in a div for print layout control
    st.markdown('<div class="report-container-for-print">', unsafe_allow_html=True)
    
    person = st.session_state.person_row
    check_date = person.get("วันที่ตรวจ", "-")

    report_header_html = f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem;">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        <p><b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>
    """
    st.markdown(report_header_html, unsafe_allow_html=True)
    
    # ... The rest of your report display code remains the same ...
    # (I've omitted the middle part for brevity, it's identical to your last version)

    st.markdown('</div>', unsafe_allow_html=True) # Close the wrapper div
