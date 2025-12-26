import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import datetime
import json

# --- Configuration ---
SERVICE_ACCOUNT_FILE = "service_account.json" 
GOOGLE_SHEET_FILENAME = "LINE User id for Database"
GOOGLE_SHEET_TABNAME = "UserID"
LIFF_ID = "2008725340-YHOiWxtj" 

# --- Google Sheets Connection ---
def get_gsheet_client():
    """สร้าง Connection ไปยัง Google Sheets (รองรับทั้ง Local และ Cloud)"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = None
    
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception as e:
            st.error(f"❌ อ่าน Secrets ไม่สำเร็จ: {e}")
            return None
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        except Exception as e:
            st.error(f"❌ อ่านไฟล์ JSON ไม่สำเร็จ: {e}")
            return None
    else:
        st.error("❌ ไม่พบ Credentials!")
        return None

    try:
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google API ไม่สำเร็จ: {e}")
        return None

def get_user_worksheet():
    client = get_gsheet_client()
    if not client: return None
    try:
        sheet_file = client.open(GOOGLE_SHEET_FILENAME)
        try:
            worksheet = sheet_file.worksheet(GOOGLE_SHEET_TABNAME)
        except gspread.WorksheetNotFound:
            worksheet = sheet_file.sheet1
        
        if not worksheet.row_values(1):
            worksheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID", "Timestamp"])
        return worksheet
    except Exception as e:
        st.error(f"❌ Google Sheet Error: {e}")
        return None

# --- User Management Functions ---
def check_if_user_registered(line_user_id):
    sheet = get_user_worksheet()
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
    sheet = get_user_worksheet()
    if not sheet: return False, "DB Error"
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([str(fname), str(lname), str(line_user_id), timestamp])
        return True, "Success"
    except Exception as e: return False, str(e)

# --- Helper Functions ---
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

# --- NEW: Login System (Manual Trigger) ---
def liff_initializer_component():
    """
    ระบบล็อกอินแบบใหม่:
    1. พยายามดึง User ID เงียบๆ (ถ้าอยู่ใน LINE Browser จะได้เลย)
    2. ถ้าไม่ได้ จะ 'ไม่ทำอะไรเลย' (ปล่อยให้ Python แสดงปุ่ม Login)
    ป้องกัน Error 'refused to connect'
    """
    if "line_user_id" in st.session_state or st.query_params.get("userid"):
        return

    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        async function main() {{
            try {{
                await liff.init({{ liffId: "{LIFF_ID}" }});
                if (liff.isLoggedIn()) {{
                    // ถ้า Login อยู่แล้ว (เช่นเปิดใน LINE) ให้ดึง ID แล้วรีโหลดหน้าเว็บ
                    const profile = await liff.getProfile();
                    const currentUrl = new URL(window.location.href);
                    if (!currentUrl.searchParams.has("userid")) {{
                        currentUrl.searchParams.set("userid", profile.userId);
                        window.top.location.href = currentUrl.toString();
                    }}
                }} 
                // ถ้ายังไม่ Login: "ไม่ทำอะไร" (Don't auto login)
                // ปล่อยให้ User กดปุ่มสีเขียวเอง เพื่อหลีกเลี่ยงการโดนบล็อก
            }} catch (e) {{
                console.log("LIFF Init skipped or failed", e);
            }}
        }}
        main();
    </script>
    """
    # height=0 เพื่อซ่อน component นี้ไม่ให้เกะกะ
    components.html(js_code, height=0)

# --- Admin Manager ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน (Google Sheets)")
    sheet = get_user_worksheet()
    if sheet:
        st.dataframe(pd.DataFrame(sheet.get_all_records()), use_container_width=True)

# --- Main Render Function ---
def render_registration_page(df):
    # 1. รับค่า User ID จาก URL
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: st.session_state["line_user_id"] = qp_userid
    
    # 2. พยายามดึง ID เงียบๆ (เผื่อเปิดใน LINE App)
    liff_initializer_component()

    # 3. ถ้ายังไม่มี User ID ให้แสดงหน้า "Login" แทนหน้าลงทะเบียน
    if "line_user_id" not in st.session_state:
        st.markdown("""
        <style>
        .login-box { text-align: center; padding: 40px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-top: 20px;}
        .login-title { color: #00B900; font-weight: bold; font-size: 24px; margin-bottom: 10px; }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.image("https://upload.wikimedia.org/wikipedia/commons/4/41/LINE_logo.svg", width=80)
        st.markdown("<div class='login-title'>ยืนยันตัวตนผ่าน LINE</div>", unsafe_allow_html=True)
        st.write("กรุณากดปุ่มด้านล่างเพื่อเข้าสู่ระบบ")
        
        # --- ปุ่มพระเอกของเรา ---
        # ปุ่มนี้จะพา User ออกไปหน้า LINE Login อย่างถูกต้อง (ไม่โดนบล็อก)
        # แล้ว LINE จะดีดกลับมาหน้าเว็บเราเอง
        st.link_button("🟢 เข้าสู่ระบบด้วย LINE (คลิก)", f"https://liff.line.me/{LIFF_ID}", type="primary", use_container_width=True)
        
        if st.checkbox("Dev Mode (ทดสอบในคอม)"):
            if st.button("ใช้ Mock ID"):
                st.session_state["line_user_id"] = "U_MOCK_123456"
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # --- ส่วนทำงานเมื่อได้ User ID แล้ว (Logic เดิม) ---
    line_user_id = st.session_state["line_user_id"]
    
    # ... (ส่วนเช็คทะเบียนและฟอร์ม Logic เดิม คงไว้เหมือนเดิม) ...
    with st.spinner("ตรวจสอบข้อมูล..."):
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
                    'authenticated': True, 'pdpa_accepted': True,
                    'user_hn': matched_user['HN'], 'user_name': matched_user['ชื่อ-สกุล'], 'is_line_login': True
                })
                st.rerun()
             return
        else:
             st.error(f"ไม่พบข้อมูลสุขภาพของ คุณ{user_info['first_name']} ในปีนี้")
             return

    # หน้าลงทะเบียน (เมื่อได้ ID แล้วแต่ยังไม่เคยลงทะเบียน)
    st.markdown("""<style>.reg-container {padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; background-color: white;} .reg-header { color: #00B900; text-align: center; font-weight: bold; margin-bottom: 1.5rem; } .stButton>button { background-color: #00B900 !important; color: white !important; border-radius: 50px; height: 50px; font-size: 18px; border: none; }</style>""", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='reg-container'>", unsafe_allow_html=True)
        st.markdown("<h2 class='reg-header'>ลงทะเบียนครั้งแรก</h2>", unsafe_allow_html=True)
        
        pdpa_check = st.checkbox("ยอมรับข้อตกลงและเงื่อนไข (PDPA)")
        with st.form("line_reg_form"):
            f = st.text_input("ชื่อ (ภาษาไทย)")
            l = st.text_input("นามสกุล (ภาษาไทย)")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            sub = st.form_submit_button("ยืนยันตัวตน", use_container_width=True)

        if sub:
            if not pdpa_check: st.warning("กรุณายอมรับ PDPA")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    if save_new_user_to_gsheet(clean_string(f), clean_string(l), line_user_id):
                        st.session_state.update({'authenticated': True, 'pdpa_accepted': True, 'user_hn': row['HN'], 'user_name': row['ชื่อ-สกุล']})
                        st.rerun()
                    else: st.error("บันทึกข้อมูลไม่สำเร็จ")
                else: st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)
