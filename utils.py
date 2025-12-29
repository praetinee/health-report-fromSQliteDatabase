import pandas as pd
import numpy as np

def is_empty(val):
    if val is None: return True
    if isinstance(val, str) and val.strip() == "": return True
    if isinstance(val, (int, float)) and pd.isna(val): return True
    val_str = str(val).strip().lower()
    if val_str in ["-", "none", "nan", "null"]: return True
    return False

def normalize_name(name):
    if not isinstance(name, str): return str(name)
    return " ".join(name.split())

def has_basic_health_data(row):
    columns = ['Weight', 'Height', 'BMI', 'Waist', 'SBP', 'DBP', 'Pulse', 
               'น้ำหนัก', 'ส่วนสูง', 'รอบเอว']
    return any(not is_empty(row.get(col)) for col in columns)

def has_vision_data(row):
    # เช็คทุก format ที่เป็นไปได้สำหรับ Vision
    prefixes = ['V_R', 'V_L', 'R', 'L']
    suffixes = ['Far', 'Near', 'Color', 'Blind']
    
    # สร้างรายการ key ที่เป็นไปได้ทั้งหมด
    possible_keys = [
        'V_R_Far', 'V_L_Far', 'V_R_Near', 'V_L_Near', 'Color_Blind',
        'Color Blind', 'ColorBlind', 'ตาบอดสี',
        'Vision Right', 'Vision Left'
    ]
    
    # เช็คแบบ manual
    for key in possible_keys:
        if not is_empty(row.get(key)): return True
        
    # เช็คแบบ contains (เผื่อชื่อแปลกๆ)
    keys = row.keys() if hasattr(row, 'keys') else []
    for k in keys:
        k_lower = str(k).lower()
        if 'vision' in k_lower or 'สายตา' in k_lower:
            if not is_empty(row.get(k)): return True
            
    return False

def has_hearing_data(row):
    # สร้าง pattern ทั้งหมดที่เป็นไปได้: R250, R_250, R250Hz, Right 250, etc.
    sides = ['R', 'L', 'R_', 'L_']
    freqs = ['250', '500', '1000', '1k', '2000', '2k', '3000', '3k', '4000', '4k', '6000', '6k', '8000', '8k']
    
    # 1. เช็ค Exact Match ตาม Pattern
    for s in sides:
        for f in freqs:
            key = f"{s}{f}"
            if not is_empty(row.get(key)): return True
            
    # 2. เช็คกรณีชื่อเต็ม (Right_500, etc.) - เผื่อไว้
    if any(not is_empty(row.get(k)) for k in ['Right_500', 'Left_500', 'Audiometry']):
        return True
        
    return False

def has_lung_data(row):
    # เช็คชื่อคอลัมน์ปอดที่หลากหลาย
    keywords = ['FVC', 'FEV1', 'PEF', 'Lung', 'Spirometry']
    
    # เช็ค Direct match
    direct_keys = ['FVC', 'FVC predic', 'FVC %', 'FEV1', 'FEV1 predic', 'FEV1 %', 'FEV1/FVC', 'FEV1/FVC %']
    if any(not is_empty(row.get(k)) for k in direct_keys): return True
    
    # เช็ค Partial match ใน keys
    keys = row.keys() if hasattr(row, 'keys') else []
    for k in keys:
        k_str = str(k)
        if any(kw in k_str for kw in keywords):
            if not is_empty(row.get(k)): return True
            
    return False

def has_visualization_data(df):
    return df is not None and not df.empty
