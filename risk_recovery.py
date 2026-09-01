#RISK RECOVERY

import math
import pandas as pd
from prediction import load_attendance_data, analyze_all_students

def classes_can_miss(attended, total, required_pct=75):
    """
    attended: how many classes they've attended so far (cumulative)
    total: how many classes have been held so far (cumulative)
    """
    threshold = required_pct / 100

    # Already below 75%? They can't afford to miss any more.
    if attended / total < threshold:
        return 0

    # Solve: attended / (total + k) >= threshold  ->  find max k
    max_k = (attended / threshold) - total
    return int(max_k)  # round down, can't skip half a class


def classes_needed_to_recover(attended, total, required_pct=75):
    threshold = required_pct / 100

    # Already safe? Nothing to recover from.
    if attended / total >= threshold:
        return 0

    # Solve: (attended + k) / (total + k) >= threshold  ->  find min k
    k = ((threshold * total) - attended) / (1 - threshold)
    return math.ceil(k)  # round up, need at least this many

def generate_warning_message(row):
    subject = row['subject']
    current = row['current_attendance']
    predicted = row['predicted_attendance']
    risk = row['risk_level']

    if risk == 'HIGH':
        return (f"⚠️ HIGH RISK in {subject}: Attendance is {current}%, "
                f"projected to drop to {predicted}%. Act now.")
    elif risk == 'MEDIUM':
        gap = round(current - 75, 1)
        return (f"🟡 MEDIUM RISK in {subject}: Attendance is {current}%, "
            f"{gap} points above the 75% cutoff. Predicted: {predicted}%.")
            
    else:
        return (f"🟢 LOW RISK in {subject}: Attendance is {current}%, "
                f"on a healthy track (predicted: {predicted}%).")

def generate_risk_explanation(row):
    direction = row['trend_direction']
    slope = row['trend_slope']
    risk = row['risk_level']

    if direction == 'DECLINING':
        reason = f"attendance has been dropping ~{abs(slope):.1f}% per week."
    elif direction == 'IMPROVING':
        reason = f"attendance has been improving ~{slope:.1f}% per week."
    else:
        reason = "attendance has stayed roughly stable recently."

    return f"Marked {risk} risk because: {reason}"

def generate_recommendation(row, attended, total):
    risk = row['risk_level']

    if risk == 'HIGH':
        needed = classes_needed_to_recover(attended, total)
        if needed == 0:
            return "Attend your next few classes without any misses to stay safe."
        return f"Attend the next {needed} classes in a row (no misses) to get back above 75%."

    elif risk == 'MEDIUM':
        safe = classes_can_miss(attended, total)
        return f"You can afford to miss about {safe} more class(es) — but don't push it."

    else:
        safe = classes_can_miss(attended, total)
        return f"You're in good shape — you could miss up to {safe} class(es) if needed."


def build_student_report(row, attended, total):
    return {
        "student_id": row['student_id'],
        "name": row.get('name', 'Unknown'),
        "subject": row['subject'],
        "risk_level": row['risk_level'],
        "current_attendance": row['current_attendance'],
        "predicted_attendance": row['predicted_attendance'],
        "classes_can_miss": classes_can_miss(attended, total),
        "classes_needed_to_recover": classes_needed_to_recover(attended, total),
        "warning_message": generate_warning_message(row),
        "risk_explanation": generate_risk_explanation(row),
        "recommendation": generate_recommendation(row, attended, total),
    }

def get_cumulative_totals(df, student_id, subject):
    # NOTE: these column names must match load_attendance_data's output:
    # student_id, subject, attendance, total_classes
    subset = df[(df['student_id'] == student_id) & (df['subject'] == subject)]
    attended = subset['attendance'].sum()
    total = subset['total_classes'].sum()
    return attended, total


if __name__ == "__main__":
    # dataset lives directly inside the vigil folder
    csv_path = r"C:\Users\safeer\Desktop\vigil\attendance_dataset.csv"

    df = load_attendance_data(csv_path)
    results_df = analyze_all_students(df)

    high_risk_rows = results_df[results_df['risk_level'] == 'HIGH']
    sample_row = high_risk_rows.iloc[0] if len(high_risk_rows) > 0 else results_df.iloc[0]

    sid, subj = sample_row['student_id'], sample_row['subject']
    attended, total = get_cumulative_totals(df, sid, subj)
    print(f"Student: {sid} | Subject: {subj} | attended={attended}/{total}")

    report = build_student_report(sample_row, attended, total)
    for k, v in report.items():
        print(f"  {k}: {v}")
