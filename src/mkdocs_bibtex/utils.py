import re
import requests
import tempfile
from collections import OrderedDict
from itertools import groupby
from pathlib import Path

import pypandoc
from pybtex.backends.markdown import Backend as MarkdownBackend
from pybtex.database import BibliographyData
from pybtex.style.formatting.plain import Style as PlainStyle


def format_simple(entries):
    """
    Format the entries using a simple built in style

    Args:
        entries (dict): dictionary of entries

    Returns:
        references (dict): dictionary of citation texts
    """
    style = PlainStyle()
    backend = MarkdownBackend()
    citations = OrderedDict()
    for key, entry in entries.items():
        formatted_entry = style.format_entry("", entry)
        entry_text = formatted_entry.text.render(backend)
        entry_text = entry_text.replace("\n", " ")
        # Local reference list for this file
        citations[key] = (
            entry_text.replace("\\(", "(").replace("\\)", ")").replace("\\.", ".")
        )
    return citations


def format_pandoc(entries, csl_path):
    """
    Format the entries using pandoc

    Args:
        entries (dict): dictionary of entries
        csl_path (str): path to formatting CSL Fle
    Returns:
        references (dict): dictionary of citation texts
    """
    pandoc_version = tuple(int(ver) for ver in pypandoc.get_pandoc_version().split("."))
    citations = OrderedDict()
    for key, entry in entries.items():
        bibtex_string = BibliographyData(entries={entry.key: entry}).to_string("bibtex")
        if pandoc_version >= (2, 11):
            citations[key] = _convert_pandoc_new(bibtex_string, csl_path)
        else:
            citations[key] = _convert_pandoc_legacy(bibtex_string, csl_path)

    return citations


def _convert_pandoc_new(bibtex_string, csl_path):
    """
    Converts the PyBtex entry into formatted markdown citation text
    using pandoc version 2.11 or newer
    """
    markdown = pypandoc.convert_text(
        source=bibtex_string,
        to="markdown-citations",
        format="bibtex",
        extra_args=[
            "--citeproc",
            "--csl",
            csl_path,
        ],
    )

    # This should cut off the pandoc preamble and ending triple colons
    markdown = " ".join(markdown.split("\n")[2:-2])

    citation_regex = re.compile(r"\{\.csl-left-margin\}\[(.*)\]\{\.csl-right-inline\}")
    try:

        citation = citation_regex.findall(markdown.replace("\n", " "))[0]
    except IndexError:
        citation = markdown
    return citation.strip()


def _convert_pandoc_legacy(bibtex_string, csl_path):
    """
    Converts the PyBtex entry into formatted markdown citation text
    using pandoc version older than 2.11
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bib_path = Path(tmpdir).joinpath("temp.bib")
        with open(bib_path, "w") as bibfile:
            bibfile.write(bibtex_string)
        citation_text = """
---
nocite: '@*'
---
"""

        markdown = pypandoc.convert_text(
            source=citation_text,
            to="markdown_strict",
            format="md",
            extra_args=["--csl", csl_path, "--bibliography", bib_path],
            filters=["pandoc-citeproc"],
        )

    citation_regex = re.compile(r"[\d\.\\\s]*(.*)")
    citation = citation_regex.findall(markdown.replace("\n", " "))[0]
    return citation.strip()


def find_cite_keys(markdown):
    """
    Finds the cite keys in the markdown text
    This function can handle multiple keys in a single reference

    Args:
        markdown (str): the markdown text to be extract citation
                        keys from
    """

    cite_regex = re.compile(r"(\[(?:@\w+;{0,1}\s*)+\])")
    cite_keys = cite_regex.findall(markdown)
    return list(OrderedDict.fromkeys(cite_keys).keys())


def insert_citation_keys(citation_quads, markdown):
    """
    Insert citations into the markdown text replacing
    the old citation keys

    Args:
        citation_quads (tuple): a quad tuple of all citation info
        markdown (str): the markdown text to modify

    Returns:
        markdown (str): the modified Markdown
    """

    # Renumber quads if using numbers for citation links

    grouped_quads = [list(g) for _, g in groupby(citation_quads, key=lambda x: x[0])]
    for quad_group in grouped_quads:
        full_citation = quad_group[0][0]  # the first key in the whole citation
        replacement_citaton = "".join(["[^{}]".format(quad[2]) for quad in quad_group])
        markdown = markdown.replace(full_citation, replacement_citaton)

    return markdown


def format_bibliography(citation_quads):
    """
    Generates a bibliography from the citation quads

    Args:
        citation_quads (tuple): a quad tuple of all citation info

    Returns:
        markdown (str): the Markdown string for the bibliography
    """
    new_bib = {quad[2]: quad[3] for quad in citation_quads}
    bibliography = []
    for key, citation in new_bib.items():
        bibliography_text = "[^{}]: {}".format(key, citation)
        bibliography.append(bibliography_text)

    return "\n".join(bibliography)


def tempfile_from_url(url, suffix):
    for i in range(3):
        try:
            dl = requests.get(url)
            if dl.status_code != 200:
                raise RuntimeError(f"Couldn't download the url: {url}.\n Status Code: {dl.status_code}")

            file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
            file.write(dl.text)
            file.close()
            return file.name

        except requests.exceptions.RequestException:
            pass
    raise RuntimeError(f"Couldn't successfully download the url: {url}")
