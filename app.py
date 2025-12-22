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
# ใช้ try-except เพื่อความชัวร์
try:
    from line_register import render_registration_page
except ImportError:
    def render_registration_page(df):
        st.error("ไม่พบไฟล์ line_register.py กรุณาสร้างไฟล์นี้ก่อน")

# --- Import Print Functions ---
try:
    from print_report import generate_printable_report
except ImportError:
    def generate_printable_report(*args): return ""

try:
    from print_performance_report import generate_performance_report_html
except ImportError:
    def generate_performance_report_html(*args): return ""

# --- Import Utils ---
try:
    from utils import (
        is_empty, normalize_name, has_basic_health_data, 
        has_vision_data, has_hearing_data, has_lung_data, has_visualization_data
    )
except ImportError:
    # Fallback
    def is_empty(v): return pd.isna(v) or str(v).strip() == ""
    def normalize_name(n): return str(n).strip()
    def has_basic_health_data(r): return True
    def has_vision_data(r): return False
    def has_hearing_data(r): return False
    def has_lung_data(r): return False
    def has_visualization_data(d): return False

# --- Import Shared UI ---
try:
    from shared_ui import inject_custom_css, display_common_header
except ImportError:
    def inject_custom_css(): pass
    def display_common_header(d): st.write(d)

# --- Import Display Functions ---
try:
    from visualization import display_visualization_tab
except ImportError:
    def display_visualization_tab(d, a): st.info("No visualization")

try:
    from admin_panel import display_admin_panel, display_main_report, display_performance_report
except ImportError:
    def display_admin_panel(df): st.error("Admin Panel Error")
    def display_main_report(p, a): pass
    def display_performance_report(p, t, a=None): pass

# --- Data Loading ---
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


# --------------------------------------------------------------------------------
# MAIN LOGIC (ส่วนตัดสินใจว่าจะโชว์หน้าไหน)
# --------------------------------------------------------------------------------

# 1. Initialize State
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False

# 2. Load Data
df = load_sqlite_data()
if df is None: st.stop()

# 3. Check LINE / LIFF Parameters (จุดสำคัญ!)
# เช็คว่ามี ?page=register หรือ ?userid=... ส่งมาไหม
is_line_mode = False
try:
    q_page = st.query_params.get("page", "")
    q_userid = st.query_params.get("userid", "")
    if q_page == "register" or q_userid:
        is_line_mode = True
except:
    pass

# 4. Routing (ตัดสินใจพาไปหน้าไหน)

if is_line_mode:
    # 🟢 กรณีเข้าจาก LINE -> บังคับไปหน้าลงทะเบียนใหม่ทันที (ไม่สน Login เก่า)
    render_registration_page(df)

elif not st.session_state['authenticated']:
    # 🔴 กรณีเข้าปกติแล้วยังไม่ Login -> โชว์หน้า Login เดิม
    
    # (Optional) ปุ่มแอบทดสอบสำหรับเรา (Dev)
    # ถ้าไม่อยากให้รก เอาบรรทัด if st.checkbox... ออกได้เลยครับ
    if st.checkbox("Dev: ลองเปิดโหมด LINE (กดเล่นๆ)", value=False):
        render_registration_page(df)
    else:
        authentication_flow(df)

elif not st.session_state['pdpa_accepted']:
    # 🟡 Login แล้วแต่ยังไม่กด PDPA
    if st.session_state.get('is_admin', False):
        st.session_state['pdpa_accepted'] = True; st.rerun()
    else:
        pdpa_consent_page()

else:
    # 🔵 Login เสร็จสมบูรณ์แล้ว -> เข้าใช้งานระบบ
    if st.session_state.get('is_admin', False):
        display_admin_panel(df)
    else:
        main_app(df)
