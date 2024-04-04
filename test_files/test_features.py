"""
This test file checks to make sure each feature works rather than checking each
function. Each feature should have a single test function that covers all the python
functions it that would need to be tested
"""
import os

import pytest
import pypandoc

from mkdocs_bibtex.plugin import BibTexPlugin

from mkdocs_bibtex.utils import (
    find_cite_blocks,
    format_bibliography,
    insert_citation_keys,
)

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


@pytest.fixture
def plugin():
    """
    Basic BibTex Plugin without CSL
    """
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_file": os.path.join(test_files_dir, "test.bib")},
        config_file_path=test_files_dir,
    )
    plugin.on_config(plugin.config)
    plugin.csl_file = None
    return plugin



@pytest.fixture
def plugin_advanced_pandoc(plugin):
    """
    Enables advanced features via pandoc
    """
    # Only valid for Pandoc > 2.11
    pandoc_version = pypandoc.get_pandoc_version()
    pandoc_version_tuple = tuple(int(ver) for ver in pandoc_version.split("."))
    if pandoc_version_tuple <= (2, 11):
        pytest.skip(f"Unsupported version of pandoc (v{pandoc_version}) installed.")

    plugin.config["bib_file"] = os.path.join(test_files_dir, "test.bib")
    plugin.config["csl_file"] = os.path.join(
        test_files_dir, "springer-basic-author-date.csl"
    )
    plugin.config["cite_inline"] = True

    delattr(plugin,"last_configured")
    plugin.on_config(plugin.config)

    return plugin


def test_basic_citations(plugin):
    """
    Tests super basic citations using the built-in citation style
    """
    assert find_cite_blocks("[@test]") == ["[@test]"]

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

    ### TODO: test format_bibliography

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

    # test long citation
    assert (
        "[@Bivort2016]",
        "Bivort2016",
        "1",
        "Benjamin L. De Bivort and Bruno Van Swinderen. Evidence for selective attention in the insect brain. *Current Opinion in Insect Science*, 15:1–7, 2016. [doi:10.1016/j.cois.2016.02.007](https://doi.org/10.1016/j.cois.2016.02.007).",  # noqa: E501
    ) == plugin.format_citations(["[@Bivort2016]"])[0]

    # Test \url embedding
    assert (
        "[@test_citavi]",
        "test_citavi",
        "1",
        "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019. URL: [\\\\url\\{https://doi.org/10.21577/0103\\-5053.20190253\\}](\\url{https://doi.org/10.21577/0103-5053.20190253}).",  # noqa: E501
    ) == plugin.format_citations(["[@test_citavi]"])[0]


def test_compound_citations(plugin):
    """
    Compound citations are citations that include multiple cite keys
    """
    assert find_cite_blocks("[@test; @test2]") == ["[@test; @test2]"]
    assert find_cite_blocks("[@test]\n [@test; @test2]") == [
        "[@test]",
        "[@test; @test2]",
    ]

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


###############
# PANDOC ONLY #
###############


def test_basic_pandoc(plugin):
    plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
    assert (
        "[@test]",
        "test",
        "1",
        "Author, F. & Author, S. Test title. *Testing Journal* **1**, (2019).",
    ) == plugin.format_citations(["[@test]"])[0]

    assert (
        "[@Bivort2016]",
        "Bivort2016",
        "1",
        "De Bivort, B. L. & Van Swinderen, B. Evidence for selective attention in the insect brain. *Current Opinion in Insect Science* **15**, 1–7 (2016).",  # noqa: E501
    ) == plugin.format_citations(["[@Bivort2016]"])[0]

    # Test a CSL that outputs references in a different style
    plugin.csl_file = os.path.join(test_files_dir, "springer-basic-author-date.csl")
    assert (
        "[@test]",
        "test",
        "1",
        "Author, F. & Author, S. Test title. *Testing Journal* **1**, (2019).",
    ) == plugin.format_citations(["[@test]"])[0]

    assert (
        "[@test_citavi]",
        "test_citavi",
        "1",
        "Author F, Author S (2019) Test Title (TT). Testing Journal (TJ) 1:",
    ) == plugin.format_citations(["[@test_citavi]"])[0]


def test_inline_ciations(plugin_advanced_pandoc):
    plugin = plugin_advanced_pandoc

    # Ensure inline citation works
    quads = [("[@test]", None, "1", None)]
    test_markdown = "Hello[@test]"
    result = "Hello (Author and Author 2019)[^1]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )


def test_supressed_authors(plugin_advanced_pandoc):
    plugin = plugin_advanced_pandoc

    # Ensure suppressed authors works
    quads = [("[-@test]", None, "1", None)]
    test_markdown = "Suppressed [-@test]"
    result = "Suppressed (2019)[^1]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )


def test_affixes(plugin_advanced_pandoc):
    plugin = plugin_advanced_pandoc
    # Ensure affixes work
    quads = [("[see @test]", None, "1", None)]
    test_markdown = "Hello[see @test]"
    result = "Hello (see Author and Author 2019)[^1]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )

    quads = [("[@test, p. 123]", None, "1", None)]
    test_markdown = "[@test, p. 123]"
    result = " (Author and Author 2019, p. 123)[^1]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )

    # Combined
    quads = [("[see @test, p. 123]", None, "1", None)]
    test_markdown = "Hello[see @test, p. 123]"
    result = "Hello (see Author and Author 2019, p. 123)[^1]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )

    # Combined, suppressed author
    quads = [("[see -@test, p. 123]", None, "1", None)]
    test_markdown = "Suppressed [see -@test, p. 123]"
    result = "Suppressed (see 2019, p. 123)[^1]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )


def test_invalid_blocks(plugin_advanced_pandoc):
    pass


def test_citavi_format(plugin_advanced_pandoc):
    pass


def test_duplicate_reference(plugin_advanced_pandoc):
    """
    Ensures duplicats references show up appropriately
    # TODO: These test cases don't seem right
    """
    plugin = plugin_advanced_pandoc
    # Ensure multi references work
    quads = [
        ("[@test; @Bivort2016]", None, "1", None),
        ("[@test; @Bivort2016]", None, "2", None),
    ]
    test_markdown = "[@test; @Bivort2016]"
    # CSL defines the order, this ordering is therefore expected with springer.csl
    result = " (De Bivort and Van Swinderen 2016; Author and Author 2019)[^1][^2]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )

    quads = [
        ("[@test, p. 12; @Bivort2016, p. 15]", None, "1", None),
        ("[@test, p. 12; @Bivort2016, p. 15]", None, "2", None),
    ]
    test_markdown = "[@test, p. 12; @Bivort2016, p. 15]"
    # CSL defines the order, this ordering is therefore expected with springer.csl
    result = " (De Bivort and Van Swinderen 2016, p. 15; Author and Author 2019, p. 12)[^1][^2]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )


def test_multi_reference(plugin_advanced_pandoc):
    """
    Ensures multiple inline references show up appropriately
    """

    plugin = plugin_advanced_pandoc
    # Ensure multiple inline references works
    quads = [
        ("[@test]", None, "1", None),
        ("[see @Bivort2016, p. 123]", None, "2", None),
    ]
    test_markdown = "Hello[@test] World [see @Bivort2016, p. 123]"
    result = "Hello (Author and Author 2019)[^1] World (see De Bivort and Van Swinderen 2016, p. 123)[^2]"
    assert result == insert_citation_keys(
        quads, test_markdown, plugin.csl_file, plugin.bib_data.to_string("bibtex")
    )


def test_custom_footnote_formatting(plugin):

    assert plugin.format_footnote_key(1) == "1"
    plugin.footnote_format = "Test Format {number}"
    assert plugin.format_footnote_key(1) == "Test Format 1"

    plugin.csl_file = os.path.join(test_files_dir, "nature.csl")
    assert (
        "[@test]",
        "test",
        "Test Format 1",
        "Author, F. & Author, S. Test title. *Testing Journal* **1**, (2019).",
    ) == plugin.format_citations(["[@test]"])[0]
