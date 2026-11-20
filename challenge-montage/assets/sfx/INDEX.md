# Banque de bruitages — challenge-montage

Tous les sons sont **100 % synthétisés** (numpy/scipy) : aucun échantillon téléchargé, aucun droit d'auteur tiers.

Format : WAV PCM 24 bits, 48 kHz, stéréo. Crête échantillon normalisée à **−1 dBFS** (crête vraie ≤ −0,3 dBTP), fondu d'entrée 2 ms et de sortie 5 ms (premier et dernier échantillons à 0), passe-haut anti-DC. Le son commence à t = 0 ; `whoosh_reverse_*` et `riser_*` démarrent bas à t = 0 et culminent à la fin.

## Régler le niveau

- Hypothèse : voix mixée à **-14 LUFS intégré**.
- *Niveau conseillé* : écart visé entre la loudness momentanée max du bruitage (BS.1770, fenêtre 400 ms) et la voix. Ex. « −8 dB » = le bruitage culmine à −22 LUFS momentané.
- *Gain à appliquer* : gain à mettre sur le fichier pour atteindre ce niveau (ffmpeg `volume=-9dB`). Point de départ à ajuster ; baisser encore de 3 à 6 dB si le son tombe PENDANT une phrase.
- Exemple ffmpeg : `[2:a]volume=-9dB,adelay=12340|12340[fx1]` puis `amix=inputs=N:normalize=0`.
- Les sons très courts (tick, pop) se lisent bas en LUFS momentané : leurs cibles en tiennent compte.
- Compatibles mono (haut-parleur de téléphone) : aucune annulation de phase ; les sons à bruit décorrélé perdent au plus ~3 dB en mono. Les graves (bass_drop, sub_boom, heartbeat, impacts) ont des harmoniques au-dessus de 100 Hz pour rester perceptibles sur téléphone.

## Liste

| Fichier | Durée | Description | Utilisation conseillée | Repère de calage | Niveau conseillé | Gain à appliquer |
|---|---|---|---|---|---|---|
| `whoosh_short_a.wav` | 0,25 s | Whoosh court et brillant : bande de bruit qui monte puis redescend, passe de gauche à droite. | Transition rapide, coupe sur le temps, apparition d'un texte. | pic à 0,10 s : caler ce point sur la coupe | −8 dB sous la voix | **−8,0 dB** (fichier : -13,9 LUFS-M) |
| `whoosh_short_b.wav` | 0,25 s | Whoosh court plus sourd, plus « souffle », léger sifflement tonal (droite → gauche). | Transition discrète sous une voix, changement de plan. | pic à 0,10 s : caler ce point sur la coupe | −9 dB sous la voix | **−8,5 dB** (fichier : -14,5 LUFS-M) |
| `whoosh_long_a.wav` | 0,60 s | Whoosh ample qui traverse l'image de gauche à droite. | Transition de section, zoom ou travelling, entrée d'une carte joueur. | pic à 0,29 s : caler ce point sur la coupe | −8 dB sous la voix | **−10,5 dB** (fichier : -11,3 LUFS-M) |
| `whoosh_long_b.wav` | 0,60 s | Whoosh long, grave et tonal (« vvvouf »), de droite à gauche. | Gros mouvement de caméra, passage au ralenti. | pic à 0,28 s : caler ce point sur la coupe | −8 dB sous la voix | **−9,5 dB** (fichier : -12,4 LUFS-M) |
| `whoosh_reverse_a.wav` | 0,80 s | Whoosh inversé (souffle + réverbération à l'envers) qui monte et s'arrête net sur son pic. | Aspiration juste avant une coupe ou un impact. | culmine à la FIN (0,80 s) : caler la fin sur l'évènement | −8 dB sous la voix | **−9,0 dB** (fichier : -13,0 LUFS-M) |
| `whoosh_reverse_b.wav` | 1,00 s | Cymbale à l'envers : nappe métallique qui gonfle jusqu'à la coupe. | Montée vers un drop, un freeze frame ou l'apparition du score. | culmine à la FIN (1,00 s) : caler la fin sur l'évènement | −9 dB sous la voix | **−12,0 dB** (fichier : -11,1 LUFS-M) |
| `impact_hit_a.wav` | 1,00 s | Impact sec : coup grave à chute de hauteur + claquement + transitoire. | Punch sur un mot clé, apparition d'un titre, tremblement d'image. | attaque à 0 s | −4 dB sous la voix | **−8,5 dB** (fichier : -9,3 LUFS-M) |
| `impact_hit_b.wav` | 2,00 s | Impact « cinéma » : grosse basse, craquement saturé, longue queue de salle. | Gros moment : panier décisif, victoire, révélation. | attaque à 0 s | −5 dB sous la voix | **−9,5 dB** (fichier : -9,7 LUFS-M) |
| `bass_drop_a.wav` | 1,50 s | 808 qui plonge (106 → 31 Hz) ; harmoniques ajoutées pour rester audible sur téléphone. | Drop musical, moment choc, ralenti dramatique. | attaque à 0 s | −4 dB sous la voix | **−13,5 dB** (fichier : -4,7 LUFS-M) |
| `bass_drop_b.wav` | 1,50 s | 808 « phonk » très distordue : chute rapide 180 → 29 Hz, grain agressif. | Moment drôle ou choc, effet mème, entrée de drop_winner. | attaque à 0 s | −4 dB sous la voix | **−9,5 dB** (fichier : -8,4 LUFS-M) |
| `sub_boom_a.wav` | 1,20 s | Boom grave réverbéré façon mème (88 → 38 Hz, distorsion, grande réverb sombre). | Chute comique, « bruh moment », révélation, mot choc. | attaque à 0 s | −3 dB sous la voix | **−5,5 dB** (fichier : -11,5 LUFS-M) |
| `sub_boom_b.wav` | 1,20 s | Boom plus profond et plus propre, queue plus longue. | Suspense, apparition du score final, transition lourde. | attaque à 0 s | −3 dB sous la voix | **−6,5 dB** (fichier : -10,6 LUFS-M) |
| `riser_a.wav` | 2,00 s | Montée : bruit qui s'ouvre + accord de la mineur qui monte d'une octave + trémolo qui accélère ; s'arrête net. | Avant un drop, un panier ou une révélation. | culmine à la FIN (2,00 s) : caler la fin sur l'évènement | −10 dB sous la voix | **−14,0 dB** (fichier : -9,8 LUFS-M) |
| `riser_b.wav` | 2,00 s | Montée sans hauteur (aucun conflit de tonalité) : souffle qui s'ouvre + roulement qui accélère ; s'arrête net. | Suspense avant une réponse ou le dernier tir. | culmine à la FIN (2,00 s) : caler la fin sur l'évènement | −10 dB sous la voix | **−15,0 dB** (fichier : -8,9 LUFS-M) |
| `downlifter_a.wav` | 1,00 s | Descente : souffle qui se referme + double dent de scie qui chute de deux octaves. | Retour au calme après un gros moment, fin de section, avant une explication. | attaque à 0 s | −10 dB sous la voix | **−14,0 dB** (fichier : -10,2 LUFS-M) |
| `downlifter_b.wav` | 1,00 s | Descente grave : sinus 170 → 38 Hz saturé + souffle descendant. | Retombée après la hype, transition vers une scène calme. | attaque à 0 s | −9 dB sous la voix | **−12,5 dB** (fichier : -10,7 LUFS-M) |
| `swish_net_a.wav` | 0,35 s | « Swish » : le ballon traverse le filet sans toucher le cercle. | Au moment EXACT où le ballon entre dans le filet (début du fichier = entrée). | attaque à 0 s | −6 dB sous la voix | **−3,5 dB** (fichier : -16,3 LUFS-M) |
| `swish_net_b.wav` | 0,35 s | Variante plus dense et un peu plus grave du swish. | Alterner avec swish_net_a pour éviter la répétition. | attaque à 0 s | −6 dB sous la voix | **−5,0 dB** (fichier : -14,8 LUFS-M) |
| `ball_bounce_a.wav` | 0,90 s | Rebond de ballon sur parquet, proche, petite réverb de gymnase. | Dribble à l'image, ponctuation « pom » d'un texte, transition sportive. | attaque à 0 s | −8 dB sous la voix | **−6,0 dB** (fichier : -15,8 LUFS-M) |
| `ball_bounce_b.wav` | 0,90 s | Rebond plus lointain et plus claqué (plus de salle). | Ambiance de match, rebond hors champ. | attaque à 0 s | −8 dB sous la voix | **−6,0 dB** (fichier : -16,0 LUFS-M) |
| `ball_dribble.wav` | 1,90 s | Dribble : 4 rebonds réguliers (0,43 s d'écart) dans un gymnase. | Sous une présentation de joueur, transition, intro du jeu. | attaque à 0 s | −8 dB sous la voix | **−6,5 dB** (fichier : -15,7 LUFS-M) |
| `rim_clang_a.wav` | 1,20 s | Ballon sur le cercle : « clang » métallique qui résonne. | Tir raté qui touche le cercle, tension, effet comique. | attaque à 0 s | −8 dB sous la voix | **−11,5 dB** (fichier : -10,4 LUFS-M) |
| `rim_clang_b.wav` | 1,50 s | Ballon qui tourne sur le cercle : 3 chocs métalliques (dedans-dehors). | Tir qui hésite ou ressort, suspense avant panier ou raté. | attaque à 0 s | −8 dB sous la voix | **−12,0 dB** (fichier : -10,0 LUFS-M) |
| `buzzer.wav` | 1,00 s | Buzzer de fin de match : klaxon de salle grave et rugueux, avec résonance de salle. | Fin du match, fin de manche, « temps écoulé » avant une réponse. | attaque à 0 s | −6 dB sous la voix | **−14,0 dB** (fichier : -6,0 LUFS-M) |
| `whistle_a.wav` | 0,75 s | Coup de sifflet d'arbitre court (sifflet à bille). | Début ou fin d'action, faute, « stop » comique sur une erreur. | attaque à 0 s | −8 dB sous la voix | **−20,5 dB** (fichier : -1,6 LUFS-M) |
| `whistle_b.wav` | 0,65 s | Double coup de sifflet bref (« tuit-tuit »). | Coup d'envoi, changement de joueur, rappel à l'ordre drôle. | attaque à 0 s | −8 dB sous la voix | **−18,0 dB** (fichier : -4,2 LUFS-M) |
| `correct_ding_a.wav` | 1,00 s | Validation brillante « ding-ding » (mi6 → la6, clochette + écho stéréo). | Bonne réponse, point validé, apparition du +1. | attaque à 0 s | −8 dB sous la voix | **−16,5 dB** (fichier : -5,7 LUFS-M) |
| `correct_ding_b.wav` | 1,20 s | Validation « arpège + paillettes » (la majeur montant, scintillement aigu). | Bonne réponse importante, point gagnant, victoire. | attaque à 0 s | −8 dB sous la voix | **−13,0 dB** (fichier : -8,8 LUFS-M) |
| `wrong_buzz_a.wav` | 0,75 s | Mauvaise réponse : double buzz grave descendant (« beu-beuuh »), drôle sans être agressif. | Mauvaise réponse, tir raté, erreur. | attaque à 0 s | −6 dB sous la voix | **−14,5 dB** (fichier : -5,6 LUFS-M) |
| `wrong_buzz_b.wav` | 0,70 s | Mauvaise réponse cartoon : « bwoooomp » qui dégonfle (glissando descendant + wah). | Échec comique, ballon qui rate tout, réponse absurde. | attaque à 0 s | −6 dB sous la voix | **−10,0 dB** (fichier : -10,0 LUFS-M) |
| `sad_trombone.wav` | 2,75 s | Trombone triste « wah wah wah waaah » : 4 notes chromatiques descendantes, sourdine wah, vibrato final. | Gros raté, défaite, moment gênant (1 ou 2 fois maximum). | attaque à 0 s | −6 dB sous la voix | **−11,5 dB** (fichier : -8,3 LUFS-M) |
| `boing_a.wav` | 0,80 s | Ressort cartoon « boyoyoing » (hauteur qui oscille puis se calme). | Saut, rebond bizarre, chute comique, apparition rigolote. | attaque à 0 s | −8 dB sous la voix | **−12,5 dB** (fichier : -9,6 LUFS-M) |
| `boing_b.wav` | 1,00 s | Ressort plus grave et plus long (« bwoiiing »). | Grosse chute ou gros raté comique. | attaque à 0 s | −8 dB sous la voix | **−12,5 dB** (fichier : -9,3 LUFS-M) |
| `pop_ui_a.wav` | 0,09 s | Petit « pop » de bulle (médium). | Apparition d'un texte, d'un emoji, d'une étiquette. | attaque à 0 s | −14 dB sous la voix | **−10,5 dB** (fichier : -17,6 LUFS-M) |
| `pop_ui_b.wav` | 0,10 s | Pop plus grave et plus doux. | Apparition d'un élément plus gros (score, photo). | attaque à 0 s | −14 dB sous la voix | **−11,0 dB** (fichier : -16,9 LUFS-M) |
| `pop_ui_c.wav` | 0,07 s | Pop aigu très court (« blip »). | Petits éléments en cascade (lettres, icônes, puces). | attaque à 0 s | −15 dB sous la voix | **−11,5 dB** (fichier : -17,6 LUFS-M) |
| `tick_a.wav` | 0,03 s | Clic léger et sec. | Mot qui apparaît dans un sous-titre animé, compteur. | attaque à 0 s | −18 dB sous la voix | **−8,5 dB** (fichier : -23,7 LUFS-M) |
| `tick_b.wav` | 0,05 s | Clic boisé plus doux (« toc »). | Mots de sous-titres, décompte, horloge de suspense. | attaque à 0 s | −18 dB sous la voix | **−12,5 dB** (fichier : -19,7 LUFS-M) |
| `glitch_a.wav` | 0,30 s | Glitch numérique (bursts bit-crush, bégaiements, bips). | Transition « bug », image qui saute, moment absurde. | attaque à 0 s | −10 dB sous la voix | **−9,5 dB** (fichier : -14,4 LUFS-M) |
| `glitch_b.wav` | 0,30 s | Autre glitch, séquence différente. | Alterner avec glitch_a. | attaque à 0 s | −10 dB sous la voix | **−11,5 dB** (fichier : -12,5 LUFS-M) |
| `camera_shutter_a.wav` | 0,24 s | Déclencheur d'appareil photo (« clic-clac » mécanique). | Freeze frame, photo de joueur, capture d'un moment. | attaque à 0 s | −10 dB sous la voix | **−1,0 dB** (fichier : -22,9 LUFS-M) |
| `camera_shutter_b.wav` | 0,45 s | Déclencheur rapide + sifflement de flash qui se recharge. | Freeze frame « paparazzi », photo officielle de joueur. | attaque à 0 s | −10 dB sous la voix | **−2,5 dB** (fichier : -21,6 LUFS-M) |
| `score_up_a.wav` | 0,65 s | « +1 » arcade : trois notes 8-bit montantes (la5-mi6-la6) + écho. | Point marqué, compteur de score qui augmente. | attaque à 0 s | −9 dB sous la voix | **−15,5 dB** (fichier : -7,4 LUFS-M) |
| `score_up_b.wav` | 0,55 s | « Bling » arcade : glissando 8-bit montant + écho. | Bonus, point décisif, record, « level up ». | attaque à 0 s | −9 dB sous la voix | **−14,0 dB** (fichier : -8,9 LUFS-M) |
| `crowd_ooh_a.wav` | 2,40 s | Foule synthétique « ooooh » impressionnée (56 voix à formants, montée puis descente, grande salle). | Beau geste, tir spectaculaire, panier improbable. | attaque à 0 s | −8 dB sous la voix | **−12,0 dB** (fichier : -10,1 LUFS-M) |
| `crowd_ooh_b.wav` | 1,80 s | Foule « ohhh… » déçue (part haut et retombe). | Tir raté de peu, mauvaise réponse, occasion manquée. | attaque à 0 s | −8 dB sous la voix | **−13,0 dB** (fichier : -9,0 LUFS-M) |
| `crowd_swell.wav` | 2,00 s | Swell d'air sans voix (souffle filtré en « o » qui gonfle et retombe) : alternative neutre à la foule. | Même usage que crowd_ooh si celle-ci sonne trop synthétique. | pic à 0,90 s : caler ce point sur la coupe | −10 dB sous la voix | **−15,0 dB** (fichier : -8,8 LUFS-M) |
| `heartbeat_a.wav` | 1,55 s | Battement de cœur « boum-boum » ×2, lent (~70 bpm), audible sur téléphone. | Suspense avant une réponse ou un tir décisif ; répéter toutes les 0,85 s pour prolonger. | attaque à 0 s | −6 dB sous la voix | **−10,0 dB** (fichier : -10,1 LUFS-M) |
| `heartbeat_b.wav` | 1,05 s | Battement de cœur ×2 rapide (~115 bpm). | Dernier point, tension maximale. | attaque à 0 s | −6 dB sous la voix | **−10,0 dB** (fichier : -10,2 LUFS-M) |
| `card_slam_a.wav` | 1,10 s | Apparition de carte joueur : whoosh montant, claque, punch grave, petit « shing » métallique. | Entrée d'une carte ou d'une photo de joueur. | impact à 0,26 s : caler ce point sur l'image | −6 dB sous la voix | **−7,5 dB** (fichier : -12,5 LUFS-M) |
| `card_slam_b.wav` | 1,30 s | Variante plus lourde (whoosh plus long, punch plus grave). | Dernier joueur présenté, carte « MVP », révélation du gagnant. | impact à 0,36 s : caler ce point sur l'image | −6 dB sous la voix | **−7,5 dB** (fichier : -12,5 LUFS-M) |

## Notes et limites

- `crowd_ooh_a` / `crowd_ooh_b` : foule synthétisée (56 à 60 voix à formants « oh/ou », hauteurs, départs et durées aléatoires, grande salle). Crédible en fond et à distance ; en solo et fort, un grain « chœur synthétique » peut s'entendre. `crowd_swell` (souffle sans voix) est l'alternative neutre.
- `sad_trombone`, `boing_*`, `wrong_buzz_*` : volontairement cartoon. `whistle_*` et `buzzer` : timbres proches du réel mais plus « propres » qu'un enregistrement.
- Repères de calage (pic, impact) mesurés sur les fichiers (enveloppe RMS 10 ms).
- Régénérer : `scripts/sound/make_sfx.py` puis `write_index.py` (mesures : `analyze.py`, planches spectrogrammes : `sheet.py`).
