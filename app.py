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

# --- Import CSV Saving Function ---
try:
    from line_register import save_new_user_to_csv, liff_initializer_component, check_if_user_registered, normalize_db_name_field
except ImportError:
    # Fallback function
    def save_new_user_to_csv(f, l, uid): return True, "Saved"
    def liff_initializer_component(): pass
    def check_if_user_registered(uid): return False, None
    def normalize_db_name_field(s): return s, ""

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

# --- Import Shared UI (Main Display Logic) ---
# แก้ไข: Import display functions จาก shared_ui แทน admin_panel
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

# --- Main App Logic (แก้ใหม่ให้โหลดข้อมูลชัวร์ๆ) ---
def main_app(df):
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
    inject_custom_css()

    # --- Inject Custom CSS สำหรับปุ่ม Sidebar โดยเฉพาะ ---
    st.markdown("""
    <style>
        /* Styling เฉพาะปุ่ม Primary ใน Sidebar */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(90deg, #00C853 0%, #00796B 100%) !important;
            color: #ffffff !important;
            border: none !important;
            padding: 10px 20px !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            border-radius: 50px !important;
            box-shadow: 0 4px 15px rgba(0, 121, 107, 0.4), inset 0 2px 2px rgba(255, 255, 255, 0.3) !important;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            letter-spacing: 0.5px !important;
            width: 100%;
            margin-bottom: 10px;
            position: relative;
            overflow: hidden;
        }
        
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: linear-gradient(90deg, #00E676 0%, #009688 100%) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(0, 121, 107, 0.5), inset 0 2px 2px rgba(255, 255, 255, 0.5) !important;
        }
        
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:active {
            transform: translateY(1px) !important;
            box-shadow: 0 2px 5px rgba(0, 121, 107, 0.4) !important;
        }

        /* Shine Effect */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]::after {
            content: "";
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: 0.5s;
        }
        
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover::after {
            left: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

    if 'user_hn' not in st.session_state: 
        st.error("Error: No user data found in session.")
        st.stop()
        
    user_hn = st.session_state['user_hn']
    
    # 1. กรองข้อมูลของ User คนนี้ออกมา
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    if results_df.empty:
        st.error(f"ไม่พบข้อมูลผลตรวจสำหรับ HN: {user_hn}")
        if st.button("กลับหน้าหลัก"):
            st.session_state.clear()
            st.rerun()
        return

    # 2. หาปีที่มีข้อมูลทั้งหมด
    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    
    if not available_years:
        st.warning("ไม่พบประวัติการตรวจสุขภาพรายปี")
        return

    # 3. เลือกปีล่าสุดอัตโนมัติ (ถ้ายังไม่ได้เลือก)
    if 'selected_year' not in st.session_state or st.session_state.selected_year not in available_years:
        st.session_state.selected_year = available_years[0]

    # 4. ดึงข้อมูลของปีที่เลือกมาเตรียมไว้ (Important!)
    # ไม่ใช้ Logic เก่าที่ซับซ้อน ดึงตรงๆ เลย
    yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
    if not yr_df.empty:
        # ใช้ bfill/ffill เพื่อรวมข้อมูลถ้ามีหลาย row ในปีเดียว
        person_row = yr_df.bfill().ffill().iloc[0].to_dict()
        st.session_state.person_row = person_row
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
        # ไม่ต้องทำอะไรเพิ่ม เพราะโค้ดด้านบนจะดึงข้อมูลใหม่ให้เองเมื่อ rerun

    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"<div class='sidebar-title'>ยินดีต้อนรับ</div><h3>{st.session_state.get('user_name', '')}</h3>", unsafe_allow_html=True)
        st.markdown(f"**HN:** {user_hn}")
        st.markdown("---")
        
        # Year Selector
        idx = available_years.index(st.session_state.selected_year)
        st.selectbox("เลือกปี พ.ศ.", available_years, index=idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change)
        
        st.markdown("---")
        # ปุ่ม Print (แสดงเฉพาะเมื่อมีข้อมูล)
        if st.session_state.get("selected_row_found", False):
            # ปรับให้ใช้ type="primary" เพื่อรับ CSS สีเขียวหรูหรา
            if st.button("🖨️ พิมพ์รายงานสุขภาพ", type="primary", use_container_width=True): st.session_state.print_trigger = True
            if st.button("🖨️ พิมพ์รายงานสมรรถภาพ", type="primary", use_container_width=True): st.session_state.print_performance_trigger = True
        
        st.markdown("---")
        if st.button("ออกจากระบบ (Logout)"):
            st.session_state.clear()
            st.rerun()

    # --- Main Content Area (แสดงผลทันที!) ---
    # ตัดเงื่อนไขยุ่งยากออก ถ้ามี person_row ให้โชว์เลย
    if st.session_state.get("person_row") is not None:
        p_data = st.session_state.person_row
        all_hist = st.session_state.search_result
        
        # สร้าง Tabs
        tabs_map = OrderedDict()
        
        # ตรวจสอบการแสดงผลกราฟิก (ตอนนี้จะแสดงถ้ามีข้อมูล >= 1 ปี)
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
            # Fallback: ถ้าไม่มีข้อมูลพิเศษเลย ให้โชว์หน้าหลักไว้ก่อน
            display_common_header(p_data)
            st.warning("ไม่พบข้อมูลการตรวจสำหรับหมวดหมู่ที่กำหนด แต่พบประวัติการมาตรวจ")
            display_main_report(p_data, all_hist) # บังคับโชว์

        # Print Components (Hidden)
        if st.session_state.get('print_trigger', False):
            h = generate_printable_report(p_data, all_hist)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_trigger = False
        if st.session_state.get('print_performance_trigger', False):
            h = generate_performance_report_html(p_data, all_hist)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_performance_trigger = False
            
    else:
        # กรณีข้อมูลยังไม่พร้อม (ไม่ควรเกิดขึ้นเพราะเราบังคับโหลดข้างบนแล้ว)
        st.info(f"กำลังโหลดข้อมูลสำหรับปี {st.session_state.selected_year}...")
        st.rerun() # ลองรีเฟรชอีกทีเผื่อพลาด


# --------------------------------------------------------------------------------
# MAIN ROUTING LOGIC
# --------------------------------------------------------------------------------

# 1. Initialize State
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False

# 2. Load Data
df = load_sqlite_data()
if df is None: st.stop()

# 3. Detect LINE UserID
try:
    q_userid = st.query_params.get("userid", "")
    if q_userid:
        st.session_state["line_user_id"] = q_userid

    # Auto Login from CSV
    if st.session_state.get("line_user_id") and not st.session_state['authenticated']:
        is_reg, info = check_if_user_registered(st.session_state["line_user_id"])
        if is_reg:
            found_rows = df[df['ชื่อ-สกุล'].str.contains(info['first_name'], na=False)]
            matched_user = None
            for _, row in found_rows.iterrows():
                db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
                if db_f == info['first_name'] and db_l == info['last_name']:
                    matched_user = row
                    break
            
            if matched_user is not None:
                st.session_state['authenticated'] = True
                st.session_state['user_hn'] = matched_user['HN']
                st.session_state['user_name'] = matched_user['ชื่อ-สกุล']
                st.session_state['pdpa_accepted'] = True 
                st.rerun()

    # LIFF Initializer
    q_page = st.query_params.get("page", "")
    if (q_page == "register" or q_userid) and "line_user_id" not in st.session_state:
        liff_initializer_component()

except Exception as e:
    pass

# 4. Routing Decision

if not st.session_state['authenticated']:
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
