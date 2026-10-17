---
name: video-edit
description: Монтаж видео кодом через vedit (ffmpeg + локальный Whisper + HTML-моушн). Используй, когда пользователь присылает видео/фото/музыку и просит смонтировать ролик, нарезать Reels/TikTok/Shorts, убрать паузы, добавить субтитры, переходы, титры, анимации, музыку, звуки, цветокор, или смонтировать в бит.
---

# Видеомонтаж через vedit

Всё делается из корня репозитория командой `python3 -m vedit …`. Монтаж описывается
JSON-планом (`work/edit.json`), рендер детерминирован — правки = правка JSON и перерендер.

## 0. Окружение

```bash
bash scripts/setup.sh        # идемпотентно; ставит pip/npm-зависимости и шрифты
python3 -m vedit doctor      # всё ли на месте
python3 -m vedit list        # все переходы, грейды, стили субтитров, анимации, шаблоны, звуки
```
HuggingFace в облачном окружении закрыт — Whisper берётся из npm (`sts-whisper-small`), это нормально.

## 1. Бриф (если пользователь не сказал — спроси коротко, одним сообщением)

Платформа и формат (9:16 / 16:9 / 1:1 / 4:5), целевая длина, стиль/референс, нужны ли субтитры,
музыка (свой трек или без), что обязательно должно попасть в ролик, бренд-цвета/шрифт.
Если пользователь просит «просто сделай круто» — бери дефолты: 9:16, 30 fps, субтитры `tiktok`,
грейд `cinematic`, длина по материалу, хук в первые 2 секунды.

## 2. Разбор материала — обязательно ДО плана

```bash
python3 -m vedit analyze input/            # все файлы папки
python3 -m vedit transcribe input/talk.mp4 # для всего, где есть речь
```
- Открой каждый `work/<имя>/sheet.jpg` через Read — это контакт-лист (24 кадра с таймкодами).
  Так ты «видишь» видео. Для точного выбора кадра: `python3 -m vedit frames input/x.mp4 --at 3.2,7.5`.
- `work/<имя>/analysis.json`: `scenes` (склейки внутри исходника), `silences` (паузы),
  `beats` (BPM, доли, `strong` — сильные доли, `bar_starts` — начала тактов), `loudness_lufs`.
- `work/<имя>/words.json` — пословные таймкоды речи; читай текст, чтобы резать по смыслу.
  Whisper-small ошибается в редких словах — если субтитры важны, проверь и поправь `words.json` руками
  (поля `w`, `s`, `e`) до рендера.

## 3. Монтажный план

Быстрые черновики (потом доработай руками):
```bash
python3 -m vedit autocut silence input/talk.mp4 --out work/edit.json      # убрать паузы, джамп-каты
python3 -m vedit autocut beats input/clips/ --music input/track.mp3 --out work/edit.json  # клип в бит
```

### Схема edit.json
```jsonc
{
  "output": {"path": "output/final.mp4", "size": "9:16", "fps": 30, "crf": 18},  // size: "9:16"|"16:9"|"1:1"|"4:5"|[w,h]
  "defaults": {"fit": "cover", "grade": "cinematic", "transition": {"type": "fade", "duration": 0.35}},
  "clips": [
    // видео: in/out — секунды исходника
    {"src": "input/a.mp4", "in": 2.0, "out": 5.5,
     "speed": 1.0,            // 0.25…4, звук тянется atempo
     "fit": "cover",          // cover (обрезать) | contain (поля) | blur (размытый фон — для горизонталки в вертикаль)
     "crop": [0.2, 0, 0.6, 1],// ручной кроп источника x,y,w,h в долях (до fit) — чтобы держать человека в кадре
     "zoom": "in",            // in | out | punch | pulse | {"from":1.0,"to":1.2}
     "pan": "left",           // left | right | up | down
     "grade": "vivid",        // перекрывает defaults.grade; "lut:input/my.cube"
     "volume": 1.0, "mute": false, "reverse": false, "mirror": false, "freeze_end": 0.5,
     "filters": "eq=gamma=1.1",   // любые ffmpeg-фильтры
     "transition": {"type": "whip", "duration": 0.3},  // переход В СЛЕДУЮЩИЙ клип; "cut" — склейка
     "sfx": "whoosh",         // звук на этом переходе (перекрывает sfx.transitions)
     "sfx_in": "impact",      // звук в момент начала клипа
     "no_captions": false},
    // фото (Ken Burns)
    {"src": "input/p.jpg", "duration": 3, "zoom": "in", "pan": "right"},
    // титульная карточка (*слово* — акцентный цвет)
    {"title": "ГЛАВА *1*", "subtitle": "начало", "duration": 1.5, "bg": "#0B0B12", "anim": "zoom",
     "font": "Unbounded Black", "accent": "#FFE600"}
  ],
  "captions": {"style": "tiktok", "position": "lower", "overrides": {"hl": "#39FF88"}},  // source: "auto" | путь к words.json
  "overlays": [  // текстовые титры поверх (время — по таймлайну результата)
    {"text": "ВАЖНО", "start": 1.0, "end": 2.5, "anim": "pop", "pos": "top", "size": 0.09,
     "font": "Unbounded Black", "color": "#FFFFFF", "accent": "#FFE600", "box": "#FF0044", "rotate": -4, "upper": true}
  ],
  "motion": [    // HTML-моушн-графика (tools/motion/*.html), прозрачная, поверх видео
    {"template": "lower_third", "start": 2, "duration": 3, "params": {"name": "Имя", "role": "Роль"}}
  ],
  "music": {"src": "input/track.mp3", "volume": 0.3, "offset": 12.0, "duck": true, "fade_in": 0.3, "fade_out": 2, "loop": true},
  "sfx": {"transitions": "whoosh", "cuts": null, "volume": 0.5,
          "extra": [{"src": "impact", "at": 7.2, "volume": 0.8}]},  // src: имя синтезированного звука или путь к файлу
  "grade_all": null, "vignette": 0.25, "grain": 4, "letterbox": 2.39,
  "loudness": -14   // LUFS: -14 для соцсетей/YouTube
}
```

Справочник значений — `python3 -m vedit list`. Кратко:
- **Переходы**: все `xfade` (fade, slideleft, smoothleft, circleopen, zoomin, pixelize, hblur, radial, dissolve…)
  + алиасы `whip`, `flash`, `dip`, `zoom`, `glitch`, `push`, `circle`, `wipe` и `cut`.
- **Грейды**: cinematic, teal_orange, warm, cool, vivid, moody, film, bw, bright, `lut:путь.cube`.
- **Субтитры**: tiktok (3 слова, жёлтая подсветка + поп), neon (2 слова, Unbounded, зелёный),
  karaoke (заливка слова), clean (строки), minimal. Позиции: top, upper, center, lower, bottom.
- **Анимации титров**: pop, zoom, fade, slide_up, slide_left, drop, typewriter, blur_in.
- **Моушн-шаблоны** (`params`):
  - `title` — кинетический заголовок: `title` ("\n" — перенос, *слово* — акцент), `subtitle`, `accent`, `size`
  - `lower_third` — плашка имени: `name`, `role`, `accent`, `x`, `y`
  - `counter` — счётчик: `from`, `to`, `prefix`, `suffix`, `decimals`, `label`, `count_time`
  - `callout` — обвести и подписать: `x`, `y`, `r`, `label`, `lx`, `ly`
  - `cta` — кнопка «подписаться» с курсором и кликом: `text`, `done_text`, `accent`, `y`
  - `progress` — полоса прогресса (duration = длина ролика): `position`, `thickness`, `accent`
  Новый шаблон = новый HTML в `tools/motion/` на CSS-анимациях (`_base.css`/`_base.js`; время
  управляется через `document.getAnimations()`, для JS-анимаций реализуй `window.seek(t)`).
- **Звуки** (синтез, без внешних файлов): whoosh, swoosh, impact, pop, click, riser, ding.

## 4. Рендер и самопроверка — всегда

```bash
python3 -m vedit render work/edit.json --preview   # половинное разрешение, быстро
python3 -m vedit analyze output/final_preview.mp4 --no-scenes --frames 30
```
Открой контакт-лист результата и проверь: титры/субтитры не обрезаны и не налезают друг на друга,
лица не срезаны кропом, переходы на местах, нет чёрных кадров. Громкость результата должна быть ≈ −14 LUFS.
`work/render/<план>/timeline.json` — где каждый клип начинается на итоговом таймлайне
(по нему ставь `overlays`, `motion`, `sfx.extra`). Затем финал без `--preview`.

Отдай результат через SendUserFile (`output/*.mp4`), коротко перечисли, что сделано, и спроси про правки.
Видео в `output/` и `work/` не коммить (они в .gitignore); коммить только планы, если пользователь хочет.

## Правила хорошего монтажа (применяй по умолчанию)

- **Хук в первые 1–2 с**: самый сильный момент/фраза в начало, титр-обещание, без логотипов и «привет, ребята».
- **Темп**: для Reels/TikTok кадр живёт 1.5–4 с; длинные планы оживляй `zoom: in`/`punch`, чередуй крупность
  на джамп-катах (`zoom: {"from":1.12,"to":1.12}` через клип).
- **Переходы — специя, не основа**: 70–90 % склеек — `cut`. Эффектный переход — на смене темы/локации
  или на сильную долю. Один-два типа переходов на ролик, не зоопарк.
- **В бит**: склейки на `beats`, акценты (flash, punch, impact) — на `strong`/`bar_starts`.
- **Субтитры**: для вертикали — `position: lower` (выше интерфейса TikTok), не больше 3 слов; не закрывай лицо.
  Безопасная зона 9:16: верхние ~12 % и нижние ~20 % перекрывает интерфейс платформы.
- **Звук**: голос важнее всего — музыка 0.2–0.35 с `duck: true`; whoosh на переходах тихо (0.3–0.5);
  в финале `fade_out`. Итог −14 LUFS.
- **Цвет**: один грейд на весь ролик (`defaults.grade`), отдельные клипы — только для выравнивания.
- **Финал**: CTA (`cta`) или сильная последняя фраза; не обрывай музыку — `fade_out`.

## AI-генерация (Higgsfield, если подключён)

Если не хватает кадров — B-roll, фон, интро, апскейл до 4K, удаление фона, перекадрирование, дубляж —
через инструменты `mcp__Higgsfield__*` (generate_video, upscale_video, reframe…). Это тратит кредиты
пользователя: сначала спроси и, если можно, покажи стоимость (`get_cost: true`). Скачанные результаты
клади в `input/generated/` и используй как обычные клипы.

## Если что-то сломалось
- `VEDIT_DEBUG=1 python3 -m vedit render …` — печатает команды ffmpeg; граф фильтров — `work/render/<план>/graph.txt`.
- Ошибка «no such filter» / шрифт не тот — `bash scripts/setup.sh`, `fc-list | grep Montserrat`.
- Очень длинные исходники (> 20 мин, 4K): сначала нарезать нужные куски, `ffmpeg -ss … -t … -c copy`.
