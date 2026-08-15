# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

PROFILE = r"f:\deepseek harness\.pw_profile"
TARGETS = [
    ("#9 Wiley pdfdirect", "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/jwas.70005"),
    ("#2 Elsevier /pdf", "https://www.sciencedirect.com/science/article/pii/S0301479722001967/pdf"),
]

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
        accept_downloads=True, viewport={"width":1360,"height":900},
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def on_dl(dl):
        print("    [下载事件] suggested=", dl.suggested_filename)
    def on_resp(resp):
        ct = (resp.headers.get("content-type") or "").lower()
        if "pdf" in ct or resp.url.lower().endswith(".pdf"):
            try:
                b = resp.body()
                print("    [响应] ct=%s magic=%s size=%d url=%s" % (ct, b[:5], len(b), resp.url[:90]))
            except Exception as e:
                print("    [响应] body读取失败:", repr(e))
    page.on("download", on_dl)
    page.on("response", on_resp)

    for name, url in TARGETS:
        print("\n=== %s ===" % name)
        print("  导航到:", url)
        try:
            with page.expect_download(timeout=15000) as dl_info:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            dl = dl_info.value
            print("    [expect_download] 捕获到下载:", dl.suggested_filename)
        except Exception as e:
            print("    [expect_download] 未触发下载:", repr(e)[:120])
        page.wait_for_timeout(5000)
        print("    当前 URL:", page.url[:120])

    ctx.close()
