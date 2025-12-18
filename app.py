import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html
import numpy as np
from collections import OrderedDict
from datetime import datetime
import re
import os
import json
from streamlit_js_eval import streamlit_js_eval

# --- Import Authentication ---
from auth import authentication_flow, pdpa_consent_page

# --- Import New Line Register Module ---
from line_register import render_registration_page

# --- Import Print Functions ---
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html

# --- Import Admin Panel and SHARED UI functions FROM admin_panel ---
from admin_panel import (
    display_admin_panel,
    is_empty,
    normalize_name,
    inject_custom_css,
    display_common_header,
    has_basic_health_data,
    has_vision_data,
    has_hearing_data,
    has_lung_data,
    has_visualization_data,
    display_main_report,
    display_performance_report,
    display_visualization_tab
)

# --- ค่าคงที่ (Constants) ---
THAI_MONTHS_GLOBAL = {1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน", 5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม", 9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {"ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2, "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4, "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6, "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8, "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10, "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12}


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
            if s_val.endswith('.0'): return s_val[:-2]
            return s_val

        df_loaded['HN'] = df_loaded['HN'].apply(clean_hn)
        # Clean Data เบื้องต้น
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        # สำคัญ: บังคับให้เลขบัตรประชาชนเป็น String และ Trim space
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# --- Main Application Logic Wrapper for Regular Users ---
def main_app(df):
    """
    This function contains the main application logic for displaying health reports for regular users.
    It's called after the user has successfully logged in and accepted the PDPA consent.
    """
    st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

    inject_custom_css() # Use inject_custom_css from admin_panel (where it's now defined)

    # --- Logic to handle data for the logged-in user ---
    if 'user_hn' not in st.session_state:
        st.error("เกิดข้อผิดพลาด: ไม่พบข้อมูลผู้ใช้")
        st.stop()

    user_hn = st.session_state['user_hn']
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    def handle_year_change():
        st.session_state.selected_year = st.session_state.year_select
        st.session_state.pop("person_row", None)
        st.session_state.pop("selected_row_found", None)

    # Initialize states for the logged-in user
    if 'selected_year' not in st.session_state: st.session_state.selected_year = None
    if 'print_trigger' not in st.session_state: st.session_state.print_trigger = False
    if 'print_performance_trigger' not in st.session_state: st.session_state.print_performance_trigger = False

    with st.sidebar:
        # --- Display user info ---
        st.markdown(f"<div class='sidebar-title'>ยินดีต้อนรับ</div><h3>{st.session_state.get('user_name', '')}</h3>", unsafe_allow_html=True)
        st.markdown(f"**HN:** {st.session_state.get('user_hn', '')}")
        st.markdown("---")

        if not results_df.empty:
            available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
            if available_years:
                if st.session_state.selected_year not in available_years:
                    st.session_state.selected_year = available_years[0]

                year_idx = available_years.index(st.session_state.selected_year)
                st.selectbox("เลือกปี พ.ศ. ที่ต้องการดูผลตรวจ", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change)

                person_year_df = results_df[results_df["Year"] == st.session_state.selected_year]

                if not person_year_df.empty:
                    merged_series = person_year_df.bfill().ffill().iloc[0]
                    st.session_state.person_row = merged_series.to_dict()
                    st.session_state.selected_row_found = True
                else:
                     st.session_state.pop("person_row", None)
                     st.session_state.pop("selected_row_found", None)
            else:
                st.warning("ไม่พบข้อมูลรายปี")
                st.session_state.pop("person_row", None)
                st.session_state.pop("selected_row_found", None)
        else:
            st.warning("ไม่พบข้อมูลสำหรับผู้ใช้นี้")
            st.session_state.pop("person_row", None)
            st.session_state.pop("selected_row_found", None)

        # --- Print Buttons ---
        st.markdown("---")
        st.markdown('<div class="sidebar-title" style="font-size: 1.2rem; margin-top: 1rem;">พิมพ์รายงาน</div>', unsafe_allow_html=True)
        if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
            if st.button("พิมพ์รายงานสุขภาพ", use_container_width=True):
                 st.session_state.print_trigger = True
            if st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True):
                st.session_state.print_performance_trigger = True
        else:
            st.button("พิมพ์รายงานสุขภาพ", use_container_width=True, disabled=True)
            st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True, disabled=True)

        # --- Logout Button ---
        st.markdown("---")
        if st.button("ออกจากระบบ (Logout)", use_container_width=True):
            keys_to_clear = [
                'authenticated', 'pdpa_accepted', 'user_hn', 'user_name', 'is_admin',
                'search_result', 'selected_year', 'person_row', 'selected_row_found',
                'admin_search_term', 'admin_search_results', 'admin_selected_hn',
                'admin_selected_year', 'admin_person_row', 'line_register_success', 'line_registered_user'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # --- Main Page Content ---
    if "person_row" not in st.session_state or not st.session_state.get("selected_row_found", False):
        st.info("กรุณาเลือกปีที่ต้องการดูผลตรวจจากเมนูด้านข้าง")
    else:
        person_data = st.session_state.person_row
        all_person_history_df = st.session_state.search_result

        # --- Determine available report tabs ---
        available_reports = OrderedDict()
        # Use functions imported from admin_panel (where they are now defined)
        if has_visualization_data(all_person_history_df): available_reports['ภาพรวมสุขภาพ (Graphs)'] = 'visualization_report'
        if has_basic_health_data(person_data): available_reports['สุขภาพพื้นฐาน'] = 'main_report'
        if has_vision_data(person_data): available_reports['สมรรถภาพการมองเห็น'] = 'vision_report'
        if has_hearing_data(person_data): available_reports['สมรรถภาพการได้ยิน'] = 'hearing_report'
        if has_lung_data(person_data): available_reports['สมรรถภาพปอด'] = 'lung_report'

        # --- Display Header and Tabs ---
        if not available_reports:
            display_common_header(person_data)
            st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับปีที่เลือก")
        else:
            display_common_header(person_data)
            tabs = st.tabs(list(available_reports.keys()))

            # --- Render Content for Each Tab ---
            for i, (tab_title, page_key) in enumerate(available_reports.items()):
                with tabs[i]:
                    if page_key == 'visualization_report':
                        display_visualization_tab(person_data, all_person_history_df)
                    elif page_key == 'vision_report':
                        display_performance_report(person_data, 'vision')
                    elif page_key == 'hearing_report':
                        display_performance_report(person_data, 'hearing', all_person_history_df=all_person_history_df)
                    elif page_key == 'lung_report':
                        display_performance_report(person_data, 'lung')
                    elif page_key == 'main_report':
                        display_main_report(person_data, all_person_history_df)

        # --- Print Logic ---
        if st.session_state.get("print_trigger", False):
            report_html_data = generate_printable_report(person_data, all_person_history_df)
            escaped_html = json.dumps(report_html_data)
            iframe_id = f"print-iframe-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            print_component = f"""
            <iframe id="{iframe_id}" style="display:none;"></iframe>
            <script>
                (function() {{
                    const iframe = document.getElementById('{iframe_id}');
                    if (!iframe) return;
                    const iframeDoc = iframe.contentWindow.document;
                    iframeDoc.open();
                    iframeDoc.write({escaped_html});
                    iframeDoc.close();
                    iframe.onload = function() {{ setTimeout(function() {{ try {{ iframe.contentWindow.focus(); iframe.contentWindow.print(); }} catch (e) {{ console.error("Printing failed:", e); }} }}, 500); }};
                }})();
            </script>
            """
            st.components.v1.html(print_component, height=0, width=0)
            st.session_state.print_trigger = False

        if st.session_state.get("print_performance_trigger", False):
            report_html_data = generate_performance_report_html(person_data, all_person_history_df)
            escaped_html = json.dumps(report_html_data)
            iframe_id = f"print-perf-iframe-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            print_component = f"""
            <iframe id="{iframe_id}" style="display:none;"></iframe>
            <script>
                (function() {{
                    const iframe = document.getElementById('{iframe_id}');
                    if (!iframe) return;
                    const iframeDoc = iframe.contentWindow.document;
                    iframeDoc.open();
                    iframeDoc.write({escaped_html});
                    iframeDoc.close();
                    iframe.onload = function() {{ setTimeout(function() {{ try {{ iframe.contentWindow.focus(); iframe.contentWindow.print(); }} catch (e) {{ console.error("Printing performance report failed:", e); }} }}, 500); }};
                }})();
            </script>
            """
            st.components.v1.html(print_component, height=0, width=0)
            st.session_state.print_performance_trigger = False

# --- Main Logic to control page flow ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state:
    st.session_state['pdpa_accepted'] = False
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

# Load data once
df = load_sqlite_data()
if df is None:
    st.error("ไม่สามารถโหลดฐานข้อมูลได้ กรุณาลองอีกครั้งในภายหลัง")
    st.stop()

# --- เช็ค Query Parameter ว่าจะเข้าหน้าลงทะเบียน (LINE Register) หรือไม่ ---
# ใน LINE Rich Menu ให้ใส่ Link เป็น: https://your-app-url.streamlit.app/?page=register
try:
    query_params = st.query_params 
    page_param = query_params.get("page", "")
except:
    page_param = ""

# --- Routing Logic ---
if page_param == "register":
    # 1. เข้าสู่โหมดลงทะเบียน LINE (แยกโมดูลตามที่ขอ)
    render_registration_page(df)

elif not st.session_state['authenticated']:
    # 2. เข้าสู่โหมด Login ปกติ (Desktop/Web)
    
    # เพิ่มตัวเลือกเล็กๆ ด้านบนเผื่อกด Test ใน Dev Mode
    if st.checkbox("ทดสอบโหมดลงทะเบียน LINE OA (Dev Only)", value=False):
        render_registration_page(df)
    else:
        authentication_flow(df)

elif not st.session_state['pdpa_accepted']:
    # 3. ผ่าน Login แล้วแต่ยังไม่ยอมรับ PDPA (กรณี Web Login)
    if st.session_state.get('is_admin', False):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
    else:
        pdpa_consent_page()
else:
    # 4. เข้าสู่ระบบสำเร็จ (แสดง Admin หรือ User Report)
    if st.session_state.get('is_admin', False):
        display_admin_panel(df) 
    else:
        main_app(df)
