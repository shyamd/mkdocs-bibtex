from functools import cached_property
from typing import Union
from abc import ABC, abstractmethod
from mkdocs_bibtex.citation import Citation, CitationBlock, InlineReference
from mkdocs_bibtex.utils import log
from pybtex.database import BibliographyData, parse_file
from pybtex.backends.markdown import Backend as MarkdownBackend
from pybtex.style.formatting.plain import Style as PlainStyle
import pypandoc
import tempfile
import re
from pathlib import Path


class ReferenceRegistry(ABC):
    """
    A registry of references that can be used to format citations
    """

    def __init__(self, bib_files: list[str], footnote_format: str = "{key}"):
        refs = {}
        log.info(f"Loading data from bib files: {bib_files}")
        for bibfile in bib_files:
            log.debug(f"Parsing bibtex file {bibfile}")
            bibdata = parse_file(bibfile)
            refs.update(bibdata.entries)
        self.bib_data = BibliographyData(entries=refs)
        self.footnote_format = footnote_format

    @abstractmethod
    def validate_citation_blocks(self, citation_blocks: list[CitationBlock]) -> None:
        """Validates all citation blocks. Throws an error if any citation block is invalid"""

    @abstractmethod
    def validate_inline_references(self, inline_references: list[InlineReference]) -> set[InlineReference]:
        """Validates inline references and returns only the valid ones"""

    @abstractmethod
    def inline_text(self, citation_block: CitationBlock) -> str:
        """Retrieves the inline citation text for a citation block"""

    @abstractmethod
    def reference_text(self, citation: Union[Citation, InlineReference]) -> str:
        """Retrieves the reference text for a citation or inline reference"""


class SimpleRegistry(ReferenceRegistry):
    def __init__(self, bib_files: list[str], footnote_format: str = "{key}"):
        super().__init__(bib_files, footnote_format)
        self.style = PlainStyle()
        self.backend = MarkdownBackend()

    def validate_citation_blocks(self, citation_blocks: list[CitationBlock]) -> None:
        """Validates all citation blocks. Throws an error if any citation block is invalid"""
        for citation_block in citation_blocks:
            for citation in citation_block.citations:
                if citation.key not in self.bib_data.entries:
                    log.warning(f"Citing unknown reference key {citation.key}")

        for citation_block in citation_blocks:
            for citation in citation_block.citations:
                if citation.prefix != "" or citation.suffix != "":
                    log.warning(f"Affixes not supported in simple mode: {citation}")

    def validate_inline_references(self, inline_references: list[InlineReference]) -> set[InlineReference]:
        valid_refs = {ref for ref in inline_references if ref.key in self.bib_data.entries}
        invalid_refs = {ref for ref in inline_references if ref not in valid_refs}

        for ref in invalid_refs:
            log.warning(f"Inline reference to unknown key {ref.key}")

        return valid_refs

    def inline_text(self, citation_block: CitationBlock) -> str:
        keys = [
            self.footnote_format.format(key=citation.key)
            for citation in citation_block.citations
            if citation.key in self.bib_data.entries
        ]
        return "".join(f"[^{key}]" for key in keys)

    def reference_text(self, citation: Union[Citation, InlineReference]) -> str:
        entry = self.bib_data.entries[citation.key]
        log.debug(f"Converting bibtex entry {citation.key!r} without pandoc")
        formatted_entry = self.style.format_entry("", entry)
        entry_text = formatted_entry.text.render(self.backend)
        entry_text = entry_text.replace("\n", " ")
        # Clean up some common escape sequences
        entry_text = entry_text.replace("\\(", "(").replace("\\)", ")").replace("\\.", ".")
        log.debug(f"SUCCESS Converting bibtex entry {citation.key!r} without pandoc")
        return entry_text


class PandocRegistry(ReferenceRegistry):
    """A registry that uses Pandoc to format citations"""

    def __init__(self,
                 bib_files: list[str],
                 csl_file: str,
                 csl_file_encoding: Union[str, None],
                 footnote_format: str = "{key}"):
        super().__init__(bib_files, footnote_format)
        self.csl_file = csl_file

        # Get pandoc version for formatting decisions
        pandoc_version = tuple(int(ver) for ver in pypandoc.get_pandoc_version().split("."))
        if not pandoc_version >= (2, 11):
            raise ValueError("Pandoc version 2.11 or higher is required for this registry")

        # Cache for formatted citations
        self._inline_cache: dict[str, str] = {}
        self._reference_cache: dict[str, str] = {}
        self._is_inline = self._check_csl_type(csl_file=self.csl_file, csl_file_encoding=csl_file_encoding)

    def inline_text(self, citation_block: CitationBlock) -> str:
        """Get the inline text for a citation block"""
        footnotes = " ".join(
            f"[^{self.footnote_format.format(key=citation.key)}]"
            for citation in citation_block.citations
            if citation.key in self._reference_cache
        )

        if self._is_inline:
            # For inline styles, return both inline citation and footnote
            inline_text = self._inline_cache.get(str(citation_block), str(citation_block))
            return inline_text + footnotes
        else:
            # For footnote styles, just return footnote links
            return footnotes

    def reference_text(self, citation: Union[Citation, InlineReference]) -> str:
        """Returns cached reference text"""
        return self._reference_cache[citation.key]

    def validate_citation_blocks(self, citation_blocks: list[CitationBlock]) -> None:
        """Validates citation blocks and pre-formats all citations"""
        # First validate all keys exist
        for citation_block in citation_blocks:
            for citation in citation_block.citations:
                if citation.key not in self.bib_data.entries:
                    log.warning(f"Citing unknown reference key {citation.key}")

        # Pre-Process with appropriate pandoc version
        if self._is_inline:
            unprocessed_blocks = [block for block in citation_blocks if str(block) not in self._inline_cache]
        else:
            unprocessed_blocks = [
                block
                for block in citation_blocks
                if not all(citation.key in self._reference_cache for citation in block.citations)
            ]

        if len(unprocessed_blocks) > 0:
            _inline_cache, _reference_cache = self._process_with_pandoc(unprocessed_blocks)
            self._inline_cache.update(_inline_cache)
            self._reference_cache.update(_reference_cache)

    def validate_inline_references(self, inline_references: list[InlineReference]) -> set[InlineReference]:
        valid_references = set()

        for ref in inline_references:
            if ref.key not in self.bib_data.entries:
                log.warning("Citing unknown reference key %s", ref.key)
            else:
                valid_references |= {ref}

        if valid_references:
            _, _references = self._process_with_pandoc(
                [CitationBlock(citations=[Citation(key=ref.key)]) for ref in valid_references]
            )

            self._reference_cache.update(_references)
        return valid_references

    @cached_property
    def bib_data_bibtex(self) -> str:
        """Convert bibliography data to BibTeX format"""
        return self.bib_data.to_string("bibtex")

    def _process_with_pandoc(self, citation_blocks: list[CitationBlock]) -> tuple[dict, dict]:
        """Process citations with pandoc"""

        # Build the document pandoc can process and we can parse to extract inline citations and reference text
        full_doc = """
---
link-citations: false
---

"""
        citation_map = {index: block for index, block in enumerate(citation_blocks)}
        full_doc += "\n\n".join(f"{index}. {block}" for index, block in citation_map.items())
        full_doc += "\n\n# References\n\n"
        log.debug("Converting with pandoc:")
        log.debug(full_doc)
        with tempfile.TemporaryDirectory() as tmpdir:
            bib_path = Path(tmpdir).joinpath("temp.bib")
            with open(bib_path, "wt", encoding="utf-8") as bibfile:
                bibfile.write(self.bib_data_bibtex)

            args = ["--citeproc", "--bibliography", str(bib_path), "--csl", self.csl_file]
            markdown = pypandoc.convert_text(
                source=full_doc, to="markdown-citations", format="markdown", extra_args=args
            )

        log.debug("Pandoc output:")
        log.debug(markdown)
        try:
            splits = markdown.split("# References")
            inline_citations, references = splits[0], splits[1]
        except IndexError:
            raise ValueError("Failed to parse pandoc output")

        # Parse inline citations
        inline_citations = inline_citations.strip()

        # Use regex to match numbered entries, handling multi-line citations
        citation_pattern = re.compile(r"(\d+)\.\s+(.*?)(?=(?:\n\d+\.|$))", re.DOTALL)
        matches = citation_pattern.finditer(inline_citations)

        # Create a dictionary of cleaned citations (removing extra whitespace and newlines)
        inline_citations = {int(match.group(1)): " ".join(match.group(2).split()) for match in matches}

        inline_cache = {str(citation_map[index]): citation for index, citation in inline_citations.items()}

        # Parse references
        reference_cache = {}

        # Pattern for format with .csl-left-margin and .csl-right-inline
        pattern1 = r"::: \{#ref-(?P<key>[^\s]+) .csl-entry\}\r?\n\[.*?\]\{\.csl-left-margin\}\[(?P<citation>.*?)\]\{\.csl-right-inline\}"  # noqa: E501

        # Pattern for simple reference format
        pattern2 = r"::: \{#ref-(?P<key>[^\s]+) .csl-entry\}\r?\n(?P<citation>.*?)(?=:::|$)"

        # Try first pattern
        matches1 = re.finditer(pattern1, references, re.DOTALL)
        for match in matches1:
            key = match.group("key").strip()
            citation = match.group("citation").replace("\n", " ").strip()
            reference_cache[key] = citation

        # If no matches found, try second pattern
        if not reference_cache:
            matches2 = re.finditer(pattern2, references, re.DOTALL)
            for match in matches2:
                key = match.group("key").strip()
                citation = match.group("citation").replace("\n", " ").strip()
                reference_cache[key] = citation

        log.debug("Inline cache: %s", inline_cache)
        log.debug("Reference cache: %s", reference_cache)
        return inline_cache, reference_cache

    def _check_csl_type(self, csl_file: str, csl_file_encoding: Union[str, None]) -> bool:
        """Check if CSL file is footnote or inline style"""
        if not csl_file:
            return False

        try:
            with open(csl_file, encoding=csl_file_encoding) as f:
                csl_content = f.read()
                # Check if citation-format is "author-date"
                # For "numeric" styles we default to footnotes
                if 'citation-format="author-date"' in csl_content:
                    return True
                # Default to footnote style
                return False
        except Exception as e:
            log.warning("Error reading CSL file: ", exc_info=e)
            return False
