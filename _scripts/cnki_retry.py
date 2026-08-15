# -*- coding: utf-8 -*-
"""知网自动下载 · 重试改进版：处理 15 篇失败条目（放宽匹配 / 详情页下载 / 重试）。"""
import csv, io, os, re, time, urllib.parse
from playwright.sync_api import sync_playwright

WORK = r'F:\deepseek harness'
OUTDIR = os.path.join(WORK, 'pdfs_cn')
PROFILE = os.path.join(WORK, '.pw_cache', 'cnki_profile')
TARGETS = ['CN-06','CN-10','CN-13','CN-14','CN-15','CN-16','CN-19','CN-31','CN-32',
           'CN-63','CN-68','CN-69','CN-75','CN-76','JP-31']

def norm(s):
    return re.sub(r'[\s“”"\'’‘、，。；：（）()·\-—–]+', '', s or '')

def load_meta():
    meta = {}
    with io.open(os.path.join(WORK, '文献传递申请清单.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            meta[r['编号']] = (r['题名'], r['期刊年卷期页'])
    return meta

def search_url(kw):
    return 'https://kns.cnki.net/kns8s/defaultresult/index?korder=SU&kw=' + urllib.parse.quote(kw)

def find_row(page, title):
    t = norm(title)
    keys = [t[:6], t[:8]]
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
                for k in keys:
                    if k and k in txt:
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
    # 1) 结果行内直接点
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
    # 2) 行内"下载"下拉（点开后弹层选 PDF）
    try:
        dl = row.locator('a:has-text("下载")').first
        if dl.count() > 0:
            with page.expect_download(timeout=60000) as info:
                dl.click(timeout=15000)
                try:
                    page.locator('a:has-text("PDF下载"), a:has-text("PDF 下载")').first.click(timeout=8000)
                except Exception:
                    pass
            r = save_download(info.value, cid)
            if r:
                return r
    except Exception:
        pass
    # 3) 进入详情页下载
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

def wait_login(page, timeout=600):
    print('>>> 检测登录状态（已保存 profile，通常直接通过）...')
    start = time.time()
    while time.time() - start < timeout:
        try:
            page.goto('https://kns.cnki.net/', timeout=40000, wait_until='domcontentloaded')
            time.sleep(3)
            body = page.locator('body').inner_text(timeout=15000)
            if ('海南大学' in body) or ('退出' in body) or ('我的CNKI' in body):
                print('>>> 已登录，开始下载。')
                return True
        except Exception:
            pass
        time.sleep(4)
    print('>>> 未确认登录，继续尝试（可能失败）')
    return False

def main():
    meta = load_meta()
    results = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, accept_downloads=True, viewport={'width': 1280, 'height': 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        wait_login(page)
        for idx, cid in enumerate(TARGETS, 1):
            title, journal = meta.get(cid, (cid, ''))
            print('[%d/%d] %s %s ...' % (idx, len(TARGETS), cid, title[:24]))
            got = None
            for attempt in range(2):
                try:
                    pg = ctx.new_page()
                    pg.goto(search_url(title), timeout=60000, wait_until='domcontentloaded')
                    try:
                        pg.wait_for_selector('table.result-table-list tr, li.list-item, #gridTable tr', timeout=18000)
                    except Exception:
                        pg.close()
                        continue
                    time.sleep(2)
                    row = find_row(pg, title)
                    if row is None:
                        # 换短关键词重试：去常见前缀
                        short = re.sub(r'^(我国|基于|国内外|国外|浅议|如何)', '', title)
                        pg.goto(search_url(short[:14]), timeout=60000, wait_until='domcontentloaded')
                        try:
                            pg.wait_for_selector('table.result-table-list tr, li.list-item, #gridTable tr', timeout=18000)
                        except Exception:
                            pass
                        time.sleep(2)
                        row = find_row(pg, short)
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
            results.append((cid, got or 'fail'))
            print('    -> %s' % (got if got else '需人工'))
            time.sleep(1)
        ctx.close()
    ok = [r for r in results if r[1]]
    print('\n===== 重试完成 =====')
    print('成功 %d / %d' % (len(ok), len(TARGETS)))
    print('成功: %s' % ', '.join(r[0] for r in ok))
    print('仍失败: %s' % ', '.join(r[0] for r in results if not r[1]))
    with io.open(os.path.join(WORK, 'cnki_retry_log.txt'), 'w', encoding='utf-8') as f:
        for r in results:
            f.write('%s\t%s\n' % (r[0], r[1]))

if __name__ == '__main__':
    main()
