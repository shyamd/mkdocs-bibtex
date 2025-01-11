import re
import time
import validators
from collections import OrderedDict
from pathlib import Path

from mkdocs.plugins import BasePlugin
from pybtex.database import BibliographyData, parse_file

from mkdocs_bibtex.config import BibTexConfig
from mkdocs.exceptions import ConfigurationError


from mkdocs_bibtex.utils import (
    find_cite_blocks,
    extract_cite_keys,
    format_bibliography,
    format_pandoc,
    format_simple,
    insert_citation_keys,
    tempfile_from_url,
    log,
)


class BibTexPlugin(BasePlugin[BibTexConfig]):
    """
    Allows the use of bibtex in markdown content for MKDocs.
    """

    def __init__(self):
        self.bib_data = None
        self.all_references = OrderedDict()
        self.last_configured = None

    def on_startup(self, *, command, dirty):
        """ Having on_startup() tells mkdocs to keep the plugin object upon rebuilds"""
        pass

    def on_config(self, config):
        """
        Loads bibliography on load of config
        """

        bibfiles = []

        # Set bib_file from either url or path
        if self.config.bib_file is not None:
            is_url = validators.url(self.config.bib_file)
            # if bib_file is a valid URL, cache it with tempfile
            if is_url:
                bibfiles.append(tempfile_from_url("bib file", self.config.bib_file, ".bib"))
            else:
                bibfiles.append(self.config.bib_file)
        elif self.config.bib_dir is not None:
            bibfiles.extend(Path(self.config.bib_dir).rglob("*.bib"))
        else:  # pragma: no cover
            raise ConfigurationError("Must supply a bibtex file or directory for bibtex files")

        # Skip rebuilding bib data if all files are older than the initial config
        if self.last_configured is not None:
            if all(Path(bibfile).stat().st_mtime < self.last_configured for bibfile in bibfiles):
                log.info("BibTexPlugin: No changes in bibfiles.")
                return config

        # load bibliography data
        refs = {}
        log.info(f"Loading data from bib files: {bibfiles}")
        for bibfile in bibfiles:
            log.debug(f"Parsing bibtex file {bibfile}")
            bibdata = parse_file(bibfile)
            refs.update(bibdata.entries)

        # Clear references on reconfig
        self.all_references = OrderedDict()

        self.bib_data = BibliographyData(entries=refs)
        self.bib_data_bibtex = self.bib_data.to_string("bibtex")

        # Set CSL from either url or path (or empty)
        if self.config.csl_file is not None and validators.url(self.config.csl_file):
            self.csl_file = tempfile_from_url("CSL file", self.config.csl_file, ".csl")
        else:
            self.csl_file = self.config.csl_file

        # Toggle whether or not to render citations inline (Requires CSL)
        if self.config.cite_inline and not self.csl_file:  # pragma: no cover
            raise ConfigurationError("Must supply a CSL file in order to use cite_inline")

        if "{number}" not in self.config.footnote_format:
            raise ConfigurationError("Must include `{number}` placeholder in footnote_format")

        self.last_configured = time.time()
        return config

    def on_page_markdown(self, markdown, page, config, files):
        """
        Parses the markdown for each page, extracting the bibtex references
        If a local reference list is requested, this will render that list where requested

        1. Finds all cite keys (may include multiple citation references)
        2. Convert all cite keys to citation quads:
            (full cite key,
            individual cite key,
            citation key in corresponding style,
            citation for individual cite key)
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
        if self.config.cite_inline:
            markdown = insert_citation_keys(
                citation_quads,
                markdown,
                self.csl_file,
                self.bib_data_bibtex,
            )
        else:
            markdown = insert_citation_keys(citation_quads, markdown)

        # 4. Insert in the bibliopgrahy text into the markdown
        bib_command = self.config.bib_command

        if self.config.bib_by_default:
            markdown += f"\n{bib_command}"

        bibliography = format_bibliography(citation_quads)
        markdown = re.sub(
            re.escape(bib_command),
            bibliography,
            markdown,
        )

        # 5. Build the full Bibliography and insert into the text
        full_bib_command = self.config.full_bib_command

        markdown = re.sub(
            re.escape(full_bib_command),
            self.full_bibliography,
            markdown,
        )

        return markdown

    def format_footnote_key(self, number):
        """
        Create footnote key based on footnote_format

        Args:
            number (int): citation number

        Returns:
            formatted footnote
        """
        return self.config.footnote_format.format(number=number)

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
        log.debug("Formatting all bib entries...")
        if self.csl_file:
            self.all_references.update(format_pandoc(entries, self.csl_file))
        else:
            self.all_references.update(format_simple(entries))
        log.debug("SUCCESS Formatting all bib entries")

        # 4. Construct quads
        quads = [
            (
                cite_block,
                key,
                self.format_footnote_key(numbers[key]),
                self.all_references[key],
            )
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
            bibliography_text = "[^{}]: {}".format(
                number,
                citation,
            )
            bibliography.append(bibliography_text)

        return "\n".join(bibliography)
