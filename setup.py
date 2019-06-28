
from setuptools import setup, find_packages


setup(
    name="mkdocs-bibtex",
    version="0.2.0",
    description="An MkDocs plugin that enables managing citations with BibTex",
    keywords="mkdocs python markdown bibtex",
    url="https://github.com/shyamd/mkdocs-bibtex/",
    author="Shyam Dwaraknath",
    author_email="shyamd@lbl.gov",
    license="BSD",
    python_requires=">=3.7",
    install_requires=["mkdocs>=1", "markdown>=3.1.1", "pybtex>=0.22"],
    test_suite="nose.collector",
    tests_require=["nose"],
    packages=find_packages(),
    entry_points={"mkdocs.plugins": ["bibtex = mkdocs_bibtex.plugin:BibTexPlugin"]},
)
