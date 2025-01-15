import collections.abc
import os
import random
import string

import pytest
import responses

from mkdocs_bibtex.plugin import BibTexPlugin

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))
MOCK_ZOTERO_URL = "https://api.zotero.org/groups/FOO/collections/BAR/items?format=bibtex"


@pytest.fixture
def mock_zotero_api(request: pytest.FixtureRequest) -> collections.abc.Generator[responses.RequestsMock]:
    zotero_api_url = "https://api.zotero.org/groups/FOO/collections/BAR/items?format=bibtex&limit=100"
    bibtex_contents = generate_bibtex_entries(request.param)

    limit = 100
    pages = [bibtex_contents[i : i + limit] for i in range(0, len(bibtex_contents), limit)]

    with responses.RequestsMock() as mock_api:
        for page_num, page in enumerate(pages):
            current_start = "" if page_num == 0 else f"&start={page_num * limit}"
            next_start = f"&start={(page_num + 1) * limit}"
            mock_api.add(
                responses.Response(
                    method="GET",
                    url=f"{zotero_api_url}{current_start}",
                    json="\n".join(page),
                    headers={}
                    if page_num == len(pages) - 1
                    else {"Link": f"<{zotero_api_url}{next_start}>; rel='next'"},
                )
            )

        yield mock_api


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


@pytest.mark.parametrize(("mock_zotero_api", "number_of_entries"), ((4, 4), (150, 150)), indirect=["mock_zotero_api"])
def test_bibtex_loading_zotero(mock_zotero_api: responses.RequestsMock, number_of_entries: int) -> None:
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_file": MOCK_ZOTERO_URL},
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.bib_data.entries) == number_of_entries

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


def test_footnote_formatting_config(plugin):
    """
    This function tests to ensure footnote formatting configuration is working properly
    """
    # Test to make sure the config enforces {number} in the format
    bad_plugin = BibTexPlugin()
    bad_plugin.load_config(
        options={"footnote_format": ""},
        config_file_path=test_files_dir,
    )

    with pytest.raises(Exception):
        bad_plugin.on_config(bad_plugin.config)

def generate_bibtex_entries(n: int) -> list[str]:
    """Generates n random bibtex entries."""

    entries = []

    for i in range(n):
        author_first = "".join(random.choices(string.ascii_letters, k=8))
        author_last = "".join(random.choices(string.ascii_letters, k=8))
        title = "".join(random.choices(string.ascii_letters, k=10))
        journal = "".join(random.choices(string.ascii_uppercase, k=5))
        year = str(random.randint(1950, 2025))

        entries.append(f"""
@article{{{author_last}_{i}}},
    title = {{{title}}},
    volume = {{1}},
    journal = {{{journal}}},
    author = {{{author_last}, {author_first}}},
    year = {{{year}}},
""")
    return entries
