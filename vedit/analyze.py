"""Разбор исходников: метаданные, контакт-лист кадров, сцены, тишина, биты, громкость."""
import json
import math
import re
import subprocess
from pathlib import Path

from .util import WORK, ffmpeg, log, probe, resolve

MEDIA_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mts",
             ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
             ".jpg", ".jpeg", ".png", ".webp"}


def workdir(path):
    d = WORK / Path(path).stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def contact_sheet(path, info, out, frames=24, cols=6, width=320):
    dur = max(info["duration"], 0.1)
    rows = math.ceil(frames / cols)
    font = "fontcolor=white:fontsize=22:box=1:boxcolor=black@0.6:boxborderw=4:x=6:y=6"
    vf = (f"fps={frames}/{dur:.3f},scale={width}:-2,"
          f"drawtext=text='%{{pts\\:hms}}':{font},tile={cols}x{rows}:padding=4:margin=4")
    ffmpeg(["-i", path, "-vf", vf, "-frames:v", "1", "-q:v", "3", out])


def grab_frames(path, times, outdir):
    outs = []
    for t in times:
        o = Path(outdir) / f"frame_{t:08.3f}.jpg"
        ffmpeg(["-ss", f"{t}", "-i", path, "-frames:v", "1", "-q:v", "2", str(o)])
        outs.append(str(o))
    return outs


def scenes(path, threshold=27.0):
    try:
        from scenedetect import ContentDetector, detect
    except ImportError:
        log("scenedetect не установлен — пропускаю сцены")
        return []
    lst = detect(str(path), ContentDetector(threshold=threshold), show_progress=False)
    return [[round(a.get_seconds(), 3), round(b.get_seconds(), 3)] for a, b in lst]


def silences(path, noise_db=-35, min_dur=0.45):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else None
        out.append([round(max(s, 0), 3), round(e, 3) if e is not None else None])
    return out


def loudness(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                        "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    return float(m.group(1)) if m else None


def beats(path):
    try:
        import librosa
        import numpy as np
    except ImportError:
        log("librosa не установлен — пропускаю биты")
        return None
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    times = librosa.frames_to_time(frames, sr=sr)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    strength = onset_env[np.clip(frames, 0, len(onset_env) - 1)] if len(frames) else []
    # «сильные» доли — верхняя треть по силе атаки: на них ставим самые заметные склейки
    thr = float(np.percentile(strength, 66)) if len(strength) else 0
    tempo = float(np.atleast_1d(tempo)[0])
    return {"bpm": round(tempo, 1), "beats": [round(float(t), 3) for t in times],
            "strong": [round(float(t), 3) for t, s in zip(times, strength) if s >= thr],
            "bar_starts": [round(float(t), 3) for t in times[::4]]}


def analyze(path, sheet_frames=24, do_scenes=True, do_beats=None):
    path = resolve(path)
    info = probe(path)
    wd = workdir(path)
    res = {"info": info}
    if info.get("has_video") and not info.get("image"):
        sheet = wd / "sheet.jpg"
        contact_sheet(path, info, sheet, frames=sheet_frames)
        res["contact_sheet"] = str(sheet)
        if do_scenes:
            res["scenes"] = scenes(path)
    if info.get("has_audio"):
        res["loudness_lufs"] = loudness(path)
        if info.get("has_video"):
            res["silences"] = silences(path)
        if do_beats or (do_beats is None and not info.get("has_video")):
            res["beats"] = beats(path)
    (wd / "analysis.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    res["analysis_json"] = str(wd / "analysis.json")
    return res


def summarize(res):
    i = res["info"]
    lines = [f"{Path(i['path']).name}: {i['duration']:.2f}s"]
    if i.get("has_video"):
        lines[0] += f", {i['width']}x{i['height']} @ {i.get('fps')}fps"
    if i.get("has_audio"):
        lines[0] += f", audio {res.get('loudness_lufs')} LUFS"
    if "scenes" in res:
        lines.append(f"  сцен: {len(res['scenes'])}")
    if res.get("silences"):
        lines.append(f"  пауз (>0.45s): {len(res['silences'])}")
    if res.get("beats"):
        b = res["beats"]
        lines.append(f"  BPM {b['bpm']}, битов {len(b['beats'])}, сильных {len(b['strong'])}")
    if "contact_sheet" in res:
        lines.append(f"  контакт-лист: {res['contact_sheet']}")
    lines.append(f"  json: {res['analysis_json']}")
    return "\n".join(lines)


def expand_inputs(paths):
    out = []
    for p in paths:
        p = resolve(p)
        if p.is_dir():
            out += sorted(x for x in p.iterdir() if x.suffix.lower() in MEDIA_EXT)
        else:
            out.append(p)
    return out
