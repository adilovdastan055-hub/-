"""Черновые монтажные планы: вырезка пауз (говорящая голова) и нарезка в бит (клип-монтаж)."""
import json
from pathlib import Path

from .analyze import analyze, silences
from .util import WORK, probe, resolve


def speech_segments(src, pad=0.12, merge_gap=0.35, min_len=0.4):
    src = resolve(src)
    dur = probe(src)["duration"]
    wj = WORK / src.stem / "words.json"
    if wj.exists():  # по словам точнее, чем по громкости
        words = json.loads(wj.read_text())["words"]
        spans = [[w["s"], w["e"]] for w in words]
    else:
        sil = silences(src)
        spans, t = [], 0.0
        for s, e in sil:
            if s > t:
                spans.append([t, s])
            t = e if e is not None else dur
        if t < dur:
            spans.append([t, dur])
    merged = []
    for s, e in spans:
        s, e = max(s - pad, 0), min(e + pad, dur)
        if merged and s - merged[-1][1] < merge_gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [[round(s, 3), round(e, 3)] for s, e in merged if e - s >= min_len]


def plan_silence(src, size="9:16", punch=True):
    segs = speech_segments(src)
    clips = []
    for i, (s, e) in enumerate(segs):
        c = {"src": str(src), "in": s, "out": e, "transition": "cut"}
        if punch and i % 2 == 1:  # чередование крупности — классический приём для джамп-катов
            c["zoom"] = {"from": 1.12, "to": 1.12}
        clips.append(c)
    return {"output": {"path": f"output/{Path(src).stem}_cut.mp4", "size": size, "fps": 30},
            "defaults": {"fit": "cover", "grade": "bright"},
            "clips": clips, "captions": {"style": "tiktok"}, "loudness": -14}


def plan_beats(sources, music, size="9:16", beats_per_clip=None, max_len=None):
    music = resolve(music)
    a = analyze(music, do_beats=True)
    b = a["beats"]
    beats = b["beats"]
    if not beats:
        raise RuntimeError("не нашёл биты в треке")
    bpm = b["bpm"] or 120
    n = beats_per_clip or (4 if bpm >= 140 else 2)
    strong = set(b["strong"])
    cuts = beats[::n]
    if max_len:
        cuts = [t for t in cuts if t <= max_len + 0.01]
    srcs = [resolve(s) for s in sources]
    clips = []
    for i in range(len(cuts) - 1):
        seg_len = cuts[i + 1] - cuts[i]
        src = srcs[i % len(srcs)]
        info = probe(src)
        use = (i // len(srcs))  # при повторе берём следующий кусок исходника
        if info.get("image"):
            c = {"src": str(src), "duration": round(seg_len, 3), "zoom": "in" if i % 2 else "out"}
        else:
            span = max(info["duration"] - seg_len, 0)
            start = (span * (0.3 + 0.25 * use)) % max(span, 0.001) if span else 0
            c = {"src": str(src), "in": round(start, 3), "out": round(start + seg_len, 3), "mute": True}
        nxt = cuts[i + 1]
        c["transition"] = {"type": "flash", "duration": 0.12} if nxt in strong and i % 4 == 3 else "cut"
        if i % 3 == 2:
            c["zoom"] = "pulse"
        clips.append(c)
    return {"output": {"path": "output/beat_montage.mp4", "size": size, "fps": 30},
            "defaults": {"fit": "cover", "grade": "cinematic"},
            "clips": clips, "music": {"src": str(music), "volume": 1.0, "duck": False, "fade_out": 1.5},
            "vignette": 0.25, "loudness": -14}
