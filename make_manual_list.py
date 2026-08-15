# -*- coding: utf-8 -*-
"""生成《需人工下载清单.md》：从两份下载报告 + 源清单提取未下载条目的 DOI/链接。"""
import re, os

BASE = r"F:\deepseek harness"

def parse_entries(md):
    lines = open(md, encoding="utf-8").read().splitlines()
    ents = {}
    for i, l in enumerate(lines):
        m = re.match(r"^(\d+)\.\s+\*\*(.+?)\*\*", l)
        if not m:
            continue
        num = int(m.group(1))
        block = [l]
        j = i + 1
        while j < len(lines) and not re.match(r"^\d+\.\s+\*\*", lines[j]):
            block.append(lines[j])
            j += 1
        bt = "\n".join(block)
        doi = None
        dm = re.search(r"DOI[:：]?\s*\[?\s*(10\.\d{4,9}/[^\s（\[）\]）]+)", bt)
        if dm:
            doi = re.split(r"[\s（(【\[·,，;；）)\]}】]+", dm.group(1).strip())[0].strip(".*")
        urls = list(dict.fromkeys(u.rstrip(".,;") for u in re.findall(r"https?://[^\s）)\]>}]+", bt)))
        title = re.sub(r"^(作者待核实|（作者待核实）|\(作者待核实\)|作者待核实（[^）]*）)\s*", "", m.group(2))
        ents[num] = {"title": title.strip(), "doi": doi, "urls": urls}
    return ents

def failed_nums(report_md):
    nums = []
    in_fail = False
    for l in open(report_md, encoding="utf-8").read().splitlines():
        if l.startswith("## "):
            in_fail = ("需人工" in l) or ("未获取" in l) or ("未下载" in l)
            continue
        if in_fail:
            m = re.match(r"-\s*#?0*(\d+)\s", l)
            if m:
                nums.append(int(m.group(1)))
    return sorted(set(nums))

jobs = [
    ("中文", "中国近岸养殖政策_文献收集_中文.md", "下载结果_中国近岸养殖政策_中文.md"),
    ("英文", "中国近岸养殖政策_文献收集_英文.md", "下载结果_中国近岸养殖政策_英文.md"),
]
out = []
out.append("# 需人工下载清单（WebVPN 登录后浏览器下载）")
out.append("")
out.append("> 用途：以下文献无法脚本下载（知网/付费墙）。请在浏览器登录 **webvpn.hainanu.edu.cn**（或校园网/CARSI）后，")
out.append("> 逐个打开 DOI 或链接下载 PDF；知网文献建议直接在知网检索标题下载。")
out.append("")
out.append("## 操作提示")
out.append("- 知网（CNKI）：登录后按标题检索 → 下载；批量下载有风控，建议逐篇。")
out.append("- Elsevier（ScienceDirect）、Wiley、Springer：经 WebVPN 打开 DOI → 页面出现机构访问标识后即可下载 PDF。")
out.append("")
for lang, src, rep in jobs:
    ents = parse_entries(os.path.join(BASE, src))
    nums = failed_nums(os.path.join(BASE, rep))
    out.append("## %s（%d 篇）" % (lang, len(nums)))
    out.append("")
    out.append("| 编号 | 标题 | DOI | 直达链接 |")
    out.append("|---|---|---|---|")
    for n in nums:
        e = ents.get(n, {})
        doi = e.get("doi") or "—"
        doi_link = ("https://doi.org/%s" % doi) if doi and doi != "—" else "—"
        urls = e.get("urls") or []
        pick = urls[0] if urls else "—"
        out.append("| %s | %s | %s | %s |" % (n, (e.get("title") or "")[:50], doi, pick))
    out.append("")

with open(os.path.join(BASE, "需人工下载清单.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("已生成: 需人工下载清单.md")
for lang, src, rep in jobs:
    print(lang, "待人工:", len(failed_nums(os.path.join(BASE, rep))), "篇")
