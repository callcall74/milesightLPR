"""수신된 페이로드를 기준(첫 수신분)과 비교해 구조 차이를 출력

실행:  python compare.py [기준 파일] [비교 파일]   (.json 또는 _raw.bin, 생략 시 첫 json vs 최신 json)
"""
import glob
import json
import os
import sys

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "received")
SNAPSHOT_KEYS = ("license_plate_snapshot", "vehicle_snapshot", "full_snapshot")


def load(path):
    raw = open(path, "rb").read()
    try:
        return json.loads(raw.decode("utf-8")), raw
    except Exception:
        return None, raw


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def summarize(v, key):
    if key.split(".")[-1] in SNAPSHOT_KEYS and isinstance(v, str) and len(v) > 50:
        return f"<base64 {len(v)} chars>"
    return repr(v)


files = sorted(glob.glob(os.path.join(SAVE_DIR, "*.json")))
base_path = sys.argv[1] if len(sys.argv) > 1 else files[0]
new_path = sys.argv[2] if len(sys.argv) > 2 else files[-1]
base, _ = load(base_path)
new, new_raw = load(new_path)

print(f"기준: {os.path.basename(base_path)}")
print(f"비교: {os.path.basename(new_path)}  ({len(new_raw)} bytes)")
if new is None:
    print("[!] 비교 대상이 JSON이 아님. 앞부분:")
    print(new_raw[:1500])
    sys.exit()

b, n = flatten(base), flatten(new)
print(f"\n키 순서 동일: {list(b) == list(n)}")
for k in [k for k in b if k not in n]:
    print(f"  - 사라진 키: {k}")
for k in [k for k in n if k not in b]:
    print(f"  + 새 키    : {k} = {summarize(n[k], k)}")
print("\n공통 키 값/타입:")
for k in [k for k in n if k in b]:
    tb, tn = type(b[k]).__name__, type(n[k]).__name__
    mark = "  TYPE!" if tb != tn else ""
    print(f"  {k:28} {summarize(b[k], k):40} -> {summarize(n[k], k)}{mark}")
