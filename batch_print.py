import streamlit as st
import pandas as pd
import html
import json
from datetime import datetime

# --- Import ฟังก์ชันที่ถูกแยกส่วนมาจากไฟล์พิมพ์ ---
from print_report import render_printable_report_body, get_main_report_css
from print_performance_report import render_performance_report_body, get_performance_report_css
# นำเข้าฟังก์ชันเช็คข้อมูลจากไฟล์อื่นเพื่อนำมาใช้ตรวจสอบสถานะ
from print_performance_report import has_vision_data, has_hearing_data, has_lung_data

# --- Helper Functions สำหรับตรวจสอบความพร้อมข้อมูลในไฟล์นี้ ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def has_basic_health_data(person_data):
    """ตรวจสอบว่ามีข้อมูลสุขภาพพื้นฐาน (Main Report) หรือไม่"""
    # เช็คคอลัมน์หลักๆ ของ Lab และ Vitals
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'SBP', 'Hb(%)']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def check_data_readiness(person_data, report_type):
    """
    ตรวจสอบสถานะความพร้อมของข้อมูลตามประเภทรายงาน
    Returns: (is_ready: bool, status_text: str)
    """
    has_main = has_basic_health_data(person_data)
    
    # Check Performance Data
    has_vis = has_vision_data(person_data)
    has_hear = has_hearing_data(person_data)
    has_lung = has_lung_data(person_data)
    has_perf = has_vis or has_hear or has_lung

    if report_type == "รายงานสุขภาพ (Health Report)":
        if has_main:
            return True, "✅ พร้อมพิมพ์"
        else:
            return False, "⚠️ ไม่มีผลเลือด/ร่างกาย"
            
    elif report_type == "รายงานสมรรถภาพ (Performance Report)":
        if has_perf:
            details = []
            if has_vis: details.append("ตา")
            if has_hear: details.append("หู")
            if has_lung: details.append("ปอด")
            return True, f"✅ มีผล: {','.join(details)}"
        else:
            return False, "⚠️ ไม่มีผลสมรรถภาพ"
            
    elif report_type == "ทั้งรายงานสุขภาพและสมรรถภาพ":
        if has_main and has_perf:
            return True, "✅ พร้อมครบทั้ง 2 ส่วน"
        elif has_main:
            return True, "⚠️ ขาดผลสมรรถภาพ" # ยังให้ True เพราะพิมพ์ส่วนที่มีได้
        elif has_perf:
            return True, "⚠️ ขาดผลสุขภาพ"   # ยังให้ True เพราะพิมพ์ส่วนที่มีได้
        else:
            return False, "❌ ไม่พบข้อมูลใดๆ"

    return False, "❓ ไม่ระบุ"

def generate_batch_html(df, selected_hns, report_type, year_logic="ใช้ข้อมูลปีล่าสุดของแต่ละคน"):
    """
    สร้าง HTML ฉบับยาวสำหรับคนไข้หลายคน โดยมี Page Break คั่น
    รองรับการพิมพ์ทั้ง 2 แบบพร้อมกัน
    """
    report_bodies = []
    page_break_div = "<div style='page-break-after: always;'></div>"
    
    # Prepare CSS
    css_main = get_main_report_css()
    css_perf = get_performance_report_css()
    
    # รวม CSS กรณีเลือกทั้งคู่ (CSS อาจจะซ้ำกันบ้าง แต่ Browser จัดการได้)
    full_css = f"{css_main}\n{css_perf}" 

    progress_bar = st.progress(0)
    total_patients = len(selected_hns)
    skipped_count = 0
    
    for i, hn in enumerate(selected_hns):
        try:
            progress_bar.progress((i + 1) / total_patients, text=f"กำลังตรวจสอบและสร้างรายงานคนที่ {i+1}/{total_patients} (HN: {hn})")
            
            person_history_df = df[df['HN'] == hn].copy()
            if person_history_df.empty:
                skipped_count += 1
                continue

            # เลือกข้อมูลปีล่าสุด
            latest_year_series = person_history_df.sort_values(by='Year', ascending=False).iloc[0]
            person_data = latest_year_series.to_dict()

            # Logic การสร้าง Body ตามประเภทรายงาน
            patient_bodies = []
            
            # 1. ตรวจสอบว่าจะเอา Main Report ไหม
            need_main = report_type in ["รายงานสุขภาพ (Health Report)", "ทั้งรายงานสุขภาพและสมรรถภาพ"]
            if need_main and has_basic_health_data(person_data):
                patient_bodies.append(render_printable_report_body(person_data, person_history_df))
            
            # 2. ตรวจสอบว่าจะเอา Performance Report ไหม
            need_perf = report_type in ["รายงานสมรรถภาพ (Performance Report)", "ทั้งรายงานสุขภาพและสมรรถภาพ"]
            has_vis = has_vision_data(person_data)
            has_hear = has_hearing_data(person_data)
            has_lung = has_lung_data(person_data)
            if need_perf and (has_vis or has_hear or has_lung):
                patient_bodies.append(render_performance_report_body(person_data, person_history_df))

            # ถ้าไม่มีข้อมูลเลยสำหรับ HN นี้
            if not patient_bodies:
                skipped_count += 1
                continue
            
            # รวม Body ของคนคนนี้ (ถ้าเลือกทั้งคู่ จะมี 2 ส่วน คั่นด้วย Page Break)
            combined_patient_html = page_break_div.join(patient_bodies)
            report_bodies.append(combined_patient_html)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด HN: {hn} - {e}")
            continue 

    progress_bar.empty()

    if not report_bodies:
        return None, skipped_count

    # รวม HTML ของทุกคน คั่นด้วย Page Break
    all_bodies = page_break_div.join(report_bodies)
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ (Batch Print)</title>
        {full_css}
    </head>
    <body>
        {all_bodies}
    </body>
    </html>
    """
    return full_html, skipped_count

def display_print_center_page(df):
    """
    แสดงหน้าจอ 'ศูนย์จัดการพิมพ์รายงาน' (Print Center)
    """
    st.title("🖨️ ศูนย์จัดการพิมพ์รายงาน (Print Center)")
    st.markdown("---")
    
    # --- CSS for UI Enhancements ---
    st.markdown("""
    <style>
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #1B5E20 !important;
            color: #ffffff !important;
            border: none !important;
            padding: 12px 32px !important;
            font-size: 20px !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            width: 100%;
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #2E7D32 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- Initialize Session State ---
    if 'bp_dept_filter' not in st.session_state: st.session_state.bp_dept_filter = []
    if 'bp_date_filter' not in st.session_state: st.session_state.bp_date_filter = "(ทั้งหมด)"
    if 'bp_report_type' not in st.session_state: st.session_state.bp_report_type = "รายงานสุขภาพ (Health Report)"
    # New filters state
    if 'bp_name_search' not in st.session_state: st.session_state.bp_name_search = None
    if 'bp_hn_search' not in st.session_state: st.session_state.bp_hn_search = ""
    if 'bp_cid_search' not in st.session_state: st.session_state.bp_cid_search = ""

    # --- 1. ส่วนคัดกรองข้อมูล (Filter Section) ---
    st.subheader("1. คัดกรองผู้ป่วยที่ต้องการพิมพ์")
    
    # Row 1: ค้นหาด้วยข้อมูลบุคคล
    c1, c2, c3 = st.columns(3)
    with c1:
        # เตรียมรายชื่อสำหรับ Autocomplete
        all_names = sorted(df['ชื่อ-สกุล'].dropna().unique().tolist())
        # ใช้ Selectbox ให้ค้นหาและเลือกได้
        search_name = st.selectbox(
            "1. ชื่อ-สกุล (ค้นหา)", 
            options=["(ไม่ระบุ)"] + all_names,
            index=0,
            key="bp_name_search"
        )
    with c2:
        search_hn = st.text_input("2. HN", key="bp_hn_search", placeholder="พิมพ์ค้นหา HN")
    with c3:
        search_cid = st.text_input("3. เลขบัตรประชาชน", key="bp_cid_search", placeholder="พิมพ์ค้นหาเลขบัตรฯ")

    # Row 2: ค้นหาด้วยกลุ่มข้อมูล และประเภทรายงาน
    c4, c5, c6 = st.columns(3)
    
    with c4:
        all_depts = sorted(df['หน่วยงาน'].dropna().astype(str).str.strip().unique())
        selected_depts = st.multiselect(
            "4. หน่วยงาน", 
            options=all_depts,
            placeholder="เลือกหน่วยงาน...",
            key="bp_dept_filter" 
        )

    with c5:
        # Logic Dependent Dropdown for Date
        temp_df = df.copy()
        if selected_depts:
            temp_df = temp_df[temp_df['หน่วยงาน'].astype(str).str.strip().isin(selected_depts)]
        
        available_dates = sorted(temp_df['วันที่ตรวจ'].dropna().astype(str).unique(), reverse=True)
        date_options = ["(ทั้งหมด)"] + list(available_dates)
        
        # Maintain selection if possible
        idx = 0
        if st.session_state.bp_date_filter in date_options:
            idx = date_options.index(st.session_state.bp_date_filter)

        selected_date = st.selectbox(
            "5. วันที่ตรวจ", 
            options=date_options,
            index=idx,
            key="bp_date_filter"
        )

    with c6:
        # 3 Options
        report_type_options = [
            "รายงานสุขภาพ (Health Report)", 
            "รายงานสมรรถภาพ (Performance Report)",
            "ทั้งรายงานสุขภาพและสมรรถภาพ"
        ]
        
        type_idx = 0
        if st.session_state.bp_report_type in report_type_options:
            type_idx = report_type_options.index(st.session_state.bp_report_type)
            
        report_type = st.selectbox(
            "6. เลือกประเภทรายงาน", 
            options=report_type_options,
            index=type_idx,
            key="bp_report_type"
        )

    # --- 2. เลือกรายชื่อผู้ป่วย (Data Selection) ---
    st.subheader("2. เลือกรายชื่อผู้ป่วย")

    # Filter Dataframe Logic
    filtered_df = df.copy()
    
    # 1. Name Filter
    if search_name and search_name != "(ไม่ระบุ)":
        filtered_df = filtered_df[filtered_df['ชื่อ-สกุล'] == search_name]
    
    # 2. HN Filter (Partial Match)
    if search_hn:
        filtered_df = filtered_df[filtered_df['HN'].astype(str).str.contains(search_hn, na=False)]
        
    # 3. CID Filter (Partial Match)
    if search_cid:
        filtered_df = filtered_df[filtered_df['เลขบัตรประชาชน'].astype(str).str.contains(search_cid, na=False)]

    # 4. Dept Filter
    if selected_depts:
        filtered_df = filtered_df[filtered_df['หน่วยงาน'].astype(str).str.strip().isin(selected_depts)]
        
    # 5. Date Filter
    if selected_date != "(ทั้งหมด)":
        filtered_df = filtered_df[filtered_df['วันที่ตรวจ'].astype(str) == selected_date]

    # Process for Display
    filtered_df = filtered_df.sort_values(by=['Year'], ascending=False)
    unique_patients_df = filtered_df.drop_duplicates(subset=['HN'])
    
    display_df = unique_patients_df[['HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']].copy()
    
    # Smart Status Logic
    status_list = []
    ready_list = []
    
    for _, row in display_df.iterrows():
        full_data_row = unique_patients_df.loc[unique_patients_df['HN'] == row['HN']].iloc[0].to_dict()
        is_ready, status_text = check_data_readiness(full_data_row, report_type)
        status_list.append(status_text)
        ready_list.append(is_ready)
    
    display_df['สถานะ'] = status_list
    display_df['เลือก'] = ready_list 

    # Sorting
    display_df = display_df.sort_values(by=['เลือก', 'ชื่อ-สกุล'], ascending=[False, True])
    
    # Reorder columns
    cols = ['เลือก', 'สถานะ', 'HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']
    display_df = display_df[cols]

    # Display Table
    if display_df.empty:
        st.info("ไม่พบข้อมูลตามเงื่อนไขที่เลือก")
        selected_hns = []
        count_selected = 0
    else:
        edited_df = st.data_editor(
            display_df,
            column_config={
                "เลือก": st.column_config.CheckboxColumn("เลือกพิมพ์", default=False),
                "สถานะ": st.column_config.TextColumn("สถานะข้อมูล", help="✅=พร้อม, ⚠️=ไม่ครบ, ❌=ไม่มี", disabled=True),
                "HN": st.column_config.TextColumn("HN", disabled=True),
                "ชื่อ-สกุล": st.column_config.TextColumn("ชื่อ-สกุล", disabled=True),
                "หน่วยงาน": st.column_config.TextColumn("หน่วยงาน", disabled=True),
                "วันที่ตรวจ": st.column_config.TextColumn("วันที่ตรวจ", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            height=400 
        )
        
        selected_hns = edited_df[edited_df['เลือก'] == True]['HN'].tolist()
        count_selected = len(selected_hns)
        count_ready = sum(ready_list)
        st.caption(f"พบผู้ป่วย {len(display_df)} คน | พร้อมพิมพ์ ✅ {count_ready} คน | เลือกพิมพ์ {count_selected} คน")

    # --- 3. ดำเนินการสั่งพิมพ์ (Action) ---
    st.markdown("---")
    st.subheader("3. ดำเนินการสั่งพิมพ์")
    
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if st.button(f"สั่งพิมพ์รายงาน ({count_selected} ท่าน)", type="primary", use_container_width=True, disabled=(count_selected == 0)):
            if count_selected > 0:
                html_content, skipped = generate_batch_html(df, selected_hns, report_type)
                
                if html_content:
                    st.session_state.batch_print_html = html_content
                    st.session_state.batch_print_ready = True
                    if skipped > 0:
                        st.warning(f"สร้างรายงานสำเร็จ! (ข้าม {skipped} คน เนื่องจากไม่มีข้อมูล)")
                    else:
                        st.success("สร้างรายงานสำเร็จครบถ้วน!")
                    st.rerun()
                else:
                    st.error("ไม่สามารถสร้างรายงานได้ (อาจไม่มีข้อมูลในรายชื่อที่เลือก)")

    # --- Hidden Print Trigger ---
    if st.session_state.get("batch_print_ready", False):
        html_content = st.session_state.batch_print_html
        escaped_html = json.dumps(html_content)
        iframe_id = f"print-batch-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        print_script = f"""
        <iframe id="{iframe_id}" style="display:none;"></iframe>
        <script>
            (function() {{
                const iframe = document.getElementById('{iframe_id}');
                if (!iframe) return;
                const doc = iframe.contentWindow.document;
                doc.open();
                doc.write({escaped_html});
                doc.close();
                iframe.onload = function() {{
                    setTimeout(function() {{
                        try {{ 
                            iframe.contentWindow.focus(); 
                            iframe.contentWindow.print(); 
                        }} catch (e) {{ 
                            console.error("Print error:", e); 
                        }}
                    }}, 1000);
                }};
            }})();
        </script>
        """
        st.components.v1.html(print_script, height=0, width=0)
        st.session_state.batch_print_ready = False
