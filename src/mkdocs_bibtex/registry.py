from abc import ABC, abstractmethod
from mkdocs_bibtex.citation import Citation, CitationBlock
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

    def __init__(self, bib_files: list[str]):
        refs = {}
        log.info(f"Loading data from bib files: {bib_files}")
        for bibfile in bib_files:
            log.debug(f"Parsing bibtex file {bibfile}")
            bibdata = parse_file(bibfile)
            refs.update(bibdata.entries)
        self.bib_data = BibliographyData(entries=refs)

    @abstractmethod
    def validate_citation_blocks(self, citation_blocks: list[CitationBlock]) -> None:
        """Validates all citation blocks. Throws an error if any citation block is invalid"""

    @abstractmethod
    def inline_text(self, citation_block: CitationBlock) -> str:
        """Retreives the inline citation text for a citation block"""

    @abstractmethod
    def reference_text(self, citation: Citation) -> str:
        """Retreives the reference text for a citation"""


class SimpleRegistry(ReferenceRegistry):
    def __init__(self, bib_files: list[str]):
        super().__init__(bib_files)
        self.style = PlainStyle()
        self.backend = MarkdownBackend()

    def validate_citation_blocks(self, citation_blocks: list[CitationBlock]) -> None:
        """Validates all citation blocks. Throws an error if any citation block is invalid"""
        for citation_block in citation_blocks:
            for citation in citation_block.citations:
                if citation.key not in self.bib_data.entries:
                    # TODO: Should this be a warning or fatal error?
                    pass

        for citation_block in citation_blocks:
            for citation in citation_block.citations:
                if citation.prefix != "" or citation.suffix != "":
                    # TODO: Should this be a warning or fatal error?
                    pass

    def inline_text(self, citation_block: CitationBlock) -> str:
        keys = sorted(set(citation.key for citation in citation_block.citations))

        return "[" + ",".join(f"^{key}" for key in keys) + "]"

    def reference_text(self, citation: Citation) -> str:
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

    def __init__(self, bib_files: list[str], csl_file: str):
        super().__init__(bib_files)
        self.csl_file = csl_file

        # Get pandoc version for formatting decisions
        pandoc_version = tuple(int(ver) for ver in pypandoc.get_pandoc_version().split("."))
        if not pandoc_version >= (2, 11):
            raise ValueError("Pandoc version 2.11 or higher is required for this registry")

        # Cache for formatted citations
        self._inline_cache = {}
        self._reference_cache = {}

    def inline_text(self, citation_block: CitationBlock) -> str:
        """Returns cached inline citation text"""
        return self._inline_cache.get(str(citation_block), "")

    def reference_text(self, citation: Citation) -> str:
        """Returns cached reference text"""
        return self._reference_cache.get(citation.key, "")

    def validate_citation_blocks(self, citation_blocks: list[CitationBlock]) -> None:
        """Validates citation blocks and pre-formats all citations"""
        # First validate all keys exist
        for citation_block in citation_blocks:
            for citation in citation_block.citations:
                if citation.key not in self.bib_data.entries:
                    raise ValueError(f"Citation key {citation.key} not found in bibliography")

        # Pre-Process with appropriate pandoc version
        self._inline_cache, self._reference_cache = _process_with_pandoc(
            citation_blocks, self.bib_data_bibtex, self.csl_file
        )

    @property
    def bib_data_bibtex(self) -> str:
        """Convert bibliography data to BibTeX format"""
        return self.bib_data.to_string("bibtex")


def _process_with_pandoc(citation_blocks: list[CitationBlock], bib_data: str, csl_file: str) -> tuple[dict, dict]:
    """Process citations with pandoc"""

    # Build the document pandoc can process and we can parse to extract inline citations and reference text
    full_doc = """
---
title: "Test"
link-citations: false
nocite: |
    @*
---
"""
    citation_map = {index: block for index, block in enumerate(citation_blocks)}
    full_doc += "\n\n".join(f"{index}. {block}" for index, block in citation_map.items())
    full_doc += "# References\n\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        bib_path = Path(tmpdir).joinpath("temp.bib")
        with open(bib_path, "wt", encoding="utf-8") as bibfile:
            bibfile.write(bib_data)

        args = ["--citeproc", "--bibliography", str(bib_path), "--csl", csl_file]
        markdown = pypandoc.convert_text(source=full_doc, to="markdown-citations", format="markdown", extra_args=args)

    try:
        splits = markdown.split("# References")
        inline_citations, references = splits[0], splits[1]
    except IndexError:
        print(markdown)
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
    pattern1 = r"::: \{#ref-(?P<key>[^\s]+) .csl-entry\}\n\[.*?\]\{\.csl-left-margin\}\[(?P<citation>.*?)\]\{\.csl-right-inline\}"

    # Pattern for simple reference format
    pattern2 = r"::: \{#ref-(?P<key>[^\s]+) .csl-entry\}\n(?P<citation>.*?)(?=:::|$)"

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

    return inline_cache, reference_cache
