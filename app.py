# -*- coding: utf-8 -*-
"""
PDF to PPTX Converter -- 배포용 실행기 (GUI + CLI)

GUI : 인자 없이 실행
CLI : PDF2PPTX.exe "파일.pdf" [--out 결과.pptx] [--pages 1,3] [--dpi 200] [--font "맑은 고딕"] [--no-render]
"""
import os, sys, io, threading, traceback, queue, subprocess

# windowed(콘솔 없는) 빌드에서는 stdout/stderr가 None이라 print가 예외를 낸다
if sys.stdout is None: sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None: sys.stderr = open(os.devnull, "w", encoding="utf-8")


class _QueueWriter(io.TextIOBase):
    """모듈들의 print 출력을 GUI 로그로 전달"""
    def __init__(self, put): self.put = put
    def write(self, s):
        if s and s.strip(): self.put(s.rstrip())
        return len(s)
    def flush(self): pass


APP_TITLE = "PDF → 편집 가능한 PowerPoint 변환기"
VERSION = "1.0"


def respath(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


# --------------------------------------------------------------- pipeline
def run_pipeline(pdf, out, work, pages=None, dpi=200, font="맑은 고딕", render=True, log=print):
    import extract, build, render as render_mod

    def stage(name, mod, argv):
        log(f"\n[{name}] 시작")
        old = sys.argv
        sys.argv = argv
        try:
            mod.main()
        finally:
            sys.argv = old
        log(f"[{name}] 완료")

    os.makedirs(work, exist_ok=True)
    pg = ["--pages", pages] if pages else []

    stage("1/3 분석 및 OCR", extract, ["extract", pdf, work, "--dpi", str(dpi)] + pg)
    stage("2/3 PPTX 생성", build, ["build", work, out, "--font", font] + pg)
    if render:
        try:
            stage("3/3 렌더링 검수", render_mod, ["render", out, work] + pg)
            log(f"비교 이미지: {os.path.join(work, 'compare')}")
        except Exception as ex:
            log(f"[3/3 렌더링 검수] 건너뜀: {ex}")
            log("PowerPoint 또는 LibreOffice가 설치되어 있으면 검수 이미지를 만들 수 있습니다.")
    return out


def check_ocr():
    """한국어 Windows OCR 사용 가능 여부"""
    ps = ("[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null; "
          "[Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { $_.LanguageTag }")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, text=True, timeout=60)
        tags = [t.strip() for t in r.stdout.split()]
        return any(t.lower().startswith("ko") for t in tags), tags
    except Exception:
        return False, []


# --------------------------------------------------------------- CLI
def main_cli():
    a = sys.argv[1:]
    def opt(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    pdf = a[0]
    base = os.path.splitext(os.path.basename(pdf))[0]
    outdir = os.path.dirname(os.path.abspath(pdf))
    out = opt("--out", os.path.join(outdir, base + "_편집가능.pptx"))
    work = opt("--work", os.path.join(outdir, "work_" + base))
    run_pipeline(pdf, out, work, opt("--pages"), int(opt("--dpi", 200)),
                 opt("--font", "맑은 고딕"), "--no-render" not in a)
    print("\n완료:", out)


# --------------------------------------------------------------- GUI
def main_gui():
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox

    root = tk.Tk()
    root.title(f"{APP_TITLE}  v{VERSION}")
    root.geometry("760x560")
    try:
        root.iconbitmap(respath("icon.ico"))
    except Exception:
        pass

    pdf_var = tk.StringVar()
    out_var = tk.StringVar()
    pages_var = tk.StringVar()
    dpi_var = tk.StringVar(value="200")
    font_var = tk.StringVar(value="맑은 고딕")
    render_var = tk.BooleanVar(value=True)
    open_var = tk.BooleanVar(value=True)
    msgs = queue.Queue()
    state = {"running": False}

    def log(*parts):
        msgs.put(" ".join(str(p) for p in parts) + "\n")

    def pump():
        while not msgs.empty():
            txt.configure(state="normal")
            txt.insert("end", msgs.get())
            txt.see("end")
            txt.configure(state="disabled")
        root.after(120, pump)

    def pick():
        p = filedialog.askopenfilename(title="변환할 PDF 선택", filetypes=[("PDF 파일", "*.pdf")])
        if p:
            pdf_var.set(p)
            base = os.path.splitext(os.path.basename(p))[0]
            out_var.set(os.path.join(os.path.dirname(p), base + "_편집가능.pptx"))

    def pick_out():
        p = filedialog.asksaveasfilename(title="저장 위치", defaultextension=".pptx",
                                         filetypes=[("PowerPoint", "*.pptx")],
                                         initialfile=os.path.basename(out_var.get() or "결과_편집가능.pptx"))
        if p:
            out_var.set(p)

    _orig_out, _orig_err = sys.stdout, sys.stderr

    def worker():
        try:
            pdf = pdf_var.get()
            out = out_var.get()
            work = os.path.join(os.path.dirname(os.path.abspath(out)),
                                "work_" + os.path.splitext(os.path.basename(pdf))[0])
            sys.stdout = _QueueWriter(log); sys.stderr = sys.stdout
            log(f"입력: {pdf}")
            log(f"출력: {out}")
            ok, tags = check_ocr()
            if not ok:
                log("경고: 한국어 Windows OCR을 찾지 못했습니다. 설치된 언어:", tags or "없음")
                log("설정 > 시간 및 언어 > 언어에서 한국어 선택 기능(OCR)을 설치하세요.")
            run_pipeline(pdf, out, work, pages_var.get().strip() or None,
                         int(dpi_var.get() or 200), font_var.get(), render_var.get(), log)
            log("\n===== 변환 완료 =====")
            log(f"결과 파일: {out}")
            if open_var.get():
                os.startfile(out)
        except Exception:
            log("\n[오류]\n" + traceback.format_exc())
        finally:
            sys.stdout = _orig_out; sys.stderr = _orig_err
            state["running"] = False

    def start():
        if not pdf_var.get() or not os.path.exists(pdf_var.get()):
            messagebox.showwarning(APP_TITLE, "변환할 PDF 파일을 선택하세요.")
            return
        if not out_var.get():
            messagebox.showwarning(APP_TITLE, "저장할 위치를 지정하세요.")
            return
        btn_run.configure(state="disabled")
        state["running"] = True
        bar.start(12)
        txt.configure(state="normal"); txt.delete("1.0", "end"); txt.configure(state="disabled")
        threading.Thread(target=worker, daemon=True).start()

    def watch_done():
        if not state["running"] and str(btn_run["state"]) == "disabled" and msgs.empty():
            bar.stop(); btn_run.configure(state="normal")
        root.after(300, watch_done)

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="PDF 파일").grid(row=0, column=0, sticky="w")
    ttk.Entry(frm, textvariable=pdf_var, width=68).grid(row=0, column=1, sticky="we", padx=6)
    ttk.Button(frm, text="찾아보기", command=pick).grid(row=0, column=2)

    ttk.Label(frm, text="저장 위치").grid(row=1, column=0, sticky="w", pady=6)
    ttk.Entry(frm, textvariable=out_var, width=68).grid(row=1, column=1, sticky="we", padx=6, pady=6)
    ttk.Button(frm, text="변경", command=pick_out).grid(row=1, column=2, pady=6)

    opts = ttk.Frame(frm)
    opts.grid(row=2, column=0, columnspan=3, sticky="we", pady=(4, 10))
    ttk.Label(opts, text="페이지(예: 1,3-비우면 전체)").pack(side="left")
    ttk.Entry(opts, textvariable=pages_var, width=12).pack(side="left", padx=(6, 16))
    ttk.Label(opts, text="해상도 DPI").pack(side="left")
    ttk.Combobox(opts, textvariable=dpi_var, values=["150", "200", "300"], width=6,
                 state="readonly").pack(side="left", padx=(6, 16))
    ttk.Label(opts, text="폰트").pack(side="left")
    ttk.Combobox(opts, textvariable=font_var, values=["맑은 고딕", "NanumGothic", "Noto Sans KR"], width=12,
                 state="readonly").pack(side="left", padx=(6, 16))
    ttk.Checkbutton(opts, text="렌더링 검수 이미지 생성", variable=render_var).pack(side="left", padx=(0, 16))
    ttk.Checkbutton(opts, text="완료 후 파일 열기", variable=open_var).pack(side="left")

    btn_run = ttk.Button(frm, text="변환 시작", command=start)
    btn_run.grid(row=3, column=0, columnspan=3, sticky="we")
    bar = ttk.Progressbar(frm, mode="indeterminate")
    bar.grid(row=4, column=0, columnspan=3, sticky="we", pady=8)

    txt = tk.Text(frm, height=20, state="disabled", wrap="word", bg="#1E1E1E", fg="#D4D4D4",
                  insertbackground="#D4D4D4")
    txt.grid(row=5, column=0, columnspan=3, sticky="nsew")
    sb = ttk.Scrollbar(frm, command=txt.yview)
    sb.grid(row=5, column=3, sticky="ns")
    txt.configure(yscrollcommand=sb.set)

    frm.columnconfigure(1, weight=1)
    frm.rowconfigure(5, weight=1)

    log(f"{APP_TITLE}  v{VERSION}")
    log("PDF를 고르고 '변환 시작'을 누르면 텍스트 상자·도형·이미지로 재구성한 PPTX를 만듭니다.")
    pump(); watch_done()
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        main_cli()
    else:
        main_gui()
