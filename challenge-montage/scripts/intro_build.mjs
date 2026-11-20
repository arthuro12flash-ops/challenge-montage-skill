#!/usr/bin/env node
// challenge-montage — génère l'intro animée « règles du jeu » (mannequins 3D) d'après une configuration.
//
//   node intro_build.mjs <intro.config.json> <dossier_projet_intro>
//   puis : cd <dossier_projet_intro> && hyperframes lint && hyperframes render -q delivery -w 3 -o intro.mp4
//
// La voix IA est générée PHRASE PAR PHRASE (edge-tts) : on connaît donc exactement le début et la fin de chaque phrase,
// on resserre les pauses (les vidéos de référence parlent à ≈ 215 mots/min), puis on répartit les mots par syllabes.
// Le gabarit attend 11 phrases dans cet ordre (voir references/intro-3d.md) :
//   0 titre · 1 « c'est simple » · 2 la question · 3 « mais pour avoir le droit de répondre » · 4 « il faut d'abord marquer »
//   5 « Panier ? » · 6 « Tu réponds » · 7 « Bonne réponse » · 8 « un point » · 9 la règle de victoire · 10 « Place aux joueurs »
import { spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [cfgPath, outDir] = process.argv.slice(2);
if (!cfgPath || !outDir) { console.log("usage : node intro_build.mjs <intro.config.json> <dossier_projet_intro>"); process.exit(1); }

// ---------------------------------------------------------------- configuration (valeurs par défaut = exemple basket × quiz)
const DEF = {
  voice: {
    name: "fr-FR-RemyMultilingualNeural", // voix multilingue : prononce correctement les mots anglais (« Shoot Contest »)
    rate: "+8%",
    tempo: 1.05,
    phrases: ["Le Shoot Contest,", "c'est simple.", "On te pose une question de physique-chimie…", "mais pour avoir le droit de répondre,",
      "il faut d'abord marquer !", "Panier ?", "Tu réponds.", "Bonne réponse :", "un point.", "Le premier à trois points remporte la partie.", "Place aux joueurs !"],
    gaps: [0, 0.15, 0.24, 0.2, 0.12, 0.34, 0.26, 0.26, 0.12, 0.3, 0.3],
  },
  text: {
    title: ["SHOOT", "CONTEST"], question: "QUESTION", qcardTag: "QUESTION · PHYSIQUE-CHIMIE", qcard: "Combien de planètes dans le système solaire ?",
    hostTag: "L'ANIMATEUR", playerTag: "LE JOUEUR", neon: "RÉPONSE", answer: "8 !", marquer: ["D'ABORD", "MARQUER !"], panier: "PANIER !",
    stamp: "BONNE RÉPONSE", premier: ["PREMIER À 3", "VICTOIRE"], joueurs: ["PLACE AUX", "JOUEURS"], steps: ["QUESTION", "TIR", "PANIER", "RÉPONSE", "+1"],
    counterLabel: "POINTS", court: "SHOOT CONTEST",
  },
  points: 3,
  players: [
    { name: "JOUEUR 1", color: "#f07a1a" }, { name: "JOUEUR 2", color: "#3ddffe" }, { name: "JOUEUR 3", color: "#7dc696" },
    { name: "JOUEUR 4", color: "#fd3a4c" }, { name: "JOUEUR 5", color: "#fcc52e" },
  ],
  musicVolume: 0.13, // ≈ −18 dB sous la voix
};
const user = JSON.parse(fs.readFileSync(cfgPath, "utf8").replace(/^﻿/, ""));
const CFG = { ...DEF, ...user, voice: { ...DEF.voice, ...(user.voice || {}) }, text: { ...DEF.text, ...(user.text || {}) } };
if (CFG.voice.phrases.length !== 11) { console.error("Le gabarit attend exactement 11 phrases (voir references/intro-3d.md)."); process.exit(1); }
if (CFG.voice.gaps.length !== 11) { console.error("Il faut 11 valeurs dans voice.gaps (pause avant chaque phrase)."); process.exit(1); }

const sh = (cmd, args, opts = {}) => spawnSync(cmd, args, { encoding: "utf8", ...opts });
// projet HyperFrames d'abord (hyperframes init refuse un dossier non vide)
if (!fs.existsSync(path.join(outDir, "hyperframes.json"))) {
  const parent = path.dirname(path.resolve(outDir)), name = path.basename(path.resolve(outDir));
  if (fs.existsSync(outDir) && fs.readdirSync(outDir).length) { console.error(`${outDir} existe et n'est pas un projet HyperFrames : choisissez un dossier vide.`); process.exit(1); }
  fs.mkdirSync(parent, { recursive: true });
  const r = sh("hyperframes", ["init", name, "--example", "blank", "--resolution", "portrait", "--non-interactive", "--skip-skills"], { cwd: parent, shell: process.platform === "win32" });
  if (r.status !== 0) { console.error(r.stderr || r.stdout); process.exit(1); }
}
const WORK = path.join(outDir, ".work");
fs.mkdirSync(WORK, { recursive: true });
const ffmpeg = (args, label) => { const r = sh("ffmpeg", ["-y", "-loglevel", "error", ...args]); if (r.status !== 0) { console.error(`ffmpeg (${label}) : ${r.stderr}`); process.exit(1); } };
const dur = (f) => +sh("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).stdout.trim();

// ---------------------------------------------------------------- 1. voix phrase par phrase
const bounds = [];
CFG.voice.phrases.forEach((txt, i) => {
  const key = crypto.createHash("md5").update(`${CFG.voice.name}|${CFG.voice.rate}|${txt}`).digest("hex").slice(0, 10);
  const mp3 = path.join(WORK, `p${i}_${key}.mp3`);
  if (!fs.existsSync(mp3)) {
    const r = sh("edge-tts", ["--voice", CFG.voice.name, `--rate=${CFG.voice.rate}`, "--text", txt, "--write-media", mp3]);
    if (r.status !== 0) { console.error(`edge-tts a échoué pour « ${txt} » :\n${r.stderr}\n(installer : uv tool install edge-tts)`); process.exit(1); }
  }
  // début et fin de la parole dans le fichier (silencedetect)
  const d = dur(mp3);
  const sd = sh("ffmpeg", ["-hide_banner", "-i", mp3, "-af", "silencedetect=noise=-40dB:d=0.06", "-f", "null", "-"]).stderr;
  const starts = [...sd.matchAll(/silence_start: (-?[\d.]+)/g)].map((m) => +m[1]);
  const ends = [...sd.matchAll(/silence_end: ([\d.]+)/g)].map((m) => +m[1]);
  // silence k = [starts[k], ends[k]] ; edge-tts ajoute ≈ 0,15 s devant et jusqu'à 1,2 s derrière chaque phrase
  const s = starts.length && starts[0] <= 0.01 && ends.length ? ends[0] : 0;
  const k = starts.length - 1;
  const trailing = k >= 0 && starts[k] > s + 0.1 && (ends[k] === undefined || ends[k] >= d - 0.05);
  const e = trailing ? starts[k] : d;
  bounds.push({ mp3, s, e, txt });
});

// ---------------------------------------------------------------- 2. montage de la voix + temps des mots
const PAD_IN = 0.03, PAD_OUT = 0.06, TEMPO = CFG.voice.tempo;
const syll = (w) => Math.max(1, (w.toLowerCase().match(/[aeiouyàâäéèêëîïôöùûüœæ]+/g) || []).length);
let fc = "", parts = [], t = 0;
const phrases = [], words = [];
bounds.forEach((b, i) => {
  const gap = CFG.voice.gaps[i];
  if (gap > 0) { fc += `aevalsrc=0:s=48000:d=${gap.toFixed(3)}[g${i}];`; parts.push(`[g${i}]`); t += gap; }
  const a = Math.max(0, b.s - PAD_IN), z = b.e + PAD_OUT;
  fc += `[${i}:a]atrim=start=${a.toFixed(3)}:end=${z.toFixed(3)},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=mono[s${i}];`;
  parts.push(`[s${i}]`);
  const ps = (t + (b.s - a)) / TEMPO, pe = (t + (b.e - a)) / TEMPO;
  phrases.push({ start: +ps.toFixed(3), end: +pe.toFixed(3) });
  // en français la ponctuation haute est précédée d'une espace (« marquer ! ») : on la recolle au mot
  const toks = b.txt.split(/\s+/).filter(Boolean).reduce((acc, x) => (/^[?!:;…,.]+$/u.test(x) && acc.length ? (acc[acc.length - 1] += x, acc) : (acc.push(x), acc)), []);
  const weights = toks.map(syll), tot = weights.reduce((x, y) => x + y, 0);
  let acc = 0;
  toks.forEach((w, k) => {
    const disp = w.toUpperCase().replace(/[.,:;…]+$/u, "").replace(/([?!])$/, " $1");
    words.push({ w: disp, t: +(ps + ((pe - ps) * acc) / tot).toFixed(3), p: i, brk: k === toks.length - 1 || /[.,:;…?!]$/u.test(w) });
    acc += weights[k];
  });
  t += z - a;
});
fs.mkdirSync(path.join(outDir, "assets", "sfx"), { recursive: true });
fs.mkdirSync(path.join(outDir, "assets", "music"), { recursive: true });
const voiceWav = path.join(outDir, "assets", "voice.wav");
ffmpeg([...bounds.flatMap((b) => ["-i", b.mp3]), "-filter_complex", `${fc}${parts.join("")}concat=n=${parts.length}:v=0:a=1,atempo=${TEMPO},apad=pad_dur=0.6[out]`, "-map", "[out]", "-ac", "1", "-ar", "48000", voiceWav], "voix");
const VO_DUR = +dur(voiceWav).toFixed(3);

// ---------------------------------------------------------------- 3. temps clés
const V = 0.25; // la voix démarre à 0,25 s (la caméra plonge d'abord)
const ofP = (p) => words.filter((w) => w.p === p);
const pw = (p, k) => { const ws = ofP(p); return V + ws[k < 0 ? ws.length + k : Math.min(k, ws.length - 1)].t; };
const kw = (p, re, fb) => { const w = ofP(p).find((x) => re.test(x.w)); return w ? V + w.t : fb; };
const T = {};
T.contest = pw(0, -1); T.simple = pw(1, 0); T.on = pw(2, 0); T.question = kw(2, /QUESTION/i, pw(2, 3));
T.mais = pw(3, 0); T.repondre = pw(3, -1); T.marquer = pw(4, -1); T.panier = pw(5, 0); T.tu = pw(6, 0); T.reponds = pw(6, -1);
T.bonne = pw(7, 0); T.point = pw(8, -1); T.le2 = pw(9, 0); T.premier = pw(9, Math.min(1, ofP(9).length - 1));
const p9 = ofP(9), iTrois = p9.findIndex((x) => /^(UN|DEUX|TROIS|QUATRE|CINQ|SIX|SEPT|HUIT|NEUF|DIX|\d+)/.test(x.w));
T.trois = iTrois >= 0 ? V + p9[iTrois].t : pw(9, 2);
T.points = iTrois >= 0 && iTrois + 1 < p9.length ? V + p9[iTrois + 1].t : T.trois + 0.15;
T.remporte = kw(9, /REMPORTE|GAGNE|GAGNANT|VAINQUEUR/i, pw(9, -3)); T.partie = pw(9, -1);
T.place = pw(10, 0); T.joueurs = pw(10, -1);
const DUR = Math.ceil((V + phrases[10].end + 0.55) * 30) / 30;
// dérivés (mêmes formules que dans le gabarit)
const dribble0 = T.mais - 0.1, rel = T.marquer + 0.4, tin = T.panier + 0.2, swap = T.partie + 0.15;

// ---------------------------------------------------------------- 4. sous-titres : 1 à 3 mots, ≤ 20 caractères, une phrase à la fois
const CAPS = []; let cur = [];
words.forEach((w, i) => {
  const len = cur.reduce((n, k) => n + words[k].w.length + 1, 0) + w.w.length;
  if (cur.length && (cur.length >= 3 || len > 20)) { CAPS.push([cur[0], cur[cur.length - 1] + 1]); cur = []; }
  cur.push(i);
  if (w.brk) { CAPS.push([cur[0], cur[cur.length - 1] + 1]); cur = []; }
});
if (cur.length) CAPS.push([cur[0], cur[cur.length - 1] + 1]);

// ---------------------------------------------------------------- 5. bruitages calés sur les événements
const S = [["whoosh_long_a", 0, 1.2, 0.5], ["impact_hit_a", T.contest, 1.2, 0.75], ["pop_ui_a", T.on, 0.5, 0.3], ["card_slam_a", T.question, 1, 0.5],
  ["whoosh_short_a", T.mais - 0.15, 0.6, 0.5], ["pop_ui_b", T.repondre, 0.5, 0.4], ["impact_hit_b", T.marquer, 1, 0.6], ["whoosh_short_b", rel - 0.03, 0.6, 0.35],
  ["swish_net_a", tin, 0.6, 0.9], ["tick_a", T.tu, 0.3, 0.45], ["pop_ui_c", T.reponds, 0.5, 0.4], ["correct_ding_a", T.bonne, 1.2, 0.6],
  ["score_up_a", T.point, 0.8, 0.55], ["whoosh_short_a", T.le2 - 0.04, 0.6, 0.4], ["riser_a", DUR - 2.0, 2, 0.4], ["bass_drop_a", T.partie, 1.5, 0.8]];
for (let k = 0; ; k++) { const at = dribble0 + 0.25 + k * 0.5; if (at >= T.marquer - 0.05) break; S.push([k % 2 ? "ball_bounce_b" : "ball_bounce_a", at, 0.5, 0.35]); }
for (let i = 0; i < CFG.points; i++) S.push(["tick_b", T.trois + ((T.points + 0.12 - T.trois) * i) / Math.max(1, CFG.points - 1), 0.2, 0.5]);
["pop_ui_a", "pop_ui_b", "pop_ui_c"].forEach((n, i) => S.push([n, swap + i * 0.16 + 0.4, 0.4, 0.25]));
const sfxAudio = S.sort((a, b) => a[1] - b[1]).map(([n, at, d, v], i) => `      <audio id="s${String(i + 1).padStart(2, "0")}" src="assets/sfx/${n}.wav" data-start="${Math.max(0, at).toFixed(3)}" data-duration="${d}" data-volume="${v}"></audio>`).join("\n");

// ---------------------------------------------------------------- 6. remplissage du gabarit
const esc = (x) => String(x).replace(/&/g, "&amp;").replace(/</g, "&lt;");
let html = fs.readFileSync(path.join(SKILL, "templates", "intro-3d", "index.template.html"), "utf8");
const flat = { DUR: DUR.toFixed(3), VO_DUR: VO_DUR.toFixed(3), SFX_AUDIO: sfxAudio,
  COUNTER_N: Array.from({ length: CFG.points + 1 }, (_, i) => `<span id="c${i}"${i === 0 ? ' style="opacity: 1"' : ""}>${i}/${CFG.points}</span>`).join(""),
  COUNTER_DOTS: Array.from({ length: CFG.points }, (_, i) => `<div class="d" id="d${i + 1}"></div>`).join("") };
for (const [k, v] of Object.entries(CFG.text)) {
  if (Array.isArray(v)) v.forEach((x, i) => (flat[`${k}.${i}`] = esc(x)));
  else flat[k] = esc(v);
}
html = html.replace(/\{\{([A-Za-z_.0-9]+)\}\}/g, (m, k) => (k in flat ? flat[k] : (console.warn(`texte manquant : ${k}`), m)));
html = html.replace(/(<audio id="mus"[^>]*data-volume=")[\d.]+/, `$1${CFG.musicVolume}`);
const inject = [
  `const DUR = ${DUR.toFixed(3)}; const V = ${V};`,
  `const CFG = ${JSON.stringify({ players: CFG.players, points: CFG.points, text: CFG.text })};`,
  `const VOICE = ${JSON.stringify({ phrases, words: words.map((w) => [w.w, w.t]) })};`,
  `const w = (i) => V + VOICE.words[i][1];`,
  `const CAPS = ${JSON.stringify(CAPS)};`,
  `const T = ${JSON.stringify(Object.fromEntries(Object.entries(T).map(([k, v]) => [k, +v.toFixed(3)])))};`,
].join("\n      ");
html = html.replace("/*@@CONFIG@@*/", inject);
if (/\{\{[A-Za-z_.0-9]+\}\}/.test(html)) console.warn("attention : des textes du gabarit n'ont pas été remplis");

// médias
const calm = path.join(SKILL, "assets", "music", "intro_calm.wav");
if (fs.existsSync(calm)) fs.copyFileSync(calm, path.join(outDir, "assets", "music", "intro_calm.wav"));
else { console.warn("musique absente : lancez scripts/sound/make_music.py (l'intro sera sans musique)"); html = html.replace(/\s*<audio id="mus"[^>]*><\/audio>/, ""); }
fs.writeFileSync(path.join(outDir, "index.html"), html);
const sfxDir = path.join(SKILL, "assets", "sfx");
for (const f of fs.readdirSync(sfxDir)) if (f.endsWith(".wav")) fs.copyFileSync(path.join(sfxDir, f), path.join(outDir, "assets", "sfx", f));
const nw = words.length;
console.log(`intro : ${path.join(outDir, "index.html")} — ${DUR.toFixed(2)} s, voix ${VO_DUR.toFixed(2)} s, ${nw} mots (${Math.round(nw / ((phrases[10].end - phrases[0].start) / 60))} mots/min)`);
console.log(`temps clés : ${Object.entries(T).map(([k, v]) => `${k} ${v.toFixed(2)}`).join(" · ")}`);
