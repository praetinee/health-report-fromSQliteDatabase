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
    return "พบเม็ดเลือดแดงในปัสสาวะ"

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
    
# ... (existing code ... no changes in this function) ...
    """, unsafe_allow_html=True)

# --- END OF CHANGE ---

# --- START OF CHANGE: New Centralized and Adaptive CSS ---
def inject_custom_css():
# ... (existing code ... no changes in this function) ...
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
