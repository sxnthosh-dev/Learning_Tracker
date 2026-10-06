"""
models.py - SQLAlchemy ORM models.

This module contains the original DevOps Job-Readiness Tracker models.

It supports both:

    uvicorn main:app --reload

and:

    uvicorn devops_tracker.main:app --reload

The newer Software + Cloud Engineer models are kept in
feature_models.py and use the same SQLAlchemy Base.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


# ============================================================
# DATABASE IMPORT COMPATIBILITY
# ============================================================

try:
    from .database import Base
except ImportError:
    from database import Base


# ============================================================
# SPECIAL CHARACTERS
# ============================================================

TICK_DONE = "\u2611"
TICK_OPEN = "\u2610"
TICK_WIP = "\u25D0"


# ============================================================
# ENUM / DROPDOWN DEFINITIONS
# ============================================================

class TaskStatus(str, enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class TaskView(str, enum.Enum):
    ALL = "All Tasks"
    PENDING = "Pending Only"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


class TaskCategory(str, enum.Enum):
    TASK = "Task"
    TOPIC = "Topic"
    BUILD = "Build"
    OPTIONAL = "Optional"
    EXIT_TEST = "Exit Test"


class Difficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class DsaPattern(str, enum.Enum):
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


class JobStatus(str, enum.Enum):
    APPLIED = "Applied"
    OA = "OA"
    INTERVIEW_1 = "Interview 1"
    INTERVIEW_2 = "Interview 2"
    OFFER = "Offer"
    REJECTED = "Rejected"
    NO_REPLY = "No reply"


class BlockStatus(str, enum.Enum):
    PENDING = "Pending"
    DONE = "Done"
    SKIPPED = "Skipped"
    NOT_APPLICABLE = "-"


def _enum_col(
    py_enum: type[enum.Enum],
    length: int = 32,
) -> SAEnum:
    """
    Store enum values such as 'In Progress'
    instead of enum member names.
    """

    return SAEnum(
        py_enum,
        native_enum=False,
        length=length,
        validate_strings=True,
        values_callable=lambda e: [
            member.value for member in e
        ],
    )


# ============================================================
# PLAN SETTINGS
# ============================================================

class PlanSettings(Base):
    """
    Single-row application settings table.
    """

    __tablename__ = "plan_settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )

    owner_name: Mapped[str] = mapped_column(
        String(100),
        default="Santhosh N",
    )

    target_role: Mapped[str] = mapped_column(
        String(150),
        default="Junior Cloud & DevOps Software Engineer",
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        default=date(2026, 10, 5),
    )

    last_refreshed: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )


# ============================================================
# PHASES
# ============================================================

class Phase(Base):
    """
    Setup (0), Phases 1-6, Tracks (7).
    """

    __tablename__ = "phases"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
    )

    label: Mapped[str] = mapped_column(
        String(100),
        unique=True,
    )

    week_start: Mapped[int] = mapped_column(
        Integer,
    )

    week_end: Mapped[int] = mapped_column(
        Integer,
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="phase",
        cascade="all, delete-orphan",
    )

    @property
    def weeks_label(self) -> str:
        if self.id == 0:
            return "Pre-W1"

        return f"W{self.week_start}-{self.week_end}"

    @property
    def short_code(self) -> str:
        return self.label.split(" ", 1)[0]


# ============================================================
# TASKS
# ============================================================

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phases.id"),
        index=True,
    )

    category: Mapped[TaskCategory] = mapped_column(
        _enum_col(TaskCategory, 20),
        default=TaskCategory.TASK,
    )

    item: Mapped[str] = mapped_column(
        Text,
    )

    status: Mapped[TaskStatus] = mapped_column(
        _enum_col(TaskStatus, 20),
        default=TaskStatus.NOT_STARTED,
        index=True,
    )

    done_on: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    phase: Mapped[Phase] = relationship(
        back_populates="tasks",
        lazy="joined",
    )

    @property
    def phase_label(self) -> str:
        return self.phase.label

    @property
    def weeks(self) -> str:
        return self.phase.weeks_label

    @property
    def tick(self) -> str:
        if not self.item:
            return ""

        if self.status == TaskStatus.COMPLETED:
            return TICK_DONE

        if self.status == TaskStatus.IN_PROGRESS:
            return TICK_WIP

        return TICK_OPEN


# ============================================================
# WEEKLY SUMMARY
# ============================================================

class WeeklySummary(Base):
    __tablename__ = "weekly_summary"

    __table_args__ = (
        CheckConstraint(
            "week BETWEEN 1 AND 18",
            name="ck_week_range",
        ),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 1 AND 5",
            name="ck_confidence_range",
        ),
    )

    week: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
    )

    phase_code: Mapped[str] = mapped_column(
        String(4),
    )

    focus: Mapped[str] = mapped_column(
        String(120),
    )

    planned_hours: Mapped[float] = mapped_column(
        Float,
        default=19.0,
    )

    build_shipped: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    confidence: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    checkpoint_phase: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
    )

    checkpoint_done: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


# ============================================================
# DAILY PLAN
# ============================================================

class DailyPlan(Base):
    """
    One row per plan day.
    """

    __tablename__ = "daily_plan"

    __table_args__ = (
        UniqueConstraint(
            "week",
            "day_index",
            name="uq_daily_week_day",
        ),
        CheckConstraint(
            "day_index BETWEEN 0 AND 6",
            name="ck_day_index",
        ),
        CheckConstraint(
            "actual_hours IS NULL OR "
            "(actual_hours >= 0 AND actual_hours <= 24)",
            name="ck_actual_hours",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    week: Mapped[int] = mapped_column(
        ForeignKey("weekly_summary.week"),
        index=True,
    )

    day_index: Mapped[int] = mapped_column(
        Integer,
    )

    plan: Mapped[str] = mapped_column(
        Text,
    )

    planned_hours: Mapped[float] = mapped_column(
        Float,
    )

    actual_hours: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    block1: Mapped[BlockStatus] = mapped_column(
        _enum_col(BlockStatus, 12),
        default=BlockStatus.PENDING,
    )

    block2: Mapped[BlockStatus] = mapped_column(
        _enum_col(BlockStatus, 12),
        default=BlockStatus.PENDING,
    )

    block3: Mapped[BlockStatus] = mapped_column(
        _enum_col(BlockStatus, 12),
        default=BlockStatus.PENDING,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


# ============================================================
# SKILLS
# ============================================================

class Skill(Base):
    __tablename__ = "skills"

    __table_args__ = (
        CheckConstraint(
            "wk1 IS NULL OR wk1 BETWEEN 0 AND 3",
            name="ck_wk1",
        ),
        CheckConstraint(
            "wk9 IS NULL OR wk9 BETWEEN 0 AND 3",
            name="ck_wk9",
        ),
        CheckConstraint(
            "wk18 IS NULL OR wk18 BETWEEN 0 AND 3",
            name="ck_wk18",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    skill_type: Mapped[str] = mapped_column(
        String(20),
    )

    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
    )

    evidence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    wk1: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    wk9: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    wk18: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )


# ============================================================
# DSA
# ============================================================

class DsaEntry(Base):
    __tablename__ = "dsa_log"

    __table_args__ = (
        CheckConstraint(
            "time_min IS NULL OR "
            "(time_min BETWEEN 0 AND 600)",
            name="ck_time_min",
        ),
        CheckConstraint(
            "help_level IS NULL OR "
            "help_level BETWEEN 0 AND 2",
            name="ck_help_level",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    solved_on: Mapped[date] = mapped_column(
        Date,
        index=True,
    )

    problem: Mapped[str] = mapped_column(
        String(200),
    )

    pattern: Mapped[Optional[DsaPattern]] = mapped_column(
        _enum_col(DsaPattern, 40),
        nullable=True,
    )

    difficulty: Mapped[Optional[Difficulty]] = mapped_column(
        _enum_col(Difficulty, 10),
        nullable=True,
    )

    time_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    help_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    key_idea: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


# ============================================================
# JOB APPLICATIONS
# ============================================================

class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    applied_on: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    company: Mapped[str] = mapped_column(
        String(150),
    )

    role: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )

    source: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )

    status: Mapped[Optional[JobStatus]] = mapped_column(
        _enum_col(JobStatus, 16),
        nullable=True,
    )

    follow_up_on: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    learned: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


# ============================================================
# MISTAKES
# ============================================================

class MistakeEntry(Base):
    __tablename__ = "mistake_log"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    logged_on: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    what_went_wrong: Mapped[str] = mapped_column(
        Text,
    )

    correction: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    topic: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
