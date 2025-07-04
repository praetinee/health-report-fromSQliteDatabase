import pandas as pd

def get_float(col, person):
    try:
        return float(person[col])
    except:
        return None

def flag(val, low, high):
    if val is None:
        return False
    return val < low or val > high

def is_empty(x):
    return str(x).strip() == ""

def safe_value(x):
    try:
        return float(x)
    except:
        return None

def safe_text(x):
    if pd.isna(x):
        return ""
    return str(x)

def calc_gfr(sex, age, cr):
    if cr is None or cr <= 0 or age <= 0:
        return None
    if sex == "ชาย":
        return 194 * (cr ** -1.094) * (age ** -0.287)
    else:
        return 194 * (cr ** -1.094) * (age ** -0.287) * 0.739

def convert_to_bmi(weight, height_cm):
    try:
        h = float(height_cm) / 100
        return round(float(weight) / (h * h), 1)
    except:
        return None

def normalize_date(x):
    try:
        return pd.to_datetime(x, errors="coerce", dayfirst=True)
    except:
        return None
