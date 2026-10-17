"""Синтез звуковых эффектов (без внешних библиотек звуков): whoosh, impact, pop, riser, click."""
from .util import WORK, ffmpeg

SR = 48000
RECIPES = {
    # (длительность, lavfi-источник, фильтры)
    "whoosh": (0.7, f"anoisesrc=color=pink:sample_rate={SR}:amplitude=0.9",
               "highpass=f=300,lowpass=f=4500,aphaser=type=t:speed=2,"
               "afade=t=in:d=0.38:curve=exp,afade=t=out:st=0.38:d=0.32:curve=exp,volume=1.4"),
    "swoosh": (0.4, f"anoisesrc=color=white:sample_rate={SR}:amplitude=0.6",
               "highpass=f=1200,lowpass=f=8000,afade=t=in:d=0.18:curve=qsin,afade=t=out:st=0.18:d=0.22,volume=1.2"),
    "impact": (1.2, f"aevalsrc='0.9*sin(2*PI*(38+70*exp(-8*t))*t)*exp(-3.2*t)+0.35*(random(0)*2-1)*exp(-25*t)':s={SR}",
               "lowpass=f=900,volume=1.6"),
    "pop": (0.15, f"aevalsrc='sin(2*PI*(1400-5000*t)*t)*exp(-38*t)':s={SR}", "volume=1.2"),
    "click": (0.06, f"aevalsrc='(random(0)*2-1)*exp(-120*t)':s={SR}", "highpass=f=2000,volume=1.5"),
    "riser": (1.6, f"aevalsrc='0.5*sin(2*PI*(180*t+260*t*t)*t)+0.25*(random(0)*2-1)':s={SR}",
              "highpass=f=200,afade=t=in:d=1.5:curve=exp,afade=t=out:st=1.5:d=0.1"),
    "ding": (1.0, f"aevalsrc='0.6*sin(2*PI*1320*t)*exp(-5*t)+0.3*sin(2*PI*2640*t)*exp(-7*t)':s={SR}", "volume=1"),
}
# где «пик» эффекта (чтобы ставить точно на склейку)
PEAK = {"whoosh": 0.38, "swoosh": 0.18, "impact": 0.0, "pop": 0.0, "click": 0.0, "riser": 1.5, "ding": 0.0}


def sfx_path(name):
    if name not in RECIPES:
        return None
    d = WORK / "sfx"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.wav"
    if not p.exists():
        dur, src, flt = RECIPES[name]
        ffmpeg(["-f", "lavfi", "-i", src, "-t", f"{dur}", "-af", f"{flt},aformat=channel_layouts=stereo",
                "-ar", str(SR), p])
    return p
