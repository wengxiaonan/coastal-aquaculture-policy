# -*- coding: utf-8 -*-
"""生成《图书馆文献传递申请清单.md》：52 篇中文文献的著录信息 + 下载状态。"""
import re, io, os, csv

WORK = r'F:\deepseek harness'
SRC = os.path.join(WORK, '中美欧日中近岸养殖政策文献总目.md')
OUT = os.path.join(WORK, '图书馆文献传递申请清单.md')
IDS = ['CN-%02d' % i for i in range(1, 33)]
IDS += ['CN-54','CN-56','CN-58','CN-59','CN-61','CN-62','CN-63','CN-64','CN-65','CN-68','CN-69','CN-71','CN-73','CN-74','CN-75','CN-76','CN-77','JP-31','JP-37','KR-02']

text = io.open(SRC, encoding='utf-8').read()

# 已下载状态
have = set()
for d in ('pdfs_cn',):
    p = os.path.join(WORK, d)
    if os.path.isdir(p):
        for f in os.listdir(p):
            if f.endswith('.pdf'):
                have.add(f[:-4])

# 提取每条著录
rows = []
for cid in IDS:
    m = re.search(r'(?m)^\| ' + re.escape(cid) + r' \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|', text)
    if not m:
        rows.append({'Id': cid, 'Theme': '', 'Lit': '', 'Jour': '', 'Db': '', 'Got': 'not_found'})
        continue
    theme, lit, jour, doicol = (m.group(i).strip() for i in range(1, 5))
    lit_clean = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', lit)
    # 作者 年份 标题
    ym = re.search(r'(\d{4})', lit_clean)
    author = ''
    title = lit_clean
    if ym:
        author = lit_clean[:ym.start()].strip()
        tail = lit_clean[ym.end():]
        title = re.sub(r'^[^.\s．]*\s*[.．]?\s*', '', tail).strip()
        author = re.sub(r'[（(]作者待核实[^）)]*[）)]|（作者待核实）|（线索[^）)]*）', '', author).strip()
    # 数据库判断
    db = '期刊官网'
    if re.search(r'cnki|知网', doicol, re.I):
        db = 'CNKI（知网）'
    elif re.search(r'wanfang|万方', doicol, re.I):
        db = '万方'
    elif re.search(r'cqvip|维普', doicol, re.I):
        db = '维普'
    rows.append({'Id': cid, 'Theme': theme, 'Lit': lit_clean, 'Author': author, 'Title': title, 'Jour': jour, 'Db': db, 'Got': 'yes' if cid in have else 'no'})

L = []
L.append('# 图书馆文献传递申请清单（中文文献，52 篇）')
L.append('')
L.append('> **用途**：对无法自动获取全文的中文期刊论文，通过图书馆文献传递服务获取。')
L.append('> **常用渠道**：① 本校图书馆文献传递/CALIS（高校）；② [NSTL 国家科技图书文献中心](https://www.nstl.gov.cn)；③ 读秀/百链（超星）；④ 中国国家图书馆；⑤ 知网单篇购买。')
L.append('> **提交格式**：复制下表所需行（题名/作者/期刊/年卷期页/数据库）粘贴到系统申请表单即可；多数系统支持"按篇提交"并邮件发送 PDF。')
L.append('')
L.append('## 一、需文献传递的篇目（未获取全文）')
L.append('')
L.append('| 编号 | 题名 | 作者 | 期刊/年卷期页 | 数据库 |')
L.append('|---|---|---|---|---|')
for r in rows:
    if r['Got'] != 'yes':
        L.append('| %s | %s | %s | %s | %s |' % (r['Id'], r['Title'], r['Author'] or '（作者待核实）', r['Jour'], r['Db']))
L.append('')
L.append('## 二、已下载全文（供核对，无需传递）')
L.append('')
L.append('| 编号 | 题名 | 期刊/年卷期页 |')
L.append('|---|---|---|')
for r in rows:
    if r['Got'] == 'yes':
        L.append('| %s | %s | %s |' % (r['Id'], r['Title'], r['Jour']))
L.append('')
L.append('## 三、操作提示')
L.append('')
L.append('- 知网（CNKI）论文：多数高校图书馆的"文献传递"不直接代理知网，建议优先用**校园网 + 知网账号**直接下载；校外可用机构 VPN。')
L.append('- NSTL：支持期刊论文文献传递（收费，约数元/篇），提交后由馆藏单位扫描发送。')
L.append('- 读秀/百链：输入题名可申请"图书馆文献传递"，通常 1~2 个工作日内邮箱接收（每篇限部分页数，可多次申请）。')
L.append('- 老文献（如 2004~2015 年）部分未电子化，传递可能为扫描件，申请时注明"无电子版可扫描"。')
L.append('')
with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

need = sum(1 for r in rows if r['Got'] != 'yes')
print('total=%d need_delivery=%d downloaded=%d' % (len(rows), need, len(rows) - need))
