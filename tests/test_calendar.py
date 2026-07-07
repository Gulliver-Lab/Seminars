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
            },
            {
                "date": datetime.datetime(2026, 8, 3, 14, 30),
                "speaker": "Future Speaker",
                "topic": "Active Matter",
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
