import datetime

import pandas as pd

from seminars.calendar import build_calendar_weeks


def test_build_calendar_weeks_lists_newest_monday_first():
    talks = pd.DataFrame(
        [
            {
                "date": datetime.datetime(2026, 6, 29, 14, 30),
                "speaker": "Past Speaker",
                "topic": "Theory",
                "status": "completed",
            },
            {
                "date": datetime.datetime(2026, 8, 3, 14, 30),
                "speaker": "Future Speaker",
                "topic": "Active Matter",
                "status": "planned",
            },
        ]
    )

    weeks = build_calendar_weeks(talks, current_date=datetime.date(2026, 7, 7))

    assert weeks[0].monday == "2027-01-04"
    assert weeks[-1].monday == "2026-06-29"
    assert [week.monday for week in weeks].index("2026-08-03") < [
        week.monday for week in weeks
    ].index("2026-06-29")


def test_build_calendar_weeks_extends_six_months_after_current_week():
    weeks = build_calendar_weeks(pd.DataFrame(), current_date=datetime.date(2026, 7, 7))

    assert weeks[0].monday == "2027-01-04"
    assert weeks[-1].monday == "2026-07-06"
    assert len(weeks) == 27


def test_build_calendar_weeks_marks_current_week():
    weeks = build_calendar_weeks(pd.DataFrame(), current_date=datetime.date(2026, 7, 7))

    current_weeks = [week for week in weeks if week.is_current]

    assert len(current_weeks) == 1
    assert current_weeks[0].monday == "2026-07-06"


def test_build_calendar_weeks_marks_blank_speaker_talk_as_unavailable():
    talks = pd.DataFrame(
        [
            {
                "date": datetime.datetime(2026, 7, 6, 14, 30),
                "speaker": "",
                "topic": "Other",
                "status": "planned",
                "comments": "Reserved for internal meeting",
            }
        ]
    )

    weeks = build_calendar_weeks(talks, current_date=datetime.date(2026, 7, 7))
    week = next(week for week in weeks if week.monday == "2026-07-06")

    assert week.talk is not None
    assert week.talk.is_unavailable
    assert week.talk.comments == "Reserved for internal meeting"
    assert week.color_class == "unavailable-week"


def test_build_calendar_weeks_colors_completed_and_planned_talks():
    talks = pd.DataFrame(
        [
            {
                "date": datetime.datetime(2026, 7, 6, 14, 30),
                "speaker": "Completed Speaker",
                "topic": "Other",
                "status": "completed",
                "comments": "",
            },
            {
                "date": datetime.datetime(2026, 7, 13, 14, 30),
                "speaker": "Planned Speaker",
                "topic": "Other",
                "status": "planned",
                "comments": "",
            },
        ]
    )

    weeks = build_calendar_weeks(talks, current_date=datetime.date(2026, 7, 7))
    weeks_by_monday = {week.monday: week for week in weeks}

    assert weeks_by_monday["2026-07-06"].color_class == "completed-week"
    assert weeks_by_monday["2026-07-13"].color_class == "planned-week"


def test_build_calendar_weeks_colors_empty_future_weeks():
    weeks = build_calendar_weeks(pd.DataFrame(), current_date=datetime.date(2026, 7, 7))
    weeks_by_monday = {week.monday: week for week in weeks}

    assert weeks_by_monday["2026-07-13"].color_class == "future-empty-week"
    assert weeks_by_monday["2026-07-06"].color_class == ""


def test_build_calendar_weeks_marks_completed_talks_with_title_abstract():
    talks = pd.DataFrame(
        [
            {
                "date": datetime.datetime(2026, 7, 6, 14, 30),
                "speaker": "Missing Title",
                "topic": "Other",
                "status": "completed",
                "title": "",
                "comments": "",
            },
            {
                "date": datetime.datetime(2026, 7, 13, 14, 30),
                "speaker": "Ready Title",
                "topic": "Other",
                "status": "completed",
                "title": "A completed talk",
                "comments": "",
            },
        ]
    )

    weeks = build_calendar_weeks(talks, current_date=datetime.date(2026, 7, 7))
    weeks_by_monday = {week.monday: week for week in weeks}

    assert weeks_by_monday["2026-07-06"].talk is not None
    assert not weeks_by_monday["2026-07-06"].talk.has_title_abstract
    assert weeks_by_monday["2026-07-13"].talk is not None
    assert weeks_by_monday["2026-07-13"].talk.has_title_abstract
