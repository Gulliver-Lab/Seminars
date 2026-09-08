import argparse
import datetime
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, Sequence, cast, get_args

import pandas as pd
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.templating import Jinja2Templates

from seminars.calendar import build_calendar_weeks
from seminars.db import (
    delete_speaker,
    delete_talk_for_week,
    insert_speaker,
    open_or_create_db,
    read_emails,
    read_speakers,
    read_talks,
    update_speaker,
    upsert_talk_for_week,
)
from seminars.models import PERSONS, ResearchTopic, Speaker

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")

COLUMNS = [
    ("name", "Name"),
    ("affiliation", "Affiliation"),
    ("last_talk", "Last talk"),
    ("topic", "Topic"),
    ("contact_persons", "Contact persons"),
    ("notes", "Notes"),
]
SORTABLE_COLUMNS = {key for key, _label in COLUMNS}
RESEARCH_TOPICS = list(get_args(ResearchTopic))
CONTACT_PERSON_OPTIONS = [person for person in get_args(PERSONS) if person]
CONFERENCE_ROOM_URL = "https://visio.numerique.gouv.fr/vuf-njri-opc"
WORDPRESS_ORIGIN = "https://blog.espci.fr"


def url_path_for(request: Request, endpoint_name: str, **path_params: str) -> str:
    root_path = request.scope.get("root_path", "").rstrip("/")
    route_path = str(request.app.url_path_for(endpoint_name, **path_params))
    return f"{root_path}{route_path}"


def build_app(
    db_path: str | Path,
    root_path: str = "",
    cors_origins: Sequence[str] = (WORDPRESS_ORIGIN,),
) -> FastAPI:
    app = FastAPI(title="Seminars", root_path=root_path)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_private_network=True,
    )
    database_path = Path(db_path)

    @app.middleware("http")
    async def add_frame_ancestor_policy(request: Request, call_next: Any) -> Response:
        response = cast(Response, await call_next(request))
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' " + " ".join(cors_origins)
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    def home_index(request: Request) -> Any:
        connection = open_or_create_db(database_path)
        try:
            talks = read_talks(connection)
            upcoming_talks = upcoming_confirmed_talks(talks, read_speakers(connection))
        finally:
            connection.close()

        return TEMPLATES.TemplateResponse(
            request,
            "home.html",
            {
                "conference_room_url": CONFERENCE_ROOM_URL,
                "next_talk": upcoming_talks[0] if upcoming_talks else None,
                "following_talks": upcoming_talks[1:3],
                "url_path_for": url_path_for,
            },
        )

    @app.get("/speakers", response_class=HTMLResponse)
    def speakers_index(
        request: Request, sort: str = "name", direction: str = "asc"
    ) -> Any:
        connection = open_or_create_db(database_path)
        try:
            talks = read_talks(connection)
            dataframe = speakers_with_last_talk(
                read_speakers(connection),
                talks,
            )
            dataframe = speakers_with_talks(dataframe, talks)
        finally:
            connection.close()

        dataframe = sort_speakers(dataframe, sort, direction)
        speakers = cast(list[dict[str, Any]], dataframe.to_dict("records"))
        active_sort = sort if sort in SORTABLE_COLUMNS else "name"
        active_direction = "desc" if direction == "desc" else "asc"

        return TEMPLATES.TemplateResponse(
            request,
            "speakers.html",
            {
                "columns": COLUMNS,
                "speakers": [_format_speaker(row) for row in speakers],
                "research_topics": RESEARCH_TOPICS,
                "contact_person_options": CONTACT_PERSON_OPTIONS,
                "visible_count": sum(
                    bool(speaker["want_to_invite"]) for speaker in speakers
                ),
                "active_sort": active_sort,
                "active_direction": active_direction,
                "url_path_for": url_path_for,
            },
        )

    @app.get("/calendar", response_class=HTMLResponse)
    def calendar_index(request: Request) -> Any:
        connection = open_or_create_db(database_path)
        try:
            talks = read_talks(connection)
            speakers = read_speakers(connection)
            emails = read_emails(connection)
            calendar_weeks = build_calendar_weeks(
                _talks_with_topics_and_last_email(talks, speakers, emails)
            )
            speaker_options = speakers["name"].sort_values().tolist()
        except ValueError as error:
            return PlainTextResponse(str(error), status_code=400)
        finally:
            connection.close()

        return TEMPLATES.TemplateResponse(
            request,
            "calendar.html",
            {
                "calendar_weeks": calendar_weeks,
                "speaker_options": speaker_options,
                "organizer_options": CONTACT_PERSON_OPTIONS,
                "url_path_for": url_path_for,
            },
        )

    @app.post("/calendar/weeks/{monday}")
    def update_calendar_week(
        request: Request,
        monday: str,
        speaker: str = Form(),
        status: str = Form(),
        title: str = Form(""),
        abstract: str = Form(""),
        organizer: str = Form(""),
    ) -> Response:
        try:
            monday_date = datetime.date.fromisoformat(monday)
            talk_status = _parse_calendar_talk_status(status)
            talk_organizer = _parse_organizer(organizer)
        except ValueError as error:
            return PlainTextResponse(str(error), status_code=400)

        connection = open_or_create_db(database_path)
        try:
            upsert_talk_for_week(
                connection,
                monday_date,
                speaker,
                talk_status,
                title,
                abstract,
                talk_organizer,
            )
        except sqlite3.IntegrityError as error:
            return PlainTextResponse(str(error), status_code=400)
        finally:
            connection.close()
        return RedirectResponse(
            url_path_for(request, "calendar_index"), status_code=303
        )

    @app.post("/calendar/weeks/{monday}/delete")
    def delete_calendar_week(request: Request, monday: str) -> Response:
        try:
            monday_date = datetime.date.fromisoformat(monday)
        except ValueError as error:
            return PlainTextResponse(str(error), status_code=400)

        connection = open_or_create_db(database_path)
        try:
            delete_talk_for_week(connection, monday_date)
        finally:
            connection.close()
        return RedirectResponse(
            url_path_for(request, "calendar_index"), status_code=303
        )

    @app.post("/speakers")
    def create_speaker(
        request: Request,
        name: str = Form(),
        affiliation: str = Form(""),
        email: str = Form(""),
        topic: str = Form(""),
        contact_persons: list[str] = Form([]),
        notes: str = Form(""),
        want_to_invite: str | None = Form(None),
    ) -> Response:
        try:
            speaker = _speaker_from_form(
                name, affiliation, email, topic, contact_persons, notes, want_to_invite
            )
        except ValueError as error:
            return PlainTextResponse(str(error), status_code=400)
        connection = open_or_create_db(database_path)
        try:
            insert_speaker(connection, speaker)
        finally:
            connection.close()
        return RedirectResponse(
            url_path_for(request, "speakers_index"), status_code=303
        )

    @app.post("/speakers/{original_name}")
    def edit_speaker(
        request: Request,
        original_name: str,
        name: str = Form(),
        affiliation: str = Form(""),
        email: str = Form(""),
        topic: str = Form(""),
        contact_persons: list[str] = Form([]),
        notes: str = Form(""),
        want_to_invite: str | None = Form(None),
    ) -> Response:
        try:
            speaker = _speaker_from_form(
                name, affiliation, email, topic, contact_persons, notes, want_to_invite
            )
        except ValueError as error:
            return PlainTextResponse(str(error), status_code=400)
        connection = open_or_create_db(database_path)
        try:
            update_speaker(connection, original_name, speaker)
        finally:
            connection.close()
        return RedirectResponse(
            url_path_for(request, "speakers_index"), status_code=303
        )

    @app.post("/speakers/{name}/delete")
    def remove_speaker(request: Request, name: str) -> Response:
        connection = open_or_create_db(database_path)
        try:
            delete_speaker(connection, name)
        except ValueError as error:
            return PlainTextResponse(str(error), status_code=409)
        finally:
            connection.close()
        return RedirectResponse(
            url_path_for(request, "speakers_index"), status_code=303
        )

    return app


def upcoming_confirmed_talks(
    talks: pd.DataFrame, speakers: pd.DataFrame, limit: int = 3
) -> list[dict[str, Any]]:
    if talks.empty:
        return []

    upcoming = talks[
        talks["status"].isin(["completed", "confirmed"])
        & (talks["date"].dt.date >= datetime.date.today())
    ].sort_values("date", kind="mergesort")
    if upcoming.empty:
        return []

    speaker_details = speakers[["name", "affiliation"]]
    upcoming = upcoming.merge(
        speaker_details,
        how="left",
        left_on="speaker",
        right_on="name",
    ).head(limit)

    upcoming["date"] = upcoming["date"].dt.strftime("%Y-%m-%d")
    upcoming["affiliation"] = upcoming["affiliation"].fillna("")
    return cast(list[dict[str, Any]], upcoming.to_dict("records"))


def next_upcoming_confirmed_talk(
    talks: pd.DataFrame, speakers: pd.DataFrame
) -> dict[str, Any] | None:
    upcoming_talks = upcoming_confirmed_talks(talks, speakers, limit=1)
    return upcoming_talks[0] if upcoming_talks else None


def speakers_with_last_talk(
    speakers: pd.DataFrame, talks: pd.DataFrame
) -> pd.DataFrame:
    if talks.empty:
        speakers = speakers.copy()
        speakers["last_talk"] = ""
        return speakers

    last_talks = talks.groupby("speaker")["date"].max().reset_index()
    last_talks.columns = ["speaker", "last_talk"]
    last_talks["last_talk"] = last_talks["last_talk"].dt.strftime("%Y-%m-%d")

    merged = speakers.merge(
        last_talks,
        how="left",
        left_on="name",
        right_on="speaker",
    )
    merged = merged.drop(columns=["speaker"])
    merged["last_talk"] = merged["last_talk"].fillna("")
    return merged


def sort_speakers(
    speakers: pd.DataFrame, sort: str = "name", direction: str = "asc"
) -> pd.DataFrame:
    sort_column = sort if sort in SORTABLE_COLUMNS else "name"
    ascending = direction != "desc"
    return speakers.sort_values(
        by=sort_column,
        ascending=ascending,
        kind="mergesort",
        na_position="last",
    )


def speakers_with_talks(speakers: pd.DataFrame, talks: pd.DataFrame) -> pd.DataFrame:
    speakers = speakers.copy()
    speakers["talks"] = [[] for _row in range(len(speakers))]
    if talks.empty:
        return speakers

    talks = talks.copy()
    talks["date"] = talks["date"].dt.strftime("%Y-%m-%d")
    talks = talks.sort_values("date", ascending=False, kind="mergesort")
    talks_by_speaker = {
        speaker: rows[["date", "title"]].to_dict("records")
        for speaker, rows in talks.groupby("speaker", sort=False)
    }
    speakers["talks"] = (
        speakers["name"]
        .map(talks_by_speaker)
        .map(lambda value: value if isinstance(value, list) else [])
    )
    return speakers


def _talks_with_topics_and_last_email(
    talks: pd.DataFrame,
    speakers: pd.DataFrame,
    emails: pd.DataFrame,
    current_date: datetime.date | None = None,
) -> pd.DataFrame:
    if talks.empty:
        talks = talks.copy()
        talks["topic"] = []
        talks["contact_persons"] = []
        talks["last_email"] = []
        return talks

    speaker_details = speakers[["name", "email", "topic", "contact_persons"]]
    merged = talks.merge(
        speaker_details,
        how="left",
        left_on="speaker",
        right_on="name",
    )
    merged["topic"] = merged["topic"].fillna("Other")
    merged["contact_persons"] = merged["contact_persons"].map(
        lambda value: value if isinstance(value, list) else []
    )
    merged["last_email"] = merged["email"].map(
        last_email_by_address(emails, current_date=current_date)
    )
    return merged.drop(columns=["name", "email"])


def last_email_by_address(
    emails: pd.DataFrame,
    current_date: datetime.date | None = None,
) -> Callable[[Any], str]:
    current_date = current_date or datetime.date.today()

    def format_last_email(address: Any) -> str:
        if emails.empty or not isinstance(address, str) or not address:
            return ""

        address = address.lower()
        matches = emails[
            emails["recipient"].str.lower().str.contains(address, regex=False, na=False)
        ]
        if matches.empty:
            return ""

        days = (current_date - matches["date"].max().date()).days
        unit = "day" if days == 1 else "days"
        return f"{days} {unit} ago"

    return format_last_email


def _format_speaker(row: dict[str, Any]) -> dict[str, Any]:
    contact_persons = row["contact_persons"]
    if isinstance(contact_persons, list):
        row["contact_persons"] = ", ".join(contact_persons)
    return row


def _speaker_from_form(
    name: str,
    affiliation: str,
    email: str,
    topic: str,
    contact_persons: Sequence[str],
    notes: str,
    want_to_invite: str | None,
) -> Speaker:
    return Speaker(
        name=name.title(),
        affiliation=affiliation,
        email=email,
        topic=_parse_research_topic(topic),
        contact_persons=_parse_contact_persons(contact_persons),
        notes=notes,
        want_to_invite=want_to_invite == "on",
    )


def _parse_research_topic(value: str) -> ResearchTopic:
    if value in RESEARCH_TOPICS:
        return cast(ResearchTopic, value)
    return "Other"


def _parse_contact_persons(value: Sequence[str]) -> list[PERSONS]:
    selected = [person.strip() for person in value if person.strip()]
    if not selected:
        return [""]

    allowed_persons = set(get_args(PERSONS))
    invalid_persons = [person for person in selected if person not in allowed_persons]
    if invalid_persons:
        raise ValueError(f"invalid contact persons: {', '.join(invalid_persons)}")

    deduplicated = list(dict.fromkeys(selected))
    return cast(list[PERSONS], deduplicated)


def _parse_calendar_talk_status(value: str) -> str:
    if value == "planned":
        return "planned"
    if value in {"completed", "complete", "confirmed"}:
        return "completed"
    raise ValueError("invalid talk status")


def _parse_organizer(value: str) -> PERSONS:
    organizer = value.strip()
    if organizer in get_args(PERSONS):
        return cast(PERSONS, organizer)
    raise ValueError("invalid organizer")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seminar web interface")
    parser.add_argument("--db_path", required=True, help="Path to sqlite database")
    parser.add_argument(
        "--root_path", required=False, help="Path prefix added by the proxy", default=""
    )
    parser.add_argument(
        "--cors_origin",
        action="append",
        default=[WORDPRESS_ORIGIN],
        help="Origin allowed to embed and access the app",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    uvicorn.run(
        build_app(args.db_path, args.root_path, args.cors_origin),
        host=args.host,
        port=args.port,
    )
