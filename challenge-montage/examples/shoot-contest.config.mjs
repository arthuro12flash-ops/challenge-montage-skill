// Exemple complet : « Shoot Contest » (basket × quiz de physique-chimie), monté pour TikTok en 1080×1920.
// C'est la liste de montage réelle d'un projet (2 min 38), anonymisée : remplacez les chemins, les joueurs et les temps.
// Temps « in/out/at/src » = secondes dans le rush ; « t » = secondes depuis le début du segment monté. Voir references/edl.md.
// Joueurs : 0 → JOUEUR 1 … 4 → JOUEUR 5 (même ordre que la présentation filmée).
export const PROJECT = {
  root: "video-agent/montage",                    // dossier de travail (build/edit y est créé)
  rush: "A-roll/rush.mov",                        // rush principal (ici un assemblage de clips iPhone 4K, 16 i/s)
  transcript: "video-agent/montage/work/rush.json", // whisper-ctranslate2 --word_timestamps True --output_format json
  intro: "video-agent/montage/build/intro/intro.mp4", // rendu de l'intro 3D (scripts/intro_build.mjs)
  // Enregistrement téléphone (meilleur son) recalé PAR CLIP caméra avec scripts/sync_window.py : off = temps rush − temps téléphone.
  phones: [
    { file: "A-roll/memo-q2.m4a", transcript: "video-agent/montage/work/phone.json", pieces: [{ a: 79.9, b: 119.35, off: 77.194 }] },
  ],
  players: [
    { name: "JOUEUR 1", color: "#f07a1a", photo: "video-agent/montage/cards/P1.jpg" },
    { name: "JOUEUR 2", color: "#3ddffe", photo: "video-agent/montage/cards/P2.jpg" },
    { name: "JOUEUR 3", color: "#7dc696", photo: "video-agent/montage/cards/P3.jpg" },
    { name: "JOUEUR 4", color: "#fd3a4c", photo: "video-agent/montage/cards/P4.jpg" },
    { name: "JOUEUR 5", color: "#fcc52e", photo: "video-agent/montage/cards/P5.jpg" },
  ],
  // corrections de la transcription (mot en minuscules sans ponctuation → texte affiché)
  fix: { "née": "NÉ", "ganas": "GAGNANT", "créée": "FORMÉE" },
  maxPoints: 3,
  text: { finalCta: "ABONNE-TOI POUR LE PROCHAIN SHOOT CONTEST" },
  credits: { by: "VIDÉO PRODUITE PAR", lines: ["PRÉNOM", "& PRÉNOM"], sub: "SHOOT CONTEST · BASKET × PHYSIQUE-CHIMIE" },
};
const PLAYERS = PROJECT.players;

const swish = (at, v = 0.85) => ({ at, type: "sfx", sfx: at % 2 > 1 ? "swish_net_b" : "swish_net_a", vol: v });
const panier = (at, txt = "PANIER !") => [swish(at), { at: at + 0.033, type: "flash" }, { at, type: "title", dur: 1.1, lines: [[txt, "c"]] }, { at, type: "shake" }];
const question = (label, text, who, at, dur) => [
  { at, type: "label", dur, text: who },
  { at: at + 0.2, type: "qcard", dur: dur - 0.3, label, text },
  { at: at + 0.2, type: "sfx", sfx: "card_slam_a", vol: 0.45 },
];

export const SEGMENTS = [
  // ------------------------------------------------------------- ACCROCHE (cold open)
  { id: "h1", in: 174.82, out: 177.15, cap: true, music: "none", zoom: [1.12, 0.56, 0.42, 1.32, 0.56, 0.42],
    events: [{ at: 174.9, type: "qcard", dur: 2.2, label: "QUESTION 4", text: "Il y a combien de temps la Terre s'est formée ?" }] },
  { id: "h2", kind: "freeze", src: 177.1, dur: 1.4, music: "none", zoom: [1.32, 0.56, 0.42, 1.42, 0.56, 0.42],
    events: [
      { t: 0, type: "sfx", sfx: "wrong_buzz_a", vol: 0.6 }, { t: 0, type: "flash" },
      { t: 0.02, type: "title", dur: 0.62, lines: [["2008 ?!", "r"]] },
      { t: 0.66, type: "title", dur: 0.74, lines: [["COMMENT ON", "w"], ["EN EST LÀ ?", "y"]] },
      { t: 0.66, type: "sfx", sfx: "glitch_a", vol: 0.5 }, { t: 1.05, type: "sfx", sfx: "whoosh_reverse_a", vol: 0.5 },
    ] },
  // ------------------------------------------------------------- INTRO 3D (rendu séparé, avec sa voix et ses sons)
  { id: "intro", kind: "intro", dur: 13.3, music: "none" },
  // ------------------------------------------------------------- PRÉSENTATION DES JOUEURS
  // chaque joueur avance vers la caméra (entrée → pose), puis arrêt sur image avec sa carte photo
  ...[[16.9, 19.0, 0, 0.5, 0.6], [21.0, 22.6, 1, 0.4, 0.56], [25.0, 26.4, 2, 0.4, 0.58], [28.6, 29.8, 3, 0.45, 0.55], [31.6, 33.0, 4, 0.6, 0.56]].flatMap(([a, b, p, x, y], i) => [
    { id: `p${p}l`, in: a, out: b, music: "players", zoom: [1.0, x, y, 1.28, x, y], events: i === 0 ? [{ t: 0, type: "sfx", sfx: "impact_hit_a", vol: 0.6 }] : [{ t: 0, type: "sfx", sfx: "whoosh_short_a", vol: 0.4 }] },
    { id: `p${p}f`, kind: "freeze", src: b, dur: 1.3, audioThrough: 0.6, music: "players", dim: true, zoom: [1.28, x, y, 1.36, x, y],
      events: [{ t: 0, type: "card", player: p, dur: 1.3 }, { t: 0, type: "sfx", sfx: "card_slam_b", vol: 0.55 }, { t: 0, type: "sfx", sfx: "camera_shutter_a", vol: 0.35 }, { t: 0, type: "flash", peak: 0.3 }] },
  ]),
  // ------------------------------------------------------------- QUESTION 1 (duel Joueur 4 / Joueur 5)
  { id: "q1a", in: 49.25, out: 53.6, cap: true, music: "game", zoom: [1.0, 0.5, 0.45, 1.08, 0.5, 0.45],
    events: [{ at: 49.25, type: "hud" }, ...question("QUESTION 1", "Combien y a-t-il de planètes dans le système solaire ?", "DUEL · JOUEUR 4 vs JOUEUR 5", 49.25, 4.35)] },
  { id: "q1b", in: 53.6, out: 54.7, music: "game", zoom: [1.08, 0.5, 0.4, 1.16, 0.5, 0.4] },
  { id: "q1c", in: 54.7, out: 55.6, speed: 0.4, music: "game", zoom: [1.2, 0.52, 0.4, 1.45, 0.5, 0.39], events: panier(55.135) },
  { id: "q1d", in: 56.4, out: 61.4, cap: true, music: "game", zoom: [1.0, 0.78, 0.5, 1.22, 0.78, 0.5],
    events: [
      { at: 57.45, type: "sfx", sfx: "wrong_buzz_b", vol: 0.45 }, { at: 57.45, type: "title", dur: 0.9, lines: [["7 ?!", "r"]] },
      { at: 58.4, type: "title", dur: 1.2, lines: [["NON… 8 !", "y"]] }, { at: 60.2, type: "wow", dur: 0.7, text: "CONTESTÉ !" },
    ] },
  // réponse contestée → rembobinage façon cassette VHS, puis la question est reposée
  { id: "q1rw", in: 58.4, out: 61.4, speed: 3, reverse: true, music: "none",
    events: [{ t: 0, type: "vhs", dur: 1.0, text: "◀◀ REMBOBINAGE" }, { t: 0, type: "sfx", sfx: "glitch_b", vol: 0.5 }, { t: 0.05, type: "title", dur: 0.95, lines: [["ON", "w"], ["RECOMMENCE !", "y"]] }, { t: 0.6, type: "sfx", sfx: "whoosh_reverse_b", vol: 0.45 }] },
  { id: "q1e", in: 65.5, out: 69.7, cap: true, fix: { combien: "COMBIEN Y" }, music: "game", zoom: [1.0, 0.5, 0.45, 1.1, 0.5, 0.42],
    events: [{ t: 0, type: "flash", peak: 0.45 }, { at: 65.6, type: "qcard", dur: 2.9, label: "QUESTION 1 · ON REJOUE", text: "Combien y a-t-il de planètes dans le système solaire ?" }, { at: 65.6, type: "sfx", sfx: "card_slam_a", vol: 0.45 }] },
  { id: "q1f", in: 69.7, out: 71.2, speed: 0.45, music: "game", zoom: [1.2, 0.5, 0.38, 1.5, 0.5, 0.38],
    events: [
      { at: 69.95, type: "sfx", sfx: "rim_clang_a", vol: 0.6 }, { at: 69.95, type: "title", dur: 2.0, lines: [["LE REBOND", "w"], ["DE LA FOLIE", "y"]] },
      { at: 70.4, type: "sfx", sfx: "boing_a", vol: 0.45 }, swish(70.858), { at: 70.89, type: "flash" },
    ] },
  // après le rebond rentré, on passe directement à la bonne réponse de Joueur 5 (gros plan sur lui pour masquer le saut)
  { id: "q1g", in: 76.7, out: 78.28, cap: true, tail: 0.04, music: "game", zoom: [1.35, 0.8, 0.5, 1.45, 0.8, 0.5],
    events: [{ t: 0, type: "flash", peak: 0.3 }, { t: 0, type: "sfx", sfx: "whoosh_short_a", vol: 0.35 }, { at: 77.0, type: "sfx", sfx: "correct_ding_a", vol: 0.6 },
      { at: 77.0, type: "title", dur: 1.3, lines: [["BONNE RÉPONSE", "g"]] }, { at: 77.05, type: "score", player: 4, pts: 1 }] },
  // ------------------------------------------------------------- QUESTION 2 (mêlée Joueur 1 / Joueur 2 / Joueur 3)
  // la question 2 démarre sur la coupe caméra de 79,86 s (« Allez, top ! » n'existe que sur le téléphone, hors image)
  { id: "q2a", in: 79.9, out: 86.8, cap: true, fix: { "numéro": "QUESTION NUMÉRO" }, music: "game", zoom: [1.0, 0.54, 0.45, 1.06, 0.54, 0.45],
    events: [{ t: 0, type: "flash", peak: 0.45 }, { t: 0, type: "sfx", sfx: "whoosh_long_b", vol: 0.45 },
      ...question("QUESTION 2", "Le plus rapide : le son, la lumière ou les fusées ?", "JOUEUR 1 · JOUEUR 2 · JOUEUR 3", 79.9, 6.9)] },
  { id: "q2b", in: 86.9, out: 89.2, speed: 1.6, music: "game", events: [{ t: 0, type: "title", dur: 1.2, lines: [["LA MÊLÉE", "r"]] }, { t: 0, type: "sfx", sfx: "whoosh_long_a", vol: 0.4 }] },
  // son de la Q2 : enregistrement du téléphone recalé (+77,194 s), réponses entendues : Joueur 2 « les fusées » ✗, puis Joueur 1 « la lumière » ✓
  { id: "q2c", in: 95.25, out: 99.3, cap: true, music: "game", zoom: [1.15, 0.45, 0.42, 1.25, 0.45, 0.45],
    events: [{ t: 0, type: "flash", peak: 0.3 }, { t: 0, type: "sfx", sfx: "whoosh_short_b", vol: 0.4 }, swish(95.85, 0.6), { at: 95.88, type: "label", dur: 3.0, text: "PANIER DE JOUEUR 2" },
      { at: 98.3, type: "sfx", sfx: "wrong_buzz_b", vol: 0.45 }, { at: 98.3, type: "info", dur: 1.0, text: "JOUEUR 2 : « LES FUSÉES » ✗", color: "r" }] },
  // « Vas-y ! » → « C'est le son ! » (on retire la phrase de l'animateur qui validait une mauvaise réponse) → grosse croix CONTESTÉ
  { id: "q2d", in: 103.3, out: 104.95, cap: true, tail: 0.05, music: "game", zoom: [1.05, 0.5, 0.45, 1.12, 0.5, 0.45] },
  { id: "q2d2", in: 107.72, out: 108.45, cap: true, tail: 0, music: "game", zoom: [1.3, 0.5, 0.5, 1.36, 0.5, 0.5] },
  { id: "q2dx", kind: "freeze", src: 108.43, dur: 1.2, music: "game", dim: true, zoom: [1.36, 0.5, 0.5, 1.42, 0.5, 0.5],
    events: [{ t: 0, type: "bigx", dur: 1.2 }, { t: 0, type: "sfx", sfx: "wrong_buzz_a", vol: 0.6 }, { t: 0, type: "shake" }, { t: 0.04, type: "title", dur: 1.16, lines: [["CONTESTÉ !", "r"]] }] },
  { id: "q2e", in: 112.3, out: 113.6, tail: 0.5, music: "game", zoom: [1.0, 0.6, 0.42, 1.12, 0.62, 0.4], events: [{ t: 0, type: "flash", peak: 0.3 }, { t: 0, type: "sfx", sfx: "whoosh_short_b", vol: 0.4 }] },
  { id: "q2f", in: 113.6, out: 114.2, speed: 0.4, music: "game", zoom: [1.2, 0.64, 0.4, 1.4, 0.66, 0.39], events: panier(113.892, "SWISH !") },
  { id: "q2g", in: 114.2, out: 118.2, cap: true, music: "game", zoom: [1.0, 0.5, 0.45, 1.12, 0.45, 0.48],
    events: [swish(114.772, 0.55), { at: 115.85, type: "sfx", sfx: "correct_ding_b", vol: 0.6 }, { at: 115.85, type: "title", dur: 1.3, lines: [["LA LUMIÈRE !", "g"]] }, { at: 116.6, type: "score", player: 0, pts: 1 }] },
  { id: "q2h", in: 119.5, out: 122.7, cap: true, tail: 0, music: "game" },
  // ------------------------------------------------------------- QUESTION 3 (duel)
  { id: "q3a", in: 125.5, out: 130.35, cap: true, fix: { tu: "QUI", es: "EST" }, music: "game",
    events: question("QUESTION 3", "Qui est le meilleur prof de physique ?", "DUEL · JOUEUR 4 vs JOUEUR 5", 125.5, 4.5) },
  { id: "q3b", in: 130.35, out: 131.2, music: "game", zoom: [1.0, 0.5, 0.42, 1.14, 0.5, 0.4] },
  { id: "q3c", in: 131.2, out: 132.0, speed: 0.4, music: "game", zoom: [1.2, 0.5, 0.4, 1.42, 0.5, 0.39], events: panier(131.73) },
  { id: "q3d", in: 132.0, out: 136.25, cap: true, music: "game", zoom: [1.0, 0.75, 0.48, 1.18, 0.78, 0.48],
    events: [{ at: 134.2, type: "sfx", sfx: "correct_ding_a", vol: 0.6 }, { at: 134.2, type: "score", player: 4, pts: 2 }, { at: 134.3, type: "wow", dur: 1.4, text: "INCONTESTABLE 😇" }] },
  // ------------------------------------------------------------- QUESTION 4 (le moment drôle)
  { id: "q4a", in: 146.4, out: 150.0, cap: true, music: "game",
    events: question("QUESTION 4", "Il y a combien de temps la Terre s'est formée ?", "JOUEUR 1 · JOUEUR 2 · JOUEUR 3", 146.4, 3.6) },
  { id: "q4b", in: 150.0, out: 161.8, speed: 3.0, music: "game", events: [{ t: 0, type: "wow", dur: 3.8, text: "RATÉ… RATÉ… RATÉ… 😬" }, { t: 0.6, type: "sfx", sfx: "rim_clang_a", vol: 0.4 }, { t: 2.2, type: "sfx", sfx: "rim_clang_b", vol: 0.4 }] },
  { id: "q4c", in: 161.8, out: 163.4, music: "game", zoom: [1.0, 0.5, 0.42, 1.12, 0.5, 0.41] },
  { id: "q4d", in: 163.4, out: 164.4, speed: 0.4, music: "game", zoom: [1.2, 0.5, 0.4, 1.4, 0.5, 0.4],
    events: [swish(163.847), swish(163.96, 0.7), { at: 163.88, type: "flash" }, { at: 163.85, type: "title", dur: 1.2, lines: [["DOUBLÉ !", "c"]] }, { at: 163.85, type: "shake" }] },
  { id: "q4e", in: 164.85, out: 168.05, cap: true, music: "suspense", zoom: [1.0, 0.56, 0.45, 1.1, 0.56, 0.45] },
  { id: "q4f", in: 168.8, out: 171.35, cap: true, music: "suspense", zoom: [1.32, 0.56, 0.4, 1.38, 0.56, 0.4],
    events: [{ at: 168.88, type: "wow", dur: 1.3, text: "IL A OUBLIÉ LA QUESTION 💀" }, { at: 168.9, type: "sfx", sfx: "boing_b", vol: 0.45 }] },
  { id: "q4g", in: 171.35, out: 177.25, cap: true, fix: { suis: "SUIS NÉ" }, music: "suspense", zoom: [1.1, 0.56, 0.42, 1.18, 0.56, 0.42],
    events: [{ at: 175.6, type: "punch", scale: 1.3 }, { at: 175.68, type: "sfx", sfx: "wrong_buzz_a", vol: 0.55 }, { at: 175.7, type: "title", dur: 1.4, lines: [["2008 ?!", "r"]] },
      { at: 176.1, type: "info", dur: 1.05, text: "RÉPONSE : 4,5 MILLIARDS D'ANNÉES 🌍", color: "r" }] },
  { id: "q4h", in: 182.75, out: 189.4, cap: true, music: "suspense", zoom: [1.0, 0.5, 0.45, 1.12, 0.5, 0.45],
    events: [{ at: 185.0, type: "punch", scale: 1.25 }, { at: 185.1, type: "title", dur: 1.3, lines: [["2026 ANS ?!", "r"]] }, { at: 186.4, type: "sfx", sfx: "sad_trombone", vol: 0.5 },
      { at: 187.6, type: "info", dur: 1.3, text: "PERSONNE NE MARQUE", color: "r" }] },
  // ------------------------------------------------------------- QUESTION 5 (balle de match)
  { id: "q5a", in: 189.4, out: 195.7, cap: true, music: "game",
    events: [...question("QUESTION 5", "Le Soleil tourne autour de la Terre… ou l'inverse ?", "BALLE DE MATCH · JOUEUR 4 vs JOUEUR 5", 189.4, 6.3), { at: 193.5, type: "sfx", sfx: "heartbeat_a", vol: 0.5 }] },
  { id: "q5b", in: 195.7, out: 199.3, music: "game", zoom: [1.0, 0.5, 0.42, 1.1, 0.5, 0.42], events: [{ at: 197.45, type: "sfx", sfx: "rim_clang_b", vol: 0.5 }, { at: 197.5, type: "wow", dur: 0.9, text: "RATÉ !" }] },
  { id: "q5c", in: 199.3, out: 200.35, speed: 0.4, music: "game", zoom: [1.2, 0.52, 0.4, 1.45, 0.51, 0.4], events: panier(200.123) },
  { id: "q5d", in: 200.35, out: 204.4, cap: true, music: "game", zoom: [1.05, 0.78, 0.48, 1.2, 0.8, 0.48],
    events: [{ at: 202.8, type: "sfx", sfx: "correct_ding_a", vol: 0.6 }, { at: 202.8, type: "title", dur: 1.2, lines: [["BONNE RÉPONSE", "g"]] }, { at: 202.85, type: "score", player: 4, pts: 3 }] },
  // ------------------------------------------------------------- VICTOIRE
  { id: "v0", kind: "black", dur: 1.35, music: "none", events: [{ t: 0, type: "dots", dur: 1.35, text: "ET LE GAGNANT EST" }, { t: 0, type: "sfx", sfx: "heartbeat_b", vol: 0.6 }] },
  { id: "v1", in: 210.62, out: 214.7, cap: true, music: "winner", zoom: [1.0, 0.5, 0.48, 1.1, 0.5, 0.48],
    events: [{ at: 213.35, type: "sfx", sfx: "impact_hit_b", vol: 0.8 }, { at: 213.35, type: "sfx", sfx: "sub_boom_a", vol: 0.7 }, { at: 213.38, type: "flash", peak: 0.6 },
      { at: 213.35, type: "winner", player: 4, dur: 2.6 }, { at: 213.35, type: "confetti" }, { at: 213.35, type: "shake" }] },
  { id: "v2", in: 214.7, out: 216.4, music: "winner" },
  { id: "o1", kind: "freeze", src: 216.35, dur: 2.6, music: "winner", dim: true, zoom: [1.0, 0.5, 0.5, 1.06, 0.5, 0.5],
    events: [{ t: 0, type: "final", dur: 2.6 }, { t: 0, type: "sfx", sfx: "whoosh_long_b", vol: 0.45 }] },
  // ------------------------------------------------------------- BONUS : le dunk du gagnant (A-roll/bonus-dunk.mov, Joueur 5 en le gagnant)
  { id: "b1", file: "A-roll/bonus-dunk.mov", in: 0.3, out: 2.9, music: "winner", zoom: [1.0, 0.55, 0.45, 1.12, 0.6, 0.4],
    events: [{ t: 0, type: "label", dur: 2.4, text: "VIDÉO BONUS" }, { t: 0, type: "flash", peak: 0.4 }, { t: 0, type: "sfx", sfx: "whoosh_long_a", vol: 0.5 },
      { t: 0.15, type: "title", dur: 2.2, lines: [["LE DUNK", "w"], ["DU GAGNANT", "y"]] }, { t: 1.6, type: "sfx", sfx: "riser_b", vol: 0.4 }] },
  { id: "b2", file: "A-roll/bonus-dunk.mov", in: 2.9, out: 3.45, speed: 0.35, music: "winner", zoom: [1.15, 0.6, 0.38, 1.45, 0.62, 0.32],
    events: [{ at: 3.15, type: "sfx", sfx: "impact_hit_b", vol: 0.8 }, { at: 3.15, type: "sfx", sfx: "bass_drop_b", vol: 0.7 }, { at: 3.17, type: "flash", peak: 0.55 }, { at: 3.15, type: "shake" },
      { at: 3.15, type: "title", dur: 1.3, lines: [["DUNK !", "c"]] }] },
  { id: "b3", file: "A-roll/bonus-dunk.mov", in: 3.45, out: 6.2, music: "winner", zoom: [1.1, 0.5, 0.45, 1.0, 0.5, 0.5],
    events: [{ at: 4.3, type: "info", dur: 1.6, text: "JOUEUR 5 · VAINQUEUR 🏆", color: "g" }] },
  // ------------------------------------------------------------- GÉNÉRIQUE DE FIN
  { id: "cr", kind: "black", dur: 3.4, music: "winner", events: [{ t: 0, type: "credits", dur: 3.4 }, { t: 0, type: "sfx", sfx: "whoosh_long_a", vol: 0.35 }, { t: 0.35, type: "sfx", sfx: "impact_hit_a", vol: 0.4 }] },
];
