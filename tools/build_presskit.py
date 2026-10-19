"""Construit les fichiers de la release GitHub du press kit, et la publie si demandé.

Sortie dans dist/ :
  battlespinners_presskit.zip     textes, logos, key art, captures 1080p et 4K, GIF, boucles
  battlespinners_broll.zip        rushes sans musique (presskit-src/06_videos/broll)
  battlespinners_loop_*.gif       chaque GIF, téléchargeable seul depuis la page
  battlespinners_announcement_trailer_*.mp4   copiés depuis presskit-src/trailer/

Usage :
  python tools/build_presskit.py                     construit dist/ et affiche les tailles à reporter dans la page
  python tools/build_presskit.py --release presskit-2026-10
                                                     construit puis publie la release (nécessite gh connecté)

Les noms de fichiers ne changent jamais d'une release à l'autre : les liens
.../releases/latest/download/<nom> de la page servent toujours la dernière version.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "presskit-src"
DIST = ROOT / "dist"
ALREADY_COMPRESSED = {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".zip", ".woff2"}
EXCLUDED_FROM_MAIN_ZIP = ("06_videos/broll", "trailer")


def add_tree(zf: zipfile.ZipFile, folder: Path, arc_root: str, skip: tuple[str, ...] = ()) -> int:
    count = 0
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        if not path.is_file() or path.name in {"README.md", ".DS_Store", "Thumbs.db"}:
            continue
        if any(rel == s or rel.startswith(s + "/") for s in skip):
            continue
        method = zipfile.ZIP_STORED if path.suffix.lower() in ALREADY_COMPRESSED else zipfile.ZIP_DEFLATED
        zf.write(path, f"{arc_root}/{rel}", compress_type=method)
        count += 1
    return count


def mb(path: Path) -> str:
    size = path.stat().st_size / 1_000_000
    return f"{size:.1f} Mo" if size < 10 else f"{size:.0f} Mo"


def main() -> int:
    args = sys.argv[1:]
    tag = None
    if args[:1] == ["--release"]:
        if len(args) != 2:
            print(__doc__)
            return 1
        tag = args[1]
    elif args:
        print(__doc__)
        return 1

    for expected in ("01_texts", "02_logos", "03_keyart", "04_screenshots", "05_gifs"):
        if not any((SRC / expected).rglob("*.*")):
            print(f"  ! presskit-src/{expected} est vide")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    main_zip = DIST / "battlespinners_presskit.zip"
    with zipfile.ZipFile(main_zip, "w") as zf:
        n = add_tree(zf, SRC, "battlespinners_presskit", EXCLUDED_FROM_MAIN_ZIP)
    print(f"battlespinners_presskit.zip : {n} fichiers, {mb(main_zip)}")

    broll_dir = SRC / "06_videos/broll"
    if any(broll_dir.glob("*.*")):
        broll_zip = DIST / "battlespinners_broll.zip"
        with zipfile.ZipFile(broll_zip, "w") as zf:
            add_tree(zf, broll_dir, "battlespinners_broll")
        print(f"battlespinners_broll.zip : {mb(broll_zip)}")

    for gif in sorted((SRC / "05_gifs").glob("*.gif")):
        shutil.copy2(gif, DIST / gif.name)
        print(f"{gif.name} : {mb(DIST / gif.name)}")
    for video in sorted((SRC / "trailer").glob("*.mp4")):
        shutil.copy2(video, DIST / video.name)
        print(f"{video.name} : {mb(DIST / video.name)}")

    print("\nReporte ces tailles dans les deux pages presse (les <mark class=\"todo\">000 Mo</mark>).")

    if tag:
        if shutil.which("gh") is None:
            print("gh introuvable : installe GitHub CLI puis lance « gh auth login ».")
            return 1
        files = [str(p) for p in sorted(DIST.iterdir())]
        subprocess.run(["gh", "release", "create", tag, *files,
                        "--title", f"Press kit {tag}",
                        "--notes", "Fichiers du dossier de presse BattleSpinners.",
                        "--latest"], check=True, cwd=ROOT)
        print(f"Release {tag} publiée.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
