import os
import pytest
import pypandoc
from mkdocs_bibtex.registry import PandocRegistry
from mkdocs_bibtex.citation import Citation, CitationBlock, InlineReference

module_dir = os.path.dirname(os.path.abspath(__file__))
test_files_dir = os.path.abspath(os.path.join(module_dir, "..", "test_files"))


@pytest.fixture
def bib_file():
    return os.path.join(test_files_dir, "test.bib")


@pytest.fixture
def csl():
    """Provide the Springer CSL file for testing"""
    return os.path.join(test_files_dir, "springer-basic-author-date.csl")

@pytest.fixture
def bristol_csl():
    """Provide the Springer CSL file for testing csl encoding support"""
    return os.path.join(test_files_dir, "bristol-university-press.csl")


@pytest.fixture
def numeric_csl():
    """Provide the Nature CSL file for testing"""
    return os.path.join(test_files_dir, "nature.csl")


@pytest.fixture
def registry(bib_file, csl):
    """Create a registry with Springer style for testing"""
    return PandocRegistry(bib_files=[bib_file], csl_file=csl, csl_file_encoding='windows-1252')

def test_csl_encoding_support(bib_file, bristol_csl):
    """Create a registry with Bristol style for testing, forcing windows default encoding."""

    assert PandocRegistry(bib_files=[bib_file], csl_file=bristol_csl, csl_file_encoding='utf-8')._is_inline

    # _is_inline fallbacks to False because of reading failure using windows encoding
    assert not PandocRegistry(bib_files=[bib_file], csl_file=bristol_csl, csl_file_encoding='windows-1252')._is_inline


@pytest.fixture
def numeric_registry(bib_file, nature_csl):
    """Create a registry with Nature style for testing"""
    return PandocRegistry(bib_files=[bib_file], csl_file=nature_csl, csl_file_encoding=None)


def test_bad_pandoc_registry(bib_file):
    """Throw error if no CSL file is provided"""
    with pytest.raises(Exception):
        PandocRegistry([bib_file])


def test_pandoc_registry_initialization(registry, csl):
    """Test basic initialization and loading of bib files"""
    assert len(registry.bib_data.entries) == 4
    assert registry.csl_file is csl


def test_multiple_bib_files(csl):
    """Test loading multiple bibliography files"""
    bib1 = os.path.join(test_files_dir, "multi_bib", "bib1.bib")
    bib2 = os.path.join(test_files_dir, "multi_bib", "multi_bib_child_dir", "bib2.bib")

    registry = PandocRegistry(bib_files=[bib1, bib2], csl_file=csl, csl_file_encoding=None)
    assert "test1" in registry.bib_data.entries
    assert "test2" in registry.bib_data.entries

    # Test citations from both files work
    citation1 = Citation("test1", "", "")
    citation2 = Citation("test2", "", "")
    registry.validate_citation_blocks([CitationBlock([citation1, citation2])])
    text1 = registry.reference_text(citation1)
    text2 = registry.reference_text(citation2)
    assert "Test title 1" in text1
    assert "Test title 2" in text2


def test_validate_citation_blocks_valid(registry):
    """Test validation of valid citation blocks"""
    # Single citation
    citations = [Citation("test", "", "")]
    block = CitationBlock(citations)
    registry.validate_citation_blocks([block])

    # Multiple citations
    citations = [Citation("test", "", ""), Citation("test2", "", "")]
    block = CitationBlock(citations)
    registry.validate_citation_blocks([block])


@pytest.mark.xfail(reason="For some reason pytest does not catch the warning")
def test_validate_citation_blocks_invalid(registry):
    """Test validation fails with invalid citation key"""
    citations = [Citation("nonexistent", "", "")]
    block = CitationBlock(citations)
    with pytest.warns(UserWarning, match="Citing unknown reference key nonexistent"):
        registry.validate_citation_blocks([block])


def test_inline_text_basic(registry):
    """Test basic inline citation formatting with different styles"""
    citations = [Citation("test", "", "")]
    block = CitationBlock(citations)
    registry.validate_citation_blocks([block])
    text = registry.inline_text(block)
    assert text  # Basic check that we got some text back
    assert "Author" in text  # Should contain author name


def test_inline_text_multiple(registry):
    """Test inline citation with multiple references"""
    citations = [Citation("test", "", ""), Citation("test2", "", "")]
    block = CitationBlock(citations)
    registry.validate_citation_blocks([block])
    text = registry.inline_text(block)
    assert text
    assert "Author" in text


# Use springer style for consistent prefix/suffix tests
def test_inline_text_with_prefix(registry):
    """Test inline citation with prefix"""
    citations = [Citation("test", "see", "")]
    block = CitationBlock(citations)
    registry.validate_citation_blocks([block])
    text = registry.inline_text(block)
    assert text
    assert "see" in text.lower()


def test_inline_text_with_suffix(registry):
    """Test inline citation with suffix"""
    citations = [Citation("test", "", "p. 123")]
    block = CitationBlock(citations)
    registry.validate_citation_blocks([block])
    text = registry.inline_text(block)
    assert text
    assert "123" in text


def test_reference_text(registry):
    """Test basic reference text formatting"""
    citation = Citation("test", "", "")
    block = CitationBlock([citation])
    registry.validate_citation_blocks([block])
    text = registry.reference_text(citation)
    # Update assertion to match Springer style
    assert "Author" in text and "Test title" in text

    # Test inline reference
    ref = InlineReference("test")
    text = registry.reference_text(ref)
    assert "Author" in text and "Test title" in text


def test_pandoc_formatting(registry):
    """Test formatting with newer Pandoc versions"""
    citation = Citation("test", "", "")
    block = CitationBlock([citation])
    registry.validate_citation_blocks([block])
    text = registry.reference_text(citation)
    assert text == "Author F, Author S (2019) Test title. Testing Journal 1:"


def test_multiple_citation_blocks(registry):
    """Test multiple citation blocks"""
    citations1 = [Citation("test", "", ""), Citation("test2", "", "")]
    block1 = CitationBlock(citations1)

    citations2 = [Citation("Bivort2016", "", "")]
    block2 = CitationBlock(citations2)
    citation_blocks = [block1, block2]
    registry.validate_citation_blocks(citation_blocks)

    text = registry.inline_text(block1)
    assert text
    assert "Author" in text

    # Test individual citations from block1
    text1 = registry.reference_text(citations1[0])
    text2 = registry.reference_text(citations1[1])
    assert text1
    assert text2
    assert "Author" in text1
    assert "Author" in text2

    text = registry.inline_text(block2)
    assert text
    assert "Bivort" in text


@pytest.mark.skipif(
    int(pypandoc.get_pandoc_version().split(".")[0]) < 3, reason="Pandoc formatting is different in Pandoc 3.0"
)
def test_complex_citation_formatting(registry):
    """Test complex citation scenarios"""
    citations = [
        Citation("test", "see", "p. 123-125"),
        Citation("test2", "compare", "chapter 2"),
        Citation("Bivort2016", "also", "figure 3"),
    ]
    block = CitationBlock(citations)
    registry.validate_citation_blocks([block])
    text = registry.inline_text(block)

    # Check that prefix, suffix, and multiple citations are formatted correctly
    assert "see" in text.lower()
    assert "123--125" in text
    assert "compare" in text.lower()
    assert "chap. 2" in text
    assert "also" in text.lower()
    assert "fig. 3" in text


def test_validate_inline_refs(registry):
    ref = InlineReference("test")
    bad_ref = InlineReference("bad_ref")
    assert len(registry.validate_inline_references([ref])) == 1
    assert len(registry.validate_inline_references([bad_ref])) == 0
    assert len(registry.validate_inline_references([ref, bad_ref])) == 1
