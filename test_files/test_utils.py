import pytest

from mkdocs_bibtex.utils import (
    sanitize_zotero_query,
)

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
