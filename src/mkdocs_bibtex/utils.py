import os
import logging
import requests
import tempfile
import urllib.parse
from mkdocs.config.defaults import MkDocsConfig


# Grab a logger
log = logging.getLogger("mkdocs.plugins.mkdocs-bibtex")


def tempfile_from_url(name: str, url: str, suffix: str) -> str:
    """Download bibfile from a URL."""
    log.debug(f"Downloading {name} from URL {url} to temporary file...")
    if urllib.parse.urlparse(url).hostname == "api.zotero.org":
        return tempfile_from_zotero_url(name, url, suffix)
    for i in range(3):
        try:
            dl = requests.get(url)
            if dl.status_code != 200:  # pragma: no cover
                raise RuntimeError(f"Couldn't download the url: {url}.\n Status Code: {dl.status_code}")

            file = tempfile.NamedTemporaryFile(mode="wt", encoding="utf-8", suffix=suffix, delete=False)
            file.write(dl.text)
            file.close()
            log.info(f"{name} downladed from URL {url} to temporary file ({file})")
            return file.name

        except requests.exceptions.RequestException:  # pragma: no cover
            pass
    raise RuntimeError(f"Couldn't successfully download the url: {url}")  # pragma: no cover


def tempfile_from_zotero_url(name: str, url: str, suffix: str) -> str:
    """Download bibfile from the Zotero API."""
    log.debug(f"Downloading {name} from Zotero at {url}")
    bib_contents = ""

    url = sanitize_zotero_query(url)

    # Limit the pages requested to 999 arbitrarily. This will support a maximum of ~100k items
    for page_num in range(999):
        for _ in range(3):
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    msg = f"Couldn't download the url: {url}.\nStatus Code: {response.status_code}"
                    raise RuntimeError(msg)
                break
            except requests.exceptions.RequestException:  # pragma: no cover
                pass

        bib_contents += response.text
        try:
            url = response.links["next"]["url"]
        except KeyError:
            log.debug(f"Downloaded {page_num}(s) from {url}")
            break
    else:
        log.debug(f"Exceeded the maximum number of pages. Found: {page_num} pages")
    with tempfile.NamedTemporaryFile(mode="wt", encoding="utf-8", suffix=suffix, delete=False) as file:
        file.write(bib_contents)
    log.info(f"{name} downloaded from URL {url} to temporary file ({file})")
    return file.name


def sanitize_zotero_query(url: str) -> str:
    """Sanitize query params in the Zotero URL.

    The query params are amended to meet the following requirements:
        - `mkdocs-bibtex` expects all bib data to be in bibtex format.
        - Requesting the maximum number of items (100) reduces the requests
            required, hence reducing load times.
    """
    updated_query_params = {"format": "bibtex", "limit": 100}

    parsed_url = urllib.parse.urlparse(url)

    query_params = dict(urllib.parse.parse_qsl(parsed_url.query))

    return urllib.parse.ParseResult(
        scheme=parsed_url.scheme,
        netloc=parsed_url.netloc,
        path=parsed_url.path,
        params=parsed_url.params,
        query=urllib.parse.urlencode(query={**query_params, **updated_query_params}),
        fragment=parsed_url.fragment,
    ).geturl()

def get_path_relative_to_mkdocs_yaml(path: str, config: MkDocsConfig) -> str:
    """Get the relative path of a file to the mkdocs.yaml file."""
    mkdocs_rel_path = os.path.normpath(os.path.join(os.path.dirname(config.config_file_path), path))
    return mkdocs_rel_path
