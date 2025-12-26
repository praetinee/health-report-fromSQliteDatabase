import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import datetime
import json
import urllib.parse

# --- 1. Configuration ---
SERVICE_ACCOUNT_FILE = "service_account.json" 
GOOGLE_SHEET_FILENAME = "LINE User id for Database"
GOOGLE_SHEET_TABNAME = "UserID"
LIFF_ID = "2008725340-YHOiWxtj" 

# --- 2. Google Sheets Connection (ตัวเขียนข้อมูล) ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = None
    
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception as e:
            return None, f"Secrets Error: {str(e)}"
    
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        except Exception as e:
            return None, f"File Error: {str(e)}"
    else:
        return None, "ไม่พบกุญแจ (Credentials) กรุณาตั้งค่า st.secrets หรือวางไฟล์ json"

    try:
        client = gspread.authorize(creds)
        return client, "OK"
    except Exception as e:
        return None, f"Auth Error: {str(e)}"

def get_user_worksheet():
    client, msg = get_gsheet_client()
    if not client: return None, msg
    
    try:
        sheet_file = client.open(GOOGLE_SHEET_FILENAME)
        try:
            worksheet = sheet_file.worksheet(GOOGLE_SHEET_TABNAME)
        except gspread.WorksheetNotFound:
            worksheet = sheet_file.sheet1
        
        if not worksheet.row_values(1):
            worksheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID", "Timestamp"])
        return worksheet, "OK"
    except Exception as e:
        return None, f"Sheet Error: {str(e)}"

# --- 3. User Management Functions ---
def check_if_user_registered(line_user_id):
    sheet, msg = get_user_worksheet()
    if not sheet: return False, None
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if "LINE User ID" not in df.columns: return False, None
        match = df[df["LINE User ID"].astype(str) == str(line_user_id)]
        if not match.empty:
            row = match.iloc[0]
            return True, {"first_name": str(row["ชื่อ"]), "last_name": str(row["นามสกุล"]), "line_id": str(line_user_id)}
        return False, None
    except: return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id):
    sheet, msg = get_user_worksheet()
    if not sheet: return False, msg
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([str(fname), str(lname), str(line_user_id), timestamp])
        return True, "Success"
    except Exception as e: return False, str(e)

# --- 4. Helpers ---
def clean_string(val): return str(val).strip() if not pd.isna(val) else ""
def normalize_db_name_field(full_name_str):
    parts = clean_string(full_name_str).split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    return (parts[0], "") if len(parts) == 1 else ("", "")

def check_registration_logic(df, input_fname, input_lname, input_id):
    i_fname, i_lname, i_id = clean_string(input_fname), clean_string(input_lname), clean_string(input_id)
    if not i_fname or not i_lname or not i_id: return False, "กรุณากรอกข้อมูลให้ครบ", None
    if len(i_id) != 13 or not i_id.isdigit(): return False, "เลขบัตรต้องเป็น 13 หลัก", None
    
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]
    if user_match.empty: return False, "ไม่พบเลขบัตรในระบบ", None
    
    for _, row in user_match.iterrows():
        db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
        if db_f.replace(" ","") == i_fname.replace(" ","") and db_l.replace(" ","") == i_lname.replace(" ",""):
            return True, "OK", row.to_dict()
    return False, "ชื่อ-สกุลไม่ตรงกับฐานข้อมูล", None

# --- 5. Admin Panel ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน (Google Sheets)")
    sheet, msg = get_user_worksheet()
    if sheet:
        st.dataframe(pd.DataFrame(sheet.get_all_records()), use_container_width=True)
    else:
        st.error(f"ไม่สามารถโหลดข้อมูลได้: {msg}")

# --- 6. MAIN RENDER FUNCTION ---
def render_registration_page(df):
    
    # 1. เช็คสถานะ Google Sheet
    client, msg = get_gsheet_client()
    if not client:
        st.error(f"❌ ระบบเชื่อมต่อ Google Sheets ไม่ได้: {msg}")
        st.warning("Admin: กรุณาตรวจสอบ st.secrets บน Cloud")
        return

    # 2. ดึง User ID จาก URL
    # LIFF จะส่งกลับมาในรูปแบบ ?liff.state=... ถ้าใช้ LIFF v2 Login
    # แต่ถ้าใช้ liff.line.me แบบ Basic มันจะวิ่งไปตาม Endpoint ที่ตั้งใน Developer Console
    qp_userid = st.query_params.get("userid", None)
    
    # บางที LIFF อาจส่ง id_token มาแทน (ถ้าตั้งค่า OpenID Connect)
    # แต่เบื้องต้นเราเช็ค userid แบบธรรมดาก่อน
    
    if qp_userid: 
        st.session_state["line_user_id"] = qp_userid

    # 3. ถ้ายังไม่มี User ID -> แสดงปุ่ม Login
    if "line_user_id" not in st.session_state:
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h3>ยืนยันตัวตนเพื่อดูผลตรวจ</h3>
            <p style="color:gray;">กรุณากดปุ่มสีเขียวด้านล่าง เพื่อเข้าสู่ระบบผ่าน LINE</p>
        </div>
        """, unsafe_allow_html=True)
        
        # สร้าง Login URL ที่ปลอดภัยขึ้น
        # ใช้ LIFF URL โดยตรง (https://liff.line.me/{LIFF_ID})
        # ซึ่งใน LINE Developer Console ต้องตั้ง Endpoint URL ให้ตรงกับหน้าเว็บนี้
        login_url = f"https://liff.line.me/{LIFF_ID}"
        
        st.link_button("🟢 เข้าสู่ระบบด้วย LINE (คลิก)", login_url, type="primary", use_container_width=True)
        return

    # 4. ได้ User ID แล้ว -> ทำงานต่อ
    line_user_id = st.session_state["line_user_id"]
    
    with st.spinner("กำลังตรวจสอบข้อมูล..."):
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
                st.session_state.update({'authenticated': True, 'pdpa_accepted': True, 'user_hn': matched_user['HN'], 'user_name': matched_user['ชื่อ-สกุล'], 'is_line_login': True})
                st.rerun()
             return
        else:
             st.error(f"ไม่พบประวัติสุขภาพของ {user_info['first_name']} ในปีนี้")
             return

    # 5. ยังไม่เคยลงทะเบียน -> แสดงฟอร์ม
    st.markdown("---")
    st.subheader("📝 ลงทะเบียนครั้งแรก")
    
    with st.form("reg_form"):
        st.caption("กรอกข้อมูลให้ตรงกับบัตรประชาชน")
        f = st.text_input("ชื่อ (ไม่ต้องมีคำนำหน้า)")
        l = st.text_input("นามสกุล")
        i = st.text_input("เลขบัตรประชาชน (13 หลัก)")
        pdpa = st.checkbox("ข้าพเจ้ายอมรับข้อตกลง PDPA")
        
        if st.form_submit_button("ยืนยันข้อมูล", use_container_width=True):
            if not pdpa:
                st.warning("⚠️ กรุณายอมรับข้อตกลง PDPA")
            else:
                valid, msg, row = check_registration_logic(df, f, l, i)
                if valid:
                    save_suc, save_msg = save_new_user_to_gsheet(clean_string(f), clean_string(l), line_user_id)
                    if save_suc:
                        st.success("✅ ลงทะเบียนสำเร็จ! กำลังเข้าสู่ระบบ...")
                        st.session_state.update({'authenticated': True, 'pdpa_accepted': True, 'user_hn': row['HN'], 'user_name': row['ชื่อ-สกุล']})
                        st.rerun()
                    else:
                        st.error(f"❌ บันทึก Google Sheet ไม่ได้: {save_msg}")
                else:
                    st.error(f"❌ {msg}")
