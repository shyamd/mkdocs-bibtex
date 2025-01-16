import time
import validators
from collections import OrderedDict
from pathlib import Path

from mkdocs.plugins import BasePlugin

from mkdocs_bibtex.citation import CitationBlock, Citation

from mkdocs_bibtex.config import BibTexConfig
from mkdocs_bibtex.registry import SimpleRegistry, PandocRegistry
from mkdocs.exceptions import ConfigurationError


from mkdocs_bibtex.utils import (
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
        self.registry = None

    def on_startup(self, *, command, dirty):
        """Having on_startup() tells mkdocs to keep the plugin object upon rebuilds"""
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

        # Clear references on reconfig
        self.all_references = OrderedDict()

        # Set CSL from either url or path (or empty)
        if self.config.csl_file is not None and validators.url(self.config.csl_file):
            self.csl_file = tempfile_from_url("CSL file", self.config.csl_file, ".csl")
        else:
            self.csl_file = self.config.csl_file

        if "{key}" not in self.config.footnote_format:
            raise ConfigurationError("Must include `{key}` placeholder in footnote_format")

        if self.csl_file:
            self.registry = PandocRegistry(
                bib_files=bibfiles, csl_file=self.csl_file, footnote_format=self.config.footnote_format
            )
        else:
            self.registry = SimpleRegistry(bib_files=bibfiles, footnote_format=self.config.footnote_format)

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

        # 1. Find all cite blocks in the markdown
        cite_blocks = CitationBlock.from_markdown(markdown)

        # 2. Validate the cite blocks
        self.registry.validate_citation_blocks(cite_blocks)

        # 3. Replace the cite blocks with the inline citations
        for block in cite_blocks:
            replacement = self.registry.inline_text(block)
            markdown = markdown.replace(str(block), replacement)

        # 4a. Esnure we have a bibliography if desired
        bib_command = self.config.bib_command

        if self.config.bib_by_default and markdown.count(bib_command) == 0:
            markdown += f"\n{bib_command}"

        # 4. Insert in the bibliopgrahy text into the markdown
        citations = OrderedDict()
        for block in cite_blocks:
            for citation in block.citations:
                citations[citation.key] = citation

        bibliography = []
        for citation in citations.values():
            try:
                bibliography.append(
                    "[^{}]: {}".format(
                        self.registry.footnote_format.format(key=citation.key), self.registry.reference_text(citation)
                    )
                )
            except Exception as e:
                log.warning(f"Error formatting citation {citation.key}: {e}")
        bibliography = "\n".join(bibliography)
        markdown = markdown.replace(bib_command, bibliography)

        # 5. Build the full Bibliography and insert into the text
        full_bib_command = self.config.full_bib_command
        if markdown.count(full_bib_command) > 0:
            log.info("Building full bibliography")
            all_citations = [Citation(key=key) for key in self.registry.bib_data.entries]
            blocks = [CitationBlock(citations=[cite]) for cite in all_citations]
            self.registry.validate_citation_blocks(blocks)
            full_bibliography = []
            for citation in all_citations:
                full_bibliography.append(
                    "[^{}]: {}".format(
                        self.registry.footnote_format.format(key=citation.key), self.registry.reference_text(citation)
                    )
                )
            full_bibliography = "\n".join(full_bibliography)
            markdown = markdown.replace(full_bib_command, full_bibliography)

        log.debug(f"Markdown: \n{markdown}")

        return markdown
