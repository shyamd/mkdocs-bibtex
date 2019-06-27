import unittest
import os
from os.path import join

from mkdocs_bibtex import BibTexPlugin
from mkdocs.config.base import Config

from pybtex.database import parse_file

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = BibTexPlugin()
        self.fake_config = Config([])
        self.fake_config.config_file_path = test_files_dir
        self.fake_config["bib_file"] = os.path.join(test_files_dir, "single.bib")

    def test_config_one_bibtex_file(self):
        self.plugin.on_config(self.fake_config)
        self.assertEqual(len(self.plugin.bib_data.entries), 1)

    def test_config_one_bibtex_dir(self):
        plugin = BibTexPlugin()
        fake_config = Config([])
        fake_config.config_file_path = test_files_dir
        fake_config["bib_dir"] = os.path.join(test_files_dir, "multi_bib")

        plugin.on_config(fake_config)
        self.assertEqual(len(plugin.bib_data.entries), 2)

    def test_format_citations(self):
        test_data = parse_file(os.path.join(test_files_dir, "single.bib"))
        self.assertIn(
            "First Author and Second Author",
            self.plugin.format_citations(test_data.entries.items())["test"],
        )

    def test_full_bibliography(self):
        test_data = parse_file(os.path.join(test_files_dir, "single.bib"))
        self.plugin.format_citations(test_data.entries.items())

        self.assertIn("First Author and Second Author", self.plugin.full_bibliography)

    def test_on_page_markdown(self):
        self.plugin.on_config(self.fake_config)
        test_data = parse_file(os.path.join(test_files_dir, "single.bib"))
        test_markdown = "This is a citation. [@test]\n\n \\bibliography"

        self.assertIn(
            "[^1]: First Author and Second Author\. Test title\. *Testing Journal*, 2019\.",
            self.plugin.on_page_markdown(test_markdown, None, None, None),
        )
