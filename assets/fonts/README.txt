Police d'affichage (titres)
===========================

Le site cherche ici un fichier nommé display.woff2 : la police pixel du jeu.
Sans ce fichier, les titres s'affichent en Verdana.

1. Prends la police utilisée dans le jeu (res://Assets/fonts/...).
   Vérifie que sa licence autorise l'usage web (les polices OFL l'autorisent).
2. Convertis-la en WOFF2 :
     pip install fonttools brotli
     python -m fontTools.ttLib.woff2 compress -o display.woff2 MaPolice.ttf
3. Dépose display.woff2 dans ce dossier, avec le fichier de licence de la police
   s'il en exige la diffusion (OFL.txt par exemple).

Ne charge pas la police depuis Google Fonts : l'appel transmet l'adresse IP des
visiteurs à Google, ce que le site promet de ne pas faire (voir mentions légales).
