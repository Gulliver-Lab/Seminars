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
class CalendarTalk:
    speaker: str
    topic: str
    topic_class: str
    status: str
    has_title_abstract: bool
    comments: str
    is_unavailable: bool


@dataclasses.dataclass
class CalendarWeek:
    monday: str
    talk: CalendarTalk | None
    is_current: bool
    color_class: str


def monday_of_week(value: datetime.datetime) -> datetime.date:
    return value.date() - datetime.timedelta(days=value.weekday())


def build_calendar_weeks(
    talks: pd.DataFrame, current_date: datetime.date | None = None
) -> list[CalendarWeek]:
    current_date = current_date or datetime.datetime.now().date()
    current_monday = current_date - datetime.timedelta(days=current_date.weekday())
    talk_by_monday: dict[datetime.date, CalendarTalk] = {}

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
        talk = talk_by_monday.get(monday)
        weeks.append(
            CalendarWeek(
                monday=monday.isoformat(),
                talk=talk,
                is_current=monday == current_monday,
                color_class=_week_color_class(monday, talk, current_monday),
            )
        )
        monday += datetime.timedelta(weeks=1)

    return list(reversed(weeks))


def _calendar_talk(row: Mapping[Any, Any]) -> CalendarTalk:
    speaker = str(row["speaker"]).strip()
    topic = row.get("topic")
    if topic not in TOPIC_COLORS:
        topic = "Other"

    return CalendarTalk(
        speaker=speaker,
        topic=str(topic),
        topic_class=TOPIC_COLORS[str(topic)],
        status=str(row.get("status", "")),
        has_title_abstract=bool(str(row.get("title", "")).strip()),
        comments=str(row.get("comments", "")),
        is_unavailable=speaker == "",
    )


def _week_color_class(
    monday: datetime.date, talk: CalendarTalk | None, current_monday: datetime.date
) -> str:
    if talk is not None and talk.is_unavailable:
        return "unavailable-week"
    if talk is not None and talk.status == "completed":
        return "completed-week"
    if talk is not None and talk.status == "planned":
        return "planned-week"
    if talk is None and monday > current_monday:
        return "future-empty-week"
    return ""
