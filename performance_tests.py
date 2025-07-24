import pandas as pd

def is_empty(val):
    """
    ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่
    """
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

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
    แปลผลตรวจสมรรถภาพการได้ยิน
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

def interpret_lung_capacity(fvc_raw, fvc_predic_raw, fvc_percent_raw, 
                            fev1_raw, fev1_predic_raw, fev1_percent_raw, 
                            ratio_raw, ratio_predic_raw,
                            pef_raw, fef2575_raw, fef2575_percent_raw):
    """
    แปลผลตรวจสมรรถภาพความจุปอด
    Args:
        All raw values from the database for lung capacity.
    Returns:
        tuple: (สรุปผล, คำแนะนำ, dictionary ข้อมูลดิบทั้งหมด)
    """
    summary = "ไม่ได้เข้ารับการตรวจ"
    advice = ""
    
    # Helper to safely convert to float
    def to_float(val):
        if is_empty(val):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # Populate raw_values with all provided data, converting to numbers where possible
    raw_values = {
        'FVC': to_float(fvc_raw),
        'FVC predic': to_float(fvc_predic_raw),
        'FVC %': to_float(fvc_percent_raw),
        'FEV1': to_float(fev1_raw),
        'FEV1 predic': to_float(fev1_predic_raw),
        'FEV1 %': to_float(fev1_percent_raw),
        'FEV1/FVC %': to_float(ratio_raw),
        'FEV1/FVC % pre': to_float(ratio_predic_raw),
        'PEF': to_float(pef_raw),
        'FEF25-75': to_float(fef2575_raw),
        'FEF25-75 %': to_float(fef2575_percent_raw),
    }

    fvc_p = raw_values['FVC %']
    fev1_p = raw_values['FEV1 %']
    ratio = raw_values['FEV1/FVC %']
    
    # Check if essential data for interpretation is missing
    if fvc_p is None and fev1_p is None and ratio is None:
        return summary, advice, raw_values
        
    if fvc_p is None or ratio is None:
        return "สรุปผลไม่ได้ (ข้อมูลไม่เพียงพอ)", "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม", raw_values

    # Interpretation Logic
    if ratio < 70:
        if fvc_p < 80:
            summary = "ความผิดปกติแบบผสม (Mixed)"
        else:
            if fev1_p is not None and fev1_p >= 60:
                summary = "ความผิดปกติแบบหลอดลมอุดกั้นเล็กน้อย"
            else:
                summary = "ความผิดปกติแบบหลอดลมอุดกั้น"
    elif ratio >= 70:
        if fvc_p < 80:
            if fvc_p >= 60:
                summary = "ความผิดปกติแบบปอดจำกัดการขยายตัวเล็กน้อย"
            else:
                summary = "ความผิดปกติแบบปอดจำกัดการขยายตัว"
        else:
            summary = "สมรรถภาพปอดปกติ"

    # Set advice based on summary
    if "ปกติ" in summary:
        advice = "เพิ่มสมรรถภาพปอดด้วยการออกกำลังกาย หลีกเลี่ยงการสัมผัสสารเคมี ฝุ่น และควัน"
    elif "ผิดปกติ" in summary:
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"
    elif not summary:
        summary = "สรุปผลไม่ได้ (มีความคลาดเคลื่อนในการทดสอบ)"
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"
        
    return summary, advice, raw_values
