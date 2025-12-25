import csv
import os
import streamlit as st
import pandas as pd

# ชื่อไฟล์ CSV ที่เราอัปโหลดขึ้นไป
CSV_FILENAME = "LINE User id for Database - UserID.csv"

def get_line_id_from_csv(input_name, input_surname):
    """
    ค้นหา LINE User ID จากไฟล์ CSV โดยอ้างอิงจาก ชื่อ และ นามสกุล
    รองรับไฟล์ CSV ที่ save มาจาก Excel (utf-8-sig) และตัดช่องว่างส่วนเกินออก
    """
    if not os.path.exists(CSV_FILENAME):
        st.error(f"❌ ไม่พบไฟล์รายชื่อ: {CSV_FILENAME} กรุณาตรวจสอบว่าไฟล์อยู่ในโฟลเดอร์เดียวกับโค้ด")
        return None

    # เตรียมข้อมูล input: ตัดช่องว่างซ้ายขวา
    clean_input_name = str(input_name).strip()
    clean_input_surname = str(input_surname).strip()

    try:
        # ใช้ pandas อ่านจะจัดการเรื่อง encoding และหัวตารางได้เก่งกว่า csv ธรรมดา
        # encoding='utf-8-sig' ช่วยให้อ่านภาษาไทยจาก Excel ได้ไม่เพี้ยน
        df = pd.read_csv(CSV_FILENAME, dtype=str, encoding='utf-8-sig')
        
        # ทำความสะอาดข้อมูลในตาราง: ลบช่องว่างหัวคอลัมน์ (ถ้ามี)
        df.columns = df.columns.str.strip()
        
        # ตรวจสอบว่ามีคอลัมน์ที่ต้องการครบไหม
        required_columns = ['ชื่อ', 'นามสกุล', 'LINE User ID']
        if not all(col in df.columns for col in required_columns):
            st.error(f"❌ ไฟล์ CSV ขาดคอลัมน์สำคัญ: ต้องมี {required_columns}")
            st.write(f"คอลัมน์ที่พบในไฟล์: {list(df.columns)}")
            return None

        # ทำความสะอาดข้อมูลในแถว: ตัดช่องว่างในเนื้อหา
        df['ชื่อ'] = df['ชื่อ'].str.strip()
        df['นามสกุล'] = df['นามสกุล'].str.strip()
        df['LINE User ID'] = df['LINE User ID'].str.strip()

        # ค้นหาแถวที่ ชื่อ และ นามสกุล ตรงกัน
        match = df[
            (df['ชื่อ'] == clean_input_name) & 
            (df['นามสกุล'] == clean_input_surname)
        ]

        if not match.empty:
            # คืนค่า LINE User ID ของคนแรกที่เจอ
            return match.iloc[0]['LINE User ID']
        else:
            return None # ไม่พบข้อมูล

    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการอ่านไฟล์ CSV: {e}")
        return None
