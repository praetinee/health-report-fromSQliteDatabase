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
# ใช้ None เพื่อให้ Plotly ปรับสีตาม Theme ของ Streamlit อัตโนมัติ
THEME = {
    'primary': '#00796B',
    'text_dark': None, # Let Streamlit theme handle text color
    'grid': 'rgba(128, 128, 128, 0.2)', # Transparent grid works for both
    'success': '#00C853',
    'warning': '#FFAB00',
    'danger': '#D50000',
    'info': '#2962FF',
    # Legacy colors
    'sbp_color': '#E53935',
    'dbp_color': '#1E88E5',
    'hct_color': '#AB47BC',
}

FONT_FAMILY = "Sarabun, sans-serif"

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
    """Standard Layout (Theme Adaptive)"""
    layout_args = dict(
        title=dict(
            text=f"<b>{title}</b>", 
            font=dict(family=FONT_FAMILY, size=16), # Remove fixed color
            x=0,
            y=0.95
        ),
        font=dict(family=FONT_FAMILY), # Remove fixed color
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=80, b=20),
        showlegend=show_legend,
        legend=dict(orientation="h", y=1.15, x=1, xanchor='right')
    )
    
    if x_title: layout_args['xaxis'] = dict(title=x_title, showgrid=True, gridcolor=THEME['grid'])
    if y_title: layout_args['yaxis'] = dict(title=y_title, showgrid=True, gridcolor=THEME['grid'])
    if height: layout_args['height'] = height

    fig.update_layout(**layout_args)
    return fig

def calculate_metric_score(val, metric_type):
    if val is None: return 0
    if metric_type == 'BMI':
        x, y = [15, 18.5, 20.75, 22.9, 23, 25, 30, 35], [50, 90, 100, 100, 90, 70, 40, 10]
        return np.interp(val, x, y)
    elif metric_type == 'BP':
        x, y = [90, 115, 120, 129, 130, 139, 140, 160, 180], [90, 100, 95, 85, 75, 60, 50, 20, 0]
        return np.interp(val, x, y)
    elif metric_type == 'FBS':
        x, y = [50, 70, 99, 100, 125, 126, 200, 300], [40, 100, 100, 90, 60, 40, 10, 0]
        return np.interp(val, x, y)
    elif metric_type == 'LDL':
        x, y = [0, 99, 100, 129, 130, 159, 160, 190], [100, 100, 90, 80, 70, 50, 40, 10]
        return np.interp(val, x, y)
    elif metric_type == 'GFR':
        x, y = [0, 15, 30, 45, 60, 90, 120], [0, 10, 30, 50, 70, 100, 100]
        return np.interp(val, x, y)
    elif metric_type == 'Liver':
        x, y = [0, 35, 40, 50, 80, 120], [100, 100, 90, 70, 40, 0]
        return np.interp(val, x, y)
    elif metric_type == 'Uric':
        x, y = [0, 6, 7, 8, 9, 10], [100, 100, 90, 70, 50, 0]
        return np.interp(val, x, y)
    return 0

def plot_historical_trends(history_df, person_data):
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
        'ความเข้มข้นเลือด (HCT)': ('HCT', '%', 35.0, THEME['hct_color'], 'above_threshold'),
        'ฮีโมโกลบิน (Hb)': ('Hb(%)', 'g/dL', hb_goal, '#EC407A', 'above_threshold')
    }

    cols = st.columns(3)
    for i, (title, config) in enumerate(trend_metrics.items()):
        keys, unit, goals, colors, direction_type = config
        d_text = {"range":"(ควรอยู่ในเกณฑ์)", "higher":"(ยิ่งสูงยิ่งดี)", "target":"(ไม่ควรเกินเกณฑ์)", "above_threshold":"(ไม่ควรต่ำกว่าเกณฑ์)"}.get(direction_type, "")

        with cols[i % 3]:
            fig = go.Figure()
            if isinstance(keys, list):
                df_plot = history_df[['Year_str'] + keys].dropna(subset=keys, how='all')
                if df_plot.empty: continue
                for j, key in enumerate(keys):
                    goal = goals[j]
                    fig.add_trace(go.Scatter(x=df_plot['Year_str'], y=df_plot[key], mode='lines+markers', name=key, line=dict(color=colors[j], width=3, shape='spline'), marker=dict(size=6, color='white', line=dict(width=2, color=colors[j])), hovertemplate=f'<b>{key}: %{{y:.0f}}</b> {unit}<extra></extra>'))
                    if goal: fig.add_shape(type="line", x0=df_plot['Year_str'].iloc[0], y0=goal, x1=df_plot['Year_str'].iloc[-1], y1=goal, line=dict(color=colors[j], width=1, dash="dot"), opacity=0.6)
            else:
                df_plot = history_df[['Year_str', keys]].dropna()
                if df_plot.empty: continue
                fig.add_trace(go.Scatter(x=df_plot['Year_str'], y=df_plot[keys], mode='lines+markers', name=title, line=dict(color=colors, width=3, shape='spline'), marker=dict(size=8, color='white', line=dict(width=2, color=colors)), hovertemplate=f'<b>%{{x}}</b><br>%{{y:.1f}} {unit}<extra></extra>'))
                fig.add_shape(type="line", x0=df_plot['Year_str'].iloc[0], y0=goals, x1=df_plot['Year_str'].iloc[-1], y1=goals, line=dict(color="gray", width=1, dash="dash"), opacity=0.5)
            
            fig.update_layout(
                title=dict(text=f"{title}<br><span style='font-size:12px; opacity:0.7;'>{d_text}</span>", font=dict(size=14)),
                height=220, margin=dict(l=10, r=10, t=50, b=30),
                xaxis=dict(showgrid=False, showline=True, linecolor=THEME['grid']),
                yaxis=dict(showgrid=True, gridcolor=THEME['grid']),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                showlegend=(isinstance(keys, list)), legend=dict(orientation="h", y=1.15, x=1, xanchor='right'),
                font=dict(family=FONT_FAMILY)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True})

def plot_audiogram(person_data):
    freq_cols = {'500': ('R500', 'L500'), '1000': ('R1k', 'L1k'), '2000': ('R2k', 'L2k'), '3000': ('R3k', 'L3k'), '4000': ('R4k', 'L4k'), '6000': ('R6k', 'L6k'), '8000': ('R8k', 'L8k')}
    freqs = list(freq_cols.keys())
    r_vals = [get_float(person_data, freq_cols[f][0]) for f in freqs]
    l_vals = [get_float(person_data, freq_cols[f][1]) for f in freqs]

    if all(v is None for v in r_vals) and all(v is None for v in l_vals):
        st.info("ไม่มีข้อมูลสมรรถภาพการได้ยิน")
        return

    fig = go.Figure()
    # ใช้สีพื้นหลังที่โปร่งใสกว่าเดิมเพื่อรองรับ Dark Mode
    zones = [(0, 25, 'ปกติ', 'rgba(76, 175, 80, 0.2)'), (25, 40, 'เล็กน้อย', 'rgba(255, 255, 0, 0.1)'), (40, 55, 'ปานกลาง', 'rgba(255, 193, 7, 0.15)'), (55, 70, 'ค่อนข้างรุนแรง', 'rgba(255, 152, 0, 0.2)'), (70, 90, 'รุนแรง', 'rgba(255, 87, 34, 0.2)'), (90, 120, 'รุนแรงมาก', 'rgba(244, 67, 54, 0.25)')]
    for s, e, l, c in zones:
        fig.add_shape(type="rect", x0=-0.5, x1=len(freqs)-0.5, y0=s, y1=e, fillcolor=c, opacity=0.5, layer="below", line_width=0)
        fig.add_annotation(x=len(freqs)-0.6, y=(s+e)/2, text=l, showarrow=False, font=dict(size=10, color="gray"))

    fig.add_trace(go.Scatter(x=freqs, y=r_vals, mode='lines+markers', name='หูขวา', line=dict(color='#D32F2F', width=2), marker=dict(symbol='circle-open')))
    fig.add_trace(go.Scatter(x=freqs, y=l_vals, mode='lines+markers', name='หูซ้าย', line=dict(color='#1976D2', width=2, dash='dash'), marker=dict(symbol='x')))

    fig = apply_medical_layout(fig, "ผลตรวจการได้ยิน (Audiogram)", "ความถี่ (Hz)", "dB HL")
    fig.update_layout(yaxis=dict(autorange='reversed', range=[-10, 120], zeroline=False))
    st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})

def plot_lung_comparison(person_data):
    fvc = get_float(person_data, 'FVC')
    fvc_p = get_float(person_data, 'FVC predic')
    fev1 = get_float(person_data, 'FEV1')
    fev1_p = get_float(person_data, 'FEV1 predic')

    if fvc is None:
        st.info("ไม่มีข้อมูลสมรรถภาพปอด")
        return

    cats = ['FVC', 'FEV1']
    fig = go.Figure()
    fig.add_trace(go.Bar(name='ค่าจริง (Actual)', x=cats, y=[fvc, fev1], marker_color=THEME['primary'], text=[f"{fvc}L", f"{fev1}L"], textposition='auto'))
    fig.add_trace(go.Bar(name='ค่ามาตรฐาน (Pred)', x=cats, y=[fvc_p, fev1_p], marker_color='rgba(158,158,158,0.5)', text=[f"{fvc_p}L", f"{fev1_p}L"], textposition='auto'))

    fig = apply_medical_layout(fig, "สมรรถภาพปอด (Spirometry)", "", "Liters")
    fig.update_layout(barmode='group')
    st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})

def get_status_text(val, m_type):
    """
    ฟังก์ชันช่วยสำหรับกำหนดข้อความสถานะตามค่าผลตรวจ (ใช้สำหรับ Label ใน Radar Chart)
    """
    if val is None: return ""
    
    if m_type == 'BMI':
        if val < 18.5: return "น้ำหนักน้อย"
        if 18.5 <= val < 23: return "สมส่วน"
        if 23 <= val < 25: return "เริ่มเกินเกณฑ์" 
        if 25 <= val < 30: return "น้ำหนักเกิน"
        return "น้ำหนักเกินมาก"
    
    if m_type == 'BP': # SBP
        if val < 120: return "ปกติ"
        if val < 140: return "เสี่ยงความดันสูง"
        return "ความดันสูง" # ชัดเจน
        
    if m_type == 'FBS':
        if val < 100: return "ปกติ"
        if val < 126: return "เสี่ยงเบาหวาน"
        return "เบาหวาน" # ชัดเจน (ตามเกณฑ์คัดกรองเบื้องต้น)
        
    if m_type == 'LDL':
        if val < 130: return "ปกติ"
        if val < 160: return "เสี่ยงไขมันสูง"
        return "ไขมันสูง" # ชัดเจน
        
    if m_type == 'GFR':
        if val >= 90: return "ดีมาก"
        if val >= 60: return "ปกติ"
        return "เสื่อม"
        
    if m_type == 'Liver': # SGPT
        if val <= 40: return "ปกติ"
        if val <= 80: return "เสี่ยงตับอักเสบ"
        return "ตับอักเสบ" # สูง > 2 เท่า ถือว่าชัดเจน
        
    if m_type == 'Uric':
        if val <= 7.0: return "ปกติ"
        if val <= 9.0: return "เสี่ยงโรคเกาต์"
        return "กรดยูริกสูงมาก" # ปรับเป็น "สูงมาก" ตามที่ user ต้องการ
        
    return ""

def plot_health_radar(person_data):
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        w, h = get_float(person_data, 'น้ำหนัก'), get_float(person_data, 'ส่วนสูง')
        if w and h: bmi = w / ((h/100)**2)
    
    metrics = [
        {'type': 'BMI', 'val': bmi, 'label': 'ดัชนีมวลกาย', 'fmt': '{:.1f}'},
        {'type': 'BP', 'val': get_float(person_data, 'SBP'), 'label': 'ความดัน', 'fmt': '{:.0f}'},
        {'type': 'FBS', 'val': get_float(person_data, 'FBS'), 'label': 'น้ำตาล', 'fmt': '{:.0f}'},
        {'type': 'LDL', 'val': get_float(person_data, 'LDL'), 'label': 'ไขมันเลว', 'fmt': '{:.0f}'},
        {'type': 'GFR', 'val': get_float(person_data, 'GFR'), 'label': 'ไต', 'fmt': '{:.0f}'},
        {'type': 'Liver', 'val': get_float(person_data, 'SGPT'), 'label': 'เอนไซม์ตับ', 'fmt': '{:.0f}'},
        {'type': 'Uric', 'val': get_float(person_data, 'Uric Acid'), 'label': 'กรดยูริก', 'fmt': '{:.1f}'}
    ]
    
    scores, categories, display_vals = [], [], []
    for m in metrics:
        if m['val'] is not None:
            scores.append(calculate_metric_score(m['val'], m['type']))
            
            # ปรับ Label ให้แสดงสถานะด้วย
            status = get_status_text(m['val'], m['type'])
            if status:
                categories.append(f"{m['label']}<br>({status})")
            else:
                categories.append(m['label'])
                
            display_vals.append(m['fmt'].format(m['val']))
    
    if scores:
        scores.append(scores[0])
        categories.append(categories[0])
        display_vals.append(display_vals[0])
            
    fig = go.Figure()
    
    ideal_r = [100] * (len(categories) - 1)
    if ideal_r: ideal_r.append(ideal_r[0])

    fig.add_trace(go.Scatterpolar(
        r=ideal_r,
        theta=categories,
        fill='toself',
        name='Ideal',
        line=dict(color='rgba(0, 200, 83, 0.3)', dash='dot', width=1),
        fillcolor='rgba(0, 200, 83, 0.05)',
        hoverinfo='skip'
    ))

    fig.add_trace(go.Scatterpolar(
        r=scores, theta=categories, fill='toself', name='You',
        line=dict(color=THEME['primary'], width=3),
        fillcolor='rgba(0, 121, 107, 0.4)',
        text=display_vals
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor=THEME['grid']),
            angularaxis=dict(gridcolor=THEME['grid']), # Remove fixed color
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=80, b=40, l=60, r=60),
        font=dict(family=FONT_FAMILY),
        paper_bgcolor='rgba(0,0,0,0)',
        height=500 
    )
    st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})

def display_visualization_tab(person_data, history_df):
    st.markdown(f"""
    <style>
        .viz-header-card {{
            background-color: var(--secondary-background-color);
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid {THEME['primary']};
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            color: var(--text-color);
        }}
        .viz-header-title {{ margin:0; font-family:'Sarabun'; font-size:1.5rem; font-weight:600; }}
        .viz-header-subtitle {{ margin:5px 0 0 0; opacity:0.8; font-family:'Sarabun'; }}
    </style>
    <div class="viz-header-card">
        <h3 class="viz-header-title">📊 แดชบอร์ดสุขภาพอัจฉริยะ</h3>
        <p class="viz-header-subtitle">วิเคราะห์แนวโน้มและความเสี่ยงสุขภาพ: <b>{person_data.get('ชื่อ-สกุล', '')}</b></p>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### 🛡️ ภาพรวมคะแนนสุขภาพ (Health Score Overview)")
            st.markdown("""
            แผนภูมินี้แสดงการประเมินสุขภาพแบบองค์รวม โดยเทียบค่าผลตรวจเป็นคะแนนเต็ม 100 คะแนน:
            
            * **พื้นที่กราฟเต็มวง** หมายถึง ผลตรวจอยู่ในเกณฑ์ดีเยี่ยมตามมาตรฐาน
            * **ส่วนที่เว้าแหว่ง** หมายถึง ด้านที่มีความเสี่ยงหรือควรได้รับการดูแลเพิ่มเติม

            <small>*(เกณฑ์การประเมินอ้างอิงตามค่ามาตรฐานทางการแพทย์)*</small>
            """, unsafe_allow_html=True)
        with c2: plot_health_radar(person_data)

    with st.container(border=True):
        plot_historical_trends(history_df, person_data)

    st.markdown("---")
    st.subheader("🔬 ผลตรวจสมรรถภาพเฉพาะทาง")
    c_audio, c_lung = st.columns(2)
    with c_audio:
        with st.container(border=True): plot_audiogram(person_data)
    with c_lung:
        with st.container(border=True): plot_lung_comparison(person_data)
