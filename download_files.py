"""Download the example LabChart files listed in manifest.csv.

By default the files come from a shared Google Drive folder that mirrors this
repository's layout (figshare_<id>/..., osf_<id>/...). Every file is checked
against the size and MD5 recorded in manifest.csv, and files that are already
present and correct are skipped, so the script is safe to re-run.

Usage:
    pip install -r requirements.txt
    python download_files.py                      # use DRIVE_FOLDER_URL below
    python download_files.py --drive-url URL      # use another shared folder
    python download_files.py --from-source        # fetch from Figshare/OSF instead
                                                  # (LabChart/SDK samples are copied from
                                                  # a local ADInstruments install)
    python download_files.py --only osf_          # only paths containing "osf_"
    python download_files.py --verify             # just check local files

The Drive folder must be shared as "Anyone with the link can view".
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# Paste the shared Google Drive folder link here once the files are uploaded.
DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1xLb_VhNhePa7TmIKxcm7qEfsrqnWFL0X?usp=sharing"

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"


def read_manifest(only: str | None) -> list[dict]:
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["size_bytes"] = int(r["size_bytes"])
    if only:
        rows = [r for r in rows if only in r["path"]]
    return rows


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_good(path: Path, entry: dict) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == entry["size_bytes"]
        and md5_of(path) == entry["md5"]
    )


def norm(p: str) -> str:
    return p.replace("\\", "/").strip("/")


def list_drive_folder(url: str) -> dict[str, str]:
    """Return {relative path inside the shared folder: Drive file id}."""
    import gdown

    files = gdown.download_folder(url=url, skip_download=True, quiet=True)
    if not files:
        sys.exit("Could not list the Drive folder. Is it shared as 'Anyone with the link'?")
    return {norm(f.path): f.id for f in files}


def match_drive_id(entry_path: str, listing: dict[str, str]) -> str | None:
    """Find the Drive file for a manifest path.

    Matches the path exactly, or as a suffix, so it still works if the shared
    folder has an extra top-level folder (e.g. example_labchart_files/...).
    """
    want = norm(entry_path)
    if want in listing:
        return listing[want]
    hits = [fid for p, fid in listing.items() if p.endswith("/" + want)]
    return hits[0] if len(hits) == 1 else None


def fetch_drive(file_id: str, out: Path) -> None:
    import gdown

    # Google sometimes refuses a file briefly ("Cannot retrieve the public link"
    # after many requests); waiting and trying again usually works.
    for attempt in range(4):
        try:
            if gdown.download(id=file_id, output=str(out), quiet=False, retries=3):
                return
        except Exception as ex:
            if attempt == 3:
                raise
            print(f"    retrying in {15 * (attempt + 1)} s ({str(ex).strip().splitlines()[0]})")
        time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"gdown could not download Drive file {file_id}")


def fetch_url(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(out, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drive-url", default=DRIVE_FOLDER_URL, help="shared Google Drive folder link")
    ap.add_argument("--from-source", action="store_true", help="download from the original Figshare/OSF links")
    ap.add_argument("--dest", default=str(HERE), help="where to put the files (default: this folder)")
    ap.add_argument("--only", help="only files whose path contains this text")
    ap.add_argument("--verify", action="store_true", help="only check files already on disk")
    args = ap.parse_args()

    dest = Path(args.dest)
    entries = read_manifest(args.only)
    todo = [e for e in entries if not is_good(dest / e["path"], e)]
    print(f"{len(entries)} files in manifest, {len(entries) - len(todo)} already present and verified.")

    if args.verify:
        for e in todo:
            print(f"  MISSING or BAD: {e['path']}")
        return 1 if todo else 0
    if not todo:
        return 0

    listing: dict[str, str] = {}
    if not args.from_source:
        if not args.drive_url:
            sys.exit("No Drive link: set DRIVE_FOLDER_URL in this script, pass --drive-url, or use --from-source.")
        listing = list_drive_folder(args.drive_url)
        print(f"Drive folder lists {len(listing)} files.")

    failed = []
    for n, e in enumerate(todo, 1):
        target = dest / e["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{n}/{len(todo)}] {e['path']} ({e['size_bytes'] / 1e6:.1f} MB)")
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, suffix=".part")
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            if args.from_source and e["source_download_url"]:
                fetch_url(e["source_download_url"], tmp)
            elif args.from_source:
                # Install samples have no public URL: copy from a local ADInstruments install if present.
                local = e["dataset_page"].removeprefix("Original location: ")
                if not os.path.isfile(local):
                    raise RuntimeError(f"no public source; install LabChart or use Drive (expected {local})")
                shutil.copyfile(local, tmp)
            else:
                fid = match_drive_id(e["path"], listing)
                if fid is None:
                    raise RuntimeError("not found in the Drive folder")
                fetch_drive(fid, tmp)
            if not is_good(tmp, e):
                raise RuntimeError("size or MD5 does not match manifest.csv")
            os.replace(tmp, target)
        except Exception as ex:  # report and keep going with the other files
            print(f"    FAILED: {ex}")
            failed.append(e["path"])
        finally:
            tmp.unlink(missing_ok=True)

    print(f"\nDone: {len(todo) - len(failed)} downloaded, {len(failed)} failed.")
    for p in failed:
        print(f"  {p}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
