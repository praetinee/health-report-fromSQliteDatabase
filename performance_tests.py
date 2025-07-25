import pandas as pd

def is_empty(val):
    """
    ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่
    """
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def interpret_vision(person_data):
    """
    แปลผลตรวจสมรรถภาพการมองเห็นแบบละเอียดตามรายการใหม่
    Args:
        person_data (dict): Dictionary ข้อมูลของบุคคลนั้นๆ จากแถวใน DataFrame
    Returns:
        dict: Dictionary ที่มี DataFrame ของผลตรวจ, สรุป และคำแนะนำ
    """
    
    # Mapping a user-friendly name to the potential normal/abnormal columns
    # This structure helps in iterating and checking for values easily
    vision_test_mapping = {
        "1. การมองด้วย 2 ตา (Binocular vision)": ("ป.การรวมภาพ", "ผ.การรวมภาพ"),
        "2. การมองภาพระยะไกลสองตา (Far vision – Both)": ("ป.ความชัดของภาพระยะไกล", "ผ.ความชัดของภาพระยะไกล"),
        "3. การมองภาพระยะไกลตาขวา (Far vision – Right)": ("การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)", None), # This is a value field
        "4. การมองภาพระยะไกลตาซ้าย (Far vision – Left)": ("การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)", None), # This is a value field
        "5. การมองภาพ 3 มิติ (Stereo depth)": ("ป.การกะระยะและมองความชัดลึกของภาพ", "ผ.การกะระยะและมองความชัดลึกของภาพ"),
        "6. การมองจำแนกสี (Color discrimination)": ("ป.การจำแนกสี", "ผ.การจำแนกสี"),
        "7. ความสมดุลกล้ามเนื้อระยะไกลแนวตั้ง (Far vertical phoria)": ("ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง", "ผิดปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง"),
        "8. ความสมดุลกล้ามเนื้อระยะไกลแนวนอน (Far lateral phoria)": ("ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน", "ผิดปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน"),
        "9. การมองภาพระยะใกล้สองตา (Near vision – Both)": ("ป.ความชัดของภาพระยะใกล้", "ผ.ความชัดของภาพระยะใกล้"),
        "10. การมองภาพระยะใกล้ตาขวา (Near vision – Right)": ("การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)", None), # This is a value field
        "11. การมองภาพระยะใกล้ตาซ้าย (Near vision – Left)": ("การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)", None), # This is a value field
        "12. ความสมดุลกล้ามเนื้อระยะใกล้แนวนอน (Near lateral phoria)": ("ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน", "ผิดปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน"),
        "13. ลานสายตา (Visual field)": ("ป.ลานสายตา", "ผ.ลานสายตา"),
    }

    report_data = []
    has_any_data = False

    for test_name, (normal_col, abnormal_col) in vision_test_mapping.items():
        result_normal = ""
        result_abnormal = ""
        
        # Check for value-based fields first
        if abnormal_col is None:
            value = person_data.get(normal_col)
            if not is_empty(value):
                # If there's a value, we can consider it as the 'normal' result for display purposes
                result_normal = str(value)
                has_any_data = True
        else: # Handle normal/abnormal flag fields
            if not is_empty(person_data.get(normal_col)):
                result_normal = "✓"
                has_any_data = True
            elif not is_empty(person_data.get(abnormal_col)):
                result_abnormal = "✓"
                has_any_data = True
        
        report_data.append({
            "รายการตรวจ (Vision Test)": test_name,
            "ปกติ (Normal)": result_normal,
            "ผิดปกติ (Abnormal)": result_abnormal
        })

    if not has_any_data:
        return {
            "summary": "ไม่ได้เข้ารับการตรวจ",
            "report_df": pd.DataFrame(),
            "recommendation": "",
            "work_fitness": ""
        }

    df = pd.DataFrame(report_data)
    recommendation = person_data.get("แนะนำABN EYE", "")
    work_fitness = person_data.get("สรุปเหมาะสมกับงาน", "")

    return {
        "summary": "มีผลการตรวจ",
        "report_df": df,
        "recommendation": recommendation if not is_empty(recommendation) else "ไม่มีคำแนะนำเพิ่มเติม",
        "work_fitness": work_fitness if not is_empty(work_fitness) else "ไม่ระบุ"
    }

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

    if all(v is None for v in [fvc_p, fev1_p, ratio]):
        return "ไม่ได้เข้ารับการตรวจ", "", raw_values

    if fvc_p is None or ratio is None:
        return "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ", "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม", raw_values

    summary = "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ"

    if ratio < 70:
        if fvc_p < 80:
            summary = "สมรรถภาพปอดสรุปผลไม่ได้เนื่องจากมีความคลาดเคลื่อนในการทดสอบ"
        else:
            if fev1_p is not None:
                if fev1_p >= 66:
                     summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้นเล็กน้อย"
                elif fev1_p >= 50:
                     summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้นปานกลาง"
                else:
                     summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้นรุนแรง"
            else:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบหลอดลมอุดกั้น"

    elif ratio >= 70:
        if fvc_p < 80:
            if fvc_p >= 66:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัวเล็กน้อย"
            elif fvc_p >= 50:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัวปานกลาง"
            else:
                summary = "สมรรถภาพปอดพบความผิดปกติแบบปอดจำกัดการขยายตัวรุนแรง"
        else:
            summary = "สมรรถภาพปอดปกติ"

    if summary == "สมรรถภาพปอดปกติ" or "เล็กน้อย" in summary:
        advice = "เพิ่มสมรรถภาพปอดด้วยการออกกำลังกาย หลีกเลี่ยงการสัมผัสสารเคมี ฝุ่น และควัน"
    else:
        advice = "ให้พบแพทย์เพื่อตรวจวินิจฉัย รักษาเพิ่มเติม"
        
    return summary, advice, raw_values
