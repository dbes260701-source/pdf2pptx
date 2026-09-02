# -*- coding: utf-8 -*-
"""
pdfio.py -- PDF 렌더링 백엔드 추상화

배포용 exe는 AGPL인 PyMuPDF 없이 pypdfium2(BSD-3-Clause / Apache-2.0)만으로 동작한다.
백엔드 선택 순서: 환경변수 PDF2PPTX_BACKEND > pypdfium2 > pymupdf
"""
import os, math

_BACKEND = None


def backend():
    global _BACKEND
    if _BACKEND: return _BACKEND
    want = os.environ.get("PDF2PPTX_BACKEND", "").lower()
    order = [want] if want else ["pypdfium2", "pymupdf"]
    for name in order:
        try:
            __import__(name); _BACKEND = name; return _BACKEND
        except ImportError:
            continue
    raise RuntimeError("PDF 렌더링 백엔드(pypdfium2 또는 pymupdf)가 없습니다.")


def page_count(path):
    if backend() == "pypdfium2":
        import pypdfium2 as pdfium
        d = pdfium.PdfDocument(path); n = len(d); d.close(); return n
    import pymupdf
    d = pymupdf.open(path); n = len(d); d.close(); return n


def page_size(path, index):
    """1-based page index -> (width_pt, height_pt)"""
    if backend() == "pypdfium2":
        import pypdfium2 as pdfium
        d = pdfium.PdfDocument(path); w, h = d[index - 1].get_size(); d.close(); return w, h
    import pymupdf
    d = pymupdf.open(path); r = d[index - 1].rect; d.close(); return r.width, r.height


def render_page(path, index, dpi, out_png):
    """1-based page index를 dpi로 렌더링해 PNG 저장. 크기는 PyMuPDF와 동일하게 반올림."""
    w_pt, h_pt = page_size(path, index)
    tw, th = int(w_pt * dpi / 72 + 0.5), int(h_pt * dpi / 72 + 0.5)
    if backend() == "pypdfium2":
        import pypdfium2 as pdfium
        d = pdfium.PdfDocument(path)
        img = d[index - 1].render(scale=dpi / 72).to_pil().convert("RGB")
        d.close()
        if img.size != (tw, th):
            img = img.crop((0, 0, tw, th)) if img.size[0] >= tw and img.size[1] >= th else img.resize((tw, th))
        img.save(out_png)
    else:
        import pymupdf
        d = pymupdf.open(path)
        d[index - 1].get_pixmap(dpi=dpi).save(out_png)
        d.close()
    return tw, th
