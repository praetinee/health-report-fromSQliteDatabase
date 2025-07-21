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

def interpret_lung_capacity(fvc_percent_raw, fev1_percent_raw, ratio_raw):
    """
    แปลผลตรวจสมรรถภาพความจุปอด
    Args:
        fvc_percent_raw: ค่า FVC เปอร์เซ็นต์
        fev1_percent_raw: ค่า FEV1 เปอร์เซ็นต์
        ratio_raw: ค่า FEV1/FVC%
    Returns:
        tuple: (สรุปผล, คำแนะนำ, dictionary ข้อมูลดิบ)
    """
    summary = "ไม่ได้เข้ารับการตรวจ"
    advice = ""
    raw_values = {
        'FVC %': '-',
        'FEV1 %': '-',
        'FEV1/FVC %': '-'
    }
    
    try:
        fvc_p = float(fvc_percent_raw) if not is_empty(fvc_percent_raw) else None
        fev1_p = float(fev1_percent_raw) if not is_empty(fev1_percent_raw) else None
        ratio = float(ratio_raw) if not is_empty(ratio_raw) else None
        
        # Update raw_values with actual numbers if they exist
        if fvc_p is not None: raw_values['FVC %'] = fvc_p
        if fev1_p is not None: raw_values['FEV1 %'] = fev1_p
        if ratio is not None: raw_values['FEV1/FVC %'] = ratio

    except (ValueError, TypeError):
        return "ข้อมูลผลตรวจไม่ถูกต้อง", "กรุณาตรวจสอบข้อมูลนำเข้า", raw_values

    if fvc_p is None and fev1_p is None and ratio is None:
        return summary, advice, raw_values
        
    if fvc_p is None or ratio is None:
        return "สรุปผลไม่ได้ (ข้อมูลไม่เพียงพอ)", "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม", raw_values

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

    if "ปกติ" in summary:
        advice = "เพิ่มสมรรถภาพปอดด้วยการออกกำลังกาย หลีกเลี่ยงการสัมผัสสารเคมี ฝุ่น และควัน"
    elif "ผิดปกติ" in summary:
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"
    elif not summary:
        summary = "สรุปผลไม่ได้ (มีความคลาดเคลื่อนในการทดสอบ)"
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"
        
    return summary, advice, raw_values
