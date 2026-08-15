# -*- coding: utf-8 -*-
"""从《中美欧日中近岸养殖政策文献总目.md》解析 271 条记录并生成 Zotero 可导入的 RIS 文件。"""
import re, io

SRC = r'F:\deepseek harness\中美欧日中近岸养殖政策文献总目.md'
OUT = r'F:\deepseek harness\zotero_import_271.ris'
PREFIXES = ('CN','EU','US','JP','CA','MX','KR','NO','AU','NZ','CL','IN','VN','ID','BR','ZA')

with io.open(SRC, encoding='utf-8') as f:
    text = f.read()

rows = []
for ln in text.split('\n'):
    if not ln.startswith('|'):
        continue
    cells = [c.strip() for c in ln.strip('|').split('|')]
    if len(cells) < 6:
        continue
    cid = cells[0]
    if not re.match(r'^(?:%s)-\d+$' % '|'.join(PREFIXES), cid):
        continue
    rows.append((cid, cells[1], cells[2], cells[3], cells[4], cells[5]))

def split_authors(a_part):
    a2 = re.sub(r'[（(][^）)]*[）)]', '', a_part).strip()
    a2 = a2.replace('et al.', '').replace('等', '')
    parts = re.split(r'[,，、&]| and ', a2)
    out = []
    for p in parts:
        p = p.strip(' .')
        if p and p not in ('et al', '等'):
            out.append(p)
    return out

records = []
for cid, theme, lit, jour, doiurl, verif in rows:
    lit_clean = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', lit)

    if '专著章节' in lit or '章节' in lit:
        typ = 'CHAP'
    elif '会议' in lit or 'Conf. Ser.' in jour or 'OOS' in jour or '研讨会' in lit:
        typ = 'CONF'
    elif '专著' in lit:
        typ = 'BOOK'
    else:
        typ = 'JOUR'

    authors, year, title = [], '', lit_clean
    ym = re.search(r'(\d{4})', lit_clean)
    if ym:
        year = ym.group(1)
        a_part = lit_clean[:ym.start()].strip()
        tail = lit_clean[ym.end():]
        title = re.sub(r'^[^.\s．]*\s*[.．]?\s*', '', tail).strip()
        if not title:
            title = lit_clean
        if '待核实' not in a_part:
            authors = split_authors(a_part)
        # 移除标题尾部类型/语言/状态括号标注（含组合标注如"日文，研讨会报告"）
        for _ in range(3):
            title = re.sub(r'[（(][^（)）]*(专著章节|专著|会议论文|研讨会报告|日文|中文|中文比较文献|韩文|英文|在线优先|在线先行|OA)[^（)）]*[）)]\s*$', '', title).strip()

    journal, volume, issue, pages = '', '', '', ''
    j = re.sub(r'（※.*?）|\(※.*?\)|※.*$', '', jour).strip()
    m2 = re.match(r'^(.*?)[\s]?(\d{1,4})[(（](\d+)[)）][:：]?\s*([\d–\-~a-zA-Z]+)?\s*$', j)
    if m2:
        journal, volume, issue, pages = m2.group(1).strip(), m2.group(2), m2.group(3), (m2.group(4) or '')
    else:
        m3 = re.match(r'^(.*?)[\s]?(\d{1,4})[:：]\s*([\d–\-~a-zA-Z]+)?\s*$', j)
        if m3:
            journal, volume, pages = m3.group(1).strip(), m3.group(2), (m3.group(3) or '')
        else:
            journal = j
    if '期刊待核实' in jour or '期刊未确认' in jour:
        journal = ''

    doi, url = '', ''
    dm = re.search(r'10\.\d{4,9}/[^\s)\]]+', doiurl)
    if dm:
        doi = dm.group(0).rstrip('.,;')
    um = re.search(r'https?://[^\s)\]]+', doiurl)
    if um:
        url = um.group(0).rstrip('.,;')

    sp, ep = '', ''
    if pages:
        pm = re.split(r'[–\-~]', pages)
        sp = pm[0].strip()
        if len(pm) > 1:
            ep = pm[1].strip()

    rec = []
    rec.append('TY  - ' + typ)
    for a in authors:
        rec.append('AU  - ' + a)
    if year:
        rec.append('PY  - ' + year)
    if title:
        rec.append('TI  - ' + title)
    if journal:
        if typ in ('CHAP', 'BOOK'):
            rec.append('T2  - ' + journal)
        else:
            rec.append('JO  - ' + journal)
    if volume:
        rec.append('VL  - ' + volume)
    if issue:
        rec.append('IS  - ' + issue)
    if sp:
        rec.append('SP  - ' + sp)
    if ep:
        rec.append('EP  - ' + ep)
    if doi:
        rec.append('DO  - ' + doi)
    if url:
        rec.append('UR  - ' + url)
    rec.append('N1  - 编号：' + cid + ('；主题：' + theme if theme else ''))
    rec.append('ER  - ')
    records.append('\n'.join(rec))

with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n\n'.join(records) + '\n')

print('records=%d' % len(records))
# 摘要统计
from collections import Counter
c = Counter(r.split('\n')[0].replace('TY  - ','') for r in records)
print('types:', dict(c))
no_author = sum(1 for r in records if 'AU  -' not in r)
no_year = sum(1 for r in records if 'PY  -' not in r)
no_doi = sum(1 for r in records if 'DO  -' not in r)
print('no-author=%d no-year=%d no-doi=%d' % (no_author, no_year, no_doi))
