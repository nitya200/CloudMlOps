"""Extractor factory and parser unit tests."""

from __future__ import annotations

import pytest

from app.core.exceptions import ExtractionError, UnsupportedFileTypeError
from app.models.enums import FileType
from app.services.extraction_service import (
    DocumentExtractorFactory,
    DocxExtractor,
    ExtractionService,
    PdfExtractor,
    TxtExtractor,
)
from tests.factories import build_docx_bytes, build_pdf_bytes, build_txt_bytes


class TestFactory:
    @pytest.mark.parametrize(
        ("file_type", "expected"),
        [
            (FileType.PDF, PdfExtractor),
            (FileType.DOCX, DocxExtractor),
            (FileType.TXT, TxtExtractor),
            ("pdf", PdfExtractor),
            ("TXT", TxtExtractor),
        ],
    )
    def test_creates_the_matching_extractor(self, file_type, expected) -> None:
        assert isinstance(DocumentExtractorFactory.create(file_type), expected)

    def test_resolves_from_a_filename(self) -> None:
        extractor = DocumentExtractorFactory.create_for_filename("report.DOCX")
        assert isinstance(extractor, DocxExtractor)

    def test_rejects_an_unknown_type(self) -> None:
        with pytest.raises(UnsupportedFileTypeError):
            DocumentExtractorFactory.create("rtf")

    def test_reports_supported_types(self) -> None:
        assert set(DocumentExtractorFactory.supported_types()) == {"pdf", "docx", "txt"}


class TestExtraction:
    def test_extracts_text_from_a_pdf(self) -> None:
        result = ExtractionService().extract(FileType.PDF, build_pdf_bytes(pages=2))

        assert "Cloud native machine learning" in result.text
        assert result.page_count == 2
        assert result.word_count > 20

    def test_extracts_paragraphs_and_tables_from_a_docx(self) -> None:
        result = ExtractionService().extract(FileType.DOCX, build_docx_bytes())

        assert "Quarterly Platform Review" in result.text
        assert "Average latency" in result.text  # table content is included

    def test_extracts_text_from_a_txt_file(self) -> None:
        result = ExtractionService().extract(FileType.TXT, build_txt_bytes())
        assert "Containerized inference services" in result.text

    def test_decodes_non_utf8_text(self) -> None:
        result = ExtractionService().extract(
            FileType.TXT, "Café résumé naïve coordination".encode("latin-1")
        )
        assert "sum" in result.text.lower()

    def test_raises_on_a_corrupt_pdf(self) -> None:
        with pytest.raises(ExtractionError):
            ExtractionService().extract(FileType.PDF, b"%PDF-1.7 totally not a pdf")

    def test_raises_when_no_text_is_found(self) -> None:
        with pytest.raises(ExtractionError):
            ExtractionService().extract(FileType.TXT, b"   \n\n   \t  ")

    def test_normalizes_pdf_whitespace_and_hyphenation(self) -> None:
        raw = ["Distributed sys-", "tems require    careful", "", "", "coordination."]
        result = ExtractionService().extract(FileType.TXT, "\n".join(raw).encode())

        assert "systems" in result.text  # hyphen line break was re-joined
        assert "  " not in result.text
