import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import datetime
import json

# กำหนด Scope ของการเข้าถึง Google APIs
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# ชื่อ Google Sheet ที่สร้างไว้
SHEET_NAME = 'Health_Report_Registration' 

def get_db_connection():
    """เชื่อมต่อกับ Google Sheets ผ่าน Streamlit Secrets เท่านั้น"""
    try:
        # ตรวจสอบว่ามี Secrets ชื่อ 'gsheets_key_json' หรือไม่
        if "gsheets_key_json" in st.secrets:
            # แปลงข้อความ JSON String ใน Secrets กลับเป็น Dictionary เพื่อใช้งาน
            key_dict = json.loads(st.secrets["gsheets_key_json"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, SCOPE)
            
            # เชื่อมต่อกับ Google Sheets
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet
        else:
            st.error("❌ ไม่พบการตั้งค่า Secrets (gsheets_key_json)")
            st.info("กรุณาไปที่หน้าตั้งค่า App บน Streamlit Cloud แล้วเพิ่ม Secrets ตามคู่มือ")
            return None

    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google Sheets ไม่สำเร็จ: {e}")
        return None

def check_is_registered(line_user_id):
    """ตรวจสอบว่า UserID นี้เคยลงทะเบียนหรือยัง"""
    sheet = get_db_connection()
    if not sheet:
        return None

    try:
        records = sheet.get_all_records()
        for record in records:
            # แปลงเป็น String ทั้งคู่ก่อนเทียบ เพื่อป้องกันความผิดพลาด
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
        # เรียงลำดับข้อมูลที่จะบันทึก [เวลา, UserID, ชื่อ, นามสกุล]
        row_data = [timestamp, line_user_id, name, surname]
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"❌ บันทึกข้อมูลล้มเหลว: {e}")
        return False
