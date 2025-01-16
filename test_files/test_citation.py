"""
This test file tests the citation module and ensures it is compatible with
pybtex basic citations and pandoc citation formattting
"""

from mkdocs_bibtex.citation import Citation, CitationBlock


def test_basic_citation():
    """Test basic citation extraction"""
    citations = Citation.from_markdown("@test")
    assert len(citations) == 1
    assert citations[0].key == "test"
    assert citations[0].prefix == ""
    assert citations[0].suffix == ""


def test_citation_with_prefix():
    """Test citation with prefix"""
    citations = Citation.from_markdown("see @test")
    assert len(citations) == 1
    assert citations[0].key == "test"
    assert citations[0].prefix == "see"
    assert citations[0].suffix == ""


def test_citation_with_suffix():
    """Test citation with suffix"""
    citations = Citation.from_markdown("@test, p. 123")
    assert len(citations) == 1
    assert citations[0].key == "test"
    assert citations[0].prefix == ""
    assert citations[0].suffix == "p. 123"


def test_citation_with_prefix_and_suffix():
    """Test citation with both prefix and suffix"""
    citations = Citation.from_markdown("see @test, p. 123")
    assert len(citations) == 1
    assert citations[0].key == "test"
    assert citations[0].prefix == "see"
    assert citations[0].suffix == "p. 123"


def test_suppressed_author():
    """Test suppressed author citation"""
    citations = Citation.from_markdown("-@test")
    assert len(citations) == 1
    assert citations[0].key == "test"
    assert citations[0].prefix == "-"
    assert citations[0].suffix == ""


def test_multiple_citations():
    """Test multiple citations separated by semicolon"""
    citations = Citation.from_markdown("@test; @test2")
    assert len(citations) == 2
    assert citations[0].key == "test"
    assert citations[1].key == "test2"


def test_complex_multiple_citations():
    """Test multiple citations with prefixes and suffixes"""
    citations = Citation.from_markdown("see @test, p. 123; @test2, p. 456")
    assert len(citations) == 2
    assert citations[0].key == "test"
    assert citations[0].prefix == "see"
    assert citations[0].suffix == "p. 123"
    assert citations[1].key == "test2"
    assert citations[1].prefix == ""
    assert citations[1].suffix == "p. 456"


def test_citation_block():
    """Test citation block extraction"""
    blocks = CitationBlock.from_markdown("[see @test, p. 123]")
    assert len(blocks) == 1
    assert len(blocks[0].citations) == 1
    assert blocks[0].citations[0].key == "test"
    assert blocks[0].citations[0].prefix == "see"
    assert blocks[0].citations[0].suffix == "p. 123"
    assert str(blocks[0]) == "[see @test, p. 123]"


def test_multiple_citation_blocks():
    """Test multiple citation blocks"""
    blocks = CitationBlock.from_markdown("[see @test, p. 123] Some text [@test2]")
    assert len(blocks) == 2
    assert blocks[0].citations[0].key == "test"
    assert blocks[1].citations[0].key == "test2"
    assert str(blocks[0]) == "[see @test, p. 123]"
    assert str(blocks[1]) == "[@test2]"


def test_invalid_citation():
    """Test invalid citation formats"""
    citations = Citation.from_markdown("not a citation")
    assert len(citations) == 0


def test_email_exclusion():
    """Test that email addresses are not parsed as citations"""
    citations = Citation.from_markdown("user@example.com")
    assert len(citations) == 0


def test_complex_citation_block():
    """Test complex citation block with multiple citations"""
    blocks = CitationBlock.from_markdown("[see @test1, p. 123; @test2, p. 456; -@test3]")
    assert len(blocks) == 1
    assert len(blocks[0].citations) == 3

    assert blocks[0].citations[0].key == "test1"
    assert blocks[0].citations[0].prefix == "see"
    assert blocks[0].citations[0].suffix == "p. 123"

    assert blocks[0].citations[1].key == "test2"
    assert blocks[0].citations[1].prefix == ""
    assert blocks[0].citations[1].suffix == "p. 456"

    assert blocks[0].citations[2].key == "test3"
    assert blocks[0].citations[2].prefix == " -"
    assert blocks[0].citations[2].suffix == ""
    assert str(blocks[0]) == "[see @test1, p. 123; @test2, p. 456; -@test3]"


def test_citation_string():
    """Test citation string"""
    citation = Citation("test", "Author", "2020")
    assert str(citation) == "Author @test 2020"

    block = CitationBlock([citation])
    assert str(block) == "[Author @test 2020]"

    citations = [citation, citation]
    block = CitationBlock(citations)
    assert str(block) == "[Author @test 2020; Author @test 2020]"
