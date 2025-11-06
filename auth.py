import streamlit as st
import pandas as pd
import re
import random

# --- Helper Functions ---

def is_empty(val):
    """ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่"""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
    """จัดการการเว้นวรรคในชื่อ-นามสกุลที่ไม่สม่ำเสมอ"""
    if is_empty(name):
        return ""
    return re.sub(r'\s+', '', str(name).strip())

# --- START OF CHANGE: 'generate_questions' function removed ---
# --- END OF CHANGE ---


def display_primary_login(df):
    """แสดงหน้าจอเข้าสู่ระบบหลัก (ชื่อ-สกุล + เลขบัตรประชาชน หรือ HN)"""
    st.markdown("<h4>เข้าสู่ระบบ</h4>", unsafe_allow_html=True)
    name_input = st.text_input("ชื่อ-นามสกุล", key="login_name", label_visibility="collapsed", placeholder="ชื่อ-นามสกุล")
    
    id_input = st.text_input(
        "รหัสผ่าน (เลขบัตรประชาชน 13 หลัก หรือ HN)", 
        key="login_id", 
        help="กรอกเลขบัตรประชาชน 13 หลัก หรือ หมายเลข HN ของท่าน", 
        label_visibility="collapsed", 
        placeholder="รหัสผ่าน (เลขบัตรประชาชน 13 หลัก หรือ HN)", 
        type="password"
    )

    # --- START OF CHANGE: Removed columns and "Forgot Password" button ---
    if st.button("ลงชื่อเข้าใช้", use_container_width=True, type="primary"):
        
        # --- START OF CHANGE: Add Admin login check ---
        if name_input == "admin" and id_input == "admin":
            st.session_state['authenticated'] = True
            st.session_state['is_admin'] = True
            st.session_state['user_name'] = "Admin"
            st.success("ลงชื่อเข้าใช้สำเร็จ (Admin)!")
            st.rerun()
        # --- END OF CHANGE ---

        elif name_input and id_input: # Keep existing user logic in elif
            normalized_input_name = normalize_name(name_input)
            input_password = str(id_input).strip()
            
            # ค้นหาผู้ใช้โดยใช้ 'เลขบัตรประชาชน' หรือ 'HN'
            user_record = df[
                (df['ชื่อ-สกุล'].apply(normalize_name) == normalized_input_name) &
                (
                    (df['เลขบัตรประชาชน'].astype(str) == input_password) |
                    (df['HN'].astype(str) == input_password)
                )
            ]
            
            if not user_record.empty:
                st.session_state['authenticated'] = True
                st.session_state['is_admin'] = False # Set user as not admin
                # ยังคงเก็บ HN ไว้ใน session เพื่อให้ส่วนที่เหลือของแอปทำงานได้ตามปกติ
                st.session_state['user_hn'] = user_record.iloc[0]['HN'] 
                st.session_state['user_name'] = user_record.iloc[0]['ชื่อ-สกุล']
                st.success("ลงชื่อเข้าใช้สำเร็จ!")
                st.rerun()
            else:
                st.error("ชื่อ-นามสกุล หรือ รหัสผ่าน (เลขบัตร/HN) ไม่ถูกต้อง")
        else:
            st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")
    # --- END OF CHANGE ---

# --- START OF CHANGE: 'display_question_verification' function removed ---
# --- END OF CHANGE ---


def authentication_flow(df):
    """จัดการ Flow การเข้าสู่ระบบทั้งหมด"""
    st.set_page_config(page_title="ลงชื่อเข้าใช้", layout="centered")
    
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        /* Center the main block content */
        .block-container {
            padding-top: 3rem !important;
        }

        /* Style the container for login */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            background-color: var(--background-color); /* Changed from white */
            color: var(--text-color); /* Added */
            padding: 2rem 2.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .auth-header {
            text-align: center;
            padding-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div class="auth-header">
          <img src="https://i.postimg.cc/tJd4DZSY/image.png" alt="Logo" width="350">
          <h2 style='text-align: center; margin-top: 10px; margin-bottom: 0px;'>ระบบรายงานผลตรวจสุขภาพ</h2>
          <p style='text-align: center; color: #555; margin-top: 5px; margin-bottom: 20px;'>กลุ่มงานอาชีวเวชกรรม รพ.สันทราย</p>
        </div>
        """, unsafe_allow_html=True)

        # --- START OF CHANGE: Removed auth_step logic ---
        # No more 'auth_step' needed, just show the primary login
        display_primary_login(df)
        # --- END OF CHANGE ---

def pdpa_consent_page():
    """แสดงหน้าสำหรับให้ความยินยอม PDPA"""
    st.set_page_config(page_title="PDPA Consent", layout="centered")
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div, li, ul {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        .block-container {
            padding-top: 3rem !important;
        }

        /* --- START OF CHANGE: Make theme-adaptive --- */
        /* Style the container for consent */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
             background-color: var(--background-color); /* Was white */
             color: var(--text-color); /* Added */
             padding: 2rem 3rem; 
             border-radius: 10px;
             box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        h2 { text-align: center; color: var(--text-color); } /* Added text color */
        .consent-text {
            height: 300px; 
            overflow-y: scroll; 
            border: 1px solid var(--border-color); /* Was #ddd */
            padding: 1rem; 
            border-radius: 5px; 
            background-color: var(--secondary-background-color); /* Was #fafafa */
            margin-bottom: 1.5rem; 
            text-align: left;
            color: var(--text-color); /* Added */
        }
        /* --- END OF CHANGE --- */
        .stButton>button { width: 100%; height: 3rem; }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<h2>ข้อตกลงและเงื่อนไขการใช้งาน (PDPA Consent)</h2>", unsafe_allow_html=True)
        st.markdown("""
        <div class="consent-text">
            <h4>คำประกาศเกี่ยวกับความเป็นส่วนตัว (Privacy Notice)</h4>
            <p><strong>โรงพยาบาลสันทราย</strong> ให้ความสำคัญกับการคุ้มครองข้อมูลส่วนบุคคลของท่าน เพื่อให้ท่านมั่นใจได้ว่าข้อมูลส่วนบุคคลของท่านที่เราได้รับจะถูกนำไปใช้ตรงตามความต้องการของท่านและถูกต้องตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล</p>
            <p><strong>วัตถุประสงค์ในการเก็บรวบรวม ใช้ หรือเปิดเผยข้อมูลส่วนบุคคล</strong></p>
            <ul>
                <li>เพื่อใช้ในการระบุและยืนยันตัวตนของท่านก่อนเข้าใช้งานระบบรายงานผลตรวจสุขภาพ</li>
                <li>เพื่อแสดงผลการตรวจสุขภาพและข้อมูลที่เกี่ยวข้องซึ่งเป็นข้อมูลส่วนบุคคลที่มีความอ่อนไหว</li>
                <li>เพื่อการวิเคราะห์ข้อมูลในภาพรวมสำหรับการพัฒนาคุณภาพบริการของโรงพยาบาล (โดยไม่ระบุตัวตน)</li>
            </ul>
            <p><strong>การรักษาความปลอดภัยของข้อมูล</strong></p>
            <p>โรงพยาบาลมีมาตรการรักษาความปลอดภัยของข้อมูลส่วนบุคคลของท่านอย่างเข้มงวด เพื่อป้องกันการเข้าถึง การใช้ หรือการเปิดเผยข้อมูลโดยไม่ได้รับอนุญาต</p>
            <p><strong>การเปิดเผยข้อมูลส่วนบุคคล</strong></p>
            <p>โรงพยาบาลจะไม่เปิดเผยข้อมูลส่วนบุคคลของท่านแก่บุคคลภายนอก เว้นแต่จะได้รับความยินยอมจากท่าน หรือเป็นไปตามที่กฎหมายกำหนด</p>
            <p>โดยการคลิกปุ่ม <strong>"ยอมรับ"</strong> ด้านล่างนี้ ท่านรับทราบและยินยอมให้โรงพยาบาลเก็บรวบรวม ใช้ และเปิดเผยข้อมูลส่วนบุคคลของท่านตามวัตถุประสงค์ที่ระบุไว้ในคำประกาศนี้</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("ยอมรับและดำเนินการต่อ (Accept & Continue)"):
            st.session_state['pdpa_accepted'] = True
            st.rerun()

