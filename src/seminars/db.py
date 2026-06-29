import sqlite3
from pathlib import Path

EXPECTED_SPEAKERS_SCHEMA = [
    ("name", "TEXT"),
    ("affiliation", "TEXT"),
    ("email", "TEXT"),
    ("topic", "TEXT"),
    ("contact_person", "TEXT"),
    ("notes", "TEXT"),
    ("exclude", "BOOLEAN"),
]


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
            name TEXT,
            affiliation TEXT,
            email TEXT,
            topic TEXT,
            contact_person TEXT,
            notes TEXT,
            exclude BOOLEAN
        )
        """
    )
    connection.commit()
