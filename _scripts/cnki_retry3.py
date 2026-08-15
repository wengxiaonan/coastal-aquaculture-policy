# -*- coding: utf-8 -*-
"""最后一次尝试：JP-31 知网文章直达页下载。"""
import io, os, time
from playwright.sync_api import sync_playwright

WORK = r'F:\deepseek harness'
OUTDIR = os.path.join(WORK, 'pdfs_cn')
PROFILE = os.path.join(WORK, '.pw_cache', 'cnki_profile')
URLS = [
    'https://wap.cnki.net/touch/web/Journal/Article/SJNY201808024.html',
    'https://www.cnki.net/',
]

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

def main():
    got = None
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, accept_downloads=True, viewport={'width': 1280, 'height': 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URLS[0], timeout=60000, wait_until='domcontentloaded')
        time.sleep(4)
        btns = ['a:has-text("PDF下载")', 'a:has-text("PDF 下载")', 'a:has-text("下载")',
                'a:has-text("CAJ下载")', 'a:has-text("在线阅读")', 'a[href*="download"]']
        for sel in btns:
            try:
                b = page.locator(sel).first
                if b.count() == 0:
                    continue
                with page.expect_download(timeout=60000) as info:
                    b.click(timeout=15000)
                r = save_download(info.value, 'JP-31')
                if r:
                    got = r
                    break
            except Exception:
                continue
        ctx.close()
    print('JP-31 ->', got if got else '需人工')

if __name__ == '__main__':
    main()
