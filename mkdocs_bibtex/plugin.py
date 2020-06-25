import os.path

import pypandoc
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin


class BibTexPlugin(BasePlugin):
    """
    Allows the use of bibtex in markdown content for MKDocs.

    Options:
        bib_file (string): path to a single bibtex file for entries, relative to mkdocs.yml.
        csl_file (string, optional): path to a CLS file, relative to mkdocs.yml.
    """

    config_scheme = [
        ("bib_file", config_options.Type(str, required=True)),  # TODO: multiple files.
        ("csl_file", config_options.Type(str, required=False)),
    ]

    def on_config(self, config):
        """Get path on load of config."""
        config_path = os.path.dirname(config.config_file_path)

        self.csl_path = get_path(self.config.get("csl_file", None), config_path)
        self.bib_path = get_path(self.config["bib_file"], config_path)

        return config

    def on_page_markdown(self, markdown, page, config, files):

        to = "markdown_strict"
        input_format = "md"
        extra_args = []

        # Add bibtex files.
        # TODO: multiple bib files. Pandoc supports multiple "--bibliography" args,
        #  but I don't know yet how to get a list from the config.
        extra_args.extend(["--bibliography", self.bib_path])

        # Add CSL files.
        if self.csl_path is not None:
            extra_args.extend(["--csl", self.csl_path])

        # Call Pandoc.
        markdown = pypandoc.convert_text(markdown, to, input_format, extra_args)

        return str(markdown)


def get_path(path, base_path):
    if path is None:
        return None
    elif os.path.isabs(path):
        return path
    else:
        return os.path.abspath(os.path.join(base_path, path))
