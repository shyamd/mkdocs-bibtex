from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="mkdocs-bibtex",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="An MkDocs plugin that enables managing citations with BibTex",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="mkdocs python markdown bibtex",
    url="https://github.com/shyamd/mkdocs-bibtex/",
    author="Shyam Dwaraknath",
    author_email="shyamd@lbl.gov",
    license="BSD-3-Clause-LBNL",
    python_requires=">=3.5",
    install_requires=["mkdocs>=1", "markdown>=3.1.1", "pybtex>=0.22", "pypandoc>=1.5"],
    tests_require=["pytest"],
    packages=find_packages(),
    entry_points={"mkdocs.plugins": ["bibtex = mkdocs_bibtex.plugin:BibTexPlugin"]},
)
