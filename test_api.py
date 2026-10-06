"""Run from the directory that contains the devops_tracker/ package:  pytest devops_tracker/tests -q"""
from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from devops_tracker import services
from devops_tracker.database import Base, get_db
from devops_tracker.main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with factory() as s:
        services.seed_database(s)

    def override() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)          # not used as a context manager -> lifespan (real DB file) is skipped
    app.dependency_overrides.clear()


def test_seed_counts(client: TestClient) -> None:
    assert len(client.get("/api/v1/tasks").json()) == 105
    assert len(client.get("/api/v1/daily").json()) == 126
    assert len(client.get("/api/v1/weekly").json()["rows"]) == 18
    assert len(client.get("/api/v1/skills").json()["skills"]) == 20


def test_cycle_status_stamps_and_clears_completion_date(client: TestClient) -> None:
    assert client.post("/api/v1/tasks/1/cycle-status").json()["task"]["status"] == "In Progress"
    done = client.post("/api/v1/tasks/1/cycle-status").json()["task"]
    assert done["status"] == "Completed" and done["done_on"] is not None and done["tick"] == "\u2611"
    back = client.post("/api/v1/tasks/1/cycle-status").json()["task"]
    assert back["status"] == "Not Started" and back["done_on"] is None


def test_phase_complete_flag_on_last_setup_task(client: TestClient) -> None:
    setup = client.get("/api/v1/tasks", params={"phase_id": 0}).json()
    assert len(setup) == 7
    flags = [client.put(f"/api/v1/tasks/{t['id']}/status", json={"status": "Completed"}).json()["phase_complete"]
             for t in setup]
    assert flags[:-1] == [False] * 6 and flags[-1] is True


def test_pending_view_excludes_completed(client: TestClient) -> None:
    client.put("/api/v1/tasks/1/status", json={"status": "Completed"})
    pending = client.get("/api/v1/tasks", params={"view": "Pending Only"}).json()
    assert 1 not in {t["id"] for t in pending} and len(pending) == 104


def test_weekend_blocks_not_applicable(client: TestClient) -> None:
    sat = next(d for d in client.get("/api/v1/daily", params={"week": 1}).json() if d["day"] == "Sat")
    assert sat["block2"] == "-"
    assert client.post(f"/api/v1/daily/{sat['id']}/blocks/2/cycle").status_code == 400
    assert client.post(f"/api/v1/daily/{sat['id']}/blocks/1/cycle").json()["block1"] == "Done"


def test_day_percent_and_hours_validation(client: TestClient) -> None:
    mon = client.get("/api/v1/daily", params={"week": 1}).json()[0]
    r = client.patch(f"/api/v1/daily/{mon['id']}", json={"block1": "Done", "actual_hours": 2.5}).json()
    assert round(r["day_pct"], 3) == 0.333
    assert client.patch(f"/api/v1/daily/{mon['id']}", json={"actual_hours": 25}).status_code == 422


def test_job_defaults_and_overdue(client: TestClient) -> None:
    r = client.post("/api/v1/jobs", json={"company": "Acme", "applied_on": "2020-01-01"}).json()
    assert r["status"] == "Applied" and r["follow_up_on"] == "2020-01-08"
    assert r["follow_up_overdue"] is True and r["days_waiting"] > 0
    assert len(client.get("/api/v1/jobs", params={"overdue_only": True}).json()) == 1


def test_skill_latest_and_gap(client: TestClient) -> None:
    r = client.patch("/api/v1/skills/1", json={"wk1": 1, "wk9": 2}).json()
    assert r["latest"] == 2 and r["gap"] == "Need +1 to reach level 3"
    assert client.patch("/api/v1/skills/1", json={"wk18": 4}).status_code == 422


def test_settings_must_be_monday(client: TestClient) -> None:
    assert client.patch("/api/v1/settings", json={"start_date": "2026-10-06"}).status_code == 422
    assert client.patch("/api/v1/settings", json={"start_date": "2026-10-12"}).status_code == 200


def test_missing_records_are_404_and_rebuild_needs_confirm(client: TestClient) -> None:
    assert client.get("/api/v1/tasks/9999").status_code == 404
    assert client.post("/api/v1/admin/rebuild").status_code == 400
    assert client.post("/api/v1/admin/rebuild", params={"confirm": True}).status_code == 200


def test_dashboard_shape(client: TestClient) -> None:
    d = client.get("/api/v1/dashboard").json()
    assert d["overall"]["pct_done"] == 0 and len(d["phases"]) == 8 and len(d["next_up"]) == 5
    assert d["totals"]["total"] == 105 and len(d["snapshot"]) == 7
