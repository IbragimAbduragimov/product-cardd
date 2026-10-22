"""Пословные таймкоды из распознавания GigaAM (символьные метки → слова)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def words(name):
    d = json.load(open(f"{ROOT}/build/asr.json"))
    out = []
    for seg in d[name]:
        cur = None
        for tk, t in seg["toks"]:
            if tk.strip() == "":
                if cur:
                    out.append(cur)
                cur = None
                continue
            if tk.startswith("▁") or tk.startswith(" "):
                if cur:
                    out.append(cur)
                cur = dict(w=tk.strip("▁ "), s=t, e=t + 0.08)
            elif cur is None:
                cur = dict(w=tk, s=t, e=t + 0.08)
            else:
                cur["w"] += tk
                cur["e"] = t + 0.08
        if cur:
            out.append(cur)
    return out


if __name__ == "__main__":
    for name in sys.argv[1:]:
        ws = words(name)
        json.dump(ws, open(f"{ROOT}/build/words_{name}.json", "w"), ensure_ascii=False, indent=0)
        line = []
        for i, w in enumerate(ws):
            gap = w["s"] - ws[i - 1]["e"] if i else w["s"]
            if gap > 0.45:
                line.append(f"\n   ⏸{gap:.2f}s  ")
            line.append(f"{w['w']}@{w['s']:.2f}")
        print(f"== {name}: {len(ws)} слов", " ".join(line))
