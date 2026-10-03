import os, sys, re, random, datetime as dt, numpy as np, xarray as xr, boto3
from botocore import UNSIGNED
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor
from pyproj import Proj
SAT, YEAR, DAYS, HOURS = int(sys.argv[1]), 2024, [int(x) for x in sys.argv[2].split(",")], range(18, 24)
BANDS = [8, 10, 13, 15]; P, C, NL, NR = 128, 4, 12, 6
B = "noaa-goes%d" % SAT; s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED, max_pool_connections=64), region_name="us-east-1")
TMP = "tmp%d" % SAT; os.makedirs(TMP, exist_ok=True); OUT = "patches"; os.makedirs(OUT, exist_ok=True)
def keys(prefix):
    out, tok = [], None
    while True:
        kw = dict(Bucket=B, Prefix=prefix)
        if tok: kw["ContinuationToken"] = tok
        r = s3.list_objects_v2(**kw); out += [c["Key"] for c in r.get("Contents", [])]
        if not r.get("IsTruncated"): return out
        tok = r["NextContinuationToken"]
def get(k):
    f = os.path.join(TMP, k.split("/")[-1])
    if not os.path.exists(f): s3.download_file(B, k, f)
    return f
def stime(k): return dt.datetime.strptime(re.search(r"_s(\d{13})", k).group(1), "%Y%j%H%M%S")
def flashes(day):
    ks = [k for h in list(HOURS) + [HOURS[-1] + 1] for k in keys("GLM-L2-LCFA/%d/%03d/%02d/" % (YEAR, day, h % 24))]
    with ThreadPoolExecutor(48) as ex: fs = list(ex.map(get, ks))
    T, LA, LO = [], [], []
    for f in fs:
        try:
            d = xr.open_dataset(f)
            q = d.flash_quality_flag.values == 0
            T.append(d.flash_time_offset_of_first_event.values[q]); LA.append(d.flash_lat.values[q]); LO.append(d.flash_lon.values[q]); d.close()
        except Exception: pass
        os.remove(f)
    return np.concatenate(T), np.concatenate(LA), np.concatenate(LO)
def run(day):
    ft, fla, flo = flashes(day); rng = random.Random(SAT * 1000 + day)
    scans = {}
    for h in HOURS:
        for k in keys("ABI-L2-CMIPC/%d/%03d/%02d/" % (YEAR, day, h)):
            m = re.search(r"M6C(\d\d)_G", k)
            if m and int(m.group(1)) in BANDS: scans.setdefault(stime(k).replace(second=0, microsecond=0), {})[int(m.group(1))] = k
    times = sorted(t for t, v in scans.items() if len(v) == 4)
    X, Y, META = [], [], []
    for w in range(0, len(times) - 3, 3):
        ts = times[w:w + 4]
        if (ts[-1] - ts[0]).total_seconds() > 16 * 60: continue
        files = [[scans[t][b] for b in BANDS] for t in ts]
        with ThreadPoolExecutor(16) as ex: paths = list(ex.map(get, [k for row in files for k in row]))
        stack, real = [], []
        for i in range(4):
            imgs = []
            for j in range(4):
                d = xr.open_dataset(paths[i * 4 + j]); imgs.append(d.CMI.values.astype(np.float32))
                if i == 0 and j == 0:
                    pr = d.goes_imager_projection.attrs; x = d.x.values; y = d.y.values
                real.append(d.t.values); d.close()
            stack.append(np.stack(imgs))
        for p_ in paths: os.remove(p_)
        S = np.stack(stack); H = pr["perspective_point_height"]
        proj = Proj(proj="geos", h=H, lon_0=pr["longitude_of_projection_origin"], sweep="x", a=pr["semi_major_axis"], b=pr["semi_minor_axis"])
        t_img = [np.datetime64(real[i * 4 + 2]) for i in range(4)]
        sel = (ft >= t_img[0]) & (ft < t_img[3]); fx, fy = proj(flo[sel], fla[sel]); fx = np.asarray(fx) / H; fy = np.asarray(fy) / H
        col = np.floor((fx - x[0]) / (x[1] - x[0]) + 0.5).astype(int); row = np.floor((fy - y[0]) / (y[1] - y[0]) + 0.5).astype(int)
        nr, nc = S.shape[2] // C, S.shape[3] // C; G = np.zeros((3, nr, nc), np.int32); tt = ft[sel]
        ok = (row >= 0) & (row < nr * C) & (col >= 0) & (col < nc * C) & np.isfinite(fx)
        for k in range(3):
            m = ok & (tt >= t_img[k]) & (tt < t_img[k + 1]); np.add.at(G[k], (row[m] // C, col[m] // C), 1)
        act = np.argwhere(G.sum(0) > 0); taken = []; cands = []
        for _ in range(NL):
            if len(act) == 0: break
            r, c = act[rng.randrange(len(act))]; cands.append((r - 16 + rng.randint(-8, 8), c - 16 + rng.randint(-8, 8)))
        for _ in range(NR): cands.append((rng.randrange(0, nr - 32), rng.randrange(0, nc - 32)))
        for r0, c0 in cands:
            if r0 < 0 or c0 < 0 or r0 + 32 > nr or c0 + 32 > nc: continue
            if any(abs(r0 - a) < 32 and abs(c0 - b) < 32 for a, b in taken): continue
            xin = S[:, :, r0 * C:(r0 + 32) * C, c0 * C:(c0 + 32) * C]
            if not np.isfinite(xin).all(): continue
            taken.append((r0, c0)); X.append(xin.astype(np.float16)); Y.append(G[:, r0:r0 + 32, c0:c0 + 32].astype(np.uint16)); lon_c, lat_c = proj(float(x[(c0 + 16) * C]) * H, float(y[(r0 + 16) * C]) * H, inverse=True); META.append((day, w, r0, c0, float(lat_c), float(lon_c), float((t_img[3] - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s"))))
        print("sat %d day %d window %d patches so far %d flashes %d" % (SAT, day, w, len(X), int(sel.sum())), flush=True)
    np.savez_compressed(os.path.join(OUT, "g%d_d%03d.npz" % (SAT, day)), X=np.array(X), Y=np.array(Y), META=np.array(META))
for d in DAYS: run(d)
print("DONE", flush=True)
