# -*- coding: utf-8 -*-
"""生成《海南大学知网下载清单_中文47篇.html》：每篇含知网检索直达链接 + 勾选记忆。"""
import csv, io, os, urllib.parse

CSV = r'F:\deepseek harness\文献传递申请清单.csv'
OUT = r'F:\deepseek harness\海南大学知网下载清单_中文47篇.html'

rows = []
with io.open(CSV, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['全文状态'] == '需文献传递':
            rows.append(r)

def cnki_url(title):
    return 'https://kns.cnki.net/kns8s/defaultresult/index?korder=SU&kw=' + urllib.parse.quote(title)

L = []
L.append('<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>海南大学知网下载清单（中文47篇）</title>')
L.append('<style>body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#222;line-height:1.7} h1{font-size:20px}')
L.append('.tip{background:#e6f4ff;border-left:4px solid #1677ff;padding:10px 14px;font-size:14px;border-radius:4px;margin-bottom:14px}')
L.append('.step{background:#f6ffed;border-left:4px solid #52c41a;padding:10px 14px;font-size:14px;border-radius:4px;margin-bottom:14px}')
L.append('table{width:100%;border-collapse:collapse;font-size:13px} th,td{border:1px solid #e1e4e8;padding:6px 8px;text-align:left;vertical-align:top}')
L.append('th{background:#f0f4f8} a{color:#1677ff;text-decoration:none} a:hover{text-decoration:underline} input{margin-right:6px}')
L.append('.done td{background:#f6ffed;color:#999} .cnt{font-size:12px;color:#666}</style></head><body>')
L.append('<h1>海南大学知网下载清单（中文 47 篇）</h1>')
L.append('<div class="step"><b>CARSI 登录步骤：</b>① 校园网外先打开 <a href="https://kns.cnki.net" target="_blank">知网 kns.cnki.net</a> → 右上角「机构登录」→ 选 <b>海南大学</b> → 统一身份认证（学号/工号）登录；② 点击下表「知网检索」链接 → 找到对应文献 → 点「下载/CAJ/PDF」；③ 抓完勾选（自动记忆，刷新不丢）。<br>若「机构登录」无海南大学，改用校园网或 WebVPN（webvpn.hainanu.edu.cn）访问知网。</div>')
L.append('<p class="cnt" id="cnt"></p>')
L.append('<table><tr><th style="width:52px">编号</th><th>题名</th><th>作者</th><th style="width:150px">期刊年卷期页</th><th style="width:90px">操作</th></tr>')
for r in rows:
    L.append('<tr id="r%s"><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><input type="checkbox" data-id="%s"><a href="%s" target="_blank">知网检索</a></td></tr>' % (
        r['编号'], r['编号'], r['题名'], r['作者'], r['期刊年卷期页'], r['编号'], cnki_url(r['题名'])))
L.append('</table>')
L.append('<script>var trs=document.querySelectorAll("tr[id]");trs.forEach(function(tr){var cb=tr.querySelector("input");var k="cnki_"+cb.dataset.id;if(localStorage.getItem(k)==="1"){cb.checked=true;tr.className="done";}cb.addEventListener("change",function(){if(cb.checked){localStorage.setItem(k,"1");tr.className="done";}else{localStorage.removeItem(k);tr.className="";}update();});});')
L.append('function update(){var done=document.querySelectorAll("tr.done").length;document.getElementById("cnt").textContent="已完成 "+done+" / 47 篇";}update();</script>')
L.append('</body></html>')

with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))
print('rows=%d' % len(rows))
