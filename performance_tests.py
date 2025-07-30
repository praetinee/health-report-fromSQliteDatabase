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

def interpret_audiogram(person_data):
    """
    แปลผลตรวจสมรรถภาพการได้ยินอย่างละเอียด (Audiogram)
    Args:
        person_data (dict): Dictionary ข้อมูลของบุคคลนั้นๆ
    Returns:
        dict: ผลการแปลข้อมูลอย่างละเอียด
    """
    def to_int(val):
        if is_empty(val): return None
        try: return int(float(val))
        except (ValueError, TypeError): return None

    # --- สำคัญ: แก้ไขชื่อคอลัมน์ตรงนี้ให้ตรงกับฐานข้อมูลของคุณ ---
    # โครงสร้าง: 'ความถี่': ('ชื่อคอลัมน์หูขวา', 'ชื่อคอลัมน์หูซ้าย')
    freq_columns = {
        '500 Hz': ('R_500Hz', 'L_500Hz'),
        '1000 Hz': ('R_1000Hz', 'L_1000Hz'),
        '2000 Hz': ('R_2000Hz', 'L_2000Hz'),
        '3000 Hz': ('R_3000Hz', 'L_3000Hz'),
        '4000 Hz': ('R_4000Hz', 'L_4000Hz'),
        '6000 Hz': ('R_6000Hz', 'L_6000Hz'),
        '8000 Hz': ('R_8000Hz', 'L_8000Hz'),
    }
    # ---------------------------------------------------------

    results = {'raw_values': {}, 'averages': {}, 'summary': {}, 'advice': ""}
    has_data = False

    for freq, (r_col, l_col) in freq_columns.items():
        r_val = to_int(person_data.get(r_col))
        l_val = to_int(person_data.get(l_col))
        results['raw_values'][freq] = {'right': r_val, 'left': l_val}
        if r_val is not None or l_val is not None:
            has_data = True

    if not has_data:
        return {'summary': {'overall': "ไม่ได้เข้ารับการตรวจ"}, 'advice': "", 'raw_values': {}, 'averages': {}}

    # Calculate averages
    def calculate_avg(freq_keys, ear):
        vals = [results['raw_values'][f][ear] for f in freq_keys if results['raw_values'][f][ear] is not None]
        return sum(vals) / len(vals) if vals else None

    results['averages']['right_500_2000'] = calculate_avg(['500 Hz', '1000 Hz', '2000 Hz'], 'right')
    results['averages']['left_500_2000'] = calculate_avg(['500 Hz', '1000 Hz', '2000 Hz'], 'left')
    results['averages']['right_3000_6000'] = calculate_avg(['3000 Hz', '4000 Hz', '6000 Hz'], 'right')
    results['averages']['left_3000_6000'] = calculate_avg(['3000 Hz', '4000 Hz', '6000 Hz'], 'left')

    # Interpretation logic
    def classify_hearing(avg_val):
        if avg_val is None: return "ข้อมูลไม่เพียงพอ"
        if avg_val <= 25: return "ปกติ"
        if avg_val <= 40: return "หูตึงเล็กน้อย"
        if avg_val <= 55: return "หูตึงปานกลาง"
        if avg_val <= 70: return "หูตึงค่อนข้างรุนแรง"
        if avg_val <= 90: return "หูตึงรุนแรง"
        return "หูตึงรุนแรงมาก"

    summary_r = classify_hearing(results['averages']['right_500_2000'])
    summary_l = classify_hearing(results['averages']['left_500_2000'])
    results['summary']['right'] = summary_r
    results['summary']['left'] = summary_l

    if summary_r == "ปกติ" and summary_l == "ปกติ":
        results['summary']['overall'] = "การได้ยินโดยรวมปกติ"
        results['advice'] = "สมรรถภาพการได้ยินอยู่ในเกณฑ์ปกติ ควรหลีกเลี่ยงการอยู่ในที่เสียงดังเป็นเวลานานเพื่อถนอมการได้ยิน"
    else:
        results['summary']['overall'] = "การได้ยินผิดปกติ"
        advice_parts = []
        if summary_r != "ปกติ": advice_parts.append(f"หูขวา: {summary_r}")
        if summary_l != "ปกติ": advice_parts.append(f"หูซ้าย: {summary_l}")
        results['advice'] = f"ผลการได้ยิน: {', '.join(advice_parts)} ควรพบแพทย์ผู้เชี่ยวชาญด้านหู คอ จมูก เพื่อตรวจประเมินเพิ่มเติม และพิจารณาแนวทางการรักษาหรือใช้อุปกรณ์ช่วยฟัง"

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
