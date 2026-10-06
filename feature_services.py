from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

try:
    from .feature_models import (
        CloudRoadmapProgress,
        DailyTask,
        LeetCodeProblem,
        Project,
        SavedPrompt,
        TopicProgress,
        UserPreference,
    )
except ImportError:
    from feature_models import (
        CloudRoadmapProgress,
        DailyTask,
        LeetCodeProblem,
        Project,
        SavedPrompt,
        TopicProgress,
        UserPreference,
    )

try:
    from .feature_schemas import (
        CloudRoadmapUpdate,
        DailyTaskCreate,
        DailyTaskUpdate,
        LeetCodeCreate,
        LeetCodeUpdate,
        PreferenceUpdate,
        ProjectCreate,
        ProjectUpdate,
        PromptCreate,
        TopicProgressCreate,
        TopicProgressUpdate,
    )
except ImportError:
    from feature_schemas import (
        CloudRoadmapUpdate,
        DailyTaskCreate,
        DailyTaskUpdate,
        LeetCodeCreate,
        LeetCodeUpdate,
        PreferenceUpdate,
        ProjectCreate,
        ProjectUpdate,
        PromptCreate,
        TopicProgressCreate,
        TopicProgressUpdate,
    )


# =============================================================================
# Utility helpers
# =============================================================================

def _model_dict(model) -> dict:
    """Return only explicitly supplied Pydantic fields."""
    return model.model_dump(exclude_unset=True)


def _percentage(completed: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((completed / total) * 100, 1)


# =============================================================================
# Home dashboard
# =============================================================================

def get_home_summary(db: Session) -> dict:
    topics_total = db.scalar(
        select(func.count()).select_from(TopicProgress)
    ) or 0

    topics_completed = db.scalar(
        select(func.count())
        .select_from(TopicProgress)
        .where(TopicProgress.status == "Completed")
    ) or 0

    leetcode_total = db.scalar(
        select(func.count()).select_from(LeetCodeProblem)
    ) or 0

    leetcode_solved = db.scalar(
        select(func.count())
        .select_from(LeetCodeProblem)
        .where(LeetCodeProblem.status == "Solved")
    ) or 0

    daily_total = db.scalar(
        select(func.count()).select_from(DailyTask)
    ) or 0

    daily_completed = db.scalar(
        select(func.count())
        .select_from(DailyTask)
        .where(DailyTask.completed.is_(True))
    ) or 0

    cloud_total = db.scalar(
        select(func.count()).select_from(CloudRoadmapProgress)
    ) or 0

    cloud_completed = db.scalar(
        select(func.count())
        .select_from(CloudRoadmapProgress)
        .where(CloudRoadmapProgress.completed.is_(True))
    ) or 0

    projects_total = db.scalar(
        select(func.count()).select_from(Project)
    ) or 0

    projects_completed = db.scalar(
        select(func.count())
        .select_from(Project)
        .where(Project.stage == "Completed")
    ) or 0

    streak = get_streak(db)

    return {
        "total_topics": topics_total,
        "completed_topics": topics_completed,
        "topic_completion_pct": _percentage(
            topics_completed, topics_total
        ),
        "total_leetcode": leetcode_total,
        "solved_leetcode": leetcode_solved,
        "leetcode_completion_pct": _percentage(
            leetcode_solved, leetcode_total
        ),
        "total_daily_tasks": daily_total,
        "completed_daily_tasks": daily_completed,
        "daily_completion_pct": _percentage(
            daily_completed, daily_total
        ),
        "total_cloud_stages": cloud_total,
        "completed_cloud_stages": cloud_completed,
        "cloud_completion_pct": _percentage(
            cloud_completed, cloud_total
        ),
        "total_projects": projects_total,
        "completed_projects": projects_completed,
        "current_streak": streak["current_streak"],
    }


# =============================================================================
# Topic progress
# =============================================================================

def list_topic_progress(
    db: Session,
    language: Optional[str] = None,
    status: Optional[str] = None,
) -> list[TopicProgress]:
    query = select(TopicProgress).order_by(
        TopicProgress.language,
        TopicProgress.id,
    )

    if language:
        query = query.where(TopicProgress.language == language)

    if status:
        query = query.where(TopicProgress.status == status)

    return list(db.scalars(query).all())


def create_topic_progress(
    db: Session,
    payload: TopicProgressCreate,
) -> TopicProgress:
    item = TopicProgress(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_topic_progress(
    db: Session,
    item_id: int,
    payload: TopicProgressUpdate,
) -> Optional[TopicProgress]:
    item = db.get(TopicProgress, item_id)

    if item is None:
        return None

    for key, value in _model_dict(payload).items():
        setattr(item, key, value)

    if item.status == "Completed" and item.completed_date is None:
        item.completed_date = date.today()

    db.commit()
    db.refresh(item)
    return item


# =============================================================================
# LeetCode
# =============================================================================

def list_leetcode(
    db: Session,
    difficulty: Optional[str] = None,
    status: Optional[str] = None,
    topic: Optional[str] = None,
    language: Optional[str] = None,
    revision_only: bool = False,
) -> list[LeetCodeProblem]:
    query = select(LeetCodeProblem).order_by(
        LeetCodeProblem.number
    )

    if difficulty:
        query = query.where(
            LeetCodeProblem.difficulty == difficulty
        )

    if status:
        query = query.where(
            LeetCodeProblem.status == status
        )

    if topic:
        query = query.where(
            LeetCodeProblem.topic == topic
        )

    if language:
        query = query.where(
            LeetCodeProblem.language == language
        )

    if revision_only:
        query = query.where(
            LeetCodeProblem.revision_flag.is_(True)
        )

    return list(db.scalars(query).all())


def create_leetcode(
    db: Session,
    payload: LeetCodeCreate,
) -> LeetCodeProblem:
    item = LeetCodeProblem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_leetcode(
    db: Session,
    item_id: int,
    payload: LeetCodeUpdate,
) -> Optional[LeetCodeProblem]:
    item = db.get(LeetCodeProblem, item_id)

    if item is None:
        return None

    for key, value in _model_dict(payload).items():
        setattr(item, key, value)

    if item.status == "Solved" and item.solved_on is None:
        item.solved_on = date.today()

    db.commit()
    db.refresh(item)
    return item


def delete_leetcode(
    db: Session,
    item_id: int,
) -> bool:
    item = db.get(LeetCodeProblem, item_id)

    if item is None:
        return False

    db.delete(item)
    db.commit()
    return True


# =============================================================================
# Daily plan
# =============================================================================

def list_daily_tasks(
    db: Session,
    completed: Optional[bool] = None,
) -> list[DailyTask]:
    query = select(DailyTask).order_by(
        DailyTask.day_number
    )

    if completed is not None:
        query = query.where(
            DailyTask.completed.is_(completed)
        )

    return list(db.scalars(query).all())


def create_daily_task(
    db: Session,
    payload: DailyTaskCreate,
) -> DailyTask:
    item = DailyTask(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_daily_task(
    db: Session,
    item_id: int,
    payload: DailyTaskUpdate,
) -> Optional[DailyTask]:
    item = db.get(DailyTask, item_id)

    if item is None:
        return None

    for key, value in _model_dict(payload).items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def get_today_task(db: Session) -> Optional[DailyTask]:
    return db.scalar(
        select(DailyTask)
        .where(DailyTask.task_date == date.today())
        .order_by(DailyTask.day_number)
    )


# =============================================================================
# Streak
# =============================================================================

def get_streak(db: Session) -> dict:
    completed_dates = db.scalars(
        select(DailyTask.task_date)
        .where(DailyTask.completed.is_(True))
        .order_by(DailyTask.task_date.desc())
    ).all()

    unique_dates = sorted(
        set(completed_dates),
        reverse=True,
    )

    if not unique_dates:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "completed_days": 0,
        }

    current_streak = 0
    expected = date.today()

    if unique_dates[0] != expected:
        expected = unique_dates[0]

    for completed_date in unique_dates:
        if completed_date == expected:
            current_streak += 1
            expected -= timedelta(days=1)
        elif completed_date < expected:
            break

    longest_streak = 0
    running = 0
    previous: Optional[date] = None

    for completed_date in sorted(unique_dates):
        if previous is None:
            running = 1
        elif completed_date == previous + timedelta(days=1):
            running += 1
        else:
            running = 1

        longest_streak = max(longest_streak, running)
        previous = completed_date

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "completed_days": len(unique_dates),
    }


# =============================================================================
# Projects
# =============================================================================

def list_projects(db: Session) -> list[Project]:
    return list(
        db.scalars(
            select(Project).order_by(Project.id.desc())
        ).all()
    )


def create_project(
    db: Session,
    payload: ProjectCreate,
) -> Project:
    item = Project(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_project(
    db: Session,
    item_id: int,
    payload: ProjectUpdate,
) -> Optional[Project]:
    item = db.get(Project, item_id)

    if item is None:
        return None

    for key, value in _model_dict(payload).items():
        setattr(item, key, value)

    if item.stage == "Completed" and item.completed_date is None:
        item.completed_date = date.today()

    db.commit()
    db.refresh(item)
    return item


def delete_project(
    db: Session,
    item_id: int,
) -> bool:
    item = db.get(Project, item_id)

    if item is None:
        return False

    db.delete(item)
    db.commit()
    return True


# =============================================================================
# Prompt library
# =============================================================================

def list_prompts(
    db: Session,
    category: Optional[str] = None,
) -> list[SavedPrompt]:
    query = select(SavedPrompt).order_by(
        SavedPrompt.id.desc()
    )

    if category:
        query = query.where(
            SavedPrompt.category == category
        )

    return list(db.scalars(query).all())


def create_prompt(
    db: Session,
    payload: PromptCreate,
) -> SavedPrompt:
    item = SavedPrompt(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_prompt(
    db: Session,
    item_id: int,
) -> bool:
    item = db.get(SavedPrompt, item_id)

    if item is None:
        return False

    db.delete(item)
    db.commit()
    return True


# =============================================================================
# Preferences
# =============================================================================

def get_preferences(db: Session) -> UserPreference:
    item = db.scalar(
        select(UserPreference)
        .order_by(UserPreference.id)
    )

    if item is None:
        item = UserPreference(
            python_target_pct=70,
            java_target_pct=30,
            interview_mode="Balanced",
            ai_provider="Local/Fallback",
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    return item


def update_preferences(
    db: Session,
    payload: PreferenceUpdate,
) -> UserPreference:
    if payload.python_target_pct + payload.java_target_pct != 100:
        raise ValueError(
            "Python and Java target percentages must total 100."
        )

    item = get_preferences(db)

    for key, value in payload.model_dump().items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


# =============================================================================
# Cloud roadmap
# =============================================================================

def list_cloud_roadmap(db: Session) -> list[CloudRoadmapProgress]:
    return list(
        db.scalars(
            select(CloudRoadmapProgress)
            .order_by(CloudRoadmapProgress.stage_number)
        ).all()
    )


def update_cloud_roadmap(
    db: Session,
    stage_id: int,
    payload: CloudRoadmapUpdate,
) -> Optional[CloudRoadmapProgress]:
    item = db.get(CloudRoadmapProgress, stage_id)

    if item is None:
        return None

    item.completed = payload.completed

    if payload.completed:
        item.completed_date = (
            payload.completed_date or date.today()
        )
    else:
        item.completed_date = None

    db.commit()
    db.refresh(item)
    return item


# =============================================================================
# Analytics
# =============================================================================

def get_analytics(db: Session) -> dict:
    summary = get_home_summary(db)

    return {
        "topics_total": summary["total_topics"],
        "topics_completed": summary["completed_topics"],
        "topics_completion_pct": summary["topic_completion_pct"],
        "leetcode_total": summary["total_leetcode"],
        "leetcode_solved": summary["solved_leetcode"],
        "leetcode_completion_pct": summary["leetcode_completion_pct"],
        "daily_total": summary["total_daily_tasks"],
        "daily_completed": summary["completed_daily_tasks"],
        "daily_completion_pct": summary["daily_completion_pct"],
        "cloud_total": summary["total_cloud_stages"],
        "cloud_completed": summary["completed_cloud_stages"],
        "cloud_completion_pct": summary["cloud_completion_pct"],
        "projects_total": summary["total_projects"],
        "projects_completed": summary["completed_projects"],
        "current_streak": summary["current_streak"],
    }

# =============================================================================
# FEATURE DATA SEEDING
# =============================================================================

DATA_DIR = Path(__file__).resolve().parent / "data"


def seed_feature_data(db: Session) -> None:
    """
    Seed the new Software + Cloud Engineer tracker tables.

    This function is intentionally idempotent:
    if a table already contains data, that table is not seeded again.

    Existing original tracker tables are never modified.
    """

    # ------------------------------------------------------------
    # Default preferences
    # ------------------------------------------------------------

    if db.scalar(
        select(UserPreference).where(UserPreference.id == 1)
    ) is None:
        db.add(
            UserPreference(
                id=1,
                python_target_pct=75,
                java_target_pct=25,
                interview_mode="Balanced",
                ai_provider="Local/Fallback",
            )
        )

    # ------------------------------------------------------------
    # Python + Java concepts
    # ------------------------------------------------------------

    if db.scalar(
        select(TopicProgress.id).limit(1)
    ) is None:

        concepts_file = DATA_DIR / "concepts.json"

        if concepts_file.exists():
            concepts = json.loads(
                concepts_file.read_text(encoding="utf-8")
            )

            for concept in concepts:
                concept_name = concept["concept"]

                for language in ("Python", "Java"):
                    db.add(
                        TopicProgress(
                            concept=concept_name,
                            language=language,
                            status="Not Started",
                        )
                    )

    # ------------------------------------------------------------
    # 30-day plan
    # ------------------------------------------------------------

    if db.scalar(
        select(DailyTask.id).limit(1)
    ) is None:

        plan_file = DATA_DIR / "plan_30_days.json"

        if plan_file.exists():
            plan = json.loads(
                plan_file.read_text(encoding="utf-8")
            )

            for item in plan:
                day_number = int(item["day_number"])

                db.add(
                    DailyTask(
                        day_number=day_number,
                        task_date=(
                            date.today()
                            + timedelta(days=day_number - 1)
                        ),
                        concept=item["concept"],
                        python_task=item.get(
                            "python_task",
                            "",
                        ),
                        java_task=item.get(
                            "java_task",
                            "",
                        ),
                        leetcode_task=item.get(
                            "leetcode_task",
                            "",
                        ),
                        ai_prompt=item.get(
                            "ai_prompt",
                            "",
                        ),
                        completed=False,
                        notes=item.get("notes"),
                    )
                )

    # ------------------------------------------------------------
    # Cloud Engineer roadmap
    # ------------------------------------------------------------

    if db.scalar(
        select(CloudRoadmapProgress.id).limit(1)
    ) is None:

        roadmap_file = DATA_DIR / "cloud_roadmap.json"

        if roadmap_file.exists():
            roadmap = json.loads(
                roadmap_file.read_text(encoding="utf-8")
            )

            for stage in roadmap:
                stage_number = int(stage["stage"])
                stage_title = stage["title"]
                description = stage.get("description")

                for topic in stage.get("topics", []):
                    db.add(
                        CloudRoadmapProgress(
                            stage_number=stage_number,
                            stage_title=stage_title,
                            topic=topic,
                            description=description,
                            completed=False,
                        )
                    )

    # ------------------------------------------------------------
    # AI prompt library
    # ------------------------------------------------------------

    if db.scalar(
        select(SavedPrompt.id).limit(1)
    ) is None:

        prompts_file = DATA_DIR / "prompts.json"

        if prompts_file.exists():
            prompts = json.loads(
                prompts_file.read_text(encoding="utf-8")
            )

            for prompt in prompts:
                db.add(
                    SavedPrompt(
                        title=prompt["title"],
                        category=prompt.get(
                            "category",
                            "Custom",
                        ),
                        content=prompt["content"],
                    )
                )

    # ------------------------------------------------------------
    # LeetCode starter problems
    # ------------------------------------------------------------

    if db.scalar(
        select(LeetCodeProblem.id).limit(1)
    ) is None:

        leetcode_file = DATA_DIR / "leetcode_seed.csv"

        if leetcode_file.exists():
            with leetcode_file.open(
                newline="",
                encoding="utf-8",
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:
                    db.add(
                        LeetCodeProblem(
                            number=int(row["number"]),
                            title=row["title"],
                            difficulty=row["difficulty"],
                            status="Not Started",
                            language="Python",
                            topic=row.get("topic"),
                            acceptance=(
                                row["acceptance"]
                                if row.get("acceptance")
                                else None
                            ),
                            frequency=(
                                row["frequency"]
                                if row.get("frequency")
                                else None
                            ),
                            date_added=date.today(),
                            revision_priority="Medium",
                            confidence=None,
                            revision_flag=False,
                            stage=row.get("stage") or "Foundation",
                        )
                    )

    db.commit()