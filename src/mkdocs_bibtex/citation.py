from dataclasses import dataclass
from typing import List
import re


CITATION_REGEX = re.compile(r"(?:(?P<prefix>[^@;]*?)\s*)?@(?P<key>[\w-]+)(?:,\s*(?P<suffix>[^;]+))?")
CITATION_BLOCK_REGEX = re.compile(r"\[(.*?)\]")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
INLINE_CITATION_REGEX = re.compile(r"(?<!\[)@(?P<key>[\w:-]+)(?![\w\s]*\])")


@dataclass
class Citation:
    """Represents a citation in raw markdown without formatting"""

    key: str
    prefix: str = ""
    suffix: str = ""

    def __str__(self) -> str:
        """String representation of the citation"""
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(f"@{self.key}")
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts)

    @classmethod
    def from_markdown(cls, markdown: str) -> List["Citation"]:
        """Extracts citations from a markdown string"""
        citations = []

        pos_citations = markdown.split(";")
        pos_citations = [citation for citation in pos_citations if EMAIL_REGEX.match(citation) is None]

        for citation in pos_citations:
            match = CITATION_REGEX.match(citation)

            if match:
                result = {group: (match.group(group) or "") for group in ["prefix", "key", "suffix"]}
                citations.append(Citation(prefix=result["prefix"], key=result["key"], suffix=result["suffix"]))
        return citations


@dataclass
class CitationBlock:
    citations: List[Citation]
    raw: str = ""
    inline: bool = False

    def __str__(self) -> str:
        """String representation of the citation block"""
        if self.raw != "":
            return f"[{self.raw}]"
        return "[" + "; ".join(str(citation) for citation in self.citations) + "]"

    @classmethod
    def from_markdown(cls, markdown: str) -> List["CitationBlock"]:
        """Extracts citation blocks from a markdown string"""
        """
        Given a markdown string
        1. Find all cite blocks by looking for square brackets
        2. For each cite block, try to extract the citations
            - if this errors there are no citations in this block and we move on
            - if this succeeds we have a list of citations
        3. Extract inline citations and mark them as CitationBlocks with the inline option
        """
        citation_blocks = []
        for match in CITATION_BLOCK_REGEX.finditer(markdown):
            try:
                citations = Citation.from_markdown(match.group(1))
                citation_blocks.append(CitationBlock(raw=match.group(1), citations=citations))
            except Exception as e:
                print(f"Error extracting citations from block: {e}")

        markdown_without_blocks = markdown
        for block in citation_blocks:
            markdown_without_blocks = markdown_without_blocks.replace(str(block), "")

        inline_citations = [
            CitationBlock([Citation(key=match.group("key"))], inline=True)
            for match in INLINE_CITATION_REGEX.finditer(markdown_without_blocks)
            if match
        ]

        all_blocks = citation_blocks + inline_citations
        return [block for block in all_blocks if block._is_valid]

    @property
    def _is_valid(self) -> bool:
        """Internal validity method to perform basic sanity checks"""
        # Citation blocks can't be empty
        if len(self.citations) == 0:
            return False
        # Inline citation blocks can only have 1 citation
        elif self.inline and len(self.citations) > 1:
            return False
        return True
