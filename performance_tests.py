import pandas as pd

def is_empty(val):
    """
    ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่ (ใช้ซ้ำจากไฟล์หลักเพื่อความสมบูรณ์)
    """
    return str(val).strip().lower() in ["", "-", "none", "nan", "null"]

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
    advice = []

    # แปลผลสายตา
    if not is_empty(vision_raw):
        vision_lower = str(vision_raw).lower().strip()
        if "ปกติ" in vision_lower:
            vision_summary = "ปกติ"
        elif "ผิดปกติ" in vision_lower or "สั้น" in vision_lower or "ยาว" in vision_lower or "เอียง" in vision_lower:
            vision_summary = f"ผิดปกติ ({vision_raw})"
            advice.append("สายตาผิดปกติ ควรปรึกษาจักษุแพทย์เพื่อตรวจวัดสายตาและพิจารณาตัดแว่น")
        else:
            vision_summary = vision_raw # แสดงผลตามที่กรอกมาถ้าไม่เข้าเงื่อนไข

    # แปลผลตาบอดสี
    if not is_empty(color_blindness_raw):
        color_blindness_lower = str(color_blindness_raw).lower().strip()
        if "ปกติ" in color_blindness_lower:
            color_blindness_summary = "ปกติ"
        elif "ผิดปกติ" in color_blindness_lower:
            color_blindness_summary = "ผิดปกติ"
            advice.append("ภาวะตาบอดสี ควรหลีกเลี่ยงงานที่ต้องใช้การแยกสีที่สำคัญ")
        else:
            color_blindness_summary = color_blindness_raw

    return vision_summary, color_blindness_summary, " ".join(advice)

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
            summary = f"ผิดปกติ ({hearing_raw})"
            advice = "การได้ยินผิดปกติ ควรพบแพทย์เพื่อตรวจประเมินและหาสาเหตุ"
        else:
            summary = hearing_raw

    return summary, advice

def interpret_lung_capacity(fvc_percent, fev1_percent, ratio):
    """
    แปลผลตรวจสมรรถภาพความจุปอดแบบง่าย
    Args:
        fvc_percent (float): %FVC (เทียบกับค่ามาตรฐาน)
        fev1_percent (float): %FEV1 (เทียบกับค่ามาตรฐาน)
        ratio (float): FEV1/FVC ratio
    Returns:
        tuple: (สรุปผล, คำแนะนำ)
    """
    summary = "ไม่ได้เข้ารับการตรวจ"
    advice = ""
    
    # ตรวจสอบว่ามีข้อมูลเพียงพอหรือไม่
    if is_empty(fvc_percent) and is_empty(fev1_percent) and is_empty(ratio):
        return summary, advice

    try:
        # แปลงค่าเป็น float, ถ้าแปลงไม่ได้ให้เป็น None
        fvc = float(fvc_percent) if not is_empty(fvc_percent) else None
        fev1 = float(fev1_percent) if not is_empty(fev1_percent) else None
        fev1_fvc_ratio = float(ratio) if not is_empty(ratio) else None

        # เริ่มการแปลผล
        if fvc is None or fev1 is None or fev1_fvc_ratio is None:
             summary = "ข้อมูลไม่เพียงพอต่อการแปลผล"
             return summary, ""

        if fvc >= 80 and fev1 >= 80 and fev1_fvc_ratio >= 70:
            summary = "ปกติ (Normal)"
        elif fev1_fvc_ratio < 70 and fev1 < 80:
            summary = "มีภาวะทางเดินหายใจอุดกั้น (Obstructive)"
            advice = "สมรรถภาพปอดมีภาวะอุดกั้น ควรหลีกเลี่ยงฝุ่นควันและสารเคมีที่ระคายเคืองระบบทางเดินหายใจ และปรึกษาแพทย์"
        elif fvc < 80 and fev1_fvc_ratio >= 70:
            summary = "มีความจุอากาศในปอดจำกัด (Restrictive)"
            advice = "สมรรถภาพปอดมีความจุปอดจำกัด ควรปรึกษาแพทย์เพื่อหาสาเหตุเพิ่มเติม"
        elif fvc < 80 and fev1_fvc_ratio < 70:
            summary = "เป็นแบบผสม (Mixed Pattern)"
            advice = "สมรรถภาพปอดผิดปกติแบบผสม ควรปรึกษาแพทย์เพื่อตรวจวินิจฉัยและรักษา"
        else:
            summary = "ไม่สามารถสรุปผลได้ชัดเจน"
            advice = "ผลตรวจสมรรถภาพปอดไม่สามารถสรุปได้ชัดเจน ควรปรึกษาแพทย์เพื่อประเมินซ้ำ"

    except (ValueError, TypeError):
        summary = "ข้อมูลผลตรวจไม่ถูกต้อง"
        advice = ""

    return summary, advice
