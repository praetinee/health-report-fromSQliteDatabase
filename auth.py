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
        # ใช้ HTML เพื่อจัดแต่งหัวข้อใน Form ให้ดูดีขึ้น (รองรับ Dark Mode)
        st.markdown("""
            <div style='text-align: left; margin-bottom: 20px;'>
                <h3 style='margin: 0; color: var(--text-color); font-weight: 600;'>เข้าสู่ระบบ</h3>
                <p style='margin: 0; font-size: 0.9rem; opacity: 0.8;'>กรุณากรอกข้อมูลเพื่อยืนยันตัวตน</p>
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

        # ปุ่ม Submit (Style จะถูกจัดการด้วย CSS ด้านล่าง)
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
    
    # --- CSS Injection for Responsive & Themed Design ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        
        /* Global Font Settings */
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        /* --- Responsive Container Layout --- */
        .block-container {
            padding-top: 4rem !important;
            max-width: 550px; /* Desktop width constraint */
            margin: 0 auto;
        }

        /* Mobile Adjustments */
        @media (max-width: 576px) {
            .block-container {
                padding-top: 2rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                max-width: 100% !important;
            }
            [data-testid="stForm"] {
                padding: 1.5rem !important; /* Reduce padding inside card on mobile */
            }
            .auth-header img {
                max-width: 80% !important; /* Slightly smaller logo on mobile */
            }
        }

        /* --- Adaptive Card Design (Theme Aware) --- */
        [data-testid="stForm"] {
            background-color: var(--secondary-background-color);
            padding: 2.5rem;
            border-radius: 16px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.08); 
            border: 1px solid rgba(128, 128, 128, 0.1); /* Subtle border for definition */
        }

        /* --- Input Fields Styling --- */
        .stTextInput input {
            border-radius: 8px;
            padding: 10px 12px;
            border: 1px solid var(--secondary-background-color); /* Matches background initially */
            background-color: var(--background-color); /* Input bg matches main bg */
            color: var(--text-color) !important;
            transition: all 0.3s;
        }
        /* Add a subtle border when input is not focused to distinguish it */
        .stTextInput input {
            border: 1px solid rgba(128, 128, 128, 0.2);
        }
        .stTextInput input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(0, 121, 107, 0.1);
        }
        
        /* --- Header & Logo --- */
        .auth-header {
            text-align: center;
            padding-bottom: 2rem;
        }
        .auth-header img {
            margin-bottom: 1.5rem;
            border-radius: 12px;
            height: auto;
        }

        /* --- BUTTON STYLE (Clean/White Theme - Adaptive) --- */
        /* Uses var(--background-color) to ensure it looks 'Clean' (matching page bg) 
           in both Light and Dark modes.
           Text color uses var(--text-color) to automatically switch between Black/White.
        */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"] {
            background-color: var(--background-color) !important; 
            color: var(--text-color) !important;
            border: 1px solid rgba(128, 128, 128, 0.3) !important; /* Subtle border */
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            height: 3rem !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease !important;
        }

        /* Hover State */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"]:hover {
            background-color: var(--secondary-background-color) !important;
            border-color: var(--primary-color) !important; /* Highlight border color on hover */
            color: var(--primary-color) !important; /* Highlight text on hover */
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
        }

        /* Active/Click State */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"]:active {
            transform: translateY(0px);
            opacity: 0.8;
        }

        /* Focus State */
        [data-testid="stForm"] [data-testid="baseButton-secondaryFormSubmit"]:focus {
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 0 0.2rem rgba(0, 121, 107, 0.2) !important;
        }
        
        /* --- Password Toggle Button (Adaptive) --- */
        [data-testid="stTextInput"] button {
            color: var(--text-color) !important;
            opacity: 0.6;
            border: none !important;
            background-color: transparent !important;
        }
        [data-testid="stTextInput"] button:hover {
            opacity: 1;
            color: var(--primary-color) !important;
        }

        /* Override generic button text color if needed */
        [data-testid="stForm"] button p {
            color: inherit !important;
        }
        
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("""
        <div class="auth-header">
          <img src="https://i.postimg.cc/tJd4DZSY/image.png" alt="Logo" width="300" style="max-width: 100%; height: auto;">
          <h2 style='text-align: center; margin-top: 0px; margin-bottom: 5px; font-weight: 700; color: var(--text-color); letter-spacing: -0.5px;'>ระบบรายงานผลตรวจสุขภาพ</h2>
          <p style='text-align: center; opacity: 0.7; margin-top: 0px; margin-bottom: 20px; font-weight: 400;'>กลุ่มงานอาชีวเวชกรรม</p>
        </div>
        """, unsafe_allow_html=True)

        display_primary_login(df)
        
        # Footer Updated with requested text
        st.markdown("""
        <div style='text-align: center; margin-top: 4rem; opacity: 0.6; font-size: 0.75rem; letter-spacing: 0.5px; line-height: 1.6;'>
            © 2025 Health Data Reporting System. All rights reserved.<br>
            <span style='opacity: 0.8; font-weight: 500;'>Realized by P.P. for Occupational Health Dept.</span>
        </div>
        """, unsafe_allow_html=True)

def pdpa_consent_page():
    """แสดงหน้าสำหรับให้ความยินยอม PDPA"""
    st.set_page_config(page_title="PDPA Consent", layout="centered")
    
    # --- Responsive PDPA CSS ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div, li, ul {
            font-family: 'Sarabun', sans-serif !important;
        }
        
        .block-container {
            padding-top: 3rem !important;
        }

        @media (max-width: 576px) {
             div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
                padding: 1.5rem 1.5rem !important;
             }
             h2 { font-size: 1.5rem !important; }
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
        
        /* Button style for consent */
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
