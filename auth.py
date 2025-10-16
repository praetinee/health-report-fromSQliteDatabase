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

def generate_questions(user_profile, num_questions=3):
    """สร้างชุดคำถามยืนยันตัวตนแบบสุ่มจากข้อมูลผู้ใช้"""
    question_pool = []
    
    # 1. คำถามเลขบัตรประชาชน (ถ้ามีข้อมูล)
    id_card = user_profile.get('เลขบัตรประชาชน')
    if not is_empty(id_card):
        question_pool.append({
            'type': 'text_input', 'key': 'id_card',
            'label': 'กรุณากรอก **เลขบัตรประชาชน** 13 หลักของท่าน',
            'answer': str(id_card).strip()
        })

    # 2. คำถามน้ำหนักล่าสุด (ถ้ามีข้อมูล)
    weight = user_profile.get('น้ำหนัก')
    if not is_empty(weight):
        try:
            question_pool.append({
                'type': 'number_input', 'key': 'weight',
                'label': 'จากผลตรวจสุขภาพกับกลุ่มงานอาชีวเวชกรรมครั้งล่าสุด **น้ำหนัก** ของท่านคือเท่าไหร่ (กรอกเฉพาะตัวเลข)?',
                'answer': float(weight)
            })
        except (ValueError, TypeError):
            pass # ไม่เพิ่มคำถามถ้าแปลงเป็น float ไม่ได้

    # 3. คำถามหน่วยงาน (ถ้ามีข้อมูล)
    department = user_profile.get('หน่วยงาน')
    if not is_empty(department):
        question_pool.append({
            'type': 'text_input', 'key': 'department',
            'label': 'ท่านสังกัด **หน่วยงาน** ใด?',
            'answer': str(department).strip()
        })

    # 4. คำถามประวัติการแพ้ยา (ถ้ามีข้อมูล)
    # หมายเหตุ: สมมติว่าคอลัมน์ชื่อ 'แพ้ยา' หากไม่ใช่ ต้องเปลี่ยนชื่อคอลัมน์ตรงนี้
    drug_allergy = user_profile.get('แพ้ยา') 
    if not is_empty(drug_allergy):
        correct_answer = f"{drug_allergy}"
        # รายการยาหลอก (ควรมีทั้งชื่อไทยและอังกฤษ)
        decoy_drugs = [
            "Paracetamol / พาราเซตามอล", 
            "Aspirin / แอสไพริน", 
            "Ibuprofen / ไอบูโพรเฟน",
            "Amoxicillin / อะมอกซิซิลลิน"
        ]
        options = [correct_answer] + random.sample([d for d in decoy_drugs if d.split(' ')[0].lower() not in correct_answer.lower()], 2)
        options.append("ฉันไม่มีประวัติการแพ้ยา")
        random.shuffle(options)
        
        question_pool.append({
            'type': 'radio', 'key': 'allergy',
            'label': 'ท่านมีประวัติ **การแพ้ยา** ตามที่ระบุไว้ในข้อใด?',
            'options': options,
            'answer': correct_answer
        })
    
    # ถ้าไม่มีประวัติแพ้ยา ให้สร้างคำถามที่คำตอบคือ "ไม่มีประวัติ"
    elif 'แพ้ยา' in user_profile and is_empty(drug_allergy):
        decoy_drugs = ["Paracetamol / พาราเซตามอล", "Aspirin / แอสไพริน", "Ibuprofen / ไอบูโพรเฟน"]
        correct_answer = "ฉันไม่มีประวัติการแพ้ยา"
        options = [correct_answer] + random.sample(decoy_drugs, 2)
        random.shuffle(options)
        question_pool.append({
            'type': 'radio', 'key': 'allergy_none',
            'label': 'ท่านมีประวัติ **การแพ้ยา** ตามที่ระบุไว้ในข้อใด?',
            'options': options,
            'answer': correct_answer
        })

    # สุ่มเลือกคำถามตามจำนวนที่ต้องการ
    if len(question_pool) < num_questions:
        return question_pool # ถ้ามีคำถามไม่พอ ให้ใช้ทั้งหมด
    return random.sample(question_pool, num_questions)


def display_primary_login(df):
    """แสดงหน้าจอเข้าสู่ระบบหลัก (ชื่อ-สกุล + HN)"""
    st.markdown("<h3>เข้าสู่ระบบ</h3>", unsafe_allow_html=True)
    name_input = st.text_input("ชื่อ-นามสกุล", key="login_name", label_visibility="collapsed", placeholder="ชื่อ-นามสกุล")
    hn_input = st.text_input("รหัสผ่าน (HN)", key="login_hn", help="กรอก Hospital Number ของท่าน", label_visibility="collapsed", placeholder="รหัสผ่าน (HN)")

    col1, col2 = st.columns([3, 2])
    with col1:
        if st.button("ลงชื่อเข้าใช้", use_container_width=True, type="primary"):
            if name_input and hn_input:
                normalized_input_name = normalize_name(name_input)
                # ค้นหาผู้ใช้
                user_record = df[
                    (df['ชื่อ-สกุล'].apply(normalize_name) == normalized_input_name) &
                    (df['HN'].astype(str) == str(hn_input).strip())
                ]
                
                if not user_record.empty:
                    st.session_state['authenticated'] = True
                    st.session_state['user_hn'] = user_record.iloc[0]['HN']
                    st.session_state['user_name'] = user_record.iloc[0]['ชื่อ-สกุล']
                    st.success("ลงชื่อเข้าใช้สำเร็จ!")
                    st.rerun()
                else:
                    st.error("ชื่อ-นามสกุล หรือ HN ไม่ถูกต้อง")
            else:
                st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")
    
    with col2:
        if st.button("ลืม HN?", use_container_width=True):
            st.session_state['auth_step'] = 'questions'
            st.rerun()

def display_question_verification(df):
    """แสดงหน้าจอสำหรับตอบคำถามยืนยันตัวตน"""
    st.markdown("<h3>ยืนยันตัวตนเพื่อเข้าสู่ระบบ</h3>", unsafe_allow_html=True)
    
    name_input = st.text_input("กรุณากรอก ชื่อ-นามสกุล ของท่านเพื่อเริ่มต้น", key="verify_name")

    if name_input:
        if 'questions' not in st.session_state or st.session_state.get('current_verify_name') != name_input:
            normalized_input_name = normalize_name(name_input)
            user_records = df[df['ชื่อ-สกุล'].apply(normalize_name) == normalized_input_name]
            
            if not user_records.empty:
                # ใช้ข้อมูลปีล่าสุด
                user_profile = user_records.sort_values('Year', ascending=False).iloc[0].to_dict()
                st.session_state['user_profile_to_verify'] = user_profile
                st.session_state['questions'] = generate_questions(user_profile, num_questions=3)
                st.session_state['current_verify_name'] = name_input
            else:
                st.error("ไม่พบชื่อ-นามสกุลดังกล่าวในระบบ")
                st.session_state.pop('questions', None)
        
        if 'questions' in st.session_state and st.session_state['questions']:
            st.markdown("---")
            st.info("กรุณาตอบคำถามต่อไปนี้ให้ถูกต้องทั้งหมดเพื่อยืนยันตัวตนของท่าน")
            
            answers = {}
            for q in st.session_state['questions']:
                if q['type'] == 'text_input':
                    answers[q['key']] = st.text_input(q['label'], key=f"q_{q['key']}")
                elif q['type'] == 'number_input':
                    answers[q['key']] = st.number_input(q['label'], step=1.0, format="%.1f", key=f"q_{q['key']}")
                elif q['type'] == 'radio':
                    answers[q['key']] = st.radio(q['label'], options=q['options'], key=f"q_{q['key']}", index=None)

            if st.button("ยืนยันคำตอบ", type="primary"):
                all_correct = True
                for q in st.session_state['questions']:
                    user_answer = answers.get(q['key'])
                    correct_answer = q['answer']
                    
                    is_correct = False
                    if q['key'] == 'weight':
                        is_correct = abs(float(user_answer or 0) - correct_answer) <= 1.0
                    elif isinstance(correct_answer, str):
                         is_correct = str(user_answer).strip().lower() == correct_answer.lower()

                    if not is_correct:
                        all_correct = False
                        break
                
                if all_correct:
                    user_profile = st.session_state['user_profile_to_verify']
                    st.session_state['authenticated'] = True
                    st.session_state['user_hn'] = user_profile['HN']
                    st.session_state['user_name'] = user_profile['ชื่อ-สกุล']
                    st.success("การยืนยันตัวตนสำเร็จ!")
                    # ล้าง state ที่ไม่จำเป็น
                    for key in ['questions', 'user_profile_to_verify', 'current_verify_name']:
                        if key in st.session_state: del st.session_state[key]
                    st.rerun()
                else:
                    st.error("ข้อมูลไม่ถูกต้อง กรุณาลองอีกครั้ง")
    
    if st.button("กลับไปหน้าเข้าสู่ระบบหลัก"):
        st.session_state['auth_step'] = 'primary_login'
        st.rerun()


def authentication_flow(df):
    """จัดการ Flow การเข้าสู่ระบบทั้งหมด"""
    st.set_page_config(page_title="ลงชื่อเข้าใช้", layout="centered")
    
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div {
            font-family: 'Sarabun', sans-serif !important;
        }

        .main { background-color: #f0f2f6; }
        
        /* --- START OF CHANGE: Remove vertical centering --- */
        /* .stApp is removed */
        /* --- END OF CHANGE --- */

        .auth-container {
            background-color: white;
            padding: 2rem 3rem;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-width: 500px;
            width: 100%;
            /* --- START OF CHANGE: Add margin auto for horizontal centering --- */
            margin: 5rem auto; 
            /* --- END OF CHANGE --- */
        }
        
        .auth-header {
            text-align: center;
            padding-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="auth-header">
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#00796B" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z"></path>
        <path d="M12 8v8"></path>
        <path d="M8 12h8"></path>
      </svg>
      <h2 style='text-align: center; margin-top: 10px; margin-bottom: 0px;'>ระบบรายงานผลตรวจสุขภาพ</h2>
      <p style='text-align: center; color: #555; margin-top: 5px; margin-bottom: 20px;'>กลุ่มงานอาชีวเวชกรรม รพ.สันทราย</p>
    </div>
    """, unsafe_allow_html=True)

    if 'auth_step' not in st.session_state:
        st.session_state['auth_step'] = 'primary_login'

    if st.session_state['auth_step'] == 'primary_login':
        display_primary_login(df)
    elif st.session_state['auth_step'] == 'questions':
        display_question_verification(df)
    
    st.markdown('</div>', unsafe_allow_html=True)

def pdpa_consent_page():
    """แสดงหน้าสำหรับให้ความยินยอม PDPA"""
    st.set_page_config(page_title="PDPA Consent", layout="centered")
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        
        html, body, [class*="st-"], h1, h2, h3, h4, h5, h6, p, label, button, input, div, li, ul {
            font-family: 'Sarabun', sans-serif !important;
        }

        .main { background-color: #f0f2f6; }
        .consent-container {
            background-color: white; padding: 2rem 3rem; border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 700px;
            margin: 3rem auto;
        }
        h2 { text-align: center; }
        .consent-text {
            height: 300px; overflow-y: scroll; border: 1px solid #ddd;
            padding: 1rem; border-radius: 5px; background-color: #fafafa;
            margin-bottom: 1.5rem; text-align: justify;
        }
        .stButton>button { width: 100%; height: 3rem; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="consent-container">', unsafe_allow_html=True)
    st.markdown("<h2>ข้อตกลงและเงื่อนไขการใช้งาน (PDPA Consent)</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div class="consent-text">
        <h4>คำประกาศเกี่ยวกับความเป็นส่วนตัว (Privacy Notice)</h4>
        <p><strong>โรงพยาบาลสันทราย ("โรงพยาบาล")</strong> ให้ความสำคัญกับการคุ้มครองข้อมูลส่วนบุคคลของท่าน เพื่อให้ท่านมั่นใจได้ว่าข้อมูลส่วนบุคคลของท่านที่เราได้รับจะถูกนำไปใช้ตรงตามความต้องการของท่านและถูกต้องตามกฎหมายคุ้มครองข้อมูลส่วนบุคคล</p>
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
    st.markdown('</div>', unsafe_allow_html=True)

