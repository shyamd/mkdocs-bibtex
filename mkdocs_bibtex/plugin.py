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

    def on_config(self, config):
        """
        Loads bibliography on load of config
        """
        config_path = os.path.dirname(config.config_file_path)

        bibfiles = []
        if config["bib_file"] is not None:
            bibfiles.append(config["bib_file"])
        elif config["bib_dir"] is not None:
            bibfiles.extend(config["bib_dir"])
        else:
            raise Exception("Must supply a bibtex file or directory for bibtex files")

        # load bibliography data
        refs = []
        for bibfile in bibfiles:
            if not os.path.isabs(bibfile):
                bibfile = os.path.abspath(os.path.join(config_path, bibfile))
                bibdata = parse_file(bib_file)
                refs.update(bibdata.entries)

        self.bib_data = BibliographyData(entries=refs)

        return config
