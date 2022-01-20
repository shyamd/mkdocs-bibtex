import re
import tempfile
from itertools import groupby
from pathlib import Path

import pypandoc
from pybtex.database import BibliographyData


def to_markdown_pandoc(entry, csl_path):
    """
    Converts the PyBtex entry into formatted markdown citation text
    """
    bibtex_string = BibliographyData(entries={entry.key: entry}).to_string("bibtex")
    if tuple(int(ver) for ver in pypandoc.get_pandoc_version().split(".")) >= (
        2,
        11,
    ):
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

        citation_regex = re.compile(
            r"\{\.csl-left-margin\}\[(.*)\]\{\.csl-right-inline\}"
        )
        try:

            citation = citation_regex.findall(markdown)[0]
        except IndexError:
            citation = markdown
    else:
        # Older citeproc-filter version of pandoc
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

        citation_regex = re.compile(r"(1\.)?(.*)")
        citation = citation_regex.findall(markdown.replace("\n", " "))[0]
    return citation


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
    return list(cite_keys)


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
    if all(quad[2].isnumeric() for quad in citation_quads):
        citation_quads = [
            (quad[0], quad[1], str(n + 1), quad[2])
            for n, quad in enumerate(citation_quads)
        ]

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
