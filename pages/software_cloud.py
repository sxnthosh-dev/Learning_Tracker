import csv
import io
from datetime import date

import httpx
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8000/api/v1"


# ============================================================
# API HELPERS
# ============================================================

def api_get(endpoint: str):
    try:
        response = httpx.get(
            f"{API_BASE_URL}{endpoint}",
            timeout=15,
        )

        if response.status_code == 200:
            return response.json()

        st.error(
            f"API error {response.status_code}: "
            f"{response.text}"
        )

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )

    return None


def api_post(endpoint: str, payload: dict):
    try:
        response = httpx.post(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=15,
        )

        if response.status_code in (200, 201):
            return response.json()

        st.error(
            f"API error {response.status_code}: "
            f"{response.text}"
        )

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )

    return None


def api_put(endpoint: str, payload: dict):
    try:
        response = httpx.put(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=15,
        )

        if response.status_code in (200, 201):
            return response.json()

        st.error(
            f"API error {response.status_code}: "
            f"{response.text}"
        )

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )

    return None


def api_patch(endpoint: str, payload: dict):
    try:
        response = httpx.patch(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=15,
        )

        if response.status_code in (200, 201):
            return response.json()

        st.error(
            f"API error {response.status_code}: "
            f"{response.text}"
        )

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )

    return None


def api_delete(endpoint: str):
    try:
        response = httpx.delete(
            f"{API_BASE_URL}{endpoint}",
            timeout=15,
        )

        if response.status_code in (200, 204):
            return True

        st.error(
            f"API error {response.status_code}: "
            f"{response.text}"
        )

    except httpx.RequestError as exc:
        st.error(
            "Cannot connect to the FastAPI backend.\n\n"
            f"Error: {exc}"
        )

    return False


# ============================================================
# HOME
# ============================================================

def home():
    st.header("🏠 Software + Cloud Engineer")

    st.write(
        "Your combined Software Engineering and "
        "Cloud Engineering career dashboard."
    )

    data = api_get("/home")

    if not data:
        return

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Topics",
        f"{data.get('completed_topics', 0)} / "
        f"{data.get('total_topics', 0)}",
        f"{data.get('topic_completion_pct', 0)}%",
    )

    col2.metric(
        "LeetCode",
        f"{data.get('solved_leetcode', 0)} / "
        f"{data.get('total_leetcode', 0)}",
        f"{data.get('leetcode_completion_pct', 0)}%",
    )

    col3.metric(
        "Daily Plan",
        f"{data.get('completed_daily_tasks', 0)} / "
        f"{data.get('total_daily_tasks', 0)}",
        f"{data.get('daily_completion_pct', 0)}%",
    )

    col4.metric(
        "Cloud Roadmap",
        f"{data.get('completed_cloud_stages', 0)} / "
        f"{data.get('total_cloud_stages', 0)}",
        f"{data.get('cloud_completion_pct', 0)}%",
    )

    st.divider()

    col5, col6 = st.columns(2)

    col5.metric(
        "Projects",
        f"{data.get('completed_projects', 0)} / "
        f"{data.get('total_projects', 0)}",
    )

    col6.metric(
        "🔥 Current Streak",
        data.get("current_streak", 0),
    )

    st.divider()

    st.subheader("🎯 Career Focus")

    st.info(
        "Build strong Python fundamentals, maintain Java "
        "interview readiness, solve DSA problems, build "
        "projects, and develop practical Cloud/DevOps skills."
    )

    st.subheader("📈 Progress Overview")

    progress_items = [
        (
            "Python + Java Topics",
            data.get("topic_completion_pct", 0),
        ),
        (
            "LeetCode",
            data.get("leetcode_completion_pct", 0),
        ),
        (
            "30-Day Daily Plan",
            data.get("daily_completion_pct", 0),
        ),
        (
            "Cloud Engineer Roadmap",
            data.get("cloud_completion_pct", 0),
        ),
    ]

    for label, percentage in progress_items:
        percentage = float(percentage or 0)

        st.write(
            f"**{label}: {percentage:.1f}%**"
        )

        st.progress(
            min(max(percentage / 100, 0.0), 1.0)
        )


# ============================================================
# PYTHON + JAVA
# ============================================================

def python_java():
    st.header("🐍☕ Python + Java")

    st.write(
        "Learn the same core programming concepts in "
        "both Python and Java."
    )

    data = api_get("/topic-progress")

    if not data:
        return

    records = data if isinstance(data, list) else data.get(
        "items",
        [],
    )

    if not records:
        st.info("No programming topics found.")
        return

    languages = sorted(
        {
            str(item.get("language", "Unknown"))
            for item in records
        }
    )

    selected_language = st.selectbox(
        "Language",
        ["All"] + languages,
    )

    statuses = [
        "Not Started",
        "In Progress",
        "Completed",
    ]

    selected_status = st.selectbox(
        "Status",
        ["All"] + statuses,
    )

    filtered = records

    if selected_language != "All":
        filtered = [
            item
            for item in filtered
            if item.get("language")
            == selected_language
        ]

    if selected_status != "All":
        filtered = [
            item
            for item in filtered
            if item.get("status")
            == selected_status
        ]

    st.write(
        f"Showing **{len(filtered)}** topics."
    )

    for item in filtered:
        topic_id = item.get("id")

        concept = item.get(
            "concept",
            "Unnamed Concept",
        )

        language = item.get(
            "language",
            "Unknown",
        )

        status = item.get(
            "status",
            "Not Started",
        )

        with st.expander(
            f"{language} — {concept}"
        ):
            st.write(
                f"**Current status:** {status}"
            )

            if item.get("notes"):
                st.write(
                    f"**Notes:** {item['notes']}"
                )

            new_status = st.selectbox(
                "Update status",
                statuses,
                index=(
                    statuses.index(status)
                    if status in statuses
                    else 0
                ),
                key=f"topic_status_{topic_id}",
            )

            notes = st.text_area(
                "Notes",
                value=item.get("notes") or "",
                key=f"topic_notes_{topic_id}",
            )

            if st.button(
                "Save Progress",
                key=f"topic_save_{topic_id}",
            ):
                result = api_patch(
                    f"/topic-progress/{topic_id}",
                    {
                        "status": new_status,
                        "notes": notes,
                    },
                )

                if result:
                    st.success(
                        "Topic progress saved."
                    )
                    st.rerun()


# ============================================================
# AI PROGRAMMING TUTOR
# ============================================================

def ai_tutor():
    st.header("🤖 AI Programming Tutor")

    st.write(
        "Use the tracker as a structured programming "
        "learning assistant."
    )

    st.subheader("Ask a Programming Question")

    question = st.text_area(
        "Your question",
        placeholder=(
            "Example: Explain Python dictionaries "
            "and compare them with Java HashMap."
        ),
        height=150,
    )

    language = st.selectbox(
        "Primary language",
        [
            "Python",
            "Java",
            "Both",
        ],
    )

    difficulty = st.selectbox(
        "Difficulty",
        [
            "Beginner",
            "Intermediate",
            "Advanced",
        ],
    )

    if st.button(
        "Generate Tutor Prompt",
        type="primary",
    ):
        if not question.strip():
            st.warning(
                "Please enter a question."
            )
            return

        prompt = f"""
Act as my {difficulty.lower()}-level
software engineering tutor.

Language focus: {language}

Question:
{question}

Please:
1. Explain the concept clearly.
2. Use a simple example.
3. Show Python and Java differences when useful.
4. Explain common mistakes.
5. Give me one small practice exercise.
6. Do not skip important fundamentals.
""".strip()

        st.subheader("📋 Tutor Prompt")

        st.code(
            prompt,
            language="text",
        )

        st.info(
            "You can copy this prompt into your preferred "
            "AI assistant. The Prompt Library contains "
            "additional reusable prompts."
        )

    st.divider()

    st.subheader("💡 Recommended Learning Method")

    st.markdown(
        """
**Learn → Explain → Code → Test → Debug → Review**

For every programming concept:

1. Understand the concept.
2. Write a small example.
3. Modify the example yourself.
4. Solve a small exercise.
5. Identify mistakes.
6. Record what you learned.
7. Revisit the concept later.
"""
    )


# ============================================================
# LEETCODE
# ============================================================

def leetcode():
    st.header("🧩 LeetCode Practice")

    data = api_get("/leetcode")

    if not data:
        return

    records = data if isinstance(data, list) else data.get(
        "items",
        [],
    )

    st.write(
        f"Total problems: **{len(records)}**"
    )

    col1, col2, col3 = st.columns(3)

    difficulties = sorted(
        {
            str(item.get("difficulty", "Unknown"))
            for item in records
        }
    )

    statuses = sorted(
        {
            str(item.get("status", "Unknown"))
            for item in records
        }
    )

    topics = sorted(
        {
            str(item.get("topic", "Unknown"))
            for item in records
        }
    )

    with col1:
        difficulty = st.selectbox(
            "Difficulty",
            ["All"] + difficulties,
        )

    with col2:
        status = st.selectbox(
            "Status",
            ["All"] + statuses,
        )

    with col3:
        topic = st.selectbox(
            "Topic",
            ["All"] + topics,
        )

    filtered = records

    if difficulty != "All":
        filtered = [
            item for item in filtered
            if item.get("difficulty")
            == difficulty
        ]

    if status != "All":
        filtered = [
            item for item in filtered
            if item.get("status")
            == status
        ]

    if topic != "All":
        filtered = [
            item for item in filtered
            if item.get("topic")
            == topic
        ]

    st.write(
        f"Showing **{len(filtered)}** problems."
    )

    st.divider()

    for item in filtered:
        problem_id = item.get("id")

        number = item.get(
            "number",
            "",
        )

        title = item.get(
            "title",
            "Unnamed Problem",
        )

        difficulty_value = item.get(
            "difficulty",
            "Unknown",
        )

        current_status = item.get(
            "status",
            "Not Started",
        )

        display_title = (
            f"#{number} — {title}"
            if number
            else title
        )

        with st.expander(
            f"{display_title} "
            f"({difficulty_value})"
        ):
            st.write(
                f"**Topic:** "
                f"{item.get('topic', 'N/A')}"
            )

            st.write(
                f"**Current status:** "
                f"{current_status}"
            )

            if item.get("acceptance"):
                st.write(
                    f"**Acceptance:** "
                    f"{item['acceptance']}"
                )

            if item.get("frequency"):
                st.write(
                    f"**Frequency:** "
                    f"{item['frequency']}"
                )

            statuses_for_edit = [
                "Not Started",
                "In Progress",
                "Solved",
            ]

            new_status = st.selectbox(
                "Status",
                statuses_for_edit,
                index=(
                    statuses_for_edit.index(
                        current_status
                    )
                    if current_status
                    in statuses_for_edit
                    else 0
                ),
                key=f"lc_status_{problem_id}",
            )

            confidence = st.slider(
                "Confidence",
                min_value=1,
                max_value=5,
                value=int(
                    item.get("confidence") or 1
                ),
                key=f"lc_confidence_{problem_id}",
            )

            revision_priority = st.selectbox(
                "Revision priority",
                [
                    "Low",
                    "Medium",
                    "High",
                ],
                index=[
                    "Low",
                    "Medium",
                    "High",
                ].index(
                    item.get(
                        "revision_priority",
                        "Medium",
                    )
                )
                if item.get(
                    "revision_priority",
                    "Medium",
                )
                in ["Low", "Medium", "High"]
                else 1,
                key=f"lc_priority_{problem_id}",
            )

            revision_flag = st.checkbox(
                "Mark for revision",
                value=bool(
                    item.get(
                        "revision_flag",
                        False,
                    )
                ),
                key=f"lc_revision_{problem_id}",
            )

            notes = st.text_area(
                "Notes",
                value=item.get("notes") or "",
                key=f"lc_notes_{problem_id}",
            )

            mistakes = st.text_area(
                "Mistakes",
                value=item.get("mistakes") or "",
                key=f"lc_mistakes_{problem_id}",
            )

            if st.button(
                "Save LeetCode Progress",
                key=f"lc_save_{problem_id}",
            ):
                result = api_patch(
                    f"/leetcode/{problem_id}",
                    {
                        "status": new_status,
                        "confidence": confidence,
                        "revision_priority": revision_priority,
                        "revision_flag": revision_flag,
                        "notes": notes,
                        "mistakes": mistakes,
                    },
                )

                if result:
                    st.success(
                        "LeetCode progress saved."
                    )
                    st.rerun()

    st.divider()

    st.subheader("📥 Import LeetCode CSV")

    st.caption(
        "CSV import is available when your backend "
        "supports the corresponding import endpoint."
    )

    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
    )

    if uploaded_file is not None:
        csv_text = uploaded_file.getvalue().decode(
            "utf-8-sig"
        )

        reader = csv.DictReader(
            io.StringIO(csv_text)
        )

        rows = list(reader)

        st.write(
            f"Detected **{len(rows)}** CSV rows."
        )

        if rows:
            st.dataframe(
                rows[:10],
                use_container_width=True,
            )

        st.info(
            "Review the CSV before importing. "
            "The current backend seed structure uses "
            "number, title, difficulty, status, language, "
            "topic, acceptance, frequency, and stage fields."
        )


# ============================================================
# DAILY PLAN
# ============================================================

def daily_plan():
    st.header("📅 30-Day Software Engineering Plan")

    data = api_get("/daily-plan")

    if not data:
        return

    records = data if isinstance(data, list) else data.get(
        "items",
        [],
    )

    if not records:
        st.info("No daily plan found.")
        return

    completed = sum(
        1
        for item in records
        if item.get("completed")
    )

    percentage = (
        completed / len(records) * 100
        if records
        else 0
    )

    st.metric(
        "Plan Progress",
        f"{completed}/{len(records)}",
        f"{percentage:.1f}%",
    )

    st.progress(
        min(max(percentage / 100, 0), 1)
    )

    st.divider()

    selected_day = st.selectbox(
        "Select Day",
        records,
        format_func=lambda item: (
            f"Day {item.get('day_number', '?')} — "
            f"{item.get('concept', 'Learning')}"
        ),
    )

    if not selected_day:
        return

    day_id = selected_day.get("id")

    st.subheader(
        f"Day {selected_day.get('day_number')}"
    )

    st.write(
        f"**Date:** "
        f"{selected_day.get('task_date', 'N/A')}"
    )

    st.write(
        f"**Concept:** "
        f"{selected_day.get('concept', 'N/A')}"
    )

    st.write(
        f"**Python Task:** "
        f"{selected_day.get('python_task', 'N/A')}"
    )

    st.write(
        f"**Java Task:** "
        f"{selected_day.get('java_task', 'N/A')}"
    )

    st.write(
        f"**LeetCode:** "
        f"{selected_day.get('leetcode_task', 'N/A')}"
    )

    st.write(
        f"**AI Prompt:** "
        f"{selected_day.get('ai_prompt', 'N/A')}"
    )

    st.divider()

    completed_value = st.checkbox(
        "Mark this day as completed",
        value=bool(
            selected_day.get("completed")
        ),
        key=f"daily_completed_{day_id}",
    )

    notes = st.text_area(
        "Notes",
        value=selected_day.get("notes") or "",
        key=f"daily_notes_{day_id}",
    )

    if st.button(
        "Save Daily Progress",
        type="primary",
    ):
        result = api_patch(
            f"/daily-plan/{day_id}",
            {
                "completed": completed_value,
                "notes": notes,
            },
        )

        if result:
            st.success(
                "Daily progress saved."
            )
            st.rerun()


# ============================================================
# DAILY TRACKER
# ============================================================

def daily_tracker():
    st.header("🔥 Daily Tracker")

    streak = api_get("/streak")

    if streak:
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Current Streak",
            streak.get("current_streak", 0),
        )

        col2.metric(
            "Longest Streak",
            streak.get("longest_streak", 0),
        )

        col3.metric(
            "Completed Days",
            streak.get("completed_days", 0),
        )

    st.divider()

    today = api_get("/daily-plan/today")

    if today:
        st.subheader("📌 Today's Focus")

        st.write(
            f"**Day {today.get('day_number', '?')}**"
        )

        st.write(
            f"**Concept:** "
            f"{today.get('concept', 'N/A')}"
        )

        st.write(
            f"**Python:** "
            f"{today.get('python_task', 'N/A')}"
        )

        st.write(
            f"**Java:** "
            f"{today.get('java_task', 'N/A')}"
        )

        st.write(
            f"**LeetCode:** "
            f"{today.get('leetcode_task', 'N/A')}"
        )

        st.write(
            f"**AI Prompt:** "
            f"{today.get('ai_prompt', 'N/A')}"
        )

        if today.get("completed"):
            st.success(
                "Today's task is completed. 🎉"
            )
        else:
            st.warning(
                "Today's task is not completed yet."
            )

    st.divider()

    st.subheader("🎯 Daily Rules")

    st.markdown(
        """
- Complete the planned programming concept.
- Write code instead of only watching tutorials.
- Solve the assigned LeetCode problem.
- Spend time on Cloud/DevOps skills.
- Record mistakes and lessons learned.
- Keep the streak alive.
"""
    )


# ============================================================
# CLOUD ROADMAP
# ============================================================

def cloud():
    st.header("☁️ Cloud Engineer Roadmap")

    data = api_get("/cloud-roadmap")

    if not data:
        return

    records = data if isinstance(data, list) else data.get(
        "items",
        [],
    )

    if not records:
        st.info("No cloud roadmap found.")
        return

    total = len(records)

    completed = sum(
        1
        for item in records
        if item.get("completed")
    )

    percentage = (
        completed / total * 100
        if total
        else 0
    )

    st.metric(
        "Cloud Roadmap Progress",
        f"{completed}/{total}",
        f"{percentage:.1f}%",
    )

    st.progress(
        min(max(percentage / 100, 0), 1)
    )

    st.divider()

    stages = {}

    for item in records:
        stage_number = item.get(
            "stage_number",
            0,
        )

        stages.setdefault(
            stage_number,
            [],
        ).append(item)

    for stage_number in sorted(stages):
        stage_items = stages[stage_number]

        stage_title = stage_items[0].get(
            "stage_title",
            f"Stage {stage_number}",
        )

        with st.expander(
            f"Stage {stage_number} — "
            f"{stage_title}"
        ):
            for item in stage_items:
                item_id = item.get("id")

                completed_value = bool(
                    item.get("completed")
                )

                checkbox_value = st.checkbox(
                    item.get(
                        "topic",
                        "Cloud Topic",
                    ),
                    value=completed_value,
                    key=f"cloud_{item_id}",
                )

                st.caption(
                    item.get(
                        "description",
                        "",
                    )
                )

                if checkbox_value != completed_value:
                    result = api_patch(
                        f"/cloud-roadmap/{item_id}",
                        {
                            "completed": checkbox_value,
                        },
                    )

                    if result:
                        st.success(
                            "Cloud roadmap updated."
                        )
                        st.rerun()


# ============================================================
# PROJECTS
# ============================================================

def projects():
    st.header("🚀 Projects")

    st.write(
        "Track portfolio projects that demonstrate "
        "your Software + Cloud Engineering skills."
    )

    data = api_get("/projects")

    records = []

    if data:
        records = (
            data
            if isinstance(data, list)
            else data.get("items", [])
        )

    if records:
        st.subheader("📂 Existing Projects")

        for project in records:
            project_id = project.get("id")

            with st.expander(
                project.get(
                    "name",
                    "Unnamed Project",
                )
            ):
                st.write(
                    f"**Stage:** "
                    f"{project.get('stage', 'N/A')}"
                )

                st.write(
                    project.get(
                        "description",
                        "",
                    )
                )

                if project.get("tech_stack"):
                    st.write(
                        f"**Tech Stack:** "
                        f"{project['tech_stack']}"
                    )

                if project.get("repo_url"):
                    st.write(
                        f"**Repository:** "
                        f"{project['repo_url']}"
                    )

                if project.get("live_url"):
                    st.write(
                        f"**Live URL:** "
                        f"{project['live_url']}"
                    )

                if project.get("notes"):
                    st.write(
                        f"**Notes:** "
                        f"{project['notes']}"
                    )

    else:
        st.info(
            "No projects have been added yet."
        )

    st.divider()

    st.subheader("➕ Add Project")

    with st.form("new_project_form"):
        name = st.text_input(
            "Project name"
        )

        description = st.text_area(
            "Description"
        )

        stage = st.selectbox(
            "Stage",
            [
                "Idea",
                "Development",
                "Testing",
                "Deployment",
                "Portfolio",
                "Completed",
            ],
        )

        tech_stack = st.text_input(
            "Tech stack",
            placeholder=(
                "Python, FastAPI, Docker, AWS..."
            ),
        )

        repo_url = st.text_input(
            "Repository URL"
        )

        live_url = st.text_input(
            "Live URL"
        )

        start_date = st.date_input(
            "Start date",
            value=date.today(),
        )

        target_date = st.date_input(
            "Target date",
            value=date.today(),
        )

        notes = st.text_area(
            "Notes"
        )

        submitted = st.form_submit_button(
            "Create Project",
            type="primary",
        )

    if submitted:
        if not name.strip():
            st.warning(
                "Project name is required."
            )
            return

        payload = {
            "name": name.strip(),
            "description": description.strip(),
            "stage": stage,
            "tech_stack": tech_stack.strip(),
            "repo_url": repo_url.strip() or None,
            "live_url": live_url.strip() or None,
            "start_date": start_date.isoformat(),
            "target_date": target_date.isoformat(),
            "notes": notes.strip(),
        }

        result = api_post(
            "/projects",
            payload,
        )

        if result:
            st.success(
                "Project created successfully."
            )
            st.rerun()


# ============================================================
# ANALYTICS
# ============================================================

def analytics():
    st.header("📈 Analytics")

    data = api_get("/analytics")

    if not data:
        return

    st.subheader("Overall Progress")

    topic_pct = float(
        data.get(
            "topic_completion_pct",
            0,
        )
        or 0
    )

    leetcode_pct = float(
        data.get(
            "leetcode_completion_pct",
            0,
        )
        or 0
    )

    daily_pct = float(
        data.get(
            "daily_completion_pct",
            0,
        )
        or 0
    )

    cloud_pct = float(
        data.get(
            "cloud_completion_pct",
            0,
        )
        or 0
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Programming Topics",
            f"{topic_pct:.1f}%",
        )

        st.progress(
            min(max(topic_pct / 100, 0), 1)
        )

        st.metric(
            "LeetCode",
            f"{leetcode_pct:.1f}%",
        )

        st.progress(
            min(max(leetcode_pct / 100, 0), 1)
        )

    with col2:
        st.metric(
            "Daily Plan",
            f"{daily_pct:.1f}%",
        )

        st.progress(
            min(max(daily_pct / 100, 0), 1)
        )

        st.metric(
            "Cloud Roadmap",
            f"{cloud_pct:.1f}%",
        )

        st.progress(
            min(max(cloud_pct / 100, 0), 1)
        )

    st.divider()

    st.subheader("📊 Raw Analytics")

    st.json(data)


# ============================================================
# PROMPT LIBRARY
# ============================================================

def prompt_library():
    st.header("📚 Prompt Library")

    st.write(
        "Reusable prompts for learning, coding, "
        "debugging, interviews, and projects."
    )

    data = api_get("/prompts")

    if not data:
        return

    records = data if isinstance(data, list) else data.get(
        "items",
        [],
    )

    if not records:
        st.info(
            "No prompts found."
        )
        return

    categories = sorted(
        {
            str(
                item.get(
                    "category",
                    "General",
                )
            )
            for item in records
        }
    )

    selected_category = st.selectbox(
        "Category",
        ["All"] + categories,
    )

    filtered = records

    if selected_category != "All":
        filtered = [
            item
            for item in filtered
            if item.get("category")
            == selected_category
        ]

    for item in filtered:
        title = item.get(
            "title",
            "Untitled Prompt",
        )

        category = item.get(
            "category",
            "General",
        )

        content = item.get(
            "content",
            "",
        )

        with st.expander(
            f"{title} — {category}"
        ):
            st.code(
                content,
                language="text",
            )

            st.caption(
                "Copy the prompt above and adapt it "
                "to your current learning task."
            )


# ============================================================
# PREFERENCES
# ============================================================

def preferences():
    st.header("⚙️ Preferences")

    data = api_get("/preferences")

    if not data:
        return

    python_pct = int(
        data.get(
            "python_target_pct",
            75,
        )
    )

    java_pct = int(
        data.get(
            "java_target_pct",
            25,
        )
    )

    interview_mode = data.get(
        "interview_mode",
        "Balanced",
    )

    ai_provider = data.get(
        "ai_provider",
        "Local/Fallback",
    )

    st.subheader("🎯 Programming Focus")

    python_target = st.slider(
        "Python target percentage",
        min_value=0,
        max_value=100,
        value=python_pct,
        step=5,
    )

    java_target = 100 - python_target

    st.metric(
        "Java target percentage",
        f"{java_target}%",
    )

    st.caption(
        "Python + Java targets must always total 100%."
    )

    st.divider()

    st.subheader("💼 Interview Mode")

    interview_options = [
        "Balanced",
        "Software Engineering",
        "Cloud / DevOps",
        "DSA Heavy",
    ]

    if interview_mode not in interview_options:
        interview_mode = "Balanced"

    selected_interview_mode = st.selectbox(
        "Interview focus",
        interview_options,
        index=interview_options.index(
            interview_mode
        ),
    )

    st.subheader("🤖 AI Provider")

    ai_options = [
        "Local/Fallback",
        "OpenAI",
        "Claude",
        "Gemini",
    ]

    if ai_provider not in ai_options:
        ai_provider = "Local/Fallback"

    selected_ai_provider = st.selectbox(
        "Preferred AI provider",
        ai_options,
        index=ai_options.index(
            ai_provider
        ),
    )

    if st.button(
        "Save Preferences",
        type="primary",
    ):
        result = api_put(
            "/preferences",
            {
                "python_target_pct": python_target,
                "java_target_pct": java_target,
                "interview_mode": (
                    selected_interview_mode
                ),
                "ai_provider": (
                    selected_ai_provider
                ),
            },
        )

        if result:
            st.success(
                "Preferences saved successfully."
            )
            st.rerun()
