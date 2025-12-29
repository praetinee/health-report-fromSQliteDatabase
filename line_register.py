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

# --- Google Sheets Connection ---
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # 1. Try Local JSON (Priority)
    target_files = ["service_account.json.json", "service_account.json"]
    for f in target_files:
        if os.path.exists(f):
            try:
                return gspread.authorize(Credentials.from_service_account_file(f, scopes=scopes))
            except Exception as e:
                st.error(f"❌ อ่านไฟล์ {f} ไม่สำเร็จ: {e}")
    
    # 2. Try st.secrets
    if "gcp_service_account" in st.secrets:
        try:
            return gspread.authorize(Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes))
        except Exception as e:
            st.error(f"❌ Secrets Error: {e}")

    st.error("❌ ไม่พบไฟล์ service_account หรือการตั้งค่า Secrets")
    return None

def get_worksheet():
    client = get_gsheet_client()
    if not client: return None
    try:
        # เปิดไฟล์ด้วยชื่อ
        sheet = client.open(SHEET_NAME)
        # ลองหา Worksheet ที่ถูกต้อง
        try: 
            return sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            # STRICT MODE: ไม่สร้างใหม่แล้ว ให้แจ้ง Error เลยถ้าไม่เจอ
            st.error(f"❌ ไม่พบ Tab ชื่อ '{WORKSHEET_NAME}' ในไฟล์ '{SHEET_NAME}'")
            st.info("กรุณาสร้าง Tab ใหม่ชื่อ 'UserID' ให้ถูกต้อง")
            return None
    except gspread.SpreadsheetNotFound:
        st.error(f"❌ ไม่พบไฟล์ Google Sheet ชื่อ '{SHEET_NAME}'")
        st.info("กรุณาตรวจสอบชื่อไฟล์ใน Google Drive ให้ตรงเป๊ะๆ (ระวังช่องว่าง)")
        return None
    except Exception as e:
        st.error(f"❌ Error เปิด Google Sheet: {e}")
        return None

def test_connection_status():
    try: return True if get_worksheet() else False
    except: return False

# --- User Management ---
def check_if_user_registered(line_user_id):
    try:
        ws = get_worksheet()
        if not ws: return False, None
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty: return False, None
        
        target_col = "LINE User ID"
        if target_col not in df.columns:
            for c in df.columns: 
                if "Line" in str(c) and "ID" in str(c): target_col = c; break
        
        if target_col in df.columns:
            match = df[df[target_col].astype(str).str.strip() == str(line_user_id).strip()]
            if not match.empty:
                r = match.iloc[0]
                return True, {"first_name": str(r.get("ชื่อ","")), "last_name": str(r.get("นามสกุล","")), "line_id": str(line_user_id)}
        return False, None
    except: return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id, id_card=""):
    try:
        ws = get_worksheet()
        if not ws: return False, "Connect Failed"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [timestamp, str(fname).strip(), str(lname).strip(), str(line_user_id).strip(), str(id_card).strip()]
        
        ws.append_row(row_data)
        
        # DEBUG: ส่งชื่อไฟล์กลับไปบอก User
        return True, f"บันทึกแล้วที่ไฟล์: {ws.spreadsheet.title} (Tab: {ws.title})"
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
    if "line_user_id" in st.session_state or st.query_params.get("userid"): return
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
        }} catch(e) {{ document.getElementById("msg").innerText="Error: "+e; }}
    }}
    main();
    </script>
    <div id="msg" style="text-align:center;padding:20px;">กำลังเชื่อมต่อ LINE...</div>"""
    components.html(js, height=100)

def render_admin_line_manager(): st.error("Disabled")

# --- UI ---
def render_registration_page(df):
    st.markdown("""<style>.reg-container {padding: 2rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 500px; margin: auto; background-color: white;} .stButton>button {background-color: #00B900 !important; color: white !important;}</style>""", unsafe_allow_html=True)
    
    # 1. เช็คการเชื่อมต่อทันที
    if not test_connection_status():
        st.stop() # หยุดการทำงานถ้าระบบ Database ไม่พร้อม จะได้ไม่กด Submit ฟรี
    
    qp = st.query_params.get("userid")
    if qp: st.session_state["line_user_id"] = qp
    if "line_user_id" not in st.session_state: liff_initializer_component(); return

    uid = st.session_state["line_user_id"]
    is_reg, info = check_if_user_registered(uid)
    
    if is_reg:
        found = df[df['ชื่อ-สกุล'].str.contains(info['first_name'], na=False)]
        user = None
        for _, r in found.iterrows():
            dbf, dbl = normalize_db_name_field(r['ชื่อ-สกุล'])
            if dbf == info['first_name'] and dbl == info['last_name']: user = r; break
        
        if user is not None:
            if not st.session_state.get('authenticated'):
                st.session_state.update({'authenticated': True, 'pdpa_accepted': True, 'user_hn': user['HN'], 'user_name': user['ชื่อ-สกุล'], 'is_line_login': True})
                st.rerun()
            return
        else: st.error("User ID not linked to Health Data")

    if st.session_state.get('line_register_success'):
        st.success("✅ ลงทะเบียนสำเร็จ!"); 
        if st.button("ดูผลตรวจ"): st.rerun()
        return

    with st.container():
        st.markdown("<div class='reg-container'><h3 style='text-align:center;'>ลงทะเบียน</h3>", unsafe_allow_html=True)
        with st.form("reg_form"):
            c1, c2 = st.columns(2)
            f = c1.text_input("ชื่อ")
            l = c2.text_input("นามสกุล")
            i = st.text_input("เลขบัตร (13 หลัก)", max_chars=13)
            pdpa = st.checkbox("ยอมรับเงื่อนไข PDPA")
            sub = st.form_submit_button("ยืนยันข้อมูล", use_container_width=True)
        
        if sub:
            if not pdpa: st.warning("กรุณายอมรับ PDPA")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    # บันทึกทันที
                    with st.spinner("⏳ กำลังบันทึกลงฐานข้อมูล..."):
                        sv_suc, sv_msg = save_new_user_to_gsheet(clean_string(f), clean_string(l), uid, clean_string(i))
                    
                    if sv_suc:
                        # แสดงข้อความยืนยันก่อน Redirect
                        st.success(f"✅ {sv_msg}") 
                        
                        # อัปเดต State ให้ครบถ้วน เพื่อไม่ให้เด้งไปหน้า PDPA ซ้ำ
                        st.session_state['line_saved'] = True
                        st.session_state['line_register_success'] = True
                        st.session_state['authenticated'] = True
                        st.session_state['pdpa_accepted'] = True
                        st.session_state['user_hn'] = row['HN']
                        st.session_state['user_name'] = row['ชื่อ-สกุล']
                        
                        time.sleep(2) # ให้เวลา User อ่านข้อความว่าบันทึกสำเร็จที่ไฟล์ไหน
                        st.rerun()
                    else: 
                        st.error(f"❌ บันทึกไม่สำเร็จ: {sv_msg}")
                else: 
                    st.error(f"❌ {msg}")
        st.markdown("</div>", unsafe_allow_html=True)
