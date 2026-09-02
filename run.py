"""
run.py -- one-shot pipeline:  PDF -> layout -> (overrides) -> PPTX -> PowerPoint render -> compare images
usage:
  python run.py <pdf> [--work <dir>] [--out <pptx>] [--pages 1,3] [--font NanumGothic] [--no-extract]
Steps:
  1. extract.py  (render, Windows OCR, text/line/rect/photo/image detection)  -> work/layout/pN.json + work/debug/pN_boxes.png
  2. build.py    (layout + work/overrides/pN.json -> pptx)
  3. render.py   (PowerPoint COM export -> work/render/sN.png, work/compare/cN.png side-by-side, oN.png overlay)
Re-run with --no-extract after editing overrides (text corrections) to rebuild + re-render only.
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
def run(cmd):
    print(">", " ".join(cmd)); subprocess.run(cmd, check=True, env=env)
if "--no-extract" not in sys.argv:
    run([sys.executable, os.path.join(HERE, "extract.py"), pdf, work] + (["--pages", pages] if pages else []))
run([sys.executable, os.path.join(HERE, "build.py"), work, out, "--font", font] + (["--pages", pages] if pages else []))
run([sys.executable, os.path.join(HERE, "render.py"), out, work] + (["--pages", pages] if pages else []))
print("done:", out)
