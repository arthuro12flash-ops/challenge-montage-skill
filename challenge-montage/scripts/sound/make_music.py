# -*- coding: utf-8 -*-
"""
make_music.py - musique originale trap/phonk 100 % synthese pour challenge-montage.

144 BPM (sensation half-time : clap sur le temps 3), la mineur, 48 kHz stereo 24 bits.
1 temps = 20 000 echantillons, 1 mesure = 80 000 echantillons = 1,6667 s = 50 images a 30 fps.

Sorties (assets/music/) :
  <section>.wav                      mix de la section (bouclable sauf buildup/outro)
  stems/<section>_drums|bass|music.wav   stems (leur somme = le mix, au bit pres hors arrondi)
  demo_full.wav                      enchainement de toutes les sections (queues naturelles)
  music.json                         BPM, durees, temps forts, loudness...

Usage : uv run --no-project --python 3.12 --with numpy --with scipy python make_music.py
"""
import json
import os
import time
import zlib
from functools import lru_cache

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

from dsp import (SR, add_at, bp, damped, eq, fade_io, hp, loudness, lp, make_ir, mtof, nrm, ns, pan,
                 phase_acc, pingpong, pk, pulse_f, reverb, rng, sat, saw_f, smoothstep, st, true_peak_db, tt,
                 undb, white, write_wav)
from make_sfx import cymbal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "assets", "music"))

BPM = 144.0
SPB = 20000            # echantillons par temps (60 / 144 * 48000)
BAR = 4 * SPB          # 80 000
STEP = SPB // 4        # double-croche = 5 000
TAIL = ns(2.5)
TARGET_LUFS = -16.0
TP_MAX = -1.0

CHORDS = {
    "Am": dict(root=33, pad=[57, 60, 64]),   # La1 = 55 Hz
    "F": dict(root=29, pad=[57, 60, 65]),    # Fa1 = 43,7 Hz
    "Dm": dict(root=38, pad=[57, 62, 65]),   # Re2 = 73,4 Hz
    "E": dict(root=40, pad=[56, 59, 64]),    # Mi2 = 82,4 Hz
    "Bb": dict(root=34, pad=[58, 62, 65]),   # Sib1 = 58,3 Hz
}
# motif de cloche : (pas de double-croche, note MIDI, duree en pas)
MOTIF = {
    "Am": [(0, 76, 3), (3, 72, 3), (6, 69, 2), (10, 71, 2), (12, 72, 4)],
    "F": [(0, 72, 3), (3, 69, 3), (6, 65, 2), (10, 67, 2), (12, 69, 4)],
    "Dm": [(0, 74, 3), (3, 69, 3), (6, 65, 2), (10, 64, 2), (12, 65, 4)],
    "E": [(0, 68, 3), (3, 71, 3), (6, 76, 2), (10, 74, 2), (12, 71, 4)],
}
ARP = {"Am": [57, 60, 64, 69], "F": [53, 57, 60, 65], "Dm": [50, 57, 62, 65], "E": [52, 56, 59, 64]}
ARP_ORDER = [0, 1, 2, 3, 2, 1, 2, 3]

K1 = [0, 10]
K2 = [0, 7, 10]
K3 = [0, 3, 10, 14]
K4 = [0, 6, 9, 10, 13]
H8 = list(range(0, 16, 2))
H16 = list(range(16))
# 808 : (pas, duree en pas, transposition, glisse)
B1 = [(0, 10, 0, False), (10, 6, 0, False)]
B2 = [(0, 7, 0, False), (7, 3, 0, False), (10, 4, 0, False), (14, 2, 12, True)]
B3 = [(0, 6, 0, False), (6, 4, 0, False), (10, 3, 0, False), (13, 3, 7, True)]
ROLLS = {"r32": (4, 2.0), "r64": (8, 2.0), "trip": (6, 4.0), "trip8": (6, 8.0)}
BUSES = ("kick", "snare", "hats", "cym", "fx_drum", "b808", "sub", "pad", "bell", "pluck", "fx_music")


def at(bar, step=0.0):
    return int(round(bar * BAR + step * STEP))


# =========================================================================== instruments (rendus mis en cache)
@lru_cache(None)
def KICK():
    L = ns(0.5)
    t = tt(L)
    f = 58 + (230 - 58) * np.exp(-t / 0.026)
    body = sat(np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / 0.14) * 1.4, 1.6)
    click = pk(hp(white(L, 9001), 1800, 2) * np.exp(-t / 0.0018)) * 0.22
    return pk(fade_io(body + click, 0.0005, 0.01))


@lru_cache(None)
def CLAP(var=0):
    L = ns(0.45)
    t = tt(L)
    nz = white(L, 9101 + var)
    b = bp(nz, 950, 2300, 2) + 0.35 * bp(nz, 5000, 9500, 2)
    env = np.zeros(L)
    for d, a in ((0.0, 0.75), (0.008, 0.65), (0.017, 0.6)):
        m = t >= d
        env[m] += a * np.exp(-(t[m] - d) / 0.0035)
    m = t >= 0.025
    env[m] += np.exp(-(t[m] - 0.025) / 0.07)
    tone = damped(190, 0.045, L, 0.9) + damped(330, 0.03, L, 0.4)
    noise = hp(white(L, 9111 + var), 1500, 2) * np.exp(-t / 0.09) * (1 - np.exp(-t / 0.001))
    return pk(fade_io(0.9 * pk(b * env) + 0.45 * pk(tone) + 0.35 * pk(noise), 0.0005, 0.02))


@lru_cache(None)
def SNR(tune):
    L = ns(0.25)
    t = tt(L)
    tone = damped(200 * tune, 0.035, L, 1.0) + damped(340 * tune, 0.02, L, 0.4)
    noise = bp(white(L, 9201 + int(tune * 100)), 1200, 7000, 2) * np.exp(-t / 0.06)
    return pk(fade_io(0.5 * pk(tone) + 0.7 * pk(noise), 0.0005, 0.02))


@lru_cache(None)
def HAT(decay, tone, seed):
    L = ns(min(decay * 7 + 0.01, 0.6))
    t = tt(L)
    r = rng(9300 + seed)
    metal = sum(pulse_f(f * tone, 0.5, L, r.random()) for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0))
    metal = bp(metal, 7000, 14000, 2)
    nz = hp(white(L, 9350 + seed), 8000, 2)
    env = (1 - np.exp(-t / 0.0003)) * np.exp(-t / decay)
    return pk(fade_io((0.6 * nrm(metal) + 0.4 * nrm(nz)) * env, 0.0003, 0.003))


@lru_cache(None)
def CRASH():
    c = cymbal(2.2, seed=9401, tau=0.7)
    return fade_io(hp(c, 3000, 2), 0.0005, 0.05)


@lru_cache(None)
def REVCYM(L):
    c = cymbal(L / SR + 0.6, seed=9402, tau=0.6)[:L][::-1]
    return fade_io(hp(c, 2500, 2), 0.005, 0.003)


@lru_cache(None)
def IMPACT():
    L = ns(1.5)
    t = tt(L)
    f = 38 + 37 * np.exp(-t / 0.08)
    body = np.sin(2 * np.pi * phase_acc(f)) * np.exp(-t / 0.5)
    thump = pk(lp(white(L, 9501), 300, 2) * np.exp(-t / 0.05))
    x = body + 0.6 * thump
    x = 0.5 * x + 0.5 * lp(sat(x * 2.5, 2.5, asym=0.1), 1200, 2)
    return pk(fade_io(x, 0.001, 0.3))


def b808_note(f, L, f_from=None, glide=0.07, decay=0.9):
    t = tt(L)
    if f_from is not None:
        fr = f + (f_from - f) * np.exp(-t / (glide / 3.0))
    else:
        fr = f * (1 + 0.05 * np.exp(-t / 0.015))
    y = np.sin(2 * np.pi * phase_acc(fr))
    env = (1 - np.exp(-t / 0.0015)) * (0.45 + 0.55 * np.exp(-t / decay))
    return fade_io(y * env, 0.0, 0.03)


def pad_chord(midis, L, seed, voices=3, det=9.0, attack=0.3, release=0.35):
    total = L + ns(release)
    out = np.zeros((total, 2))
    r = rng(seed)
    for m in midis:
        f = float(mtof(m))
        for v in range(voices):
            c = det * (v - (voices - 1) / 2) / max((voices - 1) / 2, 1) + r.uniform(-1.5, 1.5)
            s = saw_f(f * 2 ** (c / 1200), total, r.random())
            out += pan(s, (-0.75 + 1.5 * v / max(voices - 1, 1)))
    t = tt(total)
    env = smoothstep(t / attack) * np.clip(1 - (t - L / SR) / release, 0, 1)
    return out * env[:, None] / (len(midis) * voices)


def bell_note(f, L, decay=0.45):
    t = tt(L)
    idx = 1.6 * np.exp(-t / 0.05) + 0.25
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 2.0 * f * t))
    y = y + 0.12 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t / 0.04)
    return fade_io(y * (1 - np.exp(-t / 0.001)) * np.exp(-t / decay), 0.0, 0.02)


def pluck_note(f, L, decay=0.35):
    t = tt(L)
    y = np.zeros(L)
    for k in range(1, 7):
        if k * f > 6000:
            break
        y += (1.0 / k) * np.sin(2 * np.pi * k * f * t) * np.exp(-t / (decay / k ** 0.8))
    return fade_io(y * (1 - np.exp(-t / 0.0015)), 0.0, 0.02)


def tv_filter(x, fcs, kind="lp", q=0.8, block=256):
    """Filtre a frequence variable (biquad RBJ par blocs de 256 ech., etat conserve)."""
    x = st(x)
    n = x.shape[0]
    out = np.zeros_like(x, dtype=np.float64)
    for ch in range(2):
        zi = np.zeros((1, 2))
        for s in range(0, n, block):
            e = min(n, s + block)
            fc = float(min(fcs[(s + e) // 2], 0.45 * SR))
            w0 = 2 * np.pi * fc / SR
            cw, al = np.cos(w0), np.sin(w0) / (2 * q)
            if kind == "lp":
                b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
            else:  # bandpass crete 0 dB
                b = [al, 0.0, -al]
            a = [1 + al, -2 * cw, 1 - al]
            sos = np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1.0, a[1] / a[0], a[2] / a[0]]])
            out[s:e, ch], zi = signal.sosfilt(sos, x[s:e, ch], zi=zi)
    return out


def duck(n, hits, depth_db, release=0.12, attack=0.002):
    """Courbe de side-chain : creux de depth_db a chaque kick, remontee exponentielle."""
    g = np.ones(n)
    d = 1 - undb(-depth_db)
    shape = np.concatenate([np.linspace(0, 1, ns(attack)), np.exp(-tt(ns(release * 5)) / release)])
    seg = 1 - d * shape
    for h in hits:
        e = min(n, h + seg.shape[0])
        if e > h:
            g[h:e] = np.minimum(g[h:e], seg[: e - h])
    return g


IR_ROOM = make_ir(rt60=0.9, predelay=0.008, seed=9601, lf=1.0, hf=0.5)
IR_HALL = make_ir(rt60=1.8, predelay=0.02, seed=9602, lf=1.1, hf=0.45)


# =========================================================================== section
class Sec:
    def __init__(self, name, bars, chords, loop=True, energy=3, desc=""):
        self.name, self.bars, self.chords, self.loop, self.energy, self.desc = name, bars, chords, loop, energy, desc
        self.N = bars * BAR
        self.n = self.N + TAIL
        self.buf = {k: np.zeros((self.n, 2), dtype=np.float32) for k in BUSES}
        self.kick_pos, self.snare_pos, self.accents = [], [], []
        self.pad_filter = ("static", 1400.0)
        self.last808 = None
        self.end_fade = 0.0
        self.r = rng(zlib.crc32(name.encode()))

    # ---- batterie
    def kick(self, bar, step, vel=1.0):
        p = at(bar, step)
        add_at(self.buf["kick"], p, st(KICK() * (0.9 * vel)))
        self.kick_pos.append(p)

    def clap(self, bar, step, vel=1.0, var=0):
        p = at(bar, step)
        add_at(self.buf["snare"], p, st(CLAP(var) * (0.6 * vel)))
        if vel >= 0.6:
            self.snare_pos.append(p)

    def snr(self, bar, step, vel=0.5, tune=1.0):
        add_at(self.buf["snare"], at(bar, step), pan(SNR(round(tune, 2)) * (0.45 * vel), 0.05))

    def hat(self, bar, step, vel=0.5, tone=1.0, decay=0.035, p=0.15):
        h = HAT(round(decay, 3), round(tone, 2), int(round(step * 7)) % 3)
        v = vel * (1 + 0.08 * (self.r.random() - 0.5))
        add_at(self.buf["hats"], at(bar, step), pan(h * (0.22 * v), p))

    def ohat(self, bar, step, vel=0.4):
        add_at(self.buf["hats"], at(bar, step), pan(HAT(0.16, 1.0, 1) * (0.18 * vel), -0.2))

    def crash(self, bar, step=0, vel=0.8):
        add_at(self.buf["cym"], at(bar, step), CRASH() * (0.22 * vel))
        self.accents.append((at(bar, step), "crash"))

    def rev_cym(self, end, beats=2, vel=0.6):
        L = beats * SPB
        add_at(self.buf["cym"], end - L, REVCYM(L) * (0.25 * vel))

    def impact(self, bar, step=0, vel=1.0):
        add_at(self.buf["fx_drum"], at(bar, step), st(IMPACT() * (0.7 * vel)))
        self.accents.append((at(bar, step), "impact"))

    # ---- basse
    def b808(self, bar, step, midi, steps, vel=1.0, glide=False, decay=0.9):
        f_from = float(mtof(self.last808)) if (glide and self.last808 is not None) else None
        y = b808_note(float(mtof(midi)), int(steps * STEP), f_from, decay=decay)
        add_at(self.buf["b808"], at(bar, step), st(y * (0.55 * vel)))
        self.last808 = midi

    def bassline(self, bar, chord, pattern, glide_first=False, vel=1.0):
        root = CHORDS[chord]["root"]
        for i, (s, l, o, gl) in enumerate(pattern):
            self.b808(bar, s, root + o, l, vel=vel, glide=gl or (i == 0 and glide_first))

    def sub(self, bar, midi, bars=1, vel=1.0):
        L = int(bars * BAR)
        t = tt(L + ns(0.3))
        ph = 2 * np.pi * float(mtof(midi)) * t
        y = (np.sin(ph) + 0.15 * np.sin(2 * ph)) * smoothstep(t / 0.25) * np.clip((L / SR + 0.3 - t) / 0.3, 0, 1)
        add_at(self.buf["sub"], at(bar), st(y * (0.35 * vel)))

    def pulse(self, bar, step, midi, vel=1.0):
        L = ns(0.45)
        t = tt(L)
        f = float(mtof(midi))
        y = np.sin(2 * np.pi * phase_acc(f * (1 + 0.5 * np.exp(-t / 0.02)))) * np.exp(-t / 0.12)
        y = 0.7 * y + 0.3 * sat(y, 3.0)
        add_at(self.buf["sub"], at(bar, step), st(fade_io(y, 0.001, 0.02) * (0.5 * vel)))

    # ---- harmonie / melodie
    def pad(self, bar, chord, bars=1.0, vel=1.0, seed=0):
        y = pad_chord(CHORDS[chord]["pad"], int(bars * BAR), seed=7000 + seed)
        add_at(self.buf["pad"], at(bar), y * (0.7 * vel))

    def bell(self, bar, step, midi, vel=1.0, decay=0.45, length=1.4, p=0.1):
        y = bell_note(float(mtof(midi)), ns(length), decay=decay)
        add_at(self.buf["bell"], at(bar, step), pan(y * (0.3 * vel), p))

    def pluck(self, bar, step, midi, vel=1.0, p=-0.25):
        y = pluck_note(float(mtof(midi)), ns(0.9))
        add_at(self.buf["pluck"], at(bar, step), pan(y * (0.18 * vel), p))

    def arp(self, bar, chord, vel=0.4):
        notes = ARP[chord]
        for i, s in enumerate(range(0, 16, 2)):
            self.pluck(bar, s, notes[ARP_ORDER[i]], vel)

    def motif(self, bar, chord, vel=1.0, upto=5, octave=False, decay=0.45):
        for (s, m, l) in MOTIF[chord][:upto]:
            self.bell(bar, s, m, vel, decay=decay)
            if octave:
                self.bell(bar, s, m + 12, vel * 0.32, decay=0.3, p=-0.15)

    def riser(self, bar, bars, vel=1.0):
        L = int(bars * BAR)
        u = (np.arange(L) + 0.5) / L
        fc = 300 * (9000 / 300) ** (u ** 1.4)
        noise = np.stack([white(L, 9701), white(L, 9702)], axis=1)
        x = tv_filter(noise, fc, "bp", q=1.2)
        x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * undb(-30 * (1 - u) ** 1.3)[:, None]
        add_at(self.buf["fx_music"], at(bar), fade_io(x, 0.01, 0.003) * (0.12 * vel))


def hats_bar(S, bar, base, rolls=(), vel=0.5, tone_ramp=0.12):
    covered = []
    for s0, kind in rolls:
        k, span = ROLLS[kind]
        covered.append((s0, s0 + span))
        for i in range(k):
            fr = i / max(k - 1, 1)
            S.hat(bar, s0 + i * span / k, vel * (0.5 + 0.5 * fr), tone=1.0 + tone_ramp * fr, decay=0.025)
    for s in base:
        if any(a <= s < b for a, b in covered):
            continue
        S.hat(bar, s, vel * (1.0 if s % 4 == 0 else (0.8 if s % 2 == 0 else 0.6)))


# =========================================================================== arrangement
def sec_intro_calm():
    ch = ["Am", "Am", "F", "F", "Dm", "Dm", "E", "E"]
    S = Sec("intro_calm", 8, ch, energy=1,
            desc="Nappe filtree qui s'ouvre, cloche clairsemee, sous-basse douce ; charleys legers puis kick/clap discrets "
                 "a partir de la mesure 5. Tension legere pour l'explication des regles.")
    for b in range(0, 8, 2):
        S.pad(b, ch[b], 2, vel=1.15, seed=b)
        S.sub(b, CHORDS[ch[b]]["root"], 2, vel=1.0)
        S.motif(b, ch[b], vel=0.7, upto=3, decay=0.7)
    for b in range(8):
        rolls = {3: [(14, "r32")], 7: [(12, "trip")]}.get(b, [])
        hats_bar(S, b, H8 if b < 4 else H16, rolls, vel=0.36 if b < 4 else 0.4)
        if b >= 4:
            S.kick(b, 0, vel=0.55)
            S.clap(b, 8, vel=0.4)
            S.arp(b, ch[b], vel=0.35)
    S.pad_filter = ("sweep", 450.0, 1600.0)
    return S


def sec_players_hype():
    ch = ["Am", "F", "Dm", "E"] * 2
    S = Sec("players_hype", 8, ch, energy=4,
            desc="Beat complet et punchy : kick + 808 avec glissandos, clap sur le temps 3, charleys avec roulements, "
                 "motif de cloche complet. Pour la presentation des joueurs.")
    S.last808 = CHORDS["E"]["root"]
    for b, c in enumerate(ch):
        S.pad(b, c, 1, vel=0.85, seed=10 + b)
        S.motif(b, c, vel=0.9)
        for s in (K2 if b % 2 == 0 else K3):
            S.kick(b, s)
        S.clap(b, 8)
        if b in (3, 7):
            S.clap(b, 15, vel=0.3, var=1)
        rolls = {1: [(14, "r32")], 3: [(12, "trip")], 5: [(6, "r32")], 7: [(14, "r64")]}.get(b, [])
        hats_bar(S, b, H8, rolls, vel=0.55)
        if b % 4 == 0:
            S.ohat(b, 6, 0.4)
        S.bassline(b, c, B2 if b % 2 == 0 else B1, glide_first=(b % 2 == 0))
    S.crash(0, 0, 0.8)
    S.crash(4, 0, 0.6)
    S.pad_filter = ("static", 1400.0)
    return S


def sec_game_groove_a():
    ch = ["Am", "Am", "F", "F", "Dm", "Dm", "E", "E"]
    S = Sec("game_groove_a", 8, ch, energy=3,
            desc="Groove de match aere (harmonie lente, cloche reduite a 2 notes toutes les 2 mesures) : laisse "
                 "beaucoup de place aux dialogues.")
    S.last808 = CHORDS["E"]["root"]
    for b, c in enumerate(ch):
        if b % 2 == 0:
            S.pad(b, c, 2, vel=0.95, seed=20 + b)
            S.motif(b, c, vel=0.6, upto=2, decay=0.5)
        for s in (K2 if b in (3, 7) else K1):
            S.kick(b, s, 0.95)
        S.clap(b, 8, 0.9)
        rolls = {3: [(12, "trip")], 7: [(14, "r32")]}.get(b, [])
        hats_bar(S, b, H8, rolls, vel=0.45)
        S.bassline(b, c, B1, glide_first=(b == 0))
    S.pad_filter = ("static", 1100.0)
    return S


def sec_game_groove_b():
    ch = ["Am", "F", "Dm", "E"] * 2
    S = Sec("game_groove_b", 8, ch, energy=3,
            desc="Variation du groove de match : charleys en doubles-croches avec roulements, arpege pluck, 808 plus "
                 "syncopee, cloche en question-reponse une mesure sur deux.")
    S.last808 = CHORDS["E"]["root"]
    for b, c in enumerate(ch):
        S.pad(b, c, 1, vel=0.9, seed=30 + b)
        S.arp(b, c, vel=0.42)
        if b % 2 == 1:
            S.motif(b, c, vel=0.6, upto=2)
        for s in (K3 if b % 2 == 0 else K2):
            S.kick(b, s, 0.95)
        S.clap(b, 8, 0.95)
        if b in (1, 5):
            S.clap(b, 14, 0.3, var=1)
        rolls = {1: [(6, "r64")], 3: [(12, "trip")], 5: [(14, "r32")], 7: [(8, "trip8")]}.get(b, [])
        hats_bar(S, b, H16, rolls, vel=0.36)
        if b % 2 == 0:
            S.ohat(b, 14, 0.35)
        S.bassline(b, c, B3, glide_first=(b % 4 == 0))
    S.pad_filter = ("static", 1200.0)
    return S


def sec_suspense():
    ch = ["Am", "Am", "Bb", "E"]
    S = Sec("suspense", 4, ch, energy=1,
            desc="Quasi sans batterie : nappe sombre (la mineur -> sib -> mi), tic-tac discret, pulsation grave type "
                 "battement de coeur, notes de cloche isolees. Pour les moments de reponse.")
    for b, c in enumerate(ch):
        S.pad(b, c, 1, vel=1.3, seed=40 + b)
        for q in range(4):
            S.hat(b, q * 4, vel=0.42 if q % 2 == 0 else 0.3, tone=0.9 if q % 2 == 0 else 0.78, decay=0.018,
                  p=0.3 if q % 2 == 0 else -0.3)
        S.pulse(b, 0, CHORDS[c]["root"], 1.1)
        S.pulse(b, 3, CHORDS[c]["root"], 0.75)
    S.bell(0, 0, 76, 0.75, decay=1.0, length=2.5)
    S.bell(2, 0, 77, 0.75, decay=1.0, length=2.5)
    S.bell(3, 0, 68, 0.7, decay=1.0, length=2.5)
    S.rev_cym(S.N, beats=2, vel=0.35)
    S.pad_filter = ("static", 800.0)
    return S


def sec_buildup():
    ch = ["F", "F", "E", "E"]
    S = Sec("buildup", 4, ch, loop=False, energy=4,
            desc="Montee de 4 mesures : kick en noires, roulement de caisse claire qui accelere (croches -> 64es), "
                 "filtre qui s'ouvre, bruit montant, cymbale inversee ; s'arrete net sur la fin (le drop suit).")
    for b in range(3):
        for s in (0, 4, 8, 12):
            S.kick(b, s, 0.85)
    sched = [(0, [8]), (1, list(range(0, 16, 2))), (2, list(range(16))),
             (3, [i * 0.5 for i in range(24)] + [12 + i * 0.25 for i in range(16)])]
    for b, steps in sched:
        for s in steps:
            pos = (b * 16 + s) / 64.0
            S.snr(b, s, vel=0.3 + 0.7 * pos ** 1.5, tune=1.0 + round(0.5 * pos * 10) / 10)
    for b in range(3):
        hats_bar(S, b, H8 if b < 2 else H16, [], vel=0.4)
    S.b808(0, 0, CHORDS["F"]["root"], 16, decay=1.5)
    S.b808(1, 0, CHORDS["F"]["root"], 16, decay=1.5)
    S.b808(2, 0, CHORDS["E"]["root"], 16, decay=1.5, glide=True)
    S.pad(0, "F", 2, vel=0.8, seed=45)
    S.pad(2, "E", 2, vel=0.85, seed=46)
    S.motif(0, "F", vel=0.6, upto=3)
    S.motif(1, "F", vel=0.65, upto=3)
    S.motif(2, "E", vel=0.7, upto=5)
    for i, s in enumerate(range(0, 16, 2)):
        S.bell(3, s, 76, 0.35 + 0.07 * i, decay=0.25)
    S.riser(0, 4, 1.0)
    S.rev_cym(S.N, beats=2, vel=0.7)
    S.accents.append((S.N, "drop (fin de la section)"))
    S.pad_filter = ("sweep", 600.0, 4500.0)
    return S


def sec_drop_winner():
    ch = ["Am", "F", "Dm", "E"] * 2
    S = Sec("drop_winner", 8, ch, energy=5,
            desc="Section la plus energique : impact grave + crash d'entree, kick et 808 charges, charleys en "
                 "doubles-croches avec roulements, cloche doublee a l'octave, arpege. Pour la victoire.")
    S.last808 = CHORDS["E"]["root"]
    S.impact(0, 0)
    S.crash(0, 0, 0.9)
    S.crash(4, 0, 0.75)
    for b, c in enumerate(ch):
        S.pad(b, c, 1, vel=0.9, seed=50 + b)
        S.motif(b, c, vel=1.0, octave=True)
        S.arp(b, c, vel=0.35)
        for s in (K4 if b % 2 == 0 else K2):
            S.kick(b, s)
        S.clap(b, 8, 1.0)
        if b % 2 == 1:
            S.clap(b, 6, 0.28, var=1)
            S.clap(b, 15, 0.32, var=1)
        rolls = {0: [(14, "r32")], 1: [(12, "trip")], 2: [(6, "r64")], 3: [(8, "trip8")],
                 4: [(14, "r32")], 5: [(12, "trip")], 6: [(2, "r32")], 7: [(12, "r64")]}[b]
        hats_bar(S, b, H16, rolls, vel=0.45)
        S.ohat(b, 14 if b % 2 == 0 else 6, 0.35)
        S.bassline(b, c, B2, glide_first=True)
    S.pad_filter = ("static", 1800.0)
    return S


def sec_outro():
    ch = ["Am", "F", "E", "Am"]
    S = Sec("outro", 4, ch, loop=False, energy=3,
            desc="Fin : deux mesures de groove, une mesure qui s'allege avec un petit roulement, puis coup final "
                 "(kick + 808 + crash + accord) au debut de la mesure 4 et queue qui s'eteint : fin nette.")
    S.last808 = CHORDS["E"]["root"]
    for b in range(3):
        c = ch[b]
        S.pad(b, c, 1, vel=0.8, seed=60 + b)
        if b < 2:
            for s in K1:
                S.kick(b, s)
            S.motif(b, c, vel=0.8)
        else:
            S.kick(b, 0)
            S.motif(b, c, vel=0.7, upto=3)
            for s in (12, 13, 14, 15):
                S.snr(b, s, vel=0.35 + 0.12 * (s - 12), tune=1.1)
        S.clap(b, 8)
        hats_bar(S, b, H8, [(14, "r32")] if b == 1 else [], vel=0.45)
        S.bassline(b, c, B1, glide_first=(b == 0))
    S.kick(3, 0, 1.0)
    S.crash(3, 0, 0.8)
    S.b808(3, 0, CHORDS["Am"]["root"], 14, vel=1.0, glide=True, decay=0.45)
    S.pad(3, "Am", 0.5, vel=0.8, seed=63)
    S.bell(3, 0, 69, 0.9, decay=0.6)
    S.bell(3, 0, 81, 0.4, decay=0.5, p=-0.15)
    S.accents.append((at(3, 0), "coup final"))
    S.end_fade = 0.3
    return S


SECTIONS = [sec_intro_calm, sec_players_hype, sec_game_groove_a, sec_game_groove_b, sec_suspense, sec_buildup,
            sec_drop_winner, sec_outro]


# =========================================================================== mixage
def mixdown(S):
    n = S.n
    kicks = list(S.kick_pos)
    if S.loop:  # la queue repliee doit etre 'side-chainee' par les kicks du debut
        kicks += [k + S.N for k in S.kick_pos if k < TAIL]
    g808 = duck(n, kicks, 9.0, 0.11)
    gpad = duck(n, kicks, 4.0, 0.16)
    B = S.buf
    sn = B["snare"].astype(np.float64)
    drums = (B["kick"].astype(np.float64) + sn + reverb(sn, IR_ROOM, wet=0.18, dry=0.0, keep_len=True)
             + B["hats"] + B["cym"] + B["fx_drum"])
    drums = hp(eq(drums, "peak", 2600, 0.9, -3.0), 30, 2)
    bb = B["b808"].astype(np.float64)
    bb = 0.84 * (0.55 * bb + 0.5 * sat(bb, 2.8, asym=0.12))
    bb = lp(hp(bb, 28, 2), 1100, 2) * g808[:, None]
    bass = hp(bb + B["sub"], 30, 4)
    bass = eq(bass, "lowshelf", 55, 0.7, -3.0)        # sous-basse < 60 Hz maitrisee
    pad = B["pad"].astype(np.float64)
    if S.pad_filter[0] == "static":
        pad = lp(pad, S.pad_filter[1], 2)
    else:
        u = np.arange(n) / S.N
        pad = tv_filter(pad, S.pad_filter[1] * (S.pad_filter[2] / S.pad_filter[1]) ** np.clip(u, 0, 1), "lp", q=0.9)
    pad = pad * gpad[:, None]
    bell = pingpong(B["bell"], 3 * STEP / SR, fb=0.35, n_rep=5, lp_hz=3500, wet=0.2, keep_len=True)
    pluck = pingpong(B["pluck"], 3 * STEP / SR, fb=0.3, n_rep=4, lp_hz=3000, wet=0.15, keep_len=True)
    verb = reverb(0.6 * bell + 0.3 * pad + 0.4 * pluck, IR_HALL, wet=1.0, dry=0.0, keep_len=True)
    music = pad + bell + pluck + B["fx_music"] + 0.25 * verb
    music = hp(music, 140, 2)
    music = eq(music, "peak", 2500, 0.8, -6.0)       # creux pour l'intelligibilite de la voix
    music = eq(music, "highshelf", 8000, 0.7, -2.0)
    return {"drums": drums.astype(np.float32), "bass": bass.astype(np.float32), "music": music.astype(np.float32)}


def fold(x, S):
    """Version fichier : boucle sans couture (queue repliee sur le debut) ou fin coupee/fondue."""
    y = np.array(x[: S.N], dtype=np.float64)
    if S.loop:
        y[: x.shape[0] - S.N] += x[S.N:]
    else:
        if S.end_fade > 0:
            m = ns(S.end_fade)
            y[-m:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(1, m + 1) / m))[:, None]
        y = fade_io(y, 0.0, 0.003)
    return y


def limiter_gain(mix, ceiling_db, hold=0.012, smooth=0.006):
    """Gain de limitation (anticipation + maintien) calcule sur le mix, applique a l'identique aux stems."""
    a = np.max(np.abs(mix), axis=1)
    g = np.minimum(1.0, undb(ceiling_db) / np.maximum(a, 1e-9))
    if g.min() >= 1.0:
        return None
    g = minimum_filter1d(g, size=2 * ns(hold) + 1, mode="nearest")
    return uniform_filter1d(g, size=ns(smooth), mode="nearest")


def main():
    os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)
    t0 = time.time()
    secs, files, raws = [], {}, {}
    for fn in SECTIONS:
        S = fn()
        stems = mixdown(S)
        S.buf = None
        files[S.name] = {k: fold(v, S).astype(np.float32) for k, v in stems.items()}
        raws[S.name] = (stems["drums"] + stems["bass"] + stems["music"]).astype(np.float32)
        secs.append(S)
        print(f"{S.name:14s} rendu ({time.time() - t0:5.1f} s)", flush=True)

    # demo : sections bout a bout, queues naturelles (non repliees)
    total = sum(S.N for S in secs)
    demo = np.zeros((total + TAIL, 2), dtype=np.float32)
    starts, pos = {}, 0
    for S in secs:
        starts[S.name] = pos
        demo[pos: pos + raws[S.name].shape[0]] += raws[S.name]
        pos += S.N
    demo = demo[:total].astype(np.float64)
    if secs[-1].end_fade > 0:
        m = ns(secs[-1].end_fade)
        demo[-m:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(1, m + 1) / m))[:, None]
    L0 = loudness(demo)["I"]
    G = undb(TARGET_LUFS - L0)
    demo *= G
    lg = limiter_gain(demo, -1.6)
    if lg is not None:
        demo *= lg[:, None]
    demo = fade_io(demo, 0.0, 0.003)
    write_wav(os.path.join(OUT, "demo_full.wav"), demo)
    Ld = loudness(demo)
    info_demo = {"file": "demo_full.wav", "order": [S.name for S in secs],
                 "section_starts_s": {k: round(v / SR, 4) for k, v in starts.items()},
                 "duration_s": round(total / SR, 4), "bars": total // BAR,
                 "lufs_i": round(Ld["I"], 1), "true_peak_dbtp": round(true_peak_db(demo), 2),
                 "limiter_used": lg is not None}
    print(f"demo : I {Ld['I']:.1f} LUFS (gain maitre {20 * np.log10(G):+.1f} dB), TP {info_demo['true_peak_dbtp']} dBTP")
    del demo, raws

    sec_info = []
    for S in secs:
        st_ = {k: v.astype(np.float64) * G for k, v in files[S.name].items()}
        mix = st_["drums"] + st_["bass"] + st_["music"]
        lg = limiter_gain(mix, -1.6)
        if lg is not None:
            for k in st_:
                st_[k] *= lg[:, None]
            mix = st_["drums"] + st_["bass"] + st_["music"]
        write_wav(os.path.join(OUT, S.name + ".wav"), mix)
        stem_files = {}
        for k, v in st_.items():
            fn_ = f"stems/{S.name}_{k}.wav"
            write_wav(os.path.join(OUT, fn_), v)
            stem_files[k] = fn_
        Lm = loudness(mix)
        stem_lufs = {k: round(loudness(v)["I"], 1) for k, v in st_.items()}
        bar_s = BAR / SR

        def tl(lst):
            return [round(p / SR, 4) for p in sorted(set(lst)) if p < S.N]

        sec_info.append({
            "name": S.name, "file": S.name + ".wav", "stems": stem_files, "bars": S.bars,
            "duration_s": round(S.N / SR, 4), "samples": S.N, "frames_30fps": S.N // 1600,
            "loopable": S.loop, "energy_1_5": S.energy, "chords_per_bar": S.chords, "description": S.desc,
            "demo_start_s": round(starts[S.name] / SR, 4),
            "lufs_i": round(Lm["I"], 1), "lufs_s_max": round(Lm["S"], 1),
            "true_peak_dbtp": round(true_peak_db(mix), 2), "stems_lufs_i": stem_lufs,
            "limiter_used": lg is not None,
            "downbeats_s": [round(b * bar_s, 4) for b in range(S.bars)],
            "kicks_s": tl(S.kick_pos), "snares_s": tl(S.snare_pos),
            "accents": [{"t_s": round(p / SR, 4), "type": ty} for p, ty in sorted(S.accents)],
        })
        print(f"{S.name:14s} I {Lm['I']:6.1f}  TP {sec_info[-1]['true_peak_dbtp']:6.2f}  stems {stem_lufs}  "
              f"lim {lg is not None}", flush=True)

    info = {
        "title": "Musique originale challenge-montage (100 % synthese, libre de droits tiers)",
        "bpm": BPM, "time_signature": "4/4",
        "feel": "trap/phonk, sensation half-time (clap/caisse claire sur le temps 3 de chaque mesure = 72 BPM ressentis)",
        "key": "la mineur (progression principale Am - F - Dm - E)",
        "sample_rate": SR, "bit_depth": 24, "channels": 2,
        "beat_s": round(SPB / SR, 6), "bar_s": round(BAR / SR, 6), "beat_samples": SPB, "bar_samples": BAR,
        "frames_per_bar_30fps": 50, "frames_per_beat_30fps": 12.5,
        "grid_note": "Une mesure = 80 000 echantillons = 50 images exactes a 30 fps : toute coupe sur une barre de "
                     "mesure tombe sur une image entiere. Temps forts : debut de mesure (kick) et temps 3 (clap) = "
                     "debut + 0,8333 s.",
        "master_gain_db": round(20 * np.log10(G), 2), "loudness_target_lufs": TARGET_LUFS,
        "voice_space": "stem music : passe-haut 140 Hz, creux -6 dB centre sur 2,5 kHz (Q 0,8), etagere -2 dB > 8 kHz ; "
                       "stem drums : creux -3 dB a 2,6 kHz. Melodie sobre (cloche/pluck sous 1 kHz).",
        "mix_notes": "Kick (corps ~58 Hz, court) et 808 (41-82 Hz) separes par side-chain : 808 baissee de 9 dB a chaque "
                     "kick (remontee 110 ms), nappe -4 dB (160 ms). 808 saturee pour etre audible sur telephone.",
        "how_to_use": "Les sections 'loopable' bouclent sans couture (la queue de fin est repliee sur le debut). "
                      "Pour enchainer deux sections differentes : bout a bout, sur une barre de mesure ; ajouter un "
                      "fondu de 5-10 ms si un clic apparait, ou partir de demo_full. Couper la batterie ou la basse = "
                      "utiliser stems/<section>_music.wav (+ _bass) au lieu du mix ; la somme des 3 stems = le mix.",
        "sections": sec_info,
        "demo": info_demo,
    }
    with open(os.path.join(OUT, "music.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)
    print(f"termine en {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
