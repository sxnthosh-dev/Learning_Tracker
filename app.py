import streamlit as st
import requests

from pages.legacy import dashboard, tasks, dsa_tracker
from pages.software_cloud import (
    home,
    python_java,
    ai_tutor,
    leetcode,
    daily_plan,
    daily_tracker,
    cloud,
    projects,
    analytics,
    prompt_library,
    preferences,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="DevOps Job-Readiness Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# BACKEND HEALTH CHECK
# ============================================================

API_BASE_URL = "http://127.0.0.1:8000"

@st.cache_data(ttl=10)
def check_backend_status() -> bool:
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return res.status_code == 200
    except Exception:
        return False


# ============================================================
# APPLICATION HEADER & STATUS
# ============================================================

st.title("📊 DevOps Job-Readiness Tracker")

if not check_backend_status():
    st.error(
        "⚠️ **FastAPI Backend Offline**: Make sure Uvicorn is running at "
        "`http://127.0.0.1:8000` via `uvicorn main:app --reload`."
    )


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.header("Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard",
        "Tasks",
        "DSA Tracker",
        "Software + Cloud Engineer",
    ],
)


# ============================================================
# ORIGINAL / LEGACY TRACKER
# ============================================================

if page == "Dashboard":
    dashboard()

elif page == "Tasks":
    tasks()

elif page == "DSA Tracker":
    dsa_tracker()


# ============================================================
# SOFTWARE + CLOUD ENGINEER TRACKER
# ============================================================

elif page == "Software + Cloud Engineer":

    st.sidebar.divider()

    st.sidebar.subheader("Software + Cloud")

    software_cloud_page = st.sidebar.radio(
        "Section",
        [
            "Home",
            "Python + Java",
            "AI Programming Tutor",
            "LeetCode Practice",
            "Daily Plan",
            "Daily Tracker",
            "Cloud Engineer Roadmap",
            "Projects",
            "Analytics",
            "Prompt Library",
            "Preferences",
        ],
        key="software_cloud_navigation",
    )

    st.sidebar.divider()

    st.sidebar.caption(
        "Software + Cloud Engineer Career Tracker"
    )

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if software_cloud_page == "Home":
        home()

    # --------------------------------------------------------
    # PYTHON + JAVA
    # --------------------------------------------------------

    elif software_cloud_page == "Python + Java":
        python_java()

    # --------------------------------------------------------
    # AI PROGRAMMING TUTOR
    # --------------------------------------------------------

    elif software_cloud_page == "AI Programming Tutor":
        ai_tutor()

    # --------------------------------------------------------
    # LEETCODE
    # --------------------------------------------------------

    elif software_cloud_page == "LeetCode Practice":
        leetcode()

    # --------------------------------------------------------
    # DAILY PLAN
    # --------------------------------------------------------

    elif software_cloud_page == "Daily Plan":
        daily_plan()

    # --------------------------------------------------------
    # DAILY TRACKER
    # --------------------------------------------------------

    elif software_cloud_page == "Daily Tracker":
        daily_tracker()

    # --------------------------------------------------------
    # CLOUD ROADMAP
    # --------------------------------------------------------

    elif software_cloud_page == "Cloud Engineer Roadmap":
        cloud()

    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    elif software_cloud_page == "Projects":
        projects()

    # --------------------------------------------------------
    # ANALYTICS
    # --------------------------------------------------------

    elif software_cloud_page == "Analytics":
        analytics()

    # --------------------------------------------------------
    # PROMPT LIBRARY
    # --------------------------------------------------------

    elif software_cloud_page == "Prompt Library":
        prompt_library()

    # --------------------------------------------------------
    # PREFERENCES
    # --------------------------------------------------------

    elif software_cloud_page == "Preferences":
        preferences()