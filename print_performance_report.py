import pandas as pd
import html
from collections import OrderedDict
from datetime import datetime

# แก้ไข: import ฟังก์ชัน interpret_audiogram, interpret_lung_capacity, และ interpret_cxr
from performance_tests import interpret_audiogram, interpret_lung_capacity, interpret_cxr

# ==============================================================================
# Module: print_performance_report.py
# Purpose: Contains functions to generate HTML for performance test reports
# (Vision, Hearing, Lung) for the standalone printable version.
#
# NOTE: This file has been completely redesigned for a more modern,
# informative, and doctor-friendly printable layout.
# ==============================================================================


# --- Helper & Data Availability Functions ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
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
    
    # Vital Signs Formatting
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    try:
        sbp_int, dbp_int = int(float(sbp)), int(float(dbp))
        bp_val = f"{sbp_int}/{dbp_int} ม.ม.ปรอท"
    except: bp_val = "-"
    
    pulse_raw = person.get("pulse", "-")
    pulse_val = str(int(float(pulse_raw))) if not is_empty(pulse_raw) and str(pulse_raw).replace('.', '', 1).isdigit() else "-"

    header = f"""
    <div class="report-header-container">
        <h1 style="font-size: 1.5rem; margin:0;">รายงานผลการตรวจสมรรถภาพ</h1>
        <p style="font-size: 0.8rem; margin:0;">คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
        <p style="font-size: 0.8rem; margin:0;"><b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>
    """
    
    personal_info = f"""
    <div class="personal-info-container">
        <hr>
        <table class="info-table">
            <tr>
                <td><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</td>
                <td><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')} ปี</td>
                <td><b>เพศ:</b> {person.get('เพศ', '-')}</td>
                <td><b>HN:</b> {str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')}</td>
            </tr>
            <tr>
                <td><b>หน่วยงาน:</b> {person.get('หน่วยงาน', '-')}</td>
                <td><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</td>
                <td><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</td>
                <td><b>ความดัน:</b> {bp_val}</td>
            </tr>
        </table>
        <hr>
    </div>
    """
    return header + personal_info


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
        {'display': '10. การมองภาพระยะใกล้ด้วยตาขวา (Near vision - Right)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)'},
        {'display': '11. การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision - Left)', 'type': 'value', 'col': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)'},
        {'display': '12. ความสมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'related_keyword': 'แนวนอนระยะใกล้'},
        {'display': '13. ลานสายตา (Visual field)', 'type': 'paired_value', 'normal_col': 'ป.ลานสายตา', 'abnormal_col': 'ผ.ลานสายตา'}
    ]

    rows_html = ""
    abnormal_details = []
    strabismus_val = str(person_data.get('ผ.สายตาเขซ่อนเร้น', '')).strip()

    for test in vision_tests:
        is_normal, is_abnormal = False, False
        result_text = ""
        status_text, status_class = "ไม่ได้ตรวจ", "status-nt"

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
            status_class = 'status-ok'
        elif is_abnormal:
            status_text = f"ผิดปกติ ({html.escape(result_text)})"
            status_class = 'status-abn'
            abnormal_details.append(test['display'].split('(')[0].strip())
        
        rows_html += f"<tr><td>{test['display']}</td><td class='{status_class}'>{status_text}</td></tr>"

    doctor_advice = person_data.get('แนะนำABN EYE', '')
    summary_advice = person_data.get('สรุปเหมาะสมกับงาน', '')
    
    # แก้ไข: จัดการส่วนสรุปและคำแนะนำใหม่
    summary_section_html = ""
    advice_parts = []
    if not is_empty(summary_advice):
        advice_parts.append(f"<div class='advice-box info-box'><b>สรุปความเหมาะสมกับงาน:</b> {html.escape(summary_advice)}</div>")

    if abnormal_details or not is_empty(doctor_advice):
        abnormal_summary_parts = []
        if abnormal_details:
            abnormal_summary_parts.append(f"<b>พบความผิดปกติ:</b> {', '.join(sorted(list(set(abnormal_details))))}")
        if not is_empty(doctor_advice):
            abnormal_summary_parts.append(f"<b>คำแนะนำแพทย์:</b> {html.escape(doctor_advice)}")
        advice_parts.append("<div class='advice-box warning-box'>" + "<br>".join(abnormal_summary_parts) + "</div>")
    
    # ถ้าไม่มีคำแนะนำใดๆ เลย ให้แสดงว่าปกติ
    if not advice_parts:
        advice_parts.append("<div class='advice-box info-box'>ผลการตรวจโดยรวมปกติ ไม่มีคำแนะนำเพิ่มเติม</div>")

    summary_section_html = "<div class='summary-container'>" + "".join(advice_parts) + "</div>"

    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพการมองเห็น (Vision Test)")}
        <div class="main-content-full">
            <table class="data-table">
                <thead><tr><th>รายการตรวจ</th><th>ผลการตรวจ</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            {summary_section_html}
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
        if "ปกติ" in summary_text: return "status-ok"
        if "N/A" in summary_text or "ไม่ได้" in summary_text: return "status-nt"
        return "status-abn"

    summary_cards_html = f"""
    <div class="summary-cards">
        <div class="card {get_summary_class(summary_r_raw)}">
            <div class="card-title">หูขวา (Right Ear)</div>
            <div class="card-body">{html.escape(summary_r_raw)}</div>
        </div>
        <div class="card {get_summary_class(summary_l_raw)}">
            <div class="card-title">หูซ้าย (Left Ear)</div>
            <div class="card-body">{html.escape(summary_l_raw)}</div>
        </div>
    </div>
    """

    advice = results.get('advice', 'ไม่มีคำแนะนำเพิ่มเติม')
    advice_box_html = f"<div class='advice-box info-box'><b>คำแนะนำ:</b> {html.escape(advice)}</div>"
    if results.get('sts_detected'):
        advice_box_html = f"<div class='advice-box warning-box'><b>⚠️ พบการเปลี่ยนแปลงระดับการได้ยินอย่างมีนัยสำคัญ (STS)</b><br>{html.escape(advice)}</div>"

    raw_data = results.get('raw_values', {})
    rows_html = ""
    for freq, values in raw_data.items():
        r_val = values.get('right', '-')
        l_val = values.get('left', '-')
        rows_html += f"<tr><td>{freq}</td><td>{r_val}</td><td>{l_val}</td></tr>"
    data_table_html = f"""
    <table class="data-table">
        <thead><tr><th>ความถี่ (Hz)</th><th>หูขวา (dB)</th><th>หูซ้าย (dB)</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """
    
    # แก้ไข: ปรับปรุงการแสดงผล Baseline Comparison กลับเป็นตาราง
    baseline_html = ""
    if results.get('baseline_source') != 'none':
        baseline_year = results.get('baseline_year')
        
        baseline_rows_html = ""
        freq_order = ['500 Hz', '1000 Hz', '2000 Hz', '3000 Hz', '4000 Hz', '6000 Hz', '8000 Hz']
        for freq in freq_order:
            if freq not in results['shift_values']: continue
            
            shift_r = results['shift_values'][freq].get('right')
            shift_l = results['shift_values'][freq].get('left')
            
            shift_r_text = f"+{shift_r}" if shift_r is not None and shift_r > 0 else (str(shift_r) if shift_r is not None else "-")
            shift_l_text = f"+{shift_l}" if shift_l is not None and shift_l > 0 else (str(shift_l) if shift_l is not None else "-")

            baseline_rows_html += f"<tr><td>{freq}</td><td>{shift_r_text}</td><td>{shift_l_text}</td></tr>"
        
        baseline_html = f"""
        <div class='baseline-comparison'>
            <b>การเปลี่ยนแปลง (dB) เทียบกับผลตรวจพื้นฐาน (พ.ศ. {baseline_year})</b>
            <table class='data-table'>
                <thead><tr><th>ความถี่ (Hz)</th><th>Shift ขวา</th><th>Shift ซ้าย</th></tr></thead>
                <tbody>{baseline_rows_html}</tbody>
            </table>
        </div>
        """
    
    averages = results.get('averages', {})
    avg_r_speech = averages.get('right_500_2000')
    avg_l_speech = averages.get('left_500_2000')
    avg_r_high = averages.get('right_3000_6000')
    avg_l_high = averages.get('left_3000_6000')
    averages_html = f"""
    <div class="advice-box info-box" style="margin-top: 10px;">
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
        {summary_cards_html}
        <div class="content-columns">
            <div class="main-content">
                {data_table_html}
                {baseline_html if baseline_html else ""}
            </div>
            <div class="side-content">
                {advice_box_html}
                {averages_html}
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
        if val is None: return "status-nt"
        return "status-ok" if val >= low_threshold else "status-abn"

    metrics_html = f"""
    <div class="summary-cards">
        <div class="card {get_status_class(raw.get('FVC %'), 80)}">
            <div class="card-title">FVC %Pred</div>
            <div class="card-body">{format_val('FVC %')}%</div>
        </div>
        <div class="card {get_status_class(raw.get('FEV1 %'), 80)}">
            <div class="card-title">FEV1 %Pred</div>
            <div class="card-body">{format_val('FEV1 %')}%</div>
        </div>
        <div class="card {get_status_class(raw.get('FEV1/FVC %'), 70)}">
            <div class="card-title">FEV1/FVC Ratio</div>
            <div class="card-body">{format_val('FEV1/FVC %')}%</div>
        </div>
    </div>
    """
    
    summary_class = "status-ok" if "ปกติ" in summary else "status-abn"
    if "ไม่ได้" in summary or "คลาดเคลื่อน" in summary:
        summary_class = "status-nt"
    
    advice_box_html = f"<div class='advice-box info-box'><b>คำแนะนำ:</b> {html.escape(advice)}</div>"
    
    year = person_data.get("Year")
    cxr_result_text = "ไม่มีข้อมูล"
    if year:
        cxr_col = f"CXR{str(year)[-2:]}" if year != (datetime.now().year + 543) else "CXR"
        cxr_result, cxr_status = interpret_cxr(person_data.get(cxr_col, ''))
        cxr_result_text = cxr_result
    cxr_html = f"""
    <div class="advice-box info-box" style="margin-top: 10px;">
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

    # แก้ไข: จัด Layout ใหม่สำหรับส่วนของปอด
    summary_section_html = f"""
    <div class="summary-container">
        <div class="advice-box {summary_class}" style="text-align: center; margin-bottom: 10px;">
            {html.escape(summary)}
        </div>
        {advice_box_html}
        {cxr_html}
    </div>
    """

    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพปอด (Spirometry)")}
        {metrics_html}
        <div class="main-content-full">
            {data_table_html}
            {summary_section_html}
        </div>
    </div>
    """

def generate_performance_report_html(person_data, all_person_history_df):
    """
    Checks for available performance tests and generates the combined HTML for the standalone performance report.
    This is the main function called to create the printable page.
    """
    # --- Assemble the final HTML page ---
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสมรรถภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
            body {{
                font-family: 'Sarabun', sans-serif !important;
                font-size: 10px;
                margin: 10mm;
                color: #333;
                background-color: #fff;
            }}
            hr {{ border: 0; border-top: 1px solid #e0e0e0; margin: 0.5rem 0; }}
            .info-table {{ width: 100%; font-size: 10px; text-align: left; border-collapse: collapse; }}
            .info-table td {{ padding: 2px 5px; border: none; }}
            
            .report-section {{ margin-bottom: 1.5rem; page-break-inside: avoid; }}
            .section-header {{
                background-color: #00796B; 
                color: white; text-align: center;
                padding: 0.4rem; font-weight: bold; border-radius: 8px;
                margin-bottom: 1rem;
                font-size: 12px;
            }}

            .content-columns {{ display: flex; gap: 15px; align-items: flex-start; }}
            .main-content {{ flex: 2; min-width: 0; }}
            .side-content {{ flex: 1; min-width: 0; }}
            .main-content-full {{ flex: 1; }} /* For single column sections */

            .data-table {{ width: 100%; font-size: 9.5px; border-collapse: collapse; }}
            .data-table th, .data-table td {{
                border: 1px solid #e0e0e0; padding: 4px 6px; text-align: center;
            }}
            .data-table th {{ background-color: #f5f5f5; font-weight: bold; }}
            .data-table td:first-child {{ text-align: left; }}

            .summary-cards {{ display: flex; gap: 10px; margin-bottom: 0.8rem; }}
            .card {{ 
                flex: 1; border-radius: 6px; padding: 8px; text-align: center; 
                border: 1px solid #e0e0e0; background-color: #f9f9f9;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .card-title {{ font-weight: bold; font-size: 10px; margin-bottom: 4px; color: #555;}}
            .card-body {{ font-size: 12px; font-weight: bold; }}

            .summary-container {{ margin-top: 10px; }}
            .advice-box {{
                border-radius: 6px; padding: 8px 12px; font-size: 9.5px;
                line-height: 1.5; border: 1px solid;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                margin-bottom: 5px;
            }}
            .info-box {{ background-color: #e3f2fd; border-color: #bbdefb; }}
            .warning-box {{ background-color: #fff8e1; border-color: #ffecb3; }}
            
            .baseline-comparison {{ margin-top: 10px; }}
            .baseline-comparison b {{ 
                font-size: 10px; display: block; margin-bottom: 5px; text-align: center;
                font-weight: bold;
            }}
            
            .status-ok, .status-abn, .status-nt {{
                padding: 3px 8px;
                border-radius: 12px;
                font-weight: bold;
                font-size: 9px;
                display: inline-block;
                border: 1px solid transparent;
            }}
            .status-ok {{ background-color: #e8f5e9; color: #1b5e20; border-color: #c8e6c9; }}
            .status-abn {{ background-color: #ffcdd2; color: #b71c1c; border-color: #ef9a9a; }}
            .status-nt {{ background-color: #f0f0f0; color: #616161; border-color: #e0e0e0; }}
            
            .signature-section {{
                margin-top: 2rem;
                text-align: right;
                padding-right: 1rem;
                page-break-inside: avoid;
            }}
            .signature-line {{
                display: inline-block;
                text-align: center;
                width: 280px;
            }}
            .signature-line .line {{
                border-bottom: 1px dotted #333;
                margin-bottom: 0.4rem;
                width: 100%;
            }}
            .signature-line .name, .signature-line .title, .signature-line .license {{
                white-space: nowrap;
                font-size: 10px;
            }}

            @media print {{
                body {{ -webkit-print-color-adjust: exact; margin: 0; }}
            }}
        </style>
    </head>
    <body>
        {render_html_header_and_personal_info(person_data)}
        {render_print_vision(person_data)}
        {render_print_hearing(person_data, all_person_history_df)}
        {render_print_lung(person_data)}
        
        <div class="signature-section">
            <div class="signature-line">
                <div class="line"></div>
                <div class="name">นายแพทย์นพรัตน์ รัชฎาพร</div>
                <div class="title">แพทย์อาชีวเวชศาสตร์</div>
                <div class="license">เลขที่ใบอนุญาตฯ ว.26674</div>
            </div>
        </div>
    </body>
    </html>
    """
    return final_html

def generate_performance_report_html_for_main_report(person_data, all_person_history_df):
    """
    Generates a compact version of performance reports to be embedded
    into the main health report. This function remains for compatibility with the main report print.
    """
    parts = []
    
    # Vision
    if has_vision_data(person_data):
        vision_advice = person_data.get('สรุปเหมาะสมกับงาน', 'ไม่มีข้อมูลสรุป')
        parts.append(f"""
        <div class="perf-section">
            <b>การมองเห็น:</b> <span class="summary-box">{html.escape(vision_advice)}</span>
        </div>
        """)

    # Hearing
    if has_hearing_data(person_data):
        results = interpret_audiogram(person_data, all_person_history_df)
        summary = results['summary'].get('overall', 'N/A')
        advice = results.get('advice', 'ไม่มีคำแนะนำ')
        parts.append(f"""
        <div class="perf-section">
            <b>การได้ยิน:</b> <span class="summary-box">สรุป: {html.escape(summary)} | คำแนะนำ: {html.escape(advice)}</span>
        </div>
        """)

    # Lung
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
