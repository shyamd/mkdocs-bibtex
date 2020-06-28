[![testing](https://github.com/shyamd/mkdocs-bibtex/workflows/testing/badge.svg)](https://github.com/shyamd/mkdocs-bibtex/actions?query=workflow%3Atesting)
[![codecov](https://codecov.io/gh/shyamd/mkdocs-bibtex/branch/master/graph/badge.svg)](https://codecov.io/gh/shyamd/mkdocs-bibtex)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/shyamd/mkdocs-bibtex.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/shyamd/mkdocs-bibtex/context:python)

# mkdocs-bibtex

A [MkDocs](https://www.mkdocs.org/) plugin for citation management using bibtex.

## Setup

Install the plugin using pip:

```
pip install mkdocs-bibtex
```

Next, add the following lines to your `mkdocs.yml`:

```yml
plugins:
  - search
  - bibtex:
      bib_file: "refs.bib"
      cite_style: "pandoc"
```

> If you have no `plugins` entry in your config file yet, you'll likely also want to add the `search` plugin. MkDocs enables it by default if there is no `plugins` entry set.

## Options

- `bib_file` - Name of your bibtex file. Either the absolute path or the path relative to `mkdocs.yml`
- `bib_dir` - Directory for bibtex files to load, same as above for path resolution
- `cite_style` - The way you place citations into text: "pandoc" for `[@myRef]` and "plain" for `@myRef`
- `bib_command` - The command for your bibliography, defaults to `\bibliography`
- `full_bib_command` - The command for your bibliography, defaults to `\full_bibliography`
- `csl_file` - Bibtex CSL file to format the citation with, defaults to None, using a built in plain format instead

## Usage

In your markdown files:

1. Add your citations as you would normally using either "plain" or "pandoc" style
2. Add in `\bibliography` or whatever you set your `bib_command` to where you want your references.
3. Add in `\full_bibliography` or whatever you set your `full_bib_command` to where you want the full set of references. *Note*: This is not guaranteed to work yet since one issue is the order in which markdown files are processed. Might need to do something using the `on_files()` event first.
4. (Optional) Setup `csl_file` to control the citation text formatting.
