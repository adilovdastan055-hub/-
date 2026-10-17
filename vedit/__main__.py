"""CLI: python3 -m vedit <команда> …"""
import argparse
import json
import shutil
import subprocess
import sys

from .util import TOOLS, resolve


def cmd_analyze(a):
    from .analyze import analyze, expand_inputs, summarize
    for p in expand_inputs(a.paths):
        print(summarize(analyze(p, sheet_frames=a.frames, do_scenes=not a.no_scenes,
                                do_beats=True if a.beats else None)))


def cmd_frames(a):
    from .analyze import grab_frames, workdir
    times = [float(x) for x in a.at.split(",")]
    d = workdir(resolve(a.path)) / "frames"
    d.mkdir(exist_ok=True)
    print("\n".join(grab_frames(resolve(a.path), times, d)))


def cmd_transcribe(a):
    from .analyze import expand_inputs
    from .transcribe import transcribe
    for p in expand_inputs(a.paths):
        out, data = transcribe(p, a.language, a.model)
        print(f"{p.name}: {len(data['words'])} слов → {out}\n  {data['text'][:300]}")


def cmd_render(a):
    from .render import render
    out, total, _ = render(a.spec, preview=a.preview)
    print(f"готово: {out} ({total:.2f}s)")


def cmd_autocut(a):
    from .autocut import plan_beats, plan_silence
    if a.mode == "silence":
        plan = plan_silence(a.inputs[0], size=a.size)
    else:
        plan = plan_beats(a.inputs, a.music, size=a.size, beats_per_clip=a.beats_per_clip, max_len=a.max_len)
    out = resolve(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(f"план: {out} ({len(plan['clips'])} клипов)")


def cmd_list(a):
    from .motion import TEMPLATES
    from .render import GRADES, TRANSITION_ALIASES
    from .sfx import RECIPES
    from .subs import ANIMS, CAPTION_STYLES
    xf = ("fade wipeleft wiperight wipeup wipedown slideleft slideright slideup slidedown circlecrop rectcrop "
          "distance fadeblack fadewhite radial smoothleft smoothright smoothup smoothdown circleopen circleclose "
          "vertopen vertclose horzopen horzclose dissolve pixelize diagtl diagtr diagbl diagbr hlslice hrslice "
          "vuslice vdslice hblur fadegrays wipetl wipetr wipebl wipebr squeezeh squeezev zoomin fadefast fadeslow")
    print("переходы (xfade):", xf)
    print("алиасы переходов:", ", ".join(f"{k}→{v}" for k, v in TRANSITION_ALIASES.items()), "+ cut")
    print("грейды:", ", ".join(GRADES), "+ lut:путь.cube")
    print("стили субтитров:", ", ".join(CAPTION_STYLES))
    print("анимации титров:", ", ".join(ANIMS))
    print("моушн-шаблоны:", ", ".join(TEMPLATES))
    print("звуки:", ", ".join(RECIPES))
    print("зум:", "in, out, punch, pulse, {from,to}; pan: left/right/up/down")


def cmd_doctor(a):
    ok = True
    for b in ("ffmpeg", "ffprobe", "node"):
        found = shutil.which(b)
        print(f"{'✓' if found else '✗'} {b}")
        ok &= bool(found)
    for m in ("librosa", "scenedetect", "cv2"):
        try:
            __import__(m)
            print(f"✓ python: {m}")
        except ImportError:
            print(f"✗ python: {m}")
            ok = False
    for p in ("@huggingface/transformers", "sts-whisper-small"):
        e = (TOOLS / "node_modules" / p).exists()
        print(f"{'✓' if e else '✗'} npm: {p}")
        ok &= e
    r = subprocess.run(["node", "-e", "require('playwright')"], cwd=TOOLS, capture_output=True,
                       env={**__import__('os').environ, "NODE_PATH": "/opt/node-tools/node_modules"})
    print(f"{'✓' if r.returncode == 0 else '✗'} playwright (моушн-графика)")
    fc = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    for f in ("Montserrat", "Unbounded", "Rubik"):
        print(f"{'✓' if f in fc else '✗'} шрифт {f}")
    print("всё готово" if ok else "чего-то не хватает: bash scripts/setup.sh")
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(prog="vedit", description="Видеомонтаж кодом: анализ → план → рендер")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("analyze", help="метаданные, контакт-лист, сцены, паузы, биты")
    p.add_argument("paths", nargs="+")
    p.add_argument("--frames", type=int, default=24)
    p.add_argument("--no-scenes", action="store_true")
    p.add_argument("--beats", action="store_true", help="искать биты и в видео")
    p.set_defaults(f=cmd_analyze)
    p = sp.add_parser("frames", help="достать кадры в заданные секунды")
    p.add_argument("path")
    p.add_argument("--at", required=True, help="1.5,3,10.2")
    p.set_defaults(f=cmd_frames)
    p = sp.add_parser("transcribe", help="речь → пословные таймкоды")
    p.add_argument("paths", nargs="+")
    p.add_argument("--language", default="russian")
    p.add_argument("--model", default="small")
    p.set_defaults(f=cmd_transcribe)
    p = sp.add_parser("render", help="собрать ролик по edit.json")
    p.add_argument("spec")
    p.add_argument("--preview", action="store_true", help="быстрый черновик в половинном разрешении")
    p.set_defaults(f=cmd_render)
    p = sp.add_parser("autocut", help="сгенерировать черновой edit.json")
    p.add_argument("mode", choices=["silence", "beats"])
    p.add_argument("inputs", nargs="+")
    p.add_argument("--music")
    p.add_argument("--size", default="9:16")
    p.add_argument("--beats-per-clip", type=int)
    p.add_argument("--max-len", type=float)
    p.add_argument("--out", default="work/edit.json")
    p.set_defaults(f=cmd_autocut)
    sp.add_parser("list", help="все переходы, грейды, стили, шаблоны").set_defaults(f=cmd_list)
    sp.add_parser("doctor", help="проверить окружение").set_defaults(f=cmd_doctor)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
