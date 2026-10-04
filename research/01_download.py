# Downloads the RBA login dataset (Wiefling et al., 2022) from Zenodo into data/raw/.

import hashlib
import sys
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.config import configured_path  # noqa: E402

RAW_DIR = configured_path("data") / "raw"
ZIP_PATH = RAW_DIR / "rba-dataset.zip"
CSV_PATH = RAW_DIR / "rba-dataset.csv"

RECORD_API = "https://zenodo.org/api/records/6782156"
FILE_URL = "https://zenodo.org/records/6782156/files/rba-dataset.zip?download=1"
CHUNK = 1 << 20

MANUAL_STEPS = f"""Could not download the dataset from Zenodo. Either:
  1. download rba-dataset.zip from https://zenodo.org/records/6782156 into {RAW_DIR}/, or
  2. set up a Kaggle API token and download https://www.kaggle.com/datasets/dasgroup/rba-dataset
then run `make data` again."""


def expected_md5() -> str | None:
    try:
        record = requests.get(RECORD_API, timeout=30).json()
    except (requests.RequestException, ValueError):
        return None
    for f in record.get("files", []):
        if f.get("key") == ZIP_PATH.name and f.get("checksum", "").startswith("md5:"):
            return f["checksum"].removeprefix("md5:")
    return None


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    # Write to a .part file first so a failed download never looks complete.
    part = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0)) or None
        with open(part, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar:
            for chunk in response.iter_content(CHUNK):
                f.write(chunk)
                bar.update(len(chunk))
    part.rename(dest)


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if CSV_PATH.exists():
        print(f"{CSV_PATH.name} already present, nothing to do.")
        return 0

    if ZIP_PATH.exists():
        print(f"{ZIP_PATH.name} already present, skipping download.")
    else:
        try:
            download(FILE_URL, ZIP_PATH)
        except requests.RequestException as error:
            print(f"Download failed: {error}\n\n{MANUAL_STEPS}", file=sys.stderr)
            return 1

    md5 = expected_md5()
    if md5 is None:
        print("Warning: could not fetch the MD5 from Zenodo, skipping verification.")
    elif (actual := file_md5(ZIP_PATH)) != md5:
        print(f"MD5 mismatch: expected {md5}, got {actual}. Delete {ZIP_PATH} and retry.", file=sys.stderr)
        return 1
    else:
        print(f"MD5 verified: {md5}")

    # Only the CSV is needed; the archive's docs and images stay inside the zip.
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extract(CSV_PATH.name, RAW_DIR)
    print(f"Done: {CSV_PATH} ({CSV_PATH.stat().st_size / 1e9:.2f} GB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
