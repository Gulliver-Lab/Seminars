from argparse import ArgumentParser
from csv import DictReader
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from xml.dom import minidom
from xml.etree.ElementTree import Element, ElementTree, SubElement, register_namespace

DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        return list(DictReader(handle))


def format_rss_date(value: str) -> str:
    parsed = datetime.strptime(value, "%d/%m/%y").replace(tzinfo=timezone.utc)
    return parsed.replace(hour=9).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_feed(rows: list[dict[str, str]], title: str) -> Element:
    register_namespace("dc", DC_NAMESPACE)
    rss = Element("rss", attrib={"version": "2.0"})
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = title
    SubElement(channel, "link").text = ""
    SubElement(channel, "description").text = title

    for row in rows:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = row["title"]
        SubElement(item, "link").text = ""
        SubElement(item, f"{{{DC_NAMESPACE}}}date").text = format_rss_date(row["date"])
        SubElement(item, "description").text = row["content"]

    return rss


def write_feed(feed: Element, output_path: Path) -> None:
    buffer = BytesIO()
    ElementTree(feed).write(buffer, encoding="utf-8", xml_declaration=True)
    pretty = minidom.parseString(buffer.getvalue()).toprettyxml(
        indent="  ",
        newl="\r\n",
        encoding="utf-8",
    )
    output_path.write_bytes(pretty)


def main(csv_path: str | Path) -> None:
    csv_path = Path(csv_path)
    rows = read_rows(csv_path)
    feed = build_feed(rows, csv_path.stem)
    write_feed(feed, Path.cwd() / "feed.xml")


def cli() -> None:
    parser = ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    main(args.csv_path)


if __name__ == "__main__":
    cli()
