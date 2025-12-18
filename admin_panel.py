import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- Import LINE Manager Function ---
# (สำคัญ: ต้องมีไฟล์ line_register.py อยู่ในโฟลเดอร์เดียวกัน)
try:
    from line_register import render_admin_line_manager
except ImportError:
    def render_admin_line_manager():
        st.error("ไม่พบไฟล์ line_register.py กรุณาสร้างไฟล์นี้ก่อน")

# --- Helper Functions (Shared Logic) ---
def is_empty(val):
    if val is None: return True
    if isinstance(val, str) and val.strip() == "": return True
    if isinstance(val, (int, float)) and pd.isna(val): return True
    return False

def normalize_name(name):
    if not isinstance(name, str): return str(name)
    return " ".join(name.split())

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .main-header { text-align: center; color: #2C3E50; margin-bottom: 20px; }
        .sub-header { color: #34495E; border-bottom: 2px solid #3498DB; padding-bottom: 10px; margin-top: 30px; margin-bottom: 15px; }
        .card { background-color: #F8F9F9; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .stMetric { background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #F0F2F6; border-radius: 5px; color: #555; }
        .stTabs [aria-selected="true"] { background-color: #3498DB; color: white; }
        .sidebar-title { font-size: 1.2rem; font-weight: bold; color: #2C3E50; margin-bottom: 1rem; }
        @media print { .no-print, .stSidebar, header, footer { display: none !important; } .card { box-shadow: none; border: 1px solid #ddd; } }
    </style>
    """, unsafe_allow_html=True)

# --- Data Checking Helper Functions ---
def has_basic_health_data(row):
    columns = ['Weight', 'Height', 'BMI', 'Waist', 'SBP', 'DBP', 'Pulse']
    return any(not is_empty(row.get(col)) for col in columns)

def has_vision_data(row):
    columns = ['V_R_Far', 'V_L_Far', 'V_R_Near', 'V_L_Near', 'Color_Blind']
    return any(not is_empty(row.get(col)) for col in columns)

def has_hearing_data(row):
    freqs = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
    columns = [f'R_{f}' for f in freqs] + [f'L_{f}' for f in freqs]
    return any(not is_empty(row.get(col)) for col in columns)

def has_lung_data(row):
    columns = ['FVC_Predicted', 'FVC_Actual', 'FVC_Percent', 'FEV1_Predicted', 'FEV1_Actual', 'FEV1_Percent', 'FEV1_FVC_Ratio']
    return any(not is_empty(row.get(col)) for col in columns)

def has_visualization_data(df):
    return not df.empty and len(df) > 1

# --- Display Functions ---
def display_common_header(person_data):
    st.markdown(f"<div class='main-header'><h1>รายงานผลการตรวจสุขภาพประจำปี {person_data.get('Year', '')}</h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**ชื่อ-นามสกุล:** {person_data.get('ชื่อ-สกุล', '-')}")
        st.markdown(f"**อายุ:** {person_data.get('Age', '-')} ปี")
        st.markdown(f"**หน่วยงาน:** {person_data.get('Department', '-')}")
    with col2:
        st.markdown(f"**วันที่ตรวจ:** {person_data.get('วันที่ตรวจ', '-')}")
        st.markdown(f"**HN:** {person_data.get('HN', '-')}")
        st.markdown(f"**เพศ:** {person_data.get('Gender', '-')}")
    st.markdown("---")

# ------------------------------------------------------------------------------------
# ⚠️ สำคัญ: หากคุณมี Logic การแสดงผล (Display Logic) ของเดิมอยู่ ให้ใช้ของเดิมตรงส่วนนี้
# ------------------------------------------------------------------------------------

def display_main_report(person_data, all_person_history_df):
    st.info("แสดงผลสุขภาพพื้นฐาน (Main Report) - กรุณาใส่ Code การแสดงผลเดิมของคุณที่นี่")

def display_performance_report(person_data, report_type, all_person_history_df=None):
    st.info(f"แสดงผลสมรรถภาพ: {report_type} - กรุณาใส่ Code การแสดงผลเดิมของคุณที่นี่")

def display_visualization_tab(person_data, all_person_history_df):
    st.info("แสดงกราฟแนวโน้มสุขภาพ - กรุณาใส่ Code การแสดงผลเดิมของคุณที่นี่")

# ------------------------------------------------------------------------------------

# --- Main Admin Panel Function ---
def display_admin_panel(df):
    st.set_page_config(page_title="Admin Panel - ระบบรายงานสุขภาพ", layout="wide")
    inject_custom_css()

    if 'admin_search_term' not in st.session_state: st.session_state.admin_search_term = ""
    if 'admin_search_results' not in st.session_state: st.session_state.admin_search_results = None
    if 'admin_selected_hn' not in st.session_state: st.session_state.admin_selected_hn = None

    with st.sidebar:
        st.title("Admin Panel")
        st.markdown(f"สวัสดี, {st.session_state.get('user_name', 'Admin')}")
        if st.button("ออกจากระบบ Admin", type="primary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # --- ส่วนที่เพิ่ม: TABS สำหรับ Admin ---
    tab1, tab2 = st.tabs(["🔍 ค้นหาและดูผลตรวจ", "📱 จัดการ LINE Users"])

    # TAB 1: ระบบเดิม (ค้นหาคนไข้)
    with tab1:
        st.header("ค้นหาข้อมูลผู้รับการตรวจ")
        
        c1, c2 = st.columns([3, 1])
        with c1:
            search_query = st.text_input("ค้นหาด้วย ชื่อ หรือ HN", value=st.session_state.admin_search_term, placeholder="พิมพ์ชื่อ หรือ HN แล้วกด Enter...")
        with c2:
            st.write("") # Spacer
            st.write("")
            search_btn = st.button("ค้นหา", use_container_width=True)

        if search_btn or search_query:
            st.session_state.admin_search_term = search_query
            if search_query.strip():
                mask = df['ชื่อ-สกุล'].str.contains(search_query, na=False) | df['HN'].astype(str).str.contains(search_query, na=False)
                results = df[mask].copy()
                st.session_state.admin_search_results = results
            else:
                st.session_state.admin_search_results = pd.DataFrame()

        if st.session_state.admin_search_results is not None:
            results = st.session_state.admin_search_results
            if results.empty:
                st.warning("ไม่พบข้อมูล")
            else:
                st.success(f"พบข้อมูล {len(results)} รายการ")
                
                person_options = results[['HN', 'ชื่อ-สกุล']].drop_duplicates()
                selection_list = person_options.apply(lambda x: f"{x['ชื่อ-สกุล']} (HN: {x['HN']})", axis=1).tolist()
                
                selected_person_str = st.selectbox("เลือกรายชื่อเพื่อดูรายละเอียด:", selection_list)
                
                if selected_person_str:
                    selected_hn = selected_person_str.split(" (HN: ")[1][:-1]
                    st.session_state.admin_selected_hn = selected_hn
                    
                    st.markdown("---")
                    person_history = df[df['HN'] == selected_hn].copy()
                    
                    years = sorted(person_history['Year'].unique().tolist(), reverse=True)
                    selected_year_admin = st.selectbox("เลือกปีงบประมาณ:", years)
                    
                    person_row_admin = person_history[person_history['Year'] == selected_year_admin].iloc[0].to_dict()
                    
                    display_common_header(person_row_admin)
                    
                    report_tabs = st.tabs(["สุขภาพพื้นฐาน", "กราฟแนวโน้ม"])
                    with report_tabs[0]:
                        display_main_report(person_row_admin, person_history)
                    with report_tabs[1]:
                        if has_visualization_data(person_history):
                            display_visualization_tab(person_row_admin, person_history)
                        else:
                            st.info("ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟ")

    # TAB 2: หน้าจัดการ LINE Users (Google Sheets)
    with tab2:
        # เรียกใช้ฟังก์ชันจาก line_register.py โดยตรง
        # ซึ่งในไฟล์นั้นเราเปลี่ยนเป็น Google Sheets เรียบร้อยแล้ว
        render_admin_line_manager()
