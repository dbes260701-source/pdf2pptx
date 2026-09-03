# -*- coding: utf-8 -*-
"""PowerPoint 호환성 검증 게이트 (ROADMAP R4 / 평가서 B §4.8).

PowerPoint COM 이 필요한 테스트는 needs_powerpoint 로 표시해 없는 환경에서 건너뛴다.
COM 없이 검증할 수 있는 것(개체 목록 대조, 차이 판정, 게이트 연결)은 항상 돈다.
"""
import os
import shutil
import zipfile

import pytest

import ppt_validate as pv
import quality


# skipif 로 없는 환경에서는 자동으로 건너뛰고, 마커로 -m "not needs_powerpoint" 도 되게 한다.
needs_powerpoint = pytest.mark.needs_powerpoint(
    pytest.mark.skipif(not pv.available(), reason="PowerPoint COM 이 없는 환경"))


@pytest.fixture
def pptx(work, tmp_path):
    import sys
    import build as build_mod
    out = str(tmp_path / "out.pptx")
    argv = sys.argv
    sys.argv = ["build", work, out]
    try:
        build_mod.main()
    finally:
        sys.argv = argv
    return out


# --------------------------------------------------------------- 개체 목록
def test_inventory_captures_content(pptx):
    inv = pv.inventory(pptx)
    assert inv["slide_count"] == 1
    s = inv["slides"][0]
    assert s["shapes"] >= 4
    assert s["pictures"] >= 1
    assert any("보고서 제목" in t for t in s["texts"])


def test_identical_files_have_no_differences(pptx, tmp_path):
    copy = str(tmp_path / "copy.pptx")
    shutil.copy(pptx, copy)
    assert pv._diff(pv.inventory(pptx), pv.inventory(copy)) == []


# --------------------------------------------------------------- 차이 판정
def test_lost_text_is_reported():
    before = dict(slide_count=1, width=100, height=100,
                  slides=[dict(shapes=3, texts=["가", "나"], pictures=1, tables=[])])
    after = dict(slide_count=1, width=100, height=100,
                 slides=[dict(shapes=2, texts=["가"], pictures=1, tables=[])])
    d = pv._diff(before, after)
    assert any("개체 수" in x for x in d)
    assert any("글자" in x and "유실" in x for x in d)


def test_lost_picture_is_reported():
    before = dict(slide_count=1, width=100, height=100,
                  slides=[dict(shapes=2, texts=[], pictures=2, tables=[])])
    after = dict(slide_count=1, width=100, height=100,
                 slides=[dict(shapes=2, texts=[], pictures=0, tables=[])])
    assert any("그림" in x for x in pv._diff(before, after))


def test_slide_count_change_short_circuits():
    before = dict(slide_count=3, width=1, height=1, slides=[])
    after = dict(slide_count=1, width=1, height=1, slides=[])
    d = pv._diff(before, after)
    assert len(d) == 1 and "슬라이드 수" in d[0]


def test_subpoint_size_rounding_is_not_a_difference():
    """PowerPoint 는 슬라이드 크기를 내부 정밀도로 반올림한다. 실측 0.06pt 차이는 손실이 아니다."""
    before = dict(slide_count=1, width=7563611, height=10693907, slides=[])
    after = dict(slide_count=1, width=7562850, height=10693400, slides=[])
    assert pv._diff(before, after) == []


def test_real_paper_size_change_is_a_difference():
    """용지가 실제로 바뀌면 허용 오차를 훨씬 넘으므로 반드시 잡혀야 한다."""
    before = dict(slide_count=1, width=7563611, height=10693907, slides=[])
    after = dict(slide_count=1, width=9144000, height=6858000, slides=[])
    assert any("슬라이드 크기" in x for x in pv._diff(before, after))


# --------------------------------------------------------------- 게이트 연결
def _report(pw):
    return dict(renderer="powerpoint", package_error=None, page_count=1, slide_count=1,
                powerpoint=pw,
                pages=[dict(page=1, ssim=0.99, worst_tile_ssim=0.95, mae=1.0,
                            text_coverage=1.0, unsupported=[])])


def test_powerpoint_failure_is_exit_7():
    r = _report(dict(status="fail", differences=["1번 슬라이드 그림 2 -> 0"], error=None))
    code, fails = quality.evaluate(r)
    assert code == quality.EXIT_POWERPOINT
    assert any("PowerPoint 왕복" in f for f in fails)


def test_powerpoint_failure_is_not_relaxed_by_degraded():
    """호환성 실패는 --allow-degraded 로도 봐주지 않는다. 파일이 안 열리면 편집도 못 한다."""
    r = _report(dict(status="fail", differences=["글자 3건 유실"], error=None))
    code, _ = quality.evaluate(r, allow_degraded=True)
    assert code == quality.EXIT_POWERPOINT


@pytest.mark.parametrize("status", ["unavailable", "skipped", "pass"])
def test_non_failing_powerpoint_statuses_pass_the_gate(status):
    """PowerPoint 가 없는 환경(CI, LibreOffice 전용)을 실패로 만들지 않는다."""
    code, _ = quality.evaluate(_report(dict(status=status, differences=[], error=None)))
    assert code == quality.EXIT_OK


def test_missing_powerpoint_key_does_not_crash_gate():
    r = _report(None)
    del r["powerpoint"]
    assert quality.evaluate(r)[0] == quality.EXIT_OK


# --------------------------------------------------------------- 실제 왕복
@needs_powerpoint
def test_roundtrip_of_valid_file_passes(pptx, tmp_path):
    r = pv.roundtrip(pptx, str(tmp_path / "rt"))
    assert r["status"] == "pass", f"멀쩡한 파일이 거부됐다: {r}"
    assert r["opened"] and r["saved"]
    assert os.path.exists(r["roundtrip_path"])


@needs_powerpoint
def test_roundtrip_rejects_unopenable_file(tmp_path):
    """음성 대조군: PowerPoint 가 열지 못하는 파일은 반드시 fail 이어야 한다."""
    bad = tmp_path / "broken.pptx"
    bad.write_bytes(b"this is not a pptx at all")
    r = pv.roundtrip(str(bad), str(tmp_path / "rt"))
    assert r["status"] == "fail"
    assert r["error"]


@needs_powerpoint
def test_roundtrip_rejects_file_with_broken_slide_xml(pptx, tmp_path):
    """음성 대조군: 슬라이드 XML 이 깨진 파일."""
    bad = str(tmp_path / "badslide.pptx")
    with zipfile.ZipFile(pptx) as src, zipfile.ZipFile(bad, "w") as dst:
        for it in src.infolist():
            data = src.read(it.filename)
            if it.filename.startswith("ppt/slides/slide"):
                data = b"<not-a-slide/>"
            dst.writestr(it, data)
    r = pv.roundtrip(bad, str(tmp_path / "rt"))
    assert r["status"] == "fail", f"깨진 슬라이드를 통과시켰다: {r}"
