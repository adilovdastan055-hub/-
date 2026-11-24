"""Неоновый 2D-мультик «Первый полёт на Луну» под голос «Дастан» (ElevenLabs через Higgsfield).

usage: python3 projects/moon_rocket/build.py  → музыка, фон, projects/moon_rocket/edit.json
Голос — input/generated/moon/voice.mp3 (41.3 с); пословные таймкоды — faster-whisper medium (ru).
Вся картинка — tools/motion/moon_rocket.html (canvas, кадр = функция времени); времена — по шкале голоса.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "input/generated/moon"
OFF = 0.4
VOICE_END = 41.2
TOTAL = round(VOICE_END + OFF + 2.4, 2)

TEXT = ("Три![0.00-0.42] Два![0.48-0.98] Один![1.16-1.64] Пуск![1.76-2.16] Земля[2.86-3.24] дрожит[3.24-3.78] "
        "огромная[4.06-4.46] ракета[4.46-4.86] рвётся[4.86-5.28] в[5.28-5.44] небо![5.44-5.84] Три[5.92-6.12] "
        "тысячи[6.12-6.54] тонн[6.54-6.82] огня[6.82-7.08] и[7.08-7.24] металла[7.24-7.82] вверх,[8.00-8.46] "
        "сквозь[8.56-8.84] облака![8.84-9.68] Ступени[9.80-10.28] отделяются[10.28-10.86] одна[10.86-11.08] "
        "за[11.08-11.32] другой,[11.32-11.60] и[11.96-12.20] вот[12.20-12.46] он[12.46-12.74] космос![12.76-13.30] "
        "Впереди[13.68-14.20] 384[14.20-15.78] тысячи[15.78-16.26] километров![16.26-16.82] Три[17.14-17.36] "
        "дня[17.36-17.56] пути[17.56-17.98] к[18.10-18.24] Луне.[18.24-18.60] Июль[19.02-19.48] 1969.[19.48-20.92] "
        "Лунный[21.62-22.06] модуль[22.06-22.50] «Орёл»[22.50-23.02] идёт[23.02-23.24] на[23.24-23.44] "
        "посадку.[23.44-23.94] Топливо[24.18-24.56] на[24.56-24.76] исходе.[24.76-25.22] Касание![25.32-25.96] "
        "Орёл[26.20-26.64] сел![26.64-26.94] Нил[27.50-27.82] Армстронг[27.82-28.44] делает[28.44-28.80] "
        "первый[28.80-29.16] шаг.[29.16-29.52] Это[29.52-29.96] маленький[29.96-30.50] шаг[30.50-30.78] "
        "для[30.78-31.02] человека,[31.02-31.44] и[31.44-31.92] огромный[31.92-32.38] скачок[32.38-32.96] "
        "для[32.96-33.24] человечества![33.24-34.00] Люди[34.52-35.04] на[35.04-35.24] Луне![35.24-35.94] "
        "Мечта,[35.94-36.36] которая[36.48-36.70] стала[36.70-37.18] реальностью.[37.18-37.98] "
        "Подписывайся,[38.46-39.38] дальше[39.50-39.82] будет[39.82-40.34] ещё[40.34-40.80] круче![40.80-41.20]")
WORDS = []
for tok in TEXT.split():
    w, ts = tok[:-1].split("[")
    s, e = map(float, ts.split("-"))
    WORDS.append([w, s, e])

T = {"c3": 0.0, "c2": 0.48, "c1": 1.16, "go": 1.76, "shake": 2.86, "tons": 5.92, "stages": 9.80, "sep1": 10.30,
     "sep2": 11.05, "space": 12.76, "ahead": 13.68, "days": 17.14, "july": 19.02, "eagle": 21.62, "fuel": 24.18,
     "touch": 25.32, "sat": 26.20, "neil": 27.50, "step": 29.16, "leap": 31.92, "people": 34.52, "dream": 35.94,
     "sub": 38.46}
FX = [("ding", T["c3"], .35), ("ding", T["c2"], .35), ("ding", T["c1"], .35), ("impact", T["go"], .7),
      ("riser", T["go"] + .2, .35), ("impact", T["shake"], .5), ("whoosh", T["tons"] - .1, .4),
      ("impact", T["sep1"], .55), ("impact", T["sep2"], .55), ("riser", T["space"] - 1.2, .3), ("ding", T["space"], .35),
      ("whoosh", T["ahead"] - .1, .4), ("pop", T["days"], .4), ("swoosh", T["july"] - .1, .4), ("impact", T["july"] + .05, .45),
      ("click", T["fuel"], .4), ("click", T["fuel"] + .3, .4), ("click", T["fuel"] + .6, .4),
      ("impact", T["touch"], .8), ("ding", T["sat"], .4), ("whoosh", T["neil"] - .1, .35), ("pop", T["step"], .5),
      ("swoosh", T["leap"], .4), ("impact", T["people"], .6), ("ding", T["dream"], .3),
      ("whoosh", T["sub"] - .1, .4), ("click", T["sub"] + .3, .5), ("ding", T["sub"] + .45, .3)]


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    bg = GEN / "bg.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x03010f:s=1080x1920:r=30:d={TOTAL}",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(bg)], check=True)
    music = GEN / "music.wav"
    # 120 BPM: такт = 2 с; 23 такта = 46 с
    subprocess.run(["python3", "-m", "vedit", "music", "--bpm", "120", "--sections", "intro:1,main:9,break:1,main:10,outro:2",
                    "--style", "epic", "--seed", "69", "--out", str(music)], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    plan = {
        "output": {"path": "output/moon_rocket.mp4", "size": "9:16", "fps": 30, "crf": 18},
        "defaults": {"fit": "cover", "grade": None, "transition": {"type": "cut"}},
        "clips": [{"src": str(bg.relative_to(ROOT)), "in": 0, "out": TOTAL, "mute": True, "no_captions": True}],
        "motion": [{"template": "tools/motion/moon_rocket.html", "start": 0, "duration": TOTAL,
                    "params": {"off": OFF, "t": T, "words": WORDS}}],
        "voiceover": {"src": "input/generated/moon/voice.mp3", "start": OFF, "volume": 1.0},
        "music": {"src": str(music.relative_to(ROOT)), "volume": 0.4, "duck": True, "fade_in": 0.1, "fade_out": 2.0, "loop": False},
        "sfx": {"volume": 0.5, "extra": [{"src": n, "at": round(t + OFF, 2), "volume": v} for n, t, v in FX]},
        "vignette": 0.25, "grain": 2,
        "loudness": -14,
    }
    out = ROOT / "projects/moon_rocket/edit.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(f"{out} — {TOTAL}s")


if __name__ == "__main__":
    main()
