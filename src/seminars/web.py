import argparse
from pathlib import Path
from typing import Any, Sequence, cast

import pandas as pd
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from seminars.db import open_or_create_db, read_speakers, read_talks

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")


def build_app(db_path: str | Path) -> FastAPI:
    app = FastAPI(title="Seminars")
    database_path = Path(db_path)

    @app.get("/", response_class=HTMLResponse)
    def speakers_index(request: Request) -> Any:
        connection = open_or_create_db(database_path)
        try:
            dataframe = speakers_with_last_talk(
                read_speakers(connection),
                read_talks(connection),
            )
        finally:
            connection.close()

        speakers = cast(list[dict[str, Any]], dataframe.to_dict("records"))

        return TEMPLATES.TemplateResponse(
            request,
            "speakers.html",
            {
                "columns": [
                    ("name", "Name"),
                    ("affiliation", "Affiliation"),
                    ("email", "Email"),
                    ("last_talk", "Last talk"),
                    ("topic", "Topic"),
                    ("contact_persons", "Contact persons"),
                    ("notes", "Notes"),
                    ("exclude", "Exclude"),
                ],
                "speakers": [_format_speaker(row) for row in speakers],
            },
        )

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


def _format_speaker(row: dict[str, Any]) -> dict[str, Any]:
    contact_persons = row["contact_persons"]
    if isinstance(contact_persons, list):
        row["contact_persons"] = ", ".join(contact_persons)
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seminar web interface")
    parser.add_argument("--db_path", required=True, help="Path to sqlite database")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    uvicorn.run(build_app(args.db_path), host=args.host, port=args.port)
