"""Integration tests for the FastAPI web scorebook API."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from baseball_scorebook.web.api import create_app


def _team_payload(name: str) -> dict[str, object]:
    positions = ["8", "4", "6", "3", "9", "5", "7", "2", "1"]
    return {
        "name": name,
        "lineup": [
            {
                "battingOrder": index + 1,
                "playerName": f"{name} Player {index + 1}",
                "playerNumber": index + 10,
                "position": positions[index],
            }
            for index in range(9)
        ],
    }


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr("baseball_scorebook.web.api.get_default_save_dir", lambda: tmp_path)
    app = create_app()
    return TestClient(app)


def test_create_game_and_commit_at_bat(client: TestClient) -> None:
    response = client.post(
        "/api/games",
        json={
            "awayTeam": _team_payload("Away"),
            "homeTeam": _team_payload("Home"),
        },
    )
    response.raise_for_status()
    snapshot = response.json()
    session_id = snapshot["sessionId"]

    draft = client.post(
        f"/api/games/{session_id}/drafts/at-bat",
        json={"resultType": "SINGLE"},
    )
    draft.raise_for_status()
    assert draft.json()["batterDestination"] == "FIRST"

    commit = client.post(
        f"/api/games/{session_id}/commands/at-bat",
        json={
            "resultType": "SINGLE",
            "outsOnPlay": 0,
            "batterDestination": "FIRST",
            "runnerAdvances": [],
            "rbiCount": 0,
            "notes": "",
        },
    )
    commit.raise_for_status()
    updated = commit.json()

    assert updated["effectiveEventCount"] == 1
    assert updated["state"]["currentHalf"] == "TOP"
    assert updated["state"]["currentBatter"]["battingOrder"] == 2
    assert updated["state"]["runners"][0]["base"] == "FIRST"
    assert updated["scorecards"]["away"]["rows"][0]["cells"][0]["resultDisplay"] == "1B"


def test_undo_and_redo_round_trip(client: TestClient) -> None:
    snapshot = client.post(
        "/api/games",
        json={"awayTeam": _team_payload("Away"), "homeTeam": _team_payload("Home")},
    ).json()
    session_id = snapshot["sessionId"]

    client.post(
        f"/api/games/{session_id}/commands/at-bat",
        json={
            "resultType": "GROUND_OUT",
            "outsOnPlay": 1,
            "runnerAdvances": [],
            "rbiCount": 0,
            "notes": "",
        },
    ).raise_for_status()

    undone = client.post(f"/api/games/{session_id}/undo")
    undone.raise_for_status()
    assert undone.json()["effectiveEventCount"] == 0

    redone = client.post(f"/api/games/{session_id}/redo")
    redone.raise_for_status()
    assert redone.json()["effectiveEventCount"] == 1
    assert redone.json()["state"]["outs"] == 1


def test_substitution_updates_live_lineup_snapshot(client: TestClient) -> None:
    snapshot = client.post(
        "/api/games",
        json={"awayTeam": _team_payload("Away"), "homeTeam": _team_payload("Home")},
    ).json()
    session_id = snapshot["sessionId"]

    response = client.post(
        f"/api/games/{session_id}/commands/substitution",
        json={
            "team": "TOP",
            "battingOrder": 1,
            "enteringName": "Pinch Hitter",
            "enteringNumber": 99,
            "newPosition": "10",
            "subType": "PINCH_HIT",
        },
    )
    response.raise_for_status()
    updated = response.json()

    assert updated["teams"]["away"]["lineup"][0]["playerName"] == "Pinch Hitter"
    assert updated["teams"]["away"]["lineup"][0]["enteredInning"] == 1


def test_save_and_load_game_round_trip(client: TestClient) -> None:
    snapshot = client.post(
        "/api/games",
        json={"awayTeam": _team_payload("Away"), "homeTeam": _team_payload("Home")},
    ).json()
    session_id = snapshot["sessionId"]

    client.post(
        f"/api/games/{session_id}/commands/at-bat",
        json={
            "resultType": "DOUBLE",
            "outsOnPlay": 0,
            "batterDestination": "SECOND",
            "runnerAdvances": [],
            "rbiCount": 0,
            "notes": "gap shot",
        },
    ).raise_for_status()

    saved = client.post(f"/api/games/{session_id}/save", json={"filename": "test-save.json"})
    saved.raise_for_status()
    assert saved.json()["filename"] == "test-save.json"

    listed = client.get("/api/games/saved")
    listed.raise_for_status()
    assert listed.json()["items"][0]["filename"] == "test-save.json"

    loaded = client.post("/api/games/load", json={"filename": "test-save.json"})
    loaded.raise_for_status()
    restored = loaded.json()

    assert restored["state"]["runners"][0]["base"] == "SECOND"
    assert restored["gameLog"][0]["text"].endswith("[gap shot]")
