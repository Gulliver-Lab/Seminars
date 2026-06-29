import json
import sqlite3

import pytest

from seminars.db import (
    _create_schema,
    deserialize_contact_persons,
    insert_speaker,
    read_speakers,
    serialize_contact_persons,
)
from seminars.models import Speaker


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
