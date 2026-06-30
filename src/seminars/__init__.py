from seminars.db import insert_speaker, open_or_create_db, read_speakers
from seminars.models import Speaker

__all__ = ["open_or_create_db", "Speaker", "insert_speaker", "read_speakers"]
