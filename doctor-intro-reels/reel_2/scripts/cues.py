"""Привязка к словам: субтитры и точки анимации графики на выходном таймлайне."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edl import CLIPS, ROOT, SHOTS, span  # noqa: E402

WORDS = {"front": json.load(open(f"{ROOT}/build/words_IMG_3483.json")),
         "side": json.load(open(f"{ROOT}/build/words_IMG_7785.json"))}

# Субтитры по фразам: (текст на экране, число распознанных слов). *…* — умеренный акцент.
SUBS = {
    "hook": [("Пришло время рассказать,", 3), ("для чего создан мой блог.", 5)],
    "intro": [("Как вы уже знаете,", 4), ("я Абдурагим Магомедрасулович,", 4), ("врач-ординатор,", 2),
              ("сердечно-сосудистый хирург.", 3)],
    "insight": [("Встречаясь с различными историями заболеваний,", 5), ("всё чаще убеждаюсь:", 3),
                ("здоровье человека во многом определяется тем,", 6), ("что он делал *задолго до болезни*.", 6)],
    "patients": [("Я не раз наблюдал,", 4), ("с каким сожалением", 3), ("и искренним недоумением", 3),
                 ("пациенты воспринимают", 2), ("рекомендации по профилактике.", 3),
                 ("Они просто не располагали", 4), ("этими знаниями ранее.", 3)],
    "treat": [("Теперь же остаётся только лечить,", 5), ("а порой лишь сдерживать", 4), ("развитие болезни,", 2),
              ("чтобы сократить число обострений.", 4)],
    "nocure": [("О полном излечении, увы,", 4), ("речи уже не идёт.", 4)],
    "realize": [("Осознав это, я понял,", 4), ("что обязан делиться знаниями", 4),
                ("о том, как предотвратить болезни,", 5), ("и создал эту страницу.", 4)],
    "best": [("Ведь лучшее лечение —", 3), ("это *профилактика*.", 2)],
    "numbers": [("Давайте обратимся", 2), ("к конкретным цифрам и статистике.", 5)],
    "who": [("По данным Всемирной организации", 4), ("здравоохранения,", 1), ("здоровье человека зависит", 3),
            ("от следующих факторов:", 3)],
    "f1": [("образ жизни,", 2)],
    "f2": [("наследственность,", 1)],
    "f3": [("окружающая среда", 2)],
    "f4": [("и здравоохранение.", 2)],
    "think": [("Только вдумайтесь в эти цифры.", 5)],
    "ten": [("Медицина вносит", 2), ("всего лишь *10%* вклада", 5), ("в состояние вашего организма.", 4)],
    "others": [("Отсюда следует, что решающую роль", 5), ("в вопросах здоровья", 3),
               ("играют *другие факторы*.", 3)],
    "cond": [("Однако их положительный эффект", 4), ("достижим исключительно", 2),
             ("при наличии соответствующих знаний", 4), ("и готовности следовать им.", 4)],
    "mission": [("Именно этим я как раз", 5), ("и буду заниматься —", 3)],
    "share": [("делиться профессиональными знаниями", 3), ("о мерах предупреждения болезней.", 4)],
    "cta": [("Поэтому ставьте лайки,", 3), ("подписывайтесь", 1), ("и пересылайте это видео всем,", 5),
            ("кому желаете здоровое будущее.", 4)],
}


def clip_words(c):
    return [dict(w=x["w"], t=c["out"] + (x["s"] - c["a"]), te=c["out"] + (x["e"] - c["a"]))
            for x in WORDS[c["src"]] if c["a"] <= x["s"] <= c["b"]]


def subtitle_events():
    events = []
    for c in CLIPS:
        ws = clip_words(c)
        chunks = SUBS[c["tag"]]
        n = sum(k for _, k in chunks)
        assert n == len(ws), f"{c['tag']}: в субтитрах {n} слов, распознано {len(ws)}: {[w['w'] for w in ws]}"
        i = 0
        for text, k in chunks:
            part = ws[i:i + k]
            events.append(dict(text=text, s=part[0]["t"] - 0.06, e=part[-1]["te"] + 0.32,
                               asr=" ".join(w["w"] for w in part), tag=c["tag"]))
            i += k
    for a, b in zip(events, events[1:]):
        if a["e"] > b["s"] - 0.02 or b["s"] - a["e"] < 0.28:
            a["e"] = b["s"] - 0.02
    return events


def word_time(tag, word, nth=0, end=False):
    c = next(c for c in CLIPS if c["tag"] == tag)
    hits = [w for w in clip_words(c) if w["w"].startswith(word)]
    return hits[nth]["te" if end else "t"]


def scene_cues():
    def rel(scene, t):
        s = next(x for x in SHOTS if x.get("scene") == scene)
        return round(t - s["t0"], 3)

    def dur(scene):
        s = next(x for x in SHOTS if x.get("scene") == scene)
        return round(s["t1"] - s["t0"], 4)

    end = next(x for x in SHOTS if x["kind"] == "endcard")
    return {
        "endcard": dict(dur=round(end["t1"] - end["t0"], 4)),
        "timeline": dict(dur=dur("timeline"),
                         title=rel("timeline", word_time("insight", "здоровье")),
                         draw=rel("timeline", word_time("insight", "определяется")),
                         did=rel("timeline", word_time("insight", "делал")),
                         before=rel("timeline", word_time("insight", "задолго")),
                         disease=rel("timeline", word_time("insight", "болезни"))),
        "course": dict(dur=dur("course"),
                       title=rel("course", word_time("treat", "теперь")),
                       treat=rel("course", word_time("treat", "лечить")),
                       restrain=rel("course", word_time("treat", "сдерживать")),
                       reduce=rel("course", word_time("treat", "сократить")),
                       exac=rel("course", word_time("treat", "обострений"))),
        "factors": dict(dur=dur("factors"),
                        f1=rel("factors", word_time("f1", "образ")),
                        f2=rel("factors", word_time("f2", "наследственность")),
                        f3=rel("factors", word_time("f3", "окружающая")),
                        f4=rel("factors", word_time("f4", "здравоохранение"))),
        "tenpercent": dict(dur=dur("tenpercent"),
                           med=rel("tenpercent", word_time("ten", "медицина")),
                           ten=rel("tenpercent", word_time("ten", "десять")),
                           contrib=rel("tenpercent", word_time("ten", "вклада")),
                           org=rel("tenpercent", word_time("ten", "организма")),
                           follows=rel("tenpercent", word_time("others", "отсюда")),
                           decisive=rel("tenpercent", word_time("others", "решающую")),
                           other=rel("tenpercent", word_time("others", "другие"))),
    }


def overlay_cues():
    """Моменты появления титров и подписей поверх видео (выходное время)."""
    return dict(
        handle=word_time("realize", "создал") - 0.1,
        best=word_time("best", "лучшее") - 0.05,
        best_word=word_time("best", "профилактика") - 0.1,
        cond_label=word_time("cond", "исключительно"),
        cond_know=word_time("cond", "знаний"),
        cond_ready=word_time("cond", "готовности"),
        share=word_time("share", "делиться"),
        # короткие подписи внизу — только на ключевых моментах (полных субтитров нет)
        cap_hook=(word_time("hook", "пришло") + 0.15, word_time("hook", "блог", end=True) + 0.25),
        cap_nocure=(word_time("nocure", "о") - 0.05, word_time("nocure", "идет", end=True) + 0.35),
        cap_cta=(word_time("cta", "пересылайте") - 0.05, word_time("cta", "будущее", end=True) + 0.4),
    )


def plain(text):
    return re.sub(r"\*", "", text)


if __name__ == "__main__":
    ev = subtitle_events()
    for e in ev:
        print(f"{e['s']:7.2f} → {e['e']:7.2f}  {plain(e['text'])}\n{'':19}[{e['asr']}]")
    sc = scene_cues()
    oc = overlay_cues()
    json.dump(dict(subs=ev, scenes=sc, overlay=oc), open(f"{ROOT}/build/cues.json", "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(sc, ensure_ascii=False, indent=1))
    print({k: (tuple(round(x, 2) for x in v) if isinstance(v, (tuple, list)) else round(v, 2)) for k, v in oc.items()})
