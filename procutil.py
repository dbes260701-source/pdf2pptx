# -*- coding: utf-8 -*-
"""
procutil.py -- 콘솔 창을 띄우지 않는 외부 프로세스 실행

배포 exe 는 windowed(console=False)로 빌드하지만, 그것만으로는 부족하다.
Windows 에서 콘솔 프로그램(powershell.exe, soffice.exe)을 자식으로 띄우면
OS 가 그 자식을 위해 새 콘솔 창을 만든다. GUI 앱에서는 이게 검은 창이
깜빡이는 것으로 보인다. OCR 은 페이지마다 PowerShell 을 부르므로
10쪽 문서면 창이 10번 깜빡인다 -- 업무 중에 쓰기 어렵다.

CREATE_NO_WINDOW 로 자식에게 콘솔을 주지 않으면 해결된다.
출력은 어차피 파이프로 받으므로 잃는 것이 없다.
"""
import os
import subprocess

# Windows 에서만 의미가 있는 플래그. 다른 OS 에서는 0 (영향 없음).
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def run(cmd, **kw):
    """subprocess.run 과 같지만 Windows 에서 콘솔 창을 만들지 않는다.

    호출자가 creationflags 를 직접 넘기면 그 값에 플래그를 더한다.
    """
    if _NO_WINDOW:
        kw["creationflags"] = kw.get("creationflags", 0) | _NO_WINDOW
    return subprocess.run(cmd, **kw)
