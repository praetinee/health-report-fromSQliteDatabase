import pandas as pd
from datetime import datetime
import re

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

# ---------------------------
# ✅ ฟังก์ชันแปลงวันที่ไทยเป็น datetime
thai_months_full = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
    "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
    "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4,
    "พ.ค.": 5, "มิ.ย.": 6, "ก.ค.": 7, "ส.ค.": 8,
    "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12
}

def parse_date_thai(date_str):
    try:
        if pd.isna(date_str) or not str(date_str).strip():
            return pd.NaT

        s = str(date_str).strip()
        s = s.replace("กรกฏาคม", "กรกฎาคม")  # รองรับสะกดผิดบ่อย

        # ✅ รูปแบบ: 5.กุมภาพันธ์ 2568 หรือ 5/กุมภาพันธ์/2568
        match = re.match(r"(\d{1,2})[.\-/ ]*([ก-ฮ.]+)[.\-/ ]*(\d{4})", s)
        if match:
            day, month_str, year = match.groups()
            month_str = month_str.strip(" .")
            month = thai_months_full.get(month_str, 0)
            year = int(year)
            if year > 2400:  # พ.ศ. ➝ ค.ศ.
                year -= 543
            if month > 0:
                return pd.Timestamp(datetime(year, month, int(day)))

        # ✅ Fallback: dd/mm/yyyy
        dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if dt is pd.NaT or pd.isna(dt):
            return pd.NaT
        if dt.year > 2400:
            dt = dt.replace(year=dt.year - 543)
        return dt

    except Exception as e:
        return ไม่พบวันที่ตรวจ
# ---------------------------
# ✅ ฟังก์ชันแสดงวันที่แบบไทย (5 กุมภาพันธ์ 2568)
def format_thai_date(date):
    if pd.isna(date):
        return "-"
    thai_months = [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    day = date.day
    month = thai_months[date.month - 1]
    year = date.year + 543
    return f"{day} {month} {year}"

def interpret_bp(sbp, dbp):
    try:
        sbp = float(sbp)
        dbp = float(dbp)

        if sbp < 120 and dbp < 80:
            return "ความดันปกติ"
        elif 120 <= sbp < 130 and dbp < 80:
            return "ความดันเริ่มสูง"
        elif 130 <= sbp < 140 or 80 <= dbp < 90:
            return "ความดันโลหิตสูง ระยะที่ 1"
        elif sbp >= 140 or dbp >= 90:
            return "ความดันโลหิตสูง ระยะที่ 2"
        else:
            return "-"
    except:
        return "-"

