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

# --- 2. Google Sheets Connection (Core Logic) ---
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

# --- 5. UI & Styling (Modern & Luxurious) ---
def inject_premium_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        
        .stApp { font-family: 'Sarabun', sans-serif; background-color: #f4f7f6; }
        
        /* Modern Card */
        .auth-card {
            background: #ffffff;
            padding: 2.5rem;
            border-radius: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.05);
            text-align: center;
            max-width: 480px;
            margin: 2rem auto;
            border: 1px solid rgba(0,0,0,0.02);
        }

        /* Typography */
        .auth-title {
            color: #111;
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            letter-spacing: -0.5px;
        }
        .auth-subtitle {
            color: #666;
            font-size: 1rem;
            margin-bottom: 2rem;
            font-weight: 400;
        }

        /* Input Styling */
        div[data-testid="stTextInput"] label {
            font-size: 0.9rem;
            color: #444;
            font-weight: 500;
        }
        div[data-testid="stTextInput"] input {
            border-radius: 12px !important;
            border: 1px solid #e0e0e0 !important;
            padding: 12px 15px !important;
            transition: all 0.2s;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #00A699 !important;
            box-shadow: 0 0 0 3px rgba(0, 166, 153, 0.1) !important;
        }

        /* Premium Button */
        .stButton button {
            background: linear-gradient(135deg, #00A699 0%, #00796B 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 50px !important;
            padding: 14px 28px !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            width: 100%;
            box-shadow: 0 4px 12px rgba(0, 121, 107, 0.2) !important;
            transition: transform 0.2s !important;
        }
        .stButton button:hover {
            transform: translateY(-2px);
            filter: brightness(1.05);
        }
        
        /* Status Box */
        .status-box {
            background: #E0F2F1;
            color: #00695C;
            padding: 12px;
            border-radius: 12px;
            font-size: 0.9rem;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 6. LIFF Listener (ANTI-LOOP Logic) ---
def liff_token_catcher():
    # 1. เช็ค Session State ก่อนเลย (เร็วที่สุด)
    if "line_user_id" in st.session_state:
        return True

    # 2. เช็ค URL Parameters
    qp_userid = st.query_params.get("userid")
    if qp_userid:
        st.session_state["line_user_id"] = qp_userid
        # บังคับหยุดการทำงานตรงนี้เลย แล้ว rerun ใหม่ เพื่อให้หน้าเว็บรับรู้ Session ทันที
        # ไม่ต้องรอ render HTML ข้างล่าง
        st.rerun() 
        return True

    # 3. ถ้าไม่มีอะไรเลย -> รัน JS LIFF
    # ตรรกะสำคัญ: JS จะเช็ค URL ก่อนว่ามี userid ไหม ถ้ามีจะไม่ redirect ซ้ำ
    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        const LIFF_ID = "{LIFF_ID}";
        const TARGET_URL = "{APP_URL}";

        async function main() {{
            // SAFETY CHECK 1: ถ้า URL มี userid แล้ว ห้ามทำอะไรต่อ (ป้องกัน Loop)
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('userid')) {{
                console.log("User ID found in URL, stopping LIFF script.");
                return;
            }}

            try {{
                await liff.init({{ liffId: LIFF_ID }});
                if (liff.isLoggedIn()) {{
                    const profile = await liff.getProfile();
                    const userId = profile.userId;
                    
                    // Redirect เพื่อเติม parameter
                    // SAFETY CHECK 2: เช็คอีกครั้งก่อน redirect
                    if (!window.location.href.includes(userId)) {{
                        const separator = TARGET_URL.includes("?") ? "&" : "?";
                        window.top.location.href = TARGET_URL + separator + "userid=" + userId;
                    }}
                }} else {{
                    // กรณีเปิดใน Browser นอก LINE และยังไม่ Login
                    // เราจะไม่ Auto-Login เพื่อให้ User กดปุ่มเอง (UX ดีกว่า)
                    console.log("User not logged in.");
                }}
            }} catch (e) {{
                console.error("LIFF Error:", e);
            }}
        }}
        main();
    </script>
    """
    components.html(js_code, height=0, width=0)
    return False

# --- 7. Admin Manager ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน")
    sheet, msg = get_user_worksheet()
    if sheet:
        st.dataframe(pd.DataFrame(sheet.get_all_records()), use_container_width=True)
    else:
        st.error(msg)

# --- 8. MAIN RENDER FUNCTION ---
def render_registration_page(df):
    inject_premium_css()
    
    # 1. พยายามดึง Token
    has_token = liff_token_catcher()

    # 2. จัด Layout กึ่งกลาง
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col2:
        # --- กรณีที่ 1: ยังไม่ได้รับ Line ID (แสดงปุ่ม Login) ---
        if not has_token:
            st.markdown("""
            <div class="auth-card">
                <div style="margin-bottom: 20px;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/4/41/LINE_logo.svg" width="60" alt="LINE">
                </div>
                <h2 class="auth-title">ยินดีต้อนรับ</h2>
                <p class="auth-subtitle">ระบบรายงานผลสุขภาพออนไลน์</p>
                <div style="height: 20px;"></div>
                <p style="font-size: 0.95rem; color: #555; margin-bottom: 30px;">
                    เพื่อความปลอดภัยของข้อมูลส่วนบุคคล<br>กรุณายืนยันตัวตนผ่าน LINE
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # ใช้ Link Button โดยตรงเพื่อความเสถียร (หนีปัญหา JS Loop)
            login_url = f"https://liff.line.me/{LIFF_ID}"
            st.link_button("เข้าสู่ระบบด้วย LINE", login_url, type="primary", use_container_width=True)
            return

        # --- กรณีที่ 2: มี ID แล้ว -> เช็คสถานะ ---
        line_user_id = st.session_state["line_user_id"]
        
        # ตรวจสอบสมาชิก (ใช้ Cache เพื่อไม่ให้เช็คซ้ำๆ จนกระพริบ)
        if "reg_check_result" not in st.session_state:
            with st.spinner("⏳ กำลังยืนยันข้อมูลสมาชิก..."):
                is_reg, u_info = check_if_user_registered(line_user_id)
                st.session_state["reg_check_result"] = (is_reg, u_info)
                # บังคับ Rerun เพื่อให้ UI อัปเดตทันที
                st.rerun()

        is_registered, user_info = st.session_state["reg_check_result"]

        # --- กรณีที่ 3: เป็นสมาชิกเก่า (Auto Login) ---
        if is_registered:
            # ค้นหาใน SQLite
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
                st.markdown(f"""
                <div class="auth-card">
                    <h3 class="auth-title">ไม่พบผลตรวจ</h3>
                    <div class="status-box">
                        คุณ {user_info['first_name']}
                    </div>
                    <p class="auth-subtitle">พบประวัติการลงทะเบียน แต่ไม่พบข้อมูลผลตรวจสุขภาพในปีนี้</p>
                    <hr style="opacity: 0.1;">
                    <p style="font-size: 0.85rem; color: #888;">หากมั่นใจว่าตรวจแล้ว กรุณาติดต่อเจ้าหน้าที่</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("ลองใหม่", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()
            return

        # --- กรณีที่ 4: สมาชิกใหม่ (แสดงฟอร์ม) ---
        st.markdown(f"""
        <div class="auth-card" style="padding-bottom: 10px;">
            <h2 class="auth-title">ลงทะเบียนครั้งแรก</h2>
            <div class="status-box">
                ✅ เชื่อมต่อกับ LINE: {line_user_id[:4]}...
            </div>
            <p class="auth-subtitle" style="margin-bottom: 10px;">กรอกข้อมูลให้ตรงกับบัตรประชาชน</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("modern_reg_form"):
            fname = st.text_input("ชื่อจริง (ไม่ต้องมีคำนำหน้า)")
            lname = st.text_input("นามสกุล")
            cid = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            
            st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
            pdpa = st.checkbox("ข้าพเจ้ายอมรับข้อตกลง PDPA ในการเปิดเผยข้อมูล")
            
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("ยืนยันข้อมูล")

        if submit_btn:
            if not pdpa:
                st.toast("⚠️ กรุณายอมรับข้อตกลง PDPA")
            else:
                with st.spinner("กำลังตรวจสอบ..."):
                    valid, msg, row = check_registration_logic(df, fname, lname, cid)
                    if valid:
                        success, save_msg = save_new_user_to_gsheet(clean_string(fname), clean_string(lname), line_user_id)
                        if success:
                            st.toast("✅ ลงทะเบียนสำเร็จ!")
                            time.sleep(1)
                            st.session_state.update({
                                'authenticated': True, 
                                'pdpa_accepted': True, 
                                'user_hn': row['HN'], 
                                'user_name': row['ชื่อ-สกุล']
                            })
                            st.rerun()
                        else:
                            st.error(f"ระบบบันทึกมีปัญหา: {save_msg}")
                    else:
                        st.error(f"❌ {msg}")
