import dataclasses
import datetime
from collections.abc import Mapping
from typing import Any

import pandas as pd

TOPIC_COLORS = {
    "Active Matter": "topic-active-matter",
    "Theory": "topic-theory",
    "BioPhys": "topic-biophys",
    "Soft Matter": "topic-soft-matter",
    "Other": "topic-other",
}
FUTURE_WEEKS = 26


@dataclasses.dataclass
class CalendarWeek:
    monday: str
    talk: dict[str, str] | None


def monday_of_week(value: datetime.datetime) -> datetime.date:
    return value.date() - datetime.timedelta(days=value.weekday())


def build_calendar_weeks(
    talks: pd.DataFrame, current_date: datetime.date | None = None
) -> list[CalendarWeek]:
    current_date = current_date or datetime.datetime.now().date()
    current_monday = current_date - datetime.timedelta(days=current_date.weekday())
    talk_by_monday: dict[datetime.date, dict[str, str]] = {}

    if not talks.empty:
        for row in talks.sort_values("date").to_dict("records"):
            monday = monday_of_week(row["date"])
            if monday in talk_by_monday:
                continue
            talk_by_monday[monday] = _calendar_talk(row)

    first_monday = min(talk_by_monday, default=current_monday)
    last_monday = max(
        max(talk_by_monday, default=current_monday),
        current_monday + datetime.timedelta(weeks=FUTURE_WEEKS),
    )

    weeks: list[CalendarWeek] = []
    monday = first_monday
    while monday <= last_monday:
        weeks.append(
            CalendarWeek(
                monday=monday.isoformat(),
                talk=talk_by_monday.get(monday),
            )
        )
        monday += datetime.timedelta(weeks=1)

    return list(reversed(weeks))


def _calendar_talk(row: Mapping[Any, Any]) -> dict[str, str]:
    topic = row.get("topic")
    if topic not in TOPIC_COLORS:
        topic = "Other"

    return {
        "speaker": str(row["speaker"]),
        "topic": str(topic),
        "topic_class": TOPIC_COLORS[str(topic)],
    }
