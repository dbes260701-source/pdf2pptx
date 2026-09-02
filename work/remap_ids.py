import json, re
old = {}; page = None
for line in open("old_dump.txt", encoding="utf-8"):
    m = re.match(r"== page (\d+)", line)
    if m: page = int(m.group(1)); continue
    m = re.match(r"(t\d+) \[(\d+), (\d+), (\d+), (\d+)\]", line)
    if m and page: old.setdefault(page, {})[m.group(1)] = tuple(int(v) for v in m.groups()[1:])
for p in range(1, 7):
    lay = json.load(open(f"layout/p{p}.json", encoding="utf-8"))
    new = {tuple(int(v) for v in e["bbox"]): e["id"] for e in lay["elements"] if e["type"] == "text"}
    mp = {oid: new.get(bb) for oid, bb in old.get(p, {}).items()}
    if p == 1: mp = {f"t{k}": (f"t{k}" if k < 9 else (None if k == 9 else f"t{k-1}")) for k in range(40)}
    ov = json.load(open(f"overrides/p{p}.json", encoding="utf-8"))
    miss = [k for k in ov["delete"] if k.startswith("t") and mp.get(k) is None] + [k for k in ov["set"] if k.startswith("t") and mp.get(k) is None]
    ov["delete"] = [mp[k] if k.startswith("t") else k for k in ov["delete"] if not (k.startswith("t") and mp.get(k) is None)]
    ov["set"] = {(mp[k] if k.startswith("t") else k): v for k, v in ov["set"].items() if not (k.startswith("t") and mp.get(k) is None)}
    json.dump(ov, open(f"overrides/p{p}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(p, "remapped; unmatched(old ids removed from photos etc.):", miss)
