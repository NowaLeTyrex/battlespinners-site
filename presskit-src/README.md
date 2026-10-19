# Sources des fichiers de la release « press kit »

`python tools/build_presskit.py` lit ce dossier et produit dist/ :

| Dossier            | Contenu                                                     | Versionné ? | Dans le ZIP principal ? |
|--------------------|-------------------------------------------------------------|-------------|--------------------------|
| 01_texts/          | factsheet_en.txt, factsheet_fr.txt                          | oui         | oui                      |
| 02_logos/          | logo_color/white/black.png, icon.png (+ .svg si dispo)      | oui         | oui                      |
| 03_keyart/         | keyart_16x9, 1x1, 9x16 (avec et sans logo)                  | oui         | oui                      |
| 04_screenshots/    | 1080p/ et 4k/, remplis par tools/prepare_images.py          | non         | oui                      |
| 05_gifs/           | GIF 640×360, remplis par tools/make_loops.py                | non         | oui (+ chaque GIF seul)  |
| 06_videos/loops/   | MP4 1080p des boucles, remplis par tools/make_loops.py      | non         | oui                      |
| 06_videos/broll/   | rushes 16:9 sans musique, 30 à 60 s                          | non         | non : ZIP séparé         |
| trailer/           | battlespinners_announcement_trailer_4k.mp4 et _1080p.mp4    | non         | non : fichiers séparés   |

Les fichiers non versionnés vivent uniquement sur ton disque et dans les releases :
garde une sauvegarde de ce dossier ailleurs (disque externe, cloud).
