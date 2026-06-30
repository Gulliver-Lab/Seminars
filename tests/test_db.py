import datetime
import json
import sqlite3

import pytest

from seminars.db import (
    _create_schema,
    deserialize_contact_persons,
    insert_speaker,
    insert_talk,
    open_or_create_db,
    read_speakers,
    read_talks,
    serialize_contact_persons,
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
        exclude=False,
    )

    insert_speaker(connection, speaker)

    row = connection.execute(
        """
        SELECT name, affiliation, email, topic, contact_persons, notes, exclude
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
            exclude=False,
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
            exclude=True,
        ),
    )

    rows = connection.execute(
        """
        SELECT name, affiliation, email, topic, contact_persons, notes, exclude
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
        exclude=False,
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
        "exclude",
    ]
    assert dataframe.to_dict("records") == [
        {
            "name": "Alice Example",
            "affiliation": "Example University",
            "email": "alice@example.edu",
            "topic": "Quantum seminars",
            "contact_persons": ["Bob Example", "Carol Example"],
            "notes": "Available in spring",
            "exclude": 0,
        }
    ]


def test_open_or_create_db_creates_schema_for_missing_file(tmp_path):
    filepath = tmp_path / "seminars.db"

    connection = open_or_create_db(filepath)

    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    assert tables == [("speakers",), ("talks",)]


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
            exclude=False,
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


def test_insert_talk_updates_existing_talk_with_same_date():
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
            exclude=False,
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
            "Updated title",
            "Updated abstract",
            "tentative",
            "Updated comments",
        )
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
            exclude=False,
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
