"""
schemas.py - Pydantic v2 request/response models.

These replace the worksheet Data Validation rules: every dropdown list is an Enum, every
numeric rule (hours 0-24, minutes 0-600, help 0-2, confidence 1-5, rating 0-3) is a Field
constraint, and the Monday-only StartDate rule is a validator.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from .models import (
    BlockStatus, Difficulty, DsaPattern, JobStatus, TaskCategory, TaskStatus, TaskView,
)

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Rating = Annotated[int, Field(ge=0, le=3)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str


# ----------------------------------------------------------------- settings / plan
class SettingsRead(ORMModel):
    owner_name: str
    target_role: str
    start_date: date
    last_refreshed: Optional[datetime] = None


class SettingsUpdate(BaseModel):
    owner_name: Optional[NonEmptyStr] = None
    target_role: Optional[NonEmptyStr] = None
    start_date: Optional[date] = None

    @field_validator("start_date")
    @classmethod
    def _must_be_monday(cls, v: Optional[date]) -> Optional[date]:
        # VBA: validation "=WEEKDAY($L$3,2)=1"
        if v is not None and v.weekday() != 0:
            raise ValueError("start_date must be a Monday")
        return v


class PlanStatus(BaseModel):
    """Named formulas StartDate / EndDate / CurWeek / ActivePhase."""
    start_date: date
    end_date: date
    weeks_total: int
    current_week: int          # 0 = plan has not started
    active_phase: str          # full phase label, or 'Pre-start' / 'Plan ended'
    today: date


class PhaseRead(ORMModel):
    id: int
    label: str
    weeks_label: str
    week_start: int
    week_end: int


# ----------------------------------------------------------------- tasks
class TaskCreate(BaseModel):
    phase_id: int = Field(ge=0, le=7)
    category: TaskCategory = TaskCategory.TASK
    item: NonEmptyStr
    status: TaskStatus = TaskStatus.NOT_STARTED
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    phase_id: Optional[int] = Field(default=None, ge=0, le=7)
    category: Optional[TaskCategory] = None
    item: Optional[NonEmptyStr] = None
    status: Optional[TaskStatus] = None
    notes: Optional[str] = None


class TaskRead(ORMModel):
    id: int
    phase_id: int
    phase_label: str
    weeks: str
    category: TaskCategory
    item: str
    status: TaskStatus
    tick: str
    done_on: Optional[date] = None
    notes: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskStatusResult(BaseModel):
    """Result of a status change - carries the 'phase complete' celebration flag (CheckPhaseComplete)."""
    task: TaskRead
    phase_complete: bool = False
    message: Optional[str] = None


# ----------------------------------------------------------------- weekly / daily
class WeeklyRowRead(BaseModel):
    week: int
    week_of: date
    phase_code: str
    focus: str
    planned_hours: float
    actual_hours: Optional[float]      # blank until a day has Actual hrs > 0
    dsa_solved: Optional[int]          # blank for weeks that have not started
    blocks_done_pct: float             # done blocks / 17
    build_shipped: bool
    confidence: Optional[int]
    checkpoint_phase: Optional[str]
    checkpoint_done: bool
    notes: Optional[str]
    is_current_week: bool


class WeeklyTotals(BaseModel):
    planned_hours: float
    actual_hours: float
    dsa_solved: int
    avg_blocks_done_pct: float
    builds_shipped: int
    avg_confidence: Optional[float]


class WeeklyReport(BaseModel):
    rows: list[WeeklyRowRead]
    totals: WeeklyTotals


class WeeklyUpdate(BaseModel):
    planned_hours: Optional[float] = Field(default=None, ge=0, le=168)
    build_shipped: Optional[bool] = None
    confidence: Optional[int] = Field(default=None, ge=1, le=5)
    checkpoint_done: Optional[bool] = None
    notes: Optional[str] = None


class DailyRead(BaseModel):
    id: int
    week: int
    day_index: int
    day: str                            # Mon..Sun
    day_date: date
    plan: str
    planned_hours: float
    actual_hours: Optional[float]
    block1: BlockStatus
    block2: BlockStatus
    block3: BlockStatus
    day_pct: float
    day_done: bool
    notes: Optional[str]
    is_today: bool


class DailyUpdate(BaseModel):
    actual_hours: Optional[float] = Field(default=None, ge=0, le=24)   # validation 0-24
    block1: Optional[BlockStatus] = None
    block2: Optional[BlockStatus] = None
    block3: Optional[BlockStatus] = None
    notes: Optional[str] = None


# ----------------------------------------------------------------- skills
class SkillRead(BaseModel):
    id: int
    skill_type: str
    name: str
    evidence: Optional[str]
    wk1: Optional[int]
    wk9: Optional[int]
    wk18: Optional[int]
    latest: Optional[int]
    gap: str


class SkillUpdate(BaseModel):
    evidence: Optional[str] = None
    wk1: Optional[Rating] = None
    wk9: Optional[Rating] = None
    wk18: Optional[Rating] = None


class SkillsReport(BaseModel):
    skills: list[SkillRead]
    summary: str                        # "Must-haves at level 3: x of y | Average latest rating: z / 3"
    must_haves_at_level_3: int
    must_haves_total: int
    average_latest_rating: float


# ----------------------------------------------------------------- DSA log
class DsaBase(BaseModel):
    pattern: Optional[DsaPattern] = None
    difficulty: Optional[Difficulty] = None
    time_min: Optional[int] = Field(default=None, ge=0, le=600)
    help_level: Optional[int] = Field(default=None, ge=0, le=2)
    key_idea: Optional[str] = None


class DsaCreate(DsaBase):
    problem: NonEmptyStr
    solved_on: Optional[date] = None    # stamped with today when omitted (OnLogsChanged)
    resolved: bool = False


class DsaUpdate(DsaBase):
    problem: Optional[NonEmptyStr] = None
    solved_on: Optional[date] = None
    resolved: Optional[bool] = None


class DsaRead(ORMModel):
    id: int
    solved_on: date
    problem: str
    pattern: Optional[DsaPattern]
    difficulty: Optional[Difficulty]
    time_min: Optional[int]
    help_level: Optional[int]
    resolved: bool
    key_idea: Optional[str]


# ----------------------------------------------------------------- jobs
class JobBase(BaseModel):
    role: Optional[str] = None
    source: Optional[str] = None
    status: Optional[JobStatus] = None
    follow_up_on: Optional[date] = None
    learned: Optional[str] = None


class JobCreate(JobBase):
    company: NonEmptyStr
    applied_on: Optional[date] = None   # stamped with today when omitted


class JobUpdate(JobBase):
    company: Optional[NonEmptyStr] = None
    applied_on: Optional[date] = None


class JobRead(BaseModel):
    id: int
    applied_on: Optional[date]
    company: str
    role: Optional[str]
    source: Optional[str]
    status: Optional[JobStatus]
    follow_up_on: Optional[date]
    days_waiting: Optional[int]
    follow_up_overdue: bool             # the red conditional format on the follow-up cell
    learned: Optional[str]


# ----------------------------------------------------------------- mistakes
class MistakeCreate(BaseModel):
    what_went_wrong: NonEmptyStr
    correction: Optional[str] = None
    topic: Optional[str] = None
    logged_on: Optional[date] = None


class MistakeUpdate(BaseModel):
    what_went_wrong: Optional[NonEmptyStr] = None
    correction: Optional[str] = None
    topic: Optional[str] = None
    logged_on: Optional[date] = None


class MistakeRead(ORMModel):
    id: int
    logged_on: Optional[date]
    what_went_wrong: str
    correction: Optional[str]
    topic: Optional[str]


# ----------------------------------------------------------------- dashboard
class OverallCard(BaseModel):
    pct_done: float
    bar: str
    caption: str


class ActivePhaseCard(BaseModel):
    title: str
    subtitle: str
    caption: str


class CountdownCard(BaseModel):
    days: int
    caption: str
    target_finish: str


class ThisWeekCard(BaseModel):
    pct: float
    bar: str
    caption: str


class PhaseProgressRow(BaseModel):
    phase_id: int
    phase: str
    weeks: str
    start: date
    end: date
    done: int
    total: int
    progress: float
    status: str                         # Complete / Upcoming / Behind / Active / "-"
    exit_tests: str                     # "x / y" or "-"
    in_progress: int


class NextUpItem(BaseModel):
    task_id: int
    phase_code: str
    item: str                           # truncated to 68 chars + "..." like the sheet


class MetricRow(BaseModel):
    metric: str
    actual: float
    target: Optional[float]
    progress: Optional[float]


class DashboardRead(BaseModel):
    owner_name: str
    target_role: str
    plan: PlanStatus
    overall: OverallCard
    active_phase: ActivePhaseCard
    countdown: CountdownCard
    this_week: ThisWeekCard
    phases: list[PhaseProgressRow]
    totals: PhaseProgressRow
    next_up: list[NextUpItem]
    status_line: str                    # "Completed n | In progress n | Not started n"
    snapshot: list[MetricRow]
    last_refreshed: Optional[datetime]


# ----------------------------------------------------------------- lists / admin
class ListsRead(BaseModel):
    """Dropdown sources from the hidden 'Lists' sheet (named ranges lst*)."""
    status: list[str]
    view: list[str]
    phase_filter: list[str]
    difficulty: list[str]
    dsa_pattern: list[str]
    help: list[int]
    job_status: list[str]
    block_status: list[str]
    skill_rating: list[int]
    tick: list[str]
    confidence: list[int]
    task_category: list[str]


class RefreshResult(BaseModel):
    last_refreshed: datetime


class RebuildResult(BaseModel):
    detail: str
    tasks: int
    daily_rows: int
