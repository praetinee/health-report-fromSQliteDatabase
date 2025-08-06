import pandas as pd
from datetime import datetime
import html
from collections import OrderedDict

# --- แก้ไข: import ฟังก์ชันที่จำเป็นสำหรับการตรวจสมรรถภาพ ---
from performance_tests import generate_comprehensive_recommendations
# --- ใหม่: import โมดูลสำหรับพิมพ์ผลตรวจสมรรถภาพ ---
from print_performance_report import generate_performance_report_html

# ==============================================================================
# หมายเหตุ: ไฟล์นี้ถูกปรับปรุงเพื่อเรียกใช้โมดูล print_performance_report.py
# ในการสร้างรายงานผลตรวจสมรรถภาพ
# ==============================================================================


# --- Helper Functions ---

def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def interpret_bp(sbp, dbp):
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        elif sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        elif sbp < 120 and dbp < 80: return "ความดันปกติ"
        else: return "ความดันค่อนข้างสูง"
    except: return "-"


# --- HTML Rendering Functions ---

def render_section_header(title, subtitle=None):
    full_title = f"{title} <span style='font-weight: normal;'>({subtitle})</span>" if subtitle else title
    return f"""
    <div style='
        background-color: #333;
        color: white;
        text-align: center;
        padding: 0.2rem 0.4rem;
        font-weight: bold;
        border-radius: 6px;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        font-size: 11px;
    '>
        {full_title}
    </div>
    """

def render_html_header(person):
    check_date = person.get("วันที่ตรวจ", "-")
    return f"""
    <div class="report-header-container" style="text-align: center; margin-bottom: 0.5rem; margin-top: 0.5rem;">
        <h1 style="font-size: 1.2rem; margin:0;">รายงานผลการตรวจสุขภาพ</h1>
        <h2 style="font-size: 0.8rem; margin:0;">- คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม -</h2>
        <p style="font-size: 0.7rem; margin:0;">ชั้น 2 อาคารผู้ป่วยนอก-อุบัติเหตุ โรงพยาบาลสันทราย 201 หมู่ 11 ถ.เชียงใหม่–พร้าว ต.หนองหาร อ.สันทราย จ.เชียงใหม่ 50290</p>
        <p style="font-size: 0.7rem; margin:0;">ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167 | <b>วันที่ตรวจ:</b> {check_date or "-"}</p>
    </div>
    """

def render_personal_info(person):
    sbp = person.get("SBP", "")
    dbp = person.get("DBP", "")
    pulse_raw = person.get("pulse", "-")
    pulse_val = str(int(float(pulse_raw))) if not is_empty(pulse_raw) else "-"
    bp_desc = interpret_bp(sbp, dbp)
    bp_val = f"{int(float(sbp))}/{int(float(dbp))} ม.ม.ปรอท" if not is_empty(sbp) and not is_empty(dbp) else "-"
    bp_full = f"{bp_val} ({bp_desc})" if bp_desc != "-" else bp_val

    return f"""
    <div class="personal-info-container">
        <hr style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
        <table class="info-table">
            <tr>
                <td><b>ชื่อ-สกุล:</b> {person.get('ชื่อ-สกุล', '-')}</td>
                <td><b>อายุ:</b> {str(int(float(person.get('อายุ')))) if not is_empty(person.get('อายุ')) else '-'} ปี</td>
                <td><b>เพศ:</b> {person.get('เพศ', '-')}</td>
                <td><b>HN:</b> {str(int(float(person.get('HN')))) if not is_empty(person.get('HN')) else '-'}</td>
            </tr>
            <tr>
                <td><b>น้ำหนัก:</b> {person.get("น้ำหนัก", "-")} กก.</td>
                <td><b>ส่วนสูง:</b> {person.get("ส่วนสูง", "-")} ซม.</td>
                <td><b>ความดันโลหิต:</b> {bp_full}</td>
                <td><b>ชีพจร:</b> {pulse_val} ครั้ง/นาที</td>
            </tr>
        </table>
    </div>
    """

# --- Main Report Generator ---

def generate_printable_report(person):
    """
    Generates a full, self-contained HTML string for the health report,
    including performance tests if available.
    """
    header_html = render_html_header(person)
    personal_info_html = render_personal_info(person)
    
    # Generate recommendations and split for two-column layout
    recommendations_html_full = generate_comprehensive_recommendations(person)
    rec_parts = recommendations_html_full.split("<!-- SPLIT -->")
    rec_left_html = rec_parts[0]
    rec_right_html = rec_parts[1] if len(rec_parts) > 1 else ""

    # --- NEW: Call the new module to get performance report HTML ---
    performance_section_html = generate_performance_report_html(person)

    # --- Assemble the final HTML page ---
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสุขภาพ - {html.escape(person.get('ชื่อ-สกุล', ''))}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
            body {{
                font-family: 'Sarabun', sans-serif !important;
                font-size: 9px;
                margin: 10mm;
                color: #333;
            }}
            p, div, span, td, th {{ line-height: 1.4; }}
            table {{ border-collapse: collapse; width: 100%; }}
            hr {{ border: 0; border-top: 1px solid #ccc; }}
            ul {{ padding-left: 15px; margin: 0.2rem 0; }}
            li {{ margin-bottom: 2px; }}

            .info-table td {{ padding: 2px 5px; }}
            
            .recommendation-section {{
                page-break-inside: avoid;
                margin-top: 1rem;
            }}
            .rec-columns {{ display: flex; flex-wrap: nowrap; gap: 20px; align-items: flex-start; }}
            .rec-col {{ flex: 1; min-width: 0; }}
            
            .perf-section {{ page-break-inside: avoid; margin-top: 0.5rem; }}
            .perf-columns {{ display: flex; flex-wrap: nowrap; gap: 15px; align-items: flex-start; }}
            .perf-col-summary {{ flex: 1; }}
            .perf-col-details {{ flex: 1.2; }}
            .summary-box {{ 
                border: 1px solid #eee; background-color: #fcfcfc; 
                padding: 5px; border-radius: 4px; margin-top: 2px; 
                min-height: 3em;
            }}
            .perf-table {{ width: 100%; font-size: 8px; }}
            .perf-table th, .perf-table td {{ border: 1px solid #ddd; padding: 2px 4px; text-align: center; }}
            .perf-table th {{ background-color: #f2f2f2; }}
            .perf-table td:first-child {{ text-align: left; }}
            .lung-table th, .lung-table td {{ text-align: center; border: 1px solid #ddd; padding: 3px; }}
            
            .status-ok {{ background-color: #e8f5e9; color: #2e7d32; }}
            .status-abn {{ background-color: #ffcdd2; color: #c62828; font-weight: bold; }}
            .status-nt {{ color: #757575; }}

            @media print {{
                body {{ -webkit-print-color-adjust: exact; margin: 0; }}
            }}
        </style>
    </head>
    <body>
        {header_html}
        {personal_info_html}
        {render_section_header("สรุปผลตรวจและคำแนะนำ (Summary & Recommendations)")}
        <div class="recommendation-section">
            <div class="rec-columns">
                <div class="rec-col">
                    {rec_left_html}
                </div>
                <div class="rec-col">
                    {rec_right_html}
                </div>
            </div>
        </div>
        
        {performance_section_html}

    </body>
    </html>
    """
    return final_html
