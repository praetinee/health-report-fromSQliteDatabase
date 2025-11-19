# visualization.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# --- DESIGN SYSTEM & CONSTANTS ---
# กำหนดธีมสีกลางเพื่อให้กราฟดูเป็นไปในทิศทางเดียวกัน
THEME = {
    'primary': '#00796B',      # Medical Green/Teal (หลัก)
    'secondary': '#26A69A',    # Lighter Teal
    'accent': '#FF6F00',       # Amber for highlighting
    'bg_light': '#F4F6F8',     # Very light grey/blue for backgrounds
    'text': '#37474F',         # Dark Blue Grey for text
    'grid': '#ECEFF1',         # Light grid lines
    'success': '#4CAF50',      # Green
    'warning': '#FFC107',      # Amber
    'danger': '#EF5350',       # Red
    'info': '#42A5F5'          # Blue
}

FONT_FAMILY = "Sarabun, sans-serif"

def apply_medical_layout(fig, title="", x_title="", y_title="", show_legend=True):
    """ฟังก์ชันช่วยปรับแต่ง Layout ของ Plotly ให้ดูคลีนและทันสมัย"""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(family=FONT_FAMILY, size=18, color=THEME['text']),
            x=0, xanchor='left'
        ),
        xaxis=dict(
            title=x_title,
            showgrid=True, gridcolor=THEME['grid'], gridwidth=0.5,
            zeroline=True, zerolinecolor=THEME['grid'],
            showline=True, linecolor=THEME['grid'],
            tickfont=dict(family=FONT_FAMILY, color=THEME['text'])
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True, gridcolor=THEME['grid'], gridwidth=0.5,
            zeroline=True, zerolinecolor=THEME['grid'],
            showline=False,
            tickfont=dict(family=FONT_FAMILY, color=THEME['text'])
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(family=FONT_FAMILY, size=12)
        ) if show_legend else None,
        showlegend=show_legend,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=60, b=20),
        font=dict(family=FONT_FAMILY, color=THEME['text']),
        hoverlabel=dict(
            font_family=FONT_FAMILY,
            bgcolor="white",
            bordercolor=THEME['grid']
        )
    )
    return fig

# --- HELPER FUNCTIONS ---

def get_float(person_data, key):
    """ดึงค่า float จาก dictionary อย่างปลอดภัย"""
    val = person_data.get(key, "")
    if pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

def get_bmi_desc(bmi):
    if bmi is None: return "ไม่มีข้อมูล"
    if bmi < 18.5: return "น้ำหนักน้อย"
    if bmi < 23: return "น้ำหนักปกติ"
    if bmi < 25: return "ท้วม"
    if bmi < 30: return "โรคอ้วน"
    return "โรคอ้วนอันตราย"

def get_fbs_desc(fbs):
    if fbs is None: return "ไม่มีข้อมูล"
    if fbs < 74: return "ค่อนข้างต่ำ"
    if fbs < 100: return "ปกติ"
    if fbs < 126: return "เสี่ยงเบาหวาน"
    return "เบาหวาน"

def get_gfr_desc(gfr):
    if gfr is None: return "ไม่มีข้อมูล"
    if gfr >= 90: return "ปกติ"
    if gfr >= 60: return "เสื่อมเล็กน้อย"
    if gfr >= 30: return "เสื่อมปานกลาง"
    if gfr >= 15: return "เสื่อมรุนแรง"
    return "ไตวาย"

def get_interpretation_text(metric, value, sex):
    """สร้างข้อความแปลผลสำหรับใช้ใน hover tooltip"""
    if pd.isna(value): return ""
    
    # Logic การแปลผล (คงเดิมไว้ แต่ปรับคำนิดหน่อยให้กระชับ)
    if metric == 'BMI': return f" ({get_bmi_desc(value)})"
    if metric == 'FBS': return f" ({get_fbs_desc(value)})"
    if metric == 'GFR': return f" ({get_gfr_desc(value)})"
    
    # Simple threshold checks
    thresholds = {
        'CHOL': (200, 'สูง'),
        'SBP': (140, 'สูง'),
        'DBP': (90, 'สูง')
    }
    if metric in thresholds:
        limit, msg = thresholds[metric]
        if value >= limit: return f" ({msg})"
    
    return ""

# --- PLOTTING FUNCTIONS ---

def plot_historical_trends(history_df, person_data):
    """
    สร้างกราฟเส้นแสดงแนวโน้มข้อมูลสุขภาพย้อนหลัง (Modern Sparkline Style)
    """
    st.subheader("📈 แนวโน้มสุขภาพย้อนหลัง (Health Trends)")
    st.caption("ติดตามการเปลี่ยนแปลงสุขภาพของคุณในแต่ละปี เทียบกับเกณฑ์มาตรฐาน")

    if history_df.shape[0] < 2:
        st.info("💡 ต้องการข้อมูลอย่างน้อย 2 ปี เพื่อแสดงกราฟแนวโน้ม")
        return

    # 1. Data Preparation
    history_df = history_df.sort_values(by="Year", ascending=True).copy()
    history_df['Year_str'] = history_df['Year'].astype(str)
    
    # Calculate BMI if missing
    history_df['BMI'] = history_df.apply(lambda row: (get_float(row, 'น้ำหนัก') / ((get_float(row, 'ส่วนสูง') / 100) ** 2)) if get_float(row, 'น้ำหนัก') and get_float(row, 'ส่วนสูง') else np.nan, axis=1)

    sex = person_data.get("เพศ", "ชาย")
    hb_goal = 12.0 if sex == "หญิง" else 13.0
    hct_goal = 36.0 if sex == "หญิง" else 39.0

    # Config
    trend_metrics = {
        'ความดัน (SBP)': ('SBP', 'mmHg', 130.0, 'target', THEME['primary']),
        'น้ำตาล (FBS)': ('FBS', 'mg/dL', 100.0, 'target', THEME['warning']),
        'ไขมัน (Cholesterol)': ('CHOL', 'mg/dL', 200.0, 'target', THEME['danger']),
        'ไต (GFR)': ('GFR', 'mL/min', 90.0, 'higher', THEME['info']),
        'ดัชนีมวลกาย (BMI)': ('BMI', 'kg/m²', 23.0, 'range', '#8D6E63'),
        'เลือด (Hb)': ('Hb(%)', 'g/dL', hb_goal, 'above_threshold', '#EC407A')
    }

    # 2. Render Grid
    cols = st.columns(3)
    
    for i, (title, config) in enumerate(trend_metrics.items()):
        keys, unit, goal, direction_type, color = config
        
        with cols[i % 3]:
            # Prepare data
            df_plot = history_df[['Year_str', keys]].dropna()
            if df_plot.empty:
                continue
                
            # Create Plot
            fig = go.Figure()
            
            # Add Main Line
            fig.add_trace(go.Scatter(
                x=df_plot['Year_str'], 
                y=df_plot[keys],
                mode='lines+markers',
                name=title,
                line=dict(color=color, width=3, shape='spline'), # Spline for smooth look
                marker=dict(size=8, color='white', line=dict(width=2, color=color)),
                hovertemplate=f'<b>%{x}</b><br>%{y:.1f} {unit}<extra></extra>'
            ))
            
            # Add Threshold Line (Dashed)
            fig.add_shape(
                type="line",
                x0=df_plot['Year_str'].iloc[0], y0=goal,
                x1=df_plot['Year_str'].iloc[-1], y1=goal,
                line=dict(color="gray", width=1, dash="dash"),
            )
            
            # Mini Layout
            fig.update_layout(
                title=dict(
                    text=f"{title}",
                    font=dict(family=FONT_FAMILY, size=14, color=THEME['text']),
                    y=0.95
                ),
                height=200,
                margin=dict(l=10, r=10, t=40, b=30),
                xaxis=dict(showgrid=False, showline=True, linecolor=THEME['grid']),
                yaxis=dict(showgrid=True, gridcolor=THEME['grid'], showticklabels=True),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                font=dict(family=FONT_FAMILY)
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def create_modern_gauge(value, title, min_val, max_val, steps, current_color):
    """สร้าง Gauge Chart แบบ Minimalist"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': "", 'font': {'size': 40, 'family': FONT_FAMILY, 'color': current_color}},
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16, 'family': FONT_FAMILY, 'color': THEME['text']}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "gray", 'tickfont': {'family': FONT_FAMILY}},
            'bar': {'color': current_color, 'thickness': 0.25}, # บางลงเพื่อให้ดูทันสมัย
            'bgcolor': "white",
            'borderwidth': 0,
            'steps': steps,
            'threshold': {
                'line': {'color': "red", 'width': 2},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        height=250, 
        margin=dict(l=20, r=20, t=40, b=20), 
        font=dict(family=FONT_FAMILY),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def plot_bmi_gauge(person_data):
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
         weight = get_float(person_data, 'น้ำหนัก')
         height = get_float(person_data, 'ส่วนสูง')
         if weight and height and height > 0:
             bmi = weight / ((height/100)**2)

    if bmi is not None:
        # Determine color
        if bmi < 18.5 or bmi >= 30: color = THEME['danger']
        elif bmi >= 23: color = THEME['warning']
        else: color = THEME['success']

        steps = [
            {'range': [15, 18.5], 'color': '#E3F2FD'}, # Thin
            {'range': [18.5, 23], 'color': '#E8F5E9'}, # Normal
            {'range': [23, 25], 'color': '#FFFDE7'},   # Overweight
            {'range': [25, 30], 'color': '#FFF3E0'},   # Obese
            {'range': [30, 40], 'color': '#FFEBEE'}    # Dangerous
        ]
        
        fig = create_modern_gauge(bmi, "ดัชนีมวลกาย (BMI)", 15, 40, steps, color)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<p style='text-align: center; color: {color}; font-weight: bold; font-family: Sarabun;'>{get_bmi_desc(bmi)}</p>", unsafe_allow_html=True)
    else:
        st.info("ไม่มีข้อมูล BMI")

def plot_fbs_gauge(person_data):
    fbs = get_float(person_data, 'FBS')
    if fbs is not None:
        if fbs >= 126: color = THEME['danger']
        elif fbs >= 100: color = THEME['warning']
        else: color = THEME['success']

        steps = [
            {'range': [60, 100], 'color': '#E8F5E9'},
            {'range': [100, 126], 'color': '#FFF3E0'},
            {'range': [126, 200], 'color': '#FFEBEE'}
        ]
        
        fig = create_modern_gauge(fbs, "น้ำตาลในเลือด (FBS)", 60, 200, steps, color)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<p style='text-align: center; color: {color}; font-weight: bold; font-family: Sarabun;'>{get_fbs_desc(fbs)}</p>", unsafe_allow_html=True)
    else:
        st.info("ไม่มีข้อมูล FBS")

def plot_gfr_gauge(person_data):
    gfr = get_float(person_data, 'GFR')
    if gfr is not None:
        if gfr < 60: color = THEME['danger']
        elif gfr < 90: color = THEME['warning']
        else: color = THEME['success']
        
        steps = [
            {'range': [0, 60], 'color': '#FFEBEE'},
            {'range': [60, 90], 'color': '#FFF3E0'},
            {'range': [90, 120], 'color': '#E8F5E9'}
        ]
        
        fig = create_modern_gauge(gfr, "การทำงานของไต (GFR)", 0, 120, steps, color)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<p style='text-align: center; color: {color}; font-weight: bold; font-family: Sarabun;'>{get_gfr_desc(gfr)}</p>", unsafe_allow_html=True)
    else:
        st.info("ไม่มีข้อมูล GFR")


def plot_audiogram(person_data):
    """สร้างกราฟ Audiogram แบบ Clinical Standard"""
    freq_cols = {
        '500': ('R500', 'L500'), '1000': ('R1k', 'L1k'), '2000': ('R2k', 'L2k'),
        '3000': ('R3k', 'L3k'), '4000': ('R4k', 'L4k'), '6000': ('R6k', 'L6k'),
        '8000': ('R8k', 'L8k')
    }
    freqs = list(freq_cols.keys())
    r_vals = [get_float(person_data, freq_cols[f][0]) for f in freqs]
    l_vals = [get_float(person_data, freq_cols[f][1]) for f in freqs]

    if all(v is None for v in r_vals) and all(v is None for v in l_vals):
        st.info("ไม่มีข้อมูล Audiogram")
        return

    fig = go.Figure()

    # Background Zones (Clinical Standards)
    zones = [
        (0, 25, 'ปกติ (Normal)', '#E8F5E9'),
        (25, 40, 'เล็กน้อย (Mild)', '#FFFDE7'),
        (40, 55, 'ปานกลาง (Moderate)', '#FFF9C4'),
        (55, 70, 'ค่อนข้างรุนแรง (Mod. Severe)', '#FFE0B2'),
        (70, 90, 'รุนแรง (Severe)', '#FFCCBC'),
        (90, 120, 'รุนแรงมาก (Profound)', '#FFAB91')
    ]
    
    for start, end, label, color in zones:
        fig.add_shape(type="rect", x0=-0.5, x1=len(freqs)-0.5, y0=start, y1=end,
                      fillcolor=color, opacity=0.5, layer="below", line_width=0)
        # Add label only on the right side
        fig.add_annotation(x=len(freqs)-0.6, y=(start+end)/2, text=label, showarrow=False,
                           font=dict(size=10, color="gray"))

    # Right Ear (Red Circle)
    fig.add_trace(go.Scatter(
        x=freqs, y=r_vals, mode='lines+markers', name='หูขวา (Right)',
        line=dict(color='#D32F2F', width=2), 
        marker=dict(symbol='circle-open', size=10, line=dict(width=2)),
        connectgaps=True
    ))

    # Left Ear (Blue Cross)
    fig.add_trace(go.Scatter(
        x=freqs, y=l_vals, mode='lines+markers', name='หูซ้าย (Left)',
        line=dict(color='#1976D2', width=2, dash='dash'), # Dashed for standard
        marker=dict(symbol='x', size=10, line=dict(width=2)),
        connectgaps=True
    ))

    fig = apply_medical_layout(fig, "ผลตรวจการได้ยิน (Audiogram)", "ความถี่ (Hz)", "ระดับการได้ยิน (dB HL)")
    fig.update_layout(
        yaxis=dict(autorange='reversed', range=[-10, 120], zeroline=False), # Invert Y axis
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center')
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_risk_radar(person_data):
    """กราฟ Radar Chart แบบ Modern Filled"""
    
    def normalize_score(value, thresholds, higher_is_better=False):
        if value is None: return 0
        # Score 1 (Good) to 5 (Bad)
        score = 1
        if higher_is_better:
            # ex: GFR > 90 is good (1), < 15 is bad (5)
            if value < thresholds[0]: score = 5
            elif value < thresholds[1]: score = 4
            elif value < thresholds[2]: score = 3
            elif value < thresholds[3]: score = 2
            else: score = 1
        else:
            # ex: SBP < 120 is good (1), > 160 is bad (5)
            if value > thresholds[3]: score = 5
            elif value > thresholds[2]: score = 4
            elif value > thresholds[1]: score = 3
            elif value > thresholds[0]: score = 2
            else: score = 1
        return score

    # Data Extraction & Scoring
    bmi = get_float(person_data, 'BMI') or 0
    sbp = get_float(person_data, 'SBP') or 0
    fbs = get_float(person_data, 'FBS') or 0
    chol = get_float(person_data, 'CHOL') or 0
    gfr = get_float(person_data, 'GFR') or 0

    # Thresholds logic [Level 2 start, Level 3 start, Level 4 start, Level 5 start]
    scores = [
        normalize_score(bmi, [23, 25, 30, 35]),
        normalize_score(sbp, [120, 130, 140, 160]),
        normalize_score(fbs, [100, 126, 150, 200]),
        normalize_score(chol, [200, 240, 260, 300]),
        normalize_score(gfr, [15, 30, 60, 90], higher_is_better=True)
    ]
    
    categories = ['น้ำหนัก (BMI)', 'ความดัน (BP)', 'น้ำตาล (FBS)', 'ไขมัน (Chol)', 'ไต (GFR)']
    
    # Create Chart
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=categories,
        fill='toself',
        name='ระดับความเสี่ยง',
        line=dict(color=THEME['secondary']),
        fillcolor='rgba(38, 166, 154, 0.3)' # Transparent Teal
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickvals=[1, 2, 3, 4, 5],
                ticktext=['ปกติ', 'เสี่ยงต่ำ', 'ปานกลาง', 'สูง', 'วิกฤต'],
                tickfont=dict(size=10, color="gray")
            )
        ),
        showlegend=False,
        title=dict(
            text="<b>ภาพรวมความเสี่ยงสุขภาพ (Health Risk Profile)</b>",
            font=dict(size=16, family=FONT_FAMILY, color=THEME['text']),
            x=0.5
        ),
        font=dict(family=FONT_FAMILY),
        margin=dict(t=40, b=20, l=40, r=40),
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_lung_comparison(person_data):
    """Bar Chart เปรียบเทียบสมรรถภาพปอดแบบ Grouped"""
    fvc_actual = get_float(person_data, 'FVC')
    fvc_pred = get_float(person_data, 'FVC predic')
    fev1_actual = get_float(person_data, 'FEV1')
    fev1_pred = get_float(person_data, 'FEV1 predic')

    if fvc_actual is None or fev1_actual is None:
        st.info("ไม่มีข้อมูลสมรรถภาพปอด")
        return

    categories = ['FVC (ความจุ)', 'FEV1 (การเป่าออก)']
    
    fig = go.Figure()
    
    # Actual Bar
    fig.add_trace(go.Bar(
        name='ค่าที่วัดได้ (Actual)', 
        x=categories, 
        y=[fvc_actual, fev1_actual],
        marker_color=THEME['primary'],
        text=[f"{fvc_actual:.2f} L", f"{fev1_actual:.2f} L"],
        textposition='auto'
    ))
    
    # Predicted Bar
    fig.add_trace(go.Bar(
        name='ค่ามาตรฐาน (Predicted)', 
        x=categories, 
        y=[fvc_pred, fev1_pred],
        marker_color=THEME['grid'], # Use grey for reference
        text=[f"{fvc_pred:.2f} L", f"{fev1_pred:.2f} L"],
        textposition='auto'
    ))

    fig = apply_medical_layout(fig, "สมรรถภาพปอดเทียบกับมาตรฐาน", "", "ปริมาตร (ลิตร)")
    fig.update_layout(barmode='group')
    
    st.plotly_chart(fig, use_container_width=True)


def display_visualization_tab(person_data, history_df):
    """Main Tab Display Function"""
    
    # Header Section with Card-like style
    st.markdown(f"""
    <div style="background-color:{THEME['bg_light']}; padding:20px; border-radius:10px; border-left: 5px solid {THEME['primary']}; margin-bottom: 20px;">
        <h3 style="margin:0; color:{THEME['text']}; font-family: Sarabun;">📊 แดชบอร์ดสุขภาพอัจฉริยะ</h3>
        <p style="margin:0; color:#666; font-family: Sarabun;">วิเคราะห์แนวโน้มและประเมินความเสี่ยงสุขภาพของคุณ: <b>{person_data.get('ชื่อ-สกุล', '')}</b></p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Top Row: Risk Radar & Key Gauges
    col_radar, col_gauges = st.columns([1, 1.5])
    
    with col_radar:
        with st.container(border=True):
            plot_risk_radar(person_data)
            
    with col_gauges:
        with st.container(border=True):
            st.markdown("##### 🎯 ตัวชี้วัดสำคัญ (Key Indicators)")
            c1, c2, c3 = st.columns(3)
            with c1: plot_bmi_gauge(person_data)
            with c2: plot_fbs_gauge(person_data)
            with c3: plot_gfr_gauge(person_data)

    # 2. Middle Row: Historical Trends
    with st.container(border=True):
        plot_historical_trends(history_df, person_data)

    # 3. Bottom Row: Specific Tests
    st.markdown("---")
    st.subheader("🔬 ผลตรวจสมรรถภาพเฉพาะทาง (Specialized Tests)")
    
    c_audio, c_lung = st.columns(2)
    
    with c_audio:
        with st.container(border=True):
            plot_audiogram(person_data)
            
    with c_lung:
        with st.container(border=True):
            plot_lung_comparison(person_data)
