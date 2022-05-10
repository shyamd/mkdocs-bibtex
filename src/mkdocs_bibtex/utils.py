import re
import tempfile
from collections import OrderedDict
from itertools import groupby
from pathlib import Path

import pypandoc
from pybtex.backends.markdown import Backend as MarkdownBackend
from pybtex.database import BibliographyData  # , parse_string
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

    """
    regex explanation:
    - first group: everything.
    - second group: (?:(?:\[([^@]*)) |\[(?=@))
    - third group: ((?:@\w*(?:; ){0,1})+)
    - fourth group: (?:[^\]\n]{0,1} {0,1})([^\]\n]*)
    - End: \]

    The first group captures the entire block, as is
    The second group captures the prefix, which is everything between '[' and ' @' (whitespace)
    The third group captures the citekey(s), from '@' to any symbol that isnt '; '
    The fourth group captures anything after the citekeys, excluding the leading whitespace
    (The non-capturing group removes any symbols or whitespaces between the citekey and suffix)

    Matches for [see @author; @doe my suffix here]
        [0] entire block: '[see @author; @doe my suffix here]'
        [1] prefix: 'see'
        [2] citekeys: '@author; @doe' (';' separated)
        [3] suffix: 'my suffix here'

    Does NOT match: [mail@example.com]
    DOES match [mail @example.com] as [mail][@example][com]
    """
    cite_regex = re.compile(r"((?:(?:\[([^@]*)) |\[(?=@))((?:@\w*(?:; ){0,1})+)(?:[^\]\n]{0,1} {0,1})([^\]\n]*)\])")
    citation_blocks = re.finditer(cite_regex, markdown)

    cite_keys = [
        # fullcite, citekeys
        ([x.group(1), x.group(3)])
        for x in citation_blocks
    ]
    return cite_keys


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
        full_citation = quad_group[0][0]  # the full citation block
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


def add_affix(entry, type, regex, data):
    try:
        entry.fields[type] = regex.findall(data)[0]
        return entry
    except Exception:
        return entry


def add_affixes(entry, fullcite, key):
    prefix = fullcite.split(key)[0].strip('[').strip('@')
    suffix = fullcite.split(key)[1].strip(']').strip('@')
    if prefix is not None:
        entry.fields['note'] = prefix

    # I figure something like this should work
    # parse_string(fullcite, 'bibtex')

    pages = re.compile(r"(?:p. (\d+-{0,1}\d+))")  # p. nn(-nn)
    # book = re.compile(r"(?:book (\d+-{0,1}\d+))")  # book nn(-nn)
    # chapter = re.compile(r"(?:ch. (\d+-{0,1}\d+))")  # ch. nn(-nn)
    """
    column = ''
    figure = ''
    folio = ''
    issue = ''
    line = ''
    note = ''
    opus = ''
    paragraph = ''
    part = ''
    section = ''
    sub_verbo = ''
    volume = ''
    verse = ''
    """

    entry = add_affix(entry, 'pages', pages, suffix)
    # entry = add_affix(entry, 'book', book, suffix)
    # entry = add_affix(entry, 'chapter', chapter, suffix)

    return entry
