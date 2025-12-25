import streamlit as st
import sqlite3
import pandas as pd
# ลบ import print_report ออกจากตรงนี้ เพื่อป้องกัน Circular Import
from google_sheets import check_is_registered, save_registered_user
from line_register import get_line_id_from_csv

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบรายงานผลสุขภาพ", layout="wide")

# เชื่อมต่อ SQLite (ฐานข้อมูลผลสุขภาพเดิม)
def get_connection():
    return sqlite3.connect('health_database.db')

# --- ส่วนหลักของโปรแกรม ---
def main():
    # 1. รับ UserID จาก URL (Query Parameters)
    # ลิ้งค์ต้องเป็นรูปแบบ: https://your-app.streamlit.app/?userid=U12345xxxx
    query_params = st.query_params
    line_user_id = query_params.get("userid", None)

    # === กรณีที่ 1: เข้าใช้งานผ่าน Web Browser ปกติ (PC/Mobile) ไม่มี UserID ===
    if not line_user_id:
        st.info("💻 คุณกำลังเข้าใช้งานผ่าน Web Browser (โหมดทั่วไป)")
        st.title("🔎 ตรวจสอบผลตรวจสุขภาพ")
        st.write("กรุณากรอกข้อมูลเพื่อดูผลตรวจของคุณ")

        with st.form("web_login_form"):
            input_name = st.text_input("ชื่อ")
            input_surname = st.text_input("นามสกุล")
            input_id_card = st.text_input("เลขบัตรประชาชน (13 หลัก)")
            
            submitted = st.form_submit_button("ดูผลตรวจ")

            if submitted:
                if input_name and input_surname and input_id_card:
                    # เช็คข้อมูลใน SQLite โดยตรง
                    conn = get_connection()
                    query = "SELECT * FROM health_data WHERE name = ? AND surname = ? AND id_card = ?"
                    # ใช้ strip() ตัดช่องว่างเพื่อความชัวร์
                    df = pd.read_sql(query, conn, params=(input_name.strip(), input_surname.strip(), input_id_card.strip()))
                    conn.close()

                    if not df.empty:
                        st.success(f"✅ พบข้อมูลของคุณ {input_name} {input_surname}")
                        # Import เฉพาะตอนจะใช้ (Lazy Import)
                        from print_report import show_report
                        show_report(df.iloc[0])
                    else:
                        st.error("❌ ไม่พบข้อมูลผลตรวจ หรือ ข้อมูลไม่ถูกต้อง")
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")
        
        # จบการทำงานของโหมดเว็บ (ไม่ต้องทำส่วน LINE ต่อ)
        return

    # === กรณีที่ 2: เข้าใช้งานผ่าน LINE (มี UserID มาด้วย) ===
    # 2. ตรวจสอบกับ Google Sheets (Cloud) ว่าเคยลงทะเบียนหรือยัง
    with st.spinner("⏳ กำลังตรวจสอบสถานะ..."):
        registered_data = check_is_registered(line_user_id)

    if registered_data:
        # === กรณี: ลงทะเบียนแล้ว (ขาประจำ) ===
        # st.success(f"ยินดีต้อนรับคุณ {registered_data.get('Name')} {registered_data.get('Surname')}")
        
        # ดึงผลสุขภาพจาก SQLite มาโชว์เลย
        conn = get_connection()
        query = "SELECT * FROM health_data WHERE name = ? AND surname = ?"
        df = pd.read_sql(query, conn, params=(registered_data.get('Name'), registered_data.get('Surname')))
        conn.close()

        if not df.empty:
            # ย้าย import มาไว้ตรงนี้ (Lazy Import) เพื่อแก้ปัญหา Circular Import
            from print_report import show_report 
            show_report(df.iloc[0]) # แสดงผลรายงานด้วยฟังก์ชันเดิมที่มีอยู่
        else:
            st.error("❌ ไม่พบข้อมูลผลตรวจสุขภาพในระบบ (ติดต่อเจ้าหน้าที่)")
            
    else:
        # === กรณี: ยังไม่เคยลงทะเบียน (ขาจรผ่าน LINE) ===
        st.title("ลงทะเบียนดูผลตรวจสุขภาพ")
        st.info("👋 ยินดีต้อนรับ! กรุณากรอกข้อมูลเพื่อยืนยันตัวตนครั้งแรก (ระบบจะจำบัญชี LINE ของคุณไว้)")

        with st.form("register_form"):
            input_name = st.text_input("ชื่อ")
            input_surname = st.text_input("นามสกุล")
            input_id_card = st.text_input("เลขบัตรประชาชน (13 หลัก)")
            
            submitted = st.form_submit_button("ยืนยันตัวตน")

            if submitted:
                if input_name and input_surname and input_id_card:
                    # A. เช็คผลตรวจใน SQLite (ว่ามีผลตรวจจริงไหม + เลขบัตรถูกไหม)
                    conn = get_connection()
                    query = "SELECT * FROM health_data WHERE name = ? AND surname = ? AND id_card = ?"
                    df = pd.read_sql(query, conn, params=(input_name.strip(), input_surname.strip(), input_id_card.strip()))
                    conn.close()

                    if not df.empty:
                        # B. เช็ค Mapping ใน CSV (ว่าชื่อนี้ คู่กับ UserID ที่กดเข้ามาไหม)
                        mapped_line_id = get_line_id_from_csv(input_name, input_surname)

                        if mapped_line_id == line_user_id:
                            # C. ผ่านทุกด่าน! -> บันทึกลง Google Sheets
                            if save_registered_user(line_user_id, input_name, input_surname):
                                st.success("✅ ลงทะเบียนสำเร็จ! กำลังพาไปดูผลตรวจ...")
                                st.rerun() # รีโหลดหน้าเว็บทันที
                            else:
                                st.error("บันทึกข้อมูลล้มเหลว กรุณาลองใหม่อีกครั้ง")
                        else:
                            # กรณีชื่อใน CSV ไม่ตรงกับไลน์ที่เข้า (ป้องกันคนแอบอ้าง)
                            st.error(f"❌ บัญชี LINE นี้ ไม่ได้รับอนุญาตให้ดูผลของ: {input_name}")
                            if not mapped_line_id:
                                st.warning("ไม่พบชื่อ-นามสกุลนี้ในฐานข้อมูล LINE ID (CSV)")
                            else:
                                st.warning(f"ระบบตรวจพบว่าชื่อนี้ผูกกับ LINE ID อื่นอยู่")
                    else:
                        st.error("❌ ไม่พบข้อมูลผลตรวจ หรือ เลขบัตรประชาชนไม่ถูกต้อง")
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

if __name__ == "__main__":
    main()
