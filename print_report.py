import pandas as pd
from datetime import datetime
import html
from collections import OrderedDict
import json

# --- Import a key function from performance_tests ---
from performance_tests import generate_holistic_advice # (ยังคง import ไว้เผื่อใช้ในอนาคต แต่เราจะไม่เรียกใช้)
from print_performance_report import generate_performance_report_html_for_main_report

# ==============================================================================
# NOTE: This file generates the printable health report.
# Refactored to separate CSS and Body generation for Batch Printing.
# ==============================================================================

# --- START OF CHANGE: Add CBC Recommendation Texts ---
RECOMMENDATION_TEXTS_CBC = {
    "C2": "ให้รับประทานอาหารที่มีประโยชน์ เช่น นม ผักใบเขียว ถั่วเมล็ดแห้ง เนื้อสัตว์ ไข่ เป็นต้น พักผ่อนให้เพียงพอ ถ้ามีหน้ามืดวิงเวียน อ่อนเพลียหรือมีไข้ให้พบแพทย์",
    "C4": "ให้ดูแลสุขภาพให้แข็งแรง ออกกำลังกาย ทานอาหารที่มีประโยชน์ ระมัดระวังป้องกันการเกิดแผลเนื่องจากเลือดอาจออกได้ง่ายและหยุดยาก",
    "C6": "ให้ดูแลสุขภาพร่างกายให้แข็งแรง หลีกเลี่ยงการอยู่ในที่ชุมชนที่มีโอกาสสัมผัสเชื้อโรคได้ง่าย และให้ทำการรักษาอย่างต่อเนื่องสม่ำเสมอ",
    "C8": "ให้นำผลตรวจพบแพทย์หาสาเหตุภาวะโลหิตจาง หรือกรณีรู้สาเหตุให้รับการรักษาเดิม",
    "C9": "ให้นำผลตรวจพบแพทย์หาสาเหตุภาวะโลหิตจาง หรือกรณีรู้สาเหตุให้รับการรักษาเดิมและดูแลสุขภาพให้แข็งแรงหลีกเลี่ยงการอยู่ในที่ชุมชนที่มีโอกาสสัมผัสเชื้อโรคได้ง่าย และทำการรักษาอย่างต่อเนื่อง",
    "C10": "ให้นำผลตรวจพบแพทย์หาสาเหตุเกล็ดเลือดสูงกว่าปกติ หรือกรณีรู้สาเหตุให้รับการรักษาเดิม",
    "C13": "ให้รับประทานอาหารที่มีประโยชน์ เช่น นม ผักใบเขียว ถั่วเมล็ดแห้ง เนื้อสัตว์ ไข่ เป็นต้น พักผ่อนให้เพียงพอ หลีกเลี่ยงการอยู่ในที่ชุมชนที่มีโอกาสสัมผัสเชื้อโรคได้ง่าย ดูแลสุขภาพร่างกายให้แข็งแรง ถ้ามีหน้ามืดวิงเวียน อ่อนเพลียหรือมีไข้ให้พบแพทย์",
}
# --- END OF CHANGE ---

# --- START OF CHANGE: Add Urine Recommendation Texts ---
RECOMMENDATION_TEXTS_URINE = {
    "E11": "ให้หลีกเลี่ยงการทานอาหารที่มีน้ำตาลสูง",
    "E4": "แนะนำให้ตรวจปัสสาวะซ้ำ อาจมีการปนเปื้อนของประจำเดือน กรณีตรวจแล้วพบผิดปกติให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม",
    "E10": "แนะนำให้ตรวจปัสสาวะซ้ำ กรณีตรวจแล้วพบผิดปกติให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม",
    "F3": "", # เป็นค่าว่างตามที่คุณแจ้ง
    "E2": "อาจเกิดจากการปนเปื้อนในการเก็บปัสสาวะหรือมีการติดเชื้อในระบบทางเดินปัสสาวะให้ดื่มน้ำมากๆ ไม่ควรกลั้นปัสสาวะ ถ้ามีอาการ ผิดปกติ ปัสสาวะแสบขัด ขุ่น ปวดท้องน้อย ปวดบั้นเอว กลั้นปัสสาวะไม่อยู่ ไข้สูง หนาวสั่น ควรรีบไปพบแพทย์",
}
# --- END OF CHANGE ---


# --- Helper Functions (adapted from app.py for printing) ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(col, person_data):
    """Safely gets a float value from person_data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def flag(val, low=None, high=None, higher_is_better=False):
    """Formats a lab value and flags it if it's abnormal for styling."""
    try:
        val_float = float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return "-", False
    
    formatted_val = f"{int(val_float):,}" if val_float == int(val_float) else f"{val_float:,.1f}"
    
    is_abn = False
    if higher_is_better:
        if low is not None and val_float < low: is_abn = True
    else:
        if low is not None and val_float < low: is_abn = True
        if high is not None and val_float > high: is_abn = True
        
    return formatted_val, is_abn

def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val: return map(float, val.split("-"))
        else: num = float(val); return num, num
    except: return None, None

def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 2: return "ปกติ"
    if high <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 5: return "ปกติ"
    if high <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]: return False
    if test_name == "กรด-ด่าง (pH)":
        try: return not (5.0 <= float(val) <= 8.0)
        except: return True
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try: return not (1.003 <= float(val) <= 1.030)
        except: return True
    if test_name == "เม็ดเลือดแดง (RBC)": return "พบ" in interpret_rbc(val).lower()
    if test_name == "เม็ดเลือดขาว (WBC)": return "พบ" in interpret_wbc(val).lower()
    if test_name == "น้ำตาล (Sugar)": return val.lower() not in ["negative"]
    if test_name == "โปรตีน (Albumin)": return val.lower() not in ["negative", "trace"]
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False

def interpret_stool_exam(val):
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val

def interpret_stool_cs(value):
    if is_empty(value): return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def get_ekg_col_name(year):
    current_thai_year = datetime.now().year + 543
    return "EKG" if year == current_thai_year else f"EKG{str(year)[-2:]}"

def interpret_ekg(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def hepatitis_b_advice(hbsag, hbsab, hbcab):
    hbsag_logic = hbsag.lower()
    hbsab_logic = hbsab.lower()
    hbcab_logic = hbcab.lower()
    if hbcab_logic == "-":
        hbcab_logic = "negative" 

    if "positive" in hbsag_logic: return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab_logic and "positive" not in hbsag_logic: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab_logic and "positive" not in hbsab_logic: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag_logic, hbsab_logic, hbcab_logic]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

def generate_fixed_recommendations(person_data):
    recommendations = []
    try:
        fbs_val = get_float("FBS", person_data)
        if fbs_val is not None and fbs_val > 100:
            recommendations.append("ตรวจพบน้ำตาลในเลือดสูงให้หลีกเลี่ยงการทานขนมหวาน /อาหารหวาน/ผลไม้รสหวานจัด เช่น ทุเรียน เงาะ ลำไย มะม่วงสุก ให้ทานอาหารที่มีเส้นใย เช่นผักต่างๆ ออกกำลังกายสม่ำเสมอ")
    except Exception: pass

    try:
        lipid_str = str(person_data.get("ผลไขมันในเลือด", "")).strip()
        if lipid_str in ["ไขมันในเลือดสูง", "ไขมันในเลือดสูงเล็กน้อย"]:
            recommendations.append("ตรวจพบไขมันในเลือดสูงให้ลดอาหารไขมันสูงเช่น อาหารทอด/ไข่แดง/เครื่องในสัตว์/อาหารทะเล งดสุรา ให้รับประทานผักผลไม้ ออกกำลังกาย ควบคุมน้ำหนักอย่าให้อ้วน")
    except Exception: pass

    try:
        liver_str = str(person_data.get("ผลเอ็มไซม์ตับ", "")).strip()
        if liver_str in ["การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย", "การทำงานของตับสูงกว่าเกณฑ์ปกติ"]:
            recommendations.append("ตรวจพบการทำงานของตับสูงเล็กน้อย งดสุรา/ลดอาหารไขมัน/อาหารที่ย่อยยาก/ใช้ยาในการดูแลของแพทย์ พักผ่อนให้เพียงพอ ถ้ามีอาการตัวเหลือง/ตาเหลือง/เหนื่อยเพลียผิดปกติควรไปพบแพทย์")
    except Exception: pass

    try:
        uric_str = str(person_data.get("ผลยูริค", "")).strip()
        if uric_str in ["กรดยูริคสูงกว่าเกณฑ์ปกติเล็กน้อย", "กรดยูริคสูงกว่าเกณฑ์ปกติ"]:
            recommendations.append("ตรวจพบกรดยูริคสูง(สาเหตุของโรคเก๊าท์) ลดอาหารเครื่องในสัตว์ หน่อไม้ หัวผักกาดขาว ยอดผัก สัตว์ปีกเช่น ไก่ เป็ด ดื่มน้ำมากๆ งดสุรา ถ้ามีปวดข้อ มีก้อนปุ่มตามข้อควรไปพบแพทย์")
    except Exception: pass

    try:
        gfr_str = str(person_data.get("แปลผล GFR", "")).strip()
        if gfr_str == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
            recommendations.append("การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวันและไม่ควรกลั้นปัสสาวะมีอาการบวมผิดปกติให้พบแพทย์")
    except Exception: pass

    return recommendations

def generate_cbc_recommendations(person_data, sex):
    hb = get_float("Hb(%)", person_data)
    wbc = get_float("WBC (cumm)", person_data)
    plt = get_float("Plt (/mm)", person_data)
    
    status_ce = ""
    if hb is not None:
        if sex == "ชาย":
            if hb < 12: status_ce = "พบภาวะโลหิตจาง"
            elif hb < 13: status_ce = "พบภาวะโลหิตจางเล็กน้อย"
            else: status_ce = "ความเข้มข้นของเลือดปกติ"
        elif sex == "หญิง":
            if hb < 11: status_ce = "พบภาวะโลหิตจาง"
            elif hb < 12: status_ce = "พบภาวะโลหิตจางเล็กน้อย"
            else: status_ce = "ความเข้มข้นของเลือดปกติ"

    status_cf = ""
    if wbc is not None:
        if 4000 <= wbc <= 10000: status_cf = "เม็ดเลือดขาวปกติ"
        elif 10000 < wbc < 13000: status_cf = "เม็ดเลือดขาวสูงกว่าเกณฑ์ปกติเล็กน้อย"
        elif wbc >= 13000: status_cf = "เม็ดเลือดขาวสูงกว่าเกณฑ์ปกติ"
        elif 3000 < wbc < 4000: status_cf = "เม็ดเลือดขาวต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        elif wbc <= 3000: status_cf = "เม็ดเลือดขาวต่ำกว่าเกณฑ์ปกติ"
            
    status_cg = ""
    if plt is not None:
        if 150000 <= plt <= 500000: status_cg = "เกร็ดเลือดปกติ"
        elif 500000 < plt < 600000: status_cg = "เกร็ดเลือดสูงกว่าเกณฑ์ปกติเล็กน้อย"
        elif plt >= 600000: status_cg = "เกร็ดเลือดสูงกว่าเกณฑ์ปกติ"
        elif 100000 <= plt < 150000: status_cg = "เกร็ดเลือดต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        elif plt < 100000: status_cg = "เกร็ดเลือดต่ำกว่าเกณฑ์ปกติ"
        
    if not status_ce and not status_cf and not status_cg:
        return {'summary': "ไม่ได้ตรวจ", 'status_ce': "", 'status_cf': "", 'status_cg': ""}

    status_cd = "ความสมบูรณ์ของเลือดปกติ"
    if ("พบภาวะโลหิตจาง" in status_ce) or \
       ("เม็ดเลือดขาว" in status_cf and "ปกติ" not in status_cf) or \
       ("เกร็ดเลือด" in status_cg and "ปกติ" not in status_cg):
        status_cd = "พบความสมบูรณ์ของเลือดผิดปกติ"

    advice_text = ""
    if status_ce == "ความเข้มข้นของเลือดปกติ" and status_cf == "เม็ดเลือดขาวปกติ" and status_cg == "เกร็ดเลือดปกติ":
        advice_text = ""
    elif status_ce == "พบภาวะโลหิตจาง" and status_cf == "เม็ดเลือดขาวปกติ" and status_cg == "เกร็ดเลือดปกติ":
        advice_text = RECOMMENDATION_TEXTS_CBC["C8"]
    elif status_ce == "พบภาวะโลหิตจาง" and ("เม็ดเลือดขาวต่ำ" in status_cf or "เม็ดเลือดขาวสูง" in status_cf):
        advice_text = RECOMMENDATION_TEXTS_CBC["C9"]
    elif status_ce == "พบภาวะโลหิตจางเล็กน้อย" and status_cf == "เม็ดเลือดขาวปกติ" and status_cg == "เกร็ดเลือดปกติ":
        advice_text = RECOMMENDATION_TEXTS_CBC["C2"]
    elif status_ce == "ความเข้มข้นของเลือดปกติ" and ("เม็ดเลือดขาวต่ำ" in status_cf or "เม็ดเลือดขาวสูง" in status_cf):
        advice_text = RECOMMENDATION_TEXTS_CBC["C6"]
    elif "เกร็ดเลือดต่ำ" in status_cg:
        advice_text = RECOMMENDATION_TEXTS_CBC["C4"]
    elif status_cg == "เกร็ดเลือดสูงกว่าเกณฑ์ปกติ":
        advice_text = RECOMMENDATION_TEXTS_CBC["C10"]
    elif status_ce == "พบภาวะโลหิตจางเล็กน้อย" and ("เม็ดเลือดขาวต่ำ" in status_cf or "เม็ดเลือดขาวสูง" in status_cf) and status_cg == "เกร็ดเลือดปกติ":
        advice_text = RECOMMENDATION_TEXTS_CBC["C13"]
    elif status_ce == "พบภาวะโลหิตจางเล็กน้อย" and status_cf == "เม็ดเลือดขาวปกติ" and status_cg == "เกร็ดเลือดสูงกว่าเกณฑ์ปกติเล็กน้อย":
        advice_text = RECOMMENDATION_TEXTS_CBC["C2"]

    summary_parts = []
    summary_parts.append(f"<li>{html.escape(status_cd)}</li>")
    if advice_text:
        summary_parts.append(f"<li>{html.escape(advice_text)}</li>")
    
    summary_html = f"<ul style='margin: 0; padding-left: 20px;'>{''.join(summary_parts)}</ul>"
        
    return {'summary': summary_html, 'status_ce': status_ce, 'status_cf': status_cf, 'status_cg': status_cg}

def generate_urine_recommendations(person_data, sex):
    alb_raw = str(person_data.get("Alb", "")).strip().lower()
    sugar_raw = str(person_data.get("sugar", "")).strip().lower()
    rbc_raw = str(person_data.get("RBC1", "")).strip().lower()
    wbc_raw = str(person_data.get("WBC1", "")).strip().lower()
    
    status_ct = ""
    if is_empty(alb_raw): status_ct = ""
    elif alb_raw == "negative": status_ct = "ไม่พบโปรตีนในปัสสาวะ"
    elif alb_raw in ["trace", "2+", "1+"]: status_ct = "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif alb_raw == "3+": status_ct = "พบโปรตีนในปัสสาวะ"
        
    status_cu = ""
    if is_empty(sugar_raw): status_cu = ""
    elif sugar_raw == "negative": status_cu = "ไม่พบน้ำตาลในปัสสาวะ"
    elif sugar_raw == "trace": status_cu = "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif sugar_raw in ["1+", "2+", "3+", "4+", "5+", "6+"]: status_cu = "พบน้ำตาลในปัสสาวะ"

    status_cv = ""
    if is_empty(rbc_raw): status_cv = ""
    elif rbc_raw in ["0-1", "negative", "1-2", "2-3", "3-5"]: status_cv = "เม็ดเลือดแดงในปัสสาวะปกติ"
    elif rbc_raw in ["5-10", "10-20"]: status_cv = "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    else: status_cv = "พบเม็ดเลือดแดงในปัสสาวะ"
        
    status_cw = ""
    if is_empty(wbc_raw): status_cw = ""
    elif wbc_raw in ["0-1", "negative", "1-2", "2-3", "3-5"]: status_cw = "เม็ดเลือดขาวในปัสสาวะปกติ"
    elif wbc_raw in ["5-10", "10-20"]: status_cw = "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else: status_cw = "พบเม็ดเลือดขาวในปัสสาวะ"

    if not status_ct and not status_cu and not status_cv and not status_cw:
        return {'summary': "ไม่ได้ตรวจ", 'status_ct': "", 'status_cu': "", 'status_cv': "", 'status_cw': ""}

    is_abnormal = False
    if status_ct == "พบโปรตีนในปัสสาวะ": is_abnormal = True
    if "น้ำตาล" in status_cu and "ไม่พบ" not in status_cu: is_abnormal = True
    if "เม็ดเลือดแดง" in status_cv and "ปกติ" not in status_cv: is_abnormal = True
    if status_cw == "พบเม็ดเลือดขาวในปัสสาวะ": is_abnormal = True
    
    status_cs = "ผลปัสสาวะผิดปกติ" if is_abnormal else "ปัสสาวะปกติ"

    advice_text = ""
    status_ct_ok = status_ct in ["ไม่พบโปรตีนในปัสสาวะ", "พบโปรตีนในปัสสาวะเล็กน้อย"]
    status_cu_ok = status_cu == "ไม่พบน้ำตาลในปัสสาวะ"
    status_cv_ok = status_cv == "เม็ดเลือดแดงในปัสสาวะปกติ"
    status_cw_ok = status_cw == "เม็ดเลือดขาวในปัสสาวะปกติ"

    if status_ct_ok and status_cu_ok and status_cv_ok and status_cw_ok:
        advice_text = ""
    elif "น้ำตาล" in status_cu and "ไม่พบ" not in status_cu:
        advice_text = RECOMMENDATION_TEXTS_URINE["E11"]
    elif sex == "หญิง" and status_ct_ok and status_cu_ok and ("เม็ดเลือดแดง" in status_cv and "ปกติ" not in status_cv) and status_cw_ok:
        advice_text = RECOMMENDATION_TEXTS_URINE["E4"]
    elif sex == "ชาย" and status_ct_ok and status_cu_ok and ("เม็ดเลือดแดง" in status_cv and "ปกติ" not in status_cv) and status_cw_ok:
        advice_text = RECOMMENDATION_TEXTS_URINE["E10"]
    elif status_ct_ok and status_cu_ok and status_cv_ok and status_cw == "พบเม็ดเลือดขาวในปัสสาวะ":
        advice_text = RECOMMENDATION_TEXTS_URINE["F3"]
    elif status_ct_ok and status_cu_ok and status_cv_ok and status_cw == "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย":
        advice_text = RECOMMENDATION_TEXTS_URINE["E2"]
    
    summary_parts = []
    summary_parts.append(f"<li>{html.escape(status_cs)}</li>")
    if advice_text:
        summary_parts.append(f"<li>{html.escape(advice_text)}</li>")
    
    summary_html = f"<ul style='margin: 0; padding-left: 20px;'>{''.join(summary_parts)}</ul>"
        
    return {'summary': summary_html, 'status_ct': status_ct, 'status_cu': status_cu, 'status_cv': status_cv, 'status_cw': status_cw}

def generate_doctor_opinion(person_data, sex, cbc_statuses, urine_statuses):
    opinion_parts = []

    sbp = get_float("SBP", person_data)
