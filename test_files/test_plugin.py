import os

import pytest

from mkdocs_bibtex.plugin import BibTexPlugin, parse_file
from mkdocs_bibtex.utils import (
    find_cite_keys,
    format_bibliography,
    insert_citation_keys,
    format_simple,
    format_pandoc,
)

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


@pytest.fixture
def plugin():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_file": os.path.join(test_files_dir, "test.bib")},
        config_file_path=test_files_dir,
    )
    plugin.on_config(plugin.config)
    return plugin


@pytest.fixture
def entries():
    bibdata = parse_file(os.path.join(test_files_dir, "test.bib"))
    return bibdata.entries


def test_bibtex_loading_bibfile(plugin):
    assert len(plugin.bib_data.entries) == 3


def test_bibtex_loading_bibdir():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_dir": os.path.join(test_files_dir, "multi_bib")},
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.bib_data.entries) == 2


@pytest.mark.xfail()
def test_format_citations(plugin):
    plugin.csl_file = None

    assert (
        "[@test]",
        "@test",
        "1.",
        "First Author and Second Author",
    ) == plugin.format_citations(["@test"])[0]

    # Test arithmatex compatability formatting
    assert (
        "[@test2]",
        "@test2",
        "1.",
        "First Author and Second Author\\. Test Title \\(TT\\)\\. *Testing Journal \\(TJ\\)*, 2019",
    ) == plugin.format_citations(["@test2"])

    plugin.unescape_for_arithmatex = True
    assert (
        "[@test2]",
        "@test2",
        "1.",
        "First Author and Second Author\\. Test Title (TT)\\. *Testing Journal (TJ)*, 2019",
    ) == plugin.format_citations(["@test2"])

    plugin.unescape_for_arithmatex = False

    # Test compound citation
    assert [
        (
            "[@test; @test2]",
            "@test",
            "1.",
            "First Author and Second Author",
        ),
        (
            "[@test; @test2]",
            "@test2",
            "2.",
            "First Author and Second Author\\. Test Title \\(TT\\)\\. *Testing Journal \\(TJ\\)*, 2019",
        ),
    ] == plugin.format_citations(["@test; @test2"])

    # test long citation

    plugin.csl_file = None
    assert (
        "@Biovort2016",
        "@Biovort2016",
        "1",
        "Benjamin L\\. De Bivort and Bruno Van Swinderen",
    ) == plugin.format_citations(["Bivort2016"])

    # Test formatting using a CSL style
    plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
    assert (
        "@test",
        "@test",
        "1.",
        "Author, F. & Author, S",
    ) == plugin.format_citations(["@test"])

    plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
    assert (
        "@Biovort2016",
        "@Biovort2016",
        "1",
        "De Bivort, B. L. & Van Swinderen",
    ) == plugin.format_citations(["Bivort2016"])

    plugin.csl_file = os.path.join(test_files_dir, "springer-basic-author-date.csl")
    assert ("@test", "@test", "1", "Author F, Author S") == plugin.format_citations(
        ["@test"]
    )


def test_find_cite_keys():
    assert find_cite_keys("[@test]") == ["[@test]"]
    assert find_cite_keys("[@test; @test2]") == ["[@test; @test2]"]
    assert find_cite_keys("[@test]\n [@test; @test2]") == ["[@test]", "[@test; @test2]"]


def test_insert_citation_keys():
    assert (
        insert_citation_keys(
            [
                (
                    "[@test]",
                    "@test",
                    "1",
                    "First Author and Second Author",
                )
            ],
            "[@test]",
        )
        == "[^1]"
    )

    assert (
        insert_citation_keys(
            [
                (
                    "[@test; @test2]",
                    "@test",
                    "1",
                    "First Author and Second Author",
                ),
                (
                    "[@test; @test2]",
                    "@test2",
                    "2",
                    "First Author and Second Author\\. Test Title \\(TT\\)\\. *Testing Journal \\(TJ\\)*, 2019",
                ),
            ],
            "[@test; @test2]",
        )
        == "[^1][^2]"
    )


def test_format_bibliography():
    quads = [
        (
            "[@test; @test2]",
            "@test",
            "1",
            "First Author and Second Author",
        ),
        (
            "[@test; @test2]",
            "@test2",
            "2",
            "First Author and Second Author\\. Test Title \\(TT\\)\\. *Testing Journal \\(TJ\\)*, 2019",
        ),
    ]

    bib = format_bibliography(quads)

    assert "[^1]: First Author and Second Author" in bib
    assert (
        "[^2]: First Author and Second Author\\. Test Title \\(TT\\)\\. *Testing Journal \\(TJ\\)*, 2019"
        in bib
    )


def test_format_simple(entries):
    citations = format_simple(entries)

    assert all(k in citations for k in entries)
    assert all(entry != citations[k] for k, entry in entries.items())

    print(citations)
    assert (
        citations["test"]
        == "First Author and Second Author\\. Test title\\. *Testing Journal*, 2019\\."
    )
    assert (
        citations["test2"]
        == "First Author and Second Author\\. Test Title \\(TT\\)\\. *Testing Journal \\(TJ\\)*, 2019\\."
    )


def test_format_pandoc(entries):
    citations = format_pandoc(entries, os.path.join(test_files_dir, "nature.csl"))

    assert all(k in citations for k in entries)
    assert all(entry != citations[k] for k, entry in entries.items())

    print(citations)
    assert (
        citations["test"]
        == "Author, F. & Author, S. Test title. *Testing Journal* **1**, (2019)."
    )
    assert (
        citations["test2"]
        == "Author, F. & Author, S. Test Title (TT). *Testing Journal (TJ)* **1**, (2019)."
    )
