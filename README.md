# battlespinnersgame.com

Site statique de BattleSpinners, servi par GitHub Pages sur battlespinnersgame.com.

| Adresse          | Fichier                        |
|------------------|--------------------------------|
| /                | index.html                     |
| /press/          | press/index.html (anglais)     |
| /press/fr/       | press/fr/index.html (français) |
| /mentions-legales/ | mentions-legales/index.html  |

Les fichiers lourds (ZIP, trailer, rushes, GIF) ne sont pas dans le dépôt : ils sont publiés
dans une release GitHub et la page pointe vers `releases/latest/download/<nom>`.

## Aide-mémoire

```bash
# Prévisualiser en local, puis ouvrir http://localhost:8000/press/
python -m http.server 8000

# Captures 1080p dans _captures/ -> page + sources du ZIP
python tools/prepare_images.py _captures

# Enregistrer des matchs de bots depuis le jeu (avec et sans HUD), éditeur Godot fermé.
# Le jeu s'ouvre en 1920×1080 dans le coin de l'écran principal ; sauvegarde redirigée,
# settings.cfg et save.json restaurés. Masters dans _captures/raw/ (plusieurs Go).
python tools/capture/capture.py record --project ../../BattleSpinners --godot <godot.exe> --arena 2H-a --arena 2C
python tools/capture/capture.py record --project ../../BattleSpinners --godot <godot.exe> --scenario customization
# Planches des moments candidats (_captures/raw/clips/sheet_*.png), puis export d'un candidat
python tools/capture/capture.py clips
python tools/capture/capture.py export 2H-b-1_ring_out_1 loop-03-ring-out   # -> loop-03-ring-out(-hud).mp4
# Boucle d'accueil : passages sans HUD bout à bout (<candidat>:<début s>:<fin s>)
python tools/capture/capture.py hero 2H-a-1_opening_1:0.4:3.4 2C-1_ability_6:0.2:2.0 2H-b-1_ring_out_1:1.4:3.6 2H-a-1_explosion_1:1.0:3.5

# Clips coupés dans _captures/loops/ -> boucles de la page, GIF, MP4 du ZIP
python tools/make_loops.py _captures/loops

# Construire dist/ et lire les tailles à reporter dans la page
python tools/build_presskit.py

# Construire et publier une nouvelle release (mêmes noms de fichiers à chaque fois)
python tools/build_presskit.py --release presskit-2026-11

# Mettre le site en ligne
git add -A && git commit -m "Press kit : mise à jour" && git push

# Combien de fois chaque fichier a été téléchargé
gh release view --json assets --jq '.assets[] | "\(.downloadCount)\t\(.name)"'
```

## Avant chaque publication

- `grep -rn 'class="todo"\|GITHUB_USER\|YOUTUBE_ID\|HANDLE' --include=*.html .` ne renvoie rien.
- Le factsheet correspond champ par champ à la page Steam.
- Les pages EN et FR disent la même chose.
