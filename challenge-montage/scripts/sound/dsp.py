# -*- coding: utf-8 -*-
"""
dsp.py - boite a outils DSP minimale (numpy + scipy) pour la banque de sons de challenge-montage.
Tout est synthetise : aucun echantillon externe, aucun telechargement.

Conventions : float64, mono = (n,), stereo = (n, 2), SR = 48 kHz.
"""
from __future__ import annotations

import struct

import numpy as np
from scipy import signal

SR = 48000


# --------------------------------------------------------------------------- bases
def ns(sec):
    return int(round(sec * SR))


def tt(n):
    return np.arange(n, dtype=np.float64) / SR


def undb(d):
    return 10.0 ** (np.asarray(d, dtype=np.float64) / 20.0)


def todb(x):
    return 20.0 * np.log10(np.maximum(np.abs(np.asarray(x, dtype=np.float64)), 1e-12))


def mtof(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=np.float64) - 69.0) / 12.0)


def rng(seed):
    return np.random.default_rng(seed)


def white(n, seed):
    return rng(seed).standard_normal(n)


def colored(n, seed, slope_db_oct):
    """Bruit colore : 0 = blanc, -3 = rose, -6 = brun."""
    w = white(n, seed)
    if slope_db_oct == 0 or n < 4:
        return w
    W = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1]
    W *= (f / 1000.0) ** (slope_db_oct / 6.0206)
    y = np.fft.irfft(W, n)
    return y / (np.std(y) + 1e-12)


def st(x):
    x = np.asarray(x, dtype=np.float64)
    return np.stack([x, x], axis=1) if x.ndim == 1 else x


def mono(x):
    x = np.asarray(x, dtype=np.float64)
    return x.mean(axis=1) if x.ndim == 2 else x


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-30))


def nrm(x):
    """Normalise a RMS = 1."""
    return x / (rms(x) + 1e-12)


def pk(x):
    """Normalise a crete = 1."""
    return x / (np.max(np.abs(x)) + 1e-12)


def pad_to(x, n):
    if x.shape[0] >= n:
        return x[:n]
    shape = (n - x.shape[0],) + x.shape[1:]
    return np.concatenate([x, np.zeros(shape)], axis=0)


def add_at(buf, start, sig):
    """Ajoute sig dans buf a partir de l'echantillon start (tronque aux bords)."""
    if buf.ndim == 2:
        sig = st(sig)
    start = int(start)
    if start >= buf.shape[0]:
        return
    s0 = max(start, 0)
    k0 = s0 - start
    e = min(buf.shape[0], start + sig.shape[0])
    if e <= s0:
        return
    buf[s0:e] += sig[k0:k0 + (e - s0)]


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


# --------------------------------------------------------------------------- filtres
def _bw(kind, fc, order):
    return signal.butter(order, fc, btype=kind, fs=SR, output="sos")


def sosf(x, sos):
    return signal.sosfilt(sos, x, axis=0)


def lp(x, fc, order=2):
    return sosf(x, _bw("lowpass", min(fc, 0.45 * SR), order))


def hp(x, fc, order=2):
    return sosf(x, _bw("highpass", fc, order))


def bp(x, lo, hi, order=2):
    return sosf(x, _bw("bandpass", [lo, min(hi, 0.45 * SR)], order))


def rbj(kind, fc, q=0.7071, gain_db=0.0):
    """Biquads RBJ (cookbook). kind : peak, lowshelf, highshelf, bpf (crete 0 dB), notch."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * fc / SR
    cw, sw = np.cos(w0), np.sin(w0)
    al = sw / (2.0 * q)
    if kind == "peak":
        b = [1 + al * A, -2 * cw, 1 - al * A]
        a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == "lowshelf":
        s = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * cw + s), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - s)]
        a = [(A + 1) + (A - 1) * cw + s, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - s]
    elif kind == "highshelf":
        s = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + s), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - s)]
        a = [(A + 1) - (A - 1) * cw + s, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - s]
    elif kind == "bpf":
        b = [al, 0.0, -al]
        a = [1 + al, -2 * cw, 1 - al]
    elif kind == "notch":
        b = [1.0, -2 * cw, 1.0]
        a = [1 + al, -2 * cw, 1 - al]
    else:
        raise ValueError(kind)
    b = np.asarray(b) / a[0]
    a = np.asarray(a) / a[0]
    return np.concatenate([b, a])[None, :]


def eq(x, kind, fc, q=0.7071, gain_db=0.0):
    return sosf(x, rbj(kind, fc, q, gain_db))


def svf(x, fc, q=0.7071, mode="lp"):
    """Filtre a variables d'etat TPT (Zavalishin), cutoff/Q variables echantillon par echantillon.
    mode : lp, bp (gain Q a la resonance), bpn (crete 1), hp."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        return np.stack([svf(x[:, c], fc, q, mode) for c in range(x.shape[1])], axis=1)
    n = x.shape[0]
    fcv = np.clip(np.broadcast_to(np.asarray(fc, dtype=np.float64), (n,)), 5.0, 0.45 * SR)
    qv = np.broadcast_to(np.asarray(q, dtype=np.float64), (n,))
    g = np.tan(np.pi * fcv / SR)
    k = 1.0 / qv
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    xs, A1, A2, A3 = x.tolist(), a1.tolist(), a2.tolist(), a3.tolist()
    out = [0.0] * n
    ic1 = 0.0
    ic2 = 0.0
    if mode == "lp":
        for i in range(n):
            v3 = xs[i] - ic2
            v1 = A1[i] * ic1 + A2[i] * v3
            v2 = ic2 + A2[i] * ic1 + A3[i] * v3
            ic1 = 2.0 * v1 - ic1
            ic2 = 2.0 * v2 - ic2
            out[i] = v2
        return np.asarray(out)
    if mode in ("bp", "bpn"):
        for i in range(n):
            v3 = xs[i] - ic2
            v1 = A1[i] * ic1 + A2[i] * v3
            v2 = ic2 + A2[i] * ic1 + A3[i] * v3
            ic1 = 2.0 * v1 - ic1
            ic2 = 2.0 * v2 - ic2
            out[i] = v1
        y = np.asarray(out)
        return y * k if mode == "bpn" else y
    if mode == "hp":
        K = k.tolist()
        for i in range(n):
            v3 = xs[i] - ic2
            v1 = A1[i] * ic1 + A2[i] * v3
            v2 = ic2 + A2[i] * ic1 + A3[i] * v3
            ic1 = 2.0 * v1 - ic1
            ic2 = 2.0 * v2 - ic2
            out[i] = xs[i] - K[i] * v1 - v2
        return np.asarray(out)
    raise ValueError(mode)


# --------------------------------------------------------------------------- enveloppes
def env_beta(n, peak_frac, a=2.0):
    """Enveloppe lisse 0 -> 1 -> 0 dont la crete est a peak_frac de la duree (>= 0.999 : montee pure)."""
    u = (np.arange(n) + 0.5) / n
    if peak_frac >= 0.999:
        return u ** a
    p = min(max(peak_frac, 0.02), 0.98)
    b = a * (1.0 - p) / p
    e = (u / p) ** a * ((1.0 - u) / (1.0 - p)) ** b
    return e / e.max()


def env_exp(n, tau, attack=0.0):
    t = tt(n)
    e = np.exp(-t / tau)
    if attack > 0:
        e = e * (1.0 - np.exp(-t / attack))
    return e


def env_adsr(n, a, d, s, r, gate=None):
    """ADSR lineaire-exponentiel ; gate = duree tenue (s) avant le release (defaut : n - r)."""
    t = tt(n)
    gate = (n / SR - r) if gate is None else gate
    e = np.where(t < a, t / max(a, 1e-6), s + (1.0 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    lvl_gate = s + (1.0 - s) * np.exp(-max(gate - a, 0.0) / max(d, 1e-6)) if gate > a else gate / max(a, 1e-6)
    rel = lvl_gate * np.clip(1.0 - (t - gate) / max(r, 1e-6), 0.0, 1.0) ** 2
    return np.where(t < gate, e, rel)


def fade_io(x, fin=0.002, fout=0.005):
    """Fondu d'entree quart de sinus (garde l'attaque) + fondu de sortie cosinus : 1er et dernier echantillons = 0."""
    x = np.array(x, dtype=np.float64, copy=True)
    n = x.shape[0]
    a = min(ns(fin), n // 2)
    b = min(ns(fout), n // 2)
    if a > 0:
        g = np.sin(0.5 * np.pi * np.arange(a) / a)
        x[:a] *= g[:, None] if x.ndim == 2 else g
    if b > 0:
        g = 0.5 + 0.5 * np.cos(np.pi * np.arange(1, b + 1) / b)
        x[-b:] *= g[:, None] if x.ndim == 2 else g
    return x


def fade_tail(x, dur):
    """Fondu cosinus sur les 'dur' dernieres secondes."""
    x = np.array(x, dtype=np.float64, copy=True)
    m = min(ns(dur), x.shape[0])
    if m > 0:
        g = 0.5 + 0.5 * np.cos(np.pi * np.arange(1, m + 1) / m)
        x[-m:] *= g[:, None] if x.ndim == 2 else g
    return x


# --------------------------------------------------------------------------- spatial / effets
def pan(x, p):
    """Panoramique equi-puissance normalise (centre = gain 1 sur chaque canal). p dans [-1, 1]."""
    x = mono(x)
    pv = np.broadcast_to(np.asarray(p, dtype=np.float64), x.shape)
    th = (np.clip(pv, -1.0, 1.0) + 1.0) * (np.pi / 4.0)
    return np.stack([x * np.cos(th) * np.sqrt(2.0), x * np.sin(th) * np.sqrt(2.0)], axis=1)


def sat(x, drive=2.0, asym=0.0):
    """Saturation tanh normalisee (asym > 0 : harmoniques paires)."""
    if asym:
        y = np.tanh(drive * (x + asym)) - np.tanh(drive * asym)
    else:
        y = np.tanh(drive * x)
    return y / np.tanh(drive)


def make_ir(rt60=1.5, predelay=0.012, seed=11, lf=1.2, hf=0.5, xover=(350.0, 3500.0), length=None,
            build_ms=6.0, width=1.0):
    """Reponse impulsionnelle stereo synthetique (bruit a decroissance exponentielle par bande)."""
    n = ns(length if length else predelay + rt60 * 1.15)
    pd = ns(predelay)
    m = n - pd
    tm = tt(m)
    ir = np.zeros((n, 2))
    for ch in range(2):
        w = white(m, seed * 31 + ch)
        lo = lp(w, xover[0], 2)
        hi = hp(w, xover[1], 2)
        mid = w - lo - hi

        def dec(rt):
            return np.exp(-6.9078 * tm / max(rt, 1e-3))

        r = lo * dec(rt60 * lf) + mid * dec(rt60) + hi * dec(rt60 * hf)
        r *= 1.0 - np.exp(-tm / (build_ms / 1000.0))
        ir[pd:, ch] = r
    if width != 1.0:
        M = 0.5 * (ir[:, 0] + ir[:, 1])
        S = 0.5 * (ir[:, 0] - ir[:, 1]) * width
        ir = np.stack([M + S, M - S], axis=1)
    ir /= np.sqrt(np.sum(ir ** 2) / 2.0)
    return ir


def reverb(x, ir, wet=0.2, dry=1.0, mono_in=True, keep_len=False):
    """Convolution stereo. Sortie allongee de la queue sauf keep_len."""
    x = st(x)
    n_out = x.shape[0] if keep_len else x.shape[0] + ir.shape[0] - 1
    out = np.zeros((n_out, 2))
    out[: x.shape[0]] += dry * x[:n_out]
    src = x.mean(axis=1)
    for ch in range(2):
        s = src if mono_in else x[:, ch]
        y = signal.oaconvolve(s, ir[:, ch])
        out[:, ch] += wet * y[:n_out]
    return out


def pingpong(x, delay_s, fb=0.4, n_rep=6, lp_hz=4000.0, wet=0.3, keep_len=False):
    """Delai ping-pong (repetitions alternees G/D, assombries)."""
    x = st(x)
    d = ns(delay_s)
    n_out = x.shape[0] if keep_len else x.shape[0] + d * n_rep
    out = np.zeros((n_out, 2))
    out[: x.shape[0]] += x[:n_out]
    tap = x.mean(axis=1)
    for k in range(1, n_rep + 1):
        tap = lp(tap, lp_hz, 1)
        ch = (k - 1) % 2
        s = k * d
        if s >= n_out:
            break
        e = min(n_out, s + tap.shape[0])
        out[s:e, ch] += wet * (fb ** (k - 1)) * tap[: e - s]
    return out


# --------------------------------------------------------------------------- oscillateurs
def _farr(freq, n=None):
    f = np.asarray(freq, dtype=np.float64)
    if f.ndim == 0:
        f = np.full(n, float(f))
    return f


def phase_acc(freq, n=None, phase0=0.0):
    """Phase (en cycles) a partir d'une frequence instantanee ; commence exactement a phase0."""
    f = _farr(freq, n)
    ph = np.cumsum(f) / SR
    return phase0 + ph - ph[0]


def sine_f(freq, n=None, phase0=0.0):
    return np.sin(2.0 * np.pi * phase_acc(freq, n, phase0))


def _polyblep(t, dt):
    y = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    y[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    x = (t[m] - 1.0) / dt[m]
    y[m] = x * x + x + x + 1.0
    return y


def saw_f(freq, n=None, phase0=0.0):
    """Dent de scie anti-repliement (polyBLEP), valeurs ~[-1, 1]."""
    f = _farr(freq, n)
    t = phase_acc(f, None, phase0) % 1.0
    dt = np.minimum(np.abs(f) / SR, 0.5)
    return 2.0 * t - 1.0 - _polyblep(t, dt)


def pulse_f(freq, duty=0.5, n=None, phase0=0.0):
    """Impulsion rectangulaire anti-repliement (difference de deux dents de scie), moyenne nulle."""
    f = _farr(freq, n)
    return 0.5 * (saw_f(f, None, phase0) - saw_f(f, None, phase0 + duty))


def tri_f(freq, n=None, phase0=0.0):
    t = phase_acc(freq, n, phase0 + 0.25) % 1.0
    return 4.0 * np.abs(t - 0.5) - 1.0


def damped(f, tau, n, amp=1.0, phase=0.0, fdrop=0.0, fdrop_tau=0.01):
    """Sinusoide amortie (mode resonant). fdrop : sur-accord initial relatif (ex 0.1 = +10 %)."""
    t = tt(n)
    fr = f * (1.0 + fdrop * np.exp(-t / fdrop_tau)) if fdrop else np.full(n, float(f))
    return amp * np.sin(2.0 * np.pi * phase_acc(fr) + phase) * np.exp(-t / tau)


# --------------------------------------------------------------------------- mesures
# Ponderation K (ITU-R BS.1770-4) a 48 kHz
KW_SOS = np.array([
    [1.53512485958697, -2.69169618940638, 1.19839281085285, 1.0, -1.69065929318241, 0.73248077421585],
    [1.0, -2.0, 1.0, 1.0, -1.99004745483398, 0.99007225036621],
])


def loudness(x):
    """Retourne dict(I=integre LUFS, M=momentane max, S=court terme max) selon BS.1770-4."""
    x = st(x)
    y = signal.sosfilt(KW_SOS, x, axis=0)
    p = np.sum(y * y, axis=1)
    blk = ns(0.4)
    hop = ns(0.1)
    if p.shape[0] < blk:
        p = np.concatenate([p, np.zeros(blk - p.shape[0])])
    cs = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, p.shape[0] - blk + 1, hop)
    z = (cs[starts + blk] - cs[starts]) / blk
    lk = -0.691 + 10.0 * np.log10(np.maximum(z, 1e-20))
    res = {"M": float(lk.max())}
    g1 = lk > -70.0
    if np.any(g1):
        rel = -0.691 + 10.0 * np.log10(np.mean(z[g1])) - 10.0
        g2 = g1 & (lk > rel)
        res["I"] = float(-0.691 + 10.0 * np.log10(np.mean(z[g2])))
    else:
        res["I"] = float("-inf")
    sblk = ns(3.0)
    if p.shape[0] >= sblk:
        s_starts = np.arange(0, p.shape[0] - sblk + 1, hop)
        zs = (cs[s_starts + sblk] - cs[s_starts]) / sblk
        res["S"] = float(-0.691 + 10.0 * np.log10(np.max(zs) + 1e-20))
    else:
        res["S"] = float(-0.691 + 10.0 * np.log10(np.sum(p) / sblk + 1e-20))
    return res


def true_peak_db(x, chunk=240000):
    """Crete vraie approx. (surechantillonnage x4)."""
    x = st(x)
    n = x.shape[0]
    m = 0.0
    for ch in range(x.shape[1]):
        for s in range(0, n, chunk):
            a = max(0, s - 64)
            seg = x[a: s + chunk + 64, ch]
            if seg.shape[0] < 8:
                continue
            up = signal.resample_poly(seg, 4, 1)
            m = max(m, float(np.max(np.abs(up))))
    return float(todb(m))


# --------------------------------------------------------------------------- fichiers WAV
def write_wav(path, x, bits=24):
    """WAV PCM entier 24 bits (ou 16), stereo, 48 kHz."""
    x = st(x)
    nch = x.shape[1]
    if bits == 24:
        q = np.clip(np.round(x * 8388607.0), -8388608, 8388607).astype("<i4")
        data = q.reshape(-1).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    elif bits == 16:
        data = np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2").tobytes()
    else:
        raise ValueError(bits)
    ba = nch * bits // 8
    fmt = struct.pack("<HHIIHH", 1, nch, SR, SR * ba, ba, bits)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt) + 8 + len(data)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<I", len(fmt)) + fmt)
        f.write(b"data" + struct.pack("<I", len(data)))
        f.write(data)


def read_wav(path):
    """Lit un WAV PCM 16/24/32 bits ou float32. Retourne (x float64 (n, ch), sr, bits)."""
    with open(path, "rb") as f:
        buf = f.read()
    if buf[:4] != b"RIFF" or buf[8:12] != b"WAVE":
        raise ValueError("pas un WAV : " + path)
    pos = 12
    fmt = None
    data = None
    while pos + 8 <= len(buf):
        cid = buf[pos: pos + 4]
        size = struct.unpack("<I", buf[pos + 4: pos + 8])[0]
        body = buf[pos + 8: pos + 8 + size]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", body[:16])
        elif cid == b"data":
            data = body
        pos += 8 + size + (size & 1)
    tag, nch, sr, _, _, bits = fmt
    if bits == 24:
        raw = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
        i = (raw[:, 0].astype(np.int32) | (raw[:, 1].astype(np.int32) << 8)
             | (raw[:, 2].astype(np.int8).astype(np.int32) << 16))
        x = i / 8388608.0
    elif bits == 16:
        x = np.frombuffer(data, dtype="<i2") / 32768.0
    elif bits == 32 and tag == 3:
        x = np.frombuffer(data, dtype="<f4").astype(np.float64)
    elif bits == 32:
        x = np.frombuffer(data, dtype="<i4") / 2147483648.0
    else:
        raise ValueError("format non gere")
    return x.reshape(-1, nch), sr, bits
