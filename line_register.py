import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Constants ---
SHEET_ID = "1tJ1UK4SusWNpfD-bARfCUm_zc7jlo4xvrrWDW9DoFIU"
WORKSHEET_NAME = "UserID"

# --- Google Sheets Connection ---
def get_gsheet_client():
    """เชื่อมต่อ Google Sheets โดยใช้ Service Account จาก st.secrets"""
    # ตรวจสอบว่ามี Secrets หรือไม่
    if "gcp_service_account" not in st.secrets:
        st.error("⚠️ ไม่พบตั้งค่า gcp_service_account ใน Secrets")
        return None

    # กำหนด Scope
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    
    # สร้าง Credentials
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    return client

def get_user_worksheet():
    """ดึง Worksheet 'UserID'"""
    client = get_gsheet_client()
    if not client: return None
    
    try:
        sheet = client.open_by_key(SHEET_ID)
        try:
            worksheet = sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            # ถ้าไม่มี Sheet ให้สร้างใหม่และใส่ Header
            worksheet = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=3)
            worksheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID"])
        return worksheet
    except Exception as e:
        st.error(f"❌ ไม่สามารถเปิด Google Sheet ได้: {e}")
        return None

# --- Database Management Functions (Google Sheet Version) ---

def check_if_user_registered(line_user_id):
    """ตรวจสอบว่า LINE ID นี้มีใน Sheet แล้วหรือยัง"""
    ws = get_user_worksheet()
    if not ws: return False, None # เชื่อมต่อไม่ได้

    try:
        # ดึงข้อมูลทั้งหมดมาเช็ค (Column C คือ LINE User ID)
        # records = ws.get_all_records() # อาจจะช้าถ้ารายการเยอะ
        # ใช้วิธีดึงเฉพาะ Column C มาเช็คจะเร็วกว่า
        line_ids = ws.col_values(3) # Column C
        
        if line_user_id in line_ids:
            # หาชื่อคนที่ลงทะเบียนไว้ (เผื่ออยากแสดง)
            row_idx = line_ids.index(line_user_id) + 1
            row_data = ws.row_values(row_idx)
            user_info = {
                "first_name": row_data[0] if len(row_data) > 0 else "",
                "last_name": row_data[1] if len(row_data) > 1 else "",
                "line_id": line_user_id
            }
            return True, user_info
            
        return False, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านข้อมูล: {e}")
        return False, None

def save_new_user_to_sheet(fname, lname, line_user_id):
    """บันทึกผู้ใช้ใหม่ลง Sheet (ต่อท้าย)"""
    ws = get_user_worksheet()
    if not ws: return False, "ไม่สามารถเชื่อมต่อ Google Sheet"

    try:
        # ตรวจสอบซ้ำอีกครั้งว่ามี ID นี้หรือยัง (กัน Race Condition)
        line_ids = ws.col_values(3)
        if line_user_id in line_ids:
             return True, "ผู้ใช้นี้มีอยู่ในระบบแล้ว"

        # บันทึก: ชื่อ (A), นามสกุล (B), LINE ID (C)
        ws.append_row([fname, lname, line_user_id])
        return True, "บันทึกข้อมูลสำเร็จ"
    except Exception as e:
        return False, f"บันทึกข้อมูลล้มเหลว: {e}"

# --- Helper Functions (Logic เดิม) ---
def clean_string(val):
    if pd.isna(val): return ""
    return str(val).strip()

def normalize_db_name_field(full_name_str):
    clean_val = clean_string(full_name_str)
    parts = clean_val.split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = " ".join(parts[1:])
        return first_name, last_name
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return "", ""

def check_registration_logic(df, input_fname, input_lname, input_id):
    """
    ตรวจสอบข้อมูล 3 ช่อง กับ DataFrame (SQLite)
    """
    i_fname = clean_string(input_fname)
    i_lname = clean_string(input_lname)
    i_id = clean_string(input_id)

    if not i_fname or not i_lname or not i_id:
        return False, "กรุณากรอกข้อมูลให้ครบทั้ง 3 ช่อง", None

    if len(i_id) != 13:
        return False, "เลขบัตรประชาชนต้องมี 13 หลัก", None

    # 1. กรองด้วยเลขบัตรประชาชน (ไม่ต้องสนใจปี เอาทั้งหมด)
    # ใช้ str.strip() เพื่อความชัวร์
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]

    if user_match.empty:
        return False, "ไม่พบข้อมูลเลขบัตรประชาชนนี้ในระบบ", None

    # 2. ตรวจสอบชื่อและนามสกุล
    for index, row in user_match.iterrows():
        db_fname, db_lname = normalize_db_name_field(row['ชื่อ-สกุล'])
        
        # เทียบชื่อนามสกุลแบบตัดช่องว่าง
        if db_fname == i_fname and db_lname.replace(" ", "") == i_lname.replace(" ", ""):
            # เจอแล้ว! ส่งข้อมูลกลับ (ใช้แถวไหนก็ได้ที่เจอ เพราะเลขบัตรเดียวกันคือคนเดียวกัน)
            return True, "ลงทะเบียนสำเร็จ", row.to_dict()
    
    return False, "ข้อมูลชื่อหรือนามสกุล ไม่ตรงกับฐานข้อมูล", None

# --- Main UI Function ---
def render_registration_page(df):
    """แสดงหน้า UI สำหรับการลงทะเบียนผ่าน LINE"""
    
    st.markdown("""
    <style>
        .reg-container { padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
        .reg-header { color: #00B900; text-align: center; font-weight: bold; margin-bottom: 1.5rem; }
        .stButton>button { background-color: #00B900 !important; color: white !important; border-radius: 50px; height: 50px; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

    # 1. รับ UserID
    query_params = st.query_params
    line_user_id = query_params.get("userid", None)

    if not line_user_id:
        st.warning("⚠️ ไม่พบ LINE User ID (Testing Mode)")
        # สร้าง Mock ID สำหรับเทส
        line_user_id = "U_TEST_123456789" 
    
    # 2. เช็คว่าเคยลงทะเบียนหรือยัง (จาก Google Sheet)
    is_registered, user_info = check_if_user_registered(line_user_id)
    
    if is_registered:
        # ถ้าเคยลงแล้ว -> Login เข้าไปเลย
        # เราต้องหาข้อมูล HN จาก DF อีกครั้ง เพราะใน Sheet เก็บแค่ชื่อ
        # เพื่อความชัวร์ เราจะ Search DF ด้วยชื่อนามสกุลที่มีใน Sheet
        
        # ค้นหาใน DF เพื่อเอา HN
        found_rows = df[df['ชื่อ-สกุล'].str.contains(user_info['first_name'], na=False)]
        # กรองให้แม่นยำขึ้น
        matched_user = None
        for _, row in found_rows.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            if db_f == user_info['first_name'] and db_l == user_info['last_name']:
                matched_user = row
                break
        
        if matched_user is not None:
             if not st.session_state.get('authenticated'):
                st.session_state['authenticated'] = True
                st.session_state['pdpa_accepted'] = True
                st.session_state['user_hn'] = matched_user['HN']
                st.session_state['user_name'] = matched_user['ชื่อ-สกุล']
                st.session_state['is_line_login'] = True
                st.rerun()
             return
        else:
             # กรณีแปลกๆ: มีใน Sheet แต่หาใน DB ไม่เจอ (อาจจะเปลี่ยนชื่อ?)
             st.error("พบการลงทะเบียน แต่ไม่พบข้อมูลสุขภาพในระบบ กรุณาติดต่อเจ้าหน้าที่")
             return

    # 3. ถ้ายังไม่เคยลงทะเบียน -> แสดงฟอร์ม
    if st.session_state.get('line_register_success', False):
        st.success("✅ ลงทะเบียนเรียบร้อยแล้ว!")
        user_info = st.session_state.get('line_registered_user', {})
        st.write(f"สวัสดีคุณ {user_info.get('ชื่อ-สกุล', '')}")
        
        if st.button("เข้าดูผลตรวจสุขภาพ", type="primary", use_container_width=True):
             st.rerun()
        return

    with st.container():
        st.markdown("<h2 class='reg-header'>ลงทะเบียนเชื่อมต่อบัญชี</h2>", unsafe_allow_html=True)
        
        with st.expander("📄 ข้อตกลงและเงื่อนไข (PDPA)", expanded=False):
            st.markdown("""
            **การเก็บรวบรวมข้อมูลส่วนบุคคล**
            1. ข้าพเจ้ายินยอมให้รพ.สันทราย เก็บข้อมูล ชื่อ-นามสกุล และเลขบัตรประชาชน
            2. ข้อมูลสุขภาพจะถูกแสดงเฉพาะเจ้าของข้อมูลที่ยืนยันตัวตนถูกต้องเท่านั้น
            """)
        
        pdpa_check = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข (PDPA)")
        st.markdown("---")

        with st.form("line_reg_form"):
            st.write("กรุณากรอกข้อมูลให้ตรงกับบัตรประชาชน")
            c1, c2 = st.columns(2)
            with c1: input_fname = st.text_input("ชื่อ (ไม่ต้องระบุคำนำหน้า)", placeholder="สมชาย")
            with c2: input_lname = st.text_input("นามสกุล", placeholder="ใจดี")
            input_id = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13, placeholder="xxxxxxxxxxxxx")
            
            submit_btn = st.form_submit_button("ยืนยันตัวตน", use_container_width=True)

        if submit_btn:
            if not pdpa_check:
                st.warning("⚠️ กรุณากดยอมรับเงื่อนไข PDPA ก่อนลงทะเบียน")
            else:
                # 1. เช็คกับ SQLite ก่อน
                success, msg, user_row = check_registration_logic(df, input_fname, input_lname, input_id)
                
                if success:
                    # 2. ถ้าผ่าน -> บันทึกลง Google Sheet
                    # เตรียมชื่อนามสกุลให้สะอาด (Clean)
                    clean_fname = clean_string(input_fname)
                    clean_lname = clean_string(input_lname)
                    
                    save_success, save_msg = save_new_user_to_sheet(
                        fname=clean_fname,
                        lname=clean_lname,
                        line_user_id=line_user_id
                    )
                    
                    if save_success:
                        st.session_state['line_register_success'] = True
                        st.session_state['line_registered_user'] = user_row
                        
                        # Set Login State
                        st.session_state['authenticated'] = True
                        st.session_state['pdpa_accepted'] = True
                        st.session_state['user_hn'] = user_row['HN']
                        st.session_state['user_name'] = user_row['ชื่อ-สกุล']
                        st.rerun()
                    else:
                        st.error(f"❌ ลงทะเบียนสำเร็จแต่บันทึกข้อมูลไม่ผ่าน: {save_msg}")
                else:
                    st.error(f"❌ {msg}")

# --- Admin Manager (Updated for Sheet) ---
def render_admin_line_manager():
    """Admin UI สำหรับดูข้อมูลจาก Google Sheet"""
    st.subheader("📱 จัดการผู้ใช้งาน LINE (Google Sheets)")
    
    ws = get_user_worksheet()
    if not ws:
        st.warning("ไม่สามารถเชื่อมต่อ Google Sheets ได้")
        return

    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            st.info("ยังไม่มีข้อมูลผู้ลงทะเบียน")
        else:
            st.dataframe(df, use_container_width=True)
            st.markdown(f"[เปิดดูไฟล์ Google Sheets]({ 'https://docs.google.com/spreadsheets/d/' + SHEET_ID })")
            
            st.info("💡 หากต้องการแก้ไขหรือลบข้อมูล กรุณาทำใน Google Sheets โดยตรง ข้อมูลจะอัปเดตมาที่นี่เมื่อรีเฟรช")
            
            if st.button("รีเฟรชข้อมูล"):
                st.rerun()
                
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
```

### ไฟล์: `requirements.txt`
เนื่องจากเราใช้ library ใหม่ คุณต้องเพิ่ม 2 บรรทัดนี้ในไฟล์ `requirements.txt` ครับ:
```text
gspread
google-auth
```

### วิธีการตั้งค่า Secrets (สำคัญมาก!)
เพื่อให้ระบบเขียนลง Google Sheet ของคุณได้ คุณต้องทำขั้นตอนนี้ครับ:

1.  ไปที่ **Google Cloud Console** สร้าง Service Account
2.  Download ไฟล์ Key (JSON) ออกมา
3.  **สำคัญ:** เอาอีเมลของ Service Account (เช่น `xxxx@project-id.iam.gserviceaccount.com`) ไปกด **Share** (Editor Access) ที่ไฟล์ Google Sheet ของคุณ
4.  ใน Streamlit Cloud (หรือโฟลเดอร์ `.streamlit/secrets.toml`):
    * สร้าง section ชื่อ `[gcp_service_account]`
    * ก๊อปปี้ข้อมูลในไฟล์ JSON มาใส่ให้ครบ ดังตัวอย่าง:

```toml
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----..."
client_email = "..."
client_id = "..."
auth_uri = "..."
token_uri = "..."
auth_provider_x509_cert_url = "..."
client_x509_cert_url = "..."
