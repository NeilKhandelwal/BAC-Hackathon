"""Render docs/deck/pitch_template.pptx to PNG previews in docs/deck/previews/.

Needs LibreOffice (`soffice` on PATH) and PyMuPDF (`pip install pymupdf`).
Run from the repo root:

    .venv/bin/python docs/deck/render_previews.py [--width 1600] [--out DIR]

LibreOffice renders fonts and charts slightly differently from PowerPoint.
Check the deck in PowerPoint or Keynote before presenting.
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "docs/deck/pitch_template.pptx"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--out", type=Path, default=ROOT / "docs/deck/previews")
    args = ap.parse_args()
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise SystemExit("soffice not found; install LibreOffice")
    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob("slide-*.png"):
        old.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(DECK)],
                       check=True, capture_output=True)
        doc = pymupdf.open(Path(tmp) / (DECK.stem + ".pdf"))
        for i, page in enumerate(doc, start=1):
            zoom = args.width / page.rect.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            pix.save(args.out / f"slide-{i:02d}.png")
        print(f"rendered {len(doc)} slides to {args.out}")


if __name__ == "__main__":
    main()
