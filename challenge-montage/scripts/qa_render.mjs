#!/usr/bin/env node
// Contrôle qualité d'un rendu : format, loudness, écrans noirs, images figées, silences, erreurs de décodage,
// plus une planche contact (1 image/s) à ouvrir et REGARDER en entier.
//   node qa_render.mjs <video.mp4> [dossier_sortie]
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const [video, outDir = path.join(path.dirname(video || "."), "qa")] = process.argv.slice(2);
if (!video) { console.log("usage : node qa_render.mjs <video.mp4> [dossier_sortie]"); process.exit(1); }
fs.mkdirSync(outDir, { recursive: true });
const ff = (args) => spawnSync("ffmpeg", ["-hide_banner", ...args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).stderr || "";
const probe = spawnSync("ffprobe", ["-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate", "-of", "json", video], { encoding: "utf8" });
const info = JSON.parse(probe.stdout);
const v = info.streams.find((s) => s.codec_type === "video"), a = info.streams.find((s) => s.codec_type === "audio");
const dur = +info.format.duration;
const report = [];
const ok = (cond, msg) => report.push(`${cond ? "OK " : "!! "} ${msg}`);

ok(v && v.width === 1080 && v.height === 1920, `vidéo ${v?.codec_name} ${v?.width}×${v?.height} @ ${v?.r_frame_rate}`);
ok(!!a, `son ${a ? `${a.codec_name} ${a.sample_rate} Hz` : "ABSENT"}`);
ok(true, `durée ${dur.toFixed(2)} s, ${(info.format.size / 1048576).toFixed(1)} Mo`);

const loud = ff(["-i", video, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]);
const I = (loud.match(/I:\s+(-?[\d.]+) LUFS/g) || []).pop(), TP = (loud.match(/Peak:\s+(-?[\d.]+) dBFS/g) || []).pop();
const iv = I ? +I.match(/-?[\d.]+/)[0] : NaN, tp = TP ? +TP.match(/-?[\d.]+/)[0] : NaN;
ok(iv > -16 && iv < -11, `loudness intégrée ${iv} LUFS (cible ≈ -14)`);
ok(tp <= -1, `crête vraie ${tp} dBFS (≤ -1)`);

const vis = ff(["-i", video, "-an", "-vf", "blackdetect=d=0.25:pix_th=0.05,freezedetect=n=0.002:d=2", "-f", "null", "-"]);
const blacks = [...vis.matchAll(/black_start:([\d.]+) black_end:([\d.]+)/g)].map((m) => `${(+m[1]).toFixed(2)}–${(+m[2]).toFixed(2)} s`);
const freezes = [...vis.matchAll(/freeze_start: ([\d.]+)/g)].map((m) => `${(+m[1]).toFixed(2)} s`);
ok(true, `écrans noirs : ${blacks.join(", ") || "aucun"} (vérifier qu'ils sont voulus)`);
ok(!freezes.length, `images figées > 2 s : ${freezes.join(", ") || "aucune"}`);

const sil = ff(["-i", video, "-vn", "-af", "silencedetect=noise=-45dB:d=0.5", "-f", "null", "-"]);
const silences = [...sil.matchAll(/silence_start: ([\d.]+)/g)].map((m) => `${(+m[1]).toFixed(2)} s`);
ok(!silences.length, `silences > 0,5 s : ${silences.join(", ") || "aucun"}`);

const dec = spawnSync("ffmpeg", ["-v", "error", "-i", video, "-f", "null", "-"], { encoding: "utf8" }).stderr.trim();
ok(!dec, `décodage : ${dec ? dec.split("\n").slice(0, 3).join(" | ") : "aucune erreur"}`);

const cols = 12, rows = Math.ceil(dur / cols);
spawnSync("ffmpeg", ["-y", "-loglevel", "error", "-i", video, "-vf", `fps=1,scale=216:384,tile=${cols}x${rows}`, "-frames:v", "1", path.join(outDir, "planche.jpg")]);
report.push(`\nPlanche contact (1 image/s, ${cols} par ligne) : ${path.join(outDir, "planche.jpg")}`);
const txt = report.join("\n");
fs.writeFileSync(path.join(outDir, "qa.txt"), txt);
console.log(txt);
