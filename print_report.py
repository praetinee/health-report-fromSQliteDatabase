import pandas as pd
import numpy as np
import html
from datetime import datetime

# Import logic for recommendations
try:
    from performance_tests import generate_comprehensive_recommendations
except ImportError:
    def generate_comprehensive_recommendations(person_data): return "<div>-</div>"

# --- Helper Functions ---
def is_empty(val):
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

def get_float(val):
    if is_empty(val): return None
    try: return float(str(val).replace(",", "").strip())
    except: return None

# --- CSS Styles for Main Report ---
def get_main_report_css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700&display=swap');
        
        body { font-family: 'Sarabun', sans-serif; font-size: 14px; color: #333; line-height: 1.4; }
        .page-container { width: 100%; max-width: 210mm; margin: 0 auto; padding: 20px; background: white; box-sizing: border-box; }
        
        /* Header */
        .report-header { 
            border-bottom: 3px solid #00796B; 
            padding-bottom: 15px; 
            margin-bottom: 20px; 
            display: flex; 
            justify-content: space-between; 
            align-items: flex-end; 
        }
        .hospital-name { font-size: 22px; font-weight: bold; color: #00796B; margin-bottom: 5px; }
        .dept-name { font-size: 16px; color: #555; }
        .print-date { font-size: 12px; color: #999; }
        
        /* Patient Info Grid */
        .patient-info-box { 
            background-color: #f4fdfb; 
            border: 1px solid #b2dfdb; 
            border-radius: 8px; 
            padding: 15px; 
            margin-bottom: 25px; 
            display: grid; 
            grid-template-columns: 1fr 1fr 1fr; 
            gap: 12px; 
        }
        .info-item { font-size: 14px; }
        .info-label { font-weight: 600; color: #00695c; margin-right: 5px; }
        
        /* Section Headers */
        .section-header { 
            background-color: #00796B; 
            color: white; 
            padding: 8px 15px; 
            border-radius: 5px; 
            font-weight: bold; 
            margin-bottom: 15px; 
            font-size: 16px; 
            margin-top: 10px;
        }
        
        /* Tables */
        .result-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }
        .result-table th { 
            background-color: #e0f2f1; 
            border: 1px solid #b2dfdb; 
            padding: 10px; 
            text-align: center; 
            font-weight: bold; 
            color: #004d40; 
        }
        .result-table td { border: 1px solid #ddd; padding: 8px; vertical-align: middle; }
        
        .col-name { width: 40%; }
        .col-result { width: 20%; text-align: center; font-weight: 600; }
        .col-unit { width: 15%; text-align: center; color: #7f8c8d; }
        .col-normal { width: 25%; text-align: center; font-size: 12px; color: #666; }
        
        /* Status Colors */
        .abnormal-high { color: #d32f2f; font-weight: bold; }
        .abnormal-low { color: #d32f2f; font-weight: bold; }
        .normal-val { color: #2e7d32; }
        
        /* Recommendations Box */
        .rec-container { 
            border: 1px solid #c8e6c9; 
            background-color: #e8f5e9; 
            border-radius: 8px; 
            padding: 20px; 
            min-height: 100px;
        }
        .rec-container ul { margin-top: 5px; margin-bottom: 5px; padding-left: 20px; }
        .rec-container li { margin-bottom: 5px; }
        
        /* Print Adjustments */
        @media print {
            .page-container { padding: 0; box-shadow: none; margin: 0; width: 100%; max-width: none; }
            body { background-color: white; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .section-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .patient-info-box { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .rec-container { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            @page { margin: 10mm; }
        }
    </style>
    """

def check_abnormal(val, low, high):
    v = get_float(val)
    if v is None: return "", ""
    
    status = ""
    css = "normal-val"
    if low is not None and v < low:
        status = " (ต่ำ)"
        css = "abnormal-low"
    elif high is not None and v > high:
        status = " (สูง)"
        css = "abnormal-high"
    return status, css

def render_lab_row(label, val, unit, normal_text, low=None, high=None):
    status, css = check_abnormal(val, low, high)
    display_val = str(val) if not is_empty(val) else "-"
    return f"""
    <tr>
        <td>{label}</td>
        <td class="{css}" style="text-align:center;">{display_val}{status}</td>
        <td style="text-align:center;">{unit}</td>
        <td style="text-align:center;">{normal_text}</td>
    </tr>
    """

# --- Main Render Function (Required by batch_print.py) ---
def render_printable_report_body(person_data, history_df):
    # 1. Prepare Data
    name = person_data.get('ชื่อ-สกุล', '-')
    hn = person_data.get('HN', '-')
    age = person_data.get('อายุ', '-')
    date = person_data.get('วันที่ตรวจ', '-')
    dept = person_data.get('หน่วยงาน', '-')
    
    # 2. Header Section
    header = f"""
    <div class="page-container">
        <div class="report-header">
            <div>
                <div class="hospital-name">รายงานผลการตรวจสุขภาพ (Health Checkup Report)</div>
                <div class="dept-name">คลินิกตรวจสุขภาพ โรงพยาบาลสันทราย</div>
            </div>
            <div style="text-align:right;">
                <div class="print-date">วันที่พิมพ์: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            </div>
        </div>
        
        <div class="patient-info-box">
            <div class="info-item"><span class="info-label">ชื่อ-สกุล:</span> {name}</div>
            <div class="info-item"><span class="info-label">HN:</span> {hn}</div>
            <div class="info-item"><span class="info-label">หน่วยงาน:</span> {dept}</div>
            <div class="info-item"><span class="info-label">อายุ:</span> {age} ปี</div>
            <div class="info-item"><span class="info-label">เพศ:</span> {person_data.get('เพศ','-')}</div>
            <div class="info-item"><span class="info-label">วันที่ตรวจ:</span> {date}</div>
        </div>
    """
    
    # 3. Vitals Section
    w = person_data.get('น้ำหนัก', '-')
    h = person_data.get('ส่วนสูง', '-')
    bmi = "-"
    if get_float(w) and get_float(h):
        bmi = f"{get_float(w) / ((get_float(h)/100)**2):.1f}"
    
    bp = f"{person_data.get('SBP','-')}/{person_data.get('DBP','-')}"
    
    vitals = f"""
    <div class="section-header">1. ข้อมูลสุขภาพพื้นฐาน (Vital Signs)</div>
    <table class="result-table">
        <tr>
            <th>น้ำหนัก (kg)</th><th>ส่วนสูง (cm)</th><th>ดัชนีมวลกาย (BMI)</th>
            <th>ความดันโลหิต (mmHg)</th><th>ชีพจร (bpm)</th><th>รอบเอว (cm)</th>
        </tr>
        <tr>
            <td style="text-align:center;">{w}</td>
            <td style="text-align:center;">{h}</td>
            <td style="text-align:center;">{bmi}</td>
            <td style="text-align:center;">{bp}</td>
            <td style="text-align:center;">{person_data.get('pulse','-')}</td>
            <td style="text-align:center;">{person_data.get('รอบเอว','-')}</td>
        </tr>
    </table>
    """
    
    # 4. Lab: CBC
    sex = person_data.get('เพศ', 'ชาย')
    hb_low = 12 if sex == 'หญิง' else 13
    hct_low = 36 if sex == 'หญิง' else 39
    
    labs_cbc = f"""
    <div class="section-header">2. ผลตรวจเลือด (Laboratory Results)</div>
    <table class="result-table">
        <thead>
            <tr style="background-color:#f9f9f9;"><th colspan="4" style="text-align:left; padding-left:15px; color:#333;">2.1 ความสมบูรณ์ของเม็ดเลือด (Complete Blood Count)</th></tr>
            <tr><th>รายการตรวจ (Test)</th><th>ผลการตรวจ (Result)</th><th>หน่วย (Unit)</th><th>ค่าปกติ (Normal Range)</th></tr>
        </thead>
        <tbody>
            {render_lab_row("Hemoglobin (Hb)", person_data.get('Hb(%)'), "g/dL", f"> {hb_low}", low=hb_low)}
            {render_lab_row("Hematocrit (Hct)", person_data.get('HCT'), "%", f"> {hct_low}", low=hct_low)}
            {render_lab_row("White Blood Cell (WBC)", person_data.get('WBC (cumm)'), "cells/mm³", "4,000-10,000", 4000, 10000)}
            {render_lab_row("Platelet Count", person_data.get('Plt (/mm)'), "cells/mm³", "140,000-450,000", 140000, 450000)}
        </tbody>
    </table>
    """
    
    # 5. Lab: Chemistry
    labs_chem = f"""
    <table class="result-table">
        <thead>
            <tr style="background-color:#f9f9f9;"><th colspan="4" style="text-align:left; padding-left:15px; color:#333;">2.2 เคมีคลินิก (Blood Chemistry)</th></tr>
            <tr><th>รายการตรวจ (Test)</th><th>ผลการตรวจ (Result)</th><th>หน่วย (Unit)</th><th>ค่าปกติ (Normal Range)</th></tr>
        </thead>
        <tbody>
            {render_lab_row("Glucose (FBS)", person_data.get('FBS'), "mg/dL", "70-99", 70, 99)}
            {render_lab_row("Cholesterol", person_data.get('CHOL'), "mg/dL", "< 200", high=200)}
            {render_lab_row("Triglyceride", person_data.get('TGL'), "mg/dL", "< 150", high=150)}
            {render_lab_row("HDL-Cholesterol", person_data.get('HDL'), "mg/dL", "> 40", low=40)}
            {render_lab_row("LDL-Cholesterol", person_data.get('LDL'), "mg/dL", "< 130", high=130)}
            {render_lab_row("Creatinine (Cr)", person_data.get('Cr'), "mg/dL", "0.5-1.2", 0.5, 1.2)}
            {render_lab_row("eGFR", person_data.get('GFR'), "ml/min", "> 60", low=60)}
            {render_lab_row("SGOT (AST)", person_data.get('SGOT'), "U/L", "0-40", high=40)}
            {render_lab_row("SGPT (ALT)", person_data.get('SGPT'), "U/L", "0-41", high=41)}
            {render_lab_row("Uric Acid", person_data.get('Uric Acid'), "mg/dL", "2.5-7.2", 2.5, 7.2)}
        </tbody>
    </table>
    """
    
    # 6. Recommendations
    rec_text = generate_comprehensive_recommendations(person_data)
    recommendations = f"""
    <div class="section-header">3. สรุปผลและคำแนะนำ (Summary & Recommendations)</div>
    <div class="rec-container">
        {rec_text}
    </div>
    """
    
    footer = "</div>" # Close page-container
    
    return header + vitals + labs_cbc + labs_chem + recommendations + footer

# --- Wrapper for Single Page Print ---
def generate_printable_report(person_data, history_df):
    """Wrapper to generate full HTML page"""
    css = get_main_report_css()
    body = render_printable_report_body(person_data, history_df)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>รายงานผลตรวจสุขภาพ - {person_data.get('ชื่อ-สกุล', '')}</title>
        {css}
    </head>
    <body onload="setTimeout(function(){{window.print();}}, 500)">
        {body}
    </body>
    </html>
    """
