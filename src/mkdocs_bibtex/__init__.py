import sys
from mkdocs_bibtex.plugin import BibTexPlugin

if sys.version_info[:2] >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata

__version__ = metadata.version(__package__ or __name__)
