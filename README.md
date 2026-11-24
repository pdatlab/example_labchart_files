# example_labchart_files
Example labchart files for testing things

68 LabChart files: 51 publicly available recordings, each 200 MB or less (about 666 MB total),
collected from Figshare (38 files, 23 datasets) and OSF (13 files, 7 projects), plus 17 samples that
ship with LabChart 8 and ADInstruments' Simple Data File SDK.

The data files are not stored in git. They live in a shared Google Drive folder, and
`download_files.py` fetches them into this folder and checks each one against `manifest.csv`.

## Getting the files

```
pip install -r requirements.txt
python download_files.py --drive-url "<shared Google Drive folder link>"
```

- Set `DRIVE_FOLDER_URL` in `download_files.py` to skip `--drive-url`.
- `--from-source` downloads from the original Figshare/OSF links instead of Drive.
- `--only osf_` limits the download to paths containing some text.
- `--verify` only checks the files already on disk.
- Re-running is safe: files that are present and match their MD5 are skipped.

## What's here

| File | Purpose |
|---|---|
| `labchart_file_sources.xlsx` | Where each file came from: dataset, authors, license, DOI, links, MD5 |
| `manifest.csv` | Path, size and MD5 for every file; used by the download script |
| `download_files.py` | Downloads and verifies the files |

Files are stored as `figshare_<article id>/...` and `osf_<project id>/...`.

There are also 17 sample files copied from a local ADInstruments install. They are in `manifest.csv`,
so the Drive download includes them; with `--from-source` they are copied from a local LabChart / SDK
install instead, since they have no public download link:

- `labchart8_install_samples/`: the 14 gallery files LabChart 8 installs under
  `C:\Program Files (x86)\ADInstruments\LabChart8\Welcome Center\Gallery\Getting Started`
  (7 example recordings and 7 tutorial files).
- `adi_sdk_examples/`: example data from ADInstruments' Simple Data File SDK (`.adicht` and `.adidat`).

## Licensing

- Figshare files are CC BY 4.0: cite the dataset DOI (in the spreadsheet) when you reuse them.
- The OSF projects state no license, so those files are all rights reserved by default. They are fine
  for local testing, but check with the authors before redistributing them.
- The LabChart and SDK samples are part of ADInstruments' software and are not separately licensed
  for redistribution, so sharing them through a public Drive link has the same caveat.
