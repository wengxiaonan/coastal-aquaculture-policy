# -*- coding: utf-8 -*-
import sys, os, base64
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

PROFILE = r"f:\deepseek harness\.pw_profile"
LANDING = "https://doi.org/10.1111/raq.12631"
PDF = "https://onlinelibrary.wiley.com/doi/pdf/10.1111/raq.12631"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
        accept_downloads=True, viewport={"width":1360,"height":900},
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    print("打开落地页...")
    page.goto(LANDING, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(12000)

    # 方案 A：浏览器内 fetch
    print("\n=== 方案A: page.evaluate(fetch) ===")
    js = """async (url) => {
      try {
        const r = await fetch(url, {credentials:'include', redirect:'follow'});
        const buf = await r.arrayBuffer();
        const bytes = new Uint8Array(buf);
        let bin=''; const chunk=0x8000;
        for (let i=0;i<bytes.length;i+=chunk){ bin += String.fromCharCode.apply(null, bytes.subarray(i,i+chunk)); }
        return {status:r.status, ct:(r.headers.get('content-type')||''), b64:btoa(bin)};
      } catch(e){ return {error:String(e)}; }
    }"""
    try:
        r = page.evaluate(js, PDF)
        if r and r.get("b64"):
            data = base64.b64decode(r["b64"])
            print("  status=", r["status"], "ct=", r["ct"], "bytes=", len(data), "magic=", data[:5])
        else:
            print("  结果:", r)
    except Exception as e:
        print("  fetch err:", repr(e))

    # 方案 B：导航到 PDF，监听响应
    print("\n=== 方案B: page.goto(PDF) + on_response ===")
    seen = []
    def on_resp(resp):
        ct = (resp.headers.get("content-type") or "").lower()
        seen.append((resp.status, ct, resp.url[:100]))
    page.on("response", on_resp)
    try:
        page.goto(PDF, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
    except Exception as e:
        print("  goto err:", repr(e))
    print("  响应列表:")
    for s in seen:
        print("   ", s)
    print("  当前 URL:", page.url)

    ctx.close()
