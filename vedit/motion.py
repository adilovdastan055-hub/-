"""Моушн-графика: HTML/CSS-шаблоны (tools/motion/*.html) → прозрачное видео для наложения."""
import json
import shutil
import subprocess

from .util import TOOLS, ffmpeg, log, resolve

TEMPLATES = sorted(p.stem for p in (TOOLS / "motion").glob("*.html"))


def render_motion(m, W, H, FPS, outdir):
    """m: {template, start, duration, params}. Возвращает путь к .mov (PNG с альфой)."""
    dur = float(m.get("duration", 3))
    tpl = m["template"]
    tpl_path = str(resolve(tpl)) if tpl.endswith(".html") else tpl
    frames = outdir / "frames"
    if outdir.exists():
        shutil.rmtree(outdir)
    frames.mkdir(parents=True)
    spec = {"template": tpl_path, "width": W, "height": H, "fps": FPS, "duration": dur,
            "params": m.get("params", {}), "outDir": str(frames)}
    sp = outdir / "spec.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False))
    log(f"моушн «{tpl}»: {dur}s, {int(dur * FPS)} кадров")
    p = subprocess.run(["node", TOOLS / "motion.mjs", sp], capture_output=True, text=True, cwd=TOOLS)
    if p.returncode != 0:
        raise RuntimeError("motion render failed:\n" + p.stderr[-2000:])
    mov = outdir / "motion.mov"
    ffmpeg(["-framerate", str(FPS), "-i", frames / "f_%05d.png", "-c:v", "png", "-pix_fmt", "rgba", mov])
    shutil.rmtree(frames)
    return mov
