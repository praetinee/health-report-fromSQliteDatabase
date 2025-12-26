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
# ชื่อไฟล์บน Google Drive ต้องตรงเป๊ะทุกตัวอักษร
GOOGLE_SHEET_FILENAME = "LINE User id for Database" 
# ชื่อแท็บด้านล่าง
GOOGLE_SHEET_TABNAME = "UserID"
# LIFF ID ของคุณ
LIFF_ID = "2008725340-YHOiWxtj"

# ลิ้งค์ปลายทาง (Endpoint URL) ที่ถูกต้อง
# *** สำคัญ: ต้องตรงกับ Endpoint URL ใน LINE Developers Console เป๊ะๆ ***
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
            # ถ้าหาแท็บไม่เจอ ให้ใช้แท็บแรกแทน และแจ้งเตือนใน Console (ไม่โชว์ user)
            print(f"Warning: Sheet '{GOOGLE_SHEET_TABNAME}' not found. Using the first sheet.")
            worksheet = sheet_file.sheet1
        
        # เช็คหัวตาราง (ถ้าว่างเปล่า ให้สร้างหัวตาราง)
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
        
        # แปลงเป็น string เพื่อความชัวร์ในการเปรียบเทียบ
        match = df[df["LINE User ID"].astype(str) == str(line_user_id)]
        if not match.empty:
            row = match.iloc[0]
            # คืนค่า ชื่อ-นามสกุล ที่เคยลงทะเบียนไว้ เพื่อเอาไปค้นใน SQLite ต่อ
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
    """
    ตรวจสอบสิทธิ์การเข้าใช้งาน:
    1. ค้นหาจาก ชื่อ-นามสกุล ก่อน (SQLite)
    2. ถ้าเจอ -> ตรวจสอบว่าเลขบัตรตรงกันหรือไม่
    """
    i_fname = clean_string(input_fname)
    i_lname = clean_string(input_lname)
    i_id = clean_string(input_id)
    
    # Basic Validation
    if not i_fname or not i_lname or not i_id: 
        return False, "กรุณากรอกข้อมูลให้ครบ", None
    if len(i_id) != 13 or not i_id.isdigit(): 
        return False, "เลขบัตรต้องเป็น 13 หลัก", None
    
    # เตรียมข้อมูลสำหรับค้นหา (ลบช่องว่างเพื่อความแม่นยำ)
    i_fname_norm = i_fname.replace(" ", "")
    i_lname_norm = i_lname.replace(" ", "")

    # Helper function สำหรับตรวจสอบชื่อใน DataFrame
    def name_match(row_val):
        if pd.isna(row_val): return False
        db_f, db_l = normalize_db_name_field(str(row_val))
        return (db_f.replace(" ", "") == i_fname_norm) and (db_l.replace(" ", "") == i_lname_norm)

    # 1. ค้นหาคนที่ชื่อตรงกัน
    # ใช้ apply เพื่อค้นหา (รองรับกรณีชื่อใน DB มีวรรคตอนไม่แน่นอน)
    name_matches = df[df['ชื่อ-สกุล'].apply(name_match)]
    
    if name_matches.empty:
        return False, "ไม่พบชื่อ-นามสกุลนี้ในระบบฐานข้อมูลสุขภาพ", None
    
    # 2. ตรวจสอบเลขบัตรประชาชน (Validation)
    # ในกลุ่มคนที่ชื่อตรงกัน มีคนไหนเลขบัตรตรงไหม?
    valid_user = name_matches[name_matches['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]
    
    if valid_user.empty:
        return False, "ชื่อ-นามสกุลถูกต้อง แต่เลขบัตรประชาชนไม่ตรงกับฐานข้อมูล", None
        
    # เจอข้อมูลที่ถูกต้อง (คืนค่า row แรกที่เจอ)
    return True, "OK", valid_user.iloc[0].to_dict()

# --- 5. LIFF Listener (ตัวช่วยดึง ID จาก LINE) ---
def liff_token_catcher():
    """
    ฟังก์ชันนี้จะทำงานอยู่เบื้องหลัง เพื่อรอรับค่าจาก LINE Login
    """
    # ถ้ามี ID แล้ว ไม่ต้องทำอะไร
    if "line_user_id" in st.session_state or st.query_params.get("userid"):
        return

    # ถ้ายังไม่มี ID ให้รัน Script นี้
    # มันจะเช็คว่า User Login ผ่าน LINE หรือยัง ถ้า Login แล้วจะดึง ID มาใส่ URL
    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        const TARGET_APP_URL = "{APP_URL}";
        async function main() {{
            try {{
                await liff.init({{ liffId: "{LIFF_ID}" }});
                
                // เช็คว่า Login แล้วหรือยัง
                if (liff.isLoggedIn()) {{
                    const profile = await liff.getProfile();
                    const userId = profile.userId;
                    
                    // ตรวจสอบ URL ปัจจุบัน
                    const currentUrl = new URL(window.location.href);
                    
                    // ถ้าใน URL ยังไม่มี userid ให้เติมเข้าไปแล้ว Redirect
                    if (!currentUrl.searchParams.has("userid")) {{
                        // สร้าง URL ใหม่ที่มี userid
                        const separator = TARGET_APP_URL.includes("?") ? "&" : "?";
                        const finalUrl = TARGET_APP_URL + separator + "userid=" + userId;
                        
                        // สั่ง Redirect ไปยังหน้าที่มี userid
                        window.top.location.href = finalUrl;
                    }}
                }}
            }} catch (e) {{ 
                console.log("LIFF Listener error:", e); 
            }}
        }}
        main();
    </script>
    """
    # height=0 เพื่อซ่อนไม่ให้เห็น
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
    
    # A. รันตัวดักจับสัญญาณ LIFF
    liff_token_catcher()

    # B. รับ User ID จาก URL (ถ้ามี)
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: 
        st.session_state["line_user_id"] = qp_userid

    # C. ตรวจสอบว่ามี User ID ใน Session หรือยัง
    if "line_user_id" not in st.session_state:
        # --- กรณีที่ 1: ยังไม่มี ID (แสดงปุ่ม Login) ---
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 30px; background-color: #f9f9f9; border-radius: 10px;">
            <h3 style="color: #333;">ยืนยันตัวตนเพื่อดูผลตรวจสุขภาพ</h3>
            <p style="color:gray;">กรุณากดปุ่มสีเขียวด้านล่าง เพื่อเข้าสู่ระบบผ่าน LINE</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ปุ่ม Login โดยใช้ LIFF URL
        login_url = f"https://liff.line.me/{LIFF_ID}"
        st.link_button("🟢 เข้าสู่ระบบด้วย LINE (คลิก)", login_url, type="primary", use_container_width=True)
        return

    # --- กรณีที่ 2: มี ID แล้ว (แสดง ID และทำงานต่อ) ---
    line_user_id = st.session_state["line_user_id"]
    
    # แสดงข้อความยืนยันว่าได้รับ ID แล้ว
    st.success(f"✅ เชื่อมต่อ LINE สำเร็จ (ID: {line_user_id[:8]}...)")

    # ตรวจสอบกับ Google Sheet ว่าเคยลงทะเบียนหรือยัง
    with st.spinner("กำลังตรวจสอบข้อมูลสมาชิก..."):
        is_registered, user_info = check_if_user_registered(line_user_id)

    if is_registered:
        # --- เคยลงทะเบียนแล้ว -> ให้ Login อัตโนมัติ ---
        # ใช้ชื่อ-นามสกุลจาก Google Sheet มาค้นหาข้อมูลใน SQLite
        # เพื่อดึง HN และข้อมูลล่าสุด
        
        # ค้นหาแบบ Name Match (Logic เดียวกับ check_registration_logic แต่ไม่ต้องเช็ค ID แล้ว)
        def name_match_auto(row_val):
            if pd.isna(row_val): return False
            db_f, db_l = normalize_db_name_field(str(row_val))
            # เปรียบเทียบแบบตัดช่องว่าง
            return (db_f.replace(" ", "") == user_info['first_name'].replace(" ", "")) and \
                   (db_l.replace(" ", "") == user_info['last_name'].replace(" ", ""))

        matched_rows = df[df['ชื่อ-สกุล'].apply(name_match_auto)]
        
        if not matched_rows.empty:
             matched_user = matched_rows.iloc[0]
             if not st.session_state.get('authenticated'):
                st.session_state.update({
                    'authenticated': True, 
                    'pdpa_accepted': True, # ถือว่ายอมรับแล้วจากการลงทะเบียนครั้งแรก
                    'user_hn': matched_user['HN'], 
                    'user_name': matched_user['ชื่อ-สกุล'], 
                    'is_line_login': True
                })
                st.rerun()
             return
        else:
             st.error(f"⚠️ พบประวัติการลงทะเบียนของคุณ {user_info['first_name']} {user_info['last_name']} แต่ไม่พบข้อมูลผลตรวจสุขภาพในฐานข้อมูลปีนี้")
             st.info("กรุณาติดต่อเจ้าหน้าที่หากท่านมั่นใจว่าได้ตรวจสุขภาพแล้ว")
             return

    # --- ยังไม่เคยลงทะเบียน -> แสดงฟอร์มลงทะเบียน ---
    st.markdown("---")
    st.subheader("📝 ลงทะเบียนครั้งแรก (First-time Registration)")
    
    with st.form("reg_form"):
        st.caption("กรุณากรอกข้อมูลให้ตรงกับบัตรประชาชนเพื่อยืนยันตัวตน")
        f = st.text_input("ชื่อ (ไม่ต้องมีคำนำหน้า)")
        l = st.text_input("นามสกุล")
        i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
        pdpa = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข (PDPA) ในการเปิดเผยข้อมูลสุขภาพ")
        
        if st.form_submit_button("ยืนยันข้อมูล", use_container_width=True):
            if not pdpa:
                st.warning("⚠️ กรุณายอมรับข้อตกลง PDPA ก่อนดำเนินการ")
            else:
                # ใช้ Logic ใหม่: ค้นหาชื่อ -> เช็ค ID
                valid, msg, row = check_registration_logic(df, f, l, i)
                
                if valid:
                    # บันทึกข้อมูลลง Google Sheet (ชื่อ, นามสกุล, LINE ID)
                    save_suc, save_msg = save_new_user_to_gsheet(clean_string(f), clean_string(l), line_user_id)
                    
                    if save_suc:
                        st.balloons()
                        st.success("✅ ลงทะเบียนสำเร็จ! กำลังเข้าสู่ระบบ...")
                        # อัปเดต Session เพื่อเข้าหน้าหลัก
                        st.session_state.update({
                            'authenticated': True, 
                            'pdpa_accepted': True, 
                            'user_hn': row['HN'], 
                            'user_name': row['ชื่อ-สกุล']
                        })
                        st.rerun()
                    else:
                        st.error(f"❌ บันทึกข้อมูลลงระบบทะเบียนไม่สำเร็จ: {save_msg}")
                else:
                    st.error(f"❌ {msg}")
