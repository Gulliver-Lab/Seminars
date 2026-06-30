from seminars.db import (
    insert_speaker,
    insert_talk,
    open_or_create_db,
    read_speakers,
    read_talks,
)
from seminars.models import Speaker, Talk

__all__ = [
    "open_or_create_db",
    "Speaker",
    "Talk",
    "insert_speaker",
    "insert_talk",
    "read_speakers",
    "read_talks",
]
