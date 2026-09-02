# -*- coding: utf-8 -*-
"""
tables.py -- 표 영역(bbox)에서 행/열 격자와 셀 텍스트를 복원한다.

- 행 경계: 영역을 가로지르는 괘선이 있으면 그것을, 없으면 OCR 줄 묶음의 빈 줄을 사용
- 열 경계: 영역을 세로로 관통하는 괘선 또는 모든 행을 관통하는 공백 통로(whitespace corridor)
- 셀 텍스트: OCR 줄을 셀에 배정해 합침
"""
import json, os
import numpy as np, cv2


def ocr_lines(work, page):
    p = f"{work}/ocr/p{page}.json"
    d = json.load(open(p, encoding="utf-8-sig"))
    out = []
    for l in d["lines"]:
        ws = l["words"]
        if not ws: continue
        out.append(dict(text=l["text"],
                        x0=min(w["x"] for w in ws), y0=min(w["y"] for w in ws),
                        x1=max(w["x"]+w["w"] for w in ws), y1=max(w["y"]+w["h"] for w in ws),
                        words=ws))
    return out


def _rules(img, bbox, delta=2, cover=0.75):
    """표 영역 내부에서 영역을 (거의) 가로지르는 가로/세로 괘선 위치"""
    x0, y0, x1, y1 = [int(v) for v in bbox]
    g = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    if g.size == 0: return [], []
    hc = ((cv2.blur(g, (1, 15)).astype(np.int16) - g.astype(np.int16)) > delta).astype(np.uint8)
    vc = ((cv2.blur(g, (15, 1)).astype(np.int16) - g.astype(np.int16)) > delta).astype(np.uint8)
    hc = cv2.dilate(hc, np.ones((5, 1), np.uint8))
    vc = cv2.dilate(vc, np.ones((1, 5), np.uint8))
    hrow = hc.mean(1) > cover
    vcol = vc.mean(0) > cover
    return [y0 + v for v in _runs(hrow)], [x0 + v for v in _runs(vcol)]


def _runs(flags, tol=6):
    idx = np.where(flags)[0]
    if not len(idx): return []
    groups = [[idx[0]]]
    for v in idx[1:]:
        if v - groups[-1][-1] <= tol: groups[-1].append(v)
        else: groups.append([v])
    return [int(round(np.mean(g))) for g in groups]


def _row_bands(lines, y0, y1, gap=8):
    """OCR 줄을 y로 묶어 행 경계 추정"""
    ls = sorted(lines, key=lambda l: l["y0"])
    bands = []
    for l in ls:
        if bands and l["y0"] <= bands[-1][1] + gap:
            bands[-1][1] = max(bands[-1][1], l["y1"])
        else:
            bands.append([l["y0"], l["y1"]])
    if not bands: return []
    edges = [y0]
    for a, b in zip(bands, bands[1:]):
        edges.append(int((a[1] + b[0]) / 2))
    edges.append(y1)
    return edges


def _corridors(lines, x0, x1, min_gap=16, pad=3, span_max=0.6):
    """열 경계 후보. 표 폭의 대부분을 차지하는 제목/주석 줄은 제외하고 계산한다."""
    W = max(1.0, x1 - x0)
    lines = [l for l in lines if (l["x1"] - l["x0"]) / W <= span_max] or lines
    occ = np.zeros(int(W) + 1, bool)
    for l in lines:
        a = int(max(x0, l["x0"] - pad) - x0); b = int(min(x1, l["x1"] + pad) - x0)
        if b > a: occ[a:b] = True
    edges = []; start = None
    for i, o in enumerate(occ):
        if not o and start is None: start = i
        if o and start is not None:
            if i - start >= min_gap and start > 0: edges.append(int(x0 + (start + i) / 2))
            start = None
    return edges


def build_table(img, lines, bbox, xs=None, ys=None, min_gap=16):
    """bbox 안의 표 구조를 복원해 dict(xs, ys, cells) 반환"""
    x0, y0, x1, y1 = [int(v) for v in bbox]
    inner = [l for l in lines
             if l["x0"] >= x0 - 6 and l["x1"] <= x1 + 6 and l["y0"] >= y0 - 4 and l["y1"] <= y1 + 4]
    hrules, vrules = _rules(img, bbox)
    if ys is None:
        ys = [v for v in hrules if y0 + 6 < v < y1 - 6]
        ys = [y0] + ys + [y1]
        if len(ys) < 3:                      # 괘선이 없으면 텍스트 줄 간격으로
            ys = _row_bands(inner, y0, y1) or [y0, y1]
    if xs is None:
        xs = [v for v in vrules if x0 + 6 < v < x1 - 6]
        if len(xs) < 1:
            # 여러 줄이 나란히 놓인 '데이터 행'만으로 열 통로를 계산한다
            multi = []
            for a, b in zip(ys, ys[1:]):
                inrow = [l for l in inner if a <= (l["y0"] + l["y1"]) / 2 < b]
                if len(inrow) >= 2: multi.extend(inrow)
            xs = _corridors(multi or inner, x0, x1, min_gap)
        xs = [x0] + sorted(xs) + [x1]
    rows, cols = len(ys) - 1, len(xs) - 1
    cells = [["" for _ in range(cols)] for _ in range(rows)]
    boxes = [[None] * cols for _ in range(rows)]
    heights = [[[] for _ in range(cols)] for _ in range(rows)]
    pieces = []
    for l in inner:
        by_col = {}
        for w in l.get("words", []):
            wc = max(0, min(cols - 1, int(np.searchsorted(xs, (w["x"] + w["x"] + w["w"]) / 2) - 1)))
            by_col.setdefault(wc, []).append(w)
        if len(by_col) <= 1 or not l.get("words"):
            pieces.append(l); continue
        for wc, ws in by_col.items():
            pieces.append(dict(text=" ".join(w["text"] for w in ws),
                               x0=min(w["x"] for w in ws), y0=min(w["y"] for w in ws),
                               x1=max(w["x"] + w["w"] for w in ws), y1=max(w["y"] + w["h"] for w in ws),
                               words=ws))
    for l in pieces:
        cy = (l["y0"] + l["y1"]) / 2; cx = (l["x0"] + l["x1"]) / 2
        r = max(0, min(rows - 1, int(np.searchsorted(ys, cy) - 1)))
        c = max(0, min(cols - 1, int(np.searchsorted(xs, cx) - 1)))
        cells[r][c] = (cells[r][c] + "\n" + l["text"]).strip() if cells[r][c] else l["text"]
        b = boxes[r][c]
        nb = [l["x0"], l["y0"], l["x1"], l["y1"]]
        boxes[r][c] = nb if b is None else [min(b[0], nb[0]), min(b[1], nb[1]), max(b[2], nb[2]), max(b[3], nb[3])]
        heights[r][c].append(l["y1"] - l["y0"])
    # 글자가 하나도 없는 행/열은 경계 오검출이므로 이웃과 합친다
    keep_r = [r for r in range(rows) if any(cells[r][c].strip() for c in range(cols))]
    if keep_r and len(keep_r) < rows:
        newys = [ys[0]]
        for r in range(rows):
            if r in keep_r: newys.append(ys[r + 1])
        if len(newys) >= 2:
            ys = newys
            return build_table(img, lines, bbox, xs=xs, ys=ys, min_gap=min_gap)
    keep_c = [c for c in range(cols) if any(cells[r][c].strip() for r in range(rows))]
    if keep_c and len(keep_c) < cols:
        newxs = [xs[0]]
        for c in range(cols):
            if c in keep_c: newxs.append(xs[c + 1])
        if len(newxs) >= 2:
            return build_table(img, lines, bbox, xs=newxs, ys=ys, min_gap=min_gap)
    styles = [[cell_style(img, boxes[r][c], xs[c], xs[c + 1], heights[r][c]) if boxes[r][c] else None
               for c in range(cols)] for r in range(rows)]
    fills = [[bg_color(img, xs[c], ys[r], xs[c + 1], ys[r + 1], boxes[r][c]) for c in range(cols)]
             for r in range(rows)]
    # 글자색이 배경색과 구분되지 않으면 대비되는 색으로 교정(투명 글자 방지)
    for r in range(rows):
        for c in range(cols):
            st = styles[r][c]
            if not st: continue
            fg = _hex2rgb(st["color"]); bg = _hex2rgb(fills[r][c])
            if sum(abs(a - b) for a, b in zip(fg, bg)) < 90:
                st["color"] = "#FFFFFF" if sum(bg) < 3 * 128 else "#333333"
    return dict(type="table", bbox=[x0, y0, x1, y1], xs=xs, ys=ys, rows=rows, cols=cols,
                cells=cells, styles=styles, fills=fills)


def cell_style(img, box, cx0, cx1, line_h=None):
    """셀 텍스트의 크기·굵기·색·정렬 추정"""
    import extract
    x0, y0, x1, y1 = [int(v) for v in box]
    color, bg, bold = extract.text_style(img, [x0, y0, x1, y1])
    left, right = x0 - cx0, cx1 - x1
    nlines = len(line_h or [1])
    if nlines > 1:
        align = "left" if left < 0.18 * max(1, cx1 - cx0) else "center"
    else:
        align = "center" if abs(left - right) < 0.25 * max(1, cx1 - cx0) else ("right" if right < left else "left")
    fp = float(np.median(line_h)) if line_h else (y1 - y0)
    return dict(font_px=round(fp, 1), color=color, bold=bold, align=align)


def bg_color(img, x0, y0, x1, y1, textbox=None):
    """셀 배경색(글자 영역 제외)"""
    x0, y0, x1, y1 = int(x0) + 3, int(y0) + 3, int(x1) - 3, int(y1) - 3
    if x1 <= x0 or y1 <= y0: return "#FFFFFF"
    sub = img[y0:y1, x0:x1]
    crop = sub.reshape(-1, 3)
    if textbox is not None:
        keep = np.ones(sub.shape[:2], bool)
        tb = [int(v) for v in textbox]
        a0, b0 = max(0, tb[1] - 2 - y0), max(0, tb[0] - 2 - x0)
        keep[a0:tb[3] + 2 - y0, b0:tb[2] + 2 - x0] = False
        if keep.sum() > 30: crop = sub[keep]
    q = (crop // 12) * 12
    vals, counts = np.unique(q, axis=0, return_counts=True)
    c = vals[counts.argmax()]
    return "#%02X%02X%02X" % (int(c[2]), int(c[1]), int(c[0]))


# ---------------------------------------------------------------- 자동 검출
def page_rules(img, delta=2, min_frac=0.03):
    """페이지 전체의 가로 괘선 조각"""
    H, W = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hc = ((cv2.blur(g, (1, 15)).astype(np.int16) - g.astype(np.int16)) > delta).astype(np.uint8)
    hc = cv2.dilate(hc, np.ones((5, 1), np.uint8))
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(60, int(W * min_frac)), 1))
    hl = cv2.morphologyEx(hc, cv2.MORPH_OPEN, k)
    n, lab, st, _ = cv2.connectedComponentsWithStats(hl, 8)
    return [(int(st[c][0]), int(st[c][1]), int(st[c][0] + st[c][2]), int(st[c][1] + st[c][3]))
            for c in range(1, n) if st[c][2] >= max(60, W * min_frac)]


def candidate_regions(img, max_gap=150, tol=24):
    """x 구간이 비슷한 가로 괘선이 3개 이상 쌓인 곳을 표 후보 영역으로"""
    segs = sorted(page_rules(img), key=lambda s: s[1])
    used = [False] * len(segs)
    regions = []
    for i, s in enumerate(segs):
        if used[i]: continue
        grp = [s]; used[i] = True
        for j in range(i + 1, len(segs)):
            if used[j]: continue
            t = segs[j]
            ov = min(grp[-1][2], t[2]) - max(grp[-1][0], t[0])
            base = max(grp[-1][2] - grp[-1][0], t[2] - t[0])
            if ov > 0.8 * base and abs(t[0] - grp[-1][0]) < tol and t[1] - grp[-1][3] < max_gap:
                grp.append(t); used[j] = True
        if len(grp) < 3: continue
        x0 = min(g[0] for g in grp); x1 = max(g[2] for g in grp)
        regions.append([x0, grp[0][1], x1, grp[-1][3]])
    return regions


def detect_tables(img, lines, min_cols=2, min_rows=3, min_filled=0.75, min_w=150, min_h=60):
    """자동 표 검출: 후보 영역을 복원한 뒤 '표다운' 결과만 채택"""
    out = []
    for bbox in candidate_regions(img):
        if bbox[2] - bbox[0] < min_w or bbox[3] - bbox[1] < min_h: continue
        t = build_table(img, lines, bbox)
        if t["cols"] < min_cols or t["rows"] < min_rows: continue
        filled = sum(1 for row in t["cells"] for c in row if c.strip())
        if filled / (t["rows"] * t["cols"]) < min_filled: continue
        # 한 열에만 글자가 몰려 있으면 표가 아니다(본문 문단 등)
        colfill = [sum(1 for r in range(t["rows"]) if t["cells"][r][c].strip()) for c in range(t["cols"])]
        if sum(1 for v in colfill if v >= max(1, t["rows"] * 0.5)) < 2: continue
        if any(b[0] < t["bbox"][2] and t["bbox"][0] < b[2] and b[1] < t["bbox"][3] and t["bbox"][1] < b[3]
               for b in [o["bbox"] for o in out]): continue
        out.append(t)
    return out


def _hex2rgb(h):
    h = h.lstrip("#")
    return (int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16))
