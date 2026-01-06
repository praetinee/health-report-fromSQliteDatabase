import streamlit as st

# -----------------------------------------------------------------------------
# ⚠️ 1. ต้องใส่ set_page_config เป็นบรรทัดแรกสุดเสมอ
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Health Report System", layout="wide")

import sqlite3
import requests
import pandas as pd
import tempfile
import os
import json
from collections import OrderedDict
from datetime import datetime

# --- Import Authentication & Consent ---
from auth import authentication_flow, pdpa_consent_page

# --- Import Line Register (Modules) ---
from line_register import (
    save_new_user_to_gsheet, 
    check_if_user_registered, 
    normalize_db_name_field,
    render_registration_page,
    render_admin_line_manager
)

# --- Import Print Functions ---
try:
    from print_report import generate_printable_report
except Exception:
    def generate_printable_report(*args): return ""

try:
    from print_performance_report import generate_performance_report_html
except Exception:
    def generate_performance_report_html(*args): return ""

# --- Import Utils ---
try:
    from utils import (
        is_empty, has_basic_health_data, 
        has_vision_data, has_hearing_data, has_lung_data, has_visualization_data
    )
except Exception:
    def is_empty(v): return pd.isna(v) or str(v).strip() == ""
    def has_basic_health_data(r): return True
    def has_vision_data(r): return False
    def has_hearing_data(r): return False
    def has_lung_data(r): return False
    def has_visualization_data(d): return False

# --- Import Visualization ---
try:
    from visualization import display_visualization_tab
except Exception:
    def display_visualization_tab(d, a): st.info("No visualization module")

# --- Import Shared UI ---
try:
    from shared_ui import (
        inject_custom_css, 
        display_common_header,
        display_main_report, 
        display_performance_report
    )
except Exception:
    def inject_custom_css(): pass
    def display_common_header(data): st.write(f"**รายงานผลสุขภาพ:** {data.get('ชื่อ-สกุล', '-')}")
    def display_main_report(p, a): st.error("Main Report Module Missing")
    def display_performance_report(p, t, a=None): pass

# --- Import Admin Panel ---
try:
    from admin_panel import display_admin_panel
except Exception:
    def display_admin_panel(df): st.error("Admin Panel Error")

# -----------------------------------------------------------------------------
# Configuration & Helper Functions
# -----------------------------------------------------------------------------

GAS_URL = "https://script.google.com/macros/s/AKfycbzmtd5H-YZr8EeeTUab3M2L2nEtUofDBtYCP9-CN6MVfIff94P6lDWS-cUHCi9asLlR/exec"
SQLITE_CITIZEN_ID_COL = "เลขบัตรประชาชน"  
SQLITE_NAME_COL = "ชื่อ-สกุล"           

def normalize_cid(val):
    """ฟังก์ชันทำความสะอาดเลขบัตรประชาชนให้เป็นตัวเลข 13 หลักล้วน"""
    if pd.isna(val): return ""
    s = str(val).strip().replace("-", "").replace(" ", "").replace("'", "").replace('"', "")
    if "E" in s or "e" in s:
        try: s = str(int(float(s)))
        except: pass
    if s.endswith(".0"): s = s[:-2]
    return s

def get_user_info_from_gas(line_user_id):
    """ถาม Google Sheet ว่า UserID นี้คือใคร"""
    try:
        url = f"{GAS_URL}?action=get_user&line_id={line_user_id}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"found": False, "error": str(e)}

# -----------------------------------------------------------------------------
# Data Loading
# -----------------------------------------------------------------------------
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
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
        st.session_state['debug_tables'] = tables['name'].tolist()
        table_name = "health_data" 
        if table_name not in st.session_state['debug_tables']:
             if len(st.session_state['debug_tables']) > 0: table_name = st.session_state['debug_tables'][0]
        df_loaded = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        conn.close()
        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['HN'] = df_loaded['HN'].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith('.0') else x)
        if SQLITE_NAME_COL in df_loaded.columns:
            df_loaded[SQLITE_NAME_COL] = df_loaded[SQLITE_NAME_COL].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        if SQLITE_CITIZEN_ID_COL in df_loaded.columns:
            df_loaded[SQLITE_CITIZEN_ID_COL] = df_loaded[SQLITE_CITIZEN_ID_COL].apply(normalize_cid)
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

# -----------------------------------------------------------------------------
# Main App Logic
# -----------------------------------------------------------------------------
def main_app(df):
    inject_custom_css()
    if 'user_hn' not in st.session_state: st.stop()
    user_hn = st.session_state['user_hn']
    results_df = df[df['HN'] == user_hn].copy()
    st.session_state['search_result'] = results_df

    if results_df.empty:
        st.error(f"ไม่พบข้อมูลผลตรวจสำหรับ HN: {user_hn}")
        if st.button("กลับหน้าหลัก"): st.session_state.clear(); st.rerun()
        return

    available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
    if 'selected_year' not in st.session_state or st.session_state.selected_year not in available_years:
        st.session_state.selected_year = available_years[0]

    # --- ส่วน Header ใหม่ (แทน Sidebar) ---
    st.markdown("---") # เส้นคั่นสวยงาม
    col_info, col_year = st.columns([2, 1])
    
    with col_info:
        # 1. เอา Emoji และคำว่า สวัสดี ออก เหลือแค่ คุณ [ชื่อ]
        st.markdown(f"### คุณ {st.session_state.get('user_name', '')}")
        st.caption(f"เลข HN: {user_hn}")

    with col_year:
        st.selectbox(
            "📅 เลือกปี พ.ศ. ที่ตรวจ", 
            available_years, 
            index=available_years.index(st.session_state.selected_year), 
            format_func=lambda y: f"พ.ศ. {y}", 
            key="year_select", 
            on_change=lambda: st.session_state.update({"selected_year": st.session_state.year_select})
        )

    # --- ส่วนเมนูพิมพ์ (Toolbar Style) ---
    # เราจะใช้ CSS Media Query เพื่อซ่อนส่วนนี้เมื่อหน้าจอเล็กกว่า 992px (Tablet/Mobile)
    st.markdown("""
        <style>
        /* จัดตำแหน่งปุ่มให้สวยงาม */
        div[data-testid="column"] {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Default: แสดงผลบน Desktop */
        .desktop-only-container {
            display: block;
        }

        /* Mobile & Tablet: ซ่อนการแสดงผล */
        @media (max-width: 992px) {
            .desktop-only-container {
                display: none !important;
            }
            /* ซ่อนปุ่ม Streamlit ที่อยู่ใน Container นี้ด้วย (อาจต้องใช้ CSS Selector ที่เจาะจงถ้า wrapper ไม่ทำงาน) */
            /* แต่เนื่องจาก Streamlit ไม่ให้เรา Wrap Widgets ด้วย div โดยตรงง่ายๆ เราจะใช้ Logic ซ่อน Container แทน */
        }
        </style>
    """, unsafe_allow_html=True)

    # ใช้ st.container() เพื่อกลุ่ม Widget และเราจะ Inject CSS เพื่อซ่อนมันไม่ได้โดยตรง 
    # ดังนั้นเราต้องใช้เทคนิค CSS Selector ที่ซับซ้อน หรือวิธีที่ง่ายกว่าคือ "JavaScript" เช็คขนาดหน้าจอ (แต่มันจะช้า)
    # วิธีที่เสถียรที่สุดใน Streamlit คือการยอมรับข้อจำกัดว่าเรา Wrap Widget ไม่ได้เป๊ะๆ
    
    # *** วิธีแก้: ใช้ st.markdown สร้าง Div เปล่าๆ เพื่อบอก CSS ว่า "พื้นที่แถวนี้คือ Desktop Only" ***
    # แล้วใช้ CSS :has() หรือ Adjacent Sibling Selector (ถ้าทำได้)
    # หรือใช้วิธีที่ง่ายที่สุดคือ: ซ่อนทั้ง Block โดยใช้ CSS targeting element ID หรือ structure (ยากเพราะ ID เปลี่ยน)
    
    # *** วิธีที่แนะนำ: ใช้ CSS ซ่อนปุ่มเฉพาะบน Mobile โดยดูจาก attribute ***
    # เราจะใส่ key ให้ปุ่ม แล้วใช้ CSS เลือกปุ่มที่มี attribute นั้นๆ
    
    st.markdown("""
        <style>
        @media (max-width: 992px) {
            /* ซ่อนปุ่มพิมพ์ */
            div[data-testid="stButton"] button:has(div:contains("พิมพ์รายงานสุขภาพ")),
            div[data-testid="stButton"] button:has(div:contains("พิมพ์รายงานสมรรถภาพ")) {
                display: none !important;
            }
            /* ซ่อนข้อความ Label "เมนูพิมพ์รายงาน" */
            h5:contains("เมนูพิมพ์รายงาน") {
                display: none !important;
            }
            /* ซ่อน hr ที่เราใส่ไว้ */
            hr {
                display: none;
            }
            /* แสดง hr เฉพาะอันที่จำเป็น (ถ้าต้องการ) */
        }
        </style>
        
        <script>
        // Script เสริมเพื่อความชัวร์ (ถ้า CSS :has ไม่ support ในบาง browser เก่า)
        // แต่จริงๆ แค่ CSS ก็ครอบคลุมส่วนใหญ่แล้ว
        </script>
    """, unsafe_allow_html=True)

    # --- ส่วนแสดงผลเมนูพิมพ์ (จะถูกซ่อนด้วย CSS บนมือถือ) ---
    # ใช้ Container เพื่อให้ง่ายต่อการจัดการ (แต่ Streamlit Container ไม่มี Class)
    
    # เริ่มส่วน Desktop Only Area
    # (เราจะใช้ st.markdown เพื่อสร้างเส้นคั่น และ CSS จะซ่อนมันเอง)
    
    # --- เช็ค User Agent หรือ Screen Width ใน Python ไม่ได้แม่นยำใน Streamlit ---
    # ดังนั้นเราจะ Render ปุ่มไปตามปกติ แต่ให้ CSS ซ่อนมัน
    
    # สร้าง Container สำหรับส่วนพิมพ์
    print_container = st.container()
    
    with print_container:
        st.markdown('<div class="desktop-only-print-section"></div>', unsafe_allow_html=True)
        st.markdown("""
            <style>
            @media (max-width: 992px) {
                /* ซ่อนเนื้อหาทั้งหมดใน Container นี้ (ที่เป็นไปได้) */
                /* เนื่องจากเรา wrap ไม่ได้ เราจะใช้เทคนิคซ่อน Element ที่อยู่ถัดจาก marker div */
                /* แต่วิธีที่ง่ายและชัวร์สุดคือซ่อน "ปุ่ม" โดยตรง */
                
                button[kind="secondary"] {
                     /* ระวังไปโดนปุ่มอื่น */
                }
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("---")
        c_label, c_btn1, c_btn2 = st.columns([1.2, 1, 1], gap="small")
        
        with c_label:
            st.markdown("<h5 class='print-label' style='margin:0; padding:0; text-align:center; white-space:nowrap;'>🖨️ เมนูพิมพ์รายงาน</h5>", unsafe_allow_html=True)
        
        with c_btn1:
            if st.button("พิมพ์รายงานสุขภาพ", key="print_health", use_container_width=True):
                st.session_state.print_trigger = True
                
        with c_btn2:
            if st.button("พิมพ์รายงานสมรรถภาพ", key="print_perf", use_container_width=True):
                st.session_state.print_performance_trigger = True
        
        st.markdown("---")

    # ใส่ CSS เพื่อซ่อนส่วนพิมพ์บนมือถือ (Mobile/Tablet)
    st.markdown("""
        <style>
        @media (max-width: 992px) {
            /* ซ่อนปุ่มที่มี Key เฉพาะ (Streamlit สร้าง class ตาม key ไม่ได้โดยตรง แต่เราใช้ text content ได้) */
            
            /* ซ่อนปุ่มที่มีข้อความ 'พิมพ์รายงานสุขภาพ' */
            button p:contains('พิมพ์รายงานสุขภาพ'), 
            button p:contains('พิมพ์รายงานสมรรถภาพ') {
                /* วิธีนี้ใช้ไม่ได้ใน CSS มาตรฐาน (contains) */
            }

            /* วิธีที่ใช้ได้จริง: ซ่อน row ที่ 3,4,5 ของ app (วิธีนี้เสี่ยงถ้า layout เปลี่ยน) */
            
            /* วิธีที่ดีที่สุด: ยอมให้แสดง แต่แจ้งเตือน หรือ ซ่อนด้วย Javascript */
            
            /* --- CSS Hack เพื่อซ่อนปุ่ม --- */
            /* เราจะใช้ attribute 'data-testid' ไม่ได้เจาะจง */
            
            /* ซ่อนปุ่มใน columns ที่เราสร้างไว้สำหรับพิมพ์ */
            /* เนื่องจาก Streamlit ไม่มี class ให้ columns เราต้องพึ่งลำดับ หรือไม่ก็ปล่อยให้แสดงแต่จัดให้สวย */
            
            /* ⚠️ หากต้องการซ่อนจริงๆ ต้องใช้ st_javascript หรือยอมให้แสดง */
            /* แต่โจทย์บอกว่า 'ไม่ต้องให้โชว์' */
            
            /* ลองวิธีนี้: ซ่อนปุ่มทั้งหมดใน container นี้ */
            /* เนื่องจากทำไม่ได้ใน CSS ธรรมดา ผมจะใช้ JavaScript ช่วยซ่อน */
        }
        </style>
        
        <script>
        // ฟังก์ชันซ่อนปุ่มบนมือถือ
        function hidePrintButtonsOnMobile() {
            if (window.innerWidth <= 992) {
                const buttons = window.parent.document.querySelectorAll('button');
                buttons.forEach(btn => {
                    if (btn.innerText.includes('พิมพ์รายงานสุขภาพ') || btn.innerText.includes('พิมพ์รายงานสมรรถภาพ')) {
                        // ซ่อนปุ่ม
                        btn.style.display = 'none';
                        // ซ่อน parent column ของปุ่มด้วย เพื่อไม่ให้เกิดช่องว่าง
                        const col = btn.closest('[data-testid="column"]');
                        if (col) col.style.display = 'none';
                    }
                });
                
                // ซ่อน Label
                const headings = window.parent.document.querySelectorAll('h5');
                headings.forEach(h => {
                    if (h.innerText.includes('เมนูพิมพ์รายงาน')) {
                        h.style.display = 'none';
                        const col = h.closest('[data-testid="column"]');
                        if (col) col.style.display = 'none';
                    }
                });
                
                // ซ่อนเส้นคั่น (hr) ที่อยู่ใกล้ๆ (อาจจะยากหน่อย เอาเป็นซ่อนปุ่มหลักๆ ก่อน)
            }
        }
        
        // รันฟังก์ชันเมื่อโหลดและเมื่อปรับขนาดหน้าจอ
        hidePrintButtonsOnMobile();
        window.addEventListener('resize', hidePrintButtonsOnMobile);
        
        // รันซ้ำๆ เผื่อ Streamlit rerender
        setInterval(hidePrintButtonsOnMobile, 500);
        </script>
    """, unsafe_allow_html=True)

    # --- ส่วนแสดงผลรายงาน ---
    yr_df = results_df[results_df["Year"] == st.session_state.selected_year]
    person_row = yr_df.bfill().ffill().iloc[0].to_dict() if not yr_df.empty else None
    st.session_state.person_row = person_row

    if person_row:
        display_common_header(person_row)
        
        tabs_map = OrderedDict()
        if has_visualization_data(results_df): tabs_map['ภาพรวม (Graphs)'] = 'viz'
        if has_basic_health_data(person_row): tabs_map['สุขภาพพื้นฐาน'] = 'main'
        if has_vision_data(person_row): tabs_map['การมองเห็น'] = 'vision'
        if has_hearing_data(person_row): tabs_map['การได้ยิน'] = 'hearing'
        if has_lung_data(person_row): tabs_map['ปอด'] = 'lung'

        t_objs = st.tabs(list(tabs_map.keys()))
        for i, (k, v) in enumerate(tabs_map.items()):
            with t_objs[i]:
                if v == 'viz': display_visualization_tab(person_row, results_df)
                elif v == 'main': display_main_report(person_row, results_df)
                elif v == 'vision': display_performance_report(person_row, 'vision')
                elif v == 'hearing': display_performance_report(person_row, 'hearing', all_person_history_df=results_df)
                elif v == 'lung': display_performance_report(person_row, 'lung')

        # Print Logic
        if st.session_state.get('print_trigger'):
            h = generate_printable_report(person_row, results_df)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_trigger = False
        if st.session_state.get('print_performance_trigger'):
            h = generate_performance_report_html(person_row, results_df)
            st.components.v1.html(f"<script>var w=window.open();w.document.write({json.dumps(h)});w.print();w.close();</script>", height=0)
            st.session_state.print_performance_trigger = False

# --------------------------------------------------------------------------------
# MAIN ROUTING LOGIC
# --------------------------------------------------------------------------------

if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'pdpa_accepted' not in st.session_state: st.session_state['pdpa_accepted'] = False

df = load_sqlite_data()
if df is None: st.stop()

# --- Auto-Login Logic ---
query_params = st.query_params
line_user_id = query_params.get("userid")

if line_user_id and not st.session_state['authenticated']:
    st.session_state["line_user_id"] = line_user_id
    st.info("⏳ กำลังตรวจสอบสิทธิ์การใช้งาน LINE...")
    
    u_info = get_user_info_from_gas(line_user_id)
    
    if u_info.get('found'):
        cid = normalize_cid(u_info.get('card_id'))
        fname = u_info.get('fname', '').strip()
        lname = u_info.get('lname', '').strip()
        
        # ค้นหาในฐานข้อมูล
        match = df[df[SQLITE_CITIZEN_ID_COL] == cid]
        user_found = None
        if not match.empty:
            if fname and lname:
                for _, row in match.iterrows():
                    db_f, db_l = normalize_db_name_field(row[SQLITE_NAME_COL])
                    if db_f == fname and db_l.replace(" ","") == lname.replace(" ",""):
                        user_found = row; break
            if user_found is None: user_found = match.iloc[0]
        
        if user_found is not None:
            st.session_state.update({
                'authenticated': True, 
                'user_hn': user_found['HN'], 
                'user_name': user_found[SQLITE_NAME_COL], 
                'pdpa_accepted': True
            })
            st.rerun()
        else:
            st.session_state['login_error'] = f"❌ ไม่พบประวัติสุขภาพของเลขบัตร '{cid}' ในระบบโรงพยาบาล"
    else:
        st.session_state['login_error'] = "❌ ไม่พบข้อมูลการลงทะเบียนของคุณในระบบ LINE"

# --- Final Decision ---
if not st.session_state['authenticated']:
    if st.session_state.get('login_error'):
        st.error(st.session_state['login_error'])
        if st.button("เข้าสู่ระบบด้วยชื่อ-นามสกุล"):
            del st.session_state["line_user_id"]
            del st.session_state["login_error"]
            st.rerun()
    else:
        authentication_flow(df)
elif not st.session_state['pdpa_accepted']:
    pdpa_consent_page()
else:
    if st.session_state.get('is_admin'): display_admin_panel(df)
    else: main_app(df)
