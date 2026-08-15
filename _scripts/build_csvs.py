# -*- coding: utf-8 -*-
"""① 文献传递申请清单 → CSV；② 编号↔PDF文件名↔DOI 对照表（CSV+MD）。"""
import re, io, os, csv

WORK = r'F:\deepseek harness'
SRC = os.path.join(WORK, '中美欧日中近岸养殖政策文献总目.md')
RIS = os.path.join(WORK, 'zotero_import_271.ris')
UP = os.path.join(WORK, 'unpaywall_report.csv')
IDS = ['CN-%02d' % i for i in range(1, 33)]
IDS += ['CN-54','CN-56','CN-58','CN-59','CN-61','CN-62','CN-63','CN-64','CN-65','CN-68','CN-69','CN-71','CN-73','CN-74','CN-75','CN-76','CN-77','JP-31','JP-37','KR-02']

text = io.open(SRC, encoding='utf-8').read()

# ---------- ① 传递清单 CSV ----------
have = set()
pd = os.path.join(WORK, 'pdfs_cn')
if os.path.isdir(pd):
    for f in os.listdir(pd):
        if f.endswith('.pdf'):
            have.add(f[:-4])

rows = []
for cid in IDS:
    m = re.search(r'(?m)^\| ' + re.escape(cid) + r' \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|', text)
    if not m:
        continue
    theme, lit, jour, doicol = (m.group(i).strip() for i in range(1, 5))
    lit_clean = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', lit)
    ym = re.search(r'(\d{4})', lit_clean)
    author, title = '', lit_clean
    if ym:
        author = lit_clean[:ym.start()].strip()
        title = re.sub(r'^[^.\s．]*\s*[.．]?\s*', '', lit_clean[ym.end():]).strip()
        author = re.sub(r'[（(]作者待核实[^）)]*[）)]|（作者待核实）|（线索[^）)]*）', '', author).strip()
    db = '期刊官网'
    if re.search(r'cnki|知网', doicol, re.I):
        db = 'CNKI(知网)'
    elif re.search(r'wanfang|万方', doicol, re.I):
        db = '万方'
    elif re.search(r'cqvip|维普', doicol, re.I):
        db = '维普'
    rows.append({'编号': cid, '题名': title, '作者': author or '（作者待核实）', '期刊年卷期页': jour,
                 '数据库': db, '全文状态': '已下载' if cid in have else '需文献传递'})

out1 = os.path.join(WORK, '文献传递申请清单.csv')
with io.open(out1, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['编号', '题名', '作者', '期刊年卷期页', '数据库', '全文状态'])
    w.writeheader()
    w.writerows(rows)

# ---------- ② 编号↔PDF文件名↔DOI 对照表 ----------
# RIS -> {DOI: 编号}
doi2id = {}
cur = {}
for ln in io.open(RIS, encoding='utf-8').read().split('\n'):
    if ln.startswith('DO  - '):
        cur['doi'] = ln[6:].strip()
    elif ln.startswith('N1  - '):
        mm = re.search(r'编号：([A-Z]+-\d+)', ln)
        if mm:
            cur['id'] = mm.group(1)
    elif ln.startswith('ER'):
        if 'doi' in cur and 'id' in cur:
            doi2id[cur['doi']] = cur['id']
        cur = {}

# unpaywall_report -> {DOI: status}
up = {}
if os.path.exists(UP):
    for r in csv.DictReader(io.open(UP, encoding='utf-8-sig')):
        up[r['DOI']] = r

map_rows = []
pdf_dir = os.path.join(WORK, 'pdfs')
# 从 unpaywall_report 的 File 列精确映射（避免 DOI 含下划线的还原歧义）
if os.path.isdir(pdf_dir):
    for doi, r in up.items():
        if r.get('File'):
            fname = os.path.basename(r['File'])
            map_rows.append({'编号': doi2id.get(doi, ''), '标题': '', 'DOI': doi, 'PDF文件名': fname, '状态': r.get('Status', '')})
for f in sorted(os.listdir(pd)):
    if f.endswith('.pdf'):
        cid = f[:-4]
        map_rows.append({'编号': cid, '标题': '', 'DOI': '（中文期刊，无DOI）', 'PDF文件名': f, '状态': '已下载'})

out2 = os.path.join(WORK, 'PDF文件对照表.csv')
with io.open(out2, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['编号', '标题', 'DOI', 'PDF文件名', '状态'])
    w.writeheader()
    w.writerows(map_rows)

# MD 版对照表
L = ['# PDF 文件对照表（编号 ↔ 文件名 ↔ DOI）', '', '| 编号 | DOI | PDF 文件名 | 状态 |', '|---|---|---|---|']
for r in map_rows:
    L.append('| %s | %s | `%s` | %s |' % (r['编号'] or '—', r['DOI'], r['PDF文件名'], r['状态']))
with io.open(os.path.join(WORK, 'PDF文件对照表.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

print('delivery-csv=%d rows' % len(rows))
print('mapping-csv=%d rows (EN OA %d + CN %d)' % (len(map_rows), len([r for r in map_rows if r['DOI'] != '（中文期刊，无DOI）']), len([r for r in map_rows if r['DOI'] == '（中文期刊，无DOI）'])))
