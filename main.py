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

try:
    import schemas
    import services
    import models
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
# ADMIN
# ============================================================

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