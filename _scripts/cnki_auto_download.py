# -*- coding: utf-8 -*-
"""
知网（CNKI）自动下载脚本 —— 47 篇中文文献
用法：
  1) py -3 cnki_auto_download.py
  2) 浏览器自动打开知网，请完成 CARSI 机构登录（选海南大学，学号/工号登录）
  3) 登录成功后回到终端按回车，脚本将逐篇检索并下载 PDF 到 pdfs_cn\\编号.pdf
说明：本脚本仅在用户通过机构订阅合法登录知网的前提下自动化"个人检索+下载"操作，
      不绕过任何付费或验证机制；请遵守知网服务条款与机构使用规范。
依赖：playwright（已装），Chromium 由 playwright 管理。
"""
import csv, io, os, re, sys, time, urllib.parse
from playwright.sync_api import sync_playwright

WORK = r'F:\deepseek harness'
CSV = os.path.join(WORK, '文献传递申请清单.csv')
OUTDIR = os.path.join(WORK, 'pdfs_cn')
PROFILE = os.path.join(WORK, '.pw_cache', 'cnki_profile')
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(os.path.dirname(PROFILE), exist_ok=True)

def load_list():
    rows = []
    with io.open(CSV, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['全文状态'] == '需文献传递':
                rows.append(r)
    return rows

def search_url(title):
    return 'https://kns.cnki.net/kns8s/defaultresult/index?korder=SU&kw=' + urllib.parse.quote(title)

def norm(s):
    return re.sub(r'[\s“”"\'’‘、，。；：（）()·\-—–]+', '', s or '')

def find_row(page, title, journal):
    """在结果页匹配目标条目，返回 (row_locator) 或 None"""
    selectors = [
        'table.result-table-list tr',
        'tr.result',
        '.result-table-list tr',
        '#gridTable tr',
        'li.list-item',
    ]
    row_sel = None
    for s in selectors:
        try:
            if page.locator(s).count() > 0:
                row_sel = s
                break
        except Exception:
            continue
    if not row_sel:
        return None
    t = norm(title)
    for i in range(page.locator(row_sel).count()):
        row = page.locator(row_sel).nth(i)
        try:
            txt = row.inner_text()
        except Exception:
            continue
        if not txt:
            continue
        if t[:8] in norm(txt) or t in norm(txt):
            # 期刊核对（可选，期刊名可能缩写/别名，放宽）
            if journal:
                j = norm(journal.split('（')[0].split('(')[0])[:6]
                if j and j not in norm(txt):
                    continue
            return row
    return None

def click_download(page, row, cid):
    """在匹配行中点击 PDF/CAJ 下载，返回 (pdf_path) 或 None"""
    pdf_btns = [
        'a.btn-dlpdf', 'a:has-text("PDF下载")', 'a:has-text("PDF 下载")',
        'a:has-text("下载") >> nth=0', 'a.downloadlink',
    ]
    caj_btns = ['a:has-text("CAJ下载")', 'a:has-text("CAJ 下载")']
    for sel in pdf_btns + caj_btns:
        try:
            btn = row.locator(sel).first
            if btn.count() == 0:
                continue
            with page.expect_download(timeout=60000) as dl_info:
                btn.click(timeout=15000)
            dl = dl_info.value
            fname = cid + '.pdf'
            path = os.path.join(OUTDIR, fname)
            dl.save_as(path)
            if os.path.getsize(path) > 20000:
                return path
            os.remove(path)
        except Exception:
            continue
    return None

def wait_login(page, timeout=900):
    """轮询检测知网 CARSI 登录是否完成（首页出现机构名/用户名即视为已登录）"""
    print('>>> 请在弹出的浏览器中完成知网 CARSI 机构登录（选海南大学）。')
    print('>>> 脚本将自动检测登录状态（最多等待 %d 秒）...' % timeout)
    start = time.time()
    while time.time() - start < timeout:
        try:
            page.goto('https://kns.cnki.net/', timeout=40000, wait_until='domcontentloaded')
            time.sleep(3)
            body = page.locator('body').inner_text(timeout=15000)
            if ('海南大学' in body) or ('退出' in body) or ('我的CNKI' in body) or ('个人中心' in body):
                print('>>> 检测到已登录，开始自动下载。')
                return True
        except Exception:
            pass
        time.sleep(5)
    print('>>> 未检测到登录状态，尝试继续（若下载失败请检查登录）')
    return False

def main():
    items = load_list()
    print('待下载 %d 篇' % len(items))
    results = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, accept_downloads=True,
            viewport={'width': 1280, 'height': 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto('https://kns.cnki.net/', timeout=60000)
        logged = wait_login(page)
        if not logged:
            print('警告：未能确认登录，将尝试直接下载（很可能失败）。')

        for idx, it in enumerate(items, 1):
            cid, title, journal = it['编号'], it['题名'], it['期刊年卷期页']
            print('[%d/%d] %s %s ...' % (idx, len(items), cid, title[:26]))
            try:
                pg = ctx.new_page()
                pg.goto(search_url(title), timeout=60000, wait_until='domcontentloaded')
                try:
                    pg.wait_for_selector('table.result-table-list tr, li.list-item, #gridTable tr', timeout=20000)
                except Exception:
                    results.append((cid, 'no_result_page'))
                    pg.close()
                    continue
                # 等待结果渲染
                time.sleep(2)
                row = find_row(pg, title, journal)
                if row is None:
                    # 翻到第二页尝试
                    results.append((cid, 'not_matched'))
                    pg.close()
                    continue
                path = click_download(pg, row, cid)
                if path:
                    results.append((cid, 'ok'))
                    print('    下载成功 -> %s' % os.path.basename(path))
                else:
                    results.append((cid, 'no_download_btn'))
                    print('    未找到下载按钮（可能需人工）')
                pg.close()
            except Exception as e:
                results.append((cid, 'error:' + str(e)[:60]))
                print('    异常: %s' % str(e)[:80])
            time.sleep(1)
        ctx.close()

    ok = [r for r in results if r[1] == 'ok']
    print('\n===== 完成 =====')
    print('成功 %d / %d' % (len(ok), len(items)))
    print('成功编号: %s' % ', '.join(r[0] for r in ok))
    print('需人工处理:')
    for r in results:
        if r[1] != 'ok':
            print('  %s [%s]' % (r[0], r[1]))
    with io.open(os.path.join(WORK, 'cnki_download_log.txt'), 'w', encoding='utf-8') as f:
        for r in results:
            f.write('%s\t%s\n' % r)

if __name__ == '__main__':
    main()
