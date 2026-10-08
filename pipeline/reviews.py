"""Florida signals from Google reviews written up to Sep 2021 (UCSD Google Local, review-Florida.json.gz)
-> data/fl/review_signals.parquet. Web leaderboard only: the app uses none of this.

For each Google listing: how many reviews mention a Cuban sandwich (or a Cuban/Latin coffee window: cafecito, colada, ventanita),
stone crab, a grouper sandwich, key lime pie, oysters or a raw bar, smoked fish dip or mullet, conch fritters, and the average star
rating of just those reviews. The file (5.3 GB) is streamed from UCSD, or read from data/ucsd/ if downloaded there; delete it after.
Adapted from ct-eats/pipeline/reviews.py.
"""
import os, re, gzip, json, time, collections, urllib.request
import pandas as pd
from common import FL

URL = "https://mcauleylab.ucsd.edu/public_datasets/gdrive/googlelocal/review-Florida.json.gz"
SIG = {
    "cuban": re.compile(r"\bcuban (?:sandwich|sandwiches|sandwhich|sanwich)\b|\bcubano\b|\bmedianoche\b|\bpan cubano\b|\bcuban bread\b"),
    "cafecito": re.compile(r"\bcafecito\b|\bcolada\b|\bcortadito\b|\bcafe con leche\b|\bcafé con leche\b|\bventanita\b|\bcuban coffee\b|\bpastelitos?\b|\bcroquetas?\b"),
    "stonecrab": re.compile(r"\bstone crabs?\b|\bstone crab claws?\b"),
    "grouper": re.compile(r"\bgrouper (?:sandwich|sandwiches|sandwhich|reuben|cheeks?)\b|\bfried grouper\b|\bblackened grouper\b|\bgrilled grouper\b|\bgrouper\b"),
    "keylime": re.compile(r"\bkey lime\b|\bkeylime\b"),
    "oyster": re.compile(r"\boysters?\b|\braw bar\b|\bapalachicola\b"),
    "fishdip": re.compile(r"\bfish dip\b|\bsmoked fish\b|\bsmoked mullet\b|\bmullet\b|\bfish spread\b"),
    "conch": re.compile(r"\bconch (?:fritters?|chowder|salad)\b|\bcracked conch\b"),
}
PRE = re.compile(r"cuban|cubano|medianoche|cafecito|colada|cortadito|con leche|ventanita|pastelito|croqueta|stone crab|grouper|key ?lime|oyster|raw bar|"
                 r"apalachicola|fish dip|smoked fish|mullet|fish spread|conch", re.I)

t = time.time()
cnt = collections.defaultdict(collections.Counter)
n = hit = 0
LOCAL = os.path.join(FL, "..", "ucsd", "review-Florida.json.gz")   # a resumable download (curl -C -) when streaming keeps breaking
GREP = ("cuban|cubano|medianoche|cafecito|colada|cortadito|con leche|ventanita|pastelito|croqueta|stone crab|grouper|key ?lime|oyster|"
        "raw bar|apalachicola|fish dip|smoked fish|mullet|fish spread|conch")
if os.path.exists(LOCAL):
    # gzip and grep do the 25 GB of decompressing and filtering in C; Python only parses the reviews that mention something
    import subprocess, shutil
    # ripgrep (shipped inside Claude Code's binary, run under the name "rg") is far faster than BSD grep -i; plain grep otherwise
    claude = os.environ.get("CLAUDE_CODE_EXECPATH") or os.path.expanduser("~/.local/bin/claude")
    if os.path.exists(claude):
        proc = subprocess.Popen(["rg", "-z", "-i", "--no-filename", "--no-line-number", "-e", GREP, LOCAL], executable=claude,
                                env={**os.environ, "ARGV0": "rg"}, stdout=subprocess.PIPE, text=True, bufsize=1 << 20)
    else:
        proc = subprocess.Popen(f"gzip -dc '{LOCAL}' | LC_ALL=C grep -i -E '{GREP}'", shell=True, stdout=subprocess.PIPE, text=True, bufsize=1 << 20)
    src = proc.stdout
else:
    src = gzip.open(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "fl-eats data pipeline (work-with-nick@gmail.com)"}), timeout=300), "rt")
with src as f:
    for line in f:
        n += 1
        if not PRE.search(line):
            continue
        d = json.loads(line)
        txt = (d.get("text") or "").lower()
        if not txt:
            continue
        g, rt = d.get("gmap_id"), d.get("rating")
        for k, rx in SIG.items():
            if rx.search(txt):
                c = cnt[g]; c[k] += 1
                if rt:
                    c[k + "_sum"] += rt
                hit += 1
        if n % 500_000 == 0:
            print(n, "matching reviews", round(time.time() - t), "s", flush=True)
rows = []
for g, c in cnt.items():
    row = {"gmap_id": g}
    for k in SIG:
        row["n_" + k] = c[k]
        row["r_" + k] = round(c[k + "_sum"] / c[k], 3) if c[k] else None
    rows.append(row)
pd.DataFrame(rows).to_parquet(os.path.join(FL, "review_signals.parquet"))
print("reviews read (pre-filtered):", n, "| mentions:", hit, "| listings with a mention:", len(rows), "|", round(time.time() - t), "s")
