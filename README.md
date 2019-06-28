# mkdocs-bibtex [![Build Status](https://travis-ci.com/materialsproject/mkdocs-bibtex.svg?branch=master)](https://travis-ci.com/materialsproject/mkdocs-bibtex)
A MkDocs plugin for citation management using bibtex


# Install
For now by cloning the repo and doing either `python setup.py` or `pip install` 


# Use
## mkdocs.yaml
First update your mkdocs config file with something like the following:
```
# Plugins
plugins:
  - bibtex:
      bib_file: "refs.bib"
      cite_style: "pandoc"
```

- `bib_file` - name of your bibtex file. Can be absolute path or relative path with the config file as the reference
- `bib_dir` - directory for bibtex files to load, same as above for path resolution
- `cite_style` - the way you place citations into text: `[@myRef]` is "pandoc" and `@myRef` is "plain"
- `bib_command` - the command for your bibliography, defaults to `\bibliography`
- `full_bib_command` - the command for your bibliography, defaults to `\full_bibliography`

## MKDocs Markdown files

1. Add you citations in as you normally would using which ever style you chose
2. Add in `\bibliography` or whatever you set your `bib_command` to where you want your references. 
3. Add in `\full_bibliography` or whatever you set your `full_bib_command` to where you want the full set of references. *Note*: This is not guaranteed to work yet since one issue is the order in which markdown files are processed. Might need to do something using the on_files event first. 