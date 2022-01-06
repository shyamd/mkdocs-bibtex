import os
import unittest

from pybtex.database import parse_file

from mkdocs_bibtex import BibTexPlugin

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = BibTexPlugin()
        self.plugin.load_config(
            options={"bib_file": os.path.join(test_files_dir, "single.bib")},
            config_file_path=test_files_dir,
        )

    def test_unescape_for_arithmatex(self):
        test_data = parse_file(os.path.join(test_files_dir, "parenthesis.bib"))
        self.plugin.csl_file = None

        self.plugin.unescape_for_arithmatex = True
        self.assertIn(
            "First Author and Second Author\\. Test Title (TT)\\. *Testing Journal (TJ)*, 2019",
            self.plugin.format_citations(test_data.entries.items())["test"],
        )

        self.plugin.unescape_for_arithmatex = False
        self.assertIn(
            "First Author and Second Author\\. Test Title \\(TT\\)\\. *Testing Journal \\(TJ\\)*, 2019",
            self.plugin.format_citations(test_data.entries.items())["test"],
        )

    def test_config_one_bibtex_file(self):
        self.plugin.on_config(self.plugin.config)
        self.assertEqual(len(self.plugin.bib_data.entries), 1)

    def test_config_one_bibtex_dir(self):
        plugin = BibTexPlugin()
        plugin.load_config(
            options={"bib_dir": os.path.join(test_files_dir, "multi_bib")},
            config_file_path=test_files_dir,
        )

        plugin.on_config(plugin.config)
        self.assertEqual(len(plugin.bib_data.entries), 2)

    def test_format_citations(self):
        test_data = parse_file(os.path.join(test_files_dir, "single.bib"))
        self.plugin.csl_file = None
        self.assertIn(
            "First Author and Second Author",
            self.plugin.format_citations(test_data.entries.items())["test"],
        )

        self.plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
        self.assertIn(
            "Author, F. & Author, S",
            self.plugin.format_citations(test_data.entries.items())["test"],
        )
        # TODO: Check CSL

    def test_long_citation(self):
        test_data = parse_file(os.path.join(test_files_dir, "long_cite.bib"))
        self.plugin.csl_file = None
        self.assertIn(
            "Benjamin L\\. De Bivort and Bruno Van Swinderen",
            self.plugin.format_citations(test_data.entries.items())["Bivort2016"],
        )

        self.plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
        self.assertIn(
            "De Bivort, B. L. & Van Swinderen",
            self.plugin.format_citations(test_data.entries.items())["Bivort2016"],
        )

    def test_full_bibliography(self):
        test_data = parse_file(os.path.join(test_files_dir, "single.bib"))
        self.plugin.csl_file = None
        self.plugin.format_citations(test_data.entries.items())

        self.assertIn("First Author and Second Author", self.plugin.full_bibliography)

        self.plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
        self.plugin.format_citations(test_data.entries.items())
        self.assertIn("Author, F. & Author, S", self.plugin.full_bibliography)

        self.plugin.csl_file = os.path.join(
            test_files_dir, "springer-basic-author-date.csl"
        )
        self.plugin.format_citations(test_data.entries.items())
        self.assertIn("Author F, Author S", self.plugin.full_bibliography)

    def test_on_page_markdown(self):
        self.plugin.on_config(self.plugin.config)
        test_markdown = "This is a citation. [@test]\n\n \\bibliography"

        self.assertIn(
            "[^1]: First Author and Second Author\\. Test title\\. *Testing Journal*, 2019\\.",
            self.plugin.on_page_markdown(test_markdown, None, None, None),
        )
