import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import os
import time

# --- Constants ---
LIFF_ID = "2008725340-YHOiWxtj"
SHEET_NAME = "LINE User ID for Database" 
WORKSHEET_NAME = "UserID"

# --- Mock Classes (สำหรับโหมดจำลองเมื่อเชื่อมต่อไม่ได้) ---
class MockWorksheet:
    def __init__(self):
        self.title = "Mock Worksheet"
        self.spreadsheet = type('obj', (object,), {'title': 'Mock Spreadsheet'})
        # ข้อมูลจำลองเริ่มต้น
        self.data = [
            {"Timestamp": "2024-01-01", "ชื่อ": "Test", "นามสกุล": "User", "LINE User ID": "U123456789", "CardID": "1100012345678"}
        ]

    def get_all_records(self):
        return self.data

    def append_row(self, row_data):
        # จำลองการบันทึกข้อมูล (timestamp, fname, lname, line_id, id_card)
        record = {
            "Timestamp": row_data[0],
            "ชื่อ": row_data[1],
            "นามสกุล": row_data[2],
            "LINE User ID": row_data[3],
            "CardID": row_data[4]
        }
        self.data.append(record)
        return True

class MockClient:
    def open(self, name):
        return self
    def worksheet(self, name):
        return MockWorksheet()

# --- Google Sheets Connection ---
def get_gsheet_client():
    # Definite scopes for read/write access
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # 1. Try Local JSON (Priority)
    target_files = ["service_account.json.json", "service_account.json"]
    for f in target_files:
        if os.path.exists(f):
            try:
                creds = Credentials.from_service_account_file(f, scopes=scopes)
                return gspread.authorize(creds)
            except Exception as e:
                st.error(f"❌ อ่านไฟล์ {f} ไม่สำเร็จ: {e}")
    
    # 2. Try st.secrets
    if "gcp_service_account" in st.secrets:
        try:
            # Force dictionary conversion just in case it's a Streamlit Secrets object
            service_account_info = dict(st.secrets["gcp_service_account"])
            
            # Create credentials with explicit scopes
            creds = Credentials.from_service_account_info(
                service_account_info, 
                scopes=scopes
            )
            return gspread.authorize(creds)
        except Exception as e:
            # Detailed error logging
            st.error(f"❌ Secrets Error (Detail): {str(e)}")

    # 3. Fallback to Mock Client (แก้ปัญหาแอปพัง)
    if 'mock_mode_warned' not in st.session_state:
        st.warning("⚠️ ไม่พบ Google Credentials: ระบบกำลังทำงานใน 'โหมดจำลอง' (Mock Mode) ข้อมูลจะไม่ถูกบันทึกลง Google Sheets จริง")
        st.session_state['mock_mode_warned'] = True
    
    return MockClient()

def get_worksheet():
    client = get_gsheet_client()
    if not client: return None # Should not happen with MockClient
    
    # ถ้าเป็น Mock Client ให้คืนค่า MockWorksheet เลย
    if isinstance(client, MockClient):
        return client.worksheet("Mock")

    try:
        # เปิดไฟล์ด้วยชื่อ
        sheet = client.open(SHEET_NAME)
        # ลองหา Worksheet ที่ถูกต้อง
        try: 
            return sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            st.error(f"❌ ไม่พบ Tab ชื่อ '{WORKSHEET_NAME}' ในไฟล์ '{SHEET_NAME}'")
            return None
    except gspread.SpreadsheetNotFound:
        st.error(f"❌ ไม่พบไฟล์ Google Sheet ชื่อ '{SHEET_NAME}' (ตรวจสอบชื่อไฟล์และการแชร์สิทธิ์)")
        return None
    except Exception as e:
        st.error(f"❌ Error เปิด Google Sheet: {e}")
        return None

def test_connection_status():
    try: 
        ws = get_worksheet()
        return True if ws else False
    except: 
        return False

# --- User Management ---
def check_if_user_registered(line_user_id):
    try:
        ws = get_worksheet()
        if not ws: return False, None
        
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        
        if df.empty: return False, None
        
        target_col = "LINE User ID"
        # พยายามหา Column ที่ชื่อคล้ายๆ กัน
        if target_col not in df.columns:
            for c in df.columns: 
                if "Line" in str(c) and "ID" in str(c): target_col = c; break
        
        if target_col in df.columns:
            # ใช้ str() และ strip() เพื่อความชัวร์ในการเปรียบเทียบ
            match = df[df[target_col].astype(str).str.strip() == str(line_user_id).strip()]
            if not match.empty:
                r = match.iloc[0]
                return True, {"first_name": str(r.get("ชื่อ","")), "last_name": str(r.get("นามสกุล","")), "line_id": str(line_user_id)}
        return False, None
    except Exception as e: 
        # ถ้า Error ใน Mock Mode ให้ return False ไปเลย
        return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id, id_card=""):
    try:
        ws = get_worksheet()
        if not ws: return False, "Connect Failed"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [timestamp, str(fname).strip(), str(lname).strip(), str(line_user_id).strip(), str(id_card).strip()]
        
        ws.append_row(row_data)
        
        msg = f"บันทึกแล้วที่ไฟล์: {ws.spreadsheet.title} (Tab: {ws.title})"
        if isinstance(ws, MockWorksheet):
            msg = "บันทึกในโหมดจำลองสำเร็จ (ข้อมูลไม่ได้ลง Google Sheets จริง)"

        return True, msg
    except Exception as e:
        return False, f"Write Error: {e}"

# --- Helpers ---
def clean_string(val): return str(val).strip() if not pd.isna(val) else ""
def normalize_db_name_field(s): 
    parts = clean_string(s).split()
    return (parts[0], " ".join(parts[1:])) if len(parts)>=2 else (parts[0], "") if parts else ("","")

def check_registration_logic(df, f, l, i):
    f, l, i = clean_string(f), clean_string(l), clean_string(i)
    if not f or not l or not i: return False, "กรอกข้อมูลให้ครบ", None
    if len(i.replace("-","")) != 13: return False, "เลขบัตรต้องมี 13 หลัก", None
    
    try:
        match = df[df['เลขบัตรประชาชน'].astype(str).str.strip().str.replace("-","") == i.replace("-","")]
        if match.empty: return False, "ไม่พบข้อมูลในระบบ", None
        for _, row in match.iterrows():
            db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
            if db_f == f and db_l.replace(" ","") == l.replace(" ",""): return True, "OK", row.to_dict()
        return False, "ชื่อ-นามสกุลไม่ตรง", None
    except Exception as e: return False, f"System Error: {e}", None

# --- LIFF ---
def liff_initializer_component():
    # ถ้ามี Line User ID อยู่แล้ว ไม่ต้องโหลด LIFF ซ้ำ
    if "line_user_id" in st.session_state or st.query_params.get("userid"): return
    
    # ถ้าทำงานใน Localhost หรือไม่มี LIFF ID อาจจะข้าม LIFF ไปเลยเพื่อทดสอบ
    # แต่ในที่นี้เราปล่อย script ไว้ เผื่อ user ทดสอบผ่าน ngrok
    js = f"""<script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
    async function main() {{
        try {{ await liff.init({{ liffId: "{LIFF_ID}" }});
            if(!liff.isLoggedIn()){{ liff.login(); return; }}
            const p = await liff.getProfile();
            const url = new URL(window.top.location.href);
            if(!url.searchParams.has("userid")){{
                url.searchParams.set("userid", p.userId);
                window.top.location.href = url.toString();
            }}
        }} catch(e) {{ 
            console.log("LIFF Init Error (Ignore if Localhost): " + e);
            // Fallback for Localhost Testing without HTTPS
            // document.getElementById("msg").innerText="LIFF Error: "+e; 
        }}
    }}
    main();
    </script>
    <div id="msg" style="text-align:center;padding:10px;font-size:12px;color:gray;">...Checking LINE Login...</div>"""
    components.html(js, height=50)

def render_admin_line_manager(): st.error("Disabled")

# --- UI ---
def render_registration_page(df):
    st.markdown("""<style>.reg-container {padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; background-color: white;} .stButton>button {background-color: #00B900 !important; color: white !important;}</style>""", unsafe_allow_html=True)
    
    # 1. เช็คการเชื่อมต่อ (ตอนนี้จะไม่ stop แล้ว แต่จะใช้ Mock แทน)
    if not test_connection_status():
        st.warning("⚠️ Database Connection Failed completely. App might not work correctly.")
        # st.stop() # REMOVED: เพื่อไม่ให้แอปพัง
    
    qp = st.query_params.get("userid")
    if qp: st.session_state["line_user_id"] = qp
    
    # 2. เพิ่มปุ่ม Skip Login สำหรับการทดสอบ (Developer Mode)
    # ถ้ายังไม่มี UserID และยังไม่ได้ Login
    if "line_user_id" not in st.session_state and not st.session_state.get('authenticated'):
        liff_initializer_component()
        
        # --- Debug Helper ---
        with st.expander("🛠️ Developer / Debug Options"):
            st.write("ถ้า LIFF ไม่ทำงาน (เช่น รันบน Localhost) ให้ใส่ Mock User ID ตรงนี้:")
            mock_uid = st.text_input("Mock LINE User ID", "U_MOCK_12345")
            if st.button("Set Mock User ID"):
                st.session_state["line_user_id"] = mock_uid
                st.rerun()
        
        if "line_user_id" not in st.session_state:
            return # รอ LIFF หรือ Manual Input

    uid = st.session_state["line_user_id"]
    is_reg, info = check_if_user_registered(uid)
    
    # --- Logic ที่แก้ใหม่: ป้องกัน Auto-Login ทันที ---
    if is_reg and not st.session_state.get('force_re_register', False):
        found = df[df['ชื่อ-สกุล'].str.contains(info['first_name'], na=False)]
        user = None
        for _, r in found.iterrows():
            dbf, dbl = normalize_db_name_field(r['ชื่อ-สกุล'])
            if dbf == info['first_name'] and dbl == info['last_name']: user = r; break
        
        if user is not None:
            # เจอข้อมูลตรงกัน: ให้ User ยืนยันก่อน Login
            st.info(f"ยินดีต้อนรับกลับ คุณ {user['ชื่อ-สกุล']}")
            
            col_conf1, col_conf2 = st.columns(2)
            with col_conf1:
                if st.button("เข้าใช้งานทันที (Login)", type="primary", use_container_width=True):
                    st.session_state.update({'authenticated': True, 'pdpa_accepted': True, 'user_hn': user['HN'], 'user_name': user['ชื่อ-สกุล'], 'is_line_login': True})
                    st.rerun()
            with col_conf2:
                if st.button("ไม่ใช่ฉัน / ลงทะเบียนใหม่", use_container_width=True):
                    st.session_state['force_re_register'] = True
                    st.rerun()
            return # หยุดการทำงานตรงนี้ รอ User กดปุ่ม
        else: 
            # เจอใน GSheet แต่ไม่เจอใน SQLite
            st.warning(f"พบ LINE ID ของคุณ ({info['first_name']}) แต่ไม่พบข้อมูลสุขภาพที่ตรงกันในระบบปัจจุบัน")
            if st.button("ลงทะเบียนใหม่"):
                st.session_state['force_re_register'] = True
                st.rerun()
            return

    if st.session_state.get('line_register_success'):
        st.success("✅ ลงทะเบียนสำเร็จ!"); 
        if st.button("ดูผลตรวจ"): st.rerun()
        return

    with st.container():
        title_text = "ลงทะเบียนใหม่ (LINE)" if st.session_state.get('force_re_register') else "ลงทะเบียน (LINE)"
        st.markdown(f"<div class='reg-container'><h3 style='text-align:center;'>{title_text}</h3>", unsafe_allow_html=True)
        with st.form("reg_form"):
            c1, c2 = st.columns(2)
            f = c1.text_input("ชื่อ")
            l = c2.text_input("นามสกุล")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            
            st.markdown("---")
            st.markdown("**ข้อตกลงและเงื่อนไข (PDPA)**")
            st.caption("ข้าพเจ้ายินยอมให้ระบบตรวจสอบข้อมูลชื่อ-นามสกุล และเลขบัตรประชาชน เพื่อยืนยันตัวตน และบันทึกข้อมูล User ID ของ LINE เพื่อความสะดวกในการเข้าใช้งานครั้งถัดไป")
            pdpa = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข")
            
            sub = st.form_submit_button("ยืนยันข้อมูล", use_container_width=True)
        
        if sub:
            if not pdpa: st.warning("กรุณายอมรับ PDPA ก่อนลงทะเบียน")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    with st.spinner("⏳ กำลังบันทึก..."):
                        sv_suc, sv_msg = save_new_user_to_gsheet(clean_string(f), clean_string(l), uid, clean_string(i))
                    
                    if sv_suc:
                        st.success(f"✅ {sv_msg}") 
                        st.session_state['line_saved'] = True
                        st.session_state['line_register_success'] = True
                        st.session_state['authenticated'] = True
                        st.session_state['pdpa_accepted'] = True
                        st.session_state['user_hn'] = row['HN']
                        st.session_state['user_name'] = row['ชื่อ-สกุล']
                        # Reset flag เมื่อลงทะเบียนสำเร็จ
                        if 'force_re_register' in st.session_state: del st.session_state['force_re_register']
                        time.sleep(2)
                        st.rerun()
                    else: 
                        st.error(f"❌ บันทึกไม่สำเร็จ: {sv_msg}")
                else: 
                    st.error(f"❌ {msg}")
        st.markdown("</div>", unsafe_allow_html=True)
