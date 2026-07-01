import argparse
from pathlib import Path
from typing import Any, Sequence, cast

import pandas as pd
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.templating import Jinja2Templates

from seminars.db import (
    delete_speaker,
    insert_speaker,
    open_or_create_db,
    read_speakers,
    read_talks,
    update_speaker,
)
from seminars.models import Speaker

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


def build_app(db_path: str | Path) -> FastAPI:
    app = FastAPI(title="Seminars")
    database_path = Path(db_path)

    @app.get("/", response_class=HTMLResponse)
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
                "active_sort": active_sort,
                "active_direction": active_direction,
            },
        )

    @app.post("/speakers")
    def create_speaker(
        name: str = Form(),
        affiliation: str = Form(""),
        email: str = Form(""),
        topic: str = Form(""),
        contact_persons: str = Form(""),
        notes: str = Form(""),
        want_to_invite: str | None = Form(None),
    ) -> RedirectResponse:
        speaker = _speaker_from_form(
            name, affiliation, email, topic, contact_persons, notes, want_to_invite
        )
        connection = open_or_create_db(database_path)
        try:
            insert_speaker(connection, speaker)
        finally:
            connection.close()
        return RedirectResponse("/", status_code=303)

    @app.post("/speakers/{original_name}")
    def edit_speaker(
        original_name: str,
        name: str = Form(),
        affiliation: str = Form(""),
        email: str = Form(""),
        topic: str = Form(""),
        contact_persons: str = Form(""),
        notes: str = Form(""),
        want_to_invite: str | None = Form(None),
    ) -> RedirectResponse:
        speaker = _speaker_from_form(
            name, affiliation, email, topic, contact_persons, notes, want_to_invite
        )
        connection = open_or_create_db(database_path)
        try:
            update_speaker(connection, original_name, speaker)
        finally:
            connection.close()
        return RedirectResponse("/", status_code=303)

    @app.post("/speakers/{name}/delete")
    def remove_speaker(name: str) -> Response:
        connection = open_or_create_db(database_path)
        try:
            delete_speaker(connection, name)
        except ValueError as error:
            return PlainTextResponse(str(error), status_code=409)
        finally:
            connection.close()
        return RedirectResponse("/", status_code=303)

    return app


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
    contact_persons: str,
    notes: str,
    want_to_invite: str | None,
) -> Speaker:
    return Speaker(
        name=name.title(),
        affiliation=affiliation,
        email=email,
        topic=topic,
        contact_persons=_parse_contact_persons(contact_persons),
        notes=notes,
        want_to_invite=want_to_invite == "on",
    )


def _parse_contact_persons(value: str) -> list[str]:
    return [person.strip() for person in value.split(",") if person.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seminar web interface")
    parser.add_argument("--db_path", required=True, help="Path to sqlite database")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    uvicorn.run(build_app(args.db_path), host=args.host, port=args.port)
