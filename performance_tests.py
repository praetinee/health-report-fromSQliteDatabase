import pandas as pd
import numpy as np
import re

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

    freq_columns = {
        '500 Hz': ('R500', 'L500'), '1000 Hz': ('R1k', 'L1k'), '2000 Hz': ('R2k', 'L2k'),
        '3000 Hz': ('R3k', 'L3k'), '4000 Hz': ('R4k', 'L4k'), '6000 Hz': ('R6k', 'L6k'),
        '8000 Hz': ('R8k', 'L8k'),
    }

    results = {
        'raw_values': {}, 'baseline_values': {}, 'shift_values': {},
        'averages': {}, 'summary': {}, 'advice': "", 'sts_detected': False,
        'other_data': {}
    }
    has_data = False
    has_baseline_data = False

    for freq, (r_col, l_col) in freq_columns.items():
        r_val = to_int(person_data.get(r_col))
        l_val = to_int(person_data.get(l_col))
        results['raw_values'][freq] = {'right': r_val, 'left': l_val}
        if r_val is not None or l_val is not None: has_data = True

        r_base_val = to_int(person_data.get(r_col + 'B'))
        l_base_val = to_int(person_data.get(l_col + 'B'))
        results['baseline_values'][freq] = {'right': r_base_val, 'left': l_base_val}
        if r_base_val is not None or l_base_val is not None: has_baseline_data = True

    if not has_data:
        return {'summary': {'overall': "ไม่ได้เข้ารับการตรวจ"}, 'advice': ""}

    def classify_hearing(avg_val):
        if avg_val is None: return "ข้อมูลไม่เพียงพอ"
        if avg_val <= 25: return "ปกติ"
        if avg_val <= 40: return "หูตึงเล็กน้อย"
        if avg_val <= 55: return "หูตึงปานกลาง"
        if avg_val <= 70: return "หูตึงค่อนข้างรุนแรง"
        if avg_val <= 90: return "หูตึงรุนแรง"
        return "หูตึงรุนแรงมาก"

    def format_hearing_summary_html(summary_text, severity_text, ear_values):
        if is_empty(summary_text) or "N/A" in summary_text:
            return f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0 0 0; color: var(--text-color);">N/A</p>'
        
        if "ปกติ" in summary_text:
            return f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0 0 0; color: var(--text-color);">{summary_text}</p>'

        main_status = severity_text if not is_empty(severity_text) and "ข้อมูลไม่เพียงพอ" not in severity_text else "การได้ยินลดลง"
        
        affected_freqs = []
        for freq, db_val in ear_values.items():
            if db_val is not None and db_val > 25:
                affected_freqs.append(freq)
        
        if not affected_freqs:
            return f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0.25rem 0 0 0; color: var(--text-color);">{main_status}</p>'

        low_tones, speech_tones, high_tones = [], [], []
        for f in affected_freqs:
            freq_val_str = re.sub(r'[^0-9]', '', f)
            if not freq_val_str: continue
            freq_val = int(freq_val_str)
            
            if 'k' in f.lower(): freq_val *= 1000

            if freq_val <= 500: low_tones.append(f)
            elif freq_val <= 2000: speech_tones.append(f)
            else: high_tones.append(f)

        html_output = f'<p style="font-size: 1.2rem; font-weight: bold; margin: 0; color: var(--text-color);">{main_status}</p>'
        details_parts = []
        if speech_tones: details_parts.append(f'เสียงพูด ({", ".join(speech_tones)})')
        if high_tones: details_parts.append(f'เสียงแหลม ({", ".join(high_tones)})')
        if low_tones: details_parts.append(f'เสียงทุ้ม ({", ".join(low_tones)})')

        if details_parts:
            details_str = ", ".join(details_parts)
            html_output += f'<p style="font-size: 0.8rem; margin: 0.25rem 0 0 0; color: var(--text-color);">กระทบความถี่: {details_str}</p>'

        return html_output.strip()

    results['averages']['right_500_2000'] = to_int(person_data.get('AVRต่ำ'))
    results['averages']['left_500_2000'] = to_int(person_data.get('AVLต่ำ'))
    results['averages']['right_3000_6000'] = to_int(person_data.get('AVRสูง'))
    results['averages']['left_3000_6000'] = to_int(person_data.get('AVLสูง'))
    
    severity_r = person_data.get('ระดับการได้ยินหูขวา', classify_hearing(results['averages']['right_500_2000']))
    severity_l = person_data.get('ระดับการได้ยินหูซ้าย', classify_hearing(results['averages']['left_500_2000']))
    summary_r_raw = person_data.get('ผลตรวจการได้ยินหูขวา', '')
    summary_l_raw = person_data.get('ผลตรวจการได้ยินหูซ้าย', '')

    right_ear_values = {freq: vals['right'] for freq, vals in results['raw_values'].items()}
    left_ear_values = {freq: vals['left'] for freq, vals in results['raw_values'].items()}

    results['summary']['right_raw'] = summary_r_raw
    results['summary']['left_raw'] = summary_l_raw
    results['summary']['overall'] = person_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    results['summary']['summary_html_right'] = format_hearing_summary_html(summary_r_raw or severity_r, severity_r, right_ear_values)
    results['summary']['summary_html_left'] = format_hearing_summary_html(summary_l_raw or severity_l, severity_l, left_ear_values)
    results['advice'] = person_data.get('คำแนะนำผลตรวจการได้ยิน', 'ไม่มีคำแนะนำเพิ่มเติม')

    if has_baseline_data:
        sts_freqs = ['2000 Hz', '3000 Hz', '4000 Hz']
        shifts_r, shifts_l = [], []
        for freq, values in results['raw_values'].items():
            base_vals = results['baseline_values'][freq]
            shift_r, shift_l = None, None
            if values['right'] is not None and base_vals['right'] is not None: shift_r = values['right'] - base_vals['right']
            if values['left'] is not None and base_vals['left'] is not None: shift_l = values['left'] - base_vals['left']
            results['shift_values'][freq] = {'right': shift_r, 'left': shift_l}
            if freq in sts_freqs:
                if shift_r is not None: shifts_r.append(shift_r)
                if shift_l is not None: shifts_l.append(shift_l)
        
        avg_shift_r = np.mean(shifts_r) if shifts_r else 0
        avg_shift_l = np.mean(shifts_l) if shifts_l else 0
        if avg_shift_r >= 10 or avg_shift_l >= 10: results['sts_detected'] = True
    
    other_keys = ['ผลการได้ยินเปรียบเทียบALLFq', 'ผลการได้ยินเปรียบเทียบAVRFqต่ำ', 'ผลการได้ยินเปรียบเทียบAVRFqสูง', 'ข้อมูลประกอบการตรวจสมรรถภาพการได้ยิน']
    for key in other_keys:
        val = person_data.get(key)
        if not is_empty(val): results['other_data'][key] = val

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
