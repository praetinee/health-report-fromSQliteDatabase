import pandas as pd
import numpy as np

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
    results['advice'] = current_year_data.get('คำแนะนำผลตรวจการได้ยิน', 'ไม่มีคำแนะนำเพิ่มเติม')

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
