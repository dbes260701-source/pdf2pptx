# -*- coding: utf-8 -*-
"""
PDF to PPTX Converter -- 배포용 실행기 (GUI + CLI)

GUI : 인자 없이 실행
CLI : PDF2PPTX.exe "파일.pdf" [--out 결과.pptx] [--pages 1,3] [--dpi 200] [--font "맑은 고딕"]
                   [--no-render] [--allow-degraded]
                   [--no-native] [--no-tables] [--no-ppt-check]

품질 게이트를 통과하지 못하면 0이 아닌 종료 코드로 끝난다 (규약은 quality.py 참조).
무인/배치 실행에서 부실한 변환이 성공으로 집계되지 않게 하기 위한 것이다.
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
def run_pipeline(pdf, out, work, pages=None, dpi=200, font="맑은 고딕", render=True, log=print,
                 allow_degraded=False, extra_extract=(), extra_render=()):
    """(출력 경로, 종료 코드). 품질 게이트가 실패하면 0이 아닌 코드를 돌려준다 (quality.py 규약)."""
    import extract, build, render as render_mod, quality

    def stage(name, mod, argv):
        log("")
        log(f"[{name}] 시작")
        old = sys.argv
        sys.argv = argv
        try:
            rc = mod.main()
        finally:
            sys.argv = old
        log(f"[{name}] 완료")
        return rc

    if not os.path.exists(pdf):
        log(f"[오류] 입력 PDF를 찾을 수 없습니다: {pdf}")
        return out, quality.EXIT_USAGE

    os.makedirs(work, exist_ok=True)
    pg = ["--pages", pages] if pages else []

    try:
        stage("1/3 분석 및 OCR", extract,
              ["extract", pdf, work, "--dpi", str(dpi)] + pg + list(extra_extract))
    except Exception as ex:
        log(f"[오류] 추출 실패: {ex}")
        return out, quality.EXIT_EXTRACT
    try:
        stage("2/3 PPTX 생성", build, ["build", work, out, "--font", font] + pg)
    except Exception as ex:
        log(f"[오류] PPTX 생성 실패: {ex}")
        return out, quality.EXIT_PACKAGE

    if not render:
        # 명시적 opt-out. 게이트가 돌지 않았다는 사실을 결과와 함께 분명히 남긴다.
        log("[경고] 렌더링 검수를 건너뛰어 품질 게이트가 실행되지 않았습니다. 결과를 직접 확인하세요.")
        return out, quality.EXIT_OK

    rc = stage("3/3 렌더링 검수", render_mod,
               ["render", out, work] + pg + (["--allow-degraded"] if allow_degraded else [])
               + list(extra_render))
    if rc:
        log(f"[품질 게이트 실패] 종료 코드 {rc}. 자세한 내용: {os.path.join(work, 'report.json')}")
    else:
        log(f"비교 이미지: {os.path.join(work, 'compare')}")
    return out, rc or quality.EXIT_OK


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
    import quality
    a = sys.argv[1:]
    def opt(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    pdf = a[0]
    base = os.path.splitext(os.path.basename(pdf))[0]
    outdir = os.path.dirname(os.path.abspath(pdf))
    out = opt("--out", os.path.join(outdir, base + "_편집가능.pptx"))
    work = opt("--work", os.path.join(outdir, "work_" + base))
    out, rc = run_pipeline(pdf, out, work, opt("--pages"), int(opt("--dpi", 200)),
                           opt("--font", "맑은 고딕"), "--no-render" not in a,
                           allow_degraded="--allow-degraded" in a,
                           extra_extract=[f for f in ("--no-native", "--no-tables") if f in a],
                           extra_render=[f for f in ("--no-ppt-check",) if f in a])
    print("")
    print(("완료: " if rc == quality.EXIT_OK else f"실패(종료 코드 {rc}): ") + out)
    return rc


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
    degraded_var = tk.BooleanVar(value=False)
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
            _, rc = run_pipeline(pdf, out, work, pages_var.get().strip() or None,
                                 int(dpi_var.get() or 200), font_var.get(), render_var.get(), log,
                                 allow_degraded=degraded_var.get())
            log("")
            if rc:
                log(f"===== 변환 완료 · 품질 게이트 실패 (코드 {rc}) =====")
                log("파일은 만들어졌지만 원본과 충분히 일치하지 않습니다. 비교 이미지를 확인하세요.")
            else:
                log("===== 변환 완료 =====")
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
    ttk.Checkbutton(opts, text="렌더링 검수", variable=render_var).pack(side="left", padx=(0, 12))
    ttk.Checkbutton(opts, text="품질 미달 허용", variable=degraded_var).pack(side="left", padx=(0, 12))
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
        sys.exit(main_cli())
    else:
        main_gui()
