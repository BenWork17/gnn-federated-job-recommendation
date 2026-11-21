import io, os, sys, time
base = r"E:\2026\DUT\IOT\Cuoiki\NewData"
files = ["apps.tsv","users.tsv","user_history.tsv","jobs.tsv"]
for f in files:
    p = os.path.join(base,f)
    size = os.path.getsize(p)
    # encoding check on first 4MB
    raw = open(p,'rb').read(4*1024*1024)
    try:
        raw.decode('utf-8'); enc='utf-8'
    except UnicodeDecodeError:
        enc='NOT-utf8'
    t=time.time(); n=0; last=b''
    with open(p,'rb') as fh:
        while True:
            b = fh.read(16*1024*1024)
            if not b: break
            n += b.count(b'\n')
            last = b[-1:]
    if last != b'\n':
        n += 1
    print(f"{f}: size={size/1e9:.3f} GB  lines={n:,}  enc={enc}  endsNL={last==b'\n'}  count_s={time.time()-t:.1f}", flush=True)
