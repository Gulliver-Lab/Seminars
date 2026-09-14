import datetime
from collections.abc import Mapping
from typing import Any

import pandas as pd

STATUS_ORDER = {
    "invited": 1,
    "accepted": 2,
    "title requested": 3,
    "announced": 4,
    "completed": 5,
}


def should_alert(
    talk: Any | None,
    talk_date: datetime.date | datetime.datetime,
    current_date: datetime.date | None = None,
) -> bool:
    current_date = current_date or datetime.date.today()
    talk_day = talk_date.date() if isinstance(talk_date, datetime.datetime) else talk_date
    days_until_talk = (talk_day - current_date).days

    if talk is None or not _get_value(talk, "speaker"):
        return 0 < days_until_talk < 42

    status = str(_get_value(talk, "status")).casefold()
    status_rank = STATUS_ORDER.get(status, 0)

    if days_until_talk <= 7 and status_rank < STATUS_ORDER["announced"]:
        return True
    if days_until_talk <= 14 and status_rank < STATUS_ORDER["title requested"]:
        return True
    if days_until_talk < 42 and status_rank < STATUS_ORDER["invited"]:
        return True

    status_date = _parse_date(_get_value(talk, "status_date"))
    if status in {"invited", "title requested"} and status_date is not None:
        return (current_date - status_date).days > 6

    return False


def _get_value(talk: Any, name: str) -> Any:
    if isinstance(talk, Mapping):
        return talk.get(name, "")
    return getattr(talk, name, "")


def _parse_date(value: Any) -> datetime.date | None:
    if value is None or pd.isna(value):
        return None
    if str(value) == "":
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))
