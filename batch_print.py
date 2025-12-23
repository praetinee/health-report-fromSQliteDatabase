import streamlit as st
import pandas as pd
import html
import json
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
            return True, "ข้อมูลพร้อม", "green"
        else:
            return False, "ขาดผลตรวจสุขภาพ", "orange"
            
    elif report_type == "รายงานสมรรถภาพ (Performance Report)":
        if has_perf:
            details = []
            if has_vis: details.append("ตา")
            if has_hear: details.append("หู")
            if has_lung: details.append("ปอด")
            return True, f"มีผล: {','.join(details)}", "green"
        else:
            return False, "ไม่มีผลสมรรถภาพ", "orange"
            
    elif report_type == "ทั้งรายงานสุขภาพและสมรรถภาพ":
        if has_main and has_perf:
            return True, "ข้อมูลครบถ้วน", "green"
        elif has_main:
            return True, "ขาดผลสมรรถภาพ", "blue" 
        elif has_perf:
            return True, "ขาดผลสุขภาพ", "blue"
        else:
            return False, "ไม่มีข้อมูล", "red"

    return is_ready, status_text, status_color

def generate_batch_html(df, selected_hns, report_type, year_logic="ใช้ข้อมูลปีล่าสุดของแต่ละคน"):
    """สร้าง HTML สำหรับพิมพ์"""
    report_bodies = []
    page_break_div = "<div style='page-break-after: always;'></div>"
    
    css_main = get_main_report_css()
    css_perf = get_performance_report_css()
    full_css = f"{css_main}\n{css_perf}" 

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

            patient_bodies = []
            
            need_main = report_type in ["รายงานสุขภาพ (Health Report)", "ทั้งรายงานสุขภาพและสมรรถภาพ"]
            if need_main and has_basic_health_data(person_data):
                patient_bodies.append(render_printable_report_body(person_data, person_history_df))
            
            need_perf = report_type in ["รายงานสมรรถภาพ (Performance Report)", "ทั้งรายงานสุขภาพและสมรรถภาพ"]
            has_vis = has_vision_data(person_data)
            has_hear = has_hearing_data(person_data)
            has_lung = has_lung_data(person_data)
            if need_perf and (has_vis or has_hear or has_lung):
                patient_bodies.append(render_performance_report_body(person_data, person_history_df))

            if not patient_bodies:
                skipped_count += 1
                continue
            
            combined_patient_html = page_break_div.join(patient_bodies)
            report_bodies.append(combined_patient_html)

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด HN: {hn} - {e}")
            continue 

    progress_bar.empty()

    if not report_bodies:
        return None, skipped_count

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
    
    # --- Modern & Beautiful CSS ---
    st.markdown("""
    <style>
        /* ปุ่มเพิ่มรายการ (Primary) - สีเขียว */
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
            color: white !important;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            width: 100%;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }

        /* --- List Card Design --- */
        .queue-container {
            margin-top: 10px;
        }
        
        .queue-header-row {
            display: flex;
            align-items: center;
            background-color: #f1f3f4;
            color: #555;
            font-weight: 600;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 0.9rem;
        }

        .queue-card {
            background-color: white;
            border: 1px solid #eee;
            border-radius: 12px;
            padding: 12px 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
        }
        .queue-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-color: #ddd;
            transform: translateX(2px);
        }

        /* Text Styles */
        .patient-name {
            font-size: 1rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 2px;
        }
        .patient-hn {
            font-size: 0.8rem;
            color: #888;
            font-family: monospace;
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .meta-text {
            font-size: 0.85rem;
            color: #555;
            line-height: 1.4;
        }
        .meta-label {
            color: #999;
            font-size: 0.75rem;
            margin-right: 4px;
        }

        /* Status Badge Pills */
        .status-pill {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .status-green { background-color: #E8F5E9; color: #2E7D32; border: 1px solid #C8E6C9; }
        .status-orange { background-color: #FFF3E0; color: #EF6C00; border: 1px solid #FFE0B2; }
        .status-red { background-color: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; }
        .status-blue { background-color: #E3F2FD; color: #1565C0; border: 1px solid #BBDEFB; }
        .status-gray { background-color: #F5F5F5; color: #757575; border: 1px solid #E0E0E0; }

        /* Delete Button Customization */
        div[data-testid="column"] button[kind="secondary"] {
            border: 1px solid transparent !important;
            background-color: transparent !important;
            color: #9E9E9E !important;
            transition: color 0.2s;
        }
        div[data-testid="column"] button[kind="secondary"]:hover {
            color: #D32F2F !important;
            background-color: #FFEBEE !important;
            border-color: #FFCDD2 !important;
        }
        
        /* Checkbox Customization */
        label[data-testid="stCheckbox"] {
            margin-top: 4px; /* Align with text */
        }
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

    # Button Row
    col_add, _ = st.columns([2, 3])
    with col_add:
        st.button("➕ เพิ่มลงรายการ", use_container_width=True, on_click=add_patient_to_list_callback, args=(df,))
    
    st.markdown("---")
    
    # Bulk Filter
    with st.expander("📂 เพิ่มจากกลุ่มหน่วยงาน (Bulk Selection)", expanded=False):
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

    # --- 3. รายชื่อที่เลือก (รอสั่งพิมพ์) - NEW DESIGN ---
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
        st.info("💡 ยังไม่มีรายชื่อในรายการ กรุณากดปุ่ม ➕ เพิ่มรายชื่อด้านบน")
    else:
        # --- List Action Bar ---
        col_select_all, _, col_clear = st.columns([2, 3, 2])
        with col_clear:
             if manual_hns:
                if st.button("🗑️ ล้างรายการทั้งหมด", type="secondary", use_container_width=True):
                    st.session_state.bp_manual_hns = set()
                    st.rerun()

        # --- Queue Container ---
        st.markdown('<div class="queue-container">', unsafe_allow_html=True)
        
        # Header Row
        h_ratios = [0.5, 3, 2, 1.5, 0.5]
        h_cols = st.columns(h_ratios)
        h_cols[0].markdown("<div style='text-align:center; font-weight:bold; color:#777;'>เลือก</div>", unsafe_allow_html=True)
        h_cols[1].markdown("<div style='text-align:left; font-weight:bold; color:#777;'>ชื่อ-สกุล / HN</div>", unsafe_allow_html=True)
        h_cols[2].markdown("<div style='text-align:left; font-weight:bold; color:#777;'>หน่วยงาน / วันที่</div>", unsafe_allow_html=True)
        h_cols[3].markdown("<div style='text-align:center; font-weight:bold; color:#777;'>สถานะข้อมูล</div>", unsafe_allow_html=True)
        h_cols[4].markdown("<div style='text-align:center; font-weight:bold; color:#777;'>ลบ</div>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 5px 0 15px 0; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)

        # Loop Rows
        for i, row in unique_patients_df.iterrows():
            hn = row['HN']
            full_data = row.to_dict()
            is_ready, status_text, status_color = check_data_readiness(full_data, report_type)
            
            is_manual = hn in manual_hns
            default_chk = is_ready and is_manual
            
            # Card Styling wrapper
            with st.container():
                st.markdown(f"""
                <div class="queue-card">
                """, unsafe_allow_html=True)
                
                # Widget Layout inside the card
                cols = st.columns(h_ratios, vertical_alignment="center")
                
                # 1. Checkbox (Center)
                with cols[0]:
                    _, chk_col, _ = st.columns([0.2, 1, 0.2])
                    with chk_col:
                        is_selected = st.checkbox("เลือก", value=default_chk, key=f"sel_{hn}", label_visibility="collapsed")
                        if is_selected:
                            selected_to_print_hns.append(hn)

                # 2. Patient Info (Name + HN)
                with cols[1]:
                    st.markdown(f"""
                    <div class="patient-name">{row['ชื่อ-สกุล']}</div>
                    <span class="patient-hn">{hn}</span>
                    """, unsafe_allow_html=True)

                # 3. Meta Info (Dept + Date)
                with cols[2]:
                    check_date = str(row['วันที่ตรวจ']).split(' ')[0]
                    st.markdown(f"""
                    <div class="meta-text"><span class="meta-label">แผนก:</span> {row['หน่วยงาน']}</div>
                    <div class="meta-text"><span class="meta-label">วันที่:</span> {check_date}</div>
                    """, unsafe_allow_html=True)

                # 4. Status Badge
                with cols[3]:
                    st.markdown(f"""
                    <div style="text-align:center;">
                        <span class="status-pill status-{status_color}">{status_text}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # 5. Delete Button
                with cols[4]:
                    if st.button("🗑️", key=f"del_{hn}", help="ลบรายการนี้ออกจากคิว", type="secondary"):
                        remove_hn_callback(hn)
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True) # End queue-card

        st.markdown('</div>', unsafe_allow_html=True) # End queue-container


    # --- Print Button Section ---
    count_selected = len(selected_to_print_hns)
    st.markdown("")
    
    # Floating Bottom Bar Styling
    st.markdown("""
    <style>
        .print-action-bar {
            background-color: #F0F4C3;
            border: 1px solid #DCE775;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

    if count_selected > 0:
        st.markdown(f"""
        <div class="print-action-bar">
            <h4 style="margin:0; color:#33691E;">พร้อมพิมพ์รายงาน {count_selected} ท่าน</h4>
        </div>
        """, unsafe_allow_html=True)
        
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            if st.button(f"🖨️ สั่งพิมพ์รายงาน ({count_selected})", type="primary", use_container_width=True):
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
    else:
        if not unique_patients_df.empty:
            st.info("กรุณาเลือกรายชื่อที่ต้องการพิมพ์จากรายการด้านบน")

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
