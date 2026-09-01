# Vigil

## Attendance Risk Prediction & Early Warning System

Vigil is an attendance monitoring and prediction system designed to help students and faculty identify attendance risks before they become a serious problem.

Traditional attendance systems mainly show a student's current attendance percentage. Attendora goes one step further by analyzing attendance patterns, predicting future attendance, and providing early warnings when a student is at risk of falling below the required 75% attendance.

## Problem Statement

Students may currently have a safe attendance percentage but still be at risk because their attendance is continuously decreasing.

For example, a student with 78% attendance may appear safe today, but if their attendance continues to decline, they may soon fall below the required 75% threshold.

Faculty members also have to manually monitor large numbers of students to identify such cases.

Vigil aims to make this process proactive rather than reactive.

## Our Solution

Vigil analyzes historical attendance data to:

- Calculate current attendance
- Track attendance trends
- Predict future attendance
- Identify students at risk of falling below 75%
- Categorize students based on risk
- Show subject-wise attendance and risk
- Calculate the number of classes required for recovery
- Provide early warnings and personalized messages
- Help faculty monitor and filter students who need attention

## Users

### Student

Students can view:

- Total classes
- Classes attended
- Classes completed
- Overall attendance
- Subject-wise attendance
- Subject-wise risk
- Predicted attendance
- Classes required to improve attendance
- Attendance warnings and messages

### Teacher

Teachers can view:

- Overall attendance summary
- Student attendance records
- Student attendance graphs
- Expected/predicted vs actual attendance
- Students grouped by warning category
- Student contact details
- Search by USN/name
- Filter by branch
- Filter by subject
- Filter by semester

## Key Features

### Attendance Analysis
Calculates attendance percentage from classes conducted and classes attended.

### Trend Analysis
Analyzes attendance over multiple weeks to identify whether a student's attendance is improving, stable, or declining.

### Future Prediction
Uses the student's historical attendance trend to estimate future attendance.

### Risk Detection
Students are categorized based on their current attendance and predicted attendance.

- Low Risk
- Medium Risk
- High Risk

### Early Warning System
Students approaching or predicted to fall below the 75% requirement receive an attendance warning.

### Recovery Calculation
The system estimates how many upcoming classes a student needs to attend to improve their attendance.

### Student & Teacher Dashboards
Different dashboards provide relevant information depending on whether the user is a student or teacher.

## Technology Stack

- Python
- Pandas
- NumPy
- Scikit-learn
- Streamlit
- Plotly
- CSV / SQLite

## Project Structure

```text
Vigil/
│
├── data/
│   ├── attendance_dataset.csv
│   └── teacher_dataset_6.csv
│
├── prediction.py
├── risk_recovery.py
├── dashboard.py
├── app.py
└── ReadME.md


