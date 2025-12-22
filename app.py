import streamlit as st
import sqlite3
import requests
import pandas as pd
import tempfile
import os
import json
from collections import OrderedDict
from datetime import datetime

# --- Import Authentication & Consent ---
from auth import authentication_flow, pdpa_consent_page

# --- Import CSV Saving Function (จาก line_register) ---
try:
    from line_register import save_new_user_to_csv, liff_initializer_component
except ImportError:
    # Fallback function
    def save_new_user_to_csv(f, l, uid): return True, "Saved"
    def liff_initializer_component(): pass

# --- Import Print Functions ---
try:
    from print_report import generate_printable_report
except Exception:
    def generate_printable_report(*args): return ""

try:
    from print_performance_report import generate_performance_report_html
except Exception:
    def generate_performance_report_html(*args): return ""

# --- Import Utils ---
try:
    from utils import (
        is_empty, normalize_name, has_basic_health_data, 
        has_vision_data, has_hearing_data, has_lung_data, has_visualization_data
    )
except Exception:
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
except Exception:
    def inject_custom_css(): pass
    def display_common_header(data): st.write(f"**รายงานผลสุขภาพ:** {data.get('ชื่อ-สกุล', '-')}")

# --- Import Display Functions ---
try:
    from visualization import display_visualization_tab
except Exception:
    def display_visualization_tab(d, a): st.info("No visualization module")

try:
    from admin_panel import display_admin_panel, display_main_report, display_performance_report
except Exception:
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

# --- Main App Logic (สำหรับ User ที่ล็อกอินแล้ว) ---
def main_app(df):
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
    inject_custom_css()

    if 'user_hn' not in st.session_state: 
        st.error("Error: No user data found in session.")
        st.stop()
        
    user_hn = st.session_state['user_hn']
    
    # 1. Filter Data for User
    # คัดกรองข้อมูลเฉพาะ HN นี้
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    if results_df.empty:
        st.error(f"ไม่พบข้อมูลผลตรวจสำหรับ HN: {user_hn}")
        return

    # 2. Auto-Select Latest Year (หัวใจสำคัญ!)
    # ถ้ายังไม่มีปีที่เลือก หรือปีที่เลือกไม่ถูกต้อง ให้เลือกปีล่าสุดอัตโนมัติ
    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    
    if not available_years:
        st.warning("ไม่พบประวัติการตรวจสุขภาพรายปี")
        return

    if 'selected_year' not in st.session_state or st.session_state.selected_year not in available_years:
        st.session_state.selected_year = available_years[0]
        # บังคับรีเซ็ตข้อมูลแถวเพื่อให้โหลดใหม่
        st.session_state.person_row = None
        st.session_state.selected_row_found = False

    # 3. Load Person Row Data (โหลดข้อมูลจริง)
    # ดึงข้อมูลของปีที่เลือกมาใส่ตัวแปร person_row
    if st.session_state.get('person_row') is None:
        yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
        if not yr_df.empty:
            # ใช้ bfill/ffill เพื่อรวมข้อมูลถ้ามีหลาย row ในปีเดียว
            st.session_state.person_row = yr_df.bfill().ffill().iloc[0].to_dict()
            st.session_state.selected_row_found = True
        else:
            st.session_state.person_row = None
            st.session_state.selected_row_found = False

    # --- Auto-Save LINE ID Logic ---
    if st.session_state.get("line_user_id") and not st.session_state.get("line_saved", False):
        try:
            user_name_full = st.session_state.get('user_name', '')
            parts = user_name_full.split()
            f_name = parts[0] if len(parts) > 0 else ""
            l_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            save_new_user_to_csv(f_name, l_name, st.session_state["line_user_id"])
            st.session_state["line_saved"] = True
        except:
            pass

    # --- Event Handler ---
    def handle_year_change():
        st.session_state.selected_year = st.session_state.year_select
        st.session_state.person_row = None # Clear old data
        st.session_state.selected_row_found = False

    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"<div class='sidebar-title'>ยินดีต้อนรับ</div><h3>{st.session_state.get('user_name', '')}</h3>", unsafe_allow_html=True)
        st.markdown(f"**HN:** {user_hn}")
        st.markdown("---")
        
        # Year Selector
        idx = available_years.index(st.session_state.selected_year)
        st.selectbox("เลือกปี พ.ศ.", available_years, index=idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change)
        
        st.markdown("---")
        if st.session_state.get("selected_row_found", False):
            if st.button("พิมพ์รายงานสุขภาพ"): st.session_state.print_trigger = True
            if st.button("พิมพ์รายงานสมรรถภาพ"): st.session_state.print_performance_trigger = True
        
        st.markdown("---")
        if st.button("ออกจากระบบ"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- Main Content Area ---
    if not st.session_state.get("selected_row_found", False) or st.session_state.get("person_row") is None:
        st.info(f"ไม่พบข้อมูลผลตรวจสำหรับปี {st.session_state.selected_year}")
    else:
        p_data = st.session_state.person_row
        all_hist = st.session_state.search_result
        
        # Debug: Uncomment บรรทัดล่างถ้ายังไม่ขึ้น เพื่อดูว่าข้อมูลมาจริงไหม
        # st.write(p_data) 

        # Tabs Logic
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
            st.warning("ไม่มีข้อมูลการตรวจที่สามารถแสดงผลได้สำหรับปีนี้")
        
        # Print Components (Hidden)
        if st.session_state.get('print_trigger', False):
            h = generate_printable_report(p_data, all_hist)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_trigger = False
        if st.session_state.get('print_performance_trigger', False):
            h = generate_performance_report_html(p_data, all_hist)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_performance_trigger = False


# --------------------------------------------------------------------------------
# MAIN ROUTING LOGIC
# --------------------------------------------------------------------------------

# 1. Initialize Global State
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False

# 2. Load Data (Load once)
df = load_sqlite_data()
if df is None: st.stop()

# 3. Detect LINE UserID (ถ้ามี)
try:
    q_userid = st.query_params.get("userid", "")
    if q_userid:
        st.session_state["line_user_id"] = q_userid
except:
    pass

# LIFF Initializer
try:
    q_page = st.query_params.get("page", "")
    if q_page == "register" and "line_user_id" not in st.session_state:
        liff_initializer_component()
except:
    pass

# 4. Routing Decision (Strict Order)

if not st.session_state['authenticated']:
    # 🔴 1. ยังไม่ Login -> ไปหน้า Login 3 ช่อง
    authentication_flow(df)

elif not st.session_state['pdpa_accepted']:
    # 🟡 2. Login แล้ว แต่ยังไม่ยอมรับ PDPA -> ไปหน้า PDPA
    # (ยกเว้น Admin ให้ข้ามได้เลย)
    if st.session_state.get('is_admin', False):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
    else:
        # User ทั่วไป ต้องเจอหน้านี้ก่อนเสมอ
        pdpa_consent_page()

else:
    # 🔵 3. Login + PDPA แล้ว -> เข้าสู่ระบบหลัก
    if st.session_state.get('is_admin', False):
        display_admin_panel(df)
    else:
        main_app(df)
