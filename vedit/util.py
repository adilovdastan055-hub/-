import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
WORK = ROOT / "work"


def log(*a):
    print("[vedit]", *a, file=sys.stderr, flush=True)


def run(cmd, quiet=True, capture=False):
    """Run a command list; raise with stderr tail on failure."""
    if os.environ.get("VEDIT_DEBUG"):
        log("$", " ".join(shlex.quote(str(c)) for c in cmd))
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if p.returncode != 0:
        tail = "\n".join(p.stderr.strip().splitlines()[-25:])
        raise RuntimeError(f"command failed ({p.returncode}): {cmd[0]}\n{tail}")
    return p.stdout if capture else None


def ffmpeg(args):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args])


def probe(path):
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
               "-show_streams", str(path)], capture=True)
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    info = {"path": str(path), "duration": float(d["format"].get("duration", 0) or 0),
            "has_audio": a is not None, "has_video": v is not None}
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = abs(int(sd["rotation"]))
        rot = rot or abs(int(v.get("tags", {}).get("rotate", 0) or 0))
        if rot in (90, 270):
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or "0/1").split("/")
        info.update(width=w, height=h, fps=round(float(num) / float(den), 3) if float(den) else 0,
                    vcodec=v.get("codec_name"), image=v.get("codec_name") in ("png", "mjpeg", "webp", "bmp")
                    and info["duration"] < 0.1)
    if a:
        info.update(sample_rate=int(a.get("sample_rate", 0)), channels=a.get("channels"))
    return info


def hex_to_ass(color, alpha=0):
    """'#RRGGBB' -> ASS '&HAABBGGRR'."""
    c = color.lstrip("#")
    r, g, b = c[0:2], c[2:4], c[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def ff_escape(path):
    """Escape a path for use inside an ffmpeg filter argument."""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
