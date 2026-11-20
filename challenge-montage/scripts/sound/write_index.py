# -*- coding: utf-8 -*-
"""
write_index.py - mesure chaque bruitage de assets/sfx/ et écrit assets/sfx/INDEX.md
(durée, description, usage, repère de calage, niveau conseillé et gain à appliquer pour une voix à -14 LUFS).
Les cibles de niveau (dB sous la voix) et le type de repère viennent de make_sfx.REG.
"""
import os

import numpy as np

from dsp import SR, loudness, ns, read_wav, todb, true_peak_db
from make_sfx import OUT, REG

VOICE_LUFS = -14.0

FR = {
    "whoosh_short_a": ("Whoosh court et brillant : bande de bruit qui monte puis redescend, passe de gauche à droite.", "Transition rapide, coupe sur le temps, apparition d'un texte."),
    "whoosh_short_b": ("Whoosh court plus sourd, plus « souffle », léger sifflement tonal (droite → gauche).", "Transition discrète sous une voix, changement de plan."),
    "whoosh_long_a": ("Whoosh ample qui traverse l'image de gauche à droite.", "Transition de section, zoom ou travelling, entrée d'une carte joueur."),
    "whoosh_long_b": ("Whoosh long, grave et tonal (« vvvouf »), de droite à gauche.", "Gros mouvement de caméra, passage au ralenti."),
    "whoosh_reverse_a": ("Whoosh inversé (souffle + réverbération à l'envers) qui monte et s'arrête net sur son pic.", "Aspiration juste avant une coupe ou un impact."),
    "whoosh_reverse_b": ("Cymbale à l'envers : nappe métallique qui gonfle jusqu'à la coupe.", "Montée vers un drop, un freeze frame ou l'apparition du score."),
    "impact_hit_a": ("Impact sec : coup grave à chute de hauteur + claquement + transitoire.", "Punch sur un mot clé, apparition d'un titre, tremblement d'image."),
    "impact_hit_b": ("Impact « cinéma » : grosse basse, craquement saturé, longue queue de salle.", "Gros moment : panier décisif, victoire, révélation."),
    "bass_drop_a": ("808 qui plonge (106 → 31 Hz) ; harmoniques ajoutées pour rester audible sur téléphone.", "Drop musical, moment choc, ralenti dramatique."),
    "bass_drop_b": ("808 « phonk » très distordue : chute rapide 180 → 29 Hz, grain agressif.", "Moment drôle ou choc, effet mème, entrée de drop_winner."),
    "sub_boom_a": ("Boom grave réverbéré façon mème (88 → 38 Hz, distorsion, grande réverb sombre).", "Chute comique, « bruh moment », révélation, mot choc."),
    "sub_boom_b": ("Boom plus profond et plus propre, queue plus longue.", "Suspense, apparition du score final, transition lourde."),
    "riser_a": ("Montée : bruit qui s'ouvre + accord de la mineur qui monte d'une octave + trémolo qui accélère ; s'arrête net.", "Avant un drop, un panier ou une révélation."),
    "riser_b": ("Montée sans hauteur (aucun conflit de tonalité) : souffle qui s'ouvre + roulement qui accélère ; s'arrête net.", "Suspense avant une réponse ou le dernier tir."),
    "downlifter_a": ("Descente : souffle qui se referme + double dent de scie qui chute de deux octaves.", "Retour au calme après un gros moment, fin de section, avant une explication."),
    "downlifter_b": ("Descente grave : sinus 170 → 38 Hz saturé + souffle descendant.", "Retombée après la hype, transition vers une scène calme."),
    "swish_net_a": ("« Swish » : le ballon traverse le filet sans toucher le cercle.", "Au moment EXACT où le ballon entre dans le filet (début du fichier = entrée)."),
    "swish_net_b": ("Variante plus dense et un peu plus grave du swish.", "Alterner avec swish_net_a pour éviter la répétition."),
    "ball_bounce_a": ("Rebond de ballon sur parquet, proche, petite réverb de gymnase.", "Dribble à l'image, ponctuation « pom » d'un texte, transition sportive."),
    "ball_bounce_b": ("Rebond plus lointain et plus claqué (plus de salle).", "Ambiance de match, rebond hors champ."),
    "ball_dribble": ("Dribble : 4 rebonds réguliers (0,43 s d'écart) dans un gymnase.", "Sous une présentation de joueur, transition, intro du jeu."),
    "rim_clang_a": ("Ballon sur le cercle : « clang » métallique qui résonne.", "Tir raté qui touche le cercle, tension, effet comique."),
    "rim_clang_b": ("Ballon qui tourne sur le cercle : 3 chocs métalliques (dedans-dehors).", "Tir qui hésite ou ressort, suspense avant panier ou raté."),
    "buzzer": ("Buzzer de fin de match : klaxon de salle grave et rugueux, avec résonance de salle.", "Fin du match, fin de manche, « temps écoulé » avant une réponse."),
    "whistle_a": ("Coup de sifflet d'arbitre court (sifflet à bille).", "Début ou fin d'action, faute, « stop » comique sur une erreur."),
    "whistle_b": ("Double coup de sifflet bref (« tuit-tuit »).", "Coup d'envoi, changement de joueur, rappel à l'ordre drôle."),
    "correct_ding_a": ("Validation brillante « ding-ding » (mi6 → la6, clochette + écho stéréo).", "Bonne réponse, point validé, apparition du +1."),
    "correct_ding_b": ("Validation « arpège + paillettes » (la majeur montant, scintillement aigu).", "Bonne réponse importante, point gagnant, victoire."),
    "wrong_buzz_a": ("Mauvaise réponse : double buzz grave descendant (« beu-beuuh »), drôle sans être agressif.", "Mauvaise réponse, tir raté, erreur."),
    "wrong_buzz_b": ("Mauvaise réponse cartoon : « bwoooomp » qui dégonfle (glissando descendant + wah).", "Échec comique, ballon qui rate tout, réponse absurde."),
    "sad_trombone": ("Trombone triste « wah wah wah waaah » : 4 notes chromatiques descendantes, sourdine wah, vibrato final.", "Gros raté, défaite, moment gênant (1 ou 2 fois maximum)."),
    "boing_a": ("Ressort cartoon « boyoyoing » (hauteur qui oscille puis se calme).", "Saut, rebond bizarre, chute comique, apparition rigolote."),
    "boing_b": ("Ressort plus grave et plus long (« bwoiiing »).", "Grosse chute ou gros raté comique."),
    "pop_ui_a": ("Petit « pop » de bulle (médium).", "Apparition d'un texte, d'un emoji, d'une étiquette."),
    "pop_ui_b": ("Pop plus grave et plus doux.", "Apparition d'un élément plus gros (score, photo)."),
    "pop_ui_c": ("Pop aigu très court (« blip »).", "Petits éléments en cascade (lettres, icônes, puces)."),
    "tick_a": ("Clic léger et sec.", "Mot qui apparaît dans un sous-titre animé, compteur."),
    "tick_b": ("Clic boisé plus doux (« toc »).", "Mots de sous-titres, décompte, horloge de suspense."),
    "glitch_a": ("Glitch numérique (bursts bit-crush, bégaiements, bips).", "Transition « bug », image qui saute, moment absurde."),
    "glitch_b": ("Autre glitch, séquence différente.", "Alterner avec glitch_a."),
    "camera_shutter_a": ("Déclencheur d'appareil photo (« clic-clac » mécanique).", "Freeze frame, photo de joueur, capture d'un moment."),
    "camera_shutter_b": ("Déclencheur rapide + sifflement de flash qui se recharge.", "Freeze frame « paparazzi », photo officielle de joueur."),
    "score_up_a": ("« +1 » arcade : trois notes 8-bit montantes (la5-mi6-la6) + écho.", "Point marqué, compteur de score qui augmente."),
    "score_up_b": ("« Bling » arcade : glissando 8-bit montant + écho.", "Bonus, point décisif, record, « level up »."),
    "crowd_ooh_a": ("Foule synthétique « ooooh » impressionnée (56 voix à formants, montée puis descente, grande salle).", "Beau geste, tir spectaculaire, panier improbable."),
    "crowd_ooh_b": ("Foule « ohhh… » déçue (part haut et retombe).", "Tir raté de peu, mauvaise réponse, occasion manquée."),
    "crowd_swell": ("Swell d'air sans voix (souffle filtré en « o » qui gonfle et retombe) : alternative neutre à la foule.", "Même usage que crowd_ooh si celle-ci sonne trop synthétique."),
    "heartbeat_a": ("Battement de cœur « boum-boum » ×2, lent (~70 bpm), audible sur téléphone.", "Suspense avant une réponse ou un tir décisif ; répéter toutes les 0,85 s pour prolonger."),
    "heartbeat_b": ("Battement de cœur ×2 rapide (~115 bpm).", "Dernier point, tension maximale."),
    "card_slam_a": ("Apparition de carte joueur : whoosh montant, claque, punch grave, petit « shing » métallique.", "Entrée d'une carte ou d'une photo de joueur."),
    "card_slam_b": ("Variante plus lourde (whoosh plus long, punch plus grave).", "Dernier joueur présenté, carte « MVP », révélation du gagnant."),
}


def measure(path):
    x, sr, bits = read_wav(path)
    w = ns(0.01)
    env = np.sqrt(np.convolve(np.sum(x * x, axis=1) / 2, np.ones(w) / w, mode="same"))
    L = loudness(x)
    return dict(dur=x.shape[0] / SR, m=L["M"], t_env=int(np.argmax(env)) / SR,
                peak=float(todb(np.max(np.abs(x)))), tp=true_peak_db(x), bits=bits, sr=sr, ch=x.shape[1])


def fr(v, nd=2):
    return f"{v:.{nd}f}".replace(".", ",")


def main():
    rows = []
    for name, meta in REG.items():
        m = measure(os.path.join(OUT, name + ".wav"))
        gain = round(((VOICE_LUFS + meta["target"]) - m["m"]) * 2) / 2
        sync = meta["sync"]
        if sync == "start":
            rep = "attaque à 0 s"
        elif sync == "peak":
            rep = f"pic à {fr(m['t_env'])} s : caler ce point sur la coupe"
        elif sync == "end":
            rep = f"culmine à la FIN ({fr(m['dur'])} s) : caler la fin sur l'évènement"
        else:
            rep = f"impact à {fr(m['t_env'])} s : caler ce point sur l'image"
        desc, use = FR.get(name, (meta["desc"], meta["use"]))
        rows.append((name, m, meta, rep, gain, desc, use))

    L = []
    L.append("# Banque de bruitages — challenge-montage\n")
    L.append("Tous les sons sont **100 % synthétisés** (numpy/scipy) : aucun échantillon téléchargé, aucun droit d'auteur tiers.\n")
    L.append("Format : WAV PCM 24 bits, 48 kHz, stéréo. Crête échantillon normalisée à **−1 dBFS** (crête vraie ≤ −0,3 dBTP), "
             "fondu d'entrée 2 ms et de sortie 5 ms (premier et dernier échantillons à 0), passe-haut anti-DC. "
             "Le son commence à t = 0 ; `whoosh_reverse_*` et `riser_*` démarrent bas à t = 0 et culminent à la fin.\n")
    L.append("## Régler le niveau\n")
    L.append(f"- Hypothèse : voix mixée à **{int(VOICE_LUFS)} LUFS intégré**.")
    L.append("- *Niveau conseillé* : écart visé entre la loudness momentanée max du bruitage (BS.1770, fenêtre 400 ms) "
             "et la voix. Ex. « −8 dB » = le bruitage culmine à −22 LUFS momentané.")
    L.append("- *Gain à appliquer* : gain à mettre sur le fichier pour atteindre ce niveau (ffmpeg `volume=-9dB`). "
             "Point de départ à ajuster ; baisser encore de 3 à 6 dB si le son tombe PENDANT une phrase.")
    L.append("- Exemple ffmpeg : `[2:a]volume=-9dB,adelay=12340|12340[fx1]` puis `amix=inputs=N:normalize=0`.")
    L.append("- Les sons très courts (tick, pop) se lisent bas en LUFS momentané : leurs cibles en tiennent compte.")
    L.append("- Compatibles mono (haut-parleur de téléphone) : aucune annulation de phase ; les sons à bruit décorrélé "
             "perdent au plus ~3 dB en mono. Les graves (bass_drop, sub_boom, heartbeat, impacts) ont des harmoniques "
             "au-dessus de 100 Hz pour rester perceptibles sur téléphone.\n")
    L.append("## Liste\n")
    L.append("| Fichier | Durée | Description | Utilisation conseillée | Repère de calage | Niveau conseillé | Gain à appliquer |")
    L.append("|---|---|---|---|---|---|---|")
    for name, m, meta, rep, gain, desc, use in rows:
        g = f"{gain:+.1f}".replace("-", "−").replace(".", ",")
        L.append(f"| `{name}.wav` | {fr(m['dur'])} s | {desc} | {use} | {rep} | "
                 f"{str(meta['target']).replace('-', '−')} dB sous la voix | **{g} dB** (fichier : {fr(m['m'], 1)} LUFS-M) |")
    L.append("")
    L.append("## Notes et limites\n")
    L.append("- `crowd_ooh_a` / `crowd_ooh_b` : foule synthétisée (56 à 60 voix à formants « oh/ou », hauteurs, départs et "
             "durées aléatoires, grande salle). Crédible en fond et à distance ; en solo et fort, un grain « chœur "
             "synthétique » peut s'entendre. `crowd_swell` (souffle sans voix) est l'alternative neutre.")
    L.append("- `sad_trombone`, `boing_*`, `wrong_buzz_*` : volontairement cartoon. `whistle_*` et `buzzer` : timbres "
             "proches du réel mais plus « propres » qu'un enregistrement.")
    L.append("- Repères de calage (pic, impact) mesurés sur les fichiers (enveloppe RMS 10 ms).")
    L.append("- Régénérer : `scripts/sound/make_sfx.py` puis `write_index.py` "
             "(mesures : `analyze.py`, planches spectrogrammes : `sheet.py`).")
    with open(os.path.join(OUT, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    for name, m, meta, rep, gain, desc, use in rows:
        print(f"{name:18s} {m['dur']:5.2f}s M{m['m']:6.1f} -> gain {gain:+.1f}  tp{m['tp']:6.2f}  {rep}")


if __name__ == "__main__":
    main()
