import json
import sqlite3
from pathlib import Path

import pandas as pd

from seminars.models import Speaker, Talk

EXPECTED_SPEAKERS_SCHEMA = [
    ("name", "TEXT"),
    ("affiliation", "TEXT"),
    ("email", "TEXT"),
    ("topic", "TEXT"),
    ("contact_persons", "TEXT"),
    ("notes", "TEXT"),
    ("want_to_invite", "BOOLEAN"),
]

EXPECTED_TALKS_SCHEMA = [
    ("date", "TEXT"),
    ("speaker", "TEXT"),
    ("title", "TEXT"),
    ("abstract", "TEXT"),
    ("status", "TEXT"),
    ("comments", "TEXT"),
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
            want_to_invite
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            affiliation = excluded.affiliation,
            email = excluded.email,
            topic = excluded.topic,
            contact_persons = excluded.contact_persons,
            notes = excluded.notes,
            want_to_invite = excluded.want_to_invite
        """,
        (
            speaker.name,
            speaker.affiliation,
            speaker.email,
            speaker.topic,
            serialize_contact_persons(speaker.contact_persons),
            speaker.notes,
            speaker.want_to_invite,
        ),
    )
    connection.commit()


def update_speaker(
    connection: sqlite3.Connection, original_name: str, speaker: Speaker
) -> None:
    connection.execute(
        """
        UPDATE speakers
        SET
            name = ?,
            affiliation = ?,
            email = ?,
            topic = ?,
            contact_persons = ?,
            notes = ?,
            want_to_invite = ?
        WHERE name = ?
        """,
        (
            speaker.name,
            speaker.affiliation,
            speaker.email,
            speaker.topic,
            serialize_contact_persons(speaker.contact_persons),
            speaker.notes,
            speaker.want_to_invite,
            original_name,
        ),
    )
    connection.commit()


def delete_speaker(connection: sqlite3.Connection, name: str) -> None:
    talk_count = connection.execute(
        "SELECT COUNT(*) FROM talks WHERE speaker = ?",
        (name,),
    ).fetchone()[0]
    if talk_count:
        raise ValueError("speaker has talks")

    connection.execute("DELETE FROM speakers WHERE name = ?", (name,))
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


def insert_talk(connection: sqlite3.Connection, talk: Talk) -> None:
    connection.execute(
        """
        INSERT INTO talks (
            date,
            speaker,
            title,
            abstract,
            status,
            comments
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            talk.date.isoformat(),
            talk.speaker,
            talk.title,
            talk.abstract,
            talk.status,
            talk.comments,
        ),
    )
    connection.commit()


def read_talks(connection: sqlite3.Connection) -> pd.DataFrame:
    columns = [name for name, _type in EXPECTED_TALKS_SCHEMA]
    dataframe = pd.read_sql_query(
        f"SELECT {', '.join(columns)} FROM talks",
        connection,
    )
    dataframe["date"] = pd.to_datetime(dataframe["date"])
    return dataframe


def open_or_create_db(filepath: str | Path) -> sqlite3.Connection:
    path = Path(filepath)
    exists = path.exists()

    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    if not exists:
        _create_schema(connection)
    else:
        _migrate_schema(connection)

    return connection


def _migrate_schema(connection: sqlite3.Connection) -> None:
    speaker_columns = [
        row[1] for row in connection.execute("PRAGMA table_info(speakers)").fetchall()
    ]
    if "exclude" in speaker_columns and "want_to_invite" not in speaker_columns:
        connection.execute(
            "ALTER TABLE speakers RENAME COLUMN exclude TO want_to_invite"
        )
        connection.commit()


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
            want_to_invite BOOLEAN
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
    connection.commit()
