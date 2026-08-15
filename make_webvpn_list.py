# -*- coding: utf-8 -*-
"""生成《需人工下载清单_WebVPN版》(HTML + MD)：未下载条目全部转为 WebVPN 前缀直达链接。"""
import re, os, html as htmlmod

BASE = r"F:\deepseek harness"
VP = "https://webvpn.hainanu.edu.cn/https/"

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
    nums, in_fail = [], False
    for l in open(report_md, encoding="utf-8").read().splitlines():
        if l.startswith("## "):
            in_fail = ("需人工" in l) or ("未获取" in l) or ("未下载" in l)
            continue
        if in_fail:
            m = re.match(r"-\s*#?0*(\d+)\s", l)
            if m:
                nums.append(int(m.group(1)))
    return sorted(set(nums))

def vp_link(url):
    """把 https://host/path 转为 https://webvpn.hainanu.edu.cn/https/host/path"""
    if url.startswith("https://"):
        return VP + url[len("https://"):]
    if url.startswith("http://"):
        return VP + url[len("http://"):]
    return VP + url

jobs = [
    ("中文", "中国近岸养殖政策_文献收集_中文.md", "下载结果_中国近岸养殖政策_中文.md"),
    ("英文", "中国近岸养殖政策_文献收集_英文.md", "下载结果_中国近岸养殖政策_英文.md"),
]

md_lines = ["# 需人工下载清单 · WebVPN 直达版", "",
            "> 前提：浏览器已登录 **webvpn.hainanu.edu.cn**（登录态保持）。逐个点开链接，在目标页下载 PDF。",
            "> 链接已带 `https://webvpn.hainanu.edu.cn/https/` 前缀，浏览器会以海南大学授权身份访问。",
            "> ⚠️ 知网建议**逐篇下载**，切勿批量（有风控锁号风险）。", ""]
html_parts = []
html_parts.append("""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>需人工下载清单 · WebVPN 直达版</title>
<style>body{font-family:'Microsoft YaHei',sans-serif;margin:24px;background:#f7f8fa;color:#222}
h1{font-size:22px}h2{margin-top:28px;font-size:18px;border-left:4px solid #1a73e8;padding-left:8px}
table{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.12)}
th,td{border:1px solid #e0e0e0;padding:7px 10px;font-size:14px;text-align:left;vertical-align:top}
th{background:#eef3fb}a{color:#1a73e8;text-decoration:none;word-break:break-all}a:hover{text-decoration:underline}
.warn{background:#fff8e1;border:1px solid #ffd54f;padding:10px 14px;border-radius:6px;font-size:14px;margin-bottom:12px}
.note{color:#666;font-size:12px}</style></head><body>
<h1>📄 需人工下载清单 · WebVPN 直达版</h1>
<div class="warn">⚠️ 使用前请确认浏览器已登录 <b>webvpn.hainanu.edu.cn</b>（不要退出登录）。<br>
逐篇点开链接 → 在目标页面找 <b>PDF / 全文下载</b> 按钮；知网建议逐篇下载，避免批量触发风控。
若某链接打开显示"无法访问"，可改从 <b>WebVPN 门户的资源列表</b> 进入该数据库后按标题检索下载。</div>
""")

total = 0
for lang, src, rep in jobs:
    ents = parse_entries(os.path.join(BASE, src))
    nums = failed_nums(os.path.join(BASE, rep))
    total += len(nums)
    md_lines.append("## %s（%d 篇）" % (lang, len(nums)))
    md_lines.append("")
    md_lines.append("| 编号 | 标题 | WebVPN 直达 | 备用链接 |")
    md_lines.append("|---|---|---|---|")
    html_parts.append("<h2>%s（%d 篇）</h2>" % (lang, len(nums)))
    html_parts.append("<table><tr><th>编号</th><th>标题</th><th>WebVPN 直达</th><th>备用链接</th></tr>")
    for n in nums:
        e = ents.get(n, {})
        title = (e.get("title") or "")[:70]
        links = []
        doi = e.get("doi")
        if doi and doi != "—":
            links.append(("DOI（推荐）", vp_link("https://doi.org/" + doi)))
        for u in (e.get("urls") or [])[:2]:
            links.append(("原链接", vp_link(u)))
        # HTML 行
        tds = ['<td>%s</td>' % n, '<td>%s</td>' % htmlmod.escape(title)]
        link_html = "<br>".join('<a href="%s" target="_blank">%s</a>' % (htmlmod.escape(u), t) for t, u in links) or "—"
        tds.append('<td>%s</td>' % link_html)
        backup = "<br>".join('<a href="%s" target="_blank">原址</a>' % htmlmod.escape(u) for _, u in links[1:2]) or "—"
        tds.append('<td>%s</td>' % backup)
        html_parts.append("<tr>" + "".join(tds) + "</tr>")
        # MD 行
        md_links = " ｜ ".join('[%s](%s)' % (t, u) for t, u in links) or "—"
        md_lines.append("| %s | %s | %s | %s |" % (n, title, md_links, backup.replace('原址','原址')))
    html_parts.append("</table>")

html_parts.append('<p class="note">共 %d 篇待人工下载 · 生成时间：2026-08 · 提示：本清单仅供个人学术用途，请遵守海南大学数据库使用规定。</p>' % total)
html_parts.append("</body></html>")

open(os.path.join(BASE, "需人工下载清单_WebVPN版.html"), "w", encoding="utf-8").write("\n".join(html_parts))
open(os.path.join(BASE, "需人工下载清单_WebVPN版.md"), "w", encoding="utf-8").write("\n".join(md_lines))
print("已生成:")
print("  需人工下载清单_WebVPN版.html（浏览器打开，逐个点链接）")
print("  需人工下载清单_WebVPN版.md（Zettlr/记事本）")
print("待人工总数:", total, "（中文 %s + 英文 %s）" % (len(failed_nums(os.path.join(BASE, jobs[0][2]))), len(failed_nums(os.path.join(BASE, jobs[1][2])))))
