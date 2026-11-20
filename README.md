# challenge-montage — un skill Claude pour monter tes vidéos de défis en TikTok

Tu as filmé un défi entre potes (un shoot contest, un quiz où il faut marquer pour répondre, un match, un tournoi) et tu veux un TikTok monté comme un pro ? Ce skill apprend à **Claude Code** à le faire, de tes rushs bruts jusqu'à la vidéo finale en 1080×1920 :

- **intro animée 3D** qui explique les règles : mannequins sur un terrain, voix IA, sous-titres mot à mot ;
- **présentation des joueurs** : ils avancent vers la caméra, arrêt sur image, carte photo et prénom ;
- **manches** : carte question, tableau de score qui évolue, ralentis sur les paniers avec « swish » calé à l'image, sous-titres karaoké ;
- **effets** : « BONNE RÉPONSE », buzzer et grosse croix « CONTESTÉ », rembobinage VHS quand une manche est rejouée, flashs, zooms, tremblements, mots façon BD ;
- **son** : voix nettoyées (−14 LUFS), synchro d'un enregistrement audio séparé (téléphone/dictaphone), 51 bruitages et une musique **100 % générés par synthèse**, donc sans droits d'auteur ;
- **fin** : annonce du gagnant, score final, vidéo bonus, générique « vidéo produite par… » ;
- **contrôle qualité** : mots coupés, raccords, loudness, planche contact.

Il est né d'un vrai projet (un « Shoot Contest » basket × physique-chimie) et contient toutes les corrections demandées en cours de route, pour que tu n'aies pas à les redemander.

## Installation

1. Copie le dossier `challenge-montage/` dans `.claude/skills/` de ton projet (ou dans `~/.claude/skills/` pour tous tes projets) :
   ```bash
   git clone https://github.com/arthuro12flash-ops/challenge-montage-skill.git
   mkdir -p .claude/skills && cp -r challenge-montage-skill/challenge-montage .claude/skills/
   ```
2. Installe les outils (détails et pièges Windows dans `challenge-montage/references/setup-windows.md`) : ffmpeg, Node 20+, `npm i -g hyperframes && hyperframes browser ensure`, `uv tool install whisper-ctranslate2`, `uv tool install edge-tts`.
3. Génère la musique une fois (quelques minutes) :
   ```bash
   uv run --python 3.12 --with numpy --with scipy python .claude/skills/challenge-montage/scripts/sound/make_music.py
   ```

## Utilisation

Mets tes rushs dans un dossier (par exemple `A-roll/`), ouvre Claude Code et demande simplement :

> Monte-moi un TikTok de notre shoot contest avec les vidéos de A-roll : intro qui explique les règles, présentation des joueurs, score, sous-titres.

Claude analyse les rushs (joueurs, tirs, réponses, score, son), te demande d'identifier les joueurs sur une planche photo, puis génère l'intro et le montage. Il fait le rendu, vérifie le résultat et le dépose dans ton dossier d'export. Ensuite tu donnes tes retours (« le son est coupé ici », « laisse-les avancer », « mets une croix contesté ») et il corrige.

## Contenu

```
challenge-montage/
├── SKILL.md                     instructions pour Claude
├── scripts/                     constructeur du montage, intro 3D, synchro audio, contrôle qualité, générateurs de sons
├── templates/intro-3d/          gabarit de l'intro (Three.js + GSAP)
├── assets/sfx/                  51 bruitages de synthèse (+ INDEX.md)
├── examples/                    liste de montage complète d'un vrai projet (anonymisée) + config d'intro
└── references/                  méthode, recette de style, son, intro, QA, installation, HyperFrames
```

## Prérequis et limites

- Les rendus sont locaux, avec [HyperFrames](https://www.npmjs.com/package/hyperframes) (HTML → MP4) et ffmpeg. Compte environ 5 s de calcul par seconde de vidéo, et prévois 8 Go de RAM minimum.
- La voix IA utilise edge-tts : le texte des règles est envoyé au service de synthèse vocale de Microsoft.
- L'intro 3D est conçue pour le basket. Pour un autre sport, il faut adapter le décor et les poses (voir `references/intro-3d.md`).
- Claude ne peut pas écouter le son. Il vérifie le son par des mesures, mais écoute toujours le résultat toi-même.

## Respect des personnes

Les vidéos de défis montrent souvent des mineurs. Demande leur accord (et celui de leurs parents) avant de publier, et ne mets jamais de rushs, de photos ou de prénoms dans un dépôt public.

---

**English summary** — *challenge-montage* is a Claude Code skill that turns raw phone footage of a friends' challenge (sport + quiz, matches, tournaments) into a polished vertical TikTok/Reels/Shorts edit. It produces an animated 3D rules intro with an AI voice, player intro cards, an on-screen scoreboard and questions, word-by-word captions, slow motion and freeze frames, VHS rewinds, "contested" overlays, synthesized SFX and music, end credits, and automated QA. Rendering is local, with HyperFrames (HTML → MP4) and ffmpeg. The documentation is in French.

Licence : MIT (voir `LICENSE`).
