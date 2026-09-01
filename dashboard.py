"""
app.py
------
MAIN STREAMLIT APP.

Two modes, switchable in the sidebar:
    1. STUDENT PORTAL (default) — a student enters their seat number,
       name, or email and sees ONLY their own results: attendance %,
       risk level, prediction, and how many classes they need to
       attend (or can safely skip) to hit the minimum requirement.
    2. FACULTY / ADMIN VIEW — the full cohort dashboard: KPI cards,
       risk cards, table, trend graphs, warnings — filterable by
       branch / subject / semester.

Run with:
    python -m streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils import (
    load_data,
    find_student,
    find_teacher,
    filter_data,
    risk_color,
    risk_emoji,
    get_recovery_plan,
    summary_stats,
    attendance_advice,
    build_subject_hover_cards,
)
from data_loader import MIN_REQUIRED_PCT

# ----------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="College Attendance & Risk Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
    }
    .risk-card {
        border-radius: 12px;
        padding: 16px;
        color: white;
        text-align: center;
        font-weight: 600;
    }
    .advice-box {
        border-radius: 12px;
        padding: 20px;
        font-size: 18px;
        font-weight: 600;
        text-align: center;
        margin-bottom: 10px;
    }

    /* ---- Subject hover cards (Student Portal) ---- */
    .subject-cards-container {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 20px;
    }
    .subject-card {
        position: relative;           /* anchors the tooltip below it */
        flex: 1 1 220px;
        min-width: 220px;
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-top: 6px solid #ccc;   /* color set inline per risk level */
    }
    .subject-card h4 { margin: 0 0 6px 0; }
    .subject-card .pct { font-size: 26px; font-weight: 700; margin-bottom: 4px; }
    .subject-card .risk-label { font-size: 14px; color: #555; }

    /* Tooltip: hidden by default, revealed on hover of the parent card */
    .subject-card .tooltip {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        top: 105%;
        left: 0;
        width: 260px;
        background-color: #2c3e50;
        color: #ffffff;
        padding: 12px 14px;
        border-radius: 8px;
        font-size: 13px;
        line-height: 1.5;
        transition: opacity 0.2s ease;
        z-index: 50;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3);
        pointer-events: none;
    }
    .subject-card:hover .tooltip {
        visibility: visible;
        opacity: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

df = load_data()

# ----------------------------------------------------------------------
# SIDEBAR — mode switch (Student Portal vs Faculty/Admin)
# ----------------------------------------------------------------------
st.sidebar.header("🎓 College Attendance Portal")
mode = st.sidebar.radio("Choose view", ["🧑‍🎓 Student Portal", "🧑‍🏫 Faculty / Admin View"])
st.sidebar.markdown("---")


# ========================================================================
# MODE 1: STUDENT PORTAL — the actual end-user flow
# ========================================================================
if mode == "🧑‍🎓 Student Portal":

    st.title("🧑‍🎓 Student Attendance Portal")
    st.caption("Enter your Seat Number, Name, or College Email to check your attendance risk.")

    # --- "Login" box ---
    login_input = st.text_input(
        "Seat Number / Name / Email",
        placeholder="e.g. CSE21045  or  Aarav Sharma  or  aarav.sharma0@college.edu",
    )
    check_clicked = st.button("Check My Attendance", type="primary")

    if check_clicked or login_input:
        matches = find_student(df, login_input)

        if matches.empty:
            st.error("No matching student found. Double-check your seat number, name, or email.")
        else:
            student_name = matches.iloc[0]["name"]
            seat_number = matches.iloc[0]["seat_number"]
            branch = matches.iloc[0]["branch"]
            semester = matches.iloc[0]["semester"]

            st.success(f"Welcome, **{student_name}** ({seat_number}) — {branch}, Semester {semester}")

            # A student can have multiple subjects — let them pick one,
            # or show an "overall" combined view first.
            overall_attended = matches["classes_attended"].sum()
            overall_held = matches["classes_held"].sum()
            overall_pct = round(100 * overall_attended / overall_held, 1) if overall_held else 0

            # ---- Overall summary cards ----
            st.subheader("📊 Your Overall Attendance")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="metric-card"><h2>{overall_pct}%</h2>
                    <p>Overall Attendance</p></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card"><h2>{int(overall_attended)}/{int(overall_held)}</h2>
                    <p>Classes Attended</p></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card"><h2>{MIN_REQUIRED_PCT}%</h2>
                    <p>Minimum Required</p></div>""", unsafe_allow_html=True)

            st.write("")

            # ---- All subjects at a glance — hover a card for its own advice ----
            st.subheader("📚 Your Subjects")
            st.caption("Hover your mouse over a subject card to see the recommended "
                       "action for that subject specifically.")
            st.markdown(build_subject_hover_cards(matches), unsafe_allow_html=True)

            # ---- Optional detailed view (also the fallback for touchscreens,
            #      since tapping a phone/tablet has no "hover") ----
            st.write("")
            with st.expander("📈 View detailed trend & full recommendations for one subject"):
                subject_list = matches["subject"].tolist()
                selected_subject = st.selectbox("Choose a subject", subject_list, key="detail_subject")
                row = matches[matches["subject"] == selected_subject].iloc[0]

                risk = row["risk_level"]
                color = risk_color(risk)
                emoji = risk_emoji(risk)

                colA, colB = st.columns([1, 2])

                with colA:
                    st.markdown(
                        f"""<div class="risk-card" style="background-color:{color};">
                        {emoji} Risk Level: {risk}<br>
                        <span style="font-size:26px;">{row['current_attendance_pct']}%</span> attendance
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    st.metric("Predicted Attendance (next period)", f"{row['predicted_attendance_pct']}%")

                with colB:
                    # THE KEY FEATURE: how many classes to attend / can skip
                    advice = attendance_advice(row["classes_attended"], row["classes_held"])
                    box_color = "#2ecc71" if advice["status"] == "safe" else "#e74c3c"
                    st.markdown(
                        f"""<div class="advice-box" style="background-color:{box_color}; color:white;">
                        {advice['message']}
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    if advice["status"] == "at_risk":
                        st.warning(
                            f"⚠️ You are below the {MIN_REQUIRED_PCT}% minimum required to sit for exams "
                            f"in **{selected_subject}**. Attend upcoming classes without fail."
                        )
                    else:
                        st.info(f"✅ You're safely above the {MIN_REQUIRED_PCT}% requirement in **{selected_subject}**.")

                # ---- Personal trend graph for the chosen subject ----
                st.markdown(f"**Attendance Trend — {selected_subject}**")
                trend_fig = go.Figure()
                trend_fig.add_trace(go.Scatter(
                    x=row["dates"],
                    y=row["attendance_history"],
                    mode="lines+markers",
                    line=dict(color="#3498db", width=2),
                ))
                trend_fig.update_layout(
                    yaxis=dict(tickvals=[0, 1], ticktext=["Absent", "Present"], range=[-0.2, 1.2]),
                    xaxis_title="Class Date",
                    height=320,
                    margin=dict(l=20, r=20, t=20, b=20),
                )
                st.plotly_chart(trend_fig, use_container_width=True)

                # ---- Full recovery tips list for the chosen subject ----
                st.markdown(f"**Recommended Actions — {selected_subject}**")
                for tip in get_recovery_plan(risk):
                    st.markdown(f"- {tip}")

    else:
        st.info("👆 Enter your details above to check your attendance and risk status.")


# ========================================================================
# MODE 2: FACULTY / ADMIN VIEW — full cohort dashboard
# ========================================================================
else:
    st.title("🧑‍🏫 Faculty / Admin Dashboard")

    # Session state keeps the teacher "logged in" across reruns —
    # Streamlit reruns the whole script on every click, so without this
    # she'd be logged out every time she picked a subject or filter.
    if "teacher" not in st.session_state:
        st.session_state.teacher = None

    # ---- LOGIN GATE ----
    if st.session_state.teacher is None:
        st.caption("Please log in with your Teacher ID to view your students' attendance.")

        with st.form("teacher_login_form"):
            teacher_id_input = st.text_input("Teacher ID", placeholder="e.g. T101")
            password_input = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Login", type="primary")

        if login_submitted:
            teacher = find_teacher(teacher_id_input, password_input)
            if teacher:
                st.session_state.teacher = teacher
                st.rerun()  # rerun immediately so the portal below renders
            else:
                st.error("Invalid Teacher ID or password. Please try again.")

        st.stop()  # don't render anything below until she's logged in

    # ---- LOGGED IN: show her profile + subjects she teaches ----
    teacher = st.session_state.teacher

    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.success(f"Welcome, **{teacher['name']}** (Teacher ID: {teacher['teacher_id']})")
        st.caption("Subjects you teach: " + ", ".join(teacher["subjects"]))
    with top_col2:
        if st.button("Logout"):
            st.session_state.teacher = None
            st.rerun()

    # She can only pick from the subjects SHE teaches — not the full list.
    selected_subject = st.selectbox("Select a subject to view its students", teacher["subjects"])

    # ---- Extra filters within that subject ----
    st.sidebar.subheader("🔍 Refine within this subject")
    search_query = st.sidebar.text_input("Search by name or seat number")

    branch_options = ["All"] + sorted(df["branch"].unique().tolist())
    semester_options = ["All"] + sorted(df["semester"].unique().tolist())
    selected_branch = st.sidebar.selectbox("Filter by Branch", branch_options)
    selected_semester = st.sidebar.selectbox("Filter by Semester", semester_options)

    filtered_df = filter_data(df, selected_branch, selected_subject, selected_semester, search_query)

    if filtered_df.empty:
        st.warning("No records match your filters.")
        st.stop()

    # ---- KPI cards ----
    stats = summary_stats(filtered_df)
    st.subheader("📊 Attendance Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card"><h3>{stats['total_records']}</h3>
            <p>Total Records</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><h3>{stats['avg_attendance']}%</h3>
            <p>Average Attendance</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><h3>{stats['high_risk']}</h3>
            <p>High Risk</p></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><h3>{stats['medium_risk']}</h3>
            <p>Medium Risk</p></div>""", unsafe_allow_html=True)

    st.write("")

    # ---- Risk cards ----
    st.subheader("⚠️ Risk Overview")
    r1, r2, r3 = st.columns(3)
    risk_cols = {"High": r1, "Medium": r2, "Low": r3}
    for level, col in risk_cols.items():
        count = int((filtered_df["risk_level"] == level).sum())
        with col:
            st.markdown(
                f"""<div class="risk-card" style="background-color:{risk_color(level)};">
                {risk_emoji(level)} {level} Risk<br><span style="font-size:28px;">{count}</span> records
                </div>""",
                unsafe_allow_html=True,
            )

    st.write("")

    # ---- Table (includes phone number so she can follow up directly) ----
    st.subheader("📋 Student Records")
    table_df = filtered_df[[
        "seat_number", "name", "phone", "branch", "semester",
        "current_attendance_pct", "predicted_attendance_pct", "risk_level"
    ]].rename(columns={
        "seat_number": "Seat No.", "name": "Name", "phone": "Phone",
        "branch": "Branch", "semester": "Sem",
        "current_attendance_pct": "Current (%)",
        "predicted_attendance_pct": "Predicted (%)", "risk_level": "Risk",
    })
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    # ---- Predicted vs current bar chart ----
    st.subheader("🔮 Predicted vs Current Attendance")
    pred_fig = px.bar(
        filtered_df.sort_values("predicted_attendance_pct"),
        x="name", y=["current_attendance_pct", "predicted_attendance_pct"],
        barmode="group",
        labels={"value": "Attendance (%)", "name": "Student", "variable": "Metric"},
        color_discrete_map={"current_attendance_pct": "#3498db", "predicted_attendance_pct": "#9b59b6"},
    )
    pred_fig.update_layout(height=450, xaxis_tickangle=-45, legend_title_text="")
    st.plotly_chart(pred_fig, use_container_width=True)

    # ---- Warnings ----
    st.subheader("🚨 Warnings — Students Needing Attention")
    high_risk_df = filtered_df[filtered_df["risk_level"] == "High"]
    if high_risk_df.empty:
        st.success("No high-risk records in the current filter.")
    else:
        for _, row in high_risk_df.iterrows():
            st.error(
                f"**{row['name']}** ({row['seat_number']}, {row['branch']}) — "
                f"{row['subject']}: {row['current_attendance_pct']}% attendance | "
                f"📞 {row['phone']}"
            )

st.markdown("---")
st.caption("Built with Streamlit • College Attendance Risk Portal — Hackathon Project")