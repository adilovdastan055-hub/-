"""Сборка плана ролика «Почему вы решили баллотироваться в депутаты?».
usage: python3 projects/deputat/build.py  →  work/edit.json
Тайминги субтитров/инфографики берутся из work/main/words.json и переводятся на итоговый таймлайн."""
import json

SRC = "input/main.mov"
INTRO = 3.4          # длина интро-клипа
XF = 0.35            # переход интро → речь
# сегменты речи (секунды исходника) без пауз + крупность (джамп-каты: общий ↔ крупный)
CLOSE = [0.12, 0.09, 0.76, 0.76]   # крупный план: кроп источника, голова чуть ниже центра
CLOSE2 = [0.12, 0.13, 0.76, 0.76]  # после склейки в исходнике (10.8 с) человек сидит ниже
# статичный кадр без зумов; паузы не вырезаем — без зумов джамп-каты выглядят как рывки
SEGS = [(0.00, 17.75, None, None)]
T0 = INTRO - XF       # где начинается речь на итоговом таймлайне


def omap(t):
    """время исходника → время итогового ролика"""
    acc = T0
    for a, b, *_ in SEGS:
        if t < a:
            return acc
        if t <= b:
            return acc + (t - a)
        acc += b - a
    return acc


words = json.load(open("work/main/words.json"))
words = words if isinstance(words, list) else words["words"]
WS = [w["s"] for w in words]

# субтитры: строки из (индекс слова, текст, акцент). Текст слегка выправлен (ошибки распознавания/оговорки).
CAPS = [
    [[(0, "Я"), (1, "болею"), (2, "за"), (3, "свой")], [(4, "город", 1)]],
    [[(5, "за"), (6, "свой")], [(7, "регион", 1)]],
    [[(8, "И"), (9, "хочу,"), (10, "чтобы")], [(11, "жители", 1)]],
    [[(12, "нашего"), (13, "города"), (14, "жили")], [(15, "лучше", 1)]],
    [[(16, "и"), (17, "в более")], [(18, "комфортных", 1)], [(19, "условиях")]],
    [[(20, "Второе", 1)]],
    [[(21, "у"), (22, "меня"), (23, "есть")], [(24, "опыт", 1)], [(25, "работы")]],
    [[(26, "в")], [(27, "производстве", 1)]],
    [[(28, "в"), (29, "коммунальной")], [(30, "сфере", 1)]],
    [[(31, "а"), (32, "также"), (33, "в")], [(34, "сельском", 1)], [(35, "хозяйстве")]],
    [[(36, "Третье", 1)]],
    [[(37, "есть"), (38, "опыт"), (39, "и")], [(40, "понимание", 1)]],
    [[(41, "чем"), (42, "должен"), (43, "заниматься")], [(44, "депутат", 1)]],
    [[(45, "и"), (46, "как"), (47, "создавать")], [(48, "комфорт", 1)]],
    [[(49, "и")], [(50, "уют", 1)], [(51, "в"), (52, "нашем"), (53, "городе")]],
]
captions, sfx = [], []
for i, lines in enumerate(CAPS):
    first = lines[0][0][0]
    nxt = CAPS[i + 1][0][0][0] if i + 1 < len(CAPS) else None
    last = max(x[0] for ln in lines for x in ln)
    s = omap(WS[first]) - 0.05
    e = omap(WS[nxt]) - 0.02 if nxt is not None else omap(words[last]["e"]) + 0.4
    out_lines = [[[round(omap(WS[x[0]]) - 0.05 - s, 3), x[1], len(x) > 2] for x in ln] for ln in lines]
    captions.append({"s": s, "e": e, "lines": out_lines})
    sfx.append({"src": "pop", "at": round(s, 3), "volume": 0.35})
    for ln in lines:                       # акцентное слово — свой «вжух»
        for x in ln:
            if len(x) > 2:
                sfx.append({"src": "swoosh", "at": round(omap(WS[x[0]]) - 0.05, 3), "volume": 0.3})

o = lambda i, d=0.0: round(omap(WS[i]) + d, 3)   # время слова i на таймлайне
EV = [
    {"type": "chips", "s": o(3), "e": o(8) - .05, "items": [[o(4), "🏙️", "Мой город"], [o(7), "🗺️", "Мой регион"]]},
    {"type": "chart", "s": o(11), "e": o(20) - .05, "emo": "👨‍👩‍👧", "label": "Жизнь горожан", "value": "лучше ↑",
     "t2": o(15), "bars": [0.35, 0.55, 0.75, 1.0]},
    {"type": "badge", "s": o(20), "e": o(26) - .05, "n": "2", "label": "<b>Опыт</b>"},
    {"type": "list", "s": o(27), "e": o(36) - .05, "y": .58,
     "items": [[o(27), "🏭", "Производство"], [o(29), "🚛", "ТОО «Орал Таза Сервис»"], [o(34), "🌾", "Сельское хозяйство"]]},
    {"type": "badge", "s": o(36), "e": o(38) - .05, "n": "3", "label": "<b>Понимание</b>"},
    {"type": "chips", "s": o(38), "e": o(41) - .05, "items": [[o(38), "🧠", "Опыт"], [o(40), "💡", "Понимание"]]},
    {"type": "hero", "s": o(44), "e": o(48) - .05, "y": .6, "items": [[o(44, -.1), "🏛️", "Работа депутата"]]},
    {"type": "hero", "s": o(48), "e": omap(17.75) - .02,
     "y": .6, "items": [[o(48), "🏡", "Комфорт"], [o(50), "✨", "Уют"]], "sparks": [[.2, -1, o(50)], [.8, 0, o(50, .3)]]},
]
EV[0]["items"].sort()
for ev in EV:   # опускаем под лицо: зона груди/стола, выше нижнего интерфейса платформ
    ev["y"] = .232   # сразу под субтитрами, над головой
for ev in EV:
    times = [it[0] for it in ev.get("items", [])] or [ev["s"]]
    for t in times:
        sfx.append({"src": "ding" if ev["type"] == "badge" else "click", "at": t, "volume": 0.3})

# время в шаблоне — от начала моушн-слоя
M0 = T0
def rel(x):
    return round(x - M0, 3)
for c in captions:
    c["s"], c["e"] = max(rel(c["s"]), 0.3), rel(c["e"])   # не налезать на уходящий вопрос интро
for ev in EV:
    ev["s"], ev["e"] = rel(ev["s"]), rel(ev["e"])
    if "t2" in ev:
        ev["t2"] = rel(ev["t2"])
    for it in ev.get("items", []):
        it[0] = rel(it[0])
    for sp in ev.get("sparks", []):
        sp[2] = rel(sp[2])
for c in captions:                         # слова — относительно своей карточки субтитров
    pass

END = omap(17.75)
clips = [{"src": "input/generated/navy_bg.mp4", "in": 0, "out": INTRO, "mute": True, "grade": "none",
          "transition": {"type": "zoomin", "duration": XF}}]
for a, b, crop, z in SEGS:
    c = {"src": SRC, "in": a, "out": b, "volume": 4.5}   # исходник тихий (−32 LUFS), loudnorm один не дотягивает
    if z:
        c["zoom"] = z
    if crop:
        c["crop"] = crop
    clips.append(c)

# звуки интро — на появление слов вопроса (тайминги шаблона question)
intro_sfx = [("click", .10, .35), ("click", .19, .3), ("click", .28, .3), ("whoosh", .42, .4),
             ("pop", .75, .35), ("impact", .85, .45), ("swoosh", INTRO - XF - .1, .35)]
sfx = [{"src": s, "at": t, "volume": v} for s, t, v in intro_sfx] + sfx

edit = {
    "output": {"path": "output/deputat_v3.mp4", "size": "9:16", "fps": 30, "crf": 18},
    "defaults": {"fit": "cover", "grade": "cool", "transition": {"type": "cut"}},
    "clips": clips,
    "motion": [
        {"template": "question", "start": 0, "duration": INTRO - 0.15, "params": {"mode": "intro", "bg": False}},
        {"template": "talk", "start": M0, "duration": round(END - M0, 3), "params": {"captions": captions, "events": EV, "capY": .222}},
    ],
    
    "vignette": 0.15,
    "loudness": -14,
}
json.dump(edit, open("work/edit.json", "w"), ensure_ascii=False, indent=1)
print("ok: речь", round(T0, 2), "→", round(END, 2), "с;", len(captions), "субтитров,", len(EV), "блоков инфографики,", len(sfx), "звуков")
