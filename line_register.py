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
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # 1. ลองดึงจาก Secrets (Cloud)
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
    possible_files = ["service_account.json", "service_account.json.json"]
    for f in possible_files:
        if os.path.exists(f):
            try:
                credentials = Credentials.from_service_account_file(f, scopes=scopes)
                return gspread.authorize(credentials)
            except Exception as e:
                st.error(f"❌ Error reading {f}: {e}")
    
    st.error("❌ ไม่พบการตั้งค่า Google Service Account")
    return None

def get_worksheet():
    client = get_gsheet_client()
    if not client: return None
    
    try:
        sheet = client.open(SHEET_NAME)
        try:
            return sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            # สร้างใหม่ถ้าหาไม่เจอ
            ws = sheet.add_worksheet(title=WORKSHEET_NAME, rows=100, cols=10)
            ws.append_row(["Timestamp", "ชื่อ", "นามสกุล", "LINE User ID", "เลขบัตรประชาชน"])
            return ws
    except gspread.SpreadsheetNotFound:
        st.error(f"❌ ไม่พบไฟล์ Google Sheet ชื่อ: '{SHEET_NAME}'")
        st.warning("⚠️ ตรวจสอบว่าชื่อไฟล์ตรงเป๊ะ และแชร์ให้ Service Account แล้ว")
        return None
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return None

# --- Save Function ---
def save_new_user_to_gsheet(fname, lname, line_user_id, id_card=""):
    try:
        ws = get_worksheet()
        if not ws: return False, "ไม่สามารถเชื่อมต่อ Sheet ได้"
        
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
        user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip().str.replace("-", "") == clean_id]
        if user_match.empty: 
            return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบฐานข้อมูล", None
        
        for _, row in user_match.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            if db_f == i_fname and db_l.replace(" ", "") == i_lname.replace(" ", ""):
                return True, "ยืนยันตัวตนสำเร็จ", row.to_dict()
                
        return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล", None
    except Exception as e:
        return False, f"System Error: {e}", None

def check_if_user_registered(line_user_id):
    try:
        ws = get_worksheet()
        if not ws: return False, None
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty: return False, None

        target_col = "LINE User ID"
        if target_col not in df.columns:
            for col in df.columns:
                if "Line" in str(col) and "ID" in str(col): target_col = col; break
        
        if target_col in df.columns:
            match = df[df[target_col].astype(str).str.strip() == str(line_user_id).strip()]
            if not match.empty:
                row = match.iloc[0]
                return True, {"first_name": str(row.get("ชื่อ", "")), "last_name": str(row.get("นามสกุล", "")), "line_id": str(line_user_id)}
        return False, None
    except Exception: return False, None

# --- LIFF Script (Adapted from working logic) ---
def liff_initializer_component():
    # ถ้ามี UserID แล้ว ไม่ต้องโหลด Script ซ้ำ
    if "line_user_id" in st.session_state or st.query_params.get("userid"):
        return

    # ตรรกะ: Init -> Check Login -> Get Profile -> Redirect Parent
    # ใช้ window.top.location เพื่อบังคับเปลี่ยน URL ของหน้าหลัก (หลุดจาก iframe)
    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        async function main() {{
            try {{
                await liff.init({{ liffId: "{LIFF_ID}" }});
                
                if (!liff.isLoggedIn()) {{
                    liff.login();
                    return;
                }}
                
                const profile = await liff.getProfile();
                const userId = profile.userId;
                
                // ตรวจสอบ URL ปัจจุบันของหน้าหลัก (ไม่ใช่ iframe)
                const currentUrl = new URL(window.top.location.href);
                
                // ถ้ายังไม่มี userid ใน URL ให้เติมและ Reload
                if (!currentUrl.searchParams.has("userid")) {{
                    currentUrl.searchParams.set("userid", userId);
                    window.top.location.href = currentUrl.toString();
                }}
                
            }} catch (err) {{
                console.error("LIFF Error:", err);
                document.getElementById("status-msg").innerText = "เกิดข้อผิดพลาด: " + err.message;
            }}
        }}
        main();
    </script>
    <div style="text-align:center; padding:20px; background-color:#f0f2f6; border-radius:10px;">
        <h4 style="color:#00796B;">กำลังเชื่อมต่อกับ LINE...</h4>
        <p id="status-msg">กรุณารอสักครู่ ระบบกำลังยืนยันตัวตน</p>
    </div>
    """
    components.html(js_code, height=150)

def render_admin_line_manager():
    st.error("Admin Panel Disabled")

# --- Render Page ---
def render_registration_page(df):
    st.markdown("""<style>.reg-container {padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; background-color: white;} .stButton>button {background-color: #00B900 !important; color: white !important;}</style>""", unsafe_allow_html=True)
    
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: st.session_state["line_user_id"] = qp_userid
    
    # เรียกใช้ Script เพื่อดึง UserID
    if "line_user_id" not in st.session_state: 
        liff_initializer_component()
        return

    line_user_id = st.session_state["line_user_id"]
    is_registered, user_info = check_if_user_registered(line_user_id)
    
    if is_registered:
        found_rows = df[df['ชื่อ-สกุล'].str.contains(user_info['first_name'], na=False)]
        matched_user = None
        for _, row in found_rows.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            if db_f == user_info['first_name'] and db_l == user_info['last_name']: matched_user = row; break
        
        if matched_user:
             if not st.session_state.get('authenticated'):
                st.session_state.update({'authenticated': True, 'pdpa_accepted': True, 'user_hn': matched_user['HN'], 'user_name': matched_user['ชื่อ-สกุล'], 'is_line_login': True})
                st.rerun()
             return
        else: st.error("ไม่พบข้อมูลสุขภาพในฐานข้อมูล"); return

    if st.session_state.get('line_register_success', False):
        st.success("✅ ลงทะเบียนเรียบร้อยแล้ว!"); 
        if st.button("เข้าดูผลตรวจสุขภาพ"): st.rerun()
        return

    with st.container():
        st.markdown("<div class='reg-container'><h2 style='text-align:center; color:#00B900;'>ลงทะเบียน</h2>", unsafe_allow_html=True)
        with st.form("line_reg_form"):
            c1, c2 = st.columns(2)
            f = c1.text_input("ชื่อ")
            l = c2.text_input("นามสกุล")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            pdpa = st.checkbox("ยอมรับเงื่อนไข PDPA")
            if st.form_submit_button("ยืนยัน", use_container_width=True):
                if not pdpa: st.warning("กรุณายอมรับ PDPA")
                else:
                    suc, msg, row = check_registration_logic(df, f, l, i)
                    if suc:
                        save_suc, save_msg = save_new_user_to_gsheet(clean_string(f), clean_string(l), line_user_id, clean_string(i))
                        if save_suc:
                            st.session_state.update({'line_saved': True, 'line_register_success': True, 'authenticated': True, 'pdpa_accepted': True, 'user_hn': row['HN'], 'user_name': row['ชื่อ-สกุล']})
                            st.rerun()
                        else: st.error(f"❌ บันทึกไม่สำเร็จ: {save_msg}")
                    else: st.error(f"❌ {msg}")
        st.markdown("</div>", unsafe_allow_html=True)
