# -*- coding: utf-8 -*-
"""표 인식 프로토타입 2: OCR 단어 배치 + 괘선 힌트로 행/열 격자를 추론"""
import cv2, json, numpy as np

def words(work, page):
    d = json.load(open(f"{work}/ocr/p{page}.json", encoding="utf-8-sig"))
    out = []
    for l in d["lines"]:
        for w in l["words"]:
            out.append(dict(t=w["text"], x0=w["x"], y0=w["y"], x1=w["x"]+w["w"], y1=w["y"]+w["h"]))
    return out

def rules(img, delta=2):
    H, W = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hc = ((cv2.blur(g, (1, 15)).astype(np.int16) - g) > delta).astype(np.uint8)
    hc = cv2.dilate(hc, np.ones((5, 1), np.uint8))
    hl = cv2.morphologyEx(hc, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(60, W//25), 1)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(hl, 8)
    segs = [(int(st[c][0]), int(st[c][1]), int(st[c][0]+st[c][2]), int(st[c][1]+st[c][3]))
            for c in range(1, n) if st[c][2] >= max(60, W//25)]
    return segs

def group_rows(ws, tol=0.6):
    ws = sorted(ws, key=lambda w: w["y0"])
    rows = []
    for w in ws:
        h = w["y1"] - w["y0"]
        for r in rows:
            ov = min(r["y1"], w["y1"]) - max(r["y0"], w["y0"])
            if ov > tol * min(h, r["y1"] - r["y0"]):
                r["w"].append(w); r["y0"] = min(r["y0"], w["y0"]); r["y1"] = max(r["y1"], w["y1"]); break
        else:
            rows.append(dict(y0=w["y0"], y1=w["y1"], w=[w]))
    return sorted(rows, key=lambda r: r["y0"])

def corridors(rows, x0, x1, min_gap=14):
    """모든 행을 관통하는 세로 공백 통로 -> 열 경계"""
    occupied = np.zeros(int(x1 - x0) + 1, bool)
    for r in rows:
        for w in r["w"]:
            a = int(max(x0, w["x0"] - 2) - x0); b = int(min(x1, w["x1"] + 2) - x0)
            if b > a: occupied[a:b] = True
    gaps = []; start = None
    for i, occ in enumerate(occupied):
        if not occ and start is None: start = i
        if occ and start is not None:
            if i - start >= min_gap: gaps.append((start, i))
            start = None
    if start is not None and len(occupied) - start >= min_gap: gaps.append((start, len(occupied)))
    return [int(x0 + (a + b) / 2) for a, b in gaps if a > 0 and b < len(occupied)]

def find_tables(img, ws, min_rows=3, min_cols=2):
    """가로 괘선이 3개 이상 규칙적으로 겹치는 영역을 표 후보로 삼고, 행/열을 추론"""
    segs = rules(img)
    tables = []
    used = set()
    segs = sorted(segs, key=lambda s: s[1])
    for i, s in enumerate(segs):
        if i in used: continue
        grp = [s]; used.add(i)
        for j in range(i + 1, len(segs)):
            if j in used: continue
            t = segs[j]
            ov = min(s[2], t[2]) - max(s[0], t[0])
            if ov > 0.75 * max(s[2] - s[0], t[2] - t[0]) and t[1] - grp[-1][3] < 260:
                grp.append(t); used.add(j)
        if len(grp) < min_rows: continue
        x0 = min(g[0] for g in grp); x1 = max(g[2] for g in grp)
        y0 = grp[0][1]; y1 = grp[-1][3]
        inner = [w for w in ws if w["x0"] >= x0 - 8 and w["x1"] <= x1 + 8 and w["y0"] >= y0 - 6 and w["y1"] <= y1 + 6]
        if len(inner) < 4: continue
        rows = group_rows(inner)
        xs = [x0] + corridors(rows, x0, x1) + [x1]
        ys = [g[1] for g in grp]
        if len(xs) - 1 < min_cols or len(ys) - 1 < 2: continue
        tables.append(dict(bbox=[x0, y0, x1, y1], xs=xs, ys=ys,
                           rows=len(ys) - 1, cols=len(xs) - 1, nwords=len(inner)))
    return tables

if __name__ == "__main__":
    for p in (1, 2, 3, 4, 5, 6):
        img = cv2.imread(f"work/pages/p{p}.png")
        ts = find_tables(img, words("work", p))
        print(f"== page {p}: {len(ts)} tables")
        for t in ts:
            print(f"    {t['rows']}행 x {t['cols']}열 bbox={t['bbox']} 단어={t['nwords']} xs={t['xs']}")
