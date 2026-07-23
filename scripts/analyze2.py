#!/usr/bin/env python3
"""Финальный расчёт: угол по OKLCh-тону, радиус по хроме относительно
самой хроматичной краски коллекции в той же зоне тона."""
import math
from analyze import hex_to_oklch

# --- OKLCh-тон -> угол художественного круга (жёлтый вверху, по часовой) ---
# Якоря выставлены по РЕАЛЬНЫМ краскам, а не по идеальным цветам монитора:
# лимонный жёлтый = 0, пиррол ред = 120, ультрамарин = 240, виридиан ~285.
ANCHORS = [(98.6, 0), (72.4, 45), (44.5, 90), (28.4, 120), (6.0, 150),
           (340.0, 175), (310.2, 195), (265.3, 240), (232.0, 262),
           (181.5, 285), (137.3, 315), (119.3, 335), (98.6, 360)]

def okhue_to_ryb(h):
    h %= 360
    for i in range(len(ANCHORS) - 1):
        h0, r0 = ANCHORS[i]; h1, r1 = ANCHORS[i + 1]
        span = (h0 - h1) % 360 or 360
        d = (h0 - h) % 360
        if d <= span + 1e-9:
            return (r0 + (r1 - r0) * (d / span)) % 360
    return 0.0

# имя, бренд, пигменты, cur_a, cur_c, cur_hex, wash_hex (сильная заливка)
P = [
 ("Hansa Yellow Light 041", "DS", "PY3",             350, .98, "#F2D22A", "#F7DE3F"),
 ("Hansa Yellow Deep",      "MG", "PY97",           None,None, None,      "#F49B1E"),
 ("New Gamboge 060",        "DS", "PY97 PY110",       15, .94, "#EFA61C", "#F3AC2E"),
 ("Yellow Ochre",           "DS", "PY43",             32, .50, "#C79440", "#CD9A4E"),
 ("Buff Titanium",          "DS", "PW6:1",          None,None, None,      "#DCCDB6"),
 ("Burnt Sienna",           "MG", "PBr7",             58, .52, "#A75931", "#B05E33"),
 ("Sepia",                  "MG", "PBk6 PBr7",        48, .20, "#584232", "#5A4536"),
 ("Pyrrol Scarlet 085",     "DS", "PR255",           108, 1.0, "#D6322A", "#E24328"),
 ("Pyrrol Red",             "MG", "PR254",          None,None, None,      "#D8281F"),
 ("Quinacridone Coral",     "DS", "PR209",           122, .86, "#D2475D", "#E2596C"),
 ("Quinacridone Rose 092",  "DS", "PV19",            145, .94, "#C22A6B", "#CC2E68"),
 ("Moonglow",               "DS", "PR177 PB29 PG18", 180, .30, "#6A5977", "#71607E"),
 ("Sodalite Genuine",       "DS", "genuine",        None,None, None,      "#52566B"),
 ("French Ultramarine 034", "DS", "PB29",            228, .86, "#2C4B9B", "#3457AC"),
 ("Payne's Gray",           "MG", "PB29 PBk9",       240, .24, "#495A6A", "#46566A"),
 ("Phthalo Blue GS 077",    "DS", "PB15:3",          262, 1.0, "#0E5B8C", "#0F6EA6"),
 ("Cerulean Blue Chromium", "DS", "PB36",            268, .68, "#2D85B0", "#2589B4"),
 ("Duochrome Aquamarine",   "DS", "PW20 PW6",        285, .48, "#7EB0A7", "#93C0B7"),
 ("Viridian",               "DS", "PG18",            296, .68, "#2D8B6B", "#2E8A72"),
 ("Undersea Green",         "DS", "PB29 PY150 PO48", 310, .44, "#4A6B4A", "#52704A"),
 ("Green Apatite Genuine",  "DS", "genuine",         328, .50, "#6B7A3A", "#74804A"),
]

# --- считаем ---
data = []
for n, b, pig, ca, cc, chex, wash in P:
    L, C, H = hex_to_oklch(wash)
    data.append(dict(n=n, b=b, pig=pig, ca=ca, cc=cc, chex=chex, wash=wash,
                     L=L, C=C, H=H, a=okhue_to_ryb(H)))

WINDOW = 55.0   # зона тона, внутри которой ищем «самую яркую свою краску»
for d in data:
    ref = max(o['C'] for o in data
              if abs((o['a'] - d['a'] + 180) % 360 - 180) <= WINDOW)
    d['c'] = min(1.0, d['C'] / ref)

def fmt(v, w, p=0):
    return " " * w if v is None else f"{v:{w}.{p}f}"

print(f"{'пигмент':25}{'бренд':6}|{'угол: было стало  Δ':^22}|{'насыщ.: было стало  Δ':^23}| hex")
print("-" * 108)
for d in data:
    da = None if d['ca'] is None else (d['a'] - d['ca'] + 180) % 360 - 180
    dc = None if d['cc'] is None else (d['c'] - d['cc']) * 100
    flag = " NEW" if d['ca'] is None else ""
    if da is not None and abs(da) >= 12: flag += " ⚠угол"
    if dc is not None and abs(dc) >= 15: flag += " ⚠нас."
    print(f"{d['n']:25}{d['b']:6}|{fmt(d['ca'],9)}{d['a']:6.0f}{fmt(da,7,0)}|"
          f"{fmt(None if d['cc'] is None else d['cc']*100,10)}{d['c']*100:6.0f}{fmt(dc,7,0)}|"
          f" {d['chex'] or '   —    '}→{d['wash']}{flag}")

print("\n--- порядок по кругу (проверка последовательности) ---")
old = sorted([d for d in data if d['ca'] is not None], key=lambda d: d['ca'] % 360)
new = sorted([d for d in data if d['ca'] is not None], key=lambda d: d['a'])
print("было: " + " → ".join(d['n'].split()[0] for d in old))
print("стало:" + " → ".join(d['n'].split()[0] for d in new))
print("порядок совпадает" if [d['n'] for d in old] == [d['n'] for d in new]
      else "!!! ПОРЯДОК ИЗМЕНИЛСЯ")

print("\n--- строки для data.js ---")
for d in sorted(data, key=lambda d: d['a']):
    print(f'  {{ n:"{d["n"]}", brand:"{d["b"]}", pig:"{d["pig"]}", '
          f'hex:"{d["wash"]}", a:{d["a"]:.0f}, c:{d["c"]:.2f} }},')
