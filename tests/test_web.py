import datetime

from fastapi.testclient import TestClient

from seminars.db import (
    insert_speaker,
    insert_talk,
    open_or_create_db,
    read_speakers,
    read_talks,
)
from seminars.models import Speaker, Talk
from seminars.web import build_app, speakers_with_last_talk


def test_homepage_displays_speakers_table(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
            contact_persons=["Bob Example", "Carol Example"],
            notes="Available in spring",
            exclude=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "<table" in response.text
    assert "Alice Example" in response.text
    assert "Example University" in response.text
    assert "alice@example.edu" not in response.text
    assert "Bob Example, Carol Example" in response.text
    assert "Exclude" not in response.text


def test_speakers_with_last_talk_keeps_latest_talk_date_and_blank_missing(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            exclude=False,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="No Talk Example",
            affiliation="Example Institute",
            email="no-talk@example.edu",
            topic="",
            contact_persons=[],
            notes="",
            exclude=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2024, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Earlier talk",
            abstract="",
            status="done",
            comments="",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2025, 3, 20, 14, 30),
            speaker="Alice Example",
            title="Latest talk",
            abstract="",
            status="done",
            comments="",
        ),
    )

    dataframe = speakers_with_last_talk(
        read_speakers(connection), read_talks(connection)
    )

    assert dataframe[["name", "last_talk"]].to_dict("records") == [
        {"name": "Alice Example", "last_talk": "2025-03-20"},
        {"name": "No Talk Example", "last_talk": ""},
    ]


def test_homepage_displays_last_talk_date(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            exclude=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2025, 3, 20, 14, 30),
            speaker="Alice Example",
            title="Latest talk",
            abstract="",
            status="done",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "Last talk" in response.text
    assert "2025-03-20" in response.text
