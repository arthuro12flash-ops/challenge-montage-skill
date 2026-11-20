# -*- coding: utf-8 -*-
"""
analyze.py - mesures objectives de fichiers WAV (on ne peut pas ecouter : on mesure).

Pour chaque fichier : duree, format, crete echantillon, crete vraie (x4), DC, 1er/dernier echantillon,
silence de tete (-40 dBFS), instant de la crete d'enveloppe (RMS 10 ms), loudness BS.1770
(integre, momentane max, court terme max), repartition d'energie par bandes, correlation G/D,
perte en mono, discontinuites suspectes (clics).

Usage : python analyze.py <fichier.wav | dossier> [...] [--json sortie.json] [--music]
"""
import glob
import json
import os
import sys

import numpy as np
from scipy import signal

from dsp import SR, loudness, mono, ns, read_wav, todb, true_peak_db, undb

BANDS = [(20, 60), (60, 250), (250, 1000), (1000, 4000), (4000, 10000), (10000, 24000)]


def band_energy(x):
    m = mono(x)
    f, p = signal.welch(m, fs=SR, nperseg=min(8192, max(256, len(m))), scaling="spectrum")
    tot = np.sum(p) + 1e-30
    out = {}
    for lo, hi in BANDS:
        sel = (f >= lo) & (f < hi)
        out[f"{lo}-{hi}"] = round(float(10 * np.log10(np.sum(p[sel]) / tot + 1e-30)), 1)
    cen = float(np.sum(f * p) / tot)
    return out, cen


def clicks(x):
    """Discontinuites : saut d'echantillon > 10x l'ecart-type local de la derivee ET > -30 dBFS."""
    d = np.max(np.abs(np.diff(x, axis=0)), axis=1)
    w = ns(0.003)
    loc = np.sqrt(np.convolve(d * d, np.ones(w) / w, mode="same")) + 1e-9
    # niveau local precedent (avant le saut) : un clic surgit d'un contexte calme
    prev = np.concatenate([np.zeros(w), loc[:-w]])
    sus = np.where((d > 10 * np.maximum(prev, 1e-6)) & (d > undb(-30)))[0]
    # regroupe les indices proches
    groups = []
    for i in sus:
        if not groups or i - groups[-1] > ns(0.005):
            groups.append(i)
    return [round(i / SR, 4) for i in groups]


def analyze(path, music=False):
    x, sr, bits = read_wav(path)
    n = x.shape[0]
    a = np.max(np.abs(x), axis=1)
    peak = float(todb(a.max()))
    res = {
        "file": os.path.basename(path), "sr": sr, "bits": bits, "ch": x.shape[1],
        "dur": round(n / SR, 4), "peak_dbfs": round(peak, 2), "tp_dbtp": round(true_peak_db(x), 2),
        "dc_db": round(float(todb(np.max(np.abs(x.mean(axis=0))))), 1),
        "first": float(np.max(np.abs(x[0]))), "last": float(np.max(np.abs(x[-1]))),
        "lead_s": round(int(np.argmax(a > undb(-40))) / SR, 4),
        "t_peak": round(int(np.argmax(a)) / SR, 4),
    }
    w = ns(0.01)
    env = np.sqrt(np.convolve(np.sum(x * x, axis=1) / 2, np.ones(w) / w, mode="same"))
    res["t_env_peak"] = round(int(np.argmax(env)) / SR, 4)
    # fin du son (dernier instant > -50 dB sous la crete d'enveloppe)
    above = np.where(env > env.max() * undb(-50))[0]
    res["t_end_-50"] = round(int(above[-1]) / SR, 3) if len(above) else 0.0
    L = loudness(x)
    res["lufs_i"] = round(L["I"], 1) if np.isfinite(L["I"]) else None
    res["lufs_m_max"] = round(L["M"], 1)
    res["lufs_s_max"] = round(L["S"], 1)
    be, cen = band_energy(x)
    res["bands_db"] = be
    res["centroid_hz"] = int(cen)
    if x.shape[1] == 2:
        c = np.corrcoef(x[:, 0], x[:, 1])[0, 1] if np.std(x[:, 0]) > 0 and np.std(x[:, 1]) > 0 else 1.0
        res["corr_lr"] = round(float(c), 2)
        mono_sum = np.stack([x.mean(axis=1)] * 2, axis=1)
        Lm = loudness(mono_sum)
        res["mono_loss_db"] = round(Lm["M"] - L["M"], 1)
    res["clicks_s"] = clicks(x)[:8]
    if music:
        # couture de boucle : saut fin -> debut compare au saut typique
        jump = float(np.max(np.abs(x[0] - x[-1])))
        typ = float(np.percentile(np.max(np.abs(np.diff(x, axis=0)), axis=1), 99.9))
        res["loop_jump"] = round(jump, 5)
        res["diff_p999"] = round(typ, 5)
    return res


def main(argv):
    music = "--music" in argv
    out_json = None
    if "--json" in argv:
        out_json = argv[argv.index("--json") + 1]
    paths = []
    for a in argv:
        if a.startswith("--") or a == out_json:
            continue
        if os.path.isdir(a):
            paths += sorted(glob.glob(os.path.join(a, "*.wav")))
        elif a.lower().endswith(".wav"):
            paths.append(a)
    rows = []
    for p in paths:
        r = analyze(p, music)
        rows.append(r)
        b = r["bands_db"]
        print(f"{r['file'][:30]:30s} {r['dur']:7.3f}s {r['bits']}b pk{r['peak_dbfs']:6.2f} tp{r['tp_dbtp']:6.2f} "
              f"dc{r['dc_db']:6.0f} f/l {r['first']:.0e}/{r['last']:.0e} lead{r['lead_s']:.3f} "
              f"tpk{r['t_env_peak']:.3f} end{r['t_end_-50']:.2f} I{str(r['lufs_i']):>6s} M{r['lufs_m_max']:6.1f} "
              f"S{r['lufs_s_max']:6.1f} cen{r['centroid_hz']:5d} corr{r.get('corr_lr', 1):5.2f} "
              f"mono{r.get('mono_loss_db', 0):5.1f} | <60 {b['20-60']:5.1f} 60-250 {b['60-250']:5.1f} "
              f"250-1k {b['250-1000']:5.1f} 1-4k {b['1000-4000']:5.1f} 4-10k {b['4000-10000']:5.1f} "
              f">10k {b['10000-24000']:5.1f} clicks {r['clicks_s']}"
              + (f" loopjump {r['loop_jump']} (p99.9 diff {r['diff_p999']})" if music else ""), flush=True)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
