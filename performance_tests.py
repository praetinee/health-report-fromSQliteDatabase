import pandas as pd

def is_empty(val):
    """
    ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่
    """
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def interpret_vision(person_data):
    """
    แปลผลตรวจสมรรถภาพการมองเห็นแบบละเอียด
    Args:
        person_data (dict): Dictionary ข้อมูลของบุคคลนั้นๆ จากแถวใน DataFrame
    Returns:
        dict: Dictionary ที่มีผลการตรวจแต่ละรายการ, สรุป และคำแนะนำ
    """
    
    # กำหนดรายการตรวจและชื่อคอลัมน์ในฐานข้อมูล
    vision_tests = {
        "ความชัดของภาพระยะไกล": ("ป.ความชัดของภาพระยะไกล", "ผ.ความชัดของภาพระยะไกล"),
        "ความชัดของภาพระยะใกล้": ("ป.ความชัดของภาพระยะใกล้", "ผ.ความชัดของภาพระยะใกล้"),
        "การมองเห็นภาพสามมิติ": ("ป.การกะระยะและมองความชัดลึกของภาพ", "ผ.การกะระยะและมองความชัดลึกของภาพ"),
        "การจำแนกสี": ("ป.การจำแนกสี", "ผ.การจำแนกสี"),
        "การรวมภาพ": ("ป.การรวมภาพ", "ผ.การรวมภาพ"),
        "ความสมดุลกล้ามเนื้อตา (แนวนอน)": ("ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน", "ผิดปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน"),
        "ความสมดุลกล้ามเนื้อตา (แนวตั้ง)": ("ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง", "ผิดปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง"),
        "สายตาเขซ่อนเร้น": (None, "ผ.สายตาเขซ่อนเร้น"), # มีแต่คอลัมน์ผิดปกติ
        "ลานสายตา": ("ป.ลานสายตา", None), # มีแต่คอลัมน์ปกติ
    }
    
    results = {}
    has_any_data = False
    
    for test_name, (normal_col, abnormal_col) in vision_tests.items():
        normal_val = person_data.get(normal_col) if normal_col else None
        abnormal_val = person_data.get(abnormal_col) if abnormal_col else None

        if not is_empty(normal_val):
            results[test_name] = "ปกติ"
            has_any_data = True
        elif not is_empty(abnormal_val):
            results[test_name] = "ผิดปกติ"
            has_any_data = True
        else:
            results[test_name] = "ไม่มีข้อมูล"

    # ถ้าไม่มีข้อมูลการตรวจใดๆ เลย
    if not has_any_data:
        return {
            "results": {},
            "summary": "ไม่ได้เข้ารับการตรวจ",
            "recommendation": "",
            "work_fitness": ""
        }

    # ดึงข้อมูลสรุปและคำแนะนำ
    summary = "สรุปผล: "
    abnormal_items = [name for name, res in results.items() if res == 'ผิดปกติ']
    
    if not abnormal_items:
        summary += "สมรรถภาพการมองเห็นโดยรวมปกติ"
    else:
        summary += f"พบความผิดปกติในส่วนของ {', '.join(abnormal_items)}"

    recommendation = person_data.get("แนะนำABN EYE", "")
    work_fitness = person_data.get("สรุปเหมาะสมกับงาน", "")
    
    return {
        "results": results,
        "summary": summary,
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
