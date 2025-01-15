import os

import pytest

from mkdocs_bibtex.utils import (
    find_cite_blocks,
    format_simple,
    format_pandoc,
    extract_cite_keys,
    sanitize_zotero_query,
)

from mkdocs_bibtex.plugin import parse_file

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


@pytest.fixture
def entries():
    bibdata = parse_file(os.path.join(test_files_dir, "test.bib"))
    return bibdata.entries


def test_find_cite_blocks():

    # Suppressed authors
    assert find_cite_blocks("[-@test]") == ["[-@test]"]
    # Affixes
    assert find_cite_blocks("[see @test]") == ["[see @test]"]
    assert find_cite_blocks("[@test, p. 15]") == ["[@test, p. 15]"]
    assert find_cite_blocks("[see @test, p. 15]") == ["[see @test, p. 15]"]
    assert find_cite_blocks("[see -@test, p. 15]") == ["[see -@test, p. 15]"]
    # Invalid blocks
    assert find_cite_blocks("[ @test]") is not True
    # Citavi . format
    assert find_cite_blocks("[@Bermudez.2020]") == ["[@Bermudez.2020]"]


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


def test_extract_cite_key():
    """
    Test to ensure the extract regex can handle all bibtex keys
    TODO: Make this fully compliant with bibtex keys allowed characters
    """
    assert extract_cite_keys("[@test]") == ["test"]
    assert extract_cite_keys("[@test.3]") == ["test.3"]


EXAMPLE_ZOTERO_API_ENDPOINT = "https://api.zotero.org/groups/FOO/collections/BAR/items"


@pytest.mark.parametrize(
    ("zotero_url", "expected_sanitized_url"),
    (
        (f"{EXAMPLE_ZOTERO_API_ENDPOINT}", f"{EXAMPLE_ZOTERO_API_ENDPOINT}?format=bibtex&limit=100"),
        (
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?format=bibtex&limit=25",
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?format=bibtex&limit=100",
        ),
        (
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?format=json",
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?format=bibtex&limit=100",
        ),
        (
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?sort=dateAdded",
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?sort=dateAdded&format=bibtex&limit=100",
        ),
        (
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?sort=dateAdded&sort=publisher",
            f"{EXAMPLE_ZOTERO_API_ENDPOINT}?sort=publisher&format=bibtex&limit=100",
        ),
    ),
)
def test_sanitize_zotero_query(zotero_url: str, expected_sanitized_url: str) -> None:
    assert sanitize_zotero_query(url=zotero_url) == expected_sanitized_url
