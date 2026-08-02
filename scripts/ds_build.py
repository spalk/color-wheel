#!/usr/bin/env python3
"""Каталог DS для круга: измеренный CIELab -> угол, насыщенность, hex.

Вход:
  ../ds-colormap.json  — снято с официальной карты danielsmith.com/color-map/
                         (в id элементов лежат a*, b*, L*; в имени файла — артикул)
  ds-props.json        — точные имена и свойства из ds_props.py

Почему через Lab, а не через hex, как раньше: масстоны насыщенных красок
не влезают в sRGB, и хрома, посчитанная из hex, у них занижена — то есть
ровно у тех, чьё место на ободе и есть смысл круга. Lab -> OKLab считается
напрямую, без округления до гаммы; sRGB нужен только для заливки точки.

Шкала углов (ANCHORS) — та же, что была: художественный круг, жёлтый сверху.
Насыщенность нормируется на ЗАМОРОЖЕННЫЕ референсы (REFS): максимум хромы
по всему каталогу DS в каждой зоне. Числа зафиксированы, поэтому добавление
красок ничего не пересчитывает.

Запуск: python3 ds_build.py            — отчёт и проверки
        python3 ds_build.py --json     — каталог в ds-catalog.json
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COLORMAP = os.path.join(ROOT, "ds-colormap.json")
PROPS = os.path.join(HERE, "ds-props.json")
OUT = os.path.join(HERE, "ds-catalog.json")

# Карта DS даёт Lab в D50 (стандарт полиграфии). OKLab определён в D65.
LAB_WHITE = "D50"

# --- OKLCh-тон -> угол художественного круга (жёлтый вверху, по часовой) ---
# Якоря выставлены по РЕАЛЬНЫМ краскам, а не по идеальным цветам монитора.
ANCHORS = [(98.6, 0), (72.4, 45), (44.5, 90), (28.4, 120), (6.0, 150),
           (340.0, 175), (310.2, 195), (265.3, 240), (232.0, 262),
           (181.5, 285), (137.3, 315), (119.3, 335), (98.6, 360)]

# Густота слоя для отрисовочного hex: карта DS снята с нормальной заливки,
# на круге краска должна читаться в рабочую силу. 1.0 = как измерено.
MASSTONE = 1.6

# Замороженные референсы хромы по зонам круга (шаг 30°), посчитаны один раз
# по всему каталогу DS. Между узлами — линейная интерполяция.
# Пересчитывать НЕ надо: добавление красок на шкалу больше не влияет.
# Обновить осознанно можно через --refs.
REFS = None   # заполняется ниже; None => посчитать из каталога и напечатать

# ---------- цветовая математика ----------
WHITES = {"D50": (0.96422, 1.00000, 0.82521),
          "D65": (0.95047, 1.00000, 1.08883)}

# Bradford D50 -> D65 (CSS Color 4)
BRADFORD_50_65 = [
    [0.9554734527042182, -0.023098536874261423, 0.0632593086610217],
    [-0.028369706963208136, 1.0099954580058226, 0.021041398966943008],
    [0.012314001688319899, -0.020507696433477912, 1.3303659366080753],
]
XYZ_TO_LRGB = [
    [3.2409699419045226, -1.537383177570094, -0.4986107602930034],
    [-0.9692436362808796, 1.8759675015077202, 0.04155505740717559],
    [0.05563007969699366, -0.20397695888897652, 1.0569715142428786],
]
LRGB_TO_XYZ = [
    [0.41239079926595934, 0.357584339383878, 0.1804807884018343],
    [0.21263900587151027, 0.715168678767756, 0.07219231536073371],
    [0.01933081871559182, 0.11919477979462598, 0.9505321522496607],
]


def mul(m, v):
    return [sum(mi[j] * v[j] for j in range(3)) for mi in m]


def cbrt(x):
    return math.copysign(abs(x) ** (1 / 3), x)


def lab_to_xyz(L, a, b, white=LAB_WHITE):
    eps, kappa = 216 / 24389, 24389 / 27
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    f = lambda t: t ** 3 if t ** 3 > eps else (116 * t - 16) / kappa
    xr, zr = f(fx), f(fz)
    yr = ((L + 16) / 116) ** 3 if L > kappa * eps else L / kappa
    Xn, Yn, Zn = WHITES[white]
    return [xr * Xn, yr * Yn, zr * Zn]


def lab_to_lrgb(L, a, b):
    """Lab -> линейный sRGB. Значения могут выходить за 0..1 — так и надо:
    вне гаммы мы ничего не поджимаем, иначе потеряем хрому."""
    xyz = lab_to_xyz(L, a, b)
    if LAB_WHITE == "D50":
        xyz = mul(BRADFORD_50_65, xyz)
    return mul(XYZ_TO_LRGB, xyz)


def lrgb_to_oklch(rgb):
    r, g, b = rgb
    l = cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def oklch_to_lrgb(L, C, H):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s]


def in_gamut(rgb, tol=1e-4):
    return all(-tol <= v <= 1 + tol for v in rgb)


def oklch_to_hex(L, C, H, strength=1.0):
    """В sRGB с поджатием ТОЛЬКО хромы: тон и светлота сохраняются.

    strength — имитация более густого слоя. Карта DS снята с нормальной
    заливки, а на круге краска должна читаться в рабочую силу, поэтому
    отражение возводится в степень: физически это тот же пигмент, положенный
    гуще. Одно правило на весь каталог, свои и чужие краски в равных условиях.
    """
    lo, hi = 0.0, C
    if not in_gamut(oklch_to_lrgb(L, C, H)):
        for _ in range(30):
            mid = (lo + hi) / 2
            if in_gamut(oklch_to_lrgb(L, mid, H)):
                lo = mid
            else:
                hi = mid
        C = lo
    rgb = [max(0.0, min(1.0, v)) for v in oklch_to_lrgb(L, C, H)]
    if strength != 1.0:
        rgb = [v ** strength for v in rgb]
    enc = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return "#" + "".join(f"{max(0, min(255, round(enc(v) * 255))):02X}" for v in rgb)


def okhue_to_wheel(h):
    """OKLCh-тон -> угол художественного круга по ANCHORS."""
    h %= 360
    for i in range(len(ANCHORS) - 1):
        h0, r0 = ANCHORS[i]
        h1, r1 = ANCHORS[i + 1]
        span = (h0 - h1) % 360 or 360
        d = (h0 - h) % 360
        if d <= span + 1e-9:
            return (r0 + (r1 - r0) * (d / span)) % 360
    return 0.0


def ref_at(angle, refs):
    """Линейная интерполяция замороженного референса между узлами (шаг 30°)."""
    x = (angle % 360) / 30.0
    i = int(x) % 12
    t = x - int(x)
    return refs[i] * (1 - t) + refs[(i + 1) % 12] * t


# ---------- сборка ----------
def load():
    rows = json.load(open(COLORMAP))
    props = json.load(open(PROPS)) if os.path.exists(PROPS) else {}
    by_name = {squash(v["n"]): v for v in props.values()}
    out, seen = [], set()
    for r in rows:
        if r.get("n1") is None:
            continue
        fn = r["src"].rsplit("/", 1)[-1]
        m = re.search(r"(284\d{6})", fn)
        sku = m.group(1) if m else ""
        # у 17 файлов старое имя без артикула — цепляемся к свойствам по имени
        p = props.get(sku) or by_name.get(squash(name_from_file(fn)), {})
        name = p.get("n") or name_from_file(fn)
        sku = sku or p.get("sku", "")
        key = sku or name
        if key in seen:
            continue
        seen.add(key)
        La, aa, bb = float(r["n3"]), float(r["n1"]), float(r["n2"])
        Lo, Co, Ho = lrgb_to_oklch(lab_to_lrgb(La, aa, bb))
        out.append(dict(sku=sku, n=name, code=sku[-3:] if sku else "",
                        pig=p.get("pig", ""), series=p.get("series"),
                        transparency=p.get("transparency"),
                        granulating=p.get("granulating"),
                        lightfast=p.get("lightfast"),
                        Lab=[La, aa, bb], C_lab=math.hypot(aa, bb),
                        okL=Lo, okC=Co, okH=Ho,
                        a=round(okhue_to_wheel(Ho), 1), okC_raw=Co,
                        file=fn))
    return out


def squash(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def name_from_file(fn):
    s = re.sub(r"-\d+x\d+$", "", fn.rsplit(".", 1)[0])
    s = re.sub(r"^\d+(?:[._]\d+)?[-_]", "", s)
    s = re.sub(r"[-_]?(WC[-_]?Swatch[-_]?Thumb|WC)$", "", s, flags=re.I)
    s = re.sub(r"[-_](284\d{6})$", "", s)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return re.sub(r"[-_]+", " ", s).strip()


def compute_refs(cat):
    """Максимум OKLCh-хромы по всему каталогу в каждой зоне (узлы через 30°)."""
    refs = []
    for k in range(12):
        c = k * 30
        zone = [p for p in cat if abs((p["a"] - c + 180) % 360 - 180) <= 30]
        refs.append(round(max((p["okC"] for p in zone), default=0.0), 4))
    return refs


def main():
    cat = load()
    refs = REFS or compute_refs(cat)
    for p in cat:
        p["c"] = round(min(1.0, p["okC"] / ref_at(p["a"], refs)), 2)
        p["hex_wash"] = oklch_to_hex(p["okL"], p["okC"], p["okH"])
        p["hex"] = oklch_to_hex(p["okL"], p["okC"], p["okH"], MASSTONE)

    if "--json" in sys.argv:
        json.dump({"refs": refs, "colors": cat}, open(OUT, "w"),
                  ensure_ascii=False, indent=1)
        print(f"записано {len(cat)} красок -> {OUT}", file=sys.stderr)
        return

    print("REFS =", refs)
    print(f"\nкрасок в каталоге: {len(cat)}   "
          f"без артикула: {sum(1 for p in cat if not p['sku'])}")
    print(f"\n{'краска':32}{'a':>7}{'c':>6}  hex      L*  a*     b*")
    for p in sorted(cat, key=lambda p: p["a"]):
        L, A, B = p["Lab"]
        print(f"{p['n'][:32]:32}{p['a']:7.1f}{p['c']:6.2f}  {p['hex']}  "
              f"{L:3.0f} {A:6.2f} {B:6.2f}")


if __name__ == "__main__":
    main()
