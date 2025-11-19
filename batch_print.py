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
    if report_type == "รายงานสุขภาพ (Main)":
        if has_basic_health_data(person_data):
            return True, "✅ พร้อมพิมพ์"
        else:
            return False, "⚠️ ไม่มีผลเลือด/ร่างกาย"
            
    elif report_type == "รายงานสมรรถภาพ (Performance)":
        # เช็คว่ามีผลตรวจทางอาชีวเวชศาสตร์อย่างน้อย 1 อย่างหรือไม่
        has_vis = has_vision_data(person_data)
        has_hear = has_hearing_data(person_data)
        has_lung = has_lung_data(person_data)
        
        if has_vis or has_hear or has_lung:
            details = []
            if has_vis: details.append("ตา")
            if has_hear: details.append("หู")
            if has_lung: details.append("ปอด")
            return True, f"✅ มีผล: {','.join(details)}"
        else:
            return False, "⚠️ ไม่มีผลสมรรถภาพ"
            
    return False, "❓ ไม่ระบุ"

def generate_batch_html(df, selected_hns, report_type, year_logic="ใช้ข้อมูลปีล่าสุดของแต่ละคน"):
    """
    สร้าง HTML ฉบับยาวสำหรับคนไข้หลายคน โดยมี Page Break คั่น
    """
    report_bodies = []
    page_break_div = "<div style='page-break-after: always;'></div>"
    
    # เลือกฟังก์ชัน Body และ CSS ที่จะใช้
    css = ""
    if report_type == "รายงานสุขภาพ (Main)":
        render_body_func = render_printable_report_body
        css = get_main_report_css()
    else: # "รายงานสมรรถภาพ (Performance)"
        render_body_func = render_performance_report_body
        css = get_performance_report_css()

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

            # --- Double Check: ตรวจสอบความพร้อมข้อมูลอีกครั้งก่อนสร้าง ---
            is_ready, _ = check_data_readiness(person_data, report_type)
            if not is_ready:
                # ถ้าข้อมูลไม่พร้อม ข้ามไปเลยเพื่อป้องกันการพิมพ์หน้าว่างเปล่า
                skipped_count += 1
                continue

            # สร้างเนื้อหา HTML
            body = render_body_func(person_data, person_history_df)
            report_bodies.append(body)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด HN: {hn} - {e}")
            continue 

    progress_bar.empty()

    if not report_bodies:
        return None, skipped_count

    # รวม HTML
    all_bodies = page_break_div.join(report_bodies)
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ (Batch Print)</title>
        {css}
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

    # --- Fix Issue 2: State Management (Persistence) ---
    # ตรวจสอบและกำหนดค่าเริ่มต้นใน session_state ถ้ายังไม่มี
    # การทำแบบนี้จะทำให้ค่าคงอยู่ตลอดการใช้งาน Session นั้นๆ (แม้จะเปลี่ยน Tab)
    if 'bp_dept_filter' not in st.session_state: st.session_state.bp_dept_filter = []
    if 'bp_date_filter' not in st.session_state: st.session_state.bp_date_filter = "(ทั้งหมด)"
    if 'bp_report_type' not in st.session_state: st.session_state.bp_report_type = "รายงานสุขภาพ (Main)"

    # --- 1. ส่วนคัดกรองข้อมูล (Filter Section) ---
    st.subheader("1. คัดกรองผู้ป่วยที่ต้องการพิมพ์")
    
    col1, col2, col3 = st.columns([1.5, 1.5, 1])
    
    with col1:
        all_depts = sorted(df['หน่วยงาน'].dropna().astype(str).str.strip().unique())
        # ใช้ key เชื่อมกับ session_state โดยตรง เพื่อให้ค่าคงอยู่
        selected_depts = st.multiselect(
            "1. ค้นหาหน่วยงาน (พิมพ์ชื่อได้เลย)", 
            options=all_depts,
            placeholder="เลือกหรือพิมพ์ชื่อหน่วยงาน...",
            key="bp_dept_filter" 
        )

    with col2:
        # Logic Dependent Dropdown
        if selected_depts:
            dept_filtered_df = df[df['หน่วยงาน'].astype(str).str.strip().isin(selected_depts)]
            available_dates = sorted(dept_filtered_df['วันที่ตรวจ'].dropna().astype(str).unique(), reverse=True)
        else:
            available_dates = sorted(df['วันที่ตรวจ'].dropna().astype(str).unique(), reverse=True)
        
        # คำนวณ Index สำหรับ Selectbox เพื่อให้ค่าที่เลือกไว้ยังคงอยู่ ถ้าค่าเก่ายังใช้ได้
        date_options = ["(ทั้งหมด)"] + list(available_dates)
        index_to_select = 0
        # เช็คว่าค่าเก่าใน session_state ยังมีอยู่ในตัวเลือกใหม่ไหม ถ้ามีก็ใช้ index เดิม
        if st.session_state.bp_date_filter in date_options:
            index_to_select = date_options.index(st.session_state.bp_date_filter)

        selected_date = st.selectbox(
            "2. เลือกวันที่ตรวจ", 
            options=date_options,
            index=index_to_select,
            key="bp_date_filter"
        )

    with col3:
        report_type_options = ["รายงานสุขภาพ (Main)", "รายงานสมรรถภาพ (Performance)"]
        type_index = 0
        if st.session_state.bp_report_type in report_type_options:
            type_index = report_type_options.index(st.session_state.bp_report_type)
            
        report_type = st.selectbox(
            "3. เลือกประเภทรายงาน", 
            options=report_type_options,
            index=type_index,
            key="bp_report_type"
        )

    # --- 2. แสดงตารางรายชื่อ (Data Selection with Smart Status) ---
    st.subheader("2. เลือกรายชื่อผู้ป่วย")

    # Filter Dataframe
    filtered_df = df.copy()
    if selected_depts:
        filtered_df = filtered_df[filtered_df['หน่วยงาน'].astype(str).str.strip().isin(selected_depts)]
    if selected_date != "(ทั้งหมด)":
        filtered_df = filtered_df[filtered_df['วันที่ตรวจ'].astype(str) == selected_date]

    # เอาเฉพาะรายการล่าสุดของแต่ละคน
    filtered_df = filtered_df.sort_values(by=['Year'], ascending=False)
    unique_patients_df = filtered_df.drop_duplicates(subset=['HN'])
    
    # เตรียมข้อมูลสำหรับแสดงผล
    display_df = unique_patients_df[['HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']].copy()
    
    # --- SMART LOGIC: ตรวจสอบสถานะข้อมูลแต่ละคน ---
    status_list = []
    ready_list = []
    
    # ใช้ report_type ที่เลือกปัจจุบันในการเช็ค
    for _, row in display_df.iterrows():
        full_data_row = unique_patients_df.loc[unique_patients_df['HN'] == row['HN']].iloc[0].to_dict()
        is_ready, status_text = check_data_readiness(full_data_row, report_type)
        status_list.append(status_text)
        ready_list.append(is_ready)
    
    display_df['สถานะ'] = status_list
    display_df['เลือก'] = ready_list # Default เลือกเฉพาะคนที่พร้อม (True)

    # เรียงลำดับ: เอาคนที่พร้อม (True) ขึ้นก่อน, แล้วเรียงตามชื่อ
    display_df = display_df.sort_values(by=['เลือก', 'ชื่อ-สกุล'], ascending=[False, True])
    
    # ย้ายคอลัมน์ 'เลือก' และ 'สถานะ' มาไว้หน้าสุด
    cols = ['เลือก', 'สถานะ', 'HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']
    display_df = display_df[cols]

    # แสดง Data Editor
    if display_df.empty:
        st.info("ไม่พบข้อมูลตามเงื่อนไขที่เลือก")
        selected_hns = []
        count_selected = 0
    else:
        edited_df = st.data_editor(
            display_df,
            column_config={
                "เลือก": st.column_config.CheckboxColumn("เลือกพิมพ์", default=False),
                "สถานะ": st.column_config.TextColumn("สถานะข้อมูล", help="✅=พร้อมพิมพ์, ⚠️=ไม่มีข้อมูล", disabled=True),
                "HN": st.column_config.TextColumn("HN", disabled=True),
                "ชื่อ-สกุล": st.column_config.TextColumn("ชื่อ-สกุล", disabled=True),
                "หน่วยงาน": st.column_config.TextColumn("หน่วยงาน", disabled=True),
                "วันที่ตรวจ": st.column_config.TextColumn("วันที่ตรวจ", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            height=400 
        )
        
        # ดึงรายชื่อที่ถูกเลือก
        selected_hns = edited_df[edited_df['เลือก'] == True]['HN'].tolist()
        count_selected = len(selected_hns)

        # สรุปยอด
        count_ready = sum(ready_list)
        st.caption(f"พบผู้ป่วยทั้งหมด {len(display_df)} คน | ข้อมูลพร้อมพิมพ์ ✅ {count_ready} คน | เลือกพิมพ์ {count_selected} คน")

    # --- 3. ปุ่มดำเนินการ (Action) ---
    st.subheader("3. สั่งพิมพ์")
    
    col_btn_1, col_btn_2 = st.columns([1, 2])
    
    with col_btn_1:
        if st.button(f"🖨️ สร้างรายงาน ({count_selected} ท่าน)", type="primary", use_container_width=True, disabled=(count_selected == 0)):
            if count_selected > 0:
                html_content, skipped = generate_batch_html(df, selected_hns, report_type)
                
                if html_content:
                    st.session_state.batch_print_html = html_content
                    st.session_state.batch_print_ready = True
                    if skipped > 0:
                        st.warning(f"สร้างรายงานสำเร็จ! (แต่ข้ามไป {skipped} คน เนื่องจากไม่มีข้อมูลผลตรวจ)")
                    else:
                        st.success("สร้างรายงานสำเร็จครบถ้วน!")
                    st.rerun()
                else:
                    st.error("ไม่สามารถสร้างรายงานได้ (อาจไม่มีข้อมูลผลตรวจในรายชื่อที่เลือกเลย)")

    # --- 4. ส่วนแสดงผลการพิมพ์ (Hidden Print Trigger) ---
    if st.session_state.get("batch_print_ready", False):
        # JavaScript เพื่อสั่งพิมพ์ทันที
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
