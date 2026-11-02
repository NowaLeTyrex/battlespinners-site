"""Enregistre des matchs de bots depuis le jeu et en découpe des clips pour le press kit.

Chaque prise de match produit deux vidéos 1920×1080 à 60 i/s, image pour image
identiques : window.mp4 (avec HUD) et world.mp4 (sans HUD), plus events.jsonl
(lancements, frappes, capacités, éjections, explosions). La personnalisation
(--scenario customization) ne produit que window.mp4. Voir tools/capture/capture_probe.gd.

Usage :
  python tools/capture/capture.py record --project <dossier du jeu> --godot <godot.exe>
         [--arena 2OV --arena Gym …] [--difficulty 7] [--rounds 1] [--max-seconds 40]
         [--scenario customization]
  python tools/capture/capture.py clips
  python tools/capture/capture.py export <clip> <nom>      ex. export 2OV-1_ring_out_1 loop-03-ring-out
  python tools/capture/capture.py hero <clip>:<début>:<fin> …   montage -> assets/img/hero-loop.mp4 + affiche

  record   -> _captures/raw/<arène|customization>-<n>/   (le jeu s'ouvre sur l'écran principal)
  clips    -> _captures/raw/clips/sheet_<prise>.png (6 images par moment candidat)
             + index.json (plage d'images de chaque candidat)
  export   -> découpe le candidat dans les deux masters : _captures/loops/<nom>.mp4
             (sans HUD) et <nom>-hud.mp4, puis : python tools/make_loops.py _captures/loops

Le jeu réécrit à chaque lancement des fichiers de l'utilisateur : la sauvegarde est
redirigée (--save-root) et settings.cfg / save.json sont sauvegardés puis restaurés.
Prérequis : ffmpeg dans le PATH, Pillow (planches).
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROBE = Path(__file__).resolve().parent / "capture_probe.gd"
RAW = ROOT / "_captures/raw"
CLIPS = RAW / "clips"
LOOPS = ROOT / "_captures/loops"
FPS = 60

ARENAS = {
    "2C": "arena-2C", "2C-bp": "arena-2C-bp", "2H-a": "arena-2H-a", "2H-b": "arena-2H-b",
    "2O": "arena-2O", "2OV": "arena-2OV", "Gym": "arena-Gym", "Temple": "arena-Temple",
}

# Fenêtres de découpe autour de chaque moment, en secondes (avant, après)
WINDOWS = {
    "opening": (1.0, 6.0),     # autour du premier lancement
    "clash": (-0.3, 5.3),      # juste après le lancement : la mêlée
    "ring_out": (2.5, 1.5),
    "explosion": (2.0, 2.0),
    "ability": (0.8, 2.7),
}


def user_data_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Godot/app_userdata/BattleSpinners"


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


#region Enregistrement

def record(args: argparse.Namespace) -> int:
    project = Path(args.project).resolve()
    if not (project / "project.godot").exists():
        print(f"Pas de project.godot dans {project}")
        return 1
    ffmpeg_exe = shutil.which("ffmpeg")
    if ffmpeg_exe is None:
        print("ffmpeg introuvable dans le PATH.")
        return 1
    if _godot_running():
        print("Un Godot tourne déjà (éditeur ou jeu) : ferme-le avant d'enregistrer.")
        return 1

    user_dir = user_data_dir()
    backup = RAW / "_userdata_backup"
    backup.mkdir(parents=True, exist_ok=True)
    steam_dir = project / "addons/godotsteam/win64"
    if args.scenario == "customization":
        jobs = [("customization", ["--scenario=customization"])]
    else:
        unknown = [a for a in args.arena if a not in ARENAS]
        if unknown:
            print(f"Arène inconnue : {', '.join(unknown)} ({', '.join(ARENAS)})")
            return 1
        jobs = [(arena, ["--scenario=match",
                         f"--arena=res://Environment/Arenas/ArenaData/{ARENAS[arena]}.tres",
                         f"--difficulty={args.difficulty}", f"--rounds={args.rounds}"])
                for arena in args.arena]
    for label, scenario_args in jobs:
        take = _next_take(label)
        take.mkdir(parents=True)
        saved = _backup_user_files(user_dir, backup)
        steam_before = sorted(os.listdir(steam_dir)) if steam_dir.exists() else []
        cmd = [args.godot, "--path", str(project), "--fixed-fps", str(FPS), "--script", str(PROBE), "--",
               f"--save-root={take / 'save_root'}", f"--events={take / 'events.jsonl'}",
               f"--out-window={take / 'window.mp4'}", f"--out-world={take / 'world.mp4'}",
               f"--ffmpeg={ffmpeg_exe}", f"--max-seconds={args.max_seconds}", f"--locale={args.locale}",
               *scenario_args]
        print(f"[{take.name}] enregistrement…")
        with open(take / "godot.log", "w", encoding="utf-8", errors="replace") as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
        _restore_user_files(user_dir, backup, saved)
        steam_after = sorted(os.listdir(steam_dir)) if steam_dir.exists() else []
        if steam_after != steam_before:
            print(f"  ! addons/godotsteam/win64 a changé (copie fantôme de la DLL) : "
                  f"avant {set(steam_before) - set(steam_after)}, après {set(steam_after) - set(steam_before)}")
        _report_take(take)
    return 0


def _godot_running() -> bool:
    if os.name != "nt":
        return False
    out = subprocess.run(["tasklist"], capture_output=True, text=True, check=False).stdout.lower()
    return "godot" in out


def _next_take(arena: str) -> Path:
    n = 1
    while (RAW / f"{arena}-{n}").exists():
        n += 1
    return RAW / f"{arena}-{n}"


def _backup_user_files(user_dir: Path, backup: Path) -> list[str]:
    saved = []
    for name in ("settings.cfg", "save.json"):
        if (user_dir / name).exists():
            shutil.copy2(user_dir / name, backup / name)
            saved.append(name)
    return saved


def _restore_user_files(user_dir: Path, backup: Path, saved: list[str]) -> None:
    for name in saved:
        if not filecmp.cmp(user_dir / name, backup / name, shallow=False):
            shutil.copy2(backup / name, user_dir / name)
            print(f"  {name} modifié par le jeu : restauré")


def _report_take(take: Path) -> None:
    events = load_events(take)
    kinds = [e["event"] for e in events]
    closed = [e for e in events if e["event"] == "encoder_closed"]
    if _scenario(events) == "customization":
        print(f"  {len(closed)} flux, {kinds.count('action')} action(s) jouée(s)")
        expected = 1
    else:
        print(f"  {len(closed)} flux, {kinds.count('ring_out')} éjection(s), "
              f"{kinds.count('explosion')} explosion(s), {kinds.count('ability')} capacité(s), "
              f"{'fin de manche' if 'round_ended' in kinds else 'PAS de fin de manche'}")
        expected = 2
    if len(closed) != expected:
        print(f"  ! enregistrement incomplet, voir {take / 'godot.log'}")


def _scenario(events: list[dict]) -> str:
    return next((e.get("scenario", "match") for e in events if e["event"] == "window"), "match")

#endregion


#region Découpe

def load_events(take: Path) -> list[dict]:
    path = take / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def candidates(events: list[dict]) -> list[tuple[str, int]]:
    """(moment, tick) à découper. Les capacités à moins de 2 s de la précédente
    retenue sont regroupées : elles tomberaient dans le même clip."""
    launches = [e["tick"] for e in events if e["event"] == "launch"]
    found: list[tuple[str, int]] = []
    if launches:
        found += [("opening", launches[0]), ("clash", launches[0])]
    last_ability = -FPS * 10
    for e in events:
        if e["event"] in ("ring_out", "explosion"):
            found.append((e["event"], e["tick"]))
        elif e["event"] == "ability" and e["tick"] - last_ability >= 2 * FPS:
            found.append(("ability", e["tick"]))
            last_ability = e["tick"]
    return found


def clips(_args: argparse.Namespace) -> int:
    CLIPS.mkdir(parents=True, exist_ok=True)
    takes = sorted(p for p in RAW.iterdir() if p.is_dir() and (p / "events.jsonl").exists())
    if not takes:
        print("Aucune prise dans _captures/raw : lance d'abord « record ».")
        return 1
    index: dict[str, dict] = {}
    for take in takes:
        events = load_events(take)
        start = next((e["tick"] for e in events if e["event"] == "record_start"), None)
        total = next((e["frames"] for e in events if e["event"] == "encoder_closed"), 0)
        if start is None or not total:
            print(f"[{take.name}] prise incomplète, ignorée")
            continue
        strips = []
        if _scenario(events) == "customization":
            name = f"{take.name}_customization_1"
            index[name] = {"take": take.name, "first": 0, "last": total}
            strip = CLIPS / f"{name}.png"
            _strip(take / "window.mp4", 0, total, strip)
            strips.append((name, total / FPS, strip))
        counters: dict[str, int] = {}
        for kind, tick in candidates(events):
            before, after = WINDOWS[kind]
            # Image vidéo n = rendu du tick (record_start + n - 1)
            first = max(0, tick - start + 1 - round(before * FPS))
            last = min(total, tick - start + 1 + round(after * FPS))
            if last - first < FPS:
                continue
            counters[kind] = counters.get(kind, 0) + 1
            name = f"{take.name}_{kind}_{counters[kind]}"
            index[name] = {"take": take.name, "first": first, "last": last}
            strip = CLIPS / f"{name}.png"
            _strip(take / "world.mp4", first, last, strip)
            strips.append((name, (last - first) / FPS, strip))
        _sheet(strips, CLIPS / f"sheet_{take.name}.png")
        print(f"[{take.name}] {len(strips)} candidats")
    (CLIPS / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"\nPlanches à regarder : {CLIPS}/sheet_*.png, puis « export <candidat> <nom> ».")
    return 0


def _cut(master: Path, first: int, last: int, out: Path) -> None:
    ffmpeg("-ss", f"{first / FPS:.4f}", "-i", str(master), "-frames:v", str(last - first), "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "8", "-pix_fmt", "yuv444p", str(out))


def _strip(master: Path, first: int, last: int, out: Path) -> None:
    step = max(1, (last - first) // 6)
    ffmpeg("-ss", f"{first / FPS:.4f}", "-i", str(master), "-frames:v", str(last - first),
           "-vf", f"select='not(mod(n\\,{step}))',scale=320:180:flags=area,tile=6x1",
           "-frames:v", "1", str(out))


def _sheet(strips: list[tuple[str, float, Path]], out: Path) -> None:
    if not strips:
        return
    from PIL import Image, ImageDraw
    rows = [Image.open(p) for _, _, p in strips]
    sheet = Image.new("RGB", (rows[0].width, sum(r.height + 18 for r in rows)), (20, 20, 30))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for (name, seconds, _), row in zip(strips, rows):
        draw.text((4, y + 3), f"{name}  ({seconds:.1f} s)", fill=(255, 220, 90))
        sheet.paste(row, (0, y + 18))
        y += row.height + 18
    sheet.save(out)
    for _, _, p in strips:
        p.unlink()

#endregion


def export(args: argparse.Namespace) -> int:
    index_path = CLIPS / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    if args.clip not in index:
        print(f"Candidat inconnu : {args.clip} (lance « clips », voir {index_path})")
        return 1
    clip = index[args.clip]
    first = clip["first"] + round(args.trim_start * FPS)
    last = clip["last"] - round(args.trim_end * FPS)
    LOOPS.mkdir(parents=True, exist_ok=True)
    # Sans flux « monde » (personnalisation), une seule version : l'écran tel quel.
    sources = [("world", ""), ("window", "-hud")]
    if not (RAW / clip["take"] / "world.mp4").exists():
        sources = [("window", "")]
    for source, suffix in sources:
        out = LOOPS / f"{args.name}{suffix}.mp4"
        _cut(RAW / clip["take"] / f"{source}.mp4", first, last, out)
        print(f"  {args.clip} ({source}) -> _captures/loops/{out.name}, {(last - first) / FPS:.1f} s")
    return 0


HERO = ROOT / "assets/img/hero-loop.mp4"
HERO_POSTER = ROOT / "assets/img/hero-poster.jpg"


def hero(args: argparse.Namespace) -> int:
    """Boucle d'accueil du site : montage de passages sans HUD, bout à bout.
    Chaque passage = <candidat>:<début>:<fin>, en secondes depuis le début du candidat."""
    index_path = CLIPS / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    inputs: list[str] = []
    lengths: list[int] = []
    for spec in args.segments:
        name, start, end = spec.rsplit(":", 2)
        if name not in index:
            print(f"Candidat inconnu : {name}")
            return 1
        clip = index[name]
        first = clip["first"] + round(float(start) * FPS)
        last = min(clip["first"] + round(float(end) * FPS), clip["last"])
        inputs += ["-ss", f"{first / FPS:.4f}", "-i", str(RAW / clip["take"] / "world.mp4")]
        lengths.append(last - first)
    count = len(lengths)
    graph = "".join(f"[{i}:v]trim=end_frame={frames},setpts=PTS-STARTPTS[v{i}];"
                    for i, frames in enumerate(lengths))
    graph += "".join(f"[v{i}]" for i in range(count))
    # Même encodage que les boucles de la page (tools/make_loops.py) : CRF 28, BT.709 déclaré
    graph += f"concat=n={count}:v=1:a=0,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[out]"
    ffmpeg(*inputs, "-filter_complex", graph, "-map", "[out]", "-an", "-c:v", "libx264", "-preset", "slow",
           "-crf", "28", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "iec61966-2-1",
           "-movflags", "+faststart", str(HERO))
    ffmpeg("-i", str(HERO), "-frames:v", "1", "-q:v", "3", str(HERO_POSTER))
    seconds = sum(lengths) / FPS
    print(f"  {HERO.relative_to(ROOT)} : {count} passages, {seconds:.1f} s, {HERO.stat().st_size / 1e6:.1f} Mo")
    print(f"  {HERO_POSTER.relative_to(ROOT)} : première image")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--project", required=True)
    rec.add_argument("--godot", default=os.environ.get("GODOT", "godot"))
    rec.add_argument("--arena", action="append", default=None)
    rec.add_argument("--difficulty", type=int, default=7)
    rec.add_argument("--rounds", type=int, default=1)
    rec.add_argument("--max-seconds", type=int, default=40)
    rec.add_argument("--locale", default="en")
    rec.add_argument("--scenario", choices=["match", "customization"], default="match")
    sub.add_parser("clips")
    exp = sub.add_parser("export")
    exp.add_argument("clip")
    exp.add_argument("name")
    exp.add_argument("--trim-start", type=float, default=0.0, help="secondes retirées au début")
    exp.add_argument("--trim-end", type=float, default=0.0, help="secondes retirées à la fin")
    her = sub.add_parser("hero")
    her.add_argument("segments", nargs="+", help="<candidat>:<début s>:<fin s>")
    args = parser.parse_args()
    if args.command == "record":
        args.arena = args.arena or ["2OV"]
        return record(args)
    if args.command == "clips":
        return clips(args)
    if args.command == "hero":
        return hero(args)
    return export(args)


if __name__ == "__main__":
    sys.exit(main())
