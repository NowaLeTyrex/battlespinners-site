"""Fabrique les boucles du press kit à partir de clips de jeu déjà coupés (3 à 10 s, 1080p).

Les clips viennent de tools/capture/capture.py (export) : <nom>.mp4 sans HUD et, pour
les matchs, <nom>-hud.mp4 avec HUD (mêmes images).

Pour chaque clip du dossier d'entrée (ex. _captures/loops/loop-01-clash.mp4) :
  - press/loops/<nom>.mp4                    MP4 1080p léger, sans son, lu dans la page
  - press/loops/<nom>.png                    affiche 640×360 (première image ; pas pour -hud)
  - presskit-src/05_gifs/battlespinners_<nom>.gif       GIF 640×360, 25 i/s
  - presskit-src/06_videos/loops/battlespinners_<nom>.mp4   MP4 1080p haute qualité

Le nom du GIF suit celui attendu par la page : loop-01-clash -> battlespinners_loop_01_clash.gif

Usage :  python tools/make_loops.py _captures/loops
Prérequis : ffmpeg dans le PATH
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTS = {".mp4", ".mov", ".mkv", ".webm"}
GIF_LIMIT = 15_000_000
# YUV en matrice BT.709, déclarée : sans elle, ffmpeg convertit le RGB en BT.601 alors que
# les navigateurs supposent BT.709 pour la HD (teintes décalées). Transfert sRGB : c'est
# l'encodage réel des images du jeu.
TO_BT709 = "out_color_matrix=bt709:out_range=tv,format=yuv420p"
COLOR_TAGS = ("-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "iec61966-2-1")


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    if shutil.which("ffmpeg") is None:
        print("ffmpeg introuvable : installe-le et ajoute-le au PATH.")
        return 1
    clips = sorted(p for p in Path(sys.argv[1]).iterdir() if p.suffix.lower() in EXTS)
    if not clips:
        print("Aucun clip trouvé.")
        return 1

    for clip in clips:
        name = clip.stem.lower().replace(" ", "-").replace("_", "-")
        asset = "battlespinners_" + name.replace("-", "_")
        web_mp4 = ROOT / "press/loops" / f"{name}.mp4"
        poster = ROOT / "press/loops" / f"{name}.png"
        gif = ROOT / "presskit-src/05_gifs" / f"{asset}.gif"
        hq_mp4 = ROOT / "presskit-src/06_videos/loops" / f"{asset}.mp4"
        for p in (web_mp4, gif, hq_mp4):
            p.parent.mkdir(parents=True, exist_ok=True)

        # Ramène toujours en 1920×1080 au plus proche voisin (aucun effet si le clip l'est déjà)
        to_1080 = "scale=1920:1080:flags=neighbor:" + TO_BT709
        # CRF 28 : à l'échelle 1:1, quasi identique au CRF 24 sur du gameplay chargé
        # (foule, traînées), pour 40 % de poids en moins dans la page
        ffmpeg("-i", str(clip), "-an", "-vf", to_1080, "-c:v", "libx264", "-preset", "slow",
               "-crf", "28", *COLOR_TAGS, "-movflags", "+faststart", str(web_mp4))
        ffmpeg("-i", str(clip), "-an", "-vf", to_1080, "-c:v", "libx264", "-preset", "slow",
               "-crf", "16", *COLOR_TAGS, "-movflags", "+faststart", str(hq_mp4))
        # Réduction ÷3 par moyenne de zone (voir tools/prepare_images.py : le jeu rend
        # rotations et effets en 1080p, le plus proche voisin les crénellerait)
        # Variante avec HUD (<nom>-hud) : proposée en lien seulement, pas d'affiche
        if not name.endswith("-hud"):
            ffmpeg("-i", str(clip), "-frames:v", "1", "-vf", "scale=640:360:flags=area", str(poster))
        # GIF : palette calculée sur le clip, sans tramage (le tramage abîme le pixel art)
        ffmpeg("-i", str(clip), "-vf",
               "fps=25,scale=640:360:flags=area,split[a][b];"
               "[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none",
               "-loop", "0", str(gif))

        gif_size = gif.stat().st_size
        warn = "  ! GIF au-dessus de 15 Mo : raccourcis le clip" if gif_size > GIF_LIMIT else ""
        print(f"  {name} : page {web_mp4.stat().st_size / 1e6:.1f} Mo, GIF {gif_size / 1e6:.1f} Mo{warn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
