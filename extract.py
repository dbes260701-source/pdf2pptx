"""
extract.py  --  PDF page -> layout JSON (text / lines / rects / image regions)
usage: python extract.py <pdf> <workdir> [--dpi 200] [--pages 1,2]
Produces:
  work/pages/pN.png        rendered page (dpi)
  work/hires/pN.png        hi-res page (2x dpi) for image crops
  work/ocr/pN.json         raw Windows OCR
  work/layout/pN.json      structured layout (editable)
  work/debug/pN_boxes.png  overlay for review
"""
import sys, os, json, subprocess, math
import numpy as np, cv2
import pdfio
import tables as tbl

def respath(*parts):
    """resource dir: PyInstaller bundle (_MEIPASS) when frozen, else script dir"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)
HERE = respath()

def render(pdf, work, dpi, pages):
    os.makedirs(f"{work}/pages", exist_ok=True); os.makedirs(f"{work}/hires", exist_ok=True)
    info = []
    for i in pages:
        pt_w, pt_h = pdfio.page_size(pdf, i)
        w, h = pdfio.render_page(pdf, i, dpi, f"{work}/pages/p{i}.png")
        pdfio.render_page(pdf, i, dpi*2, f"{work}/hires/p{i}.png")
        info.append(dict(page=i, w=w, h=h, pt_w=pt_w, pt_h=pt_h))
    return info

def run_ocr(work, i):
    os.makedirs(f"{work}/ocr", exist_ok=True)
    out = f"{work}/ocr/p{i}.json"
    if not os.path.exists(out):
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        os.path.join(HERE, "winocr.ps1"), "-ImagePath", os.path.abspath(f"{work}/pages/p{i}.png"),
                        "-OutJson", os.path.abspath(out)], check=True, capture_output=True)
    return json.load(open(out, encoding="utf-8-sig"))

def line_bbox(l):
    ws = l["words"]
    return [min(w["x"] for w in ws), min(w["y"] for w in ws),
            max(w["x"]+w["w"] for w in ws), max(w["y"]+w["h"] for w in ws)]

def text_style(img, bb):
    x0,y0,x1,y1 = [int(v) for v in bb]
    pad = 3
    crop = img[max(0,y0-pad):y1+pad, max(0,x0-pad):x1+pad]
    if crop.size == 0: return "#000000", "#FFFFFF", False
    px = crop.reshape(-1,3).astype(int)
    q = (px//24)*24
    vals, counts = np.unique(q, axis=0, return_counts=True)
    bg = vals[counts.argmax()]
    d = np.abs(px - bg).sum(1)
    fg = px[d > 120]
    if len(fg) < 10: fgc = np.array([0,0,0])
    else: fgc = np.median(fg, axis=0)
    # bold estimate: stroke width via distance transform
    gray = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    _, m = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if m.mean() > 127: m = 255 - m
    dt = cv2.distanceTransform((m > 0).astype(np.uint8), cv2.DIST_L2, 3)
    v = dt[dt > 0]
    sw = 2*np.percentile(v, 90) if len(v) else 0
    h = y1-y0
    bold = sw/h > 0.117
    tohex = lambda c: "#%02X%02X%02X" % (int(c[2]), int(c[1]), int(c[0]))
    return tohex(fgc), tohex(bg), bool(bold)

def group_lines(lines):
    """merge OCR lines into paragraphs: vertically adjacent, similar height, aligned left/center"""
    items = []
    for l in lines:
        bb = line_bbox(l); items.append(dict(text=l["text"], bb=bb, h=bb[3]-bb[1]))
    items.sort(key=lambda t: (t["bb"][1], t["bb"][0]))
    used = [False]*len(items); groups = []
    for i, a in enumerate(items):
        if used[i]: continue
        g = [a]; used[i] = True
        cur = a
        while True:
            best = None
            for j, b in enumerate(items):
                if used[j]: continue
                gap = b["bb"][1] - cur["bb"][3]
                if gap < -0.3*cur["h"] or gap > 0.75*cur["h"]: continue
                if abs(b["h"]-cur["h"]) > 0.3*max(b["h"],cur["h"]): continue
                left = abs(b["bb"][0]-cur["bb"][0]) < 0.8*cur["h"]
                cen = abs((b["bb"][0]+b["bb"][2])/2-(cur["bb"][0]+cur["bb"][2])/2) < 0.8*cur["h"]
                right = abs(b["bb"][2]-cur["bb"][2]) < 0.8*cur["h"]
                if not (left or cen or right): continue
                if best is None or b["bb"][1] < best["bb"][1]: best = b; bj = j
            if best is None: break
            g.append(best); used[bj] = True; cur = best
        groups.append(g)
    return groups

# 괘선으로 인정할 최대 두께(200dpi 기준 픽셀). detect_rects 의 최소 변 길이(12)와 맞물려
# 있어서 이보다 작아지면 그 사이 두께가 어느 검출기에도 안 잡히는 사각지대가 생긴다.
# 실제로 11px 괘선이 line(<=6)에도 rect(>=12)에도 걸리지 않고 사라지는 버그가 있었다.
LINE_MAX_THICK_200DPI = 11
LINE_MIN_LEN_200DPI = 60
LINE_MIN_ASPECT = 8          # 길이/두께. 이보다 뭉툭하면 선이 아니라 작은 덩어리로 본다

def _scale(px, dpi):
    """200dpi 기준으로 잡은 픽셀 임계값을 실제 dpi 로 환산한다."""
    return max(1, int(round(px * dpi / 200.0)))

def detect_lines(img, textmask, dpi=200):
    """long thin horizontal/vertical lines -> line elements"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    nonwhite = (gray < 232).astype(np.uint8)
    nonwhite[textmask > 0] = 0
    max_thick = _scale(LINE_MAX_THICK_200DPI, dpi)
    min_len = _scale(LINE_MIN_LEN_200DPI, dpi)
    out = []
    for orient in ("h", "v"):
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (min_len,1) if orient=="h" else (1,min_len))
        m = cv2.morphologyEx(nonwhite, cv2.MORPH_OPEN, k)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
        for c in range(1, n):
            x,y,w,h,a = stats[c]
            thick, length = (h, w) if orient == "h" else (w, h)
            if thick > max_thick or length < min_len: continue
            if length < LINE_MIN_ASPECT * thick: continue
            col = np.median(img[lab==c].reshape(-1,3), axis=0)
            near, far = _scale(3, dpi), _scale(6, dpi)   # 선 양옆 배경을 재는 띠
            if orient=="h":
                nb = np.concatenate([img[max(0,y-far):max(0,y-near), x:x+w], img[y+h+near:y+h+far, x:x+w]])
            else:
                nb = np.concatenate([img[y:y+h, max(0,x-far):max(0,x-near)], img[y:y+h, x+w+near:x+w+far]])
            if nb.size and nb.reshape(-1,3).std(axis=0).mean() > 22: continue
            if nb.size and (nb.reshape(-1,3).mean() - col.mean()) < 18: continue
            out.append(dict(type="line", bbox=[int(x),int(y),int(x+w),int(y+h)],
                            color="#%02X%02X%02X"%(int(col[2]),int(col[1]),int(col[0])),
                            width_px=int(h if orient=="h" else w)))
    return out

def detect_rects(img, textmask):
    """uniform-colour filled rectangles (header bands, callout boxes)"""
    small = (img//16)*16
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    nonwhite = (gray < 240).astype(np.uint8)
    nonwhite[textmask > 0] = 1
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (7,7))
    nonwhite = cv2.morphologyEx(nonwhite, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(nonwhite, 4)
    out = []
    for c in range(1, n):
        x,y,w,h,a = stats[c]
        if a < 1500 or w < 25 or h < 12: continue
        fill = a/(w*h)
        if fill < 0.85: continue
        sel = (lab[y:y+h, x:x+w]==c) & (textmask[y:y+h, x:x+w]==0)
        region = img[y:y+h, x:x+w][sel]
        if len(region) < 200 or region.std(axis=0).mean() > 26: continue   # photo-like
        col = np.median(region, axis=0)
        out.append(dict(type="rect", bbox=[int(x),int(y),int(x+w),int(y+h)],
                        fill="#%02X%02X%02X"%(int(col[2]),int(col[1]),int(col[0]))))
    return out

def detect_frames(lines, img):
    """pairs of horizontal + vertical lines forming a rectangle -> outline rect (rounded if corners are open)"""
    hs = [l for l in lines if l["bbox"][2]-l["bbox"][0] > l["bbox"][3]-l["bbox"][1]]
    vs = [l for l in lines if l not in hs]
    frames = []; used = set()
    for i, a in enumerate(hs):
        for j, b in enumerate(hs):
            if j <= i: continue
            if abs(a["bbox"][0]-b["bbox"][0]) > 14 or abs(a["bbox"][2]-b["bbox"][2]) > 14: continue
            top, bot = (a, b) if a["bbox"][1] < b["bbox"][1] else (b, a)
            y0, y1 = top["bbox"][1], bot["bbox"][3]
            if y1 - y0 < 30: continue
            xl, xr = min(a["bbox"][0], b["bbox"][0]), max(a["bbox"][2], b["bbox"][2])
            left = [v for v in vs if abs(v["bbox"][0]-xl) < 14 and v["bbox"][1] < y0+14 and v["bbox"][3] > y1-14]
            right = [v for v in vs if abs(v["bbox"][2]-xr) < 14 and v["bbox"][1] < y0+14 and v["bbox"][3] > y1-14]
            if not left or not right: continue
            L, R = left[0], right[0]
            x0, x1 = L["bbox"][0], R["bbox"][2]
            gap = max(abs(top["bbox"][0]-x0), abs(top["bbox"][2]-x1))
            inner = img[y0+6:y1-6, x0+6:x1-6]
            white = inner.size and (inner.reshape(-1,3).mean(1) > 245).mean() > 0.5
            frames.append(dict(type="rect", bbox=[int(x0),int(y0),int(x1),int(y1)], fill="#FFFFFF" if white else None,
                               line=top["color"], line_px=top["width_px"], rounded=bool(gap > 3)))
            used.update(id(e) for e in (top, bot, L, R))
    lines[:] = [l for l in lines if id(l) not in used]
    return frames

def _boxes(nonwhite, close):
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (close,close))
    m = cv2.morphologyEx(nonwhite, cv2.MORPH_CLOSE, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    boxes = []
    for c in range(1, n):
        x,y,w,h,a = stats[c]
        if w*h < 250 or w < 11 or h < 11: continue
        boxes.append([x,y,x+w,y+h])
    return boxes

def _split_gaps(gray, box, thr=210, frac=0.35, mingap=3, minsize=60):
    """recursively split a block along light rows/cols (gaps between adjacent photos)"""
    x0,y0,x1,y1 = box
    sub = (gray[y0:y1, x0:x1] < thr)
    for axis in (1, 0):   # rows first then cols
        prof = sub.mean(axis=axis)
        gaps = prof < frac
        # find interior gap runs
        runs = []; start = None
        for i, g in enumerate(gaps):
            if g and start is None: start = i
            if (not g) and start is not None:
                if i - start >= mingap and start > minsize and len(gaps) - i > minsize: runs.append((start, i))
                start = None
        if runs:
            cuts = [0] + [r for run in runs for r in run] + [len(gaps)]
            parts = []
            for a, b in zip(cuts[0::2], cuts[1::2]):
                if b - a < minsize: continue
                nb = [x0, y0+a, x1, y0+b] if axis == 1 else [x0+a, y0, x0+b, y1]
                parts.extend(_split_gaps(gray, nb, thr, frac, mingap, minsize))
            return parts
    return [box]

def _tight(gray, box, thr=235):
    x0,y0,x1,y1 = box
    sub = gray[y0:y1, x0:x1] < thr
    rows = np.where(sub.mean(1) > 0.5)[0]; cols = np.where(sub.mean(0) > 0.5)[0]
    if len(rows) == 0 or len(cols) == 0: return box
    return [x0+int(cols[0]), y0+int(rows[0]), x0+int(cols[-1])+1, y0+int(rows[-1])+1]

def detect_photos(img, textmask):
    """dense, high-variance rectangular blocks = photographs (split adjacent ones by light gaps)"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    dark = (gray < 235).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (9,9))
    m = cv2.morphologyEx(dark, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for c in range(1, n):
        x,y,w,h,a = stats[c]
        if a < 15000 or w < 80 or h < 60: continue
        if a/(w*h) < 0.80: continue
        for bx in _split_gaps(gray, [int(x),int(y),int(x+w),int(y+h)]):
            bx = _tight(gray, bx)
            x0,y0,x1,y1 = bx
            if (x1-x0) < 60 or (y1-y0) < 60: continue
            sel = textmask[y0:y1, x0:x1] == 0
            region = img[y0:y1, x0:x1][sel]
            if len(region) < 500 or region.std(axis=0).mean() < 30: continue
            out.append(dict(type="image", bbox=[int(v) for v in bx], photo=True))
    return out

def detect_images(img, occupied):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    nonwhite = (gray < 225).astype(np.uint8)
    nonwhite[occupied > 0] = 0
    boxes = _boxes(nonwhite, 15)
    # split large sparse regions (diagrams) into parts; keep dense photos whole
    out = []
    for b in boxes:
        x0,y0,x1,y1 = b
        if (x1-x0) > 300 and (y1-y0) > 200 and nonwhite[y0:y1, x0:x1].mean() < 0.55:
            sub = np.zeros_like(nonwhite); sub[y0:y1, x0:x1] = nonwhite[y0:y1, x0:x1]
            parts = _boxes(sub, 3)
            if len(parts) >= 2: out.extend(parts); continue
        out.append(b)
    boxes = out
    # merge overlapping boxes
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i+1, len(boxes)):
                a,b = boxes[i], boxes[j]
                if a[0] < b[2]+4 and b[0] < a[2]+4 and a[1] < b[3]+4 and b[1] < a[3]+4:
                    boxes[i] = [min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
                    boxes.pop(j); merged = True; break
            if merged: break
    return [dict(type="image", bbox=[int(v) for v in b]) for b in boxes]

DEBUG_COLORS = dict(text=(0,0,255), rect=(0,180,0), line=(255,0,255),
                    image=(255,128,0), table=(0,215,255))

def write_debug(work, i, img, layout):
    """감지 결과 오버레이. 미지원 객체는 빨간 점선 대신 굵은 테두리로 눈에 띄게 표시한다."""
    os.makedirs(f"{work}/debug", exist_ok=True)
    dbg = img.copy()
    for e in layout["elements"]:
        b = e["bbox"]; c = DEBUG_COLORS.get(e["type"], (128,128,128))
        cv2.rectangle(dbg, (int(b[0]),int(b[1])), (int(b[2]),int(b[3])), c, 2)
        cv2.putText(dbg, e.get("id",""), (int(b[0]), int(b[1])-3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 1)
    for u in layout.get("unsupported", []):
        b = u["bbox"]
        cv2.rectangle(dbg, (int(b[0]),int(b[1])), (int(b[2]),int(b[3])), (0,0,255), 4)
    cv2.imwrite(f"{work}/debug/p{i}_boxes.png", dbg)

def native_page(pdf, work, i, dpi, W, H, img):
    """네이티브 객체로 레이아웃을 만들고, 표는 렌더 이미지에서 이어서 검출한다."""
    import native
    pt_w, pt_h = pdfio.page_size(pdf, i)
    els, unsupported = native.page_elements(pdf, i, dpi, W, H, f"{work}/assets")
    tables_found = []
    if "--no-tables" not in sys.argv:
        try:
            tables_found = tbl.detect_tables(img, native.text_lines_for_tables(pdf, i, dpi))
        except Exception as ex:
            print(f"  표 검출 건너뜀: {ex}")
    for k, t in enumerate(tables_found):
        t["id"] = f"tb{k}"; t["name"] = f"table-{k+1}"
        t["source_method"] = "cv"
        # 표는 그 안의 텍스트·선을 대신 그리므로 가장 위에 올린다
        t["z"] = max([e.get("z", 0) for e in els], default=0) + 1
    # 원본 텍스트를 남겨 둔다. 네이티브 모드에는 OCR json 이 없어서 이게 없으면
    # quality.text_coverage() 의 누락 탐지 게이트가 조용히 꺼진다.
    src_text = [ln["text"] for ln in native.text_lines_for_tables(pdf, i, dpi) if ln["text"].strip()]
    return dict(page=i, width=W, height=H, pt_w=pt_w, pt_h=pt_h, dpi=dpi,
                source_method="native", elements=els + tables_found,
                unsupported=unsupported, source_text=src_text)

def main():
    pdf, work = sys.argv[1], sys.argv[2]
    dpi = 200; pages = None
    if "--dpi" in sys.argv: dpi = int(sys.argv[sys.argv.index("--dpi")+1])
    if "--pages" in sys.argv: pages = [int(v) for v in sys.argv[sys.argv.index("--pages")+1].split(",")]
    npages = pdfio.page_count(pdf)
    if pages is None: pages = list(range(1, npages+1))
    info = render(pdf, work, dpi, pages)
    os.makedirs(f"{work}/layout", exist_ok=True); os.makedirs(f"{work}/debug", exist_ok=True)
    use_native = ("--no-native" not in sys.argv) and pdfio.native_available()
    for pi in info:
        i = pi["page"]
        img = cv2.imread(f"{work}/pages/p{i}.png")
        H, W = img.shape[:2]

        # born-digital 페이지는 렌더링 결과를 다시 알아맞히지 않고 PDF 객체를 그대로 쓴다.
        # 글자 내용·글꼴 크기·색·그리기 순서가 추정이 아니라 원본 값이 된다 (ROADMAP R1).
        if use_native and pdfio.has_native_text(pdf, i):
            layout = native_page(pdf, work, i, dpi, W, H, img)
            json.dump(layout, open(f"{work}/layout/p{i}.json","w",encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            write_debug(work, i, img, layout)
            n_un = len(layout.get("unsupported", []))
            print(f"page {i}: native  요소 {len(layout['elements'])}개"
                  + (f", 미지원 {n_un}개" if n_un else ""))
            continue

        ocr = run_ocr(work, i)
        elements = []; eid = 0
        textmask = np.zeros((H,W), np.uint8)
        rawmask = np.zeros((H,W), np.uint8)
        for l in ocr["lines"]:
            b = line_bbox(l); cv2.rectangle(rawmask, (int(b[0])-2,int(b[1])-2), (int(b[2])+2,int(b[3])+2), 255, -1)
        photos = detect_photos(img, rawmask)
        for ph in photos: cv2.rectangle(textmask, (ph["bbox"][0],ph["bbox"][1]), (ph["bbox"][2],ph["bbox"][3]), 255, -1)
        ocr["lines"] = [l for l in ocr["lines"] if not any(
            line_bbox(l)[0] >= ph["bbox"][0] and line_bbox(l)[2] <= ph["bbox"][2] and
            line_bbox(l)[1] >= ph["bbox"][1] and line_bbox(l)[3] <= ph["bbox"][3] for ph in photos)]
        for g in group_lines(ocr["lines"]):
            x0 = min(l["bb"][0] for l in g); y0 = min(l["bb"][1] for l in g)
            x1 = max(l["bb"][2] for l in g); y1 = max(l["bb"][3] for l in g)
            hs = [l["h"] for l in g]; h = float(np.median(hs))
            fg, bg, bold = text_style(img, [x0,y0,x1,y1])
            # alignment
            lefts = [l["bb"][0] for l in g]; cents = [(l["bb"][0]+l["bb"][2])/2 for l in g]
            align = "left"
            if len(g) > 1 and max(cents)-min(cents) < 0.5*h and max(lefts)-min(lefts) > 0.5*h: align = "center"
            pitch = None
            if len(g) > 1: pitch = round((g[-1]["bb"][1]-g[0]["bb"][1])/(len(g)-1), 1)
            elements.append(dict(id=f"t{eid}", type="text", text="\n".join(l["text"] for l in g),
                                 bbox=[x0,y0,x1,y1], font_px=round(h,1), color=fg, bold=bold,
                                 align=align, pitch_px=pitch, bg=bg))
            eid += 1
            cv2.rectangle(textmask, (int(x0)-2,int(y0)-2), (int(x1)+2,int(y1)+2), 255, -1)
        rects = detect_rects(img, textmask)
        lines = detect_lines(img, textmask, dpi)
        rects += detect_frames(lines, img)
        rects.sort(key=lambda r: -(r["bbox"][2]-r["bbox"][0])*(r["bbox"][3]-r["bbox"][1]))
        occupied = textmask.copy()
        for r in rects:
            if r.get("line"):
                cv2.rectangle(occupied, (r["bbox"][0],r["bbox"][1]), (r["bbox"][2],r["bbox"][3]), 255, r["line_px"]+4)
                for cx in (r["bbox"][0], r["bbox"][2]):
                    for cy in (r["bbox"][1], r["bbox"][3]): cv2.rectangle(occupied, (cx-14,cy-14), (cx+14,cy+14), 255, -1)
            else: cv2.rectangle(occupied, (r["bbox"][0],r["bbox"][1]), (r["bbox"][2],r["bbox"][3]), 255, -1)
        for l in lines: cv2.rectangle(occupied, (l["bbox"][0]-2,l["bbox"][1]-2), (l["bbox"][2]+2,l["bbox"][3]+2), 255, -1)
        images = photos + detect_images(img, occupied)
        tables_found = [] if "--no-tables" in sys.argv else tbl.detect_tables(img, tbl.ocr_lines(work, i))
        for k, t in enumerate(tables_found):
            t["id"] = f"tb{k}"; t["name"] = f"table-{k+1}"
        for k, r in enumerate(rects): r["id"] = f"r{k}"
        for k, l in enumerate(lines): l["id"] = f"l{k}"
        for k, im in enumerate(images): im["id"] = f"i{k}"
        layout = dict(page=i, width=W, height=H, pt_w=pi["pt_w"], pt_h=pi["pt_h"], dpi=dpi,
                      elements=rects + images + lines + elements + tables_found)
        json.dump(layout, open(f"{work}/layout/p{i}.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
        write_debug(work, i, img, layout)
        print(f"page {i}: ocr  text={len(elements)} rect={len(rects)} line={len(lines)} image={len(images)} table={len(tables_found)}")

if __name__ == "__main__":
    main()
