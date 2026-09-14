import datetime
from collections.abc import Mapping
from typing import Any

import pandas as pd

from seminars.models import TalkStatus, parse_talk_status

STATUS_ORDER = {
    TalkStatus.INVITED: 1,
    TalkStatus.ACCEPTED: 2,
    TalkStatus.TITLE_REQUESTED: 3,
    TalkStatus.ANNOUNCED: 4,
    TalkStatus.COMPLETED: 5,
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

    status = parse_talk_status(_get_value(talk, "status"))
    status_rank = STATUS_ORDER[status]

    if days_until_talk <= 7 and status_rank < STATUS_ORDER[TalkStatus.ANNOUNCED]:
        return True
    if days_until_talk <= 14 and status_rank < STATUS_ORDER[TalkStatus.TITLE_REQUESTED]:
        return True
    if days_until_talk < 42 and status_rank < STATUS_ORDER[TalkStatus.INVITED]:
        return True

    status_date = _parse_date(_get_value(talk, "status_date"))
    if status in {TalkStatus.INVITED, TalkStatus.TITLE_REQUESTED} and status_date is not None:
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
