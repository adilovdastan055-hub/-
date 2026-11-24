"""Собирает edit.json: обращение кандидата, стиль «dynamic word reels» + инфо-карточки сверху.
Запуск: python3 projects/deputy_reasons/build.py && python3 -m vedit render projects/deputy_reasons/edit.json
"""
import json
from pathlib import Path

SRC = "input/main.mov"
# куски исходника (паузы вырезаны); чередуем крупность для джамп-катов
CUTS = [(0.00, 1.78, 1.0), (1.84, 5.45, 1.1), (5.60, 7.95, 1.0), (8.24, 10.70, 1.1),
        (10.80, 12.62, 1.0), (12.94, 17.35, 1.1)]

starts, t = [], 0.0
for a, b, _ in CUTS:
    starts.append(t); t += b - a
TOTAL = t


def T(s):
    """время исходника → время итогового таймлайна"""
    for (a, b, _), st in zip(CUTS, starts):
        if s <= b + 1e-6:
            return st + max(0.0, s - a)
    return TOTAL


# (lead, начало подводки, big, время big, blue, время blue, конец) — секунды исходника
WORDS = [
    ("я болею за свой", 0.00, "город", 0.62, None, None, 1.05),
    ("за свой", 1.10, "регион", 1.38, None, None, 1.88),
    ("хочу, чтобы", 1.92, "жители", 2.38, "нашего города", 2.66, 3.34),
    ("жили", 3.34, "лучше", 3.70, None, None, 4.24),
    ("в более", 4.24, "комфортных", 4.40, "условиях", 4.90, 5.50),
    (None, 5.62, "второе", 5.68, None, None, 6.28),
    ("у меня есть", 6.30, "опыт", 6.68, "в производстве", 7.32, 7.95),
    ("в", 8.26, "коммунальной", 8.36, "сфере", 8.74, 9.36),
    ("а также в", 9.38, "сельском", 9.90, "хозяйстве", 10.14, 10.70),
    (None, 10.80, "третье", 10.82, None, None, 11.48),
    ("есть опыт и", 11.50, "понимание", 12.02, None, None, 12.62),
    ("чем должен заниматься", 12.94, "депутат", 14.02, None, None, 14.88),
    ("как создавать", 14.90, "комфорт", 15.46, None, None, 16.02),
    ("и", 16.02, "уют", 16.26, "в нашем городе", 16.64, 17.35),
]

motion = []
for lead, ls, big, tb, blue, tbl, end in WORDS:
    st = T(ls)
    p = {"big": big, "t_big": round(T(tb) - st, 3), "y": 0.71, "size": 0.155}
    if lead:
        p["lead"] = lead
    if blue:
        p.update(blue=blue, t_blue=round(T(tbl) - st, 3))
    motion.append({"template": "tools/motion/word_reel.html", "start": round(st, 3),
                   "duration": round(T(end) - st, 3), "params": p})

CARDS = [
    (0.0, 5.45, {"num": "01", "label": "из 03 · почему я", "step": 1, "title": "Болею за свой город",
                  "items": [("🏙️", "Город и регион", 1.38), ("🏡", "Комфорт для жителей", 4.40)]}),
    (5.60, 10.70, {"num": "02", "label": "из 03 · опыт", "step": 2, "title": "Опыт работы",
                    "items": [("🏭", "Производство", 7.32), ("🔧", "ЖКХ", 8.36), ("🌾", "Сельское хоз-во", 9.90)]}),
    (10.80, 17.35, {"num": "03", "label": "из 03 · понимание", "step": 3, "title": "Знаю работу депутата",
                     "items": [("🏛️", "Задачи депутата", 14.02), ("🤝", "Комфорт и уют", 15.46)]}),
]
for i, (a, b, c) in enumerate(CARDS):
    st = T(a) + (0.15 if i == 0 else 0)
    c = dict(c, total=3, top=0.085, width=0.76,
             items=[{"icon": ic, "label": lb, "at": round(T(at) - st, 3)} for ic, lb, at in c["items"]])
    motion.append({"template": "tools/motion/reason_card.html", "start": round(st, 3),
                   "duration": round(T(b) - st, 3), "params": c})

clips = []
for i, (a, b, z) in enumerate(CUTS):
    clips.append({"src": SRC, "in": a, "out": b, "zoom": {"from": z, "to": z + 0.03},
                  "transition": {"type": "cut"}})

edit = {
    "output": {"path": "output/deputy_reasons.mp4", "size": "9:16", "fps": 30, "crf": 18},
    "defaults": {"fit": "cover", "grade": "cinematic"},
    "clips": clips,
    "motion": motion,
    "music": {"src": "input/generated/music_deputy.wav", "volume": 0.16, "duck": True,
              "fade_in": 0.5, "fade_out": 1.5, "loop": True},
    "sfx": {"volume": 0.35, "extra": [{"src": "pop", "at": round(T(a) + 0.15, 2), "volume": 0.4} for a, _, _ in CARDS]},
    "vignette": 0.2,
    "loudness": -14,
}
out = Path(__file__).with_name("edit.json")
out.write_text(json.dumps(edit, ensure_ascii=False, indent=1))
print(f"{out}: {TOTAL:.2f}s, motion: {len(motion)}")
