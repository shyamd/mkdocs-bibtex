# 3rd party imports
from mkdocs.config import base, config_options as c

# Local imports
from mkdocs_bibtex.type import CiteFormat, BibType


class BibTexConfig(base.Config):
    """Configuration of the BibTex pluging for mkdocs.

    Options:
        bib_file (string): Path or url to a single bibtex file for entries,
            url example: https://api.zotero.org/*/items?format=bibtex
        bib_dir (string): Path to a directory of bibtex files for entries.
        csl_file (string, optional): Path or url to a CSL file, relative to mkdocs.yml.
        cite_format (string, optional): Format of the citations in text. Should
            one of "footnote", "inline", or "link". It defaults to "footnote".
        bib_type (string, optional): Type of bibliography used in the document.
            Should be either "global" or "per_page". It defaults to "per_page"
        automatic_per_page (bool, optional): Automatically insert the bibliography
            command at the end of each page. It defaults to True.
        ref_format (string, optional): Formatting string for the citation links.
        global_bib_ref (string, optional): Absolute to the file where the global
            bibliography is rendered.
        per_page_bib_command (string, optional): Command used to insert a per
            page bibliography. It defaults to "\\bibliography".
        global_bib_command (string, optional): Command to place a global
            bibliography of all used references. It defaults to "\\full_bibliography"
    """

    # Input files
    bib_file = c.Optional(c.Type(str))
    bib_dir = c.Optional(c.Dir(exists=True))
    csl_file = c.Optional(c.Type(str))

    # General settings
    cite_format = c.Choice(
        (CiteFormat.LINK.value, CiteFormat.FOOTNOTE.value, CiteFormat.INLINE.value),
        default=CiteFormat.LINK.value,
    )
    bib_type = c.Choice(
        (BibType.GLOBAL.value, BibType.PER_PAGE.value), default=BibType.GLOBAL.value
    )
    automatic_per_page = c.Type(bool, default=True)
    ref_format = c.Type(str, default="{number}-{key}")
    global_bib_ref = c.Type(str, default="/bibliography.md")

    # Commands
    per_page_bib_command = c.Type(str, default="\\bibliography")
    global_bib_command = c.Type(str, default="\\full_bibliography")
