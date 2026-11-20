# Recette de style (1080×1920, 30 i/s)

Valeurs mesurées image par image sur des vidéos de référence du genre (explications sportives en mannequins 3D et montages « motion design » très rythmés), puis appliquées et validées sur un vrai projet. Si l'utilisateur fournit ses propres références, les mesurer (voir `workflow.md`, agent style) et adapter ces valeurs.

## Palette

| Rôle | Couleur |
|---|---|
| Jaune « concept / nom », pastille des sous-titres, étiquettes | `#FCC52E` |
| Rouge « erreur, faute, piège » | `#FD3A4C` |
| Cyan « action, réussite » (PANIER !) | `#3DDFFE` |
| Vert « validation » (bonne réponse) | `#7DC696` |
| Texte sur pastille | `#1E1A29` |
| Fond d'interface | noir à 75–90 % |
| Intro 3D : vide `#000`, parquet érable `#D2C3AB`, raquette turquoise `#058B90`, lignes `#F2F2F2`, membres `#C9CBD2`, joueur orange `#F07A1A` |

## Typographie

- Titres : **Anton** (Google Fonts), capitales. Une ligne ≈ 190–200 px ; deux lignes ≈ 160–170 px, première ligne blanche + mot-clé coloré. Lueur de la couleur du texte (pas de contour).
- Sous-titres, étiquettes, cartes : **Montserrat 800**, capitales, 64–66 px.
- Charger les polices Google dans la page ; créer les textures 3D (maillots, marquage du terrain) seulement après `document.fonts.load`.

## Grille (zones sûres TikTok)

- Interdit : y < 192 px (haut), y > 1 498 px (bas), x > 929 px au-dessus de 850 px (boutons à droite).
- Tableau de score / étiquettes : y ≈ 198–280 px. Titres : y ≈ 230–560 px. Carte question : y ≈ 350 px. Bandeaux info : y ≈ 1 170 px. Sous-titres : centre y ≈ 1 370 px.

## Titres géants

- Apparaissent **sur l'attaque du mot-clé prononcé** (± 2 images), au plus un toutes les 5–6 s.
- Entrée 5 images : opacité 0,5 → 0,85 → 1 ; échelle 0,90 → 1,02 → 1,06 → 1,03 → 1,00 (easeOutBack). Tenue : zoom linéaire +2 %/s. Sortie : fondu de 5 images.
- Durée à l'écran 1–2 s (moyenne 1,6 s).

## Sous-titres mot à mot

- 1 à 3 mots par groupe (≤ 20 caractères, une seule ligne), coupés à la ponctuation.
- Le groupe apparaît en 2 images ; le mot prononcé est sur une **pastille jaune `#FCC52E` inclinée de −1,5°**, texte `#1E1A29`, qui saute de mot en mot 2 images avant l'attaque.
- Ponctuation haute collée au mot avec une espace insécable (« MARQUER ! »).

## Transitions et effets

| Effet | Usage | Paramètres |
|---|---|---|
| Flash blanc | coupe forte, panier, changement de question | 7 images : 0,12 · 0,30 · **0,50** · 0,36 · 0,17 · 0,05 · 0, pic sur la coupe (+1 image après l'entrée du ballon) |
| Zoom lent | aucun plan immobile | +2 à +6 % sur la durée du plan, alterner les directions |
| Punch | réaction, réponse drôle | 1,00 → 1,25–1,35 en 4 images |
| Ralenti | paniers, rebonds fous | 0,35–0,45×, interpolation de mouvement |
| Arrêt sur image | présentation, erreur, fin | 1,1–1,4 s, assombri, flash 30 %, son d'origine qui continue |
| Tremblement | impact | 8 images, 14 px décroissant |
| Zoom-through | fin de l'intro → vraies images | 6 images accélérées ×1,04 → ×2,26 avec flou, flash 35 % sur la coupe |
| Rembobinage | manche rejouée | image à l'envers ×3, désaturée, bruit, décalage RVB, lignes de balayage, son inversé accéléré |
| Croix « CONTESTÉ » | réponse annulée | arrêt sur image + croix rouge (échelle 2,4 → 1 en 3 images) + buzzer |

Rythme visé : un changement visuel toutes les ≈ 2 s, un zoom fort toutes les 6–7 s, ≤ 6 % d'images immobiles.

## Son (niveaux par rapport à une voix à −14 LUFS)

| Élément | Niveau |
|---|---|
| Musique sous dialogue | −18 à −20 dB (volume 0,09) ; sur l'action 0,16–0,20 ; victoire 0,32 |
| Swish / impact | au niveau des pics de voix |
| Whoosh de transition | −6 dB, pic sur la coupe |
| Ding bonne réponse / +1 | −8 / −10 dB |
| Pop d'interface, tick | −12 dB |
| Intro : voix IA | ≈ 200–215 mots/min, pauses 0,12–0,34 s |

Un SFX sur chaque transition et chaque événement de jeu ; jamais de musique qui couvre une réponse.
