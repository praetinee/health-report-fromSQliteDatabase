import streamlit as st
import pandas as pd
import base64
import re
import streamlit.components.v1 as components
from datetime import datetime

# พยายาม Import ฟังก์ชันสร้างรายงานจากไฟล์อื่น
# ใช้ try-except เพื่อป้องกันแอปพังถ้าไฟล์เหล่านั้นมีปัญหา
try:
    from print_report import generate_printable_report
except ImportError:
    def generate_printable_report(person_data, history_df):
        return f"<h1>Error</h1><p>ไม่สามารถโหลดโมดูล print_report.py ได้</p>"

try:
    from print_performance_report import generate_performance_report_html
except ImportError:
    def generate_performance_report_html(person_data, history_df):
        return f"<h1>Error</h1><p>ไม่สามารถโหลดโมดูล print_performance_report.py ได้</p>"

def extract_body_and_style(full_html):
    """
    แยกส่วน <style> และ <body> ออกจาก HTML เพื่อนำมารวมกันในหน้าเดียว
    """
    # ดึง Style
    style_match = re.search(r'<style>(.*?)</style>', full_html, re.DOTALL)
    style_content = style_match.group(1) if style_match else ""
    
    # ดึง Body Content (เอาเฉพาะเนื้อหาใน body ไม่เอา tag body)
    body_match = re.search(r'<body.*?>(.*?)</body>', full_html, re.DOTALL)
    if body_match:
        body_content = body_match.group(1)
    else:
        # กรณีไม่มี tag body ให้พยายามตัด DOCTYPE/html/head ออกแบบหยาบๆ
        body_content = full_html
        body_content = re.sub(r'<!DOCTYPE.*?>', '', body_content, flags=re.DOTALL)
        body_content = re.sub(r'<html.*?>', '', body_content, flags=re.DOTALL)
        body_content = re.sub(r'</html>', '', body_content, flags=re.DOTALL)
        body_content = re.sub(r'<head>.*?</head>', '', body_content, flags=re.DOTALL)
    
    return style_content, body_content

def generate_batch_html(hns, full_df, year, report_type):
    """
    สร้าง HTML ไฟล์เดียวที่รวมรายงานของหลายคน โดยคั่นด้วย Page Break
    """
    combined_body = []
    combined_styles = set()
    
    # CSS สำหรับการสั่งขึ้นหน้าใหม่เวลา Print
    page_break_css = """
    @media print {
        .page-break { display: block; page-break-before: always; }
        body { margin: 0; padding: 0; }
        .container { box-shadow: none !important; margin: 0 !important; page-break-inside: avoid; }
    }
    .page-break { 
        display: block; 
        border-top: 2px dashed #ccc; 
        margin: 30px 0; 
        padding: 20px; 
        text-align: center; 
        color: #888; 
        background-color: #f9f9f9;
    }
    .page-break::before { content: "--- Page Break (Next Patient) ---"; }
    @media print {
        .page-break { border: none; margin: 0; padding: 0; background-color: transparent; height: 0; }
        .page-break::before { content: ""; }
    }
    """
    combined_styles.add(page_break_css)

    valid_count = 0
    
    for i, hn in enumerate(hns):
        # ดึงข้อมูลของคนนั้นๆ ในปีที่เลือก
        person_history = full_df[full_df['HN'] == hn].copy()
        person_year_df = person_history[person_history['Year'] == year]
        
        if person_year_df.empty:
            continue
            
        person_data = person_year_df.iloc[0].to_dict()
        valid_count += 1
        
        # สร้าง HTML รายบุคคล
        try:
            if report_type == "health":
                raw_html = generate_printable_report(person_data, person_history)
            else:
                raw_html = generate_performance_report_html(person_data, person_history)
            
            style, body = extract_body_and_style(raw_html)
            combined_styles.add(style)
            
            # ใส่ Page Break ยกเว้นคนแรก
            if valid_count > 1:
                combined_body.append('<div class="page-break"></div>')
            
            combined_body.append(f'<div class="report-wrapper" id="report-{hn}">{body}</div>')
            
        except Exception as e:
            combined_body.append(f"<div style='color:red; padding:20px;'>Error generating report for HN {hn}: {str(e)}</div>")

    # รวม HTML ทั้งหมด
    final_style = "\n".join(list(combined_styles))
    final_body = "\n".join(combined_body)
    
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Batch Report - {len(hns)} Patients</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
            body {{ font-family: 'Sarabun', sans-serif; background-color: #555; padding: 20px; }}
            @media print {{ body {{ background-color: white; padding: 0; }} }}
            {final_style}
        </style>
    </head>
    <body onload="setTimeout(function(){{window.print();}}, 1000)">
        {final_body}
    </body>
    </html>
    """
    return final_html

def open_html_in_new_tab(html_content):
    """เปิด HTML ในแท็บใหม่ด้วย JS"""
    b64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    script = f"""
    <script>
        var win = window.open("", "_blank");
        win.document.write(decodeURIComponent(escape(window.atob("{b64}"))));
        win.document.close();
    </script>
    """
    components.html(script, height=0, width=0)

def display_print_center_page(df):
    """
    ฟังก์ชันหลักสำหรับแสดงหน้า Batch Print Center ใน Admin Panel
    """
    st.markdown("## 🖨️ ศูนย์พิมพ์รายงานแบบกลุ่ม (Batch Print Center)")
    st.info("💡 เลือกปีและหน่วยงาน เพื่อกรองรายชื่อผู้ที่ต้องการพิมพ์รายงาน")

    # --- 1. ส่วนตัวกรอง (Filters) ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 2, 2])
        
        # กรองปี
        all_years = sorted(df['Year'].dropna().unique().astype(int), reverse=True)
        current_year = datetime.now().year + 543
        default_year = current_year if current_year in all_years else (all_years[0] if all_years else None)
        
        with c1:
            selected_year = st.selectbox("📅 เลือกปี พ.ศ.", all_years, index=all_years.index(default_year) if default_year else 0, key="bp_year")
        
        # กรองข้อมูลตามปี
        year_df = df[df['Year'] == selected_year].copy()
        
        # กรองหน่วยงาน
        all_depts = sorted(year_df['หน่วยงาน'].dropna().unique().tolist())
        with c2:
            selected_depts = st.multiselect("🏢 เลือกหน่วยงาน (เลือกได้หลายหน่วยงาน)", all_depts, key="bp_dept")
            
        # ค้นหา
        with c3:
            search_query = st.text_input("🔍 ค้นหา (ชื่อ, HN)", "", key="bp_search")

    # ใช้ตัวกรอง
    filtered_df = year_df.copy()
    if selected_depts:
        filtered_df = filtered_df[filtered_df['หน่วยงาน'].isin(selected_depts)]
    if search_query:
        mask = filtered_df['ชื่อ-สกุล'].str.contains(search_query, case=False, na=False) | \
               filtered_df['HN'].astype(str).str.contains(search_query, na=False)
        filtered_df = filtered_df[mask]

    # --- 2. ส่วนเลือกรายชื่อ (Selection Table) ---
    if filtered_df.empty:
        st.warning("⚠️ ไม่พบข้อมูลตามเงื่อนไขที่กำหนด")
        return

    st.markdown(f"**พบข้อมูลทั้งสิ้น: {len(filtered_df)} ราย**")

    # เตรียมข้อมูลสำหรับแสดงใน Data Editor
    # เราจะเพิ่มคอลัมน์ "เลือก" ไว้หน้าสุด
    display_cols = ['HN', 'ชื่อ-สกุล', 'หน่วยงาน', 'วันที่ตรวจ']
    # กรองเฉพาะคอลัมน์ที่มีอยู่จริง
    display_cols = [c for c in display_cols if c in filtered_df.columns]
    
    editor_df = filtered_df[display_cols].copy()
    editor_df.insert(0, "เลือก", False) # Default ไม่เลือก

    # แสดงตารางให้เลือก
    edited_df = st.data_editor(
        editor_df,
        column_config={
            "เลือก": st.column_config.CheckboxColumn(
                "เลือกพิมพ์",
                help="ติ๊กเพื่อเลือกรายชื่อนี้",
                default=False,
            ),
            "HN": st.column_config.TextColumn("HN", disabled=True),
            "ชื่อ-สกุล": st.column_config.TextColumn("ชื่อ-สกุล", disabled=True),
            "หน่วยงาน": st.column_config.TextColumn("หน่วยงาน", disabled=True),
            "วันที่ตรวจ": st.column_config.TextColumn("วันที่ตรวจ", disabled=True),
        },
        disabled=display_cols,
        hide_index=True,
        use_container_width=True,
        key="batch_editor"
    )

    # ดึงรายชื่อที่ถูกติ๊กเลือก
    selected_rows = edited_df[edited_df["เลือก"] == True]
    selected_hns = selected_rows['HN'].tolist()
    
    st.markdown(f"**✅ ผู้ที่ถูกเลือกจำนวน: {len(selected_hns)} ราย**")

    # --- 3. ส่วนปุ่มสั่งพิมพ์ (Actions) ---
    st.markdown("---")
    c_act1, c_act2 = st.columns(2)
    
    # ปุ่มพิมพ์รายงานสุขภาพ
    with c_act1:
        if st.button("🖨️ พิมพ์รายงานสุขภาพ (Health Report)", 
                     type="primary", 
                     use_container_width=True, 
                     disabled=(len(selected_hns) == 0)):
            if selected_hns:
                with st.spinner(f"กำลังสร้างไฟล์รายงานสำหรับ {len(selected_hns)} ท่าน..."):
                    combined_html = generate_batch_html(selected_hns, df, selected_year, "health")
                    open_html_in_new_tab(combined_html)

    # ปุ่มพิมพ์รายงานสมรรถภาพ
    with c_act2:
        if st.button("🖨️ พิมพ์รายงานสมรรถภาพ (Performance Report)", 
                     type="primary", 
                     use_container_width=True, 
                     disabled=(len(selected_hns) == 0)):
            if selected_hns:
                with st.spinner(f"กำลังสร้างไฟล์รายงานสำหรับ {len(selected_hns)} ท่าน..."):
                    combined_html = generate_batch_html(selected_hns, df, selected_year, "performance")
                    open_html_in_new_tab(combined_html)
