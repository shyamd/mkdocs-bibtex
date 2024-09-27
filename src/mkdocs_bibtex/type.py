# Python imports
from enum import Enum
from dataclasses import dataclass


class CiteFormat(Enum):
    FOOTNOTE = "footnote"
    INLINE = "inline"
    LINK = "link"


class BibType(Enum):
    GLOBAL = "global"
    PER_PAGE = "per_page"


@dataclass
class CitationIndexEntry:
    idx: int
    formatted_html: str
    formatted_md: str
    ref: str
    page: str


CitationIndex = dict[str, CitationIndexEntry]

CitationBlockMapping = dict[str, list[str]]
