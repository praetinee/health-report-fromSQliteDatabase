import pandas as pd

def is_empty(val):
    """
    ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่
    """
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def interpret_vision(vision_raw, color_blindness_raw):
    """
    แปลผลตรวจสมรรถภาพการมองเห็นและตาบอดสี
    (โค้ดส่วนนี้ยังคงเดิม ไม่มีการเปลี่ยนแปลง)
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
    (โค้ดส่วนนี้ยังคงเดิม ไม่มีการเปลี่ยนแปลง)
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

def interpret_lung_capacity(person_data):
    """
    แปลผลตรวจสมรรถภาพความจุปอดจาก dictionary ข้อมูลของบุคคล (ฉบับปรับปรุง)
    Args:
        person_data (dict): Dictionary ที่มีข้อมูลผลตรวจปอดทั้งหมด
    Returns:
        tuple: (สรุปผล, คำแนะนำ, dictionary ข้อมูลดิบทั้งหมด)
    """
    summary = "ไม่ได้เข้ารับการตรวจ"
    advice = ""

    def to_float(val):
        if is_empty(val): return None
        try: return float(str(val).strip())
        except (ValueError, TypeError): return None

    # ดึงข้อมูลจาก person_data โดยใช้ .get() เพื่อความปลอดภัย
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

    fvc_p = raw_values.get('FVC %')
    ratio = raw_values.get('FEV1/FVC %')

    # ตรวจสอบว่ามีข้อมูลสำคัญเพียงพอสำหรับการแปลผลหรือไม่
    if fvc_p is None or ratio is None:
        if any(v is not None for v in raw_values.values()):
            return "ข้อมูลไม่สมบูรณ์", "ข้อมูลบางส่วนขาดหายไป ทำให้ไม่สามารถสรุปผลได้อย่างชัดเจน", raw_values
        return summary, advice, raw_values

    # ตรรกะการแปลผล (ตามแนวทางมาตรฐาน)
    if ratio < 70:
        # Obstructive Pattern
        if fvc_p < 80:
            summary = "ความผิดปกติแบบผสม (Mixed)"
            advice = "พบความผิดปกติทั้งแบบหลอดลมอุดกั้นและปอดขยายตัวจำกัด ควรพบแพทย์เพื่อประเมินและรักษาเพิ่มเติม"
        else:
            summary = "ความผิดปกติแบบหลอดลมอุดกั้น (Obstructive)"
            advice = "มีภาวะหลอดลมอุดกั้น ซึ่งอาจพบในโรคหอบหืดหรือถุงลมโป่งพอง ควรพบแพทย์เพื่อวินิจฉัยและรักษา"
    elif fvc_p < 80:
        # Restrictive Pattern
        summary = "ความผิดปกติแบบปอดขยายตัวจำกัด (Restrictive)"
        advice = "ปอดขยายตัวได้น้อยกว่าปกติ ซึ่งอาจเกิดจากหลายสาเหตุ ควรพบแพทย์เพื่อตรวจหาสาเหตุเพิ่มเติม"
    else:
        summary = "สมรรถภาพปอดปกติ (Normal)"
        advice = "สมรรถภาพปอดอยู่ในเกณฑ์ปกติ ควรรักษาสุขภาพปอดโดยการออกกำลังกายและหลีกเลี่ยงมลภาวะ"
        
    return summary, advice, raw_values
