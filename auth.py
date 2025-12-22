import streamlit as st
import pandas as pd

# --- Helper Functions ---
def clean_string(val):
    """ทำความสะอาด string ตัดช่องว่างหัวท้าย"""
    if pd.isna(val): return ""
    return str(val).strip()

def normalize_db_name_field(full_name_str):
    """แยกชื่อ-นามสกุลจาก DB"""
    parts = clean_string(full_name_str).split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:]) # ชื่อแรก, ที่เหลือเป็นนามสกุล
    elif len(parts) == 1:
        return parts[0], ""
    return "", ""

def check_user_credentials(df, fname, lname, cid):
    """
    ตรวจสอบข้อมูลผู้ใช้:
    1. กรณี Admin (กรอก admin ทั้ง 3 ช่อง)
    2. กรณี User ทั่วไป (เทียบกับ DB)
    """
    fname = clean_string(fname)
    lname = clean_string(lname)
    cid = clean_string(cid)

    # 1. Check Admin Bypass
    if fname.lower() == "admin" and lname.lower() == "admin" and cid.lower() == "admin":
        return True, "Admin Access Granted", {"role": "admin", "name": "Administrator"}

    # 2. Check Regular User
    if not fname or not lname or not cid:
        return False, "กรุณากรอกข้อมูลให้ครบทุกช่อง", None

    # กรองด้วยเลขบัตรประชาชน (แม่นยำสุด)
    # แปลงคอลัมน์ใน DB เป็น string และตัดช่องว่าง
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == cid]

    if user_match.empty:
        return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบ", None

    # ตรวจสอบชื่อ-นามสกุล
    found_user = None
    for _, row in user_match.iterrows():
        db_fname, db_lname = normalize_db_name_field(row['ชื่อ-สกุล'])
        
        # เปรียบเทียบ (Ignore case และ space ใน input)
        # ใช้ replace(" ", "") เพื่อยอมหยวนกรณี User พิมพ์เว้นวรรคในชื่อตัวเองมา
        if (db_fname == fname) and (db_lname.replace(" ", "") == lname.replace(" ", "")):
            found_user = row.to_dict()
            break
    
    if found_user:
        # ใส่ role user ให้ชัดเจน
        found_user['role'] = 'user'
        return True, "Login สำเร็จ", found_user
    else:
        return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล (เลขบัตรถูกต้อง)", None

def authentication_flow(df):
    """แสดงหน้า Login แบบ 3 ช่อง (ใช้ร่วมกันทั้ง PC และ LINE)"""
    
    st.markdown("""
    <style>
        .login-container {
            background-color: white;
            padding: 3rem;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-width: 500px;
            margin: auto;
        }
        .login-header {
            text-align: center;
            color: #2C3E50;
            margin-bottom: 2rem;
        }
        .stButton>button {
            width: 100%;
            border-radius: 25px;
            height: 50px;
            font-size: 18px;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h2 class='login-header'>เข้าสู่ระบบ / ยืนยันตัวตน</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            fname = st.text_input("ชื่อ (ไม่ต้องระบุคำนำหน้า)", placeholder="เช่น สมชาย (หรือ admin)")
            lname = st.text_input("นามสกุล", placeholder="เช่น ใจดี (หรือ admin)")
            cid = st.text_input("เลขบัตรประชาชน (13 หลัก)", type="password", placeholder="xxxxxxxxxxxxx (หรือ admin)")
            
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary")

        if submitted:
            success, msg, user_data = check_user_credentials(df, fname, lname, cid)
            
            if success:
                st.session_state['authenticated'] = True
                
                if user_data['role'] == 'admin':
                    st.session_state['is_admin'] = True
                    st.session_state['user_name'] = "Administrator"
                    st.session_state['pdpa_accepted'] = True 
                else:
                    st.session_state['is_admin'] = False
                    st.session_state['user_hn'] = user_data['HN']
                    st.session_state['user_name'] = user_data['ชื่อ-สกุล']
                    st.session_state['pdpa_accepted'] = False 
                
                st.success(msg)
                st.rerun()
            else:
                st.error(f"❌ {msg}")

def pdpa_consent_page():
    """หน้ายอมรับ PDPA (แสดงหลังจาก Login ผ่านแล้ว)"""
    st.markdown("""
    <div style='background-color: white; padding: 2rem; border-radius: 10px; margin-top: 2rem;'>
        <h2 style='text-align: center; color: #2C3E50;'>ข้อตกลงการใช้งานและนโยบายความเป็นส่วนตัว (PDPA)</h2>
        <hr>
        <p>เพื่อประโยชน์ในการดูแลสุขภาพของท่าน และเพื่อให้เป็นไปตามพระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)</p>
        <ol>
            <li>ข้าพเจ้ายินยอมให้โรงพยาบาล/หน่วยงาน ใช้และเปิดเผยข้อมูลผลตรวจสุขภาพของข้าพเจ้า เพื่อการประมวลผลและแสดงรายงานสุขภาพ</li>
            <li>ข้อมูลของท่านจะถูกเก็บรักษาเป็นความลับ และเข้าถึงได้เฉพาะเจ้าของข้อมูลและเจ้าหน้าที่ที่เกี่ยวข้องเท่านั้น</li>
            <li>ท่านสามารถระงับความยินยอมได้โดยแจ้งเจ้าหน้าที่</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        agree = st.checkbox("ข้าพเจ้าได้อ่านและยอมรับข้อตกลงข้างต้น")
        if st.button("ยืนยันและเข้าใช้งาน", type="primary", use_container_width=True, disabled=not agree):
            st.session_state['pdpa_accepted'] = True
            st.rerun()
