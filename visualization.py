# visualization.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import textwrap
import requests
from streamlit_lottie import st_lottie

# --- DESIGN SYSTEM & CONSTANTS ---
THEME = {
    'primary': '#00796B',      # Teal
    'secondary': '#80CBC4',    # Soft Teal
    'text_light': '#37474F',   # Dark Grey
    'grid': 'rgba(128, 128, 128, 0.1)', 
    'success': '#66BB6A',      # Green
    'success_bg': '#E8F5E9',   # Light Green BG
    'warning': '#FFA726',      # Orange
    'warning_bg': '#FFF3E0',   # Light Orange BG
    'danger': '#EF5350',       # Red
    'danger_bg': '#FFEBEE',    # Light Red BG
    'info': '#42A5F5',         # Blue
    'info_bg': '#E3F2FD',      # Light Blue BG
    'track': '#EEEEEE',        # Light Grey for track
    'sbp_color': '#E53935',    # Red
    'dbp_color': '#1E88E5',    # Blue
    'hct_color': '#AB47BC',    # Purple
}

FONT_FAMILY = "Sarabun, sans-serif"

# --- LOTTIE URLS ---
# คุณสามารถเปลี่ยน URL เป็นไฟล์ที่คุณชอบจาก lottiefiles.com ได้เลย
LOTTIE_BMI_URL = "https://lottie.host/5b001638-468e-4782-93f3-952357718117/A0y5z55z5A.json" # Example: Person/Health
LOTTIE_BLOOD_URL = "https://lottie.host/88910080-8975-4c7b-852c-801180960999/999888777.json" # Example: Blood Drop (Placeholder URL)
# เนื่องจาก URL บางอันอาจจะหมดอายุหรือไม่มีจริง ผมจะใช้ฟังก์ชัน load_lottieurl ที่จัดการ error ได้
# และใช้ SVG เป็น Fallback ถ้าโหลดไม่ได้

# ใช้ URL กลางๆ ที่มักจะ work (เป็นตัวอย่าง)
# BMI: Person Yoga/Active
LOTTIE_BMI_URL = "https://assets9.lottiefiles.com/packages/lf20_zfszhesy.json" 
# Blood: Blood Drop
LOTTIE_BLOOD_URL = "https://assets2.lottiefiles.com/packages/lf20_t97bckwz.json"
# Kidney: Anatomy/Organ (หายากหน่อย อาจใช้ Heart แทนในตัวอย่าง หรือ Generic Organ)
LOTTIE_KIDNEY_URL = "https://assets3.lottiefiles.com/packages/lf20_9wimz7j7.json" # Example Medical Scan


def load_lottieurl(url: str):
    """โหลด Lottie JSON จาก URL"""
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def apply_medical_layout(fig, title="", x_title="", y_title="", show_legend=True):
    """Standard Layout for consistency"""
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(family=FONT_FAMILY, size=18), x=0),
        xaxis=dict(title=x_title, showgrid=True, gridcolor=THEME['grid']),
        yaxis=dict(title=y_title, showgrid=True, gridcolor=THEME['grid']),
        legend=dict(orientation="h", y=1.1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT_FAMILY),
        margin=dict(l=10, r=10, t=50, b=20)
    )
    return fig

# --- HELPER FUNCTIONS ---

def clean_html(html_str):
    dedented = textwrap.dedent(html_str)
    stripped = dedented.strip()
    return stripped

def get_float(person_data, key):
    val = person_data.get(key, "")
    if pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]: return None
    try: return float(str(val).replace(",", "").strip())
    except: return None

def get_bmi_desc(bmi):
    if bmi is None: return "ไม่มีข้อมูล"
    if bmi < 18.5: return "น้ำหนักน้อย"
    if bmi < 23: return "สมส่วน"
    if bmi < 25: return "น้ำหนักเกิน"
    if bmi < 30: return "ภาวะอ้วนระยะที่ 1"
    return "ภาวะอ้วนระยะที่ 2"

def get_fbs_desc(fbs):
    if fbs is None: return "-"
    if fbs < 100: return "ปกติ"
    if fbs < 126: return "เสี่ยงเบาหวาน"
    return "เบาหวาน"

def get_gfr_desc(gfr):
    if gfr is None: return "-"
    if gfr >= 90: return "ไตปกติ"
    if gfr >= 60: return "ไตเสื่อมเล็กน้อย"
    return "ไตเสื่อม"

# --- PLOTTING FUNCTIONS ---

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


# --- LOTTIE RENDERER ---

def render_lottie_card(title, value_str, unit, desc, color_hex, bg_hex, lottie_url):
    """
    Render Card UI พร้อม Lottie Animation (หรือ Fallback)
    """
    # Card HTML Container (ส่วนหัวและส่วนท้าย)
    # เราจะแบ่งเป็น 3 ส่วน: Header, Lottie Area (ใช้ st_lottie), Footer
    
    # 1. Opening Div & Header
    st.markdown(clean_html(f"""
    <div style="
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 20px 20px 10px 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.02);
        height: 100%;
        font-family: 'Sarabun', sans-serif;
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    ">
        <div style="font-size: 14px; color: #888; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">
            {title}
        </div>
    """), unsafe_allow_html=True)

    # 2. Middle: Lottie Animation & Value (ใช้ st.columns ภายใน container นี้ไม่ได้ง่ายๆ 
    # เราจึงต้องปิด div ก่อน แล้วใช้ st.columns แล้วค่อยเปิด div ใหม่ หรือใช้ Layout ซ้อน)
    
    # วิธีที่เนียนที่สุดคือใช้ st.columns เพื่อแบ่งซ้ายขวา: ซ้าย=Lottie, ขวา=Text
    # แต่ต้องระวังเรื่องความสูง Lottie
    
    c1, c2 = st.columns([1, 1.5])
    with c1:
        lottie_json = load_lottieurl(lottie_url)
        if lottie_json:
            st_lottie(lottie_json, speed=1, height=80, key=f"lottie_{title}_{value_str}")
        else:
            # Fallback Text Icon if Lottie fails
            st.markdown(f"<div style='font-size:40px; text-align:center;'>❤️</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(clean_html(f"""
        <div style="margin-top: 10px;">
            <div style="font-size: 28px; font-weight: 800; color: #333; line-height: 1;">{value_str}</div>
            <div style="font-size: 14px; color: #999; font-weight: 500; margin-top: 2px;">{unit}</div>
        </div>
        """), unsafe_allow_html=True)
        
    # 3. Footer: Status Badge & Close Div
    st.markdown(clean_html(f"""
        <div style="margin-top: 15px; margin-bottom: 10px;">
            <span style="
                background-color: {bg_hex}; 
                color: {color_hex}; 
                padding: 6px 14px; 
                border-radius: 50px; 
                font-size: 13px; 
                font-weight: 700; 
                display: inline-block; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                {desc}
            </span>
        </div>
        <!-- Decor Circle -->
        <div style="position: absolute; top: -30px; right: -30px; width: 100px; height: 100px; background-color: {bg_hex}; border-radius: 50%; opacity: 0.4; z-index: 0; pointer-events: none;"></div>
    </div>
    """), unsafe_allow_html=True)


def plot_bmi_gauge(person_data):
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
         weight = get_float(person_data, 'น้ำหนัก')
         height = get_float(person_data, 'ส่วนสูง')
         if weight and height: bmi = weight / ((height/100)**2)

    if bmi:
        desc = get_bmi_desc(bmi)
        if "อ้วนระยะที่ 2" in desc: c, bg = THEME['danger'], THEME['danger_bg']
        elif "เริ่ม" in desc or "ท้วม" in desc or "ระยะที่ 1" in desc: c, bg = THEME['warning'], THEME['warning_bg']
        elif "น้อย" in desc: c, bg = THEME['info'], THEME['info_bg']
        else: c, bg = THEME['success'], THEME['success_bg']
        
        # Lottie: Person Exercising / Body Scan
        # URL ตัวอย่าง: หุ่นคน/ออกกำลังกาย
        url = "https://lottie.host/5b001638-468e-4782-93f3-952357718117/A0y5z55z5A.json" 
        render_lottie_card("ดัชนีมวลกาย (BMI)", f"{bmi:.1f}", "kg/m²", desc, c, bg, url)
    else:
        st.info("ไม่มีข้อมูล BMI")

def plot_fbs_gauge(person_data):
    fbs = get_float(person_data, 'FBS')
    if fbs:
        desc = get_fbs_desc(fbs)
        c, bg = (THEME['danger'], THEME['danger_bg']) if "เบาหวาน" in desc and "เสี่ยง" not in desc else (THEME['warning'], THEME['warning_bg']) if "เสี่ยง" in desc else (THEME['success'], THEME['success_bg'])
        
        # Lottie: Blood Drop / Lab Test
        url = "https://lottie.host/88910080-8975-4c7b-852c-801180960999/999888777.json" 
        render_lottie_card("น้ำตาลในเลือด (FBS)", f"{fbs:.0f}", "mg/dL", desc, c, bg, url)
    else:
        st.info("ไม่มีข้อมูล FBS")

def plot_gfr_gauge(person_data):
    gfr = get_float(person_data, 'GFR')
    if gfr:
        desc = get_gfr_desc(gfr)
        c, bg = (THEME['success'], THEME['success_bg']) if "ปกติ" in desc else (THEME['warning'], THEME['warning_bg']) if "เล็กน้อย" in desc else (THEME['danger'], THEME['danger_bg'])
        
        # Lottie: Medical Scanner / Organ
        url = "https://lottie.host/a6d69570-5702-469a-b220-075020290043/p0f1g2h3i4.json"
        render_lottie_card("การทำงานของไต (GFR)", f"{gfr:.0f}", "mL/min", desc, c, bg, url)
    else:
        st.info("ไม่มีข้อมูล GFR")


def plot_audiogram(person_data):
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


def plot_risk_bar_chart(person_data):
    """
    เปลี่ยนจาก Radar Chart เป็น Bar Chart แนวนอน เพื่อให้อ่านง่ายขึ้น
    """
    def get_score(val, thresholds, high_bad=True):
        if val is None: return 0
        if high_bad:
            if val < thresholds[0]: return 1 # ปกติ
            if val < thresholds[1]: return 2 # เริ่มเสี่ยง
            if val < thresholds[2]: return 3 # เสี่ยงปานกลาง
            if val < thresholds[3]: return 4 # เสี่ยงสูง
            return 5 # วิกฤต
        else: # low is bad (e.g., GFR)
            if val > thresholds[3]: return 1
            if val > thresholds[2]: return 2
            if val > thresholds[1]: return 3
            if val > thresholds[0]: return 4
            return 5

    bmi = get_float(person_data, 'BMI')
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
    
    # Map scores to colors and text
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
        else: # 5
            risk_colors.append('#C62828') # Dark Red
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


def plot_lung_comparison(person_data):
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

    # 1. Top: Risk Bar Chart & Indicators
    col_risk, col_ind = st.columns([1.5, 2]) # ปรับสัดส่วน
    
    with col_risk:
        with st.container(border=True):
            plot_risk_bar_chart(person_data)
            st.caption("ℹ️ แถบยาวยิ่งแสดงถึงระดับความเสี่ยงที่สูงขึ้น")
            
    with col_ind:
        # ใช้ st.container แบบไม่ใส่ border เพราะเรามีการ์ดเงาอยู่ข้างในแล้ว จะได้ไม่ซ้อนกัน
        with st.container():
            st.markdown("##### 🎯 ตัวชี้วัดสำคัญ (Key Indicators)")
            c1, c2, c3 = st.columns(3)
            # ใส่ Card ลงใน Column (ใช้ Lottie)
            with c1: plot_bmi_gauge(person_data)
            with c2: plot_fbs_gauge(person_data)
            with c3: plot_gfr_gauge(person_data)

    # 2. Trends
    with st.container(border=True):
        plot_historical_trends(history_df, person_data)

    # 3. Specific Tests
    st.markdown("---")
    st.subheader("🔬 ผลตรวจสมรรถภาพเฉพาะทาง")
    
    c_audio, c_lung = st.columns(2)
    with c_audio:
        with st.container(border=True): plot_audiogram(person_data)
    with c_lung:
        with st.container(border=True): plot_lung_comparison(person_data)
