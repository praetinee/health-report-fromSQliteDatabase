import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

# --- Configuration ---
# ชื่อไฟล์ Credentials (ต้องวางไว้ที่ root ของโปรเจค)
SERVICE_ACCOUNT_FILE = "service_account.json" 

# 1. ชื่อไฟล์บน Google Drive (ต้องตรงเป๊ะ)
GOOGLE_SHEET_FILENAME = "LINE User id for Database"

# 2. ชื่อแท็บ/แผ่นงาน (Tab Name)
GOOGLE_SHEET_TABNAME = "UserID"

# LIFF ID
LIFF_ID = "2008725340-YHOiWxtj" 

# --- Google Sheets Connection ---
def get_gsheet_client():
    """สร้าง Connection ไปยัง Google Sheets"""
    
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        st.error(f"❌ ไม่พบไฟล์ {SERVICE_ACCOUNT_FILE} ในโฟลเดอร์โปรเจค")
        return None

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google API ไม่สำเร็จ: {e}")
        return None

def get_user_worksheet():
    """ดึง Worksheet โดยระบุชื่อไฟล์และชื่อแท็บ"""
    client = get_gsheet_client()
    if not client: return None
    
    try:
        # 1. เปิดไฟล์ด้วยชื่อไฟล์ (Workbook)
        sheet_file = client.open(GOOGLE_SHEET_FILENAME)
        
        # 2. เลือกแท็บด้วยชื่อแท็บ (Worksheet)
        try:
            worksheet = sheet_file.worksheet(GOOGLE_SHEET_TABNAME)
        except gspread.WorksheetNotFound:
            # ถ้าหาแท็บชื่อ UserID ไม่เจอ ให้ลองใช้แท็บแรกสุดแทน พร้อมแจ้งเตือน
            worksheet = sheet_file.sheet1
            # st.warning(f"⚠️ ไม่พบแท็บชื่อ '{GOOGLE_SHEET_TABNAME}' ระบบจะใช้แท็บแรก '{worksheet.title}' แทน")

        # ตรวจสอบ Header
        if not worksheet.row_values(1):
            worksheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID"])
            
        return worksheet

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"❌ ไม่พบไฟล์ Google Sheet ชื่อ '{GOOGLE_SHEET_FILENAME}' บน Google Drive")
        st.info(f"💡 กรุณาตรวจสอบว่าชื่อไฟล์บน Drive คือ '{GOOGLE_SHEET_FILENAME}' และได้แชร์ให้ Service Account แล้ว")
        return None
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเปิด Sheet: {e}")
        return None

# --- User Management Functions ---

def check_if_user_registered(line_user_id):
    """
    ตรวจสอบว่า LINE ID นี้มีใน Google Sheet แล้วหรือยัง
    """
    sheet = get_user_worksheet()
    if not sheet: return False, None
    
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        if "LINE User ID" not in df.columns:
            return False, None
            
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
        st.error(f"⚠️ อ่านข้อมูลจาก Sheet ไม่ได้: {e}")
        return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id):
    """บันทึกผู้ใช้ใหม่ลง Google Sheet"""
    sheet = get_user_worksheet()
    if not sheet: return False, "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"
    
    try:
        row_data = [str(fname), str(lname), str(line_user_id)]
        sheet.append_row(row_data)
        return True, "บันทึกข้อมูลสำเร็จ"
    except Exception as e:
        return False, f"Google Sheet Error: {str(e)}"

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
        return False, "กรุณากรอกข้อมูลให้ครบถ้วน", None
    
    if len(i_id) != 13 or not i_id.isdigit(): 
        return False, "เลขบัตรประชาชนต้องเป็นตัวเลข 13 หลัก", None
    
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]
    
    if user_match.empty: 
        return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบฐานข้อมูล", None
    
    for _, row in user_match.iterrows():
        db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
        
        match_fname = db_f.replace(" ", "") == i_fname.replace(" ", "")
        match_lname = db_l.replace(" ", "") == i_lname.replace(" ", "")
        
        if match_fname and match_lname:
            return True, "ข้อมูลถูกต้อง", row.to_dict()
            
    return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล (แต่เลขบัตรถูกต้อง)", None

# --- LIFF Script ---
def liff_initializer_component():
    if "line_user_id" in st.session_state or st.query_params.get("userid"):
        return

    # แก้ไข Script ให้รอ DOM Ready ก่อนทำงาน เพื่อแก้ Error appendChild
    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        async function runLiff() {{
            try {{
                await liff.init({{ liffId: "{LIFF_ID}" }});
                if (liff.isLoggedIn()) {{
                    const profile = await liff.getProfile();
                    const userId = profile.userId;
                    const currentUrl = new URL(window.location.href);
                    
                    if (!currentUrl.searchParams.has("userid")) {{
                        currentUrl.searchParams.set("userid", userId);
                        window.top.location.href = currentUrl.toString();
                    }}
                }} else {{
                    liff.login();
                }}
            }} catch (err) {{
                document.getElementById("status-text").innerText = "Error: " + err;
                console.error("LIFF Init failed", err);
            }}
        }}

        // รอให้หน้าเว็บโหลดเสร็จก่อนค่อยรัน LIFF
        if (document.readyState === "loading") {{
            document.addEventListener("DOMContentLoaded", runLiff);
        }} else {{
            runLiff();
        }}
    </script>
    <div style="text-align:center; padding:20px; color: #666; background-color: #f0f2f6; border-radius: 10px;">
        <p id="status-text">🔄 กำลังเชื่อมต่อกับ LINE... <br>(กรุณารอสักครู่)</p>
    </div>
    """
    components.html(js_code, height=150)

# --- Admin Manager ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน LINE (Google Sheets)")
    sheet = get_user_worksheet()
    if not sheet: return

    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)
        if st.button("รีเฟรชข้อมูล"): st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# --- Main Render Function ---
def render_registration_page(df):
    st.markdown("""
        <style>
        .reg-container {
            padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-width: 500px; margin: auto; background-color: white;
        }
        .reg-header { color: #00B900; text-align: center; font-weight: bold; margin-bottom: 1.5rem; }
        .stButton>button { background-color: #00B900 !important; color: white !important; border-radius: 50px; height: 50px; font-size: 18px; border: none; }
        </style>
    """, unsafe_allow_html=True)
    
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: 
        st.session_state["line_user_id"] = qp_userid
    
    if "line_user_id" not in st.session_state:
        if st.checkbox("Dev Mode: Mock UserID (สำหรับทดสอบ)"):
            st.session_state["line_user_id"] = "U_TEST_MOCK_123456789"
            st.rerun()
        liff_initializer_component()
        return

    line_user_id = st.session_state["line_user_id"]
    
    st.caption(f"Connected LINE ID: {line_user_id}")

    with st.spinner(f"กำลังเชื่อมต่อข้อมูล..."):
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
             st.error(f"ลงทะเบียนแล้ว แต่ไม่พบข้อมูลสุขภาพของ คุณ{user_info['first_name']} ในปีนี้")
             return

    if st.session_state.get('line_register_success', False):
        st.success("✅ ลงทะเบียนเรียบร้อยแล้ว!")
        if st.button("เข้าดูผลตรวจสุขภาพ", type="primary", use_container_width=True): 
            st.rerun()
        return

    with st.container():
        st.markdown("<div class='reg-container'>", unsafe_allow_html=True)
        st.markdown("<h2 class='reg-header'>ลงทะเบียนดูผลตรวจสุขภาพ</h2>", unsafe_allow_html=True)
        st.info("กรอกข้อมูลตามบัตรประชาชนเพื่อยืนยันตัวตนครั้งแรก")
        
        pdpa_check = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข (PDPA)")
        
        with st.form("line_reg_form"):
            f = st.text_input("ชื่อ (ภาษาไทย)")
            l = st.text_input("นามสกุล (ภาษาไทย)")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            sub = st.form_submit_button("ยืนยันตัวตน", use_container_width=True)

        if sub:
            if not pdpa_check: 
                st.warning("⚠️ กรุณายอมรับ PDPA")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    with st.spinner("กำลังบันทึกข้อมูลลง Google Sheet..."):
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
                        st.error(f"❌ {save_msg}")
                else: 
                    st.error(f"❌ {msg}")
        st.markdown("</div>", unsafe_allow_html=True)
