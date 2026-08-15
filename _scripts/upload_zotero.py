# -*- coding: utf-8 -*-
"""通过 Zotero Web API 批量上传 zotero_items.json 到用户库。
用法：py -3 upload_zotero.py <API_KEY> <USER_ID> [COLLECTION_NAME]
每次请求 ≤50 条，自动分批；先创建分类（Collection），再写入条目。
"""
import sys, io, json, time, urllib.request, urllib.error

ITEMS_FILE = r'F:\deepseek harness\zotero_items.json'
API = 'https://api.zotero.org'

def main():
    if len(sys.argv) < 3:
        print('用法: py -3 upload_zotero.py <API_KEY> <USER_ID> [COLLECTION_NAME]')
        sys.exit(1)
    key, user = sys.argv[1], sys.argv[2]
    coll_name = sys.argv[3] if len(sys.argv) > 3 else '近岸养殖政策271'

    with io.open(ITEMS_FILE, encoding='utf-8') as f:
        items = json.load(f)
    print('待上传条目: %d' % len(items))

    # 1) 建分类
    coll_key = None
    headers = {'Zotero-API-Key': key, 'Content-Type': 'application/json'}
    body = json.dumps([{'name': coll_name, 'parentCollection': False}]).encode('utf-8')
    try:
        req = urllib.request.Request(API + '/users/%s/collections' % user, data=body, headers=headers, method='POST')
        resp = urllib.request.urlopen(req, timeout=60)
        if resp.status in (200, 201):
            txt = resp.read().decode('utf-8', 'ignore')
            m = json.loads(txt) if txt.strip() else {}
            if isinstance(m, list) and m:
                coll_key = m[0].get('key')
                print('已创建分类: %s (key=%s)' % (coll_name, coll_key))
    except urllib.error.HTTPError as e:
        print('建分类失败 HTTP %s: %s' % (e.code, e.read().decode('utf-8', 'ignore')[:300]))
        sys.exit(1)
    if not coll_key:
        print('未获取到分类 key，尝试直接上传条目')

    # 2) 分批发条目（每批 50）
    BATCH = 50
    total_ok = 0
    for i in range(0, len(items), BATCH):
        batch = items[i:i+BATCH]
        payload = []
        for it in batch:
            entry = dict(it)
            entry.pop('notes', None)
            entry.pop('collections', None)
            entry['collections'] = [coll_key] if coll_key else []
            payload.append(entry)
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(API + '/users/%s/items' % user, data=data, headers=headers, method='POST')
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            txt = resp.read().decode('utf-8', 'ignore')
            results = json.loads(txt) if txt.strip() else []
            ok = sum(1 for r in results if r.get('successful'))
            total_ok += ok
            print('批 %d–%d: 成功 %d' % (i+1, min(i+BATCH, len(items)), ok))
        except urllib.error.HTTPError as e:
            print('批 %d 失败 HTTP %s: %s' % (i//BATCH+1, e.code, e.read().decode('utf-8', 'ignore')[:400]))
        time.sleep(1)

    print('完成：成功上传 %d / %d 条' % (total_ok, len(items)))
    print('提示：附件（PDF）请在 Zotero 客户端全选后右键「查找可用的 PDF」自动抓取。')

if __name__ == '__main__':
    main()
