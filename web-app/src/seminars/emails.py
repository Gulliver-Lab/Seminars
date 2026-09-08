import argparse
from typing import Sequence

from seminars import fetch_emails, insert_email, open_or_create_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse emails for seminars")
    parser.add_argument("--db_path", required=True, help="Path to sqlite database")
    parser.add_argument(
        "--credentials_path", required=True, help="Path to credential json"
    )
    parser.add_argument("--token_path", required=True, help="Path to token json")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    connection = open_or_create_db(args.db_path)

    emails = fetch_emails(args.credentials_path, args.token_path)
    for email in emails:
        insert_email(connection, email)
