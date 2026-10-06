from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Shared configuration
# =============================================================================

class FeatureBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Home / dashboard
# =============================================================================

class HomeSummaryRead(FeatureBase):
    total_topics: int = 0
    completed_topics: int = 0
    topic_completion_pct: float = 0.0

    total_leetcode: int = 0
    solved_leetcode: int = 0
    leetcode_completion_pct: float = 0.0

    total_daily_tasks: int = 0
    completed_daily_tasks: int = 0
    daily_completion_pct: float = 0.0

    total_cloud_stages: int = 0
    completed_cloud_stages: int = 0
    cloud_completion_pct: float = 0.0

    total_projects: int = 0
    completed_projects: int = 0

    current_streak: int = 0


# =============================================================================
# Topic progress
# =============================================================================

class TopicProgressCreate(BaseModel):
    concept: str = Field(min_length=1, max_length=100)
    language: str = Field(min_length=1, max_length=30)
    status: str = "Not Started"
    completed_date: Optional[date] = None
    notes: Optional[str] = None


class TopicProgressUpdate(BaseModel):
    status: Optional[str] = None
    completed_date: Optional[date] = None
    notes: Optional[str] = None


class TopicProgressRead(FeatureBase):
    id: int
    concept: str
    language: str
    status: str
    completed_date: Optional[date] = None
    notes: Optional[str] = None


# =============================================================================
# LeetCode
# =============================================================================

class LeetCodeCreate(BaseModel):
    number: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    difficulty: str = Field(min_length=1, max_length=30)
    status: str = "Not Started"
    language: Optional[str] = None
    topic: Optional[str] = None
    acceptance: Optional[str] = None
    frequency: Optional[str] = None
    date_added: Optional[date] = None
    revision_priority: Optional[str] = None
    notes: Optional[str] = None
    mistakes: Optional[str] = None
    confidence: Optional[int] = Field(default=None, ge=1, le=5)
    revision_flag: bool = False
    stage: Optional[str] = None
    solved_on: Optional[date] = None


class LeetCodeUpdate(BaseModel):
    status: Optional[str] = None
    language: Optional[str] = None
    topic: Optional[str] = None
    revision_priority: Optional[str] = None
    notes: Optional[str] = None
    mistakes: Optional[str] = None
    confidence: Optional[int] = Field(default=None, ge=1, le=5)
    revision_flag: Optional[bool] = None
    stage: Optional[str] = None
    solved_on: Optional[date] = None


class LeetCodeRead(FeatureBase):
    id: int
    number: int
    title: str
    difficulty: str
    status: str
    language: Optional[str] = None
    topic: Optional[str] = None
    acceptance: Optional[str] = None
    frequency: Optional[str] = None
    date_added: Optional[date] = None
    revision_priority: Optional[str] = None
    notes: Optional[str] = None
    mistakes: Optional[str] = None
    confidence: Optional[int] = None
    revision_flag: bool
    stage: Optional[str] = None
    solved_on: Optional[date] = None


# =============================================================================
# Daily plan
# =============================================================================

class DailyTaskCreate(BaseModel):
    day_number: int = Field(gt=0)
    task_date: date
    concept: str = Field(min_length=1, max_length=255)
    python_task: Optional[str] = None
    java_task: Optional[str] = None
    leetcode_task: Optional[str] = None
    ai_prompt: Optional[str] = None
    completed: bool = False
    notes: Optional[str] = None


class DailyTaskUpdate(BaseModel):
    completed: Optional[bool] = None
    notes: Optional[str] = None


class DailyTaskRead(FeatureBase):
    id: int
    day_number: int
    task_date: date
    concept: str
    python_task: Optional[str] = None
    java_task: Optional[str] = None
    leetcode_task: Optional[str] = None
    ai_prompt: Optional[str] = None
    completed: bool
    notes: Optional[str] = None


class StreakRead(BaseModel):
    current_streak: int
    longest_streak: int = 0
    completed_days: int = 0


# =============================================================================
# Projects
# =============================================================================

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    stage: str = "Planning"
    tech_stack: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    completed_date: Optional[date] = None
    notes: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = None
    stage: Optional[str] = None
    tech_stack: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    completed_date: Optional[date] = None
    notes: Optional[str] = None


class ProjectRead(FeatureBase):
    id: int
    name: str
    description: Optional[str] = None
    stage: str
    tech_stack: Optional[str] = None
    repo_url: Optional[str] = None
    live_url: Optional[str] = None
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    completed_date: Optional[date] = None
    notes: Optional[str] = None


# =============================================================================
# Prompt library
# =============================================================================

class PromptCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    category: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1)


class PromptRead(FeatureBase):
    id: int
    title: str
    category: str
    content: str
    created_at: datetime


# =============================================================================
# Preferences
# =============================================================================

class PreferenceUpdate(BaseModel):
    python_target_pct: int = Field(ge=0, le=100)
    java_target_pct: int = Field(ge=0, le=100)
    interview_mode: str = Field(min_length=1, max_length=50)
    ai_provider: str = Field(min_length=1, max_length=50)


class PreferenceRead(FeatureBase):
    id: int
    python_target_pct: int
    java_target_pct: int
    interview_mode: str
    ai_provider: str


# =============================================================================
# Cloud roadmap
# =============================================================================

class CloudRoadmapRead(FeatureBase):
    id: int
    stage_number: int
    stage_title: str
    topic: str
    description: Optional[str] = None
    completed: bool
    completed_date: Optional[date] = None


class CloudRoadmapUpdate(BaseModel):
    completed: bool
    completed_date: Optional[date] = None


# =============================================================================
# Analytics
# =============================================================================

class AnalyticsRead(BaseModel):
    topics_total: int = 0
    topics_completed: int = 0
    topics_completion_pct: float = 0.0

    leetcode_total: int = 0
    leetcode_solved: int = 0
    leetcode_completion_pct: float = 0.0

    daily_total: int = 0
    daily_completed: int = 0
    daily_completion_pct: float = 0.0

    cloud_total: int = 0
    cloud_completed: int = 0
    cloud_completion_pct: float = 0.0

    projects_total: int = 0
    projects_completed: int = 0

    current_streak: int = 0
