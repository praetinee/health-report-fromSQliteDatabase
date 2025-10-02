import streamlit as st
import sqlite3
import requests
import pandas as pd
import io
import tempfile
import html
import numpy as np
from collections import OrderedDict
from datetime import datetime
import re
import os
import json
from streamlit_js_eval import streamlit_js_eval
import plotly.graph_objects as go
import plotly.express as px


# --- Import ฟังก์ชันจากไฟล์อื่น ---
from performance_tests import interpret_audiogram, interpret_lung_capacity, generate_comprehensive_recommendations
from print_report import generate_printable_report
from print_performance_report import generate_performance_report_html


# --- Helper Functions (ที่ยังคงใช้งาน) ---
def is_empty(val):
    """Check if a value is empty, null, or whitespace."""
    return pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]

THAI_MONTHS_GLOBAL = {1: "มกราคม", 2: "กุมภาพันธ์", 3: "มีนาคม", 4: "เมษายน", 5: "พฤษภาคม", 6: "มิถุนายน", 7: "กรกฎาคม", 8: "สิงหาคม", 9: "กันยายน", 10: "ตุลาคม", 11: "พฤศจิกายน", 12: "ธันวาคม"}
THAI_MONTH_ABBR_TO_NUM_GLOBAL = {"ม.ค.": 1, "ม.ค": 1, "มกราคม": 1, "ก.พ.": 2, "ก.พ": 2, "กพ": 2, "กุมภาพันธ์": 2, "มี.ค.": 3, "มี.ค": 3, "มีนาคม": 3, "เม.ย.": 4, "เม.ย": 4, "เมษายน": 4, "พ.ค.": 5, "พ.ค": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิ.ย": 6, "มิถุนายน": 6, "ก.ค.": 7, "ก.ค": 7, "กรกฎาคม": 7, "ส.ค.": 8, "ส.ค": 8, "สิงหาคม": 8, "ก.ย.": 9, "ก.ย": 9, "กันยายน": 9, "ต.ค.": 10, "ต.ค": 10, "ตุลาคม": 10, "พ.ย.": 11, "พ.ย": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธ.ค": 12, "ธันวาคม": 12}

def normalize_thai_date(date_str):
    if is_empty(date_str): return pd.NA
    s = str(date_str).strip().replace("พ.ศ.", "").replace("พศ.", "").strip()
    if s.lower() in ["ไม่ตรวจ", "นัดทีหลัง", "ไม่ได้เข้ารับการตรวจ", ""]: return pd.NA
    try:
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', s):
            day, month, year = map(int, s.split('/'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"
        if re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', s):
            day, month, year = map(int, s.split('-'))
            if year > 2500: year -= 543
            dt = datetime(year, month, day)
            return f"{dt.day} {THAI_MONTHS_GLOBAL[dt.month]} {dt.year + 543}"
        match_thai_text_date = re.match(r'^(?P<day1>\d{1,2})\.?\s*(?P<month_str>[ก-ฮ]+\.?)\s*(?P<year>\d{4})$', s)
        if match_thai_text_date:
            day = int(match_thai_text_date.group('day1'))
            month_str = match_thai_text_date.group('month_str').strip().replace('.', '')
            year = int(match_thai_text_date.group('year'))
            month_num = THAI_MONTH_ABBR_TO_NUM_GLOBAL.get(month_str)
            if month_num:
                dt = datetime(year - 543, month_num, day)
                return f"{day} {THAI_MONTHS_GLOBAL[dt.month]} {year}"
    except Exception: pass
    try:
        parsed_dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(parsed_dt):
            if parsed_dt.year > datetime.now().year + 50:
                parsed_dt = parsed_dt.replace(year=parsed_dt.year - 543)
            return f"{parsed_dt.day} {THAI_MONTHS_GLOBAL[parsed_dt.month]} {parsed_dt.year + 543}"
    except Exception: pass
    return pd.NA

def get_float(col, person_data):
    """Safely gets a float value from person_data dictionary."""
    try:
        val = person_data.get(col, "")
        if is_empty(val): return None
        return float(str(val).replace(",", "").strip())
    except: return None

# --- START: โค้ดจาก visualization.py ---

# --- ฟังก์ชันหลักสำหรับแสดงผล (จัด Layout ใหม่) ---
def display_visualization_tab(person_data, history_df):
    """
    ฟังก์ชันหลักสำหรับแสดงผลแท็บ Visualization ทั้งหมด
    จัด Layout ใหม่โดยแสดง Dashboard สรุปก่อน และซ่อนรายละเอียดไว้ใน Expander
    """
    st.header(f"📊 ภาพรวมสุขภาพของคุณ: {person_data.get('ชื่อ-สกุล', '')}")
    st.markdown("---")

    # Section 1: Health Dashboard (ใหม่)
    plot_health_dashboard(person_data)

    st.markdown("---")
    
    # Section 2: รายละเอียดเพิ่มเติม (ซ่อนใน Expander)
    with st.expander("คลิกเพื่อดูรายละเอียดเชิงลึกและแนวโน้มย้อนหลัง"):
        
        st.subheader("เจาะลึกผลสุขภาพรายบุคคล")
        col1, col2 = st.columns([2, 3])
        with col1:
            plot_risk_radar(person_data)
        with col2:
            plot_gauge_charts(person_data)
        
        st.markdown("<hr>", unsafe_allow_html=True)

        st.subheader(f"เจาะลึกสมรรถภาพร่างกาย")
        col3, col4 = st.columns(2)
        with col3:
            plot_audiogram(person_data)
        with col4:
            plot_lung_comparison(person_data)
            
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.subheader("กราฟแสดงแนวโน้มผลสุขภาพย้อนหลัง")
        plot_historical_trends(history_df)

# --- ส่วนคำนวณคะแนนสุขภาพ (Health Score) ---
def calculate_health_score(person_data):
    """คำนวณคะแนนสุขภาพองค์รวมจากตัวชี้วัดหลัก"""
    scores = {}
    
    # 1. BMI Score (น้ำหนัก 20%)
    bmi = get_float('BMI', person_data)
    if bmi is None:
        weight = get_float('น้ำหนัก', person_data)
        height = get_float('ส่วนสูง', person_data)
        if weight and height: bmi = weight / ((height/100)**2)
    
    if bmi is not None:
        if 18.5 <= bmi < 23: scores['BMI'] = 100
        elif 23 <= bmi < 25: scores['BMI'] = 75
        elif 25 <= bmi < 30: scores['BMI'] = 50
        else: scores['BMI'] = 25

    # 2. Blood Pressure Score (น้ำหนัก 25%)
    sbp = get_float('SBP', person_data)
    if sbp is not None:
        if sbp < 120: scores['SBP'] = 100
        elif sbp < 130: scores['SBP'] = 80
        elif sbp < 140: scores['SBP'] = 60
        elif sbp < 160: scores['SBP'] = 40
        else: scores['SBP'] = 20

    # 3. Blood Sugar Score (น้ำหนัก 25%)
    fbs = get_float('FBS', person_data)
    if fbs is not None:
        if fbs < 100: scores['FBS'] = 100
        elif fbs < 126: scores['FBS'] = 70
        else: scores['FBS'] = 40
    
    # 4. LDL Score (น้ำหนัก 15%)
    ldl = get_float('LDL', person_data)
    if ldl is not None:
        if ldl < 130: scores['LDL'] = 100
        elif ldl < 160: scores['LDL'] = 70
        elif ldl < 190: scores['LDL'] = 40
        else: scores['LDL'] = 20
        
    # 5. GFR Score (น้ำหนัก 15%)
    gfr = get_float('GFR', person_data)
    if gfr is not None:
        if gfr >= 90: scores['GFR'] = 100
        elif gfr >= 60: scores['GFR'] = 80
        elif gfr >= 30: scores['GFR'] = 50
        else: scores['GFR'] = 20

    # คำนวณคะแนนเฉลี่ยแบบถ่วงน้ำหนัก
    weights = {'BMI': 0.20, 'SBP': 0.25, 'FBS': 0.25, 'LDL': 0.15, 'GFR': 0.15}
    total_score = 0
    total_weight = 0
    
    for key, score in scores.items():
        total_score += score * weights[key]
        total_weight += weights[key]
        
    if total_weight == 0: return 0, [], []
    
    final_score = total_score / total_weight
    
    # สรุปจุดแข็งและจุดที่ควรพัฒนา
    positives = [k for k, v in scores.items() if v >= 80]
    improvements = [k for k, v in scores.items() if v < 70]
    
    return final_score, positives, improvements

# --- Dashboard สรุปภาพรวม ---
def plot_health_dashboard(person_data):
    """สร้าง Dashboard สรุปภาพรวมสุขภาพ ประกอบด้วย Health Score และ Body Map"""
    score, positives, improvements = calculate_health_score(person_data)
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("⭐ Health Score")
        st.caption("คะแนนสุขภาพโดยรวม ประเมินจาก 5 ปัจจัยหลัก ยิ่งคะแนนสูง ยิ่งสุขภาพดี")
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            number={'suffix': "/100"},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "คะแนนสุขภาพองค์รวม", 'font': {'size': 18}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#2E7D32" if score >= 80 else ("#F9A825" if score >= 60 else "#C62828")},
                'steps': [
                    {'range': [0, 60], 'color': 'rgba(220, 53, 69, 0.2)'},
                    {'range': [60, 80], 'color': 'rgba(255, 193, 7, 0.2)'},
                    {'range': [80, 100], 'color': 'rgba(40, 167, 69, 0.2)'}],
            }))
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun")
        st.plotly_chart(fig, use_container_width=True)

        if positives:
            st.success(f"**จุดแข็ง:** {', '.join(positives)} อยู่ในเกณฑ์ดีมาก")
        if improvements:
            st.warning(f"**ควรพัฒนา:** {', '.join(improvements)} ควรให้ความสำคัญเป็นพิเศษ")

    with col2:
        st.subheader("🩺 Health Body Map")
        st.caption("แสดงภาพรวมผลกระทบของสุขภาพต่อร่างกายในส่วนต่างๆ")
        
        alerts = {}
        if get_float('SBP', person_data) and get_float('SBP', person_data) >= 140:
            alerts['หัวใจ'] = ('ความดันโลหิตสูง', 'red')
        if get_float('SGPT', person_data) and get_float('SGPT', person_data) > 41:
            alerts['ตับ'] = ('ค่าเอนไซม์ตับสูง', 'orange')
        if get_float('GFR', person_data) and get_float('GFR', person_data) < 60:
            alerts['ไต'] = ('การทำงานของไตลดลง', 'orange')
        if get_float('FVC เปอร์เซ็นต์', person_data) and get_float('FVC เปอร์เซ็นต์', person_data) < 80:
             alerts['ปอด'] = ('ความจุปอดอาจลดลง', 'lightblue')
        summary_r = person_data.get('ผลตรวจการได้ยินหูขวา', '')
        if "ผิดปกติ" in summary_r:
             alerts['หู'] = ('การได้ยินผิดปกติ', 'purple')

        body_map_html = f"""
        <div style="position: relative; width: 100%; max-width: 250px; margin: auto; text-align: center;">
            <svg viewBox="0 0 200 400" xmlns="http://www.w3.org/2000/svg">
                <path fill="#D3D3D3" d="M100 5C70 5 60 25 60 45s10 40 40 40 40-20 40-40-10-40-40-40zm-5 85c-20 0-35 10-35 30v100c0 20-10 70-10 90s-5 30 0 30h100c5 0 0-10 0-30s-10-70-10-90V120c0-20-15-30-35-30h-10z M45 250 c-10 0-15 20-15 40v60c0 10 5 20 15 20s15-10 15-20v-60c0-20-5-40-15-40zm110 0c-10 0-15 20-15 40v60c0 10 5 20 15 20s15-10 15-20v-60c0-20-5-40-15-40z"/>
            </svg>
            {'<div title="หัวใจ: {alerts['หัวใจ'][0]}" style="position: absolute; top: 35%; left: 48%; width: 15px; height: 15px; background: {alerts['หัวใจ'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'หัวใจ' in alerts else ''}
            {'<div title="ตับ: {alerts['ตับ'][0]}" style="position: absolute; top: 42%; left: 55%; width: 15px; height: 15px; background: {alerts['ตับ'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'ตับ' in alerts else ''}
            {'<div title="ไต: {alerts['ไต'][0]}" style="position: absolute; top: 48%; left: 38%; width: 15px; height: 15px; background: {alerts['ไต'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'ไต' in alerts else ''}
            {'<div title="ปอด: {alerts['ปอด'][0]}" style="position: absolute; top: 33%; left: 35%; width: 15px; height: 15px; background: {alerts['ปอด'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'ปอด' in alerts else ''}
            {'<div title="หู: {alerts['หู'][0]}" style="position: absolute; top: 15%; left: 25%; width: 15px; height: 15px; background: {alerts['หู'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'หู' in alerts else ''}
        </div>
        <div style="text-align: left; font-size: 0.8rem; margin-top: 1rem;">
            <b>คำอธิบาย:</b>
            <ul style="padding-left: 20px; margin-top: 5px;">
            {'<li><span style="color:red;"><b>หัวใจ:</b></span> {alerts['หัวใจ'][0]}</li>' if 'หัวใจ' in alerts else ''}
            {'<li><span style="color:orange;"><b>ตับ:</b></span> {alerts['ตับ'][0]}</li>' if 'ตับ' in alerts else ''}
            {'<li><span style="color:orange;"><b>ไต:</b></span> {alerts['ไต'][0]}</li>' if 'ไต' in alerts else ''}
            {'<li><span style="color:lightblue;"><b>ปอด:</b></span> {alerts['ปอด'][0]}</li>' if 'ปอด' in alerts else ''}
            {'<li><span style="color:purple;"><b>หู:</b></span> {alerts['หู'][0]}</li>' if 'หู' in alerts else ''}
            </ul>
            {'' if alerts else '<p>ไม่พบความผิดปกติที่สำคัญในร่างกาย</p>'}
        </div>
        """
        st.markdown(body_map_html, unsafe_allow_html=True)

# --- ฟังก์ชันแสดงกราฟเดิม ---
def plot_historical_trends(history_df):
    if history_df.shape[0] < 2:
        st.info("ข้อมูลย้อนหลังไม่เพียงพอ (ต้องการอย่างน้อย 2 ปี)")
        return
    history_df = history_df.sort_values(by="Year", ascending=True).copy()
    min_year, max_year = int(history_df['Year'].min()), int(history_df['Year'].max())
    all_years_df = pd.DataFrame({'Year': range(min_year, max_year + 1)})
    history_df = pd.merge(all_years_df, history_df, on='Year', how='left')
    history_df['BMI'] = history_df.apply(lambda row: (get_float('น้ำหนัก', row) / ((get_float('ส่วนสูง', row) / 100) ** 2)) if get_float('น้ำหนัก', row) and get_float('ส่วนสูง', row) else np.nan, axis=1)
    history_df['Year'] = history_df['Year'].astype(str)
    metric_bands = {'BMI': {"โรคอ้วน": (25, 40, "lightcoral"),"ท้วม": (23, 25, "yellow"),"ปกติ": (18.5, 23, "lightgreen")},'FBS': {"เข้าเกณฑ์เบาหวาน": (126, 200, "lightcoral"),"ภาวะเสี่ยง": (100, 126, "yellow"),"ปกติ": (70, 100, "lightgreen")},'CHOL': {"สูง": (240, 400, "lightcoral"),"เริ่มสูง": (200, 240, "yellow"),"ปกติ": (100, 200, "lightgreen")},'GFR': {"ปกติ": (90, 150, "lightgreen"),"เริ่มเสื่อม": (60, 90, "yellow"),"เสื่อมปานกลาง": (30, 60, "orange"),"เสื่อมรุนแรง": (0, 30, "lightcoral")},'DBP': {},'SBP': {"สูงมาก (ระดับ 2)": (140, 180, "lightcoral"),"สูง (ระดับ 1)": (130, 140, "orange"),"เริ่มสูง": (120, 130, "yellow"),"ปกติ": (90, 120, "lightgreen")}}
    trend_metrics = {'ดัชนีมวลกาย (BMI)': ('BMI', 'kg/m²'),'ระดับน้ำตาลในเลือด (FBS)': ('FBS', 'mg/dL'),'คอเลสเตอรอล (Cholesterol)': ('CHOL', 'mg/dL'),'ประสิทธิภาพการกรองของไต (GFR)': ('GFR', 'mL/min'),'ความดันโลหิต': (['SBP', 'DBP'], 'mmHg')}
    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2, col1]
    for i, (title, (keys, unit)) in enumerate(trend_metrics.items()):
        with cols[i]:
            fig = None
            bands_key = ''
            if isinstance(keys, list):
                df_plot = history_df[['Year', keys[0], keys[1]]]
                fig = px.line(df_plot, x='Year', y=keys, title=title, markers=True)
                bands_key = 'SBP'
                fig.update_layout(yaxis_range=[80,180])
            else:
                df_plot = history_df[['Year', keys]]
                fig = px.line(df_plot, x='Year', y=keys, title=title, markers=True)
                bands_key = keys
            if fig.layout.yaxis.range is None:
                if bands_key in metric_bands and metric_bands[bands_key]:
                    min_range = min(start for start, end, color in metric_bands[bands_key].values())
                    max_range = max(end for start, end, color in metric_bands[bands_key].values())
                    padding = (max_range - min_range) * 0.1
                    fig.update_layout(yaxis_range=[min_range - padding, max_range + padding])
            if bands_key in metric_bands and fig.layout.yaxis.range is not None:
                for name, (start, end, color) in metric_bands[bands_key].items():
                    fig.add_shape(type="rect", xref="paper", yref="y", x0=0, y0=start, x1=1, y1=end,fillcolor=color, opacity=0.2, layer="below", line_width=0)
                    if abs(end - start) > (fig.layout.yaxis.range[1] - fig.layout.yaxis.range[0]) * 0.1:
                         fig.add_annotation(x=0.98, y=(start+end)/2, text=name, showarrow=False,xref="paper", yref="y", font=dict(size=10, family="Sarabun"),xanchor="right")
            fig.update_traces(connectgaps=False)
            fig.update_layout(yaxis_title=unit, xaxis_title='ปี พ.ศ.', legend_title_text='เส้นเลือด' if isinstance(keys, list) else "",font_family="Sarabun",template="streamlit")
            st.plotly_chart(fig, use_container_width=True)

def plot_gauge_charts(person_data):
    st.caption("เกจวัดนี้แสดงค่าสุขภาพที่สำคัญเทียบกับเกณฑ์มาตรฐาน สีเขียวหมายถึงปกติ และจะเปลี่ยนเป็นสีเหลือง ส้ม แดง เมื่อมีความเสี่ยงเพิ่มขึ้น")
    col1, col2, col3 = st.columns(3)
    with col1:
        bmi = get_float('BMI', person_data)
        if bmi is None:
             weight = get_float('น้ำหนัก', person_data)
             height = get_float('ส่วนสูง', person_data)
             if weight and height: bmi = weight / ((height/100)**2)
        if bmi is not None:
            fig = go.Figure(go.Indicator(mode = "gauge+number",value = bmi,title = {'text': "ดัชนีมวลกาย (BMI)"},gauge = {'axis': {'range': [15, 40]},'steps' : [{'range': [15, 18.5], 'color': "lightblue"},{'range': [18.5, 23], 'color': "green"},{'range': [23, 25], 'color': "yellow"},{'range': [25, 30], 'color': "orange"},{'range': [30, 40], 'color': "red"}],'bar': {'color': "darkblue"}}))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        fbs = get_float('FBS', person_data)
        if fbs is not None:
            fig = go.Figure(go.Indicator(mode = "gauge+number",value = fbs,title = {'text': "ระดับน้ำตาล (FBS mg/dL)"},gauge = {'axis': {'range': [60, 160]},'steps' : [{'range': [60, 74], 'color': "yellow"},{'range': [74, 100], 'color': "green"},{'range': [100, 126], 'color': "orange"},{'range': [126, 160], 'color': "red"}],'bar': {'color': "darkblue"}}))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)
    with col3:
        gfr = get_float('GFR', person_data)
        if gfr is not None:
            fig = go.Figure(go.Indicator(mode = "gauge+number",value = gfr,title = {'text': "การกรองของไต (GFR mL/min)"},gauge = {'axis': {'range': [0, 120]},'steps' : [{'range': [0, 30], 'color': "red"},{'range': [30, 60], 'color': "orange"},{'range': [60, 90], 'color': "yellow"},{'range': [90, 120], 'color': "green"}],'bar': {'color': "darkblue"}}))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)

def plot_risk_radar(person_data):
    st.caption("กราฟนี้สรุปปัจจัยเสี่ยง 5 ด้าน ยิ่งพื้นที่สีกว้างและเบ้ไปทางขอบนอก หมายถึงความเสี่ยงโดยรวมสูงขึ้น (ระดับ 1 คือปกติ, 5 คือเสี่ยงสูงมาก)")
    def normalize(value, thresholds, higher_is_better=False):
        if value is None: return 1
        if higher_is_better:
            thresholds = thresholds[::-1]
            for i, threshold in enumerate(thresholds):
                if value >= threshold: return i + 1
            return len(thresholds) + 1
        else:
            for i, threshold in enumerate(thresholds):
                if value <= threshold: return i + 1
            return len(thresholds) + 1
    bmi = get_float('BMI', person_data)
    if bmi is None:
        weight = get_float('น้ำหนัก', person_data)
        height = get_float('ส่วนสูง', person_data)
        if weight and height: bmi = weight / ((height/100)**2)
    categories = ['BMI', 'ความดัน (SBP)', 'น้ำตาล (FBS)', 'ไขมัน (LDL)', 'ไต (GFR)']
    values = [normalize(bmi, [22.9, 24.9, 29.9, 35]), normalize(get_float('SBP', person_data), [120, 130, 140, 160]), normalize(get_float('FBS', person_data), [99, 125, 150, 200]), normalize(get_float('LDL', person_data), [129, 159, 189, 220]), normalize(get_float('GFR', person_data), [30, 45, 60, 90], higher_is_better=True)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values,theta=categories,fill='toself',name='ระดับความเสี่ยง'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[1, 5],tickvals=[1, 2, 3, 4, 5],ticktext=['ปกติ', 'เริ่มเสี่ยง', 'เสี่ยง', 'สูง', 'สูงมาก'])),showlegend=False,title="ภาพรวมปัจจัยเสี่ยงโรคไม่ติดต่อเรื้อรัง (NCDs)",font_family="Sarabun",template="streamlit")
    st.plotly_chart(fig, use_container_width=True)

def plot_audiogram(person_data):
    freq_cols = {'500': ('R500', 'L500'), '1000': ('R1k', 'L1k'), '2000': ('R2k', 'L2k'), '3000': ('R3k', 'L3k'), '4000': ('R4k', 'L4k'), '6000': ('R6k', 'L6k'), '8000': ('R8k', 'L8k')}
    freqs = list(freq_cols.keys())
    r_vals = [get_float(freq_cols[f][0], person_data) for f in freqs]
    l_vals = [get_float(freq_cols[f][1], person_data) for f in freqs]
    if all(v is None for v in r_vals) and all(v is None for v in l_vals):
        st.info("ไม่มีข้อมูลการตรวจการได้ยินแบบ Audiogram")
        return
    fig = go.Figure()
    levels = {"ปกติ": (0, 25, "lightgreen"),"เล็กน้อย": (25, 40, "yellow"),"ปานกลาง": (40, 70, "orange"),"รุนแรง": (70, 120, "lightcoral")}
    for name, (start, end, color) in levels.items():
        fig.add_shape(type="rect", xref="paper", yref="y", x0=0, y0=start, x1=1, y1=end,fillcolor=color, opacity=0.2, layer="below", line_width=0)
        fig.add_annotation(x=0.98, y=(start+end)/2, text=name, showarrow=False,xref="paper", yref="y", font=dict(size=10, family="Sarabun"))
    fig.add_trace(go.Scatter(x=freqs, y=r_vals, mode='lines+markers', name='หูขวา (Right)',line=dict(color='red'), marker=dict(symbol='circle-open', size=12, line=dict(width=2))))
    fig.add_trace(go.Scatter(x=freqs, y=l_vals, mode='lines+markers', name='หูซ้าย (Left)',line=dict(color='blue'), marker=dict(symbol='x-thin', size=12, line=dict(width=2))))
    fig.update_layout(title='ผลการตรวจเทียบกับระดับการสูญเสียการได้ยิน',xaxis_title='ความถี่เสียง (Hz)',yaxis_title='ระดับการได้ยิน (dB HL)',yaxis=dict(autorange='reversed', range=[-10, 120]),xaxis=dict(type='category'),legend=dict(x=0.01, y=0.99, bordercolor="black", borderwidth=1),template="streamlit",margin=dict(l=20, r=20, t=40, b=20),font_family="Sarabun")
    st.plotly_chart(fig, use_container_width=True)

def plot_lung_comparison(person_data):
    fvc_actual = get_float('FVC', person_data)
    fvc_pred = get_float('FVC predic', person_data)
    fev1_actual = get_float('FEV1', person_data)
    fev1_pred = get_float('FEV1 predic', person_data)
    if fvc_actual is None or fev1_actual is None:
        st.info("ไม่มีข้อมูลการตรวจสมรรถภาพปอด")
        return
    categories = ['FVC (L)', 'FEV1 (L)']
    actual_vals = [fvc_actual, fev1_actual]
    pred_vals = [fvc_pred, fev1_pred]
    fig = go.Figure(data=[go.Bar(name='ค่าที่วัดได้ (Actual)', x=categories, y=actual_vals, text=actual_vals, textposition='auto'),go.Bar(name='ค่ามาตรฐาน (Predicted)', x=categories, y=pred_vals, text=pred_vals, textposition='auto')])
    fig.update_traces(texttemplate='%{text:.2f}')
    fig.update_layout(barmode='group',title='เปรียบเทียบค่าสมรรถภาพปอดกับค่ามาตรฐาน',yaxis_title='ลิตร (L)',legend_title="ค่า",legend=dict(x=0.01, y=0.99),font_family="Sarabun",template="streamlit")
    st.plotly_chart(fig, use_container_width=True)

# --- END: โค้ดจาก visualization.py ---

def flag(val, low=None, high=None, higher_is_better=False):
    """Formats a lab value and flags it if it's abnormal."""
    try:
        val = float(str(val).replace(",", "").strip())
    except: return "-", False
    formatted_val = f"{int(val):,}" if val == int(val) else f"{val:,.1f}"
    is_abnormal = False
    if higher_is_better:
        if low is not None and val < low: is_abnormal = True
    else:
        if low is not None and val < low: is_abnormal = True
        if high is not None and val > high: is_abnormal = True
    return formatted_val, is_abnormal

def render_section_header(title):
    """Renders a new, modern section header."""
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)

def render_lab_table_html(title, headers, rows, table_class="lab-table"):
    """Generates HTML for a lab result table with a new header style."""
    header_html = f"<h5 class='section-subtitle'>{title}</h5>"
    html_content = f"{header_html}<div class='table-container'><table class='{table_class}'><colgroup><col style='width:40%;'><col style='width:20%;'><col style='width:40%;'></colgroup><thead><tr>"
    for i, h in enumerate(headers):
        align = "left" if i in [0, 2] else "center"
        html_content += f"<th style='text-align: {align};'>{h}</th>"
    html_content += "</tr></thead><tbody>"
    for row in rows:
        is_abn = any(flag for _, flag in row)
        row_class = f"abnormal-row" if is_abn else ""
        html_content += f"<tr class='{row_class}'><td style='text-align: left;'>{row[0][0]}</td><td>{row[1][0]}</td><td style='text-align: left;'>{row[2][0]}</td></tr>"
    html_content += "</tbody></table></div>"
    return html_content

def safe_text(val): return "-" if str(val).strip().lower() in ["", "none", "nan", "-"] else str(val).strip()
def safe_value(val):
    val = str(val or "").strip()
    return "-" if val.lower() in ["", "nan", "none", "-"] else val

def parse_range_or_number(val):
    val = val.replace("cell/hpf", "").replace("cells/hpf", "").replace("cell", "").strip().lower()
    try:
        if "-" in val: return map(float, val.split("-"))
        else: num = float(val); return num, num
    except: return None, None

def interpret_rbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 2: return "ปกติ"
    if high <= 5: return "พบเม็ดเลือดแดงในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดแดงในปัสสาวะ"

def interpret_wbc(value):
    val = str(value or "").strip().lower()
    if val in ["-", "", "none", "nan"]: return "-"
    _, high = parse_range_or_number(val)
    if high is None: return value
    if high <= 5: return "ปกติ"
    if high <= 10: return "พบเม็ดเลือดขาวในปัสสาวะเล็กน้อย"
    return "พบเม็ดเลือดขาวในปัสสาวะ"

def is_urine_abnormal(test_name, value, normal_range):
    val = str(value or "").strip().lower()
    if val in ["", "-", "none", "nan", "null"]: return False
    if test_name == "กรด-ด่าง (pH)":
        try: return not (5.0 <= float(val) <= 8.0)
        except: return True
    if test_name == "ความถ่วงจำเพาะ (Sp.gr)":
        try: return not (1.003 <= float(val) <= 1.030)
        except: return True
    if test_name == "เม็ดเลือดแดง (RBC)": return "พบ" in interpret_rbc(val).lower()
    if test_name == "เม็ดเลือดขาว (WBC)": return "พบ" in interpret_wbc(val).lower()
    if test_name == "น้ำตาล (Sugar)": return val.lower() not in ["negative"]
    if test_name == "โปรตีน (Albumin)": return val.lower() not in ["negative", "trace"]
    if test_name == "สี (Colour)": return val not in ["yellow", "pale yellow", "colorless", "paleyellow", "light yellow"]
    return False

def render_urine_section(person_data, sex, year_selected):
    """Renders the urinalysis section and returns a summary."""
    urine_data = [("สี (Colour)", person_data.get("Color", "-"), "Yellow, Pale Yellow"), ("น้ำตาล (Sugar)", person_data.get("sugar", "-"), "Negative"), ("โปรตีน (Albumin)", person_data.get("Alb", "-"), "Negative, trace"), ("กรด-ด่าง (pH)", person_data.get("pH", "-"), "5.0 - 8.0"), ("ความถ่วงจำเพาะ (Sp.gr)", person_data.get("Spgr", "-"), "1.003 - 1.030"), ("เม็ดเลือดแดง (RBC)", person_data.get("RBC1", "-"), "0 - 2 cell/HPF"), ("เม็ดเลือดขาว (WBC)", person_data.get("WBC1", "-"), "0 - 5 cell/HPF"), ("เซลล์เยื่อบุผิว (Squam.epit.)", person_data.get("SQ-epi", "-"), "0 - 10 cell/HPF"), ("อื่นๆ", person_data.get("ORTER", "-"), "-")]
    df_urine = pd.DataFrame(urine_data, columns=["การตรวจ", "ผลตรวจ", "ค่าปกติ"])
    html_content = render_lab_table_html("ผลการตรวจปัสสาวะ (Urinalysis)", ["การตรวจ", "ผล", "ค่าปกติ"], [[(row["การตรวจ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (safe_value(row["ผลตรวจ"]), is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"])), (row["ค่าปกติ"], is_urine_abnormal(row["การตรวจ"], row["ผลตรวจ"], row["ค่าปกติ"]))] for _, row in df_urine.iterrows()], table_class="lab-table")
    st.markdown(html_content, unsafe_allow_html=True)
    return any(not is_empty(val) for _, val, _ in urine_data)

def interpret_stool_exam(val):
    """Interprets stool examination results."""
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจ"
    val_lower = str(val).strip().lower()
    if val_lower == "normal": return "ไม่พบเม็ดเลือดขาวในอุจจาระ ถือว่าปกติ"
    if "wbc" in val_lower or "เม็ดเลือดขาว" in val_lower: return "พบเม็ดเลือดขาวในอุจจาระ นัดตรวจซ้ำ"
    return val
def interpret_stool_cs(value):
    """Interprets stool culture and sensitivity results."""
    if is_empty(value): return "ไม่ได้เข้ารับการตรวจ"
    val_strip = str(value).strip()
    if "ไม่พบ" in val_strip or "ปกติ" in val_strip: return "ไม่พบการติดเชื้อ"
    return "พบการติดเชื้อในอุจจาระ ให้พบแพทย์เพื่อตรวจรักษาเพิ่มเติม"

def render_stool_html_table(exam, cs):
    """Renders a self-contained HTML table for stool examination results."""
    html_content = f"""
    <div class="table-container">
        <table class="info-detail-table">
            <tbody>
                <tr>
                    <th>ผลตรวจอุจจาระทั่วไป</th>
                    <td>{exam}</td>
                </tr>
                <tr>
                    <th>ผลตรวจอุจจาระเพาะเชื้อ</th>
                    <td>{cs}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    return html_content

def get_ekg_col_name(year):
    """Gets the correct EKG column name based on the year."""
    return "EKG" if year == datetime.now().year + 543 else f"EKG{str(year)[-2:]}"
def interpret_ekg(val):
    """Interprets EKG results."""
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจคลื่นไฟฟ้าหัวใจ"
    if any(x in val.lower() for x in ["ผิดปกติ", "abnormal", "arrhythmia"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

# --- START OF FIX ---
def hepatitis_b_advice(hbsag, hbsab, hbcab):
    """Generates advice based on Hepatitis B panel results and returns a status."""
    hbsag, hbsab, hbcab = hbsag.lower(), hbsab.lower(), hbcab.lower()
    if "positive" in hbsag:
        return "ติดเชื้อไวรัสตับอักเสบบี", "infection"
    if "positive" in hbsab and "positive" not in hbsag:
        return "มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี", "immune"
    if "positive" in hbcab and "positive" not in hbsab:
        return "เคยติดเชื้อแต่ไม่มีภูมิคุ้มกันในปัจจุบัน", "unclear"
    if all(x == "negative" for x in [hbsag, hbsab, hbcab]):
        return "ไม่มีภูมิคุ้มกันต่อไวรัสตับอักเสบบี ควรปรึกษาแพทย์เพื่อรับวัคซีน", "no_immune"
    return "ไม่สามารถสรุปผลชัดเจน แนะนำให้พบแพทย์เพื่อประเมินซ้ำ", "unclear"
# --- END OF FIX ---

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_sqlite_data():
    tmp_path = None
    try:
        file_id = "1HruO9AMrUfniC8hBWtumVdxLJayEc1Xr"
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        conn = sqlite3.connect(tmp_path)
        df_loaded = pd.read_sql("SELECT * FROM health_data", conn)
        conn.close()
        
        df_loaded.columns = df_loaded.columns.str.strip()
        
        def clean_hn(hn_val):
            if pd.isna(hn_val): return ""
            s_val = str(hn_val).strip()
            if s_val.endswith('.0'): return s_val[:-2]
            return s_val
            
        df_loaded['HN'] = df_loaded['HN'].apply(clean_hn)
        
        df_loaded['ชื่อ-สกุล'] = df_loaded['ชื่อ-สกุล'].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
        df_loaded['เลขบัตรประชาชน'] = df_loaded['เลขบัตรประชาชน'].astype(str).str.strip()
        df_loaded['Year'] = df_loaded['Year'].astype(int)
        df_loaded['วันที่ตรวจ'] = df_loaded['วันที่ตรวจ'].astype(str).str.strip().replace('nan', '')
        return df_loaded
    except Exception as e:
        st.error(f"❌ โหลดฐานข้อมูลไม่สำเร็จ: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Data Availability Checkers ---
def has_basic_health_data(person_data):
    key_indicators = ['FBS', 'CHOL', 'HCT', 'Cr', 'WBC (cumm)', 'น้ำหนัก', 'ส่วนสูง', 'SBP']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

def has_vision_data(person_data):
    detailed_keys = [
        'ป.การรวมภาพ', 'ผ.การรวมภาพ', 'ป.ความชัดของภาพระยะไกล', 'ผ.ความชัดของภาพระยะไกล',
        'การมองภาพระยะไกลด้วยตาขวา(Far vision – Right)', 'การมองภาพระยะไกลด้วยตาซ้าย(Far vision –Left)',
        'ป.การกะระยะและมองความชัดลึกของภาพ', 'ผ.การกะระยะและมองความชัดลึกของภาพ', 'ป.การจำแนกสี', 'ผ.การจำแนกสี',
        'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน',
        'ป.ความชัดของภาพระยะใกล้', 'ผ.ความชัดของภาพระยะใกล้', 'การมองภาพระยะใกล้ด้วยตาขวา (Near vision – Right)',
        'การมองภาพระยะใกล้ด้วยตาซ้าย (Near vision – Left)', 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน',
        'ป.ลานสายตา', 'ผ.ลานสายตา', 'ผ.สายตาเขซ่อนเร้น'
    ]
    return any(not is_empty(person_data.get(key)) for key in detailed_keys)

def has_hearing_data(person_data):
    hearing_keys = [ 'R500', 'L500', 'R1k', 'L1k', 'R4k', 'L4k' ]
    return any(not is_empty(person_data.get(key)) for key in hearing_keys)

def has_lung_data(person_data):
    key_indicators = ['FVC เปอร์เซ็นต์', 'FEV1เปอร์เซ็นต์', 'FEV1/FVC%']
    return any(not is_empty(person_data.get(key)) for key in key_indicators)

# --- START OF CHANGE: Add check for visualization data ---
def has_visualization_data(history_df):
    """Check if there is enough data to show visualizations (at least 1 year)."""
    return history_df is not None and not history_df.empty
# --- END OF CHANGE ---

# --- UI and Report Rendering Functions ---
def interpret_bp(sbp, dbp):
    """Interprets blood pressure readings."""
    try:
        sbp, dbp = float(sbp), float(dbp)
        if sbp == 0 or dbp == 0: return "-"
        if sbp >= 160 or dbp >= 100: return "ความดันสูง"
        if sbp >= 140 or dbp >= 90: return "ความดันสูงเล็กน้อย"
        if sbp < 120 and dbp < 80: return "ความดันปกติ"
        return "ความดันค่อนข้างสูง"
    except: return "-"
    
def interpret_cxr(val):
    val = str(val or "").strip()
    if is_empty(val): return "ไม่ได้เข้ารับการตรวจเอกซเรย์"
    if any(keyword in val.lower() for keyword in ["ผิดปกติ", "ฝ้า", "รอย", "abnormal", "infiltrate", "lesion"]): return f"{val} ⚠️ กรุณาพบแพทย์เพื่อตรวจเพิ่มเติม"
    return val

# --- START OF CHANGE: New function to interpret BMI with updated terminology ---
def interpret_bmi(bmi):
    """Interprets BMI value and returns a description string."""
    if bmi is None:
        return ""
    if bmi < 18.5:
        return "น้ำหนักน้อยกว่าเกณฑ์"
    elif 18.5 <= bmi < 23:
        return "น้ำหนักปกติ"
    elif 23 <= bmi < 25:
        return "น้ำหนักเกิน (ท้วม)"
    elif 25 <= bmi < 30:
        return "เข้าเกณฑ์โรคอ้วน"
    elif bmi >= 30:
        return "เข้าเกณฑ์โรคอ้วนอันตราย"
    return ""
# --- END OF CHANGE ---

# --- START OF CHANGE: New Header and Vitals Design ---
def display_common_header(person_data):
    """Displays the new report header with integrated personal info and vitals cards."""
    
    # --- Prepare data for display ---
    name = person_data.get('ชื่อ-สกุล', '-')
    age = str(int(float(person_data.get('อายุ')))) if str(person_data.get('อายุ')).replace('.', '', 1).isdigit() else person_data.get('อายุ', '-')
    sex = person_data.get('เพศ', '-')
    hn = str(int(float(person_data.get('HN')))) if str(person_data.get('HN')).replace('.', '', 1).isdigit() else person_data.get('HN', '-')
    department = person_data.get('หน่วยงาน', '-')
    check_date = person_data.get("วันที่ตรวจ", "-")
    
    try:
        sbp_int, dbp_int = int(float(person_data.get("SBP", ""))), int(float(person_data.get("DBP", "")))
        bp_val = f"{sbp_int}/{dbp_int}"
        bp_desc = interpret_bp(sbp_int, dbp_int)
    except: 
        bp_val = "-"
        bp_desc = "ไม่มีข้อมูล"
    
    try: pulse_val = f"{int(float(person_data.get('pulse', '-')))}"
    except: pulse_val = "-"

    weight = get_float('น้ำหนัก', person_data)
    height = get_float('ส่วนสูง', person_data)
    weight_val = f"{weight}" if weight is not None else "-"
    height_val = f"{height}" if height is not None else "-"
    waist_val = f"{person_data.get('รอบเอว', '-')}"

    # --- BMI Calculation and Interpretation ---
    bmi_val_str = "-"
    bmi_desc = ""
    if weight is not None and height is not None and height > 0:
        bmi = weight / ((height / 100) ** 2)
        bmi_val_str = f"{bmi:.1f} kg/m²"
        bmi_desc = interpret_bmi(bmi)


    # --- Render HTML ---
    st.markdown(f"""
    <div class="report-header">
        <div class="header-left">
            <h2>รายงานผลการตรวจสุขภาพ</h2>
            <p>คลินิกตรวจสุขภาพ กลุ่มงานอาชีวเวชกรรม โรงพยาบาลสันทราย</p>
            <p>ติดต่อกลุ่มงานอาชีวเวชกรรม โทร 053 921 199 ต่อ 167</p>
        </div>
        <div class="header-right">
            <div class="info-card">
                <div class="info-card-item"><span>ชื่อ-สกุล:</span> {name}</div>
                <div class="info-card-item"><span>HN:</span> {hn}</div>
                <div class="info-card-item"><span>อายุ:</span> {age} ปี</div>
                <div class="info-card-item"><span>เพศ:</span> {sex}</div>
                <div class="info-card-item"><span>หน่วยงาน:</span> {department}</div>
                <div class="info-card-item"><span>วันที่ตรวจ:</span> {check_date}</div>
            </div>
        </div>
    </div>

    <div class="vitals-grid">
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">น้ำหนัก / ส่วนสูง</span>
                <span class="vital-value">{weight_val} kg / {height_val} cm</span>
                <span class="vital-sub-value">BMI: {bmi_val_str} ({bmi_desc})</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="M12 6v6l4 2"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">รอบเอว</span>
                <span class="vital-value">{waist_val} cm</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">ความดัน (mmHg)</span>
                <span class="vital-value">{bp_val}</span>
                <span class="vital-sub-value">{bp_desc}</span>
            </div>
        </div>
        <div class="vital-card">
            <div class="vital-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            </div>
            <div class="vital-data">
                <span class="vital-label">ชีพจร (BPM)</span>
                <span class="vital-value">{pulse_val}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- END OF CHANGE ---

# --- START OF CHANGE: New Centralized and Adaptive CSS ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        /* --- Color Variables for Consistency --- */
        :root {
            --abnormal-bg-color: rgba(220, 53, 69, 0.1);
            --abnormal-text-color: #C53030;
            --normal-bg-color: rgba(40, 167, 69, 0.1);
            --normal-text-color: #1E4620;
            --warning-bg-color: rgba(255, 193, 7, 0.1);
            --neutral-bg-color: rgba(108, 117, 125, 0.1);
            --neutral-text-color: #4A5568;
        }
        
        /* --- General & Typography --- */
        html, body, [class*="st-"], .st-emotion-cache-10trblm, h1, h2, h3, h4, h5, h6 {
            font-family: 'Sarabun', sans-serif !important; 
        }
        .main {
             background-color: var(--background-color);
             color: var(--text-color);
        }
        h4 { /* For section headers */
            font-size: 1.25rem;
            font-weight: 600;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            margin-top: 40px;
            margin-bottom: 24px;
            color: var(--text-color);
        }
        h5.section-subtitle {
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--text-color);
            opacity: 0.7;
        }

        /* --- Sidebar Controls --- */
        [data-testid="stSidebar"] {
            background-color: var(--secondary-background-color);
        }
        [data-testid="stSidebar"] .stTextInput input {
            border-color: var(--border-color);
        }
        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 1rem;
        }
        /* --- START OF FIX --- */
        .stButton>button {
            background-color: #00796B; /* Use the same teal as section headers */
            color: white !important;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            width: 100%;
            padding: 0.5rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            transition: background-color 0.2s, transform 0.2s;
        }
        .stButton>button:hover {
            background-color: #00695C; /* A slightly darker teal for hover */
            color: white !important;
            transform: translateY(-1px);
        }
        .stButton>button:disabled {
            background-color: #BDBDBD;
            color: #757575 !important;
            opacity: 1;
            border: none;
            box-shadow: none;
            cursor: not-allowed;
        }
        /* --- END OF FIX --- */


        /* --- New Report Header & Vitals --- */
        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2rem;
        }
        .header-left h2 { color: var(--text-color); font-size: 2rem; margin-bottom: 0.25rem;}
        .header-left p { color: var(--text-color); opacity: 0.7; margin: 0; }
        .info-card {
            background-color: var(--secondary-background-color);
            border-radius: 8px;
            padding: 1rem;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem 1.5rem;
            min-width: 400px;
            border: 1px solid var(--border-color);
        }
        .info-card-item { font-size: 0.9rem; color: var(--text-color); }
        .info-card-item span { color: var(--text-color); opacity: 0.7; margin-right: 8px; }

        .vitals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .vital-card {
            background-color: var(--secondary-background-color);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        .vital-icon svg { color: var(--primary-color); }
        .vital-data { display: flex; flex-direction: column; }
        .vital-label { font-size: 0.8rem; color: var(--text-color); opacity: 0.7; }
        .vital-value { font-size: 1.2rem; font-weight: 700; color: var(--text-color); line-height: 1.2; white-space: nowrap;}
        .vital-sub-value { font-size: 0.8rem; color: var(--text-color); opacity: 0.6; }

        /* --- Styled Tabs --- */
        div[data-testid="stTabs"] {
            border-bottom: 2px solid var(--border-color);
        }
        div[data-testid="stTabs"] button {
            background-color: transparent;
            color: var(--text-color);
            opacity: 0.7;
            border-radius: 8px 8px 0 0;
            margin: 0;
            padding: 10px 20px;
            border: none;
            border-bottom: 2px solid transparent;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background-color: var(--secondary-background-color);
            color: var(--primary-color);
            font-weight: 600;
            opacity: 1;
            border: 2px solid var(--border-color);
            border-bottom: 2px solid var(--secondary-background-color);
            margin-bottom: -2px;
        }
        
        /* --- Containers for sections --- */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div.st-emotion-cache-1jicfl2.e1f1d6gn3 > div {
             background-color: var(--secondary-background-color);
             border: 1px solid var(--border-color);
             border-radius: 12px;
             padding: 24px;
             box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }

        /* --- Lab Result Tables --- */
        .table-container { overflow-x: auto; }
        .lab-table, .info-detail-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .lab-table th, .lab-table td, .info-detail-table th, .info-detail-table td {
            padding: 12px 15px;
            border: 1px solid transparent;
            border-bottom: 1px solid var(--border-color);
        }
        .lab-table th, .info-detail-table th {
            font-weight: 600;
            text-align: left;
            color: var(--text-color);
            opacity: 0.7;
        }
        .lab-table thead th {
            background-color: rgba(128, 128, 128, 0.1);
        }
        .lab-table td:nth-child(2) {
            text-align: center;
        }
        .lab-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
        .lab-table .abnormal-row {
            background-color: var(--abnormal-bg-color);
            color: var(--abnormal-text-color);
            font-weight: 600;
        }
        .info-detail-table th { width: 35%; }
        
        /* --- Recommendation Container --- */
        .recommendation-container {
            border-left: 5px solid var(--primary-color);
            padding: 1.5rem;
            border-radius: 0 8px 8px 0;
            background-color: var(--background-color);
        }
        .recommendation-container ul { padding-left: 20px; }
        .recommendation-container li { margin-bottom: 0.5rem; }

        /* --- Performance Report Specific Styles --- */
        .status-summary-card {
            padding: 1rem; 
            border-radius: 8px; 
            text-align: center; 
            height: 100%;
        }
        .status-normal-bg { background-color: var(--normal-bg-color); }
        .status-abnormal-bg { background-color: var(--abnormal-bg-color); }
        .status-warning-bg { background-color: var(--warning-bg-color); }
        .status-neutral-bg { background-color: var(--neutral-bg-color); }

        .status-summary-card p {
            margin: 0;
            color: var(--text-color);
        }
        .vision-table {
            width: 100%; border-collapse: collapse; font-size: 14px;
            margin-top: 1.5rem;
        }
        .vision-table th, .vision-table td {
            border: 1px solid var(--border-color); padding: 10px;
            text-align: left; vertical-align: middle;
        }
        .vision-table th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; }
        .vision-table .result-cell { text-align: center; width: 180px; }
        .vision-result {
            display: inline-block; padding: 6px 16px; border-radius: 16px;
            font-size: 13px; font-weight: bold; border: 1px solid transparent;
        }
        /* --- START OF FIX --- */
        .vision-normal { background-color: var(--normal-bg-color); color: #2E7D32; }
        .vision-abnormal { background-color: var(--abnormal-bg-color); color: #C62828; }
        .vision-not-tested { background-color: var(--neutral-bg-color); color: #455A64; }
        /* --- END OF FIX --- */
        .styled-df-table {
            width: 100%; border-collapse: collapse; font-family: 'Sarabun', sans-serif !important;
            font-size: 14px;
        }
        .styled-df-table th, .styled-df-table td { border: 1px solid var(--border-color); padding: 10px; text-align: left; }
        .styled-df-table thead th { background-color: var(--secondary-background-color); opacity: 0.7; font-weight: bold; text-align: center; vertical-align: middle; }
        .styled-df-table tbody td { text-align: center; }
        .styled-df-table tbody td:first-child { text-align: left; }
        .styled-df-table tbody tr:hover { background-color: rgba(128, 128, 128, 0.1); }
        .hearing-table { table-layout: fixed; }
        
        /* --- START OF FIX --- */
        .custom-advice-box {
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            border: 1px solid transparent;
            font-weight: 600; /* Make text bolder */
        }
        .immune-box {
            background-color: var(--normal-bg-color);
            color: #2E7D32; /* Darker green for better contrast */
            border-color: rgba(40, 167, 69, 0.2);
        }
        .no-immune-box {
            background-color: var(--abnormal-bg-color);
            color: #C62828; /* Darker red for better contrast */
            border-color: rgba(220, 53, 69, 0.2);
        }
        .warning-box {
            background-color: var(--warning-bg-color);
            color: #AF6C00; /* Darker yellow/orange for better contrast */
            border-color: rgba(255, 193, 7, 0.2);
        }
        /* --- END OF FIX --- */
    </style>
    """, unsafe_allow_html=True)
# --- END OF CHANGE ---

def render_vision_details_table(person_data):
    """
    Renders a clearer, single-column result table for the vision test with corrected logic.
    """
    vision_tests = [
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
        {'display': '7. ความสมดุลกล้ามเนื้อตาแนวดิ่ง (Far vertical phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวตั้ง', 'related_keyword': 'แนวตั้งระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '8. ความสมดุลกล้ามเนื้อตาแนวนอน (Far lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะไกลแนวนอน', 'related_keyword': 'แนวนอนระยะไกล', 'outcomes': ['ปกติ', 'ผิดปกติ']},
        {'display': '12. ความสมดุลกล้ามเนื้อตาแนวนอน (Near lateral phoria)', 'type': 'phoria', 'normal_col': 'ปกติความสมดุลกล้ามเนื้อตาระยะใกล้แนวนอน', 'related_keyword': 'แนวนอนระยะใกล้', 'outcomes': ['ปกติ', 'ผิดปกติ']}
    ]

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

def display_performance_report_hearing(person_data, all_person_history_df):
    render_section_header("รายงานผลการตรวจสมรรถภาพการได้ยิน (Audiometry Report)")
    
    hearing_results = interpret_audiogram(person_data, all_person_history_df)

    if hearing_results['summary'].get('overall') == "ไม่ได้เข้ารับการตรวจ":
        st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพการได้ยินในปีนี้")
        return

    summary_r_raw = person_data.get('ผลตรวจการได้ยินหูขวา', 'N/A')
    summary_l_raw = person_data.get('ผลตรวจการได้ยินหูซ้าย', 'N/A')

    def get_summary_class(summary_text):
        if "ผิดปกติ" in summary_text:
            return "status-abnormal-bg"
        elif "ปกติ" in summary_text:
            return "status-normal-bg"
        elif "N/A" in summary_text or "ไม่ได้" in summary_text or is_empty(summary_text):
            return "status-neutral-bg"
        return "status-abnormal-bg"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="status-summary-card {get_summary_class(summary_r_raw)}">
            <p style="font-size: 1rem; font-weight: bold;">หูขวา (Right Ear)</p>
            <p style="font-size: 1.2rem; font-weight: bold; margin-top: 0.25rem;">{summary_r_raw}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="status-summary-card {get_summary_class(summary_l_raw)}">
            <p style="font-size: 1rem; font-weight: bold;">หูซ้าย (Left Ear)</p>
            <p style="font-size: 1.2rem; font-weight: bold; margin-top: 0.25rem;">{summary_l_raw}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    advice = hearing_results.get('advice', 'ไม่มีคำแนะนำเพิ่มเติม')
    st.warning(f"**คำแนะนำ:** {advice}")
    
    st.markdown("<hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)

    data_col, avg_col = st.columns([3, 2])
    
    with data_col:
        st.markdown("<h5 class='section-subtitle'>ผลการตรวจโดยละเอียด</h5>", unsafe_allow_html=True)
        has_baseline = hearing_results.get('baseline_source') != 'none'
        baseline_year = hearing_results.get('baseline_year')
        freq_order = ['500 Hz', '1000 Hz', '2000 Hz', '3000 Hz', '4000 Hz', '6000 Hz', '8000 Hz']
        
        tbody_html = ""
        for freq in freq_order:
            current = hearing_results.get('raw_values', {}).get(freq, {})
            r_val, l_val = current.get('right', '-'), current.get('left', '-')
            shift_r_text, shift_l_text = '-', '-'
            if has_baseline:
                shift = hearing_results.get('shift_values', {}).get(freq, {})
                shift_r, shift_l = shift.get('right'), shift.get('left')
                if shift_r is not None: shift_r_text = f"+{shift_r}" if shift_r > 0 else str(shift_r)
                if shift_l is not None: shift_l_text = f"+{shift_l}" if shift_l > 0 else str(shift_l)
            tbody_html += f"<tr><td style='text-align: left;'>{freq}</td><td>{r_val}</td><td>{l_val}</td><td>{shift_r_text}</td><td>{shift_l_text}</td></tr>"

        baseline_header_text = f" (พ.ศ. {baseline_year})" if has_baseline else " (ไม่มี Baseline)"
        
        full_table_html = f"""
        <table class="styled-df-table hearing-table">
            <thead>
                <tr>
                    <th rowspan="2" style="vertical-align: middle;">ความถี่ (Hz)</th>
                    <th colspan="2">ผลการตรวจปัจจุบัน (dB)</th>
                    <th colspan="2">การเปลี่ยนแปลงเทียบกับ Baseline{baseline_header_text}</th>
                </tr>
                <tr><th>หูขวา</th><th>หูซ้าย</th><th>Shift ขวา</th><th>Shift ซ้าย</th></tr>
            </thead>
            <tbody>{tbody_html}</tbody>
        </table>
        """
        st.markdown(full_table_html, unsafe_allow_html=True)

    with avg_col:
        st.markdown("<h5 class='section-subtitle'>ค่าเฉลี่ยการได้ยิน (dB)</h5>", unsafe_allow_html=True)
        averages = hearing_results.get('averages', {})
        avg_r_speech, avg_l_speech = averages.get('right_500_2000'), averages.get('left_500_2000')
        avg_r_high, avg_l_high = averages.get('right_3000_6000'), averages.get('left_3000_6000')
        st.markdown(f"""
        <div style='background-color: var(--secondary-background-color); padding: 1rem; border-radius: 8px; line-height: 1.8; height: 100%; border: 1px solid var(--border-color);'>
            <b>ความถี่เสียงพูด (500-2000 Hz):</b>
            <ul>
                <li>หูขวา: {f'{avg_r_speech:.1f}' if avg_r_speech is not None else 'N/A'}</li>
                <li>หูซ้าย: {f'{avg_l_speech:.1f}' if avg_l_speech is not None else 'N/A'}</li>
            </ul>
            <b>ความถี่สูง (3000-6000 Hz):</b>
            <ul>
                <li>หูขวา: {f'{avg_r_high:.1f}' if avg_r_high is not None else 'N/A'}</li>
                <li>หูซ้าย: {f'{avg_l_high:.1f}' if avg_l_high is not None else 'N/A'}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


def display_performance_report_lung(person_data):
    render_section_header("รายงานผลการตรวจสมรรถภาพปอด (Spirometry Report)")
    lung_summary, lung_advice, lung_raw_values = interpret_lung_capacity(person_data)

    if lung_summary == "ไม่ได้เข้ารับการตรวจ":
        st.warning("ไม่ได้เข้ารับการตรวจสมรรถภาพปอดในปีนี้")
        return

    main_col, side_col = st.columns([3, 2])

    with main_col:
        st.markdown("<h5 class='section-subtitle'>ตารางแสดงผลโดยละเอียด</h5>", unsafe_allow_html=True)
        
        def format_detail_val(key, format_spec, unit=""):
            val = lung_raw_values.get(key)
            if val is not None and isinstance(val, (int, float)):
                return f"{val:{format_spec}}{unit}"
            return "-"

        # --- START OF FIX ---
        # Build HTML string in a single f-string to prevent concatenation issues.
        table_html = f"""
        <table class="styled-df-table">
            <thead>
                <tr>
                    <th>การทดสอบ (Test)</th>
                    <th>ค่าที่วัดได้ (Actual)</th>
                    <th>ค่ามาตรฐาน (Predicted)</th>
                    <th>% เทียบค่ามาตรฐาน (% Pred)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>FVC</td>
                    <td>{format_detail_val('FVC', '.2f', ' L')}</td>
                    <td>{format_detail_val('FVC predic', '.2f', ' L')}</td>
                    <td>{format_detail_val('FVC %', '.1f', ' %')}</td>
                </tr>
                <tr>
                    <td>FEV1</td>
                    <td>{format_detail_val('FEV1', '.2f', ' L')}</td>
                    <td>{format_detail_val('FEV1 predic', '.2f', ' L')}</td>
                    <td>{format_detail_val('FEV1 %', '.1f', ' %')}</td>
                </tr>
                <tr>
                    <td>FEV1/FVC</td>
                    <td>{format_detail_val('FEV1/FVC %', '.1f', ' %')}</td>
                    <td>{format_detail_val('FEV1/FVC % pre', '.1f', ' %')}</td>
                    <td>-</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)
        # --- END OF FIX ---

    with side_col:
        st.markdown("<h5 class='section-subtitle'>ผลการแปลความหมาย</h5>", unsafe_allow_html=True)
        
        summary_class = "status-neutral-bg"
        if "ปกติ" in lung_summary:
            summary_class = "status-normal-bg"
        elif "ไม่ได้" not in lung_summary and "คลาดเคลื่อน" not in lung_summary:
            summary_class = "status-abnormal-bg"
        
        st.markdown(f"""
        <div class="status-summary-card {summary_class}">
             <p style="font-size: 1.2rem; font-weight: bold;">{lung_summary}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br><h5 class='section-subtitle'>คำแนะนำ</h5>", unsafe_allow_html=True)
        st.warning(lung_advice or "ไม่มีคำแนะนำเพิ่มเติม")

        st.markdown("<h5 class='section-subtitle'>ผลเอกซเรย์ทรวงอก</h5>", unsafe_allow_html=True)
        selected_year = person_data.get("Year")
        cxr_result_interpreted = "ไม่มีข้อมูล"
        if selected_year:
            cxr_col_name = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            cxr_result_interpreted = interpret_cxr(person_data.get(cxr_col_name, ''))
        
        st.markdown(f"""
        <div style='background-color: var(--secondary-background-color); padding: 1rem; border-radius: 8px; line-height: 1.8; border: 1px solid var(--border-color);'>
            {cxr_result_interpreted}
        </div>
        """, unsafe_allow_html=True)


def display_performance_report_vision(person_data):
    render_section_header("รายงานผลการตรวจสมรรถภาพการมองเห็น (Vision Test Report)")
    
    if not has_vision_data(person_data):
        st.warning("ไม่พบข้อมูลผลการตรวจสมรรถภาพการมองเห็นโดยละเอียดในปีนี้")
        vision_advice_summary = person_data.get('สรุปเหมาะสมกับงาน')
        doctor_advice = person_data.get('แนะนำABN EYE')
        if not is_empty(vision_advice_summary) or not is_empty(doctor_advice):
            st.info("หมายเหตุ: ข้อมูลสรุปที่แสดงอาจมาจากผลการตรวจในปีอื่น")
            if not is_empty(vision_advice_summary):
                summary_class = "status-normal-bg" if "เหมาะสม" in vision_advice_summary else "status-abnormal-bg"
                icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#28A745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>' if "เหมาะสม" in vision_advice_summary else '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#DC3545" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" x2="12" y1="8" y2="12"></line><line x1="12" x2="12.01" y1="16" y2="16"></line></svg>'
                title_color = "#28A745" if "เหมาะสม" in vision_advice_summary else "#DC3545"
                st.markdown(f"""
                 <div class='{summary_class}' style='border: 1px solid transparent; padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                    <div style='flex-shrink: 0;'>{icon_svg}</div>
                    <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: {title_color};'>สรุปความเหมาะสมกับงาน</h5><p style='margin:0;'>{vision_advice_summary}</p></div>
                 </div>""", unsafe_allow_html=True)

            if not is_empty(doctor_advice):
                 st.markdown(f"""
                 <div style='background-color: var(--warning-bg-color); border: 1px solid rgba(255, 193, 7, 0.2); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
                    <div style='flex-shrink: 0;'><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFC107" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg></div>
                    <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #FFC107;'>คำแนะนำเพิ่มเติมจากแพทย์</h5><p style='margin:0;'>{doctor_advice}</p></div>
                 </div>""", unsafe_allow_html=True)
        return

    vision_advice_summary = person_data.get('สรุปเหมาะสมกับงาน')
    if not is_empty(vision_advice_summary):
        summary_class = "status-normal-bg" if "เหมาะสม" in vision_advice_summary else "status-abnormal-bg"
        icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#28A745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>' if "เหมาะสม" in vision_advice_summary else '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#DC3545" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" x2="12" y1="8" y2="12"></line><line x1="12" x2="12.01" y1="16" y2="16"></line></svg>'
        title_color = "#28A745" if "เหมาะสม" in vision_advice_summary else "#DC3545"
        st.markdown(f"""
         <div class='{summary_class}' style='border: 1px solid transparent; padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
            <div style='flex-shrink: 0;'>{icon_svg}</div>
            <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: {title_color};'>สรุปความเหมาะสมกับงาน</h5><p style='margin:0;'>{vision_advice_summary}</p></div>
         </div>""", unsafe_allow_html=True)

    abnormality_fields = OrderedDict([('ผ.สายตาเขซ่อนเร้น', 'สายตาเขซ่อนเร้น'), ('ผ.การรวมภาพ', 'การรวมภาพ'), ('ผ.ความชัดของภาพระยะไกล', 'ความชัดของภาพระยะไกล'), ('ผ.การกะระยะและมองความชัดลึกของภาพ', 'การกะระยะ/ความชัดลึก'), ('ผ.การจำแนกสี', 'การจำแนกสี'), ('ผ.ความชัดของภาพระยะใกล้', 'ความชัดของภาพระยะใกล้'), ('ผ.ลานสายตา', 'ลานสายตา')])
    abnormal_topics = [name for col, name in abnormality_fields.items() if not is_empty(person_data.get(col))]
    doctor_advice = person_data.get('แนะนำABN EYE')

    if abnormal_topics or not is_empty(doctor_advice):
        summary_parts = []
        if abnormal_topics: summary_parts.append(f"<b>พบความผิดปกติเกี่ยวกับ:</b> {', '.join(abnormal_topics)}")
        if not is_empty(doctor_advice): summary_parts.append(f"<b>คำแนะนำเพิ่มเติมจากแพทย์:</b> {doctor_advice}")
        st.markdown(f"""
        <div style='background-color: var(--warning-bg-color); border: 1px solid rgba(255, 193, 7, 0.2); padding: 1.25rem; border-radius: 0.75rem; margin-top: 1rem; display: flex; align-items: flex-start; gap: 1rem;'>
            <div style='flex-shrink: 0;'><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFC107" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg></div>
            <div><h5 style='margin-top: 0; margin-bottom: 0.25rem; color: #FFC107;'>สรุปความผิดปกติและคำแนะนำ</h5><p style='margin:0;'>{"<br>".join(summary_parts)}</p></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)
    st.markdown("<h5 class='section-subtitle'>ผลการตรวจโดยละเอียด</h5>", unsafe_allow_html=True)
    st.markdown(render_vision_details_table(person_data), unsafe_allow_html=True)

def display_performance_report(person_data, report_type, all_person_history_df=None):
    with st.container(border=True):
        if report_type == 'lung':
            display_performance_report_lung(person_data)
        elif report_type == 'vision':
            display_performance_report_vision(person_data)
        elif report_type == 'hearing':
            display_performance_report_hearing(person_data, all_person_history_df)

def display_main_report(person_data, all_person_history_df):
    person = person_data
    sex = str(person.get("เพศ", "")).strip()
    if sex not in ["ชาย", "หญิง"]: sex = "ไม่ระบุ"
    hb_low, hct_low = (12, 36) if sex == "หญิง" else (13, 39)
    cbc_config = [("ฮีโมโกลบิน (Hb)", "Hb(%)", "ชาย > 13, หญิง > 12 g/dl", hb_low, None), ("ฮีมาโตคริต (Hct)", "HCT", "ชาย > 39%, หญิง > 36%", hct_low, None), ("เม็ดเลือดขาว (wbc)", "WBC (cumm)", "4,000 - 10,000 /cu.mm", 4000, 10000), ("นิวโทรฟิล (Neutrophil)", "Ne (%)", "43 - 70%", 43, 70), ("ลิมโฟไซต์ (Lymphocyte)", "Ly (%)", "20 - 44%", 20, 44), ("โมโนไซต์ (Monocyte)", "M", "3 - 9%", 3, 9), ("อีโอซิโนฟิล (Eosinophil)", "Eo", "0 - 9%", 0, 9), ("เบโซฟิล (Basophil)", "BA", "0 - 3%", 0, 3), ("เกล็ดเลือด (Platelet)", "Plt (/mm)", "150,000 - 500,000 /cu.mm", 150000, 500000)]
    cbc_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high in cbc_config for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high)]]
    
    blood_config = [("น้ำตาลในเลือด (FBS)", "FBS", "74 - 106 mg/dl", 74, 106), ("กรดยูริก (Uric Acid)", "Uric Acid", "2.6 - 7.2 mg%", 2.6, 7.2), ("การทำงานของเอนไซม์ตับ (ALK)", "ALP", "30 - 120 U/L", 30, 120), ("การทำงานของเอนไซม์ตับ (SGOT)", "SGOT", "< 37 U/L", None, 37), ("การทำงานของเอนไซม์ตับ (SGPT)", "SGPT", "< 41 U/L", None, 41), ("คลอเรสเตอรอล (CHOL)", "CHOL", "150 - 200 mg/dl", 150, 200), ("ไตรกลีเซอไรด์ (TGL)", "TGL", "35 - 150 mg/dl", 35, 150), ("ไขมันดี (HDL)", "HDL", "> 40 mg/dl", 40, None, True), ("ไขมันเลว (LDL)", "LDL", "0 - 160 mg/dl", 0, 160), ("การทำงานของไต (BUN)", "BUN", "7.9 - 20 mg/dl", 7.9, 20), ("การทำงานของไต (Cr)", "Cr", "0.5 - 1.17 mg/dl", 0.5, 1.17), ("ประสิทธิภาพการกรองของไต (GFR)", "GFR", "> 60 mL/min", 60, None, True)]
    blood_rows = [([(label, is_abn), (result, is_abn), (norm, is_abn)]) for label, col, norm, low, high, *opt in blood_config for higher in [opt[0] if opt else False] for val in [get_float(col, person)] for result, is_abn in [flag(val, low, high, higher)]]
    
    with st.container(border=True):
        render_section_header("ผลการตรวจทางห้องปฏิบัติการ (Laboratory Results)")
        col1, col2 = st.columns(2)
        with col1: st.markdown(render_lab_table_html("ผลตรวจความสมบูรณ์ของเม็ดเลือด (CBC)", ["การตรวจ", "ผล", "ค่าปกติ"], cbc_rows), unsafe_allow_html=True)
        with col2: st.markdown(render_lab_table_html("ผลตรวจเลือด (Blood Chemistry)", ["การตรวจ", "ผล", "ค่าปกติ"], blood_rows), unsafe_allow_html=True)
    
    selected_year = person.get("Year", datetime.now().year + 543)
    
    with st.container(border=True):
        render_section_header("ผลการตรวจอื่นๆ (Other Examinations)")
        col_ua_left, col_ua_right = st.columns(2)
        with col_ua_left:
            render_urine_section(person, sex, selected_year)
            st.markdown("<h5 class='section-subtitle'>ผลตรวจอุจจาระ (Stool Examination)</h5>", unsafe_allow_html=True)
            st.markdown(render_stool_html_table(interpret_stool_exam(person.get("Stool exam", "")), interpret_stool_cs(person.get("Stool C/S", ""))), unsafe_allow_html=True)

        with col_ua_right:
            st.markdown("<h5 class='section-subtitle'>ผลตรวจพิเศษ</h5>", unsafe_allow_html=True)
            cxr_col = f"CXR{str(selected_year)[-2:]}" if selected_year != (datetime.now().year + 543) else "CXR"
            ekg_col_name = get_ekg_col_name(selected_year)
            hep_a_value = person.get("Hepatitis A")
            hep_a_display_text = "ไม่ได้ตรวจ" if is_empty(hep_a_value) else safe_text(hep_a_value)

            st.markdown(f"""
            <div class="table-container">
                <table class="info-detail-table">
                    <tbody>
                        <tr><th>ผลเอกซเรย์ (Chest X-ray)</th><td>{interpret_cxr(person.get(cxr_col, ''))}</td></tr>
                        <tr><th>ผลคลื่นไฟฟ้าหัวใจ (EKG)</th><td>{interpret_ekg(person.get(ekg_col_name, ''))}</td></tr>
                        <tr><th>ไวรัสตับอักเสบเอ (Hepatitis A)</th><td>{hep_a_display_text}</td></tr>
                    </tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<h5 class='section-subtitle'>ผลการตรวจไวรัสตับอักเสบบี (Viral hepatitis B)</h5>", unsafe_allow_html=True)
            hbsag, hbsab, hbcab = safe_text(person.get("HbsAg")), safe_text(person.get("HbsAb")), safe_text(person.get("HBcAB"))
            st.markdown(f"""<div class="table-container"><table class='lab-table'>
                <thead><tr><th style='text-align: center;'>HBsAg</th><th style='text-align: center;'>HBsAb</th><th style='text-align: center;'>HBcAb</th></tr></thead>
                <tbody><tr><td style='text-align: center;'>{hbsag}</td><td style='text-align: center;'>{hbsab}</td><td style='text-align: center;'>{hbcab}</td></tr></tbody>
            </table></div>""", unsafe_allow_html=True)
            
            # --- START OF FIX ---
            if not (is_empty(hbsag) and is_empty(hbsab) and is_empty(hbcab)):
                advice, status = hepatitis_b_advice(hbsag, hbsab, hbcab)
                status_class = ""
                if status == 'immune':
                    status_class = 'immune-box'
                elif status == 'no_immune':
                    status_class = 'no-immune-box'
                else: # infection or unclear
                    status_class = 'warning-box'
                
                st.markdown(f"""
                <div class='custom-advice-box {status_class}'>
                    {advice}
                </div>
                """, unsafe_allow_html=True)
            # --- END OF FIX ---

    with st.container(border=True):
        render_section_header("สรุปและคำแนะนำการปฏิบัติตัว (Summary & Recommendations)")
        recommendations_html = generate_comprehensive_recommendations(person_data)
        st.markdown(f"<div class='recommendation-container'>{recommendations_html}</div>", unsafe_allow_html=True)


# --- Main Application Logic ---
df = load_sqlite_data()
if df is None:
    st.stop()

st.set_page_config(page_title="ระบบรายงานสุขภาพ", layout="wide")

inject_custom_css()

def perform_search():
    st.session_state.search_query = st.session_state.search_input
    st.session_state.selected_year = None
    st.session_state.selected_date = None
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)
    raw_search_term = st.session_state.search_query.strip()
    search_term = re.sub(r'\s+', ' ', raw_search_term)
    if search_term:
        if search_term.isdigit():
             results_df = df[df["HN"] == search_term].copy()
        else:
             results_df = df[df["ชื่อ-สกุล"] == search_term].copy()

        if results_df.empty:
            st.session_state.search_result = pd.DataFrame()
        else:
            st.session_state.search_result = results_df
    else:
        st.session_state.search_result = pd.DataFrame()

def handle_year_change():
    st.session_state.selected_year = st.session_state.year_select
    st.session_state.selected_date = None
    st.session_state.pop("person_row", None)
    st.session_state.pop("selected_row_found", None)

if 'search_query' not in st.session_state: st.session_state.search_query = ""
if 'search_input' not in st.session_state: st.session_state.search_input = ""
if 'search_result' not in st.session_state: st.session_state.search_result = pd.DataFrame()
if 'selected_year' not in st.session_state: st.session_state.selected_year = None
if 'selected_date' not in st.session_state: st.session_state.selected_date = None
if 'print_trigger' not in st.session_state: st.session_state.print_trigger = False
if 'print_performance_trigger' not in st.session_state: st.session_state.print_performance_trigger = False

# --- START OF CHANGE: Controls moved to Sidebar with Form ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">ค้นหาข้อมูล</div>', unsafe_allow_html=True)
    
    with st.form(key="search_form"):
        st.text_input("HN หรือ ชื่อ-สกุล", key="search_input", placeholder="ค้นหา...", label_visibility="collapsed")
        st.form_submit_button("ค้นหา", on_click=perform_search, use_container_width=True)
    
    results_df = st.session_state.search_result
    if results_df.empty and st.session_state.search_query:
        st.error("❌ ไม่พบข้อมูล")

    if not results_df.empty:
        available_years = sorted(results_df["Year"].dropna().unique().astype(int), reverse=True)
        if available_years:
            if st.session_state.selected_year not in available_years:
                st.session_state.selected_year = available_years[0]
            year_idx = available_years.index(st.session_state.selected_year)
            st.selectbox("เลือกปี พ.ศ.", options=available_years, index=year_idx, format_func=lambda y: f"พ.ศ. {y}", key="year_select", on_change=handle_year_change, label_visibility="collapsed")
        
            person_year_df = results_df[results_df["Year"] == st.session_state.selected_year]

            if not person_year_df.empty:
                merged_series = person_year_df.bfill().ffill().iloc[0]
                st.session_state.person_row = merged_series.to_dict()
                st.session_state.selected_row_found = True
            else:
                 st.session_state.pop("person_row", None)
                 st.session_state.pop("selected_row_found", None)
    
    st.markdown("---")
    st.markdown('<div class="sidebar-title" style="font-size: 1.2rem; margin-top: 1rem;">พิมพ์รายงาน</div>', unsafe_allow_html=True)
    if "person_row" in st.session_state and st.session_state.get("selected_row_found", False):
        if st.button("พิมพ์รายงานสุขภาพ", use_container_width=True):
             st.session_state.print_trigger = True
        if st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True):
            st.session_state.print_performance_trigger = True
    else:
        st.button("พิมพ์รายงานสุขภาพ", use_container_width=True, disabled=True)
        st.button("พิมพ์รายงานสมรรถภาพ", use_container_width=True, disabled=True)

# --- END OF CHANGE ---

# --- Main Page ---
if "person_row" not in st.session_state or not st.session_state.get("selected_row_found", False):
    st.info("กรุณาค้นหาและเลือกผลตรวจจากเมนูด้านข้าง")
else:
    person_data = st.session_state.person_row
    all_person_history_df = st.session_state.search_result
    
    available_reports = OrderedDict()
    # --- START OF CHANGE: Add Visualization tab ---
    if has_visualization_data(all_person_history_df): available_reports['ภาพรวมสุขภาพ (Graphs)'] = 'visualization_report'
    # --- END OF CHANGE ---
    if has_basic_health_data(person_data): available_reports['สุขภาพพื้นฐาน'] = 'main_report'
    if has_vision_data(person_data): available_reports['สมรรถภาพการมองเห็น'] = 'vision_report'
    if has_hearing_data(person_data): available_reports['สมรรถภาพการได้ยิน'] = 'hearing_report'
    if has_lung_data(person_data): available_reports['สมรรถภาพปอด'] = 'lung_report'
    
    if not available_reports:
        display_common_header(person_data)
        st.warning("ไม่พบข้อมูลการตรวจใดๆ สำหรับวันที่และปีที่เลือก")
    else:
        display_common_header(person_data)
        tabs = st.tabs(list(available_reports.keys()))
    
        for i, (tab_title, page_key) in enumerate(available_reports.items()):
            with tabs[i]:
                # --- START OF CHANGE: Handle the new visualization tab ---
                if page_key == 'visualization_report':
                    display_visualization_tab(person_data, all_person_history_df)
                # --- END OF CHANGE ---
                elif page_key == 'vision_report':
                    display_performance_report(person_data, 'vision')
                elif page_key == 'hearing_report':
                    display_performance_report(person_data, 'hearing', all_person_history_df=all_person_history_df)
                elif page_key == 'lung_report':
                    display_performance_report(person_data, 'lung')
                elif page_key == 'main_report':
                    display_main_report(person_data, all_person_history_df)

    # --- Print Logic ---
    if st.session_state.get("print_trigger", False):
        report_html_data = generate_printable_report(person_data, all_person_history_df)
        escaped_html = json.dumps(report_html_data)
        
        # --- START OF FIX: Use a unique ID for the iframe to allow repeated printing ---
        iframe_id = f"print-iframe-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        # --- END OF FIX ---
        
        print_component = f"""
        <iframe id="{iframe_id}" style="display:none;"></iframe>
        <script>
            (function() {{
                const iframe = document.getElementById('{iframe_id}');
                if (!iframe) return;
                const iframeDoc = iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write({escaped_html});
                iframeDoc.close();
                iframe.onload = function() {{
                    setTimeout(function() {{
                        try {{
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();
                        }} catch (e) {{
                            console.error("Printing failed:", e);
                        }}
                    }}, 500);
                }};
            }})();
        </script>
        """
        st.components.v1.html(print_component, height=0, width=0)
        st.session_state.print_trigger = False

    if st.session_state.get("print_performance_trigger", False):
        report_html_data = generate_performance_report_html(person_data, all_person_history_df)
        escaped_html = json.dumps(report_html_data)
        
        # --- START OF FIX: Use a unique ID for the iframe to allow repeated printing ---
        iframe_id = f"print-perf-iframe-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        # --- END OF FIX ---
        
        print_component = f"""
        <iframe id="{iframe_id}" style="display:none;"></iframe>
        <script>
            (function() {{
                const iframe = document.getElementById('{iframe_id}');
                if (!iframe) return;
                const iframeDoc = iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write({escaped_html});
                iframeDoc.close();
                iframe.onload = function() {{
                    setTimeout(function() {{
                        try {{
                            iframe.contentWindow.focus();
                            iframe.contentWindow.print();
                        }} catch (e) {{
                            console.error("Printing performance report failed:", e);
                        }}
                    }}, 500);
                }};
            }})();
        </script>
        """
        st.components.v1.html(print_component, height=0, width=0)
        st.session_state.print_performance_trigger = False

