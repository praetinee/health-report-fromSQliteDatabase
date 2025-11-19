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

# --- HEALTH SHIELD (RADAR CHART) ---
def plot_health_radar(person_data):
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)
    else:
        bmi = 0 # Default if calculation fails

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
    
    categories = ['รูปร่าง (BMI)', 'ความดัน (BP)', 'ระดับน้ำตาล', 'ไขมัน (LDL)', 'ไต (GFR)']

    fig = go.Figure()
    
    # Background Ideal Shape
    fig.add_trace(go.Scatterpolar(
        r=[100]*5,
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
        paper_bgcolor='rgba(0,0,0,0)',
        height=400 # ปรับความสูงให้เหมาะสม
    )
    
    st.plotly_chart(fig, use_container_width=True)


# --- MAIN DISPLAY FUNCTION ---

def display_visualization_tab(person_data, history_df):
    """Main Tab Display (Updated: Only Health Shield at the top)"""
    
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

    # --- 1. Health Shield Section (Replaced Risk Bar & Indicators) ---
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### 🛡️ ภาพรวมสุขภาพ (Health Shield)")
            st.markdown("""
            กราฟนี้แสดงคะแนนสุขภาพใน 5 ด้านหลัก:
            - **เต็มกราฟ (100%)**: สุขภาพดีเยี่ยม
            - **กราฟเว้าแหว่ง**: จุดที่ต้องดูแลเป็นพิเศษ
            """)
        with c2:
            plot_health_radar(person_data)

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
