import pandas as pd
import html
from collections import OrderedDict
from datetime import datetime

# ... existing code ...
from performance_tests import interpret_audiogram, interpret_lung_capacity, interpret_cxr

# ==============================================================================
# Module: print_performance_report.py
# ... existing code ...
# ==============================================================================


# ... existing code ...
def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
# ... existing code ...
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def has_vision_data(person_data):
# ... existing code ...
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
# ... existing code ...
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
# ... existing code ...
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

# ... existing code ...
def render_section_header(title, subtitle=None):
    """Renders a styled section header for the print report."""
# ... existing code ...
    """

def render_html_header_and_personal_info(person):
# ... existing code ...
    return header_html


def render_print_vision(person_data):
# ... existing code ...
    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพการมองเห็น (Vision Test)")}
# ... existing code ...
    </div>
    """

def render_print_hearing(person_data, all_person_history_df):
# ... existing code ...
    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพการได้ยิน (Audiometry)")}
# ... existing code ...
    </div>
    """

def render_print_lung(person_data):
# ... existing code ...
    return f"""
    <div class="report-section">
        {render_section_header("ผลการตรวจสมรรถภาพปอด (Spirometry)")}
# ... existing code ...
    </div>
    """

# --- START: Refactor for Batch Printing ---

def get_performance_report_css():
    """
    แยก CSS ออกมาเพื่อให้ไฟล์ batch_print.py สามารถเรียกใช้ได้
    """
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        body {{
            font-family: 'Sarabun', sans-serif !important;
            /* --- ADJUSTED: font-size and margin --- */
            font-size: 12px; /* <--- ปรับขนาดตัวอักษรหลักขึ้น */
            margin: 0.5cm 0.7cm; 
            /* --- END ADJUSTMENT --- */
            color: #333;
            background-color: #fff;
        }}
        hr {{ border: 0; border-top: 1px solid #e0e0e0; margin: 0.5rem 0; }}
        .info-table {{ width: 100%; font-size: 10.5px; text-align: left; border-collapse: collapse; }} /* <--- ปรับขนาด */
        .info-table td {{ padding: 1px 5px; }}
        
        .header-grid {{ display: flex; align-items: flex-end; justify-content: space-between; }}
        .header-left {{ text-align: left; }}
        .header-right {{ text-align: right; }}

        /* --- START OF CHANGE: Reduced margin-bottom --- */
        .report-section {{ margin-bottom: 0.5rem; page-break-inside: avoid; }} 
        /* --- END OF CHANGE --- */
        
        .section-header {{
            background-color: #00796B; 
            color: white; text-align: center;
            padding: 0.4rem; font-weight: bold; border-radius: 8px;
            margin-bottom: 0.7rem; /* --- CHANGED --- */
            font-size: 13px; /* <--- ปรับขนาด */
        }}

        .content-columns {{ display: flex; gap: 15px; align-items: flex-start; }}
        .main-content {{ flex: 2; min-width: 0; }}
        .side-content {{ flex: 1; min-width: 0; }}
        .main-content-full {{ width: 100%; }}

        .data-table {{ width: 100%; font-size: 10.5px; border-collapse: collapse; }} /* <--- ปรับขนาด */
        .data-table.hearing-table {{ table-layout: fixed; }}
        .data-table th, .data-table td {{
            border: 1px solid #e0e0e0; padding: 4px; text-align: center;
            vertical-align: middle;
        }}
        .data-table th {{ background-color: #f5f5f5; font-weight: bold; }}
        .data-table td:first-child {{ text-align: left; }}

        /* --- START OF CHANGE: CSS for flexbox layout --- */
        .summary-single-line-box {{
            display: flex;
            justify-content: space-between; /* ชิดซ้าย-ขวา */
            align-items: center;
            flex-wrap: wrap; /* เผื่อไว้กรณีข้อความยาวมาก */
            gap: 10px; /* ระยะห่างถ้ามีการ wrap */
            
            padding: 8px;
            border: 1px solid #e0e0e0;
            background-color: #f9f9f9;
            border-radius: 6px;
            margin-bottom: 0.5rem; /* --- CHANGED --- */
            font-size: 12px; /* <--- ปรับขนาด */
            font-weight: bold;
            page-break-inside: avoid; 
        }}
        
        .summary-single-line-box span {{
            text-align: left; /* จัดข้อความในแต่ละ span ให้ชิดซ้าย */
        }}
        /* --- END OF CHANGE --- */

        .summary-container {{ margin-top: 0; }}
        .summary-container-lung {{ margin-top: 10px; }}
        .summary-title-lung {{
            text-align: center;
            font-weight: bold;
            font-size: 11px; /* <--- ปรับลดจาก 13px */
            margin-bottom: 8px; /* <--- ปรับลด margin-bottom */
            line-height: 1.2; /* <--- เพิ่ม line-height ให้ชิดขึ้น */
        }}
        .advice-box {{
            border-radius: 6px; padding: 8px 12px; font-size: 10.5px; /* <--- ปรับขนาด */
            line-height: 1.5; border: 1px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 5px; 
            height: 100%;
            box-sizing: border-box;
            background-color: #fff8e1; 
            border-color: #ffecb3;
        }}
        .summary-container .advice-box:last-child {{
            margin-bottom: 0;
        }}
        
        .status-ok-text {{ color: #1b5e20; }}
        .status-abn-text {{ color: #b71c1c; }}
        .status-nt-text {{ color: #555; }} /* --- ADDED THIS --- */
        
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
            font-size: 11px; /* <--- ปรับขนาด */
        }}

        @media print {{
            body {{ -webkit-print-color-adjust: exact; margin: 0.5cm; }}
            /* Ensure page breaks work */
            div[style*="page-break-after: always;"] {{ page-break-after: always; }}
        }}
    </style>
    """

def render_performance_report_body(person_data, all_person_history_df):
    """
    สร้างเฉพาะส่วน <body> ของรายงานสำหรับคนไข้ 1 คน
    เพื่อให้ batch_print.py สามารถเรียกใช้ได้
    """
    header_html = render_html_header_and_personal_info(person_data)
    vision_html = render_print_vision(person_data)
    hearing_html = render_print_hearing(person_data, all_person_history_df)
    lung_html = render_print_lung(person_data)
    
    signature_html = f"""
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
    {header_html}
    {vision_html}
    {hearing_html}
    {lung_html}
    {signature_html}
    """

def generate_performance_report_html(person_data, all_person_history_df):
    """
    สร้าง HTML ที่สมบูรณ์ (รวม <html>, <head>, <body>) สำหรับคนไข้ 1 คน
    (สำหรับการพิมพ์แบบเดี่ยว)
    """
    css_html = get_performance_report_css()
    body_html = render_performance_report_body(person_data, all_person_history_df)
    
    final_html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลการตรวจสมรรถภาพ - {html.escape(person_data.get('ชื่อ-สกุล', ''))}</title>
        {css_html}
    </head>
    <body>
        {body_html}
    </body>
    </html>
    """
    return final_html

# --- END: Refactor for Batch Printing ---


def generate_performance_report_html_for_main_report(person_data, all_person_history_df):
# ... existing code ...
    return render_section_header("ผลการตรวจสมรรถภาพพิเศษ (Performance Tests)") + "".join(parts)
