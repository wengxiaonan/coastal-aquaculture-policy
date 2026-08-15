# -*- coding: utf-8 -*-
"""
下载《中国近岸养殖政策 英文文献清单》21 篇论文 PDF（v1，英文版）。
- 解析 Markdown 清单：提取 DOI 与所有链接（ScienceDirect / Frontiers / MDPI / Springer 等）
- 下载策略（按优先级）：
    1) Unpaywall 查 OA，遍历全部 OA 镜像源（url_for_pdf / pdf_url / url）
    2) DOI 直达 https://doi.org/<doi>
    3) 条目自带链接（出版方页面）
    4) 对 HTML 落地页自动搜索 .pdf 链接再尝试（Frontiers/MDPI/PLoS 等 OA 站点有效）
- requests + verify=False + 完整请求头，规避 SSL/403 部分问题
- 结果写入 UTF-8 文件，避免控制台 GBK 崩溃
- 付费墙文献（Marine Policy / Aquaculture / O&CM 等）无法直接下载，报告会标注"未获取"

用法：py -3 download_en_papers.py            # 全部
      py -3 download_en_papers.py 1,2,3     # 仅下载指定序号（测试用）
"""
import re, os, json, time, sys
import warnings
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
warnings.filterwarnings("ignore")

EMAIL = "84192105+wengxiaonan@users.noreply.github.com"
BASE = r"F:\deepseek harness"
SRC = os.path.join(BASE, "中国近岸养殖政策_文献收集_英文.md")
OUT = os.path.join(BASE, "papers", "英文")
REPORT = os.path.join(BASE, "下载结果_中国近岸养殖政策_英文.md")
os.makedirs(OUT, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
S = requests.Session()
S.verify = False
S.headers.update(HEADERS)

def clean_doi(s):
    return re.split(r'[\s（(【\[·,，;；）)\]}】]+', s.strip())[0].strip('.*')

def sanitize(name):
    return re.sub(r'[\\/:*?"<>|\r\n]+', '_', name).strip()

def is_pdf(data):
    if not data:
        return False
    if data[:5] == b"%PDF-":
        return True
    if b"<html" in data[:600].lower():
        return False
    return len(data) > 3000

def find_pdf_links(html):
    links = re.findall(r'href=["\']([^"\']*?\.pdf[^"\']*)["\']', html, re.I)
    out = []
    for l in links:
        if l.startswith("//"):
            l = "https:" + l
        elif l.startswith("/"):
            l = "https://doi.org" + l
        out.append(l)
    return out

def download(url, fpath, try_html_pdf=True):
    try:
        r = S.get(url, timeout=90, allow_redirects=True)
        if r.status_code == 200 and is_pdf(r.content):
            with open(fpath, "wb") as f:
                f.write(r.content)
            return True, "pdf"
        if try_html_pdf and r.status_code == 200 and "html" in (r.headers.get("Content-Type", "") or "").lower():
            html = r.text
            for pdf_link in find_pdf_links(html)[:5]:
                if not pdf_link.startswith("http"):
                    continue
                try:
                    r2 = S.get(pdf_link, timeout=90, allow_redirects=True)
                    if r2.status_code == 200 and is_pdf(r2.content):
                        with open(fpath, "wb") as f:
                            f.write(r2.content)
                        return True, "html_pdf"
                except Exception:
                    continue
        return False, "status=%s ct=%s" % (getattr(r, "status_code", "?"), r.headers.get("Content-Type", ""))
    except Exception as ex:
        return False, str(ex)[:80]

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
        dm = re.search(r'DOI[:：]?\s*\[?\s*(10\.\d{4,9}/[^\s（\[）\]）]+)', bt)
        if dm:
            doi = clean_doi(dm.group(1))
        urls = list(dict.fromkeys(u.rstrip(".,;") for u in re.findall(r'https?://[^\s）)\]>}]+', bt)))
        entries.append({"num": num, "title": title.strip(), "doi": doi, "urls": urls})
        i = j
    else:
        i += 1

print("解析条目数:", len(entries))

only = set()
if len(sys.argv) > 1:
    only = {int(x) for x in sys.argv[1].split(",") if x.strip()}
    entries = [e for e in entries if e["num"] in only]

results = []
for e in entries:
    num, title, doi = e["num"], e["title"], e["doi"]
    rec = {"num": num, "title": title, "doi": doi, "status": "skip", "downloaded_file": None, "notes": []}
    fname = "%02d_%s.pdf" % (num, sanitize(re.sub(r'^(作者待核实|（作者待核实）|\(作者待核实\)|作者待核实（[^）]*）)\s*', '', title)[:70]))
    fpath = os.path.join(OUT, fname)

    cands = []
    seen = set()

    def add(url, tag):
        if url and url not in seen:
            seen.add(url)
            cands.append((tag, url))

    if doi:
        try:
            upw = S.get("https://api.unpaywall.org/v2/%s?email=%s" % (doi, EMAIL), timeout=40).json()
            rec["oa"] = bool(upw.get("is_oa"))
            locs = []
            bl = upw.get("best_oa_location")
            if bl:
                locs.append(bl)
            locs += upw.get("oa_locations") or []
            for loc in locs:
                add(loc.get("url_for_pdf"), "oa_pdf")
                add(loc.get("pdf_url"), "oa_pdf")
                add(loc.get("url"), "oa_page")
        except Exception as ex:
            rec["notes"].append("unpaywall_err=%s" % ex)
        add("https://doi.org/%s" % doi, "doi_direct")
    for u in e.get("urls", []):
        add(u, "entry_url")

    done = None
    for tag, url in cands:
        ok, msg = download(url, fpath)
        if ok:
            done = (fname, tag)
            break
        else:
            rec["notes"].append("%s:%s" % (tag, msg[:50]))

    if done:
        rec["status"] = "downloaded"
        rec["downloaded_file"] = done[0]
        rec["source"] = done[1]
    else:
        rec["status"] = "paywalled_or_failed"
    results.append(rec)
    print("#%02d %-20s %s" % (num, rec["status"], ("-> " + done[0]) if done else "; ".join(rec["notes"][:2])))
    time.sleep(0.7)

# ---------- 报告 ----------
ok = [r for r in results if r["status"] == "downloaded"]
fail = [r for r in results if r["status"] != "downloaded"]

rep = []
rep.append("# 下载结果汇总（中国近岸养殖政策·英文文献）\n")
rep.append("成功下载 **%d** 篇 ｜ 未获取 **%d** 篇 ｜ 共 **%d** 篇。\n" % (len(ok), len(fail), len(results)))
rep.append("\n## 已下载\n")
for r in ok:
    rep.append("- #%02d %s  `%s`（%s）" % (r["num"], r["title"][:60], r["downloaded_file"], r.get("source", "")))
rep.append("\n## 未下载（付费墙或需机构权限）\n")
for r in fail:
    rep.append("- #%02d %s" % (r["num"], r["title"][:80]))
    if r.get("doi"):
        rep.append("  - DOI: %s" % r["doi"])
    if r.get("notes"):
        rep.append("  - 尝试: %s" % "; ".join(r["notes"][:2]))
rep.append("\n## PDF 目录\n`%s`\n" % OUT)
open(REPORT, "w", encoding="utf-8").write("\n".join(rep))

print("\n===== 完成：成功 %d / 未获取 %d / 共 %d =====" % (len(ok), len(fail), len(results)))
print("PDF 目录:", OUT)
print("报告:", REPORT)
