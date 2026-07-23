#!/usr/bin/env python3
"""Цвета 12 секторов теоретического круга: угол колеса -> OKLh -> sRGB,
по той же якорной шкале, что и пигменты (analyze2.ANCHORS обратно)."""
import math

# (OKLh, wheel_angle) — как в analyze2.py
ANCHORS = [(98.6, 0), (72.4, 45), (44.5, 90), (28.4, 120), (6.0, 150),
           (340.0, 175), (310.2, 195), (265.3, 240), (232.0, 262),
           (181.5, 285), (137.3, 315), (119.3, 335), (98.6, 360)]

def lerp_hue(h0, h1, t):
    d = ((h1 - h0 + 180) % 360) - 180      # кратчайший путь
    return (h0 + d * t) % 360

def wheel_to_okhue(a):
    a %= 360
    for i in range(len(ANCHORS) - 1):
        h0, w0 = ANCHORS[i]; h1, w1 = ANCHORS[i + 1]
        if w0 <= a <= w1:
            t = (a - w0) / (w1 - w0) if w1 > w0 else 0
            return lerp_hue(h0, h1, t)
    return ANCHORS[0][0]

def lin_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1/2.4)) - 0.055

def oklch_to_rgb(L, C, H):
    a = C * math.cos(math.radians(H)); b = C * math.sin(math.radians(H))
    l = (L + 0.3963377774*a + 0.2158037573*b) ** 3
    m = (L - 0.1055613458*a - 0.0638541728*b) ** 3
    s = (L - 0.0894841775*a - 1.2914855480*b) ** 3
    r = +4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    bb= -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return r, g, bb

def in_gamut(L, C, H):
    return all(-0.001 <= v <= 1.001 for v in oklch_to_rgb(L, C, H))

def oklch_to_hex(L, C, H):
    # ужимаем хрому под sRGB
    while C > 0 and not in_gamut(L, C, H):
        C -= 0.005
    r, g, b = oklch_to_rgb(L, C, H)
    return "#{:02X}{:02X}{:02X}".format(
        *[max(0, min(255, round(lin_to_srgb(v) * 255))) for v in (r, g, b)])

def cusp(H):
    """(L, C) самой хроматичной точки для этого тона."""
    bestL, bestC = 0.6, 0
    for i in range(30, 96):
        L = i / 100
        C = 0.0
        while in_gamut(L, C + 0.005, H): C += 0.005
        if C > bestC: bestC, bestL = C, L
    return bestL, bestC

# 12 секторов, центры на кратных 30°. Светлота своя у каждого тона (по cusp).
# Кольца от обода к центру: rf — внешняя доля радиуса, cf — доля хромы,
# lf — осветление к бумаге (0 = как есть). Обод: cf=0.72, lf=0 — идентичен
# исходному одиночному кругу, менять его не хотим.
RINGS = [("обод", 1.00, 0.72, 0.00),
         ("средн", 0.70, 0.45, 0.28),
         ("глухое", 0.50, 0.24, 0.50)]
print("const THEORY_RINGS = [")
for name, rf, cf, lf in RINGS:
    hexes = []
    for k in range(12):
        H = wheel_to_okhue(k * 30)
        Lc, Cc = cusp(H)
        L = Lc * 0.5 + 0.62 * 0.5
        Lm = L * (1 - lf) + 0.80 * lf  # к центру светлее, к бумаге
        hexes.append(oklch_to_hex(Lm, Cc * cf, H))
    row = ", ".join(f'"{h}"' for h in hexes)
    print(f'  {{ rf:{rf:.2f}, hex:[{row}] }},   // {name}')
print("];")
# a=0..330 по 30° соответствует индексам 0..11 в hex[]

# 6 подписей главных тонов на реальных позициях
LBL = [(0,"жёлтый"),(60,"оранжевый"),(120,"красный"),
       (180,"фиолетовый"),(240,"синий"),(300,"зелёный")]
print("\nconst THEORY_LABELS = [")
for a, name in LBL:
    print(f'  {{ a:{a}, t:"{name}" }},')
print("];")

# самопроверка: комплемент = напротив?
print("\n# проверка комплементов (тон vs тон+180):")
for a, name in LBL:
    opp = next(n for aa,n in LBL if aa==(a+180)%360)
    print(f"#   {name:11}({a:3}) <-> {opp}({(a+180)%360})")
