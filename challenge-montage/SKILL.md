---
name: challenge-montage
description: Monte des vidéos verticales TikTok / Reels / Shorts de défis entre amis — sport + quiz (« shoot contest », questions de culture générale, jeux à points), matchs, tournois — à partir de rushs bruts de téléphone, avec intro animée 3D qui explique les règles (mannequins, voix IA), présentation des joueurs avec cartes photo, tableau de score, questions à l'écran, sous-titres mot à mot, ralentis, arrêts sur image, rembobinage, sound design et musique originaux, générique. Utilise ce skill dès qu'on te demande de monter, éditer ou « faire un TikTok » d'une vidéo de jeu, de défi, de match ou de concours filmée entre potes, de présenter des joueurs, d'afficher un score ou des questions, de synchroniser un enregistrement audio séparé sur une vidéo, ou de corriger un montage de ce type (son coupé, faux raccords, mauvais cadrage) — même si l'utilisateur ne parle pas de « skill » ni d'HyperFrames.
---

# challenge-montage

Monter une vidéo de défi (sport + quiz, jeu à points, match entre amis) en un TikTok vertical 1080×1920 qui retient l'attention : accroche → intro animée des règles → présentation des joueurs → manches avec questions, tirs et score → victoire → bonus → générique.

Tout est rendu en local avec **HyperFrames** (HTML + GSAP + Three.js → MP4) et **ffmpeg**. Le montage est décrit par une **liste de montage** (un fichier `.config.mjs`) que des scripts transforment en composition : on modifie la liste, on régénère, on re-rend. C'est ce qui permet d'itérer vite sur les retours de l'utilisateur.

## Ce qu'il faut avoir en tête avant tout

Ces points viennent de vrais retours d'utilisateur ; ce sont eux qui font la différence entre « un assemblage » et un montage qui plaît :

1. **Le son ne doit jamais être coupé.** Une coupe au milieu d'un mot s'entend immédiatement (« des fois le son est coupé »). Lancer `scripts/check_cuts.mjs` après CHAQUE modification de la liste ; prolonger la sortie jusqu'après le dernier mot ; pas de noise gate sur les voix.
2. **Le rush est souvent un assemblage de clips** (montage rapide fait sur le téléphone). Aux jointures, quelques images d'un autre moment produisent une « scène coupée bizarre », et un enregistrement audio externe n'est synchrone que clip par clip. Repérer les jointures dès l'analyse (`references/audio.md`).
3. **Les joueurs doivent être reconnaissables.** Présentation : les laisser avancer vers la caméra, puis arrêt sur image sur leur pose et carte photo recadrée dans la source 4K, **visage visible**. Ne jamais deviner un prénom : faire valider une planche d'identification par l'utilisateur.
4. **Respecter la vérité du jeu… et l'image des organisateurs.** Reconstituer le vrai score ; mais si l'animateur valide à tort une mauvaise réponse, l'utilisateur voudra souvent la retirer et la remplacer par une grosse croix « CONTESTÉ ». Une manche rejouée se raconte avec un effet de rembobinage.
5. **Chaque saut d'image doit sembler voulu** : flash + whoosh + changement de cadrage (automatique dans `edit_build.mjs`), et une transition nette au changement de question (pas de « top » entendu avant que la question suivante n'apparaisse).
6. **Ne jamais présenter un rendu sans l'avoir regardé** : planche contact complète + images clés aux raccords modifiés (`references/qa.md`). Dire honnêtement ce qui n'a pas pu être vérifié (l'écoute).

## Déroulé

Suivre ces étapes dans l'ordre ; chaque étape renvoie au fichier de référence à lire à ce moment-là.

1. **Outils** — vérifier/installer ffmpeg, yt-dlp, whisper-ctranslate2, hyperframes (+ `hyperframes browser ensure`), edge-tts. Windows : lire `references/setup-windows.md` (Smart App Control, uv, Fontconfig…).
2. **Analyse (en parallèle si des sous-agents sont disponibles)** — `references/workflow.md` donne les briefs prêts à l'emploi :
   - rush : qui est qui (ordre de présentation), chaque question, chaque tir (réussi/raté, temps), chaque réponse, score réel, meilleurs moments, cadrage du panier, jointures de clips ;
   - son : décalage A/V, temps exact où le ballon entre, passages douteux de la transcription, silences, chaîne de nettoyage ;
   - style : mesurer les vidéos de référence de l'utilisateur (coupes, titres, sous-titres, flashs, SFX) — ou partir de `references/style-recipe.md`.
3. **Questions à l'utilisateur** (une seule fois, groupées) : identification des joueurs sur la planche, comment distinguer deux homonymes, règle réelle (« premier à 3 » vs ce qui est dit), noms propres mal transcrits, enregistrement audio de meilleure qualité disponible ?
4. **Intro animée des règles** — `scripts/intro_build.mjs` + `templates/intro-3d/` ; lire `references/intro-3d.md`.
5. **Liste de montage** — écrire `<projet>.config.mjs` (voir `examples/shoot-contest.config.mjs`, schéma complet dans `references/edl.md`), puis :
   ```bash
   node <skill>/scripts/edit_build.mjs projet.config.mjs prep        # médias (long : interpolation 30 i/s)
   node <skill>/scripts/edit_build.mjs projet.config.mjs html        # composition HyperFrames
   node <skill>/scripts/check_cuts.mjs projet.config.mjs             # mots coupés ?
   cd <root>/build/edit && hyperframes lint && hyperframes snapshot --at "t1,t2,…"
   hyperframes render -q delivery -w 3 -o final.mp4                  # en arrière-plan (≈ 5 s de calcul par seconde de vidéo)
   ```
   Pour une petite correction : `prep "id1,id2"` ne refait que ces segments (ajouter `audio` si le son change).
6. **Son** — `references/audio.md` : nettoyage, enregistrement téléphone recalé, queues de son, musique sous les voix, SFX calés à l'image.
7. **Contrôle qualité** — `node <skill>/scripts/qa_render.mjs final.mp4` puis REGARDER la planche ; checklist complète dans `references/qa.md`. Copier le rendu final dans le dossier d'export de l'utilisateur et garder les versions précédentes.

## Fichiers

| Chemin | Rôle |
|---|---|
| `scripts/edit_build.mjs` | liste de montage → médias préparés + `index.html` HyperFrames |
| `scripts/edit_template.html` | gabarit visuel du montage (titres, cartes, score, sous-titres, croix, VHS, générique) |
| `scripts/intro_build.mjs` · `templates/intro-3d/` | intro 3D des règles avec voix IA synchronisée |
| `scripts/check_cuts.mjs` | détecte les mots coupés aux entrées/sorties |
| `scripts/sync_audio.py` · `scripts/sync_window.py` | recale un enregistrement externe sur le rush |
| `scripts/qa_render.mjs` | contrôle technique d'un rendu + planche contact |
| `scripts/sound/make_sfx.py` · `make_music.py` | génèrent les bruitages et la musique (synthèse, libres de droits) |
| `assets/sfx/` | 51 bruitages prêts (`INDEX.md` : usage et gain conseillé) |
| `examples/` | liste de montage complète d'un vrai projet (anonymisée) + config d'intro |
| `references/` | `workflow.md` méthode et briefs d'agents · `edl.md` schéma de la liste · `style-recipe.md` · `audio.md` · `intro-3d.md` · `qa.md` · `setup-windows.md` · `hyperframes.md` (règles apprises) |

La musique (`assets/music/`) n'est pas versionnée : la générer une fois avec `uv run --python 3.12 --with numpy --with scipy python scripts/sound/make_music.py` (quelques minutes).

## Vie privée et droits

Les rushs montrent souvent des mineurs : ne jamais publier ni envoyer à un service externe leurs images, prénoms ou transcriptions sans l'accord de l'utilisateur. La voix IA (edge-tts) envoie seulement le texte du script des règles à Microsoft. Les vidéos de référence servent à mesurer un style : ne pas copier leurs logos, filigranes ou personnages.
