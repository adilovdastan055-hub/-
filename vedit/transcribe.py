"""Распознавание речи → пословные таймкоды (words.json) и .srt."""
import json
import subprocess

from .util import TOOLS, ffmpeg, log, resolve
from .analyze import workdir


def _ts(t):
    h, r = divmod(max(t, 0), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def to_srt(words, max_words=7, max_gap=0.6):
    lines, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["s"] - cur[-1]["e"] > max_gap):
            lines.append(cur)
            cur = []
        cur.append(w)
        if w["w"][-1:] in ".!?…":
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    out = []
    for i, ln in enumerate(lines, 1):
        out.append(f"{i}\n{_ts(ln[0]['s'])} --> {_ts(ln[-1]['e'])}\n{' '.join(x['w'] for x in ln)}\n")
    return "\n".join(out)


def transcribe(path, language="russian", model="small"):
    path = resolve(path)
    if not (TOOLS / "node_modules" / f"sts-whisper-{model}").exists():
        raise RuntimeError(f"нет модели whisper-{model}: запусти scripts/setup.sh "
                           f"(или npm i --prefix tools sts-whisper-{model})")
    wd = workdir(path)
    f32 = wd / "audio16k.f32"
    ffmpeg(["-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", f32])
    out = wd / "words.json"
    log(f"распознаю речь ({model}, {language})…")
    p = subprocess.run(["node", TOOLS / "transcribe.mjs", f32, out, language, model],
                       capture_output=True, text=True, cwd=TOOLS)
    f32.unlink(missing_ok=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2000:])
    data = json.loads(out.read_text())
    (wd / "subs.srt").write_text(to_srt(data["words"]))
    return out, data
