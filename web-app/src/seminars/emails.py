import argparse
from typing import Sequence

from seminars.gmail import fetch_emails


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
    emails = fetch_emails(args.credentials_path, args.token_path)
    for email in emails:
        print(email)
