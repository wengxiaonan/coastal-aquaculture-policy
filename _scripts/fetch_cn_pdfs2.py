# -*- coding: utf-8 -*-
"""中文 PDF 抓取 v2：file_no 构造 create_pdf 直链 + SciEngine 带 Referer + 失败重试。"""
import re, io, os, time, csv, urllib.request, urllib.error

WORK = r'F:\deepseek harness'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'}
UA2 = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'}

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
    parts = re.split(r'(?m)^(\d+)\. \*\*', text)
    entries = {}
    i = 1
    while i < len(parts):
        entries[int(parts[i])] = '**' + (parts[i + 1] if i + 1 < len(parts) else '')
        i += 2
    return entries

def get(url, hdrs, timeout=60):
    req = urllib.request.Request(url, headers=hdrs)
    return urllib.request.urlopen(req, timeout=timeout).read()

def try_download(url, hdrs, timeout=70):
    try:
        data = get(url, hdrs, timeout)
        if len(data) > 20000:
            return data
    except Exception:
        pass
    return None

def main():
    out_dir = os.path.join(WORK, 'pdfs_cn')
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for fname, mapping in FILES:
        path = os.path.join(WORK, fname)
        text = io.open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        entries = get_entries(text)
        for cid, idx in mapping:
            ent = entries.get(idx, '')
            urls = re.findall(r'https?://[^\s\)\]]+', ent)
            fpath = os.path.join(out_dir, cid + '.pdf')
            if os.path.exists(fpath) and os.path.getsize(fpath) > 20000:
                rows.append({'Id': cid, 'Status': 'already', 'Source': 'prev'})
                continue
            status, used = 'no_url', ''
            data = None
            # 1) file_no -> create_pdf 直链（海洋开发与管理等官网）
            fn = re.search(r'file_no=(\d+)', ent)
            if fn:
                base = 'http://www.haiyangkaifayuguanli.com/hykfygl/ch/reader/create_pdf.aspx?file_no=' + fn.group(1)
                for alt in (base, base.replace('/hykfygl/', '/hykfyglen/'), 'http://haiyangkaifayuguanli.com/ch/reader/create_pdf.aspx?file_no=' + fn.group(1)):
                    data = try_download(alt, UA)
                    if data:
                        status, used = 'downloaded', alt
                        break
            # 2) sciengine 带 Referer
            if not data:
                for u in urls:
                    if 'sciengine' in u:
                        h = dict(UA); h['Referer'] = 'https://www.sciengine.com/'
                        data = try_download(u, h)
                        if data:
                            status, used = 'downloaded', u
                            break
            # 3) 其他官网页面找 PDF（重试）
            if not data:
                for u in urls:
                    if re.search(r'cnki|wanfang|cqvip|webvpn', u, re.I):
                        if status == 'no_url':
                            status, used = 'needs_subscription', u
                        continue
                    for h in (UA, UA2):
                        try:
                            html = get(u, h, 50).decode('utf-8', 'ignore')
                            m = re.search(r'(?:href|src)="([^"]*(?:create_pdf|\.pdf|CN/PDF)[^"]*)"', html, re.I)
                            if m:
                                p = m.group(1)
                                if not p.startswith('http'):
                                    p = u.split('/')[0] + '//' + u.split('/')[2] + p
                                data = try_download(p, h)
                                if data:
                                    status, used = 'downloaded', p
                                    break
                            else:
                                m2 = re.search(r"file_no=(\d+)", html)
                                if m2:
                                    p2 = 'http://www.haiyangkaifayuguanli.com/hykfygl/ch/reader/create_pdf.aspx?file_no=' + m2.group(1)
                                    data = try_download(p2, h)
                                    if data:
                                        status, used = 'downloaded', p2
                                        break
                                elif status == 'no_url':
                                    status = 'page_no_pdf_link'
                        except Exception:
                            if status == 'no_url':
                                status = 'page_fetch_failed'
                    if data:
                        break
            if data:
                open(fpath, 'wb').write(data)
            rows.append({'Id': cid, 'Status': status, 'Source': used})
            time.sleep(0.5)
    with io.open(os.path.join(out_dir, 'download_report2.csv'), 'w', encoding='utf-8', newline='') as f:
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
            print('  OK %s <- %s' % (r['Id'], r['Source'][:80]))

if __name__ == '__main__':
    main()
