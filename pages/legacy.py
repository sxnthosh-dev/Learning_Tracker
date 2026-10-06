import streamlit as st
import httpx


API_BASE_URL = "http://127.0.0.1:8000/api/v1"


def dashboard():
    st.header("📊 Dashboard")

    try:
        response = httpx.get(
            f"{API_BASE_URL}/dashboard",
            timeout=10,
        )

        if response.status_code != 200:
            st.error(
                f"Unable to load dashboard. "
                f"API returned {response.status_code}"
            )
            return

        data = response.json()

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Overall Progress",
            f"{data.get('overall_progress_pct', 0)}%",
        )

        col2.metric(
            "Current Week",
            data.get("current_week", 0),
        )

        col3.metric(
            "Study Hours",
            data.get("study_hours_completed", 0),
        )

        col4.metric(
            "Completed Tasks",
            f"{data.get('completed_items', 0)} / "
            f"{data.get('total_items', 0)}",
        )

        st.divider()

        st.subheader("🎯 Career Target")

        st.write(
            f"**Role:** "
            f"{data.get('target_role', 'Not available')}"
        )

        st.write(
            f"**Owner:** "
            f"{data.get('owner_name', 'Not available')}"
        )

        st.write(
            f"**Plan:** "
            f"{data.get('plan_start', 'N/A')} → "
            f"{data.get('plan_end', 'N/A')}"
        )

        st.divider()

        st.subheader("📚 Current Phase")

        active_phase = data.get("active_phase")

        if active_phase:
            st.info(
                f"**{active_phase.get('code', '')} — "
                f"{active_phase.get('name', '')}**"
            )

            st.write(
                active_phase.get(
                    "description",
                    "",
                )
            )

        st.divider()

        st.subheader("📌 Phase Progress")

        phases = data.get("phases", [])

        if phases:
            for phase in phases:
                completed = phase.get("completed_items", 0)
                total = phase.get("total_items", 0)

                if total:
                    progress = completed / total
                else:
                    progress = 0

                st.write(
                    f"**{phase.get('code', '')} — "
                    f"{phase.get('name', '')}** "
                    f"({completed}/{total})"
                )

                st.progress(progress)

        st.divider()

        st.subheader("📝 Next Tasks")

        next_tasks = data.get("next_tasks", [])

        if next_tasks:
            for task in next_tasks:
                st.write(
                    f"**{task.get('title', 'Task')}**"
                )

                if task.get("description"):
                    st.caption(task["description"])
        else:
            st.info("No upcoming tasks found.")

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )


def tasks():
    st.header("📝 Tasks")

    try:
        response = httpx.get(
            f"{API_BASE_URL}/tasks",
            timeout=10,
        )

        if response.status_code != 200:
            st.error(
                f"Unable to load tasks. "
                f"API returned {response.status_code}"
            )
            return

        tasks_data = response.json()

        if not tasks_data:
            st.info("No tasks found.")
            return

        st.write(
            f"Total tasks: **{len(tasks_data)}**"
        )

        st.divider()

        for task in tasks_data:
            task_id = task.get("id")

            title = (
                task.get("title")
                or task.get("name")
                or f"Task {task_id}"
            )

            with st.expander(
                f"{task_id}. {title}"
            ):
                if task.get("description"):
                    st.write(task["description"])

                if task.get("week"):
                    st.write(
                        f"**Week:** {task['week']}"
                    )

                if task.get("phase"):
                    st.write(
                        f"**Phase:** {task['phase']}"
                    )

                status = task.get(
                    "status",
                    "Not Started",
                )

                st.write(
                    f"**Status:** {status}"
                )

                if task_id is not None:
                    new_status = st.selectbox(
                        "Update status",
                        [
                            "Not Started",
                            "In Progress",
                            "Completed",
                        ],
                        index=[
                            "Not Started",
                            "In Progress",
                            "Completed",
                        ].index(status)
                        if status
                        in [
                            "Not Started",
                            "In Progress",
                            "Completed",
                        ]
                        else 0,
                        key=f"task_status_{task_id}",
                    )

                    if st.button(
                        "Save Status",
                        key=f"save_task_{task_id}",
                    ):
                        try:
                            update_response = httpx.patch(
                                f"{API_BASE_URL}/tasks/{task_id}",
                                json={
                                    "status": new_status
                                },
                                timeout=10,
                            )

                            if update_response.status_code in (
                                200,
                                204,
                            ):
                                st.success(
                                    "Task status updated."
                                )
                                st.rerun()
                            else:
                                st.error(
                                    "Unable to update task. "
                                    f"API returned "
                                    f"{update_response.status_code}"
                                )

                        except httpx.RequestError as exc:
                            st.error(
                                f"API connection error: {exc}"
                            )

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )


def dsa_tracker():
    st.header("🧠 DSA Tracker")

    st.write(
        "Record your DSA practice problems here."
    )

    with st.form("dsa_form"):
        problem = st.text_input(
            "Problem",
            placeholder="Example: Two Sum",
        )

        difficulty = st.selectbox(
            "Difficulty",
            [
                "Easy",
                "Medium",
                "Hard",
            ],
        )

        topic = st.text_input(
            "Topic",
            placeholder="Example: Arrays",
        )

        status = st.selectbox(
            "Status",
            [
                "Not Started",
                "In Progress",
                "Solved",
            ],
        )

        notes = st.text_area(
            "Notes"
        )

        submitted = st.form_submit_button(
            "Add DSA Problem"
        )

    if submitted:
        if not problem.strip():
            st.warning(
                "Please enter a problem name."
            )
            return

        payload = {
            "problem": problem.strip(),
            "difficulty": difficulty,
            "topic": topic.strip(),
            "status": status,
            "notes": notes.strip(),
        }

        try:
            response = httpx.post(
                f"{API_BASE_URL}/dsa",
                json=payload,
                timeout=10,
            )

            if response.status_code in (
                200,
                201,
            ):
                st.success(
                    "DSA problem added successfully."
                )
                st.rerun()
            else:
                st.error(
                    "Unable to add DSA problem.\n\n"
                    f"API returned "
                    f"{response.status_code}\n\n"
                    f"{response.text}"
                )

        except httpx.RequestError as exc:
            st.error(
                "Cannot connect to the FastAPI backend.\n\n"
                f"Error: {exc}"
            )

    st.divider()

    st.subheader("📚 Existing DSA Problems")

    try:
        response = httpx.get(
            f"{API_BASE_URL}/dsa",
            timeout=10,
        )

        if response.status_code != 200:
            st.error(
                f"Unable to load DSA problems. "
                f"API returned {response.status_code}"
            )
            return

        problems = response.json()

        if not problems:
            st.info(
                "No DSA problems recorded yet."
            )
            return

        for item in problems:
            problem_name = (
                item.get("problem")
                or item.get("problem_name")
                or "Unnamed Problem"
            )

            st.write(
                f"**{problem_name}**"
            )

            details = []

            if item.get("difficulty"):
                details.append(
                    f"Difficulty: {item['difficulty']}"
                )

            if item.get("topic"):
                details.append(
                    f"Topic: {item['topic']}"
                )

            if item.get("status"):
                details.append(
                    f"Status: {item['status']}"
                )

            if details:
                st.caption(
                    " | ".join(details)
                )

            if item.get("notes"):
                st.write(
                    item["notes"]
                )

            st.divider()

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )
