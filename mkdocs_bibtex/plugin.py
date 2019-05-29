import os.path
import re

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs import utils

from pybtex.database import parse_file
from pybtex.database import BibliographyData


class BibTexPlugin(BasePlugin):

    config_scheme = (
        "global_references",
        mkdocs.config.config_options.Type(bool, default=False),
        "bib_style",
        mkdocs.config.config_options.Type(mkdocs.utils.string_types, required=True),
        "bib_file",
        mkdocs.config.config_options.Type(mkdocs.utils.string_types, required=False),
        "bib_dir",
        mkdocs.config.config_options.Type(mkdocs.utils.string_types, required=False),
        "cite_style",
        mkdocs.config.config_options.Type(mkdocs.utils.string_types, default="latex"),
    )

    def __init__(self):
        self.bib_data = None
