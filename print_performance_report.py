import pandas as pd
import html
from collections import OrderedDict
from datetime import datetime

from performance_tests import interpret_audiogram, interpret_lung_capacity

# ==============================================================================
# Module: print_performance_report.py
# Purpose: Contains functions to generate HTML for performance test reports
# (Vision, Hearing, Lung) for the standalone printable version.
# ==============================================================================


# --- Helper & Data Availability Functions ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

# --- แก้ไข: ใช้ฟังก์ชันตรวจสอบข้อมูลที่ครอบคลุมเหมือนใน app.py ---
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
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div class='section-header'>
        {full_title}
    </div>
    """

def render_html_header_and_personal_info(person):
    check_date = person.get("วันที่ตรวจ", "-")
    
    # Vital Signs
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
    if not has_vision_data(person_data):
        return ""

    # --- แก้ไข: ดึงข้อมูลทั้งหมดมาแสดงในตาราง ---
    vision_tests = [
        {'d': '1. การมองด้วย 2 ตา (Binocular vision)', 'c': 'ป.การรวมภาพ', 'nk': ['ปกติ']},
        {'d': '2. การมองภาพระยะไกลด้วยสองตา (Far vision - Both)', 'c': 'ป.ความชัดของภาพระยะไกล', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': '3. การมองภาพระยะไกลด้วยตาขวา (Far vision - Right)', 'c': 'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': '4. การมองภาพระยะไกลด้วยตาซ้าย (Far vision - Left)', 'c': 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': '5. การมองภาพ 3 มิติ (Stereo depth)', 'c': 'ป.การกะระยะและมองความชัดลึกของภาพ', 'nk': ['ปกติ']},
        {'d': '6. การมองจำแนกสี (Color discrimination)', 'c': 'ป.การจำแนกสี', 'nk': ['ปกติ']},
        {'d': '7. การมองภาพระยะใกล้ด้วยสองตา (Near vision - Both)', 'c': 'ป.ความชัดของภาพระยะใกล้', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': '8. การมองภาพระยะใกล้ด้วยตาขวา (Near vision - Right)', 'c': 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': '9. การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision - Left)', 'c': 'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'nk': ['ชัดเจน', 'ปกติ']},
        {'d': '10. ลานสายตา (Visual field)', 'c': 'ป.ลานสายตา', 'nk': ['ปกติ']},
        {'d': '11. ตาเข/ตาเหล่ซ่อนเร้น (Phoria)', 'c': 'ผ.สายตาเขซ่อนเร้น', 'nk': []} # หากมีค่าถือว่าผิดปกติ
    ]
    
    rows_html = ""
    abnormal_details = []
    for test in vision_tests:
        val = str(person_data.get(test['c'], '')).strip()
        status = "ไม่ได้ตรวจ"
        status_class = "status-nt"
        
        # Logic for normal/abnormal check
        is_abnormal = False
        if not is_empty(val):
            # For Phoria, any value is abnormal
            if test['c'] == 'ผ.สายตาเขซ่อนเร้น':
                is_abnormal = True
            # For others, check against normal keywords
            elif not any(k.lower() in val.lower() for k in test['nk']):
                is_abnormal = True

            if is_abnormal:
                status = f"ผิดปกติ ({val})"
                status_class = "status-abn"
                abnormal_details.append(test['d'].split('(')[0].strip())
            else:
                status = "ปกติ"
                status_class = "status-ok"

        rows_html += f"<tr><td>{test['d']}</td><td class='{status_class}'>{status}</td></tr>"

    doctor_advice = person_data.get('แนะนำABN EYE', '')
    summary_advice = person_data.get('สรุปเหมาะสมกับงาน', '')
    
    advice_html = ""
    if abnormal_details or not is_empty(doctor_advice):
        advice_parts = []
        if abnormal_details:
            advice_parts.append(f"<b>พบความผิดปกติ:</b> {', '.join(abnormal_details)}")
        if not is_empty(doctor_advice):
            advice_parts.append(f"<b>คำแนะนำแพทย์:</b> {doctor_advice}")
        advice_html = "<div class='advice-box warning-box'>" + "<br>".join(advice_parts) + "</div>"
    
    summary_html = ""
    if not is_empty(summary_advice):
         summary_html = f"<div class='advice-box info-box'><b>สรุปความเหมาะสมกับงาน:</b> {summary_advice}</div>"


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
                {summary_html}
                {advice_html}
            </div>
        </div>
    </div>
    """

def render_print_hearing(person_data, all_person_history_df):
    if not has_hearing_data(person_data):
        return ""
        
    results = interpret_audiogram(person_data, all_person_history_df)
    
    # Summary Cards
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
            <div class="card-body">{summary_r_raw}</div>
        </div>
        <div class="card {get_summary_class(summary_l_raw)}">
            <div class="card-title">หูซ้าย (Left Ear)</div>
            <div class="card-body">{summary_l_raw}</div>
        </div>
    </div>
    """

    # Advice Box
    advice = results.get('advice', 'ไม่มีคำแนะนำเพิ่มเติม')
    advice_box_html = f"<div class='advice-box info-box'><b>คำแนะนำ:</b> {advice}</div>"
    if results.get('sts_detected'):
        advice_box_html = f"<div class='advice-box warning-box'><b>⚠️ พบการเปลี่ยนแปลงระดับการได้ยินอย่างมีนัยสำคัญ (STS)</b><br>{advice}</div>"

    # Data Table
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
    
    # --- แก้ไข: เพิ่มตาราง Baseline ---
    baseline_html = ""
    if results.get('baseline_source') != 'none':
        baseline_year = results.get('baseline_year')
        baseline_rows_html = ""
        for freq, values in results.get('raw_values', {}).items():
            shift_r = results['shift_values'][freq].get('right', '-')
            shift_l = results['shift_values'][freq].get('left', '-')
            baseline_rows_html += f"<tr><td>{freq}</td><td>{shift_r}</td><td>{shift_l}</td></tr>"
        
        baseline_html = f"""
        <div class='side-content' style='margin-top: 10px;'>
            <b>การเปลี่ยนแปลงเทียบกับผลตรวจพื้นฐาน (พ.ศ. {baseline_year})</b>
            <table class='data-table'>
                <thead><tr><th>ความถี่ (Hz)</th><th>Shift ขวา (dB)</th><th>Shift ซ้าย (dB)</th></tr></thead>
                <tbody>{baseline_rows_html}</tbody>
            </table>
        </div>
        """


    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพการได้ยิน (Audiometry)")}
        {summary_cards_html}
        <div class="content-columns">
            <div class="main-content">
                {data_table_html}
                {baseline_html}
            </div>
            <div class="side-content">
                {advice_box_html}
            </div>
        </div>
    </div>
    """

def render_print_lung(person_data):
    if not has_lung_data(person_data):
        return ""
        
    summary, advice, raw = interpret_lung_capacity(person_data)

    def format_val(key, spec='.1f'):
        val = raw.get(key)
        return f"{val:{spec}}" if val is not None else "-"

    def get_status_class(summary_text):
        if "ปกติ" in summary_text: return "status-ok"
        if "ไม่ได้" in summary_text or "คลาดเคลื่อน" in summary_text: return "status-nt"
        return "status-abn"

    summary_card_html = f"""
    <div class="summary-cards">
        <div class="card {get_status_class(summary)}">
            <div class="card-title">ผลการแปลความหมาย</div>
            <div class="card-body">{summary}</div>
        </div>
    </div>
    """
    
    advice_box_html = f"<div class='advice-box info-box'><b>คำแนะนำ:</b> {advice}</div>"
    
    data_table_html = f"""
    <table class="data-table">
        <thead>
            <tr><th>การทดสอบ</th><th>ค่าที่วัดได้</th><th>ค่ามาตรฐาน</th><th>% เทียบค่ามาตรฐาน</th></tr>
        </thead>
        <tbody>
            <tr><td>FVC (L)</td><td>{format_val('FVC', '.2f')}</td><td>{format_val('FVC predic', '.2f')}</td><td class='{get_status_class("ปกติ" if (raw.get("FVC %") or 100) >= 80 else "ผิดปกติ")}'>{format_val('FVC %')} %</td></tr>
            <tr><td>FEV1 (L)</td><td>{format_val('FEV1', '.2f')}</td><td>{format_val('FEV1 predic', '.2f')}</td><td class='{get_status_class("ปกติ" if (raw.get("FEV1 %") or 100) >= 80 else "ผิดปกติ")}'>{format_val('FEV1 %')} %</td></tr>
            <tr><td>FEV1/FVC (%)</td><td class='{get_status_class("ปกติ" if (raw.get("FEV1/FVC %") or 100) >= 70 else "ผิดปกติ")}'>{format_val('FEV1/FVC %')} %</td><td>{format_val('FEV1/FVC % pre')} %</td><td>-</td></tr>
        </tbody>
    </table>
    """

    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพปอด (Spirometry)")}
        {summary_card_html}
        <div class="content-columns">
            <div class="main-content">
                {data_table_html}
            </div>
            <div class="side-content">
                {advice_box_html}
            </div>
        </div>
    </div>
    """

def generate_performance_report_html(person_data, all_person_history_df):
    """
    Checks for available performance tests and generates the combined HTML for standalone performance report.
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
            hr {{ border: 0; border-top: 1px solid #ccc; margin: 0.5rem 0; }}
            .info-table {{ width: 100%; font-size: 10px; text-align: left; }}
            .info-table td {{ padding: 2px 5px; border: none; }}
            
            .report-section {{ margin-bottom: 1.5rem; page-break-inside: avoid; }}
            .section-header {{
                background-color: #333; color: white; text-align: center;
                padding: 0.3rem; font-weight: bold; border-radius: 8px;
                margin-bottom: 0.8rem; font-size: 12px;
            }}

            .content-columns {{ display: flex; gap: 15px; align-items: flex-start; }}
            .main-content {{ flex: 2; min-width: 0; }}
            .side-content {{ flex: 1; min-width: 0; }}

            .data-table {{ width: 100%; font-size: 9.5px; border-collapse: collapse; }}
            .data-table th, .data-table td {{
                border: 1px solid #e0e0e0; padding: 4px 6px; text-align: center;
            }}
            .data-table th {{ background-color: #f2f2f2; }}
            .data-table td:first-child {{ text-align: left; }}

            .summary-cards {{ display: flex; gap: 10px; margin-bottom: 0.8rem; }}
            .card {{ flex: 1; border-radius: 6px; padding: 8px; text-align: center; border: 1px solid; }}
            .card-title {{ font-weight: bold; font-size: 10px; margin-bottom: 4px;}}
            .card-body {{ font-size: 11px; font-weight: bold; }}

            .advice-box {{
                border-radius: 6px; padding: 8px 12px; font-size: 9.5px;
                line-height: 1.5; border: 1px solid; margin-top: 5px;
            }}
            .info-box {{ background-color: #e3f2fd; border-color: #bbdefb; }}
            .warning-box {{ background-color: #fff8e1; border-color: #ffecb3; }}

            .status-ok {{ background-color: #e8f5e9; color: #1b5e20; }}
            .status-abn {{ background-color: #ffcdd2; color: #b71c1c; }}
            .status-nt {{ background-color: #f5f5f5; color: #616161; }}

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
    </body>
    </html>
    """
    return final_html

# --- HTML Rendering Functions for Main Report Integration ---

def generate_performance_report_html_for_main_report(person_data, all_person_history_df):
    """
    Generates a compact version of performance reports to be embedded
    into the main health report.
    """
    parts = []
    
    # Vision
    if has_vision_data(person_data):
        vision_advice = person_data.get('สรุปเหมาะสมกับงาน', 'ไม่มีข้อมูลสรุป')
        parts.append(f"""
        <div class="perf-section">
            <b>การมองเห็น:</b> <span class="summary-box">{vision_advice}</span>
        </div>
        """)

    # Hearing
    if has_hearing_data(person_data):
        results = interpret_audiogram(person_data, all_person_history_df)
        summary = results['summary'].get('overall', 'N/A')
        advice = results.get('advice', 'ไม่มีคำแนะนำ')
        parts.append(f"""
        <div class="perf-section">
            <b>การได้ยิน:</b> <span class="summary-box">สรุป: {summary} | คำแนะนำ: {advice}</span>
        </div>
        """)

    # Lung
    if has_lung_data(person_data):
        summary, advice, _ = interpret_lung_capacity(person_data)
        parts.append(f"""
        <div class="perf-section">
            <b>สมรรถภาพปอด:</b> <span class="summary-box">สรุป: {summary} | คำแนะนำ: {advice}</span>
        </div>
        """)

    if not parts:
        return ""

    return render_section_header("ผลการตรวจสมรรถภาพพิเศษ (Performance Tests)") + "".join(parts)
