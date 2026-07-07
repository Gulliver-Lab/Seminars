# Calendar Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a calendar page that shows one week per box, labels each box with the Monday date, displays the speaker and topic for weeks with talks, and uses a color legend for research topics.

**Architecture:** Keep the database unchanged and derive the calendar entirely from the existing talks table. Build a small pure helper layer for weekly grouping and topic-color assignment, then render that data in a dedicated Jinja template. Link the new page from the existing site so users can switch between the speaker table and the calendar quickly.

**Tech Stack:** FastAPI, Jinja2, pandas, vanilla JavaScript, pytest

---

### Task 1: Add failing calendar tests

**Files:**
- Modify: `tests/test_web.py`

- [ ] **Step 1: Write the failing test**

```python
def test_calendar_page_renders_week_boxes(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 6, 29, 14, 30),
            speaker="Alice Example",
            title="Weekly talk",
            abstract="",
            status="completed",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))
    response = client.get("/calendar")

    assert response.status_code == 200
    assert "Calendar" in response.text
    assert "2026-06-29" in response.text
    assert "Alice Example" in response.text
    assert "Active Matter" in response.text
```

```python
def test_calendar_page_includes_legend(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))
    response = client.get("/calendar")

    assert response.status_code == 200
    assert "Legend" in response.text
    assert "Active Matter" in response.text
    assert "Theory" in response.text
    assert "BioPhys" in response.text
    assert "Soft Matter" in response.text
    assert "Other" in response.text
```

```python
def test_calendar_page_displays_one_talk_when_multiple_talks_share_week(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="Bob Example",
            affiliation="Example University",
            email="bob@example.edu",
            topic="Theory",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 6, 29, 14, 30),
            speaker="Alice Example",
            title="First talk",
            abstract="",
            status="completed",
            comments="",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 7, 1, 14, 30),
            speaker="Bob Example",
            title="Second talk",
            abstract="",
            status="completed",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))
    response = client.get("/calendar")

    assert response.status_code == 200
    assert "Alice Example" in response.text
    assert "Bob Example" not in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_web.py -v`
Expected: FAIL because `/calendar` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Not applicable yet.

- [ ] **Step 4: Run test to verify it passes**

Not applicable yet.

- [ ] **Step 5: Commit**

Do not commit unless the user approves it.

### Task 2: Add calendar data helpers and route

**Files:**
- Create: `src/seminars/calendar.py`
- Modify: `src/seminars/web.py`
- Modify: `src/seminars/models.py` only if a small calendar-specific type alias is needed

- [ ] **Step 1: Write the failing test**

Use the tests from Task 1 to force the route and grouping behavior.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_web.py::test_calendar_page_renders_week_boxes -v`
Expected: FAIL until the route and calendar grouping exist.

- [ ] **Step 3: Write minimal implementation**

```python
import dataclasses
import datetime

import pandas as pd

TOPIC_COLORS = {
    "Active Matter": "topic-active-matter",
    "Theory": "topic-theory",
    "BioPhys": "topic-biophys",
    "Soft Matter": "topic-soft-matter",
    "Other": "topic-other",
}


@dataclasses.dataclass
class CalendarWeek:
    monday: str
    talk: dict[str, str] | None
```

```python
def monday_of_week(value: datetime.datetime) -> datetime.date:
    return value.date() - datetime.timedelta(days=value.weekday())


def build_calendar_weeks(talks: pd.DataFrame) -> list[CalendarWeek]:
    talk_rows = talks.sort_values("date").to_dict("records")
    talk_by_monday: dict[datetime.date, dict[str, str]] = {}

    for row in talk_rows:
        monday = monday_of_week(row["date"])
        if monday in talk_by_monday:
            continue
        talk_by_monday[monday] = {
            "speaker": row["speaker"],
            "topic": row["topic"],
            "topic_class": TOPIC_COLORS[row["topic"]],
        }

    if talk_by_monday:
        first_monday = min(talk_by_monday)
    else:
        first_monday = monday_of_week(datetime.datetime.now())

    current_monday = monday_of_week(datetime.datetime.now())
    last_monday = max(
        max(talk_by_monday, default=current_monday),
        current_monday + datetime.timedelta(weeks=26),
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
```

```python
@app.get("/calendar", response_class=HTMLResponse)
def calendar_index(request: Request) -> Any:
    connection = open_or_create_db(database_path)
    try:
        talks = read_talks(connection)
        calendar_weeks = build_calendar_weeks(talks)
    except ValueError as error:
        return PlainTextResponse(str(error), status_code=400)
    finally:
        connection.close()

    return TEMPLATES.TemplateResponse(
        request,
        "calendar.html",
        {
            "calendar_weeks": calendar_weeks,
            "research_topics": RESEARCH_TOPICS,
            "topic_colors": TOPIC_COLORS,
        },
    )
```

Choose a date range that includes:
- the first talk week,
- the current week,
- a six-month forward window so upcoming empty weeks are visible.

Represent each week with:
- Monday date,
- optional speaker name,
- optional topic,
- optional topic color class.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_web.py::test_calendar_page_renders_week_boxes -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Do not commit unless the user approves it.

### Task 3: Build the calendar template and topic legend

**Files:**
- Create: `src/seminars/templates/calendar.html`
- Modify: `src/seminars/templates/speakers.html` if you add a visible link to the calendar page

- [ ] **Step 1: Write the failing test**

Use the legend test from Task 1 to force the template structure.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_web.py::test_calendar_page_includes_legend -v`
Expected: FAIL until the template renders the legend.

- [ ] **Step 3: Write minimal implementation**

```html
<main class="calendar-page">
  <section class="calendar-grid">
    {% for week in calendar_weeks %}
      <article class="week-box">
        <div class="week-date">{{ week.monday }}</div>
        {% if week.talk %}
          <div class="talk-speaker">{{ week.talk.speaker }}</div>
          <div class="talk-topic">
            <span class="topic-dot {{ week.talk.topic_class }}"></span>
            <span>{{ week.talk.topic }}</span>
          </div>
        {% endif %}
      </article>
    {% endfor %}
  </section>

  <aside class="calendar-legend">
    <h2>Legend</h2>
    {% for topic, color_class in topic_colors.items() %}
      <div class="legend-item">
        <span class="topic-dot {{ color_class }}"></span>
        <span>{{ topic }}</span>
      </div>
    {% endfor %}
  </aside>
</main>
```

Use CSS grid for the main layout and large week boxes so the page reads like a wall calendar, not a table.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_web.py::test_calendar_page_includes_legend -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Do not commit unless the user approves it.

### Task 4: Add navigation and verify the full suite

**Files:**
- Modify: `src/seminars/templates/speakers.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Write the failing test**

```python
def test_homepage_links_to_calendar(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))
    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/calendar"' in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_web.py::test_homepage_links_to_calendar -v`
Expected: FAIL until the link exists.

- [ ] **Step 3: Write minimal implementation**

Add a top-level link or button near the existing toolbar:

```html
<a class="button" href="/calendar">Calendar</a>
```

- [ ] **Step 4: Run the full test suite**

Run: `uv run pytest tests/`
Expected: PASS.

- [ ] **Step 5: Commit**

Do not commit unless the user approves it.
