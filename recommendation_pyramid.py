import streamlit as st
import html

# --- Import function to get recommendation data ---
from performance_tests import get_recommendation_data

def display_recommendation_pyramid(person_data):
    """
    แสดง Infographic พีระมิดคำแนะนำการปรับพฤติกรรม
    (ปรับปรุงดีไซน์ใหม่เป็นแบบ Stacked Cards ให้อ่านง่ายขึ้น)
    """
    # --- ดึงข้อมูล Issues และ Health Plan ที่แยกตามระดับความสำคัญ ---
    issues, health_plan_by_severity = get_recommendation_data(person_data)

    # --- ตรวจสอบว่ามีคำแนะนำหรือไม่ ---
    has_high = bool(health_plan_by_severity['high'])
    has_medium = bool(health_plan_by_severity['medium'])
    has_low = bool(health_plan_by_severity['low'])
    has_any_recommendation = has_high or has_medium or has_low

    # --- CSS Styles for the new Stacked Card Pyramid ---
    st.markdown("""
    <style>
        .pyramid-container {
            width: 100%;
            max-width: 700px;
            margin: 2rem auto;
            display: flex;
            flex-direction: column; /* เรียงจากบนลงล่าง */
            align-items: center; /* จัดกลางแนวนอน */
        }
        .pyramid-level {
            width: 100%; /* Default width */
            padding: 1.5rem;
            margin-bottom: 0.5rem; /* ระยะห่างระหว่างการ์ด */
            position: relative;
            color: #333; /* เปลี่ยนเป็นสีเข้มให้อ่านง่าย */
            text-align: left;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.05);
            border-left-width: 6px; /* ใช้ขอบซ้ายหนาๆ เพื่อบอกสี */
        }
        .pyramid-level h5 {
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 1.15rem;
            font-weight: bold;
            color: #111; /* สี Title เข้มขึ้น */
        }
        .pyramid-level ul {
            list-style: none;
            padding-left: 5px; /* ขยับเข้ามาเล็กน้อย */
            margin: 0;
        }
        .pyramid-level li {
            margin-bottom: 0.6rem; /* เพิ่มระยะห่างระหว่างข้อ */
            font-size: 0.95rem;
            line-height: 1.5;
            display: flex;
            align-items: flex-start;
        }
        .pyramid-level li::before {
            content: "▸"; /* เปลี่ยน bullet */
            font-weight: bold;
            display: inline-block;
            margin-right: 0.75em; /* ระยะห่างจาก text */
            margin-top: 0.1em;
            flex-shrink: 0;
        }
        
        /* Base (High) */
        .level-high {
            background-color: #ffebee; /* Red light */
            border-left-color: #c62828; /* Red dark */
            width: 100%;
        }
        .level-high h5, .level-high li::before { color: #c62828; }
        
        /* Middle (Medium) */
        .level-medium {
            background-color: #fff8e1; /* Yellow light */
            border-left-color: #f9a825; /* Yellow dark */
            width: 90%; /* แคบลงเล็กน้อย */
        }
        .level-medium h5, .level-medium li::before { color: #f9a825; }

        /* Top (Low) */
        .level-low {
            background-color: #e3f2fd; /* Blue light */
            border-left-color: #1976d2; /* Blue dark */
            width: 80%; /* แคบที่สุด */
        }
        .level-low h5, .level-low li::before { color: #1976d2; }
        
        /* Healthy Case */
        .level-healthy {
            background-color: #e8f5e9; /* Green light */
            border-left-color: #4CAF50; /* Green dark */
            width: 100%;
        }
        .level-healthy h5, .level-healthy li::before { color: #4CAF50; }
        .level-healthy li::before { content: "✓"; } /* Healthy checkmark */

        /* Single Level Case */
        .pyramid-level.single-level {
            width: 100%; /* ถ้ามีอันเดียว ให้เต็ม 100% */
        }

        /* Responsive adjustments */
        @media (max-width: 600px) {
            .pyramid-container {
                width: 100%;
            }
            .level-medium { width: 95%; }
            .level-low { width: 90%; }
        }
    </style>
    """, unsafe_allow_html=True)

    # --- Display Pyramid ---
    st.subheader("พีระมิดปรับพฤติกรรม")
    st.caption("คำแนะนำเรียงตามลำดับความสำคัญ จากบน (เร่งด่วน) ลงล่าง (ป้องกัน/เฝ้าระวัง)")

    if not has_any_recommendation:
        # กรณีสุขภาพดี
        st.markdown(f"""
        <div class="pyramid-container">
            <div class="pyramid-level level-healthy">
                <h5>สุขภาพดีเยี่ยม!</h5>
                <ul><li>ขอแนะนำให้รักษาสุขภาพที่ดีเช่นนี้ต่อไป และมาตรวจสุขภาพประจำปีอย่างสม่ำเสมอ</li></ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # กรณีมีคำแนะนำ
        pyramid_html = '<div class="pyramid-container">'
        levels_present = [level for level in ['high', 'medium', 'low'] if health_plan_by_severity[level]]
        num_levels = len(levels_present)
        is_single = (num_levels == 1)

        # Function to generate list items
        def generate_list_items(plans):
            return "".join([f"<li>{html.escape(plan)}</li>" for plan in sorted(list(plans))])

        # Define titles for each level
        titles = {
            'high': "🔴 ต้องทำ/พบแพทย์ (เร่งด่วน)",
            'medium': "🟡 ควรปรับเปลี่ยน (สำคัญ)",
            'low': "🔵 ป้องกัน/เฝ้าระวัง (ทั่วไป)"
        }

        # Build levels from top (high) to bottom (low)
        # (เรียงจาก High > Medium > Low ให้ดูง่าย)
        if has_high:
            pyramid_html += f"""
            <div class="pyramid-level level-high {'single-level' if is_single else ''}">
                <h5>{titles['high']}</h5>
                <ul>{generate_list_items(health_plan_by_severity['high'])}</ul>
            </div>"""
        if has_medium:
            pyramid_html += f"""
            <div class="pyramid-level level-medium {'single-level' if is_single else ''}">
                <h5>{titles['medium']}</h5>
                <ul>{generate_list_items(health_plan_by_severity['medium'])}</ul>
            </div>"""
        if has_low:
            pyramid_html += f"""
            <div class="pyramid-level level-low {'single-level' if is_single else ''}">
                <h5>{titles['low']}</h5>
                <ul>{generate_list_items(health_plan_by_severity['low'])}</ul>
            </div>"""

        pyramid_html += '</div>'
        st.markdown(pyramid_html, unsafe_allow_html=True)

