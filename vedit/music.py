"""Синтез фоновой музыки (без лицензий): электронный бит с аккордами, басом и арпеджио.

Структура задаётся секциями в тактах: "intro:2,main:8,break:2,main:4,outro:2".
  intro — пэд + хэты + рост фильтра, без бочки;  main — всё;  break — без бочки, с райзером;
  outro — пэд затухает.  Бочка на каждую долю, поэтому склейки на целых долях/тактах попадают в бит.
"""
import numpy as np

SR = 44100
PROGRESSIONS = {
    "pop": [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]],      # Am F C G
    "epic": [[50, 53, 57], [46, 50, 53], [53, 57, 60], [48, 52, 55]],     # Dm Bb F C
    "chill": [[52, 55, 59, 62], [48, 52, 55, 59], [45, 48, 52, 55], [47, 50, 54, 57]],  # Em7 Cmaj7 Am7 Bm7
}


def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n, a, d, sr=SR):
    t = np.arange(n) / sr
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-t / max(d, 1e-4))
    return e


def _lowpass(x, cutoff):
    """Однополюсный ФНЧ; cutoff — число или массив той же длины (огибающая фильтра)."""
    if np.isscalar(cutoff):
        from scipy.signal import lfilter
        a = 1 - np.exp(-2 * np.pi * cutoff / SR)
        return lfilter([a], [1, a - 1], x)
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # переменная частота среза — поэлементно
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def _add(buf, start, sig):
    s = int(start * SR)
    if s >= len(buf):
        return
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[: e - s]


def generate(path, bpm=120, sections="intro:2,main:8,break:2,main:4,outro:2", style="pop", seed=7):
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = beat * 4
    secs = []
    for part in sections.split(","):
        name, n = part.split(":")
        secs.append((name.strip(), int(n)))
    total_bars = sum(n for _, n in secs)
    total = total_bars * bar + 2.0
    N = int(total * SR)
    drums, bass, pad, arp, fx = (np.zeros(N) for _ in range(5))
    prog = PROGRESSIONS[style]

    # заготовки ударных
    kn = int(0.35 * SR)
    kt = np.arange(kn) / SR
    kick = np.sin(2 * np.pi * (45 * kt + 90 / 30 * (1 - np.exp(-30 * kt)))) * np.exp(-kt / 0.13)
    kick += 0.3 * rng.uniform(-1, 1, kn) * np.exp(-kt / 0.004)
    cn = int(0.25 * SR)
    clap = rng.uniform(-1, 1, cn) * _env(cn, 0.001, 0.07)
    clap = clap - _lowpass(clap, 1200)
    hn = int(0.06 * SR)
    hat = rng.uniform(-1, 1, hn) * _env(hn, 0.0005, 0.018)
    hat = hat - _lowpass(hat, 7000)
    sidechain = np.ones(N)
    kick_times = []

    b0 = 0
    for name, nbars in secs:
        for b in range(b0, b0 + nbars):
            t_bar = b * bar
            chord = prog[b % len(prog)]
            progress = (b - b0 + 1) / nbars
            for k in range(4):
                tb = t_bar + k * beat
                if name in ("main",):
                    _add(drums, tb, 0.95 * kick)
                    kick_times.append(tb)
                    if k in (1, 3):
                        _add(drums, tb, 0.55 * clap)
                if name != "outro":
                    _add(drums, tb + beat / 2, (0.32 if name == "main" else 0.2) * hat)
                    if name == "main":
                        _add(drums, tb, 0.12 * hat)
                # бас — восьмые на слабую долю (pumping)
                if name == "main":
                    bn = int(beat / 2 * SR)
                    btt = np.arange(bn) / SR
                    f = _hz(chord[0] - 24)
                    tone = 0.6 * np.sign(np.sin(2 * np.pi * f * btt)) + 0.5 * np.sin(2 * np.pi * f * btt)
                    _add(bass, tb + beat / 2, tone * _env(bn, 0.005, 0.12))
                # арпеджио шестнадцатыми
                if name in ("main", "break", "intro"):
                    for s in range(4):
                        note = chord[(k * 4 + s) % len(chord)] + (12 if s % 2 else 0)
                        an = int(beat / 4 * SR * 1.5)
                        att = np.arange(an) / SR
                        f = _hz(note)
                        tone = 0.5 * np.sin(2 * np.pi * f * att) + 0.25 * np.sin(2 * np.pi * 2 * f * att)
                        _add(arp, tb + s * beat / 4, tone * _env(an, 0.002, 0.06) * (1 if name == "main" else 0.7))
            # пэд — суперпила на такт
            pn = int(bar * SR) + int(0.3 * SR)
            ptt = np.arange(pn) / SR
            sig = np.zeros(pn)
            for m in chord:
                for det in (-0.12, 0, 0.11):
                    sig += _saw(_hz(m + det / 1.0), ptt + rng.uniform(0, 1))
            sig /= len(chord) * 3
            amp = np.minimum(ptt / 0.15, 1) * np.minimum((pn / SR - ptt) / 0.3, 1)
            level = {"intro": 0.25 + 0.25 * progress, "main": 0.32, "break": 0.4, "outro": 0.35 * (1 - progress) + 0.05}[name]
            _add(pad, t_bar, sig * amp * level)
            if name == "break" and b == b0 + nbars - 1:  # райзер в последний такт брейка
                rn = int(bar * SR)
                rt = np.arange(rn) / SR
                noise = rng.uniform(-1, 1, rn)
                riser = (noise - _lowpass(noise, 800)) * (rt / bar) ** 2 * 0.5
                riser += 0.25 * np.sin(2 * np.pi * (200 * rt + 300 * rt ** 2 / bar)) * (rt / bar) ** 2
                _add(fx, t_bar, riser)
            if name == "intro" and b == b0 + nbars - 1:
                rn = int(bar * SR)
                rt = np.arange(rn) / SR
                noise = rng.uniform(-1, 1, rn)
                _add(fx, t_bar, (noise - _lowpass(noise, 1500)) * (rt / bar) ** 3 * 0.35)
        b0 += nbars

    # «насос» от бочки для пэда и арпа
    for tk in kick_times:
        s = int(tk * SR)
        n = min(int(beat * SR), N - s)
        tt = np.arange(n) / SR
        sidechain[s:s + n] = np.minimum(sidechain[s:s + n], 1 - 0.65 * np.exp(-tt / 0.09))
    pad = _lowpass(pad, 2600) * sidechain
    bass = _lowpass(bass, 420)
    arp = arp * (0.55 + 0.45 * sidechain)

    mix = 0.9 * drums + 0.75 * bass + 1.0 * pad + 0.3 * arp + 0.6 * fx
    # простое стерео: арп и пэд чуть шире
    delay = int(0.012 * SR)
    left = mix + 0.08 * np.roll(arp, delay)
    right = mix + 0.08 * np.roll(pad, delay)
    st = np.stack([left, right], axis=1)
    st /= np.max(np.abs(st)) + 1e-9
    st *= 0.89
    fade = int(1.5 * SR)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    import soundfile as sf
    sf.write(str(path), st.astype(np.float32), SR)
    # таймкоды секций — чтобы ставить сцены по тактам
    marks, t = [], 0.0
    for name, n in secs:
        marks.append({"section": name, "start": round(t, 3), "bars": n})
        t += n * bar
    return {"path": str(path), "bpm": bpm, "bar": bar, "duration": round(total, 3), "sections": marks}
