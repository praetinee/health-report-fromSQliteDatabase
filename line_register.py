import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

# --- Constants ---
SHEET_ID = "1tJ1UK4SusWNpfD-bARfCUm_zc7jlo4xvrrWDW9DoFIU"
WORKSHEET_NAME = "UserID"

# ---------------------------------------------------------------------
# จุดที่คุณต้องแก้ไขคือตรงนี้ครับ! 👇
# เอาเลข LIFF ID ที่ได้จากเว็บ LINE Developers มาใส่แทนคำว่า YOUR_LIFF_ID_HERE
# ---------------------------------------------------------------------
LIFF_ID = "YOUR_LIFF_ID_HERE" 


# --- Google Sheets Connection ---
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("⚠️ ไม่พบตั้งค่า gcp_service_account ใน Secrets")
        return None
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client

def get_user_worksheet():
    client = get_gsheet_client()
    if not client: return None
    try:
        sheet = client.open_by_key(SHEET_ID)
        try:
            worksheet = sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=3)
            worksheet.append_row(["ชื่อ", "นามสกุล", "LINE User ID"])
        return worksheet
    except Exception as e:
        st.error(f"❌ ไม่สามารถเปิด Google Sheet ได้: {e}")
        return None

# --- Helper Functions ---
def check_if_user_registered(line_user_id):
    ws = get_user_worksheet()
    if not ws: return False, None
    try:
        line_ids = ws.col_values(3)
        if line_user_id in line_ids:
            row_idx = line_ids.index(line_user_id) + 1
            row_data = ws.row_values(row_idx)
            user_info = {"first_name": row_data[0], "last_name": row_data[1], "line_id": line_user_id}
            return True, user_info
        return False, None
    except: return False, None

def save_new_user_to_sheet(fname, lname, line_user_id):
    ws = get_user_worksheet()
    if not ws: return False, "Connect Error"
    try:
        if line_user_id in ws.col_values(3): return True, "Duplicate"
        ws.append_row([fname, lname, line_user_id])
        return True, "Saved"
    except Exception as e: return False, str(e)

def clean_string(val): return str(val).strip() if not pd.isna(val) else ""

def normalize_db_name_field(full_name_str):
    parts = clean_string(full_name_str).split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    return (parts[0], "") if len(parts) == 1 else ("", "")

def check_registration_logic(df, input_fname, input_lname, input_id):
    i_fname = clean_string(input_fname)
    i_lname = clean_string(input_lname)
    i_id = clean_string(input_id)
    if not i_fname or not i_lname or not i_id: return False, "กรอกไม่ครบ", None
    if len(i_id) != 13: return False, "เลขบัตรต้อง 13 หลัก", None
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]
    if user_match.empty: return False, "ไม่พบเลขบัตร", None
    for _, row in user_match.iterrows():
        db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
        if db_f == i_fname and db_l.replace(" ", "") == i_lname.replace(" ", ""):
            return True, "สำเร็จ", row.to_dict()
    return False, "ชื่อนามสกุลไม่ตรง", None

# --- LIFF Script ---
def liff_initializer_component():
    if "line_user_id" in st.session_state or st.query_params.get("userid"):
        return

    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        async function main() {{
            try {{
                await liff.init({{ liffId: "{LIFF_ID}" }});
                if (liff.isLoggedIn()) {{
                    const profile = await liff.getProfile();
                    const userId = profile.userId;
                    const currentUrl = new URL(window.location.href);
                    if (!currentUrl.searchParams.has("userid")) {{
                        currentUrl.searchParams.set("userid", userId);
                        window.location.href = currentUrl.toString();
                    }}
                }} else {{
                    liff.login();
                }}
            }} catch (err) {{
                console.error("LIFF Init failed", err);
            }}
        }}
        main();
    </script>
    <div style="text-align:center; padding:20px;">
        <p>กำลังเชื่อมต่อกับ LINE... กรุณารอสักครู่</p>
    </div>
    """
    components.html(js_code, height=100)

# --- Admin Manager ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน LINE (Google Sheets)")
    ws = get_user_worksheet()
    if not ws:
        st.warning("ไม่สามารถเชื่อมต่อ Google Sheets ได้")
        return
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            st.info("ยังไม่มีข้อมูลผู้ลงทะเบียน")
        else:
            st.dataframe(df, use_container_width=True)
            st.markdown(f"[เปิดดูไฟล์ Google Sheets]({ 'https://docs.google.com/spreadsheets/d/' + SHEET_ID })")
            st.info("💡 หากต้องการแก้ไขหรือลบข้อมูล กรุณาทำใน Google Sheets โดยตรง ข้อมูลจะอัปเดตมาที่นี่เมื่อรีเฟรช")
            if st.button("รีเฟรชข้อมูล"): st.rerun()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

# --- Main Render Function ---
def render_registration_page(df):
    st.markdown("""<style>.reg-container{padding:2rem;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,0.1);max-width:500px;margin:auto;}.reg-header{color:#00B900;text-align:center;font-weight:bold;margin-bottom:1.5rem;}.stButton>button{background-color:#00B900!important;color:white!important;border-radius:50px;height:50px;font-size:18px;}</style>""", unsafe_allow_html=True)
    
    qp_userid = st.query_params.get("userid", None)
    if qp_userid: st.session_state["line_user_id"] = qp_userid
    
    if "line_user_id" not in st.session_state:
        if st.checkbox("Dev Mode: Mock UserID"):
            st.session_state["line_user_id"] = "U_MOCK_TEST_12345"
            st.rerun()
        liff_initializer_component()
        return

    line_user_id = st.session_state["line_user_id"]
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
             st.error("พบการลงทะเบียน แต่ไม่พบข้อมูลสุขภาพในระบบ")
             return

    if st.session_state.get('line_register_success', False):
        st.success("✅ ลงทะเบียนเรียบร้อยแล้ว!")
        if st.button("เข้าดูผลตรวจสุขภาพ", type="primary", use_container_width=True): st.rerun()
        return

    with st.container():
        st.markdown("<h2 class='reg-header'>ลงทะเบียนเชื่อมต่อบัญชี</h2>", unsafe_allow_html=True)
        with st.expander("📄 ข้อตกลงและเงื่อนไข (PDPA)", expanded=False):
            st.markdown("1. ยินยอมให้เก็บข้อมูลชื่อ-นามสกุล/เลขบัตร\n2. แสดงผลเฉพาะเจ้าของข้อมูล")
        pdpa_check = st.checkbox("ข้าพเจ้ายอมรับข้อตกลงและเงื่อนไข (PDPA)")
        st.markdown("---")
        with st.form("line_reg_form"):
            c1, c2 = st.columns(2)
            with c1: f = st.text_input("ชื่อ")
            with c2: l = st.text_input("นามสกุล")
            i = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13)
            sub = st.form_submit_button("ยืนยันตัวตน", use_container_width=True)

        if sub:
            if not pdpa_check: st.warning("กรุณายอมรับ PDPA")
            else:
                suc, msg, row = check_registration_logic(df, f, l, i)
                if suc:
                    save_suc, save_msg = save_new_user_to_sheet(clean_string(f), clean_string(l), line_user_id)
                    if save_suc:
                        st.session_state.update({
                            'line_register_success': True,
                            'authenticated': True,
                            'pdpa_accepted': True,
                            'user_hn': row['HN'],
                            'user_name': row['ชื่อ-สกุล']
                        })
                        st.rerun()
                    else: st.error(save_msg)
                else: st.error(msg)
