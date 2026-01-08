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

def get_float(col, person_data):
    """Safely gets a float value from person_data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

# เพิ่มฟังก์ชันนี้เข้ามาใหม่เพื่อแก้ปัญหา Import Error
def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้ตรวจ", False
    is_abn = False
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]):
        # ถ้าผิดปกติ ให้ใส่สีแดง
        val = f"<span class='status-abn-text'>{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม</span>"
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

def get_performance_report_css():
    """Returns the CSS string for the performance report, matching print_report.py styles."""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #34495e;
            --accent-color: #16a085;
            --danger-color: #c0392b;
            --light-bg: #f8f9fa;
            --border-color: #bdc3c7;
            --warning-bg: #fef9e7;
            --warning-text: #b7950b;
        }

        /* RESET ALL MARGINS & FORCE SARABUN FONT */
        * {
            box-sizing: border-box;
            font-family: 'Sarabun', sans-serif !important;
        }

        @page {
            size: A4;
            margin: 0.5cm !important; /* Force 0.5cm margin on page level */
        }

        html, body {
            width: 210mm;
            min-height: 297mm;
            margin: 0 !important;
            padding: 0 !important;
            background-color: #fff;
            font-family: 'Sarabun', sans-serif !important;
            font-size: 14px; /* Standard readable size matched with health report */
            line-height: 1.3;
            color: #333;
            -webkit-print-color-adjust: exact;
        }

        /* Container acts as the printable area with Padding */
        .container { 
            width: 100%;
            /* height: 297mm;  REMOVED FIXED HEIGHT to prevent extra blank pages */
            min-height: 297mm;
            padding: 0.5cm !important; /* EXACTLY 0.5cm PADDING matched with health report */
            position: relative;
            page-break-after: always;
            overflow: hidden;
        }

        /* Header Styles (Matched with Health Report) */
        .header {
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 5px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .header h1 { font-family: 'Sarabun', sans-serif !important; font-size: 22px; font-weight: 700; color: var(--primary-color); margin: 0; }
        .header p { font-family: 'Sarabun', sans-serif !important; margin: 0; font-size: 12px; color: var(--secondary-color); }
        .patient-info { font-family: 'Sarabun', sans-serif !important; font-size: 13px; text-align: right; }
        .patient-info b { color: var(--primary-color); }

        /* Vitals Bar */
        .vitals-bar {
            background-color: var(--light-bg);
            border-radius: 4px;
            padding: 6px 10px;
            margin-bottom: 10px;
            border: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            flex-wrap: wrap;
            font-family: 'Sarabun', sans-serif !important;
        }
        .vital-item b { color: var(--primary-color); font-weight: 700; margin-right: 3px; }

        /* Report Specific Styles */
        .report-section { margin-bottom: 15px; page-break-inside: avoid; } 
        
        .section-header {
            background-color: var(--primary-color); 
            color: white; 
            padding: 5px 8px;
            border-radius: 3px;
            margin-bottom: 5px;
            margin-top: 10px;
            font-size: 14px;
            font-weight: 700;
            font-family: 'Sarabun', sans-serif !important;
        }

        .content-columns { display: flex; gap: 15px; align-items: flex-start; }
        .main-content { flex: 2; min-width: 0; }
        .side-content { flex: 1; min-width: 0; display: flex; flex-direction: column; } /* Add flex column to side content */
        .main-content-full { width: 100%; }

        .data-table { width: 100%; font-size: 12px; border-collapse: collapse; margin-bottom: 5px; font-family: 'Sarabun', sans-serif !important; }
        .data-table th, .data-table td { padding: 2px 4px; border-bottom: 1px solid #eee; text-align: left; vertical-align: middle; white-space: nowrap; } /* Reduced padding and added nowrap */
        .data-table th { background-color: #f1f2f6; font-weight: 600; color: var(--secondary-color); text-align: center; border-bottom: 2px solid #ddd; }
        .data-table td:first-child { text-align: left; white-space: normal; } /* Allow wrapping only on the first column (labels) if needed, but keeping others tight */
        
        /* Hearing Table specifics */
        .data-table.hearing-table th, .data-table.hearing-table td { text-align: center; }
        .data-table.hearing-table td:first-child { text-align: center; }

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
            font-size: 13px;
            font-weight: bold;
            page-break-inside: avoid; 
        }
        
        .summary-title-lung {
            text-align: center;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 8px;
            line-height: 1.2;
        }
        
        .advice-box {
            border-radius: 6px; padding: 8px 12px; font-size: 13px;
            line-height: 1.4; border: 1px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 5px; 
            height: auto; /* Changed from 100% to auto */
            box-sizing: border-box;
            background-color: #fff8e1; 
            border-color: #ffecb3;
        }
        
        .status-ok-text { color: #1b5e20; }
        /* กำหนดสีแดงเข้มสำหรับค่าผิดปกติ */
        .status-abn-text { color: #c0392b !important; font-weight: bold; }
        .status-nt-text { color: #555; }
        
        /* Footer - FIXED TO BOTTOM OF RIGHT COLUMN (or container bottom) */
        .footer {
            margin-top: 20px;
            font-size: 14px; 
            font-family: 'Sarabun', sans-serif !important;
            text-align: center; /* Center text within the footer block */
            width: 100%;
            /* Removed absolute positioning to let it flow naturally in the column or use specific placement */
        }
        .footer-signature-container {
            position: absolute;
            bottom: 0.5cm; /* ขอบล่าง 0.5cm (padding) */
            right: 0.5cm; /* ขอบขวา 0.5cm (padding) */
            width: 30%; /* Approximate width of the side column or enough for the signature */
            text-align: center;
        }
        .signature-line {
            display: inline-block;
            text-align: center;
        }

        @media print {
            body { background-color: white; padding: 0; }
            .container { box-shadow: none; margin: 0; }
        }
        
        @media screen {
            body { background-color: #555; padding: 20px; display: flex; justify-content: center; }
            .container { box-shadow: 0 0 15px rgba(0,0,0,0.3); background-color: white; margin-bottom: 20px; }
        }
    </style>
    """

def render_section_header(title, subtitle=None):
    """Renders a styled section header matching the theme."""
    full_title = f"{title} <span style='font-weight: normal; font-size: 12px;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div class='section-header'>
        {full_title}
    </div>
    """

def render_html_header_and_personal_info(person):
    """Renders the main header matching print_report.py structure."""
    check_date = person.get("วันที่ตรวจ", datetime.now().strftime("%d/%m/%Y"))
    name = person.get('ชื่อ-สกุล', '-')
    age = str(int(float(person.get('อายุ')))) if str(person.get('อายุ')).replace('.', '', 1).isdigit() else person.get('อายุ', '-')
    sex = person.get('เพศ', '-')
    hn = str(int(float(person.get('HN')))) if str(person.get('HN')).replace('.', '', 1).isdigit() else person.get('HN', '-')
    department = person.get('หน่วยงาน', '-')
    
    return f"""
    <div class="header">
        <div>
            <h1>รายงานผลการตรวจสมรรถภาพ</h1>
            <p>โรงพยาบาลสันทราย (San Sai Hospital)</p>
            <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม</p>
        </div>
        <div class="patient-info">
            <p><b>ชื่อ-สกุล:</b> {name} &nbsp;|&nbsp; <b>อายุ:</b> {age} ปี &nbsp;|&nbsp; <b>เพศ:</b> {sex}</p>
            <p><b>HN:</b> {hn} &nbsp;|&nbsp; <b>หน่วยงาน:</b> {department}</p>
            <p><b>วันที่ตรวจ:</b> {check_date}</p>
        </div>
    </div>
    """

def render_print_vision(person_data):
    """Renders the Vision Test section for the print report."""
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
        status_class = ""

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
            status_class = "status-ok-text"
        elif is_abnormal:
            status_text = "ผิดปกติ"
            status_class = "status-abn-text" # สีแดง
            abnormal_details.append(test['display'].split('(')[0].strip())
        
        rows_html += f"<tr><td>{test['display']}</td><td class='{status_class}'>{status_text}</td></tr>"

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
                    <colgroup>
                        <col style="width: 70%;">
                        <col style="width: 30%;">
                    </colgroup>
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

    # Helper function to highlight abnormal dB values (> 25)
    def format_db_cell(val):
        try:
            float_val = float(val)
            if float_val > 25:
                return f"<span class='status-abn-text'>{val}</span>"
        except (ValueError, TypeError):
            pass
        return val

    # Helper function to format shift values but NOT highlight them in red
    def format_shift_cell(val):
        # We purposely do not apply status-abn-text here to avoid confusion
        return val

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
            <td>{format_db_cell(r_val)}</td>
            <td>{format_db_cell(l_val)}</td>
            <td>{format_shift_cell(shift_r_text)}</td>
            <td>{format_shift_cell(shift_l_text)}</td>
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
        # ถ้าค่าต่ำกว่าเกณฑ์ ให้เป็นสีแดง (abnormal)
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
        # ใช้ interpret_cxr ที่แก้ใหม่ให้มีสีแดงถ้าผิดปกติ
        cxr_result, cxr_status = interpret_cxr(person_data.get(cxr_col, ''))
        cxr_result_text = cxr_result
    
    # ไม่ต้อง escape cxr_result_text อีกรอบเพราะ interpret_cxr ใส่ HTML tag มาแล้ว
    cxr_html = f"""
    <div class="advice-box" style="margin-bottom: 5px;">
        <b>ผลเอกซเรย์ทรวงอก (CXR):</b><br>{cxr_result_text}
    </div>
    """
    
    data_table_html = f"""
    <table class="data-table">
        <colgroup>
            <col style="width: 25%;">
            <col style="width: 25%;">
            <col style="width: 25%;">
            <col style="width: 25%;">
        </colgroup>
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

def render_performance_report_body(person_data, all_person_history_df):
    """Generates the HTML body content for the performance report."""
    header_html = render_html_header_and_personal_info(person_data)
    
    # --- Add Vitals Bar ---
    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    bmi = "-"
    if weight and height:
        bmi_val = weight / ((height/100)**2)
        bmi = f"{bmi_val:.1f}"
    
    sbp, dbp = get_float("SBP", person_data), get_float("DBP", person_data)
    bp = f"{int(sbp)}/{int(dbp)}" if sbp and dbp else "-"
    pulse = f"{int(get_float('pulse', person_data))}" if get_float('pulse', person_data) else "-"
    waist = person_data.get('รอบเอว', '-')

    vitals_html = f"""
            <div class="vitals-bar">
                <span class="vital-item"><b>น้ำหนัก:</b> {weight} กก.</span>
                <span class="vital-item"><b>ส่วนสูง:</b> {height} ซม.</span>
                <span class="vital-item"><b>BMI:</b> {bmi}</span>
                <span class="vital-item"><b>ความดัน:</b> {bp} mmHg</span>
                <span class="vital-item"><b>ชีพจร:</b> {pulse} /นาที</span>
                <span class="vital-item"><b>รอบเอว:</b> {waist} ซม.</span>
            </div>
    """
    
    vision_html = render_print_vision(person_data)
    hearing_html = render_print_hearing(person_data, all_person_history_df)
    lung_html = render_print_lung(person_data)
    
    # Footer with Signature - Positioned absolute bottom right with 0.5cm margin
    footer_html = """
    <div class="footer-signature-container">
        <div class="signature-line">
            <b>นายแพทย์นพรัตน์ รัชฎาพร</b><br>
            แพทย์อาชีวเวชศาสตร์ (ว.26674)<br>
        </div>
    </div>
    """
    
    return f"""
    <div class="container">
        {header_html}
        {vitals_html}
        {vision_html}
        {hearing_html}
        {lung_html}
        {footer_html}
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
    <body onload="setTimeout(function(){{window.print();}}, 500)">
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
