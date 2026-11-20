#!/usr/bin/env node
// Signale les mots coupés par les entrées/sorties des segments à vitesse normale.
//   node check_cuts.mjs <projet.config.mjs>
// À lancer après chaque modification de la liste de montage : une coupe au milieu d'un mot s'entend
// comme un « son coupé » (c'est le défaut le plus remarqué par les spectateurs).
// Les lignes qui ne montrent qu'une ponctuation (« ?[…] », « ![…] ») sont du bruit de whisper : ignorez-les.
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const cfgPath = process.argv[2];
if (!cfgPath) { console.log("usage : node check_cuts.mjs <projet.config.mjs>"); process.exit(1); }
const { PROJECT, SEGMENTS } = await import(pathToFileURL(path.resolve(cfgPath)).href);
const phones = PROJECT.phones || [];
const pieces = phones.flatMap((p, i) => p.pieces.map((q) => ({ ...q, n: i })));
const inPiece = (t) => pieces.some((q) => t >= q.a && t <= q.b);
const j = JSON.parse(fs.readFileSync(PROJECT.transcript, "utf8"));
const words = [
  ...j.segments.flatMap((g) => g.words).filter((w) => !inPiece(w.start)),
  ...pieces.flatMap((q) => JSON.parse(fs.readFileSync(phones[q.n].transcript, "utf8")).segments.flatMap((g) => g.words)
    .map((w) => ({ ...w, start: w.start + q.off, end: w.end + q.off })).filter((w) => w.start >= q.a && w.start <= q.b)),
].filter((w) => w.word.trim() && w.probability > 0.1);

const f = (a) => a.map((w) => `${w.word.trim()}[${w.start.toFixed(2)}-${w.end.toFixed(2)}]`).join(" ");
let issues = 0;
for (const s of SEGMENTS) {
  if ((s.kind && s.kind !== "clip") || (s.speed && s.speed !== 1) || s.reverse || s.file) continue;
  const cutIn = words.filter((w) => w.start < s.in && w.end > s.in + 0.02);
  const cutOut = words.filter((w) => w.start < s.out - 0.02 && w.end > s.out);
  const nearIn = words.filter((w) => w.end <= s.in && w.end > s.in - 0.25);
  const nearOut = words.filter((w) => w.start >= s.out && w.start < s.out + 0.35);
  if (cutIn.length || cutOut.length || nearIn.length || nearOut.length) {
    issues++;
    console.log(`${s.id.padEnd(6)} ${s.in}–${s.out}  coupé à l'entrée : ${f(cutIn) || "—"} | juste avant : ${f(nearIn) || "—"} | coupé à la sortie : ${f(cutOut) || "—"} | juste après : ${f(nearOut) || "—"}`);
  }
}
console.log(issues ? `\n${issues} segment(s) à vérifier.` : "Aucun mot coupé.");
