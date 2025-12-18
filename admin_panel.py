import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- Import Module อื่นๆ ที่จำเป็นสำหรับการแสดงผล ---
# เราต้อง Import ฟังก์ชันแสดงผลจากไฟล์อื่นๆ ของคุณเพื่อให้ admin_panel เรียกใช้ได้
try:
    from shared_ui import (
        display_common_header,
        display_main_report,
        display_performance_report,
        has_visualization_data,
        has_basic_health_data,
        has_vision_data,
        has_hearing_data,
        has_lung_data
    )
    from visualization import display_visualization_tab
except ImportError:
    # Fallback ถ้าหาไฟล์ไม่เจอ (เพื่อป้องกัน Error ตอนรันครั้งแรก)
    def display_common_header(person_data): st.warning("ไม่พบ module shared_ui")
    def display_main_report(person_data, all_df): st.warning("ไม่พบ module shared_ui")
    def display_performance_report(person_data, r_type, all_df=None): st.warning("ไม่พบ module shared_ui")
    def display_visualization_tab(person_data, all_df): st.warning("ไม่พบ module visualization")
    def has_visualization_data(df): return False

# --- Import LINE Manager Function ---
# (สำคัญ: ต้องมีไฟล์ line_register.py อยู่ในโฟลเดอร์เดียวกัน)
try:
    from line_register import render_admin_line_manager
except ImportError:
    def render_admin_line_manager():
        st.error("ไม่พบไฟล์ line_register.py กรุณาสร้างไฟล์นี้ก่อน")

# --- Helper Functions (Shared Logic within Admin) ---
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
    # แยกเป็น 2 Tabs:
    # 1. ค้นหาและดูผลตรวจ (ระบบเดิม)
    # 2. จัดการ LINE Users (ระบบใหม่ที่เพิ่งทำ)
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
                # Logic การค้นหา
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
                
                # Dropdown เลือกคนไข้
                person_options = results[['HN', 'ชื่อ-สกุล']].drop_duplicates()
                selection_list = person_options.apply(lambda x: f"{x['ชื่อ-สกุล']} (HN: {x['HN']})", axis=1).tolist()
                
                selected_person_str = st.selectbox("เลือกรายชื่อเพื่อดูรายละเอียด:", selection_list)
                
                if selected_person_str:
                    selected_hn = selected_person_str.split(" (HN: ")[1][:-1]
                    st.session_state.admin_selected_hn = selected_hn
                    
                    st.markdown("---")
                    
                    # ดึงข้อมูลประวัติทั้งหมดของคนนี้
                    person_history = df[df['HN'] == selected_hn].copy()
                    
                    # เลือกปีงบประมาณ
                    years = sorted(person_history['Year'].unique().tolist(), reverse=True)
                    selected_year_admin = st.selectbox("เลือกปีงบประมาณ:", years)
                    
                    # ดึงข้อมูลของปีที่เลือก
                    person_row_admin = person_history[person_history['Year'] == selected_year_admin].iloc[0].to_dict()
                    
                    # --- ส่วนแสดงผลรายงาน (เรียกใช้ฟังก์ชันจริงจาก shared_ui.py และ visualization.py) ---
                    display_common_header(person_row_admin)
                    
                    # ตรวจสอบว่ามีข้อมูลอะไรบ้างเพื่อสร้าง Tabs ย่อย
                    report_tabs_labels = []
                    
                    if has_basic_health_data(person_row_admin): report_tabs_labels.append("สุขภาพพื้นฐาน")
                    if has_visualization_data(person_history): report_tabs_labels.append("กราฟแนวโน้ม")
                    if has_vision_data(person_row_admin): report_tabs_labels.append("สมรรถภาพการมองเห็น")
                    if has_hearing_data(person_row_admin): report_tabs_labels.append("สมรรถภาพการได้ยิน")
                    if has_lung_data(person_row_admin): report_tabs_labels.append("สมรรถภาพปอด")

                    if report_tabs_labels:
                        sub_tabs = st.tabs(report_tabs_labels)
                        
                        # วนลูปแสดงผลตาม Tab ที่มี
                        for i, label in enumerate(report_tabs_labels):
                            with sub_tabs[i]:
                                if label == "สุขภาพพื้นฐาน":
                                    display_main_report(person_row_admin, person_history)
                                elif label == "กราฟแนวโน้ม":
                                    display_visualization_tab(person_row_admin, person_history)
                                elif label == "สมรรถภาพการมองเห็น":
                                    display_performance_report(person_row_admin, 'vision')
                                elif label == "สมรรถภาพการได้ยิน":
                                    display_performance_report(person_row_admin, 'hearing', all_person_history_df=person_history)
                                elif label == "สมรรถภาพปอด":
                                    display_performance_report(person_row_admin, 'lung')
                    else:
                        st.warning("ไม่มีข้อมูลการตรวจสำหรับปีที่เลือก")

    # TAB 2: หน้าจัดการ LINE Users (Google Sheets)
    with tab2:
        # เรียกใช้ฟังก์ชันจาก line_register.py โดยตรง
        # ซึ่งในไฟล์นั้นเราเปลี่ยนเป็น Google Sheets เรียบร้อยแล้ว
        render_admin_line_manager()
