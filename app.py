"""
app.py
------
Main entry point for the College Attendance Prediction System.

This file connects and launches the existing dashboard.
The actual dashboard UI is in dashboard.py.

Run:
    python -m streamlit run app.py
"""

import os
import runpy
import streamlit as st


# ---------------------------------------------------------
# Project files required by the dashboard
# ---------------------------------------------------------

REQUIRED_FILES = [
    "dashboard.py",
    "data_loader.py",
    "prediction.py",
    "risk_recovery.py",
]


# ---------------------------------------------------------
# Check that all project modules exist
# ---------------------------------------------------------

missing_files = [
    file for file in REQUIRED_FILES
    if not os.path.exists(file)
]

if missing_files:
    st.error("❌ Some project files are missing:")
    
    for file in missing_files:
        st.write(f"- `{file}`")

    st.stop()


# ---------------------------------------------------------
# Run the actual dashboard
# ---------------------------------------------------------

runpy.run_path(
    "dashboard.py",
    run_name="__main__"
)