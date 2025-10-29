import streamlit as st
from performance_tests import get_recommendation_data

def display_recommendation_pyramid(person_data):
    """
    แสดงผล Infographic พีระมิดปรับพฤติกรรม
    """
    # --- START OF CHANGE: Use health_plan_by_severity ---
    issues, health_plan_by_severity = get_recommendation_data(person_data)

    # Check if there are any recommendations at all
    has_recommendations = any(health_plan_by_severity.values())

    if not has_recommendations:
        st.warning("ไม่พบข้อมูลเพียงพอสำหรับสร้างพีระมิดปรับพฤติกรรม")
        return
    # --- END OF CHANGE ---

    # --- CSS for the Pyramid ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');

        .pyramid-graphic-container {
            font-family: 'Sarabun', sans-serif !important;
            display: flex;
            flex-direction: column; /* Stack layers vertically */
            align-items: center;
            margin: 2rem auto;
            max-width: 600px; /* Adjust width as needed */
            position: relative; /* Needed for absolute positioning if using triangles */
        }

        .pyramid-graphic-layer {
            width: 100%;
            padding: 1.5rem 2rem;
            margin-bottom: -20px; /* Overlap layers slightly */
            clip-path: polygon(10% 0%, 90% 0%, 100% 100%, 0% 100%); /* Basic trapezoid */
            border-radius: 0; /* Remove rounding for sharp edges */
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            position: relative; /* Ensure text stays within */
            z-index: 1; /* Default stack order */
        }

        /* Adjust clip-path and width for pyramid shape */
        .layer-graphic-high {
            background: linear-gradient(135deg, #d32f2f, #b71c1c);
            color: white;
            clip-path: polygon(0% 100%, 100% 100%, 90% 0%, 10% 0%); /* Base trapezoid */
            width: 100%;
            z-index: 1; /* Base layer */
             padding-top: 2.5rem; /* Add padding to push content down from clipped top */
             padding-bottom: 1.5rem;
        }

        .layer-graphic-medium {
            background: linear-gradient(135deg, #fbc02d, #f9a825);
            color: #333;
            clip-path: polygon(10% 100%, 90% 100%, 80% 0%, 20% 0%); /* Middle trapezoid */
            width: 80%;
            z-index: 2; /* Above base */
             padding-top: 2.5rem;
             padding-bottom: 1.5rem;
        }
         .layer-graphic-medium ul { color: #504416; }

        .layer-graphic-low {
            background: linear-gradient(135deg, #1976d2, #0d47a1);
            color: white;
            clip-path: polygon(20% 100%, 80% 100%, 70% 0%, 30% 0%); /* Top trapezoid */
            width: 60%;
            z-index: 3; /* Top layer */
            padding-top: 2.5rem;
            padding-bottom: 1.5rem;
        }

         /* Single Layer Styling */
        .single-layer {
            clip-path: polygon(50% 0%, 100% 100%, 0% 100%); /* Triangle */
             width: 80%; /* Adjust width for single triangle */
             margin-bottom: 0; /* No overlap needed */
             padding-top: 3rem; /* More padding for triangle top */
             padding-bottom: 1.5rem;
        }
         /* Apply single layer colors */
        .single-layer.layer-graphic-high { background: linear-gradient(135deg, #d32f2f, #b71c1c); color: white; }
        .single-layer.layer-graphic-medium { background: linear-gradient(135deg, #fbc02d, #f9a825); color: #333; }
        .single-layer.layer-graphic-low { background: linear-gradient(135deg, #1976d2, #0d47a1); color: white; }


        .pyramid-graphic-layer:hover {
            transform: scale(1.02); /* Slight zoom on hover */
            z-index: 10; /* Bring hovered layer to front */
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }

        .pyramid-graphic-layer h3 {
            margin-top: 0;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid rgba(255,255,255,0.4);
            display: flex;
            align-items: center;
            justify-content: center; /* Center title */
            font-size: 1.3rem; /* Adjust size */
            font-weight: 700;
            text-align: center;
        }
         .layer-graphic-medium h3 { border-bottom-color: rgba(0,0,0,0.2); } /* Darker border for yellow */


        .pyramid-graphic-layer h3 svg { margin-right: 10px; }

        .pyramid-graphic-layer ul {
            margin: 0;
            padding-left: 20px;
            list-style-type: '👉 '; /* Emoji bullet point */
        }

        .pyramid-graphic-layer li {
            font-size: 0.95rem; /* Adjust font size */
            margin-bottom: 0.5rem;
            line-height: 1.6;
        }


        /* --- Healthy/Good Card --- */
        .layer-graphic-good {
            background: linear-gradient(135deg, #388e3c, #1b5e20);
            color: white;
            width: 80%; /* Match single layer width */
            text-align: center;
            clip-path: polygon(50% 0%, 100% 100%, 0% 100%); /* Triangle */
             margin-bottom: 0;
             padding-top: 3rem;
             padding-bottom: 1.5rem;
        }
        .layer-graphic-good h3 svg { margin-right: 10px; }
        .layer-graphic-good p { font-size: 1rem; }

    </style>
    """, unsafe_allow_html=True)

    # --- Determine Layers to Display ---
    layers_to_display = []
    if health_plan_by_severity['high']:
        layers_to_display.append('high')
    if health_plan_by_severity['medium']:
        layers_to_display.append('medium')
    if health_plan_by_severity['low']:
        layers_to_display.append('low')

    num_layers = len(layers_to_display)

    # --- HTML Structure ---
    st.markdown('<div class="pyramid-graphic-container">', unsafe_allow_html=True)

    if num_layers == 0:
        # กรณีสุขภาพดี (ไม่มีคำแนะนำใดๆ)
        st.markdown("""
            <div class="pyramid-graphic-layer layer-graphic-good single-layer">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    สุขภาพดี เยี่ยมเลย!
                </h3>
                <p>ไม่มีคำแนะนำการปรับพฤติกรรมเพิ่มเติม<br>รักษาสุขภาพที่ดีแบบนี้ต่อไปนะครับ</p>
            </div>
        """, unsafe_allow_html=True)
    elif num_layers == 1:
        # กรณีมีชั้นเดียว
        severity = layers_to_display[0]
        items_html = "".join([f"<li>{item}</li>" for item in sorted(list(health_plan_by_severity[severity]))])
        title_text = {
            'high': "ฐานที่ 1: ควรพบแพทย์ (เร่งด่วน)",
            'medium': "ฐานที่ 2: ควรปรับพฤติกรรม (สำคัญ)",
            'low': "ฐานที่ 3: เฝ้าระวังและป้องกัน"
        }[severity]
        icon_svg = {
            'high': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" x2="12" y1="8" y2="12"></line><line x1="12" x2="12.01" y1="16" y2="16"></line></svg>',
            'medium': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg>',
            'low': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><info-icon><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></info-icon></svg>'
        }[severity]

        st.markdown(f"""
            <div class="pyramid-graphic-layer layer-graphic-{severity} single-layer">
                <h3>{icon_svg}{title_text}</h3>
                <ul>{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)

    else:
        # กรณีมีหลายชั้น (แสดงผลจาก low -> medium -> high เพราะ CSS ใช้ column-reverse)
        if 'low' in layers_to_display and health_plan_by_severity['low']:
            items_html = "".join([f"<li>{item}</li>" for item in sorted(list(health_plan_by_severity['low']))])
            st.markdown(f"""
            <div class="pyramid-graphic-layer layer-graphic-low">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><info-icon><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></info-icon></svg>
                    ฐานที่ 3: เฝ้าระวังและป้องกัน
                </h3>
                <ul>{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)

        if 'medium' in layers_to_display and health_plan_by_severity['medium']:
            items_html = "".join([f"<li>{item}</li>" for item in sorted(list(health_plan_by_severity['medium']))])
            st.markdown(f"""
            <div class="pyramid-graphic-layer layer-graphic-medium">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" x2="12" y1="9" y2="13"></line><line x1="12" x2="12.01" y1="17" y2="17"></line></svg>
                    ฐานที่ 2: ควรปรับพฤติกรรม (สำคัญ)
                </h3>
                <ul>{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)

        if 'high' in layers_to_display and health_plan_by_severity['high']:
            items_html = "".join([f"<li>{item}</li>" for item in sorted(list(health_plan_by_severity['high']))])
            st.markdown(f"""
            <div class="pyramid-graphic-layer layer-graphic-high">
                <h3>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" x2="12" y1="8" y2="12"></line><line x1="12" x2="12.01" y1="16" y2="16"></line></svg>
                    ฐานที่ 1: ควรพบแพทย์ (เร่งด่วน)
                </h3>
                <ul>{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # --- Remove the separate Health Plan Section ---

