import os
import pytest
from mkdocs_bibtex.registry import SimpleRegistry
from mkdocs_bibtex.citation import Citation, CitationBlock

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


@pytest.fixture
def simple_registry():
    bib_file = os.path.join(test_files_dir, "test.bib")
    return SimpleRegistry([bib_file])


def test_simple_registry_initialization(simple_registry):
    """Test basic initialization and loading of bib files"""
    assert len(simple_registry.bib_data.entries) == 4


def test_validate_citation_blocks_valid(simple_registry):
    """Test validation of valid citation blocks"""
    # Single citation
    citations = [Citation("test", "", "")]
    block = CitationBlock(citations)
    simple_registry.validate_citation_blocks([block])

    # Multiple citations
    citations = [Citation("test", "", ""), Citation("test2", "", "")]
    block = CitationBlock(citations)
    simple_registry.validate_citation_blocks([block])


@pytest.mark.xfail(reason="For some reason pytest does not catch the warning")
def test_validate_citation_blocks_invalid_key(simple_registry):
    """Test validation fails with invalid citation key"""
    citations = [Citation("nonexistent", "", "")]
    block = CitationBlock(citations)
    with pytest.warns(UserWarning, match="Citing unknown reference key nonexistent"):
        simple_registry.validate_citation_blocks([block])


@pytest.mark.xfail(reason="For some reason pytest does not catch the warning")
def test_validate_citation_blocks_invalid_affixes(simple_registry):
    """Test validation fails with affixes (not supported in simple mode)"""
    # Test prefix
    citations = [Citation("test", "see", "")]
    block = CitationBlock(citations)
    with pytest.warns(UserWarning, match="Simple style does not support any affixes"):
        simple_registry.validate_citation_blocks([block])

    # Test suffix
    citations = [Citation("test", "", "p. 123")]
    block = CitationBlock(citations)
    with pytest.warns(UserWarning, match="Simple style does not support any affixes"):
        simple_registry.validate_citation_blocks([block])


def test_inline_text(simple_registry):
    """Test inline citation text generation"""
    # Single citation
    citations = [Citation("test", "", "")]
    block = CitationBlock(citations)
    assert simple_registry.inline_text(block) == "[^test]"

    # Multiple citations
    citations = [Citation("test", "", ""), Citation("test2", "", "")]
    block = CitationBlock(citations)
    assert simple_registry.inline_text(block) == "[^test][^test2]"


def test_reference_text(simple_registry):
    """Test reference text generation"""
    # Test basic citation
    citation = Citation("test", "", "")
    assert (
        simple_registry.reference_text(citation)
        == "First Author and Second Author. Test title. *Testing Journal*, 2019."
    )

    # Test another basic citation
    citation = Citation("test2", "", "")
    assert (
        simple_registry.reference_text(citation)
        == "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019."
    )

    # test long citation
    citation = Citation("Bivort2016", "", "")
    assert (
        simple_registry.reference_text(citation)
        == "Benjamin L. De Bivort and Bruno Van Swinderen. Evidence for selective attention in the insect brain. *Current Opinion in Insect Science*, 15:1–7, 2016. [doi:10.1016/j.cois.2016.02.007](https://doi.org/10.1016/j.cois.2016.02.007)."  # noqa: E501
    )

    # Test citation with URL
    citation = Citation("test_citavi", "", "")
    expected = "First Author and Second Author. Test Title (TT). *Testing Journal (TJ)*, 2019. URL: [\\\\url\\{https://doi.org/10.21577/0103\\-5053.20190253\\}](\\url{https://doi.org/10.21577/0103-5053.20190253})."
    assert simple_registry.reference_text(citation) == expected
