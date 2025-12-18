import streamlit as st
import pandas as pd
from collections import OrderedDict
import json
from datetime import datetime
import re 
import html 
import numpy as np 

# --- Import ฟังก์ชันจากไฟล์อื่นที่จำเป็น ---
from performance_tests import interpret_audiogram, interpret_lung_capacity, interpret_cxr, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
from visualization import display_visualization_tab 
from batch_print import display_print_center_page

# --- Import ตรรกะการแปลผลจาก print_report.py ---
from print_report import (
    generate_fixed_recommendations,
    generate_cbc_recommendations,
    generate_urine_recommendations,
    generate_doctor_opinion
)

# --- Import Shared UI Functions ---
# Import directly from shared_ui to avoid circular imports or missing definitions
try:
    from shared_ui import (
        is_empty,
        normalize_name,
        inject_custom_css,
        display_common_header,
        has_basic_health_data,
        has_vision_data,
        has_hearing_data,
        has_lung_data,
        has_visualization_data,
        display_main_report,
        display_performance_report,
        # interpret_cxr, # Already imported from performance_tests, avoid conflict
        # interpret_ekg, # If needed from shared_ui
    )
except ImportError as e:
    st.error(f"Error importing from shared_ui: {e}")
    # Define minimal fallbacks if import fails (critical for app stability)
    def is_empty(val): return pd.isna(val) or str(val).strip() == ""
    def normalize_name(name): return str(name).strip()
    def inject_custom_css(): pass
    def display_common_header(data): st.write(data)
    def has_basic_health_data(data): return True
    def has_vision_data(data): return False
    def has_hearing_data(data): return False
    def has_lung_data(data): return False
    def has_visualization_data(df): return False
    def display_main_report(data, df): st.write("Main Report Placeholder")
    def display_performance_report(data, type, df=None): st.write(f"Performance Report: {type}")


# --- Import LINE Manager Function ---
try:
    from line_register import render_admin_line_manager
except ImportError:
    def render_admin_line_manager():
        st.error("ไม่พบไฟล์ line_register.py กรุณาสร้างไฟล์นี้ก่อน")


def display_admin_panel(df):
    """
    แสดงหน้าจอหลักสำหรับ Admin (Search Panel)
    """
    st.set_page_config(page_title="Admin Panel", layout="wide")
    inject_custom_css()

    # --- Initialize session state keys for admin search ---
    if 'admin_search_term' not in st.session_state:
        st.session_state.admin_search_term = ""
    if 'admin_search_results' not in st.session_state:
        st.session_state.admin_search_results = None 
    if 'admin_selected_hn' not in st.session_state:
        st.session_state.admin_selected_hn = None
    if 'admin_selected_year' not in st.session_state:
        st.session_state.admin_selected_year = None
    if 'admin_print_trigger' not in st.session_state:
        st.session_state.admin_print_trigger = False
    if 'admin_print_performance_trigger' not in st.session_state:
        st.session_state.admin_print_performance_trigger = False
    if "admin_person_row" not in st.session_state:
        st.session_state.admin_person_row = None

    # --- Sidebar Menu ---
    with st.sidebar:
        st.markdown("<div class='sidebar-title'>👑 Admin Panel</div>", unsafe_allow_html=True)
        
        if st.button("ออกจากระบบ (Logout)", use_container_width=True):
            # รวมคีย์ของ batch_print ที่ต้องการล้างด้วย
            keys_to_clear = [
                'authenticated', 'pdpa_accepted', 'user_hn', 'user_name', 'is_admin',
                'search_result', 'selected_year', 'person_row', 'selected_row_found',
                'admin_search_term', 'admin_search_results', 'admin_selected_hn',
                'admin_selected_year', 'admin_person_row', 'batch_print_ready', 'batch_print_html',
                'bp_dept_filter', 'bp_date_filter', 'bp_report_type' # เพิ่มคีย์ของ batch print เพื่อให้รีเซ็ตตอน logout
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # --- Main Content Tabs ---
    tab_search, tab_print, tab_line_users = st.tabs(["🔍 ค้นหาผู้ป่วย (Search)", "🖨️ ศูนย์พิมพ์รายงาน (Print Center)", "📱 จัดการ LINE Users"])

    # --- Tab 1: Search (Original Functionality) ---
    with tab_search:
        # --- Use st.form to enable Enter key submission ---
        with st.form(key="admin_search_form"):
            col_search_input, col_search_btn = st.columns([4, 1])
            with col_search_input:
                search_term = st.text_input("ค้นหา (ชื่อ-สกุล, HN, หรือ เลขบัตร)", value=st.session_state.admin_search_term, placeholder="พิมพ์คำค้นหา...", label_visibility="collapsed")
            with col_search_btn:
                submitted = st.form_submit_button("ค้นหา", use_container_width=True)
        
        if submitted:
            st.session_state.admin_search_term = search_term
            if search_term:
                normalized_search = normalize_name(search_term)
                search_mask = (
                    df['ชื่อ-สกุล'].apply(normalize_name).str.contains(normalized_search, case=False, na=False) |
                    (df['HN'].astype(str) == search_term) |
                    (df['เลขบัตรประชาชน'].astype(str) == search_term)
                )
                results_df = df[search_mask]
                if not results_df.empty:
                    unique_hns = results_df['HN'].unique()
                    st.session_state.admin_search_results = df[df['HN'].isin(unique_hns)].copy()
                    if len(unique_hns) == 1: st.session_state.admin_selected_hn = unique_hns[0]
                    else: st.session_state.admin_selected_hn = None
                else:
                    st.session_state.admin_search_results = pd.DataFrame()
                    st.session_state.admin_selected_hn = None
            else:
                st.session_state.admin_search_results = None
                st.session_state.admin_selected_hn = None
            st.session_state.admin_selected_year = None
            st.session_state.admin_person_row = None
            st.rerun()

        if st.session_state.admin_search_results is not None:
            if st.session_state.admin_search_results.empty:
                st.warning("ไม่พบข้อมูล")
            else:
                unique_results = st.session_state.admin_search_results.drop_duplicates(subset=['HN']).set_index('HN')
                
                if len(unique_results) > 1:
                    options = {hn: f"{row['ชื่อ-สกุล']} (HN: {hn})" for hn, row in unique_results.iterrows()}
                    current_hn = st.session_state.admin_selected_hn
                    hn_list = list(options.keys())
                    index = hn_list.index(current_hn) if current_hn in hn_list else 0
                    if st.session_state.admin_selected_hn is None:
                        index = 0
                        st.session_state.admin_selected_hn = hn_list[0]

                    col_sel_hn, col_sel_year = st.columns(2)
                    with col_sel_hn:
                        selected_hn = st.selectbox("เลือกผู้ป่วย", options=hn_list, format_func=lambda hn: options[hn], index=index, key="admin_select_hn_box")
                        if selected_hn != st.session_state.admin_selected_hn:
                            st.session_state.admin_selected_hn = selected_hn
                            st.session_state.admin_selected_year = None
                            st.session_state.admin_person_row = None
                            st.rerun()
                elif len(unique_results) == 1 and st.session_state.admin_selected_hn is None:
                     st.session_state.admin_selected_hn = unique_results.index[0]
                     st.rerun()

                if st.session_state.admin_selected_hn:
                    hn_to_load = st.session_state.admin_selected_hn
                    all_person_history_df = df[df['HN'] == hn_to_load].copy()
                    available_years = sorted(all_person_history_df["Year"].dropna().unique().astype(int), reverse=True)

                    if available_years:
                        if st.session_state.admin_selected_year not in available_years:
                            st.session_state.admin_selected_year = available_years[0]
                        year_idx = available_years.index(st.session_state.admin_selected_year)
                        
                        if 'col_sel_year' not in locals(): col_sel_year = st.container() # Fallback container
                        with col_sel_year:
                            selected_year = st.selectbox("เลือกปี พ.ศ.", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="admin_year_select")
                        
                        # Add spacing
                        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                        
                        col_btn_main, col_btn_perf = st.columns(2)
                        with col_btn_main:
                             if st.button("พิมพ์รายงานสุขภาพ", use_container_width=True, key="admin_print_main", type="primary"):
                                 st.session_state.admin_print_trigger = True
                        with col_btn_perf:
                             if st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True, key="admin_print_perf", type="primary"):
                                 st.session_state.admin_print_performance_trigger = True
                        
                        # Add divider right after buttons
                        st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)

                        if selected_year != st.session_state.admin_selected_year:
                            st.session_state.admin_selected_year = selected_year
                            st.session_state.admin_person_row = None
                            st.rerun()

                        if st.session_state.admin_person_row is None:
                            person_year_df = all_person_history_df[all_person_history_df["Year"] == st.session_state.admin_selected_year]
                            if not person_year_df.empty:
                                merged_series = person_year_df.bfill().ffill().iloc[0]
                                st.session_state.admin_person_row = merged_series.to_dict()
                            else: st.session_state.admin_person_row = {}
                    else:
                        st.error("ผู้ป่วยนี้ไม่มีข้อมูลรายปี")
                        st.session_state.admin_person_row = None

        # --- Display Report Content ---
        if st.session_state.admin_person_row:
            
            person_data = st.session_state.admin_person_row
            all_person_history_df_admin = df[df['HN'] == st.session_state.admin_selected_hn].copy()

            available_reports = OrderedDict()
            if has_visualization_data(all_person_history_df_admin): available_reports['ภาพรวมสุขภาพ (Graphs)'] = 'visualization_report'
            if has_basic_health_data(person_data): available_reports['สุขภาพพื้นฐาน'] = 'main_report'
            if has_vision_data(person_data): available_reports['สมรรถภาพการมองเห็น'] = 'vision_report'
            if has_hearing_data(person_data): available_reports['สมรรถภาพการได้ยิน'] = 'hearing_report'
            if has_lung_data(person_data): available_reports['สมรรถภาพปอด'] = 'lung_report'

            if not available_reports:
                display_common_header(person_data)
                st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับปีที่เลือก")
            else:
                display_common_header(person_data)
                sub_tabs = st.tabs(list(available_reports.keys()))
                for i, (tab_title, page_key) in enumerate(available_reports.items()):
                    with sub_tabs[i]:
                        if page_key == 'visualization_report': display_visualization_tab(person_data, all_person_history_df_admin)
                        elif page_key == 'vision_report': display_performance_report(person_data, 'vision')
                        elif page_key == 'hearing_report': display_performance_report(person_data, 'hearing', all_person_history_df=all_person_history_df_admin)
                        elif page_key == 'lung_report': display_performance_report(person_data, 'lung')
                        elif page_key == 'main_report': display_main_report(person_data, all_person_history_df_admin)

            # Print Logic
            if st.session_state.get("admin_print_trigger", False):
                report_html_data = generate_printable_report(person_data, all_person_history_df_admin)
                escaped_html = json.dumps(report_html_data)
                iframe_id = f"print-iframe-admin-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                print_component = f"""<iframe id="{iframe_id}" style="display:none;"></iframe><script>(function(){{const iframe=document.getElementById('{iframe_id}');if(!iframe)return;const doc=iframe.contentWindow.document;doc.open();doc.write({escaped_html});doc.close();iframe.onload=function(){{setTimeout(function(){{try{{iframe.contentWindow.focus();iframe.contentWindow.print();}}catch(e){{console.error("Print failed:",e);}}}},500);}};}})();</script>"""
                st.components.v1.html(print_component, height=0, width=0)
                st.session_state.admin_print_trigger = False

            if st.session_state.get("admin_print_performance_trigger", False):
                report_html_data = generate_performance_report_html(person_data, all_person_history_df_admin)
                escaped_html = json.dumps(report_html_data)
                iframe_id = f"print-perf-iframe-admin-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                print_component = f"""<iframe id="{iframe_id}" style="display:none;"></iframe><script>(function(){{const iframe=document.getElementById('{iframe_id}');if(!iframe)return;const doc=iframe.contentWindow.document;doc.open();doc.write({escaped_html});doc.close();iframe.onload=function(){{setTimeout(function(){{try{{iframe.contentWindow.focus();iframe.contentWindow.print();}}catch(e){{console.error("Print failed:",e);}}}},500);}};}})();</script>"""
                st.components.v1.html(print_component, height=0, width=0)
                st.session_state.admin_print_performance_trigger = False

    # --- Tab 2: Print Center ---
    with tab_print:
        display_print_center_page(df)

    # --- Tab 3: LINE Manager (New) ---
    with tab_line_users:
        render_admin_line_manager()
