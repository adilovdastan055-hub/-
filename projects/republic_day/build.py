"""Құттықтау: Республика күні — кинетическая типографика под казахский закадровый голос.

usage: python3 projects/republic_day/build.py  → фоны, музыка, projects/republic_day/edit_visual.json
Голос (ElevenLabs через Higgsfield) сводится отдельно: в контейнере его CDN закрыт, поэтому здесь
рендерится картинка + музыка + звуки без нормализации, а голос, дакинг и −14 LUFS — в сандбоксе.
Таймкоды фраз — из faster-whisper по голосу (секунды голоса).
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "input/generated/republic_day"
V = 0.35      # голос стартует чуть позже начала ролика
LEAD = 0.1    # склейка чуть раньше первого слова фразы
TD = 0.25     # длительность переходов
TAIL = 3.2    # хвост после последнего слова
VOICE_END = 20.85
SKY, GOLD = "#00B5E2", "#FFC61A"

SCENES = [
    (0.0, {"icon": "🇰🇿", "lines": ["Құрметті", "*қазақстандықтар!*"], "word_times": [0.0, 0.64],
           "size": 0.064}),
    (1.95, {"kicker": "Баршаңызды", "kicker_time": 1.98, "lines": ["Республика", "*күнімен!*"],
            "word_times": [2.86, 3.64], "caption": "Шын жүректен *құттықтаймын!*", "caption_time": 4.4,
            "size": 0.1}),
    (5.9, {"icon": "🕊️", "lines": ["Еліміз *аман*", "жұртымыз *тыныш*"], "word_times": [5.94, 6.48, 7.16, 7.68],
           "size": 0.085}),
    (8.45, {"kicker": "Тәуелсіздігіміз", "kicker_time": 8.5, "lines": ["*тұғырлы*", "болсын!"],
            "word_times": [9.38, 9.76], "size": 0.12}),
    (10.6, {"icon": "🏡", "kicker": "Әр шаңыраққа", "kicker_time": 10.66,
            "chips": ["Бақ-береке", "Молшылық", "Қуаныш"], "chip_times": [11.54, 12.62, 13.24]}),
    (14.45, {"icon": "🇰🇿", "lines": ["Қазақстанымыз", "*көркейіп,*"], "word_times": [14.52, 15.32],
             "caption": "Көк туымыз әрдайым *биікте* желбіресін!", "caption_time": 16.12, "size": 0.082}),
    (18.75, {"icon": "✨", "kicker": "Ізгі тілекпен", "kicker_time": 18.84, "lines": ["Дастан", "*Адилов*"],
             "word_times": [19.92, 20.36], "caption": "*25 қазан* — Республика күні құтты болсын!",
             "caption_time": 21.3, "size": 0.13}),
]
# небо флага → глубокий синий, золото — только акцентом
PALETTE = [("0x001a33", "0x00a3d9", "0x003a70", "radial"), ("0x002244", "0x0090c8", "0x00c2e8", "linear"),
           ("0x00142a", "0x0077b6", "0x00b5e2", "radial"), ("0x061633", "0x1f5fbf", "0x00a3d9", "linear"),
           ("0x001e3c", "0x00a3d9", "0x7a5c00", "radial"), ("0x00183a", "0x00b5e2", "0x0060a8", "linear"),
           ("0x0a1020", "0x00a3d9", "0x8a6a00", "radial")]
TRANS = ["flash", "smoothup", "zoom", "circle", "smoothup", "flash"]


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    cuts = [0.0] + [t + V - LEAD for t, _ in SCENES[1:]]
    total = VOICE_END + V + TAIL
    ends = cuts[1:] + [total]
    clips, motion, sfx = [], [], []
    for i, ((_, sc), c0, c1) in enumerate(zip(SCENES, cuts, ends)):
        last = i == len(SCENES) - 1
        dur = c1 - c0 + (0 if last else TD)
        bg = GEN / f"bg_{i:02d}.mp4"
        a, b, c, typ = PALETTE[i]
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        f"gradients=s=1080x1920:r=30:c0={a}:c1={b}:c2={c}:n=3:speed=0.012:type={typ}:seed={i * 7 + 5}",
                        "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(bg)], check=True)
        clip = {"src": str(bg.relative_to(ROOT)), "in": 0, "out": round(dur, 3), "zoom": {"from": 1.0, "to": 1.06}}
        if not last:
            t = TRANS[i]
            clip["transition"] = {"type": t, "duration": 0.14 if t == "flash" else TD}
        clips.append(clip)
        rel = lambda x: round(max(x + V - c0, 0.0), 3)
        p = {"accent": GOLD, "deco_colors": [GOLD, SKY, "#0B4FA8"], **sc}
        for key in ("word_times", "chip_times"):
            if key in p:
                p[key] = [rel(x) for x in p[key]]
        if "caption_time" in p:
            p["caption_time"] = rel(p["caption_time"])
        if "kicker_time" in p:
            p["delay"] = rel(p.pop("kicker_time"))
        motion.append({"template": "kinetic", "start": round(c0, 3), "duration": round(c1 - c0, 3), "params": p})
        for ct in sc.get("chip_times", []):
            sfx.append({"src": "pop", "at": round(ct + V, 3), "volume": 0.3})
    motion.append({"template": "progress", "start": 0, "duration": round(total, 3),
                   "params": {"accent": GOLD, "thickness": 0.005}})
    sfx += [{"src": "riser", "at": round(cuts[-1] - 0.05, 3), "volume": 0.25},
            {"src": "ding", "at": round(SCENES[-1][1]["caption_time"] + V, 3), "volume": 0.3}]
    # 120 BPM: такт = 2 с; 13 тактов = 26 с ≥ длины ролика
    subprocess.run(["python3", "-m", "vedit", "music", "--bpm", "120", "--sections", "intro:1,main:10,outro:2",
                    "--style", "epic", "--seed", "25", "--out", str(GEN / "music.wav")], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
    plan = {
        "output": {"path": "output/republic_day_visual.mp4", "size": "9:16", "fps": 30, "crf": 20},
        "defaults": {"fit": "cover", "grade": None},
        "clips": clips,
        "motion": motion,
        "music": {"src": str((GEN / "music.wav").relative_to(ROOT)), "volume": 0.35, "duck": False,
                  "fade_in": 0.3, "fade_out": 2.0, "loop": False},
        "sfx": {"transitions": "whoosh", "volume": 0.2, "extra": sorted(sfx, key=lambda e: e["at"])},
        "vignette": 0.3, "grain": 3, "loudness": None,
    }
    out = ROOT / "projects/republic_day/edit_visual.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(f"{out} — {total:.2f}s, {len(clips)} сцен")


if __name__ == "__main__":
    main()
