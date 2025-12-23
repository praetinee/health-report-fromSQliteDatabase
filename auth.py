import streamlit as st
import pandas as pd
import os
import base64
import textwrap

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
    
    # CSS Style สำหรับหน้า Login
    login_style = """
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
    </style>
    """
    st.markdown(login_style, unsafe_allow_html=True)

    # เตรียม HTML สำหรับโลโก้
    logo_path = "image_0809c0.png"
    
    # พยายามโหลดรูปจากไฟล์ก่อน
    img_b64 = get_image_base64(logo_path)
    
    # กำหนดสไตล์แบบ Inline เพื่อบังคับขนาดรูปภาพให้เล็กลง (80px)
    img_style = "width: 80px; max-width: 80px; height: auto;"

    if img_b64:
        # ถ้าเจอไฟล์ แปลงเป็น base64
        logo_content = f"<img src='data:image/png;base64,{img_b64}' style='{img_style}'>"
    else:
        # ถ้าไม่เจอไฟล์ ให้ใช้ URL รูปที่คุณส่งมา
        fallback_url = "https://i.postimg.cc/MGxD3yWn/fce5f6c4-b813-48cc-bf40-393032a7eb6d.png" 
        logo_content = f"<img src='{fallback_url}' style='{img_style}'>"
        
    logo_html = f"<div class='logo-container'>{logo_content}</div>"

    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        with st.container():
            # ย้ายโลโก้ออกมาไว้นอก .login-container เพื่อไม่ให้มีกรอบครอบโลโก้
            st.markdown(logo_html, unsafe_allow_html=True)

            st.markdown("<div class='login-container'>", unsafe_allow_html=True)
            
            st.markdown("<h2 class='login-header'>ลงทะเบียน / เข้าสู่ระบบ</h2>", unsafe_allow_html=True)
            
            # ป้องกัน Duplicate Key โดยการไม่กำหนด Key ตายตัวหรือใช้ Key ที่ unique ใน session
            with st.form("login_form", clear_on_submit=False):
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
    """หน้ายอมรับ PDPA ดีไซน์สวยงาม พร้อมข้อความที่กำหนด"""
    
    # CSS สำหรับหน้า PDPA
    st.markdown("""
    <style>
        .pdpa-card {
            background-color: var(--secondary-background-color);
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid rgba(128,128,128,0.1);
            max-width: 800px;
            margin: 20px auto;
        }
        .pdpa-header {
            text-align: center;
            font-family: 'Sarabun', sans-serif;
            color: var(--text-color);
            margin-bottom: 20px;
            font-size: 22px;
            font-weight: bold;
            border-bottom: 1px solid rgba(128,128,128,0.2);
            padding-bottom: 15px;
        }
        .pdpa-content {
            background-color: var(--background-color);
            padding: 25px;
            border-radius: 8px;
            height: 400px;
            overflow-y: auto;
            border: 1px solid rgba(128,128,128,0.2);
            font-family: 'Sarabun', sans-serif;
            font-size: 16px;
            line-height: 1.8;
            color: var(--text-color);
        }
        .pdpa-content p {
            margin-bottom: 15px;
        }
        .pdpa-content ul {
            margin-bottom: 15px;
            padding-left: 25px;
        }
        .pdpa-content strong {
            color: #00796B;
        }
    </style>
    """, unsafe_allow_html=True)

    # เนื้อหา HTML (ใช้ textwrap.dedent เพื่อลบ indentation)
    content_html = textwrap.dedent("""
        <p><strong>โรงพยาบาลสันทราย</strong> ให้ความสำคัญกับการคุ้มครองข้อมูลส่วนบุคคลของท่าน เพื่อให้ท่านมั่นใจได้ว่าข้อมูลส่วนบุคคลของท่านที่เราได้รับจะถูกนำไปใช้ตรงตามความต้องการของท่านและถูกต้องตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล</p>
        
        <p><strong>วัตถุประสงค์ในการเก็บรวบรวม ใช้ หรือเปิดเผยข้อมูลส่วนบุคคล</strong></p>
        <ul>
            <li>เพื่อใช้ในการระบุและยืนยันตัวตนของท่านก่อนเข้าใช้งานระบบรายงานผลตรวจสุขภาพ</li>
            <li>เพื่อแสดงผลการตรวจสุขภาพและข้อมูลที่เกี่ยวข้องซึ่งเป็นข้อมูลส่วนบุคคลที่มีความอ่อนไหว</li>
            <li>เพื่อการวิเคราะห์ข้อมูลในภาพรวมสำหรับการพัฒนาคุณภาพบริการ (โดยไม่ระบุตัวตน)</li>
        </ul>

        <p><strong>การรักษาความปลอดภัยของข้อมูล</strong></p>
        <p>ระบบมีมาตรการรักษาความปลอดภัยของข้อมูลส่วนบุคคลของท่านอย่างเข้มงวด เพื่อป้องกันการเข้าถึง การใช้ หรือการเปิดเผยข้อมูลโดยไม่ได้รับอนุญาต</p>

        <p><strong>การเปิดเผยข้อมูลส่วนบุคคล</strong></p>
        <p>ระบบจะไม่เปิดเผยข้อมูลส่วนบุคคลของท่านแก่บุคคลภายนอก เว้นแต่จะได้รับความยินยอมจากท่าน หรือเป็นไปตามที่กฎหมายกำหนด</p>
        
        <p>โดยการคลิกปุ่ม <strong>"ยอมรับ"</strong> ด้านล่างนี้ ท่านรับทราบและยินยอมให้ระบบเก็บรวบรวม ใช้ และเปิดเผยข้อมูลส่วนบุคคลของท่านตามวัตถุประสงค์ที่ระบุไว้ในคำประกาศนี้</p>
    """)

    # Render UI
    st.markdown(f"""
    <div class="pdpa-card">
        <div class="pdpa-header">
            คำประกาศเกี่ยวกับความเป็นส่วนตัว (Privacy Notice)
        </div>
        <div class="pdpa-content">
            {content_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ส่วน Action (Checkbox & Button)
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.write("")
        agree = st.checkbox("ข้าพเจ้าได้อ่านและยอมรับคำประกาศเกี่ยวกับความเป็นส่วนตัวข้างต้น")
        
        # ใช้ session_state เพื่อป้องกันการ refresh แล้วค่าหาย
        if st.button("ยอมรับและเข้าใช้งาน", type="primary", use_container_width=True, disabled=not agree):
            st.session_state['pdpa_accepted'] = True
            st.rerun()
