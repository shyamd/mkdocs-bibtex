import pytest

from mkdocs_bibtex.utils import sanitize_zotero_query, tempfile_from_zotero_url
import collections.abc
import os
import random
import string

import responses
from pybtex.database import parse_file

EXAMPLE_ZOTERO_API_ENDPOINT = "https://api.zotero.org/groups/FOO/collections/BAR/items"

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


@pytest.mark.parametrize(("mock_zotero_api", "number_of_entries"), ((4, 4), (150, 150)), indirect=["mock_zotero_api"])
def test_bibtex_loading_zotero(mock_zotero_api: responses.RequestsMock, number_of_entries: int) -> None:
    bib_file = tempfile_from_zotero_url("Bib File", MOCK_ZOTERO_URL, ".bib")

    assert os.path.exists(bib_file)
    assert os.path.getsize(bib_file) > 0

    bibdata = parse_file(bib_file)

    assert len(bibdata.entries) == number_of_entries


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
