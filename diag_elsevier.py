# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

PROFILE = r"f:\deepseek harness\.pw_profile"
URL = "https://www.sciencedirect.com/science/article/abs/pii/S0308597X2400280X"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
        accept_downloads=True, viewport={"width": 1360, "height": 900},
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)
    print("URL:", page.url[:140])
    print("--- links with pdf/download ---")
    for a in page.locator("a").all():
        h = a.get_attribute("href") or ""
        t = (a.inner_text() or "").strip()
        if "pdf" in h.lower() or "download" in t.lower() or "view pdf" in t.lower() or "get access" in t.lower():
            print("A: text=%r href=%s" % (t[:60], h[:130]))
    print("--- buttons ---")
    for b in page.locator("button").all():
        t = (b.inner_text() or "").strip()
        if t:
            print("BTN: %r" % t[:80])
    print("--- any [role=button] text containing pdf/download/view ---")
    for r in ["link", "button"]:
        try:
            loc = page.get_by_role(r, name="pdf")
            print("role=%s name='pdf' count=%d" % (r, loc.count()))
        except Exception as e:
            print("err", r, repr(e)[:80])
    ctx.close()
