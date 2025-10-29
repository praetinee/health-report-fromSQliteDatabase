import pandas as pd
# ... existing code ...
    return issues, health_plan_by_severity
    # --- END OF CHANGE ---


def generate_comprehensive_recommendations(person_data):
    """
    สร้างสรุปและคำแนะนำการปฏิบัติตัวแบบองค์รวมจากข้อมูลสุขภาพทั้งหมด
    (ในรูปแบบ Text HTML เดิม)
    """
    # --- START OF CHANGE: Use health_plan_by_severity ---
    issues, health_plan_by_severity = get_recommendation_data(person_data)

    if not issues and not any(health_plan_by_severity.values()): # Check if any severity level has plans
        return ""

    if not any(issues.values()) and not any(health_plan_by_severity.values()): # Double check if completely empty
    # --- END OF CHANGE ---
        return """
        <div style='background-color: #e8f5e9; color: #1b5e20; padding: 1rem; border-radius: 8px; text-align: center;'>
            <h4 style='margin:0;'>ผลการตรวจสุขภาพโดยรวมอยู่ในเกณฑ์ดี</h4>
            <p style='margin-top: 0.5rem;'>ไม่พบความผิดปกติที่มีนัยสำคัญ ขอแนะนำให้รักษาสุขภาพที่ดีเช่นนี้ต่อไป และมาตรวจสุขภาพประจำปีอย่างสม่ำเสมอ</p>
        </div>
        """

    # --- Build Left Column (Issues) ---
    left_column_parts = []
    if issues['high']:
        left_column_parts.append("<div style='border-left: 5px solid #c62828; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #c62828; margin-top:0;'>ควรพบแพทย์เพื่อประเมินเพิ่มเติม</h5><ul>")
        for item in set(issues['high']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")

    if issues['medium']:
        left_column_parts.append("<div style='border-left: 5px solid #f9a825; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #f9a825; margin-top:0;'>ประเด็นสุขภาพที่ควรปรับพฤติกรรม</h5><ul>")
        for item in set(issues['medium']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")

    if issues['low']:
        left_column_parts.append("<div style='border-left: 5px solid #1976d2; padding-left: 15px; margin-bottom: 1.5rem;'>")
        left_column_parts.append("<h5 style='color: #1976d2; margin-top:0;'>ข้อควรระวังและการเฝ้าติดตาม</h5><ul>")
        for item in set(issues['low']): left_column_parts.append(f"<li>{item}</li>")
        left_column_parts.append("</ul></div>")

    # --- Build Right Column (Health Plan) ---
    right_column_parts = []
    # --- START OF CHANGE: Aggregate health plans from severity levels ---
    all_nutrition_plans = health_plan_by_severity['high'].union(health_plan_by_severity['medium']).union(health_plan_by_severity['low'])
    # Heuristically categorize based on keywords for the old display format
    nutrition_specific = {p for p in all_nutrition_plans if any(k in p for k in ["อาหาร", "ทาน", "งด", "ลด", "ดื่ม", "โภชนาการ", "โปรตีน", "ไขมัน", "น้ำตาล", "เค็ม", "แอลกอฮอล์", "เหล็ก"])}
    exercise_specific = {p for p in all_nutrition_plans if any(k in p for k in ["ออกกำลังกาย", "เคลื่อนไหว"])}
    monitoring_specific = all_nutrition_plans - nutrition_specific - exercise_specific # Assume the rest are monitoring/general
    # --- END OF CHANGE ---


    right_column_parts.append("<div style='border-left: 5px solid #4caf50; padding-left: 15px;'>")
    right_column_parts.append("<h5 style='color: #4caf50; margin-top:0;'>แผนการดูแลสุขภาพเบื้องต้น (Your Health Plan)</h5>")

    # --- START OF CHANGE: Check aggregated sets ---
    if nutrition_specific:
        right_column_parts.append("<b>ด้านโภชนาการ:</b><ul>")
        for item in sorted(list(nutrition_specific)): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")

    if exercise_specific:
        right_column_parts.append("<b>ด้านการออกกำลังกาย:</b><ul>")
        for item in sorted(list(exercise_specific)): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")

    if monitoring_specific:
        right_column_parts.append("<b>การติดตามและดูแลทั่วไป:</b><ul>")
        for item in sorted(list(monitoring_specific)): right_column_parts.append(f"<li>{item}</li>")
        right_column_parts.append("</ul>")
    # --- END OF CHANGE ---

    right_column_parts.append("</div>")

    # --- Combine into a two-column layout ---
    left_html = "".join(left_column_parts)
# ... existing code ...
