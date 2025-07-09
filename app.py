import streamlit as st
import sqlite3
import requests
import pandas as pd
import tempfile
import html
import numpy as np
from collections import OrderedDict
from datetime import datetime
import re

# ==============================================================================
# 1. UTILITY FUNCTIONS (ฟังก์ชันตัวช่วยพื้นฐาน)
#    - ฟังก์ชันเล็กๆ ที่ใช้งานทั่วไป ไม่เปลี่ยนแปลงจากเดิมมาก
# ==============================================================================

def is_empty(val):
    """ตรวจสอบว่าเป็นค่าว่างหรือไม่"""
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def normalize_thai_date(date_str):
    """แปลงรูปแบบวันที่ภาษาไทยให้เป็นมาตรฐาน"""
    if is_empty(date_str):
        return "-"
    
    # ... (ส่วนตรรกะของฟังก์ชันนี้เหมือนเดิมทุกประการ) ...
    # หมายเหตุ: ตรรกะของ normalize_thai_date มีความซับซ้อนและเฉพาะทาง จึงคงไว้ตามเดิม
    THAI_MONTHS_GLOBAL = {
        1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน",
        5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม",
        9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"
    }
    THAI_MONTH_ABBR_TO_NUM_GLOBAL = {
        "ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2,
        "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4,
        "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6,
        "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8,
        "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10,
        "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12
    }
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()
    if s.lower() in ["ไม่ตรวจ", "นัดที่หลัง", "ไม่ได้เข้ารับการตรวจ", ""]: return s
    try:
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}".replace('.', '')
        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})(?:-\d{1,2})?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                try:
                    dt = datetime(year - 543, month_num, day)
                    return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}".replace('.', '')
                except ValueError: pass
    except Exception: pass
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            current_ce_year = datetime.now().year
            if parsed_dt.year > current_ce_year + 50 and parsed_dt.year - 543 > 1900:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}".replace('.', '')
    except Exception: pass
    return s

def get_float(val):
    """แปลงค่าเป็น float อย่างปลอดภัย"""
    if is_empty(val):
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def flag_value(val, low=None, high=None, higher_is_better=False):
    """
    ตรวจสอบค่าและคืนค่าที่จัดรูปแบบพร้อม flag ผิดปกติ
    Returns: (formatted_string, is_abnormal_boolean)
    """
    num_val = get_float(val)
    if num_val is None:
        return "-", False

    is_abnormal = False
    if higher_is_better:
        if low is not None and num_val < low:
            is_abnormal = True
    else:
        if low is not None and num_val < low:
            is_abnormal = True
        if high is not None and num_val > high:
            is_abnormal = True

    return f"{num_val:.1f}", is_abnormal

def get_year_specific_column(base_name, year):
    """สร้างชื่อคอลัมน์สำหรับ CXR/EKG ตามปีที่เลือก"""
    current_thai_year = datetime.now().year + 543
    if year == current_thai_year:
        return base_name
    return f"{base_name}{str(year)[-2:]}"

# ==============================================================================
# 2. CONFIGURATION CLASS (รวมการตั้งค่าทั้งหมดไว้ที่นี่)
#    - ย้าย Config ของตารางต่างๆ มาไว้ในที่เดียว
# ==============================================================================
class ReportConfig:
    @staticmethod
    def get_cbc_config(sex):
        hb_low = 13 if sex == "ชาย" else 12
        hct_low = 39 if sex == "ชาย" else 36
        return [
            ("ฮีโมโกลบิน (Hb)", "Hb(%)", f"ชาย > 13, หญิง > 12 g/dl", hb_low, None),
            ("ฮีมาโตคริต (Hct)", "HCT", f"ชาย > 39%, หญิง > 36%", hct_low, None),
            ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000),
            ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70),
            ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44),
            ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9),
            ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9),
            ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3),
            ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000),
        ]

    BLOOD_CHEM_CONFIG = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2),
        ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120),
        ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37),
        ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41),
        ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200),
        ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160),
        ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17),
        ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True),
    ]

    URINE_CONFIG = [
        ("สี (Colour)", "Color", "Yellow, Pale Yellow"),
        ("น้ำตาล (Sugar)", "sugar", "Negative"),
        ("โปรตีน (Albumin)", "Alb", "Negative, trace"),
        ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0"),
        ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030"),
        ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2 cell/HPF"),
        ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5 cell/HPF"),
        ("เซลล์เยื่อบุผิว (Squam.epit.)", "SQ-epi", "0 - 10 cell/HPF"),
        ("อื่นๆ", "ORTER", "-"),
    ]

# ==============================================================================
# 3. HEALTH ANALYZER CLASS (รวมตรรกะการวิเคราะห์และคำแนะนำ)
#    - ย้ายฟังก์ชัน interpret, summarize, advice ทั้งหมดมาเป็น method ของคลาสนี้
# ==============================================================================
class HealthAnalyzer:
    def __init__(self, person_data, sex, year):
        self.data = person_data
        self.sex = sex
        self.year = year

    def get_value(self, key, default="-"):
        val = self.data.get(key, default)
        return default if is_empty(val) else val

    def get_float_value(self, key):
        return get_float(self.data.get(key))

    # --- Vital Signs & BMI ---
    def get_bmi_advice(self):
        bmi = self.get_float_value('bmi')
        sbp = self.get_float_value('SBP')
        dbp = self.get_float_value('DBP')
        # ... ตรรกะจากฟังก์ชัน combined_health_advice เดิม ...
        if bmi is None and sbp is None: return ""
        bmi_text = ""
        if bmi is not None:
            if bmi > 30: bmi_text = "น้ำหนักเกินมาตรฐานมาก"
            elif bmi >= 25: bmi_text = "น้ำหนักเกินมาตรฐาน"
            elif bmi < 18.5: bmi_text = "น้ำหนักน้อยกว่ามาตรฐาน"
            else: bmi_text = "น้ำหนักอยู่ในเกณฑ์ปกติ"
        
        bp_text = ""
        if sbp is not None and dbp is not None:
            if sbp >= 160 or dbp >= 100: bp_text = "ความดันโลหิตอยู่ในระดับสูงมาก"
            elif sbp >= 140 or dbp >= 90: bp_text = "ความดันโลหิตอยู่ในระดับสูง"
            elif sbp >= 120 or dbp >= 80: bp_text = "ความดันโลหิตเริ่มสูง"

        if bmi_text and "ปกติ" in bmi_text and not bp_text: return "น้ำหนักอยู่ในเกณฑ์ดี ควรรักษาพฤติกรรมสุขภาพนี้ต่อไป"
        if not bmi_text and bp_text: return f"{bp_text} แนะนำให้ดูแลสุขภาพ และติดตามค่าความดันอย่างสม่ำเสมอ"
        if bmi_text and bp_text: return f"{bmi_text} และ {bp_text} แนะนำให้ปรับพฤติกรรมด้านอาหารและการออกกำลังกาย"
        if bmi_text and not bp_text: return f"{bmi_text} แนะนำให้ดูแลเรื่องโภชนาการและการออกกำลังกายอย่างเหมาะสม"
        return ""

    def get_bp_interpretation(self):
        sbp = self.get_float_value('SBP')
        dbp = self.get_float_value('DBP')
        if sbp is None: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"

    # --- Blood Chemistry Advice ---
    def get_fbs_advice(self):
        value = self.get_float_value('FBS')
        if value is None: return ""
        if 100 <= value < 106: return "ระดับน้ำตาลเริ่มสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภคอาหารหวาน แป้ง และออกกำลังกาย"
        if 106 <= value < 126: return "ระดับน้ำตาลสูงเล็กน้อย ควรลดอาหารหวาน แป้ง ของมัน ตรวจติดตามน้ำตาลซ้ำ และออกกำลังกายสม่ำเสมอ"
        if value >= 126: return "ระดับน้ำตาลสูง ควรพบแพทย์เพื่อตรวจยืนยันเบาหวาน และติดตามอาการ"
        return ""
    
    def get_kidney_advice(self):
        gfr = self.get_float_value('GFR')
        if gfr is not None and gfr < 60:
            return "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวัน และไม่ควรกลั้นปัสสาวะ มีอาการบวมผิดปกติให้พบแพทย์"
        return ""

    def get_liver_advice(self):
        alp = self.get_float_value('ALP')
        sgot = self.get_float_value('SGOT')
        sgpt = self.get_float_value('SGPT')
        if alp is None or sgot is None or sgpt is None: return ""
        if alp > 120 or sgot > 36 or sgpt > 40:
            return "ควรลดอาหารไขมันสูงและตรวจติดตามการทำงานของตับซ้ำ"
        return ""
        
    def get_uric_acid_advice(self):
        value = self.get_float_value('Uric Acid')
        if value is not None and value > 7.2:
            return "ควรลดอาหารที่มีพิวรีนสูง เช่น เครื่องในสัตว์ อาหารทะเล และพบแพทย์หากมีอาการปวดข้อ"
        return ""

    def get_lipids_advice(self):
        chol = self.get_float_value('CHOL')
        tgl = self.get_float_value('TGL')
        ldl = self.get_float_value('LDL')
        if chol is None or tgl is None or ldl is None: return ""
        
        summary_text = ""
        if chol >= 250 or tgl >= 250 or ldl >= 180: summary_text = "ไขมันในเลือดสูง"
        elif not (chol <= 200 and tgl <= 150): summary_text = "ไขมันในเลือดสูงเล็กน้อย"

        if summary_text == "ไขมันในเลือดสูง":
            return "ไขมันในเลือดสูง ควรลดอาหารที่มีไขมันอิ่มตัว เช่น ของทอด หนังสัตว์ ออกกำลังกายสม่ำเสมอ และพิจารณาพบแพทย์เพื่อตรวจติดตาม"
        if summary_text == "ไขมันในเลือดสูงเล็กน้อย":
            return "ไขมันในเลือดสูงเล็กน้อย ควรปรับพฤติกรรมการบริโภค ลดของมัน และออกกำลังกายเพื่อควบคุมระดับไขมัน"
        return ""

    # --- CBC Advice ---
    def get_cbc_advice(self):
        advice_parts = []
        hb, hct = self.get_float_value('Hb(%)'), self.get_float_value('HCT')
        wbc, plt = self.get_float_value('WBC (cumm)'), self.get_float_value('Plt (/mm)')
        
        hb_ref = 13 if self.sex == "ชาย" else 12
        if hb is not None and hb < hb_ref: advice_parts.append("ระดับฮีโมโกลบินต่ำ ควรตรวจหาภาวะโลหิตจางและติดตามซ้ำ")
        
        hct_ref = 39 if self.sex == "ชาย" else 36
        if hct is not None and hct < hct_ref: advice_parts.append("ค่าฮีมาโตคริตต่ำ ควรตรวจหาภาวะเลือดจางและตรวจติดตาม")

        if wbc is not None:
            if wbc < 4000: advice_parts.append("เม็ดเลือดขาวต่ำ อาจเกิดจากภูมิคุ้มกันลด ควรติดตาม")
            elif wbc > 10000: advice_parts.append("เม็ดเลือดขาวสูง อาจมีการอักเสบ ติดเชื้อ หรือความผิดปกติ ควรพบแพทย์")

        if plt is not None:
            if plt < 150000: advice_parts.append("เกล็ดเลือดต่ำ อาจมีภาวะเลือดออกง่าย ควรตรวจยืนยันซ้ำ")
            elif plt > 500000: advice_parts.append("เกล็ดเลือดสูง ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม")

        return " ".join(advice_parts)
    
    def get_all_lab_advice(self):
        messages = [
            self.get_fbs_advice(), self.get_kidney_advice(), self.get_liver_advice(),
            self.get_uric_acid_advice(), self.get_lipids_advice(), self.get_cbc_advice()
        ]
        groups = {"FBS": [], "ไต": [], "ตับ": [], "ยูริค": [], "ไขมัน": [], "อื่นๆ": []}
        for msg in filter(None, messages):
            if "น้ำตาล" in msg: groups["FBS"].append(msg)
            elif "ไต" in msg: groups["ไต"].append(msg)
            elif "ตับ" in msg: groups["ตับ"].append(msg)
            elif "พิวรีน" in msg or "ยูริค" in msg: groups["ยูริค"].append(msg)
            elif "ไขมัน" in msg: groups["ไขมัน"].append(msg)
            else: groups["อื่นๆ"].append(msg)
        return groups

    # --- Urinalysis Interpretation & Advice ---
    def _interpret_urine_value(self, test_name, value):
        val = str(value).strip().lower()
        if is_empty(val): return "ปกติ"
        
        if test_name == "โปรตีน (Albumin)":
            if val == "negative": return "ไม่พบ"
            if val in ["trace", "1+", "2+"]: return "พบโปรตีนในปัสสาวะเล็กน้อย"
            return "พบโปรตีนในปัสสาวะ"
        if test_name == "น้ำตาล (Sugar)":
            if val == "negative": return "ไม่พบ"
            if val == "trace": return "พบน้ำตาลในปัสสาวะเล็กน้อย"
            return "พบน้ำตาลในปัสสาวะ"
        
        def parse_range(v):
            v = v.replace("cell/hpf", "").replace("cells/hpf", "").strip()
            try:
                return float(v.split("-")[-1])
            except: return None

        if test_name == "เม็ดเลือดแดง (RBC)":
            h = parse_range(val)
            if h is None: return value
            if h <= 2: return "ปกติ"
            if h <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
            return "พบเม็ดเลือดแดงในปัสสาวะ"
        if test_name == "เม็ดเลือดขาว (WBC)":
            h = parse_range(val)
            if h is None: return value
            if h <= 5: return "ปกติ"
            if h <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
            return "พบเม็ดเลือดขาวในปัสสาวะ"
        return value # For others like color, pH etc.

    def get_urine_advice(self):
        alb = self._interpret_urine_value("โปรตีน (Albumin)", self.get_value("Alb"))
        sugar = self._interpret_urine_value("น้ำตาล (Sugar)", self.get_value("sugar"))
        rbc = self._interpret_urine_value("เม็ดเลือดแดง (RBC)", self.get_value("RBC1"))
        wbc = self._interpret_urine_value("เม็ดเลือดขาว (WBC)", self.get_value("WBC1"))

        if all(x in ["-", "ปกติ", "ไม่พบ", "พบโปรตีนในปัสสาวะเล็กน้อย", "พบน้ำตาลในปัสสาวะเล็กน้อย"] for x in [alb, sugar, rbc, wbc]):
            return "ผลตรวจปัสสาวะอยู่ในเกณฑ์ปกติ"
        if "พบน้ำตาลในปัสสาวะ" in sugar and "เล็กน้อย" not in sugar:
            return "ควรลดการบริโภคน้ำตาล และตรวจระดับน้ำตาลในเลือดเพิ่มเติม"
        if self.sex == "หญิง" and "พบเม็ดเลือดแดง" in rbc and "ปกติ" in wbc:
            return "อาจมีปนเปื้อนจากประจำเดือน แนะนำให้ตรวจซ้ำ"
        if self.sex == "ชาย" and "พบเม็ดเลือดแดง" in rbc and "ปกติ" in wbc:
            return "พบเม็ดเลือดแดงในปัสสาวะ ควรตรวจทางเดินปัสสาวะเพิ่มเติม"
        if "พบเม็ดเลือดขาว" in wbc and "เล็กน้อย" not in wbc:
            return "อาจมีการอักเสบของระบบทางเดินปัสสาวะ แนะนำให้ตรวจซ้ำ"
        return "ควรตรวจปัสสาวะซ้ำเพื่อติดตามผล"
        
    def is_urine_abnormal(self, test_name, value):
        # ... ตรรกะจาก is_urine_abnormal เดิม ...
        val_str = str(value).strip().lower()
        if is_empty(val_str): return False
        if test_name == "กรด-ด่าง (pH)":
            v = get_float(value); return not (5.0 <= v <= 8.0) if v else True
        if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
            v = get_float(value); return not (1.003 <= v <= 1.030) if v else True
        interp = self._interpret_urine_value(test_name, value).lower()
        if test_name in ["เม็ดเลือดแดง (RBC)", "เม็ดเลือดขาว (WBC)"]:
             return "พบ" in interp
        if test_name in ["น้ำตาล (Sugar)", "โปรตีน (Albumin)"]:
            return "ไม่พบ" not in interp
        if test_name == "สี (Colour)":
            return val_str not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
        return False

    # --- Other Tests Interpretation ---
    def get_stool_interpretation(self):
        exam = self.get_value("Stool exam").lower()
        cs = self.get_value("Stool C/S")
        exam_interp = "ไม่ได้เข้ารับการตรวจ"
        if "normal" in exam: exam_interp = "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
        elif "wbc" in exam: exam_interp = "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
        elif not is_empty(exam): exam_interp = exam

        cs_interp = "ไม่ได้เข้ารับการตรวจ"
        if "ไม่พบ" in cs or "ปกติ" in cs: cs_interp = "ไม่พบการติดเชื้อ"
        elif not is_empty(cs): cs_interp = "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"
        
        return exam_interp, cs_interp

    def get_cxr_interpretation(self):
        cxr_col = get_year_specific_column("CXR", self.year)
        val = self.get_value(cxr_col)
        if val == "-": return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
        if any(k in val.lower() for k in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
            return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
        return val

    def get_ekg_interpretation(self):
        ekg_col = get_year_specific_column("EKG", self.year)
        val = self.get_value(ekg_col)
        if val == "-": return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
        if any(k in val.lower() for k in ["ผิดปกติ", "abnormal", "arrhythmia"]):
            return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
        return val
        
    def get_hepatitis_b_advice(self):
        hbsag = self.get_value("HbsAg").lower()
        hbsab = self.get_value("HbsAb").lower()
        hbcab = self.get_value("HBcAB").lower()
        if hbsag == "-" and hbsab == "-" and hbcab == "-": return None
        if "positive" in hbsag: return "ติดเชื้อไวรัสตับอักเสบบี"
        if "positive" in hbsab and "positive" not in hbsag: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี"
        if "positive" in hbcab and "positive" not in hbsab: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน"
        if all(x == "negative" for x in [hbsag, hbsab, hbcab]):
            return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน"
        return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ"

# ==============================================================================
# 4. REPORT RENDERER CLASS (รวมฟังก์ชันการแสดงผล HTML/CSS)
#    - สร้างฟังก์ชัน Reusable สำหรับการ render ส่วนต่างๆ ของ UI
# ==============================================================================
class ReportRenderer:
    @staticmethod
    def inject_css():
        """รวม CSS ทั้งหมดไว้ในที่เดียว"""
        st.markdown("""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
                body, h1, h2, h3, h4, h5, h6, p, li, a, label, input, select, textarea, button, th, td, div {
                    font-family: 'Sarabun', sans-serif !important;
                }
                .report-header-container h1 { font-size: 1.8rem !important; font-weight: bold; }
                .report-header-container h2 { font-size: 1.2rem !important; color: darkgrey; font-weight: bold; }
                .report-header-container * { line-height: 1.7 !important; margin: 0.2rem 0 !important; padding: 0 !important; }
                .section-header {
                    background-color: #1b5e20; color: white; text-align: center;
                    padding: 0.8rem 0.5rem; font-weight: bold; border-radius: 8px;
                    margin-top: 2rem; margin-bottom: 1rem; font-size: 14px;
                }
                .lab-table {
                    width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 14px;
                }
                .lab-table thead th {
                    background-color: var(--secondary-background-color); padding: 3px; text-align: center; font-weight: bold;
                }
                .lab-table td { padding: 3px; text-align: center; }
                .lab-table .abnormal-row { background-color: rgba(255, 64, 64, 0.25); }
                .info-box {
                    padding: 1.25rem; border-radius: 6px; margin-bottom: 1.5rem;
                    line-height: 1.6; font-size: 14px;
                    background-color: var(--secondary-background-color);
                }
                .advice-box {
                    padding: 1rem; border-radius: 8px; margin-top: 1rem; font-size: 14px;
                }
                .advice-box.normal { background-color: rgba(57, 255, 20, 0.2); }
                .advice-box.warning { background-color: rgba(255, 255, 0, 0.2); }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_section_header(title, subtitle=None):
        full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
        return f"<div class='section-header'>{full_title}</div>"

    @staticmethod
    def render_report_header(check_date):
        st.markdown(f"""
            <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem;">
                <h1>รายงานผลการตรวจสุขภาพ</h1>
                <h2>- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
                <p>ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
                <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
                <p><b>วันที่ตรวจ:</b> {check_date or "-"}</p>
            </div>
            <hr>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_personal_info(person, bmi_advice, bp_full_text):
        st.markdown(f"""
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-top: 24px; text-align: center;">
                <div><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</div>
                <div><b>อายุ:</b> {str(int(get_float(person.get('อายุ')))) if get_float(person.get('อายุ')) else '-'} ปี</div>
                <div><b>เพศ:</b> {person.get('เพศ', '-')}</div>
                <div><b>HN:</b> {str(int(get_float(person.get('HN')))) if get_float(person.get('HN')) else '-'}</div>
                <div><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</div>
            </div>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 32px; margin-top:16px; margin-bottom: 16px; text-align: center;">
                <div><b>น้ำหนัก:</b> {person.get('น้ำหนัก', '-')} กก.</div>
                <div><b>ส่วนสูง:</b> {person.get('ส่วนสูง', '-')} ซม.</div>
                <div><b>รอบเอว:</b> {person.get('รอบเอว', '-')} ซม.</div>
                <div><b>ความดันโลหิต:</b> {bp_full_text}</div>
                <div><b>ชีพจร:</b> {str(int(get_float(person.get('pulse')))) if get_float(person.get('pulse')) else '-'} ครั้ง/นาที</div>
            </div>
            {f"<div style='margin-top: 16px; text-align: center;'><b>คำแนะนำ:</b> {html.escape(bmi_advice)}</div>" if bmi_advice else ""}
        """, unsafe_allow_html=True)

    @staticmethod
    def render_lab_table(title, subtitle, headers, rows):
        header_html = ReportRenderer.render_section_header(title, subtitle)
        table_html = f"{header_html}<table class='lab-table'>"
        table_html += "<colgroup><col style='width: 34%;'><col style='width: 33%;'><col style='width: 33%;'></colgroup>"
        table_html += "<thead><tr>" + "".join(f"<th style='text-align: {'left' if i != 1 else 'center'};'>{h}</th>" for i, h in enumerate(headers)) + "</tr></thead>"
        table_html += "<tbody>"
        for row_data in rows:
            # row_data is expected to be [(label, is_abn), (result, is_abn), (norm, is_abn)]
            is_abn = any(item[1] for item in row_data)
            row_class = "abnormal-row" if is_abn else ""
            table_html += f"<tr class='{row_class}'>"
            table_html += f"<td style='text-align: left;'>{row_data[0][0]}</td>"
            table_html += f"<td>{row_data[1][0]}</td>"
            table_html += f"<td style='text-align: left;'>{row_data[2][0]}</td>"
            table_html += "</tr>"
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
        
    @staticmethod
    def render_grouped_advice(advice_groups):
        output = []
        for title, msgs in advice_groups.items():
            if msgs:
                unique_msgs = list(OrderedDict.fromkeys(msgs))
                output.append(f"<b>{title}:</b> {' '.join(unique_msgs)}")
        
        has_advice = bool(output)
        advice_html = "<br>".join(output) if has_advice else "ไม่พบคำแนะนำเพิ่มเติมจากผลตรวจ"
        css_class = "warning" if has_advice else "normal"

        st.markdown(f"<div class='advice-box {css_class}'>{advice_html}</div>", unsafe_allow_html=True)
        
    @staticmethod
    def render_info_box(title, content):
        header_html = ReportRenderer.render_section_header(title)
        st.markdown(f"{header_html}<div class='info-box'>{html.escape(content)}</div>", unsafe_allow_html=True)
        
    @staticmethod
    def render_doctor_summary(suggestion):
        if is_empty(suggestion):
            suggestion = "<i>ไม่มีคำแนะนำจากแพทย์</i>"
        st.markdown(f"""
            <div style='background-color: #1b5e20; color: white; padding: 1.5rem 2rem; border-radius: 8px; line-height: 1.6; margin-top: 2rem; font-size: 14px;'>
                <b>สรุปความเห็นของแพทย์:</b><br> {suggestion}
            </div>
            <div style='margin-top: 7rem; text-align: right; padding-right: 1rem;'>
                <div style='display: inline-block; text-align: center; width: 340px;'>
                    <div style='border-bottom: 1px dotted #ccc; margin-bottom: 0.5rem; width: 100%;'></div>
                    <div style='white-space: nowrap;'>นายแพทย์นพรัตน์ รัชฎาพร</div>
                    <div style='white-space: nowrap;'>เลขที่ใบอนุญาตผู้ประกอบวิชาชีพเวชกรรม ว.26674</div>
                </div>
            </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# 5. DATA LOADING & MAIN APPLICATION
#    - ส่วนนี้ส่วนใหญ่คงเดิม แต่เรียกใช้ Class ที่สร้างขึ้นใหม่
# ==============================================================================

@st.cache_data(ttl=600)
def load_sqlite_data():
    # ... (โค้ดส่วนนี้เหมือนเดิมทุกประการ) ...
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(response.content)
            db_path = tmp.name
        conn = sqlite3.connect(db_path)
        df_loaded = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()

        df_loaded.columns = df_loaded.columns.str.strip()
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['HN'] = df_loaded['HN'].apply(lambda x: str(int(x)) if pd.notna(x) and isinstance(x, (float, int)) else str(x)).str.strip()
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].apply(normalize_thai_date)
        df_loaded.replace(["-", "None", None], pd.NA, inplace=True)
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        st.stop()

# --- Load data and setup UI ---
df = load_sqlite_data()
st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")
ReportRenderer.inject_css()

# --- Sidebar Search Logic (เหมือนเดิม) ---
st.sidebar.markdown("<h3>ค้นหาข้อมูลผู้เข้ารับบริการ</h3>", unsafe_allow_html=True)
search_query = st.sidebar.text_input("กรอก HN หรือ ชื่อ-สกุล")
if st.sidebar.button("ค้นหา"):
    # ... (ส่วนตรรกะการค้นหาใน session_state เหมือนเดิมทุกประการ) ...
    st.session_state.clear() # Clear all state on new search
    if search_query:
        search_term = search_query.strip()
        mask = (df["HN"] == search_term) if search_term.isdigit() else (df["ชื่อ-สกุล"].str.strip() == search_term)
        query_df = df[mask]
        
        if query_df.empty:
            st.sidebar.error("❌ ไม่พบข้อมูล")
        else:
            st.session_state["search_result"] = query_df
            most_recent_year = sorted(query_df["Year"].dropna().unique().astype(int), reverse=True)[0]
            st.session_state["selected_year"] = most_recent_year
    else:
        st.sidebar.info("กรุณากรอก HN หรือ ชื่อ-สกุล")

# --- Sidebar Year/Date Selection (เหมือนเดิม) ---
if "search_result" in st.session_state:
    results_df = st.session_state["search_result"]
    with st.sidebar:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>เลือกปีและวันที่ตรวจ</h3>", unsafe_allow_html=True)
        
        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        selected_year = st.selectbox(
            "📅 เลือกปี", options=available_years,
            index=available_years.index(st.session_state.get("selected_year", available_years[0])),
            format_func=lambda y: f"พ.ศ. {y}", key="year_select"
        )
        st.session_state["selected_year"] = selected_year
        
        person_year_df = results_df[results_df["Year"] == selected_year].sort_values(by="วันที่ตรวจ", key=lambda x: pd.to_datetime(x, errors='coerce', dayfirst=True), ascending=False)
        exam_dates = person_year_df["วันที่ตรวจ"].dropna().unique().tolist()

        if exam_dates:
            selected_date = st.selectbox("🗓️ เลือกวันที่ตรวจ", options=exam_dates, key="date_select")
            st.session_state["person_row"] = person_year_df[person_year_df["วันที่ตรวจ"] == selected_date].iloc[0].to_dict()
        else:
            st.info("ไม่พบข้อมูลการตรวจสำหรับปีที่เลือก")
            if "person_row" in st.session_state: del st.session_state["person_row"]


# ==============================================================================
# 6. MAIN REPORT DISPLAY (ส่วนแสดงผลหลักที่เรียกใช้ Class ที่สร้างใหม่)
# ==============================================================================
if "person_row" in st.session_state:
    person = st.session_state["person_row"]
    year = int(person.get("Year"))
    sex = str(person.get("เพศ", "ไม่ระบุ")).strip()

    # 1. Initialize Analyzer and Renderer
    analyzer = HealthAnalyzer(person, sex, year)
    renderer = ReportRenderer()

    # 2. Render Header & Personal Info
    renderer.render_report_header(person.get("วันที่ตรวจ", "-"))
    
    # Process basic info for header
    sbp_val = analyzer.get_float_value('SBP')
    dbp_val = analyzer.get_float_value('DBP')
    bp_text = f"{int(sbp_val)}/{int(dbp_val)} ม.ม.ปรอท" if sbp_val and dbp_val else "-"
    bp_interp = analyzer.get_bp_interpretation()
    bp_full_text = f"{bp_text} - {bp_interp}" if bp_interp != "-" else bp_text
    bmi_advice = analyzer.get_bmi_advice()
    
    # Calculate BMI to pass to analyzer (this part is calculation, not analysis)
    try:
        weight = get_float(person.get('น้ำหนัก'))
        height = get_float(person.get('ส่วนสูง'))
        person['bmi'] = weight / ((height / 100) ** 2) if weight and height else None
    except:
        person['bmi'] = None
        
    renderer.render_personal_info(person, bmi_advice, bp_full_text)

    # 3. Render Lab Tables (CBC & Blood Chemistry)
    col1, col2 = st.columns(2)
    with col1:
        cbc_config = ReportConfig.get_cbc_config(sex)
        cbc_rows = []
        for label, col, norm, low, high, *opt in cbc_config:
            higher = opt[0] if opt else False
            val, is_abn = flag_value(person.get(col), low, high, higher)
            cbc_rows.append([(label, is_abn), (val, is_abn), (norm, is_abn)])
        renderer.render_lab_table("ผลตรวจ CBC", "Complete Blood Count", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows)

    with col2:
        blood_config = ReportConfig.BLOOD_CHEM_CONFIG
        blood_rows = []
        for label, col, norm, low, high, *opt in blood_config:
            higher = opt[0] if opt else False
            val, is_abn = flag_value(person.get(col), low, high, higher)
            blood_rows.append([(label, is_abn), (val, is_abn), (norm, is_abn)])
        renderer.render_lab_table("ผลตรวจเลือด", "Blood Chemistry", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows)

    # 4. Render Combined Lab Advice
    advice_groups = analyzer.get_all_lab_advice()
    renderer.render_grouped_advice(advice_groups)
    
    # 5. Render Other Test Sections
    col3, col4 = st.columns(2)
    with col3:
        # Urinalysis
        urine_config = ReportConfig.URINE_CONFIG
        urine_rows = []
        for label, col, norm in urine_config:
            val = person.get(col, "-")
            is_abn = analyzer.is_urine_abnormal(label, val)
            urine_rows.append([(label, is_abn), (val, is_abn), (norm, is_abn)])
        renderer.render_lab_table("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows)
        
        urine_advice = analyzer.get_urine_advice()
        urine_advice_class = "warning" if "ปกติ" not in urine_advice else "normal"
        st.markdown(f"<div class='advice-box {urine_advice_class}'>{urine_advice}</div>", unsafe_allow_html=True)
        
        # Stool Exam
        stool_exam, stool_cs = analyzer.get_stool_interpretation()
        st.markdown(renderer.render_section_header("ผลตรวจอุจจาระ (Stool Examination)"), unsafe_allow_html=True)
        st.markdown(f"""
            <table class='lab-table'>
                <tr><td style='text-align:left; font-weight:bold; width:50%;'>ผลตรวจอุจจาระทั่วไป</td><td style='text-align:left;'>{stool_exam}</td></tr>
                <tr><td style='text-align:left; font-weight:bold; width:50%;'>ผลตรวจอุจจาระเพาะเชื้อ</td><td style='text-align:left;'>{stool_cs}</td></tr>
            </table>
        """, unsafe_allow_html=True)


    with col4:
        # CXR
        renderer.render_info_box("ผลเอกซเรย์ (Chest X-ray)", analyzer.get_cxr_interpretation())
        
        # EKG
        renderer.render_info_box("ผลคลื่นไฟฟ้าหัวใจ (EKG)", analyzer.get_ekg_interpretation())

        # Hepatitis B
        st.markdown(renderer.render_section_header("ผลการตรวจไวรัสตับอักเสบบี", "Viral hepatitis B"), unsafe_allow_html=True)
        hbsag = analyzer.get_value("HbsAg")
        hbsab = analyzer.get_value("HbsAb")
        hbcab = analyzer.get_value("HBcAB")
        hep_b_advice = analyzer.get_hepatitis_b_advice()

        st.markdown(f"""
            <table class='lab-table' style='margin-bottom:1rem;'>
                <thead><tr><th>HBsAg</th><th>HBsAb</th><th>HBcAb</th></tr></thead>
                <tbody><tr><td>{hbsag}</td><td>{hbsab}</td><td>{hbcab}</td></tr></tbody>
            </table>
        """, unsafe_allow_html=True)
        
        if hep_b_advice:
            hep_b_class = "normal" if "มีภูมิคุ้มกัน" in hep_b_advice else "warning"
            st.markdown(f"<div class='advice-box {hep_b_class}'>{hep_b_advice}</div>", unsafe_allow_html=True)

    # 6. Render Doctor's Final Summary
    renderer.render_doctor_summary(analyzer.get_value("DOCTER suggest"))
