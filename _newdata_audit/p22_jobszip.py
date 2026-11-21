# -*- coding: utf-8 -*-
"""jobs.zip là 'jobs.zip' (không phải jobs.tsv.zip) - kiểm tra."""
import os, zipfile

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
z = os.path.join(BASE, 'jobs.zip')
t = os.path.join(BASE, 'jobs.tsv')
print('jobs.zip exists:', os.path.exists(z), '| jobs.tsv:', os.path.exists(t))
if os.path.exists(z):
    with zipfile.ZipFile(z) as zf:
        for info in zf.infolist():
            print('  member: %-24s uncompressed=%d  ratio=%.2f'
                  % (info.filename, info.file_size, info.compress_size/info.file_size if info.file_size else 0))
        names = zf.namelist()
        info = zf.getinfo(names[0])
        print('khớp kích thước jobs.tsv:', info.file_size == os.path.getsize(t))
