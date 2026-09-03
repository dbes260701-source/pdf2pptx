# -*- coding: utf-8 -*-
"""
native.py -- 네이티브 PDF 객체 -> 레이아웃 요소 (ROADMAP R1)

pdfio.native_objects() 가 꺼낸 객체를 build.py 가 아는 레이아웃 요소로 옮긴다.
OCR/CV 경로와 달리 다음이 원본 그대로 보존된다.

  - 글자 내용 (OCR 오타가 원천적으로 없음)
  - 글꼴 크기와 굵기 (글꼴 이름에서 판별)
  - 글자색 · 도형 채움색 · 선색 (추정이 아니라 실제 값)
  - 그리기 순서 (z) -> 겹침 복원 (R2)
  - 임베디드 JPEG 원본 바이트 (재인코딩 없음) (R3)

표현할 수 없는 객체는 조용히 버리지 않고 unsupported 로 돌려준다(평가서 B §4.2).
"""
import os

import pdfio

# 복잡한 경로로 보는 세그먼트 수. 사각형은 4~5 세그먼트다.
MAX_RECT_SEGMENTS = 6
# 선으로 볼 최대 두께(200dpi 기준 px). extract.LINE_MAX_THICK_200DPI 와 같은 근거.
LINE_MAX_THICK_200DPI = 11
# 페이지를 거의 덮는 흰 배경 경로는 슬라이드 배경이므로 요소로 만들지 않는다.
BG_COVER_RATIO = 0.98


def _scale(px, dpi):
    return max(1, int(round(px * dpi / 200.0)))


def _px(o, page_h_pt, dpi):
    return [round(v, 1) for v in pdfio.pt_to_px(o["bbox_pt"], page_h_pt, dpi)]


# --------------------------------------------------------------- 텍스트
def _text_lines(items):
    """같은 줄에 있는 조각들을 x 순으로 이어 붙인다."""
    lines = []
    for it in sorted(items, key=lambda t: (round(t["bbox"][3], 0), t["bbox"][0])):
        h = it["bbox"][3] - it["bbox"][1]
        placed = False
        for ln in lines:
            same_baseline = abs(ln["bbox"][3] - it["bbox"][3]) <= 0.4 * h
            same_size = abs(ln["size"] - it["size"]) <= 0.25 * max(ln["size"], it["size"])
            if same_baseline and same_size:
                ln["parts"].append(it)
                b, o = ln["bbox"], it["bbox"]
                ln["bbox"] = [min(b[0], o[0]), min(b[1], o[1]), max(b[2], o[2]), max(b[3], o[3])]
                placed = True
                break
        if not placed:
            lines.append(dict(parts=[it], bbox=list(it["bbox"]), size=it["size"],
                              color=it["color"], bold=it["bold"]))
    for ln in lines:
        ln["parts"].sort(key=lambda t: t["bbox"][0])
        ln["text"] = "".join(p["text"] for p in ln["parts"]).rstrip()
    return [l for l in lines if l["text"].strip()]


def _paragraphs(lines):
    """세로로 가깝고 크기가 비슷하며 좌/중앙/우가 맞는 줄들을 한 문단으로 묶는다.

    기준은 extract.group_lines() 와 같다. OCR 경로와 결과 모양을 맞추기 위한 것이다.
    """
    lines = sorted(lines, key=lambda l: (l["bbox"][1], l["bbox"][0]))
    used = [False] * len(lines)
    groups = []
    for i, a in enumerate(lines):
        if used[i]:
            continue
        g, used[i], cur = [a], True, a
        while True:
            best, bj = None, None
            for j, b in enumerate(lines):
                if used[j]:
                    continue
                h = cur["bbox"][3] - cur["bbox"][1]
                gap = b["bbox"][1] - cur["bbox"][3]
                if gap < -0.3 * h or gap > 0.75 * h:
                    continue
                bh = b["bbox"][3] - b["bbox"][1]
                if abs(bh - h) > 0.3 * max(bh, h):
                    continue
                if abs(b["size"] - cur["size"]) > 0.25 * max(b["size"], cur["size"]):
                    continue
                left = abs(b["bbox"][0] - cur["bbox"][0]) < 0.8 * h
                cen = abs((b["bbox"][0] + b["bbox"][2]) / 2 - (cur["bbox"][0] + cur["bbox"][2]) / 2) < 0.8 * h
                right = abs(b["bbox"][2] - cur["bbox"][2]) < 0.8 * h
                if not (left or cen or right):
                    continue
                if best is None or b["bbox"][1] < best["bbox"][1]:
                    best, bj = b, j
            if best is None:
                break
            g.append(best)
            used[bj] = True
            cur = best
        groups.append(g)
    return groups


def _text_elements(objs, page_h_pt, dpi, eid):
    items = []
    for o in objs:
        if o["kind"] != "text" or not o.get("text", "").strip():
            continue
        items.append(dict(bbox=_px(o, page_h_pt, dpi), text=o["text"],
                          size=(o.get("font_size") or 0) * dpi / 72.0,
                          color=o.get("fill") or "#000000", bold=bool(o.get("bold")),
                          z=o["z"]))
    out = []
    for g in _paragraphs(_text_lines(items)):
        x0 = min(l["bbox"][0] for l in g); y0 = min(l["bbox"][1] for l in g)
        x1 = max(l["bbox"][2] for l in g); y1 = max(l["bbox"][3] for l in g)
        lefts = [l["bbox"][0] for l in g]
        cents = [(l["bbox"][0] + l["bbox"][2]) / 2 for l in g]
        h = max(1.0, sum(l["bbox"][3] - l["bbox"][1] for l in g) / len(g))
        align = "left"
        if len(g) > 1 and max(cents) - min(cents) < 0.5 * h and max(lefts) - min(lefts) > 0.5 * h:
            align = "center"
        pitch = round((g[-1]["bbox"][1] - g[0]["bbox"][1]) / (len(g) - 1), 1) if len(g) > 1 else None
        first = g[0]
        out.append(dict(id=f"t{eid}", type="text", text="\n".join(l["text"] for l in g),
                        bbox=[x0, y0, x1, y1],
                        font_pt=round(first["parts"][0]["size"] * 72.0 / dpi, 1),
                        color=first["color"], bold=first["bold"], align=align, pitch_px=pitch,
                        z=min(p["z"] for l in g for p in l["parts"]),
                        source_method="native"))
        eid += 1
    return out, eid


# --------------------------------------------------------------- 경로
def _path_element(o, page_h_pt, dpi, W, H, eid):
    """경로 -> rect 또는 line. 표현 못 하면 (None, 사유)."""
    b = _px(o, page_h_pt, dpi)
    w, h = b[2] - b[0], b[3] - b[1]
    if w <= 0 or h <= 0:
        return None, None                                  # 빈 경로는 사유 없이 무시
    if (w >= W * BG_COVER_RATIO and h >= H * BG_COVER_RATIO
            and (o.get("fill") or "").upper() in ("#FFFFFF", "")):
        return None, None                                  # 페이지 흰 배경
    if o.get("segments", 0) > MAX_RECT_SEGMENTS:
        return None, "복잡한 벡터 경로(세그먼트 %d개)" % o["segments"]

    thick = _scale(LINE_MAX_THICK_200DPI, dpi)
    filled = bool(o.get("fill_mode"))
    stroked = bool(o.get("stroked"))

    # 채움 없이 선만 있고 한쪽이 얇으면 괘선
    if not filled and stroked and min(w, h) <= thick:
        return dict(id=f"l{eid}", type="line", bbox=b,
                    color=o.get("stroke") or "#000000",
                    width_px=max(1, int(round(min(w, h)))),
                    z=o["z"], source_method="native"), None
    if filled:
        e = dict(id=f"r{eid}", type="rect", bbox=b, fill=o.get("fill"),
                 z=o["z"], source_method="native")
        if stroked and o.get("stroke"):
            e["line"] = o["stroke"]
            e["line_px"] = max(1, int(round((o.get("stroke_width") or 1) * dpi / 72.0)))
        return e, None
    if stroked:                                            # 두꺼운 테두리만 있는 도형
        return dict(id=f"r{eid}", type="rect", bbox=b, fill=None,
                    line=o.get("stroke") or "#000000",
                    line_px=max(1, int(round((o.get("stroke_width") or 1) * dpi / 72.0))),
                    z=o["z"], source_method="native"), None
    return None, "채움도 선도 없는 경로"


# --------------------------------------------------------------- 이미지
def _image_element(o, page_h_pt, dpi, asset_dir, page, eid):
    """임베디드 이미지. JPEG 는 원본 바이트를 그대로 쓴다(R3)."""
    b = _px(o, page_h_pt, dpi)
    e = dict(id=f"i{eid}", type="image", bbox=b, photo=True,
             z=o["z"], source_method="native")
    im = o.get("image") or {}
    if im.get("ext") == "jpg" and im.get("raw") and asset_dir:
        os.makedirs(asset_dir, exist_ok=True)
        name = f"p{page}_native_{eid}.jpg"
        with open(os.path.join(asset_dir, name), "wb") as f:
            f.write(im["raw"])
        e["asset"] = name
        e["source_image"] = "original"      # 재인코딩 없음
        e["src_size"] = [im.get("width"), im.get("height")]
    else:
        # JPEG 가 아니면 원본 바이트를 그대로 못 쓴다. build.py 의 래스터 크롭으로 넘어간다.
        e["source_image"] = "raster_fallback"
        e["fallback_reason"] = "임베디드 형식 %s" % (",".join(im.get("filters") or []) or "알 수 없음")
    return e


# --------------------------------------------------------------- 진입점
def page_elements(pdf, page, dpi, W, H, asset_dir=None):
    """(요소 리스트, 미지원 목록). 요소에는 원본 그리기 순서가 z 로 들어간다."""
    _, page_h_pt = pdfio.page_size(pdf, page)
    objs = pdfio.native_objects(pdf, page)

    els, unsupported = [], []
    els_text, _ = _text_elements(objs, page_h_pt, dpi, 0)
    els += els_text

    ri = ii = 0
    for o in objs:
        if o["kind"] == "path":
            e, why = _path_element(o, page_h_pt, dpi, W, H, ri)
            if e is not None:
                els.append(e); ri += 1
            elif why:
                unsupported.append(dict(z=o["z"], kind="path", reason=why,
                                        bbox=_px(o, page_h_pt, dpi)))
        elif o["kind"] == "image":
            els.append(_image_element(o, page_h_pt, dpi, asset_dir, page, ii)); ii += 1
        elif o["kind"] in ("shading", "form"):
            unsupported.append(dict(z=o["z"], kind=o["kind"],
                                    reason="%s 객체는 아직 복원하지 않는다" % o["kind"],
                                    bbox=_px(o, page_h_pt, dpi)))

    els.sort(key=lambda e: e.get("z", 0))
    return els, unsupported


def text_lines_for_tables(pdf, page, dpi):
    """tables.detect_tables() 가 받는 줄 목록 형태로 네이티브 텍스트를 넘긴다.

    tables.ocr_lines() 와 같은 스키마(text/x0/y0/x1/y1/words)를 쓰므로,
    네이티브 경로에서도 표 검출을 그대로 쓸 수 있다.
    """
    _, page_h_pt = pdfio.page_size(pdf, page)
    items = []
    for o in pdfio.native_objects(pdf, page, want_image_bytes=False):
        if o["kind"] != "text" or not o.get("text", "").strip():
            continue
        items.append(dict(bbox=_px(o, page_h_pt, dpi), text=o["text"],
                          size=(o.get("font_size") or 0) * dpi / 72.0,
                          color=o.get("fill") or "#000000", bold=bool(o.get("bold")),
                          z=o["z"]))
    out = []
    for ln in _text_lines(items):
        words = [dict(text=p["text"].strip(), x=p["bbox"][0], y=p["bbox"][1],
                      w=p["bbox"][2] - p["bbox"][0], h=p["bbox"][3] - p["bbox"][1])
                 for p in ln["parts"] if p["text"].strip()]
        if not words:
            continue
        b = ln["bbox"]
        out.append(dict(text=ln["text"], x0=b[0], y0=b[1], x1=b[2], y1=b[3], words=words))
    return out
