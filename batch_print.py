import streamlit as st
import pandas as pd
import html
import json
import re
from datetime import datetime

# --- Import ฟังก์ชันสำหรับการสร้างรายงาน (Report Generation) ---
from print_report import (
    render_printable_report_body,
    get_main_report_css
)
from print_performance_report import (
    render_performance_report_body,
    get_performance_report_css,
    has_vision_data,
    has_hearing_data,
    has_lung_data
)

# --- Helper Functions ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def has_basic_health_data(person_data):
    """ตรวจสอบว่ามีข้อมูลสุขภาพพื้นฐาน (Main Report) หรือไม่"""
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'SBP', 'Hb(%)']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def check_data_readiness(person_data, report_type):
    """
    ตรวจสอบสถานะความพร้อมของข้อมูลตามประเภทรายงาน
    Returns: (is_ready: bool, status_text: str, status_color: str)
    """
    has_main = has_basic_health_data(person_data)
    
    has_vis = has_vision_data(person_data)
    has_hear = has_hearing_data(person_data)
    has_lung = has_lung_data(person_data)
    has_perf = has_vis or has_hear or has_lung

    status_color = "gray"
    status_text = "❓ ไม่ระบุ"
    is_ready = False

    if report_type == "รายงานสุขภาพ (Health Report)":
        if has_main:
            return True, "✅ ข้อมูลพร้อม", "green"
        else:
            return False, "⚠️ ขาดผลตรวจ", "orange"
            
    elif report_type == "รายงานสมรรถภาพ (Performance Report)":
        if has_perf:
            details = []
            if has_vis: details.append("ตา")
            if has_hear: details.append("หู")
            if has_lung: details.append("ปอด")
            return True, f"✅ มีผล: {','.join(details)}", "green"
        else:
            return False, "⚠️ ไม่มีผลสมรรถภาพ", "orange"
            
    elif report_type == "ทั้งรายงานสุขภาพและสมรรถภาพ":
        if has_main and has_perf:
            return True, "✅ ครบถ้วน", "green"
        elif has_main:
            return True, "⚠️ ขาดสมรรถภาพ", "blue" 
        elif has_perf:
            return True, "⚠️ ขาดผลสุขภาพ", "blue"
        else:
            return False, "❌ ไม่มีข้อมูล", "red"

    return is_ready, status_text, status_color

def generate_batch_html(df, selected_hns, report_type, year_logic="ใช้ข้อมูลปีล่าสุดของแต่ละคน"):
    """สร้าง HTML สำหรับพิมพ์"""
    report_bodies = []
    
    # ดึง CSS จากไฟล์ต้นฉบับ
    css_main = get_main_report_css()
    css_perf = get_performance_report_css()
    
    # สกัดเฉพาะเนื้อหาใน <style>...</style>
    main_style_match = re.search(r'<style>(.*?)</style>', css_main, re.DOTALL)
    perf_style_match = re.search(r'<style>(.*?)</style>', css_perf, re.DOTALL)
    
    main_css_content = main_style_match.group(1) if main_style_match else ""
    perf_css_content = perf_style_match.group(1) if perf_style_match else ""

    # สร้าง CSS รวม และเพิ่ม style สำหรับการแบ่งหน้า (Batch Print Specific)
    # เราใช้ !important เพื่อทับค่าที่อาจจะติดมาจากไฟล์ต้นฉบับ
    full_css = f"""
    <style>
        /* --- Base Styles from Files --- */
        {main_css_content}
        {perf_css_content}

        /* --- BATCH PRINT OVERRIDES --- */
        @media print {{
            @page {{
                size: A4;
                margin: 0 !important; /* Reset page margins, let container padding handle it */
            }}

            html, body {{ 
                margin: 0 !important; 
                padding: 0 !important; 
                width: 210mm !important;
                height: auto !important; /* Allow growing height for multiple pages */
                min-height: 100vh !important;
                background-color: white !important;
                -webkit-print-color-adjust: exact !important; 
                print-color-adjust: exact !important;
                overflow: visible !important; /* Ensure no clipping */
            }}
            
            /* Wrapper ของคนไข้แต่ละคน */
            .patient-wrapper {{
                display: block;
                width: 100%;
                margin: 0;
                padding: 0;
                page-break-after: always !important; /* จบคนนึงขึ้นหน้าใหม่ */
                break-after: page !important;
            }}
            
            /* หน้าสุดท้ายของคนสุดท้ายไม่ต้อง break */
            .patient-wrapper:last-child {{
                page-break-after: auto !important;
                break-after: auto !important;
            }}

            /* Container ของแต่ละรายงาน (สุขภาพ/สมรรถภาพ) */
            .container {{
                box-sizing: border-box !important;
                margin: 0 !important;
                padding: 0.5cm !important; /* ขอบ 0.5cm */
                width: 210mm !important;
                
                /* ใช้ min-height A4 เพื่อดัน Footer ไปล่างสุดถ้าเนื้อหาน้อย */
                min-height: 297mm !important; 
                height: auto !important; 
                
                position: relative !important;
                background-color: white !important;
                overflow: visible !important; /* ห้ามซ่อนเนื้อหา */
                
                /* ห้าม break ในตัว container เองโดยไม่จำเป็น */
                page-break-inside: avoid;
            }}

            /* ตัวคั่นระหว่างรายงานสุขภาพและสมรรถภาพ */
            .report-separator {{
                display: block;
                height: 0;
                margin: 0;
                padding: 0;
                page-break-before: always !important; /* ขึ้นหน้าใหม่เสมอ */
                break-before: page !important;
            }}
            
            /* Footer Fix */
            .footer {{
                position: absolute !important;
                bottom: 0.5cm !important; /* ติดขอบล่าง 0.5cm */
                left: 0 !important;
                width: 100% !important;
            }}
        }}
        
        /* Screen view adjustments */
        @media screen {{
            .patient-wrapper {{
                border-bottom: 5px solid #ccc;
                margin-bottom: 20px;
                padding-bottom: 20px;
            }}
            .report-separator {{
                border-top: 2px dashed #999;
                margin: 20px 0;
                position: relative;
            }}
            .report-separator::after {{
                content: "--- Page Break (Next Report) ---";
                position: absolute;
                top: -12px;
                left: 50%;
                transform: translateX(-50%);
                background: white;
                padding: 0 10px;
                color: #666;
                font-size: 12px;
            }}
        }}
    </style>
    """

    progress_bar = st.progress(0)
    total_patients = len(selected_hns)
    skipped_count = 0
    
    for i, hn in enumerate(selected_hns):
        try:
            progress_bar.progress((i + 1) / total_patients, text=f"กำลังสร้างรายงานคนที่ {i+1}/{total_patients} (HN: {hn})")
            
            person_history_df = df[df['HN'] == hn].copy()
            if person_history_df.empty:
                skipped_count += 1
                continue

            latest_year_series = person_history_df.sort_values(by='Year', ascending=False).iloc[0]
            person_data = latest_year_series.to_dict()

            parts = []
            
            # 1. Health Report Part
            need_main = report_type in ["รายงานสุขภาพ (Health Report)", "ทั้งรายงานสุขภาพและสมรรถภาพ"]
            if need_main and has_basic_health_data(person_data):
                parts.append(render_printable_report_body(person_data, person_history_df))
            
            # 2. Performance Report Part
            need_perf = report_type in ["รายงานสมรรถภาพ (Performance Report)", "ทั้งรายงานสุขภาพและสมรรถภาพ"]
            has_vis = has_vision_data(person_data)
            has_hear = has_hearing_data(person_data)
            has_lung = has_lung_data(person_data)
            
            if need_perf and (has_vis or has_hear or has_lung):
                parts.append(render_performance_report_body(person_data, person_history_df))

            if not parts:
                skipped_count += 1
                continue
            
            # Join parts with a dedicated separator div
            patient_html_content = '<div class="report-separator"></div>'.join(parts)
            
            # Wrap in patient wrapper
            report_bodies.append(f'<div class="patient-wrapper">{patient_html_content}</div>')

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด HN: {hn} - {e}")
            continue 

    progress_bar.empty()

    if not report_bodies:
        return None, skipped_count

    all_bodies = "".join(report_bodies)
    
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

# --- Callback Functions ---

def add_patient_to_list_callback(df):
    """Callback สำหรับปุ่มเพิ่มรายการ"""
    name = st.session_state.get("bp_name_search")
    hn = st.session_state.get("bp_hn_search")
    cid = st.session_state.get("bp_cid_search")
    
    target_hn = None
    found_msg = ""
    
    if name:
        matched = df[df['ชื่อ-สกุล'] == name]
        if not matched.empty:
            target_hn = matched.iloc[0]['HN']
            found_msg = f"เพิ่มคุณ {name} เรียบร้อย"
    elif hn:
        matched = df[df['HN'].astype(str) == hn.strip()]
        if not matched.empty:
            target_hn = matched.iloc[0]['HN']
            name_found = matched.iloc[0]['ชื่อ-สกุล']
            found_msg = f"เพิ่ม HN {hn} ({name_found}) เรียบร้อย"
    elif cid:
        matched = df[df['เลขบัตรประชาชน'].astype(str) == cid.strip()]
        if not matched.empty:
            target_hn = matched.iloc[0]['HN']
            name_found = matched.iloc[0]['ชื่อ-สกุล']
            found_msg = f"เพิ่มเลขบัตร {cid} ({name_found}) เรียบร้อย"
            
    if target_hn:
        if 'bp_manual_hns' not in st.session_state:
            st.session_state.bp_manual_hns = set()
            
        st.session_state.bp_manual_hns.add(target_hn)
        st.session_state.bp_action_msg = {"type": "success", "text": found_msg}
        
        # Reset inputs
        st.session_state.bp_name_search = None 
        st.session_state.bp_hn_search = ""
        st.session_state.bp_cid_search = ""
        
    else:
        st.session_state.bp_action_msg = {"type": "error", "text": "❌ ไม่พบข้อมูล หรือไม่ได้ระบุเงื่อนไขการค้นหา"}

def remove_hn_callback(hn_to_remove):
    """Callback ลบ HN"""
    if 'bp_manual_hns' in st.session_state and hn_to_remove in st.session_state.bp_manual_hns:
        st.session_state.bp_manual_hns.remove(hn_to_remove)

def display_print_center_page(df):
    """แสดงหน้าจอ Print Center"""
    st.title("🖨️ ศูนย์จัดการพิมพ์รายงาน (Print Center)")
    st.markdown("---")
    
    # --- CSS Styling (Clean & Precise Alignment) ---
    st.markdown("""
    <style>
        /* ปุ่มเพิ่มรายการ (Primary) */
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #1B5E20 !important;
            color: #ffffff !important;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            width: 100%;
            font-size: 1rem;
            font-weight: 600;
            min-height: 48px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #2E7D32 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        /* --- Custom Grid Styling --- */
        
        /* Data Row Container */
        .grid-row {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128,128,128,0.1);
            border-radius: 8px;
            padding: 5px 0;
            margin-bottom: 8px;
            display: flex;
            align-items: center; /* Vertical Center */
            min-height: 50px;
        }
        
        /* Text Cell Content */
        .grid-cell-text {
            font-size: 0.95rem;
            color: var(--text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding: 0 5px;
            line-height: 1.5;
        }
        
        /* Status Badge */
        .status-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
            white-space: nowrap;
        }
        .status-green { background-color: rgba(76, 175, 80, 0.15); color: #1b5e20; }
        .status-orange { background-color: rgba(255, 152, 0, 0.15); color: #e65100; }
        .status-red { background-color: rgba(244, 67, 54, 0.15); color: #c62828; }
        .status-blue { background-color: rgba(33, 150, 243, 0.15); color: #0d47a1; }
        .status-gray { background-color: rgba(158, 158, 158, 0.15); color: var(--text-color); }

        /* ปุ่มลบ (Secondary) - Minimal Gray Style */
        /* Target เฉพาะปุ่มในตารางเพื่อความปลอดภัย */
        div[data-testid="column"] button[kind="secondary"] {
            border: 1px solid transparent !important;
            background-color: transparent !important;
            color: #757575 !important; /* สีเทา */
            padding: 0 !important;
            font-size: 1.2rem !important; /* ไอคอนใหญ่ขึ้น */
            line-height: 1 !important;
            height: 40px !important;
            width: 40px !important;
            border-radius: 50% !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 auto !important; /* จัดกึ่งกลางแนวนอน */
        }
        div[data-testid="column"] button[kind="secondary"]:hover {
            background-color: rgba(0,0,0,0.05) !important;
            color: #333 !important;
            transform: scale(1.1);
        }
        
        /* [DELETED] ลบ Global Column Center Override ที่รุนแรงออกแล้ว */
        /* เพื่อให้ vertical_alignment="center" ทำงานได้ถูกต้องตามปกติ */
    </style>
    """, unsafe_allow_html=True)

    # --- Session State Init ---
    if 'bp_dept_filter' not in st.session_state: st.session_state.bp_dept_filter = []
    if 'bp_date_filter' not in st.session_state: st.session_state.bp_date_filter = "(ทั้งหมด)"
    if 'bp_report_type' not in st.session_state: st.session_state.bp_report_type = "รายงานสุขภาพ (Health Report)"
    if 'bp_name_search' not in st.session_state: st.session_state.bp_name_search = None
    if 'bp_hn_search' not in st.session_state: st.session_state.bp_hn_search = ""
    if 'bp_cid_search' not in st.session_state: st.session_state.bp_cid_search = ""
    if 'bp_manual_hns' not in st.session_state: st.session_state.bp_manual_hns = set()

    # --- 1. เลือกประเภทรายงาน ---
    st.subheader("1. เลือกประเภทรายงาน")
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

    # --- 2. ค้นหาและเพิ่มผู้ป่วย ---
    st.subheader("2. ค้นหาและเพิ่มรายชื่อ (ทีละคน)")
    
    if 'bp_action_msg' in st.session_state:
        msg = st.session_state.bp_action_msg
        if msg['type'] == 'success':
            st.success(msg['text'])
        else:
            st.error(msg['text'])
        del st.session_state.bp_action_msg
    
    # Input Row
    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    with c1:
        all_names = sorted(df['ชื่อ-สกุล'].dropna().unique().tolist())
        st.selectbox("ค้นหาด้วยชื่อ-สกุล", options=all_names, index=None, placeholder="พิมพ์หรือเลือกชื่อ...", key="bp_name_search")
    with c2:
        st.text_input("ค้นหาด้วย HN", key="bp_hn_search", placeholder="พิมพ์ HN")
    with c3:
        st.text_input("ค้นหาด้วยเลขบัตรฯ", key="bp_cid_search", placeholder="พิมพ์เลขบัตร")

    # Button Row: ใช้สัดส่วน 2:3 เพื่อให้ปุ่มตรงกับช่อง "ชื่อ-สกุล" ด้านบน
    col_add, _ = st.columns([2, 3])
    with col_add:
        st.button("➕ เพิ่มลงรายการ", use_container_width=True, on_click=add_patient_to_list_callback, args=(df,))
    
    st.markdown("---")
    
    # Bulk Filter
    st.write("หรือเลือกเพิ่มจากกลุ่มหน่วยงาน (Bulk Selection)")
    c4, c5 = st.columns(2)
    with c4:
        all_depts = sorted(df['หน่วยงาน'].dropna().astype(str).str.strip().unique())
        selected_depts = st.multiselect("กรองตามหน่วยงาน", options=all_depts, placeholder="เลือกหน่วยงาน...", key="bp_dept_filter")
    with c5:
        temp_df = df.copy()
        if selected_depts:
            temp_df = temp_df[temp_df['หน่วยงาน'].astype(str).str.strip().isin(selected_depts)]
        available_dates = sorted(temp_df['วันที่ตรวจ'].dropna().astype(str).unique(), reverse=True)
        date_options = ["(ทั้งหมด)"] + list(available_dates)
        
        idx = 0
        if st.session_state.bp_date_filter in date_options: idx = date_options.index(st.session_state.bp_date_filter)
        selected_date = st.selectbox("กรองตามวันที่ตรวจ", options=date_options, index=idx, key="bp_date_filter")

    # --- 3. รายชื่อที่เลือก (Custom Grid Table) ---
    st.subheader("3. รายชื่อที่เลือก (รอสั่งพิมพ์)")
    
    # Data Preparation
    filtered_df = pd.DataFrame(columns=df.columns)
    filter_active = False
    if selected_depts or (selected_date != "(ทั้งหมด)"):
        filtered_df = df.copy()
        if selected_depts: filtered_df = filtered_df[filtered_df['หน่วยงาน'].astype(str).str.strip().isin(selected_depts)]
        if selected_date != "(ทั้งหมด)": filtered_df = filtered_df[filtered_df['วันที่ตรวจ'].astype(str) == selected_date]
        filter_active = True

    manual_hns = list(st.session_state.bp_manual_hns)
    manual_df = df[df['HN'].isin(manual_hns)].copy()
    
    if filter_active:
        display_pool = pd.concat([manual_df, filtered_df]).drop_duplicates(subset=['HN'])
    elif manual_hns:
        display_pool = manual_df
    else:
        display_pool = pd.DataFrame(columns=df.columns)

    display_pool = display_pool.sort_values(by=['Year'], ascending=False)
    unique_patients_df = display_pool.drop_duplicates(subset=['HN'])
    
    selected_to_print_hns = []
    
    # Limit rows
    ROW_LIMIT = 200
    if len(unique_patients_df) > ROW_LIMIT:
        st.warning(f"⚠️ แสดงผล {ROW_LIMIT} คนแรก จากทั้งหมด {len(unique_patients_df)} คน (เพื่อความรวดเร็ว)")
        unique_patients_df = unique_patients_df.head(ROW_LIMIT)

    if unique_patients_df.empty:
        if filter_active: st.info("ไม่พบข้อมูลตามเงื่อนไขหน่วยงาน/วันที่")
        else: st.info("ยังไม่มีรายชื่อในรายการ กรุณากดปุ่ม ➕ เพิ่มรายชื่อ")
    else:
        # --- Config Ratio ---
        col_ratios = [0.6, 0.6, 1.2, 1.2, 2.5, 1.5, 1.2]

        # --- Data Rows Loop ---
        for i, row in unique_patients_df.iterrows():
            hn = row['HN']
            full_data = row.to_dict()
            is_ready, status_text, status_color = check_data_readiness(full_data, report_type)
            
            is_manual = hn in manual_hns
            default_chk = is_ready and is_manual
            
            # Row Container (Styled by CSS .grid-row to be flex)
            with st.container():
                # ใช้ vertical_alignment="center" ช่วยจัด widget ให้ตรงกลางแนวตั้ง (Native Streamlit feature)
                cols = st.columns(col_ratios, vertical_alignment="center")
                
                # 1. Delete Button
                with cols[0]:
                    if st.button("🗑️", key=f"del_{hn}", help="ลบรายการนี้", type="secondary"):
                        remove_hn_callback(hn)
                        st.rerun()
                
                # 2. Checkbox
                with cols[1]:
                    # [EDITED] ลบการซ้อนคอลัมน์ [1,1,1] ที่ทำให้ Layout พัง
                    is_selected = st.checkbox("เลือก", value=default_chk, key=f"sel_{hn}", label_visibility="collapsed")
                    if is_selected:
                        selected_to_print_hns.append(hn)

                # 3. Status Badge (Use HTML for consistent height)
                with cols[2]:
                    st.markdown(f"<div style='text-align:center;'><span class='status-badge status-{status_color}'>{status_text}</span></div>", unsafe_allow_html=True)

                # 4. HN (Use HTML)
                with cols[3]:
                    st.markdown(f"<div class='grid-cell-text' style='text-align:center; font-family:monospace;'>{hn}</div>", unsafe_allow_html=True)

                # 5. Name (Use HTML)
                with cols[4]:
                    st.markdown(f"<div class='grid-cell-text' style='text-align:left;'>{row['ชื่อ-สกุล']}</div>", unsafe_allow_html=True)

                # 6. Dept (Use HTML)
                with cols[5]:
                    st.markdown(f"<div class='grid-cell-text' style='text-align:left; color:#666;'>{row['หน่วยงาน']}</div>", unsafe_allow_html=True)

                # 7. Date (Use HTML)
                with cols[6]:
                    st.markdown(f"<div class='grid-cell-text' style='text-align:center;'>{str(row['วันที่ตรวจ']).split(' ')[0]}</div>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin:0; opacity:0.1; border-top:1px solid #ddd;'>", unsafe_allow_html=True)

        # --- Footer Actions ---
        col_summary, col_clear_btn = st.columns([4, 1])
        with col_clear_btn:
             if manual_hns:
                if st.button("🗑️ ล้างรายการทั้งหมด", type="secondary", use_container_width=True):
                    st.session_state.bp_manual_hns = set()
                    st.rerun()

    # --- Print Button ---
    count_selected = len(selected_to_print_hns)
    st.markdown("")
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if st.button(f"สั่งพิมพ์รายงาน ({count_selected} ท่าน)", type="primary", use_container_width=True, disabled=(count_selected == 0)):
            if count_selected > 0:
                html_content, skipped = generate_batch_html(df, selected_to_print_hns, report_type)
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
