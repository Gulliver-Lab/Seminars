import datetime

from fastapi.testclient import TestClient

from seminars.db import (
    insert_speaker,
    insert_talk,
    open_or_create_db,
    read_speakers,
    read_talks,
)
from seminars.models import Speaker, Talk
from seminars.web import (
    build_app,
    next_upcoming_confirmed_talk,
    speakers_with_last_talk,
)


def insert_test_speaker(connection, name: str) -> None:
    insert_speaker(
        connection,
        Speaker(
            name=name,
            affiliation="Example University",
            email="",
            topic="Other",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )


def test_homepage_displays_next_confirmed_talk(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_test_speaker(connection, "Alice Example")
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2099, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Future confirmed talk",
            abstract="Future abstract",
            status="completed",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "Next confirmed talk" in response.text
    assert "2099-01-15" in response.text
    assert "Alice Example" in response.text
    assert "Future confirmed talk" in response.text
    assert "Future abstract" in response.text
    assert "https://visio.numerique.gouv.fr/vuf-njri-opc" in response.text


def test_homepage_ignores_planned_talks(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_test_speaker(connection, "Alice Example")
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2099, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Planned talk",
            abstract="",
            status="planned",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "No upcoming confirmed talk." in response.text
    assert "Planned talk" not in response.text


def test_homepage_links_under_root_path(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path, root_path="/seminars"))

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/seminars/"' in response.text
    assert 'href="/seminars/speakers"' in response.text
    assert 'href="/seminars/calendar"' in response.text


def test_next_upcoming_confirmed_talk_keeps_nearest_confirmed(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_test_speaker(connection, "Later Example")
    insert_test_speaker(connection, "Nearest Example")
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2099, 1, 22, 14, 30),
            speaker="Later Example",
            title="Later talk",
            abstract="",
            status="completed",
            comments="",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2099, 1, 15, 14, 30),
            speaker="Nearest Example",
            title="Nearest talk",
            abstract="",
            status="completed",
            comments="",
        ),
    )

    next_talk = next_upcoming_confirmed_talk(read_talks(connection))
    connection.close()

    assert next_talk is not None
    assert next_talk["date"] == "2099-01-15"
    assert next_talk["speaker"] == "Nearest Example"
    assert next_talk["title"] == "Nearest talk"


def test_next_upcoming_confirmed_talk_accepts_legacy_confirmed_status(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_test_speaker(connection, "Alice Example")
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2099, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Legacy confirmed talk",
            abstract="",
            status="confirmed",
            comments="",
        ),
    )

    next_talk = next_upcoming_confirmed_talk(read_talks(connection))
    connection.close()

    assert next_talk is not None
    assert next_talk["title"] == "Legacy confirmed talk"


def test_speakers_page_displays_speakers_table(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example", "Carol Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert "<table" in response.text
    assert "Alice Example" in response.text
    assert "Example University" in response.text
    assert "<td>alice@example.edu</td>" not in response.text
    assert "Bob Example, Carol Example" in response.text
    assert "Sort Want to invite" not in response.text


def test_speakers_with_last_talk_keeps_latest_talk_date_and_blank_missing(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="No Talk Example",
            affiliation="Example Institute",
            email="no-talk@example.edu",
            topic="Other",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2024, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Earlier talk",
            abstract="",
            status="done",
            comments="",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2025, 3, 20, 14, 30),
            speaker="Alice Example",
            title="Latest talk",
            abstract="",
            status="done",
            comments="",
        ),
    )

    dataframe = speakers_with_last_talk(
        read_speakers(connection), read_talks(connection)
    )

    assert dataframe[["name", "last_talk"]].to_dict("records") == [
        {"name": "Alice Example", "last_talk": "2025-03-20"},
        {"name": "No Talk Example", "last_talk": ""},
    ]


def test_speakers_page_displays_last_talk_date(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2025, 3, 20, 14, 30),
            speaker="Alice Example",
            title="Latest talk",
            abstract="",
            status="done",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert "Last talk" in response.text
    assert "2025-03-20" in response.text


def test_speakers_page_sorts_speakers_by_column(tmp_path):
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
            name="Zoe Example",
            affiliation="Another University",
            email="zoe@example.edu",
            topic="Theory",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers?sort=name&direction=desc")

    assert response.status_code == 200
    assert response.text.index("Zoe Example") < response.text.index("Alice Example")


def test_speakers_page_displays_sort_links(tmp_path):
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
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert "?sort=name&amp;direction=asc" in response.text
    assert "?sort=name&amp;direction=desc" in response.text
    assert "?sort=last_talk&amp;direction=asc" in response.text
    assert "?sort=last_talk&amp;direction=desc" in response.text


def test_speakers_page_displays_name_search_controls(tmp_path):
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
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert 'id="speaker-search"' in response.text
    assert 'placeholder="Search names"' in response.text
    assert 'data-speaker-name="alice example"' in response.text
    assert 'id="visible-count"' in response.text


def test_speakers_page_displays_want_to_invite_filter(tmp_path):
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
            want_to_invite=True,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="Bob Example",
            affiliation="Example University",
            email="bob@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert 'id="want-to-invite-filter"' in response.text
    assert "checked" in response.text
    assert '<span id="visible-count">1</span>' in response.text
    assert 'data-want-to-invite="1"' in response.text
    assert 'data-want-to-invite="0"' in response.text


def test_speakers_page_links_to_home_and_calendar(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert 'href="/"' in response.text
    assert 'href="/calendar"' in response.text


def test_speakers_page_links_under_root_path(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path, root_path="/seminars"))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert 'href="/seminars/"' in response.text
    assert 'href="/seminars/calendar"' in response.text
    assert 'action="/seminars/speakers"' in response.text
    assert 'const editSpeakerPath = "/seminars/speakers/__name__";' in response.text
    assert (
        'const deleteSpeakerPath = "/seminars/speakers/__name__/delete";'
        in response.text
    )


def test_calendar_page_renders_week_rows(tmp_path):
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
    assert 'class="calendar-table"' in response.text
    assert '<th scope="col">Date</th>' in response.text
    assert '<th scope="col">Name</th>' in response.text
    assert '<th scope="col">Topic</th>' in response.text
    assert '<th scope="col">Contact person</th>' in response.text
    assert '<th scope="col">Organizer</th>' in response.text
    assert '<th scope="col">Title/Abstract</th>' in response.text
    assert "2026-06-29" in response.text
    assert "Alice Example" in response.text
    assert "Active Matter" in response.text


def test_calendar_page_links_under_root_path(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path, root_path="/seminars"))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert 'href="/seminars/"' in response.text
    assert (
        'const updateCalendarWeekPath = "/seminars/calendar/weeks/__monday__";'
        in response.text
    )
    assert (
        'const deleteCalendarWeekPath = "/seminars/calendar/weeks/__monday__/delete";'
        in response.text
    )


def test_calendar_page_uses_table_without_legend(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert "calendar-table" in response.text
    assert "calendar-grid" not in response.text
    assert "week-box" not in response.text
    assert "calendar-legend" not in response.text
    assert "Legend" not in response.text


def test_calendar_page_marks_current_week(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert "current-week" in response.text
    assert "data-current-week" in response.text


def test_calendar_page_keeps_header_sticky_and_centers_current_week(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert "position: sticky" in response.text
    assert "overflow-x: auto" not in response.text
    assert 'querySelector("[data-current-week]")' in response.text
    assert 'scrollIntoView({ block: "center", inline: "nearest" })' in response.text


def test_calendar_page_displays_comments_for_blank_speaker_talk(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="",
            affiliation="",
            email="",
            topic="Other",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 7, 6, 14, 30),
            speaker="",
            title="Blocked week",
            abstract="",
            status="completed",
            comments="Reserved for internal meeting",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert "Reserved for internal meeting" in response.text
    assert "unavailable-week" in response.text


def test_calendar_page_includes_week_color_classes(tmp_path):
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
            title="Completed talk",
            abstract="",
            status="completed",
            comments="",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 7, 13, 14, 30),
            speaker="Bob Example",
            title="Planned talk",
            abstract="",
            status="planned",
            comments="",
            organizer="David",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert "completed-week" in response.text
    assert "planned-week" in response.text
    assert "future-empty-week" in response.text


def test_calendar_page_shows_title_abstract_checkbox_for_completed_talks(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Missing Title",
            affiliation="Example University",
            email="missing@example.edu",
            topic="Active Matter",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_speaker(
        connection,
        Speaker(
            name="Ready Title",
            affiliation="Example University",
            email="ready@example.edu",
            topic="Theory",
            contact_persons=[],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 7, 6, 14, 30),
            speaker="Missing Title",
            title="",
            abstract="",
            status="completed",
            comments="",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 7, 13, 14, 30),
            speaker="Ready Title",
            title="A completed talk",
            abstract="",
            status="completed",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert '<th scope="col">Title/Abstract</th>' in response.text
    assert 'class="title-abstract-checkbox" checked disabled' in response.text
    assert 'class="title-abstract-checkbox" disabled' in response.text


def test_calendar_page_displays_contact_persons_for_planned_speaker(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Planned Speaker",
            affiliation="Example University",
            email="planned@example.edu",
            topic="Theory",
            contact_persons=["David", "Josh"],
            notes="",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 7, 13, 14, 30),
            speaker="Planned Speaker",
            title="Future talk",
            abstract="",
            status="planned",
            comments="",
            organizer="David",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert "Planned Speaker" in response.text
    assert "David, Josh" in response.text


def test_calendar_page_includes_week_edit_dialog(tmp_path):
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
            date=datetime.datetime(2026, 7, 13, 14, 30),
            speaker="Alice Example",
            title="Future talk",
            abstract="",
            status="planned",
            comments="",
            organizer="David",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/calendar")

    assert response.status_code == 200
    assert 'id="week-dialog"' in response.text
    assert 'data-week-monday="2026-07-13"' in response.text
    assert 'data-week-speaker="Alice Example"' in response.text
    assert 'data-week-status="planned"' in response.text
    assert 'data-week-title="Future talk"' in response.text
    assert 'data-week-abstract=""' in response.text
    assert 'data-week-organizer="David"' in response.text
    assert 'id="week-speaker-filter"' in response.text
    assert "Type a regex to filter speakers" in response.text
    assert 'id="week-speaker" name="speaker" required type="hidden"' in response.text
    assert 'id="week-speaker-results"' in response.text
    assert "speaker-result-list" in response.text
    assert 'new RegExp(filter, "i")' in response.text
    assert "renderSpeakerOptions" in response.text
    assert "selectSpeaker" in response.text
    assert "No matching speakers" in response.text
    assert '<option value="planned">Planned</option>' in response.text
    assert '<option value="completed">Already confirmed</option>' in response.text
    assert 'id="week-organizer" name="organizer"' in response.text
    assert '<option value="David">David</option>' in response.text
    assert "weekOrganizer.value = row.dataset.weekOrganizer" in response.text
    assert 'id="week-title" name="title"' in response.text
    assert 'id="week-abstract" name="abstract"' in response.text
    assert "weekTitle.value = row.dataset.weekTitle" in response.text
    assert "weekAbstract.value = row.dataset.weekAbstract" in response.text
    assert 'id="week-delete-button"' in response.text
    assert 'id="week-delete-form"' in response.text
    assert "weekDeleteForm.action" in response.text
    assert "weekDeleteButton.disabled" in response.text
    assert "openWeekDialog" in response.text


def test_post_calendar_week_inserts_talk(tmp_path):
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
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.post(
        "/calendar/weeks/2026-07-13",
        data={
            "speaker": "Alice Example",
            "status": "planned",
            "title": "Inserted title",
            "abstract": "Inserted abstract",
            "organizer": "David",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    connection = open_or_create_db(db_path)
    talks = read_talks(connection).to_dict("records")
    connection.close()
    assert len(talks) == 1
    assert talks[0]["date"] == datetime.datetime(2026, 7, 13, 14, 30)
    assert talks[0]["speaker"] == "Alice Example"
    assert talks[0]["status"] == "planned"
    assert talks[0]["title"] == "Inserted title"
    assert talks[0]["abstract"] == "Inserted abstract"
    assert talks[0]["comments"] == ""
    assert talks[0]["organizer"] == "David"


def test_post_calendar_week_redirects_under_root_path(tmp_path):
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
    connection.close()

    client = TestClient(build_app(db_path, root_path="/seminars"))

    response = client.post(
        "/calendar/weeks/2026-07-13",
        data={
            "speaker": "Alice Example",
            "status": "planned",
            "title": "",
            "abstract": "",
            "organizer": "David",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/seminars/calendar"


def test_post_calendar_week_updates_existing_talk(tmp_path):
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
            date=datetime.datetime(2026, 7, 15, 14, 30),
            speaker="Alice Example",
            title="Existing title",
            abstract="Existing abstract",
            status="planned",
            comments="Existing comments",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.post(
        "/calendar/weeks/2026-07-13",
        data={
            "speaker": "Bob Example",
            "status": "completed",
            "title": "Updated title",
            "abstract": "Updated abstract",
            "organizer": "Josh",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    connection = open_or_create_db(db_path)
    talks = read_talks(connection).to_dict("records")
    connection.close()
    assert len(talks) == 1
    assert talks[0]["date"] == datetime.datetime(2026, 7, 15, 14, 30)
    assert talks[0]["speaker"] == "Bob Example"
    assert talks[0]["status"] == "completed"
    assert talks[0]["title"] == "Updated title"
    assert talks[0]["abstract"] == "Updated abstract"
    assert talks[0]["comments"] == "Existing comments"
    assert talks[0]["organizer"] == "Josh"


def test_post_calendar_week_delete_removes_existing_talk(tmp_path):
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
            date=datetime.datetime(2026, 7, 15, 14, 30),
            speaker="Alice Example",
            title="Existing title",
            abstract="",
            status="planned",
            comments="",
        ),
    )
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.post(
        "/calendar/weeks/2026-07-13/delete",
        follow_redirects=False,
    )

    assert response.status_code == 303
    connection = open_or_create_db(db_path)
    talks = read_talks(connection).to_dict("records")
    connection.close()
    assert talks == []


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
    assert 'data-week-speaker="Alice Example"' in response.text
    assert 'data-week-speaker="Bob Example"' not in response.text


def test_speakers_page_displays_new_speaker_form(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()

    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert "New Speaker" in response.text
    assert 'id="new-speaker-modal"' in response.text
    assert 'action="/speakers"' in response.text
    assert '<select id="speaker-topic" name="topic">' in response.text
    assert '<option value="Active Matter">Active Matter</option>' in response.text
    assert '<option value="Theory">Theory</option>' in response.text
    assert '<option value="BioPhys">BioPhys</option>' in response.text
    assert '<option value="Soft Matter">Soft Matter</option>' in response.text
    assert '<option value="Other">Other</option>' in response.text
    assert 'id="speaker-contact-persons-input"' in response.text
    assert 'list="contact-person-options"' in response.text
    assert '<datalist id="contact-person-options">' in response.text
    assert 'id="speaker-contact-persons-tokens"' in response.text
    assert 'id="speaker-contact-persons-empty"' in response.text
    assert 'type="hidden"' in response.text
    assert 'id="edit-speaker-contact-persons-input"' in response.text
    assert 'id="edit-speaker-contact-persons-tokens"' in response.text


def test_post_speaker_creates_speaker(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post(
        "/speakers",
        data={
            "name": "New Speaker",
            "affiliation": "New University",
            "email": "new@example.edu",
            "topic": "BioPhys",
            "contact_persons": ["David", "Josh", "David"],
            "notes": "New notes",
            "want_to_invite": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/speakers"
    connection = open_or_create_db(db_path)
    dataframe = read_speakers(connection)
    connection.close()
    assert dataframe.to_dict("records") == [
        {
            "name": "New Speaker",
            "affiliation": "New University",
            "email": "new@example.edu",
            "topic": "BioPhys",
            "contact_persons": ["David", "Josh"],
            "notes": "New notes",
            "want_to_invite": 1,
        }
    ]


def test_post_speaker_redirects_under_root_path(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()
    client = TestClient(build_app(db_path, root_path="/seminars"))

    response = client.post(
        "/speakers",
        data={
            "name": "New Speaker",
            "affiliation": "New University",
            "email": "new@example.edu",
            "topic": "BioPhys",
            "notes": "New notes",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/seminars/speakers"


def test_post_speaker_creates_speaker_with_blank_contact_persons(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post(
        "/speakers",
        data={
            "name": "Blank Contact",
            "affiliation": "New University",
            "email": "blank@example.edu",
            "topic": "BioPhys",
            "notes": "New notes",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    connection = open_or_create_db(db_path)
    dataframe = read_speakers(connection)
    connection.close()
    assert dataframe.to_dict("records") == [
        {
            "name": "Blank Contact",
            "affiliation": "New University",
            "email": "blank@example.edu",
            "topic": "BioPhys",
            "contact_persons": [""],
            "notes": "New notes",
            "want_to_invite": 0,
        }
    ]


def test_post_speaker_rejects_invalid_contact_person(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post(
        "/speakers",
        data={
            "name": "Invalid Contact",
            "affiliation": "New University",
            "email": "invalid@example.edu",
            "topic": "BioPhys",
            "contact_persons": ["Not Allowed"],
            "notes": "New notes",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400


def test_speakers_page_displays_edit_speaker_data(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example", "Carol Example"],
            notes="Available in spring",
            want_to_invite=True,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2024, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Earlier talk",
            abstract="",
            status="done",
            comments="",
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2025, 3, 20, 14, 30),
            speaker="Alice Example",
            title="Latest talk",
            abstract="",
            status="done",
            comments="",
        ),
    )
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.get("/speakers")

    assert response.status_code == 200
    assert 'id="edit-speaker-modal"' in response.text
    assert 'data-edit-name="Alice Example"' in response.text
    assert 'data-edit-email="alice@example.edu"' in response.text
    assert 'data-edit-contact-persons="Bob Example, Carol Example"' in response.text
    assert 'data-edit-want-to-invite="1"' in response.text
    assert 'id="edit-speaker-talks"' in response.text
    assert 'id="delete-speaker-form"' in response.text
    assert 'id="delete-speaker-button"' in response.text
    assert response.text.index("Latest talk") < response.text.index("Earlier talk")


def test_post_speaker_edit_updates_speaker_and_cascades_talks(tmp_path):
    db_path = tmp_path / "seminars.db"
    connection = open_or_create_db(db_path)
    insert_speaker(
        connection,
        Speaker(
            name="Alice Example",
            affiliation="Example University",
            email="alice@example.edu",
            topic="Active Matter",
            contact_persons=["Bob Example"],
            notes="Available in spring",
            want_to_invite=False,
        ),
    )
    insert_talk(
        connection,
        Talk(
            date=datetime.datetime(2026, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Active Matter",
            abstract="An abstract",
            status="confirmed",
            comments="Bring projector",
        ),
    )
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post(
        "/speakers/Alice%20Example",
        data={
            "name": "Alice Updated",
            "affiliation": "Updated Institute",
            "email": "alice.updated@example.edu",
            "topic": "Soft Matter",
            "contact_persons": ["David"],
            "notes": "Updated notes",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/speakers"
    connection = open_or_create_db(db_path)
    speakers = read_speakers(connection).to_dict("records")
    talks = read_talks(connection).to_dict("records")
    connection.close()
    assert speakers == [
        {
            "name": "Alice Updated",
            "affiliation": "Updated Institute",
            "email": "alice.updated@example.edu",
            "topic": "Soft Matter",
            "contact_persons": ["David"],
            "notes": "Updated notes",
            "want_to_invite": 0,
        }
    ]
    assert talks[0]["speaker"] == "Alice Updated"


def test_post_speaker_delete_removes_speaker_without_talks(tmp_path):
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
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post("/speakers/Alice%20Example/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/speakers"
    connection = open_or_create_db(db_path)
    speakers = read_speakers(connection).to_dict("records")
    connection.close()
    assert speakers == []


def test_post_speaker_delete_rejects_speaker_with_talks(tmp_path):
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
            date=datetime.datetime(2026, 1, 15, 14, 30),
            speaker="Alice Example",
            title="Active Matter",
            abstract="",
            status="done",
            comments="",
        ),
    )
    connection.close()
    client = TestClient(build_app(db_path))

    response = client.post("/speakers/Alice%20Example/delete", follow_redirects=False)

    assert response.status_code == 409
    connection = open_or_create_db(db_path)
    speakers = read_speakers(connection).to_dict("records")
    connection.close()
    assert speakers[0]["name"] == "Alice Example"
