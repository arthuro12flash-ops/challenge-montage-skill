# Liste de montage (`*.config.mjs`)

Un module ES qui exporte `PROJECT` (sources et réglages) et `SEGMENTS` (la timeline, dans l'ordre). Exemple complet et commenté : `examples/shoot-contest.config.mjs` (55 segments, 2 min 38).

## Sommaire
1. PROJECT
2. Segments
3. Événements
4. Ce que le constructeur fait tout seul
5. Recettes

## 1. PROJECT

| Clé | Rôle |
|---|---|
| `root` | dossier de travail ; le projet HyperFrames est créé dans `<root>/build/edit` |
| `rush` | rush principal |
| `transcript` | JSON de whisper-ctranslate2 (`--word_timestamps True`) du rush |
| `intro` | MP4 de l'intro 3D (si un segment `kind: "intro"`) |
| `phones` | enregistrements externes : `[{ file, transcript, pieces: [{ a, b, off }] }]` — remplace le son caméra entre `a` et `b` (temps rush) ; `off` = temps rush − temps du fichier, **mesuré clip par clip** |
| `players` | `[{ name, color, photo }]` — photo 4:5 (620×775 conseillé), index = numéro de joueur dans les événements |
| `fix` | corrections de sous-titres : `{ "mot en minuscules": "TEXTE AFFICHÉ" }` |
| `maxPoints` | points pour gagner (cases du tableau de score) |
| `credits` | `{ by, lines: [...], sub, deco }` pour l'événement `credits` |
| `text` | textes d'interface : `winner`, `finalTitle`, `finalCta`, `rewindSub` |
| `grade`, `clean`, `phoneClean`, `musicBeds`, `fps` | réglages avancés (voir `edit_build.mjs`) |

## 2. Segments

Temps : `in`, `out`, `at`, `src` en secondes **du rush** ; `t` en secondes **depuis le début du segment monté**.

| Type | Champs |
|---|---|
| clip (défaut) | `id, in, out` · `speed` (0,4 = ralenti interpolé ; 1,6–3 = accéléré) · `reverse: true` (rembobinage VHS) · `file` (autre rush que `PROJECT.rush`) · `cap: true` (sous-titres auto) · `capFrom` · `fix` · `zoom: [s0, x0, y0, s1, x1, y1]` (échelle et point de zoom normalisés, début → fin) · `tail` (queue de son en s après la coupe, défaut 0,3 ; 0 si le mot suivant ne doit pas s'entendre) · `music` · `musicVol` · `events` |
| `kind: "freeze"` | `src` (temps de l'image), `dur`, `dim` (assombrit), `audioThrough` (volume du son d'origine qui continue sous l'arrêt), `zoom`, `music`, `events` |
| `kind: "black"` | `dur`, `music`, `events` (écran noir : suspense, générique) |
| `kind: "intro"` | `dur` = durée exacte de l'intro rendue ; son de l'intro conservé |

`music` : `"none"` ou un lit de `PROJECT.musicBeds` (`players`, `game`, `suspense`, `winner`). Un lit est lu en continu d'un segment à l'autre ; son volume baisse tout seul sous les dialogues (`cap: true`).

## 3. Événements

Chaque événement a `t` (relatif) **ou** `at` (temps rush, converti selon la vitesse du segment).

| type | Champs | Effet |
|---|---|---|
| `sfx` | `sfx` (nom dans `assets/sfx`), `vol` | bruitage |
| `title` | `dur`, `lines: [[texte, couleur], …]` | titre géant (couleurs : `w` blanc, `y` jaune concept, `r` rouge erreur, `c` cyan action, `g` vert validation) ; 2 lignes = 1re blanche + mot-clé coloré |
| `qcard` | `dur`, `label`, `text` | carte question (haut de l'écran) |
| `label` | `dur`, `text` | pastille noire « ● DUEL · A vs B » |
| `info` | `dur`, `text`, `color` (`g`/`r`) | bandeau au-dessus des sous-titres (vraie réponse, « PERSONNE NE MARQUE ») |
| `wow` | `dur`, `text` | mot BD qui oscille (humour) |
| `flash` | `peak` | flash blanc 7 images |
| `shake` | | tremblement 8 images |
| `punch` | `scale` | zoom brusque (4 images) sur le plan en cours |
| `hud` | | fait apparaître le tableau de score |
| `score` | `player`, `pts` | met à jour le score (+ son) — le score final en est déduit |
| `card` / `winner` | `player`, `dur` | carte photo du joueur / carte vainqueur |
| `bigx` | `dur` | grosse croix rouge (à combiner avec un titre « CONTESTÉ ! ») |
| `vhs` | `dur`, `text`, `sub` | surimpression de rembobinage (avec un segment `reverse`) |
| `dots` | `dur`, `text` | « ET LE GAGNANT EST… » avec points qui apparaissent |
| `confetti` | | pluie de confettis |
| `final` | `dur` | tableau du score final + appel à s'abonner |
| `credits` | `dur`, `credits` | générique de fin |

## 4. Ce que le constructeur fait tout seul

- **Sauts dans le même plan** (deux segments du même fichier non contigus) : flash 25 %, whoosh, et décalage de cadrage s'il est trop proche du précédent.
- **Son** : fondu de 30 ms à l'entrée, queue de 0,3 s qui s'éteint après la coupe (L-cut), aucun fondu entre deux segments contigus.
- **Sous-titres** : mots de la transcription (et des enregistrements externes dans leurs morceaux), apostrophes et ponctuation recollées, groupes de 1 à 3 mots ≤ 20 caractères coupés à la ponctuation, pastille jaune sur le mot prononcé 2 images avant.
- **Score final** calculé depuis les événements `score`.

## 5. Recettes

```js
// question reposée après contestation : rembobinage puis la question à nouveau
{ id: "rw", in: 58.4, out: 61.4, speed: 3, reverse: true, music: "none",
  events: [{ t: 0, type: "vhs", dur: 1.0, text: "◀◀ REMBOBINAGE" }, { t: 0.05, type: "title", dur: 0.95, lines: [["ON", "w"], ["RECOMMENCE !", "y"]] }] },

// retirer une validation erronée de l'animateur : couper avant, garder la réponse du joueur, arrêt sur image + croix
{ id: "a", in: 103.3, out: 104.95, cap: true, tail: 0.05 },
{ id: "b", in: 107.72, out: 108.45, cap: true, tail: 0 },
{ id: "x", kind: "freeze", src: 108.43, dur: 1.2, dim: true,
  events: [{ t: 0, type: "bigx", dur: 1.2 }, { t: 0, type: "sfx", sfx: "wrong_buzz_a", vol: 0.6 }, { t: 0.04, type: "title", dur: 1.16, lines: [["CONTESTÉ !", "r"]] }] },

// panier au ralenti avec swish à l'image exacte
{ id: "s", in: 54.7, out: 55.6, speed: 0.4, zoom: [1.2, 0.52, 0.4, 1.45, 0.5, 0.39],
  events: [{ at: 55.135, type: "sfx", sfx: "swish_net_a", vol: 0.85 }, { at: 55.17, type: "flash" }, { at: 55.135, type: "title", dur: 1.1, lines: [["PANIER !", "c"]] }, { at: 55.135, type: "shake" }] },
```
