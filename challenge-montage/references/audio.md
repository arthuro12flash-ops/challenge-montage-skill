# Son : nettoyage, synchro, raccords, musique

## 1. Nettoyer la voix caméra

Chaîne utilisée par `edit_build.mjs` (testée : −14 LUFS, plage 5 LU, +3,4 dB de séparation voix/fond) :

```
pan=mono|c0=0.5*c0+0.5*c1, highpass=f=100, afftdn=nr=15:nf=-40, equalizer 300 Hz −3 dB, equalizer 3,5 kHz +3 dB,
lowpass 12 kHz, deesser, acompressor 2,5:1, alimiter, loudnorm=I=-14:TP=-1.5:LRA=11
```

**Pas de noise gate** (`agate`) : dans un gymnase réverbérant elle avale la fin des mots faibles et l'utilisateur entend « le son coupé ».

## 2. Mots coupés

`node scripts/check_cuts.mjs projet.config.mjs` liste, pour chaque segment à vitesse normale, les mots coupés à l'entrée/sortie et ceux qui commencent juste après. Corriger :
- sortie trop tôt → la reculer après la fin du dernier mot (+0,1 à 0,4 s) ;
- mot indésirable juste après → `tail: 0` ou `tail: 0.05` sur le segment ;
- fin de question coupée avant la question suivante : c'est le défaut le plus visible ; toujours laisser finir la phrase.

Les lignes qui ne montrent qu'une ponctuation (`?[…]`) sont des artefacts de whisper.

## 3. Rush assemblé et jointures

Les vidéos de téléphone sont souvent déjà montées (plusieurs clips mis bout à bout). Repérer les jointures (changements de cadrage nets, `select='gt(scene,0.3)'`, coupures du son). Conséquences :
- **ne jamais faire commencer un segment juste avant une jointure** : on voit quelques images d'un autre moment (« scène coupée bizarre ») ; commencer 0,04 s après ;
- un mot à cheval sur une jointure n'existe pas vraiment ;
- un enregistrement audio continu (téléphone) n'a pas le même décalage avant et après une jointure.

## 4. Recaler un enregistrement externe (dictaphone, 2e téléphone)

Souvent de bien meilleure qualité que le son caméra. Méthode :
```bash
ffmpeg -i memo.m4a -vn -ac 1 -ar 16000 work/phone.wav
python scripts/sync_audio.py work/rush.wav work/phone.wav                 # décalage global (dominé par le plus long clip)
python scripts/sync_window.py work/rush.wav work/phone.wav 3 8 60 100       # extrait 3–8 s du téléphone cherché dans 60–100 s du rush
python scripts/sync_window.py work/rush.wav work/phone.wav 0 2.6 40 82      # chaque morceau, de chaque côté des jointures
```
Le décalage se mesure **clip par clip** : s'il diffère d'un extrait à l'autre, il y a une jointure entre les deux ; ne garder le téléphone que là où le décalage est confirmé. Vérifier l'absence de dérive (deux moitiés → même décalage). Puis transcrire le fichier externe (whisper) et le déclarer dans `PROJECT.phones` avec un morceau par clip :
```js
phones: [{ file: "A-roll/memo.m4a", transcript: "work/phone.json", pieces: [{ a: 79.9, b: 119.35, off: 77.194 }] }]
```
Le constructeur remplace le son caméra par le téléphone entre `a` et `b` avec des fondus enchaînés de 40 ms placés exactement, et prend les mots des sous-titres dans la transcription du téléphone sur ces morceaux. Une phrase présente seulement dans l'enregistrement externe (prononcée pendant un trou de l'image) ne peut pas être utilisée : la retirer.

## 5. Raccords

- Fondu d'entrée 30 ms, queue de son de 0,3 s qui s'éteint après chaque coupe (L-cut) : les coupes ne claquent plus.
- Ralentis et accélérés : pas de son d'origine (musique + SFX), la queue du plan précédent s'éteint dessus.
- Arrêts sur image : `audioThrough: 0.6` garde les cris/rires sous la carte.
- Rembobinage : son d'origine inversé et accéléré (généré automatiquement).

## 6. Musique et bruitages

- Bruitages : `assets/sfx/` (51 sons de synthèse, `INDEX.md` donne usage et gain). Caler les swishs **à l'image exacte** où le ballon passe le cercle (vérifier image par image), les whooshs avec leur pic sur la coupe.
- Musique : `scripts/sound/make_music.py` génère des sections bouclables (144 BPM half-time, la mineur) + stems ; `edit_build.mjs` les enchaîne en lits continus (`players`, `game`, `suspense`, `winner`).
- Voix IA de l'intro : edge-tts, voix multilingue `fr-FR-RemyMultilingualNeural` (prononce bien les mots anglais) ; les autres voix françaises peuvent écorcher « Shoot Contest ». Vérifier la prononciation en re-transcrivant le fichier généré.
- Loudness finale visée : −14 LUFS intégrés, crête ≤ −1 dBTP (`qa_render.mjs`).
