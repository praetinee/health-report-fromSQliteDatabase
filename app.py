import streamlit as st
import pandas as pd
import sqlite3
import gspread
from google.oauth2.service_account import Credentials
from streamlit.components.v1 import html

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="ระบบตรวจสอบผลสุขภาพ", page_icon="🏥")

# ใส่ LIFF ID ของคุณแจนที่นี่
LIFF_ID = "2008725340-YHOiWxtj"

# ชื่อไฟล์ Database SQLite (แก้ให้ตรงกับชื่อไฟล์จริงของคุณแจน)
DB_FILE = "health_database.db"

# ชื่อ Google Sheet และ Worksheet ที่เตรียมไว้
SHEET_NAME = "HealthCheck_Log" 
WORKSHEET_NAME = "Users"

# --- 2. ฟังก์ชันเชื่อมต่อ Google Sheets ---
# ระบบจะดึง key จาก st.secrets (ต้องตั้งค่าใน Streamlit Cloud)
@st.cache_resource
def get_gsheet_client():
    # ดึงข้อมูลจาก st.secrets["gcp_service_account"]
    # ใน secrets ต้องตั้งชื่อ section ว่า [gcp_service_account]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    return gspread.authorize(credentials)

# --- 3. ฟังก์ชันเชื่อมต่อ SQLite ---
def check_sqlite_data(id_card, first_name, last_name):
    """
    ตรวจสอบข้อมูลใน SQLite ว่าตรงกับที่กรอกมาหรือไม่
    Return: (Found: bool, Data: dict/None)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # รวมชื่อและนามสกุลเพื่อไปเทียบกับคอลัมน์ "ชื่อ-สกุล"
    full_name_query = f"{first_name} {last_name}"
    
    # Query ข้อมูล (ใช้ parameter binding เพื่อความปลอดภัย)
    # สมมติชื่อ Table ว่า 'health_records' (ถ้าชื่ออื่น ให้แก้ตรงนี้)
    query = f"""
        SELECT * FROM health_records 
        WHERE "เลขบัตรประชาชน" = ? AND "ชื่อ-สกุล" = ?
    """
    
    try:
        cursor.execute(query, (id_card, full_name_query))
        result = cursor.fetchone()
        
        if result:
            # ดึงชื่อคอลัมน์มาด้วยเพื่อให้แสดงผลง่ายๆ
            columns = [description[0] for description in cursor.description]
            data = dict(zip(columns, result))
            return True, data
        else:
            return False, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล SQLite: {e}")
        return False, None
    finally:
        conn.close()

# --- 4. ฟังก์ชันจัดการ Google Sheet (Log User) ---
def check_user_registered(line_user_id):
    """เช็คว่า userId นี้เคยลงทะเบียนหรือยัง"""
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
        
        # ค้นหา cell ที่มี userId
        cell = sheet.find(line_user_id)
        if cell:
            # ถ้าเจอ ให้ดึงข้อมูลเลขบัตรประชาชนมาด้วย (สมมติว่าอยู่คอลัมน์ที่ 4)
            # Layout Sheet: [Timestamp, UserID, Name, ID_Card]
            row_data = sheet.row_values(cell.row)
            # ส่งกลับ (True, เลขบัตรประชาชน, ชื่อ-สกุล)
            # ปรับ index ตามโครงสร้าง sheet จริง (ตัวอย่างนี้สมมติ ID Card อยู่ index 3)
            return True, row_data[3], row_data[2] 
        return False, None, None
    except Exception as e:
        # ถ้ายังไม่มี Sheet หรือหาไม่เจอ
        return False, None, None

def register_user(line_user_id, full_name, id_card):
    """บันทึกข้อมูลผู้ใช้ใหม่ลง Google Sheet"""
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
        # บันทึก: [Timestamp, LineUserID, Name-Surname, ID Card]
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, line_user_id, full_name, id_card])
        return True
    except Exception as e:
        st.error(f"บันทึกข้อมูลไม่สำเร็จ: {e}")
        return False

# --- 5. Javascript สำหรับ LIFF (ดึง UserID) ---
# ส่วนนี้จะทำงานเฉพาะตอนเปิดครั้งแรกเพื่อดึง UserID แล้ว Reload หน้าเว็บพร้อม params
def liff_auth_component():
    js_code = f"""
    <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        async function main() {{
            await liff.init({{ liffId: "{LIFF_ID}" }});
            if (liff.isLoggedIn()) {{
                const profile = await liff.getProfile();
                const userId = profile.userId;
                const currentUrl = new URL(window.location.href);
                if (!currentUrl.searchParams.has('userid')) {{
                    currentUrl.searchParams.set('userid', userId);
                    window.location.href = currentUrl.toString();
                }}
            }} else {{
                liff.login();
            }}
        }}
        main();
    </script>
    <div style="text-align:center; padding: 20px;">
        <h3>กำลังเชื่อมต่อกับ LINE...</h3>
        <p>กรุณารอสักครู่</p>
    </div>
    """
    return html(js_code, height=200)

# ================= MAIN APP =================

# 1. รับค่าจาก URL (Query Params)
query_params = st.query_params
line_user_id = query_params.get("userid", None)

# 2. ถ้าไม่มี UserID ให้รัน LIFF Script เพื่อ Login
if not line_user_id:
    liff_auth_component()
    st.stop() # หยุดการทำงานส่วนล่างจนกว่าจะได้ UserID

# 3. ถ้ามี UserID แล้ว เริ่มกระบวนการตรวจสอบ
st.title("🏥 ผลตรวจสุขภาพ")
# st.write(f"Debug: UserID = {line_user_id}") # บรรทัดนี้ไว้เทส ถ้าใช้จริงให้ลบออก

# เช็คใน Google Sheet ว่าเคยลงทะเบียนไหม
is_registered, saved_id_card, saved_name = check_user_registered(line_user_id)

if is_registered:
    st.success(f"ยินดีต้อนรับคุณ {saved_name}")
    st.info("ระบบจดจำท่านจาก LINE เรียบร้อยแล้ว")
    
    # ดึงผลตรวจจาก SQLite ทันที
    # เราต้องแยกชื่อนามสกุลจาก saved_name หรือแก้ฟังก์ชัน query ให้รับชื่อเต็ม
    # เพื่อความง่าย แก้ฟังก์ชัน query ให้รับชื่อเต็มไปเลย หรือเรา Query ด้วย ID Card อย่างเดียวก็ได้ถ้ามั่นใจ
    # ในที่นี้สมมติ Query ด้วย ID Card และ ชื่อ-สกุล เพื่อความชัวร์
    found, result_data = check_sqlite_data(saved_id_card, saved_name.split()[0], " ".join(saved_name.split()[1:]))
    
    if found:
        st.subheader("📋 รายละเอียดผลตรวจของคุณ")
        # แสดงผลข้อมูลทั้งหมดในรูปแบบตารางหรือการ์ด
        for key, value in result_data.items():
            st.write(f"**{key}:** {value}")
    else:
        st.warning("ไม่พบผลตรวจสุขภาพในรอบนี้ (อาจข้อมูลไม่ตรงกัน โปรดติดต่อเจ้าหน้าที่)")

else:
    # --- หน้าจอลงทะเบียน (ถ้ายังไม่เคย Login) ---
    st.warning("🔒 กรุณาลงทะเบียนเพื่อยืนยันตัวตน (ทำครั้งแรกครั้งเดียว)")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            input_name = st.text_input("ชื่อ (ไม่ต้องมีคำนำหน้า)")
        with col2:
            input_surname = st.text_input("นามสกุล")
        
        input_id_card = st.text_input("เลขบัตรประชาชน", max_chars=13)
        
        submitted = st.form_submit_button("ตรวจสอบและดูผล")
        
        if submitted:
            if not input_name or not input_surname or not input_id_card:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            else:
                # ตรวจสอบกับ SQLite
                found, result_data = check_sqlite_data(input_id_card, input_name, input_surname)
                
                if found:
                    # ถ้าข้อมูลถูกต้อง -> บันทึกลง Google Sheet
                    full_name = f"{input_name} {input_surname}"
                    save_success = register_user(line_user_id, full_name, input_id_card)
                    
                    if save_success:
                        st.balloons()
                        st.success("ลงทะเบียนเรียบร้อย! ครั้งต่อไปท่านสามารถดูผลได้ทันที")
                        st.rerun() # รีโหลดหน้าเพื่อเข้าสู่โหมด Logged In ทันที
                    else:
                        st.error("เกิดปัญหาในการบันทึกข้อมูล (Google Sheet)")
                else:
                    st.error("❌ ไม่พบข้อมูล หรือ ชื่อ-นามสกุล ไม่ตรงกับเลขบัตรประชาชน")
                    st.write("คำแนะนำ: ตรวจสอบการสะกดชื่อ หรือ ติดต่อเจ้าหน้าที่เวชระเบียน")
