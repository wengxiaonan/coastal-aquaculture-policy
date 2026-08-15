# -*- coding: utf-8 -*-
"""针对性重试：CN-68（修正题名）、JP-31（短关键词）。"""
import io, os, re, time, urllib.parse
from playwright.sync_api import sync_playwright

WORK = r'F:\deepseek harness'
OUTDIR = os.path.join(WORK, 'pdfs_cn')
PROFILE = os.path.join(WORK, '.pw_cache', 'cnki_profile')

# 编号 -> (检索关键词, 行内判别词)
TASKS = [
    ('CN-68', '国内外养殖贝类质量安全管理比对', '贝类质量安全'),
    ('JP-31', '水产养殖保险', '韩国'),
]

def norm(s):
    return re.sub(r'[\s“”"\'’‘、，。；：（）()·\-—–]+', '', s or '')

def find_row(page, keyword, marker):
    k = norm(keyword)
    m = norm(marker)
    selectors = ['table.result-table-list tr', 'tr.result', 'li.list-item', '#gridTable tr']
    for s in selectors:
        try:
            if page.locator(s).count() == 0:
                continue
            for i in range(page.locator(s).count()):
                row = page.locator(s).nth(i)
                try:
                    txt = norm(row.inner_text())
                except Exception:
                    continue
                if k[:6] in txt:
                    if m and m not in txt:
                        continue
                    return row
        except Exception:
            continue
    return None

def save_download(dl, cid):
    p = os.path.join(OUTDIR, cid + '.pdf')
    dl.save_as(p)
    if not os.path.exists(p) or os.path.getsize(p) < 20000:
        if os.path.exists(p):
            os.remove(p)
        return None
    with open(p, 'rb') as f:
        head = f.read(8)
    if head[:4] == b'%PDF':
        return 'pdf'
    if head[:3] == b'CAJ':
        os.rename(p, os.path.join(OUTDIR, cid + '.caj'))
        return 'caj'
    os.remove(p)
    return None

def click_pdf(page, row, cid):
    btns = ['a:has-text("PDF下载")', 'a:has-text("PDF 下载")', 'a.btn-dlpdf', 'a:has-text("PDF")']
    for sel in btns:
        try:
            b = row.locator(sel).first
            if b.count() == 0:
                continue
            with page.expect_download(timeout=60000) as info:
                b.click(timeout=15000)
            r = save_download(info.value, cid)
            if r:
                return r
        except Exception:
            continue
    try:
        link = row.locator('td.name a, a.name, .name a, a.name').first
        if link.count() == 0:
            link = row.locator('a').first
        if link.count() == 0:
            return None
        with page.context.expect_page(timeout=20000) as pg_info:
            link.click()
        dp = pg_info.value
        dp.wait_for_load_state('domcontentloaded', timeout=40000)
        time.sleep(2)
        for sel in btns:
            try:
                b = dp.locator(sel).first
                if b.count() == 0:
                    continue
                with dp.expect_download(timeout=60000) as info:
                    b.click(timeout=15000)
                r = save_download(info.value, cid)
                if r:
                    dp.close()
                    return r
            except Exception:
                continue
        dp.close()
    except Exception:
        pass
    return None

def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, accept_downloads=True, viewport={'width': 1280, 'height': 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto('https://kns.cnki.net/', timeout=60000, wait_until='domcontentloaded')
        time.sleep(3)
        for cid, kw, marker in TASKS:
            print('[%s] 检索: %s' % (cid, kw))
            got = None
            for attempt in range(3):
                try:
                    pg = ctx.new_page()
                    pg.goto('https://kns.cnki.net/kns8s/defaultresult/index?korder=SU&kw='
                            + urllib.parse.quote(kw), timeout=60000, wait_until='domcontentloaded')
                    try:
                        pg.wait_for_selector('table.result-table-list tr, li.list-item, #gridTable tr', timeout=18000)
                    except Exception:
                        pg.close()
                        continue
                    time.sleep(2)
                    row = find_row(pg, kw, marker)
                    if row is not None:
                        got = click_pdf(pg, row, cid)
                    pg.close()
                    if got:
                        break
                except Exception as e:
                    print('    异常: %s' % str(e)[:60])
                    try:
                        pg.close()
                    except Exception:
                        pass
            print('    %s -> %s' % (cid, got if got else '需人工'))
            time.sleep(1)
        ctx.close()
    print('DONE')

if __name__ == '__main__':
    main()
