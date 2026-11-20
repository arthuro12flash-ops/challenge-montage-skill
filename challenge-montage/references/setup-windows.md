# Installation (Windows en priorité, notes macOS/Linux)

## Outils

| Outil | Windows | macOS / Linux |
|---|---|---|
| ffmpeg / ffprobe | `winget install Gyan.FFmpeg` | `brew install ffmpeg` / `apt install ffmpeg` |
| yt-dlp | `winget install yt-dlp.yt-dlp` | `brew install yt-dlp` |
| uv (Python géré) | `winget install astral-sh.uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| whisper | `uv tool install --python 3.12 whisper-ctranslate2` | idem |
| edge-tts (voix IA) | `uv tool install --python 3.12 edge-tts` | idem |
| Node 20+ | `winget install OpenJS.NodeJS.LTS` | `brew install node` |
| HyperFrames | `npm install -g hyperframes` puis `hyperframes browser ensure` | idem |

Python des scripts : `uv run --python 3.12 --with numpy --with scipy python scripts/sound/make_sfx.py` (rien à installer globalement).

## Pièges rencontrés sous Windows

- **Smart App Control** bloque les DLL non signées : `openai-whisper` (PyTorch, `shm.dll`) et `melt`/une partie de Kdenlive ne démarrent pas. Utiliser **whisper-ctranslate2** (faster-whisper) et faire les rendus avec ffmpeg/HyperFrames. Ne pas désactiver ce réglage à la place de l'utilisateur (il est souvent irréversible). Diagnostic : journal `Microsoft-Windows-CodeIntegrity/Operational`, événements 3033/3077.
- **Application Claude empaquetée (MSIX)** : les écritures dans `%APPDATA%` sont virtualisées, ce qui casse les Python gérés par uv (« Missing expected target directory »). Dans la commande d'installation : `$env:UV_PYTHON_INSTALL_DIR="$env:USERPROFILE\.local\share\uv\python"; $env:UV_TOOL_DIR="$env:USERPROFILE\.local\share\uv\tools"`.
- **PATH** : après une installation winget, rafraîchir le PATH dans chaque commande PowerShell :
  `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`.
- **ffmpeg drawtext** (build Gyan) : Fontconfig absent → toujours passer `fontfile='C\:/Windows/Fonts/arialbd.ttf'`.
- **PowerShell** : entourer de guillemets les listes à virgules (`--at "1,2,3"`), sinon elles deviennent des tableaux ; les `.cmd` npm se lancent avec `shell: true` depuis Node.
- **Console** : les scripts Python forcent `sys.stdout.reconfigure(encoding="utf-8")` pour les accents.
- **JSON écrit par PowerShell** : `Set-Content -Encoding utf8` ajoute un BOM ; les scripts le retirent, mais préférer écrire les fichiers avec l'outil d'écriture.
- **RAM** : sur 8 Go, un seul whisper à la fois, rendus HyperFrames avec `-w 3`, fermer les éditeurs vidéo pendant les rendus.

## Vérifier

```bash
ffmpeg -version && yt-dlp --version && whisper-ctranslate2 --help && edge-tts --list-voices | grep fr-FR && hyperframes doctor
```
