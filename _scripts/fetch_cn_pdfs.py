# -*- coding: utf-8 -*-
"""按文件+条目序号提取 52 篇中文文献链接并下载开放 PDF（Python 3，UTF-8）。"""
import re, io, os, time, csv, urllib.request, urllib.error

WORK = r'F:\deepseek harness'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36'}

# 文件 -> [(编号, 条目序号)]  （序号从 1 起）
FILES = [
    ('中国近岸养殖政策_文献收集.md', [('CN-%02d' % i, i) for i in range(1, 33)]),
    ('中国近岸养殖政策_文献收集_补检_T5社会接受度.md', [('CN-54', 1), ('CN-56', 3), ('CN-58', 5), ('CN-59', 6)]),
    ('中国近岸养殖政策_文献收集_补检_T6海藻贝类.md', [('CN-61', 1), ('CN-62', 2), ('CN-63', 3), ('CN-64', 4), ('CN-65', 5), ('CN-68', 8), ('CN-69', 9)]),
    ('近岸养殖与藻类养殖政策_六地扩充清单.md', [('CN-71', 1), ('CN-73', 3), ('JP-31', 7), ('CN-74', 11), ('CN-75', 12)]),
    ('近岸养殖政策_六地深挖补充清单.md', [('CN-76', 1), ('CN-77', 2)]),
    ('韩国挪威澳新智利近岸养殖政策_新增地区清单.md', [('KR-02', 2)]),
    ('欧盟挪威美日韩近岸养殖政策_深挖清单.md', [('JP-37', 17)]),
]

def get_entries(text):
    """按 '^数字. **' 切分条目，返回 [(序号, 条目文本)]"""
    parts = re.split(r'(?m)^(\d+)\. \*\*', text)
    entries = []
    i = 1
    while i < len(parts):
        num = int(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ''
        entries.append((num, '**' + body))
        i += 2
    return entries

def fetch(url, timeout=70):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()

def main():
    out_dir = os.path.join(WORK, 'pdfs_cn')
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for fname, mapping in FILES:
        path = os.path.join(WORK, fname)
        if not os.path.exists(path):
            for cid, _ in mapping:
                rows.append({'Id': cid, 'Status': 'file_missing', 'Source': ''})
            continue
        text = io.open(path, encoding='utf-8').read()
        entries = dict(get_entries(text))
        for cid, idx in mapping:
            ent = entries.get(idx, '')
            urls = re.findall(r'https?://[^\s\)\]]+', ent)
            status, used = 'no_url', ''
            for u in urls:
                is_pdf = bool(re.search(r'create_pdf|\.pdf|sciengine|/CN/PDF/|pdfpreview|open\.pdf', u, re.I))
                is_paid = bool(re.search(r'cnki|wanfang|cqvip|webvpn', u, re.I))
                fpath = os.path.join(out_dir, cid + '.pdf')
                if is_pdf and status != 'downloaded':
                    try:
                        data = fetch(u)
                        if len(data) > 20000:
                            open(fpath, 'wb').write(data)
                            status, used = 'downloaded', u
                        else:
                            status = 'small_or_error'
                    except Exception:
                        status = 'download_failed'
                elif not is_paid:
                    try:
                        html = fetch(u, 50).decode('utf-8', 'ignore')
                        m = re.search(r'href="([^"]*(?:create_pdf|\.pdf|CN/PDF)[^"]*)"', html, re.I)
                        if m:
                            p = m.group(1)
                            if not p.startswith('http'):
                                p = u.split('/')[0] + '//' + u.split('/')[2] + p
                            data = fetch(p)
                            if len(data) > 20000:
                                open(fpath, 'wb').write(data)
                                status, used = 'downloaded', p
                            else:
                                status = 'small_or_error'
                        else:
                            if status == 'no_url':
                                status = 'page_no_pdf_link'
                    except Exception:
                        if status == 'no_url':
                            status = 'page_fetch_failed'
                else:
                    if status == 'no_url':
                        status = 'needs_subscription'
                        used = u
            rows.append({'Id': cid, 'Status': status, 'Source': used})
            time.sleep(0.3)

    with io.open(os.path.join(out_dir, 'download_report.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['Id', 'Status', 'Source'])
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    c = Counter(r['Status'] for r in rows)
    print('SUMMARY downloaded=%d / %d' % (c.get('downloaded', 0), len(rows)))
    for k, v in c.most_common():
        print('  %s: %d' % (k, v))
    for r in rows:
        if r['Status'] == 'downloaded':
            print('  OK %s' % r['Id'])

if __name__ == '__main__':
    main()
