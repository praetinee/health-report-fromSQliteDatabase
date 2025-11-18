import streamlit as st
import pandas as pd
import html
import json
from datetime import datetime

# --- Import ฟังก์ชันที่ถูกแยกส่วนมาจากไฟล์พิมพ์ ---
from print_report import render_printable_report_body, get_main_report_css
from print_performance_report import render_performance_report_body, get_performance_report_css

def generate_batch_html(df, selected_hns, report_type, year_logic="ใช้ข้อมูลปีล่าสุดของแต่ละคน"):
    """
    สร้าง HTML ฉบับยาวสำหรับคนไข้หลายคน โดยมี Page Break คั่น
    """
    report_bodies = []
    
    # CSS สำหรับ Page Break
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
    
    for i, hn in enumerate(selected_hns):
        try:
            # อัพเดท Progress
            progress_bar.progress((i + 1) / total_patients, text=f"กำลังสร้างรายงานคนที่ {i+1}/{total_patients} (HN: {hn})")
            
            person_history_df = df[df['HN'] == hn].copy()
            if person_history_df.empty:
                continue

            # ตรรกะการเลือกปี (ปัจจุบันใช้ปีล่าสุดเสมอ)
            if year_logic == "ใช้ข้อมูลปีล่าสุดของแต่ละคน":
                latest_year_series = person_history_df.sort_values(by='Year', ascending=False).iloc[0]
                person_data = latest_year_series.to_dict()
            else:
                # เผื่อไว้สำหรับ logic อื่น
                latest_year_series = person_history_df.sort_values(by='Year', ascending=False).iloc[0]
                person_data = latest_year_series.to_dict()

            # สร้างเนื้อหา HTML สำหรับคนไข้คนนี้
            body = render_body_func(person_data, person_history_df)
            report_bodies.append(body)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการสร้างรายงานสำหรับ HN: {hn} - {e}")
            continue 

    progress_bar.empty() # ลบ progress bar เมื่อเสร็จ

    if not report_bodies:
        return None

    # รวม HTML ของทุกคนเข้าด้วยกัน คั่นด้วยตัวแบ่งหน้า
    all_bodies = page_break_div.join(report_bodies)
    
    # สร้างหน้า HTML ที่สมบูรณ์ (CSS + All Bodies)
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
    return full_html

def display_print_center_page(df):
    """
    แสดงหน้าจอ 'ศูนย์จัดการพิมพ์รายงาน' (Print Center)
    """
    st.title("🖨️ ศูนย์จัดการพิมพ์รายงาน (Print Center)")
    st.markdown("---")

    # --- 1. ส่วนคัดกรองข้อมูล (Filter Section) ---
    st.subheader("1. คัดกรองผู้ป่วยที่ต้องการพิมพ์")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # ตัวเลือกวันที่ตรวจ
        all_dates = sorted(df['วันที่ตรวจ'].unique(), reverse=True)
        # พยายามเลือกวันนี้เป็นค่าเริ่มต้น ถ้ามี
        today_str = datetime.now().strftime('%Y-%m-%d') # หรือ format ที่ตรงกับ DB
        # เนื่องจาก format วันที่ใน DB อาจหลากหลาย ให้ใช้ index 0 ไปก่อน
        selected_date = st.selectbox("เลือกวันที่ตรวจ", ["(ทั้งหมด)"] + list(all_dates), index=0)

    with col2:
        # ตัวเลือกหน่วยงาน
        all_depts = sorted(df['หน่วยงาน'].dropna().unique())
        selected_dept = st.selectbox("เลือกหน่วยงาน", ["(ทั้งหมด)"] + list(all_depts))

    with col3:
        # ตัวเลือกประเภทรายงานที่จะพิมพ์
        report_type = st.selectbox("เลือกประเภทรายงาน", ["รายงานสุขภาพ (Main)", "รายงานสมรรถภาพ (Performance)"])

    # --- 2. แสดงตารางรายชื่อ (Data Selection) ---
    st.subheader("2. เลือกรายชื่อผู้ป่วย")

    # Filter Dataframe
    filtered_df = df.copy()
    if selected_date != "(ทั้งหมด)":
        filtered_df = filtered_df[filtered_df['วันที่ตรวจ'] == selected_date]
    if selected_dept != "(ทั้งหมด)":
        filtered_df = filtered_df[filtered_df['หน่วยงาน'] == selected_dept]

    # เอาเฉพาะรายการล่าสุดของแต่ละคน (Unique HN) เพื่อไม่ให้ซ้ำซ้อนใน list
    # เรียงตามปีล่าสุดก่อน
    filtered_df = filtered_df.sort_values(by=['Year'], ascending=False)
    unique_patients_df = filtered_df.drop_duplicates(subset=['HN'])
    
    # เตรียมข้อมูลสำหรับ Data Editor
    # เพิ่มคอลัมน์ 'เลือก' (Select) เป็น True โดย default
    display_df = unique_patients_df[['HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']].copy()
    display_df.insert(0, "เลือก", True) 

    # แสดง Data Editor
    edited_df = st.data_editor(
        display_df,
        column_config={
            "เลือก": st.column_config.CheckboxColumn(
                "เลือกพิมพ์",
                help="ติ๊กถูกเพื่อเลือกพิมพ์รายงานของคนนี้",
                default=True,
            )
        },
        disabled=["HN", "ชื่อ-สกุล", "หน่วยงาน", "วันที่ตรวจ"],
        hide_index=True,
        use_container_width=True,
        height=400 
    )

    # ดึงรายชื่อที่ถูกเลือก
    selected_hns = edited_df[edited_df['เลือก'] == True]['HN'].tolist()
    count_selected = len(selected_hns)

    st.caption(f"จำนวนผู้ป่วยที่เลือก: {count_selected} ท่าน")

    # --- 3. ปุ่มดำเนินการ (Action) ---
    st.subheader("3. สั่งพิมพ์")
    
    col_btn_1, col_btn_2 = st.columns([1, 2])
    
    with col_btn_1:
        if st.button(f"🖨️ สร้างรายงาน ({count_selected} ท่าน)", type="primary", use_container_width=True, disabled=(count_selected == 0)):
            if count_selected > 0:
                html_content = generate_batch_html(df, selected_hns, report_type)
                if html_content:
                    # เก็บลง Session State
                    st.session_state.batch_print_html = html_content
                    st.session_state.batch_print_ready = True
                else:
                    st.error("ไม่สามารถสร้างรายงานได้ กรุณาลองใหม่")

    # --- 4. ส่วนแสดงผลการพิมพ์ (Hidden Print Trigger) ---
    if st.session_state.get("batch_print_ready", False):
        st.success("✅ สร้างรายงานเสร็จสิ้น! กำลังเปิดหน้าต่างพิมพ์...")
        
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
        
        # Reset state เพื่อไม่ให้พิมพ์ซ้ำถ้าแค่ refresh หน้า
        st.session_state.batch_print_ready = False
