#!/usr/bin/env python3
"""hex -> OKLCh -> угол на художественном (RYB) круге + относительная хрома."""
import math

# ---------- sRGB <-> OKLab ----------
def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def lin_to_srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

def hex_to_oklch(h):
    h = h.lstrip('#')
    r, g, b = (srgb_to_lin(int(h[i:i+2], 16)) for i in (0, 2, 4))
    l = (0.4122214708*r + 0.5363325363*g + 0.0514459929*b) ** (1/3)
    m = (0.2119034982*r + 0.6806995451*g + 0.1073969566*b) ** (1/3)
    s = (0.0883024619*r + 0.2817188376*g + 0.6299787005*b) ** (1/3)
    L = 0.2104542553*l + 0.7936177850*m - 0.0040720468*s
    a = 1.9779984951*l - 2.4285922050*m + 0.4505937099*s
    bb = 0.0259040371*l + 0.7827717662*m - 0.8086757660*s
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return L, C, H

def oklch_in_gamut(L, C, H):
    a = C * math.cos(math.radians(H)); bb = C * math.sin(math.radians(H))
    l = (L + 0.3963377774*a + 0.2158037573*bb) ** 3
    m = (L - 0.1055613458*a - 0.0638541728*bb) ** 3
    s = (L - 0.0894841775*a - 1.2914855480*bb) ** 3
    r = +4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    b = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    return all(-0.0001 <= v <= 1.0001 for v in (r, g, b))

def max_chroma(L, H):
    """Максимальная хрома, представимая в sRGB при данных L и H."""
    lo, hi = 0.0, 0.5
    for _ in range(40):
        mid = (lo + hi) / 2
        if oklch_in_gamut(L, mid, H): lo = mid
        else: hi = mid
    return lo

# ---------- RGB-тон -> угол художественного круга ----------
# Якоря: жёлтый наверху (0), по часовой через оранжевый/красный/фиолетовый/синий/зелёный.
ANCHORS = [(60, 0), (30, 60), (0, 120), (300, 165), (270, 195),
           (240, 240), (180, 275), (120, 300), (90, 330), (60, 360)]

def rgbhue_to_ryb(h):
    h %= 360
    for i in range(len(ANCHORS) - 1):
        h0, r0 = ANCHORS[i]; h1, r1 = ANCHORS[i + 1]
        span = (h0 - h1) % 360 or 360
        d = (h0 - h) % 360
        if d <= span + 1e-9:
            return (r0 + (r1 - r0) * (d / span)) % 360
    return 0.0

def hex_to_rgbhue(hx):
    hx = hx.lstrip('#')
    r, g, b = (int(hx[i:i+2], 16) / 255 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn: return None
    if mx == r: h = 60 * (((g - b) / (mx - mn)) % 6)
    elif mx == g: h = 60 * ((b - r) / (mx - mn) + 2)
    else: h = 60 * ((r - g) / (mx - mn) + 4)
    return h % 360

# ---------- данные ----------
# cur_a/cur_c/cur_hex = что стоит в palitra-krug.html сейчас (None = пигмента там нет)
# new_hex = мой предлагаемый масстон
P = [
 # имя,                      бренд, пигменты,           cur_a, cur_c, cur_hex,   new_hex
 ("Hansa Yellow Light 041",  "DS", "PY3",                350, .98, "#F2D22A", "#F3D62B"),
 ("Hansa Yellow Deep",       "MG", "PY97",              None,None, None,      "#F2A007"),
 ("New Gamboge 060",         "DS", "PY97 PY110",          15, .94, "#EFA61C", "#F0A81E"),
 ("Yellow Ochre",            "DS", "PY43",                32, .50, "#C79440", "#C68E3C"),
 ("Buff Titanium",           "DS", "PW6:1",             None,None, None,      "#D9CBB4"),
 ("Burnt Sienna",            "MG", "PBr7",                58, .52, "#A75931", "#A9552D"),
 ("Sepia",                   "MG", "PBk6 PBr7",           48, .20, "#584232", "#4A3A2E"),
 ("Pyrrol Scarlet 085",      "DS", "PR255",              108, 1.0, "#D6322A", "#E03A20"),
 ("Pyrrol Red",              "MG", "PR254",             None,None, None,      "#D2231E"),
 ("Quinacridone Coral",      "DS", "PR209",              122, .86, "#D2475D", "#DE4E63"),
 ("Quinacridone Rose 092",   "DS", "PV19",               145, .94, "#C22A6B", "#C6255F"),
 ("Moonglow",                "DS", "PR177 PB29 PG18",    180, .30, "#6A5977", "#6A5977"),
 ("Sodalite Genuine",        "DS", "genuine",           None,None, None,      "#4A4E63"),
 ("French Ultramarine 034",  "DS", "PB29",               228, .86, "#2C4B9B", "#2B4A9B"),
 ("Payne's Gray",            "MG", "PB29 PBk9",          240, .24, "#495A6A", "#3E4C5A"),
 ("Phthalo Blue GS 077",     "DS", "PB15:3",             262, 1.0, "#0E5B8C", "#0B5C8F"),
 ("Cerulean Blue Chromium",  "DS", "PB36",               268, .68, "#2D85B0", "#1E7FA8"),
 ("Duochrome Aquamarine",    "DS", "PW20 PW6",           285, .48, "#7EB0A7", "#8FBDB4"),
 ("Viridian",                "DS", "PG18",               296, .68, "#2D8B6B", "#2A7F6B"),
 ("Undersea Green",          "DS", "PB29 PY150 PO48",    310, .44, "#4A6B4A", "#4C6642"),
 ("Green Apatite Genuine",   "DS", "genuine",            328, .50, "#6B7A3A", "#6E7A44"),
]

def fmt(v, w, p=0):
    return " " * w if v is None else f"{v:{w}.{p}f}"

def report():
  print(f"{'пигмент':26} {'бренд':5} | {'угол':^17} | {'насыщенность':^17} | hex")
  print(f"{'':26} {'':5} | {'было':>5}{'стало':>6}{'Δ':>6} | {'было':>5}{'стало':>6}{'Δ':>6} |")
  print("-" * 92)
  rows = []
  for n, b, pig, ca, cc, chex, nhex in P:
      L, C, H = hex_to_oklch(nhex)
      rgbh = hex_to_rgbhue(nhex)
      a = rgbhue_to_ryb(rgbh) if rgbh is not None else None
      cmax = max_chroma(L, H)
      c = C / cmax if cmax > 0 else 0
      da = None if ca is None else (a - ca + 180) % 360 - 180
      dc = None if cc is None else (c - cc) * 100
      flag = ""
      if da is not None and abs(da) >= 12: flag += " ⚠угол"
      if dc is not None and abs(dc) >= 15: flag += " ⚠нас."
      if ca is None: flag = " NEW"
      print(f"{n:26} {b:5} | {fmt(ca,5)}{a:6.0f}{fmt(da,6,0)} | "
            f"{fmt(None if cc is None else cc*100,5)}{c*100:6.0f}{fmt(dc,6,0)} | "
            f"{chex or '—':>8}→{nhex}{flag}")
      rows.append((n, b, pig, round(a), round(c, 3), nhex))

  print("\n--- готовые строки для data.js ---")
  for n, b, pig, a, c, hx in rows:
      print(f'  {{ n:"{n}", brand:"{b}", pig:"{pig}", hex:"{hx}", a:{a}, c:{c:.2f} }},')

if __name__ == "__main__":
    report()
