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

# --- Import Library สำหรับเช็คหน้าจอ ---
try:
    from streamlit_js_eval import streamlit_js_eval
except ImportError:
    # Fallback ถ้าไม่มี library
    def streamlit_js_eval(**kwargs): return 1200 # สมมติว่าเป็น Desktop ไว้ก่อน

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
        display_main_report, 
        display_performance_report,
        # เราจะไม่ใช้ display_common_header ตัวเดิมแล้ว เพราะจะสร้างใหม่ในนี้เพื่อแทรกปุ่ม
        get_float 
    )
except Exception:
    def inject_custom_css(): pass
    def display_main_report(p, a): st.error("Main Report Module Missing")
    def display_performance_report(p, t, a=None): pass
    def get_float(c, p): return None

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

# --- Custom Header Function (เพื่อการจัดวางตามต้องการ) ---
def render_custom_header_with_actions(person_data, available_years):
    # เตรียมข้อมูล
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    # แก้ไข: เปลี่ยน person.get เป็น person_data.get เพื่อแก้ NameError
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    
    # ไอคอน SVG (คัดลอกมาจาก shared_ui เพื่อความสวยงามเหมือนเดิม)
    icon_profile = """<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>"""
    icon_body = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>"""
    icon_waist = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M8 12h8"></path></svg>"""
    icon_heart = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>"""
    icon_pulse = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>"""

    # Vitals Calculations
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", 0))), int(float(person_data.get("DBP", 0)))
        bp_val = f"{sbp_int}/{dbp_int}"
        # Simple Interpretation
        if sbp_int >= 140 or dbp_int >= 90: bp_desc = "ความดันสูง"
        elif sbp_int < 120 and dbp_int < 80: bp_desc = "ความดันปกติ"
        else: bp_desc = "ความดันค่อนข้างสูง"
    except:
        bp_val = "-"
        bp_desc = "ไม่มีข้อมูล"
        
    try: pulse_val = f"{int(float(person_data.get('pulse', 0)))}"
    except: pulse_val = "-"
    
    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight}" if weight is not None else "-"
    height_val = f"{height}" if height is not None else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')}"
    
    bmi_val_str = "-"
    bmi_desc = ""
    if weight is not None and height is not None and height > 0:
        bmi = weight / ((height / 100) ** 2)
        bmi_val_str = f"{bmi:.1f}"
        if bmi < 18.5: bmi_desc = "น้ำหนักน้อย"
        elif 18.5 <= bmi < 23: bmi_desc = "น้ำหนักปกติ"
        elif 23 <= bmi < 25: bmi_desc = "น้ำหนักเกิน"
        elif 25 <= bmi < 30: bmi_desc = "อ้วน"
        elif bmi >= 30: bmi_desc = "อ้วนอันตราย"

    # --- Render Container ---
    with st.container():
        # c1 = ซ้าย (ข้อมูลส่วนตัว + ปุ่ม), c2 = ขวา (วันที่ + Dropdown)
        c1, c2 = st.columns([3, 1.3])
        
        with c1:
            st.markdown(f"""
            <div style="display: flex; gap: 15px; align-items: flex-start;">
                <div style="min-width: 60px; height: 60px; background-color: rgba(0, 121, 107, 0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #00796B;">
                    {icon_profile}
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold; line-height: 1.2;">{name}</div>
                    <div style="font-size: 0.95rem; opacity: 0.8; margin-top: 4px;">
                        HN: {hn} | เพศ: {sex} | อายุ: {age} ปี
                    </div>
                    <div style="background-color: rgba(128,128,128,0.1); padding: 2px 10px; border-radius: 4px; display: inline-block; font-size: 0.85rem; margin-top: 6px; font-weight: 500;">
                        หน่วยงาน: {department}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
            
            # --- ปุ่มพิมพ์ ---
            # ใช้ st.columns เพื่อสร้าง Grid ให้ปุ่ม
            cb1, cb2, cb_rest = st.columns([1.2, 1.2, 2.5])
            with cb1:
                if st.button("🖨️ ผลสุขภาพ", key="hdr_print_h", use_container_width=True):
                    st.session_state.print_trigger = True
            with cb2:
                if st.button("🖨️ ผลสมรรถภาพ", key="hdr_print_p", use_container_width=True):
                    st.session_state.print_performance_trigger = True
            
            # --- ส่วนแจ้งเตือนสำหรับมือถือ (แสดงตลอดเวลา) ---
            # ข้อความแจ้งเตือน: จัดรูปแบบชิดซ้ายเพื่อป้องกันการแสดงเป็น Code block
            st.markdown("""
<style>
.mobile-print-note-container {
    display: block !important;
    width: 100%;
    margin-top: 0px;
}
.mobile-print-note {
    background: linear-gradient(to right, #fff3cd, #ffffff) !important;
    border: none !important;
    border-left: 5px solid #ffc107 !important;
    color: #856404;
    font-size: 0.75rem;
    font-weight: 400;
    padding: 5px 10px;
    width: 100%;
    max-width: 300px;
    margin-left: 2px;
    line-height: 1.2;
    border-radius: 4px;
}
</style>
<div class="mobile-print-note-container">
    <div class="mobile-print-note">
    ฟังก์ชันพิมพ์ รองรับการใช้งานผ่านคอมพิวเตอร์ (PC) เท่านั้น
    </div>
</div>
""", unsafe_allow_html=True)
            # --------------------------------------------------------

        with c2:
            st.markdown(f"""
            <div style="text-align: right; color: var(--text-color);">
                <div style="font-size: 0.95rem; font-weight: bold; margin-bottom: 2px;">วันที่ตรวจ: {check_date}</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">คลินิกตรวจสุขภาพ</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">อาชีวเวชกรรม</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">รพ.สันทราย</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)
            st.selectbox(
                "เลือกปี พ.ศ.", 
                available_years, 
                index=available_years.index(st.session_state.selected_year), 
                format_func=lambda y: f"พ.ศ. {y}", 
                key="year_select", 
                on_change=lambda: st.session_state.update({"selected_year": st.session_state.year_select}),
                label_visibility="collapsed" # ซ่อน Label เพื่อความสวยงาม (เพราะอยู่ใต้กลุ่มวันที่แล้ว)
            )

        # เส้นคั่นบางๆ ก่อนส่วน Vitals
        st.markdown('<hr style="margin: 15px 0; border: 0; border-top: 1px solid rgba(128,128,128,0.2);">', unsafe_allow_html=True)

        # 5. Vitals Grid (ส่วนล่าง)
        # ใช้ HTML/CSS Grid เพื่อความสวยงามเหมือนเดิม
        st.markdown(f"""
        <div class="vitals-grid-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;">
            <div class="vital-card" style="background: var(--card-bg-color); border-radius: 8px; padding: 15px; display: flex; align-items: center; gap: 10px; border: 1px solid rgba(128,128,128,0.2);">
                <div class="vital-icon-box" style="color: #2196F3;">{icon_body}</div>
                <div class="vital-content">
                    <div class="vital-label" style="font-size: 0.8rem; opacity: 0.7;">สัดส่วนร่างกาย</div>
                    <div class="vital-value" style="font-size: 1.1rem; font-weight: bold;">{weight_val} <span style="font-size:0.8rem; font-weight:normal;">kg</span> / {height_val} <span style="font-size:0.8rem; font-weight:normal;">cm</span></div>
                    <div class="vital-sub" style="font-size: 0.75rem; opacity: 0.8;">BMI: {bmi_val_str} ({bmi_desc})</div>
                </div>
            </div>
            <div class="vital-card" style="background: var(--card-bg-color); border-radius: 8px; padding: 15px; display: flex; align-items: center; gap: 10px; border: 1px solid rgba(128,128,128,0.2);">
                <div class="vital-icon-box" style="color: #4CAF50;">{icon_waist}</div>
                <div class="vital-content">
                    <div class="vital-label" style="font-size: 0.8rem; opacity: 0.7;">รอบเอว</div>
                    <div class="vital-value" style="font-size: 1.1rem; font-weight: bold;">{waist_val} <span style="font-size:0.8rem; font-weight:normal;">cm</span></div>
                </div>
            </div>
            <div class="vital-card" style="background: var(--card-bg-color); border-radius: 8px; padding: 15px; display: flex; align-items: center; gap: 10px; border: 1px solid rgba(128,128,128,0.2);">
                <div class="vital-icon-box" style="color: #F44336;">{icon_heart}</div>
                <div class="vital-content">
                    <div class="vital-label" style="font-size: 0.8rem; opacity: 0.7;">ความดันโลหิต</div>
                    <div class="vital-value" style="font-size: 1.1rem; font-weight: bold;">{bp_val} <span style="font-size:0.8rem; font-weight:normal;">mmHg</span></div>
                    <div class="vital-sub" style="font-size: 0.75rem; opacity: 0.8;">{bp_desc}</div>
                </div>
            </div>
            <div class="vital-card" style="background: var(--card-bg-color); border-radius: 8px; padding: 15px; display: flex; align-items: center; gap: 10px; border: 1px solid rgba(128,128,128,0.2);">
                <div class="vital-icon-box" style="color: #FF9800;">{icon_pulse}</div>
                <div class="vital-content">
                    <div class="vital-label" style="font-size: 0.8rem; opacity: 0.7;">ชีพจร</div>
                    <div class="vital-value" style="font-size: 1.1rem; font-weight: bold;">{pulse_val} <span style="font-size:0.8rem; font-weight:normal;">bpm</span></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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

    # --- ส่วน CSS/JS สำหรับซ่อนปุ่มพิมพ์บนมือถือ ---
    # ลบส่วนนี้ออกแล้วตามที่ต้องการ

    # --- ส่วนแสดงผลรายงาน ---
    yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
    person_row = yr_df.bfill().ffill().iloc[0].to_dict() if not yr_df.empty else None
    st.session_state.person_row = person_row

    if person_row:
        # ใช้ Custom Header ที่เราสร้างขึ้นใหม่แทน display_common_header เดิม
        render_custom_header_with_actions(person_row, available_years)
        
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
