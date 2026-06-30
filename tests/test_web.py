from fastapi.testclient import TestClient

from seminars.db import insert_speaker, open_or_create_db
from seminars.models import Speaker
from seminars.web import build_app


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
    assert "alice@example.edu" in response.text
    assert "Bob Example, Carol Example" in response.text
