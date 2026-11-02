Police d'affichage (titres)
===========================

display.woff2 = Pixeloid Sans Bold de GGBotNet (https://ggbot.net), la police de
l'UI du jeu (res://Assets/Fonts/PixeloidSansBold-OG894.ttf), convertie en WOFF2
sans autre modification. Licence SIL Open Font License 1.1 : OFL.txt doit rester
à côté du fichier.

Grille de la police : 9 px par em. Elle n'est nette qu'à 18, 27, 36 ou 45 px
(voir les tailles de titres dans assets/site.css).

Pour la régénérer :
     pip install fonttools brotli
     python -m fontTools.ttLib.woff2 compress -o display.woff2 PixeloidSansBold-OG894.ttf

Ne charge pas la police depuis Google Fonts : l'appel transmet l'adresse IP des
visiteurs à Google, ce que le site promet de ne pas faire (voir mentions légales).
