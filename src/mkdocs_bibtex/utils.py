# Python imports
import logging
import re
import requests
import tempfile
from functools import lru_cache
from pathlib import Path
from packaging.version import Version

# 3rd party imports
import mkdocs
import pypandoc

from pybtex.backends.markdown import Backend as MarkdownBackend
from pybtex.backends.html import Backend as HtmlBackend
from pybtex.database import BibliographyData, Entry
from pybtex.style.formatting.plain import Style as PlainStyle

# Local imports
from mkdocs_bibtex.type import *

# Grab a logger
log = logging.getLogger("mkdocs.plugins.mkdocs-bibtex")

# Add the warning filter only if the version is lower than 1.2
# Filter doesn't do anything since that version
MKDOCS_LOG_VERSION = "1.2"
if Version(mkdocs.__version__) < Version(MKDOCS_LOG_VERSION):
    from mkdocs.utils import warning_filter

    log.addFilter(warning_filter)


def format_simple(entry: Entry, html_backend: bool = False) -> str:
    """Format the entry using a simple builtin style.

    Args:
        entry (Entry): Bibliography entry.
        html_backend (bool): Format the entry as HTML if set to True.
            Format the entry as markdown otherwise.

    Returns:
        Citation formatted as markdown or HTML.
    """
    # Select style and backend
    style = PlainStyle()
    backend = HtmlBackend() if html_backend else MarkdownBackend()

    # Apply style to the entry
    formatted_entry = style.format_entry("", entry)
    entry_text = formatted_entry.text.render(backend)

    # Modify the entry before returning it
    return entry_text.replace("\n", " ").replace("\\(", "(").replace("\\)", ")").replace("\\.", ".")


def format_pandoc(entry: Entry, csl_path: str) -> str:
    """Format the entry using pandoc.

    Args:
        entry (Entry): Bibliography entry.
        csl_path (str): Path to formatting CSL File.
    Returns:
        Citation formatted as markdown.
    """
    # Grab the pandoc version
    pandoc_version = tuple(int(ver) for ver in pypandoc.get_pandoc_version().split("."))
    is_new_pandoc = pandoc_version >= (2, 11)

    # Apply styling
    bibtex_string = BibliographyData(entries={entry.key: entry}).to_string("bibtex")
    if is_new_pandoc:
        entry_text = _convert_pandoc_new(bibtex_string, csl_path)
    else:
        entry_text = _convert_pandoc_legacy(bibtex_string, csl_path)
    return entry_text


def _convert_pandoc_new(bibtex_string: str, csl_path: str) -> str:
    """Converts the PyBtex entry into formatted markdown citation text
    using pandoc version 2.11 or newer.

    Args:
        bibtex_string (str): Bibliography entry formatted as bibtex string.
        csl_path (str): Path to formatting CSL File.
    Returns:
        Citation formatted as markdown.
    """
    markdown = pypandoc.convert_text(
        source=bibtex_string,
        to="markdown_strict",
        format="bibtex",
        extra_args=[
            "--citeproc",
            "--csl",
            csl_path,
        ],
    )

    # Remove newlines from any generated span tag (non-capitalized words)
    markdown = " ".join(markdown.split("\n"))
    markdown = re.compile(r"<\/span>[\r\n]").sub("</span> ", markdown)
    citation_regex = re.compile(
        r"<span\s+class=\"csl-(?:left-margin|right-inline)\">(.+?)(?=<\/span>)<\/span>"
    )
    try:
        citation = citation_regex.findall(re.sub(r"(\r|\n)", "", markdown))[1]
    except IndexError:
        citation = markdown
    return citation.strip()


def _convert_pandoc_legacy(bibtex_string: str, csl_path: str) -> str:
    """Converts the PyBtex entry into formatted markdown citation text
    using pandoc version older than 2.11.

    Args:
        bibtex_string (str): Bibliography entry formatted as bibtex string.
        csl_path (str): Path to formatting CSL File.
    Returns:
        Citation formatted as markdown.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bib_path = Path(tmpdir).joinpath("temp.bib")
        with open(bib_path, "wt", encoding="utf-8") as bibfile:
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


def extract_cite_keys(cite_block: str) -> list[str]:
    """Extract just the keys from a cite block.

    Args:
        cite_block (str): Cite block extracted from an mkdocs page.

    Returns:
        List of cite keys contained in the cite block.
    """
    cite_regex = re.compile(r"@([\w\.:-]*)")
    cite_keys = re.findall(cite_regex, cite_block)
    return cite_keys


def find_cite_blocks(markdown: str) -> list[str]:
    """Finds entire cite blocks in the markdown text.

    Args:
        markdown (str): The markdown text to be extract citation
                        blocks from

    Regex explanation:
    - first group  (1): everything. (the only thing we need)
    - second group (2): (?:(?:\[(-{0,1}[^@]*)) |\[(?=-{0,1}@))
    - third group  (3): ((?:-{0,1}@\w*(?:; ){0,1})+)
    - fourth group (4): (?:[^\]\n]{0,1} {0,1})([^\]\n]*)

    The first group captures the entire cite block, as is
    The second group captures the prefix, which is everything between '[' and ' @| -@'
    The third group captures the citekey(s), ';' separated (affixes NOT supported)
    The fourth group captures anything after the citekeys, excluding the leading whitespace
    (The non-capturing group removes any symbols or whitespaces between the citekey and suffix)

    Matches for [see @author; @doe my suffix here]
        [0] entire block: '[see @author; @doe my suffix here]'
        [1] prefix: 'see'
        [2] citekeys: '@author; @doe'
        [3] suffix: 'my suffix here'

    Does NOT match: [mail@example.com]
    DOES match [mail @example.com] as [mail][@example][com]

    Returns:
        A list of citation blocks.
    """
    # Generate the regex
    r = r"((?:(?:\[(-{0,1}[^@]*)) |\[(?=-{0,1}@))((?:-{0,1}@\w*(?:; ){0,1})+)(?:[^\]\n]{0,1} {0,1})([^\]\n]*)\])"
    cite_regex = re.compile(r)

    # Extract the citation blocks from the markdown
    return [
        # We only care about the block (group 1)
        (matches.group(1))
        for matches in re.finditer(cite_regex, markdown)
    ]


def insert_citation_keys_footnote(
    citation_index: CitationIndex, mapping: CitationBlockMapping, markdown: str
) -> str:
    """Insert citations into the markdown text replacing the old citation keys.
    This function inserts the citations as footnotes.

    Args:
        citation_index (CitationIndex): Citation index containing bibliography entries.
        mapping (CitationBlockMapping): Mapping from cite blocks to the cite keys they contain.
        markdown (str): Markdown text to modify.

    Returns:
        Modified markdown.
    """
    # Generate the footnore with the correct format and inject in markdown
    for cite_group, cite_keys in mapping.items():
        replacement_citaton = "".join(
            ["[^{}]".format(citation_index[cite_key].ref) for cite_key in cite_keys]
        )
        markdown = markdown.replace(cite_group, replacement_citaton)
    return markdown


def insert_citation_keys_link(
    citation_index: CitationIndex, mapping: CitationBlockMapping, markdown: str
) -> str:
    """Insert citations into the markdown text replacing the old citation keys.
    This function inserts the citations as a link to a bibliography.

    Args:
        citation_index (CitationIndex): Citation index containing bibliography entries.
        mapping (CitationBlockMapping): Mapping from cite blocks to the cite keys they contain.
        markdown (str): Markdown text to modify.

    Returns:
        Modified markdown.
    """
    # Generate the link with the correct format and inject in markdown
    for cite_group, cite_keys in mapping.items():
        replacement_citaton = ", ".join(
            [
                "[{}]({}#{})".format(
                    citation_index[cite_key].idx,
                    citation_index[cite_key].page,
                    citation_index[cite_key].ref,
                )
                for cite_key in cite_keys
            ]
        )
        replacement_citaton = "[" + replacement_citaton + "]"
        markdown = markdown.replace(cite_group, replacement_citaton)
    return markdown


def insert_citation_keys_inline(
    citation_index: CitationIndex, mapping: CitationBlockMapping, markdown: str, csl_path: str, bib
) -> str:
    """Insert citations into the markdown text replacing the old citation keys.
    This function inserts the citations as inline citations.

    Args:
        citation_index (CitationIndex): Citation index containing bibliography entries.
        mapping (CitationBlockMapping): Mapping from cite blocks to the cite keys they contain.
        markdown (str): Markdown text to modify.
        csl_path (str): Path the CSL file used to format the citations.
        bib

    Returns:
        Modified markdown.
    """
    # Generate the link with the correct format and inject in markdown
    for cite_group, cite_keys in mapping.items():
        replacement_citaton = "".join(
            ["[^{}]".format(citation_index[cite_key].ref) for cite_key in cite_keys]
        )

        # Verify that the pandoc installation is newer than 2.11
        pandoc_version = pypandoc.get_pandoc_version()
        pandoc_version_tuple = tuple(int(ver) for ver in pandoc_version.split("."))
        if pandoc_version_tuple <= (2, 11):
            raise RuntimeError(
                f"Your version of pandoc (v{pandoc_version}) is "
                "incompatible with the cite_inline feature."
            )

        # Convert full_citation with pandoc and add to replacement_citaton
        log.debug(f"--Rendering citation inline for {cite_group!r}...")
        inline_citation = _convert_pandoc_citekey(bib, csl_path, cite_group)
        replacement_citaton = f" {inline_citation}{replacement_citaton}"

        # Make sure inline citations doesn't get an extra whitespace by
        # replacing it with whitespace added first
        markdown = markdown.replace(f" {cite_group}", replacement_citaton)
        log.debug(f"--SUCCESS Rendering citation inline for {cite_group!r}")

        # Replace full citations with footnotes
        markdown = markdown.replace(cite_group, replacement_citaton)
    return markdown


def format_bibliography_footnote(citation_index: CitationIndex) -> str:
    """Generates a footnote bibliography from the citation index.

    Args:
        citation_index (CitationIndex): Citation index containing bibliography entries.

    Returns:
        Markdown string for the bibliography.
    """
    bibliography = []
    for _, value in citation_index.items():
        bibliography_text = "[^{}]: {}".format(value.ref, value.formatted_md)
        bibliography.append(bibliography_text)
    return "\n".join(bibliography)


def format_bibliography_link(citation_index: CitationIndex) -> str:
    """Generates a link bibliography from the citation index.

    Args:
        citation_index (CitationIndex): Citation index containing bibliography entries.

    Returns:
        Markdown string for the bibliography.
    """
    # Generate a list of HTML table strings containing the rows of the bibliography
    bibliography = []
    for _, value in citation_index.items():
        table_cell_ref = '<td style="border:none; padding: 0.5vw;">[{}]</td>'.format(value.idx)
        table_cell_bib = '<td style="border:none; padding: 0.5vw;">{}</td>'.format(
            value.formatted_html
        )
        table_row = '<tr style="all: unset;" id="{}"> {} {} </tr>'.format(
            value.ref, table_cell_ref, table_cell_bib
        )
        bibliography.append(table_row)

    # Merge the rows into a full HTML table
    output = "\n".join(bibliography)
    output = '<table style="all: unset; border-collapse:collapse;">' + output + "</table>"
    return output


def tempfile_from_url(name, url, suffix) -> str:
    log.debug(f"Downloading {name} from URL {url} to temporary file...")
    for i in range(3):
        try:
            dl = requests.get(url)
            if dl.status_code != 200:  # pragma: no cover
                raise RuntimeError(
                    f"Couldn't download the url: {url}.\n Status Code: {dl.status_code}"
                )

            file = tempfile.NamedTemporaryFile(
                mode="wt", encoding="utf-8", suffix=suffix, delete=False
            )
            file.write(dl.text)
            file.close()
            log.info(f"{name} downladed from URL {url} to temporary file ({file})")
            return file.name

        except requests.exceptions.RequestException:  # pragma: no cover
            pass
    raise RuntimeError(f"Couldn't successfully download the url: {url}")  # pragma: no cover


@lru_cache(maxsize=1024)
def _convert_pandoc_citekey(bibtex_string: str, csl_path: str, fullcite: str) -> str:
    """Uses pandoc to convert a markdown citation key reference
    to a rendered markdown citation in the given CSL format.

        Limitation (atleast for harvard.csl): multiple citekeys
        REQUIRE a '; ' separator to render correctly:
            - [see @test; @test2] Works
            - [see @test and @test2] Doesn't work

    Args:
        bibtex_string (str): Bibliography entry formatted as bibtex string.
        csl_path (str): Path to formatting CSL File.
        fullcite (str): Cite group string.
    Returns:
        Citation formatted as markdown.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bib_path = Path(tmpdir).joinpath("temp.bib")
        with open(bib_path, "wt", encoding="utf-8") as bibfile:
            bibfile.write(bibtex_string)

        log.debug(
            f"----Converting pandoc citation key {fullcite!r} with CSL file {csl_path!r} and Bibliography file"
            f" '{bib_path!s}'..."
        )
        markdown = pypandoc.convert_text(
            source=fullcite,
            to="markdown-citations",
            format="markdown",
            extra_args=["--citeproc", "--csl", csl_path, "--bibliography", bib_path],
        )
        log.debug(
            f"----SUCCESS Converting pandoc citation key {fullcite!r} with CSL file {csl_path!r} and "
            f"Bibliography file '{bib_path!s}'"
        )

    # Return only the citation text (first line(s))
    # remove any extra linebreaks to accommodate large author names
    markdown = re.compile(r"[\r\n]").sub("", markdown)
    return markdown.split(":::")[0].strip()
