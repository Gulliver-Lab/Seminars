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
            topic="Active Matter",
            contact_persons=["Bob Example", "Carol Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "<table" in response.text
    assert "Alice Example" in response.text
    assert "Example University" in response.text
    assert "<td>alice@example.edu</td>" not in response.text
    assert "Bob Example, Carol Example" in response.text
    assert "Sort Want to invite" not in response.text


def test_speakers_with_last_talk_keeps_latest_talk_date_and_blank_missing(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="No Talk Example",
            affiliation="Example Institute",
            email="no-talk@example.edu",
            topic="Other",
            contact_persons=[],
            notes="",
            want_to_invite=False,
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
            topic="Active Matter",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
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


def test_homepage_sorts_speakers_by_column(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="Zoe Example",
            affiliation="Another University",
            email="zoe@example.edu",
            topic="Theory",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/?sort=name&direction=desc")

    assert response.status_code == 200
    assert response.text.index("Zoe Example") < response.text.index("Alice Example")


def test_homepage_displays_sort_links(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "?sort=name&amp;direction=asc" in response.text
    assert "?sort=name&amp;direction=desc" in response.text
    assert "?sort=last_talk&amp;direction=asc" in response.text
    assert "?sort=last_talk&amp;direction=desc" in response.text


def test_homepage_displays_name_search_controls(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="speaker-search"' in response.text
    assert 'placeholder="Search names"' in response.text
    assert 'data-speaker-name="alice example"' in response.text
    assert 'id="visible-count"' in response.text


def test_homepage_displays_want_to_invite_filter(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=True,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="Bob Example",
            affiliation="Example University",
            email="bob@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="want-to-invite-filter"' in response.text
    assert "checked" in response.text
    assert '<span id="visible-count">1</span>' in response.text
    assert 'data-want-to-invite="1"' in response.text
    assert 'data-want-to-invite="0"' in response.text


def test_homepage_displays_new_speaker_form(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "New Speaker" in response.text
    assert 'id="new-speaker-modal"' in response.text
    assert 'action="/speakers"' in response.text
    assert '<select id="speaker-topic" name="topic">' in response.text
    assert '<option value="Active Matter">Active Matter</option>' in response.text
    assert '<option value="Theory">Theory</option>' in response.text
    assert '<option value="BioPhys">BioPhys</option>' in response.text
    assert '<option value="Soft Matter">Soft Matter</option>' in response.text
    assert '<option value="Other">Other</option>' in response.text
    assert 'name="contact_persons"' in response.text


def test_post_speaker_creates_speaker(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post(
        "/speakers",
        data={
            "name": "New Speaker",
            "affiliation": "New University",
            "email": "new@example.edu",
            "topic": "BioPhys",
            "contact_persons": "Alice Example, Bob Example",
            "notes": "New notes",
            "want_to_invite": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    connection = open_or_create_db(db_path)
    dataframe = read_speakers(connection)
    connection.close()
    assert dataframe.to_dict("records") == [
        {
            "name": "New Speaker",
            "affiliation": "New University",
            "email": "new@example.edu",
            "topic": "BioPhys",
            "contact_persons": ["Alice Example", "Bob Example"],
            "notes": "New notes",
            "want_to_invite": 1,
        }
    ]


def test_homepage_displays_edit_speaker_data(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example", "Carol Example"],
            notes="Available in spring",
            want_to_invite=True,
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
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="edit-speaker-modal"' in response.text
    assert 'data-edit-name="Alice Example"' in response.text
    assert 'data-edit-email="alice@example.edu"' in response.text
    assert 'data-edit-contact-persons="Bob Example, Carol Example"' in response.text
    assert 'data-edit-want-to-invite="1"' in response.text
    assert 'id="edit-speaker-talks"' in response.text
    assert 'id="delete-speaker-form"' in response.text
    assert 'id="delete-speaker-button"' in response.text
    assert response.text.index("Latest talk") < response.text.index("Earlier talk")


def test_post_speaker_edit_updates_speaker_and_cascades_talks(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Active Matter",
            abstract="An abstract",
            status="confirmed",
            comments="Bring projector",
        ),
    )
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post(
        "/speakers/Alice%20Example",
        data={
            "name": "Alice Updated",
            "affiliation": "Updated Institute",
            "email": "alice.updated@example.edu",
            "topic": "Soft Matter",
            "contact_persons": "Carol Example",
            "notes": "Updated notes",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    connection = open_or_create_db(db_path)
    speakers = read_speakers(connection).to_dict("records")
    talks = read_talks(connection).to_dict("records")
    connection.close()
    assert speakers == [
        {
            "name": "Alice Updated",
            "affiliation": "Updated Institute",
            "email": "alice.updated@example.edu",
            "topic": "Soft Matter",
            "contact_persons": ["Carol Example"],
            "notes": "Updated notes",
            "want_to_invite": 0,
        }
    ]
    assert talks[0]["speaker"] == "Alice Updated"


def test_post_speaker_delete_removes_speaker_without_talks(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post("/speakers/Alice%20Example/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    connection = open_or_create_db(db_path)
    speakers = read_speakers(connection).to_dict("records")
    connection.close()
    assert speakers == []


def test_post_speaker_delete_rejects_speaker_with_talks(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Active Matter",
            abstract="",
            status="done",
            comments="",
        ),
    )
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post("/speakers/Alice%20Example/delete", follow_redirects=False)

    assert response.status_code == 409
    connection = open_or_create_db(db_path)
    speakers = read_speakers(connection).to_dict("records")
    connection.close()
    assert speakers[0]["name"] == "Alice Example"
