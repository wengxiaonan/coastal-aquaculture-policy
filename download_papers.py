# -*- coding: utf-8 -*-
"""
下载《美国近岸/沿海水产养殖政策 文献清单》36 篇论文 PDF（v2）。
- 精确提取 DOI
- 用 Unpaywall 查 OA，遍历所有 OA 镜像源（不只 best）
- requests + verify=False + 完整请求头，规避 SSL/403 部分问题
- 结果写入 UTF-8 文件，避免控制台 GBK 崩溃
"""
import re, os, json, time, sys, io
import ssl, warnings
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
warnings.filterwarnings("ignore")

EMAIL = "84192105+wengxiaonan@users.noreply.github.com"
BASE = r"f:\deepseek harness"
SRC = os.path.join(BASE, "美国养殖政策_文献收集.md")
OUT = os.path.join(BASE, "美国养殖政策_文献PDF")
os.makedirs(OUT, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

S = requests.Session()
S.verify = False
S.headers.update(HEADERS)

def clean_doi(s):
    s = s.strip()
    # 在首个全角/半角括号或分隔符处截断
    s = re.split(r'[\s（(【\[·,，;；）)\]}】]+', s)[0]
    return s

def sanitize(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()

def is_pdf(data):
    if not data:
        return False
    if data[:5] == b"%PDF-":
        return True
    # 不是 HTML 且足够大
    if b"<html" in data[:600].lower():
        return False
    return len(data) > 3000

def download(url, fpath):
    try:
        r = S.get(url, timeout=90, allow_redirects=True)
        if r.status_code == 200 and is_pdf(r.content):
            with open(fpath, "wb") as f:
                f.write(r.content)
            return True, r.headers.get("Content-Type", "")
    except Exception as ex:
        return False, str(ex)
    return False, "status=%s" % r.status_code if 'r' in dir() else ""

# ---------- 解析 markdown ----------
text = open(SRC, encoding="utf-8").read()
lines = text.splitlines()

entries = []
i = 0
while i < len(lines):
    m = re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*', lines[i])
    if m:
        num = int(m.group(1))
        title = m.group(2)
        block = [lines[i]]
        j = i + 1
        while j < len(lines) and not re.match(r'^\d+\.\s+\*\*', lines[j]):
            block.append(lines[j])
            j += 1
        bt = "\n".join(block)
        doi = None
        dm = re.search(r'DOI:\s*(10\.\d{4,9}/\S+)', bt)
        if dm:
            doi = clean_doi(dm.group(1))
        ssrn = None
        sm = re.search(r'https://papers\.ssrn\.com/sol3/papers\.cfm\?abstract_id=\d+', bt)
        if sm:
            ssrn = sm.group(0)
        entries.append({"num": num, "title": title.strip(), "doi": doi, "ssrn": ssrn})
        i = j
    else:
        i += 1

print("解析条目数:", len(entries))

results = []
for e in entries:
    num, title, doi = e["num"], e["title"], e["doi"]
    rec = {"num": num, "title": title, "doi": doi,
           "status": "skip", "downloaded_file": None, "notes": []}
    fname = "%02d_%s.pdf" % (num, sanitize(title[:70]))
    fpath = os.path.join(OUT, fname)

    # 收集候选 URL（按优先级）
    cands = []
    seen = set()

    def add(url, tag):
        if url and url not in seen:
            seen.add(url)
            cands.append((tag, url))

    if e.get("ssrn"):
        add(e["ssrn"], "ssrn_preprint")

    if doi:
        try:
            upw = S.get("https://api.unpaywall.org/v2/%s?email=%s" % (doi, EMAIL),
                        timeout=40).json()
            rec["oa"] = bool(upw.get("is_oa"))
            rec["oa_title"] = (upw.get("title") or "")[:80]
            locs = []
            bl = upw.get("best_oa_location")
            if bl:
                locs.append(bl)
            locs += upw.get("oa_locations") or []
            for loc in locs:
                add(loc.get("url_for_pdf"), "oa_pdf")
                add(loc.get("pdf_url"), "oa_pdf")
                add(loc.get("url"), "oa_page")
            if rec["oa"] and not cands:
                rec["notes"].append("oa但无可用pdf链接")
        except Exception as ex:
            rec["notes"].append("unpaywall_err=%s" % ex)

    # 下载
    done = None
    for tag, url in cands:
        ok, msg = download(url, fpath)
        if ok:
            done = (fname, tag)
            break
        else:
            rec["notes"].append("%s:%s" % (tag, msg[:60]))

    if done:
        rec["status"] = "downloaded"
        rec["downloaded_file"] = done[0]
        rec["source"] = done[1]
    else:
        rec["status"] = "paywalled_or_failed"
    results.append(rec)
    print("#%02d %-18s %s" % (num, rec["status"], ("-> " + done[0]) if done else "; ".join(rec["notes"][:2])))
    time.sleep(0.7)

# ---------- 报告 ----------
json.dump(results, open(os.path.join(BASE, "download_results.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

ok = [r for r in results if r["status"] == "downloaded"]
fail = [r for r in results if r["status"] != "downloaded"]

rep = []
rep.append("# 下载结果汇总\n")
rep.append("成功下载 **%d** 篇 / 共 **%d** 篇。\n" % (len(ok), len(results)))
rep.append("\n## 已下载\n")
for r in ok:
    rep.append("- #%02d %s  `%s`" % (r["num"], r["title"][:60], r["downloaded_file"]))
rep.append("\n## 未下载（付费墙或需机构权限）\n")
for r in fail:
    rep.append("- #%02d %s" % (r["num"], r["title"][:80]))
    if r.get("doi"):
        rep.append("  - DOI: %s" % r["doi"])
rep.append("\n## 目录\n`%s`\n" % OUT)
report = "\n".join(rep)
open(os.path.join(BASE, "下载结果_美国养殖政策.md"), "w", encoding="utf-8").write(report)

print("\n===== 完成：成功 %d / %d =====" % (len(ok), len(results)))
print("PDF 目录:", OUT)
print("报告:", os.path.join(BASE, "下载结果_美国养殖政策.md"))
