import glob
import os.path
import re
import tempfile
from collections import OrderedDict

import pypandoc
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from pybtex.backends.markdown import Backend as MarkdownBackend
from pybtex.database import BibliographyData, parse_file
from pybtex.style.formatting.plain import Style as PlainStyle


class BibTexPlugin(BasePlugin):
    """
    Allows the use of bibtex in markdown content for MKDocs.

    Options:
        bib_file (string): path to a single bibtex file for entries
        bib_dir (string): path to a directory of bibtex files for entries
        cite_style (string): either "plain" or "pandoc" to define the cite key style
                             defaults to "pandoc"
            plain - @cite_key
            pandoc - [@cite_key]
        bib_command (string): command to place a bibliography relevant to just that file
                              defaults to \bibliography
        full_bib_command (string): command to place a full bibliography of all references
        csl_file (string, optional): path to a CSL file, relative to mkdocs.yml.
    """

    config_scheme = [
        ("bib_file", config_options.Type(str, required=False)),
        ("bib_dir", config_options.Type(str, required=False)),
        ("cite_style", config_options.Type(str, default="plain")),
        ("bib_command", config_options.Type(str, default="\\bibliography")),
        ("full_bib_command", config_options.Type(str, default="\\full_bibliography")),
        ("csl_file", config_options.Type(str, required=False)),
    ]

    def __init__(self):
        self.bib_data = None
        self.all_references = OrderedDict()

    def on_config(self, config):
        """
        Loads bibliography on load of config
        """
        config_path = os.path.dirname(config.config_file_path)

        bibfiles = []

        if self.config.get("bib_file", None) is not None:
            bibfiles.append(get_path(self.config["bib_file"], config_path))
        elif self.config.get("bib_dir", None) is not None:
            bibfiles.extend(
                glob.glob(
                    get_path(os.path.join(self.config["bib_dir"], "*.bib"), config_path)
                )
            )
        else:
            raise Exception("Must supply a bibtex file or directory for bibtex files")

        # load bibliography data
        refs = {}
        for bibfile in bibfiles:
            bibfile = get_path(bibfile, config_path)
            bibdata = parse_file(bibfile)
            refs.update(bibdata.entries)

        self.bib_data = BibliographyData(entries=refs)

        cite_style = config.get("cite_style", "pandoc")
        # Decide on how citations are entered into the markdown text
        if cite_style == "plain":
            self.cite_regex = re.compile(r"\@(\w+)")
            self.insert_regex = r"\@{}"
        elif cite_style == "pandoc":
            self.cite_regex = re.compile(r"\[\@(\w+)\]")
            self.insert_regex = r"\[@{}\]"
        else:
            raise Exception("Invalid citation style: {}".format(cite_style))

        self.csl_file = config.get("csl_file", None)

        return config

    def on_page_markdown(self, markdown, page, config, files):
        """
        Parses the markdown for each page, extracting the bibtex references
        If a local reference list is requested, this will render that list where requested

        1. Finds all cite keys
        2. Convert all the corresponding bib entries into citations
        3. Insert the ordered citation numbers into the markdown text
        4. Insert the bibliography into the markdown
        5. Insert the full bibliograph into the markdown
        """

        # 1. Grab all the cited keys in the markdown
        cite_keys = self.cite_regex.findall(markdown)
        citations = [
            (cite_key, self.bib_data.entries[cite_key])
            for cite_key in cite_keys
            if cite_key in self.bib_data.entries
        ]

        # 2. Convert all the citations to text references
        references = self.format_citations(citations)

        # 3. Insert in numbers into the main markdown and build bibliography
        bibliography = []
        for number, key in enumerate(references.keys()):
            markdown = re.sub(
                self.insert_regex.format(key), "[^{}]".format(number + 1), markdown
            )
            bibliography_text = "[^{}]: {}".format(number + 1, references[key])
            bibliography.append(bibliography_text)

        # 4. Insert in the bibliopgrahy text into the markdown
        bibliography = "\n\n".join(bibliography)
        markdown = re.sub(
            re.escape(self.config.get("bib_command", "\\bibliography")),
            bibliography,
            markdown,
        )

        # 5. Build the full Bibliography and insert into the text
        markdown = re.sub(
            re.escape(self.config.get("full_bib_command", "\\full_bibliography")),
            self.full_bibliography,
            markdown,
        )

        return markdown

    def format_citations(self, citations):
        """
        Formats references and adds them to the global registry

        Args:
            citations (dict): mapping of cite_key to entry

        Returns OrderedDict of references
        """
        style = PlainStyle()
        backend = MarkdownBackend()
        references = OrderedDict()
        for key, entry in citations:
            if self.csl_file is not None:
                entry_text = to_markdown_pandoc(entry, self.csl_file)
            else:
                formatted_entry = style.format_entry("", entry)
                entry_text = formatted_entry.text.render(backend)
                entry_text = entry_text.replace("\n", " ")
            # Local reference list for this file
            references[key] = entry_text
            # Global reference list for all files
            self.all_references[key] = entry_text
        return references

    @property
    def full_bibliography(self):
        """
        Returns the full bibliography text
        """
        full_bibliography = []

        for number, key in enumerate(self.all_references.keys()):
            bibliography_text = "{}: {}".format(number + 1, self.all_references[key])
            full_bibliography.append(bibliography_text)

        return "\n".join(full_bibliography)


def get_path(path, base_path):
    if path is None:
        return None
    elif os.path.isabs(path):
        return path
    else:
        return os.path.abspath(os.path.join(base_path, path))


def to_markdown_pandoc(entry, csl_path):
    """
    Converts the PyBtex entry into formatted markdown citation text
    """
    bibtex_string = BibliographyData(entries={entry.key: entry}).to_string("bibtex")
    citation_text = """
---
nocite: '@*'
---
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        bib_path = os.path.join(tmpdir, "temp.bib")
        with open(bib_path, "w") as bibfile:
            bibfile.write(bibtex_string)

        # Call Pandoc.
        markdown = pypandoc.convert_text(
            source=citation_text,
            to="markdown_strict-citations",
            format="md",
            extra_args=["--csl", csl_path, "--bibliography", bib_path],
            filters=["pandoc-citeproc"],
        )

    # TODO: Perform this extraction better
    markdown = markdown.split("\n")[0][2:]

    return str(markdown)
