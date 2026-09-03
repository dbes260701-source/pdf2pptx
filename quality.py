# -*- coding: utf-8 -*-
"""
quality.py -- 변환 품질 측정과 게이트(fail-closed) 판정.

평가서 지적(§4.2 / §4.3) 대응:
  - 렌더링 검수가 실패해도 종료 코드 0으로 "성공" 처리되던 문제를 없앤다.
  - 페이지 전체 평균 지표만 보면 큰 객체 하나가 통째로 빠져도 통과하므로,
    타일 단위 최솟값과 요소 누락률을 함께 본다.

종료 코드 규약(README 참조):
  0 필요한 품질 게이트 통과
  2 잘못된 입력 또는 옵션
  3 PDF 파싱/추출 실패
  4 PPTX 패키지 검증 실패
  5 시각 품질 임계값 미달
  6 원본 요소 누락 감지
  7 PowerPoint 열기/저장/재열기 실패
  8 필수 렌더러 또는 외부 의존성 없음
"""
import os, json, glob
import numpy as np, cv2

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_EXTRACT = 3
EXIT_PACKAGE = 4
EXIT_VISUAL = 5
EXIT_MISSING = 6
EXIT_POWERPOINT = 7
EXIT_RENDERER = 8

# 임계값. 환경변수 PDF2PPTX_THRESHOLDS=<json 경로> 로 덮어쓸 수 있다.
# 문서군마다 적정값이 다르므로 코드에 박지 않고 여기 한 곳에 모은다.
DEFAULTS = dict(
    page_ssim=0.75,        # 페이지 전체 SSIM 하한
    tile_ssim=0.35,        # 최악 타일 SSIM 하한 (국소 누락 탐지)
    tile_grid=8,           # 타일 격자 (8x8)
    max_mae=28.0,          # 평균 절대 픽셀 오차 상한
    text_coverage=0.90,    # OCR 줄 중 PPTX 텍스트로 복원된 비율 하한
    max_slide_gap=0,       # 원본 페이지 수 - 슬라이드 수 허용 차이
)


def thresholds():
    t = dict(DEFAULTS)
    p = os.environ.get("PDF2PPTX_THRESHOLDS")
    if p and os.path.exists(p):
        t.update(json.load(open(p, encoding="utf-8")))
    return t


def ssim_map(a, b):
    """회색조 두 이미지의 SSIM 맵. gaussian 11x11, sigma 1.5 (Wang et al. 2004)."""
    a = a.astype(np.float64); b = b.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k, s = (11, 11), 1.5
    mu_a = cv2.GaussianBlur(a, k, s); mu_b = cv2.GaussianBlur(b, k, s)
    mu_a2, mu_b2, mu_ab = mu_a * mu_a, mu_b * mu_b, mu_a * mu_b
    va = cv2.GaussianBlur(a * a, k, s) - mu_a2
    vb = cv2.GaussianBlur(b * b, k, s) - mu_b2
    vab = cv2.GaussianBlur(a * b, k, s) - mu_ab
    return ((2 * mu_ab + C1) * (2 * vab + C2)) / ((mu_a2 + mu_b2 + C1) * (va + vb + C2))


def page_metrics(orig_bgr, rend_bgr, grid=None):
    """원본 페이지와 렌더 결과의 지표. 국소 손실을 잡기 위해 타일 최솟값을 함께 낸다."""
    grid = grid or DEFAULTS["tile_grid"]
    if rend_bgr.shape[:2] != orig_bgr.shape[:2]:
        rend_bgr = cv2.resize(rend_bgr, (orig_bgr.shape[1], orig_bgr.shape[0]))
    go = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2GRAY)
    gr = cv2.cvtColor(rend_bgr, cv2.COLOR_BGR2GRAY)
    m = ssim_map(go, gr)
    H, W = m.shape
    th, tw = max(1, H // grid), max(1, W // grid)
    tiles = [(float(m[y:y + th, x:x + tw].mean()), [x, y, min(x + tw, W), min(y + th, H)])
             for y in range(0, H - th + 1, th) for x in range(0, W - tw + 1, tw)]
    worst_val, worst_box = min(tiles, key=lambda t: t[0]) if tiles else (float(m.mean()), [0, 0, W, H])
    return dict(
        ssim=round(float(m.mean()), 4),
        worst_tile_ssim=round(worst_val, 4),
        worst_tile_bbox=worst_box,
        mae=round(float(np.abs(go.astype(np.int16) - gr.astype(np.int16)).mean()), 3),
    )


def text_coverage(work, page):
    """OCR이 읽은 줄 중 레이아웃 요소로 살아남은 비율. 조용한 누락 탐지용."""
    ocr_p, lay_p = f"{work}/ocr/p{page}.json", f"{work}/layout/p{page}.json"
    if not (os.path.exists(ocr_p) and os.path.exists(lay_p)):
        return None
    ocr = json.load(open(ocr_p, encoding="utf-8-sig"))
    lay = json.load(open(lay_p, encoding="utf-8"))
    src = [ln["text"].strip() for ln in ocr.get("lines", []) if ln.get("text", "").strip()]
    if not src:
        return 1.0
    out = []
    for e in lay.get("elements", []):
        if e.get("type") == "text":
            out += [s.strip() for s in e.get("text", "").split("\n")]
        elif e.get("type") == "table":
            out += [c.strip() for row in e.get("cells", []) for c in row]
    pool = list(out)
    hit = 0
    for s in src:
        if s in pool:
            pool.remove(s); hit += 1
    return round(hit / len(src), 4)


# 보고 우선순위: 앞쪽일수록 근본 원인. 렌더러가 없으면 "슬라이드 0장"이나 SSIM 미측정은
# 그 결과일 뿐이므로, 종료 코드는 파생 증상이 아니라 원인을 가리켜야 한다.
_PRECEDENCE = [EXIT_USAGE, EXIT_EXTRACT, EXIT_RENDERER, EXIT_PACKAGE,
               EXIT_POWERPOINT, EXIT_MISSING, EXIT_VISUAL]


def evaluate(report, th=None, allow_degraded=False):
    """report -> (exit_code, [실패 사유]). allow_degraded=True 면 시각/누락 실패를 경고로 낮춘다."""
    th = th or thresholds()
    fails = []   # (exit_code, message)

    no_renderer = report.get("renderer") in (None, "none")
    if no_renderer:
        fails.append((EXIT_RENDERER, "렌더러(PowerPoint/LibreOffice)를 찾지 못해 시각 검수를 하지 못했습니다."))
    if report.get("package_error"):
        fails.append((EXIT_PACKAGE, f"PPTX 패키지 검증 실패: {report['package_error']}"))

    # 렌더러가 없을 때의 슬라이드 수는 "0장 생성"이 아니라 "측정 불가"다.
    if not no_renderer:
        gap = report.get("page_count", 0) - report.get("slide_count", 0)
        if gap > th["max_slide_gap"]:
            fails.append((EXIT_MISSING,
                          f"원본 {report['page_count']}쪽 중 {report['slide_count']}장만 생성되었습니다."))

    for p in report.get("pages", []):
        n = p.get("page")
        if p.get("ssim") is not None and p["ssim"] < th["page_ssim"]:
            fails.append((EXIT_VISUAL, f"{n}쪽 SSIM {p['ssim']} < {th['page_ssim']}"))
        if p.get("worst_tile_ssim") is not None and p["worst_tile_ssim"] < th["tile_ssim"]:
            fails.append((EXIT_VISUAL, f"{n}쪽 국소 손실: 최악 타일 SSIM {p['worst_tile_ssim']} "
                                       f"< {th['tile_ssim']} @ {p.get('worst_tile_bbox')}"))
        if p.get("mae") is not None and p["mae"] > th["max_mae"]:
            fails.append((EXIT_VISUAL, f"{n}쪽 MAE {p['mae']} > {th['max_mae']}"))
        if p.get("text_coverage") is not None and p["text_coverage"] < th["text_coverage"]:
            fails.append((EXIT_MISSING, f"{n}쪽 텍스트 복원율 {p['text_coverage']} < {th['text_coverage']}"))

    report["failures"] = [m for _, m in fails]
    if not fails:
        report["status"] = "pass"
        return EXIT_OK, []
    # 의존성/패키지 실패는 degraded 모드로도 봐주지 않는다.
    hard = [f for f in fails if f[0] in (EXIT_PACKAGE, EXIT_RENDERER)]
    if allow_degraded and not hard:
        report["status"] = "degraded"
        return EXIT_OK, [m for _, m in fails]
    report["status"] = "fail"
    return min((f[0] for f in fails), key=_PRECEDENCE.index), [m for _, m in fails]


def validate_package(pptx):
    """PPTX가 zip/XML로 온전하고 python-pptx로 다시 열리는지. 실패 시 사유 문자열."""
    import zipfile
    from xml.etree import ElementTree
    try:
        with zipfile.ZipFile(pptx) as z:
            bad = z.testzip()
            if bad:
                return f"손상된 zip 항목: {bad}"
            names = set(z.namelist())
            for req in ("[Content_Types].xml", "ppt/presentation.xml"):
                if req not in names:
                    return f"필수 파트 누락: {req}"
            for n in names:
                if n.endswith((".xml", ".rels")):
                    ElementTree.fromstring(z.read(n))
        from pptx import Presentation
        Presentation(pptx)
    except Exception as ex:
        return f"{type(ex).__name__}: {ex}"
    return None


def write_report(work, report):
    os.makedirs(work, exist_ok=True)
    p = os.path.join(work, "report.json")
    json.dump(report, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return p


def summary(report):
    lines = [f"품질 판정: {report.get('status', '?')}  (렌더러: {report.get('renderer') or '없음'})"]
    for p in report.get("pages", []):
        lines.append(f"  {p['page']}쪽  SSIM {p.get('ssim')}  최악타일 {p.get('worst_tile_ssim')}"
                     f"  MAE {p.get('mae')}  텍스트복원율 {p.get('text_coverage')}")
    for f in report.get("failures", []):
        lines.append(f"  ! {f}")
    return "\n".join(lines)
