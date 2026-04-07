from __future__ import annotations

from services.ingestion_service import build_pdf_page_title


def test_build_pdf_page_title_uses_semantic_heading_when_present() -> None:
    text = """Document #: 248966-050US
11-20 MULTICORE AND INTEL HYPER-THREADING TECHNOLOGY
Shared memory optimization.
"""

    title = build_pdf_page_title("intel_opt_manual", 42, text)

    assert title == "intel_opt_manual | MULTICORE AND INTEL HYPER-THREADING TECHNOLOGY"


def test_build_pdf_page_title_falls_back_to_page_label_when_no_heading_found() -> None:
    text = """

Document #: 248966-050US

"""

    title = build_pdf_page_title("intel_opt_manual", 7, text)

    assert title == "intel_opt_manual page 7"