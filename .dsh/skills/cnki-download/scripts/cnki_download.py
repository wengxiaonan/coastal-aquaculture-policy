# -*- coding: utf-8 -*-
"""
知网（CNKI）批量下载脚本 —— cnki-download 技能核心
用法：
  py -3 cnki_download.py --list <清单.csv> [--out <目录>] [--profile <目录>]
                          [--retry 2] [--ids CN-01,CN-02] [--headless]
清单 CSV 需含列：编号、题名（必填）；期刊年卷期页（可选，用于判别）；直达链接（可选）。
合规：仅用于机构订阅合法登录下的个人检索下载，不绕过付费/验证。
"""
import argparse, csv, io, os, re, sys, time, urllib.parse
from playwright.sync_api import sync_playwright

def norm(s):
    return re.sub(r'[\s“”"\'’‘、，。；：（）()·\-—–]+', '', s or '')

def load_meta(path):
    meta = {}
    with io.open(path, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if '编号' in r and '题名' in r:
                meta[r['编号']] = r
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

def save_download(dl, cid, outdir):
    p = os.path.join(outdir, cid + '.pdf')
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
        os.rename(p, os.path.join(outdir, cid + '.caj'))
        return 'caj'
    os.remove(p)
    return None

def click_pdf(page, row, cid, outdir):
    btns = ['a:has-text("PDF下载")', 'a:has-text("PDF 下载")', 'a.btn-dlpdf', 'a:has-text("PDF")']
    for sel in btns:
        try:
            b = row.locator(sel).first
            if b.count() == 0:
                continue
            with page.expect_download(timeout=60000) as info:
                b.click(timeout=15000)
            r = save_download(info.value, cid, outdir)
            if r:
                return r
        except Exception:
            continue
    # "下载"下拉
    try:
        dl = row.locator('a:has-text("下载")').first
        if dl.count() > 0:
            with page.expect_download(timeout=60000) as info:
                dl.click(timeout=15000)
                try:
                    page.locator('a:has-text("PDF下载"), a:has-text("PDF 下载")').first.click(timeout=8000)
                except Exception:
                    pass
            r = save_download(info.value, cid, outdir)
            if r:
                return r
    except Exception:
        pass
    # 详情页
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
                r = save_download(info.value, cid, outdir)
                if r:
                    dp.close()
                    return r
            except Exception:
                continue
        dp.close()
    except Exception:
        pass
    return None

def try_direct_page(ctx, url, cid, outdir):
    """已知直达链接（如 wap.cnki.net 文章页）直接下载"""
    try:
        pg = ctx.new_page()
        pg.goto(url, timeout=60000, wait_until='domcontentloaded')
        time.sleep(4)
        btns = ['a:has-text("PDF下载")', 'a:has-text("PDF 下载")', 'a:has-text("下载")',
                'a:has-text("CAJ下载")', 'a[href*="download"]']
        for sel in btns:
            try:
                b = pg.locator(sel).first
                if b.count() == 0:
                    continue
                with pg.expect_download(timeout=60000) as info:
                    b.click(timeout=15000)
                r = save_download(info.value, cid, outdir)
                if r:
                    return r
            except Exception:
                continue
        pg.close()
    except Exception:
        pass
    return None

def wait_login(page, timeout=900):
    print('>>> 请在弹出的浏览器中完成知网 CARSI 机构登录（选所在高校）。')
    print('>>> 脚本自动检测登录状态（最多等待 %d 秒）...' % timeout)
    start = time.time()
    while time.time() - start < timeout:
        try:
            page.goto('https://kns.cnki.net/', timeout=40000, wait_until='domcontentloaded')
            time.sleep(3)
            body = page.locator('body').inner_text(timeout=15000)
            if ('海南大学' in body) or ('退出' in body) or ('我的CNKI' in body) or ('个人中心' in body):
                print('>>> 检测到已登录，开始下载。')
                return True
        except Exception:
            pass
        time.sleep(5)
    print('>>> 未确认登录，继续尝试（可能失败）')
    return False

def main():
    ap = argparse.ArgumentParser(description='知网批量下载')
    ap.add_argument('--list', required=True, help='清单 CSV（编号/题名/期刊年卷期页/直达链接）')
    ap.add_argument('--out', default='pdfs_cn', help='输出目录')
    ap.add_argument('--profile', default=None, help='playwright profile 目录')
    ap.add_argument('--retry', type=int, default=2, help='每篇重试次数')
    ap.add_argument('--ids', default='', help='仅下载指定编号（逗号分隔）')
    ap.add_argument('--headless', action='store_true', help='无头模式（需 profile 已登录）')
    args = ap.parse_args()

    meta = load_meta(args.list)
    if args.ids:
        ids = [x.strip() for x in args.ids.split(',') if x.strip()]
        meta = {k: v for k, v in meta.items() if k in ids}
    if not meta:
        print('清单为空或列名不符（需：编号、题名）')
        sys.exit(1)
    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)
    profile = args.profile or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.pw_cache', 'cnki_profile')
    os.makedirs(os.path.dirname(profile), exist_ok=True)

    print('待下载 %d 篇 -> %s' % (len(meta), outdir))
    results = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, headless=args.headless, accept_downloads=True,
            viewport={'width': 1280, 'height': 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        wait_login(page)
        for idx, (cid, it) in enumerate(meta.items(), 1):
            title = it.get('题名', cid)
            direct = it.get('直达链接', '').strip()
            print('[%d/%d] %s %s ...' % (idx, len(meta), cid, title[:24]))
            got = None
            if direct:
                got = try_direct_page(ctx, direct, cid, outdir)
            for attempt in range(args.retry):
                if got:
                    break
                keywords = [title]
                short = re.sub(r'^(我国|基于|国内外|国外|浅议|如何)', '', title)
                if short and short != title:
                    keywords.append(short[:14])
                for kw in keywords:
                    if got:
                        break
                    try:
                        pg = ctx.new_page()
                        pg.goto(search_url(kw), timeout=60000, wait_until='domcontentloaded')
                        try:
                            pg.wait_for_selector('table.result-table-list tr, li.list-item, #gridTable tr', timeout=18000)
                        except Exception:
                            pg.close()
                            continue
                        time.sleep(2)
                        row = find_row(pg, kw)
                        if row is not None:
                            got = click_pdf(pg, row, cid, outdir)
                        pg.close()
                        if got:
                            break
                    except Exception as e:
                        print('    异常: %s' % str(e)[:60])
                        try:
                            pg.close()
                        except Exception:
                            pass
                time.sleep(1)
            results.append((cid, got or 'fail'))
            print('    -> %s' % (got if got else '需人工'))
        ctx.close()

    logpath = outdir.rstrip('\\/') + '_log.csv'
    with io.open(logpath, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['编号', '状态'])
        for cid, st in results:
            w.writerow([cid, st])
    ok = [r for r in results if r[1] != 'fail']
    print('\n===== 完成 =====')
    print('成功 %d / %d' % (len(ok), len(results)))
    print('成功: %s' % ', '.join(r[0] for r in ok))
    print('需人工: %s' % ', '.join(r[0] for r in results if r[1] == 'fail'))
    print('日志: %s' % logpath)

if __name__ == '__main__':
    main()
