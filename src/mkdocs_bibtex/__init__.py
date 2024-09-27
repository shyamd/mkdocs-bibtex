# Python imports
import sys

# 3rd party imports
from mkdocs_bibtex.plugin import BibTexPlugin

# Handle module versioning
if sys.version_info[:2] >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata

__version__ = metadata.version(__package__ or __name__)
