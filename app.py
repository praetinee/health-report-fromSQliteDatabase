import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import os
import sqlite3
import io

@st.cache_data(ttl=3600)
def load_data(file_path_or_buffer):
    """
    โหลดข้อมูลจากไฟล์ Excel, CSV หรือ SQLite Database
    """
    try:
        # กรณีเป็น Database Path (String)
        if isinstance(file_path_or_buffer, str):
            if file_path_or_buffer.endswith('.db') or file_path_or_buffer.endswith('.sqlite'):
                if not os.path.exists(file_path_or_buffer):
                    return None
                try:
                    conn = sqlite3.connect(file_path_or_buffer)
                    df = pd.read_sql("SELECT * FROM health_records", conn)
                    conn.close()
                    # แปลงคอลัมน์วันที่
                    if 'Date' in df.columns:
                        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                    return df
                except Exception as e:
                    # ถ้าอ่าน DB ไม่ได้ อาจเป็นเพราะยังไม่มีตาราง
                    return None

        # กรณีเป็น File Buffer (Upload)
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
        # st.error(f"Error loading data: {e}") # ปิด error ไว้ก่อนเพื่อไม่ให้รกหน้าจอตอนเริ่มต้น
        return None

def safe_float(val):
    """แปลงค่าเป็น float อย่างปลอดภัย (ใช้สำหรับการคำนวณ)"""
    if pd.isna(val) or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def get_unique_years(df):
    """ดึงรายการปีงบประมาณที่มีในข้อมูล"""
    if df is None or df.empty:
        return []
    
    years = []
    if 'Year' in df.columns:
        years = sorted(df['Year'].dropna().unique().tolist(), reverse=True)
    elif 'Date' in df.columns:
        years = sorted(df['Date'].dt.year.dropna().unique().tolist(), reverse=True)
        
    return years

def filter_data_by_year(df, year):
    """กรองข้อมูลตามปี"""
    if df is None or df.empty or year is None:
        return df
        
    if 'Year' in df.columns:
        # ตรวจสอบประเภทข้อมูลของ Year ใน df ว่าเป็น int หรือ str เพื่อกรองให้ถูก
        if pd.api.types.is_numeric_dtype(df['Year']):
            try:
                year = int(year)
            except: pass
        return df[df['Year'] == year]
    elif 'Date' in df.columns:
        return df[df['Date'].dt.year == int(year)]
        
    return df

def process_uploaded_file(uploaded_file):
    """ประมวลผลไฟล์ที่อัปโหลด (CSV/Excel) ให้เป็น DataFrame"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Clean Columns
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def sync_to_database(df, db_path='health_data.db'):
    """บันทึก DataFrame ลง SQLite Database"""
    try:
        conn = sqlite3.connect(db_path)
        df.to_sql('health_records', conn, if_exists='replace', index=False)
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database Sync Error: {e}")
        return False

# --- Existing Helper Functions ---

def clean_string(val):
    """ทำความสะอาดข้อมูลสตริง (ตัดช่องว่าง, จัดการ NaN)"""
    if pd.isna(val): return ""
    return str(val).strip()

def normalize_cid(val):
    """ทำความสะอาดเลขบัตรประชาชน (13 หลักล้วน ตัดขีด/เว้นวรรค)"""
    if pd.isna(val): return ""
    s = str(val).strip().replace("-", "").replace(" ", "").replace("'", "").replace('"', "")
    # กรณีเป็น Scientific notation (เช่น 1.23E+12)
    if "E" in s or "e" in s:
        try: s = str(int(float(s)))
        except: pass
    if s.endswith(".0"): s = s[:-2]
    return s

def normalize_db_name_field(full_name_str):
    """แยกชื่อ-นามสกุลจากสตริงเดียว"""
    clean_val = clean_string(full_name_str)
    parts = clean_val.split()
    if len(parts) >= 2: return parts[0], " ".join(parts[1:])
    elif len(parts) == 1: return parts[0], ""
    return "", ""

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
        search_val = str(search_term).strip()
    elif search_type == "CID":
        col_name = 'เลขบัตรประชาชน'
        search_val = normalize_cid(search_term)
        # ทำความสะอาดคอลัมน์ใน df เพื่อเปรียบเทียบ
        if col_name in df.columns:
            df[col_name] = df[col_name].apply(normalize_cid)
    else:
        col_name = 'HN'
        search_val = str(search_term).strip()

    # ค้นหา
    try:
        if search_type == "CID":
             person_rows = df[df[col_name] == search_val]
        else:
             person_rows = df[df[col_name].astype(str).str.strip() == search_val]
    except KeyError:
        return None

    if person_rows.empty:
        return None
    
    # ถ้ามีหลายปี ให้เอาปีล่าสุด
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
        search_val = str(search_term).strip()
    elif search_type == "CID":
        col_name = 'เลขบัตรประชาชน'
        search_val = normalize_cid(search_term)
        if col_name in df.columns:
            df[col_name] = df[col_name].apply(normalize_cid)
    else:
        col_name = 'HN'
        search_val = str(search_term).strip()

    try:
        if search_type == "CID":
             history_df = df[df[col_name] == search_val]
        else:
             history_df = df[df[col_name].astype(str).str.strip() == search_val]
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
    
    try:
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except:
        return 0

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
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

def set_background(png_file):
    """
    ตั้งค่าพื้นหลังของแอพ
    """
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
        page_bg_img = '''
        <style>
        .stApp {
        background-image: url("data:image/png;base64,%s");
        background-size: cover;
        }
        </style>
        ''' % bin_str
        st.markdown(page_bg_img, unsafe_allow_html=True)
