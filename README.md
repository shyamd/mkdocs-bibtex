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
> If you're having trouble with pandoc, try installing the conda-forge version of pypandoc: `conda install -c conda-forge pypandoc` which will install a version with built in pandoc binaries


Next, add the following lines to your `mkdocs.yml`:

```yml
plugins:
  - search
  - bibtex:
      bib_file: "refs.bib"
markdown_extensions:
  - footnotes
```

The footnotes extension is how citations are linked for now.

> If you have no `plugins` entry in your config file yet, you'll likely also want to add the `search` plugin. MkDocs enables it by default if there is no `plugins` entry set.

## Options

- `bib_file` - Name of your bibtex file. Either the absolute path or the path relative to `mkdocs.yml`
- `bib_dir` - Directory for bibtex files to load, same as above for path resolution
- `bib_command` - The command for your bibliography, defaults to `\bibliography`
- `full_bib_command` - The command for your full bibliography, defaults to `\full_bibliography`
- `csl_file` - Bibtex CSL file to format the citation with, defaults to None, using a built in plain format instead

## Usage

In your markdown files:

1. Add your citations as you would if you used pandoc, IE: `[@first_cite;@second_cite]`
2. Add in `\bibliography` or whatever you set your `bib_command` to where you want your references.
3. Add in `\full_bibliography` or whatever you set your `full_bib_command` to where you want the full set of references. *Note*: This is not work just right since this plugin can't dictate the orer in which files are processed. The best way to ensure the file with the full bibliography gets processed last is to use numbers in front of file/folder names to enforce an order of processing, IE: `01_my_first_file.md`
4. (Optional) Setup `csl_file` to control the citation text formatting.
