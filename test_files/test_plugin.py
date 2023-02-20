import os

import pytest

from mkdocs_bibtex.plugin import BibTexPlugin

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
    plugin.csl_file = None
    return plugin


def test_bibtex_loading_bibfile(plugin):
    assert len(plugin.bib_data.entries) == 4


def test_bibtex_loading_bib_url():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={
            "bib_file": "https://raw.githubusercontent.com/shyamd/mkdocs-bibtex/main/test_files/test.bib"
        },
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.bib_data.entries) == 4


def test_bibtex_loading_bibdir():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_dir": os.path.join(test_files_dir, "multi_bib")},
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.bib_data.entries) == 2


def test_on_page_markdown(plugin):
    """
    This function just tests to make sure the rendered markdown changees with
    options and basic functionality works.  It doesn't test "features"
    """
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

    assert "[@i_do_not_exist]" in plugin.on_page_markdown(
        test_markdown, None, None, None
    )

    # Ensure if an item is referenced multiple times, it only shows up as one reference
    test_markdown = "This is a citation. [@test] This is another citation [@test]\n\n \\bibliography"

    assert "[^2]" not in plugin.on_page_markdown(test_markdown, None, None, None)

    # Ensure item only shows up once even if used in multiple places as both a compound and lone cite key
    test_markdown = "This is a citation. [@test; @test2] This is another citation [@test]\n\n \\bibliography"

    assert "[^3]" not in plugin.on_page_markdown(test_markdown, None, None, None)
