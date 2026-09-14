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
                "contact_persons": [],
            },
            {
                "date": datetime.datetime(2026, 8, 3, 14, 30),
                "speaker": "Future Speaker",
                "topic": "Active Matter",
                "status": "planned",
                "contact_persons": [],
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
                "contact_persons": [],
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
                "contact_persons": [],
            },
            {
                "date": datetime.datetime(2026, 7, 13, 14, 30),
                "speaker": "Planned Speaker",
                "topic": "Other",
                "status": "planned",
                "comments": "",
                "contact_persons": [],
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


def test_build_calendar_weeks_formats_status_age():
    talks = pd.DataFrame(
        [
            {
                "date": datetime.datetime(2026, 7, 6, 14, 30),
                "speaker": "Recent Status",
                "topic": "Other",
                "status": "accepted",
                "status_date": datetime.datetime(2026, 7, 6, 9, 0),
                "title": "",
                "comments": "",
                "contact_persons": [],
            },
            {
                "date": datetime.datetime(2026, 7, 13, 14, 30),
                "speaker": "Older Status",
                "topic": "Other",
                "status": "title requested",
                "status_date": datetime.datetime(2026, 7, 1, 9, 0),
                "title": "A completed talk",
                "comments": "",
                "contact_persons": [],
            },
        ]
    )

    weeks = build_calendar_weeks(talks, current_date=datetime.date(2026, 7, 7))
    weeks_by_monday = {week.monday: week for week in weeks}

    assert weeks_by_monday["2026-07-06"].talk is not None
    assert weeks_by_monday["2026-07-06"].talk.status_label == "Accepted"
    assert weeks_by_monday["2026-07-06"].talk.status_age == "1 day ago"
    assert weeks_by_monday["2026-07-13"].talk is not None
    assert weeks_by_monday["2026-07-13"].talk.status_label == "Title requested"
    assert weeks_by_monday["2026-07-13"].talk.status_age == "6 days ago"


def test_build_calendar_weeks_hides_status_age_for_completed_talks():
    talks = pd.DataFrame(
        [
            {
                "date": datetime.datetime(2026, 7, 6, 14, 30),
                "speaker": "Completed Status",
                "topic": "Other",
                "status": "completed",
                "status_date": datetime.datetime(2026, 7, 1, 9, 0),
                "comments": "",
                "contact_persons": [],
            },
        ]
    )

    weeks = build_calendar_weeks(talks, current_date=datetime.date(2026, 7, 7))
    week = next(week for week in weeks if week.monday == "2026-07-06")

    assert week.talk is not None
    assert week.talk.status_label == "Completed"
    assert week.talk.status_age == ""


def test_build_calendar_weeks_formats_contact_persons_for_planned_speaker():
    talks = pd.DataFrame(
        [
            {
                "date": datetime.datetime(2026, 7, 13, 14, 30),
                "speaker": "Planned Speaker",
                "topic": "Other",
                "status": "planned",
                "title": "",
                "comments": "",
                "contact_persons": ["David", "Josh"],
            }
        ]
    )

    weeks = build_calendar_weeks(talks, current_date=datetime.date(2026, 7, 7))
    week = next(week for week in weeks if week.monday == "2026-07-13")

    assert week.talk is not None
    assert week.talk.contact_persons == "David, Josh"
