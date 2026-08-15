# -*- coding: utf-8 -*-
"""
最终下载脚本：用 curl + 多候选源（Europe PMC / 仓储 / 出版社直链）下载 OA 论文。
解析机构仓储落地页提取真实 PDF 直链。
"""
import re, os, json, subprocess, time, sys
import requests, warnings
warnings.filterwarnings("ignore")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

BASE = r"f:\deepseek harness"
OUT = os.path.join(BASE, "美国养殖政策_文献PDF")
os.makedirs(OUT, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
EMAIL = "84192105+wengxiaonan@users.noreply.github.com"

S = requests.Session(); S.verify = False; S.headers["User-Agent"] = UA

def sanitize(n): return re.sub(r'[\\/:*?"<>|]', '_', n).strip()

def curl_fetch(url, out, referer=None):
    cmd = ["curl", "-sL", "--max-time", "90", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9"]
    if referer: cmd += ["-e", referer]
    cmd += ["-o", out, url]
    subprocess.run(cmd, capture_output=True)
    if os.path.exists(out) and os.path.getsize(out) > 0:
        with open(out, "rb") as f: data = f.read()
        return data
    return b""

def is_pdf(data):
    return b"%PDF" in data[:1024]

def try_download(url, fpath, referer=None):
    data = curl_fetch(url, fpath, referer)
    if is_pdf(data):
        return True, "pdf"
    # 若是 HTML 落地页，尝试从中提取 PDF 链接
    html = data[:200000].decode("utf-8", "ignore")
    links = set(re.findall(r'https?://[^"\'\s<>]+?(?:\.pdf|viewcontent\.cgi|/pdf/|download|ndownloader|bitstream)[^"\'\s<>]*', html))
    # 通用 .pdf 链接
    links |= set(re.findall(r'https?://[^"\'\s<>]+?\.pdf[^"\'\s<>]*', html))
    for lnk in list(links)[:5]:
        if lnk == url: continue
        d2 = curl_fetch(lnk, fpath, referer=url)
        if is_pdf(d2):
            return True, "resolved:" + lnk[:60]
    return False, "no_pdf"

# ---- 加载已解析的 DOI/条目 ----
text = open(os.path.join(BASE, "美国养殖政策_文献收集.md"), encoding="utf-8").read()
lines = text.splitlines()
entries = []
i = 0
while i < len(lines):
    m = re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*', lines[i])
    if m:
        num = int(m.group(1)); title = m.group(2)
        block = [lines[i]]; j = i + 1
        while j < len(lines) and not re.match(r'^\d+\.\s+\*\*', lines[j]):
            block.append(lines[j]); j += 1
        bt = "\n".join(block)
        dm = re.search(r'DOI:\s*(10\.\d{4,9}/\S+)', bt)
        doi = None
        if dm:
            doi = re.split(r'[\s（(【\[·,，;；）)\]}】]+', dm.group(1).strip())[0]
        ssrn = None
        sm = re.search(r'https://papers\.ssrn\.com/sol3/papers\.cfm\?abstract_id=\d+', bt)
        if sm: ssrn = sm.group(0)
        entries.append({"num": num, "title": title.strip(), "doi": doi, "ssrn": ssrn})
        i = j
    else: i += 1

# 补充 unpaywall locs（含上次 dump）
try:
    dump = json.load(open(os.path.join(BASE, "unpaywall_dump.json"), encoding="utf-8"))
except Exception:
    dump = {}

def get_upw_locs(doi):
    # 从 dump 读；若缺失则现场查
    for num, rec in dump.items():
        if rec.get("doi") == doi and rec.get("locs"):
            return rec["locs"]
    try:
        j = S.get("https://api.unpaywall.org/v2/%s?email=%s" % (doi, EMAIL), timeout=30).json()
        return [{"host": l.get("host_type"), "pdf": l.get("url_for_pdf"), "url": l.get("url")}
                for l in j.get("oa_locations", [])]
    except Exception:
        return []

def europepmc_pdf(doi):
    try:
        j = S.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%22%s%22&format=json" % doi, timeout=30).json()
        r = (j.get("resultList", {}).get("result") or [None])[0]
        if r and r.get("pmcid") and r.get("isOpenAccess") == "Y":
            return "https://europepmc.org/articles/%s?pdf=render" % r["pmcid"]
    except Exception:
        pass
    return None

results = []
for e in entries:
    num, title, doi = e["num"], e["title"], e["doi"]
    fname = "%02d_%s.pdf" % (num, sanitize(title[:70]))
    fpath = os.path.join(OUT, fname)
    rec = {"num": num, "title": title, "doi": doi, "status": "fail", "file": None, "via": None, "notes": []}

    cands = []
    def add(u, tag):
        if u and u not in [c[0] for c in cands]:
            cands.append((u, tag))

    if e.get("ssrn"): add(e["ssrn"], "ssrn")
    if doi:
        for loc in get_upw_locs(doi):
            add(loc.get("pdf"), "upw_pdf")
            add(loc.get("url"), "upw_url")
        ep = europepmc_pdf(doi)
        if ep: add(ep, "europepmc")
        # 出版社直链兜底
        if doi.startswith("10.1007/"):
            add("https://link.springer.com/content/pdf/%s.pdf" % doi.replace("/", "%2F"), "springer")
        if doi.startswith("10.1080/"):
            add("https://www.tandfonline.com/doi/pdf/%s?needAccess=true" % doi, "tandf")
        if doi.startswith("10.1038/"):
            sid = doi.split("/")[-1]
            add("https://www.nature.com/articles/%s.pdf" % sid, "nature")
        if doi.startswith("10.1371/"):
            add("https://journals.plos.org/plosone/article/file?id=%s&type=printable" % doi, "plos")

    done = False
    for url, tag in cands:
        ok, via = try_download(url, fpath)
        if ok:
            rec["status"] = "downloaded"; rec["file"] = fname; rec["via"] = tag + ":" + via
            done = True
            break
        else:
            rec["notes"].append("%s(%s)" % (tag, via[:30]))
    if not done and not cands:
        rec["status"] = "no_oa"
    results.append(rec)
    print("#%02d %-10s %s %s" % (num, rec["status"], rec["via"] or "", "; ".join(rec["notes"][:1])))
    time.sleep(0.3)

json.dump(results, open(os.path.join(BASE, "download_final_results.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

ok = [r for r in results if r["status"] == "downloaded"]
print("\n===== 成功 %d / %d =====" % (len(ok), len(results)))
for r in ok:
    print("  #%02d %s" % (r["num"], r["file"]))
print("\n--- 未下载 ---")
for r in results:
    if r["status"] != "downloaded":
        print("#%02d %s %s" % (r["num"], r["status"], (r["doi"] or "") ))
