import streamlit as st
import pandas as pd
from collections import OrderedDict
import json
import base64

# --- Imports with Error Handling (Optional modules) ---
try:
    from utils import (
        is_empty,
        normalize_name,
        has_basic_health_data,
        has_vision_data,
        has_hearing_data,
        has_lung_data,
        has_visualization_data
    )
except ImportError:
    def is_empty(val): return pd.isna(val) or str(val).strip() == ""
    def normalize_name(name): return str(name).strip()
    def has_basic_health_data(row): return True
    def has_vision_data(row): return False
    def has_hearing_data(row): return False
    def has_lung_data(row): return False
    def has_visualization_data(df): return False

try:
    from print_report import generate_printable_report
    from print_performance_report import generate_performance_report_html
except ImportError:
    def generate_printable_report(*args): return ""
    def generate_performance_report_html(*args): return ""

try:
    from visualization import display_visualization_tab 
except ImportError:
    def display_visualization_tab(person_data, all_df): st.info("Visualization module not found")

try:
    from shared_ui import (
        inject_custom_css,
        display_main_report,
        display_performance_report
    )
except Exception as e:
    def inject_custom_css(): pass
    def display_main_report(p, a): st.error("Main Report Function Missing")
    def display_performance_report(p, r, a=None): st.error("Performance Report Function Missing")

# --- Safe Import for Batch Print (แก้ไขใหม่) ---
# ใช้ try-except เพื่อป้องกันหน้าเว็บพัง (Crash) หากไฟล์ batch_print.py มีปัญหา
# แต่จะแสดง Error จริงออกมาเพื่อให้ทราบสาเหตุแทนข้อความ Not Found
try:
    from batch_print import display_print_center_page
except Exception as e:
    def display_print_center_page(df):
        st.error(f"❌ Batch Print Module Error: {e}")
        st.warning("สาเหตุอาจเกิดจาก: ไฟล์ batch_print.py หรือไฟล์ที่เกี่ยวข้อง (print_report.py, print_performance_report.py) มีข้อผิดพลาด")

# Note: We duplicate the custom header function here to avoid circular imports with app.py
def render_admin_header_with_actions(person_data, available_years):
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    
    icon_profile = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>"""
    
    # ใช้ CSS Classes จาก shared_ui เพื่อรองรับ Theme และ Responsive
    st.markdown(f"""
    <div class="report-header-container">
        <div class="header-main">
            <div class="patient-profile">
                <div class="profile-icon">{icon_profile}</div>
                <div class="profile-details">
                    <div class="patient-name">{name}</div>
                    <div class="patient-meta"><span>HN: {hn}</span> | <span>เพศ: {sex}</span> | <span>อายุ: {age} ปี</span></div>
                    <div class="patient-dept">หน่วยงาน: {department}</div>
                </div>
            </div>
            <div class="report-meta">
                <div class="meta-date">วันที่ตรวจ: {check_date}</div>
                <div class="hospital-brand">
                    <div class="hosp-name">คลินิกตรวจสุขภาพ</div>
                    <div class="hosp-dept">อาชีวเวชกรรม</div>
                    <div class="hosp-sub">รพ.สันทราย</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action Buttons (Same as Main App)
    cb1, cb2, cb3 = st.columns([1.5, 1.5, 4])
    with cb1:
        if st.button("🖨️ พิมพ์ผลสุขภาพ", key="adm_print_h", use_container_width=True):
            st.session_state.admin_print_trigger = True
    with cb2:
        if st.button("🖨️ พิมพ์สมรรถภาพ", key="adm_print_p", use_container_width=True):
            st.session_state.admin_print_performance_trigger = True

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
        st.title("Admin Panel")
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

    tab_search, tab_print = st.tabs(["🔍 ค้นหาผู้ป่วย (Search)", "🖨️ ศูนย์พิมพ์รายงาน (Print Center)"])

    # --- TAB 1: Search ---
    with tab_search:
        with st.form(key="admin_search_form"):
            st.markdown("<b>ค้นหา (ระบุ ชื่อ, HN หรือเลขบัตรประชาชน)</b>", unsafe_allow_html=True)
            c1, c2 = st.columns([4, 1])
            with c1: 
                search_term = st.text_input("Search Term", value=st.session_state.admin_search_term, label_visibility="collapsed", placeholder="กรอกข้อมูลที่ต้องการค้นหา...")
            with c2: 
                submitted = st.form_submit_button("ค้นหา", use_container_width=True)
        
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
                        
                        # Use Custom Header with Print Actions
                        render_admin_header_with_actions(p_row, years)
                        
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

                    # Handle Print Triggers in Admin Panel
                    if st.session_state.admin_print_trigger:
                        h = generate_printable_report(st.session_state.admin_person_row, history)
                        b64_html = base64.b64encode(h.encode('utf-8')).decode('utf-8')
                        st.components.v1.html(f"<script>var w=window.open('','_blank');w.document.write(decodeURIComponent(escape(window.atob('{b64_html}'))));w.document.close();</script>", height=0)
                        st.session_state.admin_print_trigger = False
                    
                    if st.session_state.admin_print_performance_trigger:
                        h = generate_performance_report_html(st.session_state.admin_person_row, history)
                        b64_html = base64.b64encode(h.encode('utf-8')).decode('utf-8')
                        st.components.v1.html(f"<script>var w=window.open('','_blank');w.document.write(decodeURIComponent(escape(window.atob('{b64_html}'))));w.document.close();</script>", height=0)
                        st.session_state.admin_print_performance_trigger = False

    # --- TAB 2: Print Center ---
    with tab_print:
        display_print_center_page(df)
