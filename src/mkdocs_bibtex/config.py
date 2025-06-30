# 3rd party imports
from mkdocs.config import base, config_options


class BibTexConfig(base.Config):
    """Configuration of the BibTex pluging for mkdocs.

    Options:
        bib_file (string): path or url to a single bibtex file for entries,
                           url example: https://api.zotero.org/*/items?format=bibtex
        bib_dir (string): path to a directory of bibtex files for entries
        bib_command (string): command to place a bibliography relevant to just that file
                              defaults to \bibliography
        bib_by_default (bool): automatically appends bib_command to markdown pages
                               by default, defaults to true
        full_bib_command (string): command to place a full bibliography of all references
        csl_file (string, optional): path or url to a CSL file, relative to mkdocs.yml.
        footnote_format (string): format for the footnote number, defaults to "{number}"
        enable_inline_citations (bool): enable inline citations, these can clash with a lot of other features
    """

    # Input files
    bib_file = config_options.Optional(config_options.Type(str))
    bib_dir = config_options.Optional(config_options.Dir(exists=True))
    csl_file = config_options.Optional(config_options.Type(str))
    csl_file_encoding = config_options.Optional(config_options.Type(str))

    # Commands
    bib_command = config_options.Type(str, default="\\bibliography")
    full_bib_command = config_options.Type(str, default="\\full_bibliography")

    # Settings
    bib_by_default = config_options.Type(bool, default=True)
    footnote_format = config_options.Type(str, default="{key}")
    enable_inline_citations = config_options.Type(bool, default=True)
