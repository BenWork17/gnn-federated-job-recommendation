# -*- coding: utf-8 -*-
"""Kiểm tra zip có trùng với .tsv không + tài nguyên máy."""
import os, zipfile, hashlib, shutil

BASE = r"E:\2026\DUT\IOT\Cuoiki\NewData"
for f in ("apps.tsv", "users.tsv", "user_history.tsv", "jobs.tsv"):
    z = os.path.join(BASE, f + ".zip")
    t = os.path.join(BASE, f)
    if not os.path.exists(z):
        print(f, '- no zip')
        continue
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
        info = zf.getinfo(names[0])
        print('%-20s zip members=%s | uncompressed=%d | tsv=%d | same size=%s'
              % (f, names, info.file_size, os.path.getsize(t),
                 info.file_size == os.path.getsize(t)))

try:
    import psutil
    vm = psutil.virtual_memory()
    print('\nRAM: total %.1f GB | available %.1f GB' % (vm.total/2**30, vm.available/2**30))
    print('CPU: %d logical' % psutil.cpu_count(logical=True))
except Exception as e:
    print('\npsutil không có:', e)

d = shutil.disk_usage(BASE)
print('Disk E: total %.0f GB | free %.0f GB' % (d.total/2**30, d.free/2**30))
