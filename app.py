import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from prediction import (
    load_attendance_data,
    analyze_student_attendance,
    analyze_all_students
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Attendora",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# FILE PATHS
# ============================================================

ATTENDANCE_FILE = "data/attendance_dataset.csv"
TEACHER_FILE = "data/teacher_dataset_6.csv"


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_attendance():

    df = load_attendance_data(ATTENDANCE_FILE)

    return df


@st.cache_data
def load_teachers():

    return pd.read_csv(TEACHER_FILE)


attendance_df = load_attendance()
teacher_df = load_teachers()


# ============================================================
# GENERATE PREDICTION RESULTS
# ============================================================

@st.cache_data
def generate_predictions(df):

    results = analyze_all_students(
        df,
        periods_ahead=4,
        threshold=85
    )

    return results


prediction_df = generate_predictions(
    attendance_df
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_student(student_id):

    student = attendance_df[
        attendance_df["student_id"].astype(str)
        == str(student_id)
    ]

    return student


def get_teacher(teacher_id):

    teacher = teacher_df[
        teacher_df["teacher_id"].astype(str)
        == str(teacher_id)
    ]

    if len(teacher) == 0:
        return None

    return teacher.iloc[0]


def calculate_recovery_classes(
    attended,
    total,
    target=75
):

    """
    Calculates how many consecutive classes
    a student needs to attend to reach target attendance.
    """

    if total == 0:
        return 0

    current = (attended / total) * 100

    if current >= target:
        return 0

    required = 0

    while (
        (attended + required) /
        (total + required)
    ) * 100 < target:

        required += 1

        if required > 1000:
            break

    return required


def risk_icon(risk):

    if risk == "HIGH":
        return "🔴"

    if risk == "MEDIUM":
        return "🟡"

    return "🟢"


def notification_message(
    name,
    subject,
    current,
    predicted,
    risk
):

    if risk == "HIGH":

        return (
            f"🚨 **Attendance Warning — {subject}**\n\n"
            f"{name}, your current attendance is "
            f"**{current:.1f}%** and your predicted "
            f"attendance is **{predicted:.1f}%**.\n\n"
            f"Please attend upcoming classes regularly."
        )

    elif risk == "MEDIUM":

        return (
            f"🟡 **Attendance Alert — {subject}**\n\n"
            f"Your current attendance is "
            f"**{current:.1f}%**.\n\n"
            f"Your attendance trend needs attention."
        )

    else:

        return (
            f"✅ **Attendance Safe — {subject}**\n\n"
            f"Your current attendance is "
            f"**{current:.1f}%**."
        )


# ============================================================
# LOGIN PAGE
# ============================================================

def login_page():

    st.title("📚 Attendora")

    st.subheader(
        "Attendance Risk Prediction & Early Warning System"
    )

    st.write(
        "Know your attendance before it becomes a problem."
    )

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        st.subheader("Login")

        role = st.selectbox(
            "Login as",
            ["Student", "Teacher"]
        )

        if role == "Student":

            user_id = st.text_input(
                "Enter Student ID"
            )

        else:

            user_id = st.text_input(
                "Enter Teacher ID"
            )

        if st.button(
            "Login",
            use_container_width=True
        ):

            if role == "Student":

                student = get_student(user_id)

                if len(student) > 0:

                    st.session_state.logged_in = True
                    st.session_state.role = "Student"
                    st.session_state.user_id = user_id

                    st.rerun()

                else:

                    st.error(
                        "Student ID not found."
                    )

            else:

                teacher = get_teacher(user_id)

                if teacher is not None:

                    st.session_state.logged_in = True
                    st.session_state.role = "Teacher"
                    st.session_state.user_id = user_id

                    st.rerun()

                else:

                    st.error(
                        "Teacher ID not found."
                    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

def student_dashboard(student_id):

    student_data = get_student(student_id)

    # Student information
    first_row = student_data.iloc[0]

    name = first_row["name"]
    branch = first_row["branch"]
    semester = first_row["semester"]
    section = first_row["section"]

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    with st.sidebar:

        st.title("📚 Attendora")

        st.write(f"**{name}**")

        st.caption(
            f"{branch} | Semester {semester} | Section {section}"
        )

        st.divider()

        page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Notifications",
                "Profile"
            ]
        )

        st.divider()

        if st.button("Sign Out"):

            st.session_state.clear()

            st.rerun()

    # --------------------------------------------------------
    # GET PREDICTION DATA FOR THIS STUDENT
    # --------------------------------------------------------

    student_predictions = prediction_df[
        prediction_df["student_id"].astype(str)
        == str(student_id)
    ]

    # ========================================================
    # DASHBOARD
    # ========================================================

    if page == "Dashboard":

        st.title(
            f"Welcome, {name} 👋"
        )

        # ----------------------------------------------------
        # OVERALL ATTENDANCE
        # ----------------------------------------------------

        total_attended = student_data[
            "attendance"
        ].sum()

        total_classes = student_data[
            "total_classes"
        ].sum()

        if total_classes > 0:

            overall_attendance = (
                total_attended /
                total_classes
            ) * 100

        else:

            overall_attendance = 0

        st.subheader(
            "Attendance Overview"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Total Classes",
            int(total_classes)
        )

        c2.metric(
            "Classes Attended",
            int(total_attended)
        )

        c3.metric(
            "Overall Attendance",
            f"{overall_attendance:.1f}%"
        )

        st.divider()

        # ----------------------------------------------------
        # SUBJECT-WISE ATTENDANCE
        # ----------------------------------------------------

        st.subheader(
            "Subject-wise Attendance"
        )

        for _, row in student_predictions.iterrows():

            subject = row["subject"]

            current = row["current_attendance"]

            predicted = row["predicted_attendance"]

            risk = row["risk_level"]

            slope = row["trend_slope"]

            direction = row["trend_direction"]

            icon = risk_icon(risk)

            with st.expander(
                f"{icon} {subject} — {current:.1f}%"
            ):

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Current Attendance",
                    f"{current:.1f}%"
                )

                c2.metric(
                    "Predicted Attendance",
                    f"{predicted:.1f}%"
                )

                c3.metric(
                    "Risk",
                    risk
                )

                st.write(
                    f"**Trend:** {direction}"
                )

                st.write(
                    f"**Trend slope:** {slope}"
                )

                # Recovery calculation
                subject_data = student_data[
                    student_data["subject"]
                    == subject
                ]

                latest = (
                    subject_data
                    .sort_values("week")
                    .iloc[-1]
                )

                attended = latest["attendance"]

                total = latest["total_classes"]

                needed = calculate_recovery_classes(
                    attended,
                    total,
                    target=75
                )

                if needed > 0:

                    st.info(
                        f"📚 You need to attend "
                        f"**{needed} consecutive classes** "
                        f"to reach 75% attendance."
                    )

                else:

                    st.success(
                        "Your attendance is already "
                        "at or above 75%."
                    )

                # Notification
                message = notification_message(
                    name,
                    subject,
                    current,
                    predicted,
                    risk
                )

                if risk == "HIGH":

                    st.error(message)

                elif risk == "MEDIUM":

                    st.warning(message)

                else:

                    st.success(message)

        # ----------------------------------------------------
        # ATTENDANCE GRAPH
        # ----------------------------------------------------

        st.subheader(
            "Attendance Trend"
        )

        subjects = student_data[
            "subject"
        ].unique()

        selected_subject = st.selectbox(
            "Select Subject",
            subjects
        )

        graph_data = student_data[
            student_data["subject"]
            == selected_subject
        ].sort_values("week")

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=graph_data["week"],
                y=graph_data[
                    "attendance_percentage"
                ],
                mode="lines+markers",
                name="Actual Attendance"
            )
        )

        # 75% requirement
        fig.add_hline(
            y=75,
            line_dash="dash",
            annotation_text="75% Requirement"
        )

        # Predicted line
        selected_prediction = student_predictions[
            student_predictions["subject"]
            == selected_subject
        ]

        if len(selected_prediction) > 0:

            prediction = selected_prediction.iloc[0]

            future_predictions, _ = (
                __import__(
                    "prediction"
                ).predict_future_attendance(
                    graph_data[
                        "attendance_percentage"
                    ].tolist(),
                    periods_ahead=4
                )
            )

            last_week = int(
                graph_data["week"].max()
            )

            future_weeks = [
                last_week + i
                for i in range(1, 5)
            ]

            fig.add_trace(
                go.Scatter(
                    x=future_weeks,
                    y=future_predictions,
                    mode="lines+markers",
                    name="Predicted Attendance",
                    line=dict(
                        dash="dot"
                    )
                )
            )

        fig.update_layout(
            xaxis_title="Week",
            yaxis_title="Attendance (%)",
            yaxis=dict(
                range=[0, 100]
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # NOTIFICATIONS
    # ========================================================

    elif page == "Notifications":

        st.title("🔔 Notifications")

        warnings = student_predictions[
            student_predictions["risk_level"]
            .isin(["HIGH", "MEDIUM"])
        ]

        if len(warnings) == 0:

            st.success(
                "🎉 No attendance warnings!"
            )

        else:

            for _, row in warnings.iterrows():

                message = notification_message(
                    name,
                    row["subject"],
                    row["current_attendance"],
                    row["predicted_attendance"],
                    row["risk_level"]
                )

                if row["risk_level"] == "HIGH":

                    st.error(message)

                else:

                    st.warning(message)

    # ========================================================
    # PROFILE
    # ========================================================

    elif page == "Profile":

        st.title("👤 Profile")

        st.write(
            f"**Name:** {name}"
        )

        st.write(
            f"**Student ID:** {student_id}"
        )

        st.write(
            f"**Branch:** {branch}"
        )

        st.write(
            f"**Semester:** {semester}"
        )

        st.write(
            f"**Section:** {section}"
        )


# ============================================================
# TEACHER DASHBOARD
# ============================================================

def teacher_dashboard(teacher_id):

    teacher = get_teacher(teacher_id)

    teacher_name = teacher["name"]
    teacher_subject = teacher["subject"]

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    with st.sidebar:

        st.title("📚 Attendora")

        st.write(
            f"**{teacher_name}**"
        )

        st.caption(
            f"Subject: {teacher_subject}"
        )

        st.divider()

        page = st.radio(
            "Navigation",
            [
                "Overview",
                "Student Records",
                "Warnings",
                "Profile"
            ]
        )

        st.divider()

        if st.button("Sign Out"):

            st.session_state.clear()

            st.rerun()

    # --------------------------------------------------------
    # TEACHER'S SUBJECT DATA
    # --------------------------------------------------------

    teacher_data = attendance_df[
        attendance_df["subject"]
        == teacher_subject
    ]

    teacher_predictions = prediction_df[
        prediction_df["subject"]
        == teacher_subject
    ]

    # ========================================================
    # OVERVIEW
    # ========================================================

    if page == "Overview":

        st.title(
            f"Welcome, {teacher_name} 👋"
        )

        st.subheader(
            f"{teacher_subject} — Attendance Overview"
        )

        total_students = (
            teacher_data[
                "student_id"
            ].nunique()
        )

        high_count = len(
            teacher_predictions[
                teacher_predictions["risk_level"]
                == "HIGH"
            ]
        )

        medium_count = len(
            teacher_predictions[
                teacher_predictions["risk_level"]
                == "MEDIUM"
            ]
        )

        low_count = len(
            teacher_predictions[
                teacher_predictions["risk_level"]
                == "LOW"
            ]
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Students",
            total_students
        )

        c2.metric(
            "High Risk",
            high_count
        )

        c3.metric(
            "Medium Risk",
            medium_count
        )

        c4.metric(
            "Low Risk",
            low_count
        )

        st.divider()

        st.subheader(
            "Risk Distribution"
        )

        risk_counts = pd.DataFrame({
            "Risk Level": [
                "HIGH",
                "MEDIUM",
                "LOW"
            ],
            "Students": [
                high_count,
                medium_count,
                low_count
            ]
        })

        st.bar_chart(
            risk_counts.set_index(
                "Risk Level"
            )
        )

    # ========================================================
    # STUDENT RECORDS
    # ========================================================

    elif page == "Student Records":

        st.title(
            "👥 Student Records"
        )

        # ----------------------------------------------------
        # FILTERS
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            search = st.text_input(
                "Search Student ID / Name"
            )

        with col2:

            branches = [
                "All"
            ] + sorted(
                teacher_data[
                    "branch"
                ].astype(str).unique()
            )

            branch_filter = st.selectbox(
                "Branch",
                branches
            )

        with col3:

            semesters = [
                "All"
            ] + sorted(
                teacher_data[
                    "semester"
                ].astype(str).unique()
            )

            semester_filter = st.selectbox(
                "Semester",
                semesters
            )

        filtered = teacher_predictions.copy()

        # Search

        if search:

            filtered = filtered[
                filtered["student_id"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
                |
                filtered["name"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

        # Branch

        if branch_filter != "All":

            filtered = filtered[
                filtered["branch"]
                .astype(str)
                == branch_filter
            ]

        # Semester

        if semester_filter != "All":

            filtered = filtered[
                filtered["semester"]
                .astype(str)
                == semester_filter
            ]

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        display_df = filtered[
            [
                "student_id",
                "name",
                "section",
                "branch",
                "semester",
                "subject",
                "current_attendance",
                "predicted_attendance",
                "trend_direction",
                "risk_level",
                "risk_score"
            ]
        ].copy()

        display_df.columns = [
            "Student ID",
            "Name",
            "Section",
            "Branch",
            "Semester",
            "Subject",
            "Current Attendance",
            "Predicted Attendance",
            "Trend",
            "Risk",
            "Risk Score"
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # STUDENT GRAPH
        # ----------------------------------------------------

        st.subheader(
            "Student Attendance Trend"
        )

        if len(filtered) > 0:

            selected_student = st.selectbox(
                "Select Student",
                filtered["student_id"].unique()
            )

            selected_data = teacher_data[
                teacher_data["student_id"]
                == selected_student
            ].sort_values("week")

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=selected_data["week"],
                    y=selected_data[
                        "attendance_percentage"
                    ],
                    mode="lines+markers",
                    name="Actual Attendance"
                )
            )

            fig.add_hline(
                y=75,
                line_dash="dash",
                annotation_text="75% Requirement"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

    # ========================================================
    # WARNINGS
    # ========================================================

    elif page == "Warnings":

        st.title(
            "⚠️ Students Requiring Attention"
        )

        warnings = teacher_predictions[
            teacher_predictions["risk_level"]
            == "HIGH"
        ].copy()

        if len(warnings) == 0:

            st.success(
                "No high-risk students detected."
            )

        else:

            st.dataframe(
                warnings[
                    [
                        "student_id",
                        "name",
                        "section",
                        "branch",
                        "semester",
                        "current_attendance",
                        "predicted_attendance",
                        "risk_score"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            st.subheader(
                "Warning Messages"
            )

            for _, row in warnings.iterrows():

                st.error(
                    f"🚨 **{row['name']} "
                    f"({row['student_id']})** — "
                    f"{row['subject']}\n\n"
                    f"Current attendance: "
                    f"**{row['current_attendance']:.1f}%**\n\n"
                    f"Predicted attendance: "
                    f"**{row['predicted_attendance']:.1f}%**"
                )

    # ========================================================
    # PROFILE
    # ========================================================

    elif page == "Profile":

        st.title(
            "👤 Teacher Profile"
        )

        st.write(
            f"**Name:** {teacher_name}"
        )

        st.write(
            f"**Teacher ID:** {teacher_id}"
        )

        st.write(
            f"**Subject:** {teacher_subject}"
        )

        st.write(
            f"**Number of Classes:** "
            f"{teacher['num_classes']}"
        )


# ============================================================
# MAIN APPLICATION CONTROLLER
# ============================================================

if "logged_in" not in st.session_state:

    st.session_state.logged_in = False


if not st.session_state.logged_in:

    login_page()

else:

    if st.session_state.role == "Student":

        student_dashboard(
            st.session_state.user_id
        )

    elif st.session_state.role == "Teacher":

        teacher_dashboard(
            st.session_state.user_id
        )