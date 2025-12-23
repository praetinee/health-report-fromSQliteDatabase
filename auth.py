import streamlit as st
import pandas as pd
import os
import base64

# --- Helper Functions ---
def clean_string(val):
    if pd.isna(val): return ""
    return str(val).strip()

def normalize_db_name_field(full_name_str):
    clean_val = clean_string(full_name_str)
    parts = clean_val.split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    elif len(parts) == 1: return parts[0], ""
    return "", ""

def get_image_base64(path):
    """แปลงไฟล์รูปภาพเป็น Base64 เพื่อแสดงใน HTML"""
    try:
        if not os.path.exists(path):
            return None
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None

def check_user_credentials(df, fname, lname, cid):
    i_fname = clean_string(fname)
    i_lname = clean_string(lname)
    i_id = clean_string(cid)

    if i_fname.lower() == "admin" and i_lname.lower() == "admin" and i_id.lower() == "admin":
        return True, "เข้าสู่ระบบผู้ดูแลระบบ", {"role": "admin", "name": "Administrator"}

    if not i_fname or not i_lname or not i_id:
        return False, "กรุณากรอกข้อมูลให้ครบทุกช่อง", None

    if len(i_id) != 13:
        return False, "เลขบัตรประชาชนต้องมี 13 หลัก", None

    user_match = df[df['เลขบัตรประชาชน'].astype(str).str.strip() == i_id]

    if user_match.empty:
        return False, "ไม่พบเลขบัตรประชาชนนี้ในระบบ", None

    found_user = None
    for _, row in user_match.iterrows():
        db_fname, db_lname = normalize_db_name_field(row['ชื่อ-สกุล'])
        if (db_fname == i_fname) and (db_lname.replace(" ", "") == i_lname.replace(" ", "")):
            found_user = row.to_dict()
            break
    
    if found_user:
        found_user['role'] = 'user'
        return True, "ยืนยันตัวตนสำเร็จ", found_user
    else:
        return False, "ชื่อหรือนามสกุลไม่ตรงกับฐานข้อมูล (แต่เลขบัตรถูกต้อง)", None

def authentication_flow(df):
    """หน้า Login แบบ Responsive และ Theme-Aware พร้อมโลโก้"""
    
    st.markdown("""
    <style>
        .login-container {
            background-color: var(--secondary-background-color);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            max-width: 500px;
            margin: auto;
            border: 1px solid rgba(128, 128, 128, 0.2);
        }
        .login-header {
            text-align: center;
            color: #00B900; 
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
            border: none;
        }
        .stButton>button:hover {
            filter: brightness(1.1);
        }
        .logo-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 20px;
            width: 100%;
        }
        .logo-img {
            max-width: 80px; /* ลดขนาดรูปลงจาก 100px เป็น 80px */
            height: auto;
            object-fit: contain;
        }
    </style>
    """, unsafe_allow_html=True)

    # เตรียม HTML สำหรับโลโก้
    logo_path = "image_0809c0.png"
    logo_html = ""
    
    # พยายามโหลดรูปจากไฟล์ก่อน
    img_b64 = get_image_base64(logo_path)
    
    if img_b64:
        # ถ้าเจอไฟล์ แปลงเป็น base64
        logo_src = f"data:image/png;base64,{img_b64}"
        logo_html = f"<div class='logo-container'><img src='{logo_src}' class='logo-img'></div>"
    else:
        # ถ้าไม่เจอไฟล์ ให้ใช้ URL รูปที่คุณส่งมา
        fallback_url = "https://i.postimg.cc/MGxD3yWn/fce5f6c4-b813-48cc-bf40-393032a7eb6d.png" 
        logo_html = f"<div class='logo-container'><img src='{fallback_url}' class='logo-img'></div>"

    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        with st.container():
            st.markdown("<div class='login-container'>", unsafe_allow_html=True)
            
            # แสดงโลโก้ (จะแสดงแน่นอนเพราะมี fallback)
            st.markdown(logo_html, unsafe_allow_html=True)
            
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
                    st.session_state['pdpa_accepted'] = False 
                
                st.success(msg)
                st.rerun()
            else:
                st.error(f"❌ {msg}")

def pdpa_consent_page():
    """หน้ายอมรับ PDPA แบบ Theme-Aware"""
    st.markdown("""
    <div style='background-color: var(--secondary-background-color); padding: 2rem; border-radius: 10px; margin-top: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid rgba(128,128,128,0.2);'>
        <h3 style='text-align: center; color: var(--text-color);'>ข้อตกลงและเงื่อนไข (PDPA)</h3>
        <hr style='border-color: rgba(128,128,128,0.2);'>
        <div style='height: 200px; overflow-y: auto; background-color: var(--background-color); padding: 15px; border-radius: 5px; font-size: 14px; border: 1px solid rgba(128,128,128,0.1); color: var(--text-color);'>
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
