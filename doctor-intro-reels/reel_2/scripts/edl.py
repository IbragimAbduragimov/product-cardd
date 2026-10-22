"""Монтажный лист ролика «Для чего создан мой блог».

Звук: фразы из фронтального дубля (основа) и две фразы из бокового дубля
(боковое видео — отдельный дубль, поэтому ракурс меняется только целыми фразами
вместе с его собственным звуком). Длинные паузы сокращаются до естественных;
каждая подрезка совпадает со сменой плана, поэтому «скачков» в кадре нет.

Изображение: список планов поверх выходного таймлайна — фронт (с приближением),
бок, фото, графические сцены. Все времена выходного таймлайна кратны кадру 59,94 fps.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(ROOT)
FRONT_SRC = os.path.join(PROJECT, "sources", "IMG_3483.mov")
SIDE_SRC = os.path.join(PROJECT, "sources", "IMG_7785.mov")
FPS_NUM, FPS_DEN = 60000, 1001
FPS = FPS_NUM / FPS_DEN
W, H = 1080, 1920

VAD = json.load(open(os.path.join(ROOT, "build", "vad.json")))
ISL = {i + 1: tuple(v) for i, v in enumerate(VAD["front"])}     # острова речи фронта, нумерация с 1

# Фразы в порядке монтажа: (источник, острова фронта | (начало, конец) бока, пауза после, метка)
PHRASES = [
    ("front", [1], 0.45, "hook"),             # Пришло время рассказать, для чего создан мой блог.
    ("front", [2], 0.50, "intro"),            # Как вы уже знаете, я … сердечно-сосудистый хирург.
    ("front", [3, 4, 5, 6], 0.50, "insight"),  # Встречаясь … задолго до болезни.
    ("side", (16.33, 23.70), 0.45, "patients"),   # Я не раз наблюдал … по профилактике.
    ("front", [10], 0.45, "noknow"),          # Они просто не располагали этими знаниями ранее.
    ("front", [11, 12, 13], 0.55, "treat"),   # Теперь же остаётся только лечить … обострений.
    ("front", [14], 0.50, "nocure"),          # О полном излечении, увы, речи уже не идёт.
    ("side", (40.62, 48.31), 0.55, "realize"),    # Осознав это … и создал эту страницу.
    ("front", [18, 19, 20], 0.50, "best"),    # Ведь лучшее лечение — это профилактика.
    ("front", [21, 22], 0.42, "numbers"),     # Давайте обратимся к конкретным цифрам и статистике.
    ("front", [23, 24], 0.45, "who"),         # По данным ВОЗ, здоровье человека зависит от следующих факторов:
    ("front", [25], 0.42, "f1"),              # образ жизни,
    ("front", [26], 0.40, "f2"),              # наследственность,
    ("front", [27], 0.40, "f3"),              # окружающая среда
    ("front", [28], 0.55, "f4"),              # и здравоохранение.
    ("front", [29], 0.50, "think"),           # Только вдумайтесь в эти цифры.
    # остров 30 «Согласно ВОЗ» — повтор уже сказанной ссылки, убран
    ("front", [31], 0.50, "ten"),             # Медицина вносит всего лишь 10% …
    ("front", [32, 33], 0.45, "others"),      # Отсюда следует … играют другие факторы.
    ("front", [34, 35, 36], 0.60, "cond"),    # Однако их положительный эффект достижим …
    ("front", [37], 0.40, "mission"),         # Именно этим я как раз и буду заниматься —
    ("front", [38], 0.50, "share"),           # делиться профессиональными знаниями …
    ("front", [39, 40, 41, 42], 0.0, "cta"),  # Поэтому ставьте лайки … здоровое будущее.
]
LEAD_IN = 0.20       # тишина перед первой фразой
TAIL = 0.55          # после последнего слова до начала финальной плашки
END_CARD = 2.2


def q(t):
    """Округление длительности до целого числа кадров."""
    return round(t * FPS) / FPS


def build_clips():
    clips, out = [], 0.0
    side_gaps = {"patients": (15.40, 24.30), "realize": (39.60, 48.95)}   # тишина вокруг фраз бока
    prev_gap = LEAD_IN
    for k, (src, rng, gap_after, tag) in enumerate(PHRASES):
        if src == "front":
            s, e = ISL[rng[0]][0], ISL[rng[-1]][1]
            before = ISL[rng[0] - 1][1] if rng[0] > 1 else 0.0
            nxt = PHRASES[k + 1] if k + 1 < len(PHRASES) else None
            after = ISL[nxt[1][0]][0] if nxt and nxt[0] == "front" and nxt[1][0] == rng[-1] + 1 else e + 2.0
        else:
            s, e = rng
            before, after = side_gaps[tag]
        # тишина вокруг фразы: сколько взять до и после (не больше, чем есть в исходнике)
        pre = min(prev_gap * 0.45, s - before - 0.02) if k else min(LEAD_IN, s)
        post_target = gap_after * 0.55 if gap_after else TAIL
        post = min(post_target, max(0.05, after - e - 0.02))
        a, b = s - pre, e + post
        dur = q(b - a)
        clips.append(dict(src=src, a=round(a, 4), b=round(a + dur, 4), out=round(out, 6), tag=tag,
                          speech=(s, e)))
        out += dur
        prev_gap = gap_after
    return clips, out


CLIPS, SPEECH_END = build_clips()
TOTAL = q(SPEECH_END + END_CARD)


def out_time(src, t):
    """Выходное время для момента t источника (берётся клип, содержащий t)."""
    for c in CLIPS:
        if c["src"] == src and c["a"] - 1e-6 <= t <= c["b"] + 1e-6:
            return c["out"] + (t - c["a"])
    raise ValueError(f"{src} {t} не попадает в монтаж")


def clip(tag):
    return next(c for c in CLIPS if c["tag"] == tag)


def span(tag_from, tag_to=None):
    c0, c1 = clip(tag_from), clip(tag_to or tag_from)
    return c0["out"], c1["out"] + (c1["b"] - c1["a"])


# ---- Планы (изображение) ----
# zoom: (z_начало, z_конец) — приближение относительно полного кадра; лицо по центру
SHOTS = []


def shot(kind, t0, t1, **kw):
    SHOTS.append(dict(kind=kind, t0=q(t0), t1=q(t1), **kw))


def build_shots():
    t = span("hook")
    shot("front", 0, t[1], zoom=(1.22, 1.26))
    t = span("intro")
    shot("front", t[0], t[1], zoom=(1.0, 1.0))
    t = span("insight")
    mid = out_time("front", (ISL[4][1] + ISL[5][0]) / 2)          # пауза перед «здоровье человека»
    shot("photo", t[0], mid, src="operating_room", kb=(1.04, 1.10), focus=(0.62, 0.42))
    shot("scene", mid, t[1], scene="timeline")
    t = span("patients")
    shot("side", t[0], t[1], src_a=clip("patients")["a"])
    t = span("noknow")
    shot("front", t[0], t[1], zoom=(1.36, 1.36))
    t = span("treat")
    shot("scene", t[0], t[1], scene="course")
    t = span("nocure")
    shot("front", t[0], t[1], zoom=(1.58, 1.70))
    t = span("realize")
    shot("side", t[0], t[1], src_a=clip("realize")["a"])
    t = span("best")
    shot("front", t[0], t[1], zoom=(1.70, 1.70))
    t = span("numbers")
    shot("front", t[0], t[1], zoom=(1.0, 1.0))
    t = span("who")
    shot("front", t[0], t[1], zoom=(1.26, 1.30))
    t = span("f1", "f4")
    shot("scene", t[0], t[1], scene="factors")
    t = span("think")
    shot("front", t[0], t[1], zoom=(1.62, 1.62))
    t = span("ten", "others")
    shot("scene", t[0], t[1], scene="tenpercent")
    t = span("cond")
    shot("front", t[0], t[1], zoom=(1.30, 1.38))
    t = span("mission")
    shot("front", t[0], t[1], zoom=(1.66, 1.66))
    t = span("share")
    shot("photo", t[0], t[1], src="lecture_heart", kb=(1.03, 1.09), focus=(0.47, 0.40))
    t = span("cta")
    shot("front", t[0], TOTAL - END_CARD + 0.6, zoom=(1.0, 1.06))
    shot("endcard", TOTAL - END_CARD, TOTAL)


build_shots()


def export():
    data = dict(fps=[FPS_NUM, FPS_DEN], total=TOTAL, speech_end=SPEECH_END, clips=CLIPS, shots=SHOTS,
                islands=ISL)
    json.dump(data, open(os.path.join(ROOT, "build", "edl.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    export()
    print("Звуковые клипы:")
    for c in CLIPS:
        print(f"  {c['out']:7.2f}  {c['src']:5s} {c['a']:7.2f}–{c['b']:7.2f} ({c['b'] - c['a']:5.2f} с)  {c['tag']}")
    print("Планы:")
    for s in SHOTS:
        extra = s.get("zoom") or s.get("scene") or s.get("src") or ""
        print(f"  {s['t0']:7.2f}–{s['t1']:7.2f} ({s['t1'] - s['t0']:5.2f} с)  {s['kind']:7s} {extra}")
    print(f"Итого: речь до {SPEECH_END:.2f} с, ролик {TOTAL:.2f} с")
