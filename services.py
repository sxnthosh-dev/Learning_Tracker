"""
services.py - business logic and all database transactions.

Route handlers in main.py never touch the Session directly; they call these functions.
Errors are raised as HTTPException (404 missing record, 400 invalid input, 409 conflict,
500 database failure) so every route gets consistent error responses.

VBA -> Python map (procedures that carry logic)
-----------------------------------------------
  BuildDevOpsTracker / CreateSheets / BuildLists / Build*Sheet   -> seed_database()
  DefineNames (StartDate, EndDate, CurWeek, ActivePhase,
               TasksTotal, TasksDone, PctDone)                   -> compute_plan_status(), get_dashboard()
  ApplyTaskFilter / ShowAllTasks / ShowPendingTasks              -> list_tasks(phase_id, view)
  HandleSheetChange -> OnTasksChanged                            -> _apply_status(), set_task_status(), update_task()
  CheckPhaseComplete                                             -> _phase_complete()
  CycleTaskStatus (double-click)                                 -> cycle_task_status()
  HandleSheetChange -> OnLogsChanged                             -> create_dsa/create_job/create_mistake date stamping
  HandleDoubleClick (daily blocks / build shipped / checkpoint
                     / DSA re-solved)                            -> cycle_daily_block(), toggle_build_shipped(),
                                                                    toggle_checkpoint(), toggle_dsa_resolved()
  ToggleTick                                                     -> the toggle_* functions
  GoToCurrentWeek                                                -> get_today_plan()
  StampRefresh / RefreshAll / OnWorkbookOpen                     -> stamp_refresh(), refresh_all(), ensure_seeded()
  Weekly Summary / Daily Planner / Skill Matrix / Job / Dashboard
  worksheet FORMULAS                                             -> get_weekly_report(), list_daily(),
                                                                    get_skills_report(), _job_read(), get_dashboard()
  Navigation macros (GoToDashboard, JumpSkills ...)              -> not applicable to an API (UI-only)
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import schemas
from . import seed_data as sd
from .models import (
    TICK_DONE, TICK_OPEN, BlockStatus, DailyPlan, Difficulty, DsaEntry, DsaPattern,
    JobApplication, JobStatus, MistakeEntry, Phase, PlanSettings, Skill, Task,
    TaskCategory, TaskStatus, TaskView, WeeklySummary,
)

WEEKS_TOTAL = sd.WEEKS_TOTAL
BLOCKS_PER_WEEK = sd.BLOCKS_PER_WEEK
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
BAR_FULL = "\u2588"      # VBA BarFull  (ChrW 9608)
BAR_EMPTY = "\u2591"     # VBA BarEmpty (ChrW 9617)
BAR_WIDTH = 34
FOLLOW_UP_DAYS = 7
# Dashboard snapshot targets (BuildDashboard metricT)
TARGET_DSA_SOLVED = 80
TARGET_DSA_RESOLVED = 80
TARGET_JOB_APPLICATIONS = 65


# =============================================================================
# Small helpers
# =============================================================================
def _today() -> date:
    return date.today()


def _not_found(what: str, key: object) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{what} '{key}' not found")


def _bad_request(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail=msg)


def _commit(db: Session) -> None:
    """Commit or roll back, translating DB failures into HTTP errors."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Operation violates a database constraint") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error") from exc


def _apply_patch(obj: Any, data: dict[str, Any], non_nullable: frozenset[str] = frozenset()) -> None:
    for key, value in data.items():
        if value is None and key in non_nullable:
            raise _bad_request(f"'{key}' cannot be null")
        setattr(obj, key, value)


def _bar(fraction: float) -> str:
    filled = max(0, min(BAR_WIDTH, int(fraction * BAR_WIDTH + 0.5)))
    return BAR_FULL * filled + BAR_EMPTY * (BAR_WIDTH - filled)


def _fmt(d: date, *, weekday: bool = False, year: bool = False) -> str:
    """Excel 'd mmm' / 'ddd d mmm yyyy' (locale-independent)."""
    out = f"{d.day} {d.strftime('%b')}"
    if weekday:
        out = f"{DAY_NAMES[d.weekday()]} {out}"
    if year:
        out = f"{out} {d.year}"
    return out


# =============================================================================
# Plan settings and the named formulas (StartDate / EndDate / CurWeek / ActivePhase)
# =============================================================================
def get_settings(db: Session) -> PlanSettings:
    row = db.get(PlanSettings, 1)
    if row is None:
        row = PlanSettings(id=1)
        db.add(row)
        _commit(db)
    return row


def update_settings(db: Session, data: schemas.SettingsUpdate) -> PlanSettings:
    row = get_settings(db)
    _apply_patch(
        row, data.model_dump(exclude_unset=True),
        non_nullable=frozenset({"owner_name", "target_role", "start_date"}),
    )
    _commit(db)
    return row


def stamp_refresh(db: Session) -> datetime:
    """VBA StampRefresh: set 'last refreshed' (caller commits)."""
    now = datetime.now()
    get_settings(db).last_refreshed = now
    return now


def refresh_all(db: Session) -> datetime:
    """VBA RefreshAll. Every metric is computed on read, so only the timestamp changes."""
    now = stamp_refresh(db)
    _commit(db)
    return now


def phase_window(phase: Phase, start: date) -> tuple[date, date]:
    """Start/end dates of a phase (BuildDashboard phase-table formulas)."""
    end = start + timedelta(days=WEEKS_TOTAL * 7 - 1)
    if phase.id == 0:                       # Setup
        return start - timedelta(days=2), start - timedelta(days=1)
    if phase.id == 7:                       # Tracks
        return start, end
    return (start + timedelta(days=(phase.week_start - 1) * 7),
            start + timedelta(days=phase.week_end * 7 - 1))


def compute_plan_status(db: Session, today: Optional[date] = None) -> schemas.PlanStatus:
    today = today or _today()
    start = get_settings(db).start_date
    end = start + timedelta(days=WEEKS_TOTAL * 7 - 1)
    cur_week = 0 if today < start else min(WEEKS_TOTAL, (today - start).days // 7 + 1)

    phases = [p for p in db.scalars(select(Phase).order_by(Phase.id)) if 1 <= p.id <= 6]
    active = "Pre-start"
    if phases:
        windows = [(p, *phase_window(p, start)) for p in phases]
        if today < windows[0][1]:
            active = "Pre-start"
        elif today > windows[-1][2]:
            active = "Plan ended"
        else:                                # MATCH(TODAY(), start-dates, 1)
            active = [p for p, s, _e in windows if s <= today][-1].label
    return schemas.PlanStatus(
        start_date=start, end_date=end, weeks_total=WEEKS_TOTAL,
        current_week=cur_week, active_phase=active, today=today,
    )


def list_phases(db: Session) -> list[Phase]:
    return list(db.scalars(select(Phase).order_by(Phase.id)))


# =============================================================================
# Phases & Tasks
# =============================================================================
def _require_phase(db: Session, phase_id: int) -> Phase:
    phase = db.get(Phase, phase_id)
    if phase is None:
        raise _not_found("Phase", phase_id)
    return phase


def _get_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise _not_found("Task", task_id)
    return task


def list_tasks(db: Session, phase_id: Optional[int] = None, view: TaskView = TaskView.ALL) -> list[Task]:
    """ApplyTaskFilter / ShowAllTasks / ShowPendingTasks."""
    stmt = select(Task).order_by(Task.id)
    if phase_id is not None:
        _require_phase(db, phase_id)
        stmt = stmt.where(Task.phase_id == phase_id)
    if view == TaskView.PENDING:
        stmt = stmt.where(Task.status != TaskStatus.COMPLETED)
    elif view == TaskView.IN_PROGRESS:
        stmt = stmt.where(Task.status == TaskStatus.IN_PROGRESS)
    elif view == TaskView.COMPLETED:
        stmt = stmt.where(Task.status == TaskStatus.COMPLETED)
    return list(db.scalars(stmt))


def get_task(db: Session, task_id: int) -> Task:
    return _get_task(db, task_id)


def create_task(db: Session, data: schemas.TaskCreate, today: Optional[date] = None) -> Task:
    """Replaces typing into one of the ~45 spare rows."""
    _require_phase(db, data.phase_id)
    task = Task(
        phase_id=data.phase_id, category=data.category, item=data.item, notes=data.notes,
        status=TaskStatus.NOT_STARTED,
    )
    _apply_status(task, data.status, today or _today())
    db.add(task)
    _commit(db)
    return task


def delete_task(db: Session, task_id: int) -> None:
    db.delete(_get_task(db, task_id))
    _commit(db)


def _apply_status(task: Task, new_status: TaskStatus, today: date) -> None:
    """OnTasksChanged: stamp 'Completed on' once, clear it for any other status."""
    task.status = new_status
    if new_status == TaskStatus.COMPLETED:
        if task.done_on is None:
            task.done_on = today
    else:
        task.done_on = None


def _phase_complete(db: Session, phase_id: int) -> bool:
    """CheckPhaseComplete: is every item in this phase group Completed?"""
    total = db.scalar(select(func.count()).select_from(Task).where(Task.phase_id == phase_id)) or 0
    done = db.scalar(
        select(func.count()).select_from(Task)
        .where(Task.phase_id == phase_id, Task.status == TaskStatus.COMPLETED)
    ) or 0
    return total > 0 and total == done


def _status_result(db: Session, task: Task, completed_now: bool) -> schemas.TaskStatusResult:
    complete = completed_now and _phase_complete(db, task.phase_id)
    msg = (
        f"Every item in this group is complete: {task.phase.label}. "
        "Update the Learning Log and the Skill Matrix, then move on."
    ) if complete else None
    return schemas.TaskStatusResult(
        task=schemas.TaskRead.model_validate(task), phase_complete=complete, message=msg,
    )


def set_task_status(db: Session, task_id: int, new_status: TaskStatus,
                    today: Optional[date] = None) -> schemas.TaskStatusResult:
    task = _get_task(db, task_id)
    _apply_status(task, new_status, today or _today())
    stamp_refresh(db)
    _commit(db)
    return _status_result(db, task, new_status == TaskStatus.COMPLETED)


def cycle_task_status(db: Session, task_id: int, today: Optional[date] = None) -> schemas.TaskStatusResult:
    """VBA CycleTaskStatus: Not Started > In Progress > Completed > Not Started."""
    task = _get_task(db, task_id)
    nxt = {
        TaskStatus.NOT_STARTED: TaskStatus.IN_PROGRESS,
        TaskStatus.IN_PROGRESS: TaskStatus.COMPLETED,
        TaskStatus.COMPLETED: TaskStatus.NOT_STARTED,
    }[task.status]
    return set_task_status(db, task_id, nxt, today)


def update_task(db: Session, task_id: int, data: schemas.TaskUpdate,
                today: Optional[date] = None) -> schemas.TaskStatusResult:
    task = _get_task(db, task_id)
    changes = data.model_dump(exclude_unset=True)
    new_status = changes.pop("status", None)
    if "status" in data.model_fields_set and new_status is None:
        raise _bad_request("'status' cannot be null")
    if changes.get("phase_id") is not None:
        _require_phase(db, changes["phase_id"])
    _apply_patch(task, changes, non_nullable=frozenset({"phase_id", "category", "item"}))
    if new_status is not None:
        _apply_status(task, new_status, today or _today())
        stamp_refresh(db)
    _commit(db)
    db.refresh(task)
    return _status_result(db, task, new_status == TaskStatus.COMPLETED)


# =============================================================================
# Weekly Tracker - A. Weekly Summary
# =============================================================================
def _get_week(db: Session, week: int) -> WeeklySummary:
    if not 1 <= week <= WEEKS_TOTAL:
        raise _bad_request(f"week must be between 1 and {WEEKS_TOTAL}")
    row = db.get(WeeklySummary, week)
    if row is None:
        raise _not_found("Week", week)
    return row


def _blocks_done_by_week(dailies: list[DailyPlan]) -> dict[int, int]:
    done: Counter[int] = Counter()
    for d in dailies:
        done[d.week] += sum(1 for b in (d.block1, d.block2, d.block3) if b == BlockStatus.DONE)
    return dict(done)


def get_weekly_report(db: Session, today: Optional[date] = None) -> schemas.WeeklyReport:
    today = today or _today()
    start = get_settings(db).start_date
    cur_week = compute_plan_status(db, today).current_week
    weeks = list(db.scalars(select(WeeklySummary).order_by(WeeklySummary.week)))
    dailies = list(db.scalars(select(DailyPlan)))

    blocks_done = _blocks_done_by_week(dailies)
    actual: dict[int, float] = {}
    for d in dailies:                        # SUMIFS(Day_Actual, Day_Wk, wk) only when some Actual > 0
        if d.actual_hours is not None and d.actual_hours > 0:
            actual[d.week] = actual.get(d.week, 0.0) + d.actual_hours

    dsa_by_week: Counter[int] = Counter()    # COUNTIFS(DSA_Date, >=week_of, <=week_of+6)
    for solved_on in db.scalars(select(DsaEntry.solved_on)):
        if solved_on >= start:
            idx = (solved_on - start).days // 7 + 1
            if idx <= WEEKS_TOTAL:
                dsa_by_week[idx] += 1

    rows: list[schemas.WeeklyRowRead] = []
    for w in weeks:
        week_of = start + timedelta(days=(w.week - 1) * 7)
        rows.append(schemas.WeeklyRowRead(
            week=w.week, week_of=week_of, phase_code=w.phase_code, focus=w.focus,
            planned_hours=w.planned_hours,
            actual_hours=actual.get(w.week),
            dsa_solved=None if week_of > today else dsa_by_week.get(w.week, 0),
            blocks_done_pct=blocks_done.get(w.week, 0) / BLOCKS_PER_WEEK,
            build_shipped=w.build_shipped, confidence=w.confidence,
            checkpoint_phase=w.checkpoint_phase, checkpoint_done=w.checkpoint_done,
            notes=w.notes, is_current_week=(w.week == cur_week),
        ))

    confs = [r.confidence for r in rows if r.confidence is not None]
    totals = schemas.WeeklyTotals(
        planned_hours=sum(r.planned_hours for r in rows),
        actual_hours=sum(r.actual_hours for r in rows if r.actual_hours is not None),
        dsa_solved=sum(r.dsa_solved for r in rows if r.dsa_solved is not None),
        avg_blocks_done_pct=(sum(r.blocks_done_pct for r in rows) / len(rows)) if rows else 0.0,
        builds_shipped=sum(1 for r in rows if r.build_shipped),
        avg_confidence=(sum(confs) / len(confs)) if confs else None,
    )
    return schemas.WeeklyReport(rows=rows, totals=totals)


def _weekly_row(db: Session, week: int) -> schemas.WeeklyRowRead:
    return next(r for r in get_weekly_report(db).rows if r.week == week)


def update_weekly(db: Session, week: int, data: schemas.WeeklyUpdate) -> schemas.WeeklyRowRead:
    row = _get_week(db, week)
    changes = data.model_dump(exclude_unset=True)
    if "checkpoint_done" in changes and row.checkpoint_phase is None:
        raise _bad_request(f"Week {week} is not a checkpoint week")
    _apply_patch(row, changes, non_nullable=frozenset({"planned_hours", "build_shipped", "checkpoint_done"}))
    _commit(db)
    return _weekly_row(db, week)


def toggle_build_shipped(db: Session, week: int) -> schemas.WeeklyRowRead:
    """Double-click on 'Build shipped?'."""
    row = _get_week(db, week)
    row.build_shipped = not row.build_shipped
    _commit(db)
    return _weekly_row(db, week)


def toggle_checkpoint(db: Session, week: int) -> schemas.WeeklyRowRead:
    """Double-click on 'Checkpoint' (swaps the leading box). Only checkpoint weeks have one."""
    row = _get_week(db, week)
    if row.checkpoint_phase is None:
        raise _bad_request(f"Week {week} is not a checkpoint week")
    row.checkpoint_done = not row.checkpoint_done
    _commit(db)
    return _weekly_row(db, week)


# =============================================================================
# Weekly Tracker - B. Daily Planner
# =============================================================================
def _get_daily(db: Session, daily_id: int) -> DailyPlan:
    row = db.get(DailyPlan, daily_id)
    if row is None:
        raise _not_found("Daily plan row", daily_id)
    return row


def _daily_read(d: DailyPlan, start: date, today: date) -> schemas.DailyRead:
    day_date = start + timedelta(days=(d.week - 1) * 7 + d.day_index)
    blocks = (d.block1, d.block2, d.block3)
    applicable = 3 - sum(1 for b in blocks if b == BlockStatus.NOT_APPLICABLE)
    done = sum(1 for b in blocks if b == BlockStatus.DONE)
    pct = done / applicable if applicable > 0 else 0.0       # IFERROR(..., 0)
    return schemas.DailyRead(
        id=d.id, week=d.week, day_index=d.day_index, day=DAY_NAMES[d.day_index], day_date=day_date,
        plan=d.plan, planned_hours=d.planned_hours, actual_hours=d.actual_hours,
        block1=d.block1, block2=d.block2, block3=d.block3,
        day_pct=pct, day_done=pct >= 1, notes=d.notes, is_today=(day_date == today),
    )


def list_daily(db: Session, week: Optional[int] = None, today: Optional[date] = None) -> list[schemas.DailyRead]:
    today = today or _today()
    start = get_settings(db).start_date
    stmt = select(DailyPlan).order_by(DailyPlan.week, DailyPlan.day_index)
    if week is not None:
        if not 1 <= week <= WEEKS_TOTAL:
            raise _bad_request(f"week must be between 1 and {WEEKS_TOTAL}")
        stmt = stmt.where(DailyPlan.week == week)
    return [_daily_read(d, start, today) for d in db.scalars(stmt)]


def get_today_plan(db: Session, today: Optional[date] = None) -> schemas.DailyRead:
    """VBA GoToCurrentWeek: today's row, clamped to the plan window."""
    today = today or _today()
    start = get_settings(db).start_date
    idx = max(0, min(WEEKS_TOTAL * 7 - 1, (today - start).days))
    row = db.scalar(select(DailyPlan).where(
        DailyPlan.week == idx // 7 + 1, DailyPlan.day_index == idx % 7))
    if row is None:
        raise _not_found("Daily plan for day index", idx)
    return _daily_read(row, start, today)


def update_daily(db: Session, daily_id: int, data: schemas.DailyUpdate) -> schemas.DailyRead:
    row = _get_daily(db, daily_id)
    changes = data.model_dump(exclude_unset=True)
    for key in ("block1", "block2", "block3"):
        if key in changes:
            if changes[key] is None:
                raise _bad_request(f"'{key}' cannot be null")
            current: BlockStatus = getattr(row, key)
            if current == BlockStatus.NOT_APPLICABLE or changes[key] == BlockStatus.NOT_APPLICABLE:
                raise _bad_request(f"{key} is not applicable on {DAY_NAMES[row.day_index]} and cannot be changed")
    _apply_patch(row, changes)
    _commit(db)
    return _daily_read(row, get_settings(db).start_date, _today())


def cycle_daily_block(db: Session, daily_id: int, block: int) -> schemas.DailyRead:
    """Double-click on a block cell: Pending > Done > Skipped > Pending ('-' does nothing)."""
    if block not in (1, 2, 3):
        raise _bad_request("block must be 1, 2 or 3")
    row = _get_daily(db, daily_id)
    attr = f"block{block}"
    current: BlockStatus = getattr(row, attr)
    if current == BlockStatus.NOT_APPLICABLE:
        raise _bad_request(f"Block {block} is not applicable on {DAY_NAMES[row.day_index]}")
    nxt = {
        BlockStatus.PENDING: BlockStatus.DONE,
        BlockStatus.DONE: BlockStatus.SKIPPED,
        BlockStatus.SKIPPED: BlockStatus.PENDING,
    }[current]
    setattr(row, attr, nxt)
    _commit(db)
    return _daily_read(row, get_settings(db).start_date, _today())


# =============================================================================
# Skills & Logs - 1. Skill Matrix
# =============================================================================
def _latest_rating(s: Skill) -> Optional[int]:
    """Sheet formula LOOKUP(2, 1/(E:G<>""), E:G): the right-most rating that is filled in."""
    rated = [v for v in (s.wk1, s.wk9, s.wk18) if v is not None]
    return rated[-1] if rated else None


def _skill_gap(latest: Optional[int]) -> str:
    if latest is None:
        return "Not rated yet"
    if latest >= 3:
        return "Level 3 reached"
    if latest == 0:
        return "Never used: need +3"
    return f"Need +{3 - latest} to reach level 3"


def _skill_read(s: Skill) -> schemas.SkillRead:
    latest = _latest_rating(s)
    return schemas.SkillRead(
        id=s.id, skill_type=s.skill_type, name=s.name, evidence=s.evidence,
        wk1=s.wk1, wk9=s.wk9, wk18=s.wk18, latest=latest, gap=_skill_gap(latest),
    )


def get_skills_report(db: Session) -> schemas.SkillsReport:
    skills = [_skill_read(s) for s in db.scalars(select(Skill).order_by(Skill.id))]
    must = [s for s in skills if s.skill_type == "Must-have"]
    at3 = sum(1 for s in must if s.latest == 3)
    rated = [s.latest for s in skills if s.latest is not None]
    avg = (sum(rated) / len(rated)) if rated else 0.0
    return schemas.SkillsReport(
        skills=skills,
        summary=f"Must-haves at level 3: {at3} of {len(must)}     |     Average latest rating: {avg:.1f} / 3",
        must_haves_at_level_3=at3, must_haves_total=len(must), average_latest_rating=avg,
    )


def update_skill(db: Session, skill_id: int, data: schemas.SkillUpdate) -> schemas.SkillRead:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise _not_found("Skill", skill_id)
    _apply_patch(skill, data.model_dump(exclude_unset=True))
    _commit(db)
    return _skill_read(skill)


# =============================================================================
# Skills & Logs - 2. DSA Log
# =============================================================================
def _get_dsa(db: Session, entry_id: int) -> DsaEntry:
    row = db.get(DsaEntry, entry_id)
    if row is None:
        raise _not_found("DSA entry", entry_id)
    return row


def list_dsa(db: Session, resolved: Optional[bool] = None, limit: int = 200, offset: int = 0) -> list[DsaEntry]:
    stmt = select(DsaEntry).order_by(DsaEntry.solved_on, DsaEntry.id)
    if resolved is not None:
        stmt = stmt.where(DsaEntry.resolved == resolved)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def create_dsa(db: Session, data: schemas.DsaCreate, today: Optional[date] = None) -> DsaEntry:
    """OnLogsChanged: the date is stamped with today when a problem is typed without one."""
    entry = DsaEntry(
        solved_on=data.solved_on or today or _today(), problem=data.problem, pattern=data.pattern,
        difficulty=data.difficulty, time_min=data.time_min, help_level=data.help_level,
        resolved=data.resolved, key_idea=data.key_idea,
    )
    db.add(entry)
    _commit(db)
    return entry


def update_dsa(db: Session, entry_id: int, data: schemas.DsaUpdate) -> DsaEntry:
    entry = _get_dsa(db, entry_id)
    _apply_patch(entry, data.model_dump(exclude_unset=True),
                 non_nullable=frozenset({"problem", "solved_on", "resolved"}))
    _commit(db)
    return entry


def toggle_dsa_resolved(db: Session, entry_id: int) -> DsaEntry:
    """Double-click on 'Re-solved'."""
    entry = _get_dsa(db, entry_id)
    entry.resolved = not entry.resolved
    _commit(db)
    return entry


def delete_dsa(db: Session, entry_id: int) -> None:
    db.delete(_get_dsa(db, entry_id))
    _commit(db)


# =============================================================================
# Skills & Logs - 3. Job Application Tracker
# =============================================================================
def _get_job(db: Session, job_id: int) -> JobApplication:
    row = db.get(JobApplication, job_id)
    if row is None:
        raise _not_found("Job application", job_id)
    return row


def _stamp_job_defaults(job: JobApplication, today: date) -> None:
    """OnLogsChanged: date = today, status = 'Applied', follow-up = date + 7 days (only if empty)."""
    if job.applied_on is None:
        job.applied_on = today
    if job.status is None:
        job.status = JobStatus.APPLIED
    if job.follow_up_on is None:
        job.follow_up_on = job.applied_on + timedelta(days=FOLLOW_UP_DAYS)


def _job_read(job: JobApplication, today: date) -> schemas.JobRead:
    closed = job.status in (JobStatus.OFFER, JobStatus.REJECTED)
    days_waiting = None if (job.applied_on is None or closed) else (today - job.applied_on).days
    overdue = (
        job.follow_up_on is not None and job.follow_up_on < today
        and job.status in (JobStatus.APPLIED, JobStatus.NO_REPLY)
    )
    return schemas.JobRead(
        id=job.id, applied_on=job.applied_on, company=job.company, role=job.role, source=job.source,
        status=job.status, follow_up_on=job.follow_up_on, days_waiting=days_waiting,
        follow_up_overdue=overdue, learned=job.learned,
    )


def list_jobs(db: Session, job_status: Optional[JobStatus] = None, overdue_only: bool = False,
              limit: int = 200, offset: int = 0, today: Optional[date] = None) -> list[schemas.JobRead]:
    today = today or _today()
    stmt = select(JobApplication).order_by(JobApplication.applied_on, JobApplication.id)
    if job_status is not None:
        stmt = stmt.where(JobApplication.status == job_status)
    reads = [_job_read(j, today) for j in db.scalars(stmt.limit(limit).offset(offset))]
    return [j for j in reads if j.follow_up_overdue] if overdue_only else reads


def create_job(db: Session, data: schemas.JobCreate, today: Optional[date] = None) -> schemas.JobRead:
    today = today or _today()
    job = JobApplication(
        applied_on=data.applied_on, company=data.company, role=data.role, source=data.source,
        status=data.status, follow_up_on=data.follow_up_on, learned=data.learned,
    )
    _stamp_job_defaults(job, today)
    db.add(job)
    _commit(db)
    return _job_read(job, today)


def update_job(db: Session, job_id: int, data: schemas.JobUpdate, today: Optional[date] = None) -> schemas.JobRead:
    today = today or _today()
    job = _get_job(db, job_id)
    changes = data.model_dump(exclude_unset=True)
    _apply_patch(job, changes, non_nullable=frozenset({"company"}))
    if "company" in changes:                 # the VBA event only fires when the Company cell changes
        _stamp_job_defaults(job, today)
    _commit(db)
    return _job_read(job, today)


def delete_job(db: Session, job_id: int) -> None:
    db.delete(_get_job(db, job_id))
    _commit(db)


# =============================================================================
# Skills & Logs - 4. Mistake Log
# =============================================================================
def _get_mistake(db: Session, mistake_id: int) -> MistakeEntry:
    row = db.get(MistakeEntry, mistake_id)
    if row is None:
        raise _not_found("Mistake entry", mistake_id)
    return row


def list_mistakes(db: Session, topic: Optional[str] = None, limit: int = 200, offset: int = 0) -> list[MistakeEntry]:
    stmt = select(MistakeEntry).order_by(MistakeEntry.logged_on, MistakeEntry.id)
    if topic:
        stmt = stmt.where(MistakeEntry.topic == topic)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def create_mistake(db: Session, data: schemas.MistakeCreate, today: Optional[date] = None) -> MistakeEntry:
    entry = MistakeEntry(
        logged_on=data.logged_on or today or _today(), what_went_wrong=data.what_went_wrong,
        correction=data.correction, topic=data.topic,
    )
    db.add(entry)
    _commit(db)
    return entry


def update_mistake(db: Session, mistake_id: int, data: schemas.MistakeUpdate) -> MistakeEntry:
    entry = _get_mistake(db, mistake_id)
    _apply_patch(entry, data.model_dump(exclude_unset=True), non_nullable=frozenset({"what_went_wrong"}))
    _commit(db)
    return entry


def delete_mistake(db: Session, mistake_id: int) -> None:
    db.delete(_get_mistake(db, mistake_id))
    _commit(db)


# =============================================================================
# Dashboard (every card / table on the sheet was a formula)
# =============================================================================
def get_dashboard(db: Session, today: Optional[date] = None) -> schemas.DashboardRead:
    today = today or _today()
    settings = get_settings(db)
    plan = compute_plan_status(db, today)
    phases = list_phases(db)

    # One grouped query replaces the COUNTIF/COUNTIFS family over TaskPhase/TaskCat/TaskStatus.
    counts: Counter[tuple[int, TaskCategory, TaskStatus]] = Counter()
    for pid, cat, st, n in db.execute(
        select(Task.phase_id, Task.category, Task.status, func.count()).group_by(Task.phase_id, Task.category, Task.status)
    ):
        counts[(pid, cat, st)] = n

    def tally(pid: Optional[int] = None, cat: Optional[TaskCategory] = None,
              st: Optional[TaskStatus] = None) -> int:
        return sum(n for (p, c, s), n in counts.items()
                   if (pid is None or p == pid) and (cat is None or c == cat) and (st is None or s == st))

    tasks_total = tally()
    tasks_done = tally(st=TaskStatus.COMPLETED)
    tasks_wip = tally(st=TaskStatus.IN_PROGRESS)
    pct_done = tasks_done / tasks_total if tasks_total else 0.0

    weekly = get_weekly_report(db, today)
    this_week_pct = 0.0
    if plan.current_week > 0:
        this_week_pct = next(r.blocks_done_pct for r in weekly.rows if r.week == plan.current_week)

    # --- cards ---------------------------------------------------------------
    overall = schemas.OverallCard(pct_done=pct_done, bar=_bar(pct_done),
                                  caption=f"{tasks_done} of {tasks_total} items completed")

    if plan.active_phase in ("Pre-start", "Plan ended"):
        ap_title = plan.active_phase
        ap_sub = ("Finish the Setup checklist first" if plan.active_phase == "Pre-start"
                  else "Keep going while you interview")
    else:
        ap_title = f"Phase {plan.active_phase[1]}"          # MID(ActivePhase, 2, 1)
        ap_sub = plan.active_phase[5:65]                     # MID(ActivePhase, 6, 60)
    if plan.current_week == 0:
        ap_cap = f"Week 1 starts {_fmt(plan.start_date, weekday=True)}"
    elif today > plan.end_date:
        ap_cap = "Plan window complete"
    else:
        wk_start = plan.start_date + timedelta(days=(plan.current_week - 1) * 7)
        ap_cap = (f"Week {plan.current_week} of {WEEKS_TOTAL}   |   "
                  f"{_fmt(wk_start)} - {_fmt(wk_start + timedelta(days=6))}")
    active_card = schemas.ActivePhaseCard(title=ap_title, subtitle=ap_sub, caption=ap_cap)

    if today < plan.start_date:
        cd_days, cd_cap = (plan.start_date - today).days, "days until Week 1 starts"
    else:
        cd_days = max(0, (plan.end_date - today).days)
        cd_cap = "plan window has ended" if today > plan.end_date else f"days left in the {WEEKS_TOTAL}-week plan"
    countdown = schemas.CountdownCard(
        days=cd_days, caption=cd_cap,
        target_finish=f"Target finish: {_fmt(plan.end_date, weekday=True, year=True)}",
    )

    tw_cap = ("Week 1 not started yet" if plan.current_week == 0 else
              f"{int(this_week_pct * BLOCKS_PER_WEEK + 0.5)} of {BLOCKS_PER_WEEK} study blocks done (Week {plan.current_week})")
    this_week = schemas.ThisWeekCard(pct=this_week_pct, bar=_bar(this_week_pct), caption=tw_cap)

    # --- phase table ---------------------------------------------------------
    rows: list[schemas.PhaseProgressRow] = []
    for p in phases:
        start, end = phase_window(p, plan.start_date)
        total, done = tally(pid=p.id), tally(pid=p.id, st=TaskStatus.COMPLETED)
        ex_total = tally(pid=p.id, cat=TaskCategory.EXIT_TEST)
        ex_done = tally(pid=p.id, cat=TaskCategory.EXIT_TEST, st=TaskStatus.COMPLETED)
        if total == 0:
            st_txt = "-"
        elif done == total:
            st_txt = "Complete"
        elif today < start:
            st_txt = "Upcoming"
        elif today > end:
            st_txt = "Behind"
        else:
            st_txt = "Active"
        rows.append(schemas.PhaseProgressRow(
            phase_id=p.id, phase=p.label, weeks=p.weeks_label, start=start, end=end,
            done=done, total=total, progress=(done / total if total else 0.0), status=st_txt,
            exit_tests=("-" if ex_total == 0 else f"{ex_done} / {ex_total}"),
            in_progress=tally(pid=p.id, st=TaskStatus.IN_PROGRESS),
        ))
    ex_all, ex_all_done = tally(cat=TaskCategory.EXIT_TEST), tally(cat=TaskCategory.EXIT_TEST, st=TaskStatus.COMPLETED)
    totals_row = schemas.PhaseProgressRow(
        phase_id=-1, phase="TOTAL", weeks="", start=plan.start_date, end=plan.end_date,
        done=tasks_done, total=tasks_total, progress=pct_done, status="",
        exit_tests=f"{ex_all_done} / {ex_all}", in_progress=tasks_wip,
    )

    # --- next up: first 5 open Task / Build / Exit Test items ------------------
    next_stmt = (
        select(Task).where(
            Task.status != TaskStatus.COMPLETED,
            Task.category.in_([TaskCategory.TASK, TaskCategory.BUILD, TaskCategory.EXIT_TEST]),
        ).order_by(Task.id).limit(5)
    )
    next_up = [
        schemas.NextUpItem(
            task_id=t.id, phase_code=t.phase.short_code,
            item=t.item[:68] + ("..." if len(t.item) > 68 else ""),
        )
        for t in db.scalars(next_stmt)
    ]

    # --- tracker snapshot ------------------------------------------------------
    skills = get_skills_report(db)
    dsa_total = db.scalar(select(func.count()).select_from(DsaEntry)) or 0
    dsa_resolved = db.scalar(select(func.count()).select_from(DsaEntry).where(DsaEntry.resolved.is_(True))) or 0
    jobs_total = db.scalar(select(func.count()).select_from(JobApplication)) or 0
    interviews = db.scalar(select(func.count()).select_from(JobApplication).where(
        JobApplication.status.in_([JobStatus.OA, JobStatus.INTERVIEW_1, JobStatus.INTERVIEW_2, JobStatus.OFFER]))) or 0
    mistakes = db.scalar(select(func.count()).select_from(MistakeEntry)) or 0

    def metric(label: str, actual: float, target: Optional[float]) -> schemas.MetricRow:
        prog = min(1.0, actual / target) if (target is not None and target > 0) else None
        return schemas.MetricRow(metric=label, actual=actual, target=target, progress=prog)

    snapshot = [
        metric("DSA problems solved", dsa_total, TARGET_DSA_SOLVED),
        metric("DSA problems re-solved", dsa_resolved, TARGET_DSA_RESOLVED),
        metric("Job applications sent", jobs_total, TARGET_JOB_APPLICATIONS),
        metric("Interviews / OAs / offers", interviews, None),
        metric("Study hours logged", weekly.totals.actual_hours, weekly.totals.planned_hours),
        metric("Must-have skills at level 3", skills.must_haves_at_level_3, skills.must_haves_total),
        metric("Mistakes logged", mistakes, None),
    ]

    return schemas.DashboardRead(
        owner_name=settings.owner_name, target_role=settings.target_role, plan=plan,
        overall=overall, active_phase=active_card, countdown=countdown, this_week=this_week,
        phases=rows, totals=totals_row, next_up=next_up,
        status_line=(f"Completed {tasks_done}   |   In progress {tasks_wip}   |   "
                     f"Not started {tally(st=TaskStatus.NOT_STARTED)}"),
        snapshot=snapshot, last_refreshed=settings.last_refreshed,
    )


# =============================================================================
# Dropdown lists (the hidden 'Lists' sheet)
# =============================================================================
def get_lists(db: Session) -> schemas.ListsRead:
    return schemas.ListsRead(
        status=[e.value for e in TaskStatus],
        view=[e.value for e in TaskView],
        phase_filter=["All Phases"] + [p.label for p in list_phases(db)],
        difficulty=[e.value for e in Difficulty],
        dsa_pattern=[e.value for e in DsaPattern],
        help=[0, 1, 2],
        job_status=[e.value for e in JobStatus],
        block_status=[e.value for e in BlockStatus if e != BlockStatus.NOT_APPLICABLE],
        skill_rating=[0, 1, 2, 3],
        tick=[TICK_OPEN, TICK_DONE],
        confidence=[1, 2, 3, 4, 5],
        task_category=[e.value for e in TaskCategory],
    )


# =============================================================================
# Build / seed  (BuildDevOpsTracker and the Build*Sheet / LoadTaskData procedures)
# =============================================================================
def _wipe(db: Session) -> None:
    """Child tables first so foreign keys stay satisfied."""
    for model in (DailyPlan, WeeklySummary, Task, Phase, Skill, DsaEntry, JobApplication,
                  MistakeEntry, PlanSettings):
        db.execute(delete(model))


def seed_database(db: Session, *, reset: bool = False) -> schemas.RebuildResult:
    """Create the plan data. reset=True wipes every table first, exactly like the VBA rebuild
    deleted and re-created all sheets."""
    try:
        if reset:
            _wipe(db)
        if db.get(PlanSettings, 1) is None:
            db.add(PlanSettings(id=1))
        db.add_all(Phase(id=i, label=lbl, week_start=w1, week_end=w2) for i, lbl, w1, w2 in sd.PHASES)
        db.flush()
        db.add_all(
            Task(phase_id=pid, category=TaskCategory(cat), item=item, status=TaskStatus.NOT_STARTED)
            for pid, cat, item in sd.TASKS
        )
        for wk in range(1, WEEKS_TOTAL + 1):
            db.add(WeeklySummary(
                week=wk, phase_code=sd.phase_of_week(wk), focus=sd.week_focus(wk),
                planned_hours=sd.DEFAULT_WEEKLY_PLANNED_HOURS,
                checkpoint_phase=sd.phase_of_week(wk) if sd.is_checkpoint_week(wk) else None,
            ))
        db.flush()
        daily: list[DailyPlan] = []
        for wk in range(1, WEEKS_TOTAL + 1):
            for d in range(7):
                weekday = d <= 4
                daily.append(DailyPlan(
                    week=wk, day_index=d, plan=sd.day_plan_text(wk, d),
                    planned_hours=sd.day_planned_hours(d),
                    block1=BlockStatus.PENDING,
                    block2=BlockStatus.PENDING if weekday else BlockStatus.NOT_APPLICABLE,
                    block3=BlockStatus.PENDING if weekday else BlockStatus.NOT_APPLICABLE,
                ))
        db.add_all(daily)
        db.add_all(Skill(skill_type=t, name=n) for t, n in sd.SKILLS)
        _commit(db)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Seeding failed") from exc
    return schemas.RebuildResult(
        detail="Tracker rebuilt" if reset else "Tracker seeded",
        tasks=len(sd.TASKS), daily_rows=len(daily),
    )


def ensure_seeded(db: Session) -> bool:
    """Called at start-up (the Workbook_Open equivalent). Seeds only when the DB is empty."""
    if db.scalar(select(func.count()).select_from(Phase)):
        return False
    seed_database(db)
    return True
