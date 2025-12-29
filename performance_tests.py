import pandas as pd
import numpy as np
from collections import OrderedDict

# ==============================================================================
# หมายเหตุ: ไฟล์นี้ถูกปรับปรุงใหม่ทั้งหมด
# - เพิ่มฟังก์ชัน generate_comprehensive_recommendations เพื่อสร้างคำแนะนำแบบองค์รวม
# - ย้ายและรวมตรรกะการแปลผลจากไฟล์ app.py และ print_report.py มาไว้ที่นี่
#   เพื่อให้เป็นศูนย์กลางของการสร้างคำแนะนำทั้งหมด
# ==============================================================================


# --- Helper Functions ---

def is_empty(val):
    """ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่"""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(person_data, key):
    """ดึงค่า float จาก dictionary อย่างปลอดภัย"""
    val = person_data.get(key, "")
    if is_empty(val):
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

# --- Interpretation Functions (ย้ายและรวมศูนย์จากไฟล์อื่น) ---

def interpret_cxr(val):
    """แปลผล Chest X-ray"""
    val_str = str(val or "").strip()
    if is_empty(val_str):
        return "ไม่ได้ตรวจ", "normal"
    if any(keyword in val_str.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion", "cardiomegaly"]):
        return f"{val_str}", "abnormal"
    return val_str, "normal"

def interpret_ekg(val):
    """แปลผล EKG"""
    val_str = str(val or "").strip()
    if is_empty(val_str):
        return "ไม่ได้ตรวจ", "normal"
    if any(x in val_str.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]):
        return f"{val_str}", "abnormal"
    return val_str, "normal"

def interpret_urine(person_data):
    """แปลผลตรวจปัสสาวะทั้งหมดและคืนค่าสรุป"""
    # --- แก้ไข: ตรวจสอบก่อนว่ามีการตรวจปัสสาวะจริงหรือไม่ ---
    if is_empty(person_data.get("Color")) and is_empty(person_data.get("pH")) and is_empty(person_data.get("Spgr")):
        return {} # ถ้าไม่มีข้อมูลหลัก ให้ถือว่าไม่ได้ตรวจ

    results = {}
    sex = person_data.get("เพศ", "ชาย")
    
    # Protein (Albumin)
    alb = str(person_data.get("Alb", "")).strip().lower()
    if alb in ["3+", "4+"]: results['โปรตีนในปัสสาวะ'] = ('พบโปรตีนปริมาณมาก', 'high')
    elif alb in ["trace", "1+", "2+"]: results['โปรตีนในปัสสาวะ'] = ('พบโปรตีนเล็กน้อย', 'medium')

    # Sugar
    sugar = str(person_data.get("sugar", "")).strip().lower()
    if sugar not in ["negative", "trace", "", " "]:
        results['น้ำตาลในปัสสาวะ'] = ('พบน้ำตาลในปัสสาวะ', 'high')

    # RBC
    rbc_val = str(person_data.get("RBC1", "")).strip()
    if not is_empty(rbc_val):
        try:
            if "-" in rbc_val: high_rbc = float(rbc_val.split('-')[1].strip())
            else: high_rbc = float(rbc_val)
            
            if high_rbc > 5:
                issue = "พบเม็ดเลือดแดงในปัสสาวะ"
                if sex == "หญิง": issue += " (อาจเกิดจากประจำเดือน)"
                results['เม็ดเลือดแดงในปัสสาวะ'] = (issue, 'medium')
        except: pass # Ignore if parsing fails

    # WBC
    wbc_val = str(person_data.get("WBC1", "")).strip()
    if not is_empty(wbc_val):
        try:
            if "-" in wbc_val: high_wbc = float(wbc_val.split('-')[1].strip())
            else: high_wbc = float(wbc_val)

            if high_wbc > 10:
                results['เม็ดเลือดขาวในปัสสาวะ'] = ('พบเม็ดเลือดขาวในปัสสาวะ', 'medium')
        except: pass

    return results

def interpret_stool(person_data):
    """แปลผลตรวจอุจจาระ"""
    # --- แก้ไข: ตรวจสอบก่อนว่ามีการตรวจอุจจาระจริงหรือไม่ ---
    if is_empty(person_data.get("Stool exam")) and is_empty(person_data.get("Stool C/S")):
        return {}

    results = {}
    exam = str(person_data.get("Stool exam", "")).strip().lower()
    culture = str(person_data.get("Stool C/S", "")).strip().lower()

    if "wbc" in exam or "เม็ดเลือดขาว" in exam:
        results['ผลตรวจอุจจาระ'] = ('พบเม็ดเลือดขาว (อาจมีการอักเสบ)', 'medium')
    
    if "ไม่พบ" not in culture and "ปกติ" not in culture and not is_empty(culture):
         results['ผลเพาะเชื้ออุจจาระ'] = ('พบการติดเชื้อ', 'high')
         
    return results

def interpret_hepatitis(person_data):
    """แปลผลตรวจไวรัสตับอักเสบ"""
    # --- แก้ไข: ตรวจสอบก่อนว่ามีการตรวจ Hepatitis จริงหรือไม่ ---
    if is_empty(person_data.get("HbsAg")) and is_empty(person_data.get("HbsAb")):
        return {}

    results = {}
    hbsag = str(person_data.get("HbsAg", "")).strip().lower()
    hbsab = str(person_data.get("HbsAb", "")).strip().lower()

    if "positive" in hbsag:
        results['ไวรัสตับอักเสบบี'] = ('เป็นพาหะหรือกำลังติดเชื้อ', 'high')
    elif "negative" in hbsag and "negative" in hbsab:
        results['ไวรัสตับอักเสบบี'] = ('ไม่มีภูมิคุ้มกัน', 'low')
        
    return results


# --- Main Recommendation Engine ---

def generate_comprehensive_recommendations(person_data):
    """
    สร้างสรุปและคำแนะนำการปฏิบัติตัวแบบองค์รวมจากข้อมูลสุขภาพทั้งหมด
    โดยจัดลำดับความสำคัญของแต่ละประเด็น
    """
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    has_data = any(not is_empty(person_data.get(key)) for key in key_indicators)

    if not has_data:
        return "" 

    issues = {'high': [], 'medium': [], 'low': []}
    conditions = set()
    
    # --- 1. Vital Signs & BMI ---
    weight = get_float(person_data, "น้ำหนัก")
    height = get_float(person_data, "ส่วนสูง")
    sbp = get_float(person_data, "SBP")
    dbp = get_float(person_data, "DBP")

    if weight and height and height > 0:
        bmi = weight / ((height / 100) ** 2)
        if bmi >= 30:
            issues['medium'].append(f"<b>ภาวะอ้วน (BMI ≥ 30):</b> เป็นความเสี่ยงหลักต่อโรคเรื้อรังต่างๆ")
            conditions.add('obesity')
        elif bmi >= 25:
            issues['low'].append(f"<b>น้ำหนักเกินเกณฑ์ (BMI 25-29.9):</b> ควรเริ่มควบคุมอาหารและออกกำลังกาย")
            conditions.add('overweight')
    
    if sbp and dbp:
        if sbp >= 160 or dbp >= 100:
            issues['high'].append(f"<b>ความดันโลหิตสูงรุนแรง ({int(sbp)}/{int(dbp)} mmHg):</b> มีความเสี่ยงอันตราย ควรพบแพทย์โดยเร็ว")
            conditions.add('hypertension')
        elif sbp >= 140 or dbp >= 90:
            issues['medium'].append(f"<b>ความดันโลหิตสูง ({int(sbp)}/{int(dbp)} mmHg):</b> ควรปรับเปลี่ยนพฤติกรรมและติดตามใกล้ชิด")
            conditions.add('hypertension')
        elif sbp >= 120 or dbp >= 80:
            issues['low'].append(f"<b>ความดันโลหิตเริ่มสูง ({int(sbp)}/{int(dbp)} mmHg):</b> เป็นสัญญาณเตือนให้เริ่มดูแลสุขภาพ")
            conditions.add('prehypertension')

    # --- 2. Blood Chemistry ---
    fbs = get_float(person_data, "FBS")
    if fbs:
        if fbs >= 126:
            issues['high'].append(f"<b>ระดับน้ำตาลในเลือดสูง ({int(fbs)} mg/dL):</b> เข้าเกณฑ์เบาหวาน ควรพบแพทย์เพื่อยืนยันและรักษา")
            conditions.add('diabetes')
        elif fbs >= 100:
            issues['medium'].append(f"<b>ภาวะเสี่ยงเบาหวาน ({int(fbs)} mg/dL):</b> ควรควบคุมอาหารและออกกำลังกายอย่างจริงจัง")
            conditions.add('prediabetes')

    # --- แก้ไข: เพิ่มความละเอียดในการแปลผลไขมัน ---
    chol = get_float(person_data, "CHOL")
    tgl = get_float(person_data, "TGL")
    ldl = get_float(person_data, "LDL")
    hdl = get_float(person_data, "HDL")
    lipid_issues_text = []
    is_lipid_high_risk = False
    
    if chol:
        if chol >= 240:
            lipid_issues_text.append("คอเลสเตอรอลสูงมาก")
            is_lipid_high_risk = True
        elif chol >= 200:
            lipid_issues_text.append("คอเลสเตอรอลสูง")
    if tgl:
        if tgl >= 500:
            lipid_issues_text.append("ไตรกลีเซอไรด์สูงมาก")
            is_lipid_high_risk = True
        elif tgl >= 200:
            lipid_issues_text.append("ไตรกลีเซอไรด์สูง")
        elif tgl >= 150:
            lipid_issues_text.append("ไตรกลีเซอไรด์เริ่มสูง")
    if ldl:
        if ldl >= 190:
            lipid_issues_text.append("LDL (ไขมันเลว) สูงมาก")
            is_lipid_high_risk = True
        elif ldl >= 160:
            lipid_issues_text.append("LDL (ไขมันเลว) สูง")
        elif ldl >= 130:
            lipid_issues_text.append("LDL (ไขมันเลว) เริ่มสูง")
    if hdl and hdl < 40:
        lipid_issues_text.append("HDL (ไขมันดี) ต่ำ")

    if lipid_issues_text:
        risk_level = 'high' if is_lipid_high_risk else 'medium'
        issues[risk_level].append(f"<b>ภาวะไขมันในเลือดผิดปกติ ({', '.join(lipid_issues_text)}):</b> เพิ่มความเสี่ยงโรคหัวใจและหลอดเลือด")
        conditions.add('dyslipidemia')


    gfr = get_float(person_data, "GFR")
    if gfr:
        if gfr < 30:
            issues['high'].append("<b>การทำงานของไตลดลงมาก (ระยะ 4-5):</b> ควรพบแพทย์ผู้เชี่ยวชาญโรคไตโดยด่วน")
            conditions.add('kidney_disease')
        elif gfr < 60:
            issues['medium'].append("<b>การทำงานของไตเริ่มเสื่อม (ระยะ 3):</b> ควรลดอาหารเค็มและโปรตีนสูง ปรึกษาแพทย์")
            conditions.add('kidney_disease')
        elif gfr < 90:
             issues['low'].append("<b>การทำงานของไตลดลงเล็กน้อย (ระยะ 2):</b> ควรดื่มน้ำให้เพียงพอและหลีกเลี่ยงยาที่มีผลต่อไต")
             conditions.add('kidney_disease')

    # --- แก้ไข: เพิ่มความละเอียดในการแปลผลเอนไซม์ตับ ---
    sgot = get_float(person_data, "SGOT")
    sgpt = get_float(person_data, "SGPT")
    sgot_upper, sgpt_upper = 37, 41
    if (sgot and sgot > sgot_upper) or (sgpt and sgpt > sgpt_upper):
        if (sgot and sgot > sgot_upper * 3) or (sgpt and sgpt > sgpt_upper * 3):
            issues['high'].append("<b>ค่าเอนไซม์ตับสูงมาก:</b> บ่งชี้ภาวะตับอักเสบ ควรพบแพทย์โดยเร็ว")
        else:
            issues['medium'].append("<b>ค่าเอนไซม์ตับสูง:</b> อาจเกิดจากไขมันพอกตับ ควรลดของมัน แอลกอฮอล์")
        conditions.add('liver')

    # --- แก้ไข: เพิ่มความละเอียดในการแปลผลกรดยูริก ---
    uric = get_float(person_data, "Uric Acid")
    if uric:
        if uric > 9.0:
            issues['medium'].append("<b>กรดยูริกสูงมาก:</b> มีความเสี่ยงสูงต่อโรคเกาต์ ควรปรึกษาแพทย์")
            conditions.add('uric_acid')
        elif uric > 7.2:
            issues['low'].append("<b>กรดยูริกสูง:</b> เสี่ยงต่อโรคเกาต์ ควรลดการทานเครื่องในสัตว์ สัตว์ปีก")
            conditions.add('uric_acid')

    # --- 3. Complete Blood Count (CBC) ---
    sex = person_data.get("เพศ", "ชาย")
    hb = get_float(person_data, "Hb(%)")
    wbc = get_float(person_data, "WBC (cumm)")
    platelet = get_float(person_data, "Plt (/mm)")
    
    hb_limit = 12 if sex == "หญิง" else 13
    if hb and hb < hb_limit:
        issues['medium'].append("<b>ภาวะโลหิตจาง:</b> ควรทานอาหารที่มีธาตุเหล็กสูงและตรวจหาสาเหตุเพิ่มเติม")
        conditions.add('anemia')
        
    if wbc:
        if wbc > 10000: issues['medium'].append("<b>เม็ดเลือดขาวสูง:</b> อาจมีการอักเสบหรือติดเชื้อในร่างกาย ควรตรวจหาสาเหตุ")
        if wbc < 4000: issues['low'].append("<b>เม็ดเลือดขาวต่ำ:</b> อาจส่งผลต่อภูมิคุ้มกัน ควรพักผ่อนให้เพียงพอ")
        
    if platelet:
        if platelet < 150000: issues['medium'].append("<b>เกล็ดเลือดต่ำ:</b> อาจเสี่ยงเลือดออกง่าย ควรระมัดระวังอุบัติเหตุและปรึกษาแพทย์")
        if platelet > 500000: issues['medium'].append("<b>เกล็ดเลือดสูง:</b> ควรพบแพทย์เพื่อตรวจหาสาเหตุ")

    # --- 4. Urinalysis, Stool, X-ray, EKG, Hepatitis ---
    urine_issues = interpret_urine(person_data)
    for issue, (text, level) in urine_issues.items():
        issues[level].append(f"<b>{issue}:</b> {text}")

    stool_issues = interpret_stool(person_data)
    for issue, (text, level) in stool_issues.items():
        issues[level].append(f"<b>{issue}:</b> {text}")
        
    hep_issues = interpret_hepatitis(person_data)
    for issue, (text, level) in hep_issues.items():
        issues[level].append(f"<b>{issue}:</b> {text}")

    year = person_data.get("Year", "")
    cxr_col = f"CXR{str(year)[-2:]}" if str(year) != "" and str(year) != str(np.datetime64('now', 'Y').astype(int) + 1970 + 543) else "CXR"
    cxr_result, cxr_status = interpret_cxr(person_data.get(cxr_col, ''))
    if cxr_status == 'abnormal':
        issues['high'].append(f"<b>ผลเอกซเรย์ทรวงอกผิดปกติ ({cxr_result}):</b> ควรพบแพทย์เพื่อตรวจวินิจฉัยเพิ่มเติม")

    ekg_col = f"EKG{str(year)[-2:]}" if str(year) != "" and str(year) != str(np.datetime64('now', 'Y').astype(int) + 1970 + 543) else "EKG"
    ekg_result, ekg_status = interpret_ekg(person_data.get(ekg_col, ''))
    if ekg_status == 'abnormal':
        issues['high'].append(f"<b>ผลคลื่นไฟฟ้าหัวใจผิดปกติ ({ekg_result}):</b> ควรพบแพทย์โรคหัวใจ")

    # --- Build the final HTML output ---
    
    if not any(issues.values()):
        return """
        <div style='background-color: #e8f5e9; color: #1b5e20; padding: 1rem; border-radius: 8px; text-align: center;'>
            <h4 style='margin:0;'>ผลการตรวจสุขภาพโดยรวมอยู่ในเกณฑ์ดี</h4>
            <p style='margin-top: 0.5rem;'>ไม่พบความผิดปกติที่มีนัยสำคัญ ขอแนะนำให้รักษาสุขภาพที่ดีเช่นนี้ต่อไป และมาตรวจสุขภาพประจำปีอย่างสม่ำเสมอ</p>
        </div>
        """

    # --- Build Left Column (Issues) ---
    left_column_parts = []
    if issues['high']:
        left_column_parts.append("<div style='border-left: 5px solid #c62828; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #c62828; margin-top:0;'>ควรพบแพทย์เพื่อประเมินเพิ่มเติม</h5><ul>")
        for item in set(issues['high']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")

    if issues['medium']:
        left_column_parts.append("<div style='border-left: 5px solid #f9a825; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #f9a825; margin-top:0;'>ประเด็นสุขภาพที่ควรปรับพฤติกรรม</h5><ul>")
        for item in set(issues['medium']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")

    if issues['low']:
        left_column_parts.append("<div style='border-left: 5px solid #1976d2; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #1976d2; margin-top:0;'>ข้อควรระวังและการเฝ้าติดตาม</h5><ul>")
        for item in set(issues['low']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")

    # --- Build Right Column (Health Plan) ---
    right_column_parts = []
    health_plan = {'nutrition': set(), 'exercise': set(), 'monitoring': set()}
    
    if 'diabetes' in conditions or 'prediabetes' in conditions:
        health_plan['nutrition'].add("ควบคุมอาหารประเภทแป้งและน้ำตาลอย่างจริงจัง")
        health_plan['monitoring'].add("ตรวจติดตามระดับน้ำตาลในเลือดสม่ำเสมอ")
    if 'hypertension' in conditions or 'prehypertension' in conditions:
        health_plan['nutrition'].add("ลดอาหารเค็มและโซเดียมสูง")
        health_plan['monitoring'].add("วัดความดันโลหิตที่บ้านอย่างสม่ำเสมอ")
    if 'dyslipidemia' in conditions:
        health_plan['nutrition'].add("ลดอาหารมัน ของทอด และไขมันอิ่มตัว")
    if 'obesity' in conditions or 'overweight' in conditions:
        health_plan['nutrition'].add("ควบคุมปริมาณอาหารและเลือกทานอาหารแคลอรี่ต่ำ")
    if 'kidney_disease' in conditions:
        health_plan['nutrition'].add("ลดอาหารเค็มจัดและโปรตีนสูงบางชนิด (ปรึกษาแพทย์)")
        health_plan['monitoring'].add("ดื่มน้ำให้เพียงพอและหลีกเลี่ยงยาที่มีผลต่อไต")
    if 'liver' in conditions:
        health_plan['nutrition'].add("งดเครื่องดื่มแอลกอฮอล์และลดอาหารไขมันสูง")
    if 'uric_acid' in conditions:
        health_plan['nutrition'].add("ลดการทานเครื่องในสัตว์, สัตว์ปีก, และยอดผัก")
    if 'anemia' in conditions:
        health_plan['nutrition'].add("ทานอาหารที่มีธาตุเหล็กและวิตามินซีสูง เช่น ตับ, เนื้อแดง, ผักใบเขียว")

    if any(c in conditions for c in ['obesity', 'overweight', 'hypertension', 'diabetes', 'prediabetes', 'dyslipidemia']):
        health_plan['exercise'].add("ออกกำลังกายแบบแอโรบิก (เดินเร็ว, วิ่ง, ว่ายน้ำ) อย่างน้อย 150 นาที/สัปดาห์")
    else:
        health_plan['exercise'].add("เคลื่อนไหวร่างกายอย่างสม่ำเสมอ 3-4 วัน/สัปดาห์")

    health_plan['monitoring'].add("นอนหลับพักผ่อนให้เพียงพอ 7-8 ชั่วโมง/คืน")
    health_plan['monitoring'].add("ตรวจสุขภาพประจำปีเพื่อติดตามผล")

    right_column_parts.append("<div style='border-left: 5px solid #4caf50; padding-left: 15px;'>")
    right_column_parts.append("<h5 style='color: #4caf50; margin-top:0;'>แผนการดูแลสุขภาพเบื้องต้น (Your Health Plan)</h5>")
    
    if health_plan['nutrition']:
        right_column_parts.append("<b>ด้านโภชนาการ:</b><ul>")
        for item in sorted(list(health_plan['nutrition'])): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")
        
    if health_plan['exercise']:
        right_column_parts.append("<b>ด้านการออกกำลังกาย:</b><ul>")
        for item in sorted(list(health_plan['exercise'])): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")

    if health_plan['monitoring']:
        right_column_parts.append("<b>การติดตามและดูแลทั่วไป:</b><ul>")
        for item in sorted(list(health_plan['monitoring'])): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")

    right_column_parts.append("</div>")

    # --- Combine into a two-column layout ---
    left_html = "".join(left_column_parts)
    right_html = "".join(right_column_parts)

    final_html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 30px; align-items: flex-start;">
        <div style="flex: 1; min-width: 300px;">
            {left_html}
        </div>
        <div style="flex: 1; min-width: 300px;">
            {right_html}
        </div>
    </div>
    """
    
    return final_html
    
def interpret_vision(vision_raw, color_blindness_raw):
    """
    แปลผลตรวจสมรรถภาพการมองเห็นและตาบอดสี
    Args:
        vision_raw (str): ผลตรวจสายตาจากฐานข้อมูล
        color_blindness_raw (str): ผลตรวจตาบอดสีจากฐานข้อมูล
    Returns:
        tuple: (สรุปผลสายตา, สรุปผลตาบอดสี, คำแนะนำ)
    """
    vision_summary = "ไม่ได้เข้ารับการตรวจ"
    color_blindness_summary = "ไม่ได้เข้ารับการตรวจ"
    advice_parts = []

    # แปลผลสายตา
    if not is_empty(vision_raw):
        vision_lower = str(vision_raw).lower().strip()
        if "ปกติ" in vision_lower:
            vision_summary = "ปกติ"
        elif "ผิดปกติ" in vision_lower or "สั้น" in vision_lower or "ยาว" in vision_lower or "เอียง" in vision_lower:
            vision_summary = f"ผิดปกติ"
            advice_parts.append("สายตาผิดปกติ ควรปรึกษาจักษุแพทย์เพื่อตรวจวัดสายตาและพิจารณาตัดแว่น")
        else:
            vision_summary = vision_raw

    # แปลผลตาบอดสี
    if not is_empty(color_blindness_raw):
        color_blindness_lower = str(color_blindness_raw).lower().strip()
        if "ปกติ" in color_blindness_lower:
            color_blindness_summary = "ปกติ"
        elif "ผิดปกติ" in color_blindness_lower:
            color_blindness_summary = "ผิดปกติ"
            advice_parts.append("ภาวะตาบอดสี ควรหลีกเลี่ยงงานที่ต้องใช้การแยกสีที่สำคัญ")
        else:
            color_blindness_summary = color_blindness_raw

    return vision_summary, color_blindness_summary, " ".join(advice_parts)

def interpret_hearing(hearing_raw):
    """
    แปลผลตรวจสมรรถภาพการได้ยิน (แบบสรุปเก่า)
    Args:
        hearing_raw (str): ผลตรวจการได้ยินจากฐานข้อมูล
    Returns:
        tuple: (สรุปผล, คำแนะนำ)
    """
    summary = "ไม่ได้เข้ารับการตรวจ"
    advice = ""

    if not is_empty(hearing_raw):
        hearing_lower = str(hearing_raw).lower().strip()
        if "ปกติ" in hearing_lower:
            summary = "ปกติ"
        elif "ผิดปกติ" in hearing_lower or "เสื่อม" in hearing_lower:
            summary = f"ผิดปกติ"
            advice = "การได้ยินผิดปกติ ควรพบแพทย์เพื่อตรวจประเมินและหาสาเหตุ"
        else:
            summary = hearing_raw

    return summary, advice

def interpret_audiogram(current_year_data, all_person_history_df=None):
    """
    แปลผลตรวจสมรรถภาพการได้ยินอย่างละเอียด (Audiogram)
    - เปรียบเทียบกับ Baseline ที่ระบุ (คอลัมน์ B)
    - หากไม่มี Baseline ที่ระบุ จะใช้ผลตรวจปีแรกเป็น Baseline โดยอัตโนมัติ
    Args:
        current_year_data (dict): Dictionary ข้อมูลของบุคคลในปีที่เลือก
        all_person_history_df (pd.DataFrame, optional): DataFrame ที่มีประวัติการตรวจทั้งหมดของบุคคลนั้น
                                                        จำเป็นสำหรับการหา Baseline จากปีแรก
    Returns:
        dict: ผลการแปลข้อมูลอย่างละเอียด
    """
    def to_int(val):
        if is_empty(val): return None
        try: return int(float(val))
        except (ValueError, TypeError): return None

    freq_columns = {
        '500 Hz': ('R500', 'L500'),
        '1000 Hz': ('R1k', 'L1k'),
        '2000 Hz': ('R2k', 'L2k'),
        '3000 Hz': ('R3k', 'L3k'),
        '4000 Hz': ('R4k', 'L4k'),
        '6000 Hz': ('R6k', 'L6k'),
        '8000 Hz': ('R8k', 'L8k'),
    }

    results = {
        'raw_values': {},
        'baseline_values': {freq: {'right': None, 'left': None} for freq in freq_columns},
        'shift_values': {freq: {'right': None, 'left': None} for freq in freq_columns},
        'averages': {},
        'summary': {},
        'advice': "",
        'sts_detected': False,
        'baseline_source': 'none', # 'none', 'explicit', 'first_year'
        'baseline_year': None,
        'other_data': {}
    }

    # 1. ดึงข้อมูลปัจจุบัน (Current Year Data)
    has_current_data = False
    for freq, (r_col, l_col) in freq_columns.items():
        r_val = to_int(current_year_data.get(r_col))
        l_val = to_int(current_year_data.get(l_col))
        results['raw_values'][freq] = {'right': r_val, 'left': l_val}
        if r_val is not None or l_val is not None:
            has_current_data = True

    if not has_current_data:
        results['summary']['overall'] = "ไม่ได้เข้ารับการตรวจ"
        return results

    # 2. ค้นหาและกำหนดค่า Baseline
    # 2.1 ตรวจสอบหา Baseline ที่ระบุ (Explicit) ในข้อมูลปีปัจจุบัน
    has_explicit_baseline = False
    for freq, (r_col, l_col) in freq_columns.items():
        r_base_val = to_int(current_year_data.get(r_col + 'B'))
        l_base_val = to_int(current_year_data.get(l_col + 'B'))
        if r_base_val is not None or l_base_val is not None:
            has_explicit_baseline = True
        # เก็บค่า baseline ที่อาจจะมีไว้ก่อน
        if r_base_val is not None: results['baseline_values'][freq]['right'] = r_base_val
        if l_base_val is not None: results['baseline_values'][freq]['left'] = l_base_val


    if has_explicit_baseline:
        results['baseline_source'] = 'explicit'
        results['baseline_year'] = current_year_data.get('Year') # Assume explicit baseline is for the current year context
    
    # 2.2 หากไม่มี Baseline ที่ระบุ, ให้ค้นหาจากปีแรกที่มีการตรวจ
    elif all_person_history_df is not None and not all_person_history_df.empty:
        # กรองหาปีที่มีข้อมูลการได้ยิน (อย่างน้อยหนึ่งค่า)
        hearing_cols = [col for pair in freq_columns.values() for col in pair]
        hearing_test_years_df = all_person_history_df.dropna(
            subset=hearing_cols,
            how='all'
        ).copy()
        
        if not hearing_test_years_df.empty:
            hearing_test_years_df = hearing_test_years_df.sort_values(by='Year', ascending=True)
            first_test_row = hearing_test_years_df.iloc[0]
            
            # ตรวจสอบว่าปีที่เลือกไม่ใช่ปีเดียวกับปีแรก (ถ้าใช่ ก็ไม่มี baseline ให้เทียบ)
            if int(first_test_row['Year']) != int(current_year_data['Year']):
                results['baseline_source'] = 'first_year'
                results['baseline_year'] = int(first_test_row['Year'])
                
                for freq, (r_col, l_col) in freq_columns.items():
                    results['baseline_values'][freq] = {
                        'right': to_int(first_test_row.get(r_col)),
                        'left': to_int(first_test_row.get(l_col))
                    }

    # 3. คำนวณค่าเฉลี่ยและสรุปผลของปีปัจจุบัน
    results['averages']['right_500_2000'] = to_int(current_year_data.get('AVRต่ำ'))
    results['averages']['left_500_2000'] = to_int(current_year_data.get('AVLต่ำ'))
    results['averages']['right_3000_6000'] = to_int(current_year_data.get('AVRสูง'))
    results['averages']['left_3000_6000'] = to_int(current_year_data.get('AVLสูง'))
    
    summary_r = current_year_data.get('ระดับการได้ยินหูขวา', '')
    summary_l = current_year_data.get('ระดับการได้ยินหูซ้าย', '')
    results['summary']['right'] = "N/A" if is_empty(summary_r) else summary_r
    results['summary']['left'] = "N/A" if is_empty(summary_l) else summary_l
    results['summary']['overall'] = current_year_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    # --- START OF CHANGE: Handle None for advice ---
    results['advice'] = current_year_data.get('คำแนะนำผลตรวจการได้ยิน', '') or "ไม่มีคำแนะนำเพิ่มเติม"
    # --- END OF CHANGE ---

    # 4. คำนวณ Shift และ STS ถ้ามีข้อมูล Baseline
    if results['baseline_source'] != 'none':
        sts_freqs = ['2000 Hz', '3000 Hz', '4000 Hz']
        shifts_r_for_avg, shifts_l_for_avg = [], []
        
        for freq, values in results['raw_values'].items():
            base_vals = results['baseline_values'][freq]
            shift_r, shift_l = None, None
            
            if values['right'] is not None and base_vals['right'] is not None:
                shift_r = values['right'] - base_vals['right']
            if values['left'] is not None and base_vals['left'] is not None:
                shift_l = values['left'] - base_vals['left']
            
            results['shift_values'][freq] = {'right': shift_r, 'left': shift_l}

            if freq in sts_freqs:
                if shift_r is not None: shifts_r_for_avg.append(shift_r)
                if shift_l is not None: shifts_l_for_avg.append(shift_l)
        
        avg_shift_r = np.mean(shifts_r_for_avg) if shifts_r_for_avg else 0
        avg_shift_l = np.mean(shifts_l_for_avg) if shifts_l_for_avg else 0

        if avg_shift_r >= 10 or avg_shift_l >= 10:
            results['sts_detected'] = True
    
    # 5. ดึงข้อมูลสรุปอื่นๆ
    other_keys = [
        'ผลการได้ยินเปรียบเทียบALLFq', 'ผลการได้ยินเปรียบเทียบAVRFqต่ำ',
        'ผลการได้ยินเปรียบเทียบAVRFqสูง', 'ข้อมูลประกอบการตรวจสมรรถภาพการได้ยิน'
    ]
    for key in other_keys:
        val = current_year_data.get(key)
        if not is_empty(val):
            results['other_data'][key] = val

    return results


def interpret_lung_capacity(person_data):
    """
    แปลผลตรวจสมรรถภาพความจุปอดตามตรรกะมาตรฐานที่กำหนด
    Args:
        person_data (dict): Dictionary ข้อมูลของบุคคลนั้นๆ จากแถวใน DataFrame
    Returns:
        tuple: (สรุปผล, คำแนะนำ, dictionary ข้อมูลดิบที่เกี่ยวข้อง)
    """
    def to_float(val):
        if is_empty(val): return None
        try: return float(val)
        except (ValueError, TypeError): return None

    # ดึงข้อมูลจาก person_data ด้วย key ที่ถูกต้อง
    raw_values = {
        'FVC': to_float(person_data.get('FVC')),
        'FVC predic': to_float(person_data.get('FVC predic')),
        'FVC %': to_float(person_data.get('FVC เปอร์เซ็นต์')),
        'FEV1': to_float(person_data.get('FEV1')),
        'FEV1 predic': to_float(person_data.get('FEV1 predic')),
        'FEV1 %': to_float(person_data.get('FEV1เปอร์เซ็นต์')),
        'FEV1/FVC %': to_float(person_data.get('FEV1/FVC%')),
        'FEV1/FVC % pre': to_float(person_data.get('FEV1/FVC % pre')),
        'PEF': to_float(person_data.get('PEF')),
        'FEF25-75': to_float(person_data.get('FEF25-75')),
        'FEF25-75 %': to_float(person_data.get('FEF25-75 %')),
    }

    fvc_p = raw_values['FVC %']
    fev1_p = raw_values['FEV1 %']
    ratio = raw_values['FEV1/FVC %']

    # ตรวจสอบว่ามีข้อมูลการตรวจหรือไม่
    if all(v is None for v in [fvc_p, fev1_p, ratio]):
        return "ไม่ได้เข้ารับการตรวจ", "", raw_values

    # หากข้อมูลสำคัญขาดไป
    if fvc_p is None or ratio is None:
        return "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ", "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม", raw_values

    summary = "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ" # Default summary

    # Interpretation Logic based on provided standard
    if ratio < 70:
        if fvc_p < 80:
            summary = "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ" # Mixed -> Inconclusive as per list
        else: # Obstructive
            if fev1_p is not None:
                if fev1_p >= 66: # Mild (66-80 from image, but logic implies >=66)
                     summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้นเล็กน้อย"
                elif fev1_p >= 50: # Moderate
                     summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้นปานกลาง"
                else: # Severe
                     summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้นรุนแรง"
            else: # fev1_p is None
                summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้น"

    elif ratio >= 70:
        if fvc_p < 80: # Restrictive
            if fvc_p >= 66: # Mild
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัวเล็กน้อย"
            elif fvc_p >= 50: # Moderate
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัวปานกลาง"
            else: # Severe
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัวรุนแรง"
        else: # Normal
            summary = "สมรรถภาพปอดปกติ"

    # --- NEW ADVICE LOGIC ---
    # Set advice based on severity
    if summary == "สมรรถภาพปอดปกติ" or "เล็กน้อย" in summary:
        advice = "เพิ่มสมรรถภาพปอดด้วยการออกกำลังกาย หลีกเลี่ยงการสัมผัสสารเคมี ฝุ่น และควัน"
    else:
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"
        
    return summary, advice, raw_values

def generate_holistic_advice(person_data):
    """
    สร้างสรุปความเห็นของแพทย์แบบองค์รวมโดยอัตโนมัติจากข้อมูลสุขภาพทั้งหมด
    """
    def get_float(val):
        if is_empty(val): return None
        try: return float(str(val).replace(",", "").strip())
        except: return None

    issues = {'high': [], 'medium': [], 'low': []}

    # 1. BMI and Blood Pressure
    weight = get_float(person_data.get("น้ำหนัก"))
    height = get_float(person_data.get("ส่วนสูง"))
    sbp = get_float(person_data.get("SBP"))
    dbp = get_float(person_data.get("DBP"))

    if weight and height and height > 0:
        bmi = weight / ((height / 100) ** 2)
        if bmi >= 30:
            issues['medium'].append("ภาวะอ้วน (BMI ≥ 30)")
        elif bmi >= 25:
            issues['low'].append("น้ำหนักเกิน (BMI 25-29.9)")

    if sbp and dbp:
        if sbp >= 160 or dbp >= 100:
            issues['high'].append(f"ความดันโลหิตสูงระดับรุนแรง ({int(sbp)}/{int(dbp)} mmHg)")
        elif sbp >= 140 or dbp >= 90:
            issues['medium'].append(f"ความดันโลหิตสูง ({int(sbp)}/{int(dbp)} mmHg)")
        elif sbp >= 120 or dbp >= 80:
            issues['low'].append(f"ความดันโลหิตเริ่มสูง ({int(sbp)}/{int(dbp)} mmHg)")

    # 2. Blood Sugar (FBS)
    fbs = get_float(person_data.get("FBS"))
    if fbs:
        if fbs >= 126:
            issues['high'].append(f"ระดับน้ำตาลในเลือดสูง เข้าเกณฑ์เบาหวาน ({int(fbs)} mg/dL)")
        elif fbs >= 100:
            issues['medium'].append(f"ภาวะเสี่ยงเบาหวาน ({int(fbs)} mg/dL)")

    # 3. Lipids (ไขมัน)
    chol = get_float(person_data.get("CHOL"))
    tgl = get_float(person_data.get("TGL"))
    ldl = get_float(person_data.get("LDL"))
    hdl = get_float(person_data.get("HDL"))
    lipid_issues = []
    if chol and chol >= 240: lipid_issues.append("Cholesterol สูง")
    if tgl and tgl >= 200: lipid_issues.append("Triglyceride สูง")
    if ldl and ldl >= 160: lipid_issues.append("LDL สูง")
    if hdl and hdl < 40: lipid_issues.append("HDL ต่ำ")
    if lipid_issues:
        issues['medium'].append(f"ภาวะไขมันในเลือดผิดปกติ ({', '.join(lipid_issues)})")

    # 4. Kidney Function (GFR)
    gfr = get_float(person_data.get("GFR"))
    if gfr:
        if gfr < 30:
            issues['high'].append("การทำงานของไตลดลงอย่างมาก")
        elif gfr < 60:
            issues['medium'].append("การทำงานของไตเริ่มเสื่อม")

    # 5. Liver Function (SGOT/SGPT)
    sgot = get_float(person_data.get("SGOT"))
    sgpt = get_float(person_data.get("SGPT"))
    if (sgot and sgot > 37) or (sgpt and sgpt > 41):
        issues['medium'].append("ค่าเอนไซม์ตับสูงกว่าปกติ")

    # 6. Uric Acid
    uric = get_float(person_data.get("Uric Acid"))
    if uric and uric > 7.2:
        issues['low'].append("ระดับกรดยูริกสูง")

    # 7. CBC (Anemia)
    sex = person_data.get("เพศ", "ชาย")
    hb = get_float(person_data.get("Hb(%)"))
    hct = get_float(person_data.get("HCT"))
    hb_limit = 12 if sex == "หญิง" else 13
    hct_limit = 36 if sex == "หญิง" else 39
    if (hb and hb < hb_limit) or (hct and hct < hct_limit):
        issues['medium'].append("ภาวะโลหิตจาง")

    # --- Build the final summary string ---
    summary_parts = []
    if not any(issues.values()):
        return "ผลการตรวจสุขภาพโดยรวมอยู่ในเกณฑ์ปกติ ควรดูแลรักษาสุขภาพที่ดีเช่นนี้ต่อไป และมาตรวจสุขภาพประจำปีอย่างสม่ำเสมอ"

    summary_parts.append("ผลตรวจสุขภาพโดยรวมพบประเด็นที่ควรให้ความสำคัญดังนี้:")
    
    if issues['high']:
        summary_parts.append("<b><u>ประเด็นสำคัญเร่งด่วน:</u></b> " + " ".join([f"<li>{i}</li>" for i in issues['high']]))
    if issues['medium']:
        summary_parts.append("<b><u>ประเด็นที่ควรติดตามและปรับเปลี่ยนพฤติกรรม:</u></b> " + " ".join([f"<li>{i}</li>" for i in issues['medium']]))
    if issues['low']:
        summary_parts.append("<b><u>ประเด็นอื่นๆ:</u></b> " + " ".join([f"<li>{i}</li>" for i in issues['low']]))

    # Add concluding remarks
    if issues['high']:
        summary_parts.append("<br><b>คำแนะนำ:</b> จากผลตรวจข้างต้น ท่านมีความเสี่ยงสูง ควร<b>พบแพทย์</b>เพื่อประเมินอาการ รับการวินิจฉัย และการรักษาที่เหมาะสมโดยเร็วที่สุด")
    elif issues['medium']:
        summary_parts.append("<br><b>คำแนะนำ:</b> ควรปรับเปลี่ยนพฤติกรรมสุขภาพอย่างจริงจัง ทั้งด้านอาหารและการออกกำลังกาย เพื่อควบคุมภาวะเสี่ยงต่างๆ และควรตรวจติดตามผลเลือดตามคำแนะนำของแพทย์")
    else: # Only low issues
        summary_parts.append("<br><b>คำแนะนำ:</b> ควรใส่ใจดูแลสุขภาพและปรับพฤติกรรมเล็กน้อยเพื่อป้องกันไม่ให้ค่าต่างๆ ผิดปกติมากขึ้นในอนาคต")

    return "<ul>" + "".join(summary_parts) + "</ul>"
