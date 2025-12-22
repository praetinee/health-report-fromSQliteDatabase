import streamlit as st
import pandas as pd
from utils import normalize_name

def authentication_flow(df):
    st.title("ระบบรายงานผลตรวจสุขภาพ")
    
    with st.form("login_form"):
        st.subheader("เข้าสู่ระบบ")
        
        # User Inputs
        name_input = st.text_input("ชื่อ-นามสกุล (ไม่ต้องระบุคำนำหน้า)", placeholder="เช่น สมชาย ใจดี")
        hn_input = st.text_input("HN (เลขประจำตัวผู้ป่วย)", placeholder="ระบุเลข HN")
        
        submitted = st.form_submit_button("เข้าสู่ระบบ")
        
        if submitted:
            # 1. Backdoor for Admin (Simple "admin" check)
            if name_input.strip().lower() == "admin":
                st.session_state['authenticated'] = True
                st.session_state['user_name'] = "Administrator"
                st.session_state['user_hn'] = "ADMIN"
                st.session_state['is_admin'] = True
                st.session_state['pdpa_accepted'] = True # Skip PDPA for admin
                st.success("เข้าสู่ระบบ Admin สำเร็จ")
                st.rerun()
                return

            # 2. Normal User Login Logic
            if not name_input or not hn_input:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                return

            # Normalize inputs
            search_name = normalize_name(name_input)
            search_hn = hn_input.strip()

            # Filter DataFrame
            # Check HN first (more specific)
            user_match = df[df['HN'].astype(str) == search_hn]
            
            if not user_match.empty:
                # Check Name match (fuzzy or exact)
                # We'll take the first match for HN, then check name
                row = user_match.iloc[0]
                db_name = normalize_name(row['ชื่อ-สกุล'])
                
                # Loose matching: check if input name is part of DB name
                if search_name in db_name:
                    st.session_state['authenticated'] = True
                    st.session_state['user_name'] = row['ชื่อ-สกุล']
                    st.session_state['user_hn'] = row['HN']
                    st.session_state['is_admin'] = False
                    st.success(f"ยินดีต้อนรับ คุณ{row['ชื่อ-สกุล']}")
                    st.rerun()
                else:
                    st.error("ชื่อ-นามสกุล ไม่ตรงกับ HN ที่ระบุ")
            else:
                st.error("ไม่พบเลข HN นี้ในระบบ")

def pdpa_consent_page():
    st.title("ข้อตกลงการใช้งาน (PDPA)")
    st.markdown("""
    **ความยินยอมในการเปิดเผยข้อมูลส่วนบุคคล**
    
    ข้าพเจ้ายินยอมให้โรงพยาบาล... เปิดเผยข้อมูลผลการตรวจสุขภาพ...
    (เนื้อหา PDPA สมมติ...)
    """)
    
    if st.button("ยอมรับเงื่อนไข"):
        st.session_state['pdpa_accepted'] = True
        st.rerun()
