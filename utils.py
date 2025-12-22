import pandas as pd
import numpy as np

def is_empty(val):
    if val is None: return True
    if isinstance(val, str) and val.strip() == "": return True
    if isinstance(val, (int, float)) and pd.isna(val): return True
    return False

def normalize_name(name):
    if not isinstance(name, str): return str(name)
    return " ".join(name.split())

def has_basic_health_data(row):
    # เพิ่มคอลัมน์ภาษาไทยที่มักใช้ในไฟล์จริง
    columns = ['Weight', 'Height', 'BMI', 'Waist', 'SBP', 'DBP', 'Pulse', 
               'น้ำหนัก', 'ส่วนสูง', 'รอบเอว']
    return any(not is_empty(row.get(col)) for col in columns)

def has_vision_data(row):
    # เช็คทั้งชื่อภาษาอังกฤษและภาษาไทยที่อาจมีในฐานข้อมูล
    columns = [
        'V_R_Far', 'V_L_Far', 'V_R_Near', 'V_L_Near', 'Color_Blind',
        'ป.การรวมภาพ', 'ผ.การรวมภาพ',
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)',
        'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)'
    ]
    return any(not is_empty(row.get(col)) for col in columns)

def has_hearing_data(row):
    # แก้ไข: ชื่อคอลัมน์ให้ตรงกับ Performance Tests (R250, R1k, etc.)
    # และเผื่อกรณีชื่อแบบเก่า (R_250)
    keys = [
        'R250', 'R500', 'R1k', 'R2k', 'R3k', 'R4k', 'R6k', 'R8k',
        'L250', 'L500', 'L1k', 'L2k', 'L3k', 'L4k', 'L6k', 'L8k',
        'R_250', 'R_500', 'R_1000', 'R_2000', 'R_3000', 'R_4000', 'R_6000', 'R_8000'
    ]
    return any(not is_empty(row.get(col)) for col in keys)

def has_lung_data(row):
    # แก้ไข: ชื่อคอลัมน์ให้ตรงกับฐานข้อมูลจริง
    columns = [
        'FVC', 'FVC predic', 'FVC เปอร์เซ็นต์', 
        'FEV1', 'FEV1 predic', 'FEV1เปอร์เซ็นต์', 
        'FEV1/FVC%', 'PEF'
    ]
    return any(not is_empty(row.get(col)) for col in columns)

def has_visualization_data(df):
    return df is not None and not df.empty
