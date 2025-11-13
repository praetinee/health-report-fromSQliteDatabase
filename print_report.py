import streamlit as st
import pandas as pd
from collections import OrderedDict
import json
from datetime import datetime
import re # Add re import
import html # Add html import
import numpy as np # Add numpy import

# --- Import ฟังก์ชันจากไฟล์อื่นที่จำเป็น ---

# --- START: Import ฟังก์ชันที่ย้ายไป shared_ui.py ---
from shared_ui import (
    is_empty,
    normalize_name,
    get_float,
    flag,
    render_section_header,
    render_lab_table_html,
    safe_text,
    safe_value,
    parse_range_or_number,
    interpret_rbc,
    interpret_wbc,
    is_urine_abnormal,
    render_urine_section,
    interpret_stool_exam,
    interpret_stool_cs,
    render_stool_html_table,
    get_ekg_col_name,
    interpret_ekg,
    hepatitis_b_advice,
    has_basic_health_data,
    has_vision_data,
    has_hearing_data,
    has_lung_data,
    has_visualization_data,
    interpret_bp,
    interpret_cxr,
    interpret_bmi,
    display_common_header,
    inject_custom_css,
    display_performance_report_hearing,
    display_performance_report_lung,
    display_performance_report_vision,
    render_vision_details_table,
    display_performance_report,
    display_main_report,
    display_visualization_tab
)
# --- END: Import ฟังก์ชันที่ย้ายไป shared_ui.py ---

# --- START: Import ฟังก์ชันสำหรับพิมพ์ (เดี่ยว) ---
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html
# --- END: Import ฟังก์ชันสำหรับพิมพ์ (เดี่ยว) ---

# --- START: Import ฟังก์ชันสำหรับพิมพ์ (ชุด) ---
from batch_print import display_batch_print_ui
# --- END: Import ฟังก์ชันสำหรับพิมพ์ (ชุด) ---


def display_admin_panel(df):
    """
    แสดงหน้าจอหลักสำหรับ Admin (Search Panel)
    """
    st.set_page_config(page_title="Admin Panel", layout="wide")
    inject_custom_css()

    # --- Initialize session state keys for admin search ---
    if 'admin_search_term' not in st.session_state:
        st.session_state.admin_search_term = ""
    if 'admin_search_results' not in st.session_state:
        st.session_state.admin_search_results = None # Stores the search result DF
    if 'admin_selected_hn' not in st.session_state:
        st.session_state.admin_selected_hn = None
    if 'admin_selected_year' not in st.session_state:
        st.session_state.admin_selected_year = None
    if 'admin_print_trigger' not in st.session_state:
        st.session_state.admin_print_trigger = False
    if 'admin_print_performance_trigger' not in st.session_state:
        st.session_state.admin_print_performance_trigger = False
    if "admin_person_row" not in st.session_state:
        st.session_state.admin_person_row = None
        
    # --- START: Add keys for batch printing ---
    if 'batch_print_trigger' not in st.session_state:
        st.session_state.batch_print_trigger = False
    if 'batch_print_html_content' not in st.session_state:
        st.session_state.batch_print_html_content = None
    # --- END: Add keys for batch printing ---


    with st.sidebar:
        # --- START OF CHANGE: Added emoji ---
        st.markdown("<div class='sidebar-title'>👑 Admin Panel</div>", unsafe_allow_html=True)
        # --- END OF CHANGE ---

        # --- Search Form ---
        with st.form(key="admin_search_form"):
            search_term = st.text_input(
                "ค้นหา (ชื่อ-สกุล, HN, หรือ เลขบัตร)",
                value=st.session_state.admin_search_term
            )
            submitted = st.form_submit_button("ค้นหา")

            if submitted:
                st.session_state.admin_search_term = search_term
                if search_term:
                    normalized_search = normalize_name(search_term) # Use imported normalize_name
                    # ค้นหาในทั้ง 3 คอลัมน์
                    search_mask = (
                        df['ชื่อ-สกุล'].apply(normalize_name).str.contains(normalized_search, case=False, na=False) |
                        (df['HN'].astype(str) == search_term) |
                        (df['เลขบัตรประชาชน'].astype(str) == search_term)
                    )
                    results_df = df[search_mask]

                    if not results_df.empty:
                        # ดึง HN ที่ไม่ซ้ำกัน
                        unique_hns = results_df['HN'].unique()
                        # เก็บข้อมูล *ทั้งหมด* ของ HN ที่พบ
                        st.session_state.admin_search_results = df[df['HN'].isin(unique_hns)].copy()

                        if len(unique_hns) == 1:
                            st.session_state.admin_selected_hn = unique_hns[0]
                        else:
                            st.session_state.admin_selected_hn = None # บังคับให้เลือก
                    else:
                        st.session_state.admin_search_results = pd.DataFrame() # Empty df
                        st.session_state.admin_selected_hn = None
                else:
                    st.session_state.admin_search_results = None
                    st.session_state.admin_selected_hn = None

                # Reset ค่าเมื่อค้นหาใหม่
                st.session_state.admin_selected_year = None
                st.session_state.admin_person_row = None
                st.rerun()

        # --- Display search results / selection ---
        if st.session_state.admin_search_results is not None:
            if st.session_state.admin_search_results.empty:
                st.warning("ไม่พบข้อมูล")
            else:
                # สร้าง list ผู้ป่วยที่ไม่ซ้ำกัน
                # --- FIX: Sort by 'ชื่อ-สกุล' before presenting ---
                unique_results = st.session_state.admin_search_results.drop_duplicates(subset=['HN']).sort_values(by='ชื่อ-สกุล').set_index('HN')

                if len(unique_results) > 1:
                    st.info(f"พบ {len(unique_results)} คน กรุณาเลือก:")
                    options = {hn: f"{row['ชื่อ-สกุล']} (HN: {hn})" for hn, row in unique_results.iterrows()}

                    current_hn = st.session_state.admin_selected_hn
                    hn_list = list(options.keys())
                    
                    # Set default index to 0 if current_hn is not in the list
                    index = 0
                    if current_hn in hn_list:
                        index = hn_list.index(current_hn)
                    elif hn_list: # If list is not empty
                         st.session_state.admin_selected_hn = hn_list[0] # Select first item

                    selected_hn = st.selectbox(
                        "เลือกผู้ป่วย",
                        options=hn_list,
                        format_func=lambda hn: options.get(hn, hn), # Use .get for safety
                        index=index,
                        key="admin_select_hn_box"
                    )
                    # ถ้ามีการเปลี่ยน selection
                    if selected_hn != st.session_state.admin_selected_hn:
                        st.session_state.admin_selected_hn = selected_hn
                        st.session_state.admin_selected_year = None # Reset ปี
                        st.session_state.admin_person_row = None
                        st.rerun()
                elif len(unique_results) == 1 and st.session_state.admin_selected_hn is None:
                     # Auto-select if only one result
                     st.session_state.admin_selected_hn = unique_results.index[0]
                     st.rerun()


                # --- Year selection (แสดงเมื่อเลือกผู้ป่วยแล้ว) ---
                if st.session_state.admin_selected_hn:
                    hn_to_load = st.session_state.admin_selected_hn
                    all_person_history_df = df[df['HN'] == hn_to_load].copy()

                    available_years = sorted(all_person_history_df["Year"].dropna().unique().astype(int), reverse=True)

                    if available_years:
                        # ตั้งค่าปี default ถ้ายังไม่ได้เลือก
                        if st.session_state.admin_selected_year not in available_years:
                            st.session_state.admin_selected_year = available_years[0]

                        year_idx = available_years.index(st.session_state.admin_selected_year)

                        selected_year = st.selectbox(
                            "เลือกปี พ.ศ. ที่ต้องการดูผลตรวจ",
                            options=available_years,
                            index=year_idx,
                            format_func=lambda y: f"พ.ศ. {y}",
                            key="admin_year_select"
                        )

                        # ถ้าเปลี่ยนปี
                        if selected_year != st.session_state.admin_selected_year:
                            st.session_state.admin_selected_year = selected_year
                            st.session_state.admin_person_row = None # บังคับให้โหลดข้อมูลใหม่
                            st.rerun()

                        # โหลดข้อมูลของปีที่เลือก
                        if st.session_state.admin_person_row is None:
                            person_year_df = all_person_history_df[all_person_history_df["Year"] == st.session_state.admin_selected_year]
                            if not person_year_df.empty:
                                merged_series = person_year_df.bfill().ffill().iloc[0]
                                st.session_state.admin_person_row = merged_series.to_dict()
                            else:
                                st.session_state.admin_person_row = {} # Empty dict
                    else:
                        st.error("ผู้ป่วยนี้ไม่มีข้อมูลรายปี")
                        st.session_state.admin_person_row = None

                # --- Print Buttons for Admin (Single) ---
                st.markdown("---")
                st.markdown('<div class="sidebar-title" style="font-size: 1.2rem; margin-top: 1rem;">พิมพ์รายงาน (รายคน)</div>', unsafe_allow_html=True)
                if st.session_state.admin_person_row:
                    st.markdown(f"**กำลังเลือก:** {st.session_state.admin_person_row.get('ชื่อ-สกุล', '')} (ปี {st.session_state.admin_selected_year})")
                    if st.button("พิมพ์รายงานสุขภาพ", use_container_width=True, key="admin_print_main"):
                        st.session_state.admin_print_trigger = True
                    if st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True, key="admin_print_perf"):
                        st.session_state.admin_print_performance_trigger = True
                else:
                    st.button("พิมพ์รายงานสุขภาพ", use_container_width=True, disabled=True)
                    st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True, disabled=True)

        # --- START: Add Batch Print UI ---
        st.markdown("---")
        display_batch_print_ui(df) # เรียกใช้ UI จาก batch_print.py
        # --- END: Add Batch Print UI ---

        st.markdown("---")
        # --- Logout Button ---
        if st.button("ออกจากระบบ (Logout)", use_container_width=True):
            keys_to_clear = [
                'authenticated', 'pdpa_accepted', 'user_hn', 'user_name', 'is_admin',
                'search_result', 'selected_year', 'person_row', 'selected_row_found',
                'admin_search_term', 'admin_search_results', 'admin_selected_hn',
                'admin_selected_year', 'admin_person_row',
                'batch_print_trigger', 'batch_print_html_content' # Clear batch print states
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # --- Main Page (for Admin) ---
    if not st.session_state.admin_person_row:
        st.info("กรุณาค้นหาและเลือกผู้ป่วยจากเมนูด้านข้าง")
    else:
        person_data = st.session_state.admin_person_row
        # Ensure we always fetch the full history for the selected HN for display functions
        all_person_history_df_admin = df[df['HN'] == st.session_state.admin_selected_hn].copy()


        # --- ใช้ฟังก์ชันแสดงผลเดียวกับของผู้ใช้ ---
        available_reports = OrderedDict()
        if has_visualization_data(all_person_history_df_admin): available_reports['ภาพรวมสุขภาพ (Graphs)'] = 'visualization_report'
        if has_basic_health_data(person_data): available_reports['สุขภาพพื้นฐาน'] = 'main_report'
        if has_vision_data(person_data): available_reports['สมรรถภาพการมองเห็น'] = 'vision_report'
        if has_hearing_data(person_data): available_reports['สมรรถภาพการได้ยิน'] = 'hearing_report'
        if has_lung_data(person_data): available_reports['สมรรถภาพปอด'] = 'lung_report'

        if not available_reports:
            display_common_header(person_data)
            st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับปีที่เลือก")
        else:
            display_common_header(person_data)
            tabs = st.tabs(list(available_reports.keys()))

            for i, (tab_title, page_key) in enumerate(available_reports.items()):
                with tabs[i]:
                    if page_key == 'visualization_report':
                        display_visualization_tab(person_data, all_person_history_df_admin)
                    elif page_key == 'vision_report':
                        display_performance_report(person_data, 'vision')
                    elif page_key == 'hearing_report':
                        # Pass the full history for hearing interpretation
                        display_performance_report(person_data, 'hearing', all_person_history_df=all_person_history_df_admin)
                    elif page_key == 'lung_report':
                        display_performance_report(person_data, 'lung')
                    elif page_key == 'main_report':
                        # Pass the full history for main report's performance section
                        display_main_report(person_data, all_person_history_df_admin)


    # --- Print Logic for Admin (Single) ---
    if st.session_state.get("admin_print_trigger", False):
        person_data_to_print = st.session_state.admin_person_row
        history_df_to_print = df[df['HN'] == st.session_state.admin_selected_hn].copy()
        
        report_html_data = generate_printable_report(person_data_to_print, history_df_to_print)
        escaped_html = json.dumps(report_html_data)
        iframe_id = f"print-iframe-admin-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
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
                iframe.onload = function() {{
                    setTimeout(function() {{
                        try {{ iframe.contentWindow.focus(); iframe.contentWindow.print(); }}
                        catch (e) {{ console.error("Printing failed:", e); }}
                    }}, 500);
                }};
            }})();
        </script>
        """
        st.components.v1.html(print_component, height=0, width=0)
        st.session_state.admin_print_trigger = False

    if st.session_state.get("admin_print_performance_trigger", False):
        person_data_to_print = st.session_state.admin_person_row
        history_df_to_print = df[df['HN'] == st.session_state.admin_selected_hn].copy()
        
        report_html_data = generate_performance_report_html(person_data_to_print, history_df_to_print)
        escaped_html = json.dumps(report_html_data)
        iframe_id = f"print-perf-iframe-admin-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
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
                iframe.onload = function() {{
                    setTimeout(function() {{
                        try {{ iframe.contentWindow.focus(); iframe.contentWindow.print(); }}
                        catch (e) {{ console.error("Printing performance report failed:", e); }}
                    }}, 500);
                }};
            }})();
        </script>
        """
        st.components.v1.html(print_component, height=0, width=0)
        st.session_state.admin_print_performance_trigger = False

    # --- START: Add Batch Print Trigger Logic ---
    if st.session_state.get("batch_print_trigger", False):
        html_content = st.session_state.batch_print_html_content
        if html_content:
            escaped_html = json.dumps(html_content)
            iframe_id = f"print-iframe-batch-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
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
                    iframe.onload = function() {{
                        setTimeout(function() {{
                            try {{ iframe.contentWindow.focus(); iframe.contentWindow.print(); }}
                            catch (e) {{ console.error("Batch printing failed:", e); }}
                        }}, 500);
                    }};
                }})();
            </script>
            """
            st.components.v1.html(print_component, height=0, width=0)
        
        # Reset triggers
        st.session_state.batch_print_trigger = False
        st.session_state.batch_print_html_content = None
    # --- END: Add Batch Print Trigger Logic ---
