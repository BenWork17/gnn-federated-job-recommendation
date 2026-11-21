# -*- coding: utf-8 -*-
"""Kiểm tra Tianchi dataset 31623 lấy được metadata gì mà không cần đăng nhập."""
import urllib.request, json, re

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      'Accept': 'application/json, text/plain, */*',
      'Referer': 'https://tianchi.aliyun.com/dataset/31623'}

urls = [
    'https://tianchi.aliyun.com/api/dataSet/getDataSetDetail?dataSetId=31623',
    'https://tianchi.aliyun.com/api/dataset/getDataSetDetail?dataSetId=31623',
    'https://tianchi.aliyun.com/api/dataSet/getDataSetList?dataSetId=31623',
    'https://tianchi.aliyun.com/api/dataSet/getFileList?dataSetId=31623',
]
for u in urls:
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode('utf-8', 'replace')
            print('OK %-70s len=%d' % (u.rsplit('/', 1)[-1][:70], len(body)))
            print('   ', body[:600])
    except Exception as e:
        print('FAIL %-68s %s %s' % (u.rsplit('/', 1)[-1][:68], type(e).__name__, str(e)[:80]))
    print()
