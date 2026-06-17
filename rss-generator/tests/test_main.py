from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from xml.etree import ElementTree as ET

from rss_generator.main import main


class MainTest(TestCase):
    def test_main_writes_feed_xml(self):
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            csv_path = tmp_path / "seminars.csv"
            csv_path.write_text(
                "title,date,content\n"
                + (
                    "François Villemot (Gulliver),18/06/26,"
                    "Practical LLM Use in Everyday Research\n"
                ),
                encoding="utf-8",
            )

            with patch("pathlib.Path.cwd", return_value=tmp_path):
                main(csv_path)

            root = ET.parse(tmp_path / "feed.xml").getroot()
            item = root.find("channel/item")

            self.assertIsNotNone(item)
            self.assertEqual(item.findtext("title"), "François Villemot (Gulliver)")
            self.assertEqual(
                item.findtext("{http://purl.org/dc/elements/1.1/}date"),
                "18/06/26",
            )
            self.assertIsNotNone(item.find("link"))
            self.assertEqual(
                item.findtext("description"),
                "Practical LLM Use in Everyday Research",
            )
