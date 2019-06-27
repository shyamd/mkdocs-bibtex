import os.path
import re
from collections import OrderedDict

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs import utils

from pybtex.style.formatting.unsrt import Style
from pybtex.backends.markdown import Backend
from pybtex.database import parse_file, BibliographyData


class BibTexPlugin(BasePlugin):
    """
    Allows the use of bibtex in markdown content for MKDocs

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
    """

    config_scheme = [
        ("bib_file", config_options.Type(utils.string_types, required=False)),
        ("bib_dir", config_options.Type(utils.string_types, required=False)),
        ("cite_style", config_options.Type(utils.string_types, default="pandoc")),
        (
            "bib_command",
            config_options.Type(utils.string_types, default="\\bibliography"),
        ),
        (
            "full_bib_command",
            config_options.Type(utils.string_types, default="\\full_bibliography"),
        ),
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
        if self.config["bib_file"] is not None:
            bibfiles.append(self.config["bib_file"])
        elif self.config["bib_dir"] is not None:
            bibfiles.extend(self.config["bib_dir"])
        else:
            raise Exception("Must supply a bibtex file or directory for bibtex files")

        # load bibliography data
        refs = {}
        for bibfile in bibfiles:
            if not os.path.isabs(bibfile):
                bibfile = os.path.abspath(os.path.join(config_path, bibfile))
                bibdata = parse_file(bibfile)
                refs.update(bibdata.entries)

        self.bib_data = BibliographyData(entries=refs)

        cite_style = self.config["cite_style"]
        # Decide on how citations are entered into the markdown text
        if cite_style == "plain":
            self.cite_regex = re.compile(r"\@(\w+)")
            self.insert_regex = r"\@{}"
        elif cite_style == "pandoc":
            self.cite_regex = re.compile(r"\[\@(\w+)\]")
            self.insert_regex = r"\[@{}\]"
        else:
            raise Exception("Invalid citation style: {}".format(cite_style))   

        return config

    def on_page_markdown(self, markdown, page, config, files):
        """
        Parses the markdown for each page, extracting the bibtex references
        If a local reference list is requested, this will render that list where requested

        1. Finds all cite keys
        2. Convert all the corresponding bib entries into citations
        3. Insert the ordered citation numbers into the markdown text
        4. Insert the bibliography into the markdown
        5. Insert teh full bibliograph into the markdown
        """

        # 1. Grab all the cited keys in the markdown
        cite_keys = self.cite_regex.findall(markdown)
        citations = [
            (cite_key, self.bib_data.entries[cite_key])
            for cite_key in cite_keys
            if cite_key in self.bib_data.entries
        ]

        # 2. Convert all the references to text
        style = Style()
        backend = Backend()
        references = OrderedDict()
        for key, entry in citations:
            formatted_entry = style.format_entry("", entry)
            entry_text = formatted_entry.text.render(backend)
            # Local reference list for this file
            references[key] = entry_text
            # Global reference list for all files
            self.all_references[key] = entry_text

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
        markdown = re.sub(re.escape(self.config["bib_command"]), bibliography, markdown)


        # 5. Build the full Bibliography and insert into the text
        full_bibliography = []
        for number,key in enumerate(self.all_references.keys()):
            bibliography_text = "{}: {}".format(number + 1, references[key])
            full_bibliography.append(bibliography_text)
        full_bibliography = "\n\n".join(full_bibliography)
        markdown = re.sub(re.escape(self.config["full_bib_command"]), full_bibliography, markdown)
        
        return markdown