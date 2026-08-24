"""
TTC Bus Delays — download, clean, and summarise.

This is the whole pipeline. One file, top to bottom, no hidden pieces:

    1. ask the City of Toronto's open-data catalogue what delay files exist
    2. download them
    3. clean them into one consistent table
    4. answer three questions: how much, why, and where
    5. write data.json, which index.html reads

Usage:
    python analyze.py                 # everything from 2014 on (slow, ~15 min)
    python analyze.py --since 2023    # just recent years (fast, start here)
    python analyze.py --selftest      # check the cleaning logic, no download

Every function below is short enough to read in one sitting. If you change one
thing, change a threshold in the CONFIG block and re-run.
"""

import argparse
import io
import json
import re
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# CONFIG — the only numbers you might want to change
# ---------------------------------------------------------------------------
DATASET = "ttc-bus-delay-data"
CKAN = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"

TOP_N = 15          # how many causes / locations / routes to chart
MIN_DELAY = 1       # ignore logged events with no actual delay
MAX_DELAY = 600     # minutes; anything longer is a data-entry error, not a bus

OUTPUT = "data.json"
USER_AGENT = "ttc-bus-delays (student open-data project)"


# ---------------------------------------------------------------------------
# STEP 1 — find the files
# ---------------------------------------------------------------------------
def list_files(since_year=None):
    """
    Ask the open-data catalogue which files belong to the bus delay dataset.

    We don't hardcode the URLs because the City adds a new file every year;
    asking the catalogue means this keeps working without edits.
    """
    r = requests.get(f"{CKAN}/package_show", params={"id": DATASET},
                     headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    resources = r.json()["result"]["resources"]

    delay_files, code_file = [], None
    for res in resources:
        name = res.get("name") or ""
        fmt = (res.get("format") or "").upper()

        # The lookup table that turns codes like "MFDV" into readable text.
        # Prefer the CSV: it opens without an Excel engine.
        if "code" in name.lower() and fmt == "CSV":
            code_file = res["url"]
            continue

        if fmt not in ("XLSX", "CSV") or "readme" in name.lower():
            continue

        # Skip old years if asked. Filenames contain the year they cover.
        if since_year:
            years = [int(y) for y in re.findall(r"(20\d\d)", name)]
            if years and max(years) < since_year:
                continue

        delay_files.append((name, res["url"], fmt))

    # A few resources duplicate the same data in different formats. Keep one
    # per name so we don't count the same delays twice.
    seen, unique = set(), []
    for name, url, fmt in delay_files:
        key = re.sub(r"\.(xlsx|csv|xml|json)$", "", name, flags=re.I).strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append((name, url, fmt))

    return unique, code_file


def download(url, fmt):
    """Download one file and hand back a DataFrame."""
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
    r.raise_for_status()
    buf = io.BytesIO(r.content)
    return pd.read_excel(buf) if fmt == "XLSX" else pd.read_csv(buf, encoding_errors="replace")


# ---------------------------------------------------------------------------
# STEP 2 — clean
# ---------------------------------------------------------------------------
# The same column means different things in different years, so every header is
# lowercased and looked up here. Unknown columns are simply ignored.
COLUMNS = {
    "date": "date", "report date": "date",
    "route": "route",
    "time": "time",
    "day": "day",
    "location": "location",
    "incident": "cause", "code": "cause",
    "min delay": "delay", "delay": "delay",
    "direction": "direction", "bound": "direction",
    "vehicle": "vehicle",
}

# Words that describe the *type* of street, not which street it is. Removing
# them makes "JANE ST" and "JANE" the same place.
STREET_WORDS = r"\b(AVE|AVENUE|ST|STREET|RD|ROAD|BLVD|BOULEVARD|DR|DRIVE|CRES|CRESCENT|PKWY|PARKWAY|TERR|TERRACE|GDNS|GARDENS|SQ|SQUARE|PL|PLACE|CRT|COURT|LN|LANE)\b"


def normalize_location(raw):
    """
    Collapse the many spellings of one intersection into a single label.

    This matters more than it looks. The raw data spells the same corner as
    "JANE AND FINCH", "Jane & Finch", "FINCH AVE AT JANE ST" and
    "JANE ST. / FINCH AVE." — four rows that are really one place. Left alone,
    the busiest intersection in the city gets split four ways and never shows
    up in a ranking.

    The fix has three parts:
      1. upper-case and strip punctuation, so casing and dots stop mattering
      2. drop street-type words (ST, AVE, RD...), so "JANE ST" == "JANE"
      3. sort the two street names alphabetically, so "JANE & FINCH" and
         "FINCH & JANE" become the same key

    Step 3 is the one people miss.
    """
    s = str(raw).upper().strip()
    if not s or s in ("NAN", "NONE"):
        return None

    s = re.sub(r"[.,'\"]", " ", s)                  # punctuation
    s = re.sub(r"\s+(AND|AT)\s+|[&/]", " & ", s)    # every join word -> " & "
    s = re.sub(STREET_WORDS, " ", s)                # street-type words
    s = re.sub(r"\s+", " ", s).strip(" &")          # tidy whitespace

    parts = [p.strip() for p in s.split("&") if p.strip()]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return " & ".join(sorted(parts))                # order-independent key


def clean(df, source):
    """Turn one downloaded file into the shape every other file uses."""
    renamed = {}
    for col in df.columns:
        key = re.sub(r"\s+", " ", str(col)).strip().lower()
        if key in COLUMNS:
            renamed[col] = COLUMNS[key]
    df = df.rename(columns=renamed)

    for needed in ("date", "route", "time", "location", "cause", "delay"):
        if needed not in df.columns:
            df[needed] = None
    df = df[["date", "route", "time", "location", "cause", "delay"]].copy()

    # Dates come as real dates in some files and as "13/04/2019" strings in
    # others. format="mixed" resolves each value on its own instead of forcing
    # one guess on the whole column and mangling half of it.
    df["date"] = pd.to_datetime(df["date"], errors="coerce", format="mixed")

    # Times are sometimes "07:35" and sometimes unparseable text. Bad ones
    # become NaN and get left out of the hourly chart. If we let them default
    # to zero we'd invent a huge fake spike at midnight.
    df["hour"] = pd.to_datetime(df["time"].astype(str), errors="coerce",
                                format="mixed").dt.hour

    df["delay"] = pd.to_numeric(df["delay"], errors="coerce")
    df["route"] = df["route"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["cause"] = df["cause"].astype(str).str.strip()
    df["location_clean"] = df["location"].map(normalize_location)
    df["source"] = source

    before = len(df)
    df = df[df["date"].notna()]
    # Keep only rows that describe a real delay of a believable length. A
    # 0-minute row is a logged event with no service impact; a 900-minute bus
    # delay is somebody typing in the wrong box.
    df = df[df["delay"].between(MIN_DELAY, MAX_DELAY)]
    dropped = before - len(df)
    return df, dropped


# ---------------------------------------------------------------------------
# STEP 3 — summarise
# ---------------------------------------------------------------------------
def top_table(df, column, n=TOP_N):
    """Group by one column, rank by total delay time, keep the top n."""
    out = (df.groupby(column)
             .agg(incidents=("delay", "size"), minutes=("delay", "sum"),
                  average=("delay", "mean"))
             .reset_index()
             .sort_values("minutes", ascending=False)
             .head(n))
    out["hours"] = (out["minutes"] / 60).round(0)
    out["average"] = out["average"].round(1)
    return out.rename(columns={column: "label"})[
        ["label", "incidents", "hours", "average"]].to_dict("records")


def summarise(df):
    """Everything index.html needs, in one dictionary."""
    df = df.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["dow"] = df["date"].dt.dayofweek

    by_hour = (df[df["hour"].notna()].groupby(df["hour"].astype("Int64"))
                 .agg(incidents=("delay", "size"), minutes=("delay", "sum"))
                 .reindex(range(24)).reset_index())
    by_hour.columns = ["hour", "incidents", "minutes"]

    by_dow = (df.groupby("dow").agg(incidents=("delay", "size"),
                                    minutes=("delay", "sum")).reset_index())
    by_month = (df.groupby("month").agg(incidents=("delay", "size"),
                                        minutes=("delay", "sum"))
                  .reset_index().sort_values("month"))

    def clean_records(frame):
        return json.loads(frame.fillna(0).to_json(orient="records"))

    return {
        "meta": {
            "incidents": int(len(df)),
            "total_hours": round(float(df["delay"].sum()) / 60, 1),
            "average_minutes": round(float(df["delay"].mean()), 1),
            "median_minutes": round(float(df["delay"].median()), 1),
            "first_date": df["date"].min().strftime("%Y-%m-%d"),
            "last_date": df["date"].max().strftime("%Y-%m-%d"),
            "locations_named": int(df["location_clean"].nunique()),
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "causes": top_table(df[df["cause"] != ""], "cause"),
        "locations": top_table(df[df["location_clean"].notna()], "location_clean"),
        "routes": top_table(df[df["route"].notna() & (df["route"] != "")], "route"),
        "by_hour": clean_records(by_hour),
        "by_dow": clean_records(by_dow),
        "by_month": clean_records(by_month),
    }


# ---------------------------------------------------------------------------
# STEP 4 — say what we found, in words
# ---------------------------------------------------------------------------
def print_findings(s):
    """
    Print the answers in plain English.

    This exists so the analysis has a conclusion, not just charts. Read what it
    prints and put the interesting parts on the page.
    """
    m = s["meta"]
    print("\n" + "=" * 64)
    print(f"{m['incidents']:,} bus delays, {m['first_date']} to {m['last_date']}")
    print(f"{m['total_hours']:,.0f} hours of service lost "
          f"(average {m['average_minutes']} min, median {m['median_minutes']} min)")
    print("=" * 64)

    print("\nWHY — the five causes that cost the most time")
    for row in s["causes"][:5]:
        share = 100 * row["hours"] / max(1, m["total_hours"])
        print(f"  {row['label'][:38]:<38} {row['hours']:>7,.0f} h  "
              f"({share:4.1f}% of all lost time, {row['incidents']:,} times, "
              f"avg {row['average']} min)")

    print("\nWHERE — the five locations with the most lost time")
    for row in s["locations"][:5]:
        print(f"  {row['label'][:38]:<38} {row['hours']:>7,.0f} h  "
              f"({row['incidents']:,} delays, avg {row['average']} min)")

    print("\nWHICH ROUTES lose the most time")
    for row in s["routes"][:5]:
        print(f"  Route {row['label']:<33} {row['hours']:>7,.0f} h  "
              f"({row['incidents']:,} delays)")

    worst_hour = max(s["by_hour"], key=lambda r: r["minutes"])
    print(f"\nWHEN — worst hour of the day: {int(worst_hour['hour']):02d}:00 "
          f"({worst_hour['incidents']:,} delays)")
    print()


# ---------------------------------------------------------------------------
# Self-test — proves the cleaning works, without downloading anything
# ---------------------------------------------------------------------------
def selftest():
    print("running self-test (no download)...\n")

    # The location cleaner is the part most likely to break quietly.
    cases = [
        ("JANE AND FINCH", "FINCH & JANE"),
        ("Jane & Finch", "FINCH & JANE"),
        ("FINCH AVE AT JANE ST", "FINCH & JANE"),
        ("jane st. / finch ave.", "FINCH & JANE"),
        ("YONGE AND BLOOR", "BLOOR & YONGE"),
        ("BLOOR ST W AND YONGE ST", "BLOOR W & YONGE"),
        ("KIPLING STATION", "KIPLING STATION"),
        ("", None),
        ("nan", None),
    ]
    for raw, expected in cases:
        got = normalize_location(raw)
        assert got == expected, f"normalize_location({raw!r}) -> {got!r}, expected {expected!r}"
        print(f"  ok  {raw!r:<28} -> {got!r}")

    # All four spellings must collapse into ONE row, not four.
    variants = ["JANE AND FINCH", "Jane & Finch", "FINCH AVE AT JANE ST", "jane st. / finch ave."]
    assert len({normalize_location(v) for v in variants}) == 1
    print("\n  ok  four spellings of one intersection collapse to a single label")

    # The cleaner must drop bad rows and keep good ones.
    raw = pd.DataFrame({
        "Report Date": ["2024-01-05", "06/01/2024", "not a date", "2024-01-07", "2024-01-08"],
        "Route": [29, 32, 35, 36, 39],
        "Time": ["08:15", "17:40", "09:00", "bad time", "12:00"],
        "Location": ["JANE AND FINCH", "Finch Ave at Jane St", "X", "KEELE STATION", "Y"],
        "Incident": ["Mechanical", "Diversion", "Mechanical", "Security", "Mechanical"],
        "Min Delay": [12, 45, 20, 8, 0],          # last row: 0 = no real delay
        "Extra Column": ["ignore", "me", "please", "ok", "sure"],
    })
    out, dropped = clean(raw, "test")
    assert dropped == 2, f"expected 2 dropped rows (bad date + zero delay), got {dropped}"
    assert len(out) == 3
    assert out["location_clean"].iloc[0] == out["location_clean"].iloc[1] == "FINCH & JANE"
    assert "Extra Column" not in out.columns
    assert out["hour"].isna().sum() == 1        # "bad time" -> NaN, not midnight
    print("  ok  cleaner drops bad dates and zero-minute rows, keeps the rest")
    print("  ok  unparseable times become blank instead of a fake midnight spike")
    print("  ok  both spellings of Jane & Finch merged into one location")

    summary = summarise(out)
    assert summary["meta"]["incidents"] == 3
    assert summary["causes"][0]["label"] == "Diversion"     # 45 min, the biggest
    json.dumps(summary)                                      # must be serialisable
    print("  ok  summary builds and is valid JSON")
    print("\nall checks passed\n")


# ---------------------------------------------------------------------------
def run(since=None, write=True):
    """
    The whole pipeline: download, clean, summarise, save.

    Split out from main() so it can be called directly — from a notebook, from
    another script, or from a Python prompt — without going through argparse.
    Returns the summary dictionary, or None if nothing could be loaded.
    """
    print("looking up the dataset ...")
    files, code_url = list_files(since)
    if not files:
        print("no files found — is --since set too high?")
        return None
    print(f"found {len(files)} data files\n")

    frames, total_dropped = [], 0
    for name, url, fmt in files:
        try:
            raw = download(url, fmt)
            cleaned, dropped = clean(raw, name)
            total_dropped += dropped
            frames.append(cleaned)
            print(f"  {name[:45]:<45} {len(raw):>7,} rows -> {len(cleaned):>7,} kept")
        except Exception as exc:
            print(f"  {name[:45]:<45} SKIPPED ({exc})")

    if not frames:
        print("nothing loaded")
        return None

    df = pd.concat(frames, ignore_index=True)
    print(f"\ncombined: {len(df):,} usable delays "
          f"({total_dropped:,} rows dropped as unusable)")

    # Replace cause codes with readable descriptions, where a lookup exists.
    if code_url:
        try:
            codes = pd.read_csv(code_url)
            codes.columns = [c.strip().lower() for c in codes.columns]
            ccol = next(c for c in codes.columns if "code" in c)
            dcol = next(c for c in codes.columns if "desc" in c)
            mapping = {str(k).strip(): str(v).strip()
                       for k, v in zip(codes[ccol], codes[dcol]) if pd.notna(k)}
            df["cause"] = df["cause"].map(lambda c: mapping.get(c, c))
            print(f"translated {len(mapping)} cause codes into descriptions")
        except Exception as exc:
            print(f"could not load cause descriptions ({exc}) — showing raw codes")

    summary = summarise(df)
    if write:
        with open(OUTPUT, "w") as fh:
            json.dump(summary, fh, indent=1)
        print(f"\nwrote {OUTPUT}")

    print_findings(summary)
    return summary


def main():
    ap = argparse.ArgumentParser(description="Analyse TTC bus delays.")
    ap.add_argument("--since", type=int, help="only load files from this year onward")
    ap.add_argument("--selftest", action="store_true", help="check the logic, no download")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return 0

    summary = run(args.since)
    if summary is None:
        return 1
    print("Now open index.html to see it, and put the interesting bits on the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
