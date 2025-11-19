# visualization.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import textwrap
import requests
from streamlit_lottie import st_lottie
from datetime import datetime

# --- DESIGN SYSTEM & CONSTANTS ---
THEME = {
    'primary': '#00796B',      # Teal
    'secondary': '#80CBC4',    # Soft Teal
    'accent': '#009688',       # Bright Teal
    'text_dark': '#37474F',    # Dark Grey
    'text_light': '#90A4AE',   # Light Grey
    'grid': 'rgba(128, 128, 128, 0.1)', 
    'success': '#00C853',      # Bright Green
    'success_bg': '#E8F5E9',   
    'warning': '#FFAB00',      # Amber
    'warning_bg': '#FFF8E1',   
    'danger': '#D50000',       # Red
    'danger_bg': '#FFEBEE',    
    'info': '#2962FF',         # Blue
    'info_bg': '#E3F2FD',      
    'bg_card': '#FFFFFF',
}

FONT_FAMILY = "Sarabun, sans-serif"

# --- LOTTIE URLS (Stable URLs) ---
LOTTIE_ASSETS = {
    'heart': "https://lottie.host/88910080-8975-4c7b-852c-801180960999/999888777.json", # Blood/Heart
    'weight': "https://lottie.host/5b001638-468e-4782-93f3-952357718117/A0y5z55z5A.json", # Body/Scale
    'kidney': "https://lottie.host/a6d69570-5702-469a-b220-075020290043/p0f1g2h3i4.json", # Scanner/Organ
    'liver': "https://assets5.lottiefiles.com/packages/lf20_zfszhesy.json", # Generic Health
    'general': "https://assets9.lottiefiles.com/packages/lf20_5njp3vgg.json" # Doctor/Checkup
}

# --- HELPER FUNCTIONS ---

def load_lottieurl(url: str):
    """โหลด Lottie JSON จาก URL อย่างปลอดภัย"""
    try:
        r = requests.get(url, timeout=3)
        if r.status_code != 200: return None
        return r.json()
    except: return None

def get_float(person_data, key):
    val = person_data.get(key, "")
    if pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]: return None
    try: return float(str(val).replace(",", "").strip())
    except: return None

def apply_medical_layout(fig, title="", height=None, show_legend=True):
    """Standard Layout for Modern Medical Charts"""
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(family=FONT_FAMILY, size=16, color=THEME['text_dark']), x=0),
        font=dict(family=FONT_FAMILY, color=THEME['text_dark']),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        height=height,
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def calculate_health_score(val, target_min, target_max, reverse=False):
    """
    Normalize health values to 0-100 score for Radar Chart.
    reverse=True means lower is better (e.g. Cholesterol).
    """
    if val is None: return 0
    
    # Simple linear mapping logic
    # 100 = Perfect (Mean of target)
    # 0 = Critical
    
    ideal = (target_min + target_max) / 2
    
    if not reverse: # Higher is generally better (e.g. GFR, HDL) or Range based
        # For simplicity in this visualization, we treat range bound metrics by distance from ideal
        # If metric is strictly higher is better (GFR):
        if target_max > 1000: # Like infinity
            if val >= target_min: return 100
            return max(0, (val / target_min) * 100)
        else: # Range (e.g. BMI 18.5-23)
            if target_min <= val <= target_max: return 100
            dist = min(abs(val - target_min), abs(val - target_max))
            return max(0, 100 - (dist * 5)) # Deduct score based on distance
            
    else: # Lower is better (e.g. LDL, BP, Sugar)
        if val <= target_min: return 100
        if val >= target_max * 1.5: return 0 # Critical cap
        # Map range target_min...target_max*1.5 to 100...0
        slope = 100 / ((target_max * 1.5) - target_min)
        return max(0, 100 - ((val - target_min) * slope))

# --- 1. VISUALIZATION: HEALTH SHIELD (RADAR CHART) ---

def plot_health_radar(person_data):
    # Prepare Data
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)
    
    sbp = get_float(person_data, 'SBP')
    fbs = get_float(person_data, 'FBS')
    ldl = get_float(person_data, 'LDL')
    gfr = get_float(person_data, 'GFR')
    alt = get_float(person_data, 'SGPT') # Liver

    # Scoring (Approximation for Visualization)
    scores = [
        calculate_health_score(bmi, 18.5, 23), # BMI Range
        calculate_health_score(sbp, 110, 120, reverse=True), # BP (Lower better)
        calculate_health_score(fbs, 70, 100, reverse=True), # Sugar (Lower better)
        calculate_health_score(ldl, 0, 100, reverse=True), # LDL (Lower better)
        calculate_health_score(gfr, 90, 200), # Kidney (Higher better)
        calculate_health_score(alt, 0, 40, reverse=True) # Liver (Lower better)
    ]
    
    categories = ['รูปร่าง (BMI)', 'ความดัน (BP)', 'ระดับน้ำตาล', 'ไขมัน (LDL)', 'ไต (GFR)', 'ตับ (SGPT)']
    
    fig = go.Figure()

    # Background Ideal Shape
    fig.add_trace(go.Scatterpolar(
        r=[100]*6,
        theta=categories,
        fill='toself',
        name='ค่าสมบูรณ์แบบ',
        line=dict(color='rgba(0, 200, 83, 0.2)', dash='dot'),
        fillcolor='rgba(0, 200, 83, 0.05)',
        hoverinfo='skip'
    ))

    # Actual Data
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=categories,
        fill='toself',
        name='สุขภาพของคุณ',
        line=dict(color=THEME['primary'], width=3),
        fillcolor='rgba(0, 121, 107, 0.4)',
        hovertemplate='%{theta}: <b>%{r:.0f}%</b> คะแนน<extra></extra>'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        title=dict(text="<b>🛡️ Health Shield (เกราะป้องกันสุขภาพ)</b>", font=dict(family=FONT_FAMILY, size=18), x=0.1),
        margin=dict(t=60, b=40, l=40, r=40),
        font=dict(family=FONT_FAMILY),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- 2. VISUALIZATION: SMART KPI CARDS 2.0 ---

def get_trend_indicator(current, previous, reverse=False):
    """
    Return HTML string for trend arrow.
    reverse=True means 'Increase' is Bad (e.g. BP, Weight).
    """
    if current is None or previous is None: return ""
    diff = current - previous
    percent = (diff / previous * 100) if previous != 0 else 0
    
    if abs(percent) < 1: return "<span style='color:gray; font-size:12px;'>➖ คงที่</span>"
    
    is_good = (diff < 0) if reverse else (diff > 0)
    color = THEME['success'] if is_good else THEME['danger']
    arrow = "▼" if diff < 0 else "▲"
    
    return f"<span style='color:{color}; font-weight:bold; font-size:13px;'>{arrow} {abs(diff):.1f} ({abs(percent):.1f}%)</span>"

def render_smart_card(title, value, unit, status, trend_html, lottie_url, color_code):
    """Render Modern Card with Lottie + Trend"""
    # Custom CSS for Card
    card_style = f"""
        background: linear-gradient(145deg, #ffffff, #f0f2f5);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 5px 5px 15px #d1d9e6, -5px -5px 15px #ffffff;
        border-left: 5px solid {color_code};
        position: relative;
        overflow: hidden;
        min-height: 180px;
    """
    
    c1, c2 = st.columns([1.2, 2])
    
    with st.container():
        st.markdown(f"""<div style="{card_style}">
            <div style="position:absolute; top:15px; right:15px; font-size:12px; color:#888; font-weight:600; letter-spacing:1px;">{title}</div>
        """, unsafe_allow_html=True)
        
        col_lottie, col_info = st.columns([1, 2])
        with col_lottie:
            if lottie_url:
                lottie_json = load_lottieurl(lottie_url)
                if lottie_json:
                    st_lottie(lottie_json, height=70, key=f"card_{title}")
                else:
                    st.markdown("❤️", unsafe_allow_html=True)
            else:
                 st.markdown("📊", unsafe_allow_html=True)

        with col_info:
            st.markdown(f"""
                <div style="margin-top:10px;">
                    <div style="font-size:28px; font-weight:800; color:#333; line-height:1;">{value}</div>
                    <div style="font-size:14px; color:#666;">{unit}</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="margin-top:15px; padding-top:10px; border-top:1px solid #eee; display:flex; justify-content:space-between; align-items:center;">
                <span style="background-color:{color_code}20; color:{color_code}; padding:4px 10px; border-radius:15px; font-size:12px; font-weight:bold;">{status}</span>
                {trend_html}
            </div>
            </div>
        """, unsafe_allow_html=True)

def display_smart_cards(person_data, history_df):
    # Get previous year data if available
    prev_data = {}
    if history_df is not None and len(history_df) >= 2:
        sorted_df = history_df.sort_values('Year', ascending=False)
        # Check if the first row is current year (which it should be), then take the second row
        if len(sorted_df) > 1:
             # Check if current display year matches the top of history, if so take 2nd. 
             # If we are viewing an old year, we can't easily get 'previous' without more logic.
             # For simplicity, assume we compare to the immediately preceding record in time.
             current_year = person_data.get('Year')
             # Find row with year < current_year
             past_rows = sorted_df[sorted_df['Year'] < current_year]
             if not past_rows.empty:
                 prev_row = past_rows.iloc[0]
                 prev_data = prev_row.to_dict()

    # 1. BMI Card
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)
    
    bmi_prev = get_float(prev_data, 'BMI') if prev_data else None
    if bmi_prev is None and prev_data:
         w, h = get_float(prev_data, 'น้ำหนัก'), get_float(prev_data, 'ส่วนสูง')
         if w and h: bmi_prev = w / ((h/100)**2)

    bmi_status = "ปกติ" if bmi and 18.5 <= bmi < 23 else "เสี่ยง/ผิดปกติ"
    bmi_color = THEME['success'] if bmi_status == "ปกติ" else THEME['warning']
    
    # 2. FBS Card
    fbs = get_float(person_data, 'FBS')
    fbs_prev = get_float(prev_data, 'FBS')
    fbs_status = "ปกติ" if fbs and fbs < 100 else "สูง"
    fbs_color = THEME['success'] if fbs_status == "ปกติ" else THEME['danger']

    # 3. BP Card (SBP)
    sbp = get_float(person_data, 'SBP')
    sbp_prev = get_float(prev_data, 'SBP')
    sbp_status = "ปกติ" if sbp and sbp < 130 else "สูง"
    sbp_color = THEME['success'] if sbp_status == "ปกติ" else THEME['danger']

    # 4. Kidney (GFR)
    gfr = get_float(person_data, 'GFR')
    gfr_prev = get_float(prev_data, 'GFR')
    gfr_status = "ดี" if gfr and gfr > 90 else ("เสื่อมเล็กน้อย" if gfr and gfr > 60 else "เสื่อม")
    gfr_color = THEME['success'] if gfr and gfr > 60 else THEME['danger']

    # Render Columns
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_smart_card("ดัชนีมวลกาย (BMI)", f"{bmi:.1f}" if bmi else "-", "kg/m²", bmi_status, get_trend_indicator(bmi, bmi_prev, True), LOTTIE_ASSETS['weight'], bmi_color)
    with c2:
        render_smart_card("น้ำตาล (FBS)", f"{int(fbs)}" if fbs else "-", "mg/dL", fbs_status, get_trend_indicator(fbs, fbs_prev, True), LOTTIE_ASSETS['heart'], fbs_color)
    with c3:
        render_smart_card("ความดัน (SBP)", f"{int(sbp)}" if sbp else "-", "mmHg", sbp_status, get_trend_indicator(sbp, sbp_prev, True), None, sbp_color) # No dedicated Lottie for BP, use None
    with c4:
        render_smart_card("ไต (GFR)", f"{int(gfr)}" if gfr else "-", "mL/min", gfr_status, get_trend_indicator(gfr, gfr_prev, False), LOTTIE_ASSETS['kidney'], gfr_color)

# --- 3. VISUALIZATION: BULLET GRAPHS (LINEAR GAUGES) ---

def plot_bullet_charts(person_data):
    
    def create_bullet(title, val, unit, ranges, target_val, reverse=False):
        # ranges: [min_bad, limit_good, max_scale]
        # reverse: True if Lower is Better
        
        fig = go.Figure(go.Indicator(
            mode = "number+gauge+delta",
            value = val if val else 0,
            delta = {'reference': target_val, 'increasing': {'color': THEME['danger'] if reverse else THEME['success']}, 'decreasing': {'color': THEME['success'] if reverse else THEME['danger']}},
            domain = {'x': [0.1, 1], 'y': [0, 1]},
            title = {'text': f"<b>{title}</b><br><span style='font-size:0.8em;color:gray'>{unit}</span>", 'font':{'size':14}},
            gauge = {
                'shape': "bullet",
                'axis': {'range': [ranges[0], ranges[-1]]},
                'threshold': {
                    'line': {'color': "black", 'width': 2},
                    'thickness': 0.75,
                    'value': target_val
                },
                'steps': [
                    {'range': [ranges[0], ranges[1]], 'color': THEME['success_bg'] if not reverse else THEME['success_bg']}, # Zone 1
                    {'range': [ranges[1], ranges[2]], 'color': THEME['warning_bg']}, # Zone 2
                    {'range': [ranges[2], ranges[3]], 'color': THEME['danger_bg']} if len(ranges)>3 else None # Zone 3
                ],
                'bar': {'color': THEME['primary']}
            }
        ))
        fig.update_layout(height=120, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    # BP
    sbp = get_float(person_data, 'SBP')
    if sbp:
        st.plotly_chart(create_bullet("ความดันโลหิต (SBP)", sbp, "mmHg", [90, 120, 140, 180], 120, reverse=True), use_container_width=True)
    
    # LDL
    ldl = get_float(person_data, 'LDL')
    if ldl:
        st.plotly_chart(create_bullet("ไขมันเลว (LDL)", ldl, "mg/dL", [0, 100, 130, 190], 100, reverse=True), use_container_width=True)

    # GFR
    gfr = get_float(person_data, 'GFR')
    if gfr:
        st.plotly_chart(create_bullet("การทำงานของไต (GFR)", gfr, "mL/min", [0, 60, 90, 120], 90, reverse=False), use_container_width=True)

# --- 4. VISUALIZATION: DIGITAL TWIN / BODY MAP ---

def plot_digital_twin(person_data):
    """
    Create an abstract Body Map using Plotly Shapes.
    Colors organs based on status.
    """
    
    # 1. Define Body Shapes (Stick Figure / Abstract Block)
    shapes = []
    
    # Head
    shapes.append(dict(type="circle", xref="x", yref="y", x0=-1, y0=8, x1=1, y1=10, line_color="#333", fillcolor="#eee"))
    # Body
    shapes.append(dict(type="rect", xref="x", yref="y", x0=-1.5, y0=4, x1=1.5, y1=8, line_color="#333", fillcolor="#fafafa"))
    # Legs
    shapes.append(dict(type="rect", xref="x", yref="y", x0=-1.2, y0=0, x1=-0.2, y1=4, line_color="#333", fillcolor="#eee"))
    shapes.append(dict(type="rect", xref="x", yref="y", x0=0.2, y0=0, x1=1.2, y1=4, line_color="#333", fillcolor="#eee"))
    
    # 2. Define Organs (Status Points)
    
    # Logic for status colors
    def get_color(val, bad_thresh, mid_thresh, reverse=False):
        if val is None: return "gray"
        # Reverse: High is Bad (BP, Sugar)
        if reverse:
            if val >= bad_thresh: return THEME['danger']
            if val >= mid_thresh: return THEME['warning']
            return THEME['success']
        else: # Normal: Low is Bad (GFR)
            if val <= bad_thresh: return THEME['danger']
            if val <= mid_thresh: return THEME['warning']
            return THEME['success']

    # Brain (BP)
    sbp = get_float(person_data, 'SBP')
    c_brain = get_color(sbp, 140, 130, reverse=True)
    
    # Lungs (CXR) - Text based
    cxr = str(person_data.get('CXR', '')).lower()
    c_lungs = THEME['danger'] if 'abnormal' in cxr or 'infiltrate' in cxr else THEME['success']
    
    # Heart (Lipids/LDL)
    ldl = get_float(person_data, 'LDL')
    c_heart = get_color(ldl, 160, 130, reverse=True)
    
    # Liver (SGPT)
    sgpt = get_float(person_data, 'SGPT')
    c_liver = get_color(sgpt, 40, 30, reverse=True) # Strict threshold
    
    # Kidneys (GFR) - x position offset
    gfr = get_float(person_data, 'GFR')
    c_kidney = get_color(gfr, 60, 90, reverse=False)
    
    # Stomach/Waist (BMI)
    bmi = get_float(person_data, 'BMI')
    if bmi is None: 
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)
    c_body = get_color(bmi, 30, 25, reverse=True)

    # Plot Points
    organs = [
        {'x': 0, 'y': 9, 'label': 'สมอง/ความดัน', 'color': c_brain, 'val': f"{sbp} mmHg"},
        {'x': 0, 'y': 7, 'label': 'ปอด (CXR)', 'color': c_lungs, 'val': cxr if cxr else "-"},
        {'x': 0.5, 'y': 6.5, 'label': 'หัวใจ (LDL)', 'color': c_heart, 'val': f"{ldl} mg/dL"},
        {'x': -0.5, 'y': 5.5, 'label': 'ตับ (SGPT)', 'color': c_liver, 'val': f"{sgpt} U/L"},
        {'x': 0.5, 'y': 5.0, 'label': 'ไต (GFR)', 'color': c_kidney, 'val': f"{gfr}"},
        {'x': 0, 'y': 4.5, 'label': 'รูปร่าง (BMI)', 'color': c_body, 'val': f"{bmi:.1f}" if bmi else "-"},
    ]
    
    fig = go.Figure()
    
    # Draw Points
    fig.add_trace(go.Scatter(
        x=[o['x'] for o in organs],
        y=[o['y'] for o in organs],
        mode='markers+text',
        marker=dict(size=25, color=[o['color'] for o in organs], line=dict(width=2, color='white')),
        text=[o['label'] for o in organs],
        textposition="middle right",
        hovertext=[f"{o['label']}: {o['val']}" for o in organs],
        hoverinfo="text"
    ))
    
    # Add Shapes
    fig.update_layout(shapes=shapes)
    
    fig.update_layout(
        xaxis=dict(range=[-3, 3], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-1, 11], showgrid=False, zeroline=False, visible=False),
        width=400, height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor='rgba(0,0,0,0)',
        title=dict(text="<b>🧍 Digital Twin (จำลองสุขภาพ)</b>", x=0.5, y=0.95, font=dict(family=FONT_FAMILY, size=16))
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- MAIN APP LAYOUT ---

def plot_historical_trends(history_df):
    # Re-using existing logic but improved styling
    if history_df is None or len(history_df) < 2:
        st.info("ต้องการข้อมูลอย่างน้อย 2 ปี เพื่อแสดงกราฟแนวโน้ม")
        return
        
    history_df = history_df.sort_values('Year')
    history_df['Year_Str'] = history_df['Year'].astype(str)
    
    metrics = [
        {'key': 'FBS', 'name': 'น้ำตาล (FBS)', 'color': THEME['warning']},
        {'key': 'SBP', 'name': 'ความดัน (SBP)', 'color': THEME['danger']},
        {'key': 'LDL', 'name': 'ไขมัน (LDL)', 'color': THEME['info']},
        {'key': 'GFR', 'name': 'ไต (GFR)', 'color': THEME['success']}
    ]
    
    fig = go.Figure()
    for m in metrics:
        if m['key'] in history_df.columns:
            df_clean = history_df.dropna(subset=[m['key']])
            if not df_clean.empty:
                # Clean data to float
                df_clean[m['key']] = df_clean[m['key']].astype(str).str.replace(',', '').astype(float)
                fig.add_trace(go.Scatter(
                    x=df_clean['Year_Str'], y=df_clean[m['key']],
                    mode='lines+markers',
                    name=m['name'],
                    line=dict(color=m['color'], width=3),
                    marker=dict(size=8)
                ))
    
    apply_medical_layout(fig, "แนวโน้มสุขภาพย้อนหลัง (Historical Trends)", height=350)
    st.plotly_chart(fig, use_container_width=True)

def display_visualization_tab(person_data, history_df):
    """Main function to render the revamped Visualization Tab"""
    
    # Header
    st.markdown(f"""
    <div style="background-color:{THEME['success_bg']}; padding:15px; border-radius:10px; border-left:5px solid {THEME['success']}; margin-bottom:20px;">
        <h3 style="margin:0; color:{THEME['text_dark']}; font-family:{FONT_FAMILY};">🏥 Smart Health Dashboard</h3>
        <p style="margin:0; color:{THEME['text_dark']}; opacity:0.7;">วิเคราะห์สุขภาพของคุณ: {person_data.get('ชื่อ-สกุล', '-')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Smart Cards Row (Concept 2)
    st.markdown("#### 1. ภาพรวมดัชนีชี้วัด (Smart KPIs)")
    display_smart_cards(person_data, history_df)
    
    st.markdown("---")
    
    # 2. Health Shield & Digital Twin (Concept 1 & 4)
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        # Health Shield
        st.markdown("#### 2. เกราะป้องกันสุขภาพ (Health Shield)")
        st.caption("กราฟนี้แสดงความสมบูรณ์ของร่างกายในแต่ละด้าน (เต็ม 100% คือดีเยี่ยม)")
        plot_health_radar(person_data)
        
    with c2:
        # Digital Twin
        st.markdown("#### 3. ร่างกายจำลอง (Digital Twin)")
        st.caption("จุดสีแสดงสถานะอวัยวะ: 🟢ปกติ 🟡เสี่ยง 🔴อันตราย")
        plot_digital_twin(person_data)

    st.markdown("---")

    # 3. Bullet Graphs (Concept 3) - Target vs Actual
    st.markdown("#### 4. ระยะห่างจากเป้าหมาย (Targets)")
    st.caption("เส้นขีดสีดำคือเป้าหมาย (Target) ที่ควรทำให้ได้")
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        plot_bullet_charts(person_data)
    with c_b2:
        # Historical Trends
        st.markdown("##### 📈 แนวโน้มย้อนหลัง")
        plot_historical_trends(history_df)
