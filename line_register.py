import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import datetime
import json
import time

# --- 1. Configuration ---
SERVICE_ACCOUNT_FILE = "service_account.json" 
GOOGLE_SHEET_FILENAME = "LINE User id for Database" 
GOOGLE_SHEET_TABNAME = "UserID"
LIFF_ID = "2008725340-YHOiWxtj"
APP_URL = "https://health-report-fromappdatabase-d53gxcssza4ravg7plcbcv.streamlit.app/"

# --- 2. Google Sheets Connection (Core Logic - ไม่แตะต้องส่วนนี้) ---
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    creds = None
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception as e: return None, f"Secrets Error: {str(e)}"
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
        except Exception as e: return None, f"File Error: {str(e)}"
    else: return None, "Credential Not Found"
    try:
        client = gspread.authorize(creds)
        return client, "OK"
    except Exception as e: return None, f"Auth Error: {str(e)}"

def get_user_worksheet():
    client, msg = get_gsheet_client()
    if not client: return None, msg
    try:
        sheet_file = client.open(GOOGLE_SHEET_FILENAME)
        try: worksheet = sheet_file.worksheet(GOOGLE_SHEET_TABNAME)
        except gspread.WorksheetNotFound: worksheet = sheet_file.sheet1
        if not worksheet.row_values(1): worksheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID", "Timestamp"])
        return worksheet, "OK"
    except Exception as e: return None, f"Sheet Error: {str(e)}"

# --- 3. User Management Logic ---
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
    except Exception as e: return False, None

def save_new_user_to_gsheet(fname, lname, line_user_id):
    sheet, msg = get_user_worksheet()
    if not sheet: return False, msg
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([str(fname), str(lname), str(line_user_id), timestamp])
        return True, "Success"
    except Exception as e: return False, f"Write Error: {str(e)}"

# --- 4. Logic Helpers ---
def clean_string(val): return str(val).strip() if not pd.isna(val) else ""
def normalize_db_name_field(full_name_str):
    parts = clean_string(full_name_str).split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    return (parts[0], "") if len(parts) == 1 else ("", "")

def check_registration_logic(df, input_fname, input_lname, input_id):
    i_fname = clean_string(input_fname).replace(" ", "")
    i_lname = clean_string(input_lname).replace(" ", "")
    i_id = clean_string(input_id)
    
    if not input_fname or not input_lname or not i_id: return False, "กรุณากรอกข้อมูลให้ครบถ้วน", None
    if len(i_id) != 13 or not i_id.isdigit(): return False, "เลขบัตรประชาชนต้องเป็นตัวเลข 13 หลัก", None

    def name_match(row_val):
        if pd.isna(row_val): return False
        db_f, db_l = normalize_db_name_field(str(row_val))
        return (db_f.replace(" ", "") == i_fname) and (db_l.replace(" ", "") == i_lname)

    name_matches = df[df['ชื่อ-สกุล'].apply(name_match)]
    if name_matches.empty: return False, "ไม่พบชื่อ-นามสกุลนี้ในระบบฐานข้อมูล", None
    
    valid_user = name_matches[name_matches['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]
    if valid_user.empty: return False, "ชื่อถูกต้อง แต่เลขบัตรประชาชนไม่ตรงกับฐานข้อมูล", None
        
    return True, "OK", valid_user.iloc[0].to_dict()

# --- 5. UI & Styling (The Luxurious Upgrade) ---
def inject_premium_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        
        /* Global Reset */
        .stApp { font-family: 'Sarabun', sans-serif; background-color: #f8f9fa; }
        
        /* Card Style */
        .login-card {
            background: #ffffff;
            padding: 2.5rem;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.02);
            text-align: center;
            max-width: 500px;
            margin: 0 auto;
        }

        /* Typography */
        .header-title {
            color: #1B5E20; /* Dark Green */
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .header-subtitle {
            color: #666;
            font-size: 0.95rem;
            margin-bottom: 2rem;
            font-weight: 400;
        }

        /* Input Fields Customization */
        div[data-testid="stTextInput"] input {
            border-radius: 12px !important;
            border: 1px solid #e0e0e0 !important;
            padding: 12px 15px !important;
            font-size: 1rem !important;
            transition: all 0.3s;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #1B5E20 !important;
            box-shadow: 0 0 0 2px rgba(27, 94, 32, 0.1) !important;
        }

        /* Buttons */
        .stButton button {
            background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 12px 24px !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 15px rgba(27, 94, 32, 0.3) !important;
            transition: transform 0.2s, box-shadow 0.2s !important;
            width: 100%;
        }
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(27, 94, 32, 0.4) !important;
        }

        /* Success/Error Message Styling */
        .msg-box {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .msg-error { background-color: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; }
        .msg-success { background-color: #E8F5E9; color: #2E7D32; border: 1px solid #C8E6C9; }
        .msg-info { background-color: #E3F2FD; color: #1565C0; border: 1px solid #BBDEFB; }

        /* Loader */
        .stSpinner > div { border-top-color: #1B5E20 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 6. LIFF Listener (The Anti-Loop Version) ---
def liff_token_catcher():
    # ถ้ามี ID ใน Session แล้ว ไม่ต้องรัน Script ซ้ำ (หยุด Loop)
    if "line_user_id" in st.session_state:
        return

    # Check query params
    qp_userid = st.query_params.get("userid")
    
    # ถ้าใน URL มี ID แล้ว ให้ดึงมาใส่ Session เลย ไม่ต้องรัน Script
    if qp_userid:
        st.session_state["line_user_id"] = qp_userid
        st.rerun() # รีโหลดเพื่ออัปเดต State ทันที
        return

    # ถ้ายังไม่มีอะไรเลย รัน Script นี้เพื่อ Redirect
    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        const LIFF_ID = "{LIFF_ID}";
        const TARGET_URL = "{APP_URL}";

        async function main() {{
            try {{
                await liff.init({{ liffId: LIFF_ID }});
                if (liff.isLoggedIn()) {{
                    const profile = await liff.getProfile();
                    const userId = profile.userId;
                    
                    // ตรวจสอบว่า URL ปัจจุบันมี userid หรือยัง เพื่อป้องกัน Loop
                    const urlParams = new URLSearchParams(window.location.search);
                    if (!urlParams.has('userid')) {{
                        // Redirect เพื่อเติม parameter
                        const separator = TARGET_URL.includes("?") ? "&" : "?";
                        window.top.location.href = TARGET_URL + separator + "userid=" + userId;
                    }}
                }} else {{
                    // ถ้ายังไม่ Login ไม่ต้องทำอะไร รอ user กดปุ่ม
                }}
            }} catch (e) {{
                console.error("LIFF Error:", e);
            }}
        }}
        main();
    </script>
    """
    components.html(js_code, height=0, width=0)

# --- 7. Admin Manager ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน (Admin Only)")
    sheet, msg = get_user_worksheet()
    if sheet:
        st.dataframe(pd.DataFrame(sheet.get_all_records()), use_container_width=True)
    else:
        st.error(f"Error: {msg}")

# --- 8. MAIN RENDER FUNCTION ---
def render_registration_page(df):
    inject_premium_css()
    
    # 1. รัน LIFF Listener (แบบป้องกัน Loop)
    liff_token_catcher()

    # 2. จัด Layout ให้อยู่ตรงกลางแบบ Card
    cols = st.columns([1, 2, 1])
    with cols[1]:
        
        # --- A. เช็คสถานะการเชื่อมต่อ LINE ---
        if "line_user_id" not in st.session_state:
            # กรณี: ยังไม่ได้รับ Line ID
            st.markdown("""
            <div class="login-card">
                <h2 class="header-title">บริการรายงานผลสุขภาพ</h2>
                <p class="header-subtitle">Health Report Service</p>
                <div style="margin: 30px 0;">
                    <img src="https://img.icons8.com/color/96/line-me.png" alt="LINE" style="width:80px; margin-bottom:15px;">
                    <p style="color:#555; font-size:0.9rem;">กรุณายืนยันตัวตนผ่าน LINE เพื่อความปลอดภัย<br>และเข้าถึงข้อมูลสุขภาพของท่าน</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # ปุ่ม Login (ใช้ Link LIFF ตรงๆ เพื่อความชัวร์)
            login_url = f"https://liff.line.me/{LIFF_ID}"
            st.link_button("🟢 เข้าสู่ระบบด้วย LINE", login_url, type="primary", use_container_width=True)
            return

        # --- B. ได้รับ Line ID แล้ว -> กำลังตรวจสอบ ---
        line_user_id = st.session_state["line_user_id"]
        
        # ค้นหาใน Google Sheets (ใช้ Spinner เพื่อความสวยงาม)
        if "reg_check_done" not in st.session_state:
            with st.spinner("⏳ กำลังตรวจสอบสถานะสมาชิก..."):
                is_registered, user_info = check_if_user_registered(line_user_id)
                st.session_state["reg_is_registered"] = is_registered
                st.session_state["reg_user_info"] = user_info
                st.session_state["reg_check_done"] = True
                # หน่วงเวลาเล็กน้อยให้ UX ดูลื่นไหล ไม่กระพริบ
                time.sleep(0.5) 
                st.rerun()

        is_registered = st.session_state.get("reg_is_registered", False)
        user_info = st.session_state.get("reg_user_info", None)

        # --- C. กรณี: เป็นสมาชิกแล้ว (Auto Login) ---
        if is_registered:
            # Logic: ค้นหาข้อมูลใน SQLite ตามชื่อที่ได้จาก GSheet
            def name_match_auto(row_val):
                if pd.isna(row_val): return False
                db_f, db_l = normalize_db_name_field(str(row_val))
                return (db_f.replace(" ", "") == user_info['first_name'].replace(" ", "")) and \
                       (db_l.replace(" ", "") == user_info['last_name'].replace(" ", ""))

            matched_rows = df[df['ชื่อ-สกุล'].apply(name_match_auto)]
            
            if not matched_rows.empty:
                # Login สำเร็จ
                matched_user = matched_rows.iloc[0]
                if not st.session_state.get('authenticated'):
                    st.session_state.update({
                        'authenticated': True, 
                        'pdpa_accepted': True, 
                        'user_hn': matched_user['HN'], 
                        'user_name': matched_user['ชื่อ-สกุล'], 
                        'is_line_login': True
                    })
                    st.rerun()
            else:
                # กรณีแปลก: ลงทะเบียนแล้ว แต่ปีนี้ไม่มีชื่อใน SQLite
                st.markdown(f"""
                <div class="login-card">
                    <div class="msg-box msg-info">
                        <span>👋 สวัสดีคุณ <b>{user_info['first_name']}</b><br>พบประวัติการลงทะเบียนเดิม แต่ไม่พบผลตรวจสุขภาพในปีนี้</span>
                    </div>
                    <p style="color:#666; font-size:0.9rem;">หากท่านมั่นใจว่าได้ตรวจสุขภาพแล้ว กรุณาติดต่อเจ้าหน้าที่</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("ลองค้นหาใหม่อีกครั้ง", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()
            return

        # --- D. กรณี: สมาชิกใหม่ (แสดงฟอร์มลงทะเบียน) ---
        st.markdown(f"""
        <div class="login-card">
            <h2 class="header-title">ลงทะเบียนใช้งานครั้งแรก</h2>
            <p class="header-subtitle">First-time Registration</p>
            <div class="msg-box msg-info" style="justify-content: center;">
                <span>เชื่อมต่อกับ LINE ID: <b>{line_user_id[:6]}...</b> ✅</span>
            </div>
            <p style="font-size: 0.9rem; color: #555; text-align: left; margin-bottom: 15px;">
                กรุณากรอกข้อมูลให้ตรงกับบัตรประชาชน เพื่อยืนยันว่าเป็นเจ้าของข้อมูลจริง
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Form Container (แยกออกมานอก Card HTML เพื่อให้ Streamlit Input ทำงานได้)
        with st.form("modern_reg_form"):
            fname = st.text_input("ชื่อจริง (ไม่ต้องระบุคำนำหน้า)", placeholder="เช่น สมชาย")
            lname = st.text_input("นามสกุล", placeholder="เช่น ใจดี")
            cid = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13, placeholder="xxxxxxxxxxxxx")
            
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            pdpa = st.checkbox("ข้าพเจ้ายอมรับข้อตกลง PDPA ในการเปิดเผยข้อมูลสุขภาพ")
            
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("ยืนยันข้อมูลและเข้าสู่ระบบ")

        if submit_btn:
            if not pdpa:
                st.toast("⚠️ กรุณายอมรับข้อตกลง PDPA ก่อนดำเนินการ")
            else:
                with st.spinner("กำลังตรวจสอบความถูกต้อง..."):
                    valid, msg, row = check_registration_logic(df, fname, lname, cid)
                    
                    if valid:
                        # บันทึก GSheet
                        save_suc, save_msg = save_new_user_to_gsheet(clean_string(fname), clean_string(lname), line_user_id)
                        
                        if save_suc:
                            st.balloons()
                            st.toast("✅ ลงทะเบียนสำเร็จ! ยินดีต้อนรับครับ")
                            time.sleep(1) # รอให้ user อ่านข้อความ
                            # Login
                            st.session_state.update({
                                'authenticated': True, 
                                'pdpa_accepted': True, 
                                'user_hn': row['HN'], 
                                'user_name': row['ชื่อ-สกุล']
                            })
                            st.rerun()
                        else:
                            st.error(f"ระบบบันทึกข้อมูลขัดข้อง: {save_msg}")
                    else:
                        st.error(f"❌ {msg}")
