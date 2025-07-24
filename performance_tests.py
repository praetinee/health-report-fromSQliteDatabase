import pandas as pd

def is_empty(val):
    """
    ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่
    """
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def interpret_vision(vision_raw, color_blindness_raw):
    """
    แปลผลตรวจสมรรถภาพการมองเห็นและตาบอดสี
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
            vision_summary = "ผิดปกติ"
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
    แปลผลตรวจสมรรถภาพการได้ยิน
    """
    summary = "ไม่ได้เข้ารับการตรวจ"
    advice = ""

    if not is_empty(hearing_raw):
        hearing_lower = str(hearing_raw).lower().strip()
        if "ปกติ" in hearing_lower:
            summary = "ปกติ"
        elif "ผิดปกติ" in hearing_lower or "เสื่อม" in hearing_lower:
            summary = "ผิดปกติ"
            advice = "การได้ยินผิดปกติ ควรพบแพทย์เพื่อตรวจประเมินและหาสาเหตุ"
        else:
            summary = hearing_raw

    return summary, advice

def interpret_lung_capacity(person_data):
    """
    แปลผลตรวจสมรรถภาพความจุปอดตามมาตรฐานเดิม
    """
    # --- ตรวจสอบว่ามีการตรวจจริงหรือไม่ ---
    fvc_p_raw = person_data.get('FVC เปอร์เซ็นต์')
    fev1_p_raw = person_data.get('FEV1เปอร์เซ็นต์')
    ratio_raw = person_data.get('FEV1/FVC%')

    if is_empty(fvc_p_raw) and is_empty(fev1_p_raw) and is_empty(ratio_raw):
        return "ไม่ได้เข้ารับการตรวจ", "", {} # summary, advice, raw_values
    
    # --- Helper Functions ---
    def to_float(val):
        if is_empty(val): return None
        try:
            cleaned_val = str(val).split(' ')[0]
            return float(cleaned_val)
        except (ValueError, TypeError):
            return None

    # --- 1. ดึงข้อมูลและแปลงเป็นตัวเลข ---
    raw_values = {
        'FVC': to_float(person_data.get('FVC')), 'FEV1': to_float(person_data.get('FEV1')),
        'PEF': to_float(person_data.get('PEF')), 'FEF25-75': to_float(person_data.get('FEF25-75')),
        'FVC predic': to_float(person_data.get('FVC predic')), 'FEV1 predic': to_float(person_data.get('FEV1 predic')),
        'FEV1/FVC % pre': to_float(person_data.get('FEV1/FVC % pre')),
        'FVC %': to_float(fvc_p_raw), 'FEV1 %': to_float(fev1_p_raw),
        'FEV1/FVC %': to_float(ratio_raw), 'FEF25-75 %': to_float(person_data.get('FEF25-75%'))
    }

    fvc_p = raw_values.get('FVC %')
    fev1_p = raw_values.get('FEV1 %')
    ratio = raw_values.get('FEV1/FVC %')

    # --- 2. ตรวจสอบข้อมูลเบื้องต้น ---
    if any(v is None for v in [fvc_p, fev1_p, ratio]):
        summary = "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ"
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"
        return summary, advice, raw_values

    # --- 3. ตรรกะการแปลผลตามมาตรฐานเดิม ---
    summary = ""
    if ratio < 70:
        if fvc_p < 80:
            summary = "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ"
        else:
            if fev1_p >= 60:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้นเล็กน้อย"
            else:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้น"
    else:
        if fvc_p < 80:
            if fvc_p >= 60:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัวเล็กน้อย"
            else:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัว"
        else:
            summary = "สมรรถภาพปอดปกติ"
    
    if not summary:
        summary = "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ"

    # --- 4. กำหนดคำแนะนำ ---
    if "ปกติ" in summary:
        advice = "เพิ่มสมรรถภาพปอดด้วยการออกกำลังกาย หลีกเลี่ยงการสัมผัสสารเคมี ฝุ่น และควัน"
    else:
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"

    return summary, advice, raw_values
