# -*- coding: utf-8 -*-
"""重试 Unpaywall 中 api_error / small_or_error 的 DOI：重新查询并下载 OA PDF。"""
import re, io, os, time, csv, urllib.request, urllib.error

WORK = r'F:\deepseek harness'
UP = os.path.join(WORK, 'unpaywall_report.csv')
OUTDIR = os.path.join(WORK, 'pdfs')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'}
EMAIL = 'test@mail.com'

rows = []
with io.open(UP, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)

targets = [r for r in rows if r['Status'] in ('api_error', 'small_or_error')]
print('retry targets=%d' % len(targets))

def get(url, hdrs, timeout=60):
    req = urllib.request.Request(url, headers=hdrs)
    return urllib.request.urlopen(req, timeout=timeout).read()

results = []
for r in targets:
    doi = r['DOI']
    status, used = 'failed', ''
    try:
        data = get('https://api.unpaywall.org/v2/%s?email=%s' % (doi, EMAIL), UA, 40)
        import json as _j
        info = _j.loads(data.decode('utf-8', 'ignore'))
        if info.get('is_oa'):
            loc = info.get('best_oa_location') or {}
            u = loc.get('url_for_pdf') or loc.get('url') or ''
            if u:
                try:
                    pdf = get(u, UA, 70)
                    if len(pdf) > 20000:
                        fname = re.sub(r'[^A-Za-z0-9._-]', '_', doi) + '.pdf'
                        open(os.path.join(OUTDIR, fname), 'wb').write(pdf)
                        status, used = 'downloaded', fname
                    else:
                        status = 'small_or_error'
                except Exception:
                    status = 'download_failed'
            else:
                status = 'oa_no_pdf_url'
        else:
            status = 'no_oa'
    except Exception:
        status = 'api_error_again'
    results.append({'No': r['No'], 'DOI': doi, 'Old': r['Status'], 'New': status, 'File': used})
    print('  %s [%s -> %s]' % (doi[:44], r['Status'], status))
    time.sleep(1.1)

with io.open(os.path.join(WORK, 'retry_report.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['No', 'DOI', 'Old', 'New', 'File'])
    w.writeheader()
    w.writerows(results)
from collections import Counter
c = Counter(x['New'] for x in results)
print('RETRY SUMMARY:', dict(c))
