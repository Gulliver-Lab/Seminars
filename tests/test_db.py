import datetime
import json
import sqlite3

import pytest

from seminars.db import (
    _create_schema,
    delete_speaker,
    deserialize_contact_persons,
    insert_speaker,
    insert_talk,
    open_or_create_db,
    read_speakers,
    read_talks,
    serialize_contact_persons,
    update_speaker,
)
from seminars.models import Speaker, Talk


def test_serializes_and_deserializes_contact_persons():
    value = ["Alice Example", "Bob Example"]

    encoded = serialize_contact_persons(value)

    assert json.loads(encoded) == value
    assert deserialize_contact_persons(encoded) == value

    with pytest.raises(ValueError):
        serialize_contact_persons("Alice Example")


def test_inserts_speaker():
    connection = sqlite3.connect(":memory:")
    _create_schema(connection)

    speaker = Speaker(
        name="Alice Example",
        affiliation="Example University",
        email="alice@example.edu",
        topic="Quantum seminars",
        contact_persons=["Bob Example", "Carol Example"],
        notes="Available in spring",
        want_to_invite=False,
    )

    insert_speaker(connection, speaker)

    row = connection.execute(
        """
        SELECT name, affiliation, email, topic, contact_persons, notes, want_to_invite
        FROM speakers
        """
    ).fetchone()
    assert row == (
        "Alice Example",
        "Example University",
        "alice@example.edu",
        "Quantum seminars",
        '["Bob Example", "Carol Example"]',
        "Available in spring",
        0,
    )


def test_insert_speaker_updates_existing_speaker_with_same_name():
    connection = sqlite3.connect(":memory:")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
            contact_persons=["Bob Example", "Carol Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )

    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Updated Institute",
            email="alice.updated@example.edu",
            topic="Updated topic",
            contact_persons=["Dana Example"],
            notes="Updated notes",
            want_to_invite=True,
        ),
    )

    rows = connection.execute(
        """
        SELECT name, affiliation, email, topic, contact_persons, notes, want_to_invite
        FROM speakers
        """
    ).fetchall()
    assert rows == [
        (
            "Alice Example",
            "Updated Institute",
            "alice.updated@example.edu",
            "Updated topic",
            '["Dana Example"]',
            "Updated notes",
            1,
        )
    ]


def test_update_speaker_updates_existing_row():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )

    update_speaker(
        connection,
        "Alice Example",
        Speaker(
            name="Alice Updated",
            affiliation="Updated Institute",
            email="alice.updated@example.edu",
            topic="Updated topic",
            contact_persons=["Carol Example"],
            notes="Updated notes",
            want_to_invite=True,
        ),
    )

    rows = connection.execute(
        """
        SELECT name, affiliation, email, topic, contact_persons, notes, want_to_invite
        FROM speakers
        """
    ).fetchall()
    assert rows == [
        (
            "Alice Updated",
            "Updated Institute",
            "alice.updated@example.edu",
            "Updated topic",
            '["Carol Example"]',
            "Updated notes",
            1,
        )
    ]


def test_update_speaker_name_cascades_to_talks():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
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
            title="Quantum seminars",
            abstract="An abstract",
            status="confirmed",
            comments="Bring projector",
        ),
    )

    update_speaker(
        connection,
        "Alice Example",
        Speaker(
            name="Alice Updated",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )

    talk_speakers = connection.execute("SELECT speaker FROM talks").fetchall()
    assert talk_speakers == [("Alice Updated",)]


def test_delete_speaker_removes_speaker_without_talks():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )

    delete_speaker(connection, "Alice Example")

    assert connection.execute("SELECT name FROM speakers").fetchall() == []


def test_delete_speaker_rejects_speaker_with_talks():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
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
            title="Quantum seminars",
            abstract="An abstract",
            status="confirmed",
            comments="Bring projector",
        ),
    )

    with pytest.raises(ValueError, match="speaker has talks"):
        delete_speaker(connection, "Alice Example")

    assert connection.execute("SELECT name FROM speakers").fetchall() == [
        ("Alice Example",)
    ]


def test_reads_speakers_as_dataframe():
    connection = sqlite3.connect(":memory:")
    _create_schema(connection)
    speaker = Speaker(
        name="Alice Example",
        affiliation="Example University",
        email="alice@example.edu",
        topic="Quantum seminars",
        contact_persons=["Bob Example", "Carol Example"],
        notes="Available in spring",
        want_to_invite=False,
    )
    insert_speaker(connection, speaker)

    dataframe = read_speakers(connection)

    assert list(dataframe.columns) == [
        "name",
        "affiliation",
        "email",
        "topic",
        "contact_persons",
        "notes",
        "want_to_invite",
    ]
    assert dataframe.to_dict("records") == [
        {
            "name": "Alice Example",
            "affiliation": "Example University",
            "email": "alice@example.edu",
            "topic": "Quantum seminars",
            "contact_persons": ["Bob Example", "Carol Example"],
            "notes": "Available in spring",
            "want_to_invite": 0,
        }
    ]


def test_open_or_create_db_creates_schema_for_missing_file(tmp_path):
    filepath = tmp_path / "seminars.db"

    connection = open_or_create_db(filepath)

    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    assert tables == [("speakers",), ("talks",)]


def test_open_or_create_db_renames_existing_exclude_column(tmp_path):
    filepath = tmp_path / "seminars.db"
    connection = sqlite3.connect(filepath)
    connection.execute(
        """
        CREATE TABLE speakers (
            name TEXT PRIMARY KEY,
            affiliation TEXT,
            email TEXT,
            topic TEXT,
            contact_persons TEXT,
            notes TEXT,
            exclude BOOLEAN
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE talks (
            date TEXT,
            speaker TEXT,
            title TEXT,
            abstract TEXT,
            status TEXT,
            comments TEXT,
            FOREIGN KEY (speaker) REFERENCES speakers(name) ON UPDATE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO speakers (
            name,
            affiliation,
            email,
            topic,
            contact_persons,
            notes,
            exclude
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Alice Example",
            "Example University",
            "alice@example.edu",
            "Quantum seminars",
            '["Bob Example"]',
            "Available in spring",
            1,
        ),
    )
    connection.commit()
    connection.close()

    connection = open_or_create_db(filepath)

    columns = [
        row[1] for row in connection.execute("PRAGMA table_info(speakers)").fetchall()
    ]
    assert "exclude" not in columns
    assert "want_to_invite" in columns
    assert read_speakers(connection).to_dict("records") == [
        {
            "name": "Alice Example",
            "affiliation": "Example University",
            "email": "alice@example.edu",
            "topic": "Quantum seminars",
            "contact_persons": ["Bob Example"],
            "notes": "Available in spring",
            "want_to_invite": 1,
        }
    ]


def test_inserts_talk():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
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
            title="Quantum seminars",
            abstract="An abstract",
            status="confirmed",
            comments="Bring projector",
        ),
    )

    row = connection.execute(
        """
        SELECT date, speaker, title, abstract, status, comments
        FROM talks
        """
    ).fetchone()
    assert row == (
        "2026-01-15T14:30:00",
        "Alice Example",
        "Quantum seminars",
        "An abstract",
        "confirmed",
        "Bring projector",
    )


def test_insert_talk_rejects_unknown_speaker():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)

    with pytest.raises(sqlite3.IntegrityError):
        insert_talk(
            connection,
            Talk(
                date=datetime.datetime(2026, 1, 15, 14, 30),
                speaker="Missing Speaker",
                title="Quantum seminars",
                abstract="An abstract",
                status="confirmed",
                comments="Bring projector",
            ),
        )


def test_insert_talk_allows_multiple_talks_with_same_date():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
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
            title="Quantum seminars",
            abstract="An abstract",
            status="confirmed",
            comments="Bring projector",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Updated title",
            abstract="Updated abstract",
            status="tentative",
            comments="Updated comments",
        ),
    )

    rows = connection.execute(
        """
        SELECT date, speaker, title, abstract, status, comments
        FROM talks
        """
    ).fetchall()
    assert rows == [
        (
            "2026-01-15T14:30:00",
            "Alice Example",
            "Quantum seminars",
            "An abstract",
            "confirmed",
            "Bring projector",
        ),
        (
            "2026-01-15T14:30:00",
            "Alice Example",
            "Updated title",
            "Updated abstract",
            "tentative",
            "Updated comments",
        ),
    ]


def test_reads_talks_as_dataframe():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    _create_schema(connection)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Quantum seminars",
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
            title="Quantum seminars",
            abstract="An abstract",
            status="confirmed",
            comments="Bring projector",
        ),
    )

    dataframe = read_talks(connection)

    assert list(dataframe.columns) == [
        "date",
        "speaker",
        "title",
        "abstract",
        "status",
        "comments",
    ]
    assert dataframe.to_dict("records") == [
        {
            "date": datetime.datetime(2026, 1, 15, 14, 30),
            "speaker": "Alice Example",
            "title": "Quantum seminars",
            "abstract": "An abstract",
            "status": "confirmed",
            "comments": "Bring projector",
        }
    ]
