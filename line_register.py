import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Constants ---
# LIFF ID ที่คุณแจนให้มา
LIFF_ID = "2008725340-YHOiWxtj"

# ตั้งค่า Google Sheet (อ้างอิงจากไฟล์ CSV ที่คุณแจนให้มา)
# หมายเหตุ: ชื่อ Sheet และ Worksheet ยังคงใช้ตามที่ตกลงกันไว้
SHEET_NAME = "HealthCheck_Log" 
WORKSHEET_NAME = "Users"

# --- Google Sheets Connection ---
@st.cache_resource
def get_gsheet_client():
    """เชื่อมต่อ Google Sheets โดยใช้ st.secrets"""
    try:
        # ตรวจสอบว่ามีการตั้งค่า Secrets หรือยัง
        if "gcp_service_account" not in st.secrets:
            st.error("ไม่พบข้อมูล 'gcp_service_account' ใน Secrets กรุณาตั้งค่าก่อนใช้งาน")
            return None
            
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
        return None

def get_worksheet():
    """ดึง Worksheet ออกมาใช้งาน"""
    client = get_gsheet_client()
    if not client: return None
    
    try:
        sheet = client.open(SHEET_NAME)
        # ลองหา Worksheet ที่ชื่อ Users ก่อน
        try:
            return sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            # ถ้าไม่มี ให้สร้างใหม่ พร้อม Header ตามไฟล์ CSV ที่คุณแจนให้มา
            # เพิ่มคอลัมน์ Timestamp และ ID_Card เพื่อเก็บข้อมูลให้ครบถ้วน
            ws = sheet.add_worksheet(title=WORKSHEET_NAME, rows=100, cols=10)
            # ปรับ Header ให้ตรงกับความต้องการและไฟล์ CSV
            ws.append_row(["Timestamp", "ชื่อ", "นามสกุล", "LINE User ID", "เลขบัตรประชาชน"])
            return ws
    except gspread.SpreadsheetNotFound:
        st.error(f"ไม่พบ Google Sheet ชื่อ '{SHEET_NAME}' กรุณาสร้างไฟล์ชื่อนี้และแชร์ให้ Service Account (Email) ก่อนครับ")
        return None
    except Exception as e:
        st.error(f"Error accessing worksheet: {e}")
        return None

# --- User Management Functions (Google Sheets) ---

def check_if_user_registered(line_user_id):
    """ตรวจสอบว่า LINE ID นี้มีใน Google Sheet แล้วหรือยัง"""
    try:
        ws = get_worksheet()
        if not ws: return False, None
        
        # ดึงข้อมูลทั้งหมดมาเช็ค
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        
        # ตรวจสอบว่ามีคอลัมน์ "LINE User ID" หรือไม่ (ตามไฟล์ CSV)
        target_col = "LINE User ID"
        
        # กรณีคนสร้าง Sheet ใหม่อาจจะใช้ชื่ออื่น กันเหนียวไว้เช็ค
        if target_col not in df.columns:
            # ลองหาชื่ออื่นที่ใกล้เคียง
            for col in df.columns:
                if "Line" in col and "ID" in col:
                    target_col = col
                    break
        
        if not df.empty and target_col in df.columns:
            # แปลงเป็น String เพื่อความชัวร์ในการเปรียบเทียบ
            match = df[df[target_col].astype(str) == str(line_user_id)]
            
            if not match.empty:
                row = match.iloc[0]
                # ดึงข้อมูลตามชื่อคอลัมน์ในไฟล์ CSV
                user_info = {
                    "first_name": str(row.get("ชื่อ", "")), 
                    "last_name": str(row.get("นามสกุล", "")), 
                    "line_id": str(line_user_id)
                }
                return True, user_info
        
        return False, None
    except Exception as e: 
        st.error(f"Error checking user in Sheet: {e}")
        return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id, id_card=""):
    """บันทึกผู้ใช้ใหม่ลง Google Sheet (ต่อท้าย)"""
    try:
        ws = get_worksheet()
        if not ws: return False, "เชื่อมต่อ Google Sheet ไม่ได้"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # เรียงลำดับข้อมูลให้ตรงกับ Header: [Timestamp, ชื่อ, นามสกุล, LINE User ID, เลขบัตรประชาชน]
        ws.append_row([timestamp, str(fname), str(lname), str(line_user_id), str(id_card)])
        
        return True, "บันทึกข้อมูลสำเร็จ"
    except Exception as e:
        return False, f"บันทึกข้อมูลล้มเหลว: {e}"

# --- Helper Functions ---
def clean_string(val): return str(val).strip() if not pd.isna(val) else ""

def normalize_db_name_field(full_name_str):
    parts = clean_string(full_name_str).split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    return (parts[0], "") if len(parts) == 1 else ("", "")

def check_registration_logic(df, input_fname, input_lname, input_id):
    i_fname = clean_string(input_fname)
    i_lname = clean_string(input_lname)
    i_id = clean_string(input_id)
    
    if not i_fname or not i_lname or not i_id: 
        return False, "กรุณากรอกข้อมูลให้ครบทุกช่อง", None
    
    clean_id = i_id.replace("-", "")
    if len(clean_id) != 13: 
        return False, "เลขบัตรประชาชนต้องมี 13 หลัก", None
    
    # ค้นหาใน SQLite DataFrame (กรองด้วยเลขบัตรก่อนเพื่อความเร็ว)
    # หมายเหตุ: ใช้ชื่อคอลัมน์ตาม Database ของคุณแจน
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip().str.replace("-", "") == clean_id]
    
    if user_match.empty: 
        return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบฐานข้อมูล", None
    
    for _, row in user_match.iterrows():
        db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
        # เทียบชื่อนามสกุล (ตัดช่องว่างออกเพื่อความชัวร์)
        if db_f == i_fname and db_l.replace(" ", "") == i_lname.replace(" ", ""):
            return True, "ยืนยันตัวตนสำเร็จ", row.to_dict()
            
    return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล", None

# --- LIFF Script ---
def liff_initializer_component():
    # ถ้ามี UserID แล้ว ไม่ต้องโหลด Script ซ้ำ
    if "line_user_id" in st.session_state or st.query_params.get("userid"):
        return

    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        async function main() {{
            try {{
                await liff.init({{ liffId: "{LIFF_ID}" }});
                if (liff.isLoggedIn()) {{
                    const profile = await liff.getProfile();
                    const userId = profile.userId;
                    const currentUrl = new URL(window.location.href);
                    if (!currentUrl.searchParams.has("userid")) {{
                        currentUrl.searchParams.set("userid", userId);
                        window.location.href = currentUrl.toString();
                    }}
                }} else {{
                    liff.login();
                }}
            }} catch (err) {{
                console.error("LIFF Init failed", err);
            }}
        }}
        main();
    </script>
    <div style="text-align:center; padding:20px; background-color:#f0f2f6; border-radius:10px; margin-bottom:20px;">
        <h4 style="color:#00796B;">กำลังเชื่อมต่อกับ LINE...</h4>
        <p>กรุณารอสักครู่ ระบบกำลังยืนยันตัวตนของท่าน</p>
    </div>
    """
    components.html(js_code, height=150)

# --- Admin Manager (GSheet Version) ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน LINE (Google Sheets)")
    
    ws = get_worksheet()
    if not ws:
        st.error("ไม่สามารถเชื่อมต่อ Google Sheets ได้")
        return

    try:
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty:
            st.info("ยังไม่มีข้อมูลผู้ลงทะเบียนใน Google Sheet")
        else:
            st.dataframe(df, use_container_width=True)
            st.info(f"💡 ข้อมูลถูกบันทึกอยู่ที่ Google Sheet: {SHEET_NAME} > {WORKSHEET_NAME}")
            
            if st.button("รีเฟรชข้อมูล"): 
                st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

# --- Main Render Function (Registration Page) ---
def render_registration_page(df):
    st.markdown("""
    <style>
        .reg-container { padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; background-color: white; }
        .reg-header { color: #00B900; text-align: center; font-weight: bold; margin-bottom: 1.5rem; }
        .stButton>button { background-color: #00B900 !important; color: white !important; border-radius: 50px; height: 50px; font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
    
    # 1. รับ UserID
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: 
        st.session_state["line_user_id"] = qp_userid
    
    # 2. ถ้ายังไม่มี UserID ให้รัน LIFF
    if "line_user_id" not in st.session_state:
        liff_initializer_component()
        return

    line_user_id = st.session_state["line_user_id"]
    
    # 3. เช็คว่าเคยลงทะเบียนหรือยัง (Check Google Sheet)
    is_registered, user_info = check_if_user_registered(line_user_id)
    
    if is_registered:
        # ถ้าเคยลงทะเบียนแล้ว ให้ Auto Login
        found_rows = df[df['ชื่อ-สกุล'].str.contains(user_info['first_name'], na=False)]
        matched_user = None
        
        for _, row in found_rows.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            if db_f == user_info['first_name'] and db_l == user_info['last_name']:
                matched_user = row
                break
        
        if matched_user is not None:
             if not st.session_state.get('authenticated'):
                st.session_state.update({
                    'authenticated': True,
                    'pdpa_accepted': True,
                    'user_hn': matched_user['HN'],
                    'user_name': matched_user['ชื่อ-สกุล'],
                    'is_line_login': True
                })
                st.rerun()
             return
        else:
             st.error("พบข้อมูลการลงทะเบียน LINE แต่ไม่พบข้อมูลสุขภาพในฐานข้อมูล (SQLite)")
             st.info("กรุณาติดต่อเจ้าหน้าที่เพื่อตรวจสอบความถูกต้องของชื่อ-นามสกุล")
             return

    # 4. ถ้ายังไม่เคยลงทะเบียน แสดงหน้า Form
    if st.session_state.get('line_register_success', False):
        st.success("✅ ลงทะเบียนเรียบร้อยแล้ว!")
        st.balloons()
        if st.button("เข้าดูผลตรวจสุขภาพ", type="primary", use_container_width=True): 
            st.rerun()
        return

    # 5. Form ลงทะเบียน
    with st.container():
        st.markdown("<div class='reg-container'>", unsafe_allow_html=True)
        st.markdown("<h2 class='reg-header'>ลงทะเบียนดูผลตรวจสุขภาพ</h2>", unsafe_allow_html=True)
        
        with st.expander("📄 ข้อตกลงและเงื่อนไข (PDPA)", expanded=False):
            st.markdown("""
            1. ข้าพเจ้ายินยอมให้ระบบตรวจสอบข้อมูลชื่อ-นามสกุล และเลขบัตรประชาชน เพื่อยืนยันตัวตน
            2. ข้อมูล User ID ของ LINE จะถูกบันทึกเพื่อความสะดวกในการเข้าใช้งานครั้งถัดไป
            3. ผลตรวจสุขภาพนี้เป็นข้อมูลส่วนบุคคล ห้ามเผยแพร่แก่ผู้อื่น
            """)
        
        pdpa_check = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข (PDPA)")
        st.markdown("---")
        
        with st.form("line_reg_form"):
            c1, c2 = st.columns(2)
            with c1: f = st.text_input("ชื่อ (ไม่ต้องมีคำนำหน้า)")
            with c2: l = st.text_input("นามสกุล")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            
            sub = st.form_submit_button("ยืนยันตัวตน", use_container_width=True)

        if sub:
            if not pdpa_check: 
                st.warning("กรุณาติ๊กยอมรับข้อตกลง PDPA ก่อนลงทะเบียน")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    # บันทึกลง Google Sheet
                    save_suc, save_msg = save_new_user_to_gsheet(clean_string(f), clean_string(l), line_user_id, clean_string(i))
                    if save_suc:
                        st.session_state.update({
                            'line_register_success': True,
                            'authenticated': True,
                            'pdpa_accepted': True,
                            'user_hn': row['HN'],
                            'user_name': row['ชื่อ-สกุล']
                        })
                        st.rerun()
                    else: 
                        st.error(f"เกิดปัญหาในการบันทึกข้อมูล: {save_msg}")
                else: 
                    st.error(f"ตรวจสอบข้อมูลไม่ผ่าน: {msg}")
        
        st.markdown("</div>", unsafe_allow_html=True)
