# -*- coding: utf-8 -*-
"""Tìm bài OKRA / Zhaopin 人岗匹配 trên arXiv."""
import urllib.request, urllib.parse, re, sys

def arxiv(q, n=15):
    url = 'http://export.arxiv.org/api/query?' + urllib.parse.urlencode(
        {'search_query': q, 'max_results': n, 'sortBy': 'relevance'})
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        xml = r.read().decode('utf-8', 'replace')
    entries = re.findall(r'<entry>(.*?)</entry>', xml, re.S)
    out = []
    for e in entries:
        t = re.search(r'<title>(.*?)</title>', e, re.S)
        i = re.search(r'<id>(.*?)</id>', e, re.S)
        s = re.search(r'<summary>(.*?)</summary>', e, re.S)
        au = re.findall(r'<name>(.*?)</name>', e)
        out.append({
            'title': ' '.join(t.group(1).split()) if t else '',
            'id': i.group(1).strip() if i else '',
            'authors': au[:4],
            'summary': ' '.join(s.group(1).split()) if s else '',
        })
    return out

for q in ['ti:OKRA', 'all:"Zhaopin"', 'all:"job recommendation" AND all:"knowledge graph"']:
    print('=' * 90)
    print('QUERY:', q)
    try:
        for e in arxiv(q):
            print(' -', e['id'])
            print('   ', e['title'][:120])
            low = e['summary'].lower()
            if 'zhaopin' in low or 'tianchi' in low or 'okra' in low:
                print('    >>> MATCH summary:', e['summary'][:400])
    except Exception as ex:
        print('  FAIL', type(ex).__name__, str(ex)[:100])
