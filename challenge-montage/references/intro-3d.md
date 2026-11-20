# Intro animée « règles du jeu » (mannequins 3D)

≈ 14 s : la caméra plonge sur un terrain-île dans le vide noir, un animateur-mannequin pose une question (carte), un joueur dribble, tire, le ballon traverse le filet, il répond, +1, compteur « premier à 3 », confettis, les joueurs tombent en ligne avec leur prénom, zoom-through vers les vraies images. Voix IA synchronisée mot à mot, sous-titres karaoké, barre d'étapes, panneau néon RÉPONSE (rouge → vert), SFX et musique.

## Générer

```bash
cp <skill>/examples/intro.config.json intro.config.json      # puis l'adapter
node <skill>/scripts/intro_build.mjs intro.config.json video-agent/<projet>/build/intro
cd video-agent/<projet>/build/intro
hyperframes lint
hyperframes snapshot --at "1,3.5,5.5,7,8.5,10,12,13.5"      # REGARDER avant de rendre
hyperframes render -q delivery -w 3 -o intro.mp4
```
Puis dans la liste de montage : `PROJECT.intro` = ce fichier, segment `{ id: "intro", kind: "intro", dur: <durée affichée par intro_build> }`.

## Configuration (`intro.config.json`)

- `voice.phrases` : **11 phrases dans cet ordre**, car chaque animation se cale sur l'une d'elles :
  0 titre (« Le Shoot Contest, ») · 1 « c'est simple. » · 2 la question (contient « question ») · 3 « mais pour avoir le droit de répondre, » · 4 « il faut d'abord marquer ! » · 5 « Panier ? » · 6 « Tu réponds. » · 7 « Bonne réponse : » · 8 « un point. » · 9 la règle de victoire (contient le nombre de points puis « points », et « remporte »/« gagne ») · 10 « Place aux joueurs ! »
- `voice.gaps` : pause avant chaque phrase (s). Les valeurs fournies donnent ≈ 200 mots/min, le rythme des références.
- `voice.name`, `rate`, `tempo` : voix edge-tts, débit, accélération finale.
- `text` : tous les textes à l'écran (titre sur 2 lignes, carte question, panneau, bulle de réponse, tampon, compteur, étapes, marquage du terrain).
- `points` : cases du compteur ; `players` : 2 à 6 joueurs `{ name, color }` (couleur = maillot, anneau et étiquette ; les mêmes que dans le montage).

## Comment c'est construit

- `intro_build.mjs` génère la voix phrase par phrase (on connaît exactement les bornes de chaque phrase), coupe les silences de début/fin que edge-tts ajoute (jusqu'à 1,2 s), assemble avec les pauses voulues, répartit les mots par syllabes, calcule les temps clés `T` (contest, question, marquer, panier, bonne, point, trois, remporte, partie, joueurs…), place les bruitages et remplit `templates/intro-3d/index.template.html`.
- La scène Three.js (r149, script classique) est dessinée dans un écouteur `hf-seek` à partir du temps seul : chaque image est indépendante (rendu dans le désordre possible). Ne pas utiliser `requestAnimationFrame`.
- La chorégraphie (poses des mannequins, trajectoire du ballon, caméra) est entièrement exprimée en fonction de `T` : changer la voix recale tout.

## Adapter à un autre jeu

- Autre règle (premier à 5…) : changer la phrase 9, `text.premier`, `points`.
- Autre sport : le décor (`courtTexture`, panier) et les poses (`POSES`, `PLAYER_TRACK`) sont dans le gabarit ; garder le principe « tout dépend de T ».
- Autre structure de règles : garder 11 phrases (une peut être très courte) ou adapter la table `T` dans `intro_build.mjs` et les animations correspondantes dans le gabarit.

## Pièges rencontrés

- Titres visibles en permanence à 50 % : un `fromTo` dont la valeur de départ n'est pas 0 s'applique dès la création → `immediateRender: false`.
- `Object.assign(mesh, { position })` plante (propriété en lecture seule) : écrire `mesh.position.y = …`.
- Polices des textures 3D : créer la scène dans `document.fonts.load(...).then(boot)` et enregistrer la timeline à la fin.
- Lumières trop fortes → parquet blanc : exposition ≈ 0,92, spot principal 1,55.
- Éléments d'interface qui se chevauchent : titres en haut (230–560 px), barre d'étapes à 606 px, carte question ancrée à côté de la tête de l'animateur, sous-titres à 1 370 px.
