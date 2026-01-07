import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64

@st.cache_data(ttl=3600)
def load_data(file_path_or_buffer):
    """
    โหลดข้อมูลจากไฟล์ Excel หรือ CSV
    """
    try:
        # ตรวจสอบว่าเป็นไฟล์ Excel หรือ CSV
        if hasattr(file_path_or_buffer, 'name'):
            file_name = file_path_or_buffer.name
        else:
            file_name = str(file_path_or_buffer)

        if file_name.endswith('.csv'):
            df = pd.read_csv(file_path_or_buffer)
        else:
            df = pd.read_excel(file_path_or_buffer)
        
        # แปลงชื่อคอลัมน์ให้เป็นมาตรฐาน (ตัดช่องว่าง)
        df.columns = df.columns.str.strip()
        
        # แปลงคอลัมน์วันที่ถ้ามี
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def get_person_data(df, search_term, search_type="HN"):
    """
    ค้นหาข้อมูลล่าสุดของบุคคลตาม HN หรือ เลขบัตรประชาชน
    """
    if df.empty:
        return None

    # แปลงข้อมูลเป็น string เพื่อการค้นหาที่แม่นยำ
    df = df.copy()
    
    if search_type == "HN":
        col_name = 'HN'
    elif search_type == "CID":
        col_name = 'เลขบัตรประชาชน'
    else:
        # Default search by Name if needed, but usually HN/CID is unique
        col_name = 'HN'

    # ค้นหา
    try:
        person_rows = df[df[col_name].astype(str).str.strip() == str(search_term).strip()]
    except KeyError:
        return None

    if person_rows.empty:
        return None
    
    # ถ้ามีหลายปี ให้เอาปีล่าสุด (สมมติว่ามีคอลัมน์ Year หรือ Date)
    if 'Year' in df.columns:
        latest_row = person_rows.sort_values('Year', ascending=False).iloc[0]
    elif 'Date' in df.columns:
        latest_row = person_rows.sort_values('Date', ascending=False).iloc[0]
    else:
        latest_row = person_rows.iloc[0]

    return latest_row.to_dict()

def get_history_data(df, search_term, search_type="HN"):
    """
    ดึงข้อมูลประวัติย้อนหลังทั้งหมดของบุคคลนั้น
    """
    if df.empty:
        return pd.DataFrame()

    if search_type == "HN":
        col_name = 'HN'
    elif search_type == "CID":
        col_name = 'เลขบัตรประชาชน'
    else:
        col_name = 'HN'

    try:
        history_df = df[df[col_name].astype(str).str.strip() == str(search_term).strip()]
    except KeyError:
        return pd.DataFrame()
        
    return history_df

def calculate_age(dob):
    """
    คำนวณอายุจากวันเกิด (รูปแบบ datetime หรือ string)
    """
    if pd.isna(dob):
        return 0
    
    today = datetime.today()
    
    if isinstance(dob, str):
        try:
            # พยายาม parse วันที่แบบต่างๆ
            birth_date = pd.to_datetime(dob, dayfirst=True)
        except:
            return 0
    else:
        birth_date = dob
        
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def local_css(file_name):
    """
    โหลด CSS ไฟล์
    """
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def get_base64_of_bin_file(bin_file):
    """
    แปลงไฟล์ binary เป็น base64 string
    """
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(png_file):
    """
    ตั้งค่าพื้นหลังของแอพ
    """
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = '''
    <style>
    .stApp {
    background-image: url("data:image/png;base64,%s");
    background-size: cover;
    }
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)
