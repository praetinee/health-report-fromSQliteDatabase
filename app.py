import streamlit as st
import sqlite3
import requests
import pandas as pd
import tempfile
import os
import json
from collections import OrderedDict
from datetime import datetime

# --- Import Authentication ---
from auth import authentication_flow, pdpa_consent_page

# --- Import Line Register ---
from line_register import render_registration_page

# --- Import Print Functions ---
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html

# --- Import Utils (New!) ---
# ดึงฟังก์ชันตรวจสอบข้อมูลจากไฟล์กลาง utils.py
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
    st.error("Critical Error: utils module not found. Please create utils.py.")
    st.stop()

# --- Import Helper Functions from Shared UI (Only UI) ---
try:
    from shared_ui import (
        inject_custom_css,
        display_common_header
    )
except ImportError:
    # ถ้าหา shared_ui ไม่เจอ (เช่นยังไม่ได้สร้าง) ให้ใช้ Default
    def inject_custom_css(): pass
    def display_common_header(data): st.write(data)

# --- Import Display Functions ---
try:
    from visualization import display_visualization_tab
except ImportError:
    def display_visualization_tab(d, all_df): st.info("No visualization module")

try:
    from admin_panel import display_admin_panel, display_main_report, display_performance_report
except ImportError:
    st.error("Critical Error: admin_panel module not found or has errors.")
    st.stop()

# --- Data Loading (เหมือนเดิม) ---
@st.cache_data(ttl=600)
def load_sqlite_data():
    tmp_path = None
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
        def clean_hn(hn_val):
            if pd.isna(hn_val): return ""
            s_val = str(hn_val).strip()
            return s_val[:-2] if s_val.endswith('.0') else s_val
        df_loaded['HN'] = df_loaded['HN'].apply(clean_hn)
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

# --- Main App Logic ---
def main_app(df):
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
    inject_custom_css()

    if 'user_hn' not in st.session_state: st.error("Error: No user data"); st.stop()
    user_hn = st.session_state['user_hn']
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    def handle_year_change():
        st.session_state.selected_year = st.session_state.year_select
        st.session_state.pop("person_row", None)
        st.session_state.pop("selected_row_found", None)

    if 'selected_year' not in st.session_state: st.session_state.selected_year = None
    if 'print_trigger' not in st.session_state: st.session_state.print_trigger = False
    if 'print_performance_trigger' not in st.session_state: st.session_state.print_performance_trigger = False

    with st.sidebar:
        st.markdown(f"<div class='sidebar-title'>ยินดีต้อนรับ</div><h3>{st.session_state.get('user_name', '')}</h3>", unsafe_allow_html=True)
        st.markdown(f"**HN:** {user_hn}")
        st.markdown("---")
        
        if not results_df.empty:
            years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
            if years:
                if st.session_state.selected_year not in years: st.session_state.selected_year = years[0]
                idx = years.index(st.session_state.selected_year)
                st.selectbox("เลือกปี พ.ศ.", years, index=idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change)
                
                yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
                if not yr_df.empty:
                    st.session_state.person_row = yr_df.bfill().ffill().iloc[0].to_dict()
                    st.session_state.selected_row_found = True
                else:
                    st.session_state.person_row = None
                    st.session_state.selected_row_found = False
            else:
                st.warning("ไม่พบข้อมูลรายปี")
        else:
            st.warning("ไม่พบข้อมูลสำหรับผู้ใช้นี้")

        st.markdown("---")
        if st.session_state.get("selected_row_found", False):
            if st.button("พิมพ์รายงานสุขภาพ"): st.session_state.print_trigger = True
            if st.button("พิมพ์รายงานสมรรถภาพ"): st.session_state.print_performance_trigger = True
        
        st.markdown("---")
        if st.button("ออกจากระบบ"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # Content
    if "person_row" not in st.session_state or not st.session_state.get("selected_row_found", False):
        st.info("กรุณาเลือกปีที่ต้องการดูผลตรวจ")
    else:
        p_data = st.session_state.person_row
        all_hist = st.session_state.search_result
        
        tabs_map = OrderedDict()
        if has_visualization_data(all_hist): tabs_map['ภาพรวม (Graphs)'] = 'viz'
        if has_basic_health_data(p_data): tabs_map['สุขภาพพื้นฐาน'] = 'main'
        if has_vision_data(p_data): tabs_map['การมองเห็น'] = 'vision'
        if has_hearing_data(p_data): tabs_map['การได้ยิน'] = 'hearing'
        if has_lung_data(p_data): tabs_map['ปอด'] = 'lung'

        if tabs_map:
            display_common_header(p_data)
            t_objs = st.tabs(list(tabs_map.keys()))
            for i, (k, v) in enumerate(tabs_map.items()):
                with t_objs[i]:
                    if v == 'viz': display_visualization_tab(p_data, all_hist)
                    elif v == 'main': display_main_report(p_data, all_hist)
                    elif v == 'vision': display_performance_report(p_data, 'vision')
                    elif v == 'hearing': display_performance_report(p_data, 'hearing', all_person_history_df=all_hist)
                    elif v == 'lung': display_performance_report(p_data, 'lung')
        else:
            display_common_header(p_data)
            st.warning("ไม่พบข้อมูลการตรวจ")
        
        # Print
        if st.session_state.print_trigger:
            h = generate_printable_report(p_data, all_hist)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_trigger = False
        if st.session_state.print_performance_trigger:
            h = generate_performance_report_html(p_data, all_hist)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_performance_trigger = False


# --- Entry Point ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False

df = load_sqlite_data()
if df is None: st.stop()

# LINE Logic
try: q_page = st.query_params.get("page", "")
except: q_page = ""

if q_page == "register":
    render_registration_page(df)
elif not st.session_state['authenticated']:
    if st.checkbox("ทดสอบโหมดลงทะเบียน LINE OA (Dev Only)"): render_registration_page(df)
    else: authentication_flow(df)
elif not st.session_state['pdpa_accepted']:
    if st.session_state.get('is_admin', False):
        st.session_state['pdpa_accepted'] = True; st.rerun()
    else: pdpa_consent_page()
else:
    if st.session_state.get('is_admin', False): display_admin_panel(df)
    else: main_app(df)
