# -*- coding: utf-8 -*-
"""
sheet.py - planche de controle visuel (ffmpeg) : pour chaque WAV, nom + forme d'onde + spectrogramme
(frequences log 20 Hz - 20 kHz, lignes reperes a 100 Hz, 1 kHz et 4 kHz).

Usage : python sheet.py sortie.png fichier1.wav fichier2.wav ... [--cols 2] [--w 560]
"""
import math
import os
import subprocess
import sys

FONT = "fontfile='C\\:/Windows/Fonts/arialbd.ttf'"


def build(out_png, files, cols=2, W=560, HW=60, HS=200):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for f in files:
        args += ["-i", f]
    parts = []
    lines = []
    for ref in (100, 1000, 4000):
        y = int(HS - HS * math.log(ref / 20.0) / math.log(1000.0))
        lines.append(f"drawbox=x=0:y={y}:w={W}:h=1:color=white@0.45:t=fill")
    for i, f in enumerate(files):
        name = os.path.splitext(os.path.basename(f))[0]
        parts.append(f"[{i}:a]asplit=2[a{i}][b{i}]")
        parts.append(f"[a{i}]showwavespic=s={W}x{HW}:split_channels=0:colors=0x55ccff,"
                     f"drawtext={FONT}:text='{name}':x=4:y=3:fontsize=15:fontcolor=yellow[w{i}]")
        # FFT interne haute (2048 cases -> ~23 Hz de resolution) puis reduction a HS pixels
        parts.append(f"[b{i}]showspectrumpic=s={W}x1024:legend=0:fscale=log:scale=log:start=20:stop=20000:"
                     f"drange=100:color=intensity,scale={W}:{HS}:flags=area," + ",".join(lines) + f"[s{i}]")
        parts.append(f"[w{i}][s{i}]vstack=inputs=2,pad=w={W + 6}:h={HW + HS + 6}:color=black[t{i}]")
    th, tw = HW + HS + 6, W + 6
    if len(files) == 1:
        parts.append("[t0]null[out]")
    else:
        lay = "|".join(f"{(i % cols) * tw}_{(i // cols) * th}" for i in range(len(files)))
        parts.append("".join(f"[t{i}]" for i in range(len(files))) + f"xstack=inputs={len(files)}:layout={lay}:fill=black[out]")
    args += ["-filter_complex", ";".join(parts), "-map", "[out]", "-frames:v", "1", out_png]
    subprocess.run(args, check=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    cols = 2
    W = 560
    if "--cols" in a:
        cols = int(a[a.index("--cols") + 1])
        del a[a.index("--cols"): a.index("--cols") + 2]
    if "--w" in a:
        W = int(a[a.index("--w") + 1])
        del a[a.index("--w"): a.index("--w") + 2]
    build(a[0], a[1:], cols=cols, W=W)
