import streamlit as st
from performance_tests import get_recommendation_data

def display_recommendation_pyramid(person_data):
    """
    แสดงผล Infographic พีระมิดสุขภาพ
    """
    
    issues, health_plan = get_recommendation_data(person_data)
    
    if not issues and not health_plan:
        st.warning("ไม่พบข้อมูลเพียงพอสำหรับสร้างพีระมิดสุขภาพ")
        return

    # --- CSS for the Pyramid ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        .pyramid-container {
            font-family: 'Sarabun', sans-serif !important;
            display: flex;
            flex-direction: column-reverse; /* นี่คือส่วนสำคัญที่ทำให้ฐานอยู่ล่างสุด */
            align-items: center;
            gap: 4px;
            margin: 2rem auto;
            max-width: 800px;
        }
        
        .pyramid-layer {
            width: 100%;
            padding: 1.5rem 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        
        .pyramid-layer:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.1);
        }

        .pyramid-layer h3 {
            margin-top: 0;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid rgba(255,255,255,0.4);
            display: flex;
            align-items: center;
            font-size: 1.5rem;
            font-weight: 700;
        }
        
        .pyramid-layer ul {
            margin: 0;
            padding-left: 20px;
        }
        
        .pyramid-layer li {
            font-size: 1rem;
            margin-bottom: 0.5rem;
            line-height: 1.5;
        }

        /* --- Base: High Priority (เร่งด่วน) --- */
        .layer-high {
            background: linear-gradient(135deg, #d32f2f, #b71c1c);
            color: white;
            width: 100%; /* ฐานกว้างสุด */
        }
        .layer-high h3 svg { margin-right: 10px; }

        /* --- Middle: Medium Priority (ควรปรับ) --- */
        .layer-medium {
            background: linear-gradient(135deg, #fbc02d, #f9a825);
            color: #333;
            width: 90%; /* แคบลง */
        }
        .layer-medium h3 svg { margin-right: 10px; }
        .layer-medium ul { color: #504416; }

        /* --- Top: Low Priority (เฝ้าระวัง) --- */
        .layer-low {
            background: linear-gradient(135deg, #1976d2, #0d47a1);
            color: white;
            width: 80%; /* แคบสุด */
        }
        .layer-low h3 svg { margin-right: 10px; }

        /* --- No Data Card --- */
        .layer-good {
            background: linear-gradient(135deg, #388e3c, #1b5e20);
            color: white;
            width: 100%;
            text-align: center;
        }
        .layer-good h3 svg { margin-right: 10px; }
        
        /* --- Health Plan Section --- */
        .health-plan-container {
            max-width: 800px;
            margin: 2rem auto;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            background-color: var(--secondary-background-color);
            padding: 1.5rem;
        }
        .health-plan-container h4 {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--primary-color);
            margin-top: 0;
            margin-bottom: 1rem;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        .plan-columns {
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
        }
        .plan-column {
            flex: 1;
            min-width: 200px;
        }
        .plan-column h5 {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-color);
            opacity: 0.8;
            margin-top: 0;
            margin-bottom: 0.5rem;
        }
        .plan-column ul {
            padding-left: 20px;
            margin: 0;
        }
        .plan-column li {
            font-size: 0.95rem;
            margin-bottom: 0.25rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HTML Structure ---
    
    if not any(issues.values()):
        # กรณีสุขภาพดี
        st.markdown("""
        <div class="pyramid-container">
            <div class="pyramid-layer layer-good">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    สุขภาพโดยรวมอยู่ในเกณฑ์ดี
                </h3>
                <p>ไม่พบความผิดปกติที่มีนัยสำคัญ ขอแนะนำให้รักษาสุขภาพที่ดีเช่นนี้ต่อไปครับ</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # กรณีมีประเด็นสุขภาพ
        st.markdown('<div class="pyramid-container">', unsafe_allow_html=True)
        
        # --- Base Layer (High Priority) ---
        if issues['high']:
            items_html = "".join([f"<li>{item}</li>" for item in set(issues['high'])])
            st.markdown(f"""
            <div class="pyramid-layer layer-high">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" x2="12" y1="8" y2="12"></line><line x1="12" x2="12.01" y1="16" y2="16"></line></svg>
                    ฐานที่ 1: ควรพบแพทย์ (เร่งด่วน)
                </h3>
                <ul>{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)

        # --- Middle Layer (Medium Priority) ---
        if issues['medium']:
            items_html = "".join([f"<li>{item}</li>" for item in set(issues['medium'])])
            st.markdown(f"""
            <div class="pyramid-layer layer-medium">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg>
                    ฐานที่ 2: ควรปรับพฤติกรรม (สำคัญ)
                </h3>
                <ul>{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)

        # --- Top Layer (Low Priority) ---
        if issues['low']:
            items_html = "".join([f"<li>{item}</li>" for item in set(issues['low'])])
            st.markdown(f"""
            <div class="pyramid-layer layer-low">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><info-icon><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></info-icon></svg>
                    ฐานที่ 3: เฝ้าระวังและป้องกัน
                </h3>
                <ul>{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Health Plan Section ---
    if health_plan and any(health_plan.values()):
        st.markdown('<div class="health-plan-container">', unsafe_allow_html=True)
        st.markdown('<h4>แผนการดูแลสุขภาพ (Your Health Plan)</h4>', unsafe_allow_html=True)
        st.markdown('<div class="plan-columns">', unsafe_allow_html=True)

        if health_plan['nutrition']:
            items_html = "".join([f"<li>{item}</li>" for item in sorted(list(health_plan['nutrition']))])
            st.markdown(f'<div class="plan-column"><h5>🥗 ด้านโภชนาการ</h5><ul>{items_html}</ul></div>', unsafe_allow_html=True)
            
        if health_plan['exercise']:
            items_html = "".join([f"<li>{item}</li>" for item in sorted(list(health_plan['exercise']))])
            st.markdown(f'<div class="plan-column"><h5>🏃 ด้านการออกกำลังกาย</h5><ul>{items_html}</ul></div>', unsafe_allow_html=True)

        if health_plan['monitoring']:
            items_html = "".join([f"<li>{item}</li>" for item in sorted(list(health_plan['monitoring']))])
            st.markdown(f'<div class="plan-column"><h5>🔬 การติดตาม/ดูแลทั่วไป</h5><ul>{items_html}</ul></div>', unsafe_allow_html=True)

        st.markdown('</div></div>', unsafe_allow_html=True)

