"""
main.py - FastAPI application.

Can be run directly from the project root with:

    uvicorn main:app --reload

Or as a package with:

    uvicorn devops_tracker.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator, Optional

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session


# ============================================================
# IMPORT COMPATIBILITY
# ============================================================
# Supports BOTH:
#
#   uvicorn main:app --reload
#
# and:
#
#   uvicorn devops_tracker.main:app --reload
# ============================================================

# ============================================================
# IMPORT COMPATIBILITY
# ============================================================
# Supports BOTH:
#
#   uvicorn main:app --reload
#
# and:
#
#   uvicorn devops_tracker.main:app --reload
# ============================================================

try:
    import schemas
    import services
    import models
    import feature_schemas
    import feature_services

    from database import SessionLocal, get_db, init_db

    from models import (
        DsaEntry,
        JobStatus,
        MistakeEntry,
        Phase,
        PlanSettings,
        Task,
        TaskView,
    )

except ImportError:
    import schemas
    import services
    import models
    import feature_schemas
    import feature_services

    from database import SessionLocal, get_db, init_db

    from models import (
        DsaEntry,
        JobStatus,
        MistakeEntry,
        Phase,
        PlanSettings,
        Task,
        TaskView,
    )
    from models import ( 
        DsaEntry,
        JobStatus,
        MistakeEntry,
        Phase,
        PlanSettings,
        Task,
        TaskView,
    )
except ImportError:
    import schemas
    import services
    from database import SessionLocal, get_db, init_db
    from models import (
        DsaEntry,
        JobStatus,
        MistakeEntry,
        Phase,
        PlanSettings,
        Task,
        TaskView,
    )


DB = Annotated[Session, Depends(get_db)]


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    Application startup.

    Creates database tables and seeds the database if necessary.
    """

    init_db()

    with SessionLocal() as db:
        services.ensure_seeded(db)
        feature_services.seed_feature_data(db)

    yield


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="DevOps Job-Readiness Tracker API",
    description=(
        "FastAPI + SQLite backend for the DevOps Job-Readiness Tracker."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


api = APIRouter(prefix="/api/v1")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# ============================================================
# DASHBOARD / PLAN
# ============================================================

@api.get(
    "/dashboard",
    response_model=schemas.DashboardRead,
    tags=["dashboard"],
)
def dashboard(db: DB) -> schemas.DashboardRead:
    return services.get_dashboard(db)


@api.get(
    "/plan/status",
    response_model=schemas.PlanStatus,
    tags=["dashboard"],
)
def plan_status(db: DB) -> schemas.PlanStatus:
    return services.compute_plan_status(db)


@api.get(
    "/settings",
    response_model=schemas.SettingsRead,
    tags=["dashboard"],
)
def read_settings(db: DB) -> PlanSettings:
    return services.get_settings(db)


@api.patch(
    "/settings",
    response_model=schemas.SettingsRead,
    tags=["dashboard"],
)
def patch_settings(
    body: schemas.SettingsUpdate,
    db: DB,
) -> PlanSettings:
    return services.update_settings(db, body)


@api.post(
    "/refresh",
    response_model=schemas.RefreshResult,
    tags=["dashboard"],
)
def refresh(db: DB) -> schemas.RefreshResult:
    return schemas.RefreshResult(
        last_refreshed=services.refresh_all(db)
    )


@api.get(
    "/lists",
    response_model=schemas.ListsRead,
    tags=["dashboard"],
)
def lists(db: DB) -> schemas.ListsRead:
    return services.get_lists(db)


@api.get(
    "/phases",
    response_model=list[schemas.PhaseRead],
    tags=["tasks"],
)
def phases(db: DB) -> list[Phase]:
    return services.list_phases(db)


# ============================================================
# PHASES & TASKS
# ============================================================

@api.get(
    "/tasks",
    response_model=list[schemas.TaskRead],
    tags=["tasks"],
)
def tasks(
    db: DB,
    phase_id: Annotated[
        Optional[int],
        Query(
            ge=0,
            le=7,
            description="Omit for 'All Phases'",
        ),
    ] = None,
    view: TaskView = TaskView.ALL,
) -> list[Task]:
    return services.list_tasks(db, phase_id, view)


@api.post(
    "/tasks",
    response_model=schemas.TaskRead,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
)
def add_task(
    body: schemas.TaskCreate,
    db: DB,
) -> Task:
    return services.create_task(db, body)


@api.get(
    "/tasks/{task_id}",
    response_model=schemas.TaskRead,
    tags=["tasks"],
)
def read_task(
    task_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Task:
    return services.get_task(db, task_id)


@api.patch(
    "/tasks/{task_id}",
    response_model=schemas.TaskStatusResult,
    tags=["tasks"],
)
def patch_task(
    task_id: Annotated[int, Path(ge=1)],
    body: schemas.TaskUpdate,
    db: DB,
) -> schemas.TaskStatusResult:
    return services.update_task(db, task_id, body)


@api.put(
    "/tasks/{task_id}/status",
    response_model=schemas.TaskStatusResult,
    tags=["tasks"],
)
def put_task_status(
    task_id: Annotated[int, Path(ge=1)],
    body: schemas.TaskStatusUpdate,
    db: DB,
) -> schemas.TaskStatusResult:
    return services.set_task_status(
        db,
        task_id,
        body.status,
    )


@api.post(
    "/tasks/{task_id}/cycle-status",
    response_model=schemas.TaskStatusResult,
    tags=["tasks"],
)
def cycle_status(
    task_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> schemas.TaskStatusResult:
    """Double-click on the tick column."""
    return services.cycle_task_status(db, task_id)


@api.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tasks"],
)
def remove_task(
    task_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Response:
    services.delete_task(db, task_id)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# ============================================================
# WEEKLY TRACKER
# ============================================================

@api.get(
    "/weekly",
    response_model=schemas.WeeklyReport,
    tags=["weekly"],
)
def weekly(db: DB) -> schemas.WeeklyReport:
    return services.get_weekly_report(db)


@api.patch(
    "/weekly/{week}",
    response_model=schemas.WeeklyRowRead,
    tags=["weekly"],
)
def patch_week(
    week: Annotated[int, Path(ge=1, le=18)],
    body: schemas.WeeklyUpdate,
    db: DB,
) -> schemas.WeeklyRowRead:
    return services.update_weekly(db, week, body)


@api.post(
    "/weekly/{week}/toggle-build",
    response_model=schemas.WeeklyRowRead,
    tags=["weekly"],
)
def toggle_build(
    week: Annotated[int, Path(ge=1, le=18)],
    db: DB,
) -> schemas.WeeklyRowRead:
    return services.toggle_build_shipped(db, week)


@api.post(
    "/weekly/{week}/toggle-checkpoint",
    response_model=schemas.WeeklyRowRead,
    tags=["weekly"],
)
def toggle_cp(
    week: Annotated[int, Path(ge=1, le=18)],
    db: DB,
) -> schemas.WeeklyRowRead:
    return services.toggle_checkpoint(db, week)


@api.get(
    "/daily",
    response_model=list[schemas.DailyRead],
    tags=["weekly"],
)
def daily(
    db: DB,
    week: Annotated[
        Optional[int],
        Query(ge=1, le=18),
    ] = None,
) -> list[schemas.DailyRead]:
    return services.list_daily(db, week)


@api.get(
    "/daily/today",
    response_model=schemas.DailyRead,
    tags=["weekly"],
)
def daily_today(db: DB) -> schemas.DailyRead:
    return services.get_today_plan(db)


@api.patch(
    "/daily/{daily_id}",
    response_model=schemas.DailyRead,
    tags=["weekly"],
)
def patch_daily(
    daily_id: Annotated[int, Path(ge=1)],
    body: schemas.DailyUpdate,
    db: DB,
) -> schemas.DailyRead:
    return services.update_daily(db, daily_id, body)


@api.post(
    "/daily/{daily_id}/blocks/{block}/cycle",
    response_model=schemas.DailyRead,
    tags=["weekly"],
)
def cycle_block(
    daily_id: Annotated[int, Path(ge=1)],
    block: Annotated[int, Path(ge=1, le=3)],
    db: DB,
) -> schemas.DailyRead:
    return services.cycle_daily_block(
        db,
        daily_id,
        block,
    )


# ============================================================
# SKILLS & LOGS
# ============================================================

@api.get(
    "/skills",
    response_model=schemas.SkillsReport,
    tags=["skills"],
)
def skills(db: DB) -> schemas.SkillsReport:
    return services.get_skills_report(db)


@api.patch(
    "/skills/{skill_id}",
    response_model=schemas.SkillRead,
    tags=["skills"],
)
def patch_skill(
    skill_id: Annotated[int, Path(ge=1)],
    body: schemas.SkillUpdate,
    db: DB,
) -> schemas.SkillRead:
    return services.update_skill(
        db,
        skill_id,
        body,
    )


@api.get(
    "/dsa",
    response_model=list[schemas.DsaRead],
    tags=["dsa"],
)
def dsa_list(
    db: DB,
    resolved: Optional[bool] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=500),
    ] = 200,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
) -> list[DsaEntry]:
    return services.list_dsa(
        db,
        resolved,
        limit,
        offset,
    )


@api.post(
    "/dsa",
    response_model=schemas.DsaRead,
    status_code=status.HTTP_201_CREATED,
    tags=["dsa"],
)
def dsa_create(
    body: schemas.DsaCreate,
    db: DB,
) -> DsaEntry:
    return services.create_dsa(db, body)


@api.patch(
    "/dsa/{entry_id}",
    response_model=schemas.DsaRead,
    tags=["dsa"],
)
def dsa_patch(
    entry_id: Annotated[int, Path(ge=1)],
    body: schemas.DsaUpdate,
    db: DB,
) -> DsaEntry:
    return services.update_dsa(
        db,
        entry_id,
        body,
    )


@api.post(
    "/dsa/{entry_id}/toggle-resolved",
    response_model=schemas.DsaRead,
    tags=["dsa"],
)
def dsa_toggle(
    entry_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> DsaEntry:
    return services.toggle_dsa_resolved(
        db,
        entry_id,
    )


@api.delete(
    "/dsa/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["dsa"],
)
def dsa_delete(
    entry_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Response:
    services.delete_dsa(db, entry_id)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# ============================================================
# JOBS
# ============================================================

@api.get(
    "/jobs",
    response_model=list[schemas.JobRead],
    tags=["jobs"],
)
def jobs_list(
    db: DB,
    job_status: Annotated[
        Optional[JobStatus],
        Query(alias="status"),
    ] = None,
    overdue_only: bool = False,
    limit: Annotated[
        int,
        Query(ge=1, le=500),
    ] = 200,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
) -> list[schemas.JobRead]:
    return services.list_jobs(
        db,
        job_status,
        overdue_only,
        limit,
        offset,
    )


@api.post(
    "/jobs",
    response_model=schemas.JobRead,
    status_code=status.HTTP_201_CREATED,
    tags=["jobs"],
)
def jobs_create(
    body: schemas.JobCreate,
    db: DB,
) -> schemas.JobRead:
    return services.create_job(db, body)


@api.patch(
    "/jobs/{job_id}",
    response_model=schemas.JobRead,
    tags=["jobs"],
)
def jobs_patch(
    job_id: Annotated[int, Path(ge=1)],
    body: schemas.JobUpdate,
    db: DB,
) -> schemas.JobRead:
    return services.update_job(
        db,
        job_id,
        body,
    )


@api.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["jobs"],
)
def jobs_delete(
    job_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Response:
    services.delete_job(db, job_id)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# ============================================================
# MISTAKES
# ============================================================

@api.get(
    "/mistakes",
    response_model=list[schemas.MistakeRead],
    tags=["mistakes"],
)
def mistakes_list(
    db: DB,
    topic: Optional[str] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=500),
    ] = 200,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
) -> list[MistakeEntry]:
    return services.list_mistakes(
        db,
        topic,
        limit,
        offset,
    )


@api.post(
    "/mistakes",
    response_model=schemas.MistakeRead,
    status_code=status.HTTP_201_CREATED,
    tags=["mistakes"],
)
def mistakes_create(
    body: schemas.MistakeCreate,
    db: DB,
) -> MistakeEntry:
    return services.create_mistake(
        db,
        body,
    )


@api.patch(
    "/mistakes/{mistake_id}",
    response_model=schemas.MistakeRead,
    tags=["mistakes"],
)
def mistakes_patch(
    mistake_id: Annotated[int, Path(ge=1)],
    body: schemas.MistakeUpdate,
    db: DB,
) -> MistakeEntry:
    return services.update_mistake(
        db,
        mistake_id,
        body,
    )


@api.delete(
    "/mistakes/{mistake_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["mistakes"],
)
def mistakes_delete(
    mistake_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Response:
    services.delete_mistake(
        db,
        mistake_id,
    )
    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# ============================================================
# SOFTWARE + CLOUD ENGINEER TRACKER
# ============================================================

# ------------------------------------------------------------
# HOME
# ------------------------------------------------------------

@api.get(
    "/home",
    response_model=feature_schemas.HomeSummaryRead,
    tags=["software-cloud"],
)
def feature_home(db: DB) -> dict:
    return feature_services.get_home_summary(db)


# ------------------------------------------------------------
# PYTHON + JAVA TOPIC PROGRESS
# ------------------------------------------------------------

@api.get(
    "/topic-progress",
    response_model=list[feature_schemas.TopicProgressRead],
    tags=["software-cloud"],
)
def topic_progress_list(
    db: DB,
    language: Optional[str] = None,
    topic_status: Annotated[
        Optional[str],
        Query(alias="status"),
    ] = None,
) -> list:
    return feature_services.list_topic_progress(
        db,
        language=language,
        status=topic_status,
    )


@api.post(
    "/topic-progress",
    response_model=feature_schemas.TopicProgressRead,
    status_code=status.HTTP_201_CREATED,
    tags=["software-cloud"],
)
def topic_progress_create(
    body: feature_schemas.TopicProgressCreate,
    db: DB,
):
    return feature_services.create_topic_progress(
        db,
        body,
    )


@api.patch(
    "/topic-progress/{item_id}",
    response_model=feature_schemas.TopicProgressRead,
    tags=["software-cloud"],
)
def topic_progress_patch(
    item_id: Annotated[int, Path(ge=1)],
    body: feature_schemas.TopicProgressUpdate,
    db: DB,
):
    item = feature_services.update_topic_progress(
        db,
        item_id,
        body,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic progress item not found.",
        )

    return item


# ------------------------------------------------------------
# LEETCODE
# ------------------------------------------------------------

@api.get(
    "/leetcode",
    response_model=list[feature_schemas.LeetCodeRead],
    tags=["software-cloud"],
)
def leetcode_list(
    db: DB,
    difficulty: Optional[str] = None,
    problem_status: Annotated[
        Optional[str],
        Query(alias="status"),
    ] = None,
    topic: Optional[str] = None,
    language: Optional[str] = None,
    revision_only: bool = False,
):
    return feature_services.list_leetcode(
        db,
        difficulty=difficulty,
        status=problem_status,
        topic=topic,
        language=language,
        revision_only=revision_only,
    )


@api.post(
    "/leetcode",
    response_model=feature_schemas.LeetCodeRead,
    status_code=status.HTTP_201_CREATED,
    tags=["software-cloud"],
)
def leetcode_create(
    body: feature_schemas.LeetCodeCreate,
    db: DB,
):
    return feature_services.create_leetcode(
        db,
        body,
    )


@api.patch(
    "/leetcode/{item_id}",
    response_model=feature_schemas.LeetCodeRead,
    tags=["software-cloud"],
)
def leetcode_patch(
    item_id: Annotated[int, Path(ge=1)],
    body: feature_schemas.LeetCodeUpdate,
    db: DB,
):
    item = feature_services.update_leetcode(
        db,
        item_id,
        body,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LeetCode problem not found.",
        )

    return item


@api.delete(
    "/leetcode/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["software-cloud"],
)
def leetcode_delete(
    item_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Response:
    deleted = feature_services.delete_leetcode(
        db,
        item_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LeetCode problem not found.",
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# ------------------------------------------------------------
# DAILY PLAN
# ------------------------------------------------------------

@api.get(
    "/daily-plan",
    response_model=list[feature_schemas.DailyTaskRead],
    tags=["software-cloud"],
)
def daily_plan_list(
    db: DB,
    completed: Optional[bool] = None,
):
    return feature_services.list_daily_tasks(
        db,
        completed=completed,
    )


@api.get(
    "/daily-plan/today",
    response_model=Optional[feature_schemas.DailyTaskRead],
    tags=["software-cloud"],
)
def daily_plan_today(db: DB):
    return feature_services.get_today_task(db)


@api.post(
    "/daily-plan",
    response_model=feature_schemas.DailyTaskRead,
    status_code=status.HTTP_201_CREATED,
    tags=["software-cloud"],
)
def daily_plan_create(
    body: feature_schemas.DailyTaskCreate,
    db: DB,
):
    return feature_services.create_daily_task(
        db,
        body,
    )


@api.patch(
    "/daily-plan/{item_id}",
    response_model=feature_schemas.DailyTaskRead,
    tags=["software-cloud"],
)
def daily_plan_patch(
    item_id: Annotated[int, Path(ge=1)],
    body: feature_schemas.DailyTaskUpdate,
    db: DB,
):
    item = feature_services.update_daily_task(
        db,
        item_id,
        body,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily task not found.",
        )

    return item


# ------------------------------------------------------------
# STREAK
# ------------------------------------------------------------

@api.get(
    "/streak",
    response_model=feature_schemas.StreakRead,
    tags=["software-cloud"],
)
def streak(db: DB):
    return feature_services.get_streak(db)


# ------------------------------------------------------------
# PROJECTS
# ------------------------------------------------------------

@api.get(
    "/projects",
    response_model=list[feature_schemas.ProjectRead],
    tags=["software-cloud"],
)
def projects_list(db: DB):
    return feature_services.list_projects(db)


@api.post(
    "/projects",
    response_model=feature_schemas.ProjectRead,
    status_code=status.HTTP_201_CREATED,
    tags=["software-cloud"],
)
def projects_create(
    body: feature_schemas.ProjectCreate,
    db: DB,
):
    return feature_services.create_project(
        db,
        body,
    )


@api.patch(
    "/projects/{item_id}",
    response_model=feature_schemas.ProjectRead,
    tags=["software-cloud"],
)
def projects_patch(
    item_id: Annotated[int, Path(ge=1)],
    body: feature_schemas.ProjectUpdate,
    db: DB,
):
    item = feature_services.update_project(
        db,
        item_id,
        body,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return item


@api.delete(
    "/projects/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["software-cloud"],
)
def projects_delete(
    item_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Response:
    deleted = feature_services.delete_project(
        db,
        item_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# ------------------------------------------------------------
# PROMPT LIBRARY
# ------------------------------------------------------------

@api.get(
    "/prompts",
    response_model=list[feature_schemas.PromptRead],
    tags=["software-cloud"],
)
def prompts_list(
    db: DB,
    category: Optional[str] = None,
):
    return feature_services.list_prompts(
        db,
        category=category,
    )


@api.post(
    "/prompts",
    response_model=feature_schemas.PromptRead,
    status_code=status.HTTP_201_CREATED,
    tags=["software-cloud"],
)
def prompts_create(
    body: feature_schemas.PromptCreate,
    db: DB,
):
    return feature_services.create_prompt(
        db,
        body,
    )


@api.delete(
    "/prompts/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["software-cloud"],
)
def prompts_delete(
    item_id: Annotated[int, Path(ge=1)],
    db: DB,
) -> Response:
    deleted = feature_services.delete_prompt(
        db,
        item_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found.",
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


# ------------------------------------------------------------
# USER PREFERENCES
# ------------------------------------------------------------

@api.get(
    "/preferences",
    response_model=feature_schemas.PreferenceRead,
    tags=["software-cloud"],
)
def preferences_read(db: DB):
    return feature_services.get_preferences(db)


@api.put(
    "/preferences",
    response_model=feature_schemas.PreferenceRead,
    tags=["software-cloud"],
)
def preferences_update(
    body: feature_schemas.PreferenceUpdate,
    db: DB,
):
    try:
        return feature_services.update_preferences(
            db,
            body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ------------------------------------------------------------
# CLOUD ENGINEER ROADMAP
# ------------------------------------------------------------

@api.get(
    "/cloud-roadmap",
    response_model=list[feature_schemas.CloudRoadmapRead],
    tags=["software-cloud"],
)
def cloud_roadmap_list(db: DB):
    return feature_services.list_cloud_roadmap(db)


@api.patch(
    "/cloud-roadmap/{stage_id}",
    response_model=feature_schemas.CloudRoadmapRead,
    tags=["software-cloud"],
)
def cloud_roadmap_patch(
    stage_id: Annotated[int, Path(ge=1)],
    body: feature_schemas.CloudRoadmapUpdate,
    db: DB,
):
    item = feature_services.update_cloud_roadmap(
        db,
        stage_id,
        body,
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cloud roadmap stage not found.",
        )

    return item


# ------------------------------------------------------------
# ANALYTICS
# ------------------------------------------------------------

@api.get(
    "/analytics",
    response_model=feature_schemas.AnalyticsRead,
    tags=["software-cloud"],
)
def analytics(db: DB):
    return feature_services.get_analytics(db)

@api.post(
    "/admin/rebuild",
    response_model=schemas.RebuildResult,
    tags=["admin"],
)
def rebuild(
    db: DB,
    confirm: bool = False,
) -> schemas.RebuildResult:

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This DELETES all data and rebuilds the plan. "
                "Re-send with ?confirm=true to proceed."
            ),
        )

    return services.seed_database(
        db,
        reset=True,
    )


# ============================================================
# REGISTER API ROUTES
# ============================================================

app.include_router(api)