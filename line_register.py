import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os

# --- Constants ---
# ชื่อไฟล์ CSV ที่จะใช้เก็บข้อมูล
CSV_FILE_NAME = "LINE User id for Database - UserID.csv"

# ---------------------------------------------------------------------
# จุดที่คุณต้องแก้ไขคือตรงนี้ครับ! 👇
# เอาเลข LIFF ID ที่ได้จากเว็บ LINE Developers มาใส่แทนคำว่า YOUR_LIFF_ID_HERE
# ---------------------------------------------------------------------
LIFF_ID = "YOUR_LIFF_ID_HERE" 

# --- CSV Management Functions ---
def get_user_dataframe():
    """อ่านข้อมูลจากไฟล์ CSV ถ้าไม่มีไฟล์ให้สร้างใหม่"""
    if not os.path.exists(CSV_FILE_NAME):
        # สร้าง DataFrame ว่างพร้อม Header
        df = pd.DataFrame(columns=["ชื่อ", "นามสกุล", "LINE User ID"])
        df.to_csv(CSV_FILE_NAME, index=False, encoding='utf-8-sig') # ใช้ utf-8-sig เพื่อรองรับภาษาไทยใน Excel
        return df
    try:
        df = pd.read_csv(CSV_FILE_NAME)
        # ตรวจสอบว่ามี Column ครบไหม ถ้าไม่ครบให้สร้างใหม่ (กัน Error)
        required_cols = ["ชื่อ", "นามสกุล", "LINE User ID"]
        if not all(col in df.columns for col in required_cols):
             st.warning("ไฟล์ CSV มีโครงสร้างไม่ถูกต้อง กำลังสร้างใหม่...")
             df = pd.DataFrame(columns=required_cols)
             df.to_csv(CSV_FILE_NAME, index=False, encoding='utf-8-sig')
        return df
    except Exception as e:
        st.error(f"❌ ไม่สามารถอ่านไฟล์ CSV ได้: {e}")
        return pd.DataFrame(columns=["ชื่อ", "นามสกุล", "LINE User ID"])

def save_new_user_to_csv(fname, lname, line_user_id):
    """บันทึกผู้ใช้ใหม่ลง CSV (ต่อท้าย)"""
    try:
        df = get_user_dataframe()
        
        # ตรวจสอบซ้ำอีกครั้งว่ามี ID นี้หรือยัง
        if line_user_id in df["LINE User ID"].astype(str).values:
             return True, "ผู้ใช้นี้มีอยู่ในระบบแล้ว"

        # สร้าง DataFrame แถวใหม่
        new_row = pd.DataFrame([{
            "ชื่อ": fname,
            "นามสกุล": lname,
            "LINE User ID": line_user_id
        }])
        
        # บันทึกต่อท้าย (Append mode 'a') หรือเขียนทับทั้งไฟล์
        # เพื่อความง่ายและปลอดภัย ใช้ concat แล้ว save ทับทั้งไฟล์
        updated_df = pd.concat([df, new_row], ignore_index=True)
        updated_df.to_csv(CSV_FILE_NAME, index=False, encoding='utf-8-sig')
        
        return True, "บันทึกข้อมูลสำเร็จ"
    except Exception as e:
        return False, f"บันทึกข้อมูลล้มเหลว: {e}"

def check_if_user_registered(line_user_id):
    """ตรวจสอบว่า LINE ID นี้มีใน CSV แล้วหรือยัง"""
    try:
        df = get_user_dataframe()
        # แปลงเป็น string เพื่อความชัวร์ในการเปรียบเทียบ
        match = df[df["LINE User ID"].astype(str) == str(line_user_id)]
        
        if not match.empty:
            row = match.iloc[0]
            user_info = {
                "first_name": str(row["ชื่อ"]), 
                "last_name": str(row["นามสกุล"]), 
                "line_id": line_user_id
            }
            return True, user_info
        return False, None
    except Exception as e: 
        st.error(f"Error checking user: {e}")
        return False, None

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
    if not i_fname or not i_lname or not i_id: return False, "กรอกไม่ครบ", None
    if len(i_id) != 13: return False, "เลขบัตรต้อง 13 หลัก", None
    
    # แปลงคอลัมน์เลขบัตรประชาชนให้เป็น string และลบช่องว่างก่อนเปรียบเทียบ
    # สำคัญ: ต้องแน่ใจว่า df มาจาก load_sqlite_data ที่ clean แล้ว
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]
    
    if user_match.empty: return False, "ไม่พบเลขบัตร", None
    for _, row in user_match.iterrows():
        db_f, db_l = normalize_db_name_field(row['ชื่อ-สกุล'])
        # เทียบแบบ ignore case และ space
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

# --- Admin Manager (CSV Version) ---
def render_admin_line_manager():
    st.subheader("📱 จัดการผู้ใช้งาน LINE (CSV Database)")
    try:
        df = get_user_dataframe()
        if df.empty:
            st.info("ยังไม่มีข้อมูลผู้ลงทะเบียน")
        else:
            st.dataframe(df, use_container_width=True)
            
            # ปุ่ม Download CSV
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์ CSV",
                data=csv,
                file_name=CSV_FILE_NAME,
                mime='text/csv',
            )
            
            st.info("💡 ข้อมูลถูกบันทึกอยู่ในไฟล์ CSV บน Server")
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
                    save_suc, save_msg = save_new_user_to_csv(clean_string(f), clean_string(l), line_user_id)
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
