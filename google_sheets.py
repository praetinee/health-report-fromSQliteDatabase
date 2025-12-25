import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import datetime

# กำหนด Scope ของการเข้าถึง Google APIs
SCOPE = [
    "[https://spreadsheets.google.com/feeds](https://spreadsheets.google.com/feeds)",
    "[https://www.googleapis.com/auth/spreadsheets](https://www.googleapis.com/auth/spreadsheets)",
    "[https://www.googleapis.com/auth/drive.file](https://www.googleapis.com/auth/drive.file)",
    "[https://www.googleapis.com/auth/drive](https://www.googleapis.com/auth/drive)"
]

# ชื่อไฟล์ JSON Key ของคุณ (ต้องเอาไฟล์นี้มาวางในโฟลเดอร์โปรเจกต์)
SERVICE_ACCOUNT_FILE = 'service_account.json'

# ชื่อ Google Sheet ที่สร้างไว้
SHEET_NAME = 'Health_Report_Registration'  # <-- อย่าลืมเปลี่ยนชื่อให้ตรงกับ Sheet ของคุณ

def get_db_connection():
    """เชื่อมต่อกับ Google Sheets"""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except FileNotFoundError:
        st.error(f"❌ ไม่พบไฟล์กุญแจ '{SERVICE_ACCOUNT_FILE}' โปรดนำไฟล์มาวางในโฟลเดอร์โปรเจกต์")
        return None
    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google Sheets ไม่สำเร็จ: {e}")
        return None

def check_is_registered(line_user_id):
    """
    ตรวจสอบว่า UserID นี้เคยลงทะเบียนหรือยัง
    Return: ข้อมูล user (dict) ถ้าเจอ, หรือ None ถ้าไม่เจอ
    """
    sheet = get_db_connection()
    if not sheet:
        return None

    try:
        # ดึงข้อมูลทั้งหมดมาเช็ค (สมมติว่า UserID อยู่คอลัมน์ A หรือ index 0)
        records = sheet.get_all_records()
        for record in records:
            # แปลงเป็น String เพื่อความชัวร์เวลาเทียบ
            if str(record.get('UserID')) == str(line_user_id):
                return record
        return None
    except Exception as e:
        st.warning(f"⚠️ เกิดข้อผิดพลาดขณะตรวจสอบข้อมูล: {e}")
        return None

def save_registered_user(line_user_id, name, surname):
    """บันทึกข้อมูลคนใหม่ลง Google Sheets"""
    sheet = get_db_connection()
    if not sheet:
        return False

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # เรียงลำดับข้อมูลตามหัวตารางใน Sheet: [Timestamp, UserID, Name, Surname]
        row_data = [timestamp, line_user_id, name, surname]
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"❌ บันทึกข้อมูลล้มเหลว: {e}")
        return False
