import json
import sqlite3
from pathlib import Path

import pandas as pd

from seminars.models import Speaker

EXPECTED_SPEAKERS_SCHEMA = [
    ("name", "TEXT"),
    ("affiliation", "TEXT"),
    ("email", "TEXT"),
    ("topic", "TEXT"),
    ("contact_persons", "TEXT"),
    ("notes", "TEXT"),
    ("exclude", "BOOLEAN"),
]


def serialize_contact_persons(contact_persons: list[str]) -> str:
    if not isinstance(contact_persons, list) or not all(
        isinstance(person, str) for person in contact_persons
    ):
        raise ValueError("contact_person must be a list of strings")
    return json.dumps(contact_persons)


def deserialize_contact_persons(value: str | None) -> list[str] | None:
    if value is None:
        return None

    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(
        isinstance(person, str) for person in parsed
    ):
        raise ValueError("contact_person must be a JSON list of strings")
    return parsed


def insert_speaker(connection: sqlite3.Connection, speaker: Speaker) -> None:
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
        ON CONFLICT(name) DO UPDATE SET
            affiliation = excluded.affiliation,
            email = excluded.email,
            topic = excluded.topic,
            contact_persons = excluded.contact_persons,
            notes = excluded.notes,
            exclude = excluded.exclude
        """,
        (
            speaker.name,
            speaker.affiliation,
            speaker.email,
            speaker.topic,
            serialize_contact_persons(speaker.contact_persons),
            speaker.notes,
            speaker.exclude,
        ),
    )
    connection.commit()


def read_speakers(connection: sqlite3.Connection) -> pd.DataFrame:
    columns = [name for name, _type in EXPECTED_SPEAKERS_SCHEMA]
    dataframe = pd.read_sql_query(
        f"SELECT {', '.join(columns)} FROM speakers",
        connection,
    )
    dataframe["contact_persons"] = dataframe["contact_persons"].map(
        deserialize_contact_persons
    )
    return dataframe


def open_or_create_db(filepath: str | Path) -> sqlite3.Connection:
    path = Path(filepath)

    connection = sqlite3.connect(path)
    if not path.exists():
        _create_schema(connection)

    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
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
    connection.commit()
