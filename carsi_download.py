# -*- coding: utf-8 -*-
"""
海南大学 CARSI 半自动论文下载脚本（Playwright）

原理：
  - 开放获取论文：直接用 Unpaywall 查到的「PDF 直链」导航过去，
    浏览器内置 PDF 查看器会抓取真正的 PDF，脚本通过 response 事件自动保存。
  - 付费墙论文：打开落地页，脚本停下来等你在浏览器里完成机构登录
    （Access through your institution -> Hainan University），按回车继续。

用法：
  py -3.13 carsi_download.py            # 全部
  py -3.13 carsi_download.py 13 18 27   # 只处理指定编号
"""

import os
import re
import sys
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = r"f:\deepseek harness"
OUT = os.path.join(BASE, "CARSI下载")
PROFILE = os.path.join(BASE, ".pw_profile")
LOGFILE = os.path.join(BASE, "carsi_run.log")
os.makedirs(OUT, exist_ok=True)

# 论文清单：num, title, url(落地页), pdf(OA 直链, 可为 None), publisher, login
PAPERS = [
    # ---- 开放获取（有 PDF 直链）----
    {"num": 1,  "title": "Lester 2022 Diverse state-level marine aquaculture policy",
     "url": "https://doi.org/10.1111/raq.12631",
     "pdf": "https://repository.library.noaa.gov/view/noaa/62315/noaa_62315_DS1.pdf",
     "publisher": "NOAA(OA)", "login": False},
    {"num": 2,  "title": "Froehlich 2022 Piecing together the data",
     "url": "https://doi.org/10.1016/j.jenvman.2022.114623",
     "pdf": "https://www.sciencedirect.com/science/article/pii/S0301479722001967/pdf",
     "publisher": "Elsevier(OA)", "login": False},
    {"num": 6,  "title": "Fong 2024 Structure and function of a state aquaculture plan",
     "url": "https://doi.org/10.1016/j.aquaculture.2024.741164",
     "pdf": "https://www.sciencedirect.com/science/article/pii/S0044848624006252/pdf",
     "publisher": "Elsevier(OA)", "login": False},
    {"num": 9,  "title": "Engle 2025 National Regulatory Cost Burden",
     "url": "https://doi.org/10.1111/jwas.70005",
     "pdf": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/jwas.70005",
     "publisher": "Wiley(OA)", "login": False},
    {"num": 14, "title": "Fong 2024 Winners and losers under climate change",
     "url": "https://doi.org/10.1088/1748-9326/ad76c0",
     "pdf": "https://iopscience.iop.org/article/10.1088/1748-9326/ad76c0/pdf",
     "publisher": "IOP(OA)", "login": False},
    {"num": 22, "title": "Froehlich 2022 Emerging trends climate change aquaculture",
     "url": "https://doi.org/10.1016/j.aquaculture.2021.737812",
     "pdf": "https://www.sciencedirect.com/science/article/pii/S0044848621014757/pdf",
     "publisher": "Elsevier(OA)", "login": False},
    {"num": 29, "title": "Marriott 2024 Florida social license",
     "url": "https://doi.org/10.1111/jwas.13031",
     "pdf": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/jwas.13031",
     "publisher": "Wiley(OA)", "login": False},
    {"num": 30, "title": "Mather Fanning 2019 Social licence research agenda",
     "url": "https://doi.org/10.1016/j.marpol.2018.10.049",
     "pdf": "https://www.sciencedirect.com/science/article/pii/S0308597X18304603/pdf",
     "publisher": "Elsevier(OA)", "login": False},
    {"num": 31, "title": "Fairbanks 2016 Moving mussels offshore",
     "url": "https://doi.org/10.1016/j.ocecoaman.2016.05.004",
     "pdf": "https://www.sciencedirect.com/science/article/am/pii/S0964569116300941?via%3Dihub",
     "publisher": "Elsevier(OA)", "login": False},
    # ---- 开放获取（无直链，落地页兜底）----
    {"num": 25, "title": "Fong 2024 Conflict and alignment Californian communities",
     "url": "https://doi.org/10.1016/j.aquaculture.2023.740230",
     "pdf": "https://www.sciencedirect.com/science/article/pii/S0044848623010049/pdf",
     "publisher": "Elsevier(OA)", "login": False},
    {"num": 33, "title": "Working the ground game Maine social license",
     "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4783738",
     "pdf": None, "publisher": "SSRN", "login": False},
    # ---- 付费墙（需 CARSI 登录）----
    {"num": 13, "title": "Ruff Lester 2024 Leaving seafood on the table",
     "url": "https://www.sciencedirect.com/science/article/abs/pii/S0308597X2400280X",
     "pdf": None, "publisher": "Elsevier", "login": True},
    {"num": 18, "title": "Lester 2024 Role of marine aquaculture US seafood",
     "url": "https://www.sciencedirect.com/science/article/abs/pii/S0308597X23005274",
     "pdf": None, "publisher": "Elsevier", "login": True},
    {"num": 27, "title": "Murray D'Anna 2015 Seeing shellfish from the seashore",
     "url": "https://doi.org/10.1016/j.marpol.2015.09.005",
     "pdf": None, "publisher": "Elsevier", "login": True},
    {"num": 28, "title": "Suryanata Umemoto 2005 Beyond environmental impact",
     "url": "https://doi.org/10.1016/j.geoforum.2004.11.007",
     "pdf": None, "publisher": "Elsevier", "login": True},
    {"num": 15, "title": "Gentry 2017 Mapping global potential",
     "url": "https://doi.org/10.1038/s41559-017-0257-9",
     "pdf": None, "publisher": "Nature", "login": True},
    {"num": 19, "title": "Froehlich 2018 Global change production potential",
     "url": "https://doi.org/10.1038/s41559-018-0669-1",
     "pdf": None, "publisher": "Nature", "login": True},
    {"num": 3,  "title": "Knapp Rubino 2016 Political economics",
     "url": "https://doi.org/10.1080/23308249.2015.1121202",
     "pdf": None, "publisher": "Taylor & Francis", "login": True},
    {"num": 5,  "title": "Rubino 2023 Policy considerations",
     "url": "https://doi.org/10.1080/23308249.2022.2083452",
     "pdf": None, "publisher": "Taylor & Francis", "login": True},
    {"num": 32, "title": "Murray 2025 Framing conflict Maine",
     "url": "https://doi.org/10.1080/08941920.2025.2524745",
     "pdf": None, "publisher": "Taylor & Francis", "login": True},
    {"num": 4,  "title": "Fairbanks 2019 Policy mobilities",
     "url": "https://doi.org/10.1177/0263774X18809708",
     "pdf": None, "publisher": "SAGE", "login": True},
    {"num": 8,  "title": "Anderson 2002 Why fisheries economists should care",
     "url": "https://doi.org/10.1086/mre.17.2.42629357",
     "pdf": None, "publisher": "UChicago", "login": True},
    {"num": 24, "title": "Clements Chopin 2017 Ocean acidification",
     "url": "https://doi.org/10.1111/raq.12140",
     "pdf": None, "publisher": "Wiley", "login": True},
]


def log(msg):
    line = str(msg)
    try:
        print(line)
    except Exception:
        pass
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def sanitize(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def save_path(num, title):
    return os.path.join(OUT, "%02d_%s.pdf" % (num, sanitize(title[:60])))


def valid_pdf(path):
    try:
        if not os.path.exists(path):
            return False
        if os.path.getsize(path) < 10000:
            return False
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except Exception:
        return False


CURRENT_SAVE = None


def wait_for_save(target, timeout_s=30):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if valid_pdf(target):
            return True
        time.sleep(0.5)
    return valid_pdf(target)


def _abs(page_url, href):
    if not href:
        return ""
    return urljoin(page_url, href)


def _same_root(a, b):
    try:
        ra = ".".join(urlparse(a).netloc.lower().split(".")[-2:])
        rb = ".".join(urlparse(b).netloc.lower().split(".")[-2:])
        return ra == rb
    except Exception:
        return False


def find_pdf_url(page):
    """在落地页上寻找真正的 PDF 直链（同域优先，排除 epdf / 补充材料 / 参考文献外链）。"""
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
            for i in range(loc.count()):
                a = _abs(page_url, loc.nth(i).get_attribute("href"))
                if not a.lower().startswith(("http://", "https://")):
                    continue
                if re.search(r'/epdf|downloadSupplement|supp-|\.docx|\.xlsx', a, re.I):
                    continue
                if _same_root(a, page_url):
                    return a
        except Exception:
            continue
    try:
        loc = page.locator("a[href$='.pdf']")
        for i in range(loc.count()):
            a = _abs(page_url, loc.nth(i).get_attribute("href"))
            if _same_root(a, page_url):
                return a
    except Exception:
        pass
    return None


def try_auto_download(page, ctx, target):
    """在落地页上找 PDF 直链并抓取；成功返回 True。"""
    if valid_pdf(target):
        return True

    pdf_url = None
    for _ in range(40):
        pdf_url = find_pdf_url(page)
        if pdf_url:
            break
        page.wait_for_timeout(500)

    if pdf_url:
        log("    找到 PDF 直链: " + pdf_url)
        try:
            page.goto(pdf_url, wait_until="domcontentloaded", timeout=60000)
            if wait_for_save(target, timeout_s=25):
                return True
        except Exception as e:
            log("    直链导航失败: %r" % e)

    for txt in ["Download This Paper", "Download Paper", "Download PDF",
                "Download Pdf", "View PDF", "Full text PDF", "PDF"]:
        for role in ["link", "button"]:
            try:
                loc = page.get_by_role(role, name=re.compile(re.escape(txt), re.I)).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click(timeout=6000)
                    if wait_for_save(target, timeout_s=15):
                        return True
            except Exception:
                continue

    return valid_pdf(target)


def wait_login_and_download(page, ctx, target, landing_url, timeout_s=240):
    """付费墙：等待用户在浏览器完成机构登录并下载，脚本纯轮询检测 PDF（不导航、不打断登录）。"""
    log("  → 需机构登录。请在浏览器完成：机构登录 → 若停在摘要页按 F5 刷新 → 点 View PDF。脚本自动检测保存（最多等 %d 秒）" % timeout_s)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if valid_pdf(target):
            return True
        pdf_url = find_pdf_url(page)
        if pdf_url:
            log("    找到直链: " + pdf_url)
            try:
                page.goto(pdf_url, wait_until="domcontentloaded", timeout=60000)
                if wait_for_save(target, timeout_s=20):
                    return True
            except Exception:
                pass
        for txt in ["Download PDF", "Download Pdf", "View PDF", "Full text PDF", "PDF"]:
            for role in ["link", "button"]:
                try:
                    loc = page.get_by_role(role, name=re.compile(re.escape(txt), re.I)).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click(timeout=6000)
                        if wait_for_save(target, timeout_s=8):
                            return True
                except Exception:
                    continue
        page.wait_for_timeout(3000)
    return valid_pdf(target)


def main():
    global CURRENT_SAVE
    only = set(int(x) for x in sys.argv[1:] if x.isdigit())

    with open(LOGFILE, "w", encoding="utf-8") as f:
        f.write("=== CARSI 下载日志 ===\n")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE,
            headless=False,
            accept_downloads=True,
            viewport={"width": 1360, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )

        def on_download(dl):
            try:
                dl.save_as(CURRENT_SAVE)
                log("    [下载] 已保存: " + os.path.basename(CURRENT_SAVE))
            except Exception as e:
                log("    [下载失败] %r" % e)

        def on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                if "pdf" in ct or resp.url.lower().endswith(".pdf"):
                    body = resp.body()
                    if body[:5] == b"%PDF-":
                        with open(CURRENT_SAVE, "wb") as f:
                            f.write(body)
                        log("    [响应] 已保存: " + os.path.basename(CURRENT_SAVE))
            except Exception:
                pass

        def bind_page(pg):
            pg.on("download", on_download)
            pg.on("response", on_response)

        ctx.on("page", bind_page)
        for pg in ctx.pages:
            bind_page(pg)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        todo = [x for x in PAPERS if (not only or x["num"] in only)]
        log("待处理 %d 篇，保存到: %s" % (len(todo), OUT))

        for paper in todo:
            num, title, url = paper["num"], paper["title"], paper["url"]
            direct = paper.get("pdf")
            CURRENT_SAVE = save_path(num, title)
            if valid_pdf(CURRENT_SAVE):
                log("[跳过] #%02d 已存在" % num)
                continue

            log("")
            log("[处理] #%02d  %s" % (num, title))
            done = False

            # 1) OA 直链
            if direct:
                log("  [直链] " + direct)
                try:
                    page.goto(direct, wait_until="domcontentloaded", timeout=60000)
                    if wait_for_save(CURRENT_SAVE, timeout_s=30):
                        done = True
                except Exception as e:
                    log("  直链导航失败: %r" % e)

            # 2) 落地页兜底
            if not done:
                log("  [落地页] " + url)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    log("  ! 打开页面失败: %r" % e)
                if try_auto_download(page, ctx, CURRENT_SAVE):
                    done = True

            # 3) 手动登录（自动等待 + 检测）
            if not done:
                if wait_login_and_download(page, ctx, CURRENT_SAVE, url):
                    done = True

            log("  ✓ 完成 #%02d" % num if done else "  ✗ 跳过 #%02d（未完成）" % num)

        log("")
        log("全部处理结束。PDF 目录: " + OUT)
        ctx.close()


if __name__ == "__main__":
    main()
