# visualization.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# --- ฟังก์ชันตัวช่วย ---

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
    if fbs < 126: return "ภาวะเสี่ยงเบาหวาน"
    return "เข้าเกณฑ์เบาหวาน"

def get_gfr_desc(gfr):
    if gfr is None: return "ไม่มีข้อมูล"
    if gfr >= 90: return "ปกติ"
    if gfr >= 60: return "เริ่มเสื่อมเล็กน้อย"
    if gfr >= 30: return "เสื่อมปานกลาง"
    if gfr >= 15: return "เสื่อมรุนแรง"
    return "ไตวายระยะสุดท้าย"


def get_interpretation_text(metric, value, sex):
    """สร้างข้อความแปลผลสำหรับใช้ใน hover tooltip ของกราฟ"""
    if pd.isna(value):
        return ""
        
    # --- START OF CHANGE: Added Hb and HCT interpretation ---
    if metric == 'Hb(%)':
        goal = 12.0 if sex == "หญิง" else 13.0
        if value < goal: return f" (ต่ำกว่าเกณฑ์ {goal})"
        return " (ปกติ)"
    if metric == 'HCT':
        goal = 36.0 if sex == "หญิง" else 39.0
        if value < goal: return f" (ต่ำกว่าเกณฑ์ {goal})"
        return " (ปกติ)"
    # --- END OF CHANGE ---
        
    if metric == 'BMI':
        return f" ({get_bmi_desc(value)})"
    if metric == 'FBS':
        return f" ({get_fbs_desc(value)})"
    if metric == 'CHOL':
        if value < 200: return " (ปกติ)"
        if value < 240: return " (เริ่มสูง)"
        return " (สูง)"
    if metric == 'GFR':
        return f" ({get_gfr_desc(value)})"
    if metric == 'SBP':
        if value < 120: return " (ปกติ)"
        if value < 130: return " (เริ่มสูง)"
        if value < 140: return " (สูงระดับ 1)"
        if value < 160: return " (สูงระดับ 2)"
        return " (สูงมาก)"
    if metric == 'DBP':
        if value < 80: return " (ปกติ)"
        if value < 90: return " (สูงระดับ 1)"
        if value < 100: return " (สูงระดับ 2)"
        return " (สูงมาก)"
    return ""

def get_bp_classification(sbp, dbp):
    """จำแนกระดับความดันโลหิตสำหรับใช้ในกราฟ (ฟังก์ชันนี้ไม่ได้ใช้ในกราฟแนวโน้มแล้ว แต่เก็บไว้เผื่อใช้อื่นๆ)"""
    if sbp is None or dbp is None or pd.isna(sbp) or pd.isna(dbp):
        return "ไม่มีข้อมูล"
    sbp, dbp = float(sbp), float(dbp)
    if sbp >= 180 or dbp >= 120: return "สูงวิกฤต"
    if sbp >= 140 or dbp >= 90: return "สูงระยะที่ 2"
    if 130 <= sbp <= 139 or 80 <= dbp <= 89: return "สูงระยะที่ 1"
    if 120 <= sbp <= 129 and dbp < 80: return "เริ่มสูง"
    if sbp < 120 and dbp < 80: return "ปกติ"
    return "ไม่สามารถจำแนกได้"

# --- 1. กราฟแสดงแนวโน้มย้อนหลัง ---
def plot_historical_trends(history_df, person_data): # --- START OF CHANGE: Added person_data ---
    """
    สร้างกราฟเส้น/ตารางแสดงแนวโน้มข้อมูลสุขภาพย้อนหลัง
    """
    st.caption("กราฟนี้แสดงการเปลี่ยนแปลงของค่าต่างๆ ในแต่ละปีที่มีการตรวจ พร้อมเส้นคาดการณ์แนวโน้มในอีก 2 ปีข้างหน้า (เส้นประ) และเส้นเกณฑ์สุขภาพ (เส้นสีเขียว)")

    if history_df.shape[0] < 2:
        st.info("ข้อมูลย้อนหลังไม่เพียงพอที่จะสร้างกราฟแนวโน้ม (ต้องการอย่างน้อย 2 ปี)")
        return

    history_df = history_df.sort_values(by="Year", ascending=True).copy()
    min_year, max_year = int(history_df['Year'].min()), int(history_df['Year'].max())
    all_years_df = pd.DataFrame({'Year': range(min_year, max_year + 1)})
    history_df = pd.merge(all_years_df, history_df, on='Year', how='left')
    history_df['BMI'] = history_df.apply(lambda row: (get_float(row, 'น้ำหนัก') / ((get_float(row, 'ส่วนสูง') / 100) ** 2)) if get_float(row, 'น้ำหนัก') and get_float(row, 'ส่วนสูง') else np.nan, axis=1)

    # --- START OF CHANGE: Added Hb and HCT metrics and dynamic goals ---
    sex = person_data.get("เพศ", "ชาย") # Get sex from person_data
    hb_goal = 12.0 if sex == "หญิง" else 13.0
    hct_goal = 36.0 if sex == "หญิง" else 39.0

    trend_metrics = {
        'ฮีโมโกลบิน (Hb)': ('Hb(%)', 'g/dL', hb_goal, 'above_threshold'), # Changed 'higher' to 'above_threshold'
        'ฮีมาโตคริต (Hct)': ('HCT', '%', hct_goal, 'above_threshold'), # Changed 'higher' to 'above_threshold'
        'ดัชนีมวลกาย (BMI)': ('BMI', 'kg/m²', 23.0, 'range'),
        'ระดับน้ำตาลในเลือด (FBS)': ('FBS', 'mg/dL', 100.0, 'target'),
        'คอเลสเตอรอล (Cholesterol)': ('CHOL', 'mg/dL', 200.0, 'target'),
        'ประสิทธิภาพการกรองของไต (GFR)': ('GFR', 'mL/min', 90.0, 'higher'), # Kept as 'higher'
        'ความดันตัวบน (SBP)': ('SBP', 'mmHg', 130.0, 'target'),
        'ความดันตัวล่าง (DBP)': ('DBP', 'mmHg', 80.0, 'target')
    }
    # --- END OF CHANGE ---

    # Prepare interpretation text columns
    for title, (keys, unit, goal, *_) in trend_metrics.items():
         # --- START OF CHANGE: Pass sex to interpretation function ---
         history_df[f'{keys}_interp'] = history_df[keys].apply(lambda x: get_interpretation_text(keys, x, sex))
         # --- END OF CHANGE ---

    history_df['Year_str'] = history_df['Year'].astype(str)

    # Create a list of metrics to plot
    metrics_to_plot = [ (title, keys, unit, goal, direction_type)
                        for title, (keys, unit, goal, direction_type) in trend_metrics.items() ]

    # Use a loop to create a responsive grid
    num_metrics = len(metrics_to_plot)
    cols = st.columns(min(num_metrics, 3)) # Max 3 columns, adjust if fewer metrics

    for i in range(num_metrics):
        with cols[i % len(cols)]:
            title, keys, unit, goal, direction_type = metrics_to_plot[i]
            
            # --- START OF CHANGE: Added icon logic for Hb/Hct ---
            icon = "❤️" if keys in ['Hb(%)', 'HCT'] else ("🩸" if keys in ['SBP', 'DBP'] else "📊")
            # --- END OF CHANGE ---

            # --- START OF CHANGE: Updated direction text logic ---
            if direction_type == 'range':
                direction_text = "(ควรอยู่ในเกณฑ์)"
            elif direction_type == 'higher':
                direction_text = "(ยิ่งสูงยิ่งดี)"
            elif direction_type == 'target':
                direction_text = "(ไม่ควรสูงเกินเกณฑ์)"
            elif direction_type == 'above_threshold':
                direction_text = "(ไม่ควรต่ำกว่าเกณฑ์)"
            else:
                direction_text = "(ยิ่งต่ำยิ่งดี)"
            # --- END OF CHANGE ---

            full_title = f"<h5 style='text-align:center;'>{icon} {title} <br><span style='font-size:0.8em;color:gray;'>{direction_text}</span></h5>"

            df_plot = history_df[['Year_str', keys, f'{keys}_interp']].copy() # Ensure using copy

            # Check if there's any non-NaN data to plot for this metric
            if df_plot[keys].isnull().all():
                st.markdown(full_title, unsafe_allow_html=True)
                st.info(f"ไม่มีข้อมูล {title} เพียงพอที่จะแสดงผล")
                continue # Skip to the next metric if no data

            fig = px.line(df_plot, x='Year_str', y=keys, title=full_title.replace("<h5 style='text-align:center;'>", "").replace("</h5>",""), markers=True, custom_data=[keys, f'{keys}_interp'])
            fig.update_traces(hovertemplate='<b>%{x}</b><br>%{customdata[0]:.1f} ' + unit + '%{customdata[1]}<extra></extra>')
            # Add target line (hline)
            fig.add_hline(y=goal, line_width=2, line_dash="dash", line_color="green", annotation_text="เกณฑ์", annotation_position="bottom right")

            # Add trendline prediction if enough data
            clean_df = history_df[['Year', keys]].dropna()
            if len(clean_df) >= 3:
                model = np.polyfit(clean_df['Year'], clean_df[keys], 1)
                predict = np.poly1d(model)
                future_years = np.array([max_year + 1, max_year + 2])
                predicted_values = predict(future_years)
                # Extend trendline smoothly from last data point
                all_future_years = np.insert(future_years, 0, max_year)
                all_predicted_values = np.insert(predicted_values, 0, predict(max_year)) # Use prediction at max_year for continuity
                fig.add_trace(go.Scatter(x=all_future_years.astype(str), y=all_predicted_values, mode='lines', line=dict(color='rgba(128,128,128,0.7)', width=2, dash='dot'), name='คาดการณ์', hovertemplate='คาดการณ์ปี %{x}: %{y:.1f}<extra></extra>'))

            fig.update_traces(connectgaps=False) # Don't connect missing years
            fig.update_layout(yaxis_title=unit, xaxis_title='ปี พ.ศ.', legend_title_text="", font_family="Sarabun", template="streamlit", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)


# --- 2. เกจวัด ---

def plot_bmi_gauge(person_data):
    """สร้างเกจวัดสำหรับ BMI"""
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
         weight = get_float(person_data, 'น้ำหนัก')
         height = get_float(person_data, 'ส่วนสูง')
         if weight and height and height > 0:
             bmi = weight / ((height/100)**2)

    if bmi is not None:
        st.markdown("<p style='text-align: center; font-weight: bold;'>ดัชนีมวลกาย (BMI)</p>", unsafe_allow_html=True)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = bmi,
            gauge = {
                'axis': {'range': [15, 40], 'tickfont': {'color': "gray"}},
                'steps' : [
                    {'range': [15, 18.5], 'color': "lightblue"},
                    {'range': [18.5, 23], 'color': "green"},
                    {'range': [23, 25], 'color': "yellow"},
                    {'range': [25, 30], 'color': "orange"},
                    {'range': [30, 40], 'color': "red"}],
                'bar': {'color': "royalblue"}
            }))
        fig.update_layout(height=220, margin=dict(l=20, r=20, t=20, b=20), font_family="Sarabun", template="streamlit")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<p style='text-align: center; font-weight: bold;'>ผล: {get_bmi_desc(bmi)}</p>", unsafe_allow_html=True)
    else:
        st.info("ไม่มีข้อมูล BMI")

def plot_fbs_gauge(person_data):
    """สร้างเกจวัดสำหรับ FBS"""
    fbs = get_float(person_data, 'FBS')
    if fbs is not None:
        st.markdown("<p style='text-align: center; font-weight: bold;'>ระดับน้ำตาล (FBS mg/dL)</p>", unsafe_allow_html=True)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = fbs,
            gauge = {
                'axis': {'range': [60, 160], 'tickfont': {'color': "gray"}},
                'steps' : [
                    {'range': [60, 74], 'color': "yellow"},
                    {'range': [74, 100], 'color': "green"},
                    {'range': [100, 126], 'color': "orange"},
                    {'range': [126, 160], 'color': "red"}],
                'bar': {'color': "royalblue"}
            }))
        fig.update_layout(height=220, margin=dict(l=20, r=20, t=20, b=20), font_family="Sarabun", template="streamlit")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<p style='text-align: center; font-weight: bold;'>ผล: {get_fbs_desc(fbs)}</p>", unsafe_allow_html=True)
    else:
        st.info("ไม่มีข้อมูล FBS")

def plot_gfr_gauge(person_data):
    """สร้างเกจวัดสำหรับ GFR"""
    gfr = get_float(person_data, 'GFR')
    if gfr is not None:
        st.markdown("<p style='text-align: center; font-weight: bold;'>การกรองของไต (GFR mL/min)</p>", unsafe_allow_html=True)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = gfr,
            gauge = {
                'axis': {'range': [0, 120], 'tickfont': {'color': "gray"}},
                'steps' : [
                    {'range': [0, 30], 'color': "red"},
                    {'range': [30, 60], 'color': "orange"},
                    {'range': [60, 90], 'color': "yellow"},
                    {'range': [90, 120], 'color': "green"}],
                'bar': {'color': "royalblue"}
            }))
        fig.update_layout(height=220, margin=dict(l=20, r=20, t=20, b=20), font_family="Sarabun", template="streamlit")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<p style='text-align: center; font-weight: bold;'>ผล: {get_gfr_desc(gfr)}</p>", unsafe_allow_html=True)
    else:
        st.info("ไม่มีข้อมูล GFR")



# --- 3. กราฟการได้ยิน ---

def plot_audiogram(person_data):
    """สร้างกราฟแสดงผลการตรวจการได้ยิน (Audiogram) พร้อมแถบสีแสดงเกณฑ์"""
    freq_cols = {
        '500': ('R500', 'L500'), '1000': ('R1k', 'L1k'), '2000': ('R2k', 'L2k'),
        '3000': ('R3k', 'L3k'), '4000': ('R4k', 'L4k'), '6000': ('R6k', 'L6k'),
        '8000': ('R8k', 'L8k')
    }

    freqs = list(freq_cols.keys())
    r_vals = [get_float(person_data, freq_cols[f][0]) for f in freqs]
    l_vals = [get_float(person_data, freq_cols[f][1]) for f in freqs]

    if all(v is None for v in r_vals) and all(v is None for v in l_vals):
        st.info("ไม่มีข้อมูลการตรวจการได้ยินแบบ Audiogram")
        return

    fig = go.Figure()

    levels = {
        "ปกติ": (0, 25, "lightgreen"),
        "เล็กน้อย": (25, 40, "yellow"),
        "ปานกลาง": (40, 70, "orange"),
        "รุนแรง": (70, 120, "lightcoral")
    }
    for name, (start, end, color) in levels.items():
        fig.add_shape(type="rect", xref="paper", yref="y", x0=0, y0=start, x1=1, y1=end,
                      fillcolor=color, opacity=0.2, layer="below", line_width=0)
        fig.add_annotation(x=0.98, y=(start+end)/2, text=name, showarrow=False,
                           xref="paper", yref="y", font=dict(size=10, family="Sarabun"))

    fig.add_trace(go.Scatter(
        x=freqs, y=r_vals, mode='lines+markers', name='หูขวา (Right)',
        line=dict(color='red'), marker=dict(symbol='circle-open', size=12, line=dict(width=2))
    ))

    fig.add_trace(go.Scatter(
        x=freqs, y=l_vals, mode='lines+markers', name='หูซ้าย (Left)',
        line=dict(color='blue'), marker=dict(symbol='x-thin', size=12, line=dict(width=2))
    ))

    fig.update_layout(
        title='ผลการตรวจเทียบกับระดับการสูญเสียการได้ยิน',
        xaxis_title='ความถี่เสียง (Hz)',
        yaxis_title='ระดับการได้ยิน (dB HL)',
        yaxis=dict(autorange='reversed', range=[-10, 120]),
        xaxis=dict(type='category'),
        legend=dict(x=0.01, y=0.99, bordercolor="black", borderwidth=1),
        template="streamlit",
        margin=dict(l=20, r=20, t=40, b=20),
        font_family="Sarabun"
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 4. แดชบอร์ดปัจจัยเสี่ยง ---

def plot_risk_radar(person_data):
    """สร้างกราฟเรดาร์สรุปปัจจัยเสี่ยง พร้อมคำอธิบาย"""
    st.caption("กราฟนี้สรุปปัจจัยเสี่ยง 5 ด้าน ยิ่งพื้นที่สีกว้างและเบ้ไปทางขอบนอก หมายถึงความเสี่ยงโดยรวมสูงขึ้น (ระดับ 1 คือปกติ, 5 คือเสี่ยงสูงมาก)")

    def normalize(value, thresholds, higher_is_better=False):
        if value is None: return 1
        scores = list(range(1, len(thresholds) + 2))
        if higher_is_better:
            thresholds = sorted(thresholds)
            for i, threshold in enumerate(thresholds):
                if value < threshold: return scores[i]
            return scores[-1]
        else: # Lower is better
            thresholds = sorted(thresholds)
            for i, threshold in enumerate(thresholds):
                if value <= threshold: return scores[i]
            return scores[-1]


    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        weight = get_float(person_data, 'น้ำหนัก')
        height = get_float(person_data, 'ส่วนสูง')
        if weight and height:
            bmi = weight / ((height/100)**2)

    categories = ['BMI', 'ความดัน (SBP)', 'น้ำตาล (FBS)', 'ไขมัน (LDL)', 'ไต (GFR)']
    values = [
        normalize(bmi, [22.9, 24.9, 29.9, 35]),
        normalize(get_float(person_data, 'SBP'), [120, 130, 140, 160]),
        normalize(get_float(person_data, 'FBS'), [99, 125, 150, 200]),
        normalize(get_float(person_data, 'LDL'), [129, 159, 189, 220]),
        normalize(get_float(person_data, 'GFR'), [60, 90], higher_is_better=True) # Note: GFR is higher_is_better
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='ระดับความเสี่ยง'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[1, 5],
                tickvals=[1, 2, 3, 4, 5],
                ticktext=['ปกติ', 'เริ่มเสี่ยง', 'เสี่ยง', 'สูง', 'สูงมาก']
            )),
        showlegend=False,
        title="ภาพรวมปัจจัยเสี่ยงโรคไม่ติดต่อเรื้อรัง (NCDs)",
        font_family="Sarabun",
        template="streamlit"
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 5. กราฟแท่งเปรียบเทียบ ---

def plot_lung_comparison(person_data):
    """สร้างกราฟแท่งเปรียบเทียบสมรรถภาพปอด พร้อมแสดงค่าบนแท่ง"""
    fvc_actual = get_float(person_data, 'FVC')
    fvc_pred = get_float(person_data, 'FVC predic')
    fev1_actual = get_float(person_data, 'FEV1')
    fev1_pred = get_float(person_data, 'FEV1 predic')

    if fvc_actual is None or fev1_actual is None:
        st.info("ไม่มีข้อมูลการตรวจสมรรถภาพปอด")
        return

    categories = ['FVC (L)', 'FEV1 (L)']
    actual_vals = [fvc_actual, fev1_actual]
    pred_vals = [fvc_pred, fev1_pred]

    fig = go.Figure(data=[
        go.Bar(name='ค่าที่วัดได้ (Actual)', x=categories, y=actual_vals, text=actual_vals, textposition='auto'),
        go.Bar(name='ค่ามาตรฐาน (Predicted)', x=categories, y=pred_vals, text=pred_vals, textposition='auto')
    ])
    fig.update_traces(texttemplate='%{text:.2f}')
    fig.update_layout(
        barmode='group',
        title='เปรียบเทียบค่าสมรรถภาพปอดกับค่ามาตรฐาน',
        yaxis_title='ลิตร (L)',
        legend_title="ค่า",
        legend=dict(x=0.01, y=0.99),
        font_family="Sarabun",
        template="streamlit"
    )
    st.plotly_chart(fig, use_container_width=True)


# --- ฟังก์ชันหลักสำหรับแสดงผล ---
def display_visualization_tab(person_data, history_df):
    """
    ฟังก์ชันหลักสำหรับแสดงผลแท็บ Visualization ทั้งหมด
    ถูกเรียกจาก app.py และมีการปรับปรุง Layout ใหม่
    """
    st.header(f"📊 ภาพรวมสุขภาพของคุณ: {person_data.get('ชื่อ-สกุล', '')}")
    st.markdown("---")

    # Section 1: Gauges and Radar (Current Year Snapshot)
    with st.container(border=True):
        st.subheader(f"🎯 สรุปผลสุขภาพภาพรวม (ปี พ.ศ. {person_data.get('Year', '')})")

        col1, col2 = st.columns(2)

        with col1:
            plot_risk_radar(person_data)

        with col2:
            plot_bmi_gauge(person_data)
            plot_fbs_gauge(person_data)
            plot_gfr_gauge(person_data)

    # Section 2: Trends (Historical View)
    with st.container(border=True):
        st.subheader("📈 กราฟแสดงแนวโน้มผลสุขภาพย้อนหลัง")
        # --- START OF CHANGE: Pass person_data to handle gender-specific goals ---
        plot_historical_trends(history_df, person_data)
        # --- END OF CHANGE ---

    # Section 3: Performance graphs (Current Year Details)
    with st.container(border=True):
        st.subheader(f" เจาะลึกสมรรถภาพร่างกาย (ปี พ.ศ. {person_data.get('Year', '')})")
        charts_to_plot = [
            {'type': 'audiogram', 'data': person_data},
            {'type': 'lung', 'data': person_data}
        ]

        cols = st.columns(len(charts_to_plot))
        for i, chart in enumerate(charts_to_plot):
            with cols[i]:
                if chart['type'] == 'audiogram':
                    plot_audiogram(chart['data'])
                elif chart['type'] == 'lung':
                    plot_lung_comparison(chart['data'])

