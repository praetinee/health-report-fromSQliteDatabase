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

# --- [ใหม่] ฟังก์ชันหลักสำหรับแสดงผล (จัด Layout ใหม่) ---

def display_visualization_tab(person_data, history_df):
    """
    ฟังก์ชันหลักสำหรับแสดงผลแท็บ Visualization ทั้งหมด
    จัด Layout ใหม่โดยแสดง Dashboard สรุปก่อน และซ่อนรายละเอียดไว้ใน Expander
    """
    st.header(f"📊 ภาพรวมสุขภาพของคุณ: {person_data.get('ชื่อ-สกุล', '')}")
    st.markdown("---")

    # Section 1: Health Dashboard (ใหม่)
    plot_health_dashboard(person_data)

    st.markdown("---")
    
    # Section 2: รายละเอียดเพิ่มเติม (ซ่อนใน Expander)
    with st.expander("คลิกเพื่อดูรายละเอียดเชิงลึกและแนวโน้มย้อนหลัง"):
        
        st.subheader("เจาะลึกผลสุขภาพรายบุคคล")
        col1, col2 = st.columns([2, 3])
        with col1:
            plot_risk_radar(person_data)
        with col2:
            plot_gauge_charts(person_data)
        
        st.markdown("<hr>", unsafe_allow_html=True)

        st.subheader(f"เจาะลึกสมรรถภาพร่างกาย")
        col3, col4 = st.columns(2)
        with col3:
            plot_audiogram(person_data)
        with col4:
            plot_lung_comparison(person_data)
            
        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.subheader("กราฟแสดงแนวโน้มผลสุขภาพย้อนหลัง")
        plot_historical_trends(history_df)

# --- [ใหม่] ส่วนคำนวณคะแนนสุขภาพ (Health Score) ---

def calculate_health_score(person_data):
    """คำนวณคะแนนสุขภาพองค์รวมจากตัวชี้วัดหลัก"""
    scores = {}
    
    # 1. BMI Score (น้ำหนัก 20%)
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        weight = get_float(person_data, 'น้ำหนัก')
        height = get_float(person_data, 'ส่วนสูง')
        if weight and height and height > 0: 
            bmi = weight / ((height/100)**2)
    
    if bmi is not None:
        if 18.5 <= bmi < 23: scores['BMI'] = 100
        elif 23 <= bmi < 25: scores['BMI'] = 75
        elif 25 <= bmi < 30: scores['BMI'] = 50
        else: scores['BMI'] = 25

    # 2. Blood Pressure Score (น้ำหนัก 25%)
    sbp = get_float(person_data, 'SBP')
    if sbp is not None:
        if sbp < 120: scores['SBP'] = 100
        elif sbp < 130: scores['SBP'] = 80
        elif sbp < 140: scores['SBP'] = 60
        elif sbp < 160: scores['SBP'] = 40
        else: scores['SBP'] = 20

    # 3. Blood Sugar Score (น้ำหนัก 25%)
    fbs = get_float(person_data, 'FBS')
    if fbs is not None:
        if fbs < 100: scores['FBS'] = 100
        elif fbs < 126: scores['FBS'] = 70
        else: scores['FBS'] = 40
    
    # 4. LDL Score (น้ำหนัก 15%)
    ldl = get_float(person_data, 'LDL')
    if ldl is not None:
        if ldl < 130: scores['LDL'] = 100
        elif ldl < 160: scores['LDL'] = 70
        elif ldl < 190: scores['LDL'] = 40
        else: scores['LDL'] = 20
        
    # 5. GFR Score (น้ำหนัก 15%)
    gfr = get_float(person_data, 'GFR')
    if gfr is not None:
        if gfr >= 90: scores['GFR'] = 100
        elif gfr >= 60: scores['GFR'] = 80
        elif gfr >= 30: scores['GFR'] = 50
        else: scores['GFR'] = 20

    # คำนวณคะแนนเฉลี่ยแบบถ่วงน้ำหนัก
    weights = {'BMI': 0.20, 'SBP': 0.25, 'FBS': 0.25, 'LDL': 0.15, 'GFR': 0.15}
    total_score = 0
    total_weight = 0
    
    for key, score in scores.items():
        total_score += score * weights[key]
        total_weight += weights[key]
        
    if total_weight == 0: return 0, [], []
    
    final_score = total_score / total_weight
    
    # สรุปจุดแข็งและจุดที่ควรพัฒนา
    positives = [k for k, v in scores.items() if v >= 80]
    improvements = [k for k, v in scores.items() if v < 70]
    
    return final_score, positives, improvements

# --- [ใหม่] Dashboard สรุปภาพรวม ---

def plot_health_dashboard(person_data):
    """สร้าง Dashboard สรุปภาพรวมสุขภาพ ประกอบด้วย Health Score และ Body Map"""
    score, positives, improvements = calculate_health_score(person_data)
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("⭐ Health Score")
        st.caption("คะแนนสุขภาพโดยรวม ประเมินจาก 5 ปัจจัยหลัก ยิ่งคะแนนสูง ยิ่งสุขภาพดี")
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            number={'suffix': "/100"},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "คะแนนสุขภาพองค์รวม", 'font': {'size': 18}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#2E7D32" if score >= 80 else ("#F9A825" if score >= 60 else "#C62828")},
                'steps': [
                    {'range': [0, 60], 'color': 'rgba(220, 53, 69, 0.2)'},
                    {'range': [60, 80], 'color': 'rgba(255, 193, 7, 0.2)'},
                    {'range': [80, 100], 'color': 'rgba(40, 167, 69, 0.2)'}],
            }))
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun")
        st.plotly_chart(fig, use_container_width=True)

        # สรุปจุดแข็ง-จุดอ่อน
        if positives:
            st.success(f"**จุดแข็ง:** {', '.join(positives)} อยู่ในเกณฑ์ดีมาก")
        if improvements:
            st.warning(f"**ควรพัฒนา:** {', '.join(improvements)} ควรให้ความสำคัญเป็นพิเศษ")


    with col2:
        st.subheader("🩺 Health Body Map")
        st.caption("แสดงภาพรวมผลกระทบของสุขภาพต่อร่างกายในส่วนต่างๆ")
        
        # ตรวจสอบความผิดปกติ
        alerts = {}
        if get_float(person_data, 'SBP') and get_float(person_data, 'SBP') >= 140:
            alerts['หัวใจ'] = ('ความดันโลหิตสูง', 'red')
        if get_float(person_data, 'SGPT') and get_float(person_data, 'SGPT') > 41:
            alerts['ตับ'] = ('ค่าเอนไซม์ตับสูง', 'orange')
        if get_float(person_data, 'GFR') and get_float(person_data, 'GFR') < 60:
            alerts['ไต'] = ('การทำงานของไตลดลง', 'orange')
        if get_float(person_data, 'FVC เปอร์เซ็นต์') and get_float(person_data, 'FVC เปอร์เซ็นต์') < 80:
             alerts['ปอด'] = ('ความจุปอดอาจลดลง', 'lightblue')
        summary_r = person_data.get('ผลตรวจการได้ยินหูขวา', '')
        if "ผิดปกติ" in summary_r:
             alerts['หู'] = ('การได้ยินผิดปกติ', 'purple')


        # --- HTML & SVG สำหรับ Body Map ---
        body_map_html = f"""
        <div style="position: relative; width: 100%; max-width: 250px; margin: auto; text-align: center;">
            <svg viewBox="0 0 200 400" xmlns="http://www.w3.org/2000/svg">
                <path fill="#D3D3D3" d="M100 5C70 5 60 25 60 45s10 40 40 40 40-20 40-40-10-40-40-40zm-5 85c-20 0-35 10-35 30v100c0 20-10 70-10 90s-5 30 0 30h100c5 0 0-10 0-30s-10-70-10-90V120c0-20-15-30-35-30h-10z M45 250 c-10 0-15 20-15 40v60c0 10 5 20 15 20s15-10 15-20v-60c0-20-5-40-15-40zm110 0c-10 0-15 20-15 40v60c0 10 5 20 15 20s15-10 15-20v-60c0-20-5-40-15-40z"/>
            </svg>
            {'<div title="หัวใจ: {alerts['หัวใจ'][0]}" style="position: absolute; top: 35%; left: 48%; width: 15px; height: 15px; background: {alerts['หัวใจ'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'หัวใจ' in alerts else ''}
            {'<div title="ตับ: {alerts['ตับ'][0]}" style="position: absolute; top: 42%; left: 55%; width: 15px; height: 15px; background: {alerts['ตับ'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'ตับ' in alerts else ''}
            {'<div title="ไต: {alerts['ไต'][0]}" style="position: absolute; top: 48%; left: 38%; width: 15px; height: 15px; background: {alerts['ไต'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'ไต' in alerts else ''}
            {'<div title="ปอด: {alerts['ปอด'][0]}" style="position: absolute; top: 33%; left: 35%; width: 15px; height: 15px; background: {alerts['ปอด'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'ปอด' in alerts else ''}
            {'<div title="หู: {alerts['หู'][0]}" style="position: absolute; top: 15%; left: 25%; width: 15px; height: 15px; background: {alerts['หู'][1]}; border-radius: 50%; border: 2px solid white;"></div>' if 'หู' in alerts else ''}
        </div>
        <div style="text-align: left; font-size: 0.8rem; margin-top: 1rem;">
            <b>คำอธิบาย:</b>
            <ul style="padding-left: 20px; margin-top: 5px;">
            {'<li><span style="color:red;"><b>หัวใจ:</b></span> {alerts['หัวใจ'][0]}</li>' if 'หัวใจ' in alerts else ''}
            {'<li><span style="color:orange;"><b>ตับ:</b></span> {alerts['ตับ'][0]}</li>' if 'ตับ' in alerts else ''}
            {'<li><span style="color:orange;"><b>ไต:</b></span> {alerts['ไต'][0]}</li>' if 'ไต' in alerts else ''}
            {'<li><span style="color:lightblue;"><b>ปอด:</b></span> {alerts['ปอด'][0]}</li>' if 'ปอด' in alerts else ''}
            {'<li><span style="color:purple;"><b>หู:</b></span> {alerts['หู'][0]}</li>' if 'หู' in alerts else ''}
            </ul>
            {'' if alerts else '<p>ไม่พบความผิดปกติที่สำคัญในร่างกาย</p>'}
        </div>
        """
        st.markdown(body_map_html, unsafe_allow_html=True)


# --- ฟังก์ชันแสดงกราฟเดิม (จะถูกย้ายไปใน Expander) ---

def plot_historical_trends(history_df):
    if history_df.shape[0] < 2:
        st.info("ข้อมูลย้อนหลังไม่เพียงพอ (ต้องการอย่างน้อย 2 ปี)")
        return
    history_df = history_df.sort_values(by="Year", ascending=True).copy()
    min_year, max_year = int(history_df['Year'].min()), int(history_df['Year'].max())
    all_years_df = pd.DataFrame({'Year': range(min_year, max_year + 1)})
    history_df = pd.merge(all_years_df, history_df, on='Year', how='left')
    history_df['BMI'] = history_df.apply(lambda row: (get_float(row, 'น้ำหนัก') / ((get_float(row, 'ส่วนสูง') / 100) ** 2)) if get_float(row, 'น้ำหนัก') and get_float(row, 'ส่วนสูง') and get_float(row, 'ส่วนสูง') > 0 else np.nan, axis=1)
    history_df['Year'] = history_df['Year'].astype(str)
    metric_bands = {'BMI': {"โรคอ้วน": (25, 40, "lightcoral"),"ท้วม": (23, 25, "yellow"),"ปกติ": (18.5, 23, "lightgreen")},'FBS': {"เข้าเกณฑ์เบาหวาน": (126, 200, "lightcoral"),"ภาวะเสี่ยง": (100, 126, "yellow"),"ปกติ": (70, 100, "lightgreen")},'CHOL': {"สูง": (240, 400, "lightcoral"),"เริ่มสูง": (200, 240, "yellow"),"ปกติ": (100, 200, "lightgreen")},'GFR': {"ปกติ": (90, 150, "lightgreen"),"เริ่มเสื่อม": (60, 90, "yellow"),"เสื่อมปานกลาง": (30, 60, "orange"),"เสื่อมรุนแรง": (0, 30, "lightcoral")},'DBP': {},'SBP': {"สูงมาก (ระดับ 2)": (140, 180, "lightcoral"),"สูง (ระดับ 1)": (130, 140, "orange"),"เริ่มสูง": (120, 130, "yellow"),"ปกติ": (90, 120, "lightgreen")}}
    trend_metrics = {'ดัชนีมวลกาย (BMI)': ('BMI', 'kg/m²'),'ระดับน้ำตาลในเลือด (FBS)': ('FBS', 'mg/dL'),'คอเลสเตอรอล (Cholesterol)': ('CHOL', 'mg/dL'),'ประสิทธิภาพการกรองของไต (GFR)': ('GFR', 'mL/min'),'ความดันโลหิต': (['SBP', 'DBP'], 'mmHg')}
    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2, col1]
    for i, (title, (keys, unit)) in enumerate(trend_metrics.items()):
        with cols[i]:
            fig = None
            bands_key = ''
            if isinstance(keys, list):
                df_plot = history_df[['Year', keys[0], keys[1]]]
                fig = px.line(df_plot, x='Year', y=keys, title=title, markers=True)
                bands_key = 'SBP'
                fig.update_layout(yaxis_range=[80,180])
            else:
                df_plot = history_df[['Year', keys]]
                fig = px.line(df_plot, x='Year', y=keys, title=title, markers=True)
                bands_key = keys
            if fig.layout.yaxis.range is None:
                if bands_key in metric_bands and metric_bands[bands_key]:
                    min_range = min(start for start, end, color in metric_bands[bands_key].values())
                    max_range = max(end for start, end, color in metric_bands[bands_key].values())
                    padding = (max_range - min_range) * 0.1
                    fig.update_layout(yaxis_range=[min_range - padding, max_range + padding])
            if bands_key in metric_bands and fig.layout.yaxis.range is not None:
                for name, (start, end, color) in metric_bands[bands_key].items():
                    fig.add_shape(type="rect", xref="paper", yref="y", x0=0, y0=start, x1=1, y1=end,fillcolor=color, opacity=0.2, layer="below", line_width=0)
                    if abs(end - start) > (fig.layout.yaxis.range[1] - fig.layout.yaxis.range[0]) * 0.1:
                         fig.add_annotation(x=0.98, y=(start+end)/2, text=name, showarrow=False,xref="paper", yref="y", font=dict(size=10, family="Sarabun"),xanchor="right")
            fig.update_traces(connectgaps=False)
            fig.update_layout(yaxis_title=unit, xaxis_title='ปี พ.ศ.', legend_title_text='เส้นเลือด' if isinstance(keys, list) else "",font_family="Sarabun",template="streamlit")
            st.plotly_chart(fig, use_container_width=True)

def plot_gauge_charts(person_data):
    st.caption("เกจวัดนี้แสดงค่าสุขภาพที่สำคัญเทียบกับเกณฑ์มาตรฐาน สีเขียวหมายถึงปกติ และจะเปลี่ยนเป็นสีเหลือง ส้ม แดง เมื่อมีความเสี่ยงเพิ่มขึ้น")
    col1, col2, col3 = st.columns(3)
    with col1:
        bmi = get_float(person_data, 'BMI')
        if bmi is None:
             weight = get_float(person_data, 'น้ำหนัก')
             height = get_float(person_data, 'ส่วนสูง')
             if weight and height and height > 0: 
                 bmi = weight / ((height/100)**2)
        if bmi is not None:
            fig = go.Figure(go.Indicator(mode = "gauge+number",value = bmi,title = {'text': "ดัชนีมวลกาย (BMI)"},gauge = {'axis': {'range': [15, 40]},'steps' : [{'range': [15, 18.5], 'color': "lightblue"},{'range': [18.5, 23], 'color': "green"},{'range': [23, 25], 'color': "yellow"},{'range': [25, 30], 'color': "orange"},{'range': [30, 40], 'color': "red"}],'bar': {'color': "darkblue"}}))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        fbs = get_float(person_data, 'FBS')
        if fbs is not None:
            fig = go.Figure(go.Indicator(mode = "gauge+number",value = fbs,title = {'text': "ระดับน้ำตาล (FBS mg/dL)"},gauge = {'axis': {'range': [60, 160]},'steps' : [{'range': [60, 74], 'color': "yellow"},{'range': [74, 100], 'color': "green"},{'range': [100, 126], 'color': "orange"},{'range': [126, 160], 'color': "red"}],'bar': {'color': "darkblue"}}))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)
    with col3:
        gfr = get_float(person_data, 'GFR')
        if gfr is not None:
            fig = go.Figure(go.Indicator(mode = "gauge+number",value = gfr,title = {'text': "การกรองของไต (GFR mL/min)"},gauge = {'axis': {'range': [0, 120]},'steps' : [{'range': [0, 30], 'color': "red"},{'range': [30, 60], 'color': "orange"},{'range': [60, 90], 'color': "yellow"},{'range': [90, 120], 'color': "green"}],'bar': {'color': "darkblue"}}))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=10), font_family="Sarabun", template="streamlit")
            st.plotly_chart(fig, use_container_width=True)

def plot_risk_radar(person_data):
    st.caption("กราฟนี้สรุปปัจจัยเสี่ยง 5 ด้าน ยิ่งพื้นที่สีกว้างและเบ้ไปทางขอบนอก หมายถึงความเสี่ยงโดยรวมสูงขึ้น (ระดับ 1 คือปกติ, 5 คือเสี่ยงสูงมาก)")
    def normalize(value, thresholds, higher_is_better=False):
        if value is None: return 1
        if higher_is_better:
            thresholds = thresholds[::-1]
            for i, threshold in enumerate(thresholds):
                if value >= threshold: return i + 1
            return len(thresholds) + 1
        else:
            for i, threshold in enumerate(thresholds):
                if value <= threshold: return i + 1
            return len(thresholds) + 1
    bmi = get_float(person_data, 'BMI')
    if bmi is None:
        weight = get_float(person_data, 'น้ำหนัก')
        height = get_float(person_data, 'ส่วนสูง')
        if weight and height and height > 0: 
            bmi = weight / ((height/100)**2)
    categories = ['BMI', 'ความดัน (SBP)', 'น้ำตาล (FBS)', 'ไขมัน (LDL)', 'ไต (GFR)']
    values = [normalize(bmi, [22.9, 24.9, 29.9, 35]), normalize(get_float(person_data, 'SBP'), [120, 130, 140, 160]), normalize(get_float(person_data, 'FBS'), [99, 125, 150, 200]), normalize(get_float(person_data, 'LDL'), [129, 159, 189, 220]), normalize(get_float(person_data, 'GFR'), [30, 45, 60, 90], higher_is_better=True)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values,theta=categories,fill='toself',name='ระดับความเสี่ยง'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[1, 5],tickvals=[1, 2, 3, 4, 5],ticktext=['ปกติ', 'เริ่มเสี่ยง', 'เสี่ยง', 'สูง', 'สูงมาก'])),showlegend=False,title="ภาพรวมปัจจัยเสี่ยงโรคไม่ติดต่อเรื้อรัง (NCDs)",font_family="Sarabun",template="streamlit")
    st.plotly_chart(fig, use_container_width=True)

def plot_audiogram(person_data):
    freq_cols = {'500': ('R500', 'L500'), '1000': ('R1k', 'L1k'), '2000': ('R2k', 'L2k'), '3000': ('R3k', 'L3k'), '4000': ('R4k', 'L4k'), '6000': ('R6k', 'L6k'), '8000': ('R8k', 'L8k')}
    freqs = list(freq_cols.keys())
    r_vals = [get_float(person_data, freq_cols[f][0]) for f in freqs]
    l_vals = [get_float(person_data, freq_cols[f][1]) for f in freqs]
    if all(v is None for v in r_vals) and all(v is None for v in l_vals):
        st.info("ไม่มีข้อมูลการตรวจการได้ยินแบบ Audiogram")
        return
    fig = go.Figure()
    levels = {"ปกติ": (0, 25, "lightgreen"),"เล็กน้อย": (25, 40, "yellow"),"ปานกลาง": (40, 70, "orange"),"รุนแรง": (70, 120, "lightcoral")}
    for name, (start, end, color) in levels.items():
        fig.add_shape(type="rect", xref="paper", yref="y", x0=0, y0=start, x1=1, y1=end,fillcolor=color, opacity=0.2, layer="below", line_width=0)
        fig.add_annotation(x=0.98, y=(start+end)/2, text=name, showarrow=False,xref="paper", yref="y", font=dict(size=10, family="Sarabun"))
    fig.add_trace(go.Scatter(x=freqs, y=r_vals, mode='lines+markers', name='หูขวา (Right)',line=dict(color='red'), marker=dict(symbol='circle-open', size=12, line=dict(width=2))))
    fig.add_trace(go.Scatter(x=freqs, y=l_vals, mode='lines+markers', name='หูซ้าย (Left)',line=dict(color='blue'), marker=dict(symbol='x-thin', size=12, line=dict(width=2))))
    fig.update_layout(title='ผลการตรวจเทียบกับระดับการสูญเสียการได้ยิน',xaxis_title='ความถี่เสียง (Hz)',yaxis_title='ระดับการได้ยิน (dB HL)',yaxis=dict(autorange='reversed', range=[-10, 120]),xaxis=dict(type='category'),legend=dict(x=0.01, y=0.99, bordercolor="black", borderwidth=1),template="streamlit",margin=dict(l=20, r=20, t=40, b=20),font_family="Sarabun")
    st.plotly_chart(fig, use_container_width=True)

def plot_lung_comparison(person_data):
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
    fig = go.Figure(data=[go.Bar(name='ค่าที่วัดได้ (Actual)', x=categories, y=actual_vals, text=actual_vals, textposition='auto'),go.Bar(name='ค่ามาตรฐาน (Predicted)', x=categories, y=pred_vals, text=pred_vals, textposition='auto')])
    fig.update_traces(texttemplate='%{text:.2f}')
    fig.update_layout(barmode='group',title='เปรียบเทียบค่าสมรรถภาพปอดกับค่ามาตรฐาน',yaxis_title='ลิตร (L)',legend_title="ค่า",legend=dict(x=0.01, y=0.99),font_family="Sarabun",template="streamlit")
    st.plotly_chart(fig, use_container_width=True)

