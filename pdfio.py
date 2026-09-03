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


# =====================================================================
# 네이티브 PDF 객체 추출 (ROADMAP R1)
#
# 렌더링 후 OCR/CV 로 다시 알아맞히는 대신, PDF 안에 이미 들어 있는
# 텍스트·글꼴·색·경로·임베디드 이미지와 그리기 순서를 그대로 꺼낸다.
# born-digital 문서에서는 OCR 오타가 원천적으로 생기지 않고,
# paint order 를 알 수 있어 겹침 순서를 복원할 수 있으며(R2),
# 원본 JPEG 바이트를 재인코딩 없이 넘길 수 있다(R3).
#
# pypdfium2(BSD/Apache)만 사용한다. AGPL 인 PyMuPDF 로는 구현하지 않는다.
# =====================================================================

OBJ_TEXT, OBJ_PATH, OBJ_IMAGE, OBJ_SHADING, OBJ_FORM = 1, 2, 3, 4, 5
_KIND = {1: "text", 2: "path", 3: "image", 4: "shading", 5: "form"}

# 글꼴 이름으로 굵기 판별. 서브셋 글꼴은 'BCDEEE+MalgunGothicBold' 처럼 접두사가 붙는다.
_BOLD_HINTS = ("bold", "heavy", "black", "semibold", "demibold")


def native_available():
    """네이티브 객체 추출이 가능한 백엔드인지."""
    return backend() == "pypdfium2"


def _hexcolor(getter, obj):
    import ctypes
    r, g, b, a = (ctypes.c_uint() for _ in range(4))
    if not getter(obj, *[ctypes.byref(v) for v in (r, g, b, a)]):
        return None, 255
    return "#%02X%02X%02X" % (r.value, g.value, b.value), a.value


def _obj_text(obj, textpage):
    import ctypes
    import pypdfium2.raw as raw
    nb = raw.FPDFTextObj_GetText(obj, textpage, None, 0)
    if nb <= 2:
        return ""
    buf = ctypes.create_string_buffer(nb)
    raw.FPDFTextObj_GetText(obj, textpage, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ushort)), nb)
    return buf.raw[:nb - 2].decode("utf-16-le", "replace")


def _obj_font(obj):
    """(실효 글꼴 크기 pt, 글꼴 이름, 굵기).

    FPDFTextObj_GetFontSize() 는 **행렬을 적용하기 전** 크기다. PDF 는 글꼴 크기를
    1 로 두고 행렬로 키우거나(연구노트: 1pt x 22.0), 반대로 큰 값을 두고 행렬로
    줄이는(육아휴직: 267pt x 0.12) 방식을 흔히 쓴다. 그 값을 그대로 쓰면 글자가
    22배 작거나 8배 크게 나온다 -- 실제로 그 버그가 있었다.
    세로 배율 hypot(b, d) 를 곱해야 화면에 찍히는 크기가 된다.
    """
    import ctypes
    import math
    import pypdfium2.raw as raw
    size = ctypes.c_float()
    fs = float(size.value) if raw.FPDFTextObj_GetFontSize(obj, ctypes.byref(size)) else None
    if fs is not None:
        try:
            m = obj.get_matrix()
            vscale = math.hypot(m.b, m.d)
            if vscale > 0:
                fs *= vscale
        except Exception:
            pass                            # 행렬을 못 읽으면 원래 값을 쓴다
    name = ""
    font = raw.FPDFTextObj_GetFont(obj)
    if font:
        buf = ctypes.create_string_buffer(256)
        if raw.FPDFFont_GetBaseFontName(font, buf, 256):
            name = buf.value.decode("utf-8", "replace")
    base = name.split("+", 1)[-1]          # 서브셋 접두사 제거
    bold = any(h in base.lower() for h in _BOLD_HINTS)
    return fs, name, bold


def _obj_image(obj, page):
    """임베디드 이미지의 원본 바이트와 메타데이터. 재인코딩하지 않는다."""
    import ctypes
    import pypdfium2.raw as raw
    info = {}
    md = raw.FPDF_IMAGEOBJ_METADATA()
    if raw.FPDFImageObj_GetImageMetadata(obj, page, ctypes.byref(md)):
        info.update(width=int(md.width), height=int(md.height),
                    bpp=int(md.bits_per_pixel), colorspace=int(md.colorspace))
    filters = []
    for i in range(raw.FPDFImageObj_GetImageFilterCount(obj)):
        n = raw.FPDFImageObj_GetImageFilter(obj, i, None, 0)
        if n:
            b = ctypes.create_string_buffer(n)
            raw.FPDFImageObj_GetImageFilter(obj, i, b, n)
            filters.append(b.value.decode("ascii", "replace"))
    info["filters"] = filters
    nb = raw.FPDFImageObj_GetImageDataRaw(obj, None, 0)
    raw_bytes = None
    if nb:
        b = ctypes.create_string_buffer(nb)
        raw.FPDFImageObj_GetImageDataRaw(obj, ctypes.cast(b, ctypes.POINTER(ctypes.c_ubyte)), nb)
        raw_bytes = b.raw[:nb]
    info["raw"] = raw_bytes
    # DCTDecode = JPEG. 이 경우에만 원본 바이트를 그대로 PPTX 에 넣을 수 있다.
    info["ext"] = "jpg" if filters and filters[0] == "DCTDecode" else None
    return info


def native_objects(path, index, want_image_bytes=True):
    """1-based 페이지의 객체를 **그리기 순서 그대로** 반환.

    좌표는 PDF 포인트(원점 좌하단). 픽셀 변환은 pt_to_px() 를 쓴다.
    반환 항목: kind, z, bbox_pt, (text/font_size/font/bold), fill, fill_alpha,
              stroke, stroke_width, segments, image
    """
    if not native_available():
        raise RuntimeError("네이티브 객체 추출은 pypdfium2 백엔드에서만 지원합니다.")
    import ctypes
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    doc = pdfium.PdfDocument(path)
    try:
        page = doc[index - 1]
        textpage = page.get_textpage()
        out = []
        for z, obj in enumerate(page.get_objects()):
            kind = _KIND.get(obj.type, "unknown")
            try:
                bbox = [float(v) for v in obj.get_bounds()]
            except Exception:
                continue                      # 경계를 못 구하는 객체는 건너뛴다
            e = dict(kind=kind, z=z, bbox_pt=bbox)

            if obj.type in (OBJ_TEXT, OBJ_PATH):
                e["fill"], e["fill_alpha"] = _hexcolor(raw.FPDFPageObj_GetFillColor, obj)
                e["stroke"], e["stroke_alpha"] = _hexcolor(raw.FPDFPageObj_GetStrokeColor, obj)
                wv = ctypes.c_float()
                e["stroke_width"] = (float(wv.value)
                                     if raw.FPDFPageObj_GetStrokeWidth(obj, ctypes.byref(wv)) else None)

            if obj.type == OBJ_TEXT:
                e["text"] = _obj_text(obj, textpage)
                e["font_size"], e["font"], e["bold"] = _obj_font(obj)
            elif obj.type == OBJ_PATH:
                e["segments"] = int(raw.FPDFPath_CountSegments(obj))
                # FPDFPath_GetDrawMode(path, fillmode*, stroke*) -- 채움/선 여부를 함께 돌려준다
                fillmode, stroke = ctypes.c_int(), ctypes.c_int()
                if raw.FPDFPath_GetDrawMode(obj, ctypes.byref(fillmode), ctypes.byref(stroke)):
                    e["fill_mode"] = int(fillmode.value)      # 0=없음, 1=winding, 2=even-odd
                    e["stroked"] = bool(stroke.value)
                else:
                    e["fill_mode"], e["stroked"] = None, None
            elif obj.type == OBJ_IMAGE:
                e["image"] = _obj_image(obj, page) if want_image_bytes else None
                try:
                    m = obj.get_matrix()
                    e["matrix"] = [m.a, m.b, m.c, m.d, m.e, m.f]
                except Exception:
                    e["matrix"] = None
            out.append(e)
        textpage.close()
        return out
    finally:
        doc.close()


def native_text_stats(path, index):
    """네이티브 텍스트가 쓸 만한지 판단할 근거. (문자 수, 텍스트 객체 수, 해독된 객체 수)

    셋째 값이 중요하다. 서브셋 글꼴에 ToUnicode 매핑이 없으면 텍스트 객체는 있는데
    글자를 못 읽어 빈 문자열이 나온다(실측: 어떤 안내문은 텍스트 객체 95개 중
    대부분이 빈 문자열). 그대로 네이티브 경로를 타면 글자가 통째로 사라진다.
    """
    if not native_available():
        return 0, 0, 0
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(path)
    try:
        page = doc[index - 1]
        tp = page.get_textpage()
        n_chars = tp.count_chars()
        n_text = n_ok = 0
        for o in page.get_objects():
            if o.type != OBJ_TEXT:
                continue
            n_text += 1
            if _obj_text(o, tp).strip():
                n_ok += 1
        tp.close()
        return int(n_chars), int(n_text), int(n_ok)
    finally:
        doc.close()


# 이만큼의 글자가 실제 텍스트 객체로 들어 있으면 born-digital 로 본다.
NATIVE_MIN_CHARS = 20
# 텍스트 객체 중 이 비율 이상이 실제로 해독되어야 네이티브 경로를 쓴다.
# 미달이면 글자를 잃느니 OCR 로 넘긴다.
NATIVE_MIN_DECODED_RATIO = 0.80


def has_native_text(path, index, min_chars=NATIVE_MIN_CHARS,
                    min_decoded_ratio=NATIVE_MIN_DECODED_RATIO):
    """이 페이지를 네이티브 경로로 처리해도 되는지."""
    n_chars, n_text, n_ok = native_text_stats(path, index)
    if n_chars < min_chars or n_text <= 0:
        return False
    # 글자를 못 읽는 객체가 많으면 네이티브로 가면 안 된다 (ToUnicode 없는 서브셋 글꼴)
    return (n_ok / n_text) >= min_decoded_ratio


def pt_to_px(bbox_pt, page_h_pt, dpi):
    """PDF 포인트(원점 좌하단) -> 페이지 픽셀(원점 좌상단). extract 의 bbox 규약과 맞춘다."""
    s = dpi / 72.0
    x0, y0, x1, y1 = bbox_pt
    return [x0 * s, (page_h_pt - y1) * s, x1 * s, (page_h_pt - y0) * s]
