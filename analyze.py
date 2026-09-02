import pymupdf, sys, json, collections
src = sys.argv[1]
doc = pymupdf.open(src)
print("pages:", len(doc))
sizes = collections.Counter()
fonts = collections.Counter()
summary = []
for i, p in enumerate(doc):
    r = p.rect
    sizes[(round(r.width,1), round(r.height,1))] += 1
    txt = p.get_text("dict")
    nchar = 0; spans = 0
    for b in txt["blocks"]:
        if b["type"] != 0: continue
        for l in b["lines"]:
            for s in l["spans"]:
                spans += 1; nchar += len(s["text"])
                fonts[(s["font"], round(s["size"],1))] += len(s["text"])
    imgs = p.get_images(full=True)
    draws = p.get_drawings()
    summary.append((i+1, nchar, spans, len(imgs), len(draws)))
print("sizes:", dict(sizes))
print("page: chars spans imgs drawings")
for s in summary: print(s)
print("top fonts:")
for f, c in fonts.most_common(25): print("  ", f, c)
