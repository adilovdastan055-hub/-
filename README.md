# vedit — монтаж роликов с Claude

Конвейер, в котором Claude монтирует видео целиком: режет, склеивает с переходами, делает зумы и цветокор,
накладывает анимированные субтитры, титры и моушн-графику, сводит музыку и звуковые эффекты.
Монтаж описывается JSON-планом, рендерит ffmpeg — поэтому любую правку можно внести словами
(«сделай переход резче», «убери вторую паузу», «субтитры зелёным»), и ролик пересоберётся.

## Как отдать материал

1. Положи исходники в `input/` и запушь в ветку (видео идут через **Git LFS** — `git lfs install` один раз):
   ```bash
   git lfs install
   cp ~/Videos/*.mp4 input/ && git add input && git commit -m "исходники" && git push
   ```
   Или дай ссылку на прямое скачивание (Google Drive / Dropbox / Яндекс Диск с публичным доступом).
2. Напиши бриф: платформа и формат (9:16 / 16:9), длина, стиль или ролик-референс, нужны ли субтитры, музыка.
3. Claude разберёт материал, соберёт черновик (`--preview`), пришлёт его, внесёт правки и отрендерит финал.

## Что умеет

| Блок | Возможности |
|---|---|
| Анализ | контакт-листы кадров, поиск сцен, пауз, громкости; BPM и биты музыки |
| Речь | локальный Whisper (русский и др.), пословные таймкоды, .srt |
| Монтаж | обрезка, скорость 0.25–4×, реверс, стоп-кадр, кроп, кадрирование под 9:16 / 16:9 / 1:1 / 4:5, размытый фон |
| Движение | Ken Burns, наезд/отъезд, punch-in, pulse в бит, панорамы |
| Переходы | 45+ (fade, whip, flash, zoom, slide, circle, glitch, blur, dissolve…) |
| Цвет | cinematic, teal&orange, warm, cool, vivid, moody, film, b/w, свои LUT (.cube), виньетка, зерно, леттербокс |
| Субтитры | TikTok-стиль с подсветкой слова, neon, karaoke, clean, minimal — синхронно с монтажом |
| Титры | pop, zoom, drop, slide, typewriter, blur-in; акцентные слова; плашки |
| Моушн-графика | кинетический заголовок, плашка имени, счётчик, выноска со стрелкой, кнопка «подписаться», прогресс-бар, полноэкранная кинетическая типографика с эмодзи (HTML/CSS → прозрачное видео) |
| Музыка | генератор собственных треков (pop / epic / chill, любой BPM и структура) — без авторских прав |
| Звук | музыка с автоприглушением под голос, whoosh/impact/riser/pop/ding, нормализация −14 LUFS |
| Автонарезка | вырезать паузы из «говорящей головы»; клип-монтаж в бит музыки |
| AI (Higgsfield) | генерация B-roll, апскейл до 4K, удаление фона, дубляж — по запросу |

## Команды

```bash
bash scripts/setup.sh                       # зависимости (ставится автоматически в облачной сессии)
python3 -m vedit doctor                     # проверка окружения
python3 -m vedit list                       # все переходы, стили, шаблоны
python3 -m vedit analyze input/             # разбор исходников → work/<имя>/
python3 -m vedit transcribe input/talk.mp4  # речь → work/talk/words.json
python3 -m vedit autocut silence input/talk.mp4 --out work/edit.json
python3 -m vedit autocut beats input/ --music input/track.mp3 --out work/edit.json
python3 -m vedit render work/edit.json --preview   # черновик
python3 -m vedit render work/edit.json             # финал → output/
python3 -m vedit music --bpm 120 --out input/generated/music.wav   # свой трек
bash scripts/demo.sh                        # самопроверка на сгенерированных тестовых роликах
```

Пример плана со всеми возможностями — [`examples/edit.example.json`](examples/edit.example.json),
полный справочник — [`.claude/skills/video-edit/SKILL.md`](.claude/skills/video-edit/SKILL.md).
