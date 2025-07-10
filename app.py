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
        if re.match(r'^\d{1,2}[./-]\d{1,2}[./-]\d{4}$', s):
            s = s.replace('-', '/')
            day, month, year = map(int, s.split('/'))
            if year > 2500:
                year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"

        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {year}"
    except Exception:
        pass

    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            year = parsed_dt.year
            if year > 2500:
                year -= 543
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {year + 543}"
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
        padding: 0.4rem;
        font-weight: bold;
        border-radius: 8px;
        margin-top: 0.8rem;
        margin-bottom: 0.4rem;
        font-size: 11px;
    '>
        {full_title}
    </div>
    """

def render_lab_table_html(title, subtitle, headers, rows, table_class="lab-table"):
    header_html = render_section_header(title, subtitle)
    
    html_content = f"{header_html}<div class='{table_class}-container'><table class='{table_class}'>"
    html_content += """
        <colgroup>
            <col style="width: 45%;"> <col style="width: 15%;"> <col style="width: 40%;"> </colgroup>
    """
    html_content += "<thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 else ("left" if i == 2 else "center")
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = "lab-table-abn" if is_abn else "lab-table-row"
        
        html_content += f"<tr>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[0][0]}</td>"
        html_content += f"<td class='{row_class}'>{row[1][0]}</td>"
        html_content += f"<td class='{row_class}' style='text-align: left;'>{row[2][0]}</td>"
        html_content += f"</tr>"
    html_content += "</tbody></table></div>"
    return html_content

def interpret_bp(sbp, dbp):
    try:
        sbp = float(sbp)
        dbp = float(dbp)
        if sbp >= 140 or dbp >= 90:
            return "ความดันค่อนข้างสูง"
        return "ความดันปกติ"
    except:
        return "-"

def combined_health_advice(bmi, sbp, dbp):
    advice = []
    try:
        bmi_val = float(bmi)
        if bmi_val < 18.5:
            advice.append("น้ำหนักน้อยกว่ามาตรฐาน")
    except:
        pass

    bp_interp = interpret_bp(sbp, dbp)
    if bp_interp == "ความดันค่อนข้างสูง":
        advice.append("ความดันโลหิตเริ่มสูง")
        
    if not advice:
        return "น้ำหนักอยู่ในเกณฑ์ดีและความดันโลหิตปกติ ให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
        
    return " และ ".join(advice) + " แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"

# --- ⭐ ALL HELPER FUNCTIONS RESTORED ⭐ ---
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
    if is_empty(fbs_raw): return ""
    try:
        value = float(str(fbs_raw).replace(",", "").strip())
        if 100 <= value < 106: return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
        if 106 <= value < 126: return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
        if value >= 126: return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
        return ""
    except: return ""

def summarize_liver(alp_val, sgot_val, sgpt_val):
    try:
        if float(alp_val) > 120 or float(sgot_val) > 36 or float(sgpt_val) > 40:
            return "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย"
        return "ปกติ"
    except: return ""

def liver_advice(summary_text):
    if summary_text == "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย":
        return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
    return ""

def uric_acid_advice(value_raw):
    try:
        if float(value_raw) > 7.2:
            return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""
    except: return ""

def summarize_lipids(chol_raw, tgl_raw, ldl_raw):
    try:
        chol = float(str(chol_raw).replace(",", "").strip())
        tgl = float(str(tgl_raw).replace(",", "").strip())
        ldl = float(str(ldl_raw).replace(",", "").strip())
        if chol >= 250 or tgl >= 250 or ldl >= 180: return "ไขมันในเลือดสูง"
        if chol > 200 or tgl > 150 or ldl > 160: return "ไขมันในเลือดสูงเล็กน้อย"
        return "ปกติ"
    except: return ""

def lipids_advice(summary_text):
    if summary_text == "ไขมันในเลือดสูง":
        return "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
    if summary_text == "ไขมันในเลือดสูงเล็กน้อย":
        return "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน และออกกำลังกายเพื่อควบคุมระดับไขมัน"
    return ""

def cbc_advice(hb, hct, wbc, plt, sex="ชาย"):
    advice_parts = []
    try:
        if float(hb) < (13 if sex == "ชาย" else 12):
            advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
    except: pass
    try:
        if float(hct) < (39 if sex == "ชาย" else 36):
            advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")
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
        os.unlink(tmp_path)
        
        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['HN'] = df_loaded['HN'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, int)) else str(x)).str.strip()
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None], pd.NA, inplace=True)

        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return pd.DataFrame()

df = load_sqlite_data()

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td {
        font-family: 'Sarabun', sans-serif !important;
    }
    
    @media print {
        @page {
            size: A4;
            margin: 0.8cm;
        }

        body, .main {
            margin: 0 !important;
            padding: 0 !important;
        }

        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
            width: 100% !important;
        }

        [data-testid="stSidebar"], 
        header[data-testid="stHeader"] {
            display: none !important;
        }

        * {
            background: transparent !important;
            color: #000000 !important;
            box-shadow: none !important;
            text-shadow: none !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 1rem !important;
        }
        
        div[data-testid="stVerticalBlock"] > div[style*="flex:"] {
            padding: 0 0.25rem !important;
        }

        div, p, table, th, td {
            page-break-inside: avoid !important;
            margin: 0 !important;
            padding: 1.5px !important;
            line-height: 1.25 !important;
            font-size: 8.5pt !important;
        }
        
        h1, h2, .report-header-container p {
            text-align: center;
        }
        h1 { font-size: 14pt !important; margin-bottom: 2px !important; font-weight: bold;}
        h2 { font-size: 10pt !important; margin-bottom: 2px !important;}
        .report-header-container p { font-size: 8pt !important; line-height: 1.2 !important; margin-bottom: 1px !important;}

        .patient-info p {
            font-size: 9pt !important;
            text-align: left;
            margin-bottom: 3px !important;
        }
        .advice-box p { text-align: left !important; }

        hr { display: none !important; }
        
        .section-header, .advice-box, .lab-table-abn {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        .section-header { 
            background-color: #1b5e20 !important; 
            color: white !important; 
            border-radius: 6px;
            font-size: 9.5pt !important;
            padding: 3px !important;
            margin-top: 5px !important;
            margin-bottom: 3px !important;
        }
        .advice-box { 
            background-color: rgba(255, 255, 0, 0.25) !important; 
            padding: 4px !important; 
            border-radius: 6px; 
            margin-top: 5px !important; 
            border: 1px solid #ccc !important;
        }
        .lab-table-abn { 
            background-color: rgba(255, 192, 203, 0.7) !important; 
        }
    }
    </style>
""", unsafe_allow_html=True)

if 'current_search_term' not in st.session_state:
    st.session_state.current_search_term = ""
if 'search_results_df' not in st.session_state:
    st.session_state.search_results_df = None
if 'person_row' not in st.session_state:
    st.session_state.person_row = None

st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
with st.sidebar.form(key='search_form'):
    search_query = st.text_input("กรอก HN หรือ ชื่อ-สกุล", key="search_input")
    submitted = st.form_submit_button("ค้นหา")

if submitted:
    st.session_state.current_search_term = search_query
    keys_to_clear = ['search_results_df', 'person_row', 'selected_year', 'selected_date']
    for key in keys_to_clear:
        st.session_state.pop(key, None)

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
                available_dates = sorted(year_df["วันที่ตรวจ"].dropna().unique(), key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True) if pd.notna(x) else pd.Timestamp.min, reverse=True)
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
                    #print-btn { display: inline-flex; align-items: center; justify-content: center; font-weight: 400; padding: .25rem .75rem; border-radius: .5rem; min-height: 38.4px; margin: 0; line-height: 1.6; color: #31333F; width: 100%; user-select: none; background-color: #FFFFFF; border: 1px solid rgba(49, 51, 63, 0.2); box-sizing: border-box; cursor: pointer; }
                    #print-btn:hover { border: 1px solid #FF4B4B; color: #FF4B4B; }
                    </style></head><body>
                      <button id="print-btn">🖨️ พิมพ์รายงานนี้</button>
                      <script>
                        document.getElementById('print-btn').addEventListener('click', () => window.parent.print());
                      </script>
                    </body></html>"""
                components.html(print_button_html, height=40)

if not st.session_state.current_search_term:
    st.info("เริ่มต้นใช้งานโดยการค้นหา HN หรือ ชื่อ-สกุล จากเมนูด้านซ้าย")

if st.session_state.get('person_row'):
    person = st.session_state.person_row
    
    report_header_html = f"""
    <div class="report-header-container">
        <h1>รายงานผลการตรวจสุขภาพ</h1>
        <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        <p><b>วันที่ตรวจ:</b> {person.get("วันที่ตรวจ", "-")}</p>
    </div>"""
    st.markdown(report_header_html, unsafe_allow_html=True)
    
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    try:
        bmi_val = float(person.get("น้ำหนัก", 0)) / ((float(person.get("ส่วนสูง", 1)) / 100) ** 2)
    except:
        bmi_val = None

    bp_full = f"{sbp}/{dbp} ม.ม.ปรอท - {interpret_bp(sbp, dbp)}"
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="patient-info">
            <p><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</p>
            <p><b>น้ำหนัก:</b> {person.get('น้ำหนัก', '-')} กก.</p>
            <p><b>ความดันโลหิต:</b> {bp_full}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="patient-info">
            <p><b>อายุ:</b> {person.get('อายุ', '-')} ปี &nbsp;&nbsp;<b>เพศ:</b> {person.get('เพศ', '-')}</p>
            <p><b>ส่วนสูง:</b> {person.get('ส่วนสูง', '-')} ซม. &nbsp;&nbsp;<b>รอบเอว:</b> {person.get('รอบเอว', '-')} ซม.</p>
            <p><b>ชีพจร:</b> {person.get('pulse', '-')} ครั้ง/นาที</p>
        </div>
        """, unsafe_allow_html=True)

    advice_text = combined_health_advice(bmi_val, sbp, dbp)
    if advice_text:
        st.markdown(f"<div class='advice-box'><p><b>คำแนะนำ:</b> {advice_text}</p></div>", unsafe_allow_html=True)

    sex = str(person.get("เพศ", "")).strip()
    hb_low, hct_low = (13, 39) if sex == "ชาย" else (12, 36)

    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", f"> {hb_low} g/dl", hb_low, None),
        ("ฮีมาโตคริต (Hct)", "HCT", f"> {hct_low}%", hct_low, None),
        ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000", 4000, 10000),
        ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
        ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
        ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
        ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
        ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000", 150000, 500000),
    ]

    cbc_rows = [(label, get_float(col, person), norm, low, high) for label, col, norm, low, high in cbc_config]
    cbc_rows_display = [[(d[0], False), flag(d[1], d[3], d[4])[0], (d[2], False)] for d in cbc_rows]


    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
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
    
    blood_rows_data = []
    for label, col, norm, low, high, *opt in blood_config:
        higher = opt[0] if opt else False
        val = get_float(col, person)
        result_val, is_abn = flag(val, low, high, higher)
        blood_rows_data.append([(label, is_abn), (result_val, is_abn), (norm, is_abn)])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(render_lab_table_html("ผลตรวจ CBC (Complete Blood Count)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows_data[:len(cbc_rows)]), unsafe_allow_html=True)
    with col2:
        st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows_data), unsafe_allow_html=True)

    advice_list = []
    advice_list.append(kidney_advice_from_summary(kidney_summary_gfr_only(person.get("GFR", ""))))
    advice_list.append(fbs_advice(person.get("FBS", "")))
    advice_list.append(liver_advice(summarize_liver(person.get("ALP", ""), person.get("SGOT", ""), person.get("SGPT", ""))))
    advice_list.append(uric_acid_advice(person.get("Uric Acid", "")))
    advice_list.append(lipids_advice(summarize_lipids(person.get("CHOL", ""), person.get("TGL", ""), person.get("LDL", ""))))
    advice_list.append(cbc_advice(person.get("Hb(%)", ""), person.get("HCT", ""), person.get("WBC (cumm)", ""), person.get("Plt (/mm)", ""), sex=sex))
    
    final_advice_html = " ".join([adv for adv in advice_list if adv])
    if final_advice_html:
        st.markdown(f"<div class='advice-box'><p><b>อื่นๆ:</b> {final_advice_html}</p></div>", unsafe_allow_html=True)
        
    st.markdown(f"""
    <div style='margin-top: 2rem; text-align: right; padding-right: 1rem;'>
        <div style='display: inline-block; text-align: center; width: 250px;'>
            <div style='border-bottom: 1px dotted #000; margin-bottom: 0.5rem; width: 100%;'></div>
            <div style='white-space: nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style='white-space: nowrap;'>เลขที่ใบอนุญาต ว.26674</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
