import argparse
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Seminar tool")
    parser.add_argument("--db_path", required=True, help="Path to sqlite database")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print("Path to file:", args.db_path)
