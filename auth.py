import streamlit as st
import pandas as pd
import os
import base64
import textwrap

# --- Helper Functions ---
def clean_string(val):
    if pd.isna(val): return ""
    return str(val).strip()

def normalize_cid(val):
    """ทำความสะอาดเลขบัตรประชาชน (13 หลักล้วน)"""
    if pd.isna(val): return ""
    s = str(val).strip().replace("-", "").replace(" ", "").replace("'", "").replace('"', "")
    if "E" in s or "e" in s:
        try: s = str(int(float(s)))
        except: pass
    if s.endswith(".0"): s = s[:-2]
    return s

def normalize_db_name_field(full_name_str):
    clean_val = clean_string(full_name_str)
    parts = clean_val.split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    elif len(parts) == 1: return parts[0], ""
    return "", ""

def get_image_base64(path):
    try:
        if not os.path.exists(path): return None
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception: return None

def check_user_credentials(df, fname, lname, cid):
    i_fname = clean_string(fname)
    i_lname = clean_string(lname)
    i_id = normalize_cid(cid)

    if i_fname.lower() == "admin":
        return True, "เข้าสู่ระบบผู้ดูแลระบบ", {"role": "admin", "name": "Administrator"}

    if not i_fname or not i_lname or not i_id:
        return False, "กรุณากรอกข้อมูลให้ครบทุกช่อง", None

    if len(i_id) != 13:
        return False, "เลขบัตรประชาชนต้องมี 13 หลัก", None

    # ค้นหาในคอลัมน์เลขบัตรประชาชน
    user_match = df[df['เลขบัตรประชาชน'].astype(str) == i_id]

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
    # CSS ปรับแต่งปุ่มและฟอนต์ (ลบส่วนที่ครอบ div ออกเพื่อความเสถียร)
    login_style = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, div, span, input, button, label, select, option {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        .login-header { 
            text-align: center; 
            color: #00B900; 
            font-weight: bold; 
            font-size: 1.8rem; 
            margin-bottom: 1rem; 
        }
        /* ปรับปุ่มให้เต็มความกว้างและสีเขียว */
        div.stButton > button {
            width: 100%;
            background-color: #00B900 !important;
            color: white !important;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            border: none;
            padding: 0.5rem 1rem;
        }
        div.stButton > button:hover {
            background-color: #009900 !important;
            color: white !important;
        }
        .logo-img {
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 120px;
            margin-bottom: 20px;
        }
    </style>
    """
    st.markdown(login_style, unsafe_allow_html=True)

    # จัด layout ให้อยู่ตรงกลาง (ใช้ columns แทน div wrapper)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # แสดงโลโก้
        st.markdown(
            f"<img src='https://i.postimg.cc/MGxD3yWn/fce5f6c4-b813-48cc-bf40-393032a7eb6d.png' class='logo-img'>", 
            unsafe_allow_html=True
        )
        
        st.markdown("<h2 class='login-header'>ลงทะเบียน / เข้าสู่ระบบ</h2>", unsafe_allow_html=True)
        
        # ใช้ st.container แบบมีขอบ (ถ้า streamlit version รองรับ) หรือแบบธรรมดา
        with st.container(border=True):
            with st.form("login_form"):
                st.markdown("กรุณากรอกข้อมูลเพื่อยืนยันตัวตน")
                fname = st.text_input("ชื่อ (ไม่ต้องระบุคำนำหน้า)", placeholder="เช่น สมชาย")
                lname = st.text_input("นามสกุล", placeholder="เช่น ใจดี")
                cid = st.text_input("เลขบัตรประชาชน (13 หลัก)", max_chars=13, placeholder="xxxxxxxxxxxxx")
                
                submitted = st.form_submit_button("เข้าสู่ระบบ")

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
            st.rerun()
        else:
            st.error(msg)

def pdpa_consent_page():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, div, span, input, button, label, li, ul {
            font-family: 'Sarabun', sans-serif !important;
        }

        .pdpa-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin: 10px 0; color: #333; }
        .pdpa-content { background-color: white; padding: 15px; border-radius: 5px; height: 300px; overflow-y: auto; border: 1px solid #dee2e6; margin-bottom: 15px; font-size: 14px; color: #333; }

        /* ปรับสีปุ่มยอมรับให้เป็นสีเขียว */
        div.stButton > button {
            background-color: #00B900 !important;
            color: white !important;
            border: none !important;
        }
        div.stButton > button:hover {
            background-color: #009900 !important;
            color: white !important;
        }
        div.stButton > button:active {
            background-color: #007900 !important;
            color: white !important;
        }
        /* สำหรับปุ่มที่ Disabled (ยังไม่ติ๊กถูก) */
        div.stButton > button:disabled {
            background-color: #e0e0e0 !important;
            color: #a0a0a0 !important;
            cursor: not-allowed;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### นโยบายคุ้มครองข้อมูลส่วนบุคคล")
    
    html_content = """
    <div class="pdpa-card">
        <div class="pdpa-content">
            <strong>โรงพยาบาลสันทราย</strong> ให้ความสำคัญกับการคุ้มครองข้อมูลส่วนบุคคลของท่าน เพื่อให้ท่านมั่นใจได้ว่าข้อมูลส่วนบุคคลของท่านที่เราได้รับจะถูกนำไปใช้ตรงตามความต้องการของท่านและถูกต้องตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล<br><br>
            <strong>วัตถุประสงค์ในการเก็บรวบรวม ใช้ หรือเปิดเผยข้อมูลส่วนบุคคล</strong><br>
            - เพื่อใช้ในการระบุและยืนยันตัวตนของท่านก่อนเข้าใช้งานระบบรายงานผลตรวจสุขภาพ<br>
            - เพื่อแสดงผลการตรวจสุขภาพและข้อมูลที่เกี่ยวข้องซึ่งเป็นข้อมูลส่วนบุคคลที่มีความอ่อนไหว<br>
            - เพื่อการวิเคราะห์ข้อมูลในภาพรวมสำหรับการพัฒนาคุณภาพบริการ (โดยไม่ระบุตัวตน)<br><br>
            <strong>การรักษาความปลอดภัยของข้อมูล</strong><br>
            ระบบมีมาตรการรักษาความปลอดภัยของข้อมูลส่วนบุคคลของท่านอย่างเข้มงวด เพื่อป้องกันการเข้าถึง การใช้ หรือการเปิดเผยข้อมูลโดยไม่ได้รับอนุญาต<br><br>
            <strong>การเปิดเผยข้อมูลส่วนบุคคล</strong><br>
            ระบบจะไม่เปิดเผยข้อมูลส่วนบุคคลของท่านแก่บุคคลภายนอก เว้นแต่จะได้รับความยินยอมจากท่าน หรือเป็นไปตามที่กฎหมายกำหนด<br><br>
            <em>โดยการคลิกปุ่ม "ยอมรับ" ด้านล่างนี้ ท่านรับทราบและยินยอมให้ระบบเก็บรวบรวม ใช้ และเปิดเผยข้อมูลส่วนบุคคลของท่านตามวัตถุประสงค์ที่ระบุไว้ในคำประกาศนี้</em>
        </div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

    agree = st.checkbox("ข้าพเจ้าได้อ่านและยอมรับนโยบายข้างต้น")
    if st.button("ยอมรับและเข้าใช้งาน", type="primary", use_container_width=True, disabled=not agree):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
