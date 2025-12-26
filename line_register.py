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
# แก้ชื่อไฟล์และชื่อแท็บให้ตรงกับที่คุณแจ้งมา
GOOGLE_SHEET_FILENAME = "LINE User id for Database" 
GOOGLE_SHEET_TABNAME = "UserID"
LIFF_ID = "2008725340-YHOiWxtj"

# ลิ้งค์ปลายทาง (Endpoint URL) ที่ถูกต้อง
APP_URL = "https://health-report-fromappdatabase-d53gxcssza4ravg7plcbcv.streamlit.app/"

# --- 2. Google Sheets Connection ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = None
    
    # 1. ลองอ่านจาก Secrets (บน Cloud)
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception as e:
            return None, f"Secrets Error: {str(e)}"
    
    # 2. ลองอ่านจากไฟล์ (Local)
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        except Exception as e:
            return None, f"File Error: {str(e)}"
    else:
        return None, "ไม่พบ Credentials (กรุณาเช็ค st.secrets หรือไฟล์ service_account.json)"

    try:
        client = gspread.authorize(creds)
        return client, "OK"
    except Exception as e:
        return None, f"Auth Error: {str(e)}"

def get_user_worksheet():
    client, msg = get_gsheet_client()
    if not client: return None, msg
    
    try:
        # เปิดไฟล์ Sheet
        sheet_file = client.open(GOOGLE_SHEET_FILENAME)
        
        # เลือกแท็บ
        try:
            worksheet = sheet_file.worksheet(GOOGLE_SHEET_TABNAME)
        except gspread.WorksheetNotFound:
            # ถ้าหาแท็บไม่เจอ ให้ใช้แท็บแรกแทน
            worksheet = sheet_file.sheet1
        
        # เช็คหัวตาราง
        if not worksheet.row_values(1):
            worksheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID", "Timestamp"])
            
        return worksheet, "OK"
    except Exception as e:
        return None, f"Sheet Error (เปิดไฟล์ไม่ได้): {str(e)}"

# --- 3. User Management Functions ---
def check_if_user_registered(line_user_id):
    sheet, msg = get_user_worksheet()
    if not sheet: return False, None
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        # ป้องกัน Error ถ้า Sheet ว่างเปล่าหรือไม่มี Column นี้
        if "LINE User ID" not in df.columns: return False, None
        
        match = df[df["LINE User ID"].astype(str) == str(line_user_id)]
        if not match.empty:
            row = match.iloc[0]
            return True, {"first_name": str(row["ชื่อ"]), "last_name": str(row["นามสกุล"]), "line_id": str(line_user_id)}
        return False, None
    except Exception as e: 
        print(f"Read Error: {e}")
        return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id):
    sheet, msg = get_user_worksheet()
    if not sheet: return False, msg
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([str(fname), str(lname), str(line_user_id), timestamp])
        return True, "Success"
    except Exception as e:
        return False, f"Write Error: {str(e)}"

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

# --- 5. LIFF Listener ---
def liff_token_catcher():
    if "line_user_id" in st.session_state or st.query_params.get("userid"):
        return

    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        const TARGET_APP_URL = "{APP_URL}";
        async function main() {{
            try {{
                await liff.init({{ liffId: "{LIFF_ID}" }});
                if (liff.isLoggedIn()) {{
                    const profile = await liff.getProfile();
                    const separator = TARGET_APP_URL.includes("?") ? "&" : "?";
                    const finalUrl = TARGET_APP_URL + separator + "userid=" + profile.userId;
                    window.top.location.href = finalUrl;
                }}
            }} catch (e) {{ console.log("Listener error:", e); }}
        }}
        main();
    </script>
    """
    components.html(js_code, height=0, width=0)

# --- 6. Admin Manager ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน (Google Sheets)")
    sheet, msg = get_user_worksheet()
    if sheet:
        st.dataframe(pd.DataFrame(sheet.get_all_records()), use_container_width=True)
    else:
        st.error(f"ไม่สามารถโหลดข้อมูลได้: {msg}")

# --- 7. MAIN RENDER FUNCTION ---
def render_registration_page(df):
    
    liff_token_catcher()

    # --- Debug Connection Status (Hidden by default, click to see) ---
    with st.expander("🛠️ Admin: ตรวจสอบการเชื่อมต่อ Google Sheets"):
        client, msg = get_gsheet_client()
        if client:
            st.success("✅ เชื่อมต่อ Google Sheets สำเร็จ")
            sheet, s_msg = get_user_worksheet()
            if sheet:
                st.info(f"เจอไฟล์ Sheet: {sheet.title}")
            else:
                st.error(f"❌ หาไฟล์ Sheet ไม่เจอ: {s_msg}")
        else:
            st.error(f"❌ เชื่อมต่อไม่ได้: {msg}")
            st.code(st.secrets.get("gcp_service_account", "No Secrets Found")) # ระวัง: โชว์ข้อมูลลับเฉพาะ Admin ดู

    # รับ User ID
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: 
        st.session_state["line_user_id"] = qp_userid

    # ถ้ายังไม่มี ID -> ปุ่ม Login
    if "line_user_id" not in st.session_state:
        st.markdown("---")
        st.markdown("<h3 style='text-align: center;'>ยืนยันตัวตนเพื่อดูผลตรวจ</h3>", unsafe_allow_html=True)
        login_url = f"https://liff.line.me/{LIFF_ID}"
        st.link_button("🟢 เข้าสู่ระบบด้วย LINE (คลิก)", login_url, type="primary", use_container_width=True)
        return

    # ถ้ามี ID -> เช็คข้อมูล
    line_user_id = st.session_state["line_user_id"]
    
    with st.spinner("กำลังตรวจสอบข้อมูล..."):
        is_registered, user_info = check_if_user_registered(line_user_id)

    if is_registered:
        # มีในระบบ -> Login
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

    # ถ้าไม่มีในระบบ -> ฟอร์มลงทะเบียน
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
