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


# --- START OF CHANGE: Add helper for hover text ---
def get_interpretation_text(metric, value):
    """สร้างข้อความแปลผลสำหรับใช้ใน hover tooltip ของกราฟ"""
    if pd.isna(value):
        return ""
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
# --- END OF CHANGE ---

# --- 1. กราฟแสดงแนวโน้มย้อนหลัง ---
# --- START OF CHANGE: Overhaul historical trends plot ---
def plot_historical_trends(history_df):
    """
    สร้างกราฟเส้นแสดงแนวโน้มข้อมูลสุขภาพย้อนหลัง
    พร้อมเส้นเป้าหมาย, เส้นคาดการณ์อนาคต, และคำอธิบายใน tooltip ที่ดีขึ้น
    """
    st.caption("กราฟนี้แสดงการเปลี่ยนแปลงของค่าต่างๆ ในแต่ละปีที่มีการตรวจ พร้อมเส้นคาดการณ์แนวโน้มในอีก 2 ปีข้างหน้า (เส้นประ) และเส้นเกณฑ์สุขภาพ (เส้นสีเขียว)")

    if history_df.shape[0] < 2:
        st.info("ข้อมูลย้อนหลังไม่เพียงพอที่จะสร้างกราฟแนวโน้ม (ต้องการอย่างน้อย 2 ปี)")
        return

    history_df = history_df.sort_values(by="Year", ascending=True).copy()

    # Create a full year range to show gaps in data
    min_year, max_year = int(history_df['Year'].min()), int(history_df['Year'].max())
    all_years_df = pd.DataFrame({'Year': range(min_year, max_year + 1)})
    history_df = pd.merge(all_years_df, history_df, on='Year', how='left')

    # Calculate BMI for historical data
    history_df['BMI'] = history_df.apply(
        lambda row: (get_float(row, 'น้ำหนัก') / ((get_float(row, 'ส่วนสูง') / 100) ** 2))
        if get_float(row, 'น้ำหนัก') and get_float(row, 'ส่วนสูง') else np.nan,
        axis=1
    )
    
    # Define metrics, their keys, units, and goals
    trend_metrics = {
        'ดัชนีมวลกาย (BMI)': ('BMI', 'kg/m²', 23.0, 'range'),
        'ระดับน้ำตาลในเลือด (FBS)': ('FBS', 'mg/dL', 100.0, 'lower'),
        'คอเลสเตอรอล (Cholesterol)': ('CHOL', 'mg/dL', 200.0, 'lower'),
        'ประสิทธิภาพการกรองของไต (GFR)': ('GFR', 'mL/min', 90.0, 'higher'),
        'ความดันโลหิต': (['SBP', 'DBP'], 'mmHg', 120.0, 'lower')
    }
    
    # Prepare data for plotting, including interpretation text for tooltips
    for title, (keys, unit, goal, *_) in trend_metrics.items():
        if isinstance(keys, list):
            for key in keys:
                 history_df[f'{key}_interp'] = history_df[key].apply(lambda x: get_interpretation_text(key, x))
        else:
            history_df[f'{keys}_interp'] = history_df[keys].apply(lambda x: get_interpretation_text(keys, x))

    history_df['Year_str'] = history_df['Year'].astype(str)

    # Layout for plots
    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2, col1]
    
    for i, (title, (keys, unit, goal, direction_type)) in enumerate(trend_metrics.items()):
        with cols[i]:
            fig = None
            is_bp_chart = isinstance(keys, list)
            icon = "🩸" if is_bp_chart else "📊"

            # Add direction text to the title
            if direction_type == 'higher':
                direction_text = "(ยิ่งสูงยิ่งดี)"
            elif direction_type == 'range':
                direction_text = "(ควรอยู่ในเกณฑ์)"
            else: # Default to 'lower'
                direction_text = "(ยิ่งต่ำยิ่งดี)"
            full_title = f"{icon} {title} <br><span style='font-size:0.8em;color:gray;'>{direction_text}</span>"


            # Create the base figure
            if is_bp_chart: # Blood Pressure plot
                df_plot = history_df[['Year_str', keys[0], keys[1], f'{keys[0]}_interp', f'{keys[1]}_interp']]
                fig = px.line(df_plot, x='Year_str', y=keys, title=full_title, markers=True)
                fig.data[0].name = 'SBP'
                fig.data[1].name = 'DBP'
                fig.update_traces(
                    hovertemplate='<b>%{x}</b><br>%{data.name}: %{y:.0f}'+ f' mmHg<extra></extra>'
                )

            else: # Single metric plot
                df_plot = history_df[['Year_str', keys, f'{keys}_interp']]
                fig = px.line(df_plot, x='Year_str', y=keys, title=full_title, markers=True,
                              custom_data=[keys, f'{keys}_interp'])
                fig.update_traces(hovertemplate='<b>%{x}</b><br>%{customdata[0]:.1f} ' + unit + '%{customdata[1]}<extra></extra>')

            # Add Goal Line
            fig.add_hline(y=goal, line_width=2, line_dash="dash", line_color="green",
                          annotation_text="เกณฑ์", annotation_position="bottom right")

            # Add Prediction Line
            predict_key = keys[0] if is_bp_chart else keys
            
            clean_df = history_df[['Year', predict_key]].dropna()
            if len(clean_df) >= 3:
                x_fit = clean_df['Year']
                y_fit = clean_df[predict_key]
                
                model = np.polyfit(x_fit, y_fit, 1)
                predict = np.poly1d(model)
                
                future_years = np.array([max_year + 1, max_year + 2])
                predicted_values = predict(future_years)
                
                all_future_years = np.insert(future_years, 0, max_year)
                all_predicted_values = np.insert(predicted_values, 0, predict(max_year))

                fig.add_trace(go.Scatter(
                    x=all_future_years.astype(str), y=all_predicted_values, mode='lines',
                    line=dict(color='rgba(128,128,128,0.7)', width=2, dash='dot'),
                    name='คาดการณ์',
                    hovertemplate='คาดการณ์ปี %{x}: %{y:.1f}<extra></extra>'
                ))
            
            # Final Touches
            fig.update_traces(connectgaps=False)
            fig.update_layout(
                yaxis_title=unit, 
                xaxis_title='ปี พ.ศ.', 
                legend_title_text="",
                font_family="Sarabun",
                template="streamlit",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

# --- END OF CHANGE ---


# --- 2. เกจวัด ---

def plot_gauge_charts(person_data):
    """สร้างเกจวัดสำหรับข้อมูลสุขภาพที่สำคัญ พร้อมคำอธิบาย"""
    col1, col2, col3 = st.columns(3)

    with col1:
        bmi = get_float(person_data, 'BMI')
        if bmi is None:
             weight = get_float(person_data, 'น้ำหนัก')
             height = get_float(person_data, 'ส่วนสูง')
             if weight and height:
                 bmi = weight / ((height/100)**2)

        if bmi is not None:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = bmi,
                title = {'text': "ดัชนีมวลกาย (BMI)"},
                gauge = {
                    'axis': {'range': [15, 40]},
                    'steps' : [
                        {'range': [15, 18.5], 'color': "lightblue"},
                        {'range': [18.5, 23], 'color': "green"},
                        {'range': [23, 25], 'color': "yellow"},
                        {'range': [25, 30], 'color': "orange"},
                        {'range': [30, 40], 'color': "red"}],
                    'bar': {'color': "darkblue"}
                }))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"<p style='text-align: center; font-weight: bold;'>ผล: {get_bmi_desc(bmi)}</p>", unsafe_allow_html=True)


    with col2:
        fbs = get_float(person_data, 'FBS')
        if fbs is not None:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = fbs,
                title = {'text': "ระดับน้ำตาล (FBS mg/dL)"},
                gauge = {
                    'axis': {'range': [60, 160]},
                    'steps' : [
                        {'range': [60, 74], 'color': "yellow"},
                        {'range': [74, 100], 'color': "green"},
                        {'range': [100, 126], 'color': "orange"},
                        {'range': [126, 160], 'color': "red"}],
                    'bar': {'color': "darkblue"}
                }))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"<p style='text-align: center; font-weight: bold;'>ผล: {get_fbs_desc(fbs)}</p>", unsafe_allow_html=True)


    with col3:
        gfr = get_float(person_data, 'GFR')
        if gfr is not None:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = gfr,
                title = {'text': "การกรองของไต (GFR mL/min)"},
                gauge = {
                    'axis': {'range': [0, 120]},
                    'steps' : [
                        {'range': [0, 30], 'color': "red"},
                        {'range': [30, 60], 'color': "orange"},
                        {'range': [60, 90], 'color': "yellow"},
                        {'range': [90, 120], 'color': "green"}],
                    'bar': {'color': "darkblue"}
                }))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"<p style='text-align: center; font-weight: bold;'>ผล: {get_gfr_desc(gfr)}</p>", unsafe_allow_html=True)



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
        normalize(get_float(person_data, 'GFR'), [60, 90], higher_is_better=True)
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
# --- START OF CHANGE: Add icons and adjust layout in main display function ---
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
        col1, col2 = st.columns([2, 3])
        with col1:
            plot_risk_radar(person_data)
        with col2:
            plot_gauge_charts(person_data)

    # Section 2: Trends (Historical View)
    with st.container(border=True):
        st.subheader("📈 กราฟแสดงแนวโน้มผลสุขภาพย้อนหลัง")
        plot_historical_trends(history_df)

    # Section 3: Performance graphs (Current Year Details)
    with st.container(border=True):
        st.subheader(f" เจาะลึกสมรรถภาพร่างกาย (ปี พ.ศ. {person_data.get('Year', '')})")
        col3, col4 = st.columns(2)
        with col3:
            plot_audiogram(person_data)
        with col4:
            plot_lung_comparison(person_data)
# --- END OF CHANGE ---

