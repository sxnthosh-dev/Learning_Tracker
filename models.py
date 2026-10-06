"""
models.py - SQLAlchemy ORM models.  One model per Excel table / log section.

Worksheet -> table mapping
--------------------------
  Dashboard!L3, M34 (StartDate, LastRefreshed)  -> PlanSettings
  Dashboard phase table (rows 14-21)            -> Phase  (static definitions; progress is computed)
  Phases & Tasks (rows 7-156)                   -> Task
  Weekly Tracker  A. Weekly Summary (9-26)      -> WeeklySummary (inputs only; hours/DSA/blocks are computed)
  Weekly Tracker  B. Daily Planner (32-157)     -> DailyPlan
  Skills & Logs   1. Skill Matrix               -> Skill
  Skills & Logs   2. DSA Log                    -> DsaEntry
  Skills & Logs   3. Job Application Tracker   -> JobApplication
  Skills & Logs   4. Mistake Log                -> MistakeEntry
  Lists sheet (dropdown sources)                -> the str-Enums below (Data Validation equivalents)

Columns that were worksheet formulas in the VBA (Day %, Days waiting, Latest rating ...)
are NOT stored; services.py derives them so they can never go stale.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum as SAEnum, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# --- special characters (VBA: TickDone / TickOpen / TickWip) -----------------
TICK_DONE = "\u2611"   # ballot box with check  (ChrW 9745)
TICK_OPEN = "\u2610"   # empty ballot box       (ChrW 9744)
TICK_WIP = "\u25D0"    # circle, right half black (ChrW 9680)


# --- dropdown lists (VBA BuildLists / PutList) -------------------------------
class TaskStatus(str, enum.Enum):          # lstStatus
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class TaskView(str, enum.Enum):            # lstView
    ALL = "All Tasks"
    PENDING = "Pending Only"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class TaskCategory(str, enum.Enum):        # "Category" column values used by AddTask
    TASK = "Task"
    TOPIC = "Topic"
    BUILD = "Build"
    OPTIONAL = "Optional"
    EXIT_TEST = "Exit Test"


class Difficulty(str, enum.Enum):          # lstDiff
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class DsaPattern(str, enum.Enum):          # lstPattern
    SETUP = "Setup / warm-up"
    ARRAYS = "Arrays / strings / hashing"
    TWO_POINTERS = "Two pointers"
    SLIDING_WINDOW = "Sliding window"
    STACK = "Stack"
    BINARY_SEARCH = "Binary search"
    LINKED_LIST = "Linked list"
    RECURSION = "Recursion"
    TREES = "Trees / BST"
    GRAPHS = "BFS / DFS / graphs"
    HEAPS = "Heaps"
    GREEDY = "Greedy"
    INTERVALS = "Intervals"
    DP_1D = "Dynamic programming (1-D)"
    MIXED = "Mixed / timed set"
    OTHER = "Other"


class JobStatus(str, enum.Enum):           # lstJobStatus
    APPLIED = "Applied"
    OA = "OA"
    INTERVIEW_1 = "Interview 1"
    INTERVIEW_2 = "Interview 2"
    OFFER = "Offer"
    REJECTED = "Rejected"
    NO_REPLY = "No reply"


class BlockStatus(str, enum.Enum):         # lstBlock (+ "-" = block not applicable, weekends)
    PENDING = "Pending"
    DONE = "Done"
    SKIPPED = "Skipped"
    NOT_APPLICABLE = "-"


def _enum_col(py_enum: type[enum.Enum], length: int = 32) -> SAEnum:
    """Store the human-readable value (e.g. 'In Progress'), not the member name."""
    return SAEnum(
        py_enum, native_enum=False, length=length, validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )


# --- tables ------------------------------------------------------------------
class PlanSettings(Base):
    """Single-row table: StartDate / LastRefreshed / header text from the Dashboard."""
    __tablename__ = "plan_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    owner_name: Mapped[str] = mapped_column(String(100), default="Santhosh N")
    target_role: Mapped[str] = mapped_column(
        String(150), default="Junior Cloud & DevOps Software Engineer"
    )
    start_date: Mapped[date] = mapped_column(Date, default=date(2026, 10, 5))  # must be a Monday
    last_refreshed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Phase(Base):
    """Setup (0), Phases 1-6, Tracks (7)."""
    __tablename__ = "phases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    label: Mapped[str] = mapped_column(String(100), unique=True)
    week_start: Mapped[int] = mapped_column(Integer)
    week_end: Mapped[int] = mapped_column(Integer)

    tasks: Mapped[list["Task"]] = relationship(back_populates="phase", cascade="all, delete-orphan")

    @property
    def weeks_label(self) -> str:                      # VBA PhWeeks
        return "Pre-W1" if self.id == 0 else f"W{self.week_start}-{self.week_end}"

    @property
    def short_code(self) -> str:
        """'P1' from 'P1 - Linux...' (dashboard 'Next up' column uses LEFT(label, FIND(' ')-1))."""
        return self.label.split(" ", 1)[0]


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phase_id: Mapped[int] = mapped_column(ForeignKey("phases.id"), index=True)
    category: Mapped[TaskCategory] = mapped_column(_enum_col(TaskCategory, 20), default=TaskCategory.TASK)
    item: Mapped[str] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(_enum_col(TaskStatus, 20), default=TaskStatus.NOT_STARTED, index=True)
    done_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)   # "Completed on"
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    phase: Mapped[Phase] = relationship(back_populates="tasks", lazy="joined")

    # Read-only helpers consumed by schemas.TaskRead (from_attributes=True)
    @property
    def phase_label(self) -> str:
        return self.phase.label

    @property
    def weeks(self) -> str:
        return self.phase.weeks_label

    @property
    def tick(self) -> str:
        """Same rule as the sheet's tick-column formula."""
        if not self.item:
            return ""
        if self.status == TaskStatus.COMPLETED:
            return TICK_DONE
        if self.status == TaskStatus.IN_PROGRESS:
            return TICK_WIP
        return TICK_OPEN


class WeeklySummary(Base):
    """Hand-entered columns of 'A. Weekly Summary'. Week-of date, actual hrs, DSA solved
    and block % are formulas in Excel and are derived in services.py."""
    __tablename__ = "weekly_summary"
    __table_args__ = (
        CheckConstraint("week BETWEEN 1 AND 18", name="ck_week_range"),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 1 AND 5", name="ck_confidence_range"),
    )

    week: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    phase_code: Mapped[str] = mapped_column(String(4))                 # 'P1'..'P6'
    focus: Mapped[str] = mapped_column(String(120))
    planned_hours: Mapped[float] = mapped_column(Float, default=19.0)
    build_shipped: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # lstConf 1-5
    checkpoint_phase: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)  # only checkpoint weeks
    checkpoint_done: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DailyPlan(Base):
    """One row per plan day (18 weeks x 7 = 126)."""
    __tablename__ = "daily_plan"
    __table_args__ = (
        UniqueConstraint("week", "day_index", name="uq_daily_week_day"),
        CheckConstraint("day_index BETWEEN 0 AND 6", name="ck_day_index"),
        CheckConstraint("actual_hours IS NULL OR (actual_hours >= 0 AND actual_hours <= 24)", name="ck_actual_hours"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week: Mapped[int] = mapped_column(ForeignKey("weekly_summary.week"), index=True)
    day_index: Mapped[int] = mapped_column(Integer)                    # 0 = Mon ... 6 = Sun
    plan: Mapped[str] = mapped_column(Text)
    planned_hours: Mapped[float] = mapped_column(Float)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    block1: Mapped[BlockStatus] = mapped_column(_enum_col(BlockStatus, 12), default=BlockStatus.PENDING)
    block2: Mapped[BlockStatus] = mapped_column(_enum_col(BlockStatus, 12), default=BlockStatus.PENDING)
    block3: Mapped[BlockStatus] = mapped_column(_enum_col(BlockStatus, 12), default=BlockStatus.PENDING)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint("wk1 IS NULL OR wk1 BETWEEN 0 AND 3", name="ck_wk1"),
        CheckConstraint("wk9 IS NULL OR wk9 BETWEEN 0 AND 3", name="ck_wk9"),
        CheckConstraint("wk18 IS NULL OR wk18 BETWEEN 0 AND 3", name="ck_wk18"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_type: Mapped[str] = mapped_column(String(20))               # Must-have / Should / Nice-to-have
    name: Mapped[str] = mapped_column(String(120), unique=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wk1: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wk9: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wk18: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class DsaEntry(Base):
    __tablename__ = "dsa_log"
    __table_args__ = (
        CheckConstraint("time_min IS NULL OR (time_min BETWEEN 0 AND 600)", name="ck_time_min"),
        CheckConstraint("help_level IS NULL OR help_level BETWEEN 0 AND 2", name="ck_help_level"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solved_on: Mapped[date] = mapped_column(Date, index=True)
    problem: Mapped[str] = mapped_column(String(200))
    pattern: Mapped[Optional[DsaPattern]] = mapped_column(_enum_col(DsaPattern, 40), nullable=True)
    difficulty: Mapped[Optional[Difficulty]] = mapped_column(_enum_col(Difficulty, 10), nullable=True)
    time_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    help_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # 0 none, 1 hint, 2 read solution
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)              # "Re-solved" tick
    key_idea: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    applied_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    company: Mapped[str] = mapped_column(String(150))
    role: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)   # "Source / referral"
    status: Mapped[Optional[JobStatus]] = mapped_column(_enum_col(JobStatus, 16), nullable=True)
    follow_up_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MistakeEntry(Base):
    __tablename__ = "mistake_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    logged_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    what_went_wrong: Mapped[str] = mapped_column(Text)
    correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # "Correct answer / how I verified"
    topic: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
