from abc import ABC, abstractmethod
from mkdocs_bibtex.citation import Citation, CitationBlock
from mkdocs_bibtex.utils import log
from pybtex.database import BibliographyData, parse_file
from pybtex.backends.markdown import Backend as MarkdownBackend
from pybtex.style.formatting.plain import Style as PlainStyle


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
                    pass
                    # raise ValueError(f"Citation key {citation.key} not found in bibliography")

        for citation_block in citation_blocks:
            for citation in citation_block.citations:
                if citation.prefix != "" or citation.suffix != "":
                    pass
                    # raise ValueError("Simple style does not support any affixes (prefix, suffix, or author suppression)")

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
