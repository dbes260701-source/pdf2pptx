"""
run.py -- one-shot pipeline:  PDF -> layout -> (overrides) -> PPTX -> PowerPoint render -> compare + quality gate
usage:
  python run.py <pdf> [--work <dir>] [--out <pptx>] [--pages 1,3] [--font NanumGothic]
                      [--no-extract] [--no-render] [--allow-degraded]
Steps:
  1. extract.py  (render, Windows OCR, text/line/rect/photo/image detection)  -> work/layout/pN.json + work/debug/pN_boxes.png
  2. build.py    (layout + work/overrides/pN.json -> pptx)
  3. render.py   (PowerPoint COM export -> work/render/sN.png, compare/cN.png, oN.png, report.json + 품질 게이트)
Re-run with --no-extract after editing overrides (text corrections) to rebuild + re-render only.

종료 코드는 quality.py 규약을 따른다. 품질 게이트 실패는 0이 아닌 코드로 끝나므로
배치 스크립트에서 부실한 변환을 성공으로 오인하지 않는다.
"""
import sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
def arg(k, d=None):
    return sys.argv[sys.argv.index(k)+1] if k in sys.argv else d
pdf = sys.argv[1]
base = os.path.splitext(os.path.basename(pdf))[0]
work = arg("--work", os.path.join(os.getcwd(), "work_" + base))
out = arg("--out", os.path.join(os.getcwd(), base + "_편집가능.pptx"))
pages = arg("--pages"); font = arg("--font", "NanumGothic")
env = dict(os.environ, PYTHONIOENCODING="utf-8")

def run(cmd, check=True):
    print(">", " ".join(cmd))
    rc = subprocess.run(cmd, env=env).returncode
    if check and rc:
        sys.exit(rc)
    return rc

if "--no-extract" not in sys.argv:
    run([sys.executable, os.path.join(HERE, "extract.py"), pdf, work] + (["--pages", pages] if pages else []))
run([sys.executable, os.path.join(HERE, "build.py"), work, out, "--font", font] + (["--pages", pages] if pages else []))

if "--no-render" in sys.argv:
    print("[경고] 렌더링 검수를 건너뛰어 품질 게이트가 실행되지 않았습니다. 결과를 직접 확인하세요.")
    print("done:", out)
    sys.exit(0)

# 게이트 결과를 그대로 종료 코드로 전달한다 (여기서 sys.exit 하지 않으면 fail-open 이 된다)
rc = run([sys.executable, os.path.join(HERE, "render.py"), out, work]
         + (["--pages", pages] if pages else [])
         + (["--allow-degraded"] if "--allow-degraded" in sys.argv else []), check=False)
print(("done: " if rc == 0 else f"품질 게이트 실패(코드 {rc}): ") + out)
sys.exit(rc)
