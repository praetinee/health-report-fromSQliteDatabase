import streamlit as st
import pandas as pd
import re
import random

# --- Helper Functions ---

def is_empty(val):
    """ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่"""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_name(name):
    """
    จัดการการเว้นวรรคในชื่อ-นามสกุลที่ไม่สม่ำเสมอ
    โดยการตัดช่องว่างทั้งหมดออก เพื่อให้การค้นหาแม่นยำที่สุด
    เช่น "สมชาย  ใจดี" -> "สมชายใจดี"
    """
    if is_empty(name):
        return ""
    # ลบทุกช่องว่าง (Whitespace) ออกจาก string
    return re.sub(r'\s+', '', str(name).strip())

def display_primary_login(df):
    """แสดงหน้าจอเข้าสู่ระบบหลัก (ชื่อ-สกุล + เลขบัตรประชาชน หรือ HN)"""
    
    # --- ใช้ Form เพื่อให้รองรับการกด Enter และ Tab ---
    with st.form(key='login_form'):
        # ใช้ HTML เพื่อจัดแต่งหัวข้อใน Form ให้ดูดีขึ้น
        st.markdown("""
            <div style='text-align: left; margin-bottom: 20px;'>
                <h3 style='margin: 0; color: var(--text-color); font-weight: 600;'>เข้าสู่ระบบ</h3>
                <p style='margin: 0; font-size: 0.9rem; color: gray;'>กรุณากรอกข้อมูลเพื่อยืนยันตัวตน</p>
            </div>
        """, unsafe_allow_html=True)
        
        # input fields
        name_input = st.text_input("ชื่อ-นามสกุล", key="login_name", placeholder="ระบุชื่อ-นามสกุลของท่าน")
        
        id_input = st.text_input(
            "รหัสผ่าน", 
            key="login_id", 
            help="กรอกเลขบัตรประชาชน 13 หลัก หรือ หมายเลข HN ของท่าน", 
            placeholder="เลขบัตรประชาชน 13 หลัก หรือ HN", 
            type="password"
        )

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        # ใช้ปุ่มธรรมดา (Secondary) แล้วแต่ง CSS ให้เป็นแบบ Outline
        submit_button = st.form_submit_button("ลงชื่อเข้าใช้งาน", use_container_width=True)

    if submit_button:
        if name_input == "admin" and id_input == "admin":
            st.session_state['authenticated'] = True
            st.session_state['is_admin'] = True
            st.session_state['user_name'] = "Admin"
            st.success("ลงชื่อเข้าใช้สำเร็จ (Admin)!")
            st.rerun()

        elif name_input and id_input: 
            # Normalize ชื่อที่กรอกมา (ตัดเว้นวรรคทิ้งหมด)
            normalized_input_name = normalize_name(name_input)
            input_password = str(id_input).strip()
            
            # 1. ค้นหาผู้ใช้ด้วยชื่อก่อน (Find user by name first)
            # โดยเทียบกับชื่อใน DB ที่ถูก Normalize แล้วเช่นกัน
            name_records = df[df['ชื่อ-สกุล'].apply(normalize_name) == normalized_input_name]
            
            if not name_records.empty:
                # 2. ถ้าเจอชื่อ, รวบรวม HN และ เลขบัตรประชาชน ทั้งหมดที่เชื่อมโยงกับชื่อนี้
                all_hns_for_name = name_records['HN'].astype(str).str.strip().unique()
                valid_ids_series = name_records[~name_records['เลขบัตรประชาชน'].apply(is_empty)]['เลขบัตรประชาชน'].astype(str).str.strip()
                all_ids_for_name = valid_ids_series.unique()
                
                # 3. ตรวจสอบว่า id_input ที่กรอกมา ตรงกับ HN หรือ เลขบัตร อันใดอันหนึ่งหรือไม่
                is_hn_match = input_password in all_hns_for_name
                is_id_match = input_password in all_ids_for_name
                
                if is_hn_match or is_id_match:
                    st.session_state['authenticated'] = True
                    st.session_state['is_admin'] = False
                    st.session_state['user_hn'] = name_records.iloc[0]['HN'] 
                    st.session_state['user_name'] = name_records.iloc[0]['ชื่อ-สกุล']
                    st.success("ลงชื่อเข้าใช้สำเร็จ!")
                    st.rerun()
                else:
                    st.error("ชื่อ-นามสกุล หรือ รหัสผ่าน (เลขบัตร/HN) ไม่ถูกต้อง")
            else:
                st.error("ชื่อ-นามสกุล หรือ รหัสผ่าน (เลขบัตร/HN) ไม่ถูกต้อง")
        else:
            st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")


def authentication_flow(df):
    """จัดการ Flow การเข้าสู่ระบบทั้งหมด"""
    st.set_page_config(page_title="ลงชื่อเข้าใช้ | ระบบรายงานผลสุขภาพ", layout="centered", page_icon="🏥")
    
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        /* จัดระยะห่างด้านบนใหม่ ให้ดูโปร่งขึ้น */
        .block-container {
            padding-top: 4rem !important;
            max_width: 550px; /* จำกัดความกว้างให้พอดีสายตา */
        }

        /* --- CARD DESIGN FOR LOGIN FORM --- */
        [data-testid="stForm"] {
            background-color: var(--secondary-background-color);
            padding: 2.5rem;
            border-radius: 16px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.08); 
            border: 1px solid rgba(0,0,0,0.05);
        }

        /* ปรับแต่ง Input Fields */
        .stTextInput input {
            border-radius: 8px;
            padding: 10px 12px;
            border: 1px solid #e0e0e0;
            transition: border-color 0.3s;
            color: #333 !important; /* บังคับสีตัวอักษรให้เป็นสีเข้มตามธีม */
        }
        .stTextInput input:focus {
            border-color: #999;
            box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.05);
        }
        
        /* ปรับแต่ง Header ส่วน Logo */
        .auth-header {
            text-align: center;
            padding-bottom: 2rem;
        }
        .auth-header img {
            margin-bottom: 1.5rem;
            border-radius: 12px;
        }

        /* --- BUTTON STYLE (Clean/White Theme) --- */
        /* ปรับแก้: กรอบขาว ตัวหนังสือสีเดียวกับ Input (เทาเข้ม/ดำ) */
        
        /* เล็งเป้าไปที่ปุ่ม Submit ใน Form */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"] {
            background-color: #ffffff !important; /* พื้นหลังขาว */
            color: #333333 !important; /* ตัวหนังสือสีเดียวกับ Input */
            border: 1px solid #ffffff !important; /* กรอบสีขาว */
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            height: 3rem !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important; /* เงาบางๆ ให้ปุ่มลอยขึ้นมานิดหน่อย */
            transition: all 0.2s ease !important;
        }

        /* Hover State */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"]:hover {
            background-color: #f9f9f9 !important;
            color: #000000 !important;
            border-color: #f0f0f0 !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
        }

        /* Active/Click State */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"]:active {
            background-color: #e0e0e0 !important;
            border-color: #e0e0e0 !important;
            transform: translateY(0px);
        }

        /* Focus State */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"]:focus {
            border-color: #ccc !important;
            box-shadow: 0 0 0 0.2rem rgba(0, 0, 0, 0.1) !important;
        }
        
        /* --- Password Visibility Toggle Button Theme --- */
        /* ปรับปุ่มลูกตา (Show/Hide Password) ให้เป็นธีมเดียวกับ Input */
        [data-testid="stTextInput"] button {
            color: #666 !important; /* สีเทากลางๆ (ธีมเดียวกับ Input) */
            border: none !important;
            background-color: transparent !important;
        }
        [data-testid="stTextInput"] button:hover {
            color: #333 !important; /* เข้มขึ้นเมื่อ Hover */
            background-color: transparent !important;
        }

        /* Override text color inside button (just in case) */
        [data-testid="stForm"] button p {
            color: inherit !important;
        }
        /* --- END OF FIX --- */
        
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div class="auth-header">
          <img src="https://i.postimg.cc/tJd4DZSY/image.png" alt="Logo" width="300" style="max-width: 100%; height: auto;">
          <h2 style='text-align: center; margin-top: 0px; margin-bottom: 5px; font-weight: 700; color: var(--text-color); letter-spacing: -0.5px;'>ระบบรายงานผลตรวจสุขภาพ</h2>
          <p style='text-align: center; color: #666; margin-top: 0px; margin-bottom: 20px; font-weight: 400;'>กลุ่มงานอาชีวเวชกรรม</p>
        </div>
        """, unsafe_allow_html=True)

        display_primary_login(df)
        
        # Footer Updated Text
        st.markdown("""
        <div style='text-align: center; margin-top: 4rem; color: #bbb; font-size: 0.7rem; letter-spacing: 0.5px; line-height: 1.6;'>
            © 2025 Health Data Reporting System. All rights reserved.<br>
            <span style='color: #999;'>Realized by P.P. for Occupational Health Dept.</span>
        </div>
        """, unsafe_allow_html=True)

def pdpa_consent_page():
    """แสดงหน้าสำหรับให้ความยินยอม PDPA"""
    st.set_page_config(page_title="PDPA Consent", layout="centered")
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div, li, ul {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        .block-container {
            padding-top: 3rem !important;
        }

        /* Style the container for consent */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
             background-color: var(--background-color);
             color: var(--text-color);
             padding: 2rem 3rem; 
             border-radius: 10px;
             box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        h2 { text-align: center; color: var(--text-color); }
        .consent-text {
            height: 300px; 
            overflow-y: scroll; 
            border: 1px solid var(--border-color);
            padding: 1rem; 
            border-radius: 5px; 
            background-color: var(--secondary-background-color);
            margin-bottom: 1.5rem; 
            text-align: left;
            color: var(--text-color);
        }
        
        /* Reuse button style for consent page - Keep this one FILLED GREEN for emphasis */
        .stButton > button {
            background-color: #00796B !important;
            color: white !important;
            border: 1px solid #00796B !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            width: 100%;
            height: 3rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15) !important;
        }
        .stButton > button:hover {
            background-color: #00695C !important;
            border-color: #00695C !important;
            transform: translateY(-1px);
        }
        .stButton > button:active {
            background-color: #004D40 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<h2>ข้อตกลงและเงื่อนไขการใช้งาน (PDPA Consent)</h2>", unsafe_allow_html=True)
        st.markdown("""
        <div class="consent-text">
            <h4>คำประกาศเกี่ยวกับความเป็นส่วนตัว (Privacy Notice)</h4>
            <p><strong>ระบบรายงานผลตรวจสุขภาพ</strong> ให้ความสำคัญกับการคุ้มครองข้อมูลส่วนบุคคลของท่าน เพื่อให้ท่านมั่นใจได้ว่าข้อมูลส่วนบุคคลของท่านที่เราได้รับจะถูกนำไปใช้ตรงตามความต้องการของท่านและถูกต้องตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล</p>
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
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("ยอมรับและดำเนินการต่อ (Accept & Continue)"):
            st.session_state['pdpa_accepted'] = True
            st.rerun()
