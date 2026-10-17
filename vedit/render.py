"""Рендер ролика по монтажному плану (edit.json).

Этапы: 1) каждый клип нормализуется в сегмент (обрезка, скорость, кадрирование, зум, цвет);
2) сегменты склеиваются переходами xfade/acrossfade; 3) поверх — виньетка/зерно, субтитры,
титры, моушн-графика; 4) звук: голос + музыка с приглушением + SFX, нормализация громкости.
"""
import json
import math
import shutil
from pathlib import Path

from . import sfx as sfxmod
from .subs import write_ass
from .util import WORK, ff_escape, ffmpeg, log, probe, resolve

ASPECTS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350),
           "4:3": (1440, 1080), "21:9": (2560, 1080)}

GRADES = {
    "none": "",
    "cinematic": "colorbalance=rs=-0.05:bs=0.07:rm=0.02:bm=-0.02:rh=0.07:gh=0.01:bh=-0.07,"
                 "curves=all='0/0.02 0.25/0.21 0.75/0.79 1/0.98',eq=saturation=1.08",
    "teal_orange": "colorbalance=rs=-0.1:gs=0.02:bs=0.12:rh=0.1:gh=0.02:bh=-0.12,eq=contrast=1.08:saturation=1.15",
    "warm": "colortemperature=temperature=4800:mix=0.6,eq=saturation=1.08:contrast=1.04",
    "cool": "colortemperature=temperature=8200:mix=0.6,eq=contrast=1.05",
    "vivid": "eq=saturation=1.35:contrast=1.07,unsharp=5:5:0.4",
    "moody": "eq=brightness=-0.03:contrast=1.12:saturation=0.82,colorbalance=bs=0.06:rs=-0.03",
    "film": "curves=preset=vintage,eq=saturation=0.9,noise=alls=7:allf=t",
    "bw": "hue=s=0,eq=contrast=1.18:brightness=-0.02",
    "bright": "eq=brightness=0.04:contrast=1.03:saturation=1.1,unsharp=5:5:0.3",
}

TRANSITION_ALIASES = {"crossfade": "fade", "flash": "fadewhite", "dip": "fadeblack", "whip": "smoothleft",
                      "whip_right": "smoothright", "zoom": "zoomin", "glitch": "pixelize", "blur": "hblur",
                      "push": "slideleft", "push_up": "slideup", "circle": "circleopen", "wipe": "wipeleft"}


def _size(spec):
    s = spec.get("size", "9:16")
    if isinstance(s, str):
        return ASPECTS[s]
    return int(s[0]), int(s[1])


def _grade(name):
    if not name:
        return ""
    if name.startswith("lut:"):
        return f"lut3d=file='{ff_escape(resolve(name[4:]))}'"
    if name not in GRADES:
        raise ValueError(f"неизвестный грейд {name!r}; есть: {', '.join(GRADES)} или lut:путь.cube")
    return GRADES[name]


def _atempo(speed):
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.5f}")
    return ",".join(parts)


def _zoom_filters(zoom, pan, W, H, D):
    """Ken Burns / punch-in. Возвращает фильтры, применяемые после кадрирования в W×H."""
    if not zoom and not pan:
        return []
    if isinstance(zoom, dict):
        z0, z1 = float(zoom.get("from", 1.0)), float(zoom.get("to", 1.15))
        expr = f"{z0}+({z1 - z0})*t/{D:.3f}"
    elif zoom == "in":
        expr = f"1+0.12*t/{D:.3f}"
    elif zoom == "out":
        expr = f"1.12-0.12*t/{D:.3f}"
    elif zoom == "punch":  # резкий наезд в начале клипа и удержание
        expr = "1+0.14*min(t/0.18,1)"
    elif zoom == "pulse":  # «удар» под бит
        expr = "1+0.06*exp(-9*t)"
    else:
        expr = "1.12"  # только панорама — нужен запас по краям
    p = (pan or "").lower()
    k = f"min(t/{D:.3f},1)"
    x = {"left": f"(iw-{W})*(1-{k})", "right": f"(iw-{W})*{k}"}.get(p, f"(iw-{W})/2")
    y = {"up": f"(ih-{H})*(1-{k})", "down": f"(ih-{H})*{k}"}.get(p, f"(ih-{H})/2")
    return [f"scale=w='2*trunc({W}*({expr})/2)':h='2*trunc({H}*({expr})/2)':eval=frame:flags=bicubic",
            f"crop={W}:{H}:'{x}':'{y}'"]


def _fit_filters(fit, W, H, bg="#000000"):
    if fit == "contain":
        return f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg}"
    if fit == "blur":
        return (f"split[fg][bg];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=luma_radius=40:luma_power=2,eq=brightness=-0.08[bgb];"
                f"[fg]scale={W}:{H}:force_original_aspect_ratio=decrease[fgs];[bgb][fgs]overlay=(W-w)/2:(H-h)/2")
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"


def build_segment(i, clip, ctx):
    """Нормализует один клип в work/render/seg_XXX.mkv. Возвращает (путь, длительность)."""
    W, H, FPS = ctx["W"], ctx["H"], ctx["fps"]
    out = ctx["dir"] / f"seg_{i:03d}.mkv"
    d = ctx["defaults"]
    speed = float(clip.get("speed", 1.0))
    freeze = float(clip.get("freeze_end", 0))
    grade = _grade(clip.get("grade", ctx["grade"]))
    args = []

    if "title" in clip or clip.get("color"):  # титульная карточка на цветном фоне
        D = float(clip.get("duration", 2.0))
        args += ["-f", "lavfi", "-t", f"{D}", "-i", f"color=c={clip.get('bg', '#0B0B0F')}:s={W}x{H}:r={FPS}"]
        has_audio = False
        src_dur = D
        vf = []
        if clip.get("title"):
            ass = ctx["dir"] / f"seg_{i:03d}.ass"
            ov = {"text": clip["title"], "start": 0, "end": D, "anim": clip.get("anim", "zoom"),
                  "size": clip.get("size", 0.09), "font": clip.get("font", "Unbounded Black"),
                  "color": clip.get("text_color", "#FFFFFF"), "upper": clip.get("upper", False),
                  "accent": clip.get("accent", "#FFE600")}
            ovs = [ov]
            if clip.get("subtitle"):
                ovs.append({"text": clip["subtitle"], "start": 0.25, "end": D, "anim": "slide_up",
                            "pos": [0.5, 0.58], "size": 0.038, "font": "Montserrat SemiBold",
                            "color": clip.get("subtitle_color", "#BBBBBB"), "outline": 0})
                ov["pos"] = [0.5, 0.47]
            write_ass(ass, W, H, overlays=ovs)
            vf.append(f"ass='{ff_escape(ass)}'")
    else:
        src = resolve(clip["src"])
        info = ctx["probe"](src)
        if info.get("image"):
            D = float(clip.get("duration", 3.0))
            args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{D}", "-i", src]
            has_audio = False
            src_dur = D
            speed = 1.0
        else:
            t_in = float(clip.get("in", 0))
            t_out = float(clip.get("out", info["duration"]))
            t_out = min(t_out, info["duration"])
            src_dur = t_out - t_in
            if src_dur <= 0:
                raise ValueError(f"клип {i}: out <= in ({clip})")
            args += ["-ss", f"{t_in:.3f}", "-t", f"{src_dur:.3f}", "-i", src]
            has_audio = info["has_audio"] and not clip.get("mute")
            D = src_dur / speed
        vf = [_fit_filters(clip.get("fit", d.get("fit", "cover")), W, H, clip.get("pad_color", "#000000"))]
        if clip.get("crop"):  # ручной кроп источника до вписывания: [x,y,w,h] в долях
            cx, cy, cw, ch = clip["crop"]
            vf.insert(0, f"crop=iw*{cw}:ih*{ch}:iw*{cx}:ih*{cy}")
        if clip.get("mirror"):
            vf.append("hflip")

    vf.insert(0, "setpts=PTS-STARTPTS")
    if speed != 1.0:
        vf.append(f"setpts=PTS/{speed}")
    if clip.get("reverse"):
        vf.append("reverse")
    vf.append(f"fps={FPS}")
    vf += _zoom_filters(clip.get("zoom"), clip.get("pan"), W, H, D)
    if grade:
        vf.append(grade)
    if clip.get("filters"):  # произвольные ffmpeg-фильтры для этого клипа
        vf.append(clip["filters"])
    if freeze > 0:
        vf.append(f"tpad=stop_mode=clone:stop_duration={freeze}")
    vf += ["setsar=1", "format=yuv420p"]
    total = D + freeze

    if has_audio:
        af = ["asetpts=PTS-STARTPTS", "aresample=48000", "aformat=channel_layouts=stereo"]
        if speed != 1.0:
            af.append(_atempo(speed))
        if clip.get("reverse"):
            af.append("areverse")
        af.append(f"volume={float(clip.get('volume', 1.0))}")
        af.append(f"apad=whole_dur={total:.3f}")
        a_in = "[0:a]"
    else:
        args += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        af = ["anull"]
        a_in = "[1:a]"
    fc = f"[0:v]{','.join(vf)}[v];{a_in}{','.join(af)},atrim=0:{total:.3f}[a]"
    ffmpeg([*args, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-g", str(FPS),
            "-c:a", "pcm_s16le", "-ar", "48000", out])
    return out, total


def _transition(clip, defaults):
    t = clip.get("transition", defaults.get("transition", {"type": "fade", "duration": 0.35}))
    if isinstance(t, str):
        t = {"type": t}
    typ = t.get("type", "fade")
    if typ in ("cut", "none", None):
        return None, 0
    dur = float(t.get("duration", 0.18 if typ in ("flash", "fadewhite") else 0.35))
    return TRANSITION_ALIASES.get(typ, typ), dur


def _map_words(clips, starts, ctx):
    """Переносит пословные таймкоды исходников на таймлайн монтажа."""
    words = []
    for clip, st in zip(clips, starts):
        if "src" not in clip or clip.get("mute") or clip.get("no_captions"):
            continue
        wj = WORK / Path(clip["src"]).stem / "words.json"
        if not wj.exists():
            continue
        speed = float(clip.get("speed", 1.0))
        t_in = float(clip.get("in", 0))
        t_out = float(clip.get("out", 1e9))
        for w in json.loads(wj.read_text())["words"]:
            if w["s"] >= t_in - 0.05 and w["e"] <= t_out + 0.15:
                words.append({"w": w["w"], "s": st + max(w["s"] - t_in, 0) / speed,
                              "e": st + min(w["e"] - t_in, t_out - t_in) / speed})
    words.sort(key=lambda x: x["s"])
    return words


def render(spec_path, preview=False):
    spec_path = resolve(spec_path)
    spec = json.loads(spec_path.read_text())
    out_cfg = spec.get("output", {})
    W, H = _size(out_cfg)
    FPS = int(out_cfg.get("fps", 30))
    if preview:  # быстрый черновик: половинное разрешение
        W, H = (W // 4) * 2, (H // 4) * 2
    rdir = WORK / "render" / spec_path.stem
    if rdir.exists():
        shutil.rmtree(rdir)
    rdir.mkdir(parents=True)
    cache = {}

    def cprobe(p):
        if p not in cache:
            cache[p] = probe(p)
        return cache[p]

    ctx = {"W": W, "H": H, "fps": FPS, "dir": rdir, "defaults": spec.get("defaults", {}),
           "grade": spec.get("defaults", {}).get("grade"), "probe": cprobe}
    clips = spec["clips"]
    segs = []
    for i, c in enumerate(clips):
        log(f"сегмент {i + 1}/{len(clips)}")
        segs.append(build_segment(i, c, ctx))

    # --- склейка с переходами ---
    inputs, fc = [], []
    for p, _ in segs:
        inputs += ["-i", p]
    cur_v, cur_a = "[0:v]", "[0:a]"
    cur_len = segs[0][1]
    starts = [0.0]
    trans_marks = []  # (время центра перехода, тип) — для звуков
    for i in range(1, len(segs)):
        typ, td = _transition(clips[i - 1], ctx["defaults"])
        di = segs[i][1]
        nv, na = f"[v{i}]", f"[a{i}]"
        if typ is None:
            fc.append(f"{cur_v}{cur_a}[{i}:v][{i}:a]concat=n=2:v=1:a=1{nv}{na}")
            starts.append(cur_len)
            trans_marks.append((cur_len, "cut", clips[i - 1]))
            cur_len += di
        else:
            td = min(td, segs[i - 1][1] * 0.5, di * 0.5)
            off = cur_len - td
            fc.append(f"{cur_v}[{i}:v]xfade=transition={typ}:duration={td:.3f}:offset={off:.3f}{nv}")
            fc.append(f"{cur_a}[{i}:a]acrossfade=d={td:.3f}:c1=tri:c2=tri{na}")
            starts.append(off)
            trans_marks.append((off + td / 2, typ, clips[i - 1]))
            cur_len += di - td
        cur_v, cur_a = nv, na
    total = cur_len

    # --- видео-пост: виньетка, зерно, субтитры/титры, моушн ---
    post = []
    if spec.get("grade_all"):
        post.append(_grade(spec["grade_all"]))
    if spec.get("vignette"):
        post.append(f"vignette=angle={float(spec['vignette']) * math.pi / 2:.3f}")
    if spec.get("grain"):
        post.append(f"noise=alls={int(spec['grain'])}:allf=t")
    if spec.get("letterbox"):  # киношные полосы, напр. 2.39
        ar = float(spec["letterbox"])
        bar = max(0, int((H - W / ar) / 2))
        post.append(f"drawbox=y=0:w=iw:h={bar}:color=black:t=fill,drawbox=y=ih-{bar}:w=iw:h={bar}:color=black:t=fill")

    cap = spec.get("captions")
    words = None
    if cap:
        if cap.get("source", "auto") == "auto":
            words = _map_words(clips, starts, ctx)
        else:
            words = json.loads(resolve(cap["source"]).read_text())["words"]
        if not words:
            log("субтитры: нет words.json — сначала `vedit transcribe <исходник>`")
    overlays = spec.get("overlays", [])
    if (words and cap) or overlays:
        ass = rdir / "overlay.ass"
        write_ass(ass, W, H, words=words, caption_style=cap and cap.get("style", "tiktok"),
                  caption_position=cap and cap.get("position"), caption_overrides=cap and cap.get("overrides"),
                  overlays=overlays)
        post.append(f"ass='{ff_escape(ass)}'")
    vchain = cur_v
    if post:
        fc.append(f"{cur_v}{','.join(post)}[vpost]")
        vchain = "[vpost]"

    n_in = len(segs)
    from .motion import render_motion
    for k, m in enumerate(spec.get("motion", [])):
        mov = render_motion(m, W, H, FPS, rdir / f"motion_{k}")
        inputs += ["-i", mov]
        st = float(m.get("start", 0))
        fc.append(f"[{n_in}:v]setpts=PTS-STARTPTS+{st}/TB[mo{k}]")
        fc.append(f"{vchain}[mo{k}]overlay=0:0:eof_action=pass:format=auto[vm{k}]")
        vchain = f"[vm{k}]"
        n_in += 1
    fc.append(f"{vchain}format=yuv420p[vout]")

    # --- звук ---
    mix = [cur_a]
    voice = cur_a
    music = spec.get("music")
    if music:
        inputs += ["-stream_loop", "-1" if music.get("loop", True) else "0", "-i", resolve(music["src"])]
        mi = n_in
        n_in += 1
        m_start = float(music.get("offset", 0))  # с какой секунды трека начинать
        fi, fo = float(music.get("fade_in", 0.3)), float(music.get("fade_out", 2.0))
        mf = (f"[{mi}:a]atrim=start={m_start},asetpts=PTS-STARTPTS,aresample=48000,"
              f"aformat=channel_layouts=stereo,atrim=0:{total:.3f},volume={float(music.get('volume', 0.3))},"
              f"afade=t=in:d={fi},afade=t=out:st={max(total - fo, 0):.3f}:d={fo}")
        if music.get("duck", True) and any("src" in c and not c.get("mute") for c in clips):
            fc.append(f"{cur_a}asplit=2[voice][sc]")
            fc.append(f"{mf}[mus]")
            fc.append("[mus][sc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350:makeup=1[mduck]")
            mix = ["[voice]", "[mduck]"]
        else:
            fc.append(f"{mf}[mus]")
            mix = [cur_a, "[mus]"]
    sfx_cfg = spec.get("sfx", {})
    events = []
    on_tr = sfx_cfg.get("transitions")
    if on_tr:
        for t, typ, c in trans_marks:
            name = c.get("sfx", on_tr if typ != "cut" else sfx_cfg.get("cuts"))
            if name:
                events.append({"src": name, "at": t, "volume": sfx_cfg.get("volume", 0.5), "peak": True})
    for c, st in zip(clips, starts):
        if c.get("sfx_in"):
            events.append({"src": c["sfx_in"], "at": st, "volume": sfx_cfg.get("volume", 0.5), "peak": True})
    events += sfx_cfg.get("extra", [])
    for j, ev in enumerate(events):
        p = sfxmod.sfx_path(ev["src"]) or resolve(ev["src"])
        at = float(ev["at"])
        if ev.get("peak", True) and ev["src"] in sfxmod.PEAK:
            at -= sfxmod.PEAK[ev["src"]]
        at = max(at, 0)
        inputs += ["-i", p]
        ms = int(at * 1000)
        fc.append(f"[{n_in}:a]aresample=48000,aformat=channel_layouts=stereo,"
                  f"volume={float(ev.get('volume', 0.5))},adelay={ms}|{ms}[sfx{j}]")
        mix.append(f"[sfx{j}]")
        n_in += 1
    lufs = float(spec.get("loudness", -14))
    if len(mix) > 1:
        fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first[amixed]")
        achain = "[amixed]"
    else:
        achain = voice
    fc.append(f"{achain}loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000,alimiter=limit=0.95,"
              f"atrim=0:{total:.3f}[aout]")

    out = resolve(out_cfg.get("path", "output/final.mp4"))
    if preview:
        out = out.with_name(out.stem + "_preview" + out.suffix)
    out.parent.mkdir(parents=True, exist_ok=True)
    script = rdir / "graph.txt"
    script.write_text(";\n".join(fc))
    log(f"финальный рендер: {W}x{H}@{FPS}, {total:.2f}s → {out}")
    ffmpeg([*inputs, "-filter_complex_script", script, "-map", "[vout]", "-map", "[aout]",
            "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast" if preview else out_cfg.get("preset", "slow"),
            "-crf", str(28 if preview else out_cfg.get("crf", 18)), "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    timeline = [{"clip": i, "start": round(s, 3), "duration": round(d, 3)} for i, (s, (_, d)) in enumerate(zip(starts, segs))]
    (rdir / "timeline.json").write_text(json.dumps({"total": total, "clips": timeline}, indent=1))
    return out, total, timeline
