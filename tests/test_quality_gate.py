# -*- coding: utf-8 -*-
"""품질 게이트 자체에 대한 테스트.

평가서 §4.4 의 핵심 지적은 "커버리지가 아니라 실패 탐지 능력"이었다.
그래서 여기서는 통과 사례만이 아니라 **음성 대조군**(고의로 망가뜨린 출력이
반드시 거부되는가)을 함께 검증한다. 이 테스트가 깨지면 게이트가 무력화된 것이다.
"""
import copy
import numpy as np
import cv2
import pytest

import quality


# --------------------------------------------------------------- SSIM 기본 성질
def test_ssim_of_identical_image_is_one(page_img):
    g = cv2.cvtColor(page_img, cv2.COLOR_BGR2GRAY)
    assert quality.ssim_map(g, g).mean() == pytest.approx(1.0, abs=1e-6)


def test_metrics_of_identical_page_pass(page_img):
    m = quality.page_metrics(page_img, page_img.copy())
    assert m["ssim"] == pytest.approx(1.0, abs=1e-3)
    assert m["worst_tile_ssim"] == pytest.approx(1.0, abs=1e-3)
    assert m["mae"] == 0.0


# --------------------------------------------------------------- 음성 대조군
def test_locally_missing_object_is_caught_by_tile_metric(page_img):
    """큰 객체 하나를 지웠을 때, 페이지 평균은 멀쩡해 보여도 타일 최솟값이 잡아내야 한다.

    평가서 §4.2 "평균 픽셀 지표가 의미상 치명적인 누락을 과소평가한다"에 대한 대조군.
    """
    broken = page_img.copy()
    broken[420:700, 60:340] = 255          # 사진 블록을 통째로 제거
    m = quality.page_metrics(broken, page_img)
    th = quality.thresholds()
    assert m["worst_tile_ssim"] < th["tile_ssim"], "국소 누락을 타일 지표가 놓쳤다"

    report = dict(renderer="powerpoint", package_error=None, page_count=1, slide_count=1,
                  pages=[dict(page=1, text_coverage=1.0, **m)])
    code, fails = quality.evaluate(report)
    assert code == quality.EXIT_VISUAL
    assert report["status"] == "fail"
    assert any("국소 손실" in f for f in fails)


def test_blank_render_is_rejected(page_img):
    """빈 슬라이드가 나왔는데 통과하면 게이트가 무의미하다."""
    blank = np.full_like(page_img, 255)
    report = dict(renderer="powerpoint", package_error=None, page_count=1, slide_count=1,
                  pages=[dict(page=1, text_coverage=1.0, **quality.page_metrics(page_img, blank))])
    code, _ = quality.evaluate(report)
    assert code != quality.EXIT_OK


def test_identical_render_passes(page_img):
    """양성 대조군: 완벽한 결과는 통과해야 한다(게이트가 항상 실패하면 그것도 무의미)."""
    report = dict(renderer="powerpoint", package_error=None, page_count=1, slide_count=1,
                  pages=[dict(page=1, text_coverage=1.0,
                              **quality.page_metrics(page_img, page_img.copy()))])
    code, fails = quality.evaluate(report)
    assert code == quality.EXIT_OK and fails == [] and report["status"] == "pass"


# --------------------------------------------------------------- 종료 코드 규약
def _ok_report():
    return dict(renderer="powerpoint", package_error=None, page_count=1, slide_count=1,
                pages=[dict(page=1, ssim=0.99, worst_tile_ssim=0.95, worst_tile_bbox=[0, 0, 8, 8],
                            mae=1.0, text_coverage=1.0)])


def test_missing_renderer_is_exit_8_and_not_relaxed_by_degraded():
    r = _ok_report(); r["renderer"] = None
    assert quality.evaluate(copy.deepcopy(r))[0] == quality.EXIT_RENDERER
    # 렌더러가 없으면 애초에 품질을 확인하지 못한 것이므로 degraded 로도 통과시키지 않는다
    assert quality.evaluate(copy.deepcopy(r), allow_degraded=True)[0] == quality.EXIT_RENDERER


def test_package_error_is_exit_4_and_not_relaxed_by_degraded():
    r = _ok_report(); r["package_error"] = "BadZipFile: broken"
    assert quality.evaluate(copy.deepcopy(r))[0] == quality.EXIT_PACKAGE
    assert quality.evaluate(copy.deepcopy(r), allow_degraded=True)[0] == quality.EXIT_PACKAGE


def test_slide_count_shortfall_is_missing_content():
    r = _ok_report(); r["page_count"] = 3
    assert quality.evaluate(r)[0] == quality.EXIT_MISSING


def test_low_text_coverage_is_missing_content():
    r = _ok_report(); r["pages"][0]["text_coverage"] = 0.40
    code, fails = quality.evaluate(r)
    assert code == quality.EXIT_MISSING
    assert any("텍스트 복원율" in f for f in fails)


def test_allow_degraded_downgrades_visual_failure_but_records_it():
    r = _ok_report(); r["pages"][0]["ssim"] = 0.10
    code, fails = quality.evaluate(r, allow_degraded=True)
    assert code == quality.EXIT_OK
    assert r["status"] == "degraded"          # 성공과 구분되어야 한다
    assert fails and r["failures"] == fails   # 사유가 보고서에 남아야 한다


def test_thresholds_are_overridable(tmp_path, monkeypatch):
    import json
    p = tmp_path / "th.json"
    json.dump({"page_ssim": 0.99}, open(p, "w", encoding="utf-8"))
    monkeypatch.setenv("PDF2PPTX_THRESHOLDS", str(p))
    assert quality.thresholds()["page_ssim"] == 0.99
    assert quality.thresholds()["tile_ssim"] == quality.DEFAULTS["tile_ssim"]  # 나머지는 기본값 유지


# --------------------------------------------------------------- 텍스트 복원율
def test_text_coverage_counts_recovered_lines(work):
    assert quality.text_coverage(work, 1) == 1.0


def test_text_coverage_drops_when_element_deleted(work):
    import json, os
    p = os.path.join(work, "layout", "p1.json")
    lay = json.load(open(p, encoding="utf-8"))
    lay["elements"] = [e for e in lay["elements"] if e.get("id") != "t1"]
    json.dump(lay, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    assert quality.text_coverage(work, 1) < 0.5


def test_root_cause_wins_over_derived_symptom():
    """렌더러 부재는 SSIM 미측정·슬라이드 0장의 원인이므로 종료 코드가 8이어야 한다.

    이전에는 min(코드)를 써서 파생 증상인 6이 원인을 가렸다.
    """
    r = dict(renderer=None, package_error=None, page_count=3, slide_count=0,
             pages=[dict(page=1, text_coverage=0.1)])
    code, fails = quality.evaluate(r)
    assert code == quality.EXIT_RENDERER
    assert not any("장만 생성" in f for f in fails), "측정 불가를 '0장 생성'으로 단정하면 안 된다"
