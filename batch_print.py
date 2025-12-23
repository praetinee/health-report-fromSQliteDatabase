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

# --- Callback Function (New) ---
def add_patient_to_list_callback(df):
    """
    Callback function สำหรับปุ่มเพิ่มรายการ เพื่อป้องกัน StreamlitAPIException
    """
    # ดึงค่าจาก Session State โดยตรง
    name = st.session_state.get("bp_name_search")
    hn = st.session_state.get("bp_hn_search")
    cid = st.session_state.get("bp_cid_search")
    
    target_hn = None
    found_msg = ""
    
    # 1. เช็คจากชื่อ (ตรวจสอบทั้ง None และสตริงว่าง)
    if name:
        matched = df[df['ชื่อ-สกุล'] == name]
        if not matched.empty:
            target_hn = matched.iloc[0]['HN']
            found_msg = f"เพิ่มคุณ {name} เรียบร้อย"
            
    # 2. เช็คจาก HN
    elif hn:
        matched = df[df['HN'].astype(str) == hn.strip()]
        if not matched.empty:
            target_hn = matched.iloc[0]['HN']
            name_found = matched.iloc[0]['ชื่อ-สกุล']
            found_msg = f"เพิ่ม HN {hn} ({name_found}) เรียบร้อย"
            
    # 3. เช็คจากเลขบัตร
    elif cid:
        matched = df[df['เลขบัตรประชาชน'].astype(str) == cid.strip()]
        if not matched.empty:
            target_hn = matched.iloc[0]['HN']
            name_found = matched.iloc[0]['ชื่อ-สกุล']
            found_msg = f"เพิ่มเลขบัตร {cid} ({name_found}) เรียบร้อย"
            
    if target_hn:
        # Initialize set if not exists
        if 'bp_manual_hns' not in st.session_state:
            st.session_state.bp_manual_hns = set()
            
        st.session_state.bp_manual_hns.add(target_hn)
        # เก็บข้อความแจ้งเตือนไว้แสดงผลหลัง Rerun
        st.session_state.bp_action_msg = {"type": "success", "text": found_msg}
        
        # Reset inputs: ทำให้ช่องกรอกว่างพร้อมพิมพ์ใหม่
        st.session_state.bp_name_search = None # ตั้งเป็น None เพื่อให้ selectbox ว่างเปล่า
        st.session_state.bp_hn_search = ""
        st.session_state.bp_cid_search = ""
        
    else:
        st.session_state.bp_action_msg = {"type": "error", "text": "❌ ไม่พบข้อมูล หรือไม่ได้ระบุเงื่อนไขการค้นหา"}

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
        .add-btn-hint {
            font-size: 0.8rem;
            color: #666;
            margin-top: -10px;
            margin-bottom: 10px;
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
    
    # --- State สำหรับเก็บรายการที่กดบวก (Manual Queue) ---
    if 'bp_manual_hns' not in st.session_state: st.session_state.bp_manual_hns = set()

    # --- 1. เลือกประเภทรายงาน (Moved to Top) ---
    st.subheader("1. เลือกประเภทรายงาน")
    
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
        "เลือกรูปแบบรายงานที่จะพิมพ์", 
        options=report_type_options,
        index=type_idx,
        key="bp_report_type",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # --- 2. ค้นหาและเพิ่มผู้ป่วย (Search & Add) ---
    st.subheader("2. ค้นหาและเพิ่มรายชื่อ (พิมพ์ค้นหาทีละคน)")
    
    # แสดงข้อความแจ้งเตือนจากการกระทำใน Callback (ถ้ามี)
    if 'bp_action_msg' in st.session_state:
        msg = st.session_state.bp_action_msg
        if msg['type'] == 'success':
            st.success(msg['text'])
        else:
            st.error(msg['text'])
        del st.session_state.bp_action_msg
    
    # Row 1: ค้นหาด้วยข้อมูลบุคคล
    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    with c1:
        # เตรียมรายชื่อสำหรับ Autocomplete
        all_names = sorted(df['ชื่อ-สกุล'].dropna().unique().tolist())
        st.selectbox(
            "ค้นหาด้วยชื่อ-สกุล", 
            options=all_names, # เอา "(ไม่ระบุ)" ออก เพื่อให้ใช้ index=None ได้อย่างสะอาดตา
            index=None,
            placeholder="พิมพ์หรือเลือกชื่อ...",
            key="bp_name_search"
        )
    with c2:
        st.text_input("ค้นหาด้วย HN", key="bp_hn_search", placeholder="พิมพ์ HN")
    with c3:
        st.text_input("ค้นหาด้วยเลขบัตรฯ", key="bp_cid_search", placeholder="พิมพ์เลขบัตร")

    # Row 1.5: ปุ่มเพิ่มรายการ (Plus Button Logic) - ใช้ Callback
    col_add_btn, _, _ = st.columns([2, 2, 4])
    with col_add_btn:
        st.button("➕ เพิ่มลงรายการ", use_container_width=True, 
                  help="กดเพื่อเพิ่มคนที่ค้นหาลงในลิสต์ด้านล่าง",
                  on_click=add_patient_to_list_callback,
                  args=(df,))
    
    st.markdown("---")
    
    # Row 2: ค้นหาด้วยกลุ่มข้อมูล (Bulk Filter)
    st.write("หรือเลือกเพิ่มจากกลุ่มหน่วยงาน (Bulk Selection)")
    c4, c5 = st.columns(2)
    
    with c4:
        all_depts = sorted(df['หน่วยงาน'].dropna().astype(str).str.strip().unique())
        selected_depts = st.multiselect(
            "กรองตามหน่วยงาน", 
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
            "กรองตามวันที่ตรวจ", 
            options=date_options,
            index=idx,
            key="bp_date_filter"
        )

    # --- 3. ตรวจสอบรายชื่อและสั่งพิมพ์ (Display & Action) ---
    st.subheader("3. รายชื่อที่เลือก (รอสั่งพิมพ์)")
    
    # Logic: 
    # - แสดงคนที่อยู่ใน Manual Queue (bp_manual_hns) เสมอ
    # - แสดงคนที่ผ่าน Filter (Dept/Date) 
    # - **ไม่นำ** search inputs (name/hn/cid) มากรองตาราง (เพราะใช้สำหรับปุ่ม Add เท่านั้น)
    
    filtered_df = pd.DataFrame(columns=df.columns) # เริ่มต้นว่าง
    filter_active = False # เช็คว่ามีการใช้ Bulk Filter ไหม

    # Apply Bulk Filters ONLY (Dept, Date)
    if selected_depts or (selected_date != "(ทั้งหมด)"):
        filtered_df = df.copy()
        if selected_depts: 
            filtered_df = filtered_df[filtered_df['หน่วยงาน'].astype(str).str.strip().isin(selected_depts)]
        if selected_date != "(ทั้งหมด)": 
            filtered_df = filtered_df[filtered_df['วันที่ตรวจ'].astype(str) == selected_date]
        filter_active = True

    # Prepare Display Pool
    manual_hns = list(st.session_state.bp_manual_hns)
    manual_df = df[df['HN'].isin(manual_hns)].copy()
    
    # รวมข้อมูล: Manual List + Bulk Filter Results
    if filter_active:
        display_pool = pd.concat([manual_df, filtered_df]).drop_duplicates(subset=['HN'])
    elif manual_hns:
        display_pool = manual_df
    else:
        # ถ้าไม่มี Manual List และไม่ได้ใช้ Bulk Filter -> ตารางว่าง
        display_pool = pd.DataFrame(columns=df.columns)

    # Process for Display
    display_pool = display_pool.sort_values(by=['Year'], ascending=False)
    unique_patients_df = display_pool.drop_duplicates(subset=['HN'])
    
    display_df = unique_patients_df[['HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']].copy()
    
    # Smart Status & Default Selection Logic
    status_list = []
    ready_list = [] # สำหรับเก็บว่าข้อมูลพร้อมไหม
    default_select_list = [] # สำหรับติ๊กถูกอัตโนมัติ
    
    for _, row in display_df.iterrows():
        full_data_row = unique_patients_df.loc[unique_patients_df['HN'] == row['HN']].iloc[0].to_dict()
        is_ready, status_text = check_data_readiness(full_data_row, report_type)
        status_list.append(status_text)
        ready_list.append(is_ready)
        
        # Logic การติ๊กถูก:
        # 1. ถ้าคนนี้อยู่ใน Manual Queue (กดบวกมา) -> ติ๊กถูกเสมอ (ถ้าข้อมูลพร้อม)
        # 2. ถ้ามาจาก Bulk Filter -> ไม่ติ๊ก Default (ให้เลือกเอง)
        if row['HN'] in manual_hns:
            default_select_list.append(is_ready) # ติ๊กถ้าพร้อม
        else:
            default_select_list.append(False) # Default ไม่ติ๊ก
    
    display_df['สถานะ'] = status_list
    display_df['เลือก'] = default_select_list 
    
    # เพิ่มคอลัมน์ "ลบ" (Checkbox)
    display_df['ลบ'] = False

    # Sorting: เอาคนที่เลือก (กดบวกมา) ขึ้นก่อน
    display_df = display_df.sort_values(by=['เลือก', 'ชื่อ-สกุล'], ascending=[False, True])
    
    # Reorder columns: เอาปุ่มลบไว้หน้าสุด
    cols = ['ลบ', 'เลือก', 'สถานะ', 'HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']
    display_df = display_df[cols]

    # --- Tool bar for List (REMOVED: Old Clear Button) ---
    
    # Display Table
    selected_hns = []
    count_selected = 0
    
    if display_df.empty:
        if filter_active:
            st.info("ไม่พบข้อมูลตามเงื่อนไขหน่วยงาน/วันที่")
        else:
            st.info("ตารางว่าง... กรุณาค้นหาและกดปุ่ม ➕ เพื่อเพิ่มรายชื่อ")
    else:
        edited_df = st.data_editor(
            display_df,
            column_config={
                "ลบ": st.column_config.CheckboxColumn("❌", help="กดเพื่อลบรายชื่อนี้", default=False, width="small"),
                "เลือก": st.column_config.CheckboxColumn("เลือกพิมพ์", default=False),
                "สถานะ": st.column_config.TextColumn("สถานะข้อมูล", help="✅=พร้อม, ⚠️=ไม่ครบ, ❌=ไม่มี", disabled=True),
                "HN": st.column_config.TextColumn("HN", disabled=True),
                "ชื่อ-สกุล": st.column_config.TextColumn("ชื่อ-สกุล", disabled=True),
                "หน่วยงาน": st.column_config.TextColumn("หน่วยงาน", disabled=True),
                "วันที่ตรวจ": st.column_config.TextColumn("วันที่ตรวจ", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            height=400,
            key="data_editor_print" 
        )
        
        # Logic การลบ (ถ้ามีการติ๊กช่อง 'ลบ' หรือ '❌')
        to_delete_hns = edited_df[edited_df['ลบ'] == True]['HN'].tolist()
        if to_delete_hns:
            # ลบออกจาก Session State
            for hn in to_delete_hns:
                if hn in st.session_state.bp_manual_hns:
                    st.session_state.bp_manual_hns.remove(hn)
                    
            st.toast(f"🗑️ ลบ {len(to_delete_hns)} รายการเรียบร้อย", icon="🗑️")
            st.rerun() # รีโหลดหน้าจอเพื่อให้แถวนั้นหายไปทันที (Simulate click-to-delete)

        selected_hns = edited_df[edited_df['เลือก'] == True]['HN'].tolist()
        count_selected = len(selected_hns)
        st.caption(f"กำลังเลือก {count_selected} คน")
        
        # --- Clear All Button (Moved to Below Table) ---
        col_summary, col_clear_btn = st.columns([4, 1])
        with col_clear_btn:
             if manual_hns:
                if st.button("🗑️ ล้างรายการทั้งหมด", type="secondary", use_container_width=True, help="ลบรายชื่อทั้งหมดที่เลือกมา"):
                    st.session_state.bp_manual_hns = set()
                    st.rerun()

    # --- Print Button ---
    st.markdown("---")
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
                    st.error("ไม่สามารถสร้างรายงานได้")

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
