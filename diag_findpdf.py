# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding="utf-8")
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

PROFILE = r"f:\deepseek harness\.pw_profile"
ABS = "https://www.sciencedirect.com/science/article/abs/pii/S0308597X2400280X"


def _abs(page_url, href):
    return urljoin(page_url, href) if href else ""


def _same_root(a, b):
    try:
        return ".".join(urlparse(a).netloc.lower().split(".")[-2:]) == ".".join(urlparse(b).netloc.lower().split(".")[-2:])
    except Exception:
        return False


def find_pdf_url(page):
    page_url = page.url
    priority = [
        "a[href*='pdfdirect']",
        "a[href*='/doi/pdf/']",
        "a[href*='/article/'][href*='pdf']",
        "a[href*='pdfft']",
        "a[href*='/pdf/']",
    ]
    for css in priority:
        try:
            loc = page.locator(css)
            n = loc.count()
            print("  css=%s count=%d" % (css, n))
            for i in range(min(n, 3)):
                href = loc.nth(i).get_attribute("href")
                a = _abs(page_url, href)
                print("    [%d] href=%s" % (i, (href or "")[:100]))
                if not a.lower().startswith(("http://", "https://")):
                    continue
                if re.search(r'/epdf|downloadSupplement|supp-|\.docx|\.xlsx', a, re.I):
                    continue
                if _same_root(a, page_url):
                    return a
        except Exception as e:
            print("  css err", css, repr(e)[:80])
    return None


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
        accept_downloads=True, viewport={"width": 1360, "height": 900},
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(ABS, wait_until="domcontentloaded", timeout=60000)
    for t in range(0, 21, 3):
        page.wait_for_timeout(3000)
        print("t=%ds url=%s" % (t + 3, page.url[:130]))
    r = find_pdf_url(page)
    print("RESULT:", r)
    ctx.close()
