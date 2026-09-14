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
    contact_persons: str
    status: str
    status_label: str
    status_date: str
    status_age: str
    title: str
    abstract: str
    organizer: str
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
            talk_by_monday[monday] = _calendar_talk(row, current_date)

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


def _calendar_talk(row: Mapping[Any, Any], current_date: datetime.date) -> CalendarTalk:
    speaker = str(row["speaker"]).strip()
    topic = row.get("topic")
    if topic not in TOPIC_COLORS:
        topic = "Other"

    return CalendarTalk(
        speaker=speaker,
        topic=str(topic),
        topic_class=TOPIC_COLORS[str(topic)],
        contact_persons=_format_contact_persons(row.get("contact_persons")),
        status=str(row.get("status", "")),
        status_label=_format_status_label(row.get("status")),
        status_date=_format_status_date(row.get("status_date")),
        status_age=_format_status_age(
            row.get("status"), row.get("status_date"), current_date
        ),
        title=str(row.get("title", "")),
        abstract=str(row.get("abstract", "")),
        organizer=str(row.get("organizer", "")),
        comments=str(row.get("comments", "")),
        is_unavailable=speaker == "",
    )


def _week_color_class(
    monday: datetime.date, talk: CalendarTalk | None, current_monday: datetime.date
) -> str:
    if talk is not None and talk.is_unavailable:
        return "unavailable-week"
    if talk is not None and talk.status.casefold() == "completed":
        return "completed-week"
    if talk is not None and talk.status.casefold() == "planned":
        return "planned-week"
    if talk is None and monday > current_monday:
        return "future-empty-week"
    return ""


def _format_contact_persons(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    return ", ".join(str(person) for person in value if str(person))


def _format_status_label(value: Any) -> str:
    label = str(value or "")
    if not label:
        return ""
    return label[:1].upper() + label[1:]


def _format_status_date(value: Any) -> str:
    date_value = _parse_date(value)
    if date_value is None:
        return ""
    return date_value.isoformat()


def _format_status_age(
    status: Any, value: Any, current_date: datetime.date
) -> str:
    if str(status).casefold() == "completed":
        return ""
    status_date = _parse_date(value)
    if status_date is None:
        return ""

    days = (current_date - status_date).days
    if days == 0:
        return "today"
    if days == 1:
        return "1 day ago"
    return f"{days} days ago"


def _parse_date(value: Any) -> datetime.date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))
