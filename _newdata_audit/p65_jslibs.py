# -*- coding: utf-8 -*-
"""Kiem tra co tai duoc thu vien JS cho do thi 2D tuong tac khong."""
import urllib.request, os, json

UA = {'User-Agent': 'Mozilla/5.0'}
OUT = r"E:\2026\DUT\DSS\SauGK\CuoiKi\app\assets"

CANDIDATES = [
    ('force-graph 2D (vasturiano)',
     'https://unpkg.com/force-graph@1.45.0/dist/force-graph.min.js'),
    ('d3-force',
     'https://unpkg.com/d3-force@3.0.0/dist/d3-force.min.js'),
    ('d3 v7 (full)',
     'https://unpkg.com/d3@7.9.0/dist/d3.min.js'),
    ('cytoscape',
     'https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js'),
    ('vis-network',
     'https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js'),
]

os.makedirs(OUT, exist_ok=True)
for name, url in CANDIDATES:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r:
            data = r.read()
        print(f'  {name:32s} OK  {len(data)/1024:8.1f} KB')
    except Exception as e:
        print(f'  {name:32s} FAIL {type(e).__name__}: {str(e)[:80]}')
