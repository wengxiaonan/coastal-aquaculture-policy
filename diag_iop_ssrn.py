# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

PROFILE = r"f:\deepseek harness\.pw_profile"
IOP = "https://iopscience.iop.org/article/10.1088/1748-9326/ad76c0/pdf"
SSRN = "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4783738"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
        accept_downloads=True, viewport={"width":1360,"height":900},
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def on_dl(dl):
        print("    [download] suggested=", dl.suggested_filename)
    def on_resp(resp):
        ct = (resp.headers.get("content-type") or "").lower()
        u = resp.url
        if "pdf" in ct or u.lower().endswith(".pdf") or "/pdf" in u.lower():
            try:
                b = resp.body()
                print("    [resp] status=%d ct=%s size=%d magic=%s url=%s" % (resp.status, ct, len(b), b[:5], u[:110]))
            except Exception as e:
                print("    [resp] body-err status=%d ct=%s url=%s :: %r" % (resp.status, ct, u[:110], e))
    page.on("download", on_dl)
    page.on("response", on_resp)

    print("=== IOP #14 ===")
    try:
        page.goto(IOP, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print("  goto err", repr(e)[:120])
    page.wait_for_timeout(12000)
    print("  final URL:", page.url[:120])
    for a in page.locator("a[href$='.pdf']").all():
        print("  a.pdf href=", a.get_attribute("href"))
    for i, fr in enumerate(page.frames):
        print("  frame[%d] url=%s" % (i, fr.url[:110]))

    print("\n=== SSRN #33 ===")
    try:
        page.goto(SSRN, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print("  goto err", repr(e)[:120])
    page.wait_for_timeout(8000)
    print("  final URL:", page.url[:120])
    # find download-ish buttons/links
    for role in ["link", "button"]:
        for name in ["Download", "Download This Paper", "Download Paper", "Open PDF"]:
            try:
                loc = page.get_by_role(role, name=name)
                for i in range(loc.count()):
                    el = loc.nth(i)
                    print("  [%s] %r visible=%s href=%s" % (role, name, el.is_visible(), el.get_attribute("href")))
            except Exception:
                pass
    for a in page.locator("a").all():
        t = (a.inner_text() or "").strip()
        h = a.get_attribute("href") or ""
        if "download" in t.lower() or "download" in h.lower() or h.lower().endswith(".pdf"):
            print("  a: text=%r href=%s" % (t[:50], h[:120]))

    ctx.close()
