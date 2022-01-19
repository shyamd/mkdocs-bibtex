import re
from pathlib import Path
import tempfile
from collections import OrderedDict

import pypandoc
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from pybtex.backends.markdown import Backend as MarkdownBackend
from pybtex.database import BibliographyData, parse_file
from pybtex.style.formatting.plain import Style as PlainStyle


class BibTexPlugin(BasePlugin):
    """
    Allows the use of bibtex in markdown content for MKDocs.

    Options:
        bib_file (string): path to a single bibtex file for entries
        bib_dir (string): path to a directory of bibtex files for entries
        bib_command (string): command to place a bibliography relevant to just that file
                              defaults to \bibliography
        full_bib_command (string): command to place a full bibliography of all references
        csl_file (string, optional): path to a CSL file, relative to mkdocs.yml.
    """

    config_scheme = [
        ("bib_file", config_options.File(exists=True, required=False)),
        ("bib_dir", config_options.Dir(exists=True, required=False)),
        ("bib_command", config_options.Type(str, default="\\bibliography")),
        ("full_bib_command", config_options.Type(str, default="\\full_bibliography")),
        ("csl_file", config_options.File(exists=True, required=False)),
        ("unescape_for_arithmatex", config_options.Type(bool, required=False)),
    ]

    def __init__(self):
        self.bib_data = None
        self.all_references = OrderedDict()
        self.unescape_for_arithmatex = False

    def on_config(self, config):
        """
        Loads bibliography on load of config
        """

        bibfiles = []

        if self.config.get("bib_file", None) is not None:
            bibfiles.append(self.config["bib_file"])
        elif self.config.get("bib_dir", None) is not None:
            bibfiles.extend(Path(self.config["bib_dir"]).glob("*.bib"))
        else:
            raise Exception("Must supply a bibtex file or directory for bibtex files")

        # load bibliography data
        refs = {}
        for bibfile in bibfiles:
            bibdata = parse_file(bibfile)
            refs.update(bibdata.entries)

        self.bib_data = BibliographyData(entries=refs)

        self.csl_file = self.config.get("csl_file", None)

        self.unescape_for_arithmatex = self.config.get("unescape_for_arithmatex", False)

        return config

    def on_page_markdown(self, markdown, page, config, files):
        """
        Parses the markdown for each page, extracting the bibtex references
        If a local reference list is requested, this will render that list where requested

        1. Finds all cite keys (may include multiple citation references)
        2. Convert all cite keys to citation quads: 
            (full cite key,
            induvidual cite key,
            citation key in corresponding style,
            citation for induvidual cite key)
        3. Insert formatted cite keys into text
        4. Insert the bibliography into the markdown
        5. Insert the full bibliograph into the markdown
        """

        # 1. Grab all the cited keys in the markdown
        cite_keys = find_cite_keys(markdown)

        # 2. Convert all the citations to text references
        citation_quads = self.format_citations(cite_keys)

        # 3. Insert in numbers into the main markdown and build bibliography
        markdown = insert_citation_keys(citation_quads,markdown)

        # 4. Insert in the bibliopgrahy text into the markdown
        bibliography = format_bibliography(citation_quads)
        markdown = re.sub(
            re.escape(self.config.get("bib_command", "\\bibliography")),
            bibliography,
            markdown,
        )

        # 5. Build the full Bibliography and insert into the text
        markdown = re.sub(
            re.escape(self.config.get("full_bib_command", "\\full_bibliography")),
            self.full_bibliography,
            markdown,
        )

        return markdown

    def format_citations(self, cite_keys):
        """
        Formats references into citation quads and adds them to the global registry

        Args:
            cite_keys (list): List of full cite_keys that maybe compound keys

        Returns:
            citation_quads: quad tupples of the citation inforamtion
        """
        pass

    @property
    def full_bibliography(self):
        """
        Returns the full bibliography text
        """
        full_bibliography = []

        for number, key in enumerate(self.all_references.keys()):
            bibliography_text = "{}: {}".format(number + 1, self.all_references[key])
            full_bibliography.append(bibliography_text)

        return "\n".join(full_bibliography)


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

        citation_regex = re.compile(r"(?:1\.)?(.*)")
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

    cite_regex = re.compile(r"\[((?:@\w+;{0,1}\s*)+)\]")
    cite_keys = cite_regex.findall(markdown)
    return list(cite_keys)


def insert_citation_keys(citation_quads,markdown):
    """
    Insert citations into the markdown text replacing
    the old citation keys

    Args:
        citation_quads (tuple): a quad tuple of all citation info
        markdown (str): the markdown text to modify

    Returns:
        markdown (str): the modified Markdown
    """
    pass


def format_bibliography(citation_quads):
    """
    Generates a bibliography from the citation quads

    Args:
        citation_quads (tuple): a quad tuple of all citation info
    
    Returns:
        markdown (str): the Markdown string for the bibliography
    """
    pass