import os

import pytest

from mkdocs_bibtex.plugin import BibTexPlugin

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


@pytest.fixture
def plugin():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_file": os.path.join(test_files_dir, "test.bib")},
        config_file_path=test_files_dir,
    )
    plugin.on_config(plugin.config)
    plugin.csl_file = None
    return plugin


def test_bibtex_loading_bibfile(plugin):
    assert len(plugin.registry.bib_data.entries) == 4


def test_bibtex_loading_bib_url():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_file": "https://raw.githubusercontent.com/shyamd/mkdocs-bibtex/main/test_files/test.bib"},
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.registry.bib_data.entries) == 4


def test_bibtex_loading_bibdir():
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_dir": os.path.join(test_files_dir, "multi_bib")},
        config_file_path=test_files_dir,
    )

    plugin.on_config(plugin.config)
    assert len(plugin.registry.bib_data.entries) == 2


def test_disable_inline_refs(plugin):
    plugin = BibTexPlugin()
    plugin.load_config(
        options={"bib_dir": os.path.join(test_files_dir, "multi_bib"), "enable_inline_citations": False},
        config_file_path=test_files_dir,
    )
    plugin.on_config(plugin.config)

    markdown = "This only has an @inline_cite."
    new_markdown = plugin.on_page_markdown(markdown, plugin.config, None, None)

    assert "@inline_cite" in new_markdown
