import logging
import requests
import tempfile

# Grab a logger
log = logging.getLogger("mkdocs.plugins.mkdocs-bibtex")

def tempfile_from_url(name, url, suffix):
    log.debug(f"Downloading {name} from URL {url} to temporary file...")
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
