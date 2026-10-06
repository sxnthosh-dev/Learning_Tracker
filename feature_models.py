"""
feature_models.py

Additional SQLAlchemy models for the Software + Cloud Engineer tracker.

These models intentionally live separately from the original tracker models
so the existing Dashboard, Tasks, DSA Tracker, Jobs, Skills, and Daily Planner
remain unchanged.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

try:
    from .database import Base
except ImportError:
    from database import Base


class TopicProgress(Base):
    __tablename__ = "topic_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    concept: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="Not Started"
    )
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class LeetCodeProblem(Base):
    __tablename__ = "leetcode_problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="Not Started"
    )
    language: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    acceptance: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    date_added: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    revision_priority: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mistakes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    revision_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    solved_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    task_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    python_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    java_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    leetcode_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Planning"
    )
    tech_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    live_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SavedPrompt(Base):
    __tablename__ = "saved_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    python_target_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=70
    )
    java_target_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    interview_mode: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Balanced"
    )
    ai_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Local/Fallback"
    )


class CloudRoadmapProgress(Base):
    __tablename__ = "cloud_roadmap_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stage_number: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    stage_title: Mapped[str] = mapped_column(String(150), nullable=False)
    topic: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
