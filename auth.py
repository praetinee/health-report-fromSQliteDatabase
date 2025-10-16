import streamlit as st

def login_page(df):
    """
    แสดงหน้าล็อกอินและจัดการการยืนยันตัวตนโดยใช้ข้อมูลจาก DataFrame
    Renders the login page and handles authentication using data from the DataFrame.
    """
    st.set_page_config(page_title="Login", layout="centered")
    
    st.markdown("""
    <style>
        .main {
            background-color: #f0f2f6;
        }
        .login-container {
            background-color: white;
            padding: 2rem 3rem;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-width: 450px;
            margin: auto;
            margin-top: 5rem;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        .stButton>button {
            width: 100%;
            background-color: #00796B;
            color: white;
            border-radius: 5px;
            height: 3rem;
        }
        .stButton>button:hover {
            background-color: #00695C;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown("<h1>ระบบรายงานผลตรวจสุขภาพ</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>กรุณาลงชื่อเข้าใช้เพื่อดำเนินการต่อ</p>", unsafe_allow_html=True)

        username = st.text_input("ชื่อผู้ใช้ (HN)", key="username_input", help="กรอก Hospital Number ของท่าน")
        password = st.text_input("รหัสผ่าน (เลขบัตรประชาชน)", type="password", key="password_input", help="กรอกเลขบัตรประชาชน 13 หลัก")

        if st.button("ลงชื่อเข้าใช้ (Login)"):
            if not username or not password:
                st.error("กรุณากรอก HN และ เลขบัตรประชาชนให้ครบถ้วน")
            else:
                # ค้นหาข้อมูลผู้ใช้ใน DataFrame
                # Search for the user in the DataFrame.
                try:
                    user_record = df[
                        (df['HN'].astype(str) == str(username).strip()) & 
                        (df['เลขบัตรประชาชน'].astype(str) == str(password).strip())
                    ]

                    if not user_record.empty:
                        st.session_state['authenticated'] = True
                        st.session_state['user_name'] = user_record.iloc[0]['ชื่อ-สกุล']
                        st.success("ลงชื่อเข้าใช้สำเร็จ!")
                        st.rerun()
                    else:
                        st.error("HN หรือ เลขบัตรประชาชนไม่ถูกต้อง")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการตรวจสอบข้อมูล: {e}")

        st.markdown("<p style='text-align: center; color: grey; font-size: 0.8em; margin-top: 2rem;'>ใช้ HN เป็นชื่อผู้ใช้ และใช้เลขบัตรประชาชนเป็นรหัสผ่าน</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def pdpa_consent_page():
    """
    แสดงหน้าสำหรับให้ความยินยอม PDPA
    Renders the PDPA consent page.
    """
    st.set_page_config(page_title="PDPA Consent", layout="centered")
    
    st.markdown("""
    <style>
        .main {
            background-color: #f0f2f6;
        }
        .consent-container {
            background-color: white;
            padding: 2rem 3rem;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-width: 700px;
            margin: auto;
            margin-top: 3rem;
        }
        h2 { text-align: center; }
        .consent-text {
            height: 300px;
            overflow-y: scroll;
            border: 1px solid #ddd;
            padding: 1rem;
            border-radius: 5px;
            background-color: #fafafa;
            margin-bottom: 1.5rem;
            text-align: justify;
        }
        .stButton>button {
            width: 100%;
            height: 3rem;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
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

