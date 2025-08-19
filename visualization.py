# visualization.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# --- Helper Functions ---

def get_float(person_data, key):
    """ดึงค่า float จาก dictionary อย่างปลอดภัย"""
    val = person_data.get(key, "")
    if pd.isna(val) or str(val).strip().lower() in ["", "-", "none", "nan", "null"]:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None

# --- 1. Historical Trend Graphs ---

def plot_historical_trends(history_df):
    """สร้างกราฟเส้นแสดงแนวโน้มข้อมูลสุขภาพย้อนหลัง"""
    st.subheader("📈 กราฟแสดงแนวโน้มผลสุขภาพย้อนหลัง (Historical Trends)")

    if history_df.shape[0] < 2:
        st.info("ข้อมูลย้อนหลังไม่เพียงพอที่จะสร้างกราฟแนวโน้ม (ต้องการอย่างน้อย 2 ปี)")
        return

    history_df = history_df.sort_values(by="Year", ascending=True).copy()
    history_df['Year_str'] = history_df['Year'].astype(str)

    # คำนวณ BMI สำหรับข้อมูลย้อนหลัง
    history_df['BMI'] = history_df.apply(
        lambda row: (get_float(row, 'น้ำหนัก') / ((get_float(row, 'ส่วนสูง') / 100) ** 2))
        if get_float(row, 'น้ำหนัก') and get_float(row, 'ส่วนสูง') else None,
        axis=1
    )

    trend_metrics = {
        'ดัชนีมวลกาย (BMI)': 'BMI',
        'ระดับน้ำตาลในเลือด (FBS)': 'FBS',
        'คอเลสเตอรอล (Cholesterol)': 'CHOL',
        'ประสิทธิภาพการกรองของไต (GFR)': 'GFR',
        'ความดันโลหิต (SBP/DBP)': ['SBP', 'DBP']
    }

    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2, col1]
    
    for i, (title, keys) in enumerate(trend_metrics.items()):
        with cols[i]:
            if isinstance(keys, list): # กรณีความดันโลหิต
                df_plot = history_df[['Year_str', keys[0], keys[1]]].dropna()
                if not df_plot.empty:
                    fig = px.line(df_plot, x='Year_str', y=keys, title=title, markers=True,
                                  labels={'value': 'ค่า (mmHg)', 'Year_str': 'ปี พ.ศ.'})
                    fig.update_layout(legend_title_text='เส้นเลือด')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                df_plot = history_df[['Year_str', keys]].dropna()
                if not df_plot.empty:
                    fig = px.line(df_plot, x='Year_str', y=keys, title=title, markers=True,
                                  labels={'value': 'ค่า', 'Year_str': 'ปี พ.ศ.'})
                    st.plotly_chart(fig, use_container_width=True)


# --- 2. Gauge Charts ---

def plot_gauge_charts(person_data):
    """สร้างเกจวัดสำหรับข้อมูลสุขภาพที่สำคัญ"""
    st.subheader("🎯 เกจวัดผลสุขภาพ (Health Gauges)")

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
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        fbs = get_float(person_data, 'FBS')
        if fbs is not None:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = fbs,
                title = {'text': "ระดับน้ำตาล (FBS)"},
                gauge = {
                    'axis': {'range': [60, 160]},
                    'steps' : [
                        {'range': [60, 74], 'color': "yellow"},
                        {'range': [74, 100], 'color': "green"},
                        {'range': [100, 126], 'color': "orange"},
                        {'range': [126, 160], 'color': "red"}],
                    'bar': {'color': "darkblue"}
                }))
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with col3:
        gfr = get_float(person_data, 'GFR')
        if gfr is not None:
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = gfr,
                title = {'text': "การกรองของไต (GFR)"},
                gauge = {
                    'axis': {'range': [0, 120]},
                    'steps' : [
                        {'range': [0, 30], 'color': "red"},
                        {'range': [30, 60], 'color': "orange"},
                        {'range': [60, 90], 'color': "yellow"},
                        {'range': [90, 120], 'color': "green"}],
                    'bar': {'color': "darkblue"}
                }))
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)


# --- 3. Audiogram Chart ---

def plot_audiogram(person_data):
    """สร้างกราฟแสดงผลการตรวจการได้ยิน (Audiogram)"""
    st.subheader("👂 กราฟแสดงผลการตรวจการได้ยิน (Audiogram)")

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

    fig.add_trace(go.Scatter(
        x=freqs, y=r_vals,
        mode='lines+markers',
        name='หูขวา (Right)',
        line=dict(color='red'),
        marker=dict(symbol='circle', size=10)
    ))

    fig.add_trace(go.Scatter(
        x=freqs, y=l_vals,
        mode='lines+markers',
        name='หูซ้าย (Left)',
        line=dict(color='blue'),
        marker=dict(symbol='x', size=10)
    ))

    fig.update_layout(
        title='ผลการตรวจสมรรถภาพการได้ยิน',
        xaxis_title='ความถี่เสียง (Hz)',
        yaxis_title='ระดับการได้ยิน (dB)',
        yaxis=dict(autorange='reversed', range=[-10, 120]),
        xaxis=dict(type='category'),
        legend_title="หู",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 4. Risk Factor Dashboard ---

def plot_risk_radar(person_data):
    """สร้างกราฟเรดาร์สรุปปัจจัยเสี่ยง"""
    st.subheader("🕸️ กราฟเรดาร์สรุปปัจจัยเสี่ยง (Risk Factor Radar)")

    def normalize(value, thresholds):
        if value is None: return 1
        for i, threshold in enumerate(thresholds):
            if value <= threshold:
                return i + 1
        return len(thresholds) + 1

    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        weight = get_float(person_data, 'น้ำหนัก')
        height = get_float(person_data, 'ส่วนสูง')
        if weight and height:
            bmi = weight / ((height/100)**2)

    categories = ['BMI', 'ความดัน (SBP)', 'น้ำตาล (FBS)', 'ไขมัน (LDL)', 'ไต (GFR)']
    values = [
        normalize(bmi, [18.5, 23, 25, 30]),
        normalize(get_float(person_data, 'SBP'), [120, 130, 140, 160]),
        normalize(get_float(person_data, 'FBS'), [100, 126, 150, 200]),
        normalize(get_float(person_data, 'LDL'), [130, 160, 190, 220]),
        6 - normalize(get_float(person_data, 'GFR'), [30, 60, 90, 120]) # Invert GFR score
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
        title="ภาพรวมปัจจัยเสี่ยงโรคไม่ติดต่อเรื้อรัง (NCDs)"
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 5. Bar Charts for Comparison ---

def plot_lung_comparison(person_data):
    """สร้างกราฟแท่งเปรียบเทียบสมรรถภาพปอด"""
    st.subheader("📊 กราฟแท่งเปรียบเทียบสมรรถภาพปอด (Spirometry)")

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
        go.Bar(name='ค่าที่วัดได้ (Actual)', x=categories, y=actual_vals),
        go.Bar(name='ค่ามาตรฐาน (Predicted)', x=categories, y=pred_vals)
    ])

    fig.update_layout(
        barmode='group',
        title='เปรียบเทียบค่าสมรรถภาพปอดกับค่ามาตรฐาน',
        yaxis_title='ลิตร (L)',
        legend_title="ค่า"
    )
    st.plotly_chart(fig, use_container_width=True)


# --- Main Display Function ---

def display_visualization_tab(person_data, history_df):
    """
    ฟังก์ชันหลักสำหรับแสดงผลแท็บ Visualization ทั้งหมด
    จะถูกเรียกจาก app.py
    """
    st.header(f"ภาพรวมสุขภาพของคุณ: {person_data.get('ชื่อ-สกุล', '')}")
    st.markdown("---")

    # Section 1: Gauges
    plot_gauge_charts(person_data)
    st.markdown("---")

    # Section 2: Trends in Expander
    with st.expander("คลิกเพื่อดูกราฟแนวโน้มย้อนหลัง", expanded=False):
        plot_historical_trends(history_df)
    st.markdown("---")
    
    # Section 3: Performance graphs
    col1, col2 = st.columns(2)
    with col1:
        plot_audiogram(person_data)
    with col2:
        plot_lung_comparison(person_data)
    st.markdown("---")

    # Section 4: Risk Radar
    plot_risk_radar(person_data)
