"""
Integration tests for mkdocs-bibtex plugin. These tests verify the complete functionality
of the plugin rather than testing individual components.
"""

import os
import pytest
import pypandoc
from mkdocs_bibtex.plugin import BibTexPlugin

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


@pytest.fixture
def plugin():
    """Basic BibTex Plugin without CSL"""
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_file": os.path.join(test_files_dir, "test.bib"), "bib_by_default": False},
        config_file_path=test_files_dir,
    )
    plugin.on_config(plugin.config)

    return plugin


@pytest.fixture
def pandoc_plugin(plugin):
    """BibTex Plugin with Pandoc and CSL support"""
    # Skip if Pandoc version is too old
    pandoc_version = pypandoc.get_pandoc_version()
    if tuple(int(v) for v in pandoc_version.split(".")) <= (2, 11):
        pytest.skip(f"Unsupported pandoc version (v{pandoc_version})")

    plugin = BibTexPlugin()
    plugin.load_config(
        options={
            "bib_file": os.path.join(test_files_dir, "test.bib"),
            "csl_file": os.path.join(test_files_dir, "springer-basic-author-date.csl"),
            "cite_inline": True,
            "bib_by_default": False,
        },
        config_file_path=test_files_dir,
    )
    plugin.on_config(plugin.config)
    # plugin.csl_file = None

    return plugin


def test_basic_citation_rendering(plugin):
    """Test basic citation functionality without CSL"""
    markdown = "Here is a citation [@test] and another one [@test2].\n\n\\bibliography"
    result = plugin.on_page_markdown(markdown, None, None, None)

    # Check citation replacements
    assert "[^test]" in result
    assert "[^test2]" in result

    # Check bibliography entries
    assert "First Author and Second Author. Test title. *Testing Journal*, 2019." in result
    assert "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019." in result


def test_pandoc_citation_rendering(pandoc_plugin):
    """Test citation rendering with Pandoc and CSL"""
    markdown = "Here is a citation [@test] and another [@Bivort2016].\n\n\\bibliography"
    result = pandoc_plugin.on_page_markdown(markdown, None, None, None)

    # Check inline citations
    assert "(Author and Author 2019)" in result
    assert "(De Bivort and Van Swinderen 2016)" in result

    # Check bibliography formatting
    assert "Author F, Author S (2019)" in result
    assert "De Bivort BL, Van Swinderen B (2016)" in result


def test_citation_features(pandoc_plugin):
    """Test various citation features like prefixes, suffixes, and author suppression"""
    markdown = """
See [-@test] for more.
As shown by [see @test, p. 123].
Multiple sources [@test; @test2].

\\bibliography
    """
    result = pandoc_plugin.on_page_markdown(markdown, None, None, None)

    # Check various citation formats
    assert "(2019" in result  # Suppressed author
    assert "see Author and Author 2019a, p. 123" in result  # Prefix and suffix
    assert "Author and Author 2019a, b" in result  # Multiple citations

    # Check bibliography formatting
    assert "Author F, Author S (2019a) Test title. Testing Journal 1:" in result
    assert "Author F, Author S (2019b) Test Title (TT). Testing Journal (TJ) 1:" in result

    # Check that the bibliography entries are only shown once
    assert result.count("Author F, Author S (2019a) Test title. Testing Journal 1:") == 1
    assert result.count("Author F, Author S (2019b) Test Title (TT). Testing Journal (TJ) 1:") == 1


def test_bibliography_controls(plugin):
    """Test bibliography inclusion behavior"""
    # Test with explicit bibliography command
    markdown = "Citation [@test]\n\n\\bibliography"
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "[^test]:" in result

    # Test without bibliography command when bib_by_default is False
    markdown = "Citation [@test]"
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "[^test]:" not in result

    # Test without bibliography command when bib_by_default is True
    plugin.config.bib_by_default = True
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "[^test]:" in result


def test_custom_footnote_format():
    """Test custom footnote formatting"""
    plugin = BibTexPlugin()
    plugin.load_config(
        options={
            "bib_file": os.path.join(test_files_dir, "test.bib"),
            "bib_by_default": False,
            "footnote_format": "ref-{key}",
        },
        config_file_path=test_files_dir,
    )
    plugin.on_config(plugin.config)

    markdown = "Citation [@test]\n\n\\bibliography"
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "[^ref-test]" in result
    # Test that an invalid footnote format raises an exception
    bad_plugin = BibTexPlugin()
    bad_plugin.load_config(
        options={"footnote_format": ""},
        config_file_path=test_files_dir,
    )
    with pytest.raises(Exception):
        bad_plugin.on_config(bad_plugin.config)


def test_invalid_citations(plugin):
    """Test handling of invalid citations"""
    markdown = "Invalid citation [@nonexistent]\n\n\\bibliography"
    result = plugin.on_page_markdown(markdown, None, None, None)
    # assert "[@nonexistent]" in result  # Invalid citation should remain unchanged
    assert "[^nonexistent]" not in result


def test_full_bib_command(plugin):
    """Test full bibliography command"""
    markdown = "Full bibliography [@test]\n\n\\full_bibliography"
    result = plugin.on_page_markdown(markdown, None, None, None)

    assert "Full bibliography [^test]" in result
    assert "[^test]:" in result
    assert "[^test2]:" in result
    assert "[^Bivort2016]:" in result
    assert "[^test_citavi]:" in result


def test_bib_by_default(plugin):
    """Test bib_by_default behavior"""
    markdown = "Citation [@test]"
    plugin.config.bib_by_default = False
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "[^test]:" not in result

    plugin.config.bib_by_default = True
    result = plugin.on_page_markdown(markdown, None, None, None)
    assert "[^test]:" in result


def test_full_bib_command_with_pandoc(pandoc_plugin):
    """Test full bibliography command with Pandoc"""
    markdown = "Full bibliography\n\n\\full_bibliography"
    result = pandoc_plugin.on_page_markdown(markdown, None, None, None)

    assert "[^test]: Author F, Author S (2019a)" in result
    assert "[^test2]: Author F, Author S (2019b)" in result
    assert "[^Bivort2016]: De Bivort BL, Van Swinderen B (2016)" in result
    assert "[^test_citavi]: Author F, Author S (2019c)" in result
