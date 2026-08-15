# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

BASE = r"f:\deepseek harness"
PROFILE = os.path.join(BASE, ".pw_profile")
URL = "https://doi.org/10.1111/raq.12631"

def run():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, accept_downloads=True,
            viewport={"width": 1360, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 上下文级监听：新页面、下载、响应
        def on_page(newpage):
            print("  [新页面] url=", newpage.url)
            newpage.on("download", on_download)
            newpage.on("response", on_response)
        def on_download(dl):
            print("  [下载事件] suggested=", dl.suggested_filename)
        def on_response(resp):
            ct = (resp.headers.get("content-type") or "").lower()
            if "pdf" in ct or resp.url.lower().endswith(".pdf"):
                print("  [响应] ct=", ct, " url=", resp.url[:120])
        ctx.on("page", on_page)
        page.on("download", on_download)
        page.on("response", on_response)

        print("打开:", URL)
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        print("等待 12s 让页面完全加载...")
        page.wait_for_timeout(12000)

        print("\n=== 含 pdf/download 的 <a> 链接 ===")
        try:
            links = page.eval_on_selector_all(
                "a[href]", "els => els.map(e => ({href:e.href, txt:(e.innerText||'').trim().slice(0,40), vis:e.offsetParent!==null}))"
            )
            for l in links:
                if re.search(r'pdf|download', l["href"], re.I) or re.search(r'pdf|download', l["txt"], re.I):
                    print("  ", l)
        except Exception as e:
            print("  err", e)

        print("\n=== 含 pdf/download 的 <button> ===")
        try:
            btns = page.eval_on_selector_all(
                "button", "els => els.map(e => ({txt:(e.innerText||'').trim().slice(0,40), vis:e.offsetParent!==null, cls:e.className.slice(0,50)}))"
            )
            for b in btns:
                if re.search(r'pdf|download', b["txt"], re.I):
                    print("  ", b)
        except Exception as e:
            print("  err", e)

        print("\n=== 尝试点击第一个 PDF 链接 ===")
        try:
            loc = page.locator("a[href*='/pdf'], a[href*='pdfdirect'], a[href*='/epdf']").first
            print("  count:", page.locator("a[href*='/pdf'], a[href*='pdfdirect'], a[href*='/epdf']").count())
            if loc.count() > 0:
                print("  href:", loc.get_attribute("href"))
                loc.click(timeout=6000)
                print("  已点击，等待 10s...")
                page.wait_for_timeout(10000)
        except Exception as e:
            print("  click err:", repr(e))

        print("\n=== 当前所有页面 ===")
        for pg in ctx.pages:
            print("  page url:", pg.url)

        print("\n诊断结束")
        ctx.close()

run()
