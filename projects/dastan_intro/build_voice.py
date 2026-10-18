"""Версия с голосом: сцены режутся по фразам закадра (таймкоды — из Whisper по voice.mp3).

usage: python3 projects/dastan_intro/build_voice.py  → фоны, музыка, projects/dastan_intro/edit_voice.json
Голос ожидается в input/generated/voice.mp3.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "input/generated"
V = 0.35      # голос стартует чуть позже начала ролика
LEAD = 0.1    # склейка чуть раньше первого слова фразы
TD = 0.2      # длительность переходов
TAIL = 2.8    # хвост после последнего слова — под кнопку «Подписаться»
VOICE_END = 31.18

# (начало фразы в голосе, сцена); времена появления — тоже в секундах голоса
SCENES = [
    (0.0, {"icon": "🔥", "lines": ["Всем", "*привет!*"], "word_times": [0.0, 0.22], "accent": "#FFD400", "size": 0.14}),
    (0.86, {"kicker": "Меня зовут", "kicker_time": 0.86, "lines": ["Дастан", "*Адилов*"], "word_times": [1.28, 1.7],
            "accent": "#FFE600", "size": 0.13}),
    (2.4, {"chips": ["Маркетолог", "Блогер", "Мобилограф"], "chip_times": [2.45, 3.3, 3.85], "accent": "#FFE600"}),
    (4.72, {"kicker": "Моя стихия", "kicker_time": 4.72, "lines": ["Креатив", "Технологии", "*Контент*"],
            "word_times": [5.45, 6.05, 6.9], "caption": "который *цепляет* с первых секунд", "caption_time": 7.5,
            "accent": "#00F0FF", "size": 0.11}),
    (9.32, {"icon": "📱", "lines": ["Снимаю", "на *телефон*"], "word_times": [9.32, 9.62, 9.78],
            "accent": "#FFE600", "size": 0.12}),
    (10.5, {"icon": "🚁", "kicker": "Впечатляющие", "kicker_time": 10.85, "lines": ["Кадры", "с *дрона*"],
            "word_times": [11.6, 12.0, 12.1], "accent": "#FFE600", "size": 0.12}),
    (12.46, {"icon": "🤖", "kicker": "Использую", "kicker_time": 12.95, "lines": ["Искусственный", "*интеллект*"],
             "word_times": [13.45, 14.05], "caption": "превращаю обычные идеи в *нечто особенное*",
             "caption_time": 14.95, "accent": "#00FFA3", "size": 0.088}),
    (18.28, {"kicker": "Видео — это", "kicker_time": 18.55, "lines": ["не просто", "*картинка*"],
             "word_times": [19.3, 19.45, 19.72], "accent": "#FF2D55", "size": 0.12}),
    (20.82, {"kicker": "а инструмент, который", "kicker_time": 20.85, "flow": ["Внимание", "Эмоции", "Рост бизнеса"],
             "chip_times": [22.0, 23.3, 24.8], "accent": "#FFD400"}),
    (25.88, {"icon": "🚀", "kicker": "Я", "kicker_time": 25.88, "lines": ["Дастан", "*Адилов*"],
             "word_times": [26.28, 26.72], "caption": "Создаю контент, который *выделяется*, и идеи, которые *работают*",
             "caption_time": 27.3, "accent": "#FFE600", "size": 0.13}),
]
PALETTE = [("0x1a0500", "0xff3d00", "0x7a0a00", "radial"), ("0x0b0630", "0x3b1bd6", "0x8a2be2", "linear"),
           ("0x2b0040", "0xff2d75", "0xff8a00", "linear"), ("0x001a24", "0x00a5b5", "0x103060", "radial"),
           ("0x3a0018", "0xff5e3a", "0xff2d95", "linear"), ("0x00142e", "0x1e90ff", "0x00c2ff", "linear"),
           ("0x0a0018", "0x7b2ff7", "0x00ffa3", "spiral"), ("0x050505", "0x2a2a3a", "0x15151f", "radial"),
           ("0x001a10", "0x00b36b", "0xc9a400", "linear"), ("0x12001f", "0xff2d55", "0x5a00ff", "radial")]
TRANS = ["flash", "zoom", "whip", "smoothup", "whip", "zoom", "glitch", "circle", "flash"]


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    cuts = [0.0] + [t + V - LEAD for t, _ in SCENES[1:]]
    total = VOICE_END + V + TAIL
    ends = cuts[1:] + [total]
    clips, motion, sfx = [], [], []
    for i, ((_, sc), c0, c1) in enumerate(zip(SCENES, cuts, ends)):
        last = i == len(SCENES) - 1
        dur = c1 - c0 + (0 if last else TD)
        bg = GEN / f"vbg_{i:02d}.mp4"
        a, b, c, typ = PALETTE[i]
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        f"gradients=s=1080x1920:r=30:c0={a}:c1={b}:c2={c}:n=3:speed=0.015:type={typ}:seed={i * 11 + 3}",
                        "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(bg)], check=True)
        clip = {"src": str(bg.relative_to(ROOT)), "in": 0, "out": round(dur, 3), "zoom": {"from": 1.0, "to": 1.07}}
        if not last:
            t = TRANS[i]
            clip["transition"] = {"type": t, "duration": 0.12 if t == "flash" else TD}
        clips.append(clip)
        # времена из шкалы голоса → относительно начала сцены
        rel = lambda x: round(max(x + V - c0, 0.0), 3)
        p = dict(sc)
        for key in ("word_times", "chip_times"):
            if key in p:
                p[key] = [rel(x) for x in p[key]]
        if "caption_time" in p:
            p["caption_time"] = rel(p["caption_time"])
        if "kicker_time" in p:
            p["delay"] = rel(p.pop("kicker_time"))
        motion.append({"template": "kinetic", "start": round(c0, 3), "duration": round(c1 - c0, 3), "params": p})
        for ct in sc.get("chip_times", []):
            sfx.append({"src": "pop", "at": round(ct + V, 3), "volume": 0.35})
    cta = VOICE_END + V + 0.05
    motion.append({"template": "cta", "start": round(cta, 3), "duration": round(total - cta, 3),
                   "params": {"text": "Подписаться", "y": 0.86}})
    motion.append({"template": "progress", "start": 0, "duration": round(total, 3),
                   "params": {"accent": "#FFE600", "thickness": 0.005}})
    sfx += [{"src": "impact", "at": round(cuts[1], 3), "volume": 0.6},
            {"src": "click", "at": round(cta + 1.15, 3), "volume": 0.5},
            {"src": "ding", "at": round(cta + 1.25, 3), "volume": 0.3}]
    subprocess.run(["python3", "-m", "vedit", "music", "--bpm", "128", "--sections", "main:16,outro:3",
                    "--style", "epic", "--out", str(GEN / "music_voice.wav")], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
    plan = {
        "output": {"path": "output/dastan_intro_voice.mp4", "size": "9:16", "fps": 30, "crf": 21},
        "defaults": {"fit": "cover", "grade": None},
        "clips": clips,
        "motion": motion,
        "voiceover": {"src": "input/generated/voice.mp3", "start": V, "volume": 1.0},
        "music": {"src": "input/generated/music_voice.wav", "volume": 0.5, "duck": True, "fade_in": 0.05,
                  "fade_out": 1.5, "loop": False},
        "sfx": {"transitions": "whoosh", "volume": 0.22, "extra": sorted(sfx, key=lambda e: e["at"])},
        "vignette": 0.3, "grain": 3, "loudness": -14,
    }
    out = ROOT / "projects/dastan_intro/edit_voice.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(f"{out} — {total:.2f}s, {len(clips)} сцен")


if __name__ == "__main__":
    main()
