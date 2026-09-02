"""
render.py -- render PPTX slides via PowerPoint COM and build side-by-side comparison images
usage: python render.py <pptx> <workdir> [--pages 1,2]
Outputs: work/render/sN.png, work/compare/cN.png (original | render), work/compare/oN.png (overlay)
"""
import sys, os, glob
import cv2, numpy as np

def find_soffice():
    import shutil
    p = shutil.which("soffice") or shutil.which("soffice.exe")
    if p: return p
    for c in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.exists(c): return c
    return None

def export_libreoffice(pptx, outdir, W, H):
    """fallback when PowerPoint is unavailable: pptx -> pdf -> page images"""
    soffice = find_soffice()
    if not soffice: raise RuntimeError("PowerPoint도 LibreOffice도 찾을 수 없어 렌더링 검수를 건너뜁니다.")
    import subprocess, glob as _glob, pdfio
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", outdir, os.path.abspath(pptx)],
                   check=True, capture_output=True, timeout=600)
    pdfs = _glob.glob(os.path.join(outdir, "*.pdf"))
    if not pdfs: raise RuntimeError("LibreOffice PDF 변환에 실패했습니다.")
    n = pdfio.page_count(pdfs[0])
    for k in range(1, n + 1):
        w_pt, _ = pdfio.page_size(pdfs[0], k)
        pdfio.render_page(pdfs[0], k, W / w_pt * 72, os.path.join(outdir, f"s{k}.png"))
    os.remove(pdfs[0])
    return n

def export(pptx, outdir, W, H):
    try:
        return export_powerpoint(pptx, outdir, W, H)
    except Exception as ex:
        print("PowerPoint 렌더링 실패, LibreOffice로 전환:", ex)
        return export_libreoffice(pptx, outdir, W, H)

def export_powerpoint(pptx, outdir, W, H):
    import win32com.client, pythoncom
    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("PowerPoint.Application")
    pres = app.Presentations.Open(os.path.abspath(pptx), ReadOnly=True, Untitled=False, WithWindow=False)
    n = pres.Slides.Count
    for k in range(1, n+1):
        pres.Slides(k).Export(os.path.abspath(f"{outdir}/s{k}.png"), "PNG", W, H)
    pres.Close()
    try: app.Quit()
    except Exception: pass
    return n

def main():
    pptx, work = sys.argv[1], sys.argv[2]
    pages = None
    if "--pages" in sys.argv: pages = [int(v) for v in sys.argv[sys.argv.index("--pages")+1].split(",")]
    os.makedirs(f"{work}/render", exist_ok=True); os.makedirs(f"{work}/compare", exist_ok=True)
    first = cv2.imread(sorted(glob.glob(f"{work}/pages/p*.png"))[0]); H, W = first.shape[:2]
    n = export(pptx, f"{work}/render", W, H)
    layout_pages = sorted(int(os.path.basename(f)[1:-5]) for f in glob.glob(f"{work}/layout/p*.json"))
    if pages: layout_pages = [p for p in layout_pages if p in pages]
    for k, pg in enumerate(layout_pages, start=1):
        if k > n: break
        o = cv2.imread(f"{work}/pages/p{pg}.png"); r = cv2.imread(f"{work}/render/s{k}.png")
        r = cv2.resize(r, (o.shape[1], o.shape[0]))
        side = np.concatenate([o, np.full((o.shape[0], 8, 3), (0,0,255), np.uint8), r], axis=1)
        cv2.imwrite(f"{work}/compare/c{pg}.png", cv2.resize(side, (side.shape[1]//2, side.shape[0]//2)))
        ov = cv2.addWeighted(o, 0.5, r, 0.5, 0)
        cv2.imwrite(f"{work}/compare/o{pg}.png", ov)
        cv2.imwrite(f"{work}/render/s{k}_small.png", cv2.resize(r, (r.shape[1]//2, r.shape[0]//2)))
    print("rendered", n, "slides")

if __name__ == "__main__":
    main()
