"""
data_loader.py
---------------
Replaces mock_data.py. Loads the REAL datasets your teammate pushed to
GitHub and reshapes them into the exact same columns/format that
utils.py and app.py were already built around, so nothing downstream
needs to change.

SOURCE FILES (relative to project root):
    data/attendance_dataset.csv
    data/teacher_dataset_6.csv

WHAT HAD TO BE RESHAPED AND WHY
--------------------------------
1. attendance_dataset.csv is WEEKLY data (one row per student, per
   subject, per week: 8 weeks). The rest of the app expects ONE row per
   student per subject for the whole semester (classes_held,
   classes_attended, attendance_history, dates). So we GROUP the weekly
   rows and sum them up.

2. attendance_history / dates: the source file only gives weekly totals
   (e.g. "attended 3 of 4 classes in Week 2"), not one row per
   individual class. To keep the same line-chart behaviour in app.py
   (which plots `dates` vs `attendance_history`), we expand each week's
   total into that many 1/0 entries (attended classes first, then
   missed ones) with one synthetic date per class. This is a faithful
   reconstruction of the real totals -- not fabricated attendance, just
   an ordering assumption within a week (exact day-by-day order wasn't
   in the source data).

3. predicted_attendance_pct: the source data has no ML prediction
   column. There's no model output to plug in yet, so this is a simple
   placeholder (last-2-weeks trend applied to current %). Swap this out
   the moment your ML teammate has real predictions -- search for
   "PLACEHOLDER" below.

4. TEACHERS / passwords: teacher_dataset_6.csv has no password column.
   A demo password is assigned per teacher as their teacher_id in
   lowercase (e.g. T101 -> "t101"). Tell your team this before the demo,
   or replace with real credentials later -- search for "DEMO PASSWORD"
   below.

5. email: attendance_dataset.csv has no email column. One is synthesized
   from the student's name + ID purely so the existing "search by email"
   login option in find_student() still has something to match against.
"""

import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ATTENDANCE_FILE = "data/attendance_dataset.csv"
TEACHER_FILE = "data/teacher_dataset_6.csv"

# Minimum attendance % required to sit for exams (same constant as before).
MIN_REQUIRED_PCT = 75

# Recovery suggestions shown per risk level (unchanged from mock_data.py).
RECOVERY_SUGGESTIONS = {
    "High": [
        "You are below the minimum required attendance — talk to your faculty advisor immediately.",
        "Attend every remaining class from now on — check the 'classes to attend' number below.",
        "Request make-up sessions or extra classes if your college offers them.",
        "If health/personal issues caused absences, inform your department office — some colleges allow condonation.",
    ],
    "Medium": [
        "You're close to the minimum — don't miss any more classes this month.",
        "Set reminders for class timings to avoid accidental misses.",
        "Check in with your mentor/advisor to stay on track.",
    ],
    "Low": [
        "You're in good standing — keep it up!",
        "You have some buffer if you occasionally need to miss a class.",
    ],
}


def _risk_level_from_pct(pct):
    if pct >= 85:
        return "Low"
    elif pct >= MIN_REQUIRED_PCT:
        return "Medium"
    else:
        return "High"


def _week_number(week_label):
    match = re.search(r"\d+", str(week_label))
    return int(match.group()) if match else 0


def _build_history_and_dates(group, semester_start):
    """
    Expand weekly (attended, total) counts into per-class 1/0 history
    plus one synthetic date per class. Weeks are processed in order;
    within a week, attended classes are listed before missed ones.
    """
    history = []
    dates = []
    group = group.sort_values("_week_num")

    for _, row in group.iterrows():
        attended = int(row["attendance"])
        total = int(row["total_classes"])
        missed = max(total - attended, 0)
        week_start = semester_start + timedelta(weeks=(row["_week_num"] - 1))

        week_classes = [1] * attended + [0] * missed
        for day_offset, val in enumerate(week_classes):
            history.append(val)
            dates.append((week_start + timedelta(days=day_offset)).strftime("%Y-%m-%d"))

    return history, dates


def _load_attendance():
    raw = pd.read_csv(ATTENDANCE_FILE)
    raw["_week_num"] = raw["week"].apply(_week_number)

    semester_start = datetime.today() - timedelta(weeks=int(raw["_week_num"].max()))

    group_cols = ["student_id", "name", "branch", "semester", "subject", "section", "phone_number"]
    rows = []

    for keys, group in raw.groupby(group_cols, sort=False):
        student_id, name, branch, semester, subject, section, phone_number = keys

        classes_attended = int(group["attendance"].sum())
        classes_held = int(group["total_classes"].sum())
        current_pct = round(100 * classes_attended / classes_held, 1) if classes_held else 0.0

        history, dates = _build_history_and_dates(group, semester_start)

        # PLACEHOLDER prediction: simple trend off the last two weeks vs
        # overall average. Replace with your ML teammate's real model
        # output as soon as it's available.
        weekly_pct = (100 * group["attendance"] / group["total_classes"]).values
        if len(weekly_pct) >= 2:
            recent_trend = weekly_pct[-2:].mean() - weekly_pct.mean()
        else:
            recent_trend = 0
        predicted_pct = float(np.clip(current_pct + recent_trend, 0, 100))
        predicted_pct = round(predicted_pct, 1)

        risk = _risk_level_from_pct(current_pct)

        first = str(name).split(" ")[0].lower()
        email = f"{first}.{str(student_id).lower()}@college.edu"

        rows.append({
            "seat_number": student_id,
            "name": name,
            "email": email,
            "phone": str(phone_number),
            "branch": branch,
            "semester": semester,
            "section": section,
            "subject": subject,
            "attendance_history": history,
            "dates": dates,
            "classes_held": classes_held,
            "classes_attended": classes_attended,
            "current_attendance_pct": current_pct,
            "predicted_attendance_pct": predicted_pct,
            "risk_level": risk,
        })

    return pd.DataFrame(rows)


def _load_teachers():
    raw = pd.read_csv(TEACHER_FILE)
    teachers = []

    for _, row in raw.iterrows():
        teacher_id = str(row["teacher_id"])
        teachers.append({
            "teacher_id": teacher_id,
            "name": row["name"],
            # DEMO PASSWORD: no password column exists in the source
            # data, so each teacher's password is their ID in lowercase
            # (e.g. T101 -> "t101"). Replace with real credentials
            # before this goes anywhere beyond the hackathon demo.
            "password": teacher_id.lower(),
            "subjects": [row["subject"]],
        })

    return teachers


def generate_real_students():
    """Drop-in replacement for generate_mock_students() -- same output shape."""
    return _load_attendance()


TEACHERS = _load_teachers()