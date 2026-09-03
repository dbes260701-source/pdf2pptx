# -*- coding: utf-8 -*-
"""외부 프로세스를 부를 때 콘솔 창이 뜨지 않아야 한다.

배포 exe 는 windowed 로 빌드하지만, Windows 는 콘솔 프로그램을 자식으로 띄우면
그 자식을 위해 새 콘솔 창을 만든다. OCR 은 페이지마다 PowerShell 을 부르므로
10쪽 문서면 검은 창이 10번 깜빡였다. 업무 중에 쓸 수 없다는 실사용 보고로 고쳤다.

이 테스트는 그 회귀를 막는다. 창이 실제로 뜨는지는 자동으로 볼 수 없으니,
콘솔을 만들지 않게 하는 플래그가 실제로 전달되는지를 고정한다.
"""
import os
import subprocess

import pytest

import procutil


WINDOWS = os.name == "nt"


def test_run_passes_no_window_flag_on_windows(monkeypatch):
    seen = {}

    def fake(cmd, **kw):
        seen.update(kw)
        return "ok"

    monkeypatch.setattr(procutil.subprocess, "run", fake)
    procutil.run(["whatever"])

    if WINDOWS:
        assert seen.get("creationflags", 0) & subprocess.CREATE_NO_WINDOW, \
            "CREATE_NO_WINDOW 가 빠졌다 -- 콘솔 창이 다시 깜빡인다"
    else:
        assert "creationflags" not in seen      # 다른 OS 에서는 건드리지 않는다


def test_run_keeps_caller_creationflags(monkeypatch):
    """호출자가 준 플래그를 덮어쓰지 않고 더해야 한다."""
    seen = {}
    monkeypatch.setattr(procutil.subprocess, "run", lambda cmd, **kw: seen.update(kw))
    procutil.run(["x"], creationflags=0x1)
    assert seen["creationflags"] & 0x1
    if WINDOWS:
        assert seen["creationflags"] & subprocess.CREATE_NO_WINDOW


def test_run_forwards_other_kwargs(monkeypatch):
    seen = {}
    monkeypatch.setattr(procutil.subprocess, "run", lambda cmd, **kw: seen.update(kw))
    procutil.run(["x"], capture_output=True, timeout=5, check=True)
    assert seen["capture_output"] is True and seen["timeout"] == 5 and seen["check"] is True


@pytest.mark.parametrize("module,attr", [
    ("extract", "run_ocr"),
    ("render", "export_libreoffice"),
    ("app", "check_ocr"),
])
def test_external_callers_do_not_use_bare_subprocess_run(module, attr):
    """콘솔을 띄우는 외부 프로그램 호출부가 subprocess.run 으로 되돌아가지 않았는지.

    새 호출부를 추가할 때 procutil.run 대신 subprocess.run 을 쓰면 여기서 걸린다.
    """
    import inspect
    import importlib
    src = inspect.getsource(getattr(importlib.import_module(module), attr))
    assert "subprocess.run" not in src, \
        f"{module}.{attr} 이 subprocess.run 을 직접 부른다 -- procutil.run 을 써야 한다"
    assert "procutil.run" in src


def test_real_child_process_runs_without_console():
    """플래그를 넣고도 자식 프로세스가 정상 동작하고 출력을 받아오는지."""
    import sys
    r = procutil.run([sys.executable, "-c", "print('hello')"],
                     capture_output=True, text=True, timeout=60)
    assert r.returncode == 0
    assert "hello" in r.stdout
