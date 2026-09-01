"""
utils.py
--------
Helper functions used by app.py.
"""

import math
import pandas as pd
import streamlit as st
from data_loader import generate_real_students, RECOVERY_SUGGESTIONS, MIN_REQUIRED_PCT, TEACHERS


@st.cache_data
def load_data():
    """
    Loads the attendance dataset.

    Loads from data/attendance_dataset.csv (real data) via data_loader.py,
    reshaped into the same columns the rest of the app expects:
    seat_number, name, email, branch, semester, subject, attendance_history,
    dates, classes_held, classes_attended, current_attendance_pct,
    predicted_attendance_pct, risk_level
    """
    df = generate_real_students()
    return df


def find_student(df, query):
    """
    STUDENT LOGIN / SEARCH LOGIC.
    A student can "log in" by typing their seat number, full name, or email.
    Returns all rows (one per subject) that match, or an empty DataFrame.
    """
    if not query:
        return df.iloc[0:0]  # empty

    q = query.lower().strip()
    matches = df[
        df["seat_number"].str.lower().eq(q)
        | df["email"].str.lower().eq(q)
        | df["name"].str.lower().eq(q)
        | df["name"].str.lower().str.contains(q)  # allows partial name search too
    ]
    return matches


def find_teacher(teacher_id, password):
    """
    TEACHER LOGIN LOGIC.
    Checks the entered teacher ID + password against the TEACHERS list
    in mock_data.py. Returns the matching teacher dict, or None.

    LATER: replace this with a real check against a database/auth
    service, and NEVER store plain-text passwords in production.
    """
    if not teacher_id or not password:
        return None

    for teacher in TEACHERS:
        if teacher["teacher_id"].lower() == teacher_id.strip().lower() \
                and teacher["password"] == password:
            return teacher
    return None


def filter_data(df, branch_filter, subject_filter, semester_filter, search_query):
    """Applies sidebar filters + search box (used in the Faculty/Admin view)."""
    filtered = df.copy()

    if branch_filter != "All":
        filtered = filtered[filtered["branch"] == branch_filter]

    if subject_filter != "All":
        filtered = filtered[filtered["subject"] == subject_filter]

    if semester_filter != "All":
        filtered = filtered[filtered["semester"] == semester_filter]

    if search_query:
        query = search_query.lower().strip()
        filtered = filtered[
            filtered["name"].str.lower().str.contains(query)
            | filtered["seat_number"].str.lower().str.contains(query)
        ]

    return filtered


def risk_color(risk_level):
    return {"High": "#e74c3c", "Medium": "#f39c12", "Low": "#2ecc71"}.get(risk_level, "#95a5a6")


def risk_emoji(risk_level):
    return {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(risk_level, "⚪")


def get_recovery_plan(risk_level):
    return RECOVERY_SUGGESTIONS.get(risk_level, [])


def summary_stats(df):
    """KPI numbers for the Faculty/Admin view."""
    total_records = len(df)
    avg_attendance = round(df["current_attendance_pct"].mean(), 1) if total_records else 0
    high_risk = int((df["risk_level"] == "High").sum())
    medium_risk = int((df["risk_level"] == "Medium").sum())
    low_risk = int((df["risk_level"] == "Low").sum())
    return {
        "total_records": total_records,
        "avg_attendance": avg_attendance,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
    }


def attendance_advice(classes_attended, classes_held, target_pct=MIN_REQUIRED_PCT):
    """
    THE KEY STUDENT-FACING CALCULATION.

    Given how many classes a student has attended out of how many were held,
    figures out ONE of two things:

    - If they're BELOW the target %: how many classes they must attend
      IN A ROW (assuming no more are missed) to reach the target.
    - If they're AT/ABOVE the target %: how many MORE classes they could
      safely skip and still stay at/above the target.

    Math (assuming every future class is attended when catching up):
        (attended + x) / (held + x) >= target/100
        => x >= (target/100 * held - attended) / (1 - target/100)

    Math (assuming they stop attending, to find safe skips):
        attended / (held + y) >= target/100
        => y <= (attended * 100 / target) - held
    """
    current_pct = round(100 * classes_attended / classes_held, 1) if classes_held else 0
    target_fraction = target_pct / 100

    if current_pct >= target_pct:
        safe_skips = math.floor((classes_attended * 100 / target_pct) - classes_held)
        return {
            "status": "safe",
            "current_pct": current_pct,
            "value": max(safe_skips, 0),
            "message": f"You can miss up to {max(safe_skips, 0)} more class(es) "
                       f"and still stay at or above {target_pct}%."
        }
    else:
        needed = math.ceil(
            (target_fraction * classes_held - classes_attended) / (1 - target_fraction)
        )
        return {
            "status": "at_risk",
            "current_pct": current_pct,
            "value": max(needed, 0),
            "message": f"You need to attend the next {max(needed, 0)} class(es) in a row "
                       f"(without missing any) to reach {target_pct}%."
        }


def build_subject_hover_cards(student_matches):
    """
    Builds ONE block of HTML/CSS showing all of a student's subjects as
    cards side by side. Hovering the mouse over a card reveals a tooltip
    with the recommended action for THAT subject only (its own attendance
    advice + top recovery tips) — done with pure CSS (:hover), no
    JavaScript needed.

    NOTE: hover only works with a mouse. On touchscreens (phones/tablets)
    there's no hover, so the "Detailed View" dropdown further down the
    page is the fallback way to see the same info by tapping.
    """
    cards_html = ['<div class="subject-cards-container">']

    for _, row in student_matches.iterrows():
        risk = row["risk_level"]
        color = risk_color(risk)
        emoji = risk_emoji(risk)

        advice = attendance_advice(row["classes_attended"], row["classes_held"])
        tips = get_recovery_plan(risk)[:2]  # keep tooltip short/readable

        tooltip_body = f"<b>{advice['message']}</b>"
        for tip in tips:
            tooltip_body += f"<br>• {tip}"

        # IMPORTANT: build this as ONE unindented line. Streamlit's markdown
        # renderer treats any line starting with 4+ spaces as a "code block"
        # and prints it as literal text instead of rendering it as HTML —
        # which is exactly the bug you saw (raw <div> tags showing on screen).
        card_html = (
            f'<div class="subject-card" style="border-top-color:{color};">'
            f'<h4>{row["subject"]}</h4>'
            f'<div class="pct">{row["current_attendance_pct"]}%</div>'
            f'<div class="risk-label">{emoji} {risk} risk</div>'
            f'<div class="tooltip">{tooltip_body}</div>'
            f'</div>'
        )
        cards_html.append(card_html)

    cards_html.append("</div>")
    return "".join(cards_html)
