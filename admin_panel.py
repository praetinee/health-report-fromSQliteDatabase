import streamlit as st
import pandas as pd
from collections import OrderedDict
import json
from datetime import datetime
import re 
import html 
import numpy as np 

# --- Import Utils (New!) ---
from utils import (
    is_empty,
    normalize_name,
    has_basic_health_data,
    has_vision_data,
    has_hearing_data,
    has_lung_data,
    has_visualization_data
)

# --- Import ฟังก์ชันอื่นๆ ---
from performance_tests import interpret_audiogram, interpret_lung_capacity, interpret_cxr, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
from batch_print import display_print_center_page

# --- Import Visualization ---
try:
    from visualization import display_visualization_tab 
except ImportError:
    def display_visualization_tab(person_data, all_df): st.info("Visualization module not found")

# --- Import Shared UI Functions (เฉพาะ UI เท่านั้น) ---
try:
    from shared_ui import (
        inject_custom_css,
        display_common_header,
        # เอาเฉพาะ UI component, ไม่เอา logic function
    )
except ImportError:
    # Fallback ถ้าหา shared_ui ไม่เจอ
    def inject_custom_css(): pass
    def display_common_header(data): st.write(data)

# --- Import LINE Manager Function ---
try:
    from line_register import render_admin_line_manager
except ImportError:
    def render_admin_line_manager():
        st.error("ไม่พบไฟล์ line_register.py กรุณาสร้างไฟล์นี้ก่อน")

# ------------------------------------------------------------------
# ส่วนแสดงผลรายงาน (Placeholder สำหรับให้ app.py เรียกใช้)
# ------------------------------------------------------------------

def display_main_report(person_data, all_person_history_df):
    """แสดงผลสุขภาพพื้นฐาน"""
    st.info("ℹ️ ส่วนแสดงผลสุขภาพพื้นฐาน (Main Report) - กรุณานำโค้ดแสดงผลเดิมมาใส่ตรงนี้")

def display_performance_report(person_data, report_type, all_person_history_df=None):
    """แสดงผลสมรรถภาพ"""
    st.info(f"ℹ️ ส่วนแสดงผลสมรรถภาพ: {report_type} - กรุณานำโค้ดแสดงผลเดิมมาใส่ตรงนี้")

# ------------------------------------------------------------------

def display_admin_panel(df):
    """แสดงหน้าจอหลักสำหรับ Admin (Search Panel)"""
    st.set_page_config(page_title="Admin Panel", layout="wide")
    inject_custom_css()

    if 'admin_search_term' not in st.session_state: st.session_state.admin_search_term = ""
    if 'admin_search_results' not in st.session_state: st.session_state.admin_search_results = None 
    if 'admin_selected_hn' not in st.session_state: st.session_state.admin_selected_hn = None
    if 'admin_selected_year' not in st.session_state: st.session_state.admin_selected_year = None
    if 'admin_print_trigger' not in st.session_state: st.session_state.admin_print_trigger = False
    if 'admin_print_performance_trigger' not in st.session_state: st.session_state.admin_print_performance_trigger = False
    if "admin_person_row" not in st.session_state: st.session_state.admin_person_row = None

    with st.sidebar:
        st.markdown("<div class='sidebar-title'>👑 Admin Panel</div>", unsafe_allow_html=True)
        if st.button("ออกจากระบบ (Logout)", use_container_width=True):
            keys_to_clear = [
                'authenticated', 'pdpa_accepted', 'user_hn', 'user_name', 'is_admin',
                'search_result', 'selected_year', 'person_row', 'selected_row_found',
                'admin_search_term', 'admin_search_results', 'admin_selected_hn',
                'admin_selected_year', 'admin_person_row', 'batch_print_ready', 'batch_print_html',
                'bp_dept_filter', 'bp_date_filter', 'bp_report_type'
            ]
            for key in keys_to_clear:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    tab_search, tab_print, tab_line_users = st.tabs(["🔍 ค้นหาผู้ป่วย (Search)", "🖨️ ศูนย์พิมพ์รายงาน (Print Center)", "📱 จัดการ LINE Users"])

    with tab_search:
        with st.form(key="admin_search_form"):
            c1, c2 = st.columns([4, 1])
            with c1: search_term = st.text_input("ค้นหา (ชื่อ, HN, เลขบัตร)", value=st.session_state.admin_search_term)
            with c2: submitted = st.form_submit_button("ค้นหา", use_container_width=True)
        
        if submitted:
            st.session_state.admin_search_term = search_term
            if search_term:
                nm_search = normalize_name(search_term)
                mask = (df['ชื่อ-สกุล'].apply(normalize_name).str.contains(nm_search, case=False, na=False) |
                        (df['HN'].astype(str) == search_term) |
                        (df['เลขบัตรประชาชน'].astype(str) == search_term))
                results = df[mask]
                st.session_state.admin_search_results = results if not results.empty else pd.DataFrame()
                st.session_state.admin_selected_hn = results['HN'].iloc[0] if len(results['HN'].unique()) == 1 else None
            else:
                st.session_state.admin_search_results = None
            st.session_state.admin_selected_year = None
            st.session_state.admin_person_row = None
            st.rerun()

        if st.session_state.admin_search_results is not None:
            results = st.session_state.admin_search_results
            if results.empty:
                st.warning("ไม่พบข้อมูล")
            else:
                unique_results = results.drop_duplicates(subset=['HN']).set_index('HN')
                options = {hn: f"{row['ชื่อ-สกุล']} (HN: {hn})" for hn, row in unique_results.iterrows()}
                hn_list = list(options.keys())
                
                if len(hn_list) > 1 or st.session_state.admin_selected_hn is None:
                    curr = st.session_state.admin_selected_hn if st.session_state.admin_selected_hn in hn_list else hn_list[0]
                    sel_hn = st.selectbox("เลือกผู้ป่วย", hn_list, format_func=lambda x: options[x], index=hn_list.index(curr))
                    if sel_hn != st.session_state.admin_selected_hn:
                        st.session_state.admin_selected_hn = sel_hn
                        st.session_state.admin_selected_year = None
                        st.session_state.admin_person_row = None
                        st.rerun()
                
                if st.session_state.admin_selected_hn:
                    hn = st.session_state.admin_selected_hn
                    history = df[df['HN'] == hn].copy()
                    years = sorted(history["Year"].dropna().unique().astype(int), reverse=True)
                    
                    if years:
                        if st.session_state.admin_selected_year not in years: st.session_state.admin_selected_year = years[0]
                        sel_year = st.selectbox("เลือกปี พ.ศ.", years, index=years.index(st.session_state.admin_selected_year), format_func=lambda y: f"พ.ศ. {y}")
                        
                        c_p1, c_p2 = st.columns(2)
                        with c_p1: 
                            if st.button("พิมพ์รายงานสุขภาพ", key="adm_p1"): st.session_state.admin_print_trigger = True
                        with c_p2: 
                            if st.button("พิมพ์รายงานสมรรถภาพ", key="adm_p2"): st.session_state.admin_print_performance_trigger = True
                        st.markdown("---")

                        if sel_year != st.session_state.admin_selected_year:
                            st.session_state.admin_selected_year = sel_year
                            st.session_state.admin_person_row = None
                            st.rerun()

                        if st.session_state.admin_person_row is None:
                            yr_df = history[history["Year"] == sel_year]
                            if not yr_df.empty:
                                st.session_state.admin_person_row = yr_df.bfill().ffill().iloc[0].to_dict()
                    
                    if st.session_state.admin_person_row:
                        p_row = st.session_state.admin_person_row
                        display_common_header(p_row)
                        
                        tabs_map = OrderedDict()
                        if has_visualization_data(history): tabs_map['ภาพรวม (Graphs)'] = 'viz'
                        if has_basic_health_data(p_row): tabs_map['สุขภาพพื้นฐาน'] = 'main'
                        if has_vision_data(p_row): tabs_map['การมองเห็น'] = 'vision'
                        if has_hearing_data(p_row): tabs_map['การได้ยิน'] = 'hearing'
                        if has_lung_data(p_row): tabs_map['ปอด'] = 'lung'

                        if tabs_map:
                            t_objs = st.tabs(list(tabs_map.keys()))
                            for i, (k, v) in enumerate(tabs_map.items()):
                                with t_objs[i]:
                                    if v == 'viz': display_visualization_tab(p_row, history)
                                    elif v == 'main': display_main_report(p_row, history)
                                    elif v == 'vision': display_performance_report(p_row, 'vision')
                                    elif v == 'hearing': display_performance_report(p_row, 'hearing', all_person_history_df=history)
                                    elif v == 'lung': display_performance_report(p_row, 'lung')
                        else:
                            st.warning("ไม่พบข้อมูลการตรวจในปีนี้")

                    if st.session_state.admin_print_trigger:
                        h = generate_printable_report(st.session_state.admin_person_row, history)
                        st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
                        st.session_state.admin_print_trigger = False
                    
                    if st.session_state.admin_print_performance_trigger:
                        h = generate_performance_report_html(st.session_state.admin_person_row, history)
                        st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
                        st.session_state.admin_print_performance_trigger = False

    with tab_print:
        display_print_center_page(df)

    with tab_line_users:
        render_admin_line_manager()
