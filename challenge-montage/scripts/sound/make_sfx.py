# -*- coding: utf-8 -*-
"""
make_sfx.py - banque de bruitages 100 % synthese (numpy/scipy), aucun echantillon externe.

Sortie : assets/sfx/<nom>.wav (dans le dossier du skill)  (48 kHz, stereo, PCM 24 bits, crete -1 dBFS,
fondu d'entree 2 ms + fondu de sortie 5 ms, debut du son a t = 0).

Usage :
  uv run --no-project --python 3.12 --with numpy --with scipy python make_sfx.py            (tout)
  uv run ... python make_sfx.py whoosh_short_a rim_clang_b                                   (selection)
"""
import os
import sys
import time

import numpy as np

from dsp import (SR, add_at, bp, colored, damped, env_beta, eq, fade_io, hp, lp, make_ir, mtof, nrm,
                 ns, pad_to, pan, phase_acc, pk, pingpong, pulse_f, reverb, rbj, rms, rng, sat, saw_f,
                 smoothstep, sosf, st, svf, tt, undb, white, write_wav, fade_tail)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "assets", "sfx"))

REG = {}


def sfx(name, desc, use, target, sync="start"):
    """Enregistre une recette. target = niveau conseille (dB) par rapport a la voix (-14 LUFS),
    en LUFS momentane max. sync : start | peak | end | hit (repere de calage a documenter)."""
    def deco(fn):
        REG[name] = dict(fn=fn, desc=desc, use=use, target=target, sync=sync)
        return fn
    return deco


_IRS = {}
_IR_SPECS = {
    "gym": dict(rt60=1.7, predelay=0.018, seed=3, lf=1.1, hf=0.55),
    "room": dict(rt60=0.6, predelay=0.005, seed=5, lf=1.0, hf=0.6),
    "hall": dict(rt60=2.2, predelay=0.022, seed=7, lf=1.25, hf=0.45),
    "boom": dict(rt60=1.5, predelay=0.004, seed=9, lf=1.3, hf=0.3),
    "bright": dict(rt60=1.3, predelay=0.0, seed=21, lf=0.8, hf=0.9, build_ms=2.0),
}


def IR(kind):
    if kind not in _IRS:
        _IRS[kind] = make_ir(**_IR_SPECS[kind])
    return _IRS[kind]


def finish(x, dur=None, tail=0.0, hp_hz=25.0, fin=0.002, fout=0.005, trim=True, peak_db=-1.0):
    """Passe-haut anti-DC, suppression du silence de tete, duree, fondus, crete a peak_db."""
    x = st(x)
    if hp_hz:
        x = hp(x, hp_hz, 2)
    if trim:
        a = np.max(np.abs(x), axis=1)
        i0 = int(np.argmax(a > a.max() * undb(-50.0)))
        x = x[i0:]
    if dur is not None:
        x = pad_to(x, ns(dur))
    if tail > 0:
        x = fade_tail(x, tail)
    x = fade_io(x, fin, fout)
    return x * (undb(peak_db) / np.max(np.abs(x)))


# =========================================================================== generateurs communs
def whoosh_core(dur, peak, f0, f1, f2, q=1.4, body=0.5, air=0.25, tonal=0.0, tq=6.0, seed=1,
                pan0=-0.6, pan1=0.6, a=2.0):
    """Bruit filtre a bande glissante + corps grave + air, enveloppe lisse, deplacement stereo."""
    n = ns(dur)
    u = (np.arange(n) + 0.5) / n
    env = env_beta(n, peak, a)
    p = min(peak, 0.999)
    fc = np.where(u <= p, f0 * (f1 / f0) ** np.clip(u / p, 0, 1),
                  f1 * (f2 / f1) ** np.clip((u - p) / max(1 - p, 1e-3), 0, 1))
    chans = []
    for ch in range(2):
        nz = white(n, seed * 101 + ch)
        sig = nrm(svf(nz, fc, q, "bpn"))
        if body:
            sig = sig + body * nrm(svf(nz, fc * 0.45, 0.7, "lp"))
        if air:
            sig = sig + air * nrm(hp(nz, 4500.0, 2)) * np.clip(fc / f1, 0, 1.2)
        if tonal:
            sig = sig + tonal * nrm(svf(nz, fc * 0.7, tq, "bpn"))
        chans.append(sig * env)
    x = np.stack(chans, axis=1)
    pp = pan0 + (pan1 - pan0) * smoothstep(u)
    th = (np.clip(pp, -1, 1) + 1) * np.pi / 4
    x[:, 0] *= np.sqrt(2) * np.cos(th)
    x[:, 1] *= np.sqrt(2) * np.sin(th)
    return x


def cymbal(dur, seed, tau=0.6):
    """Cymbale (crash) : partiels inharmoniques + bruit aigu + oscillateurs carres facon 808."""
    n = ns(dur)
    t = tt(n)
    r = rng(seed)
    out = np.zeros((n, 2))
    for ch in range(2):
        acc = np.zeros(n)
        for _ in range(36):
            f = r.uniform(2800, 13500)
            tk = tau * r.uniform(0.5, 1.4) * (6000.0 / f) ** 0.3
            acc += np.sin(2 * np.pi * f * t + r.uniform(0, 2 * np.pi)) * np.exp(-t / tk) * r.uniform(0.3, 1.0)
        nz = hp(white(n, seed * 7 + ch), 4000, 2) * np.exp(-t / (tau * 0.8))
        sq = sum(pulse_f(fq * 1.47, 0.5, n, r.random()) for fq in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0))
        sq = bp(sq, 3000, 11000, 2) * np.exp(-t / (tau * 0.6))
        out[:, ch] = 0.5 * nrm(acc) + 0.6 * nrm(nz) + 0.4 * nrm(sq)
    return out * (1 - np.exp(-t / 0.0007))[:, None]


def metal_shing(n, seed, lo=2500, hi=9000, k=12, tau=(0.25, 0.4)):
    t = tt(n)
    r = rng(seed)
    x = np.zeros(n)
    for _ in range(k):
        x += np.sin(2 * np.pi * r.uniform(lo, hi) * t) * np.exp(-t / r.uniform(*tau)) * r.uniform(0.4, 1)
    return x * (1 - np.exp(-t / 0.001))


# =========================================================================== whooshes
@sfx("whoosh_short_a", "Whoosh court et brillant (bruit a bande montante puis descendante, passe de G a D).",
     "Transition rapide, coupe sur le temps, apparition d'un texte.", -8, "peak")
def _():
    return finish(whoosh_core(0.25, 0.42, 500, 2600, 1100, q=1.6, body=0.5, air=0.35, seed=1,
                              pan0=-0.5, pan1=0.5), dur=0.25)


@sfx("whoosh_short_b", "Whoosh court plus sourd et plus 'souffle', leger sifflement tonal (D vers G).",
     "Transition discrete sous une voix, changement de plan.", -9, "peak")
def _():
    return finish(whoosh_core(0.25, 0.45, 250, 1300, 500, q=2.2, body=0.8, air=0.15, tonal=0.35, tq=8,
                              seed=2, pan0=0.4, pan1=-0.4), dur=0.25)


@sfx("whoosh_long_a", "Whoosh ample 0,6 s qui traverse l'image de gauche a droite.",
     "Transition de section, zoom/travelling, entree d'une carte joueur.", -8, "peak")
def _():
    return finish(whoosh_core(0.6, 0.5, 220, 3200, 700, q=1.3, body=0.6, air=0.3, seed=3,
                              pan0=-0.8, pan1=0.8), dur=0.6)


@sfx("whoosh_long_b", "Whoosh long grave et tonal ('vvvouf'), de droite a gauche.",
     "Gros mouvement de camera, passage au ralenti.", -8, "peak")
def _():
    return finish(whoosh_core(0.6, 0.55, 140, 1700, 380, q=2.5, body=0.9, air=0.15, tonal=0.5, tq=7,
                              seed=4, pan0=0.7, pan1=-0.7), dur=0.6)


@sfx("whoosh_reverse_a", "Whoosh inverse (souffle + reverb a l'envers) qui monte et s'arrete net sur son pic.",
     "Aligner la FIN du fichier sur la coupe / l'impact (aspiration avant un plan).", -8, "end")
def _():
    L = ns(1.3)
    bl = ns(0.05)
    burst = np.zeros(L)
    burst[:bl] = white(bl, 7) * np.exp(-tt(bl) / 0.012)
    burst = bp(burst, 250, 9000, 2)
    fwd = reverb(burst, IR("bright"), wet=1.0, dry=0.4)[:L]
    x = fwd[: ns(0.8)][::-1]
    sweep = whoosh_core(0.8, 1.0, 300, 6500, 6500, q=1.1, body=0.3, air=0.5, seed=22,
                        pan0=-0.35, pan1=0.35, a=1.6)
    x = nrm(x) + 0.55 * nrm(sweep)
    return finish(x, dur=0.8, fout=0.003, trim=False)


@sfx("whoosh_reverse_b", "Cymbale a l'envers (1 s) : nappe metallique qui gonfle jusqu'a la coupe.",
     "Montee vers un drop, un freeze frame ou l'apparition d'un score : FIN du fichier = coupe.", -9, "end")
def _():
    cym = cymbal(1.6, seed=31, tau=0.55)
    x = cym[: ns(1.0)][::-1]
    return finish(x, dur=1.0, fout=0.003, trim=False)


# =========================================================================== impacts / graves
@sfx("impact_hit_a", "Impact sec : coup grave (sinus a chute de hauteur) + claquement + transitoire.",
     "Punch sur un mot cle, apparition d'un titre, tremblement d'image.", -4, "start")
def _():
    n = ns(1.0)
    t = tt(n)
    f = 46 + 124 * np.exp(-t / 0.028)
    sub = np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / 0.19)
    body = pk(damped(110, 0.06, n, 1.0, fdrop=0.3, fdrop_tau=0.01) + damped(220, 0.035, n, 0.6, fdrop=0.2))
    punch = pk(lp(white(n, 41), 900, 2) * np.exp(-t / 0.022))
    crack = pk(bp(white(n, 43), 900, 3500, 2) * np.exp(-t / 0.010))
    click = pk(hp(white(n, 42), 2500, 2) * np.exp(-t / 0.0025))
    x = sub + 0.75 * body + 0.7 * punch + 0.45 * crack + 0.3 * click
    x = sat(x * 1.3, 1.8)
    x = reverb(x, IR("room"), wet=0.12)
    return finish(x, dur=1.0, tail=0.25)


@sfx("impact_hit_b", "Impact cinema : grosse basse + craquement sature + longue queue de hall (2 s).",
     "Gros moment : panier decisif, victoire, revelation.", -5, "start")
def _():
    n = ns(2.0)
    t = tt(n)
    f = 36 + 120 * np.exp(-t / 0.05)
    sub = np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / 0.65)
    body = pk(damped(90, 0.10, n, 1.0, fdrop=0.35, fdrop_tau=0.015) + damped(180, 0.05, n, 0.6, fdrop=0.2))
    crunch = sat(pk(bp(white(n, 51), 180, 3200, 2) * np.exp(-t / 0.07)) * 3, 3)
    click = pk(hp(white(n, 52), 3000, 2) * np.exp(-t / 0.003))
    x = sub + 0.7 * body + 0.55 * crunch + 0.3 * click
    x = sat(x * 1.2, 1.5)
    x = reverb(x, IR("hall"), wet=0.28)
    return finish(x, dur=2.0, tail=0.6)


@sfx("bass_drop_a", "808 qui plonge (106 -> 31 Hz) en 1,5 s, harmoniques ajoutees pour rester audible sur telephone.",
     "Drop de musique, moment 'choc', ralenti dramatique.", -4, "start")
def _():
    n = ns(1.5)
    t = tt(n)
    f = 31 + 75 * np.exp(-t / 0.33)
    y = np.sin(2 * np.pi * phase_acc(f)) * (1 - np.exp(-t / 0.002)) * (0.75 + 0.25 * np.exp(-t / 0.4))
    h = sat(y, 3.0, asym=0.15)
    x = lp(0.6 * y + 0.55 * h, 1400, 2)
    kf = 60 + 140 * np.exp(-t / 0.01)
    click = np.sin(2 * np.pi * phase_acc(kf)) * np.exp(-t / 0.03)
    x = x + 0.5 * click
    return finish(x, dur=1.5, tail=0.45, hp_hz=18)


@sfx("bass_drop_b", "808 'phonk' tres distordu : chute rapide 180 -> 29 Hz, grain agressif.",
     "Moment drole/choc, entree de la musique 'drop_winner', effet meme.", -4, "start")
def _():
    n = ns(1.5)
    t = tt(n)
    f = 29 + 150 * np.exp(-t / 0.11)
    y = (np.sin(2 * np.pi * phase_acc(f)) + 0.35 * lp(saw_f(f * 1.01), 300, 2)) * (1 - np.exp(-t / 0.002))
    y *= 0.7 + 0.3 * np.exp(-t / 0.5)
    h = sat(y * 1.0, 5.0, asym=0.2)
    x = lp(0.35 * y + 0.75 * h, 2200, 2)
    kf = 55 + 160 * np.exp(-t / 0.008)
    x = x + 0.45 * np.sin(2 * np.pi * phase_acc(kf)) * np.exp(-t / 0.025)
    return finish(x, dur=1.5, tail=0.45, hp_hz=18)


@sfx("sub_boom_a", "Boom grave reverbere facon meme (88 -> 38 Hz, distorsion douce, grande reverb sombre).",
     "Chute comique, 'bruh moment', revelation, mot choc.", -3, "start")
def _():
    n = ns(1.2)
    t = tt(n)
    f = 38 + 50 * np.exp(-t / 0.09)
    body = np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / 0.45) * (1 - np.exp(-t / 0.002))
    bwom = damped(120, 0.12, n, 0.5, fdrop=0.25, fdrop_tau=0.03) + damped(240, 0.05, n, 0.2, fdrop=0.2)
    thump = pk(lp(white(n, 71), 250, 2) * np.exp(-t / 0.04))
    mid = pk(bp(white(n, 72), 300, 1500, 2) * np.exp(-t / 0.03))
    dry = body + bwom + 0.8 * thump + 0.3 * mid
    x = 0.35 * dry + 0.65 * lp(sat(dry * 4.0, 4.0, asym=0.1), 2500, 2)
    x = reverb(x, IR("boom"), wet=0.45)
    return finish(x, dur=1.2, tail=0.35, hp_hz=20)


@sfx("sub_boom_b", "Boom plus profond et plus propre, queue plus longue (1,2 s).",
     "Suspense, apparition du score final, transition lourde.", -3, "start")
def _():
    n = ns(1.2)
    t = tt(n)
    f = 34 + 40 * np.exp(-t / 0.12)
    body = np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / 0.6) * (1 - np.exp(-t / 0.002))
    bwom = damped(100, 0.15, n, 0.35, fdrop=0.2, fdrop_tau=0.03)
    thump = pk(lp(white(n, 73), 180, 2) * np.exp(-t / 0.05))
    dry = body + bwom + 0.6 * thump
    x = 0.5 * dry + 0.5 * lp(sat(dry * 2.8, 2.8, asym=0.1), 1500, 2)
    x = reverb(x, IR("hall"), wet=0.35)
    return finish(x, dur=1.2, tail=0.4, hp_hz=20)


# =========================================================================== montees / descentes
@sfx("riser_a", "Montee 2 s : bruit filtre qui s'ouvre + accord de La mineur qui monte d'une octave + tremolo qui accelere. S'arrete net.",
     "Avant un drop, un panier, une revelation : la FIN du fichier tombe sur l'evenement.", -10, "end")
def _():
    dur = 2.0
    n = ns(dur)
    u = (np.arange(n) + 0.5) / n
    fc = 250 * (9000 / 250) ** (u ** 1.3)
    qv = 0.9 + 2.2 * u
    noise = np.stack([nrm(svf(white(n, 61 + c), fc, qv, "bpn")) for c in range(2)], 1)
    air = np.stack([nrm(hp(white(n, 63 + c), 6000, 2)) for c in range(2)], 1) * (u ** 3)[:, None]
    semis = 12.0 * u ** 2
    ton = np.zeros((n, 2))
    r = rng(64)
    for m in (57, 64, 69):
        for v in range(5):
            det = (v - 2) * 9.0 + r.uniform(-2, 2)
            f = mtof(m) * 2 ** ((semis * 100 + det) / 1200)
            ton += pan(saw_f(f, None, r.random()), (v - 2) / 2.5)
    ton = svf(ton, 350 * (7000 / 350) ** u, 1.2, "lp")
    rate = 3 + 21 * u ** 2
    gate = 1 - (0.15 + 0.55 * u) * (0.5 - 0.5 * np.cos(2 * np.pi * phase_acc(rate)))
    x = 0.75 * noise + 0.35 * air + 0.45 * nrm(ton)
    x *= (gate * undb(-27 * (1 - u) ** 1.25))[:, None]
    return finish(x, dur=dur, fout=0.003, trim=False)


@sfx("riser_b", "Montee 2 s sans hauteur (pas de conflit de tonalite) : souffle qui s'ouvre + roulement de coups qui accelere. S'arrete net.",
     "Suspense avant une reponse, avant le dernier tir. FIN = evenement.", -10, "end")
def _():
    dur = 2.0
    n = ns(dur)
    u = (np.arange(n) + 0.5) / n
    fc = 300 * (7000 / 300) ** (u ** 1.2)
    noise = np.stack([nrm(svf(white(n, 81 + c), fc, 1.0, "bpn")) for c in range(2)], 1)
    hits = np.zeros((n, 2))
    tk, iv, i = 0.0, 0.22, 0
    while tk < dur - 0.03:
        L = ns(0.06)
        h = (pk(bp(white(L, 700 + i), 900, 6000, 2) * np.exp(-tt(L) / 0.018))
             + damped(220 * rng(800 + i).uniform(0.85, 1.25), 0.02, L, 0.18))
        add_at(hits, ns(tk), pan(h * (0.25 + 0.75 * (tk / dur) ** 1.5), 0.2 * np.sin(i)))
        tk += iv
        iv = max(0.022, iv * 0.86)
        i += 1
    x = 0.7 * noise + 0.9 * pk(hits) * 2.5
    x *= undb(-25 * (1 - u) ** 1.2)[:, None]
    return finish(x, dur=dur, fout=0.003, trim=False)


@sfx("downlifter_a", "Descente 1 s : souffle qui se referme + double dent de scie qui chute de 2 octaves.",
     "Retour au calme apres un gros moment, sortie d'une section, avant une explication.", -10, "start")
def _():
    n = ns(1.0)
    t = tt(n)
    u = (np.arange(n) + 0.5) / n
    fc = 9000 * (180 / 9000) ** (u ** 0.7)
    noise = np.stack([nrm(svf(white(n, 91 + c), fc, 1.3, "bpn")) for c in range(2)], 1)
    f = 440 * 2 ** (-24 * u ** 0.8 / 12)
    ton = pan(saw_f(f * 2 ** (7 / 1200)), -0.5) + pan(saw_f(f * 2 ** (-7 / 1200), None, 0.3), 0.5)
    ton = svf(ton, 5000 * (300 / 5000) ** u, 1.0, "lp")
    env = (1 - u) ** 1.6 * (1 - np.exp(-t / 0.002))
    x = (0.8 * noise + 0.5 * nrm(ton)) * env[:, None]
    return finish(x, dur=1.0, tail=0.05)


@sfx("downlifter_b", "Descente grave 1 s : sinus 170 -> 38 Hz sature + souffle descendant.",
     "Fin d'un moment de hype, 'retombee', transition vers une scene calme.", -9, "start")
def _():
    n = ns(1.0)
    t = tt(n)
    u = (np.arange(n) + 0.5) / n
    f = 38 + 132 * (1 - u) ** 2.2
    s = np.sin(2 * np.pi * phase_acc(f))
    s = 0.6 * s + 0.5 * sat(s, 3.0, asym=0.12)
    fc = 4000 * (150 / 4000) ** u
    noise = np.stack([nrm(svf(white(n, 95 + c), fc, 1.0, "bpn")) for c in range(2)], 1)
    env = (1 - u) ** 1.3 * (1 - np.exp(-t / 0.002))
    x = (st(lp(s, 1200, 2)) * 1.0 + 0.45 * noise) * env[:, None]
    return finish(x, dur=1.0, tail=0.05, hp_hz=20)


# =========================================================================== basket
def swish(seed, n_grains=240, f_lo=1800.0, f_hi=7500.0, body=0.25, smooth=0.4, dur=0.35, center=0.06):
    """Ballon dans le filet : nuee de micro-frottements (grains) + souffle + petit 'fwip' grave."""
    n = ns(dur)
    t = tt(n)
    r = rng(seed)
    grains = np.zeros((n, 2))
    for g in range(n_grains):
        t0 = 0.003 + r.gamma(2.0, center / 2.0)
        if t0 > dur - 0.03:
            continue
        L = int(r.uniform(0.0008, 0.0035) * SR)
        e = np.exp(-tt(L) / (L / SR / 3)) * (1 - np.exp(-tt(L) / 0.0002))
        burst = np.concatenate([white(L, seed * 1000 + g) * e, np.zeros(ns(0.004))])
        burst = sosf(burst, rbj("bpf", r.uniform(f_lo, f_hi), r.uniform(1.5, 4.0)))
        dens = np.exp(-max(t0 - center, 0.0) / 0.07)
        add_at(grains, ns(t0), pan(burst * r.uniform(0.3, 1.0) * dens, r.uniform(-0.6, 0.6)))
    sm_env = (1 - np.exp(-t / 0.012)) * np.exp(-t / 0.075)
    sm = np.stack([nrm(bp(white(n, seed + 50 + c), 1500, 7000, 2)) for c in range(2)], 1) * sm_env[:, None]
    lo_env = (1 - np.exp(-t / 0.015)) * np.exp(-t / 0.05)
    lo_ = nrm(bp(white(n, seed + 60), 180, 700, 2)) * lo_env
    x = pk(grains) + smooth * pk(sm) + body * pk(st(lo_))
    x = reverb(x, IR("gym"), wet=0.07, keep_len=True)
    return finish(x, dur=dur, tail=0.06)


@sfx("swish_net_a", "'Swish' net : le ballon passe dans le filet sans toucher le cercle (0,35 s).",
     "Au moment EXACT ou le ballon traverse le filet (debut du fichier = entree dans le filet).", -6, "start")
def _():
    return swish(101)


@sfx("swish_net_b", "Variante plus dense et un peu plus grave du swish (0,35 s).",
     "Alterner avec swish_net_a pour eviter la repetition sur plusieurs paniers.", -6, "start")
def _():
    return swish(202, n_grains=300, f_lo=1300, f_hi=5500, body=0.35, smooth=0.5, center=0.07)


def bounce_core(seed, pitch=1.0, ring=1.0, slap=0.5, dur=0.6):
    """Rebond de ballon : transitoire + modes graves du ballon/parquet + 'ping' de la cavite."""
    n = ns(dur)
    t = tt(n)
    tr = pk(lp(white(n, seed), 3500, 2) * np.exp(-t / 0.0015))
    body = (damped(155 * pitch, 0.030, n, 1.0, fdrop=0.15, fdrop_tau=0.008)
            + damped(92, 0.065, n, 0.75)
            + damped(310 * pitch, 0.022, n, 0.6, fdrop=0.1)
            + damped(520 * pitch, 0.014, n, 0.35))
    rg = (damped(1040 * pitch, 0.08, n, 0.10) + damped(1490 * pitch, 0.05, n, 0.06)
          + damped(2260 * pitch, 0.035, n, 0.035))
    x = pk(body) + 0.35 * slap * tr + 0.12 * ring * pk(rg)
    return sat(x * 1.2, 1.3)


@sfx("ball_bounce_a", "Rebond de ballon sur parquet, proche, avec petite reverb de gymnase.",
     "Dribble a l'image, ponctuation 'pom' d'un texte, transition sportive.", -8, "start")
def _():
    x = reverb(bounce_core(111), IR("gym"), wet=0.14)
    return finish(x, dur=0.9, tail=0.3)


@sfx("ball_bounce_b", "Rebond plus lointain et plus 'claque' (plus de salle).",
     "Ambiance de match, rebond hors champ.", -8, "start")
def _():
    x = reverb(bounce_core(112, pitch=0.92, ring=0.6, slap=0.9), IR("gym"), wet=0.25)
    return finish(x, dur=0.9, tail=0.3)


@sfx("ball_dribble", "Dribble : 4 rebonds reguliers (0,43 s d'ecart) dans un gymnase.",
     "Sous une presentation de joueur, transition, intro du jeu.", -8, "start")
def _():
    n = ns(1.9)
    x = np.zeros(n)
    for i, (tb, pi, am) in enumerate([(0.0, 1.0, 1.0), (0.43, 0.98, 0.92), (0.86, 1.02, 0.96), (1.29, 0.99, 0.9)]):
        add_at(x, ns(tb), am * bounce_core(120 + i, pitch=pi, dur=0.5))
    x = reverb(x, IR("gym"), wet=0.16)
    return finish(x, dur=1.9, tail=0.4)


def clang_core(seed, n, f0=420.0, amp=1.0, decay=1.0):
    """Cercle metallique frappe : modes d'anneau inharmoniques (paires desaccordees -> battements)."""
    t = tt(n)
    r = rng(seed)
    ratios = [1.0, 2.82, 5.36, 8.67, 12.6, 16.9]
    taus = [0.38, 0.32, 0.2, 0.12, 0.07, 0.045]
    amps = [0.75, 0.85, 0.6, 0.38, 0.2, 0.1]
    x = np.zeros(n)
    for ra, ta, am in zip(ratios, taus, amps):
        f = f0 * ra * r.uniform(0.99, 1.01)
        x += damped(f, ta * decay, n, am * 0.5) + damped(f * 1.0045, ta * decay * 0.9, n, am * 0.5)
    thump = damped(175, 0.025, n, 0.8, fdrop=0.2) + damped(95, 0.07, n, 0.4)
    tr = pk(lp(white(n, seed + 1), 5000, 2) * np.exp(-t / 0.002))
    rattle = pk(bp(white(n, seed + 2), 800, 3000, 2) * (0.5 + 0.5 * np.sin(2 * np.pi * 28 * t)) * np.exp(-t / 0.12))
    return amp * (pk(x) + 0.55 * pk(thump) + 0.3 * tr + 0.12 * rattle)


@sfx("rim_clang_a", "Ballon sur le cercle : 'clang' metallique qui resonne (1,2 s).",
     "Tir rate qui touche le cercle, moment de tension, effet comique.", -8, "start")
def _():
    n = ns(1.2)
    x = sat(clang_core(131, n), 1.2)
    x = reverb(x, IR("gym"), wet=0.22)
    return finish(x, dur=1.2, tail=0.4)


@sfx("rim_clang_b", "Ballon qui tourne sur le cercle : 3 chocs metalliques (dedans-dehors), 1,5 s.",
     "Tir qui hesite / ressort du cercle, suspense avant un panier ou un rate.", -8, "start")
def _():
    n = ns(1.5)
    x = np.zeros(n)
    add_at(x, 0, clang_core(141, n, 420.0, 1.0))
    add_at(x, ns(0.17), clang_core(142, n, 423.0, 0.55, 0.8))
    add_at(x, ns(0.31), clang_core(143, n, 418.0, 0.25, 0.6))
    x = reverb(sat(x, 1.2), IR("gym"), wet=0.22)
    return finish(x, dur=1.5, tail=0.4)


@sfx("buzzer", "Buzzer de fin de match (klaxon de salle grave et rugueux, 1 s, avec salle).",
     "Fin du match, fin d'une manche, 'temps ecoule' avant une reponse.", -6, "start")
def _():
    n = ns(0.86)
    t = tt(n)
    f0 = 196 * (1 + 0.002 * np.sin(2 * np.pi * 5.3 * t))
    osc = pulse_f(f0, 0.3) + 0.8 * pulse_f(f0 * 1.0065, 0.42, None, 0.3) + 0.5 * saw_f(f0 * 2.003, None, 0.1)
    osc *= 1 + 0.12 * np.sin(2 * np.pi * 60 * t)
    osc = eq(osc, "peak", 950, 1.2, 6)
    osc = eq(osc, "peak", 2300, 1.5, 4)
    osc = hp(lp(osc, 6000, 2), 120, 2)
    osc = sat(pk(osc) * 1.6, 2.0)
    env = np.clip(t / 0.006, 0, 1) * np.clip((t[-1] - t) / 0.025, 0, 1)
    x = reverb(osc * env, IR("gym"), wet=0.22)
    return finish(x, dur=1.0, tail=0.12)


def whistle_blast(dur, seed, f=2950.0):
    n = ns(dur)
    t = tt(n)
    wob = lp(white(n, seed), 6.0, 1)
    rate = 36 + 7 * wob / (np.std(wob) + 1e-9)
    mod = np.sin(2 * np.pi * phase_acc(rate))
    ph = phase_acc(f * (1 - 0.02 * smoothstep((t - (dur - 0.06)) / 0.06)) + 130 * mod)
    tone = np.sin(2 * np.pi * ph) + 0.10 * np.sin(4 * np.pi * ph) + 0.03 * np.sin(6 * np.pi * ph)
    am = 0.72 + 0.28 * (0.5 + 0.5 * mod)
    breath = 0.10 * nrm(sosf(white(n, seed + 1), rbj("bpf", f, 3.0))) + 0.03 * nrm(hp(white(n, seed + 2), 6000, 2))
    env = smoothstep(t / 0.012) * smoothstep((t[-1] - t) / 0.035)
    return (tone * am + breath) * env


@sfx("whistle_a", "Coup de sifflet d'arbitre court (sifflet a bille, ~0,45 s + salle).",
     "Debut/fin d'action, faute, 'stop' comique sur une erreur.", -8, "start")
def _():
    x = reverb(whistle_blast(0.42, 151), IR("gym"), wet=0.12)
    return finish(x, dur=0.75, tail=0.25)


@sfx("whistle_b", "Double coup de sifflet bref ('tuit-tuit').",
     "Signal de debut de match, changement de joueur, rappel a l'ordre drole.", -8, "start")
def _():
    n = ns(0.5)
    x = np.zeros(n)
    add_at(x, 0, whistle_blast(0.12, 161))
    add_at(x, ns(0.2), whistle_blast(0.13, 162, f=2980.0))
    x = reverb(x, IR("gym"), wet=0.12)
    return finish(x, dur=0.65, tail=0.2)


# =========================================================================== jeu / quiz
def chime(f, n, decay=0.6, bright=1.0):
    t = tt(n)
    parts = [(1.0, 1.0, decay), (2.0, 0.32, decay * 0.45), (3.0, 0.12, decay * 0.25), (4.2, 0.07 * bright, decay * 0.12)]
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in parts)
    return x * (1 - np.exp(-t / 0.0015))


@sfx("correct_ding_a", "Validation brillante 'ding-ding' (Mi6 -> La6, clochette + echo stereo).",
     "Bonne reponse, point valide, apparition du +1.", -8, "start")
def _():
    n = ns(1.0)
    x = np.zeros((n, 2))
    add_at(x, 0, pan(chime(1318.5, n), -0.2))
    add_at(x, ns(0.085), 0.9 * pan(chime(1760.0, n), 0.2))
    x = pingpong(x, 0.11, fb=0.35, n_rep=4, lp_hz=6000, wet=0.18)
    x = reverb(x, IR("room"), wet=0.12)
    return finish(x, dur=1.0, tail=0.4)


@sfx("correct_ding_b", "Validation 'arpege + paillettes' (La majeur montant, scintillement aigu).",
     "Bonne reponse importante, point gagnant, victoire.", -8, "start")
def _():
    n = ns(1.2)
    x = np.zeros((n, 2))
    for i, (f, p) in enumerate([(880.0, -0.3), (1108.73, -0.1), (1318.51, 0.1), (1760.0, 0.3)]):
        add_at(x, ns(0.05 * i), (0.8 + 0.07 * i) * pan(chime(f, n, decay=0.5), p))
    r = rng(171)
    for k in range(10):
        L = ns(0.12)
        g = np.sin(2 * np.pi * r.uniform(4000, 9000) * tt(L)) * np.exp(-tt(L) / 0.03) * (1 - np.exp(-tt(L) / 0.001))
        add_at(x, ns(0.12 + r.uniform(0, 0.45)), 0.12 * pan(g, r.uniform(-0.8, 0.8)))
    x = reverb(x, IR("room"), wet=0.14)
    return finish(x, dur=1.2, tail=0.45)


def buzz_note(f, dur, fall=0.0):
    n = ns(dur)
    t = tt(n)
    fr = f * (1 + 0.012 * np.sin(2 * np.pi * 7 * t)) * (1 - fall * smoothstep(t / dur))
    osc = pulse_f(fr, 0.22) + 0.6 * saw_f(fr * 1.008, None, 0.2)
    osc = eq(lp(osc, 2400, 2), "peak", 700, 1.0, 4)
    env = np.clip(t / 0.005, 0, 1) * np.clip((t[-1] - t) / 0.03, 0, 1)
    return osc * env


@sfx("wrong_buzz_a", "Mauvaise reponse : double buzz grave descendant ('beu-beuuh'), drole mais pas agressif.",
     "Mauvaise reponse, tir rate, erreur.", -6, "start")
def _():
    n = ns(0.75)
    x = np.zeros(n)
    add_at(x, 0, buzz_note(155, 0.17))
    add_at(x, ns(0.21), buzz_note(110, 0.42, fall=0.1))
    x = sat(pk(x) * 1.4, 1.6)
    x = reverb(x, IR("room"), wet=0.08)
    return finish(x, dur=0.75, tail=0.08)


@sfx("wrong_buzz_b", "Mauvaise reponse cartoon : 'bwoooomp' qui degonfle (glissando descendant avec effet wah).",
     "Echec comique, ballon qui rate tout, reponse absurde.", -6, "start")
def _():
    n = ns(0.7)
    t = tt(n)
    u = (np.arange(n) + 0.5) / n
    f = 260 * (85 / 260) ** (smoothstep(u) ** 0.8)
    osc = saw_f(f) + 0.5 * pulse_f(f * 0.5, 0.5)
    wah = svf(osc, 1400 * (300 / 1400) ** u, 3.0, "bpn")
    x = 0.7 * nrm(wah) + 0.5 * nrm(lp(osc, 900, 2))
    x *= np.clip(t / 0.008, 0, 1) * np.clip((t[-1] - t) / 0.06, 0, 1)
    x = reverb(sat(pk(x) * 1.3, 1.5), IR("room"), wet=0.08)
    return finish(x, dur=0.7, tail=0.06)


@sfx("sad_trombone", "Trombone triste 'wah wah wah waaah' (4 notes chromatiques descendantes, sourdine wah, vibrato final).",
     "Gros rate, defaite, moment gene. A utiliser une ou deux fois max.", -6, "start")
def _():
    notes = [(58, 0.00, 0.40), (57, 0.43, 0.40), (56, 0.86, 0.40), (55, 1.29, 1.15)]
    out = np.zeros(ns(2.75))
    for i, (m, s, d) in enumerate(notes):
        last = i == 3
        n = ns(d + 0.08)
        t = tt(n)
        f0 = float(mtof(m))
        scoop = -0.4 * np.exp(-t / 0.045)
        vib = 0.45 * smoothstep((t - 0.25) / 0.4) * np.sin(2 * np.pi * 5.2 * t) if last else 0.0
        f = f0 * 2 ** ((scoop + vib) / 12)
        osc = saw_f(f) + 0.25 * pulse_f(f, 0.3)
        env = smoothstep(t / 0.035) * (0.85 + 0.15 * np.exp(-t / 0.2)) * np.clip((d + 0.07 - t) / 0.07, 0, 1)
        bright = smoothstep(t / 0.09) * (0.65 + 0.35 * np.exp(-t / 0.3))
        if last:
            bright = bright * (1 - 0.6 * smoothstep((t - 0.7) / 0.4))
        y = 0.7 * nrm(svf(osc, 380 + 2200 * bright, 1.4, "lp")) + 0.45 * nrm(svf(osc, 450 + 900 * bright, 2.5, "bpn"))
        breath = 0.04 * nrm(bp(white(n, 900 + i), 600, 2500, 2))
        add_at(out, ns(s), (y + breath) * env)
    x = sat(pk(out) * 1.2, 1.3)
    x = reverb(x, IR("room"), wet=0.14)
    return finish(x, dur=2.75, tail=0.25)


@sfx("boing_a", "Ressort cartoon 'boyoyoing' (hauteur qui oscille et se calme).",
     "Saut, ballon qui rebondit bizarrement, chute comique, apparition rigolote.", -8, "start")
def _():
    n = ns(0.8)
    t = tt(n)
    f = 170 * 2 ** ((6 * (1 - np.exp(-t / 0.06))) / 12) * (1 + 0.20 * np.exp(-t / 0.22) * np.sin(2 * np.pi * 13 * t))
    osc = 0.6 * saw_f(f) + 0.8 * np.sin(2 * np.pi * phase_acc(f))
    tw = svf(osc, 3.2 * f, 5.0, "bpn")
    x = (0.6 * nrm(lp(osc, 2500, 2)) + 0.6 * nrm(tw)) * (1 - np.exp(-t / 0.002)) * np.exp(-t / 0.28)
    return finish(reverb(x, IR("room"), wet=0.06), dur=0.8, tail=0.1)


@sfx("boing_b", "Ressort plus grave et plus long ('bwoiiing'), oscillation plus lente.",
     "Grosse chute / gros rate comique, personnage qui 'rebondit'.", -8, "start")
def _():
    n = ns(1.0)
    t = tt(n)
    f = 110 * 2 ** ((7 * (1 - np.exp(-t / 0.08))) / 12) * (1 + 0.25 * np.exp(-t / 0.3) * np.sin(2 * np.pi * 10 * t))
    osc = 0.6 * saw_f(f) + 0.8 * np.sin(2 * np.pi * phase_acc(f))
    tw = svf(osc, 3.5 * f, 5.0, "bpn")
    x = (0.6 * nrm(lp(osc, 2200, 2)) + 0.6 * nrm(tw)) * (1 - np.exp(-t / 0.002)) * np.exp(-t / 0.4)
    return finish(reverb(x, IR("room"), wet=0.06), dur=1.0, tail=0.12)


def pop(f_hi, f_lo, tau_f, tau_a, dur, seed):
    n = ns(dur)
    t = tt(n)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / tau_f)
    y = np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / tau_a)
    click = pk(hp(white(n, seed), 3000, 2) * np.exp(-t / 0.0008)) * 0.12
    return y + click


@sfx("pop_ui_a", "Petit 'pop' bulle (medium).", "Apparition d'un texte, d'un emoji, d'une etiquette.", -14, "start")
def _():
    return finish(pop(1100, 350, 0.012, 0.018, 0.09, 181), dur=0.09)


@sfx("pop_ui_b", "Pop plus grave et doux.", "Apparition d'un element plus gros (score, photo).", -14, "start")
def _():
    return finish(pop(650, 220, 0.015, 0.022, 0.10, 182), dur=0.10)


@sfx("pop_ui_c", "Pop aigu tres court ('blip').", "Petits elements en cascade (lettres, icones, puces).", -15, "start")
def _():
    return finish(pop(1900, 750, 0.008, 0.012, 0.07, 183), dur=0.07)


@sfx("tick_a", "Clic leger et sec (30 ms).", "Mot qui apparait dans un sous-titre anime, compteur.", -18, "start")
def _():
    n = ns(0.03)
    t = tt(n)
    x = damped(3100, 0.0022, n, 1.0) + damped(5400, 0.0012, n, 0.5) + damped(1700, 0.004, n, 0.4)
    x = x + 0.15 * pk(hp(white(n, 191), 4000, 2) * np.exp(-t / 0.0004))
    return finish(x, dur=0.03, hp_hz=200)


@sfx("tick_b", "Clic boise plus doux ('toc', 50 ms).", "Mots de sous-titres, decompte, horloge de suspense.", -18, "start")
def _():
    n = ns(0.05)
    t = tt(n)
    x = damped(1050, 0.012, n, 1.0) + damped(2650, 0.006, n, 0.45)
    x = x + 0.1 * pk(hp(white(n, 192), 3000, 2) * np.exp(-t / 0.0005))
    return finish(x, dur=0.05, hp_hz=150)


def glitch_core(seed, dur=0.3):
    n = ns(dur)
    r = rng(seed)
    x = np.zeros((n, 2))
    pos = 0
    prev = None
    while pos < n - ns(0.004):
        L = min(int(r.uniform(0.006, 0.035) * SR), n - pos)
        kind = r.choice(["tone", "noise", "stutter", "gap", "chirp"], p=[0.3, 0.25, 0.25, 0.08, 0.12])
        tl = tt(L)
        if kind == "tone":
            seg = pulse_f(r.uniform(150, 3000), r.uniform(0.1, 0.5), L)
            b = 2 ** int(r.integers(2, 5))
            seg = np.round(seg * b) / b
        elif kind == "noise":
            hold = int(r.integers(4, 17))
            seg = np.repeat(white(L // hold + 1, int(r.integers(1 << 30))), hold)[:L]
            seg = np.clip(np.round(seg * 4) / 4 * 0.5, -1, 1)
        elif kind == "stutter":
            src = prev if prev is not None else pulse_f(r.uniform(300, 2000), 0.5, L)
            sl = max(int(r.uniform(0.002, 0.006) * SR), 32)
            piece = fade_io(src[:sl], 0.0002, 0.0002)
            seg = np.tile(piece, L // sl + 1)[:L]
        elif kind == "gap":
            seg = np.zeros(L)
        else:
            f = r.uniform(2500, 5000) * (r.uniform(100, 400) / 4000) ** (tl / max(tl[-1], 1e-6))
            seg = 0.5 * np.sign(np.sin(2 * np.pi * phase_acc(f)))
        seg = fade_io(seg * r.uniform(0.4, 1.0), 0.0004, 0.0004)
        if kind != "gap":
            prev = seg
        add_at(x, pos, pan(seg, r.uniform(-0.7, 0.7)))
        pos += L
    return lp(hp(x, 120, 2), 13000, 2)


@sfx("glitch_a", "Glitch numerique 0,3 s (bursts bit-crush, begaiements, bips).",
     "Transition 'bug', effet d'image qui saute, moment absurde, apparition tech.", -10, "start")
def _():
    return finish(glitch_core(201), dur=0.3)


@sfx("glitch_b", "Autre glitch 0,3 s (sequence differente).", "Alterner avec glitch_a.", -10, "start")
def _():
    return finish(glitch_core(202), dur=0.3)


def shutter_click(n, seed, modes, low, noise_amp=0.6):
    t = tt(n)
    x = pk(bp(white(n, seed), 1500, 9000, 2) * np.exp(-t / 0.0015)) * noise_amp
    for f, tau, a in modes:
        x = x + damped(f, tau, n, a)
    return x + damped(low[0], low[1], n, low[2])


@sfx("camera_shutter_a", "Declencheur d'appareil photo ('clic-clac' mecanique, 0,24 s).",
     "Freeze frame, photo de joueur, capture d'un moment.", -10, "start")
def _():
    n = ns(0.24)
    x = np.zeros((n, 2))
    L = ns(0.06)
    add_at(x, 0, pan(shutter_click(L, 211, [(2400, .006, .8), (3900, .004, .6), (6200, .0025, .4)], (320, .008, .5)), -0.1))
    add_at(x, ns(0.072), pan(shutter_click(L, 212, [(1900, .007, .9), (3300, .005, .6), (5600, .003, .4)], (260, .012, .6), 0.7), 0.1))
    wl = ns(0.065)
    whirr = bp(white(wl, 213), 2000, 5000, 2) * np.sin(np.pi * np.arange(wl) / wl) * 0.05
    add_at(x, ns(0.005), st(whirr))
    x = reverb(x, IR("room"), wet=0.06, mono_in=False)
    return finish(x, dur=0.24, tail=0.05)


@sfx("camera_shutter_b", "Declencheur rapide + sifflement de flash qui se recharge.",
     "Freeze frame 'paparazzi', presentation de joueur facon photo officielle.", -10, "start")
def _():
    n = ns(0.45)
    x = np.zeros((n, 2))
    L = ns(0.06)
    add_at(x, 0, pan(shutter_click(L, 221, [(2700, .005, .8), (4300, .0035, .6), (6800, .002, .4)], (350, .007, .5)), -0.1))
    add_at(x, ns(0.045), pan(shutter_click(L, 222, [(2100, .006, .9), (3500, .004, .6), (6000, .0025, .4)], (280, .01, .6), 0.7), 0.1))
    wl = ns(0.35)
    tw = tt(wl)
    whine = np.sin(2 * np.pi * phase_acc(6000 + 3000 * smoothstep(tw / 0.35))) * smoothstep(tw / 0.05) * np.clip((0.35 - tw) / 0.1, 0, 1)
    add_at(x, ns(0.08), st(0.035 * whine))
    x = reverb(x, IR("room"), wet=0.06, mono_in=False)
    return finish(x, dur=0.45, tail=0.08)


def chip(f, n, duty=0.25, decay=None):
    y = pulse_f(f, duty, n)
    if decay:
        y = y * np.exp(-tt(n) / decay)
    return fade_io(y, 0.001, 0.001)


@sfx("score_up_a", "'+1' arcade : trois notes 8-bit montantes (La5-Mi6-La6) + echo.",
     "Point marque, compteur de score qui augmente.", -9, "start")
def _():
    n = ns(0.65)
    x = np.zeros(n)
    add_at(x, 0, chip(880.0, ns(0.055)))
    add_at(x, ns(0.055), chip(1318.51, ns(0.055)))
    add_at(x, ns(0.11), chip(1760.0, ns(0.3), decay=0.12))
    x = lp(x, 9000, 2)
    x = pingpong(x, 0.09, fb=0.3, n_rep=4, lp_hz=5000, wet=0.25)
    return finish(x, dur=0.65, tail=0.15)


@sfx("score_up_b", "'Bling' arcade : glissando 8-bit montant + scintillement.",
     "Bonus, point decisif, record, 'level up'.", -9, "start")
def _():
    n = ns(0.55)
    t = tt(n)
    f = 700 * (2100 / 700) ** smoothstep(t / 0.12)
    f = f * (1 + 0.01 * np.sin(2 * np.pi * 18 * t) * smoothstep((t - 0.12) / 0.05))
    y = pulse_f(f, 0.125) * np.exp(-np.maximum(t - 0.2, 0) / 0.1)
    y = lp(fade_io(y, 0.001, 0.003), 9000, 2)
    x = pingpong(y, 0.07, fb=0.3, n_rep=3, lp_hz=6000, wet=0.2)
    return finish(x, dur=0.55, tail=0.15)


# =========================================================================== foule
FORM = {
    "u": ([325, 700, 2530, 3500], [70, 90, 130, 180], [0, -8, -24, -30]),
    "o": ([450, 800, 2830, 3500], [70, 90, 130, 180], [0, -5, -20, -28]),
}


def formant_filter(src, vowel, scale):
    F, B, A = FORM[vowel]
    y = np.zeros_like(src)
    for f, b, a in zip(F, B, A):
        fs_ = f * scale
        y += undb(a) * sosf(src, rbj("bpf", fs_, fs_ / (b * scale)))
    return y


def crowd(seed, n_voices, dur, contour):
    """Foule : n voix 'oh->ou' (source dent de scie + formants), hauteurs/departs/durees aleatoires, grande salle."""
    n = ns(dur)
    r = rng(seed)
    out = np.zeros((n, 2))
    for v in range(n_voices):
        female = r.random() < 0.4
        f0 = r.uniform(175, 285) if female else r.uniform(92, 165)
        scale = (1.16 if female else 1.0) * r.uniform(0.94, 1.06)
        onset = abs(r.normal(0.04, 0.05)) + (r.random() < 0.15) * r.uniform(0.1, 0.3)
        s0 = ns(onset)
        L = min(ns(r.uniform(0.75, 1.0) * (dur - 0.5)), n - s0)
        if L < ns(0.3):
            continue
        tl = tt(L)
        u = tl / tl[-1]
        semis = contour(u, r)
        jit = lp(white(L, seed * 1000 + v), 5.0, 1)
        jit = 0.3 * jit / (np.std(jit) + 1e-9)
        vib = 0.12 * np.sin(2 * np.pi * r.uniform(4.5, 6.0) * tl + r.uniform(0, 6.28))
        f = f0 * 2 ** ((semis + jit + vib) / 12)
        src = lp(saw_f(f, None, r.random()), 2500 if female else 1800, 1)
        src = src + 0.08 * white(L, seed * 1000 + v + 500)
        mv = smoothstep(u / 0.6)
        y = (1 - mv) * formant_filter(src, "o", scale) + mv * formant_filter(src, "u", scale)
        att = r.uniform(0.08, 0.22)
        rel = r.uniform(0.3, 0.6)
        env = smoothstep(tl / att) * (1 - smoothstep((tl - (tl[-1] - rel)) / rel)) * (0.8 + 0.2 * np.sin(np.pi * u))
        dist = r.random()
        y = lp(y, 8000 - 3500 * dist, 1) * (1 - 0.45 * dist)
        g = r.uniform(0.3, 1.0) * (0.8 if female else 1.0)
        add_at(out, s0, pan(nrm(y) * env * g, r.uniform(-0.9, 0.9)))
    tb = tt(n)
    bed = np.stack([formant_filter(colored(n, seed + 7 + c, -3), "o", 1.05) for c in range(2)], 1)
    bed_env = smoothstep(tb / 0.3) * (1 - smoothstep((tb - (dur - 0.8)) / 0.8))
    out = out / (rms(out) + 1e-9) + 0.25 * nrm(bed) * bed_env[:, None]
    out = reverb(out, IR("hall"), wet=0.45, mono_in=False)
    return lp(hp(out, 90, 2), 8500, 2)


def contour_ooh(u, r):
    r1, r2 = r.uniform(1.0, 3.5), r.uniform(3.0, 7.0)
    return r1 * smoothstep(u / 0.25) - r2 * smoothstep((u - 0.3) / 0.7)


def contour_ohh(u, r):
    r1, r2 = r.uniform(2.0, 4.0), r.uniform(5.0, 9.0)
    return r1 - r2 * smoothstep(u / 0.8) ** 0.8


@sfx("crowd_ooh_a", "Foule synthetique 'ooooh' impressionnee (56 voix formantiques, montee puis descente, grande salle).",
     "Beau geste, tir spectaculaire, panier improbable. Rendu credible a distance, moins en solo.", -8, "start")
def _():
    return finish(crowd(301, 56, 2.4, contour_ooh), dur=2.4, tail=0.5)


@sfx("crowd_ooh_b", "Foule 'ohhh...' decue (part haut et retombe), 1,8 s.",
     "Tir rate de peu, mauvaise reponse, occasion manquee.", -8, "start")
def _():
    return finish(crowd(302, 60, 1.8, contour_ohh), dur=1.8, tail=0.45)


@sfx("crowd_swell", "Swell d'air (souffle rose filtre en 'o' qui gonfle et retombe, sans voix) : alternative neutre a la foule.",
     "Si crowd_ooh sonne trop synthetique : meme usage, plus discret.", -10, "peak")
def _():
    n = ns(2.0)
    nz = np.stack([formant_filter(colored(n, 311 + c, -3), "o", 1.0) + 0.5 * bp(colored(n, 313 + c, -3), 300, 5000, 2)
                   for c in range(2)], 1)
    x = nrm(nz) * env_beta(n, 0.45, 2.0)[:, None]
    x = reverb(x, IR("hall"), wet=0.3, mono_in=False)
    return finish(x, dur=2.0, tail=0.3)


# =========================================================================== suspense / cartes
def thump(n, f_start, f_end, tau_f, tau_a, amp, seed):
    t = tt(n)
    f = f_end + (f_start - f_end) * np.exp(-t / tau_f)
    y = np.sin(2 * np.pi * phase_acc(f)) * (1 - np.exp(-t / 0.004)) * np.exp(-t / tau_a)
    y = y + 0.25 * pk(lp(white(n, seed), 160, 2) * np.exp(-t / 0.02))
    # 'toc' 150-300 Hz : rend le battement audible sur un haut-parleur de telephone
    knock = damped(155, 0.03, n, 1.0, fdrop=0.15) + damped(270, 0.018, n, 0.5)
    y = y + 0.35 * pk(knock) * (1 - np.exp(-t / 0.003))
    return amp * y


def heart(beats, dur, seed):
    n = ns(dur)
    x = np.zeros(n)
    for i, tb in enumerate(beats):
        L = ns(0.35)
        add_at(x, ns(tb), thump(L, 85, 48, 0.03, 0.075, 1.0, seed + i))
        add_at(x, ns(tb + 0.24), thump(L, 95, 55, 0.025, 0.055, 0.7, seed + 50 + i))
    x = 0.65 * x + 0.5 * sat(x * 2.5, 2.5, asym=0.1)
    x = reverb(lp(x, 600, 2), IR("room"), wet=0.08)
    return finish(x, dur=dur, tail=0.15, hp_hz=20)


@sfx("heartbeat_a", "Battement de coeur 'boum-boum' x2, lent (~70 bpm), grave mais audible sur telephone.",
     "Suspense avant une reponse / un tir decisif ; boucler en le repetant toutes les 0,85 s.", -6, "start")
def _():
    return heart((0.0, 0.85), 1.55, 401)


@sfx("heartbeat_b", "Battement de coeur x2 rapide (~115 bpm), tension.",
     "Dernier point, chrono qui presse.", -6, "start")
def _():
    return heart((0.0, 0.52), 1.05, 411)


def card_slam_core(seed, t_hit=0.28, dur=1.1, deep=False):
    n = ns(dur)
    x = np.zeros((n, 2))
    w = whoosh_core(t_hit + 0.02, 0.93, 450, 4200, 3000, q=1.3, body=0.35, air=0.45, seed=seed,
                    pan0=-0.5, pan1=0.0, a=1.8)
    add_at(x, 0, 0.6 * pk(w))
    L = ns(dur - t_hit)
    t = tt(L)
    slap = pk(bp(white(L, seed + 1), 1200, 7000, 2) * np.exp(-t / 0.006))
    s2 = ns(0.007)
    slap2 = np.zeros(L)
    slap2[s2:] = slap[: L - s2] * 0.5
    f = (45 if deep else 55) + 95 * np.exp(-t / 0.02)
    punch = np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / (0.22 if deep else 0.12))
    shing = metal_shing(L, seed + 2)
    hit = sat(0.8 * slap + 0.4 * slap2 + punch + 0.18 * pk(shing), 1.4)
    add_at(x, ns(t_hit), st(hit))
    x = reverb(x, IR("room"), wet=0.12)
    return finish(x, dur=dur, tail=0.3)


@sfx("card_slam_a", "Apparition de carte joueur : whoosh montant puis claque + punch + petit 'shing' metallique.",
     "Entree d'une carte/photo de joueur : caler le REPERE D'IMPACT sur l'image ou la carte se pose.", -6, "hit")
def _():
    return card_slam_core(501)


@sfx("card_slam_b", "Variante plus lourde (whoosh plus long, punch plus grave).",
     "Dernier joueur presente, carte 'MVP', revelation du gagnant.", -6, "hit")
def _():
    return card_slam_core(502, t_hit=0.38, dur=1.3, deep=True)


# =========================================================================== main
def main(names):
    os.makedirs(OUT, exist_ok=True)
    todo = names or list(REG)
    for name in todo:
        if name not in REG:
            print("inconnu :", name)
            continue
        t0 = time.time()
        x = REG[name]["fn"]()
        write_wav(os.path.join(OUT, name + ".wav"), x)
        print(f"{name:18s} {x.shape[0] / SR:6.3f} s  ({time.time() - t0:4.1f} s de calcul)", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
