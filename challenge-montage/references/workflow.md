# Méthode complète (de rushs bruts à la vidéo finale)

## Sommaire
1. Organisation des dossiers
2. Premières mesures (à faire soi-même, 5 minutes)
3. Analyse en parallèle : briefs des agents
4. Ce qu'il faut demander à l'utilisateur
5. Structure type du montage
6. Itérer sur les retours

## 1. Organisation des dossiers

Respecter les dossiers de l'utilisateur s'il en a (ex. `A-roll/` rushs, `Références/` vidéos de style, `Exports/` rendus). Ne jamais modifier ni supprimer les fichiers sources. Tout le travail va dans un dossier à part, par exemple :

```
video-agent/<projet>/
  BRIEF.md            contexte partagé par tous les agents (sources, objectifs, contraintes machine)
  work/               audio extrait, proxy, transcriptions, planches contact
  analysis/           rush.md/json, audio.md/json, style.md, portraits/
  build/intro/        projet HyperFrames de l'intro 3D
  build/edit/         projet HyperFrames du montage (créé par edit_build.mjs)
  <projet>.config.mjs liste de montage
```

Écrire `BRIEF.md` en premier : chaque agent démarre sans contexte, le brief lui évite de tout redécouvrir (sources, durées, ce qu'on sait déjà, commandes qui marchent sur cette machine, RAM disponible).

## 2. Premières mesures

```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,avg_frame_rate -of compact rush.mov
ffmpeg -i rush.mov -vn -ac 1 -ar 16000 work/rush.wav
ffmpeg -i rush.mov -vf "scale=540:960,fps=30" -c:v libx264 -crf 23 -preset veryfast -c:a aac work/rush_proxy.mp4
# planches contact horodatées (sous Windows, drawtext exige fontfile=)
ffmpeg -i work/rush_proxy.mp4 -vf "fps=1/3,scale=216:384,drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='%{pts\:hms}':x=4:y=4:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=5x4" work/sheets/rush_%02d.jpg
whisper-ctranslate2 work/rush.wav --model large-v3-turbo --language fr --word_timestamps True --output_dir work --output_format all
```

Regarder les planches soi-même : c'est la seule façon de comprendre le jeu (qui présente, qui joue, où est le panier). Points à noter tout de suite :
- **cadence** : beaucoup d'iPhone donnent 16 i/s en cadence variable → interpolation obligatoire (faite par `edit_build.mjs`) ;
- **jointures** : changements brusques de cadrage/lieu = le rush est un assemblage de clips (`ffmpeg -vf "select='gt(scene,0.3)',showinfo"` les liste) ;
- **passages que whisper saute** (cris, bruit) : re-transcrire l'extrait seul, nettoyé (`highpass=f=120,dynaudnorm`), avec `--vad_filter False --condition_on_previous_text False`, avec deux modèles ; si un prénom reste inaudible, c'est à l'utilisateur de le dire.

## 3. Analyse en parallèle : briefs des agents

Si des sous-agents sont disponibles, en lancer 3 ou 4 en même temps (et pas plus si la machine a peu de RAM : 1 seul whisper à la fois). Chaque brief : « lis d'abord BRIEF.md », ce qu'on sait déjà, la mission numérotée par priorité, les livrables exacts, un rapport court. Si un agent est interrompu (limite d'utilisation), le relancer avec un message qui dit de reprendre sans refaire et d'aller droit aux livrables.

**Agent rush** — livrables `analysis/rush.md`, `rush.json`, `portraits/IDENTIFICATION.jpg` :
1. identifier animateurs et joueurs (tenue, cheveux, chaussures) et l'ordre de présentation (qui s'avance à chaque cri) ; aucun prénom sans preuve, marquer « à confirmer » ;
2. déroulé de chaque question : texte et temps, chaque tir (lâcher, arrivée au cercle, réussi/raté, tireur), qui répond, quoi, juste/faux, score après chaque question ;
3. meilleurs moments (entrée/sortie + raison), temps morts à couper ;
4. position du panier (x, y normalisés) par passage, plans flous/tremblés, jointures de clips ;
5. portraits 4K nets par personne + planche d'identification étiquetée (P1… avec tenue et moment) que l'utilisateur annote.

**Agent son et synchro** — livrables `analysis/audio.md`, `audio.json` :
1. décalage A/V mesuré en ≥ 4 points (rebond, cercle, claquement) et à chaque jointure ;
2. temps exact (à l'image) où le ballon passe le cercle pour chaque panier réussi ; tirs ratés ;
3. qui parle (lignes incertaines marquées) ; relecture des passages douteux par re-transcription d'extraits nettoyés ;
4. silences à couper ; loudness, bruit, réverbération ; chaîne de nettoyage testée sur 20 s (avant/après).

**Agent style** (si l'utilisateur fournit des vidéos de référence) — livrables `analysis/style.md`, `style_frames/` :
mesurer, pas deviner : coupes (`scene > 0.15`), durée des plans, flashs (luminance par image), titres (police, couleurs, position, animation image par image), sous-titres (mots par groupe, position, style du mot surligné), SFX (spectrogrammes), musique vs voix (dB), débit de la voix off (mots/min). Terminer par une recette chiffrée pour 1080×1920. Sans référence, utiliser `style-recipe.md`.

**Agent création sonore** — exécuter `scripts/sound/make_sfx.py` / `make_music.py`, vérifier par la mesure (pics, clics, loudness ; il ne peut pas écouter), écrire l'index.

Pendant que les agents travaillent : préparer ce qui n'en dépend pas (intro, voix IA, test de rendu HyperFrames). Ne jamais annoncer un résultat d'agent avant d'avoir reçu son rapport, et vérifier ses fichiers avant de s'en servir.

## 4. Ce qu'il faut demander à l'utilisateur

Une seule fois, regroupé, avec la planche d'identification envoyée :
- prénoms sur la planche (et comment distinguer deux homonymes : « PRÉNOM 1 / PRÉNOM 2 »…) ;
- la règle réelle si la vidéo dit autre chose que son brief (ex. « 5 réponses » annoncées, partie jouée en 3 points) ;
- noms propres inaudibles (le nom d'un prof…) — ne jamais en afficher un deviné ;
- existe-t-il un enregistrement audio de meilleure qualité (dictaphone du téléphone) ?
- crédits de fin souhaités.

## 5. Structure type du montage (≈ 2 min 30)

1. **Accroche (3 s)** : le moment le plus drôle, arrêt sur image + buzzer + « COMMENT ON EN EST LÀ ? ».
2. **Intro 3D des règles (≈ 14 s)**, voix IA.
3. **Présentation des joueurs** : chaque joueur avance (1,2–2 s, zoom qui le suit) puis arrêt sur image + carte photo + prénom (1,3 s), cris conservés sous l'arrêt.
4. **Manches** : étiquette (duel / groupe) + carte question pendant que l'animateur lit ; tirs (ralenti 0,4× sur les paniers, swish à l'image exacte, flash, titre) ; réponse sous-titrée ; BONNE RÉPONSE + score, ou buzzer + croix / « 2008 ?! » + la vraie réponse en bandeau ; passages longs accélérés (×1,6 à ×3) avec un mot BD (« RATÉ… RATÉ… »).
5. **Victoire** : noir « ET LE GAGNANT EST… » (battement de cœur) → annonce → impact + confettis + carte VAINQUEUR.
6. **Score final** + appel à s'abonner, **bonus** éventuel (« VIDÉO BONUS · … » au ralenti), **générique** sur fond noir.

## 6. Itérer sur les retours

- Corriger dans la liste de montage, `prep` seulement les segments touchés, `html`, `check_cuts`, snapshots aux endroits modifiés, rendu.
- Un seul rendu par série de corrections : si une information arrive bientôt (fichier audio promis), attendre pour ne rendre qu'une fois.
- Numéroter les versions dans le dossier d'export (v2, v3…, FINALE) et résumer ce qui a changé et ce qui n'a pas pu être vérifié.
