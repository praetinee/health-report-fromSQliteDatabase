import pandas as pd
import html
from collections import OrderedDict
from datetime import datetime

# แก้ไข: ตัด interpret_cxr ออกจาก import เพราะเราจะสร้างฟังก์ชันนี้ในไฟล์นี้เองเพื่อป้องกัน Error
from performance_tests import interpret_audiogram, interpret_lung_capacity

# ==============================================================================
# Module: print_performance_report.py
# Purpose: Contains functions to generate HTML for performance test reports
# (Vision, Hearing, Lung) for the standalone printable version.
# Refactored for Batch Printing capability.
# ==============================================================================


# --- Helper & Data Availability Functions ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# เพิ่มฟังก์ชันนี้เข้ามาใหม่เพื่อแก้ปัญหา Import Error
def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้ตรวจ", False
    is_abn = False
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        val = f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
        is_abn = True
    return val, is_abn

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

def has_hearing_data(person_data):
    """Check for detailed hearing (audiogram) data."""
    hearing_keys = ['R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k']
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
    """Check for lung capacity test data."""
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

# --- HTML Rendering Functions for Standalone Report ---

def render_section_header(title, subtitle=None):
    """Renders a styled section header for the print report."""
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div class='section-header'>
        {full_title}
    </div>
    """

def render_html_header_and_personal_info(person):
    """Renders the main header and personal info table for the print report."""
    check_date = person.get("วันที่ตรวจ", "-")
    name = person.get('ชื่อ-สกุล', '-')
    age = str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')
    sex = person.get('เพศ', '-')
    hn = str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')
    department = person.get('หน่วยงาน', '-')
    
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    try:
        sbp_int, dbp_int = int(float(sbp)), int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int}"
    except: bp_val = "-"
    
    pulse_raw = person.get("pulse", "-")
    pulse_val = str(int(float(pulse_raw))) if not is_empty(pulse_raw) and str(pulse_raw).replace('.', '', 1).isdigit() else "-"

    waist_val = person.get("รอบเอว", "-")
    waist_display = f"{waist_val}" if not is_empty(waist_val) else "-"
    
    weight = person.get("น้ำหนัก", "-")
    height = person.get("ส่วนสูง", "-")

    return f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #00796B; padding-bottom: 10px; margin-bottom: 15px; font-family: 'Sarabun', sans-serif;">
        <div style="width: 40%;">
            <h3 style="margin: 0; color: #00796B; font-size: 18px; line-height: 1.2;">รายงานผลการตรวจสมรรถภาพ</h3>
            <p style="margin: 4px 0 0 0; font-size: 16px; font-weight: 600;">คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม</p>
            <p style="margin: 0; font-size: 16px;">โรงพยาบาลสันทราย</p>
            <p style="margin-top: 8px; font-size: 16px;"><b>วันที่ตรวจ:</b> {check_date}</p>
        </div>
        <div style="width: 60%; text-align: right;">
            <h3 style="margin: 0; font-size: 18px; line-height: 1.2;">{name}</h3>
            <p style="margin: 4px 0 0 0; font-size: 16px;">
                <b>HN:</b> {hn}
                <span style="color: #ddd; margin: 0 8px;">|</span>
                <b>เพศ:</b> {sex}
                <span style="color: #ddd; margin: 0 8px;">|</span>
                <b>อายุ:</b> {age} ปี
            </p>
            <p style="margin: 2px 0 0 0; font-size: 16px;"><b>หน่วยงาน:</b> {department}</p>
            
            <div style="margin-top: 8px; font-size: 16px; background-color: #f8f9fa; display: inline-block; padding: 4px 10px; border-radius: 4px; border: 1px solid #e0e0e0;">
                <span style="white-space: nowrap;"><b>นน.</b> {weight}</span> <span style="color: #ccc; margin: 0 4px;">|</span>
                <span style="white-space: nowrap;"><b>ส่วนสูง</b> {height}</span> <span style="color: #ccc; margin: 0 4px;">|</span>
                <span style="white-space: nowrap;"><b>รอบเอว</b> {waist_display}</span> <span style="color: #ccc; margin: 0 8px; font-weight: 300;">/</span>
                <span style="white-space: nowrap;"><b>BP:</b> {bp_val}</span> <span style="color: #ccc; margin: 0 4px;">|</span>
                <span style="white-space: nowrap;"><b>PR:</b> {pulse_val}</span>
            </div>
        </div>
    </div>
    """


def render_print_vision(person_data):
    """Renders the Vision Test section for the print report with complete logic."""
    if not has_vision_data(person_data):
        return ""

    vision_tests = [
        {'display': '1. การมองด้วย 2 ตา (Binocular vision)', 'type': 'paired_value', 'normal_col': 'ป.การรวมภาพ', 'abnormal_col': 'ผ.การรวมภาพ'},
        {'display': '2. การมองภาพระยะไกลด้วยสองตา (Far vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะไกล', 'abnormal_col': 'ผ.ความชัดของภาพระยะไกล'},
        {'display': '3. การมองภาพระยะไกลด้วยตาขวา (Far vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)'},
        {'display': '4. การมองภาพระยะไกลด้วยตาซ้าย (Far vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)'},
        {'display': '5. การมองภาพ 3 มิติ (Stereo depth)', 'type': 'paired_value', 'normal_col': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'abnormal_col': 'ผ.การกะระยะและมองความชัดลึกของภาพ'},
        {'display': '6. การมองจำแนกสี (Color discrimination)', 'type': 'paired_value', 'normal_col': 'ป.การจำแนกสี', 'abnormal_col': 'ผ.การจำแนกสี'},
        {'display': '7. ความสมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'related_keyword': 'แนวตั้งระยะไกล'},
        {'display': '8. ความสมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'related_keyword': 'แนวนอนระยะไกล'},
        {'display': '9. การมองภาพระยะใกล้ด้วยสองตา (Near vision - Both)', 'type': 'paired_value', 'normal_col': 'ป.ความชัดของภาพระยะใกล้', 'abnormal_col': 'ผ.ความชัดของภาพระยะใกล้'},
        {'display': '10. การมองภาพระยะใกล้ด้วยตาขวา (Near vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision - Right)'},
        {'display': '11. การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision - Left)'},
        {'display': '12. ความสมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'related_keyword': 'แนวนอนระยะใกล้'},
        {'display': '13. ลานสายตา (Visual field)', 'type': 'paired_value', 'normal_col': 'ป.ลานสายตา', 'abnormal_col': 'ผ.ลานสายตา'}
    ]

    rows_html = ""
    abnormal_details = []
    strabismus_val = str(person_data.get('ผ.สายตาเขซ่อนเร้น', '')).strip()

    for test in vision_tests:
        is_normal, is_abnormal = False, False
        result_text = ""
        status_text = "ไม่ได้ตรวจ"

        if test['type'] == 'value':
            val = str(person_data.get(test['col'], '')).strip()
            if not is_empty(val):
                is_abnormal = True 
                if any(k in val.lower() for k in ['ปกติ', 'ชัดเจน']):
                    is_abnormal = False
                result_text = val
        
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

        if is_normal or (result_text and not is_abnormal):
            status_text = "ปกติ"
        elif is_abnormal:
            status_text = "ผิดปกติ"
            abnormal_details.append(test['display'].split('(')[0].strip())
        
        rows_html += f"<tr><td>{test['display']}</td><td>{status_text}</td></tr>"

    doctor_advice = person_data.get('แนะนำABN EYE', '')
    summary_advice = person_data.get('สรุปเหมาะสมกับงาน', '')
    
    summary_section_html = ""
    advice_parts = []
    if not is_empty(summary_advice):
        advice_parts.append(f"<div class='advice-box'><b>สรุปความเหมาะสมกับงาน:</b> {html.escape(summary_advice)}</div>")

    if abnormal_details or not is_empty(doctor_advice):
        abnormal_summary_parts = []
        if abnormal_details:
            abnormal_summary_parts.append(f"<b>พบความผิดปกติ:</b> {', '.join(sorted(list(set(abnormal_details))))}")
        if not is_empty(doctor_advice):
            abnormal_summary_parts.append(f"<b>คำแนะนำแพทย์:</b> {html.escape(doctor_advice)}")
        advice_parts.append("<div class='advice-box'>" + "<br>".join(abnormal_summary_parts) + "</div>")
    
    if not advice_parts:
        advice_parts.append("<div class='advice-box'>ผลการตรวจโดยรวมปกติ ไม่มีคำแนะนำเพิ่มเติม</div>")

    summary_section_html = "<div class='summary-container'>" + "".join(advice_parts) + "</div>"

    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพการมองเห็น (Vision Test)")}
        <div class="content-columns">
            <div class="main-content">
                <table class="data-table">
                    <thead><tr><th>รายการตรวจ</th><th>ผลการตรวจ</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            <div class="side-content">
                {summary_section_html}
            </div>
        </div>
    </div>
    """

def render_print_hearing(person_data, all_person_history_df):
    """Renders the Hearing Test (Audiometry) section for the print report."""
    if not has_hearing_data(person_data):
        return ""
        
    results = interpret_audiogram(person_data, all_person_history_df)
    
    summary_r_raw = person_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    summary_l_raw = person_data.get('ผลตรวจการได้ยินหูซ้าย', 'N/A')
    
    def get_summary_class(summary_text):
        if "ปกติ" in summary_text: return "status-ok-text"
        if "N/A" in summary_text or "ไม่ได้" in summary_text: return "status-nt-text"
        return "status-abn-text"

    summary_cards_html = f"""
    <div class="summary-single-line-box">
        <span class="{get_summary_class(summary_r_raw)}">
            <b>หูขวา:</b> {html.escape(summary_r_raw)}
        </span>
        <span class="{get_summary_class(summary_l_raw)}">
            <b>หูซ้าย:</b> {html.escape(summary_l_raw)}
        </span>
    </div>
    """
    
    advice = results.get('advice', '') or 'ไม่มีคำแนะนำเพิ่มเติม'
    advice_box_html = f"<div class='advice-box'><b>คำแนะนำ:</b> {html.escape(advice)}</div>"
    if results.get('sts_detected'):
        advice_box_html = f"<div class='advice-box'><b>⚠️ พบการเปลี่ยนแปลงระดับการได้ยินอย่างมีนัยสำคัญ (STS)</b><br>{html.escape(advice)}</div>"

    rows_html = ""
    has_baseline = results.get('baseline_source') != 'none'
    baseline_year = results.get('baseline_year')
    freq_order = ['500 Hz', '1000 Hz', '2000 Hz', '3000 Hz', '4000 Hz', '6000 Hz', '8000 Hz']
    
    for freq in freq_order:
        current_vals = results.get('raw_values', {}).get(freq, {})
        r_val = current_vals.get('right', '-')
        l_val = current_vals.get('left', '-')
        
        shift_r_text = "-"
        shift_l_text = "-"
        if has_baseline:
            shift_vals = results.get('shift_values', {}).get(freq, {})
            shift_r = shift_vals.get('right')
            shift_l = shift_vals.get('left')
            shift_r_text = f"+{shift_r}" if shift_r is not None and shift_r > 0 else (str(shift_r) if shift_r is not None else "-")
            shift_l_text = f"+{shift_l}" if shift_l is not None and shift_l > 0 else (str(shift_l) if shift_l is not None else "-")

        rows_html += f"""
        <tr>
            <td>{freq}</td>
            <td>{r_val}</td>
            <td>{l_val}</td>
            <td>{shift_r_text}</td>
            <td>{shift_l_text}</td>
        </tr>
        """

    baseline_header_line1 = "การเปลี่ยนแปลงเทียบกับ Baseline"
    baseline_header_line2 = f"(พ.ศ. {baseline_year})" if has_baseline else "(ไม่มี Baseline)"
    baseline_header_html = f"{baseline_header_line1}<br>{baseline_header_line2}"

    table_header_html = f"""
    <thead>
        <tr>
            <th rowspan="2" style="vertical-align: middle;">ความถี่ (Hz)</th>
            <th colspan="2">ผลการตรวจปัจจุบัน (dB)</th>
            <th colspan="2" style="vertical-align: middle;">{baseline_header_html}</th>
        </tr>
        <tr>
            <th>หูขวา</th>
            <th>หูซ้าย</th>
            <th>Shift ขวา</th>
            <th>Shift ซ้าย</th>
        </tr>
    </thead>
    """
    
    data_table_html = f"""
    <table class="data-table hearing-table">
        <colgroup>
            <col style="width: 20%;">
            <col style="width: 20%;">
            <col style="width: 20%;">
            <col style="width: 20%;">
            <col style="width: 20%;">
        </colgroup>
        {table_header_html}
        <tbody>{rows_html}</tbody>
    </table>
    """
    
    averages = results.get('averages', {})
    avg_r_speech = averages.get('right_500_2000')
    avg_l_speech = averages.get('left_500_2000')
    avg_r_high = averages.get('right_3000_6000')
    avg_l_high = averages.get('left_3000_6000')
    averages_html = f"""
    <div class="advice-box">
        <b>ค่าเฉลี่ยการได้ยิน (dB)</b>
        <ul style="margin: 5px 0 0 0; padding-left: 20px; list-style-type: square;">
            <li>ความถี่เสียงพูด (500-2k Hz): ขวา={avg_r_speech if avg_r_speech is not None else 'N/A'}, ซ้าย={avg_l_speech if avg_l_speech is not None else 'N/A'}</li>
            <li>ความถี่สูง (3k-6k Hz): ขวา={avg_r_high if avg_r_high is not None else 'N/A'}, ซ้าย={avg_l_high if avg_l_high is not None else 'N/A'}</li>
        </ul>
    </div>
    """
    
    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพการได้ยิน (Audiometry)")}
        
        <div class="content-columns">
            <div class="main-content">
                {data_table_html}
            </div>
            <div class="side-content">
                {summary_cards_html} 
                {averages_html}
                {advice_box_html}
            </div>
        </div>
    </div>
    """

def render_print_lung(person_data):
    """Renders the Lung Capacity (Spirometry) section for the print report."""
    if not has_lung_data(person_data):
        return ""
        
    summary, advice, raw = interpret_lung_capacity(person_data)

    def format_val(key, spec='.1f'):
        val = raw.get(key)
        return f"{val:{spec}}" if val is not None else "-"

    def get_status_class(val, low_threshold):
        if val is None: return "" 
        return "status-ok-text" if val >= low_threshold else "status-abn-text"
    
    summary_class = "status-ok-text" if "ปกติ" in summary else "status-abn-text"
    if "ไม่ได้" in summary or "คลาดเคลื่อน" in summary:
        summary_class = ""

    summary_title_html = f"""
    <div class="summary-title-lung {summary_class}">
        {html.escape(summary)}
    </div>
    """
    
    advice_box_html = f"<div class='advice-box'><b>คำแนะนำ:</b> {html.escape(advice)}</div>"
    
    year = person_data.get("Year")
    cxr_result_text = "ไม่มีข้อมูล"
    if year:
        cxr_col = f"CXR{str(year)[-2:]}" if year != (datetime.now().year + 543) else "CXR"
        cxr_result, cxr_status = interpret_cxr(person_data.get(cxr_col, ''))
        cxr_result_text = cxr_result
    cxr_html = f"""
    <div class="advice-box" style="margin-bottom: 5px;">
        <b>ผลเอกซเรย์ทรวงอก (CXR):</b><br>{html.escape(cxr_result_text)}
    </div>
    """
    
    data_table_html = f"""
    <table class="data-table">
        <thead>
            <tr><th>การทดสอบ</th><th>ค่าที่วัดได้ (Actual)</th><th>ค่ามาตรฐาน (Pred)</th><th>% เทียบค่ามาตรฐาน (%Pred)</th></tr>
        </thead>
        <tbody>
            <tr><td>FVC (L)</td><td>{format_val('FVC', '.2f')}</td><td>{format_val('FVC predic', '.2f')}</td><td class='{get_status_class(raw.get("FVC %"), 80)}'>{format_val('FVC %')} %</td></tr>
            <tr><td>FEV1 (L)</td><td>{format_val('FEV1', '.2f')}</td><td>{format_val('FEV1 predic', '.2f')}</td><td class='{get_status_class(raw.get("FEV1 %"), 80)}'>{format_val('FEV1 %')} %</td></tr>
            <tr><td>FEV1/FVC (%)</td><td class='{get_status_class(raw.get("FEV1/FVC %"), 70)}'>{format_val('FEV1/FVC %')} %</td><td>{format_val('FEV1/FVC % pre')} %</td><td>-</td></tr>
        </tbody>
    </table>
    """

    side_content_html = f"""
    {cxr_html}
    {advice_box_html}
    """

    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพปอด (Spirometry)")}
        {summary_title_html}
        <div class="content-columns">
            <div class="main-content">
                {data_table_html}
            </div>
            <div class="side-content">
                {side_content_html}
            </div>
        </div>
    </div>
    """

# --- NEW FUNCTIONS FOR REFACTORING ---

def get_performance_report_css():
    """Returns the CSS string for the performance report."""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        body {
            font-family: 'Sarabun', sans-serif !important;
            font-size: 16px; 
            margin: 0.5cm 0.7cm; 
            color: #333;
            background-color: #fff;
        }
        hr { border: 0; border-top: 1px solid #e0e0e0; margin: 0.5rem 0; }
        .info-table { width: 100%; font-size: 16px; text-align: left; border-collapse: collapse; }
        .info-table td { padding: 1px 5px; font-size: 16px; }
        
        .header-grid { display: flex; align-items: flex-end; justify-content: space-between; }
        .header-left { text-align: left; }
        .header-right { text-align: right; }

        .report-section { margin-bottom: 0.5rem; page-break-inside: avoid; } 
        
        .section-header {
            background-color: #00796B; 
            color: white; text-align: center;
            padding: 0.4rem; font-weight: bold; border-radius: 8px;
            margin-bottom: 0.7rem;
            font-size: 16px;
            font-family: 'Sarabun', sans-serif;
        }

        .content-columns { display: flex; gap: 15px; align-items: flex-start; }
        .main-content { flex: 2; min-width: 0; }
        .side-content { flex: 1; min-width: 0; }
        .main-content-full { width: 100%; }

        .data-table { width: 100%; font-size: 16px; border-collapse: collapse; }
        .data-table.hearing-table { table-layout: fixed; }
        .data-table th, .data-table td {
            border: 1px solid #e0e0e0; padding: 4px; text-align: center;
            vertical-align: middle;
            font-size: 16px;
        }
        .data-table th { background-color: #f5f5f5; font-weight: bold; }
        .data-table td:first-child { text-align: left; }

        .summary-single-line-box {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            padding: 8px;
            border: 1px solid #e0e0e0;
            background-color: #f9f9f9;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            font-size: 16px;
            font-weight: bold;
            page-break-inside: avoid; 
        }
        
        .summary-single-line-box span {
            text-align: left;
        }

        .summary-container { margin-top: 0; }
        .summary-container-lung { margin-top: 10px; }
        .summary-title-lung {
            text-align: center;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 8px;
            line-height: 1.2;
        }
        .advice-box {
            border-radius: 6px; padding: 8px 12px; font-size: 16px;
            line-height: 1.5; border: 1px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 5px; 
            height: 100%;
            box-sizing: border-box;
            background-color: #fff8e1; 
            border-color: #ffecb3;
        }
        .summary-container .advice-box:last-child {
            margin-bottom: 0;
        }
        
        .status-ok-text { color: #1b5e20; }
        .status-abn-text { color: #b71c1c; }
        .status-nt-text { color: #555; }
        
        .signature-section {
            margin-top: 2rem;
            text-align: right;
            padding-right: 1rem;
            page-break-inside: avoid;
            font-family: 'Sarabun', sans-serif;
        }
        .signature-line {
            display: inline-block;
            text-align: center;
            width: 280px;
        }
        .signature-line .line {
            border-bottom: 1px dotted #333;
            margin-bottom: 0.4rem;
            width: 100%;
        }
        .signature-line .name, .signature-line .title, .signature-line .license {
            white-space: nowrap;
            font-size: 16px;
        }

        @media print {
            body { -webkit-print-color-adjust: exact; margin: 0; }
        }
    </style>
    """

def render_performance_report_body(person_data, all_person_history_df):
    """Generates the HTML body content for the performance report."""
    header_html = render_html_header_and_personal_info(person_data)
    vision_html = render_print_vision(person_data)
    hearing_html = render_print_hearing(person_data, all_person_history_df)
    lung_html = render_print_lung(person_data)
    
    signature_html = """
    <div class="signature-section">
        <div class="signature-line">
            <div class="line"></div>
            <div class="name">นายแพทย์นพรัตน์ รัชฎาพร</div>
            <div class="title">แพทย์อาชีวเวชศาสตร์</div>
            <div class="license">ว.26674</div>
        </div>
    </div>
    """
    
    return f"""
    <div class="report-container">
        {header_html}
        {vision_html}
        {hearing_html}
        {lung_html}
        {signature_html}
    </div>
    """

def generate_performance_report_html(person_data, all_person_history_df):
    """
    Checks for available performance tests and generates the combined HTML for the standalone performance report.
    """
    css_html = get_performance_report_css()
    body_html = render_performance_report_body(person_data, all_person_history_df)
    
    # เพิ่ม window.print() เพื่อให้หน้าต่างพิมพ์เด้งขึ้นมาอัตโนมัติเมื่อโหลดหน้าเสร็จ
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสมรรถภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        {css_html}
    </head>
    <body onload="window.print()">
        {body_html}
    </body>
    </html>
    """
    return final_html

def generate_performance_report_html_for_main_report(person_data, all_person_history_df):
    """
    Generates a compact version of performance reports to be embedded
    into the main health report.
    """
    parts = []
    
    if has_vision_data(person_data):
        vision_advice = person_data.get('สรุปเหมาะสมกับงาน', 'ไม่มีข้อมูลสรุป')
        parts.append(f"""
        <div class="perf-section">
            <b>การมองเห็น:</b> <span class="summary-box">{html.escape(vision_advice)}</span>
        </div>
        """)

    if has_hearing_data(person_data):
        results = interpret_audiogram(person_data, all_person_history_df)
        summary = results['summary'].get('overall', 'N/A')
        advice = results.get('advice', 'ไม่มีคำแนะนำ')
        parts.append(f"""
        <div class="perf-section">
            <b>การได้ยิน:</b> <span class="summary-box">สรุป: {html.escape(summary)} | คำแนะนำ: {html.escape(advice)}</span>
        </div>
        """)

    if has_lung_data(person_data):
        summary, advice, _ = interpret_lung_capacity(person_data)
        parts.append(f"""
        <div class="perf-section">
            <b>สมรรถภาพปอด:</b> <span class="summary-box">สรุป: {html.escape(summary)} | คำแนะนำ: {html.escape(advice)}</span>
        </div>
        """)

    if not parts:
        return ""

    return render_section_header("ผลการตรวจสมรรถภาพพิเศษ (Performance Tests)") + "".join(parts)
