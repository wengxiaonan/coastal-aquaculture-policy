# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

PROFILE = r"f:\deepseek harness\.pw_profile"
OUT = r"f:\deepseek harness\CARSI下载"
URL = "https://iopscience.iop.org/article/10.1088/1748-9326/ad76c0/pdf"
TARGET = os.path.join(OUT, "14_Fong 2024 Winners and losers under climate change.pdf")


def valid_pdf(p):
    try:
        return os.path.exists(p) and os.path.getsize(p) > 10000 and open(p, "rb").read(5) == b"%PDF-"
    except Exception:
        return False


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
        accept_downloads=True, viewport={"width": 1360, "height": 900},
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def on_dl(dl):
        try:
            dl.save_as(TARGET)
            print("  [download] saved:", os.path.basename(TARGET))
        except Exception as e:
            print("  [download fail]", repr(e))

    def on_resp(resp):
        ct = (resp.headers.get("content-type") or "").lower()
        if "pdf" in ct or resp.url.lower().endswith(".pdf"):
            try:
                b = resp.body()
                if b[:5] == b"%PDF-":
                    with open(TARGET, "wb") as f:
                        f.write(b)
                    print("  [resp] saved:", os.path.basename(TARGET), len(b))
            except Exception:
                pass

    page.on("download", on_dl)
    page.on("response", on_resp)

    for attempt in range(3):
        if valid_pdf(TARGET):
            break
        print("attempt", attempt + 1)
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print("  goto err (retryable):", repr(e)[:100])
        for _ in range(80):
            if valid_pdf(TARGET):
                break
            page.wait_for_timeout(500)
        if valid_pdf(TARGET):
            print("  DONE")
            break

    print("final valid:", valid_pdf(TARGET))
    ctx.close()
