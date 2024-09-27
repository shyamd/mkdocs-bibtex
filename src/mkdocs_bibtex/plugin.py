# Python imports
import re
import time
import validators
from pathlib import Path
from typing import Optional, Tuple

# 3rd party imports
from mkdocs.plugins import BasePlugin
from mkdocs.exceptions import ConfigurationError
from pybtex.database import BibliographyData, parse_file

# Local imports
from mkdocs_bibtex import utils
from mkdocs_bibtex.config import BibTexConfig
from mkdocs_bibtex.type import *


class BibTexPlugin(BasePlugin[BibTexConfig]):
    """BibTex plugin that makes bibtex available in mkdocs."""

    def __init__(self):
        # Path to a CSL file
        self.csl_file: Optional[str] = None
        # Time at which the bibliography files were last parsed
        self.last_configured: Optional[float] = None
        # Index of citations of the whole website
        self.global_citation_index: CitationIndex = {}
        # Mapping from cite groups to a list of cite keys contained within
        self.global_mapping: CitationBlockMapping = {}
        # Available bibliography entries
        self.bib_data = None
        self.bib_data_bibtex = None

    def on_startup(self, *, command, dirty: bool):
        """Having on_startup() tells mkdocs to keep the plugin object upon rebuilds"""
        pass

    def on_config(self, config):
        """Loads bibliography on load of config"""
        # List of file paths containing bibliography entries
        bibfiles: list[str] = []

        # Set bib files from either URL or path
        if self.config.get("bib_file", None) is not None:
            # If bib_file is a valid URL, cache it with tempfile
            is_url = validators.url(self.config["bib_file"])
            if is_url:
                bibfiles.append(
                    utils.tempfile_from_url("bib file", self.config["bib_file"], ".bib")
                )
            # If it is not an URL, treat is as a local path
            else:
                bibfiles.append(self.config["bib_file"])

        # Set bib files from directory
        elif self.config.get("bib_dir", None) is not None:
            bibfiles.extend(Path(self.config["bib_dir"]).rglob("*.bib"))
        else:  # pragma: no cover
            raise ConfigurationError("Must supply a bibtex file or directory for bibtex files")

        # Set CSL from either url or path (or empty)
        is_url = validators.url(self.config["csl_file"])
        if is_url:
            self.csl_file = utils.tempfile_from_url("CSL file", self.config["csl_file"], ".csl")
        else:
            self.csl_file = self.config["csl_file"]

        # Toggle whether or not to render citations inline (Requires CSL)
        if self.config.cite_format == CiteFormat.INLINE and not self.csl_file:  # pragma: no cover
            raise ConfigurationError("Must supply a CSL file in order to use cite_inline")

        # Handle footnote format
        if "{number}" not in self.config.ref_format and "{key}" not in self.config.ref_format:
            raise ConfigurationError(
                "Must include `{number}` or `{key}` placeholders in ref_format"
            )

        # Skip rebuilding bib data if all files are older than the initial config
        if self.last_configured is not None and all(
            Path(bibfile).stat().st_mtime < self.last_configured for bibfile in bibfiles
        ):
            utils.log.info("[bibtex] No changes in bibfiles.")
        else:
            # Load bibliography data
            utils.log.info(f"[bibtex] Loading data from bib files: {bibfiles}")
            self.refresh_bib_data(bibfiles)
            self.last_configured = time.time()
        return config

    def refresh_bib_data(self, bibfiles: list[str]):
        refs = {}
        for bibfile in bibfiles:
            utils.log.debug(f"[bibtex] Parsing bibtex file {bibfile}")
            bibdata = parse_file(bibfile)
            refs.update(bibdata.entries)

        # Rebuild bibliography data
        self.bib_data = BibliographyData(entries=refs)
        self.bib_data_bibtex = self.bib_data.to_string("bibtex")

    def on_files(self, files, config):
        """Build global index if configured for global bibliography."""
        # Build the index once for a global bibliography with unique numbering
        if self.config.bib_type == BibType.GLOBAL:
            utils.log.info("[bibtex] Building global bibliography index")

            # Extract all cite keys from all pages
            cite_keys: list[str] = []
            for file in files:
                if file.is_documentation_page():
                    cite_keys.extend(utils.find_cite_blocks(file.content_string))

            # Generating the index
            self.global_citation_index, self.global_mapping = self.generate_index(cite_keys)
        else:
            utils.log.info("[bibtex] Global bibliography index not generated")
        return files

    def on_page_markdown(self, markdown, page, config, files) -> str:
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
        # If configured for a local bibliography, configured a local index
        if self.config.bib_type == BibType.PER_PAGE:
            utils.log.debug("[bibtex] Generating local bibliography index for page: %s", page.title)
            cite_keys = utils.find_cite_blocks(markdown)
            citation_index, mapping = self.generate_index(cite_keys)
        else:
            citation_index = self.global_citation_index
            mapping = self.global_mapping

        # Convert cited keys to citation
        utils.log.debug("[bibtex] Replacing citation keys with the generated ones")
        if self.config.cite_format == CiteFormat.INLINE:
            markdown = utils.insert_citation_keys_inline(
                citation_index,
                markdown,
                self.csl_file,
                self.bib_data_bibtex,
            )
        elif self.config.cite_format == CiteFormat.FOOTNOTE:
            markdown = utils.insert_citation_keys_footnote(citation_index, mapping, markdown)
        elif self.config.cite_format == CiteFormat.LINK:
            markdown = utils.insert_citation_keys_link(citation_index, mapping, markdown)

        # Automatically insert the per page bibliography if configured
        if self.config.automatic_per_page:
            markdown += f"\n{self.config.per_page_bib_command}"

        # Insert a local bibliography per page and remove global tags
        if self.config.bib_type == BibType.PER_PAGE:
            add_line = self.config.cite_format == CiteFormat.LINK
            markdown = re.sub(
                re.escape(self.config.per_page_bib_command),
                self.generate_bibliography(citation_index, add_line),
                markdown,
            )
            markdown = re.sub(re.escape(self.config.global_bib_command), "", markdown)

        # Insert a global bibliography and remove the local tags
        elif self.config.bib_type == BibType.GLOBAL:
            markdown = re.sub(
                re.escape(self.config.global_bib_command),
                self.generate_bibliography(citation_index),
                markdown,
            )
            markdown = re.sub(re.escape(self.config.per_page_bib_command), "", markdown)
        return markdown

    def generate_index(self, cite_keys: list[str]) -> Tuple[CitationIndex, CitationBlockMapping]:
        """Formats a list of citations into a citation index

        Args:
            cite_keys: List of full cite keys that may be compound keys

        Returns:
            Citation index containing all unique citations and the metadata
            needed to render the corresponding key and the bibliography.
        """
        # Go through all citations in the cite keys and split compound citations
        index: CitationIndex = {}
        mapping: CitationBlockMapping = {}
        idx = 1
        for cite_block in cite_keys:
            mapping[cite_block] = []
            for key in utils.extract_cite_keys(cite_block):

                # Check if the key in the bibliography
                if key not in self.bib_data.entries:
                    utils.log.warning("[bibtex] %s not found in bibliography entries", key)
                    continue

                # If we don't have the key in the index, create a new entry
                if key not in index:

                    # Format the key for markdown
                    entry = self.bib_data.entries[key]
                    if self.config.csl_file is not None:
                        formatted_md = utils.format_pandoc(entry, self.csl_file)
                    else:
                        formatted_md = utils.format_simple(entry)

                    # Generate a link to the reference
                    ref = self.config.ref_format
                    ref = re.sub(re.escape("{number}"), str(idx), ref)
                    ref = re.sub(re.escape("{key}"), key, ref)
                    page = (
                        self.config.global_bib_ref if self.config.bib_type == BibType.GLOBAL else ""
                    )

                    # Create the index entry
                    index[key] = CitationIndexEntry(
                        idx=idx,
                        formatted_html=utils.format_simple(entry, html_backend=True),
                        formatted_md=formatted_md,
                        ref=ref,
                        page=page,
                    )
                    idx += 1

                mapping[cite_block].append(key)

        return (index, mapping)

    def generate_bibliography(self, index: CitationIndex, add_line=False) -> str:
        # Generate bibliography depending on the selected citation type
        if self.config.cite_format in [CiteFormat.FOOTNOTE, CiteFormat.INLINE]:
            bibliography = utils.format_bibliography_footnote(index)
        elif self.config.cite_format == CiteFormat.LINK:
            bibliography = utils.format_bibliography_link(index)

        # Add a separator line in front of the bibliography if requested
        if add_line and len(index) != 0:
            bibliography = "\n---\n" + bibliography
        return bibliography
