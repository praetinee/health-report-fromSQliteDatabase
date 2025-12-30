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

# --- Import Line Register (Modules) ---
from line_register import (
    save_new_user_to_gsheet, 
    check_if_user_registered, 
    normalize_db_name_field,
    render_registration_page,
    render_admin_line_manager
)

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
        is_empty, has_basic_health_data, 
        has_vision_data, has_hearing_data, has_lung_data, has_visualization_data
    )
except Exception as e:
    st.error(f"Error loading utils: {e}")
    # Fallback utils
    def is_empty(v): return pd.isna(v) or str(v).strip() == ""
    def has_basic_health_data(r): return True
    def has_vision_data(r): return False
    def has_hearing_data(r): return False
    def has_lung_data(r): return False
    def has_visualization_data(d): return False

# --- Import Visualization ---
try:
    from visualization import display_visualization_tab
except Exception:
    def display_visualization_tab(d, a): st.info("No visualization module")

# --- Import Shared UI ---
try:
    from shared_ui import (
        inject_custom_css, 
        display_common_header,
        display_main_report, 
        display_performance_report
    )
except Exception as e:
    st.error(f"Critical Error loading shared_ui: {e}")
    def inject_custom_css(): pass
    def display_common_header(data): st.write(f"**รายงานผลสุขภาพ:** {data.get('ชื่อ-สกุล', '-')}")
    def display_main_report(p, a): st.error("Main Report Module Missing")
    def display_performance_report(p, t, a=None): pass

# --- Import Admin Panel ---
try:
    from admin_panel import display_admin_panel
except Exception:
    def display_admin_panel(df): st.error("Admin Panel Error")

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# URL ของ Google Apps Script
GAS_URL = "https://script.google.com/macros/s/AKfycbzmtd5H-YZr8EeeTUab3M2L2nEtUofDBtYCP9-CN6MVfIff94P6lDWS-cUHCi9asLlR/exec"

# ⚠️ ตั้งค่าชื่อคอลัมน์ให้ตรงกับ Database จริง (ตามที่แจนแจ้งมา)
SQLITE_CITIZEN_ID_COL = "เลขบัตรประชาชน"  # ใช้จับคู่กับ card_id ใน Sheet
SQLITE_NAME_COL = "ชื่อ-สกุล"           # ใช้แสดงผลต้อนรับ

def get_user_info_from_gas(line_user_id):
    """ฟังก์ชันสำหรับถาม Google Sheet ว่า UserID นี้คือใคร"""
    try:
        # เพิ่ม timeout ป้องกันการค้าง
        response = requests.get(f"{GAS_URL}?action=get_user&line_id={line_user_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"GAS Network Error: {e}")
        return {"found": False, "error": str(e)}
    except Exception as e:
        print(f"GAS General Error: {e}")
        return {"found": False, "error": str(e)}

# -----------------------------------------------------------------------------
# Data Loading
# -----------------------------------------------------------------------------
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
        
        # Data Cleaning
        df_loaded.columns = df_loaded.columns.str.strip()
        
        def clean_hn(hn_val):
            if pd.isna(hn_val): return ""
            s_val = str(hn_val).strip()
            return s_val[:-2] if s_val.endswith('.0') else s_val
            
        df_loaded['HN'] = df_loaded['HN'].apply(clean_hn)
        
        # Clean ชื่อ-สกุล
        if SQLITE_NAME_COL in df_loaded.columns:
            df_loaded[SQLITE_NAME_COL] = df_loaded[SQLITE_NAME_COL].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        
        # Clean เลขบัตรประชาชน (สำคัญมากสำหรับการจับคู่)
        if SQLITE_CITIZEN_ID_COL in df_loaded.columns:
            df_loaded[SQLITE_CITIZEN_ID_COL] = df_loaded[SQLITE_CITIZEN_ID_COL].astype(str).str.strip()
        else:
            st.error(f"❌ ไม่พบคอลัมน์ '{SQLITE_CITIZEN_ID_COL}' ในฐานข้อมูล SQLite")
            # Debug: แสดงรายชื่อคอลัมน์ที่มีอยู่จริง
            with st.expander("รายชื่อคอลัมน์ทั้งหมดใน Database"):
                st.write(df_loaded.columns.tolist())
            return None
            
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

# -----------------------------------------------------------------------------
# Main App Logic
# -----------------------------------------------------------------------------
def main_app(df):
    inject_custom_css()

    st.markdown("""
    <style>
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #1B5E20 !important; color: #ffffff !important; border: none !important; width: 100%; margin-bottom: 10px;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: #c62828 !important; color: #ffffff !important; border: none !important; width: 100%; margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    if 'user_hn' not in st.session_state: 
        st.error("Error: No user data found in session.")
        st.stop()
        
    user_hn = st.session_state['user_hn']
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    if results_df.empty:
        st.error(f"ไม่พบข้อมูลผลตรวจสำหรับ HN: {user_hn}")
        if st.button("กลับหน้าหลัก"):
            st.session_state.clear()
            st.rerun()
        return

    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    if not available_years:
        st.warning("ไม่พบประวัติการตรวจสุขภาพรายปี")
        return

    if 'selected_year' not in st.session_state or st.session_state.selected_year not in available_years:
        st.session_state.selected_year = available_years[0]

    yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
    if not yr_df.empty:
        person_row = yr_df.bfill().ffill().iloc[0].to_dict()
        st.session_state.person_row = person_row
        st.session_state.selected_row_found = True
    else:
        st.session_state.person_row = None
        st.session_state.selected_row_found = False

    def handle_year_change():
        st.session_state.selected_year = st.session_state.year_select

    with st.sidebar:
        # แสดงชื่อจากตัวแปร SQLITE_NAME_COL (ชื่อ-สกุล)
        user_display_name = st.session_state.get('user_name', '')
        st.markdown(f"<div class='sidebar-title'>ยินดีต้อนรับ</div><h3>{user_display_name}</h3>", unsafe_allow_html=True)
        st.markdown(f"**HN:** {user_hn}")
        st.markdown("---")
        idx = available_years.index(st.session_state.selected_year)
        st.selectbox("เลือกปี พ.ศ.", available_years, index=idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change)
        st.markdown("---")
        if st.session_state.get("selected_row_found", False):
            if st.button("พิมพ์รายงานสุขภาพ", type="primary", use_container_width=True): st.session_state.print_trigger = True
            if st.button("พิมพ์รายงานสมรรถภาพ", type="primary", use_container_width=True): st.session_state.print_performance_trigger = True
        st.markdown("---")
        if st.button("ออกจากระบบ"):
            st.session_state.clear()
            st.rerun()

    if st.session_state.get("person_row") is not None:
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
            st.warning("ไม่พบข้อมูลการตรวจสำหรับหมวดหมู่ที่กำหนด แต่พบประวัติการมาตรวจ")
            display_main_report(p_data, all_hist)

        if st.session_state.get('print_trigger', False):
            h = generate_printable_report(p_data, all_hist)
            escaped_html = json.dumps(h)
            iframe_id = f"print-main-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            print_script = f"""<iframe id="{iframe_id}" style="display:none;"></iframe><script>(function(){{const iframe=document.getElementById('{iframe_id}');if(!iframe)return;const doc=iframe.contentWindow.document;doc.open();doc.write({escaped_html});doc.close();iframe.onload=function(){{setTimeout(function(){{try{{iframe.contentWindow.focus();iframe.contentWindow.print();}}catch(e){{console.error("Print error:",e);}}}},500);}};}})();</script>"""
            st.components.v1.html(print_script, height=0, width=0)
            st.session_state.print_trigger = False
            
        if st.session_state.get('print_performance_trigger', False):
            h = generate_performance_report_html(p_data, all_hist)
            escaped_html = json.dumps(h)
            iframe_id = f"print-perf-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            print_script = f"""<iframe id="{iframe_id}" style="display:none;"></iframe><script>(function(){{const iframe=document.getElementById('{iframe_id}');if(!iframe)return;const doc=iframe.contentWindow.document;doc.open();doc.write({escaped_html});doc.close();iframe.onload=function(){{setTimeout(function(){{try{{iframe.contentWindow.focus();iframe.contentWindow.print();}}catch(e){{console.error("Print error:",e);}}}},500);}};}})();</script>"""
            st.components.v1.html(print_script, height=0, width=0)
            st.session_state.print_performance_trigger = False
    else:
        st.info(f"กำลังโหลดข้อมูลสำหรับปี {st.session_state.selected_year}...")
        st.rerun()

# --------------------------------------------------------------------------------
# MAIN ROUTING LOGIC
# --------------------------------------------------------------------------------

# 1. Initialize State
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False
if 'login_error' not in st.session_state: st.session_state['login_error'] = None 

# 2. Load Data (จาก Google Drive)
df = load_sqlite_data()
if df is None: st.stop()

# 3. Detect LINE UserID & LIFF (Enhanced Auto Login Logic)
query_params = st.query_params
line_user_id = query_params.get("userid")
status = query_params.get("status")

if line_user_id:
    st.session_state["line_user_id"] = line_user_id
    
    if not st.session_state['authenticated']:
        with st.status("กำลังตรวจสอบข้อมูลการลงทะเบียน...", expanded=True) as status_box:
            # 3.1 ถาม Google Sheet
            st.write("1. เชื่อมต่อฐานข้อมูลผู้ใช้ (Google Sheet)...")
            user_info = get_user_info_from_gas(line_user_id)
            
            if user_info.get('found'):
                st.write("✅ พบข้อมูลการลงทะเบียน")
                st.write(f"2. ตรวจสอบเลขบัตรประชาชน: {user_info.get('card_id')}...")
                
                # Clean เลขบัตรจาก Sheet
                card_id_from_sheet = str(user_info['card_id']).strip()
                
                # 3.2 ค้นหาใน SQLite โดยใช้ SQLITE_CITIZEN_ID_COL
                match = df[df[SQLITE_CITIZEN_ID_COL] == card_id_from_sheet]
                
                if not match.empty:
                    st.write("✅ พบประวัติสุขภาพในระบบ")
                    status_box.update(label="เข้าสู่ระบบสำเร็จ!", state="complete", expanded=False)
                    
                    matched_user = match.iloc[0]
                    st.session_state['authenticated'] = True
                    st.session_state['user_hn'] = matched_user['HN']
                    # ใช้ชื่อจาก SQLite (ชื่อ-สกุล) แสดงผล
                    st.session_state['user_name'] = matched_user[SQLITE_NAME_COL]
                    st.session_state['pdpa_accepted'] = True 
                    st.session_state['login_error'] = None
                    
                    if status == "new":
                        st.success(f"ลงทะเบียนสำเร็จ! ยินดีต้อนรับคุณ {matched_user[SQLITE_NAME_COL]}")
                    
                    st.rerun()
                else:
                    error_msg = f"❌ ไม่พบข้อมูลผลตรวจสุขภาพของเลขบัตร {card_id_from_sheet} ในฐานข้อมูลโรงพยาบาล"
                    st.session_state['login_error'] = error_msg
                    status_box.update(label="เกิดข้อผิดพลาด", state="error", expanded=True)
            else:
                error_detail = user_info.get('error', '')
                error_msg = f"❌ ไม่พบข้อมูลการลงทะเบียนของคุณในระบบ (Line User ID นี้ยังไม่ถูกผูกบัญชี) {error_detail}"
                st.session_state['login_error'] = error_msg
                status_box.update(label="ไม่พบข้อมูลลงทะเบียน", state="error", expanded=True)

# 4. Routing Decision (Final)
is_line_mode = "line_user_id" in st.session_state

if not st.session_state['authenticated']:
    if is_line_mode:
        st.warning("⚠️ ไม่สามารถเข้าสู่ระบบอัตโนมัติได้")
        
        if st.session_state.get('login_error'):
            st.error(st.session_state['login_error'])
            st.info("คำแนะนำ: โปรดตรวจสอบว่าท่านกรอกเลขบัตรประชาชนถูกต้อง หรือท่านเคยตรวจสุขภาพกับโรงพยาบาลแล้วหรือไม่")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("ลองลงทะเบียนใหม่"):
                 st.query_params.clear()
                 st.session_state.clear()
                 st.markdown(f'<meta http-equiv="refresh" content="0;url=https://praetinee.github.io/health-report-fromsqlitedatabase/">', unsafe_allow_html=True)
        with col2:
            if st.button("รีเฟรชหน้าจอ"):
                st.rerun()
    else:
        authentication_flow(df)

elif not st.session_state['pdpa_accepted']:
    if st.session_state.get('is_admin', False):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
    else:
        pdpa_consent_page()

else:
    if st.session_state.get('is_admin', False):
        display_admin_panel(df)
    else:
        main_app(df)
