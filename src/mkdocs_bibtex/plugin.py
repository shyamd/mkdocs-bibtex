import re
import validators
from collections import OrderedDict
from pathlib import Path

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from pybtex.database import BibliographyData, parse_file

from mkdocs_bibtex.utils import (
    find_cite_blocks,
    extract_cite_keys,
    format_bibliography,
    format_pandoc,
    format_simple,
    insert_citation_keys,
    tempfile_from_url,
)


class BibTexPlugin(BasePlugin):
    """
    Allows the use of bibtex in markdown content for MKDocs.

    Options:
        bib_file (string): path or url to a single bibtex file for entries,
                           url example: https://api.zotero.org/*/items?format=bibtex
        bib_dir (string): path to a directory of bibtex files for entries
        bib_command (string): command to place a bibliography relevant to just that file
                              defaults to \bibliography
        bib_by_default (bool): automatically appends bib_command to markdown pages
                               by default, defaults to true
        full_bib_command (string): command to place a full bibliography of all references
        csl_file (string, optional): path or url to a CSL file, relative to mkdocs.yml.
        cite_inline (bool): Whether or not to render inline citations, requires CSL, defaults to false
    """

    config_scheme = [
        ("bib_file", config_options.Type(str, required=False)),
        ("bib_dir", config_options.Dir(exists=True, required=False)),
        ("bib_command", config_options.Type(str, default="\\bibliography")),
        ("bib_by_default", config_options.Type(bool, default=True)),
        ("full_bib_command", config_options.Type(str, default="\\full_bibliography")),
        ("csl_file", config_options.Type(str, default='')),
        ("cite_inline", config_options.Type(bool, default=False)),
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

        # Set bib_file from either url or path
        if self.config.get("bib_file", None) is not None:
            is_url = validators.url(self.config["bib_file"])
            # if bib_file is a valid URL, cache it with tempfile
            if is_url:
                bibfiles.append(tempfile_from_url(self.config["bib_file"], '.bib'))
            else:
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

        # Set CSL from either url or path (or empty)
        is_url = validators.url(self.config["csl_file"])
        if is_url:
            self.csl_file = tempfile_from_url(self.config["csl_file"], '.csl')
        else:
            self.csl_file = self.config.get("csl_file", None)

        # Toggle whether or not to render citations inline (Requires CSL)
        self.cite_inline = self.config.get("cite_inline", False)
        if self.cite_inline and not self.csl_file:
            raise Exception("Must supply a CSL file in order to use cite_inline")

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
        cite_keys = find_cite_blocks(markdown)

        # 2. Convert all the citations to text references
        citation_quads = self.format_citations(cite_keys)

        # 3. Convert cited keys to citation,
        # or a footnote reference if inline_cite is false.
        if self.cite_inline:
            markdown = insert_citation_keys(citation_quads, markdown, self.csl_file,
                                            self.bib_data.to_string("bibtex"))
        else:
            markdown = insert_citation_keys(citation_quads, markdown)

        # 4. Insert in the bibliopgrahy text into the markdown
        bib_command = self.config.get("bib_command", "\\bibliography")

        if self.config.get("bib_by_default"):
            markdown += f"\n{bib_command}"

        bibliography = format_bibliography(citation_quads)
        markdown = re.sub(
            re.escape(bib_command),
            bibliography,
            markdown,
        )

        # 5. Build the full Bibliography and insert into the text
        full_bib_command = self.config.get("full_bib_command", "\\full_bibliography")

        markdown = re.sub(
            re.escape(full_bib_command),
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
            citation_quads: quad tuples of the citation inforamtion
        """

        # Deal with arithmatex fix at some point

        # 1. Extract the keys from the keyset
        entries = OrderedDict()
        pairs = [
            [cite_block, key]
            for cite_block in cite_keys
            for key in extract_cite_keys(cite_block)
        ]
        keys = list(OrderedDict.fromkeys([k for _, k in pairs]).keys())
        numbers = {k: str(n + 1) for n, k in enumerate(keys)}

        # Remove non-existant keys from pairs
        pairs = [p for p in pairs if p[1] in self.bib_data.entries]

        # 2. Collect any unformatted reference keys
        for _, key in pairs:
            if key not in self.all_references:
                entries[key] = self.bib_data.entries[key]

        # 3. Format entries
        if self.csl_file:
            self.all_references.update(format_pandoc(entries, self.csl_file))
        else:
            self.all_references.update(format_simple(entries))

        # 4. Construct quads
        quads = [
            (cite_block, key, numbers[key], self.all_references[key])
            for cite_block, key in pairs
        ]

        # List the quads in order to remove duplicate entries
        return list(dict.fromkeys(quads))

    @property
    def full_bibliography(self):
        """
        Returns the full bibliography text
        """

        bibliography = []
        for number, (key, citation) in enumerate(self.all_references.items()):
            bibliography_text = "[^{}]: {}".format(number, citation)
            bibliography.append(bibliography_text)

        return "\n".join(bibliography)
