# Décalage d'un extrait de l'enregistrement externe, cherché seulement dans une fenêtre du rush.
# Usage : python sync_window.py rush.wav externe.wav ext_debut ext_fin rush_debut rush_fin
import sys, wave
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np

def load(p):
    w = wave.open(p, "rb"); n = w.getnframes(); sr = w.getframerate()
    return np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0, sr

def env(x, sr):
    hop = sr // 100; d = np.diff(x, prepend=0.0); n = len(d) // hop
    e = np.log(np.sqrt((d[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12))
    e = e - np.convolve(e, np.ones(50) / 50, mode="same")
    return (e - e.mean()) / (e.std() + 1e-9)

a, sr = load(sys.argv[1]); b, _ = load(sys.argv[2])
e0, e1, r0, r1 = map(float, sys.argv[3:7])
ea = env(a[int(r0 * sr): int(r1 * sr)], sr); eb = env(b[int(e0 * sr): int(e1 * sr)], sr)
c = np.correlate(ea, eb, mode="valid") / len(eb)
order = np.argsort(c)[::-1]
k = int(order[0])
print(f"extrait {e0}-{e1}s : commence à {r0 + k * 0.01:.2f}s du rush (score {c[k]:.3f}, médiane {np.median(np.abs(c)):.3f}) -> décalage {r0 + k * 0.01 - e0:.3f}")
