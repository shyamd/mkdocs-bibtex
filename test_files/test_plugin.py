import os

import pytest
import pypandoc

from mkdocs_bibtex.plugin import BibTexPlugin, parse_file
from mkdocs_bibtex.utils import (
    find_cite_blocks,
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


def test_bibtex_loading_bib_url():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_file": "https://raw.githubusercontent.com/shyamd/mkdocs-bibtex/master/test_files/test.bib"},
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.bib_data.entries) == 3


def test_bibtex_loading_bibdir():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_dir": os.path.join(test_files_dir, "multi_bib")},
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.bib_data.entries) == 2


def test_format_citations(plugin):
    plugin.csl_file = None

    assert (
        "[@test]",
        "test",
        "1",
        "First Author and Second Author. Test title. *Testing Journal*, 2019.",
    ) == plugin.format_citations(["[@test]"])[0]

    assert (
        "[@test2]",
        "test2",
        "1",
        "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019.",
    ) == plugin.format_citations(["[@test2]"])[0]

    # Test compound citation
    assert [
        (
            "[@test; @test2]",
            "test",
            "1",
            "First Author and Second Author. Test title. *Testing Journal*, 2019.",
        ),
        (
            "[@test; @test2]",
            "test2",
            "2",
            "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019.",
        ),
    ] == plugin.format_citations(["[@test; @test2]"])

    # test long citation
    assert (
        "[@Bivort2016]",
        "Bivort2016",
        "1",
        "Benjamin L. De Bivort and Bruno Van Swinderen. Evidence for selective attention in the insect brain. *Current Opinion in Insect Science*, 15:1–7, 2016. [doi:10.1016/j.cois.2016.02.007](https://doi.org/10.1016/j.cois.2016.02.007).",  # noqa: E501
    ) == plugin.format_citations(["[@Bivort2016]"])[0]

    # Test formatting using a CSL style
    plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
    assert (
        "[@test]",
        "test",
        "1",
        "First Author and Second Author. Test title. *Testing Journal*, 2019.",
    ) == plugin.format_citations(["[@test]"])[0]

    assert (
        "[@Bivort2016]",
        "Bivort2016",
        "1",
        "Benjamin L. De Bivort and Bruno Van Swinderen. Evidence for selective attention in the insect brain. *Current Opinion in Insect Science*, 15:1–7, 2016. [doi:10.1016/j.cois.2016.02.007](https://doi.org/10.1016/j.cois.2016.02.007).",  # noqa: E501
    ) == plugin.format_citations(["[@Bivort2016]"])[0]

    # Test a CSL that outputs references in a different style
    plugin.csl_file = os.path.join(test_files_dir, "springer-basic-author-date.csl")
    assert (
        "[@test]",
        "test",
        "1",
        "First Author and Second Author. Test title. *Testing Journal*, 2019.",
    ) == plugin.format_citations(["[@test]"])[0]


def test_find_cite_blocks():
    assert find_cite_blocks("[@test]") == ["[@test]"]
    assert find_cite_blocks("[@test; @test2]") == ["[@test; @test2]"]
    assert find_cite_blocks("[@test]\n [@test; @test2]") == ["[@test]", "[@test; @test2]"]
    # Suppressed authors
    assert find_cite_blocks("[-@test]") == ["[-@test]"]
    # Affixes
    assert find_cite_blocks("[see @test]") == ["[see @test]"]
    assert find_cite_blocks("[@test, p. 15]") == ["[@test, p. 15]"]
    assert find_cite_blocks("[see @test, p. 15]") == ["[see @test, p. 15]"]
    assert find_cite_blocks("[see -@test, p. 15]") == ["[see -@test, p. 15]"]
    # Invalid blocks
    assert find_cite_blocks("[ @test]") is not True


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
                    "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019",  # noqa: E501
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
            "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019",
        ),
    ]

    bib = format_bibliography(quads)

    assert "[^1]: First Author and Second Author" in bib
    assert (
        "[^2]: First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019"
        in bib
    )


def test_format_simple(entries):
    citations = format_simple(entries)

    assert all(k in citations for k in entries)
    assert all(entry != citations[k] for k, entry in entries.items())

    assert (
        citations["test"]
        == "First Author and Second Author. Test title. *Testing Journal*, 2019."
    )
    assert (
        citations["test2"]
        == "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019."
    )


def test_format_pandoc(entries):
    citations = format_pandoc(entries, os.path.join(test_files_dir, "nature.csl"))

    assert all(k in citations for k in entries)
    assert all(entry != citations[k] for k, entry in entries.items())

    assert (
        citations["test"]
        == "Author, F. & Author, S. Test title. *Testing Journal* **1**, (2019)."
    )
    assert (
        citations["test2"]
        == "Author, F. & Author, S. Test Title (TT). *Testing Journal (TJ)* **1**, (2019)."
    )


def test_on_page_markdown(plugin):
    plugin.on_config(plugin.config)
    # run test with bib_by_default set to False
    plugin.config["bib_by_default"] = False

    test_markdown = "This is a citation. [@test]\n\n \\bibliography"

    assert (
        "[^1]: First Author and Second Author. Test title. *Testing Journal*, 2019."
        in plugin.on_page_markdown(test_markdown, None, None, None)
    )

    # ensure there are two items in bibliography
    test_markdown = "This is a citation. [@test2] This is another citation [@test]\n\n \\bibliography"

    assert "[^2]:" in plugin.on_page_markdown(test_markdown, None, None, None)

    # ensure bib_by_default is working
    plugin.config["bib_by_default"] = True
    test_markdown = "This is a citation. [@test]"

    assert "[^1]:" in plugin.on_page_markdown(test_markdown, None, None, None)
    plugin.config["bib_by_default"] = False

    # ensure nonexistant citekeys are removed correctly (not replaced)
    test_markdown = "A non-existant citekey. [@i_do_not_exist]"

    assert "[@i_do_not_exist]" in plugin.on_page_markdown(test_markdown, None, None, None)

    # Ensure if an item is referenced multiple times, it only shows up as one reference
    test_markdown = "This is a citation. [@test] This is another citation [@test]\n\n \\bibliography"

    assert "[^2]" not in plugin.on_page_markdown(test_markdown, None, None, None)

    # Ensure item only shows up once even if used in multiple places as both a compound and lone cite key
    test_markdown = "This is a citation. [@test; @test2] This is another citation [@test]\n\n \\bibliography"

    assert "[^3]" not in plugin.on_page_markdown(test_markdown, None, None, None)


def test_inline_citations(plugin):
    plugin.config["bib_file"] = os.path.join(test_files_dir, "test.bib")
    plugin.config["csl_file"] = os.path.join(test_files_dir, "springer-basic-author-date.csl")
    plugin.config["cite_inline"] = True

    plugin.on_config(plugin.config)

    pandoc_version = pypandoc.get_pandoc_version()
    pandoc_version_tuple = tuple(int(ver) for ver in pandoc_version.split("."))
    if pandoc_version_tuple <= (2, 11):
        pytest.skip(f"Unsupported version of pandoc (v{pandoc_version}) installed.")

    # Ensure inline citation works
    quads = [("[@test]", None, "1", None)]
    test_markdown = 'Hello[@test]'
    result = "Hello (Author and Author 2019)[^1]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    # Ensure suppressed authors works
    quads = [("[-@test]", None, "1", None)]
    test_markdown = 'Suppressed [-@test]'
    result = "Suppressed (2019)[^1]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    # Ensure affixes work
    quads = [("[see @test]", None, "1", None)]
    test_markdown = 'Hello[see @test]'
    result = "Hello (see Author and Author 2019)[^1]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    quads = [("[@test, p. 123]", None, "1", None)]
    test_markdown = '[@test, p. 123]'
    result = " (Author and Author 2019, p. 123)[^1]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    # Combined
    quads = [("[see @test, p. 123]", None, "1", None)]
    test_markdown = 'Hello[see @test, p. 123]'
    result = "Hello (see Author and Author 2019, p. 123)[^1]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    # Combined, suppressed author
    quads = [("[see -@test, p. 123]", None, "1", None)]
    test_markdown = 'Suppressed [see -@test, p. 123]'
    result = "Suppressed (see 2019, p. 123)[^1]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    # Ensure multi references work
    quads = [("[@test; @Bivort2016]", None, "1", None),
             ("[@test; @Bivort2016]", None, "2", None)]
    test_markdown = '[@test; @Bivort2016]'
    # CSL defines the order, this ordering is therefore expected with springer.csl
    result = " (De Bivort and Van Swinderen 2016; Author and Author 2019)[^1][^2]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    quads = [("[@test, p. 12; @Bivort2016, p. 15]", None, "1", None),
             ("[@test, p. 12; @Bivort2016, p. 15]", None, "2", None)]
    test_markdown = '[@test, p. 12; @Bivort2016, p. 15]'
    # CSL defines the order, this ordering is therefore expected with springer.csl
    result = " (De Bivort and Van Swinderen 2016, p. 15; Author and Author 2019, p. 12)[^1][^2]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))

    # Ensure multiple inline references works
    quads = [("[@test]", None, "1", None),
             ("[see @Bivort2016, p. 123]", None, "2", None)]
    test_markdown = 'Hello[@test] World [see @Bivort2016, p. 123]'
    result = "Hello (Author and Author 2019)[^1] World (see De Bivort and Van Swinderen 2016, p. 123)[^2]"
    assert result == insert_citation_keys(quads, test_markdown, plugin.csl_file,
                                          plugin.bib_data.to_string("bibtex"))
