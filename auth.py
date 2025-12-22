import streamlit as st
import pandas as pd

# --- Helper Functions ---
def clean_string(val):
    """ทำความสะอาด string ตัดช่องว่างหัวท้าย"""
    if pd.isna(val): return ""
    return str(val).strip()

def normalize_db_name_field(full_name_str):
    """แยกชื่อ-นามสกุลจาก DB โดยรองรับช่องว่างหลายรูปแบบ"""
    # ลบช่องว่างซ้ำซ้อน และตัดหัวท้าย
    clean_val = clean_string(full_name_str)
    # แยกด้วยช่องว่าง (กี่ช่องก็ได้)
    parts = clean_val.split()
    
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
    # Clean Input
    i_fname = clean_string(fname)
    i_lname = clean_string(lname)
    i_id = clean_string(cid)

    # 1. Check Admin Bypass
    if i_fname.lower() == "admin" and i_lname.lower() == "admin" and i_id.lower() == "admin":
        return True, "เข้าสู่ระบบผู้ดูแลระบบ", {"role": "admin", "name": "Administrator"}

    # 2. Check Regular User
    if not i_fname or not i_lname or not i_id:
        return False, "กรุณากรอกข้อมูลให้ครบทุกช่อง", None

    if len(i_id) != 13:
        return False, "เลขบัตรประชาชนต้องมี 13 หลัก", None

    # กรองด้วยเลขบัตรประชาชน (แม่นยำสุด)
    # แปลงคอลัมน์ใน DB เป็น string และตัดช่องว่าง
    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]

    if user_match.empty:
        return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบ", None

    # ตรวจสอบชื่อ-นามสกุล
    found_user = None
    for _, row in user_match.iterrows():
        db_fname, db_lname = normalize_db_name_field(row['ชื่อ-สกุล'])
        
        # เปรียบเทียบ (Ignore case และ space ใน input เพื่อความยืดหยุ่น)
        # เช่น DB: "สมชาย  ใจดี", Input: "สมชาย", "ใจดี" -> ตรงกัน
        # หรือ Input: "สมชาย ", " ใจดี " -> ตรงกัน
        if (db_fname == i_fname) and (db_lname.replace(" ", "") == i_lname.replace(" ", "")):
            found_user = row.to_dict()
            break
    
    if found_user:
        found_user['role'] = 'user'
        return True, "ยืนยันตัวตนสำเร็จ", found_user
    else:
        return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล (แต่เลขบัตรถูกต้อง)", None

def authentication_flow(df):
    """แสดงหน้า Login แบบ 3 ช่อง (ใช้ร่วมกันทั้ง PC และ LINE)"""
    
    st.markdown("""
    <style>
        .login-container {
            background-color: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            max-width: 500px;
            margin: auto;
        }
        .login-header {
            text-align: center;
            color: #00B900; /* LINE Green style or generic */
            margin-bottom: 1.5rem;
            font-weight: bold;
        }
        .stButton>button {
            width: 100%;
            border-radius: 50px;
            height: 50px;
            font-size: 18px;
            font-weight: bold;
            background-color: #00B900 !important;
            color: white !important;
        }
        div[data-testid="stTextInput"] label {
            font-size: 16px;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)

    # ใช้ Container เพื่อจัดกลาง (ถ้าระบบรองรับ) หรือใช้ Columns
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        with st.container():
            st.markdown("<div class='login-container'>", unsafe_allow_html=True)
            st.markdown("<h2 class='login-header'>ลงทะเบียน / เข้าสู่ระบบ</h2>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                st.write("กรุณากรอกข้อมูลเพื่อยืนยันตัวตน")
                fname = st.text_input("ชื่อ (ไม่ต้องระบุคำนำหน้า)", placeholder="เช่น สมชาย")
                lname = st.text_input("นามสกุล", placeholder="เช่น ใจดี")
                cid = st.text_input("เลขบัตรประชาชน (13 หลัก)", type="default", max_chars=13, placeholder="xxxxxxxxxxxxx")
                
                submitted = st.form_submit_button("ยืนยันตัวตน")

            st.markdown("</div>", unsafe_allow_html=True)

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
                    # Reset PDPA state เพื่อให้ User ต้องกดรับ (หรือจะเช็คจาก DB ก็ได้ถ้ามี)
                    # แต่ตามโจทย์ให้กดทุกครั้งที่ลงทะเบียนใหม่ หรือถ้า login แล้วให้กด PDPA
                    st.session_state['pdpa_accepted'] = False 
                
                st.success(msg)
                st.rerun()
            else:
                st.error(f"❌ {msg}")

def pdpa_consent_page():
    """หน้ายอมรับ PDPA"""
    st.markdown("""
    <div style='background-color: white; padding: 2rem; border-radius: 10px; margin-top: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.05);'>
        <h3 style='text-align: center; color: #2C3E50;'>ข้อตกลงและเงื่อนไข (PDPA)</h3>
        <hr>
        <div style='height: 200px; overflow-y: auto; background-color: #f9f9f9; padding: 15px; border-radius: 5px; font-size: 14px;'>
            <p><strong>การเก็บรวบรวมและใช้ข้อมูลส่วนบุคคล</strong></p>
            <p>1. ข้าพเจ้ายินยอมให้โรงพยาบาล/หน่วยงาน เก็บรักษาและใช้ข้อมูลส่วนบุคคลของข้าพเจ้า (ชื่อ, นามสกุล, เลขบัตรประชาชน) เพื่อวัตถุประสงค์ในการยืนยันตัวตนและแสดงผลการตรวจสุขภาพ</p>
            <p>2. ข้อมูลผลการตรวจสุขภาพจะถูกแสดงเฉพาะเจ้าของข้อมูลที่ผ่านการยืนยันตัวตนอย่างถูกต้องเท่านั้น</p>
            <p>3. ข้อมูลของท่านจะถูกเก็บรักษาตามมาตรฐานความปลอดภัยทางสารสนเทศ</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    agree = st.checkbox("ข้าพเจ้าได้อ่านและยอมรับข้อตกลงข้างต้น")
    
    if st.button("ตกลงและเข้าใช้งาน", type="primary", use_container_width=True, disabled=not agree):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
