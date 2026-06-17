from xml.etree import ElementTree as ET

from rss_generator.main import main


def test_main_writes_feed_xml(tmp_path, monkeypatch):
    csv_path = tmp_path / "seminars.csv"
    csv_path.write_text(
        "title,date,content\n"
        + (
            "François Villemot (Gulliver),18/06/26,"
            "Practical LLM Use in Everyday Research\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    main(csv_path)

    root = ET.parse(tmp_path / "feed.xml").getroot()
    item = root.find("channel/item")
    feed_xml = (tmp_path / "feed.xml").read_bytes()

    assert item is not None
    assert item.findtext("title") == "François Villemot (Gulliver)"
    assert item.findtext("{http://purl.org/dc/elements/1.1/}date") == "18/06/26"
    assert item.find("link") is not None
    assert item.findtext("description") == "Practical LLM Use in Everyday Research"
    assert b"\r\n" in feed_xml
