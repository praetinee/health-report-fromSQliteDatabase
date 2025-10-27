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
import os
import json
from streamlit_js_eval import streamlit_js_eval

# --- START OF CHANGE: Import new authentication module ---
from auth import authentication_flow, pdpa_consent_page
# --- END OF CHANGE ---

# --- Import ฟังก์ชันจากไฟล์อื่น ---
from performance_tests import interpret_audiogram, interpret_lung_capacity, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
# --- START OF CHANGE: Import the new visualization function ---
from visualization import display_visualization_tab
# --- END OF CHANGE ---

# --- START OF CHANGE: Import the new admin panel ---
from admin_panel import display_admin_panel
# --- END OF CHANGE ---


# --- Helper Functions (ที่ยังคงใช้งาน) ---
def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
# ... (existing code ... no changes in this function) ...
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

THAI_MONTHS_GLOBAL = {1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน", 5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม", 9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"}
# ... (existing code ... no changes in this variable) ...
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {"ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2, "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4, "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6, "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8, "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10, "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12}

def normalize_thai_date(date_str):
    if is_empty(date_str): return pd.NA
# ... (existing code ... no changes in this function) ...
    except Exception: pass
    return pd.NA

def get_float(col, person_data):
    """Safely gets a float value from person_data dictionary."""
# ... (existing code ... no changes in this function) ...
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
    """Formats a lab value and flags it if it's abnormal."""
# ... (existing code ... no changes in this function) ...
    return formatted_val, is_abnormal

def render_section_header(title):
    """Renders a new, modern section header."""
# ... (existing code ... no changes in this function) ...
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table"):
    """Generates HTML for a lab result table with a new header style."""
# ... (existing code ... no changes in this function) ...
    html_content += "</tbody></table></div>"
    return html_content

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
# ... (existing code ... no changes in this function) ...
def safe_value(val):
    val = str(val or "").strip()
# ... (existing code ... no changes in this function) ...
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

def parse_range_or_number(val):
# ... (existing code ... no changes in this function) ...
    except: return None, None

def interpret_rbc(value):
# ... (existing code ... no changes in this function) ...
    return "พบเม็ดเลือดแดงในปัสสาววะ"

def interpret_wbc(value):
# ... (existing code ... no changes in this function) ...
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
# ... (existing code ... no changes in this function) ...
    return False

def render_urine_section(person_data, sex, year_selected):
    """Renders the urinalysis section and returns a summary."""
# ... (existing code ... no changes in this function) ...
    st.markdown(html_content, unsafe_allow_html=True)
    return any(not is_empty(val) for _, val, _ in urine_data)

def interpret_stool_exam(val):
    """Interprets stool examination results."""
# ... (existing code ... no changes in this function) ...
    return val
def interpret_stool_cs(value):
    """Interprets stool culture and sensitivity results."""
# ... (existing code ... no changes in this function) ...
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
    """Renders a self-contained HTML table for stool examination results."""
# ... (existing code ... no changes in this function) ...
    """
    return html_content

def get_ekg_col_name(year):
    """Gets the correct EKG column name based on the year."""
# ... (existing code ... no changes in this function) ...
    return "EKG" if year == datetime.now().year + 543 else f"EKG{str(year)[-2:]}"
def interpret_ekg(val):
    """Interprets EKG results."""
# ... (existing code ... no changes in this function) ...
    return val

# --- START OF FIX ---
def hepatitis_b_advice(hbsag, hbsab, hbcab):
# ... (existing code ... no changes in this function) ...
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"
# --- END OF FIX ---

# --- Data Loading ---
@st.cache_data(ttl=600)
# ... (existing code ... no changes in this function) ...
def load_sqlite_data():
    tmp_path = None
    try:
# ... (existing code ... no changes in this function) ...
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Data Availability Checkers ---
def has_basic_health_data(person_data):
# ... (existing code ... no changes in this function) ...
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_vision_data(person_data):
# ... (existing code ... no changes in this function) ...
    ]
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
# ... (existing code ... no changes in this function) ...
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
# ... (existing code ... no changes in this function) ...
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

# --- START OF CHANGE: Add check for visualization data ---
def has_visualization_data(history_df):
# ... (existing code ... no changes in this function) ...
    return history_df is not None and not history_df.empty
# --- END OF CHANGE ---

# --- UI and Report Rendering Functions ---
def interpret_bp(sbp, dbp):
# ... (existing code ... no changes in this function) ...
    except: return "-"
    
def interpret_cxr(val):
# ... (existing code ... no changes in this function) ...
    return val

# --- START OF CHANGE: New function to interpret BMI with updated terminology ---
def interpret_bmi(bmi):
# ... (existing code ... no changes in this function) ...
    return ""
# --- END OF CHANGE ---

# --- START OF CHANGE: New Header and Vitals Design ---
# --- THIS FUNCTION IS NOW GLOBAL (MOVED OUT OF main_app) ---
def display_common_header(person_data):
    """Displays the new report header with integrated personal info and vitals cards."""
    
    # --- Prepare data for display ---
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
        bp_val = f"{sbp_int}/{dbp_int}"
        bp_desc = interpret_bp(sbp_int, dbp_int)
    except: 
        bp_val = "-"
        bp_desc = "ไม่มีข้อมูล"
    
    try: pulse_val = f"{int(float(person_data.get('pulse', '-')))}"
    except: pulse_val = "-"

    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight}" if weight is not None else "-"
    height_val = f"{height}" if height is not None else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')}"

    # --- BMI Calculation and Interpretation ---
    bmi_val_str = "-"
    bmi_desc = ""
    if weight is not None and height is not None and height > 0:
        bmi = weight / ((height / 100) ** 2)
        bmi_val_str = f"{bmi:.1f} kg/m²"
        bmi_desc = interpret_bmi(bmi)


    # --- Render HTML ---
    # --- START OF CHANGE: Replaced multi-line f-string with string list concatenation ---
    html_lines = []
    html_lines.append('<div class="report-header">')
    html_lines.append('    <div class="header-left">')
    html_lines.append('        <h2>รายงานผลการตรวจสุขภาพ</h2>')
    html_lines.append('        <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>')
    html_lines.append('        <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>') # No longer causes parser error
    html_lines.append('    </div>')
    html_lines.append('    <div class="header-right">')
    html_lines.append('        <div class="info-card">')
    html_lines.append(f'            <div class="info-card-item"><span>ชื่อ-สกุล:</span> {name}</div>')
    html_lines.append(f'            <div class="info-card-item"><span>HN:</span> {hn}</div>')
    html_lines.append(f'            <div class="info-card-item"><span>อายุ:</span> {age} ปี</div>')
    html_lines.append(f'            <div class="info-card-item"><span>เพศ:</span> {sex}</div>')
    html_lines.append(f'            <div class="info-card-item"><span>หน่วยงาน:</span> {department}</div>')
    html_lines.append(f'            <div class="info-card-item"><span>วันที่ตรวจ:</span> {check_date}</div>')
    html_lines.append('        </div>')
    html_lines.append('    </div>')
    html_lines.append('</div>')

    html_lines.append('<div class="vitals-grid">')
    
    html_lines.append('    <div class="vital-card">')
    html_lines.append('        <div class="vital-icon">')
    html_lines.append('            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>')
    html_lines.append('        </div>')
    html_lines.append('        <div class="vital-data">')
    html_lines.append('            <span class="vital-label">น้ำหนัก / ส่วนสูง</span>')
    html_lines.append(f'            <span class="vital-value">{weight_val} kg / {height_val} cm</span>')
    html_lines.append(f'            <span class="vital-sub-value">BMI: {bmi_val_str} ({bmi_desc})</span>')
    html_lines.append('        </div>')
    html_lines.append('    </div>')
    
    html_lines.append('    <div class="vital-card">')
    html_lines.append('        <div class="vital-icon">')
    html_lines.append('            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>')
    html_lines.append('        </div>')
    html_lines.append('        <div class="vital-data">')
    html_lines.append('            <span class="vital-label">รอบเอว</span>')
    html_lines.append(f'            <span class="vital-value">{waist_val} cm</span>')
    html_lines.append('        </div>')
    html_lines.append('    </div>')

    html_lines.append('    <div class="vital-card">')
    html_lines.append('        <div class="vital-icon">')
    html_lines.append('            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>')
    html_lines.append('        </div>')
    html_lines.append('        <div class="vital-data">')
    html_lines.append('            <span class="vital-label">ความดัน (mmHg)</span>')
    html_lines.append(f'            <span class="vital-value">{bp_val}</span>')
    html_lines.append(f'            <span class="vital-sub-value">{bp_desc}</span>')
    html_lines.append('        </div>')
    html_lines.append('    </div>')

    html_lines.append('    <div class="vital-card">')
    html_lines.append('        <div class="vital-icon">')
    html_lines.append('            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>')
    html_lines.append('        </div>')
    html_lines.append('        <div class="vital-data">')
    html_lines.append('            <span class="vital-label">ชีพจร (BPM)</span>')
    html_lines.append(f'            <span class="vital-value">{pulse_val}</span>')
    html_lines.append('        </div>')
    html_lines.append('    </div>')
    
    html_lines.append('</div>')
    
    html_content = "\n".join(html_lines)
    st.markdown(html_content, unsafe_allow_html=True)
    # --- END OF CHANGE ---

# --- END OF CHANGE ---

# --- START OF CHANGE: New Centralized and Adaptive CSS ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        /* --- Color Variables for Consistency --- */
        :root {
            --abnormal-bg-color: rgba(220, 53, 69, 0.1);
            --abnormal-text-color: #C53030;
            --normal-bg-color: rgba(40, 167, 69, 0.1);
            --normal-text-color: #1E4620;
            --warning-bg-color: rgba(255, 193, 7, 0.1);
            --neutral-bg-color: rgba(108, 117, 125, 0.1);
            --neutral-text-color: #4A5568;
        }
        
        /* --- General & Typography --- */
        html, body, [class*="st-"], .st-emotion-cache-10trblm, h1, h2, h3, h4, h5, h6 {
            font-family: 'Sarabun', sans-serif !important; 
        }
        .main {
             background-color: var(--background-color);
             color: var(--text-color);
        }
        h4 { /* For section headers */
            font-size: 1.25rem;
            font-weight: 600;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            margin-top: 40px;
            margin-bottom: 24px;
            color: var(--text-color);
        }
        h5.section-subtitle {
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--text-color);
            opacity: 0.7;
        }

        /* --- Sidebar Controls --- */
        [data-testid="stSidebar"] {
            background-color: var(--secondary-background-color);
        }
        [data-testid="stSidebar"] .stTextInput input {
            border-color: var(--border-color);
        }
        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 1rem;
        }
        /* --- START OF FIX --- */
        .stButton>button {
            background-color: #00796B; /* Use the same teal as section headers */
            color: white !important;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            width: 100%;
            padding: 0.5rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            transition: background-color 0.2s, transform 0.2s;
        }
        .stButton>button:hover {
            background-color: #00695C; /* A slightly darker teal for hover */
            color: white !important;
            transform: translateY(-1px);
        }
        .stButton>button:disabled {
            background-color: #BDBDBD;
            color: #757575 !important;
            opacity: 1;
            border: none;
            box-shadow: none;
            cursor: not-allowed;
        }
        /* --- END OF FIX --- */


        /* --- New Report Header & Vitals --- */
        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2rem;
        }
        .header-left h2 { color: var(--text-color); font-size: 2rem; margin-bottom: 0.25rem;}
        .header-left p { color: var(--text-color); opacity: 0.7; margin: 0; }
        .info-card {
            background-color: var(--secondary-background-color);
            border-radius: 8px;
            padding: 1rem;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem 1.5rem;
            min-width: 400px;
            border: 1px solid var(--border-color);
        }
        .info-card-item { font-size: 0.9rem; color: var(--text-color); }
        .info-card-item span { color: var(--text-color); opacity: 0.7; margin-right: 8px; }

        .vitals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .vital-card {
            background-color: var(--secondary-background-color);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        .vital-icon svg { color: var(--primary-color); }
        .vital-data { display: flex; flex-direction: column; }
        .vital-label { font-size: 0.8rem; color: var(--text-color); opacity: 0.7; }
        .vital-value { font-size: 1.2rem; font-weight: 700; color: var(--text-color); line-height: 1.2; white-space: nowrap;}
        .vital-sub-value { font-size: 0.8rem; color: var(--text-color); opacity: 0.6; }

        /* --- Styled Tabs --- */
        div[data-testid="stTabs"] {
            border-bottom: 2px solid var(--border-color);
        }
        div[data-testid="stTabs"] button {
            background-color: transparent;
            color: var(--text-color);
            opacity: 0.7;
            border-radius: 8px 8px 0 0;
            margin: 0;
            padding: 10px 20px;
            border: none;
            border-bottom: 2px solid transparent;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background-color: var(--secondary-background-color);
            color: var(--primary-color);
            font-weight: 600;
            opacity: 1;
            border: 2px solid var(--border-color);
            border-bottom: 2px solid var(--secondary-background-color);
            margin-bottom: -2px;
        }
        
        /* --- Containers for sections --- */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div.st-emotion-cache-1jicfl2.e1f1d6gn3 > div {
             background-color: var(--secondary-background-color);
             border: 1px solid var(--border-color);
             border-radius: 12px;
             padding: 24px;
             box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }

        /* --- Lab Result Tables --- */
        .table-container { overflow-x: auto; }
        .lab-table, .info-detail-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .lab-table th, .lab-table td, .info-detail-table th, .info-detail-table td {
            padding: 12px 15px;
            border: 1px solid transparent;
            border-bottom: 1px solid var(--border-color);
        }
        .lab-table th, .info-detail-table th {
            font-weight: 600;
            text-align: left;
            color: var(--text-color);
            opacity: 0.7;
        }
        .lab-table thead th {
            background-color: rgba(128, 128, 128, 0.1);
        }
        .lab-table td:nth-child(2) {
            text-align: center;
        }
        .lab-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
        .lab-table .abnormal-row {
            background-color: var(--abnormal-bg-color);
            color: var(--abnormal-text-color);
            font-weight: 600;
        }
        .info-detail-table th { width: 35%; }
        
        /* --- Recommendation Container --- */
        .recommendation-container {
            border-left: 5px solid var(--primary-color);
            padding: 1.5rem;
            border-radius: 0 8px 8px 0;
            background-color: var(--background-color);
        }
        .recommendation-container ul { padding-left: 20px; }
        .recommendation-container li { margin-bottom: 0.5rem; }

        /* --- Performance Report Specific Styles --- */
        .status-summary-card {
            padding: 1rem; 
            border-radius: 8px; 
            text-align: center; 
            height: 100%;
        }
        .status-normal-bg { background-color: var(--normal-bg-color); }
        .status-abnormal-bg { background-color: var(--abnormal-bg-color); }
        .status-warning-bg { background-color: var(--warning-bg-color); }
        .status-neutral-bg { background-color: var(--neutral-bg-color); }

        .status-summary-card p {
            margin: 0;
            color: var(--text-color);
        }
        .vision-table {
            width: 100%; border-collapse: collapse; font-size: 14px;
            margin-top: 1.5rem;
        }
        .vision-table th, .vision-table td {
            border: 1px solid var(--border-color); padding: 10px;
            text-align: left; vertical-align: middle;
        }
        .vision-table th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; }
        .vision-table .result-cell { text-align: center; width: 180px; }
        .vision-result {
            display: inline-block; padding: 6px 16px; border-radius: 16px;
            font-size: 13px; font-weight: bold; border: 1px solid transparent;
        }
        /* --- START OF FIX --- */
        .vision-normal { background-color: var(--normal-bg-color); color: #2E7D32; }
        .vision-abnormal { background-color: var(--abnormal-bg-color); color: #C62828; }
        .vision-not-tested { background-color: var(--neutral-bg-color); color: #455A64; }
        /* --- END OF FIX --- */
        .styled-df-table {
            width: 100%; border-collapse: collapse; font-family: 'Sarabun', sans-serif !important;
            font-size: 14px;
        }
        .styled-df-table th, .styled-df-table td { border: 1px solid var(--border-color); padding: 10px; text-align: left; }
        .styled-df-table thead th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; text-align: center; vertical-align: middle; }
        .styled-df-table tbody td { text-align: center; }
        .styled-df-table tbody td:first-child { text-align: left; }
        .styled-df-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
        .hearing-table { table-layout: fixed; }
        
        /* --- START OF FIX --- */
        .custom-advice-box {
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            border: 1px solid transparent;
            font-weight: 600; /* Make text bolder */
        }
        .immune-box {
            background-color: var(--normal-bg-color);
            color: #2E7D32; /* Darker green for better contrast */
            border-color: rgba(40, 167, 69, 0.2);
        }
        .no-immune-box {
            background-color: var(--abnormal-bg-color);
            color: #C62828; /* Darker red for better contrast */
            border-color: rgba(220, 53, 69, 0.2);
        }
        .warning-box {
            background-color: var(--warning-bg-color);
            color: #AF6C00; /* Darker yellow/orange for better contrast */
            border-color: rgba(255, 193, 7, 0.2);
        }
        /* --- END OF FIX --- */
    </style>
    """, unsafe_allow_html=True)
# --- END OF CHANGE ---

# --- START OF CHANGE: MOVED 'render_vision_details_table' TO GLOBAL SCOPE ---
def render_vision_details_table(person_data):
    """
# ... (existing code ... no changes in this function) ...
    html_parts.append("</tbody></table>")
    return "".join(html_parts)
# --- END OF CHANGE ---

# --- START OF CHANGE: MOVED 'display_performance_report_hearing' TO GLOBAL SCOPE ---
def display_performance_report_hearing(person_data, all_person_history_df):
    render_section_header("รายงานผลการตรวจสมรรถภาพการได้ยิน (Audiometry Report)")
    
# ... (existing code ... no changes in this function) ...
        """, unsafe_allow_html=True)
# --- END OF CHANGE ---

# --- START OF CHANGE: MOVED 'display_performance_report_lung' TO GLOBAL SCOPE ---
def display_performance_report_lung(person_data):
    render_section_header("รายงานผลการตรวจสมรรถภาพปอด (Spirometry Report)")
# ... (existing code ... no changes in this function) ...
        """, unsafe_allow_html=True)
# --- END OF CHANGE ---

# --- START OF CHANGE: MOVED 'display_performance_report_vision' TO GLOBAL SCOPE ---
def display_performance_report_vision(person_data):
    render_section_header("รายงานผลการตรวจสมรรถภาพการมองเห็น (Vision Test Report)")
    
# ... (existing code ... no changes in this function) ...
    st.markdown(render_vision_details_table(person_data), unsafe_allow_html=True)
# --- END OF CHANGE ---

# --- START OF CHANGE: MOVED 'display_performance_report' (wrapper) TO GLOBAL SCOPE ---
def display_performance_report(person_data, report_type, all_person_history_df=None):
    with st.container(border=True):
# ... (existing code ... no changes in this function) ...
        elif report_type == 'hearing':
            display_performance_report_hearing(person_data, all_person_history_df)
# --- END OF CHANGE ---

# --- START OF CHANGE: MOVED 'display_main_report' TO GLOBAL SCOPE ---
def display_main_report(person_data, all_person_history_df):
    person = person_data
# ... (existing code ... no changes in this function) ...
        st.markdown(f"<div class='recommendation-container'>{recommendations_html}</div>", unsafe_allow_html=True)
# --- END OF CHANGE ---


# --- START OF CHANGE: Main application logic is wrapped in a function ---
def main_app(df):
# ... (existing code ... no changes in this function) ...
    """
    This function contains the main application logic for displaying health reports.
    It's called after the user has successfully logged in and accepted the PDPA consent.
# ... (existing code ... no changes in this function) ...
    """
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

    inject_custom_css()

    # --- START OF CHANGE: Logic to handle data for the logged-in user ---
# ... (existing code ... no changes in this function) ...
    if 'user_hn' not in st.session_state:
        st.error("เกิดข้อผิดพลาด: ไม่พบข้อมูลผู้ใช้")
        st.stop()

    user_hn = st.session_state['user_hn']
# ... (existing code ... no changes in this function) ...
    st.session_state['search_result'] = results_df
    # --- END OF CHANGE ---

    def handle_year_change():
# ... (existing code ... no changes in this function) ...
        st.session_state.pop("selected_row_found", None)

    # Initialize states for the logged-in user
# ... (existing code ... no changes in this function) ...
    if 'print_performance_trigger' not in st.session_state: st.session_state.print_performance_trigger = False

    with st.sidebar:
        # --- START OF CHANGE: Display user info instead of search ---
# ... (existing code ... no changes in this function) ...
        st.markdown(f"**HN:** {st.session_state.get('user_hn', '')}")
        st.markdown("---")
        # --- END OF CHANGE ---
        
        if not results_df.empty:
# ... (existing code ... no changes in this function) ...
                     st.session_state.pop("selected_row_found", None)
        
        st.markdown("---")
# ... (existing code ... no changes in this function) ...
            st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True, disabled=True)

        # Add logout button
# ... (existing code ... no changes in this function) ...
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # --- Main Page ---
# ... (existing code ... no changes in this function) ...
        if "person_row" not in st.session_state or not st.session_state.get("selected_row_found", False):
            st.info("กรุณาเลือกปีที่ต้องการดูผลตรวจจากเมนูด้านข้าง")
        else:
            person_data = st.session_state.person_row
# ... (existing code ... no changes in this function) ...
                        display_main_report(person_data, all_person_history_df)

        # --- Print Logic ---
        if st.session_state.get("print_trigger", False):
# ... (existing code ... no changes in this function) ...
            st.session_state.print_trigger = False

        if st.session_state.get("print_performance_trigger", False):
# ... (existing code ... no changes in this function) ...
            st.session_state.print_performance_trigger = False

# --- Main Logic to control page flow ---
if 'authenticated' not in st.session_state:
# ... (existing code ... no changes in this function) ...
    st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state:
    st.session_state['pdpa_accepted'] = False
# --- START OF CHANGE: Add is_admin check ---
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False
# --- END OF CHANGE ---

# --- START OF CHANGE: Load data before authentication check ---
df = load_sqlite_data()
# ... (existing code ... no changes in this function) ...
    st.error("ไม่สามารถโหลดฐานข้อมูลได้ กรุณาลองอีกครั้งในภายหลัง")
    st.stop()

if not st.session_state['authenticated']:
    authentication_flow(df)
# --- START OF CHANGE: Reroute logic for Admin vs User ---
elif st.session_state['is_admin']:
    # Admin skips PDPA and goes to admin panel
    display_admin_panel(df)
elif not st.session_state['pdpa_accepted']:
    # Regular user must accept PDPA
    pdpa_consent_page()
else:
    # Regular user, PDPA accepted, show main app
    main_app(df)
# --- END OF CHANGE ---

