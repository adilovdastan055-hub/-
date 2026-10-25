"""Прогулка «10 000 шагов» в формате сплит-экрана (референс — ролик «эксперт + инфографика»).

usage: python3 projects/walk_10k/build.py  → карточка с видео, музыка, projects/walk_10k/edit.json
Исходник — input/ref/ref1.mov (съёмка на две камеры: улица + лицо в окошке).
Сверху — сцены tools/motion/walk_10k.html, снизу — окно с улицей и лицом во врезке.
Слова — faster-whisper large-v3 (ru), поправлены руками; неразборчивое между 15.3 и 18.7 с не титруется.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "input/ref/ref1.mov"
GEN = ROOT / "input/generated/walk_10k"
TOTAL = 36.8

WORDS = [
    ("Так,", 0.0, 0.78), ("вот", 0.88, 1.04), ("дошёл", 1.04, 1.62), ("до", 1.62, 1.84), ("площади", 1.84, 2.56),
    ("Батыр", 2.56, 2.94), ("қыздар.", 2.94, 3.24),
    ("От", 5.2, 5.45), ("стелы", 5.45, 6.15), ("до", 7.1, 7.4), ("сюда", 7.4, 8.05), ("это", 8.5, 9.54),
    ("4 808", 9.54, 10.86), ("шагов,", 10.86, 11.36), ("почти", 11.36, 11.58), ("5 000.", 11.58, 12.1),
    ("Получается,", 12.4, 13.0), ("прямо", 13.0, 13.22), ("от", 13.22, 13.48), ("стелы,", 13.48, 13.94),
    ("если", 13.94, 14.56), ("сюда", 14.56, 14.82), ("дойти,", 14.82, 15.16), ("Назарбаева,", 15.28, 16.06),
    ("это", 18.78, 19.44), ("практически", 19.44, 19.88), ("5 000,", 19.88, 20.48), ("и", 20.6, 20.82),
    ("обратно,", 20.82, 21.16), ("если", 21.16, 21.26), ("дойти,", 21.26, 21.56), ("то", 21.64, 21.82),
    ("10 000.", 21.82, 22.36), ("Говорят", 22.36, 23.12), ("же,", 23.12, 23.2), ("норма", 23.24, 23.54),
    ("—", 23.54, 23.54), ("проходить", 23.54, 24.02), ("10 000.", 24.02, 24.56), ("Имейте", 25.0, 25.58),
    ("в", 25.58, 25.68), ("виду:", 25.68, 25.92), ("стела,", 25.92, 26.68), ("начинайте", 26.7, 27.78),
    ("до", 27.78, 28.38), ("конца", 28.38, 28.74), ("по", 28.74, 28.8), ("проспекту", 28.8, 29.3),
    ("Назарбаева,", 29.3, 29.8), ("до", 29.84, 30.0), ("площади", 30.0, 31.36), ("Батыр қыздар", 31.36, 32.4),
    ("и", 32.4, 32.58), ("обратно.", 32.58, 34.02), ("Вот", 34.26, 34.84), ("вам", 34.84, 34.98),
    ("10 000.", 34.98, 35.6),
]
# смены сцен (совпадают со сценами в walk_10k.html) — сюда лёгкий whoosh
SCENE_CUTS = [4.55, 12.3, 22.36, 24.95, 34.2]


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    card = GEN / "card.mp4"
    if not card.exists():
        # окно 886×730 в (97, 1190): улица из основной камеры + лицо из врезки (скруглённая маска)
        from PIL import Image, ImageDraw
        mask = GEN / "face_mask.png"
        m = Image.new("L", (254, 338), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 253, 337], radius=34, fill=255)
        m.save(mask)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(SRC), "-loop", "1", "-i", str(mask), "-filter_complex",
                        "[0:v]fps=30,split[a][b];[a]crop=576:474:0:272,scale=886:730:flags=lanczos,eq=saturation=1.08:contrast=1.03[m];"
                        "[b]crop=188:250:370:20,scale=254:338:flags=lanczos,format=rgba[f0];[1:v]format=gray[mk];[f0][mk]alphamerge[f];"
                        "color=c=0x0A0F0E:s=1080x1920:r=30[bg];[bg][m]overlay=97:1190:shortest=1[v1];"
                        "[v1][f]overlay=705:1214:shortest=1,format=yuv420p[v]",
                        "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "17", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", str(card)], check=True)
    # 100 BPM: такт 2.4 с; 16 тактов = 38.4 с
    subprocess.run(["python3", "-m", "vedit", "music", "--bpm", "100", "--sections", "intro:2,main:12,outro:2",
                    "--style", "chill", "--seed", "10", "--out", str(GEN / "music.wav")], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
    plan = {
        "output": {"path": "output/walk_10k.mp4", "size": "9:16", "fps": 30, "crf": 18},
        "defaults": {"fit": "cover", "grade": None, "transition": {"type": "cut"}},
        "clips": [{"src": str(card.relative_to(ROOT)), "in": 0, "out": TOTAL, "no_captions": True}],
        "motion": [{"template": "tools/motion/walk_10k.html", "start": 0, "duration": TOTAL,
                    "params": {"words": [[w, s, e] for w, s, e in WORDS]}}],
        "music": {"src": str((GEN / "music.wav").relative_to(ROOT)), "volume": 0.12, "duck": True,
                  "fade_in": 0.5, "fade_out": 1.5},
        "sfx": {"volume": 0.3, "extra": [{"src": "whoosh" if i % 2 == 0 else "swoosh", "at": t, "volume": 0.22}
                                         for i, t in enumerate(SCENE_CUTS)]
                + [{"src": "ding", "at": 21.82, "volume": 0.2}, {"src": "riser", "at": 34.3, "volume": 0.18},
                   {"src": "impact", "at": 34.95, "volume": 0.22}]},
        "loudness": -14,
    }
    out = ROOT / "projects/walk_10k/edit.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(f"{out} — {TOTAL}s")


if __name__ == "__main__":
    main()
