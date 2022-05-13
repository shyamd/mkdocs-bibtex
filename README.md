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
> *Note:* This plugin requires pandoc to be installed on your system.<br>
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

- `bib_file` - The path or url to a single bibtex file. Path can either be absolute or relative to `mkdocs.yml`. Example URL: `https://api.zotero.org/*/items?format=bibtex`
- `bib_dir` - Directory for bibtex files to load, same as above for path resolution
- `bib_command` - The syntax to render your bibliography, defaults to `\bibliography`
- `bib_by_default` - Automatically append the `bib_command` at the end of every markdown document, defaults to `true`
- `full_bib_command` - The syntax to render your entire bibliography, defaults to `\full_bibliography`
- `csl_file` - The path or url to a bibtex CSL file, specifying your citation format. Defaults to `None`, which renders in a plain format. A registry of citation styles can be found here: https://github.com/citation-style-language/styles
- `cite_inline` - Whether or not to render citations inline, requires `csl_file` to be specified. Defaults to `False`.

## Usage

In your markdown files:

1. Add your citations as you would if you used pandoc, IE: `[@first_cite;@second_cite]`
2. Add `\bibliography`, or the value of `bib_command`, to the doc you want your references rendered (if `bib_by_default` is set to true this is automatically applied for every page).
3. (Optional) Add `\full_bibliography`, or the value of `full_bib_command`, to where you want the full bibliography rendered. *Note*: This is currently not working properly, since this plugin can't dictate the order in which files are processed. The best way to ensure the file with the full bibliography gets processed last is to use numbers in front of file/folder names to enforce the order of processing, IE: `01_my_first_file.md`
4. (Optional) Configure the `csl_file` option to dictate the citation text formatting.
