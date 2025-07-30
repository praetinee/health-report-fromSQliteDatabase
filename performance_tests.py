import streamlit as st
import pandas as pd
from collections import OrderedDict
from datetime import datetime

def is_empty(val):
    """
    ตรวจสอบว่าค่าที่รับเข้ามาเป็นค่าว่างหรือไม่
    """
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def has_vision_data(person_data):
    """Check for any ACTUAL vision test data, ignoring summary/advice fields."""
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ',
        'ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล',
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)',
        'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)',
        'ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ',
        'ป.การจำแนกสี', 'ผ.การจำแนกสี',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน',
        'ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้',
        'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)',
        'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)',
        'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน',
        'ป.ลานสายตา', 'ผ.ลานสายตา',
        'ผ.สายตาเขซ่อนเร้น'
    ]
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

def render_vision_details_table(person_data):
    """
    Renders a clearer, single-column result table for the vision test with corrected logic.
    """
    vision_tests = [
        # Tests with a single column where the value determines the outcome
        {'display': '1. การมองด้วย 2 ตา (Binocular vision)', 'type': 'value', 'col': 'ป.การรวมภาพ', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '2. การมองภาพระยะไกลด้วยสองตา (Far vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะไกล', 'abnormal_col': 'ผ.ความชัดของภาพระยะไกล', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '3. การมองภาพระยะไกลด้วยตาขวา (Far vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '4. การมองภาพระยะไกลด้วยตาซ้าย (Far vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '5. การมองภาพ 3 มิติ (Stereo depth)', 'type': 'paired_value', 'normal_col': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'abnormal_col': 'ผ.การกะระยะและมองความชัดลึกของภาพ', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '6. การมองจำแนกสี (Color discrimination)', 'type': 'paired_value', 'normal_col': 'ป.การจำแนกสี', 'abnormal_col': 'ผ.การจำแนกสี', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '9. การมองภาพระยะใกล้ด้วยสองตา (Near vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะใกล้', 'abnormal_col': 'ผ.ความชัดของภาพระยะใกล้', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '10. การมองภาพระยะใกล้ด้วยตาขวา (Near vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '11. การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'normal_keywords': ['ชัดเจน', 'ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '13. ลานสายตา (Visual field)', 'type': 'value', 'col': 'ป.ลานสายตา', 'normal_keywords': ['ปกติ'], 'outcomes': ['ปกติ', 'ผิดปกติ']},
        
        # Phoria tests with complex relationship to 'ผ.สายตาเขซ่อนเร้น'
        {'display': '7. ความสมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'related_keyword': 'แนวตั้งระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '8. ความสมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'related_keyword': 'แนวนอนระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '12. ความสมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'related_keyword': 'แนวนอนระยะใกล้', 'outcomes': ['ปกติ', 'ผิดปกติ']}
    ]

    # Sort the list by display name to ensure order
    vision_tests.sort(key=lambda x: int(x['display'].split('.')[0]))

    html_parts = []
    html_parts.append('<table class="vision-table">')
    html_parts.append('<thead><tr><th>รายการตรวจ (Vision Test)</th><th class="result-cell">ผลการตรวจ</th></tr></thead>')
    html_parts.append('<tbody>')

    strabismus_val = str(person_data.get('ผ.สายตาเขซ่อนเร้น', '')).strip()

    for test in vision_tests:
        is_normal = False
        is_abnormal = False
        result_text = ""

        if test['type'] == 'value':
            result_value = str(person_data.get(test['col'], '')).strip()
            if not is_empty(result_value):
                result_text = result_value
                if any(keyword.lower() in result_value.lower() for keyword in test['normal_keywords']):
                    is_normal = True
                else:
                    is_abnormal = True 
        
        elif test['type'] == 'paired_value':
            normal_val = str(person_data.get(test['normal_col'], '')).strip()
            abnormal_val = str(person_data.get(test['abnormal_col'], '')).strip()
            if not is_empty(normal_val):
                is_normal = True
                result_text = normal_val
            elif not is_empty(abnormal_val):
                is_abnormal = True
                result_text = abnormal_val
        
        elif test['type'] == 'phoria':
            normal_val = str(person_data.get(test['normal_col'], '')).strip()
            if not is_empty(normal_val):
                is_normal = True
                result_text = normal_val
            elif not is_empty(strabismus_val) and test['related_keyword'] in strabismus_val:
                is_abnormal = True
                result_text = f"สายตาเขซ่อนเร้น ({test['related_keyword']})"

        status_text = ""
        status_class = ""

        if is_normal:
            status_text = test['outcomes'][0] 
            status_class = 'vision-normal'
        elif is_abnormal:
            status_text = test['outcomes'][1]
            status_class = 'vision-abnormal'
        else:
            status_text = "ไม่ได้ตรวจ"
            status_class = 'vision-not-tested'

        html_parts.append('<tr>')
        html_parts.append(f"<td>{test['display']}</td>")
        html_parts.append(f'<td class="result-cell"><span class="vision-result {status_class}">{status_text}</span></td>')
        html_parts.append('</tr>')

    html_parts.append("</tbody></table>")
    return "".join(html_parts)

def interpret_lung_capacity(person_data):
    """
    แปลผลตรวจสมรรถภาพความจุปอดตามตรรกะมาตรฐานที่กำหนด
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

def display_performance_report_lung(person_data):
    """
    แสดงผลรายงานสมรรถภาพปอดในรูปแบบที่ปรับปรุงใหม่
    """
    st.markdown("<h2 style='text-align: center;'>รายงานผลการตรวจสมรรถภาพปอด (Spirometry Report)</h2>", unsafe_allow_html=True)
    lung_summary, lung_advice, lung_raw_values = interpret_lung_capacity(person_data)

    if lung_summary == "ไม่ได้เข้ารับการตรวจ":
        st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพปอดในปีนี้")
        return

    st.markdown("<h5><b>สรุปผลการตรวจที่สำคัญ</b></h5>", unsafe_allow_html=True)
    def format_val(key):
        val = lung_raw_values.get(key)
        return f"{val:.1f}" if val is not None else "-"
    col1, col2, col3 = st.columns(3)
    col1.metric(label="FVC (% เทียบค่ามาตรฐาน)", value=format_val('FVC %'), help="ความจุของปอดเมื่อหายใจออกเต็มที่ (ควร > 80%)")
    col2.metric(label="FEV1 (% เทียบค่ามาตรฐาน)", value=format_val('FEV1 %'), help="ปริมาตรอากาศที่หายใจออกในวินาทีแรก (ควร > 80%)")
    col3.metric(label="FEV1/FVC Ratio (%)", value=format_val('FEV1/FVC %'), help="สัดส่วนของ FEV1 ต่อ FVC (ควร > 70%)")
    st.markdown("<hr>", unsafe_allow_html=True)

    res_col1, res_col2 = st.columns([2, 3])
    with res_col1:
        st.markdown("<h5><b>ผลการแปลความหมาย</b></h5>", unsafe_allow_html=True)
        if "ปกติ" in lung_summary: bg_color = "background-color: #2e7d32; color: white;"
        elif "ไม่ได้" in lung_summary or "คลาดเคลื่อน" in lung_summary: bg_color = "background-color: #616161; color: white;"
        else: bg_color = "background-color: #c62828; color: white;"
        st.markdown(f'<div style="padding: 1rem; border-radius: 8px; {bg_color} text-align: center;"><h4 style="color: white; margin: 0; font-weight: bold;">{lung_summary}</h4></div>', unsafe_allow_html=True)
        st.markdown("<br><h5><b>คำแนะนำ</b></h5>", unsafe_allow_html=True)
        st.info(lung_advice or "ไม่มีคำแนะนำเพิ่มเติม")
        st.markdown("<h5><b>ผลเอกซเรย์ทรวงอก</b></h5>", unsafe_allow_html=True)
        selected_year = person_data.get("Year")
        cxr_result_interpreted = "ไม่มีข้อมูล"
        if selected_year:
            cxr_col_name = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            cxr_result_interpreted = interpret_cxr(person_data.get(cxr_col_name, ''))
        st.markdown(f'<div style="font-size: 14px; padding: 0.5rem; background-color: rgba(255,255,255,0.05); border-radius: 4px;">{cxr_result_interpreted}</div>', unsafe_allow_html=True)
    with res_col2:
        st.markdown("<h5><b>ตารางแสดงผลโดยละเอียด</b></h5>", unsafe_allow_html=True)
        def format_detail_val(key, format_spec, unit=""):
            val = lung_raw_values.get(key)
            if val is not None and isinstance(val, (int, float)): return f"{val:{format_spec}}{unit}"
            return "-"
        detail_data = {"การทดสอบ (Test)": ["FVC", "FEV1", "FEV1/FVC"],"ค่าที่วัดได้ (Actual)": [format_detail_val('FVC', '.2f', ' L'), format_detail_val('FEV1', '.2f', ' L'), format_detail_val('FEV1/FVC %', '.1f', ' %')],"ค่ามาตรฐาน (Predicted)": [format_detail_val('FVC predic', '.2f', ' L'), format_detail_val('FEV1 predic', '.2f', ' L'), format_detail_val('FEV1/FVC % pre', '.1f', ' %')],"% เทียบค่ามาตรฐาน (% Pred)": [format_detail_val('FVC %', '.1f', ' %'), format_detail_val('FEV1 %', '.1f', ' %'), "-"]}
        df_details = pd.DataFrame(detail_data)
        st.dataframe(df_details, use_container_width=True, hide_index=True)

def display_performance_report(person_data, report_type):
    """Displays various performance test reports (lung, vision, hearing)."""
    # Use columns to constrain the width of the report sections
    left_spacer, main_col, right_spacer = st.columns([0.5, 6, 0.5])
    
    with main_col:
        if report_type == 'lung':
            display_performance_report_lung(person_data)
            
        elif report_type == 'vision':
            st.markdown("<h2 style='text-align: center;'>รายงานผลการตรวจสมรรถภาพการมองเห็น (Vision Test Report)</h2>", unsafe_allow_html=True)
            
            # Check for detailed results first
            if not has_vision_data(person_data):
                st.warning("ไม่พบข้อมูลผลการตรวจสมรรถภาพการมองเห็นโดยละเอียดในปีนี้")
                # Also check if there are summary fields, and if so, inform the user they might be from another year.
                vision_advice_summary = person_data.get('สรุปเหมาะสมกับงาน')
                doctor_advice = person_data.get('แนะนำABN EYE')
                if not is_empty(vision_advice_summary) or not is_empty(doctor_advice):
                    st.info("หมายเหตุ: ข้อมูลสรุปที่แสดงอาจมาจากผลการตรวจในปีอื่น")
                    if not is_empty(vision_advice_summary):
                         st.markdown(f"""
                         <div style='background-color: rgba(64, 128, 255, 0.1); border: 1px solid rgba(64, 128, 255, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                            <div style='flex-shrink: 0;'>
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4080FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            </div>
                            <div>
                                <h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #A6C8FF;'>สรุปความเหมาะสมกับงาน</h5>
                                <p style='margin:0; color: var(--text-color);'>{vision_advice_summary}</p>
                            </div>
                         </div>
                         """, unsafe_allow_html=True)
                    if not is_empty(doctor_advice):
                         st.markdown(f"""
                         <div style='background-color: rgba(255, 229, 100, 0.1); border: 1px solid rgba(255, 229, 100, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                            <div style='flex-shrink: 0;'>
                               <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFE564" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg>
                            </div>
                            <div>
                                <h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #FFE564;'>คำแนะนำเพิ่มเติมจากแพทย์</h5>
                                <p style='margin:0; color: var(--text-color);'>{doctor_advice}</p>
                            </div>
                         </div>
                         """, unsafe_allow_html=True)
                return

            # If we have detailed data, proceed to show the full report
            vision_advice_summary = person_data.get('สรุปเหมาะสมกับงาน')
            if not is_empty(vision_advice_summary):
                st.markdown(f"""
                 <div style='background-color: rgba(64, 128, 255, 0.1); border: 1px solid rgba(64, 128, 255, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                    <div style='flex-shrink: 0;'>
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4080FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <div>
                        <h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #A6C8FF;'>สรุปความเหมาะสมกับงาน</h5>
                        <p style='margin:0; color: var(--text-color);'>{vision_advice_summary}</p>
                    </div>
                 </div>
                 """, unsafe_allow_html=True)

            # --- SIMPLIFIED ABNORMALITY SUMMARY ---
            abnormality_fields = OrderedDict([
                ('ผ.สายตาเขซ่อนเร้น', 'สายตาเขซ่อนเร้น'),
                ('ผ.การรวมภาพ', 'การรวมภาพ'),
                ('ผ.ความชัดของภาพระยะไกล', 'ความชัดของภาพระยะไกล'),
                ('ผ.การกะระยะและมองความชัดลึกของภาพ', 'การกะระยะ/ความชัดลึก'),
                ('ผ.การจำแนกสี', 'การจำแนกสี'),
                ('ผ.ความชัดของภาพระยะใกล้', 'ความชัดของภาพระยะใกล้'),
                ('ผ.ลานสายตา', 'ลานสายตา')
            ])

            abnormal_topics = []
            for col, name in abnormality_fields.items():
                if not is_empty(person_data.get(col)):
                    abnormal_topics.append(name)

            doctor_advice = person_data.get('แนะนำABN EYE')

            if abnormal_topics or not is_empty(doctor_advice):
                summary_parts = []
                if abnormal_topics:
                    summary_parts.append(f"<b>พบความผิดปกติเกี่ยวกับ:</b> {', '.join(abnormal_topics)}")
                
                if not is_empty(doctor_advice):
                    summary_parts.append(f"<b>คำแนะนำเพิ่มเติมจากแพทย์:</b> {doctor_advice}")

                summary_html = "<br>".join(summary_parts)
                st.markdown(f"""
                <div style='background-color: rgba(255, 229, 100, 0.1); border: 1px solid rgba(255, 229, 100, 0.3); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                    <div style='flex-shrink: 0;'>
                       <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFE564" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg>
                    </div>
                    <div>
                        <h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #FFE564;'>สรุปความผิดปกติของสายตา</h5>
                        <p style='margin:0; color: var(--text-color);'>{summary_html}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            # --- END OF SIMPLIFIED SUMMARY ---

            st.markdown("<hr>", unsafe_allow_html=True)
            
            st.markdown("<h5><b>ผลการตรวจโดยละเอียด</b></h5>", unsafe_allow_html=True)
            detailed_table_html = render_vision_details_table(person_data)
            st.markdown(detailed_table_html, unsafe_allow_html=True)
            
        elif report_type == 'hearing':
            st.header("รายงานผลการตรวจสมรรถภาพการได้ยิน (Hearing)")
            hearing_summary, hearing_advice = interpret_hearing(person_data.get('การได้ยิน'))
            if hearing_summary == "ไม่ได้เข้ารับการตรวจ":
                st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพการได้ยินในปีนี้")
                return
            h_col1, h_col2 = st.columns(2)
            h_col1.metric("สรุปผล", hearing_summary)
            if hearing_advice: h_col2.info(f"**คำแนะนำ:** {hearing_advice}")
