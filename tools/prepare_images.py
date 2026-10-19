"""Prépare les captures d'écran du press kit à partir de captures 1080p du jeu.

Pour chaque PNG du dossier d'entrée (ex. _captures/01-four-player-melee.png) :
  - press/img/shots/<nom>.png                         1920×1080, affichée au clic
  - press/img/shots/thumbs/<nom>.png                  640×360 (résolution native), vignette de la page
  - presskit-src/04_screenshots/1080p/battlespinners_<nom>.png
  - presskit-src/04_screenshots/4k/battlespinners_<nom>_4k.png   3840×2160

Tous les changements de taille se font au plus proche voisin et par facteur entier
(÷3 et ×2), pour que chaque pixel du jeu reste un carré net.

Usage :  python tools/prepare_images.py _captures
Prérequis : pip install pillow
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
NATIVE = (640, 360)
FULL = (1920, 1080)
UHD = (3840, 2160)


def load_as_1080p(path: Path) -> Image.Image | None:
    img = Image.open(path)
    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    w, h = img.size
    if (w, h) == FULL:
        return img
    # Capture à la résolution native ou à un multiple entier : on ramène en 1080p sans flou
    if w * NATIVE[1] == h * NATIVE[0] and w % NATIVE[0] == 0:
        return img.resize(FULL, Image.NEAREST)
    print(f"  ! {path.name} : {w}×{h} n'est pas un multiple entier de 640×360, ignorée")
    return None


def save(img: Image.Image, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, optimize=True)
    return dest.stat().st_size


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    src_dir = Path(sys.argv[1])
    files = sorted(p for p in src_dir.glob("*.png"))
    if not files:
        print(f"Aucun PNG dans {src_dir}")
        return 1

    for path in files:
        name = path.stem.lower().replace(" ", "-").replace("_", "-")
        base = load_as_1080p(path)
        if base is None:
            continue
        thumb = base.resize(NATIVE, Image.NEAREST)
        uhd = base.resize(UHD, Image.NEAREST)

        sizes = [
            save(base, ROOT / "press/img/shots" / f"{name}.png"),
            save(thumb, ROOT / "press/img/shots/thumbs" / f"{name}.png"),
            save(base, ROOT / "presskit-src/04_screenshots/1080p" / f"battlespinners_{name}.png"),
            save(uhd, ROOT / "presskit-src/04_screenshots/4k" / f"battlespinners_{name}_4k.png"),
        ]
        print(f"  {name} : 1080p {sizes[0] // 1024} Ko, vignette {sizes[1] // 1024} Ko, 4K {sizes[3] // 1024} Ko")

    web = sum(p.stat().st_size for p in (ROOT / "press/img").rglob("*") if p.is_file())
    print(f"\nPoids des images de la page (press/img) : {web / 1_000_000:.1f} Mo")
    print("Pense à mettre à jour les noms, les alt et les légendes dans press/index.html et press/fr/index.html.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
