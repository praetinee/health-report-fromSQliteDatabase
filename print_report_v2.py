import pandas as pd
import html
from datetime import datetime
import numpy as np

# --- 1. ส่วน Import Logic การแปลผล (จาก print_report.py) ---
try:
    from performance_tests import (
        interpret_audiogram, interpret_lung_capacity, 
        interpret_cxr, interpret_ekg, interpret_urine, 
        interpret_stool, interpret_hepatitis, interpret_vision
    )
except ImportError:
    # Fallback functions
    def interpret_cxr(v): return (v if v else "-"), False
    def interpret_ekg(v): return (v if v else "-"), False
    def interpret_vision(*args): return "-","-","-"
    def interpret_audiogram(*args): return {"summary": {"right": "-", "left": "-"}}
    def interpret_lung_capacity(*args): return "-", "-", "-"
    def interpret_urine(k, v): return False 

# --- 2. ค่าคงที่และข้อความแนะนำ (จาก print_report.py) ---
RECOMMENDATION_TEXTS_CBC = {
    "C2": "ให้รับประทานอาหารที่มีประโยชน์ เช่น นม ผักใบเขียว ถั่วเมล็ดแห้ง เนื้อสัตว์ ไข่ เป็นต้น พักผ่อนให้เพียงพอ ถ้ามีหน้ามืดวิงเวียน อ่อนเพลียหรือมีไข้ให้พบแพทย์",
    "C4": "ให้ดูแลสุขภาพให้แข็งแรง ออกกำลังกาย ทานอาหารที่มีประโยชน์ ระมัดระวังป้องกันการเกิดแผลเนื่องจากเลือดอาจออกได้ง่ายและหยุดยาก",
    "C6": "ให้ดูแลสุขภาพร่างกายให้แข็งแรง หลีกเลี่ยงการอยู่ในที่ชุมชนที่มีโอกาสสัมผัสเชื้อโรคได้ง่าย และให้ทำการรักษาอย่างต่อเนื่องสม่ำเสมอ",
    "C8": "ให้นำผลตรวจพบแพทย์หาสาเหตุภาวะโลหิตจาง หรือกรณีรู้สาเหตุให้รับการรักษาเดิม",
    "C9": "ให้นำผลตรวจพบแพทย์หาสาเหตุภาวะโลหิตจาง หรือกรณีรู้สาเหตุให้รับการรักษาเดิมและดูแลสุขภาพให้แข็งแรงหลีกเลี่ยงการอยู่ในที่ชุมชนที่มีโอกาสสัมผัสเชื้อโรคได้ง่าย และทำการรักษาอย่างต่อเนื่อง",
    "C10": "ให้นำผลตรวจพบแพทย์หาสาเหตุเกล็ดเลือดสูงกว่าปกติ หรือกรณีรู้สาเหตุให้รับการรักษาเดิม",
    "C13": "ให้รับประทานอาหารที่มีประโยชน์ เช่น นม ผักใบเขียว ถั่วเมล็ดแห้ง เนื้อสัตว์ ไข่ เป็นต้น พักผ่อนให้เพียงพอ หลีกเลี่ยงการอยู่ในที่ชุมชนที่มีโอกาสสัมผัสเชื้อโรคได้ง่าย ดูแลสุขภาพร่างกายให้แข็งแรง ถ้ามีหน้ามืดวิงเวียน อ่อนเพลียหรือมีไข้ให้พบแพทย์",
}

RECOMMENDATION_TEXTS_URINE = {
    "E11": "ให้หลีกเลี่ยงการทานอาหารที่มีน้ำตาลสูง",
    "E4": "แนะนำให้ตรวจปัสสาวะซ้ำ อาจมีการปนเปื้อนของประจำเดือน กรณีตรวจแล้วพบผิดปกติให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม",
    "E10": "แนะนำให้ตรวจปัสสาวะซ้ำ กรณีตรวจแล้วพบผิดปกติให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม",
    "F3": "",
    "E2": "อาจเกิดจากการปนเปื้อนในการเก็บปัสสาวะหรือมีการติดเชื้อในระบบทางเดินปัสสาวะให้ดื่มน้ำมากๆ ไม่ควรกลั้นปัสสาวะ ถ้ามีอาการ ผิดปกติ ปัสสาวะแสบขัด ขุ่น ปวดท้องน้อย ปวดบั้นเอว กลั้นปัสสาวะไม่อยู่ ไข้สูง หนาวสั่น ควรรีบไปพบแพทย์",
}

# --- 3. Helper Functions (จาก print_report.py) ---

def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(col, person_data):
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

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
    hbsag_logic = str(hbsag).lower()
    hbsab_logic = str(hbsab).lower()
    hbcab_logic = str(hbcab).lower()
    if hbcab_logic == "-": hbcab_logic = "negative" 

    if "positive" in hbsag_logic: return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab_logic and "positive" not in hbsag_logic: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab_logic and "positive" not in hbsab_logic: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag_logic, hbsab_logic, hbcab_logic]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"

# --- 4. Logic Functions (จาก print_report.py) ---

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

    # Modified for HTML output
    summary_parts = []
    if status_cd != "ความสมบูรณ์ของเลือดปกติ":
        summary_parts.append(f"<b>สรุป:</b> {status_cd}")
    if advice_text:
        summary_parts.append(f"<b>คำแนะนำ:</b> {advice_text}")
    
    summary_html = "<br>".join(summary_parts) if summary_parts else ""
        
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
        return {'summary': "", 'status_ct': "", 'status_cu': "", 'status_cv': "", 'status_cw': ""}

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
    
    summary_html = ""
    if advice_text:
        summary_html = f"<b>คำแนะนำ:</b> {advice_text}"
        
    return {'summary': summary_html, 'status_ct': status_ct, 'status_cu': status_cu, 'status_cv': status_cv, 'status_cw': status_cw}

def generate_doctor_opinion(person_data, sex, cbc_statuses, urine_statuses):
    opinion_parts = []

    sbp = get_float("SBP", person_data)
    dbp = get_float("DBP", person_data)
    if sbp is not None and dbp is not None:
        if 140 <= sbp < 160 or 90 <= dbp < 100:
             opinion_parts.append("ความดันโลหิตสูงเล็กน้อย")
        elif sbp >= 160 or dbp >= 100:
             opinion_parts.append("ความดันโลหิตสูง")

    fbs = get_float("FBS", person_data)
    if fbs is not None:
        if 100 <= fbs < 106: opinion_parts.append("น้ำตาลในเลือดเริ่มสูงเล็กน้อย")
        elif 106 <= fbs < 126: opinion_parts.append("น้ำตาลในเลือดสูงเล็กน้อย")
        elif fbs >= 126: opinion_parts.append("น้ำตาลในเลือดสูง")

    lipid_overall_status = str(person_data.get("ผลไขมันในเลือด", "")).strip()
    if lipid_overall_status != "ปกติ":
        chol_raw = get_float("CHOL", person_data)
        tgl_raw = get_float("TGL", person_data)
        ldl_raw = get_float("LDL", person_data)
        has_lipid_values = not (is_empty(chol_raw) and is_empty(tgl_raw))
        
        if has_lipid_values:
            is_high = (chol_raw is not None and chol_raw > 250) or \
                      (tgl_raw is not None and tgl_raw > 150) or \
                      (ldl_raw is not None and ldl_raw > 180)
            is_normal_raw = (chol_raw is not None and chol_raw <= 200) and \
                            (tgl_raw is not None and tgl_raw <= 150)
            
            if is_high:
                opinion_parts.append("ไขมันในเลือดสูง")
            elif is_normal_raw:
                pass 
            else:
                opinion_parts.append("ไขมันในเลือดสูงเล็กน้อย")
        elif lipid_overall_status == "ไขมันในเลือดสูง":
             opinion_parts.append("ไขมันในเลือดสูง")
        elif lipid_overall_status == "ไขมันในเลือดสูงเล็กน้อย":
             opinion_parts.append("ไขมันในเลือดสูงเล็กน้อย")

    alp = get_float("ALP", person_data)
    sgot = get_float("SGOT", person_data)
    sgpt = get_float("SGPT", person_data)
    if (alp is not None and alp > 120) or \
       (sgot is not None and sgot > 36) or \
       (sgpt is not None and sgpt > 40):
        opinion_parts.append("การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย")

    uric = get_float("Uric Acid", person_data)
    if uric is not None and uric > 7.2:
        opinion_parts.append("กรดยูริคสูงกว่าเกณฑ์ปกติเล็กน้อย")

    gfr = get_float("GFR", person_data)
    if gfr is not None and gfr < 60:
        opinion_parts.append("การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย")

    if cbc_statuses.get('status_ce') == "พบภาวะโลหิตจาง":
        opinion_parts.append("พบภาวะโลหิตจาง")

    if cbc_statuses.get('status_cf') in ["เม็ดเลือดขาวสูงกว่าเกณฑ์ปกติ", "เม็ดเลือดขาวต่ำกว่าเกณฑ์ปกติ"]:
        opinion_parts.append("เม็ดเลือดขาวผิดปกติ")

    if cbc_statuses.get('status_cg') in ["เกร็ดเลือดสูงกว่าเกณฑ์ปกติ", "เกร็ดเลือดต่ำกว่าเกณฑ์ปกติ"]:
        opinion_parts.append("เกร็ดเลือดผิดปกติ")

    if urine_statuses.get('status_ct') == "พบโปรตีนในปัสสาวะ":
        opinion_parts.append("พบโปรตีนในปัสสาวะ")

    if urine_statuses.get('status_cu') == "พบน้ำตาลในปัสสาวะ":
        opinion_parts.append("พบน้ำตาลในปัสสาวะ")

    if urine_statuses.get('status_cv') == "พบเม็ดเลือดแดงในปัสสาวะ":
        opinion_parts.append("พบเม็ดเลือดแดงในปัสสาวะ")

    if urine_statuses.get('status_cw') == "พบเม็ดเลือดขาวในปัสสาวะ":
        opinion_parts.append("พบเม็ดเลือดขาวในปัสสาวะ")

    doctor_suggest = str(person_data.get("DOCTER suggest", "")).strip()
    if not is_empty(doctor_suggest):
        opinion_parts.append(doctor_suggest)

    if not opinion_parts:
        return "สุขภาพโดยรวมปกติ (Normal)"

    return ", ".join(filter(None, opinion_parts))

# --- 5. CSS Styling (Formal & Luxurious V2 Style + AutoFit) ---
def get_single_page_style():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        @page {
            size: A4;
            margin: 0; 
        }
        
        body {
            font-family: 'Sarabun', sans-serif;
            font-size: 10px; /* Reduced base font for autofit */
            line-height: 1.25;
            color: #000;
            background: #fff;
            margin: 0;
            padding: 0;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }

        .report-container {
            width: 210mm;
            height: 296mm;
            padding: 8mm 12mm; /* Tight padding */
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            overflow: hidden; /* Ensure single page */
            page-break-after: always;
            zoom: 0.95; /* Slight zoom out to ensure fit */
        }

        /* --- Header --- */
        .header-section {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 2px solid #004d40;
            padding-bottom: 5px;
            margin-bottom: 8px;
        }
        .header-left h1 {
            margin: 0;
            font-size: 20px;
            color: #004d40;
            font-weight: 700;
            text-transform: uppercase;
        }
        .header-left p {
            margin: 2px 0 0 0;
            font-size: 11px;
            color: #333;
        }
        .header-right { text-align: right; }
        .patient-name {
            font-size: 16px;
            font-weight: 700;
            color: #000;
            margin: 0;
        }
        .patient-info-row {
            font-size: 11px;
            margin-top: 2px;
            color: #333;
        }
        .info-pill {
            display: inline-block;
            background: #f0f0f0;
            border: 1px solid #ccc;
            padding: 0px 4px;
            border-radius: 3px;
            font-weight: 600;
            margin-left: 4px;
        }

        /* --- Vitals --- */
        .vitals-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 5px;
            background-color: #f1f8e9;
            border: 1px solid #8bc34a;
            border-radius: 4px;
            padding: 6px;
            margin-bottom: 10px;
        }
        .vital-box {
            text-align: center;
            border-right: 1px solid #c5e1a5;
        }
        .vital-box:last-child { border-right: none; }
        .vital-title { font-size: 9px; font-weight: 700; color: #558b2f; text-transform: uppercase; }
        .vital-data { font-size: 12px; font-weight: 700; color: #000; margin-top: 1px; }
        .vital-u { font-size: 9px; font-weight: 400; color: #555; }

        /* --- Content Layout --- */
        .main-content {
            display: flex;
            gap: 10px;
            flex-grow: 1;
        }
        .col-left { width: 50%; display: flex; flex-direction: column; gap: 8px; }
        .col-right { width: 50%; display: flex; flex-direction: column; gap: 8px; }

        /* --- Tables --- */
        .result-group {
            border: 1px solid #000;
            border-radius: 0;
            overflow: hidden;
        }
        .group-head {
            background-color: #004d40;
            color: #fff;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            border-bottom: 1px solid #000;
        }
        .res-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 9.5px; /* Smaller font for table content */
        }
        .res-table th {
            background-color: #e0e0e0;
            color: #000;
            font-weight: 700;
            text-align: left;
            padding: 3px 6px;
            border-bottom: 1px solid #999;
        }
        .res-table td {
            padding: 2px 6px;
            border-bottom: 1px solid #ddd;
            vertical-align: middle;
            color: #000;
            height: 16px; /* Fixed minimal row height */
        }
        .res-table tr:nth-child(even) { background-color: #f9f9f9; }
        .res-table tr:last-child td { border-bottom: none; }

        .v-norm { color: #2e7d32; }
        .v-abn { color: #d50000; font-weight: 800; }
        .v-plain { color: #000; }
        
        .footer-note {
            padding: 4px 6px;
            background-color: #fffde7;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #555;
            font-style: italic;
        }

        /* --- Footer & Signature --- */
        .footer-wrap {
            margin-top: auto;
            border: 1px solid #000;
            display: flex;
            flex-direction: column;
            background-color: #fff;
        }
        .f-row {
            display: flex;
            border-bottom: 1px solid #000;
        }
        .f-row:last-child { border-bottom: none; }
        .f-head {
            width: 120px;
            background-color: #e0f2f1;
            padding: 6px;
            font-weight: 700;
            border-right: 1px solid #000;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            font-size: 10px;
        }
        .f-body {
            flex: 1;
            padding: 6px;
            font-size: 10px;
            line-height: 1.3;
        }
        .f-body ul { margin: 0; padding-left: 15px; }
        .f-body li { margin-bottom: 2px; }

        .signature-section {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
        }
        .sig-block {
            text-align: center;
            width: 180px;
        }
        .sig-line {
            border-bottom: 1px solid #000;
            height: 25px;
            margin-bottom: 4px;
        }
        .sig-name { font-weight: 700; font-size: 11px; }
        .sig-pos { font-size: 10px; color: #444; }
    </style>
    """

# --- 6. HTML Rendering Functions ---

def render_table_group(title, headers, rows, footer_html=None):
    html = f"""
    <div class="result-group">
        <div class="group-head">{title}</div>
        <table class="res-table">
            <thead>
                <tr>
                    <th style="width: 45%;">{headers[0]}</th>
                    <th style="width: 25%; text-align: center;">{headers[1]}</th>
                    <th style="width: 30%; text-align: center;">{headers[2]}</th>
                </tr>
            </thead>
            <tbody>
    """
    for row in rows:
        label_t, val_t, norm_t = row
        label = label_t[0]
        val = val_t[0]
        is_abn = val_t[1]
        norm = norm_t[0]
        
        css = "v-abn" if is_abn else "v-plain"
        
        html += f"""
        <tr>
            <td>{label}</td>
            <td style="text-align: center;" class="{css}">{val}</td>
            <td style="text-align: center;">{norm}</td>
        </tr>
        """
    html += "</tbody></table>"
    if footer_html:
        html += f"<div class='footer-note'>{footer_html}</div>"
    html += "</div>"
    return html

def render_special_group(title, items):
    html = f"""
    <div class="result-group">
        <div class="group-head">{title}</div>
        <table class="res-table">
    """
    for label, val, is_abn in items:
        css = "v-abn" if is_abn else "v-norm"
        if val in ["-", "N/A", "ไม่ได้ตรวจ"]: css = "v-plain"
        
        html += f"""
        <tr>
            <td style="width: 40%; font-weight: 600;">{label}</td>
            <td style="width: 60%; text-align: right;" class="{css}">{val}</td>
        </tr>
        """
    html += "</table></div>"
    return html

def render_vitals_grid(person):
    def g(k, u=""):
        v = get_float(k, person)
        return f"{v} <span class='vital-u'>{u}</span>" if v else "-"
    
    sbp, dbp = get_float("SBP", person), get_float("DBP", person)
    bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    
    w, h = get_float("น้ำหนัก", person), get_float("ส่วนสูง", person)
    bmi = w / ((h/100)**2) if w and h else 0
    
    return f"""
    <div class="vitals-grid">
        <div class="vital-box"><div class="vital-title">Weight</div><div class="vital-data">{g('น้ำหนัก', 'kg')}</div></div>
        <div class="vital-box"><div class="vital-title">Height</div><div class="vital-data">{g('ส่วนสูง', 'cm')}</div></div>
        <div class="vital-box"><div class="vital-title">BMI</div><div class="vital-data">{bmi:.1f} <span class="vital-u">kg/m²</span></div></div>
        <div class="vital-box"><div class="vital-title">Waist</div><div class="vital-data">{person.get('รอบเอว', '-') or '-'} <span class="vital-u">cm</span></div></div>
        <div class="vital-box"><div class="vital-title">BP</div><div class="vital-data">{bp} <span class="vital-u">mmHg</span></div></div>
        <div class="vital-box"><div class="vital-title">Pulse</div><div class="vital-data">{g('pulse', 'bpm')}</div></div>
    </div>
    """

def render_report_body(person_data, all_history_df=None):
    # --- Data Prep Logic (Identical to print_report.py) ---
    sex = person_data.get("เพศ", "ชาย")
    year = person_data.get("Year", datetime.now().year + 543)
    
    # 1. CBC
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [
        ("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12", hb_low, None),
        ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39, หญิง > 36", hct_low, None),
        ("เม็ดเลือดขาว (WBC)", "WBC (cumm)", "4,000 - 10,000", 4000, 10000),
        ("นิวโทรฟิล (Neu)", "Ne (%)", "43 - 70%", 43, 70),
        ("ลิมโฟไซต์ (Lym)", "Ly (%)", "20 - 44%", 20, 44),
        ("เกล็ดเลือด (Plt)", "Plt (/mm)", "150,000 - 500,000", 150000, 500000)
    ]
    cbc_rows = [[(label,0), flag(get_float(col, person_data), low, high), (norm,0)] for label, col, norm, low, high in cbc_config]
    
    # 2. Metabolic & Organ (Blood Chem)
    blood_config = [
        ("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106", 74, 106),
        ("กรดยูริก (Uric Acid)", "Uric Acid", "< 7.2", None, 7.2),
        ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17", 0.5, 1.17),
        ("การกรองไต (GFR)", "GFR", "> 60", 60, None, True),
        ("เอนไซม์ตับ (SGOT)", "SGOT", "< 37", None, 37),
        ("เอนไซม์ตับ (SGPT)", "SGPT", "< 41", None, 41),
        ("คลอเรสเตอรอล (Chol)", "CHOL", "< 200", None, 200),
        ("ไตรกลีเซอไรด์ (Trig)", "TGL", "< 150", None, 150),
        ("ไขมันดี (HDL)", "HDL", "> 40", 40, None, True),
        ("ไขมันเลว (LDL)", "LDL", "< 130", None, 130)
    ]
    blood_rows = [[(label,0), flag(get_float(col, person_data), low, high, opt[0] if opt else False), (norm,0)] for label, col, norm, low, high, *opt in blood_config]

    # 3. Urinalysis
    urine_config = [
        ("Sugar", "sugar", "Negative"),
        ("Protein", "Alb", "Negative"),
        ("RBC", "RBC1", "0 - 2"),
        ("WBC", "WBC1", "0 - 5")
    ]
    urine_rows = [[(l,0), (person_data.get(k,"-"), is_urine_abnormal(l, person_data.get(k), n)), (n,0)] for l,k,n in urine_config]
    
    # 4. Special Tests Interpretation
    cxr = interpret_cxr(person_data.get(f"CXR{str(year)[-2:]}", person_data.get("CXR")))[0]
    ekg = interpret_ekg(person_data.get(f"EKG{str(year)[-2:]}", person_data.get("EKG")))[0]
    vis, col_b, _ = interpret_vision(person_data.get('สรุปเหมาะสมกับงาน',''), person_data.get('Color_Blind',''))
    hear_res = interpret_audiogram(person_data, all_history_df)
    hear = f"R:{hear_res['summary']['right']} L:{hear_res['summary']['left']}"
    lung, _, _ = interpret_lung_capacity(person_data)
    lung = lung.replace("สมรรถภาพปอด","").strip() or "-"
    
    # Stool
    stool_val = interpret_stool_exam(person_data.get("Stool exam", ""))
    
    # Hepatitis
    hbsag_curr = person_data.get("HbsAg", "")
    hbsab_curr = person_data.get("HbsAb", "")
    hbcab_curr = person_data.get("HBcAb", "")
    if not is_empty(hbsag_curr):
        hep_adv, _ = hepatitis_b_advice(hbsag_curr, hbsab_curr, hbcab_curr)
    else:
        hep_adv = "ไม่ได้ตรวจ"

    sp_items = [
        ("Chest X-Ray", cxr, "ผิดปกติ" in cxr),
        ("EKG", ekg, "ผิดปกติ" in ekg),
        ("Vision", vis, "ผิดปกติ" in vis),
        ("Hearing", hear, "ผิดปกติ" in hear),
        ("Lung Function", lung, "ผิดปกติ" in lung),
        ("Stool Exam", stool_val, "พบ" in stool_val),
        ("Hepatitis B", hep_adv, "ติดเชื้อ" in hep_adv or "ไม่มีภูมิ" in hep_adv)
    ]

    # --- Recommendations Logic ---
    rec_list = generate_fixed_recommendations(person_data)
    rec_html = "<ul>" + "".join([f"<li>{r}</li>" for r in rec_list]) + "</ul>" if rec_list else "<ul><li>ดูแลสุขภาพตามปกติ</li></ul>"
    
    cbc_res = generate_cbc_recommendations(person_data, sex)
    urine_res = generate_urine_recommendations(person_data, sex)
    op = generate_doctor_opinion(person_data, sex, cbc_res, urine_res)
    if is_empty(op) or op == "-": op = "สุขภาพโดยรวมปกติ"

    # --- Footer Notes ---
    cbc_note = cbc_res.get('summary', '')
    urine_note = urine_res.get('summary', '')

    # --- HTML Assembly (V2 Layout) ---
    return f"""
    <div class="report-container">
        <div class="header-section">
            <div class="header-left">
                <h1>MEDICAL REPORT</h1>
                <p>รายงานผลการตรวจสุขภาพประจำปี {year}</p>
            </div>
            <div class="header-right">
                <div class="patient-name">{person_data.get('ชื่อ-สกุล', '-')}</div>
                <div class="patient-info-row">
                    HN: <b>{person_data.get('HN', '-')}</b> 
                    <span class="info-pill">{int(get_float('อายุ', person_data) or 0)} ปี</span>
                    <span class="info-pill">{person_data.get('หน่วยงาน', '-')}</span>
                </div>
            </div>
        </div>

        {render_vitals_grid(person_data)}

        <div class="main-content">
            <div class="col-left">
                {render_table_group("HEMATOLOGY", ["TEST", "RESULT", "NORMAL"], cbc_rows, cbc_note)}
                {render_table_group("URINALYSIS", ["TEST", "RESULT", "NORMAL"], urine_rows, urine_note)}
                {render_special_group("SPECIAL EXAMINATIONS", sp_items)}
            </div>
            <div class="col-right">
                {render_table_group("BLOOD CHEMISTRY", ["TEST", "RESULT", "NORMAL"], blood_rows)}
                
                <div class="footer-wrap">
                     <div class="f-row">
                        <div class="f-head">DOCTOR'S OPINION</div>
                        <div class="f-body">{op}</div>
                    </div>
                    <div class="f-row" style="flex: 1;">
                        <div class="f-head">RECOMMENDATIONS</div>
                        <div class="f-body">{rec_html}</div>
                    </div>
                </div>
                
                <div class="signature-section">
                    <div class="sig-block">
                        <div class="sig-line"></div>
                        <div class="sig-name">นายแพทย์นพรัตน์ รัชฎาพร</div>
                        <div class="sig-pos">แพทย์อาชีวเวชศาสตร์ (ว.26674)</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

def generate_single_page_report(person_data, all_history_df=None):
    """
    สร้างรายงานหน้าเดียวฉบับสมบูรณ์
    """
    style = get_single_page_style()
    body = render_report_body(person_data, all_history_df)
    
    return f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Health Report {person_data.get('HN')}</title>
        {style}
    </head>
    <body>
        {body}
    </body>
    </html>
    """
