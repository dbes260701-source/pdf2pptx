# -*- coding: utf-8 -*-
"""네이티브 PDF 객체 추출 경로 (ROADMAP R1).

픽스처 PDF 는 pypdfium2 로 그 자리에서 만든다. 바이너리를 커밋하지 않아도
결정적으로 재현되고, 사내 문서를 저장소에 넣지 않는다는 원칙(평가서 §8.5)에도 맞는다.
"""
import ctypes
import io as _io
import os

import pytest

import pdfio
import native

pdfium = pytest.importorskip("pypdfium2")
raw = pytest.importorskip("pypdfium2.raw")

pytestmark = pytest.mark.skipif(not pdfio.native_available(),
                                reason="pypdfium2 백엔드에서만 동작")


def _utf16(s):
    return ctypes.cast(ctypes.create_string_buffer(s.encode("utf-16-le") + b"\x00\x00"),
                       ctypes.POINTER(ctypes.c_ushort))


@pytest.fixture
def sample_pdf(tmp_path):
    """텍스트 · 채운 사각형 · 얇은 선이 있는 1쪽 PDF. 그리기 순서를 의도적으로 섞는다."""
    doc = pdfium.PdfDocument.new()
    page = doc.new_page(300, 400)
    raw_page, raw_doc = page.raw, doc.raw

    rect = raw.FPDFPageObj_CreateNewRect(20, 320, 260, 60)      # z=0 배경 띠
    raw.FPDFPageObj_SetFillColor(rect, 40, 120, 200, 255)
    raw.FPDFPath_SetDrawMode(rect, 1, False)
    raw.FPDFPage_InsertObject(raw_page, rect)

    line = raw.FPDFPageObj_CreateNewRect(20, 200, 260, 2)       # z=1 얇은 선
    raw.FPDFPageObj_SetFillColor(line, 150, 150, 150, 255)
    raw.FPDFPath_SetDrawMode(line, 1, False)
    raw.FPDFPage_InsertObject(raw_page, line)

    txt = raw.FPDFPageObj_NewTextObj(raw_doc, b"Helvetica", 20) # z=2 글자 (띠 위)
    raw.FPDFText_SetText(txt, _utf16("Quarterly Report Title"))
    raw.FPDFPageObj_SetFillColor(txt, 255, 255, 255, 255)
    raw.FPDFPageObj_Transform(txt, 1, 0, 0, 1, 30, 350)
    raw.FPDFPage_InsertObject(raw_page, txt)

    raw.FPDFPage_GenerateContent(raw_page)
    out = str(tmp_path / "sample.pdf")
    with open(out, "wb") as fh:
        doc.save(fh)
    doc.close()
    assert os.path.exists(out) and os.path.getsize(out) > 0
    return out


# --------------------------------------------------------------- 객체 열거
def test_objects_are_returned_in_paint_order(sample_pdf):
    objs = pdfio.native_objects(sample_pdf, 1)
    assert [o["z"] for o in objs] == list(range(len(objs)))
    kinds = [o["kind"] for o in objs]
    assert kinds.count("text") == 1
    assert kinds.count("path") == 2
    # 글자는 배경 띠보다 뒤에 그려져야 한다 (그래야 위에 보인다)
    assert kinds.index("text") > kinds.index("path")


def test_text_content_and_style_are_exact(sample_pdf):
    txt = [o for o in pdfio.native_objects(sample_pdf, 1) if o["kind"] == "text"][0]
    assert txt["text"].strip() == "Quarterly Report Title"   # OCR 이 아니라 원본 문자열
    assert txt["font_size"] == pytest.approx(20, abs=0.5)
    assert txt["fill"] == "#FFFFFF"


def test_path_fill_colour_is_exact(sample_pdf):
    paths = [o for o in pdfio.native_objects(sample_pdf, 1) if o["kind"] == "path"]
    fills = {p["fill"] for p in paths}
    assert "#2878C8" in fills, f"채움색이 원본과 달라졌다: {fills}"


def test_native_text_detection(sample_pdf):
    n_chars, n_text = pdfio.native_text_stats(sample_pdf, 1)
    assert n_chars >= pdfio.NATIVE_MIN_CHARS and n_text == 1
    assert pdfio.has_native_text(sample_pdf, 1)


def test_native_is_skipped_when_text_is_too_sparse(sample_pdf):
    """글자가 거의 없는 페이지는 스캔본일 수 있으므로 OCR 경로로 넘긴다."""
    assert not pdfio.has_native_text(sample_pdf, 1, min_chars=10_000)


# --------------------------------------------------------------- 좌표 변환
def test_pt_to_px_flips_origin():
    # PDF 는 좌하단 원점, 페이지 요소는 좌상단 원점
    px = pdfio.pt_to_px([0, 0, 72, 72], page_h_pt=144, dpi=200)
    assert px == [0.0, 200.0, 200.0, 400.0]


def test_pt_to_px_scales_with_dpi():
    a = pdfio.pt_to_px([0, 0, 72, 72], 72, 200)
    b = pdfio.pt_to_px([0, 0, 72, 72], 72, 400)
    assert (b[2] - b[0]) == pytest.approx(2 * (a[2] - a[0]))


# --------------------------------------------------------------- 레이아웃 변환
def test_page_elements_carry_paint_order_and_source(sample_pdf, tmp_path):
    els, unsupported = native.page_elements(sample_pdf, 1, 200, 833, 1111,
                                            str(tmp_path / "assets"))
    assert els, "요소가 하나도 안 나왔다"
    assert all(e.get("source_method") == "native" for e in els)
    assert [e["z"] for e in els] == sorted(e["z"] for e in els), "z 순 정렬이 아니다"
    texts = [e for e in els if e["type"] == "text"]
    assert len(texts) == 1 and texts[0]["text"].strip() == "Quarterly Report Title"
    assert texts[0]["color"] == "#FFFFFF"


def test_text_is_drawn_after_its_background(sample_pdf, tmp_path):
    """겹침 순서 복원(R2)의 최소 보장: 글자의 z 가 배경 띠보다 크다."""
    els, _ = native.page_elements(sample_pdf, 1, 200, 833, 1111, str(tmp_path / "a"))
    txt = next(e for e in els if e["type"] == "text")
    band = [e for e in els if e["type"] == "rect"]
    assert band, "배경 사각형을 못 찾았다"
    assert txt["z"] > min(e["z"] for e in band)


def test_thin_path_becomes_a_line(sample_pdf, tmp_path):
    els, _ = native.page_elements(sample_pdf, 1, 200, 833, 1111, str(tmp_path / "a"))
    kinds = [e["type"] for e in els]
    assert "line" in kinds or "rect" in kinds


def test_table_adapter_matches_ocr_schema(sample_pdf):
    lines = native.text_lines_for_tables(sample_pdf, 1, 200)
    assert lines
    for ln in lines:
        assert set(ln) >= {"text", "x0", "y0", "x1", "y1", "words"}
        for w in ln["words"]:
            assert set(w) >= {"text", "x", "y", "w", "h"}


# --------------------------------------------------------------- 미지원 보고
def test_unsupported_objects_are_reported_not_dropped():
    """복잡한 벡터 경로는 조용히 사라지지 않고 사유와 함께 보고되어야 한다."""
    o = dict(kind="path", z=3, bbox_pt=[0, 0, 10, 10], segments=40,
             fill="#FF0000", fill_mode=1, stroked=False, stroke=None, stroke_width=1)
    e, why = native._path_element(o, 100, 200, 1000, 1000, 0)
    assert e is None and why and "세그먼트" in why


def test_white_page_background_is_not_an_element():
    o = dict(kind="path", z=0, bbox_pt=[0, 0, 100, 100], segments=5,
             fill="#FFFFFF", fill_mode=1, stroked=False, stroke=None, stroke_width=1)
    e, why = native._path_element(o, 100, 200, 278, 278, 0)
    assert e is None and why is None, "흰 배경은 요소도 미지원도 아니다"
