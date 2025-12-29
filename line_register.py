import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import os

# --- Constants ---
LIFF_ID = "2008725340-YHOiWxtj"
SHEET_NAME = "LINE User ID for Database" 
WORKSHEET_NAME = "UserID"

# --- Google Sheets Connection ---
@st.cache_resource
def get_gsheet_client():
    """เชื่อมต่อ Google Sheets โดยรองรับทั้ง Secrets และไฟล์ JSON ในเครื่อง"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # 1. ลองดึงจาก st.secrets (บน Streamlit Cloud)
    if "gcp_service_account" in st.secrets:
        try:
            credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=scopes
            )
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"❌ Error using secrets: {e}")
    
    # 2. ลองดึงจากไฟล์ JSON (Local)
    # เช็คทั้งชื่อปกติและชื่อที่มี .json เบิ้ล เพื่อความชัวร์
    possible_files = ["service_account.json", "service_account.json.json"]
    found_file = None
    
    for f in possible_files:
        if os.path.exists(f):
            found_file = f
            break
            
    if found_file:
        try:
            credentials = Credentials.from_service_account_file(
                found_file,
                scopes=scopes
            )
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"❌ Error reading {found_file}: {e}")
            return None

    # 3. ถ้าไม่เจออะไรเลย
    st.error("❌ ไม่พบการตั้งค่า Google Service Account (ไม่เจอ Secrets และไม่เจอไฟล์ json)")
    return None

def get_worksheet():
    """ดึง Worksheet พร้อมแสดง Error ชัดเจนถ้าหาไม่เจอ"""
    client = get_gsheet_client()
    if not client: return None
    
    try:
        sheet = client.open(SHEET_NAME)
        # ลองหา Worksheet
        try:
            return sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            # ถ้าไม่มี ให้ลองสร้างใหม่
            try:
                ws = sheet.add_worksheet(title=WORKSHEET_NAME, rows=100, cols=10)
                ws.append_row(["Timestamp", "ชื่อ", "นามสกุล", "LINE User ID", "เลขบัตรประชาชน"])
                return ws
            except Exception as create_err:
                st.error(f"❌ ไม่พบแผ่นงานชื่อ '{WORKSHEET_NAME}' และสร้างใหม่ไม่ได้")
                st.error(f"สาเหตุ: {create_err}")
                return None

    except gspread.SpreadsheetNotFound:
        st.error(f"❌ ไม่พบไฟล์ Google Sheet ชื่อ: '{SHEET_NAME}'")
        st.warning("⚠️ คำแนะนำ:")
        st.markdown(f"1. เช็คชื่อไฟล์ใน Google Drive ว่าชื่อ `{SHEET_NAME}` เป๊ะๆ หรือไม่")
        st.markdown("2. เช็คว่ากด Share ให้ Email ของ Service Account หรือยัง")
        return None
    except Exception as e:
        st.error(f"❌ Error การเข้าถึง Google Sheet: {e}")
        return None

# --- User Management Functions ---

def check_if_user_registered(line_user_id):
    """ตรวจสอบว่า LINE ID นี้มีใน Google Sheet แล้วหรือยัง"""
    try:
        ws = get_worksheet()
        if not ws: return False, None
        
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty: return False, None

        # หาคอลัมน์ LINE ID (เผื่อพิมพ์ผิดเล็กน้อย)
        target_col = "LINE User ID"
        if target_col not in df.columns:
            for col in df.columns:
                if "Line" in str(col) and "ID" in str(col):
                    target_col = col
                    break
        
        if target_col in df.columns:
            # แปลงเป็น String และตัดช่องว่างก่อนเทียบ
            match = df[df[target_col].astype(str).str.strip() == str(line_user_id).strip()]
            
            if not match.empty:
                row = match.iloc[0]
                user_info = {
                    "first_name": str(row.get("ชื่อ", "")), 
                    "last_name": str(row.get("นามสกุล", "")), 
                    "line_id": str(line_user_id)
                }
                return True, user_info
        
        return False, None
    except Exception as e: 
        return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id, id_card=""):
    """บันทึกข้อมูลลง Google Sheet"""
    try:
        ws = get_worksheet()
        if not ws: return False, "ไม่สามารถเชื่อมต่อ Sheet ได้ (ดู Error ด้านบน)"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [
            timestamp, 
            str(fname).strip(), 
            str(lname).strip(), 
            str(line_user_id).strip(), 
            str(id_card).strip()
        ]
        
        ws.append_row(row_data)
        return True, f"บันทึกข้อมูลลง '{SHEET_NAME}' สำเร็จ"
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
    
    try:
        # ค้นหาใน SQLite
        user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip().str.replace("-", "") == clean_id]
        
        if user_match.empty: 
            return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบฐานข้อมูล", None
        
        for _, row in user_match.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            # เทียบชื่อนามสกุลแบบตัดช่องว่าง
            if db_f == i_fname and db_l.replace(" ", "") == i_lname.replace(" ", ""):
                return True, "ยืนยันตัวตนสำเร็จ", row.to_dict()
                
        return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล", None
    except Exception as e:
        return False, f"System Error: {e}", None

# --- LIFF Script (ตรรกะมาตรฐานจาก index.html ปรับใช้กับ Streamlit) ---
def liff_initializer_component():
    # 1. เช็คว่ามี UserID ใน Session หรือยัง
    if "line_user_id" in st.session_state:
        return

    # 2. เช็คว่ามี UserID ใน URL หรือไม่
    qp_userid = st.query_params.get("userid", None)
    if qp_userid:
        st.session_state["line_user_id"] = qp_userid
        st.rerun() # รีโหลดเพื่ออัปเดตสถานะ
        return

    # 3. ถ้ายังไม่มี ให้รัน LIFF Script
    # Logic: Init -> Login (ถ้ายัง) -> Get Profile -> Redirect หน้าหลักพร้อม params
    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        async function main() {{
            try {{
                // 1. Initialize LIFF
                await liff.init({{ liffId: "{LIFF_ID}" }});
                
                // 2. ตรวจสอบสถานะ Login
                if (!liff.isLoggedIn()) {{
                    // ถ้ายังไม่ Login ให้สั่ง Login (จะเด้งไปหน้า LINE Login)
                    liff.login();
                    return; 
                }}
                
                // 3. ดึง User Profile
                const profile = await liff.getProfile();
                const userId = profile.userId;
                
                // 4. ส่งค่า UserID กลับมาที่ Python โดยการ Reload หน้าเว็บแม่ (window.top)
                // ต้องใช้ window.top เพราะ Streamlit component รันใน iframe
                const currentUrl = new URL(window.top.location.href);
                
                // เติมพารามิเตอร์ userid ลงใน URL ถ้ายังไม่มี
                if (!currentUrl.searchParams.has("userid")) {{
                    currentUrl.searchParams.set("userid", userId);
                    window.top.location.href = currentUrl.toString();
                }}
                
            }} catch (err) {{
                console.error("LIFF Init failed", err);
                document.getElementById("liff-status").innerHTML = "<b>Connection Error:</b> " + err.message;
            }}
        }}
        main();
    </script>
    <div id="liff-status" style="text-align:center; padding:20px; background-color:#f0f2f6; border-radius:10px; margin-bottom:20px;">
        <h4 style="color:#00796B;">กำลังเชื่อมต่อกับ LINE...</h4>
        <p>กรุณารอสักครู่ ระบบกำลังยืนยันตัวตนของท่าน</p>
    </div>
    """
    components.html(js_code, height=150)

# --- Admin Manager ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน LINE (Google Sheets)")
    ws = get_worksheet()
    if not ws: return # Error จะแสดงใน get_worksheet แล้ว

    try:
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty:
            st.info("ยังไม่มีข้อมูลผู้ลงทะเบียน")
        else:
            st.dataframe(df, use_container_width=True)
            if st.button("รีเฟรชข้อมูล"): st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

# --- Render Page (Registration UI) ---
def render_registration_page(df):
    st.markdown("""
    <style>
        .reg-container { padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; background-color: white; }
        .reg-header { color: #00B900; text-align: center; font-weight: bold; margin-bottom: 1.5rem; }
        .stButton>button { background-color: #00B900 !important; color: white !important; border-radius: 50px; height: 50px; font-size: 18px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
    
    # เรียกใช้ Script เพื่อดึง UserID (ถ้ายังไม่มี)
    liff_initializer_component()

    # ถ้ายังไม่ได้ UserID ให้หยุดรอ (แสดงแค่ Component Loading)
    if "line_user_id" not in st.session_state:
        return

    line_user_id = st.session_state["line_user_id"]
    
    # ตรวจสอบว่าเคยลงทะเบียนหรือไม่
    is_registered, user_info = check_if_user_registered(line_user_id)
    
    if is_registered:
        found_rows = df[df['ชื่อ-สกุล'].str.contains(user_info['first_name'], na=False)]
        matched_user = None
        for _, row in found_rows.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            if db_f == user_info['first_name'] and db_l == user_info['last_name']: matched_user = row; break
        
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
             st.error("พบ Line ID ในระบบ แต่ไม่พบข้อมูลสุขภาพในฐานข้อมูล (ชื่ออาจไม่ตรงกัน)")
             return

    # กรณีลงทะเบียนสำเร็จแล้ว
    if st.session_state.get('line_register_success', False):
        st.success("✅ ลงทะเบียนเรียบร้อยแล้ว!")
        st.balloons()
        if st.button("เข้าดูผลตรวจสุขภาพ", type="primary", use_container_width=True): 
            st.rerun()
        return

    # แสดงฟอร์มลงทะเบียน
    with st.container():
        st.markdown("<div class='reg-container'>", unsafe_allow_html=True)
        st.markdown("<h2 class='reg-header'>ลงทะเบียนดูผลตรวจสุขภาพ</h2>", unsafe_allow_html=True)
        
        with st.form("line_reg_form"):
            c1, c2 = st.columns(2)
            with c1: f = st.text_input("ชื่อ (ไม่ต้องมีคำนำหน้า)")
            with c2: l = st.text_input("นามสกุล")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            pdpa_check = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข (PDPA)")
            
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
                        # SET FLAG: ป้องกันการบันทึกซ้ำ
                        st.session_state["line_saved"] = True  
                        st.session_state.update({
                            'line_register_success': True,
                            'authenticated': True,
                            'pdpa_accepted': True,
                            'user_hn': row['HN'],
                            'user_name': row['ชื่อ-สกุล']
                        })
                        st.rerun()
                    else: 
                        st.error(f"❌ เกิดปัญหาในการบันทึกข้อมูล: {save_msg}")
                        st.info("กรุณาแจ้งเจ้าหน้าที่ หรือลองใหม่อีกครั้ง")
                else: 
                    st.error(f"❌ ตรวจสอบข้อมูลไม่ผ่าน: {msg}")
        
        st.markdown("</div>", unsafe_allow_html=True)
