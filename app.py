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
# Configuration & New Helper Functions
# -----------------------------------------------------------------------------

# URL ของ Google Apps Script (ตัวใหม่ที่แจนเพิ่ง Deploy)
GAS_URL = "https://script.google.com/macros/s/AKfycbzmtd5H-YZr8EeeTUab3M2L2nEtUofDBtYCP9-CN6MVfIff94P6lDWS-cUHCi9asLlR/exec"

def get_user_info_from_gas(line_user_id):
    """ฟังก์ชันสำหรับถาม Google Sheet ว่า UserID นี้คือใคร"""
    try:
        response = requests.get(f"{GAS_URL}?action=get_user&line_id={line_user_id}")
        data = response.json()
        return data
    except Exception as e:
        print(f"GAS Connection Error: {e}")
        return {"found": False}

# -----------------------------------------------------------------------------
# Data Loading (คงเดิมจากไฟล์เก่าของแจน)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_sqlite_data():
    tmp_path = None
    try:
        # ใช้ File ID เดิมของแจน
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
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        # แปลงเลขบัตรประชาชนให้เป็น String เพื่อให้ตรงกับการเปรียบเทียบ
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

# -----------------------------------------------------------------------------
# Main App Logic (UI & Features)
# -----------------------------------------------------------------------------
def main_app(df):
    # inject_custom_css ถูกย้ายไปเรียกข้างนอก main_app หรือเรียกซ้ำได้ไม่มีปัญหา
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
    
    # 1. กรองข้อมูลของ User
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    if results_df.empty:
        st.error(f"ไม่พบข้อมูลผลตรวจสำหรับ HN: {user_hn}")
        if st.button("กลับหน้าหลัก"):
            st.session_state.clear()
            st.rerun()
        return

    # 2. หาปีที่มีข้อมูล
    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    if not available_years:
        st.warning("ไม่พบประวัติการตรวจสุขภาพรายปี")
        return

    # 3. เลือกปีล่าสุดอัตโนมัติ
    if 'selected_year' not in st.session_state or st.session_state.selected_year not in available_years:
        st.session_state.selected_year = available_years[0]

    # 4. ดึงข้อมูลปีที่เลือก
    yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
    if not yr_df.empty:
        person_row = yr_df.bfill().ffill().iloc[0].to_dict()
        st.session_state.person_row = person_row
        st.session_state.selected_row_found = True
    else:
        st.session_state.person_row = None
        st.session_state.selected_row_found = False

    # --- Event Handler ---
    def handle_year_change():
        st.session_state.selected_year = st.session_state.year_select

    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"<div class='sidebar-title'>ยินดีต้อนรับ</div><h3>{st.session_state.get('user_name', '')}</h3>", unsafe_allow_html=True)
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

    # --- Main Content Area ---
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

        # --- Print Logic ---
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
# MAIN ROUTING LOGIC (หัวใจสำคัญของการเชื่อมต่อ)
# --------------------------------------------------------------------------------

# 1. Initialize State
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False

# 2. Load Data (จาก Google Drive)
df = load_sqlite_data()
if df is None: st.stop()

# 3. Detect LINE UserID & LIFF (New Auto Login Logic)
# ---------------------------------------------------
# ดึงค่าจาก URL ที่ HTML ส่งมา
query_params = st.query_params
line_user_id = query_params.get("userid")
status = query_params.get("status")

# ถ้ามี UserID ใน URL ให้พยายาม Auto Login
if line_user_id:
    st.session_state["line_user_id"] = line_user_id
    
    # ถ้ายังไม่ Authenticated -> ไปถาม GAS
    if not st.session_state['authenticated']:
        with st.spinner('กำลังยืนยันตัวตน...'):
            user_info = get_user_info_from_gas(line_user_id)
            
            if user_info['found']:
                # ได้เลขบัตรประชาชนมาจาก Google Sheet
                card_id_from_sheet = user_info['card_id']
                
                # เอาไปค้นใน SQLite
                # หมายเหตุ: คอลัมน์ใน SQLite ต้องชื่อ 'เลขบัตรประชาชน' (ตามที่ Load มา)
                match = df[df['เลขบัตรประชาชน'] == str(card_id_from_sheet)]
                
                if not match.empty:
                    # เจอตัวจริง! Login เลย
                    matched_user = match.iloc[0]
                    st.session_state['authenticated'] = True
                    st.session_state['user_hn'] = matched_user['HN']
                    st.session_state['user_name'] = matched_user['ชื่อ-สกุล']
                    st.session_state['pdpa_accepted'] = True 
                    
                    if status == "new":
                        st.success(f"ลงทะเบียนสำเร็จ! ยินดีต้อนรับคุณ {matched_user['ชื่อ-สกุล']}")
                    
                    st.rerun()
                else:
                    st.error(f"ไม่พบข้อมูลผลตรวจสุขภาพของเลขบัตร {card_id_from_sheet} ในระบบ")
                    st.info("หากท่านมั่นใจว่าเคยตรวจสุขภาพแล้ว โปรดติดต่อเจ้าหน้าที่")
            else:
                # กรณีมี ID มา แต่ไม่เจอใน Sheet (แปลกมาก เพราะ HTML เช็คก่อนแล้ว)
                # อาจจะเกิดจาก HTML ส่งมาผิด หรือยังไม่ได้ลงทะเบียน
                pass

# 4. Routing Decision (Final)
is_line_mode = "line_user_id" in st.session_state

if not st.session_state['authenticated']:
    if is_line_mode:
        # ถ้าเข้ามาแบบ LINE แต่ Auto Login ไม่ผ่าน (เช่น ไม่พบเลขบัตรใน SQLite)
        # ให้แสดงหน้าแจ้งเตือน หรือหน้าลงทะเบียนใหม่ (ถ้าจำเป็น)
        st.warning("ไม่สามารถเข้าสู่ระบบอัตโนมัติได้")
        if st.button("ลองลงทะเบียนใหม่อีกครั้ง"):
             # ล้างค่าเพื่อให้กลับไปเริ่มต้นใหม่
             st.query_params.clear()
             st.session_state.clear()
             st.rerun()
    else:
        # เข้าผ่าน Browser ปกติ -> หน้า Login แบบเดิม
        authentication_flow(df)

elif not st.session_state['pdpa_accepted']:
    # ถ้า Login แล้วแต่ยังไม่กด PDPA (เผื่อไว้)
    if st.session_state.get('is_admin', False):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
    else:
        pdpa_consent_page()

else:
    # Login ผ่านหมดแล้ว -> เข้าหน้าแอปหลัก
    if st.session_state.get('is_admin', False):
        display_admin_panel(df)
    else:
        main_app(df)
