import streamlit as st
import html

# --- Import function to get recommendation data ---
from performance_tests import get_recommendation_data

def display_recommendation_pyramid(person_data):
    """
    แสดง Infographic พีระมิดคำแนะนำการปรับพฤติกรรม
    """
    # --- ดึงข้อมูล Issues และ Health Plan ที่แยกตามระดับความสำคัญ ---
    issues, health_plan_by_severity = get_recommendation_data(person_data)

    # --- ตรวจสอบว่ามีคำแนะนำหรือไม่ ---
    has_high = bool(health_plan_by_severity['high'])
    has_medium = bool(health_plan_by_severity['medium'])
    has_low = bool(health_plan_by_severity['low'])
    has_any_recommendation = has_high or has_medium or has_low

    # --- CSS Styles for the Pyramid ---
    st.markdown("""
    <style>
        .pyramid-container {
            width: 80%;
            max-width: 600px;
            margin: 2rem auto;
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .pyramid-level {
            width: 100%;
            padding: 1.5rem 1rem 1.5rem 1rem; /* Increased padding */
            margin-bottom: -1px; /* Overlap borders slightly */
            position: relative;
            color: white;
            text-align: center;
            border: 1px solid rgba(0,0,0,0.1);
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            display: flex; /* Use flexbox for centering */
            flex-direction: column; /* Stack title and content vertically */
            justify-content: center; /* Center vertically */
            align-items: center; /* Center horizontally */
            min-height: 80px; /* Ensure a minimum height */
        }
        .pyramid-level h5 {
            margin-top: 0;
            margin-bottom: 0.8rem; /* Increased space below title */
            font-size: 1.1rem;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
            width: 100%; /* Ensure title takes full width */
        }
        .pyramid-level ul {
            list-style: none;
            padding: 0;
            margin: 0;
            text-align: left; /* Align list items left */
            width: 90%; /* Adjust width for content */
            max-width: 450px; /* Limit max width for readability */
        }
        .pyramid-level li {
            margin-bottom: 0.5rem; /* Space between list items */
            font-size: 0.95rem; /* Slightly larger font */
            line-height: 1.5; /* Improve readability */
            display: flex; /* Use flex for alignment */
            align-items: flex-start; /* Align icon with top of text */
        }
        .pyramid-level li::before {
            content: "▹"; /* Use a different bullet */
            color: rgba(255, 255, 255, 0.8);
            font-weight: bold;
            display: inline-block;
            width: 1em;
            margin-left: -1em; /* Adjust alignment */
            margin-right: 0.5em; /* Space after bullet */
            flex-shrink: 0; /* Prevent bullet from shrinking */
        }
        .level-high {
            background-color: #c62828; /* Red */
            clip-path: polygon(0% 100%, 100% 100%, 85% 0%, 15% 0%); /* Base Trapezoid */
            padding-top: 2.5rem; /* More padding for base */
            padding-bottom: 2rem;
            z-index: 1;
        }
        .level-medium {
            background-color: #f9a825; /* Yellow */
            width: 70%;
             /* clip-path for middle trapezoid depends on whether high exists */
            z-index: 2;
        }
        .level-low {
            background-color: #1976d2; /* Blue */
            width: 40%;
            clip-path: polygon(50% 0%, 100% 100%, 0% 100%); /* Top Triangle */
            padding-bottom: 2rem; /* More padding for top */
            z-index: 3;
        }
        .level-healthy {
            background-color: #4CAF50; /* Green */
            clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
            width: 60%; /* Make healthy pyramid a bit wider */
            padding-bottom: 2rem;
            z-index: 1;
        }
        /* Adjustments for single level pyramid */
         .pyramid-level.single-level {
             width: 60%; /* Make single level pyramids consistent width */
             clip-path: polygon(50% 0%, 100% 100%, 0% 100%); /* Triangle */
             padding-bottom: 2rem;
         }

        /* Responsive adjustments */
        @media (max-width: 600px) {
            .pyramid-container {
                width: 95%;
            }
            .pyramid-level h5 {
                font-size: 1rem;
            }
             .pyramid-level li {
                 font-size: 0.9rem;
             }
        }
    </style>
    """, unsafe_allow_html=True)

    # --- Display Pyramid ---
    st.subheader("พีระมิดปรับพฤติกรรม")
    st.caption("คำแนะนำเรียงตามลำดับความสำคัญ จากฐาน (เร่งด่วน) สู่ยอด (ป้องกัน/เฝ้าระวัง)")

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

        # Function to generate list items
        def generate_list_items(plans):
            return "".join([f"<li>{html.escape(plan)}</li>" for plan in sorted(list(plans))])

        # Define titles for each level
        titles = {
            'high': "ต้องทำ/พบแพทย์",
            'medium': "ควรปรับเปลี่ยน",
            'low': "ป้องกัน/เฝ้าระวัง"
        }

        # Build levels from bottom (high) to top (low)
        if has_high:
            clip_path_medium = "polygon(0% 100%, 100% 100%, 85% 0%, 15% 0%)" if not has_low else "polygon(0% 100%, 100% 100%, 75% 0%, 25% 0%)"
            pyramid_html += f"""
            <div class="pyramid-level level-high {'single-level' if num_levels == 1 else ''}">
                <h5>{titles['high']}</h5>
                <ul>{generate_list_items(health_plan_by_severity['high'])}</ul>
            </div>"""
        if has_medium:
            clip_path = "polygon(50% 0%, 100% 100%, 0% 100%)" # Default top triangle if low is missing
            if has_high and has_low:
                 clip_path = "polygon(0% 100%, 100% 100%, 75% 0%, 25% 0%)" # Middle trapezoid
            elif has_high and not has_low:
                 clip_path = "polygon(0% 100%, 100% 100%, 85% 0%, 15% 0%)" # Top trapezoid (wider)
            # If only medium exists, it uses the single-level class for triangle shape

            pyramid_html += f"""
            <div class="pyramid-level level-medium {'single-level' if num_levels == 1 else ''}" style="clip-path: {clip_path if num_levels > 1 else 'none'};">
                <h5>{titles['medium']}</h5>
                <ul>{generate_list_items(health_plan_by_severity['medium'])}</ul>
            </div>"""
        if has_low:
            # Low level is always the top triangle if present with others,
            # or a single triangle if it's the only one.
            pyramid_html += f"""
            <div class="pyramid-level level-low {'single-level' if num_levels == 1 else ''}">
                <h5>{titles['low']}</h5>
                <ul>{generate_list_items(health_plan_by_severity['low'])}</ul>
            </div>"""

        pyramid_html += '</div>'
        st.markdown(pyramid_html, unsafe_allow_html=True)
