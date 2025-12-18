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
    columns = ['Weight', 'Height', 'BMI', 'Waist', 'SBP', 'DBP', 'Pulse']
    return any(not is_empty(row.get(col)) for col in columns)

def has_vision_data(row):
    columns = ['V_R_Far', 'V_L_Far', 'V_R_Near', 'V_L_Near', 'Color_Blind']
    return any(not is_empty(row.get(col)) for col in columns)

def has_hearing_data(row):
    freqs = [250, 500, 1000, 2000, 3000, 4000, 6000, 8000]
    columns = [f'R_{f}' for f in freqs] + [f'L_{f}' for f in freqs]
    return any(not is_empty(row.get(col)) for col in columns)

def has_lung_data(row):
    columns = ['FVC_Predicted', 'FVC_Actual', 'FVC_Percent', 'FEV1_Predicted', 'FEV1_Actual', 'FEV1_Percent', 'FEV1_FVC_Ratio']
    return any(not is_empty(row.get(col)) for col in columns)

def has_visualization_data(df):
    return not df.empty and len(df) > 1
