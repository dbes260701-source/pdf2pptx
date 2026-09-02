import cv2, numpy as np

def line_masks(img, delta=2):
    """가로/세로 괘선 마스크. 흐린 실선(밝기차 3~5)도 잡도록 지역 대비를 사용."""
    H, W = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.int16)
    # 세로 이웃 평균보다 어두우면 가로선 후보, 가로 이웃 평균보다 어두우면 세로선 후보
    hcand = ((cv2.blur(g.astype(np.uint8), (1, 15)).astype(np.int16) - g) > delta).astype(np.uint8)
    vcand = ((cv2.blur(g.astype(np.uint8), (15, 1)).astype(np.int16) - g) > delta).astype(np.uint8)
    # 스캔 기울어짐으로 선이 1~2px 흔들려도 이어지도록 두께 방향으로 먼저 팽창
    hcand = cv2.dilate(hcand, np.ones((5, 1), np.uint8))
    vcand = cv2.dilate(vcand, np.ones((1, 5), np.uint8))
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, W//30), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(24, H//80)))
    hl = cv2.dilate(cv2.morphologyEx(hcand, cv2.MORPH_OPEN, hk), np.ones((3, 3), np.uint8))
    vl = cv2.dilate(cv2.morphologyEx(vcand, cv2.MORPH_OPEN, vk), np.ones((3, 3), np.uint8))
    return hl*255, vl*255

def segments(mask, horiz, min_len=40):
    n, lab, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    out = []
    for c in range(1, n):
        x, y, w, h, a = st[c]
        if horiz and (w < min_len or h > 14): continue
        if not horiz and (h < min_len or w > 14): continue
        out.append((int(x), int(y), int(x+w), int(y+h)))
    return out


def _cluster(vals, tol=9):
    vals = sorted(vals); out = []
    for v in vals:
        if out and v - out[-1][-1] <= tol: out[-1].append(v)
        else: out.append([v])
    return [int(round(np.mean(g))) for g in out]


class Grid:
    """페이지 전체의 괘선에서 셀 단위 격자를 복원한다."""
    def __init__(self, img, band=4, cover=0.80):
        self.hl, self.vl = line_masks(img)
        self.H, self.W = self.hl.shape
        self.band, self.cover = band, cover
        self.ys = _cluster([(s[1]+s[3])//2 for s in segments(self.hl, True)])
        self.xs = _cluster([(s[0]+s[2])//2 for s in segments(self.vl, False)])

    def has_h(self, y, x0, x1):
        if x1 - x0 < 12: return False
        b = self.hl[max(0, y-self.band):y+self.band+1, x0:x1]
        return b.size > 0 and (b > 0).any(0).mean() >= self.cover

    def has_v(self, x, y0, y1):
        if y1 - y0 < 8: return False
        b = self.vl[y0:y1, max(0, x-self.band):x+self.band+1]
        return b.size > 0 and (b > 0).any(1).mean() >= self.cover

    def cells(self):
        """네 변이 모두 있는 최소 사각형(셀) 목록. 행 구간마다 유효한 세로선만 사용한다."""
        out = []
        for i in range(len(self.ys) - 1):
            y0, y1 = self.ys[i], self.ys[i+1]
            if y1 - y0 < 14: continue
            cols = [x for x in self.xs if self.has_v(x, y0, y1)]
            for a, b in zip(cols, cols[1:]):
                if b - a < 20: continue
                if self.has_h(y0, a, b) and self.has_h(y1, a, b):
                    out.append((i, a, y0, b, y1))
        return out


def detect_tables(img, min_cells=4, min_w=110, min_h=45):
    g = Grid(img)
    cells = g.cells()
    if not cells: return []
    parent = list(range(len(cells)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    for i, c in enumerate(cells):
        for j in range(i+1, len(cells)):
            d = cells[j]
            share_v = abs(c[3]-d[1]) < 10 or abs(c[1]-d[3]) < 10          # 좌우 인접
            share_h = abs(c[4]-d[2]) < 10 or abs(c[2]-d[4]) < 10          # 상하 인접
            ov_y = min(c[4], d[4]) - max(c[2], d[2])
            ov_x = min(c[3], d[3]) - max(c[1], d[1])
            if (share_v and ov_y > 6) or (share_h and ov_x > 6): union(i, j)
    groups = {}
    for i, c in enumerate(cells): groups.setdefault(find(i), []).append(c)
    tables = []
    for cs in groups.values():
        if len(cs) < min_cells: continue
        xs = _cluster([c[1] for c in cs] + [c[3] for c in cs])
        ys = _cluster([c[2] for c in cs] + [c[4] for c in cs])
        bbox = [xs[0], ys[0], xs[-1], ys[-1]]
        if bbox[2]-bbox[0] < min_w or bbox[3]-bbox[1] < min_h: continue
        if len(xs) < 3 and len(ys) < 3: continue
        tables.append(dict(bbox=bbox, xs=xs, ys=ys, rows=len(ys)-1, cols=len(xs)-1,
                           filled=len(cs), cells=cs))
    return sorted(tables, key=lambda t: (t["bbox"][1], t["bbox"][0]))


if __name__ == "__main__":
    for p in (1, 2, 3, 4, 5, 6):
        img = cv2.imread(f"work/pages/p{p}.png")
        ts = detect_tables(img)
        print(f"== page {p}: {len(ts)} tables")
        for t in ts:
            print(f"    {t['rows']}행 x {t['cols']}열  채워진셀={t['filled']}/{t['rows']*t['cols']}  bbox={t['bbox']}")
