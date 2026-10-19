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

# Clips coupés dans _captures/loops/ -> boucles de la page, GIF, MP4 du ZIP
python tools/make_loops.py _captures/loops

# Construire dist/ et lire les tailles à reporter dans la page
python tools/build_presskit.py

# Construire et publier une nouvelle release (mêmes noms de fichiers à chaque fois)
python tools/build_presskit.py --release presskit-2026-10

# Mettre le site en ligne
git add -A && git commit -m "Press kit : mise à jour" && git push

# Combien de fois chaque fichier a été téléchargé
gh release view --json assets --jq '.assets[] | "\(.downloadCount)\t\(.name)"'
```

## Avant chaque publication

- `grep -rn 'class="todo"\|GITHUB_USER\|YOUTUBE_ID\|HANDLE' --include=*.html .` ne renvoie rien.
- Le factsheet correspond champ par champ à la page Steam.
- Les pages EN et FR disent la même chose.
