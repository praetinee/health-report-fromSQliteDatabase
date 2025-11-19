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
    # --- Legacy Colors for Restored Charts ---
    'track': '#EEEEEE',        
    'sbp_color': '#E53935',    
    'dbp_color': '#1E88E5',    
    'hct_color': '#AB47BC',    
}

FONT_FAMILY = "Sarabun, sans-serif"

# --- LOTTIE URLS ---
LOTTIE_ASSETS = {
    'heart': "https://lottie.host/88910080-8975-4c7b-852c-801180960999/999888777.json", 
    'weight': "https://lottie.host/5b001638-468e-4782-93f3-952357718117/A0y5z55z5A.json",
    'kidney': "https://lottie.host/a6d69570-5702-469a-b220-075020290043/p0f1g2h3i4.json",
    'liver': "https://assets5.lottiefiles.com/packages/lf20_zfszhesy.json", 
    'general': "https://assets9.lottiefiles.com/packages/lf20_5njp3vgg.json"
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

def clean_html(html_str):
    dedented = textwrap.dedent(html_str)
    stripped = dedented.strip()
    return stripped

def apply_medical_layout(fig, title="", x_title="", y_title="", show_legend=True, height=None):
    """Standard Layout (Compatible with both Old and New charts)"""
    layout_args = dict(
        title=dict(text=f"<b>{title}</b>", font=dict(family=FONT_FAMILY, size=16, color=THEME['text_dark']), x=0),
        font=dict(family=FONT_FAMILY, color=THEME['text_dark']),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=50, b=20),
        showlegend=show_legend,
        legend=dict(orientation="h", y=1.1)
    )
    
    if x_title: layout_args['xaxis'] = dict(title=x_title, showgrid=True, gridcolor=THEME['grid'])
    if y_title: layout_args['yaxis'] = dict(title=y_title, showgrid=True, gridcolor=THEME['grid'])
    if height: layout_args['height'] = height

    fig.update_layout(**layout_args)
    return fig

# --- ORIGINAL FUNCTIONS (RESTORED) ---

def plot_risk_bar_chart(person_data):
    """Original Risk Bar Chart"""
    def get_score(val, thresholds, high_bad=True):
        if val is None: return 0
        if high_bad:
            if val < thresholds[0]: return 1 
            if val < thresholds[1]: return 2 
            if val < thresholds[2]: return 3 
            if val < thresholds[3]: return 4 
            return 5 
        else: 
            if val > thresholds[3]: return 1
            if val > thresholds[2]: return 2
            if val > thresholds[1]: return 3
            if val > thresholds[0]: return 4
            return 5

    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)

    sbp = get_float(person_data, 'SBP')
    fbs = get_float(person_data, 'FBS')
    chol = get_float(person_data, 'CHOL')
    gfr = get_float(person_data, 'GFR')

    scores = [
        get_score(bmi, [23, 25, 30, 35]),
        get_score(sbp, [120, 130, 140, 160]),
        get_score(fbs, [100, 126, 150, 200]),
        get_score(chol, [200, 240, 260, 300]),
        get_score(gfr, [90, 60, 30, 15], high_bad=False)
    ]
    
    categories = ['BMI (น้ำหนัก)', 'ความดันโลหิต', 'น้ำตาลในเลือด', 'ไขมัน', 'การทำงานไต']
    
    risk_colors = []
    risk_texts = []
    for s in scores:
        if s <= 1: 
            risk_colors.append(THEME['success'])
            risk_texts.append("ปกติ")
        elif s == 2:
            risk_colors.append(THEME['info'])
            risk_texts.append("เริ่มเสี่ยง")
        elif s == 3:
            risk_colors.append(THEME['warning'])
            risk_texts.append("ปานกลาง")
        elif s == 4:
            risk_colors.append(THEME['danger'])
            risk_texts.append("สูง")
        else: 
            risk_colors.append('#C62828') 
            risk_texts.append("วิกฤต")
            
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=categories,
        x=scores,
        orientation='h',
        marker=dict(color=risk_colors),
        text=risk_texts,
        textposition='auto',
        textfont=dict(family=FONT_FAMILY, color='white')
    ))
    
    fig.update_layout(
        title=dict(text="<b>ระดับความเสี่ยงสุขภาพ (Risk Level)</b>", font=dict(size=16, family=FONT_FAMILY)),
        xaxis=dict(
            range=[0, 5.5], 
            tickvals=[1, 2, 3, 4, 5],
            ticktext=['ปกติ', 'เริ่ม', 'กลาง', 'สูง', 'วิกฤต'],
            gridcolor=THEME['grid']
        ),
        yaxis=dict(title=""),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT_FAMILY),
        margin=dict(l=10, r=10, t=40, b=20),
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_historical_trends(history_df, person_data):
    """Original Historical Trends"""
    st.subheader("📈 แนวโน้มสุขภาพย้อนหลัง")
    
    if history_df.shape[0] < 2:
        st.info("💡 ต้องการข้อมูลอย่างน้อย 2 ปี เพื่อแสดงกราฟแนวโน้ม")
        return

    history_df = history_df.sort_values(by="Year", ascending=True).copy()
    history_df['Year_str'] = history_df['Year'].astype(str)
    history_df['BMI'] = history_df.apply(lambda row: (get_float(row, 'น้ำหนัก') / ((get_float(row, 'ส่วนสูง') / 100) ** 2)) if get_float(row, 'น้ำหนัก') and get_float(row, 'ส่วนสูง') else np.nan, axis=1)

    sex = person_data.get("เพศ", "ชาย")
    hb_goal = 12.0 if sex == "หญิง" else 13.0
    
    trend_metrics = {
        'ความดันโลหิต (BP)': (['SBP', 'DBP'], 'mmHg', [130.0, 80.0], [THEME['sbp_color'], THEME['dbp_color']], 'target'),
        'น้ำตาล (FBS)': ('FBS', 'mg/dL', 100.0, THEME['warning'], 'target'),
        'ไขมัน (Cholesterol)': ('CHOL', 'mg/dL', 200.0, THEME['danger'], 'target'),
        'ไต (GFR)': ('GFR', 'mL/min', 90.0, THEME['info'], 'higher'),
        'ดัชนีมวลกาย (BMI)': ('BMI', 'kg/m²', 23.0, '#8D6E63', 'range'),
        'ฮีโมโกลบิน (Hb)': ('Hb(%)', 'g/dL', hb_goal, '#EC407A', 'above_threshold')
    }

    cols = st.columns(3)
    for i, (title, config) in enumerate(trend_metrics.items()):
        keys, unit, goals, colors, direction_type = config
        
        if direction_type == 'range': d_text = "(ควรอยู่ในเกณฑ์)"
        elif direction_type == 'higher': d_text = "(ยิ่งสูงยิ่งดี)"
        elif direction_type == 'target': d_text = "(ไม่ควรเกินเกณฑ์)"
        elif direction_type == 'above_threshold': d_text = "(ไม่ควรต่ำกว่าเกณฑ์)"
        else: d_text = ""

        with cols[i % 3]:
            fig = go.Figure()
            if isinstance(keys, list):
                df_plot = history_df[['Year_str'] + keys].dropna(subset=keys, how='all')
                if df_plot.empty: continue
                for j, key in enumerate(keys):
                    goal = goals[j]
                    color = colors[j]
                    fig.add_trace(go.Scatter(x=df_plot['Year_str'], y=df_plot[key], mode='lines+markers', name=key, line=dict(color=color, width=3, shape='spline'), marker=dict(size=6, color='white', line=dict(width=2, color=color)), hovertemplate=f'<b>{key}: %{{y:.0f}}</b> {unit}<extra></extra>'))
                    if goal: fig.add_shape(type="line", x0=df_plot['Year_str'].iloc[0], y0=goal, x1=df_plot['Year_str'].iloc[-1], y1=goal, line=dict(color=color, width=1, dash="dot"), opacity=0.6)
            else:
                df_plot = history_df[['Year_str', keys]].dropna()
                if df_plot.empty: continue
                fig.add_trace(go.Scatter(x=df_plot['Year_str'], y=df_plot[keys], mode='lines+markers', name=title, line=dict(color=colors, width=3, shape='spline'), marker=dict(size=8, color='white', line=dict(width=2, color=colors)), hovertemplate=f'<b>%{{x}}</b><br>%{{y:.1f}} {unit}<extra></extra>'))
                fig.add_shape(type="line", x0=df_plot['Year_str'].iloc[0], y0=goals, x1=df_plot['Year_str'].iloc[-1], y1=goals, line=dict(color="gray", width=1, dash="dash"), opacity=0.5)
            
            fig.update_layout(
                title=dict(text=f"{title}<br><span style='font-size:12px; color:gray;'>{d_text}</span>", font=dict(size=14)),
                height=220, margin=dict(l=10, r=10, t=50, b=30),
                xaxis=dict(showgrid=False, showline=True, linecolor=THEME['grid']),
                yaxis=dict(showgrid=True, gridcolor=THEME['grid']),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                showlegend=(isinstance(keys, list)), legend=dict(orientation="h", y=1.15, x=1, xanchor='right'),
                font=dict(family=FONT_FAMILY)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def plot_audiogram(person_data):
    """Original Audiogram Plot"""
    freq_cols = {'500': ('R500', 'L500'), '1000': ('R1k', 'L1k'), '2000': ('R2k', 'L2k'), '3000': ('R3k', 'L3k'), '4000': ('R4k', 'L4k'), '6000': ('R6k', 'L6k'), '8000': ('R8k', 'L8k')}
    freqs = list(freq_cols.keys())
    r_vals = [get_float(person_data, freq_cols[f][0]) for f in freqs]
    l_vals = [get_float(person_data, freq_cols[f][1]) for f in freqs]

    if all(v is None for v in r_vals) and all(v is None for v in l_vals):
        st.info("ไม่มีข้อมูล Audiogram")
        return

    fig = go.Figure()
    zones = [(0, 25, 'ปกติ', '#E8F5E9'), (25, 40, 'เล็กน้อย', '#FFFDE7'), (40, 55, 'ปานกลาง', '#FFF9C4'), (55, 70, 'ค่อนข้างรุนแรง', '#FFE0B2'), (70, 90, 'รุนแรง', '#FFCCBC'), (90, 120, 'รุนแรงมาก', '#FFAB91')]
    for s, e, l, c in zones:
        fig.add_shape(type="rect", x0=-0.5, x1=len(freqs)-0.5, y0=s, y1=e, fillcolor=c, opacity=0.5, layer="below", line_width=0)
        fig.add_annotation(x=len(freqs)-0.6, y=(s+e)/2, text=l, showarrow=False, font=dict(size=10, color="gray"))

    fig.add_trace(go.Scatter(x=freqs, y=r_vals, mode='lines+markers', name='หูขวา', line=dict(color='#D32F2F', width=2), marker=dict(symbol='circle-open')))
    fig.add_trace(go.Scatter(x=freqs, y=l_vals, mode='lines+markers', name='หูซ้าย', line=dict(color='#1976D2', width=2, dash='dash'), marker=dict(symbol='x')))

    fig = apply_medical_layout(fig, "ผลตรวจการได้ยิน (Audiogram)", "ความถี่ (Hz)", "dB HL")
    fig.update_layout(yaxis=dict(autorange='reversed', range=[-10, 120], zeroline=False))
    st.plotly_chart(fig, use_container_width=True)

def plot_lung_comparison(person_data):
    """Original Lung Plot"""
    fvc = get_float(person_data, 'FVC')
    fvc_p = get_float(person_data, 'FVC predic')
    fev1 = get_float(person_data, 'FEV1')
    fev1_p = get_float(person_data, 'FEV1 predic')

    if fvc is None: return

    cats = ['FVC', 'FEV1']
    fig = go.Figure()
    fig.add_trace(go.Bar(name='ค่าจริง (Actual)', x=cats, y=[fvc, fev1], marker_color=THEME['primary'], text=[f"{fvc}L", f"{fev1}L"], textposition='auto'))
    fig.add_trace(go.Bar(name='ค่ามาตรฐาน (Pred)', x=cats, y=[fvc_p, fev1_p], marker_color='rgba(158,158,158,0.5)', text=[f"{fvc_p}L", f"{fev1_p}L"], textposition='auto'))

    fig = apply_medical_layout(fig, "สมรรถภาพปอด (Spirometry)", "", "Liters")
    fig.update_layout(barmode='group')
    st.plotly_chart(fig, use_container_width=True)


# --- NEW FUNCTIONS FOR KEY INDICATORS ---

def calculate_health_score(val, target_min, target_max, reverse=False):
    if val is None: return 0
    if not reverse: 
        if target_max > 1000: # Threshold logic
            if val >= target_min: return 100
            return max(0, (val / target_min) * 100)
        else: # Range logic
            if target_min <= val <= target_max: return 100
            dist = min(abs(val - target_min), abs(val - target_max))
            return max(0, 100 - (dist * 5)) 
    else: # Lower is better
        if val <= target_min: return 100
        if val >= target_max * 1.5: return 0 
        slope = 100 / ((target_max * 1.5) - target_min)
        return max(0, 100 - ((val - target_min) * slope))

def get_trend_indicator(current, previous, reverse=False):
    if current is None or previous is None: return ""
    diff = current - previous
    percent = (diff / previous * 100) if previous != 0 else 0
    if abs(percent) < 1: return "<span style='color:gray; font-size:12px;'>➖ คงที่</span>"
    is_good = (diff < 0) if reverse else (diff > 0)
    color = THEME['success'] if is_good else THEME['danger']
    arrow = "▼" if diff < 0 else "▲"
    return f"<span style='color:{color}; font-weight:bold; font-size:13px;'>{arrow} {abs(diff):.1f} ({abs(percent):.1f}%)</span>"

def render_smart_card(title, value, unit, status, trend_html, lottie_url, color_code):
    card_style = f"""
        background: linear-gradient(145deg, #ffffff, #f0f2f5);
        border-radius: 15px;
        padding: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        border-left: 4px solid {color_code};
        min-height: 140px;
    """
    st.markdown(f"""
        <div style="{card_style}">
            <div style="display:flex; justify-content:space-between;">
                <span style="font-size:11px; color:#888; font-weight:bold;">{title}</span>
                <span style="background-color:{color_code}20; color:{color_code}; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:bold;">{status}</span>
            </div>
            <div style="display:flex; align-items:center; margin-top:10px; gap:10px;">
                <div style="flex:1;">
                     <div style="font-size:24px; font-weight:800; color:#333;">{value}</div>
                     <div style="font-size:12px; color:#666;">{unit}</div>
                </div>
            </div>
            <div style="margin-top:10px; font-size:11px;">{trend_html}</div>
        </div>
    """, unsafe_allow_html=True)
    if lottie_url:
        with st.container():
             # Hack to inject lottie somewhat cleanly or just skip if too complex for layout
             pass

# --- OPTION 1: SMART CARDS ---
def display_smart_cards_panel(person_data, history_df):
    prev_data = {}
    if history_df is not None and len(history_df) >= 2:
        sorted_df = history_df.sort_values('Year', ascending=False)
        if len(sorted_df) > 1:
             current_year = person_data.get('Year')
             past_rows = sorted_df[sorted_df['Year'] < current_year]
             if not past_rows.empty: prev_data = past_rows.iloc[0].to_dict()

    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)
    bmi_prev = get_float(prev_data, 'BMI') if prev_data else None
    bmi_status = "ปกติ" if bmi and 18.5 <= bmi < 23 else "เสี่ยง"
    bmi_color = THEME['success'] if bmi_status == "ปกติ" else THEME['warning']

    fbs = get_float(person_data, 'FBS')
    fbs_prev = get_float(prev_data, 'FBS')
    fbs_status = "ปกติ" if fbs and fbs < 100 else "สูง"
    fbs_color = THEME['success'] if fbs_status == "ปกติ" else THEME['danger']

    gfr = get_float(person_data, 'GFR')
    gfr_prev = get_float(prev_data, 'GFR')
    gfr_status = "ดี" if gfr and gfr > 90 else "เสื่อม"
    gfr_color = THEME['success'] if gfr and gfr > 60 else THEME['danger']

    c1, c2, c3 = st.columns(3)
    with c1: render_smart_card("BMI", f"{bmi:.1f}" if bmi else "-", "kg/m²", bmi_status, get_trend_indicator(bmi, bmi_prev, True), None, bmi_color)
    with c2: render_smart_card("Blood Sugar", f"{int(fbs)}" if fbs else "-", "mg/dL", fbs_status, get_trend_indicator(fbs, fbs_prev, True), None, fbs_color)
    with c3: render_smart_card("Kidney (GFR)", f"{int(gfr)}" if gfr else "-", "mL/min", gfr_status, get_trend_indicator(gfr, gfr_prev, False), None, gfr_color)

# --- OPTION 2: HEALTH SHIELD ---
def plot_health_radar(person_data):
    bmi = get_float(person_data, 'BMI') or 0
    sbp = get_float(person_data, 'SBP')
    fbs = get_float(person_data, 'FBS')
    ldl = get_float(person_data, 'LDL')
    gfr = get_float(person_data, 'GFR')
    scores = [
        calculate_health_score(bmi, 18.5, 23), 
        calculate_health_score(sbp, 110, 120, reverse=True),
        calculate_health_score(fbs, 70, 100, reverse=True),
        calculate_health_score(ldl, 0, 100, reverse=True),
        calculate_health_score(gfr, 90, 200)
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[100]*5, theta=['BMI', 'BP', 'Sugar', 'Fat', 'Kidney'], fill='toself', name='Target', line=dict(color='rgba(0, 200, 83, 0.2)', dash='dot')))
    fig.add_trace(go.Scatterpolar(r=scores, theta=['BMI', 'BP', 'Sugar', 'Fat', 'Kidney'], fill='toself', name='You', line=dict(color=THEME['primary'], width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False)), showlegend=False, margin=dict(t=20, b=20, l=30, r=30), height=250)
    st.plotly_chart(fig, use_container_width=True)

# --- OPTION 3: BULLET GRAPHS ---
def plot_bullet_charts(person_data):
    def create_bullet(title, val, unit, ranges, target_val, reverse=False):
        fig = go.Figure(go.Indicator(
            mode = "number+gauge+delta", value = val if val else 0,
            delta = {'reference': target_val, 'increasing': {'color': THEME['danger'] if reverse else THEME['success']}, 'decreasing': {'color': THEME['success'] if reverse else THEME['danger']}},
            domain = {'x': [0.1, 1], 'y': [0, 1]}, title = {'text': f"<b>{title}</b>", 'font':{'size':12}},
            gauge = {'shape': "bullet", 'axis': {'range': [ranges[0], ranges[-1]]}, 'threshold': {'line': {'color': "black", 'width': 2}, 'thickness': 0.75, 'value': target_val},
                     'steps': [{'range': [ranges[0], ranges[1]], 'color': THEME['success_bg']}, {'range': [ranges[1], ranges[2]], 'color': THEME['warning_bg']}, {'range': [ranges[2], ranges[3]], 'color': THEME['danger_bg']} if len(ranges)>3 else None],
                     'bar': {'color': THEME['primary']}}))
        fig.update_layout(height=80, margin=dict(l=10, r=10, t=10, b=10))
        return fig
    sbp = get_float(person_data, 'SBP')
    if sbp: st.plotly_chart(create_bullet("BP", sbp, "mmHg", [90, 120, 140, 180], 120, reverse=True), use_container_width=True)
    gfr = get_float(person_data, 'GFR')
    if gfr: st.plotly_chart(create_bullet("GFR", gfr, "mL/min", [0, 60, 90, 120], 90, reverse=False), use_container_width=True)

# --- OPTION 4: DIGITAL TWIN ---
def plot_digital_twin(person_data):
    shapes = [
        dict(type="circle", xref="x", yref="y", x0=-1, y0=8, x1=1, y1=10, line_color="#333", fillcolor="#eee"),
        dict(type="rect", xref="x", yref="y", x0=-1.5, y0=4, x1=1.5, y1=8, line_color="#333", fillcolor="#fafafa")
    ]
    def get_color(val, bad, mid, reverse=False):
        if val is None: return "gray"
        if reverse: return THEME['danger'] if val >= bad else (THEME['warning'] if val >= mid else THEME['success'])
        else: return THEME['danger'] if val <= bad else (THEME['warning'] if val <= mid else THEME['success'])
    
    sbp = get_float(person_data, 'SBP')
    gfr = get_float(person_data, 'GFR')
    organs = [
        {'x': 0, 'y': 9, 'label': 'Brain (BP)', 'color': get_color(sbp, 140, 130, True)},
        {'x': 0.5, 'y': 5.0, 'label': 'Kidney', 'color': get_color(gfr, 60, 90, False)},
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[o['x'] for o in organs], y=[o['y'] for o in organs], mode='markers+text', marker=dict(size=20, color=[o['color'] for o in organs]), text=[o['label'] for o in organs], textposition="middle right"))
    fig.update_layout(shapes=shapes, xaxis=dict(visible=False, range=[-3, 3]), yaxis=dict(visible=False, range=[0, 11]), height=250, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)


# --- MAIN DISPLAY FUNCTION ---

def display_visualization_tab(person_data, history_df):
    """Main Tab Display (Restored Layout + New Indicators)"""
    
    st.markdown(f"""
    <style>
        .viz-header-card {{
            background-color: var(--secondary-background-color);
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid {THEME['primary']};
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .viz-header-title {{ margin:0; color:var(--text-color); font-family:'Sarabun'; font-size:1.5rem; font-weight:600; }}
        .viz-header-subtitle {{ margin:5px 0 0 0; color:var(--text-color); opacity:0.8; font-family:'Sarabun'; }}
    </style>
    <div class="viz-header-card">
        <h3 class="viz-header-title">📊 แดชบอร์ดสุขภาพอัจฉริยะ</h3>
        <p class="viz-header-subtitle">วิเคราะห์แนวโน้มและความเสี่ยงสุขภาพ: <b>{person_data.get('ชื่อ-สกุล', '')}</b></p>
    </div>
    """, unsafe_allow_html=True)

    # --- 1. Top Section: Risk Bar (Left) & Indicators (Right) ---
    col_risk, col_ind = st.columns([1.5, 2]) # สัดส่วนเดิม
    
    with col_risk:
        with st.container(border=True):
            # ใช้กราฟ Risk เดิม
            plot_risk_bar_chart(person_data)
            st.caption("ℹ️ แถบยาวยิ่งแสดงถึงระดับความเสี่ยงที่สูงขึ้น")
            
    with col_ind:
        # --- NEW: Key Indicators Section with Tabs ---
        # ตรงนี้คือจุดเดียวที่เปลี่ยน เพื่อให้คุณเลือก "Try all types" ได้
        st.markdown("##### 🎯 ตัวชี้วัดสำคัญ (Key Indicators - New Designs)")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Smart Cards", "Health Shield", "Bullet Graph", "Digital Twin"])
        
        with tab1:
            display_smart_cards_panel(person_data, history_df)
        with tab2:
            plot_health_radar(person_data)
        with tab3:
            plot_bullet_charts(person_data)
        with tab4:
            plot_digital_twin(person_data)

    # --- 2. Trends (Original Restored) ---
    with st.container(border=True):
        plot_historical_trends(history_df, person_data)

    # --- 3. Specific Tests (Original Restored) ---
    st.markdown("---")
    st.subheader("🔬 ผลตรวจสมรรถภาพเฉพาะทาง")
    
    c_audio, c_lung = st.columns(2)
    with c_audio:
        with st.container(border=True): plot_audiogram(person_data)
    with c_lung:
        with st.container(border=True): plot_lung_comparison(person_data)
