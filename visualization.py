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

# --- HELPER FUNCTIONS ---

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

# --- SCORING LOGIC (IMPROVED & MEDICALLY GROUNDED) ---

def calculate_metric_score(val, metric_type):
    """
    คำนวณคะแนนสุขภาพ (0-100) โดยใช้การประมาณค่าช่วง (Interpolation) 
    อ้างอิงตามเกณฑ์ทางการแพทย์ (Medical Guidelines)
    """
    if val is None: return 0
    
    if metric_type == 'BMI':
        # เกณฑ์คนเอเชีย: ปกติ 18.5 - 22.9 (คะแนนเต็ม)
        # น้อยกว่า 18.5 (ผอม), มากกว่า 23 (ท้วม), มากกว่า 25 (อ้วน), มากกว่า 30 (อ้วนมาก)
        x = [15, 18.5, 20.75, 22.9, 23, 25, 30, 35] # ค่าจริง
        y = [50, 90,   100,   100,  90, 70, 40, 10] # คะแนนที่ได้
        return np.interp(val, x, y)
        
    elif metric_type == 'BP': # SBP (Systolic Blood Pressure)
        # <120 (Optimal), 120-129 (Elevated), 130-139 (Stage 1), >=140 (Stage 2)
        x = [90, 115, 120, 129, 130, 139, 140, 160, 180]
        y = [90, 100, 95,  85,  75,  60,  50,  20,  0]
        return np.interp(val, x, y)
        
    elif metric_type == 'FBS': # Fasting Blood Sugar
        # 70-99 (Normal), 100-125 (Prediabetes), >=126 (Diabetes)
        # <70 (Hypoglycemia Risk)
        x = [50, 70, 99, 100, 125, 126, 200, 300]
        y = [40, 100, 100, 90, 60,  40,  10,  0]
        return np.interp(val, x, y)
        
    elif metric_type == 'LDL': # LDL Cholesterol
        # <100 (Optimal), 100-129 (Near Opt), 130-159 (Borderline), 160-189 (High)
        x = [0,  99,  100, 129, 130, 159, 160, 190]
        y = [100, 100, 90,  80,  70,  50,  40,  10]
        return np.interp(val, x, y)
        
    elif metric_type == 'GFR': # eGFR (Kidney Function)
        # >90 (G1), 60-89 (G2), 45-59 (G3a), 30-44 (G3b), 15-29 (G4), <15 (G5)
        x = [0, 15, 30, 45, 60, 90, 120]
        y = [0, 10, 30, 50, 70, 100, 100]
        return np.interp(val, x, y)
        
    return 0

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
        # --- CHANGE: Updated message ---
        st.info("ไม่มีข้อมูลสมรรถภาพการได้ยิน")
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

    if fvc is None:
        # --- CHANGE: Updated message ---
        st.info("ไม่มีข้อมูลสมรรถภาพปอด")
        return

    cats = ['FVC', 'FEV1']
    fig = go.Figure()
    fig.add_trace(go.Bar(name='ค่าจริง (Actual)', x=cats, y=[fvc, fev1], marker_color=THEME['primary'], text=[f"{fvc}L", f"{fev1}L"], textposition='auto'))
    fig.add_trace(go.Bar(name='ค่ามาตรฐาน (Pred)', x=cats, y=[fvc_p, fev1_p], marker_color='rgba(158,158,158,0.5)', text=[f"{fvc_p}L", f"{fev1_p}L"], textposition='auto'))

    fig = apply_medical_layout(fig, "สมรรถภาพปอด (Spirometry)", "", "Liters")
    fig.update_layout(barmode='group')
    st.plotly_chart(fig, use_container_width=True)

# --- HEALTH SHIELD (RADAR CHART) ---
def plot_health_radar(person_data):
    # Prepare Values
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)
    
    sbp = get_float(person_data, 'SBP')
    fbs = get_float(person_data, 'FBS')
    ldl = get_float(person_data, 'LDL')
    gfr = get_float(person_data, 'GFR')
    
    # Define Data Structure for Iteration
    # เราใช้ตรรกะ Dynamic: ถ้าค่าไหนไม่มี (None) ให้ตัดแกนนั้นทิ้งไปเลย กราฟจะได้ไม่แหว่งเป็น 0
    metrics_config = [
        {'type': 'BMI', 'val': bmi, 'label': 'รูปร่าง (BMI)', 'fmt': '{:.1f}'},
        {'type': 'BP', 'val': sbp, 'label': 'ความดัน (BP)', 'fmt': '{:.0f}'},
        {'type': 'FBS', 'val': fbs, 'label': 'ระดับน้ำตาล', 'fmt': '{:.0f}'},
        {'type': 'LDL', 'val': ldl, 'label': 'ไขมัน (LDL)', 'fmt': '{:.0f}'},
        {'type': 'GFR', 'val': gfr, 'label': 'ไต (GFR)', 'fmt': '{:.0f}'}
    ]
    
    scores = []
    categories = []
    display_vals = []
    
    for m in metrics_config:
        if m['val'] is not None:
            score = calculate_metric_score(m['val'], m['type'])
            scores.append(score)
            categories.append(m['label'])
            display_vals.append(m['fmt'].format(m['val']))
            
    if len(scores) < 3:
        # กรณีข้อมูลน้อยกว่า 3 จุด กราฟ Radar อาจดูแปลกๆ (เป็นเส้นตรง) แต่ก็ดีกว่าแสดง 0 ครับ
        pass 

    fig = go.Figure()
    
    # Background Ideal Shape (100%) - Must match active categories
    fig.add_trace(go.Scatterpolar(
        r=[100] * len(categories),
        theta=categories,
        fill='toself',
        name='ค่าสมบูรณ์แบบ (Ideal)',
        line=dict(color='rgba(0, 200, 83, 0.3)', dash='dot', width=1),
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
        hovertemplate='<b>%{theta}</b><br>ค่าจริง: %{text}<br>คะแนน: %{r:.0f}/100<extra></extra>',
        text=display_vals 
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, 
                range=[0, 100], 
                showticklabels=False, # Hide numbers on axis to look cleaner
                gridcolor=THEME['grid']
            ),
            angularaxis=dict(
                tickfont=dict(size=14, family=FONT_FAMILY, color=THEME['text_dark']),
                gridcolor=THEME['grid']
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        title=dict(text="<b>🛡️ Health Shield (เกราะป้องกันสุขภาพ)</b>", font=dict(family=FONT_FAMILY, size=20), x=0.1),
        margin=dict(t=80, b=40, l=60, r=60),
        font=dict(family=FONT_FAMILY),
        paper_bgcolor='rgba(0,0,0,0)',
        height=450
    )
    
    st.plotly_chart(fig, use_container_width=True)


# --- MAIN DISPLAY FUNCTION ---

def display_visualization_tab(person_data, history_df):
    """Main Tab Display"""
    
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
            กราฟนี้แสดงคะแนนสุขภาพใน 5 ด้านหลัก (เต็ม 100):
            
            * **พื้นที่สีเขียวเต็มกราฟ** = สุขภาพดีเยี่ยม
            * **กราฟเว้าแหว่ง** = จุดเสี่ยงที่ต้องดูแล
            
            *เกณฑ์การคำนวณอ้างอิงมาตรฐานทางการแพทย์ (เช่น ADA, NCEP ATP III)*
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
