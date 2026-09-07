import argparse
from typing import Sequence

import seminars


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seminar tool")
    parser.add_argument("--db_path", required=True, help="Path to sqlite database")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    _ = seminars.open_or_create_db(args.db_path)
    print("Connection opened")
