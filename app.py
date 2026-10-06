import streamlit as st
import httpx

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="DevOps Job-Readiness Tracker",
    layout="wide"
)

st.title("📊 DevOps Job-Readiness Tracker")


# ============================================================
# Sidebar Navigation
# ============================================================

st.sidebar.header("Navigation")

page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Tasks", "DSA Tracker"]
)


# ============================================================
# Dashboard
# ============================================================

if page == "Dashboard":

    st.header("Overall Dashboard")

    try:
        response = httpx.get(
            f"{API_BASE_URL}/dashboard",
            timeout=10.0
        )

        if response.status_code == 200:

            data = response.json()

            # ------------------------------------------------
            # Extract nested dashboard values
            # ------------------------------------------------

            overall_pct = data.get(
                "overall", {}
            ).get(
                "pct_done",
                0.0
            )

            active_phase_title = data.get(
                "active_phase", {}
            ).get(
                "title",
                "N/A"
            )

            days_left = data.get(
                "countdown", {}
            ).get(
                "days",
                0
            )

            # ------------------------------------------------
            # Render Metrics
            # ------------------------------------------------

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Overall Progress",
                f"{overall_pct:.1f}%"
            )

            col2.metric(
                "Active Phase",
                active_phase_title
            )

            col3.metric(
                "Days Remaining",
                days_left
            )

            st.divider()

            # ------------------------------------------------
            # Next Up Tasks
            # ------------------------------------------------

            st.subheader("📌 Next Up Tasks")

            next_up = data.get("next_up", [])

            if next_up:

                for task in next_up:

                    phase_code = task.get(
                        "phase_code",
                        "N/A"
                    )

                    item = task.get(
                        "item",
                        "Unnamed task"
                    )

                    st.write(
                        f"- **[{phase_code}]** {item}"
                    )

            else:
                st.info("No upcoming tasks found.")

        else:

            st.error(
                "Failed to load dashboard metrics from API."
            )

    except Exception as e:

        st.error(
            f"Cannot connect to API server: {e}"
        )


# ============================================================
# Tasks
# ============================================================

elif page == "Tasks":
    st.header("Task Management")

    try:
        response = httpx.get(
            f"{API_BASE_URL}/tasks",
            timeout=10.0
        )

        if response.status_code == 200:
            tasks = response.json()

            if not tasks:
                st.info("No tasks found.")

            else:
                # Table header
                header1, header2, header3, header4 = st.columns(
                    [0.5, 3, 1, 1]
                )

                header1.write("**#**")
                header2.write("**Task**")
                header3.write("**Status**")
                header4.write("**Action**")

                st.divider()

                for task in tasks:

                    # API task ID
                    task_id = task.get("id")

                    # Task title
                    task_title = (
                        task.get("item")
                        or task.get("task_name")
                        or task.get("title")
                        or "Unnamed Task"
                    )

                    # Task status
                    task_status = task.get(
                        "status",
                        "Not Started"
                    )

                    col1, col2, col3, col4 = st.columns(
                        [0.5, 3, 1, 1]
                    )

                    # Actual database/API task number
                    col1.write(f"**{task_id}**")

                    # Task name
                    col2.write(f"**{task_title}**")

                    # Status
                    col3.write(f"`{task_status}`")

                    # Cycle status
                    if col4.button(
                        "Cycle Status",
                        key=f"btn_task_{task_id}"
                    ):
                        update_response = httpx.post(
                            f"{API_BASE_URL}/tasks/"
                            f"{task_id}/cycle-status",
                            timeout=10.0
                        )

                        if update_response.status_code == 200:
                            st.rerun()

                        else:
                            st.error(
                                f"Failed to update task #{task_id}. "
                                f"Server responded with status code "
                                f"{update_response.status_code}."
                            )

        else:
            st.error(
                f"Failed to fetch tasks. "
                f"Server responded with status code "
                f"{response.status_code}."
            )

    except httpx.RequestError as e:
        st.error(
            f"Cannot connect to API server: {e}"
        )

    except Exception as e:
        st.error(
            f"Error fetching tasks: {e}"
        )


# ============================================================
# DSA Tracker
# ============================================================

elif page == "DSA Tracker":

    st.header("DSA Log")

    with st.form("add_dsa_form"):

        topic = st.text_input(
            "Topic"
        )

        pattern = st.text_input(
            "Pattern"
        )

        problem = st.text_input(
            "Problem Name"
        )

        submitted = st.form_submit_button(
            "Submit Problem"
        )

        if submitted:

            payload = {
                "topic": topic,
                "pattern": pattern,
                "problem_name": problem
            }

            try:

                response = httpx.post(
                    f"{API_BASE_URL}/dsa",
                    json=payload,
                    timeout=10.0
                )

                if response.status_code in [200, 201]:

                    st.success(
                        "DSA entry saved!"
                    )

                else:

                    st.error(
                        "Failed to save DSA entry."
                    )

            except Exception as e:

                st.error(
                    f"Error saving DSA entry: {e}"
                )
