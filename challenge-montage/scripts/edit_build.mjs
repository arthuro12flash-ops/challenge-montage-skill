#!/usr/bin/env node
// challenge-montage — constructeur du montage principal (HyperFrames).
//
//   node edit_build.mjs <projet.config.mjs> prep [ids] [audio]   prépare les médias (son nettoyé, clips 1080×1920
//                                                                  30 i/s interpolés, ralentis, rembobinages, arrêts sur image)
//   node edit_build.mjs <projet.config.mjs> html                  génère <root>/build/edit/index.html
//
// `ids` (facultatif) : liste « q1a,q2c » pour ne refaire que ces segments. Ajouter `audio` pour refaire aussi le son.
// Le fichier de configuration exporte PROJECT et SEGMENTS : voir examples/shoot-contest.config.mjs et references/edl.md.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [cfgPath, mode, onlyArg, audioArg] = process.argv.slice(2);
if (!cfgPath || !["prep", "html"].includes(mode)) {
  console.log("usage : node edit_build.mjs <projet.config.mjs> prep [ids] [audio] | html");
  process.exit(1);
}
const { PROJECT, SEGMENTS } = await import(pathToFileURL(path.resolve(cfgPath)).href);

// ---------------------------------------------------------------- configuration (valeurs par défaut)
const C = {
  fps: 30,
  phones: [],
  fix: {},
  maxPoints: 3,
  // étalonnage : contraste/saturation légers, ombres chaudes, vignettage
  grade: "eq=contrast=1.08:saturation=1.1:gamma=0.97,colorbalance=rs=.03:bs=-.03:rm=.03:bm=-.03:rh=.02:bh=-.02,vignette=angle=PI/5",
  // voix caméra : SANS noise gate (elle avale la fin des mots faibles) ; loudnorm à -14 LUFS
  clean: "pan=mono|c0=0.5*c0+0.5*c1,aresample=48000,highpass=f=100:poles=2,afftdn=nr=15:nf=-40:tn=1,equalizer=f=300:t=q:w=1.0:g=-3,equalizer=f=3500:t=q:w=1.2:g=3,lowpass=f=12000,deesser=i=0.3,acompressor=threshold=-22dB:ratio=2.5:attack=10:release=200:makeup=2,alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11",
  // enregistrement téléphone : plus léger (il est déjà proche de la bouche)
  phoneClean: "pan=mono|c0=0.5*c0+0.5*c1,aresample=48000,highpass=f=90:poles=2,afftdn=nr=10:nf=-42:tn=1,equalizer=f=3500:t=q:w=1.2:g=2,acompressor=threshold=-22dB:ratio=2:attack=10:release=200:makeup=1,loudnorm=I=-14:TP=-1.5:LRA=11",
  // lits musicaux continus, construits à partir des sections de make_music.py
  musicBeds: {
    players: ["players_hype", "players_hype"],
    game: ["game_groove_a", "game_groove_b", "game_groove_a", "game_groove_b", "game_groove_a", "game_groove_b", "game_groove_a", "game_groove_b", "game_groove_a"],
    suspense: ["suspense", "suspense", "suspense", "suspense"],
    winner: ["drop_winner", "outro"],
  },
  musicDir: path.join(SKILL, "assets", "music"),
  sfxDir: path.join(SKILL, "assets", "sfx"),
  text: {
    winner: "VAINQUEUR 🏆",
    finalTitle: "SCORE FINAL",
    finalCta: "ABONNE-TOI POUR LE PROCHAIN ÉPISODE",
    rewindSub: "×3 · LECTURE ARRIÈRE",
  },
  credits: null, // { by: "VIDÉO PRODUITE PAR", lines: ["PRÉNOM", "& PRÉNOM"], sub: "…", deco: true }
  ...PROJECT,
};
C.text = { winner: "VAINQUEUR 🏆", finalTitle: "SCORE FINAL", finalCta: "ABONNE-TOI POUR LE PROCHAIN ÉPISODE", rewindSub: "×3 · LECTURE ARRIÈRE", ...(PROJECT.text || {}) };
const FPS = C.fps, F = 1 / FPS;
const RUSH = C.rush;
const ROOT = C.root;
const P = path.join(ROOT, "build", "edit");
const A = path.join(P, "assets");
const players = C.players || [];
const posix = (p) => p.split(path.sep).join("/");
const cleanName = (f) => (f === RUSH ? "rush_clean.wav" : path.basename(f).replace(/\.[^.]+$/, "") + "_clean.wav");
const run = (args, label) => {
  const r = spawnSync("ffmpeg", ["-y", "-loglevel", "error", ...args], { encoding: "utf8" });
  if (r.status !== 0) { console.error(`ffmpeg a échoué (${label}) :\n${r.stderr}`); process.exit(1); }
};

// ---------------------------------------------------------------- timeline
let t = 0;
const segs = SEGMENTS.map((s) => {
  const speed = s.speed || 1;
  const dur = s.dur ?? +((s.out - s.in) / speed).toFixed(3);
  const o = { ...s, kind: s.kind || "clip", speed, dur, start: +t.toFixed(3) };
  t += dur;
  return o;
});
const TOTAL = +t.toFixed(3);
const evTime = (s, e) => +(s.start + (e.t ?? (e.at - s.in) / s.speed)).toFixed(3);
const PIECES = C.phones.flatMap((p, i) => p.pieces.map((q) => ({ ...q, n: i }))).sort((x, y) => x.a - y.a);

// ---------------------------------------------------------------- PREP
function ensureProject() {
  if (fs.existsSync(path.join(P, "hyperframes.json"))) return;
  fs.mkdirSync(path.dirname(P), { recursive: true });
  console.log("création du projet HyperFrames…");
  const r = spawnSync("hyperframes", ["init", "edit", "--example", "blank", "--resolution", "portrait", "--non-interactive", "--skip-skills"],
    { cwd: path.dirname(P), encoding: "utf8", shell: process.platform === "win32" });
  if (r.status !== 0) { console.error(r.stderr || r.stdout); process.exit(1); }
}
function prep() {
  ensureProject();
  for (const d of ["clips", "sfx", "music", "players"]) fs.mkdirSync(path.join(A, d), { recursive: true });
  const only = onlyArg && onlyArg !== "audio" ? new Set(onlyArg.split(",")) : null;
  const doAudio = !only || onlyArg === "audio" || audioArg === "audio";
  if (doAudio) {
    for (const f of new Set([RUSH, ...segs.filter((s) => s.file).map((s) => s.file)])) {
      console.log(`son nettoyé ${f}…`);
      run(["-i", f, "-vn", "-af", C.clean, "-ar", "48000", "-ac", "1", path.join(A, f === RUSH ? "rush_clean_cam.wav" : cleanName(f))], "nettoyage");
    }
    if (!PIECES.length) fs.copyFileSync(path.join(A, "rush_clean_cam.wav"), path.join(A, "rush_clean.wav"));
    else {
      // son hybride : caméra + morceaux de téléphone recalés (un décalage PAR CLIP caméra), fondus enchaînés de 40 ms.
      // Chaque morceau commence à (a − 0,02) et finit à (b + 0,02) : les fondus se recouvrent exactement, sans décaler le reste.
      console.log("son hybride caméra + téléphone…");
      C.phones.forEach((p, i) => run(["-i", p.file, "-vn", "-af", C.phoneClean, "-ar", "48000", "-ac", "1", path.join(A, `phone_clean_${i}.wav`)], `téléphone ${i}`));
      const inputs = ["-i", path.join(A, "rush_clean_cam.wav"), ...C.phones.flatMap((_, i) => ["-i", path.join(A, `phone_clean_${i}.wav`)])];
      const parts = []; let cur = 0;
      for (const q of PIECES) {
        parts.push(`[0:a]atrim=${Math.max(0, cur - 0.02).toFixed(3)}:${(q.a + 0.02).toFixed(3)},asetpts=PTS-STARTPTS`);
        parts.push(`[${q.n + 1}:a]atrim=${(q.a - 0.02 - q.off).toFixed(3)}:${(q.b + 0.02 - q.off).toFixed(3)},asetpts=PTS-STARTPTS`);
        cur = q.b;
      }
      parts.push(`[0:a]atrim=${(cur - 0.02).toFixed(3)},asetpts=PTS-STARTPTS`);
      let fc = parts.map((p, i) => `${p}[p${i}]`).join(";"), last = "p0";
      for (let i = 1; i < parts.length; i++) { fc += `;[${last}][p${i}]acrossfade=d=0.04:c1=tri:c2=tri[x${i}]`; last = `x${i}`; }
      run([...inputs, "-filter_complex", fc, "-map", `[${last}]`, "-ar", "48000", "-ac", "1", path.join(A, "rush_clean.wav")], "hybride");
    }
  }
  for (const s of segs) {
    if (only && !only.has(s.id)) continue;
    const SRC = s.file || RUSH;
    if (s.kind === "clip") {
      const out = path.join(A, "clips", `${s.id}.mp4`);
      // les rushs de téléphone sont souvent à cadence variable (ici 16 i/s) : interpolation de mouvement vers 30 i/s
      const interp = `minterpolate=fps=${FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1`;
      const vf = s.reverse
        ? `scale=1080:1920:flags=lanczos,reverse,setpts=PTS/${s.speed},fps=${FPS},eq=saturation=0.7:contrast=1.12,noise=alls=22:allf=t,rgbashift=rh=8:bh=-8,drawgrid=w=iw:h=6:t=2:c=black@0.3,${C.grade}`
        : s.speed === 1 ? `scale=1080:1920:flags=lanczos,${interp},${C.grade}`
        : s.speed < 1 ? `scale=1080:1920:flags=lanczos,setpts=PTS/${s.speed},${interp},${C.grade}`
        : `scale=1080:1920:flags=lanczos,setpts=PTS/${s.speed},fps=${FPS},${C.grade}`;
      console.log(`clip ${s.id} (${s.in}–${s.out}, x${s.speed}${s.reverse ? ", à l'envers" : ""})`);
      run(["-ss", String(s.in), "-to", String(s.out), "-i", SRC, "-an", "-vf", vf, "-t", String(s.dur), "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], s.id);
      // son de rembobinage : le dialogue à l'envers et accéléré (effet cassette)
      if (s.reverse) run(["-i", path.join(A, "rush_clean.wav"), "-af", `atrim=${s.in}:${s.out},asetpts=PTS-STARTPTS,areverse,asetrate=${48000 * s.speed},aresample=48000,volume=0.8`, path.join(A, `rewind_${s.id}.wav`)], `rembobinage ${s.id}`);
    } else if (s.kind === "freeze") {
      console.log(`arrêt sur image ${s.id} (${s.src})`);
      run(["-ss", String(s.src), "-i", SRC, "-frames:v", "1", "-vf", `scale=1080:1920:flags=lanczos,${C.grade}`, "-q:v", "2", path.join(A, "clips", `${s.id}.jpg`)], s.id);
    }
  }
  if (only) return;
  if (segs.some((s) => s.kind === "intro")) {
    if (!C.intro || !fs.existsSync(C.intro)) { console.error(`intro introuvable : ${C.intro} (rendez d'abord l'intro, voir references/intro-3d.md)`); process.exit(1); }
    fs.copyFileSync(C.intro, path.join(A, "clips", "intro.mp4"));
  }
  for (const f of fs.readdirSync(C.sfxDir)) if (f.endsWith(".wav")) fs.copyFileSync(path.join(C.sfxDir, f), path.join(A, "sfx", f));
  for (const p of players) if (p.photo) fs.copyFileSync(p.photo, path.join(A, "players", path.basename(p.photo)));
  // lits musicaux continus : on lit dedans à l'offset voulu pour garder la continuité d'un segment à l'autre
  const usedBeds = new Set(segs.map((s) => s.music).filter((m) => m && m !== "none"));
  for (const bed of usedBeds) {
    const files = C.musicBeds[bed];
    if (!files) { console.error(`lit musical inconnu : ${bed}`); process.exit(1); }
    const missing = files.filter((f) => !fs.existsSync(path.join(C.musicDir, `${f}.wav`)));
    if (missing.length) { console.error(`musique manquante (${missing.join(", ")}) : lancez scripts/sound/make_music.py`); process.exit(1); }
    run([...files.flatMap((f) => ["-i", path.join(C.musicDir, `${f}.wav`)]), "-filter_complex", `${files.map((_, i) => `[${i}:a]`).join("")}concat=n=${files.length}:v=0:a=1[a]`, "-map", "[a]", "-ar", "48000", path.join(A, "music", `${bed}.wav`)], bed);
  }
  console.log("préparation terminée");
}

// ---------------------------------------------------------------- sous-titres automatiques (transcription + corrections)
let WORDS = null;
function allWords() {
  if (WORDS) return WORDS;
  const j = JSON.parse(fs.readFileSync(C.transcript, "utf8"));
  const inPiece = (x) => PIECES.some((q) => x >= q.a && x <= q.b);
  const raw = [
    ...j.segments.flatMap((g) => g.words).filter((w) => !inPiece(w.start)),
    ...PIECES.flatMap((q) => JSON.parse(fs.readFileSync(C.phones[q.n].transcript, "utf8")).segments.flatMap((g) => g.words)
      .map((w) => ({ ...w, start: w.start + q.off, end: w.end + q.off })).filter((w) => w.start >= q.a && w.start <= q.b)),
  ].sort((a, b) => a.start - b.start);
  // whisper découpe « C » + « 'est » et isole la ponctuation : on recolle
  const merged = [];
  for (const w of raw) {
    const txt = w.word.trim();
    if (!txt) continue;
    if (/^['’\-]/.test(txt) || /^[?!.,:;…]+$/.test(txt)) { if (merged.length) merged[merged.length - 1].w += txt; continue; }
    merged.push({ w: txt, start: w.start, p: w.probability });
  }
  return (WORDS = merged);
}
function wordsOf(s) {
  const from = s.capFrom ?? s.in;
  const fix = { ...C.fix, ...(s.fix || {}) };
  return allWords().filter((w) => w.start >= from - 0.05 && w.start < s.out - 0.15 && w.p > 0.04).map((w) => {
    const key = w.w.toLowerCase().replace(/[?!.,:;…]+$/u, "");
    const punct = (w.w.match(/[?!]+$/) || [""])[0];
    const txt = fix[key] ? fix[key] + (punct ? " " + punct : "") : w.w.toUpperCase().replace(/[.,:;…]+$/u, "").replace(/\s*([?!])$/, " $1");
    return { w: txt, t: evTime(s, { at: w.start }), brk: /[.,:;…?!]$/u.test(w.w) };
  });
}
// 1 à 3 mots, ≤ 20 caractères, coupure sur la ponctuation et les pauses
function groups(words) {
  const out = []; let cur = [];
  for (const w of words) {
    const len = cur.reduce((n, x) => n + x.w.length + 1, 0) + w.w.length;
    if (cur.length && (cur.length >= 3 || len > 20 || w.t - cur[cur.length - 1].t > 0.9)) { out.push(cur); cur = []; }
    cur.push(w);
    if (w.brk) { out.push(cur); cur = []; }
  }
  if (cur.length) out.push(cur);
  return out;
}

// ---------------------------------------------------------------- HTML
function html() {
  const media = [], audio = [], overlays = [], tl = [];
  let n = 0;
  const id = (p) => `${p}${++n}`;
  const col = { w: "#ffffff", y: "#fcc52e", r: "#fd3a4c", c: "#3ddffe", g: "#7dc696" };
  const esc = (x) => String(x).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  // raccords : un saut dans le même plan → flash + whoosh + changement de cadrage ; continuité du son (fondus enchaînés)
  const srcOf = (s) => s.file || RUSH;
  const contig = (a, b) => a && b && a.kind === "clip" && b.kind === "clip" && a.speed === 1 && b.speed === 1 && !a.reverse && !b.reverse && srcOf(a) === srcOf(b) && Math.abs(b.in - a.out) < 0.02;
  for (let i = 0; i < segs.length; i++) {
    const s = segs[i], p = segs[i - 1];
    s._contigPrev = contig(p, s); s._contigNext = contig(s, segs[i + 1]);
    if (!p || s.kind !== "clip" || s.reverse || p.reverse) continue;
    const pOut = p.kind === "freeze" ? p.src : p.kind === "clip" ? p.out : null;
    if (pOut == null || srcOf(s) !== srcOf(p) || Math.abs(s.in - pOut) < 0.15) continue;
    s.events = [...(s.events || [])];
    if (!s.events.some((e) => e.type === "flash" && e.t === 0)) s.events.push({ t: 0, type: "flash", peak: 0.25 });
    if (!s.events.some((e) => e.type === "sfx" && e.t === 0)) s.events.push({ t: 0, type: "sfx", sfx: "whoosh_short_b", vol: 0.3 });
    const pz = p.zoom ? p.zoom[3] : 1, z = s.zoom || [1, 0.5, 0.45, 1.06, 0.5, 0.45];
    s.zoom = Math.abs(z[0] - pz) < 0.1 ? [z[0] + 0.14, z[1], z[2], z[3] + 0.14, z[4], z[5]] : z;
  }
  // score final calculé à partir des événements « score »
  const finalPts = players.map(() => 0);
  for (const s of segs) for (const e of s.events || []) if (e.type === "score") finalPts[e.player] = e.pts;
  const MUSIC_START = {};
  for (const s of segs) if (s.music && s.music !== "none" && MUSIC_START[s.music] === undefined) MUSIC_START[s.music] = s.start;
  for (const s of segs) {
    const wrap = id("w");
    // l'enveloppe (non minutée) porte les « punch » ; le média minuté porte le zoom lent (jamais deux tweens sur la même propriété)
    const timed = `data-start="${s.start}" data-duration="${s.dur}"`;
    if (s.kind === "clip") media.push(`<div class="shot" id="${wrap}"><video id="v${wrap}" class="clip" src="assets/clips/${s.id}.mp4" ${timed} data-media-start="0" muted></video></div>`);
    else if (s.kind === "freeze") media.push(`<div class="shot" id="${wrap}"><img id="v${wrap}" class="clip" src="assets/clips/${s.id}.jpg" ${timed} />${s.dim ? `<div class="clip dimmer" id="dim${wrap}" ${timed}></div>` : ""}</div>`);
    else if (s.kind === "intro") media.push(`<div class="shot" id="${wrap}"><video id="v${wrap}" class="clip" src="assets/clips/intro.mp4" ${timed} data-media-start="0" data-has-audio="true"></video></div>`);
    else media.push(`<div class="shot" id="${wrap}"><div id="v${wrap}" class="clip blackbg" ${timed}></div></div>`);
    if (s.zoom) { const [a, x, y, b, x2, y2] = s.zoom; tl.push(`tl.fromTo("#v${wrap}",{scale:${a},transformOrigin:"${x * 100}% ${y * 100}%"},{scale:${b},transformOrigin:"${x2 * 100}% ${y2 * 100}%",duration:${s.dur},ease:"none",immediateRender:false},${s.start});`); }
    const dsrc = `assets/${cleanName(s.file || RUSH)}`;
    if (s.kind === "clip" && s.speed === 1 && !s.reverse) {
      // queue de son (L-cut) qui s'éteint après la coupe, sauf si le plan suivant est la suite directe
      const tail = s._contigNext ? 0 : (s.tail ?? 0.3);
      const fades = `${s._contigPrev ? "" : ' data-fade-in="0.03"'}${s._contigNext ? "" : ` data-fade-out="${Math.max(0.05, tail).toFixed(2)}"`}`;
      audio.push(`<audio id="${id("d")}" src="${dsrc}" data-start="${s.start}" data-media-start="${s.in}" data-duration="${(s.dur + tail).toFixed(3)}" data-volume="1"${fades}></audio>`);
    }
    if (s.reverse) audio.push(`<audio id="${id("d")}" src="assets/rewind_${s.id}.wav" data-start="${s.start}" data-duration="${s.dur}" data-volume="0.55"></audio>`);
    if (s.kind === "freeze" && s.audioThrough) audio.push(`<audio id="${id("d")}" src="${dsrc}" data-start="${s.start}" data-media-start="${s.src}" data-duration="${s.dur}" data-volume="${s.audioThrough}" data-fade-in="0.015" data-fade-out="0.3"></audio>`);
    if (s.music && s.music !== "none") {
      // musique : basse sous les dialogues, plus forte sur l'action et la victoire
      const vol = s.musicVol ?? (s.music === "winner" ? 0.32 : s.cap ? 0.09 : s.speed < 1 ? 0.16 : 0.2);
      const last = s === segs[segs.length - 1];
      audio.push(`<audio id="${id("m")}" src="assets/music/${s.music}.wav" data-start="${s.start}" data-media-start="${(s.start - MUSIC_START[s.music]).toFixed(3)}" data-duration="${s.dur}" data-volume="${last ? Math.min(vol, 0.26) : vol}"${last ? ` data-fade-out="${(s.dur * 0.6).toFixed(2)}"` : ""}></audio>`);
    }
    if (s.cap) {
      const gs = groups(wordsOf(s));
      gs.forEach((g, gi) => {
        const gid = id("cap"); const end = gi < gs.length - 1 ? gs[gi + 1][0].t - 2 * F : Math.min(s.start + s.dur, g[g.length - 1].t + 1.0);
        overlays.push(`<div class="cap" id="${gid}">${g.map((w, k) => `<span class="w" id="${gid}w${k}">${esc(w.w)}</span>`).join("")}</div>`);
        const st = Math.max(s.start, g[0].t - 2 * F);
        tl.push(`tl.fromTo("#${gid}",{autoAlpha:0},{autoAlpha:1,duration:${2 * F},immediateRender:false},${st.toFixed(3)});tl.set("#${gid}",{autoAlpha:0},${end.toFixed(3)});`);
        g.forEach((w, k) => {
          // la pastille jaune saute sur le mot prononcé 2 images avant son attaque
          const on = Math.max(st, w.t - 2 * F); tl.push(`tl.set("#${gid}w${k}",{backgroundColor:"rgba(252,197,46,1)",color:"#1e1a29",textShadow:"none",rotation:-1.5},${on.toFixed(3)});`);
          if (k < g.length - 1) tl.push(`tl.set("#${gid}w${k}",{backgroundColor:"rgba(252,197,46,0)",color:"#ffffff",textShadow:"0 4px 10px rgba(0,0,0,0.7)",rotation:0},${Math.max(on + 0.05, g[k + 1].t - 2 * F).toFixed(3)});`);
        });
      });
    }
    for (const e of s.events || []) {
      const at = evTime(s, e);
      if (e.type === "sfx") audio.push(`<audio id="${id("s")}" src="assets/sfx/${e.sfx}.wav" data-start="${at}" data-duration="2.5" data-volume="${e.vol ?? 0.6}"></audio>`);
      else if (e.type === "title") {
        const tid = id("t"); const two = e.lines.length > 1;
        overlays.push(`<div class="title${two ? " two" : ""}" id="${tid}">${e.lines.map(([txt, c]) => `<span class="l" style="--c:${col[c] || c}">${esc(txt)}</span>`).join("")}</div>`);
        tl.push(`title("#${tid}",${at},${(at + e.dur).toFixed(3)});`);
      } else if (e.type === "qcard") {
        const qid = id("q");
        overlays.push(`<div class="qcard" id="${qid}"><div class="tg">${esc(e.label)}</div><div class="tx">${esc(e.text)}</div></div>`);
        tl.push(`tl.fromTo("#${qid}",{autoAlpha:0.15,scale:0.8,rotation:-6},{autoAlpha:1,scale:1,rotation:-2,duration:${5 * F},ease:"back.out(1.8)",immediateRender:false},${at});tl.to("#${qid}",{autoAlpha:0,duration:${4 * F}},${(at + e.dur).toFixed(3)});`);
      } else if (e.type === "label" || e.type === "info") {
        const lid = id("l");
        overlays.push(`<div class="${e.type}${e.color ? " " + e.color : ""}" id="${lid}">${e.type === "label" ? "<i></i>" : ""}${esc(e.text)}</div>`);
        tl.push(`tl.fromTo("#${lid}",{autoAlpha:0,scale:0.9},{autoAlpha:1,scale:1,duration:${4 * F},ease:"power3.out",immediateRender:false},${at});tl.to("#${lid}",{autoAlpha:0,duration:${3 * F}},${(at + e.dur).toFixed(3)});`);
        if (e.type === "info") audio.push(`<audio id="${id("s")}" src="assets/sfx/pop_ui_b.wav" data-start="${at}" data-duration="0.5" data-volume="0.35"></audio>`);
      } else if (e.type === "wow") {
        const wid = id("x");
        overlays.push(`<div class="wow" id="${wid}">${esc(e.text)}</div>`);
        tl.push(`tl.fromTo("#${wid}",{autoAlpha:0,scale:1.6,rotation:-3},{autoAlpha:1,scale:1,rotation:-3,duration:${3 * F},ease:"back.out(2)",immediateRender:false},${at});`);
        tl.push(`tl.to("#${wid}",{keyframes:[${Array.from({ length: Math.max(1, Math.floor(e.dur / 0.2)) }, (_, k) => `{rotation:${k % 2 ? -3 : 3},duration:0.2,ease:"none"}`).join(",")}]},${(at + 0.1).toFixed(3)});`);
        tl.push(`tl.to("#${wid}",{autoAlpha:0,duration:${3 * F}},${(at + e.dur).toFixed(3)});`);
      } else if (e.type === "flash") {
        // enveloppe mesurée sur les références : 7 images, pic à 50 % sur la coupe
        const k = (e.peak ?? 0.5) / 0.5;
        tl.push(`tl.to("#flash",{keyframes:[0.12,0.3,0.5,0.36,0.17,0.05,0].map(o=>({opacity:o*${k},duration:${F},ease:"none"}))},${(at - 2 * F).toFixed(3)});`);
      } else if (e.type === "shake") tl.push(`tl.to("#cam",{keyframes:[14,-12,10,-8,6,-4,2,0].map((v)=>({x:v,y:-v*0.6,duration:${F},ease:"none"}))},${at});`);
      else if (e.type === "punch") tl.push(`tl.fromTo("#${wrap}",{scale:1},{scale:${e.scale},duration:${4 * F},ease:"power4.out",immediateRender:false},${at});`);
      else if (e.type === "score") { tl.push(`score(${e.player},${e.pts},${at});`); audio.push(`<audio id="${id("s")}" src="assets/sfx/score_up_b.wav" data-start="${(at + 0.15).toFixed(3)}" data-duration="1" data-volume="0.5"></audio>`); }
      else if (e.type === "hud") tl.push(`tl.fromTo("#hud",{autoAlpha:0,y:-20},{autoAlpha:1,y:0,duration:${5 * F},immediateRender:false},${at});`);
      else if (e.type === "card" || e.type === "winner") {
        const p = players[e.player]; const cid = id("card");
        overlays.push(`<div class="card${e.type === "winner" ? " win" : ""}" id="${cid}" style="--pc:${p.color}"><div class="ph">${p.photo ? `<img src="assets/players/${esc(path.basename(p.photo))}" />` : ""}</div><div class="nm">${esc(p.name)}</div>${e.type === "winner" ? `<div class="crown">${esc(C.text.winner)}</div>` : ""}</div>`);
        tl.push(`tl.fromTo("#${cid}",{autoAlpha:0.15,scale:0.8,rotation:-8},{autoAlpha:1,scale:1,rotation:-4,duration:${5 * F},ease:"back.out(1.7)",immediateRender:false},${at});tl.to("#${cid}",{scale:1.04,duration:${(e.dur - 0.3).toFixed(3)},ease:"none"},${(at + 5 * F).toFixed(3)});tl.to("#${cid}",{autoAlpha:0,duration:${3 * F}},${(at + e.dur - 3 * F).toFixed(3)});`);
      } else if (e.type === "bigx") {
        const xid = id("bx");
        overlays.push(`<div class="bigx" id="${xid}"><i></i><i></i></div>`);
        tl.push(`tl.fromTo("#${xid}",{autoAlpha:0,scale:2.4},{autoAlpha:1,scale:1,duration:${3 * F},ease:"expo.out",immediateRender:false},${at});tl.to("#${xid}",{scale:1.06,duration:${(e.dur - 0.25).toFixed(3)},ease:"none"},${(at + 3 * F).toFixed(3)});tl.to("#${xid}",{autoAlpha:0,duration:${3 * F}},${(at + e.dur - 3 * F).toFixed(3)});`);
      } else if (e.type === "vhs") {
        const vid = id("vhs");
        overlays.push(`<div class="vhs" id="${vid}"><b>${esc(e.text)}</b><span>${esc(e.sub ?? C.text.rewindSub)}</span></div>`);
        tl.push(`tl.fromTo("#${vid}",{autoAlpha:0},{autoAlpha:1,duration:${F},immediateRender:false},${at});tl.to("#${vid}",{keyframes:[${Array.from({ length: Math.round((e.dur * FPS) / 2) }, (_, k) => `{x:${k % 2 ? -7 : 6},duration:${2 * F},ease:"none"}`).join(",")}]},${at});tl.set("#${vid}",{autoAlpha:0},${(at + e.dur).toFixed(3)});`);
      } else if (e.type === "credits") {
        const cr = { by: "VIDÉO PRODUITE PAR", lines: ["PRÉNOM", "& PRÉNOM"], sub: "", deco: true, ...(C.credits || {}), ...(e.credits || {}) };
        const ball = `<svg viewBox="0 0 52 52"><circle cx="26" cy="26" r="23" fill="#f07a1a"/><path d="M3 26h46M26 3v46M9 9c9 9 9 25 0 34M43 9c-9 9-9 25 0 34" fill="none" stroke="#1e1a29" stroke-width="3"/></svg>`;
        const atom = `<svg viewBox="0 0 32 32" fill="none" stroke="#3ddffe" stroke-width="2.2"><ellipse cx="16" cy="16" rx="14" ry="5.5"/><ellipse cx="16" cy="16" rx="14" ry="5.5" transform="rotate(60 16 16)"/><ellipse cx="16" cy="16" rx="14" ry="5.5" transform="rotate(-60 16 16)"/><circle cx="16" cy="16" r="2.6" fill="#3ddffe"/></svg>`;
        overlays.push(`<div class="credits" id="credits">${cr.deco ? `<div class="deco">${ball}<span>×</span>${atom}</div>` : ""}<div class="by"><i></i>${esc(cr.by)}<i></i></div>${cr.lines.map((l, i) => `<div class="nm${i === 0 ? 1 : 2}">${esc(l)}</div>`).join("")}${cr.sub ? `<div class="sub">${esc(cr.sub)}</div>` : ""}</div>`);
        tl.push(`tl.fromTo("#credits",{autoAlpha:0},{autoAlpha:1,duration:${4 * F},immediateRender:false},${at});`);
        if (cr.deco) tl.push(`tl.fromTo("#credits .deco",{autoAlpha:0,scale:0.4,rotation:-20},{autoAlpha:1,scale:1,rotation:0,duration:${8 * F},ease:"back.out(2)",immediateRender:false},${(at + 0.05).toFixed(3)});`);
        tl.push(`tl.fromTo("#credits .by",{autoAlpha:0,y:30},{autoAlpha:1,y:0,duration:${8 * F},ease:"power3.out",immediateRender:false},${(at + 0.2).toFixed(3)});`);
        tl.push(`tl.fromTo("#credits .nm1, #credits .nm2",{autoAlpha:0,y:50,scale:0.9},{autoAlpha:1,y:0,scale:1,duration:${8 * F},ease:"back.out(1.6)",stagger:${5 * F},immediateRender:false},${(at + 0.35).toFixed(3)});`);
        if (cr.sub) tl.push(`tl.fromTo("#credits .sub",{autoAlpha:0},{autoAlpha:1,duration:${8 * F},immediateRender:false},${(at + 0.8).toFixed(3)});`);
        tl.push(`tl.to("#credits",{autoAlpha:0,duration:${12 * F},ease:"power1.in"},${(at + e.dur - 12 * F).toFixed(3)});`);
      } else if (e.type === "confetti") tl.push(`CONF_T.push(${at});`);
      else if (e.type === "dots") {
        const did = id("dots");
        overlays.push(`<div class="dots" id="${did}">${esc(e.text)}<span id="${did}a">.</span><span id="${did}b">.</span><span id="${did}c">.</span></div>`);
        tl.push(`tl.fromTo("#${did}",{autoAlpha:0},{autoAlpha:1,duration:${2 * F},immediateRender:false},${at});["a","b","c"].forEach((x,i)=>tl.fromTo("#${did}"+x,{opacity:0},{opacity:1,duration:0.01,immediateRender:false},${at}+0.3+i*0.3));tl.set("#${did}",{autoAlpha:0},${(at + e.dur).toFixed(3)});`);
      } else if (e.type === "final") {
        overlays.push(`<div class="final" id="final"><div class="fh">${esc(C.text.finalTitle)}</div>${players.map((p, i) => `<div class="fr" style="--pc:${p.color}"><b>${esc(p.name)}</b><span>${finalPts[i]}</span></div>`).join("")}<div class="cta">${esc(C.text.finalCta)}</div></div>`);
        tl.push(`tl.fromTo("#final",{autoAlpha:0,y:40},{autoAlpha:1,y:0,duration:${6 * F},ease:"power3.out",immediateRender:false},${at});tl.fromTo("#final .fr",{autoAlpha:0,x:-40},{autoAlpha:1,x:0,duration:${4 * F},stagger:${2 * F},immediateRender:false},${(at + 0.15).toFixed(3)});tl.to("#hud",{autoAlpha:0,duration:${4 * F}},${at});tl.to("#final",{autoAlpha:0,y:-30,duration:${5 * F}},${(at + e.dur - 5 * F).toFixed(3)});`);
      } else console.warn(`événement inconnu « ${e.type} » dans ${s.id} (ignoré)`);
    }
  }
  const maxP = Math.max(C.maxPoints, ...finalPts);
  const page = fs.readFileSync(path.join(SKILL, "scripts", "edit_template.html"), "utf8")
    .replaceAll("__TOTAL__", String(TOTAL))
    .replace("__MEDIA__", media.join("\n"))
    .replace("__OVERLAYS__", overlays.join("\n"))
    .replace("__HUD__", players.map((p, i) => `<div class="hp" id="hp${i}" style="--pc:${p.color}"><b>${esc(p.name)}</b><span class="pts">${Array.from({ length: maxP + 1 }, (_, v) => `<i id="hp${i}v${v}"${v === 0 ? ' style="opacity:1"' : ""}>${v}</i>`).join("")}</span></div>`).join(""))
    .replace("__AUDIO__", audio.join("\n"))
    .replace("__TIMELINE__", tl.join("\n"));
  fs.mkdirSync(P, { recursive: true });
  fs.writeFileSync(path.join(P, "index.html"), page);
  console.log(`${posix(path.join(P, "index.html"))} : ${segs.length} segments, ${TOTAL.toFixed(1)} s, ${audio.length} pistes audio, ${overlays.length} calques`);
  for (const s of segs) console.log(`${s.id.padEnd(6)} ${s.start.toFixed(2).padStart(7)} +${s.dur.toFixed(2)}`);
}

if (mode === "prep") prep(); else html();
