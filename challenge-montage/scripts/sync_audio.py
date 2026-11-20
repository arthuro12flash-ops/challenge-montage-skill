# Trouve où un enregistrement externe (téléphone, micro) commence dans le rush : corrélation d'enveloppes puis affinage.
# Les deux fichiers doivent être en WAV mono 16 kHz (ffmpeg -i x -vn -ac 1 -ar 16000 x.wav).
# Si le rush est un ASSEMBLAGE de clips, ce décalage global n'est valable qu'après la dernière coupe : utilisez sync_window.py clip par clip.
# Trouve le décalage d'un enregistrement externe dans le rush (corrélation d'enveloppes, puis affinage fin).
# Usage : python sync_audio.py rush.wav externe.wav   (wav mono 16 kHz)
import sys, wave
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np

def load(p):
    w = wave.open(p, "rb"); n = w.getnframes(); sr = w.getframerate()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    return x, sr

def env(x, sr, hop):
    # énergie en bande voix/ballon (différences pour accentuer les attaques), une valeur par « hop » échantillons
    d = np.diff(x, prepend=0.0)
    n = len(d) // hop
    e = np.sqrt((d[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    e = np.log(e)
    e = e - np.convolve(e, np.ones(50) / 50, mode="same")  # enlève la tendance lente
    return (e - e.mean()) / (e.std() + 1e-9)

a, sr = load(sys.argv[1]); b, sr2 = load(sys.argv[2]); assert sr == sr2
hop = sr // 100  # 10 ms
ea, eb = env(a, sr, hop), env(b, sr, hop)
c = np.correlate(ea, eb, mode="valid") / len(eb)
k = int(np.argmax(c)); second = np.sort(c)[-2]
print(f"grossier : décalage {k * 0.01:.2f} s, score {c[k]:.3f} (2e meilleur {second:.3f}, bruit {np.median(np.abs(c)):.3f})")
# affinage à l'échantillon près sur ±50 ms
lo = max(0, k * hop - hop * 5); seg = b[: sr * 20]
best, bo = -1, 0
for off in range(lo, lo + hop * 10, 8):
    r = a[off : off + len(seg)]
    if len(r) < len(seg): break
    v = float(np.dot(r, seg) / (np.linalg.norm(r) * np.linalg.norm(seg) + 1e-9))
    if v > best: best, bo = v, off
print(f"fin : décalage {bo / sr:.4f} s (corrélation {best:.3f}) ; l'externe couvre {bo / sr:.2f} -> {(bo + len(b)) / sr:.2f} s du rush")
