import streamlit as st

# -----------------------------------------------------------------------------
# ⚠️ 1. ต้องใส่ set_page_config เป็นบรรทัดแรกสุดเสมอ
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Health Report System", layout="wide")

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
except Exception:
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
except Exception:
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
# Configuration & Helper Functions
# -----------------------------------------------------------------------------

GAS_URL = "https://script.google.com/macros/s/AKfycbzmtd5H-YZr8EeeTUab3M2L2nEtUofDBtYCP9-CN6MVfIff94P6lDWS-cUHCi9asLlR/exec"
SQLITE_CITIZEN_ID_COL = "เลขบัตรประชาชน"  
SQLITE_NAME_COL = "ชื่อ-สกุล"           

def normalize_cid(val):
    """ฟังก์ชันทำความสะอาดเลขบัตรประชาชนให้เป็นตัวเลข 13 หลักล้วน"""
    if pd.isna(val): return ""
    s = str(val).strip().replace("-", "").replace(" ", "").replace("'", "").replace('"', "")
    if "E" in s or "e" in s:
        try: s = str(int(float(s)))
        except: pass
    if s.endswith(".0"): s = s[:-2]
    return s

def get_user_info_from_gas(line_user_id):
    """ถาม Google Sheet ว่า UserID นี้คือใคร"""
    try:
        url = f"{GAS_URL}?action=get_user&line_id={line_user_id}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
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
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
        st.session_state['debug_tables'] = tables['name'].tolist()
        table_name = "health_data" 
        if table_name not in st.session_state['debug_tables']:
             if len(st.session_state['debug_tables']) > 0: table_name = st.session_state['debug_tables'][0]
        df_loaded = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        conn.close()
        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['HN'] = df_loaded['HN'].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith('.0') else x)
        if SQLITE_NAME_COL in df_loaded.columns:
            df_loaded[SQLITE_NAME_COL] = df_loaded[SQLITE_NAME_COL].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        if SQLITE_CITIZEN_ID_COL in df_loaded.columns:
            df_loaded[SQLITE_CITIZEN_ID_COL] = df_loaded[SQLITE_CITIZEN_ID_COL].apply(normalize_cid)
        df_loaded['Year'] = df_loaded['Year'].astype(int)
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
    if 'user_hn' not in st.session_state: st.stop()
    user_hn = st.session_state['user_hn']
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    if results_df.empty:
        st.error(f"ไม่พบข้อมูลผลตรวจสำหรับ HN: {user_hn}")
        if st.button("กลับหน้าหลัก"): st.session_state.clear(); st.rerun()
        return

    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    if 'selected_year' not in st.session_state or st.session_state.selected_year not in available_years:
        st.session_state.selected_year = available_years[0]

    # --- ส่วน Header ใหม่ (แทน Sidebar) ---
    st.markdown("---") # เส้นคั่นสวยงาม
    col_info, col_year = st.columns([2, 1])
    
    with col_info:
        # 1. เอา Emoji และคำว่า สวัสดี ออก เหลือแค่ คุณ [ชื่อ]
        st.markdown(f"### คุณ {st.session_state.get('user_name', '')}")
        st.caption(f"เลข HN: {user_hn}")

    with col_year:
        st.selectbox(
            "📅 เลือกปี พ.ศ. ที่ตรวจ", 
            available_years, 
            index=available_years.index(st.session_state.selected_year), 
            format_func=lambda y: f"พ.ศ. {y}", 
            key="year_select", 
            on_change=lambda: st.session_state.update({"selected_year": st.session_state.year_select})
        )

    # --- ส่วนเมนูพิมพ์ (ซ่อนใน Expander) ---
    # 2. ปรับ layout ให้ปุ่มไม่ซ้อนทับกัน (ใช้แบบ container ธรรมดาเพื่อให้เรียงลงมา)
    with st.expander("🖨️ เมนูพิมพ์รายงาน (Print Menu)"):
        st.caption("เลือกประเภทรายงานที่ต้องการพิมพ์:")
        
        # ใช้ container ธรรมดาเพื่อให้ปุ่มเรียงแนวตั้งและเต็มความกว้าง (Mobile-Friendly)
        if st.button("พิมพ์รายงานสุขภาพ (Health Report)", type="secondary", use_container_width=True): 
            st.session_state.print_trigger = True
            
        # เว้นระยะห่างเล็กน้อย (ถ้าจำเป็น แต่ st.button ปกติจะมี margin อยู่แล้ว)
        if st.button("พิมพ์รายงานสมรรถภาพ (Performance Report)", type="secondary", use_container_width=True): 
            st.session_state.print_performance_trigger = True
    
    st.markdown("---")

    # --- ส่วนแสดงผลรายงาน ---
    yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
    person_row = yr_df.bfill().ffill().iloc[0].to_dict() if not yr_df.empty else None
    st.session_state.person_row = person_row

    if person_row:
        display_common_header(person_row)
        
        tabs_map = OrderedDict()
        if has_visualization_data(results_df): tabs_map['ภาพรวม (Graphs)'] = 'viz'
        if has_basic_health_data(person_row): tabs_map['สุขภาพพื้นฐาน'] = 'main'
        if has_vision_data(person_row): tabs_map['การมองเห็น'] = 'vision'
        if has_hearing_data(person_row): tabs_map['การได้ยิน'] = 'hearing'
        if has_lung_data(person_row): tabs_map['ปอด'] = 'lung'

        t_objs = st.tabs(list(tabs_map.keys()))
        for i, (k, v) in enumerate(tabs_map.items()):
            with t_objs[i]:
                if v == 'viz': display_visualization_tab(person_row, results_df)
                elif v == 'main': display_main_report(person_row, results_df)
                elif v == 'vision': display_performance_report(person_row, 'vision')
                elif v == 'hearing': display_performance_report(person_row, 'hearing', all_person_history_df=results_df)
                elif v == 'lung': display_performance_report(person_row, 'lung')

        # Print Logic
        if st.session_state.get('print_trigger'):
            h = generate_printable_report(person_row, results_df)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_trigger = False
        if st.session_state.get('print_performance_trigger'):
            h = generate_performance_report_html(person_row, results_df)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_performance_trigger = False

# --------------------------------------------------------------------------------
# MAIN ROUTING LOGIC
# --------------------------------------------------------------------------------

if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False

df = load_sqlite_data()
if df is None: st.stop()

# --- Auto-Login Logic ---
query_params = st.query_params
line_user_id = query_params.get("userid")

if line_user_id and not st.session_state['authenticated']:
    st.session_state["line_user_id"] = line_user_id
    st.info("⏳ กำลังตรวจสอบสิทธิ์การใช้งาน LINE...")
    
    u_info = get_user_info_from_gas(line_user_id)
    
    if u_info.get('found'):
        cid = normalize_cid(u_info.get('card_id'))
        fname = u_info.get('fname', '').strip()
        lname = u_info.get('lname', '').strip()
        
        # ค้นหาในฐานข้อมูล
        match = df[df[SQLITE_CITIZEN_ID_COL] == cid]
        user_found = None
        if not match.empty:
            if fname and lname:
                for _, row in match.iterrows():
                    db_f, db_l = normalize_db_name_field(row[SQLITE_NAME_COL])
                    if db_f == fname and db_l.replace(" ","") == lname.replace(" ",""):
                        user_found = row; break
            if user_found is None: user_found = match.iloc[0]
        
        if user_found is not None:
            st.session_state.update({
                'authenticated': True, 
                'user_hn': user_found['HN'], 
                'user_name': user_found[SQLITE_NAME_COL], 
                'pdpa_accepted': True
            })
            st.rerun()
        else:
            st.session_state['login_error'] = f"❌ ไม่พบประวัติสุขภาพของเลขบัตร '{cid}' ในระบบโรงพยาบาล"
    else:
        st.session_state['login_error'] = "❌ ไม่พบข้อมูลการลงทะเบียนของคุณในระบบ LINE"

# --- Final Decision ---
if not st.session_state['authenticated']:
    if st.session_state.get('login_error'):
        st.error(st.session_state['login_error'])
        if st.button("เข้าสู่ระบบด้วยชื่อ-นามสกุล"):
            del st.session_state["line_user_id"]
            del st.session_state["login_error"]
            st.rerun()
    else:
        authentication_flow(df)
elif not st.session_state['pdpa_accepted']:
    pdpa_consent_page()
else:
    if st.session_state.get('is_admin'): display_admin_panel(df)
    else: main_app(df)
