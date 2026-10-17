"""Генерация .ass: анимированные субтитры (пословная подсветка) и текстовые титры с анимациями."""
from .util import hex_to_ass

# size/outline/margin — доли от ширины/высоты кадра, чтобы стиль работал в любом формате
CAPTION_STYLES = {
    "tiktok":  dict(font="Montserrat Black", size=0.072, upper=True, words=3, color="#FFFFFF",
                    hl="#FFE600", outline=0.0065, shadow=0, pop=True),
    "neon":    dict(font="Unbounded Black", size=0.058, upper=True, words=2, color="#FFFFFF",
                    hl="#39FF88", outline=0.006, shadow=0, pop=True),
    "karaoke": dict(font="Montserrat ExtraBold", size=0.058, upper=False, words=5, color="#FFFFFF",
                    hl="#FFC400", outline=0.005, shadow=0, sweep=True),
    "clean":   dict(font="Inter Display SemiBold", size=0.048, upper=False, words=7, color="#FFFFFF",
                    hl=None, outline=0.0025, shadow=0.003),
    "minimal": dict(font="Rubik Bold", size=0.056, upper=False, words=4, color="#FFFFFF",
                    hl="#FF4D6D", outline=0.004, shadow=0, pop=False),
}

POSITIONS = {"top": 0.14, "upper": 0.3, "center": 0.5, "lower": 0.66, "bottom": 0.8, "lower_third": 0.78}


def _t(sec):
    sec = max(sec, 0)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    cs = int(round(s * 100))
    if cs == 6000:
        m, cs = m + 1, 0
    return f"{int(h)}:{int(m):02d}:{cs // 100:02d}.{cs % 100:02d}"


def _esc(text):
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def _accent(text, accent, base):
    """*слово* → акцентный цвет (как в моушн-шаблоне title)."""
    parts = _esc(text).split("*")
    return "".join(p if i % 2 == 0 else f"{{\\c{hex_to_ass(accent)}}}{p}{{\\c{base}}}"
                   for i, p in enumerate(parts))


def header(w, h):
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Inter Display Black,{int(w * 0.06)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{max(2, int(w * 0.005))},0,5,{int(w * 0.06)},{int(w * 0.06)},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _dlg(start, end, text, layer=0):
    return f"Dialogue: {layer},{_t(start)},{_t(end)},Default,,0,0,0,,{text}\n"


def group_words(words, max_words, max_gap=0.5):
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["s"] - cur[-1]["e"] > max_gap):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w["w"][-1:] in ".!?…":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def caption_events(words, w, h, style="tiktok", position=None, overrides=None):
    st = dict(CAPTION_STYLES[style])
    st.update(overrides or {})
    vertical = h > w
    ypos = POSITIONS.get(position or ("lower" if vertical else "bottom"), 0.7)
    x, y = w / 2, h * ypos
    size = int(w * st["size"] * (1 if vertical else 0.62))
    outline = max(1, int(w * st["outline"] * (1 if vertical else 0.62)))
    shadow = int(w * st.get("shadow", 0))
    base = (f"\\an5\\pos({x:.0f},{y:.0f})\\fn{st['font']}\\fs{size}\\bord{outline}\\shad{shadow}"
            f"\\c{hex_to_ass(st['color'])}\\3c&H000000&\\4c&H80000000&\\q{2 if st['words'] <= 3 else 0}")
    lines = []
    groups = group_words(words, st["words"])
    for gi, g in enumerate(groups):
        g_end = g[-1]["e"]
        if gi + 1 < len(groups) and groups[gi + 1][0]["s"] - g_end < 0.35:
            g_end = groups[gi + 1][0]["s"]  # без мигания между группами
        toks = [(x_["w"].upper() if st["upper"] else x_["w"]) for x_ in g]
        if st.get("sweep"):  # караоке: заливка слова по мере произнесения
            parts = []
            for k, (wd, tok) in enumerate(zip(g, toks)):
                nxt = g[k + 1]["s"] if k + 1 < len(g) else wd["e"]
                dur_cs = max(1, int(round((max(nxt, wd["e"]) - wd["s"]) * 100)))
                parts.append(f"{{\\kf{dur_cs}}}{_esc(tok)} ")
            sweep = f"\\2c{hex_to_ass(st['color'])}\\c{hex_to_ass(st['hl'])}"
            lines.append(_dlg(g[0]["s"], g_end, f"{{{base}{sweep}\\fad(80,80)}}" + "".join(parts).rstrip()))
            continue
        if not st.get("hl"):
            lines.append(_dlg(g[0]["s"], g_end, f"{{{base}\\fad(120,120)}}" + _esc(" ".join(toks))))
            continue
        for i, wd in enumerate(g):
            s = wd["s"] if i else g[0]["s"]
            e = g[i + 1]["s"] if i + 1 < len(g) else g_end
            if e <= s:
                continue
            parts = []
            for j, tok in enumerate(toks):
                if j == i:
                    pop = "\\fscx125\\fscy125\\t(0,110,\\fscx100\\fscy100)" if st.get("pop") else ""
                    parts.append(f"{{\\c{hex_to_ass(st['hl'])}{pop}}}{_esc(tok)}{{\\r}}{{{base}}}")
                else:
                    parts.append(_esc(tok))
            intro = "\\fscx85\\fscy85\\t(0,90,\\fscx100\\fscy100)" if i == 0 else ""
            lines.append(_dlg(s, e, f"{{{base}{intro}}}" + " ".join(parts)))
    return lines


ANIMS = ("none", "fade", "pop", "zoom", "slide_up", "slide_left", "drop", "typewriter", "blur_in")


def overlay_events(overlays, w, h):
    out = []
    for o in overlays:
        start, end = float(o["start"]), float(o["end"])
        pos = o.get("pos", "center")
        if isinstance(pos, (list, tuple)):
            x, y = pos[0] * w if pos[0] <= 1 else pos[0], pos[1] * h if pos[1] <= 1 else pos[1]
        else:
            x, y = w / 2, h * POSITIONS.get(pos, 0.5)
        size = int(float(o.get("size", 0.08)) * w)
        font = o.get("font", "Unbounded Black")
        color = hex_to_ass(o.get("color", "#FFFFFF"))
        outline = int(float(o.get("outline", 0.005)) * w)
        tags = f"\\an5\\fn{font}\\fs{size}\\c{color}\\3c{hex_to_ass(o.get('outline_color', '#000000'))}\\bord{outline}\\shad0"
        if o.get("box"):  # плашка под текстом
            pad = int(size * 0.35)
            tags += f"\\3c{hex_to_ass(o['box'])}\\bord{pad}\\xbord{pad}\\ybord{int(pad * 0.6)}"
        anim = o.get("anim", "pop")
        if o.get("rotate"):
            tags += f"\\frz{o['rotate']}"
        text = o["text"].upper() if o.get("upper") else o["text"]
        if anim == "typewriter":
            text = text.replace("*", "")
        dur_ms = int((end - start) * 1000)
        out_fade = int(o.get("fade_out", 180))
        if anim == "slide_up":
            tags += f"\\move({x:.0f},{y + h * 0.06:.0f},{x:.0f},{y:.0f},0,280)\\fad(180,{out_fade})"
        elif anim == "slide_left":
            tags += f"\\move({x + w * 0.4:.0f},{y:.0f},{x:.0f},{y:.0f},0,300)\\fad(120,{out_fade})"
        elif anim == "drop":
            tags += (f"\\move({x:.0f},{y - h * 0.25:.0f},{x:.0f},{y:.0f},0,260)"
                     f"\\fscy120\\t(260,340,\\fscy90)\\t(340,420,\\fscy100)\\fad(0,{out_fade})")
        else:
            tags += f"\\pos({x:.0f},{y:.0f})"
            if anim == "fade":
                tags += f"\\fad(250,{out_fade})"
            elif anim == "pop":
                tags += f"\\fscx0\\fscy0\\t(0,170,\\fscx118\\fscy118)\\t(170,270,\\fscx100\\fscy100)\\fad(0,{out_fade})"
            elif anim == "zoom":
                tags += (f"\\fscx170\\fscy170\\blur10\\alpha&HFF&"
                         f"\\t(0,320,0.6,\\fscx100\\fscy100\\blur0\\alpha&H00&)\\fad(0,{out_fade})")
            elif anim == "blur_in":
                tags += f"\\blur25\\alpha&HFF&\\t(0,400,\\blur0\\alpha&H00&)\\fad(0,{out_fade})"
        if anim == "typewriter":
            step = min(60, max(20, int(min(dur_ms * 0.5, 1500) / max(len(text), 1))))
            body = "".join(f"{{\\alpha&HFF&\\t({i * step},{i * step + 1},\\alpha&H00&)}}{_esc(c)}"
                           for i, c in enumerate(text))
            out.append(_dlg(start, end, f"{{{tags}\\fad(0,{out_fade})}}" + body, layer=5))
        else:
            out.append(_dlg(start, end, f"{{{tags}}}" + _accent(text, o.get("accent", "#FFE600"), color),
                            layer=5))
    return out


def write_ass(path, w, h, words=None, caption_style=None, caption_position=None,
              caption_overrides=None, overlays=None):
    body = header(w, h)
    if words and caption_style:
        body += "".join(caption_events(words, w, h, caption_style, caption_position, caption_overrides))
    if overlays:
        body += "".join(overlay_events(overlays, w, h))
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path
