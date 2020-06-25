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

This version relies on Pandoc through [pypandoc](https://pypi.org/project/pypandoc/). 
Pypandoc provides Pandoc on many systems, otherwise, you have to install Pandoc manually, 
see pypandoc documentation for more details. 

Next, add the following lines to your `mkdocs.yml`:

```yml
plugins:
  - search
  - bibtex:
      bib_file: "refs.bib"
```

> If you have no `plugins` entry in your config file yet, you'll likely also want to add the `search` plugin. MkDocs enables it by default if there is no `plugins` entry set.

## Options

- `bib_file` - Name of your bibtex file. Either the absolute path or the path relative to `mkdocs.yml`.
- `csl_file` - Name of your [CSL](https://citationstyles.org/) file. Either the absolute path or the path relative to `mkdocs.yml`

## Usage

In your markdown files, add your citations as you would normally using ["pandoc"](https://pandoc.org/MANUAL.html#citations) style. 
Citations go inside square brackets and are separated by semicolons. 
Each citation must have a key, composed of ‘@’ + the citation identifier from the database.

If the style calls for a list of works cited, it will be placed in a div with id `refs`, if one exists:
```markdown
::: {#refs}
:::
```
Otherwise, it will be placed at the end of the document.
