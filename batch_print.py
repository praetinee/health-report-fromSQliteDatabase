import streamlit as st
import pandas as pd
import html
import json
from datetime import datetime

# --- Import ฟังก์ชันที่ถูกแยกส่วนมาจากไฟล์พิมพ์ ---
from print_report import render_printable_report_body, get_main_report_css
from print_performance_report import render_performance_report_body, get_performance_report_css

def generate_batch_html(df, selected_hns, report_type, year_logic):
    """
    สร้าง HTML ฉบับยาวสำหรับคนไข้หลายคน
    """
    report_bodies = []
    page_break = "<div style='page-break-after: always;'></div>"
    
    # เลือกฟังก์ชัน Body และ CSS ที่จะใช้
    if report_type == "รายงานสุขภาพ (Main)":
        render_body_func = render_printable_report_body
        css_func = get_main_report_css
    else: # "รายงานสมรรถภาพ (Performance)"
        render_body_func = render_performance_report_body
        css_func = get_performance_report_css

    for hn in selected_hns:
        try:
            person_history_df = df[df['HN'] == hn].copy()
            if person_history_df.empty:
                continue

            # ตรรกะการเลือกปี: "ใช้ข้อมูลปีล่าสุดของแต่ละคน"
            # (ในอนาคตสามารถเพิ่มตรรกะอื่นๆ เช่น เลือกปีที่ต้องการ)
            if year_logic == "ใช้ข้อมูลปีล่าสุดของแต่ละคน":
                # เรียงลำดับจากปีมากไปน้อย และเลือกแถวแรก
                latest_year_series = person_history_df.sort_values(by='Year', ascending=False).iloc[0]
                person_data = latest_year_series.to_dict()
            else:
                # (เผื่อไว้สำหรับตรรกะอื่นๆ เช่น เลือกปีที่ระบุ)
                # ในตอนนี้จะใช้ปีล่าสุดไปก่อน
                latest_year_series = person_history_df.sort_values(by='Year', ascending=False).iloc[0]
                person_data = latest_year_series.to_dict()

            # สร้างเนื้อหา HTML สำหรับคนไข้คนนี้
            body = render_body_func(person_data, person_history_df)
            report_bodies.append(body)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการสร้างรายงานสำหรับ HN: {hn} - {e}")
            continue # ไปยังคนถัดไป

    if not report_bodies:
        return None

    # รวม HTML ของทุกคนเข้าด้วยกัน คั่นด้วยตัวแบ่งหน้า
    all_bodies = page_break.join(report_bodies)
    
    # ดึง CSS
    css = css_func()

    # สร้างหน้า HTML ที่สมบูรณ์
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ (ชุด)</title>
        {css}
    </head>
    <body>
        {all_bodies}
    </body>
    </html>
    """


def display_batch_print_ui(df):
    """
    แสดง UI สำหรับการพิมพ์เป็นชุดใน Sidebar
    """
    with st.expander("🖨️ พิมพ์รายงานเป็นชุด (Batch Printing)"):
        
        # 1. เลือกหน่วยงาน
        all_depts = ["(ทั้งหมด)"] + sorted(df['หน่วยงาน'].dropna().unique())
        selected_dept = st.selectbox(
            "1. เลือกหน่วยงาน", 
            all_depts, 
            key="batch_dept"
        )

        # 2. กรองคนไข้ตามหน่วยงาน
        if selected_dept == "(ทั้งหมด)":
            filtered_df = df
        else:
            filtered_df = df[df['หน่วยงาน'] == selected_dept]
        
        # สร้าง dict ของคนไข้ในหน่วยงานนั้น
        patient_options_df = filtered_df.drop_duplicates(subset=['HN']).sort_values(by='ชื่อ-สกุล')
        options_dict = {
            row['HN']: f"{row['ชื่อ-สกุล']} (HN: {row['HN']})" 
            for _, row in patient_options_df.iterrows()
        }

        # 3. เลือกประเภทรายงาน
        report_type = st.selectbox(
            "2. เลือกประเภทรายงาน", 
            ["รายงานสุขภาพ (Main)", "รายงานสมรรถภาพ (Performance)"], 
            key="batch_report_type"
        )

        # 4. เลือกปี (ตอนนี้มีแค่ตัวเลือกเดียว)
        year_logic = st.selectbox(
            "3. เลือกปี", 
            ["ใช้ข้อมูลปีล่าสุดของแต่ละคน"], 
            key="batch_year_logic",
            disabled=True,
            help="ในอนาคตจะสามารถเลือกปีที่ต้องการได้"
        )
        
        # 5. เลือกคนไข้
        selected_hns = st.multiselect(
            f"4. เลือกคนไข้ ({len(options_dict)} คน)", 
            options=options_dict.keys(), 
            format_func=lambda hn: options_dict[hn], 
            key="batch_patients"
        )

        if st.button("เลือกทั้งหมด", key="batch_select_all", use_container_width=True):
            # ตั้งค่า session state ของ multiselect ให้เป็น key ทั้งหมด
            st.session_state.batch_patients = list(options_dict.keys())
            st.rerun()

        # 6. ปุ่มสร้างไฟล์
        if st.button("สร้างไฟล์สำหรับพิมพ์", key="batch_submit", use_container_width=True, type="primary"):
            if not selected_hns:
                st.warning("กรุณาเลือกคนไข้อย่างน้อย 1 คน")
            else:
                with st.spinner(f"กำลังสร้างรายงาน {len(selected_hns)} ชุด..."):
                    html_content = generate_batch_html(df, selected_hns, report_type, year_logic)
                    
                    if html_content:
                        # เก็บผลลัพธ์ไว้ใน session state เพื่อให้ admin_panel ดึงไปพิมพ์
                        st.session_state.batch_print_html_content = html_content
                        st.session_state.batch_print_trigger = True
                        st.success(f"สร้างรายงาน {len(selected_hns)} ชุดสำเร็จ! กำลังเตรียมพิมพ์...")
                        st.rerun() # สั่งให้ UI โหลดใหม่เพื่อเริ่มกระบวนการพิมพ์
                    else:
                        st.error("ไม่สามารถสร้างไฟล์รายงานได้ (อาจไม่มีข้อมูล)")
