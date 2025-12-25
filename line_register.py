import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# --- Configuration ---
# ชื่อไฟล์ Credentials (ต้องวางไว้ที่ root ของโปรเจค)
SERVICE_ACCOUNT_FILE = "service_account.json" 

# ชื่อ Google Sheet ที่จะใช้เก็บข้อมูล User
# *** ต้องสร้างไฟล์ชื่อนี้ใน Google Drive และ Share ให้ Service Account Email เป็น Editor ***
SHEET_NAME = "LINE User id for Database"

# LIFF ID
LIFF_ID = "YOUR_LIFF_ID_HERE" 

# --- Google Sheets Connection ---
def get_gsheet_client():
    """สร้าง Connection ไปยัง Google Sheets"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อ Google API ได้: {e}")
        return None

def get_user_worksheet():
    """ดึง Worksheet แรกจาก Google Sheet"""
    client = get_gsheet_client()
    if not client: return None
    
    try:
        sheet = client.open(SHEET_NAME).sheet1
        # ตรวจสอบว่ามี Header ไหม ถ้าไม่มีให้สร้าง (ตัดวันที่ออกตามที่แจ้ง)
        if not sheet.row_values(1):
            sheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID"])
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ ไม่พบไฟล์ Google Sheet ชื่อ '{SHEET_NAME}' กรุณาสร้างและแชร์ให้ Service Account")
        return None
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเปิด Sheet: {e}")
        return None

# --- User Management Functions ---

def check_if_user_registered(line_user_id):
    """
    ตรวจสอบว่า LINE ID นี้มีใน Google Sheet แล้วหรือยัง
    Returns: (is_registered: bool, user_info: dict)
    """
    sheet = get_user_worksheet()
    if not sheet: return False, None
    
    try:
        # ดึงข้อมูลทั้งหมดมาเช็ค
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        if "LINE User ID" not in df.columns:
            return False, None
            
        # แปลงเป็น string เพื่อความชัวร์ในการเปรียบเทียบ
        match = df[df["LINE User ID"].astype(str) == str(line_user_id)]
        
        if not match.empty:
            row = match.iloc[0]
            user_info = {
                "first_name": str(row["ชื่อ"]), 
                "last_name": str(row["นามสกุล"]), 
                "line_id": str(line_user_id)
            }
            return True, user_info
        return False, None
        
    except Exception as e: 
        # st.error(f"Error checking user in Sheet: {e}")
        return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id):
    """บันทึกผู้ใช้ใหม่ลง Google Sheet"""
    sheet = get_user_worksheet()
    if not sheet: return False, "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"
    
    try:
        # บันทึกต่อท้าย (ตัดวันที่ออกตามที่แจ้ง)
        sheet.append_row([fname, lname, str(line_user_id)])
        
        return True, "บันทึกข้อมูลสำเร็จ"
    except Exception as e:
        return False, f"บันทึกข้อมูลล้มเหลว: {e}"

# --- Helper Functions (Logic เดิม) ---
def clean_string(val): return str(val).strip() if not pd.isna(val) else ""

def normalize_db_name_field(full_name_str):
    parts = clean_string(full_name_str).split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    return (parts[0], "") if len(parts) == 1 else ("", "")

def check_registration_logic(df, input_fname, input_lname, input_id):
    """
    ตรวจสอบข้อมูลที่กรอก เทียบกับ DataFrame (SQLite)
    """
    i_fname = clean_string(input_fname)
    i_lname = clean_string(input_lname)
    i_id = clean_string(input_id)
    
    if not i_fname or not i_lname or not i_id: 
        return False, "กรุณากรอกข้อมูลให้ครบถ้วน", None
    
    # ตรวจสอบรูปแบบเลขบัตรเบื้องต้น
    if len(i_id) != 13 or not i_id.isdigit(): 
        return False, "เลขบัตรประชาชนต้องเป็นตัวเลข 13 หลัก", None
    
    # กรองหาจากเลขบัตรก่อน (Unique Key)
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]
    
    if user_match.empty: 
        return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบฐานข้อมูล", None
    
    # ถ้าพบเลขบัตร ให้เช็คชื่อ-นามสกุล
    for _, row in user_match.iterrows():
        db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
        
        # เปรียบเทียบแบบตัดช่องว่างและตัวพิมพ์
        match_fname = db_f.replace(" ", "") == i_fname.replace(" ", "")
        match_lname = db_l.replace(" ", "") == i_lname.replace(" ", "")
        
        if match_fname and match_lname:
            return True, "ข้อมูลถูกต้อง", row.to_dict()
            
    return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล (แต่เลขบัตรถูกต้อง)", None

# --- LIFF Script ---
def liff_initializer_component():
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
    <div style="text-align:center; padding:20px; color: #666;">
        <p>กำลังเชื่อมต่อกับ LINE... <br>กรุณารอสักครู่</p>
    </div>
    """
    components.html(js_code, height=100)

# --- Admin Manager (Google Sheet Version) ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน LINE (Google Sheets)")
    sheet = get_user_worksheet()
    
    if not sheet:
        st.error("ไม่สามารถโหลดข้อมูลจาก Google Sheet ได้")
        return

    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty:
            st.info("ยังไม่มีข้อมูลผู้ลงทะเบียนใน Sheet")
        else:
            st.dataframe(df, use_container_width=True)
            st.success(f"เชื่อมต่อกับ Google Sheet: {SHEET_NAME} สำเร็จ")
            
            if st.button("รีเฟรชข้อมูล"): st.rerun()
            
            st.info(f"💡 ข้อมูลถูกดึงมาจากไฟล์: {SHEET_NAME}")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

# --- Main Render Function (Registration Page) ---
def render_registration_page(df):
    st.markdown("""
        <style>
        .reg-container {
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-width: 500px;
            margin: auto;
            background-color: white;
        }
        .reg-header {
            color: #00B900;
            text-align: center;
            font-weight: bold;
            margin-bottom: 1.5rem;
        }
        .stButton>button {
            background-color: #00B900 !important;
            color: white !important;
            border-radius: 50px;
            height: 50px;
            font-size: 18px;
            border: none;
        }
        .stButton>button:hover {
            filter: brightness(1.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: 
        st.session_state["line_user_id"] = qp_userid
    
    if "line_user_id" not in st.session_state:
        if st.checkbox("Dev Mode: Mock UserID"):
            st.session_state["line_user_id"] = "U_TEST_MOCK_123456789"
            st.rerun()
        liff_initializer_component()
        return

    line_user_id = st.session_state["line_user_id"]
    is_registered, user_info = check_if_user_registered(line_user_id)
    
    if is_registered:
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
             st.error(f"พบการลงทะเบียน LINE ID นี้ในระบบ แต่ไม่พบข้อมูลสุขภาพของ คุณ{user_info['first_name']} ในฐานข้อมูลปีปัจจุบัน")
             return

    if st.session_state.get('line_register_success', False):
        st.success("✅ ลงทะเบียนเชื่อมต่อบัญชีเรียบร้อยแล้ว!")
        if st.button("เข้าดูผลตรวจสุขภาพ", type="primary", use_container_width=True): 
            st.rerun()
        return

    with st.container():
        st.markdown("<div class='reg-container'>", unsafe_allow_html=True)
        st.markdown("<h2 class='reg-header'>ลงทะเบียนดูผลตรวจสุขภาพ</h2>", unsafe_allow_html=True)
        st.info("กรุณากรอกข้อมูลให้ตรงกับบัตรประชาชนเพื่อยืนยันตัวตน")
        
        with st.expander("📄 ข้อตกลงและเงื่อนไข (PDPA)", expanded=False):
            st.markdown("""
            1. ข้าพเจ้ายินยอมให้ระบบเก็บรวบรวม ชื่อ-นามสกุล และ LINE User ID เพื่อใช้ในการยืนยันตัวตน
            2. ข้อมูลสุขภาพจะถูกแสดงเฉพาะเจ้าของข้อมูลที่ยืนยันตัวตนถูกต้องเท่านั้น
            """)
        
        pdpa_check = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข (PDPA)")
        st.markdown("---")
        
        with st.form("line_reg_form"):
            c1, c2 = st.columns(2)
            with c1: f = st.text_input("ชื่อ (ไม่ต้องมีคำนำหน้า)")
            with c2: l = st.text_input("นามสกุล")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            sub = st.form_submit_button("ยืนยันตัวตนและผูกบัญชี LINE", use_container_width=True)

        if sub:
            if not pdpa_check: 
                st.warning("⚠️ กรุณากดยอมรับเงื่อนไข PDPA ก่อนลงทะเบียน")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    save_suc, save_msg = save_new_user_to_gsheet(clean_string(f), clean_string(l), line_user_id)
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
                        st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล: {save_msg}")
                else: 
                    st.error(f"❌ {msg}")
        st.markdown("</div>", unsafe_allow_html=True)
