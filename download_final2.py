# -*- coding: utf-8 -*-
"""
最终下载 v3：清理垃圾 + 定向下载剩余 OA 论文（已确认直链 + escholarship 兜底）。
下载走 curl，写临时文件校验 %PDF 后再改名，避免覆盖好文件。
"""
import os, re, subprocess, json, glob

BASE = r"f:\deepseek harness"
OUT = os.path.join(BASE, "美国养殖政策_文献PDF")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def curl(url, referer=None):
    tmp = os.path.join(BASE, "_tmp.bin")
    cmd = ["curl", "-sL", "--max-time", "90", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9"]
    if referer: cmd += ["-e", referer]
    cmd += ["-o", tmp, url]
    subprocess.run(cmd, capture_output=True)
    if os.path.exists(tmp):
        with open(tmp, "rb") as f: d = f.read()
        os.remove(tmp)
        return d
    return b""

def is_pdf(d): return b"%PDF" in (d[:2048] if d else b"")

def sanitize(n): return re.sub(r'[\\/:*?"<>|]', '_', n).strip()

# ---------- 1. 清理垃圾文件 ----------
for f in glob.glob(os.path.join(OUT, "*.pdf")):
    with open(f, "rb") as fh: head = fh.read(2048)
    if b"%PDF" not in head:
        os.remove(f)
        print("删除垃圾:", os.path.basename(f))

# 去重 #07（两份同名有效文件）
seen07 = [f for f in glob.glob(os.path.join(OUT, "07_*.pdf"))]
for f in seen07[1:]:
    os.remove(f)

# ---------- 2. 定向下载 ----------
# 标题短名（用于文件命名）
TITLES = {
    1: "Lester 2022 Diverse state-level marine aquaculture policy",
    2: "Froehlich 2022 Piecing together the data of the US marine aquaculture puzzle",
    6: "Fong 2024 The structure and function of a state aquaculture plan",
    9: "Engle 2025 National Regulatory Cost Burden on US aquaculture farms",
    10: "Belle Rubino 2023 Refuting marine aquaculture myths",
    14: "Fong 2024 Winners and losers in US marine aquaculture under climate change",
    17: "Johnson 2019 Social-ecological system framework for marine aquaculture",
    21: "Klinger 2017 Growth of finfish in open-ocean aquaculture under climate change",
    22: "Froehlich 2022 Emerging trends climate change threats adaptation aquaculture",
    25: "Fong 2024 Conflict and alignment on aquaculture among Californian communities",
    29: "Marriott 2024 Socio-environmental suitability social license offshore aquaculture",
    30: "Mather Fanning 2019 Social licence and aquaculture research agenda",
    31: "Fairbanks 2016 Moving mussels offshore New England",
    33: "Working the ground game Maine shellfish seaweed social license",
    35: "Bell 2022 Bivalve shellfish aquaculture NERRs",
    36: "Garlock 2024 Aquaculture performance indicators",
}

CANDIDATES = {
    2: ["https://scholarworks.sjsu.edu/cgi/viewcontent.cgi?article=4287&context=faculty_rsca"],
    6: ["https://scholarworks.sjsu.edu/cgi/viewcontent.cgi?article=6625&context=faculty_rsca"],
    10: ["https://www.tandfonline.com/doi/pdf/10.1080/23308249.2021.1980767"],
    35: ["https://www.tandfonline.com/doi/pdf/10.1080/08920753.2022.2082857"],
    21: ["https://europepmc.org/articles/PMC5647286?pdf=render"],
    14: ["https://iopscience.iop.org/article/10.1088/1748-9326/ad76c0/pdf",
         "https://iopscience.iop.org/article/10.1088/1748-9326/ad76c0"],
    17: ["https://mdpi-res.com/d_attachment/sustainability/sustainability-11-02522/article_deploy/sustainability-11-02522.pdf",
         "https://www.mdpi.com/2071-1050/11/9/2522/pdf?version=1557919696"],
    36: ["https://www.nature.com/articles/s41467-024-50360-7.pdf",
         "https://www.nature.com/articles/s41467-024-49568-2.pdf"],
}

def escholarship_search(query):
    """在 escholarship 检索，返回候选 PDF 直链列表"""
    q = query.replace(" ", "+")
    html = curl("https://escholarship.org/search/?q=%s" % q)
    if not html: return []
    text = html.decode("utf-8", "ignore")
    ids = set(re.findall(r'/uc/item/([0-9a-z]{8})', text))
    return ["https://escholarship.org/content/qt%s/qt%s.pdf" % (i, i) for i in ids]

ESCH = {
    1: "Diverse state-level marine aquaculture policy United States",
    22: "Emerging trends in science and news of climate change threats aquaculture",
    25: "Conflict and alignment on aquaculture among Californian communities",
    29: "Assessing socio-environmental suitability and social license offshore aquaculture Florida",
}

results = {}
for num, urls in CANDIDATES.items():
    fname = "%02d_%s.pdf" % (num, sanitize(TITLES[num]))
    fpath = os.path.join(OUT, fname)
    ok = False
    for u in urls:
        d = curl(u, referer=None)
        if is_pdf(d):
            with open(fpath, "wb") as f: f.write(d)
            results[num] = "OK %d bytes" % len(d)
            ok = True
            break
    if not ok:
        results[num] = "FAIL " + ",".join(urls)

for num, query in ESCH.items():
    fname = "%02d_%s.pdf" % (num, sanitize(TITLES[num]))
    fpath = os.path.join(OUT, fname)
    ok = False
    for u in escholarship_search(query):
        d = curl(u)
        if is_pdf(d):
            with open(fpath, "wb") as f: f.write(d)
            results[num] = "OK(eschol) %d bytes" % len(d)
            ok = True
            break
    if not ok:
        results[num] = "FAIL(eschol no match)"

print("\n=== 下载结果 ===")
for num in sorted(results):
    print("#%02d %s" % (num, results[num]))

# 最终清单
print("\n=== 目录有效 PDF ===")
for f in sorted(glob.glob(os.path.join(OUT, "*.pdf"))):
    sz = os.path.getsize(f)
    with open(f, "rb") as fh:
        if b"%PDF" in fh.read(2048):
            print("%7d  %s" % (sz, os.path.basename(f)[:60]))
