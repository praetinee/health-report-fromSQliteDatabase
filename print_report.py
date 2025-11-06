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
# The header is compact, while the body retains the original layout.
# ==============================================================================

# --- START OF CHANGE: Add CBC Recommendation Texts ---
# เก็บข้อความคำแนะนำ CBC จาก Google Sheet
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
    # --- START OF CHANGE: Treat '-' as 'negative' for HBcAb logic ---
    hbsag_logic = hbsag.lower()
    hbsab_logic = hbsab.lower()
    hbcab_logic = hbcab.lower()
    if hbcab_logic == "-":
        hbcab_logic = "negative" # แปลงค่า '-' เป็น 'negative' สำหรับการเปรียบเทียบตรรกะ

    if "positive" in hbsag_logic: return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab_logic and "positive" not in hbsag_logic: return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab_logic and "positive" not in hbsab_logic: return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag_logic, hbsab_logic, hbcab_logic]): return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"
    # --- END OF CHANGE ---

# --- START OF CHANGE: Modified function to return a list ---
def generate_fixed_recommendations(person_data):
    """
    สร้างรายการคำแนะนำแบบคงที่ตามตรรกะ Google Sheet ที่กำหนด
    Returns:
        list: รายการ (list) ของคำแนะนำ (strings)
    """
    recommendations = []

    # 1. คำแนะนำ chem1 (น้ำตาล)
    # เงื่อนไข: DF (FBS) > 100
    try:
        fbs_val = get_float("FBS", person_data)
        if fbs_val is not None and fbs_val > 100:
            recommendations.append("ตรวจพบน้ำตาลในเลือดสูงให้หลีกเลี่ยงการทานขนมหวาน /อาหารหวาน/ผลไม้รสหวานจัด เช่น ทุเรียน เงาะ ลำไย มะม่วงสุก ให้ทานอาหารที่มีเส้นใย เช่นผักต่างๆ ออกกำลังกายสม่ำเสมอ")
    except Exception:
        pass # ป้องกันข้อผิดพลาดหากข้อมูล FBS ไม่ถูกต้อง

    # 2. คำแนะนำ chem2 (ไขมัน)
    # เงื่อนไข: DO (ผลไขมันในเลือด) = "ไขมันในเลือดสูง" หรือ "ไขมันในเลือดสูงเล็กน้อย"
    try:
        lipid_str = str(person_data.get("ผลไขมันในเลือด", "")).strip()
        if lipid_str in ["ไขมันในเลือดสูง", "ไขมันในเลือดสูงเล็กน้อย"]:
            recommendations.append("ตรวจพบไขมันในเลือดสูงให้ลดอาหารไขมันสูงเช่น อาหารทอด/ไข่แดง/เครื่องในสัตว์/อาหารทะเล งดสุรา ให้รับประทานผักผลไม้ ออกกำลังกาย ควบคุมน้ำหนักอย่าให้อ้วน")
    except Exception:
        pass

    # 3. คำแนะนำ chem3 (ตับ)
    # เงื่อนไข: DK (ผลเอ็มไซม์ตับ) = "การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย" หรือ "การทำงานของตับสูงกว่าเกณฑ์ปกติ"
    try:
        liver_str = str(person_data.get("ผลเอ็มไซม์ตับ", "")).strip()
        if liver_str in ["การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย", "การทำงานของตับสูงกว่าเกณฑ์ปกติ"]:
            recommendations.append("ตรวจพบการทำงานของตับสูงเล็กน้อย งดสุรา/ลดอาหารไขมัน/อาหารที่ย่อยยาก/ใช้ยาในการดูแลของแพทย์ พักผ่อนให้เพียงพอ ถ้ามีอาการตัวเหลือง/ตาเหลือง/เหนื่อยเพลียผิดปกติควรไปพบแพทย์")
    except Exception:
        pass

    # 4. คำแนะนำ chem4 (ยูริก)
    # เงื่อนไข: DL (ผลยูริค) = "กรดยูริคสูงกว่าเกณฑ์ปกติเล็กน้อย" หรือ "กรดยูริคสูงกว่าเกณฑ์ปกติ"
    try:
        uric_str = str(person_data.get("ผลยูริค", "")).strip()
        if uric_str in ["กรดยูริคสูงกว่าเกณฑ์ปกติเล็กน้อย", "กรดยูริคสูงกว่าเกณฑ์ปกติ"]:
            recommendations.append("ตรวจพบกรดยูริคสูง(สาเหตุของโรคเก๊าท์) ลดอาหารเครื่องในสัตว์ หน่อไม้ หัวผักกาดขาว ยอดผัก สัตว์ปีกเช่น ไก่ เป็ด ดื่มน้ำมากๆ งดสุรา ถ้ามีปวดข้อ มีก้อนปุ่มตามข้อควรไปพบแพทย์")
    except Exception:
        pass

    # 5. คำแนะนำ chem5 (ไต)
    # เงื่อนไข: DM (แปลผล GFR) = "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย"
    try:
        gfr_str = str(person_data.get("แปลผล GFR", "")).strip()
        if gfr_str == "การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย":
            recommendations.append("การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย ลดอาหารเค็ม อาหารโปรตีนสูงย่อยยาก ดื่มน้ำ 8-10 แก้วต่อวันและไม่ควรกลั้นปัสสาวะมีอาการบวมผิดปกติให้พบแพทย์")
    except Exception:
        pass

    # --- สรุปผลลัพธ์ ---
    return recommendations # คืนค่าเป็น list ของ strings
# --- END OF CHANGE ---

# --- START OF CHANGE: Add new function for CBC logic ---
# --- START OF REFACTOR: Return dictionary with statuses ---
def generate_cbc_recommendations(person_data, sex):
    """
    สร้างสรุปผลและคำแนะนำสำหรับ CBC ตามตรรกะ Google Sheet
    Returns:
        dict: {'summary': html_string, 'status_ce': text, 'status_cf': text, 'status_cg': text}
    """
    # รับค่า
    hb = get_float("Hb(%)", person_data)
    wbc = get_float("WBC (cumm)", person_data)
    plt = get_float("Plt (/mm)", person_data)
    
    # 1. ตรรกะ CE: ผล Hb/Hct
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

    # 2. ตรรกะ CF: ผล WBC
    status_cf = ""
    if wbc is not None:
        if 4000 <= wbc <= 10000: status_cf = "เม็ดเลือดขาวปกติ"
        elif 10000 < wbc < 13000: status_cf = "เม็ดเลือดขาวสูงกว่าเกณฑ์ปกติเล็กน้อย"
        elif wbc >= 13000: status_cf = "เม็ดเลือดขาวสูงกว่าเกณฑ์ปกติ"
        elif 3000 < wbc < 4000: status_cf = "เม็ดเลือดขาวต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        elif wbc <= 3000: status_cf = "เม็ดเลือดขาวต่ำกว่าเกณฑ์ปกติ"
            
    # 3. ตรรกะ CG: ผล Platelet
    status_cg = ""
    if plt is not None:
        if 150000 <= plt <= 500000: status_cg = "เกร็ดเลือดปกติ"
        elif 500000 < plt < 600000: status_cg = "เกร็ดเลือดสูงกว่าเกณฑ์ปกติเล็กน้อย"
        elif plt >= 600000: status_cg = "เกร็ดเลือดสูงกว่าเกณฑ์ปกติ"
        elif 100000 <= plt < 150000: status_cg = "เกร็ดเลือดต่ำกว่าเกณฑ์ปกติเล็กน้อย"
        elif plt < 100000: status_cg = "เกร็ดเลือดต่ำกว่าเกณฑ์ปกติ"
        
    # ตรวจสอบว่ามีข้อมูลหรือไม่ (ตามสูตร CD และ CH)
    if not status_ce and not status_cf and not status_cg:
        return {'summary': "ไม่ได้ตรวจ", 'status_ce': "", 'status_cf': "", 'status_cg': ""}

    # 4. ตรรกะ CD: สรุปผลรวม
    status_cd = "ความสมบูรณ์ของเลือดปกติ"
    if ("พบภาวะโลหิตจาง" in status_ce) or \
       ("เม็ดเลือดขาว" in status_cf and "ปกติ" not in status_cf) or \
       ("เกร็ดเลือด" in status_cg and "ปกติ" not in status_cg):
        status_cd = "พบความสมบูรณ์ของเลือดผิดปกติ"

    # 5. ตรรกะ CH: เลือกคำแนะนำ
    advice_text = ""
    if status_ce == "ความเข้มข้นของเลือดปกติ" and status_cf == "เม็ดเลือดขาวปกติ" and status_cg == "เกร็ดเลือดปกติ":
        advice_text = "" # ปกติทั้งหมด
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
    # (อาจมีเงื่อนไขซ้อนอื่นๆ ที่สูตร CH ไม่ได้ครอบคลุม แต่ logic หลักอยู่ครบแล้ว)

    # 6. ประกอบร่าง HTML (*** นี่คือส่วนที่แก้ไข ***)
    summary_parts = []
    summary_parts.append(f"<li>{html.escape(status_cd)}</li>") # 1. สรุปผล
    
    if advice_text: # 2. คำแนะนำ (ถ้ามี)
        summary_parts.append(f"<li>{html.escape(advice_text)}</li>")
    
    # ใช้ <ul> เพื่อสร้าง bullet points และจัดสไตล์เล็กน้อย
    summary_html = f"<ul style='margin: 0; padding-left: 20px;'>{''.join(summary_parts)}</ul>"
        
    return {'summary': summary_html, 'status_ce': status_ce, 'status_cf': status_cf, 'status_cg': status_cg}
# --- END OF REFACTOR ---
# --- END OF CHANGE ---

# --- START OF CHANGE: Add new function for Urine logic ---
# --- START OF REFACTOR: Return dictionary with statuses ---
def generate_urine_recommendations(person_data, sex):
    """
    สร้างสรุปผลและคำแนะนำสำหรับ Urinalysis ตามตรรกะ Google Sheet
    Returns:
        dict: {'summary': html_string, 'status_ct': text, 'status_cu': text, 'status_cv': text, 'status_cw': text}
    """
    # รับค่า
    alb_raw = str(person_data.get("Alb", "")).strip().lower()
    sugar_raw = str(person_data.get("sugar", "")).strip().lower()
    rbc_raw = str(person_data.get("RBC1", "")).strip().lower()
    wbc_raw = str(person_data.get("WBC1", "")).strip().lower()
    
    # 1. ตรรกะ CT: ผล Albumin
    status_ct = ""
    if is_empty(alb_raw): status_ct = ""
    elif alb_raw == "negative": status_ct = "ไม่พบโปรตีนในปัสสาวะ"
    elif alb_raw in ["trace", "2+", "1+"]: status_ct = "พบโปรตีนในปัสสาวะเล็กน้อย"
    elif alb_raw == "3+": status_ct = "พบโปรตีนในปัสสาวะ"
        
    # 2. ตรรกะ CU: ผล Sugar
    status_cu = ""
    if is_empty(sugar_raw): status_cu = ""
    elif sugar_raw == "negative": status_cu = "ไม่พบน้ำตาลในปัสสาวะ"
    elif sugar_raw == "trace": status_cu = "พบน้ำตาลในปัสสาวะเล็กน้อย"
    elif sugar_raw in ["1+", "2+", "3+", "4+", "5+", "6+"]: status_cu = "พบน้ำตาลในปัสสาวะ"

    # 3. ตรรกะ CV: ผล RBC
    status_cv = ""
    if is_empty(rbc_raw): status_cv = ""
    elif rbc_raw in ["0-1", "negative", "1-2", "2-3", "3-5"]: status_cv = "เม็ดเลือดแดงในปัสสาวะปกติ"
    elif rbc_raw in ["5-10", "10-20"]: status_cv = "พบเม็ดเลือดแดงในปัสสาววะเล็กน้อย" # แก้ไข: เพิ่ม "ว"
    else: status_cv = "พบเม็ดเลือดแดงในปัสสาวะ" # ค่าอื่นๆ ที่ไม่ใช่ค่าว่าง
        
    # 4. ตรรกะ CW: ผล WBC
    status_cw = ""
    if is_empty(wbc_raw): status_cw = ""
    elif wbc_raw in ["0-1", "negative", "1-2", "2-3", "3-5"]: status_cw = "เม็ดเลือดขาวในปัสสาวะปกติ"
    elif wbc_raw in ["5-10", "10-20"]: status_cw = "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    else: status_cw = "พบเม็ดเลือดขาวในปัสสาวะ" # ค่าอื่นๆ ที่ไม่ใช่ค่าว่าง

    # ตรวจสอบว่ามีข้อมูลหรือไม่ (ตามสูตร CS และ CX)
    if not status_ct and not status_cu and not status_cv and not status_cw:
        return {'summary': "ไม่ได้ตรวจ", 'status_ct': "", 'status_cu': "", 'status_cv': "", 'status_cw': ""}

    # 5. ตรรกะ CS: สรุปผลรวม
    is_abnormal = False
    if status_ct == "พบโปรตีนในปัสสาวะ": is_abnormal = True # เล็กน้อยไม่นับ
    if "น้ำตาล" in status_cu and "ไม่พบ" not in status_cu: is_abnormal = True
    if "เม็ดเลือดแดง" in status_cv and "ปกติ" not in status_cv: is_abnormal = True
    if status_cw == "พบเม็ดเลือดขาวในปัสสาวะ": is_abnormal = True # เล็กน้อยไม่นับ
    
    status_cs = "ผลปัสสาวะผิดปกติ" if is_abnormal else "ปัสสาวะปกติ"

    # 6. ตรรกะ CX: เลือกคำแนะนำ
    advice_text = ""
    status_ct_ok = status_ct in ["ไม่พบโปรตีนในปัสสาวะ", "พบโปรตีนในปัสสาวะเล็กน้อย"]
    status_cu_ok = status_cu == "ไม่พบน้ำตาลในปัสสาวะ"
    status_cv_ok = status_cv == "เม็ดเลือดแดงในปัสสาวะปกติ"
    status_cw_ok = status_cw == "เม็ดเลือดขาวในปัสสาวะปกติ"

    if status_ct_ok and status_cu_ok and status_cv_ok and status_cw_ok:
        advice_text = "" # ปกติทั้งหมด
    elif "น้ำตาล" in status_cu and "ไม่พบ" not in status_cu:
        advice_text = RECOMMENDATION_TEXTS_URINE["E11"]
    elif sex == "หญิง" and status_ct_ok and status_cu_ok and ("เม็ดเลือดแดง" in status_cv and "ปกติ" not in status_cv) and status_cw_ok:
        advice_text = RECOMMENDATION_TEXTS_URINE["E4"]
    elif sex == "ชาย" and status_ct_ok and status_cu_ok and ("เม็ดเลือดแดง" in status_cv and "ปกติ" not in status_cv) and status_cw_ok:
        advice_text = RECOMMENDATION_TEXTS_URINE["E10"]
    elif status_ct_ok and status_cu_ok and status_cv_ok and status_cw == "พบเม็ดเลือดขาวในปัสสาวะ":
        advice_text = RECOMMENDATION_TEXTS_URINE["F3"] # ซึ่งเป็น ""
    elif status_ct_ok and status_cu_ok and status_cv_ok and status_cw == "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย":
        advice_text = RECOMMENDATION_TEXTS_URINE["E2"]
    
    # 7. ประกอบร่าง HTML (*** นี่คือส่วนที่แก้ไข ***)
    summary_parts = []
    summary_parts.append(f"<li>{html.escape(status_cs)}</li>") # 1. สรุปผล
    
    if advice_text: # 2. คำแนะนำ (ถ้ามี)
        summary_parts.append(f"<li>{html.escape(advice_text)}</li>")
    
    # ใช้ <ul> เพื่อสร้าง bullet points และจัดสไตล์เล็กน้อย
    summary_html = f"<ul style='margin: 0; padding-left: 20px;'>{''.join(summary_parts)}</ul>"
        
    return {'summary': summary_html, 'status_ct': status_ct, 'status_cu': status_cu, 'status_cv': status_cv, 'status_cw': status_cw}
# --- END OF REFACTOR ---
# --- END OF CHANGE ---

# --- START OF CHANGE: Add new function for Doctor Opinion logic ---
def generate_doctor_opinion(person_data, sex, cbc_statuses, urine_statuses):
    """
    สร้างสรุปความคิดเห็นของแพทย์ตามตรรกะ Google Sheet (DP-EF)
    """
    opinion_parts = []

    # DP: สรุปความดัน
    # --- START OF CHANGE: Use SBP/DBP directly ---
    sbp = get_float("SBP", person_data)
    dbp = get_float("DBP", person_data)
    if sbp is not None and dbp is not None:
        if 140 <= sbp < 160 or 90 <= dbp < 100:
             opinion_parts.append("ความดันโลหิตสูงเล็กน้อย")
        elif sbp >= 160 or dbp >= 100:
             opinion_parts.append("ความดันโลหิตสูง")
    # --- END OF CHANGE ---

    # DQ: สรุปน้ำตาล
    fbs = get_float("FBS", person_data)
    if fbs is not None:
        if 100 <= fbs < 106: opinion_parts.append("น้ำตาลในเลือดเริ่มสูงเล็กน้อย")
        elif 106 <= fbs < 126: opinion_parts.append("น้ำตาลในเลือดสูงเล็กน้อย")
        elif fbs >= 126: opinion_parts.append("น้ำตาลในเลือดสูง")

    # DR: สรุปไขมัน
    chol = get_float("CHOL", person_data)
    tgl = get_float("TGL", person_data)
    ldl = get_float("LDL", person_data)
    lipid_overall_status = str(person_data.get("ผลไขมันในเลือด", "")).strip() # DO2
    if lipid_overall_status != "ปกติ":
        # ตรวจสอบค่าดิบ (DG2=CHOL, DH2=TGL, DJ2=LDL)
        chol_raw = get_float("CHOL", person_data)
        tgl_raw = get_float("TGL", person_data)
        ldl_raw = get_float("LDL", person_data)
        # เช็คว่ามีค่าใดค่าหนึ่งที่ไม่ใช่ค่าว่าง
        has_lipid_values = not (is_empty(chol_raw) and is_empty(tgl_raw)) # ใช้ CHOL/TGL เป็นหลักตามสูตร
        
        if has_lipid_values:
            # เงื่อนไข 'ไขมันในเลือดสูง'
            is_high = (chol_raw is not None and chol_raw > 250) or \
                      (tgl_raw is not None and tgl_raw > 150) or \
                      (ldl_raw is not None and ldl_raw > 180) # เพิ่มเช็ค ldl_raw is not None
            # เงื่อนไข 'ปกติ' (จากค่าดิบ)
            is_normal_raw = (chol_raw is not None and chol_raw <= 200) and \
                            (tgl_raw is not None and tgl_raw <= 150)
            
            if is_high:
                opinion_parts.append("ไขมันในเลือดสูง")
            elif is_normal_raw:
                pass # ถ้าค่าดิบปกติ แต่ DO2 ไม่ปกติ อาจไม่ต้องแสดงอะไร หรือแสดงตาม DO2? - ยึดตาม GSheet คือไม่แสดงอะไร
            else: # กรณีอื่นๆ ที่ไม่เข้าข่าย สูง หรือ ปกติ (จากค่าดิบ)
                opinion_parts.append("ไขมันในเลือดสูงเล็กน้อย")
        # กรณีไม่มีค่าดิบ แต่ DO2 ไม่ปกติ (อาจจะดึงค่ามาจากระบบอื่น?) - ใช้ค่า DO2 โดยตรง
        elif lipid_overall_status == "ไขมันในเลือดสูง":
             opinion_parts.append("ไขมันในเลือดสูง")
        elif lipid_overall_status == "ไขมันในเลือดสูงเล็กน้อย":
             opinion_parts.append("ไขมันในเลือดสูงเล็กน้อย")


    # DS: สรุปตับ
    alp = get_float("ALP", person_data) # CY2 -> ALP
    sgot = get_float("SGOT", person_data) # CZ2 -> SGOT
    sgpt = get_float("SGPT", person_data) # DA2 -> SGPT
    if (alp is not None and alp > 120) or \
       (sgot is not None and sgot > 36) or \
       (sgpt is not None and sgpt > 40): # แก้ไขเกณฑ์ SGOT/SGPT ตาม GSheet
        opinion_parts.append("การทำงานของตับสูงกว่าเกณฑ์ปกติเล็กน้อย")

    # DT: สรุปยูริค
    uric = get_float("Uric Acid", person_data) # DB2 -> Uric Acid
    if uric is not None and uric > 7.2:
        opinion_parts.append("กรดยูริคสูงกว่าเกณฑ์ปกติเล็กน้อย")

    # DU: สรุปไต
    gfr = get_float("GFR", person_data) # DE2 -> GFR
    if gfr is not None and gfr < 60:
        opinion_parts.append("การทำงานของไตต่ำกว่าเกณฑ์ปกติเล็กน้อย")

    # DV: สรุป HB HCT (ใช้ status จาก cbc_statuses)
    if cbc_statuses.get('status_ce') == "พบภาวะโลหิตจาง":
        opinion_parts.append("พบภาวะโลหิตจาง")

    # DW: สรุป WBC (ใช้ status จาก cbc_statuses)
    if cbc_statuses.get('status_cf') in ["เม็ดเลือดขาวสูงกว่าเกณฑ์ปกติ", "เม็ดเลือดขาวต่ำกว่าเกณฑ์ปกติ"]:
        opinion_parts.append("เม็ดเลือดขาวผิดปกติ")

    # DX: สรุป Platelet (ใช้ status จาก cbc_statuses)
    if cbc_statuses.get('status_cg') in ["เกร็ดเลือดสูงกว่าเกณฑ์ปกติ", "เกร็ดเลือดต่ำกว่าเกณฑ์ปกติ"]:
        opinion_parts.append("เกร็ดเลือดผิดปกติ")

    # DY: สรุป Albumin UA (ใช้ status จาก urine_statuses)
    if urine_statuses.get('status_ct') == "พบโปรตีนในปัสสาวะ":
        opinion_parts.append("พบโปรตีนในปัสสาวะ")

    # DZ: สรุป Sugar UA (ใช้ status จาก urine_statuses)
    if urine_statuses.get('status_cu') == "พบน้ำตาลในปัสสาวะ":
        opinion_parts.append("พบน้ำตาลในปัสสาวะ")

    # EA: สรุป RBC UA (ใช้ status จาก urine_statuses)
    if urine_statuses.get('status_cv') == "พบเม็ดเลือดแดงในปัสสาวะ":
        opinion_parts.append("พบเม็ดเลือดแดงในปัสสาวะ")

    # EB: สรุป WBC UA (ใช้ status จาก urine_statuses)
    if urine_statuses.get('status_cw') == "พบเม็ดเลือดขาวในปัสสาวะ":
        opinion_parts.append("พบเม็ดเลือดขาวในปัสสาวะ")

    # EC: สรุปปัญหาอื่น (ค่าว่าง) - ไม่ต้องทำอะไร

    # EF: DOCTER suggest (ดึงค่าโดยตรง)
    doctor_suggest = str(person_data.get("DOCTER suggest", "")).strip() # ใช้ชื่อคอลัมน์ที่คุณยืนยัน
    if not is_empty(doctor_suggest):
        opinion_parts.append(doctor_suggest)

    # รวมผลลัพธ์
    final_opinion = " ".join(filter(None, opinion_parts)) # Join เฉพาะส่วนที่ไม่ใช่ค่าว่าง

    # เพิ่มเว้นวรรค 3 ช่องด้านหน้าตามสูตร GSheet
    return f"   {final_opinion}" if final_opinion else "-" # ถ้าไม่มีอะไรเลย ให้แสดง "-"

# --- END OF CHANGE ---


# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None):
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div style='background-color: #f0f2f6; color: #333; text-align: center; padding: 0.2rem 0.4rem; font-weight: bold; border-radius: 6px; margin-top: 1rem; margin-bottom: 0.4rem; font-size: 11px; border: 1px solid #ddd;'>
        {full_title}
    </div>
    """

# --- START OF CHANGE: Modified function to accept footer_html ---
def render_lab_table_html(title, subtitle, headers, rows, table_class="print-lab-table", footer_html=None):
    header_html = render_section_header(title, subtitle)
    # --- START: Wrap content in a single table, not header + table ---
    html_content = f"<table class='{table_class}'><colgroup><col style='width: 40%;'><col style='width: 20%;'><col style='width: 40%;'></colgroup><thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i == 0 or i == 2 else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"{table_class}-abn" if is_abn else ""
        html_content += f"<tr class='{row_class}'><td style='text-align: left;'>{row[0][0]}</td><td>{row[1][0]}</td><td style='text-align: left;'>{row[2][0]}</td></tr>"
    html_content += "</tbody>" # Close tbody
    
    if footer_html:
        # --- START OF CHANGE: Ensure footer_html is treated as HTML ---
        html_content += f"<tfoot><tr class='recommendation-row'><td colspan='{len(headers)}' style='text-align: left;'><b>สรุปผล/คำแนะนำ:</b><br>{footer_html}</td></tr></tfoot>"
        # --- END OF CHANGE ---
        
    html_content += "</table>" # Close table
    # --- START: Wrap the whole block in the break-avoid div ---
    return f"<div class='column-break-avoid'>{header_html}{html_content}</div>"
    # --- END: Wrap the whole block in the break-avoid div ---
# --- END OF CHANGE ---

def render_header_and_vitals(person_data):
    """Renders the compact header and personal info table for the print report."""
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    sbp, dbp = get_float("SBP", person_data), get_float("DBP", person_data)
    bp_val = f"{int(sbp)}/{int(dbp)} ม.ม.ปรอท" if sbp and dbp else "-"
    pulse_val = f"{int(get_float('pulse', person_data))} ครั้ง/นาที" if get_float('pulse', person_data) else "-"
    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight} กก." if weight else "-"
    height_val = f"{height} ซม." if height else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')} ซม." if not is_empty(person_data.get('รอบเอว')) else "-"
    return f"""
    <div class="header-grid">
        <div class="header-left">
            <h1 style="font-size: 1.5rem; margin:0;">รายงานผลการตรวจสุขภาพ</h1>
            <p style="font-size: 0.8rem; margin:0;">คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
            <p style="font-size: 0.8rem; margin:0;"><b>วันที่ตรวจ:</b> {check_date}</p>
        </div>
        <div class="header-right">
            <table class="info-table">
                <tr>
                    <td><b>ชื่อ-สกุล:</b> {name}</td>
                    <td><b>อายุ:</b> {age} ปี</td>
                    <td><b>เพศ:</b> {sex}</td>
                    <td><b>HN:</b> {hn}</td>
                </tr>
                <tr>
                    <td><b>หน่วยงาน:</b> {department}</td>
                    <td><b>น้ำหนัก:</b> {weight_val}</td>
                    <td><b>ส่วนสูง:</b> {height_val}</td>
                    <td><b>รอบเอว:</b> {waist_val}</td>
                </tr>
                 <tr>
                    <td colspan="2"><b>ความดันโลหิต:</b> {bp_val}</td>
                    <td colspan="2"><b>ชีพจร:</b> {pulse_val}</td>
                </tr>
            </table>
        </div>
    </div>
    <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 0.5rem 0;">
    """

# --- START OF CHANGE: Pass cbc_statuses to render ---
def render_lab_section(person, sex, cbc_statuses):
# --- END OF CHANGE ---
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [[(label, is_abn), (result, is_abn), (norm, is_abn)] for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]
    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [[(label, is_abn), (result, is_abn), (norm, is_abn)] for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]

    # --- START OF CHANGE: Add footers ---
    # 1. CBC Footer (Logic)
    # --- START OF CHANGE: Use summary from passed dictionary ---
    cbc_footer = cbc_statuses.get('summary', '[Error: CBC Status Missing]')
    # --- END OF CHANGE ---
    
    # 2. Blood Chemistry Footer (Logic)
    recommendations_list = generate_fixed_recommendations(person)
    if not recommendations_list:
        blood_footer = "ผลการตรวจโดยรวมอยู่ในเกณฑ์ปกติ"
    else:
        list_items = "".join([f"<li>{html.escape(rec)}</li>" for rec in recommendations_list])
        blood_footer = f"<ul>{list_items}</ul>"
        
    cbc_html = render_lab_table_html("ผลตรวจ CBC (Complete Blood Count)", None, ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows, "print-lab-table", footer_html=cbc_footer)
    blood_html = render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", None, ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows, "print-lab-table", footer_html=blood_footer)
    # --- END OF CHANGE ---
    
    return f"""
    <table style="width: 100%; border-collapse: collapse; page-break-inside: avoid;">
        <tr>
            <td style="width: 50%; vertical-align: top; padding-right: 5px;">{cbc_html}</td>
            <td style="width: 50%; vertical-align: top; padding-left: 5px;">{blood_html}</td>
        </tr>
    </table>
    """

# --- START OF CHANGE: Pass urine_statuses and doctor_opinion to render ---
# --- START OF REFACTOR: Add all_person_history_df ---
def render_other_results_html(person, sex, urine_statuses, doctor_opinion, all_person_history_df=None):
# --- END OF REFACTOR ---
# --- END OF CHANGE ---
    urine_data = [("สี (Colour)", "Color", "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", "sugar", "Negative"), ("โปรตีน (Albumin)", "Alb", "Negative, trace"), ("กรด-ด่าง (pH)", "pH", "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", "Spgr", "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", "RBC1", "0 - 2 cell/HPF"), ("เม็ดเลือดขาว (WBC)", "WBC1", "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", "SQ-epi", "0 - 10 cell/HPF"), ("อื่นๆ", "ORTER", "-")]
    urine_rows = [[(label, is_abn), (safe_value(val), is_abn), (norm, is_abn)] for label, key, norm in urine_data for val in [person.get(key, "-")] for is_abn in [is_urine_abnormal(label, val, norm)]]
    
    # --- START OF CHANGE: Add Urine footer ---
    # --- START OF CHANGE: Use summary from passed dictionary ---
    urine_footer = urine_statuses.get('summary', '[Error: Urine Status Missing]')
    # --- END OF CHANGE ---
    urine_html = render_lab_table_html("ผลการตรวจปัสสาวะ", "Urinalysis", ["การตรวจ", "ผลตรวจ", "ค่าปกติ"], urine_rows, "print-lab-table", footer_html=urine_footer)
    # --- END OF CHANGE ---
    
    stool_exam_text = interpret_stool_exam(person.get("Stool exam", ""))
    stool_cs_text = interpret_stool_cs(person.get("Stool C/S", ""))
    stool_html = f"""
    {render_section_header("ผลตรวจอุจจาระ (Stool Examination)")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระทั่วไป</b></td><td style="text-align: left;">{stool_exam_text}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระเพาะเชื้อ</b></td><td style="text-align: left;">{stool_cs_text}</td></tr>
    </table>
    """
    # --- START OF CHANGE: Add year variable ---
    year_str = str(person.get("Year", ""))
    current_year = int(year_str) if year_str.isdigit() else (datetime.now().year + 543)
    # --- END OF CHANGE ---
    
    # --- START: Wrap in break-avoid div ---
    stool_html = f"""
    <div class='column-break-avoid'>
    {render_section_header("ผลตรวจอุจจาระ (Stool Examination)")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระทั่วไป</b></td><td style="text-align: left;">{stool_exam_text}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลตรวจอุจจาระเพาะเชื้อ</b></td><td style="text-align: left;">{stool_cs_text}</td></tr>
    </table>
    </div>
    """
    # --- END: Wrap in break-avoid div ---

    # --- START OF CHANGE: Add year variable ---
    cxr_result = interpret_cxr(person.get(f"CXR{str(current_year)[-2:]}" if current_year != (datetime.now().year+543) else "CXR", ""))
    ekg_result = interpret_ekg(person.get(get_ekg_col_name(current_year), ""))
    # --- START: Wrap in break-avoid div ---
    other_tests_html = f"""
    <div class='column-break-avoid'>
    {render_section_header("ผลตรวจอื่นๆ")}
    <table class="print-lab-table">
        <tr><td style="text-align: left; width: 40%;"><b>ผลเอกซเรย์ (Chest X-ray)</b></td><td style="text-align: left;">{cxr_result}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ผลคลื่นไฟฟ้าหัวใจ (EKG)</b></td><td style="text-align: left;">{ekg_result}</td></tr>
    </table>
    </div>
    """
    # --- END: Wrap in break-avoid div ---

    hep_a_value = person.get("Hepatitis A")
    hep_a_display_text = "ไม่ได้เข้ารับการตรวจไวรัสตับอักเสบเอ" if is_empty(hep_a_value) else safe_value(hep_a_value)
    
    hbsag_current = person.get("HbsAg")
    hbsab_current = person.get("HbsAb")
    hbcab_current = person.get("HBcAb")

    show_current_hep_b = not is_empty(hbsag_current) or not is_empty(hbsab_current) or not is_empty(hbcab_current)

    hbsag_display = ""
    hbsab_display = ""
    hep_b_advice_display, hep_b_status = "", ""
    
    hep_test_date_str = str(person.get("ปีตรวจHEP", "")).strip()
    if not is_empty(hep_test_date_str):
        hepatitis_header_text = f"ผลตรวจไวรัสตับอักเสบ (Viral Hepatitis) (ตรวจเมื่อ: {hep_test_date_str})"
    else:
        hepatitis_header_text = f"ผลตรวจไวรัสตับอักเสบ (Viral Hepatitis) (พ.ศ. {current_year})"
        
    show_hep_b_advice_row = False 

    if show_current_hep_b:
        hbsag_display = safe_value(hbsag_current)
        hbsab_display = safe_value(hbsab_current)
        hbcab_display = safe_value(hbcab_current)
        hep_b_advice_display, hep_b_status = hepatitis_b_advice(hbsag_display, hbsab_display, hbcab_display)
        show_hep_b_advice_row = True
    else:
        hbsag_display = "ไม่ได้ตรวจ"
        hbsab_display = "ไม่ได้ตรวจ"
        hbcab_display = "ไม่ได้ตรวจ"
        hep_b_advice_display = "ไม่ได้เข้ารับการตรวจในปีนี้"
        show_hep_b_advice_row = False

    advice_bg_color = '#f8f9fa'
    if show_hep_b_advice_row:
         advice_bg_color = {'infection': '#ffdddd', 'no_immune': '#fff8e1', 'immune': '#e8f5e9'}.get(hep_b_status, '#f8f9fa')

    hep_b_rows_html = f"""
        <tr><td style="text-align: left; width: 40%;"><b>ไวรัสตับอักเสบ เอ</b></td><td style="text-align: left;">{hep_a_display_text}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ไวรัสตับอักเสบ บี (HBsAg)</b></td><td style="text-align: left;">{hbsag_display}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>ภูมิคุ้มกัน (HBsAb)</b></td><td style="text-align: left;">{hbsab_display}</td></tr>
        <tr><td style="text-align: left; width: 40%;"><b>การติดเชื้อ (HBcAb)</b></td><td style="text-align: left;">{hbcab_display}</td></tr>
    """
    if show_hep_b_advice_row:
         hep_b_rows_html += f'<tr style="background-color: {advice_bg_color};"><td colspan="2" style="text-align: left;"><b>คำแนะนำ:</b> {hep_b_advice_display}</td></tr>'
    
    # --- END OF REFACTOR (Removed the part that showed previous year's data) ---

    # --- START: Wrap in break-avoid div ---
    hepatitis_html = f"""
    <div class='column-break-avoid'>
    {render_section_header(hepatitis_header_text)}
    <table class="print-lab-table">
        {hep_b_rows_html}
    </table>
    </div>
    """
    # --- END: Wrap in break-avoid div ---
    # --- END OF REFACTOR ---

    # --- START OF CHANGE: Use generated doctor_opinion ---
    # --- START: Wrap in break-avoid div ---
    doctor_opinion_html = f"""
    <div class='column-break-avoid'>
    {render_section_header("สรุปความคิดเห็นของแพทย์")}
    <div class="doctor-opinion-box">
        {html.escape(doctor_opinion)}
    </div>
    </div>
    """
    # --- END: Wrap in break-avoid div ---
    # --- END OF CHANGE ---
    
    return f"""
            <div style="border-bottom: 1px dotted #333; margin-bottom: 0.4rem; width: 100%;"></div>
            <div style="white-space: nowrap;">นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div style="white-space: nowrap;">แพทย์อาชีวเวชศาสตร์</div>
            <div style="white-space: nowrap;">ว.26674</div>
        </div>
    </div>
    """
    
    # --- 5. CSS ---
    css_html = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        body { font-family: 'Sarabun', sans-serif !important; font-size: 9.5px; margin: 10mm; color: #333; background-color: #fff; }
        p, div, span, td, th { line-height: 1.4; }
        table { border-collapse: collapse; width: 100%; }
        .print-lab-table td, .print-lab-table th { padding: 2px 4px; border: 1px solid #ccc; text-align: center; vertical-align: middle; }
        .print-lab-table th { background-color: #f2f2f2; font-weight: bold; }
        .print-lab-table-abn { background-color: #fff1f0 !important; }
        
        .print-lab-table tfoot .recommendation-row td {
            background-color: #fcf8e3; /* Light yellow */
            font-size: 9px;
            line-height: 1.3;
            border: 1px solid #ccc;
            text-align: left;
            padding: 4px 6px;
        }
        .print-lab-table tfoot ul {
            padding-left: 15px;
            margin-top: 2px;
            margin-bottom: 2px;
        }
        .print-lab-table tfoot li {
            margin-bottom: 2px;
        }
        
        .header-grid { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 0.5rem; }
        .header-left { text-align: left; }
        .header-right { text-align: right; }
        .info-table { font-size: 9.5px; text-align: left; }
        .info-table td { padding: 1px 5px; border: none; }
        
        /* --- START: CSS for Multi-column --- */
        .multi-column-container {
            column-count: 2;
            column-gap: 15px; /* ระยะห่างระหว่างคอลัมน์ */
        }
        .column-break-avoid {
            break-inside: avoid;
            page-break-inside: avoid; /* ป้องกันการตัดข้ามหน้า (เผื่อไว้) */
        }
        /* --- END: CSS for Multi-column --- */

        .advice-box { padding: 0.5rem 1rem; border-radius: 8px; line-height: 1.5; margin-top: 0.5rem; border: 1px solid #ddd; page-break-inside: avoid; }
        .advice-title { font-weight: bold; margin-bottom: 0.3rem; font-size: 11px; }
        .advice-content ul { padding-left: 20px; margin: 0; }
        .advice-content ul li { margin-bottom: 4px; }
        
        .doctor-opinion-box {
            background-color: #e8f5e9; /* Light green */
            border-color: #a5d6a7;
            border: 1px solid #ddd;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            line-height: 1.5;
            margin-top: 0.5rem;
            page-break-inside: avoid;
            font-size: 9px;
            white-space: pre-wrap;
        }
        
        .perf-section { margin-top: 0.5rem; page-break-inside: avoid; border: 1px solid #e0e0e0; border-radius: 8px; padding: 0.5rem; }
        .summary-box { background-color: #f8f9fa; border-radius: 4px; padding: 4px 8px; margin-top: 2px; font-size: 9px; }
        @media print { body { -webkit-print-color-adjust: exact; margin: 0; } }
    </style>
    """
    
    # --- 6. Final HTML Assembly ---
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        {css_html}
    </head>
    <body>
        {header_vitals_html}
        
        <div class="multi-column-container">
            {cbc_html}
            {blood_html}
            {urine_html}
            {stool_html}
            {other_tests_html}
            {hepatitis_html}
            {doctor_opinion_html}
        </div>
        
        {signature_html}
    </body>
    </html>
    """
    # --- END: CSS Multi-column Modification ---
    
    return final_html
