#!/usr/bin/env python3
"""Сборка catalog.js — сгенерированной части данных страницы.

Складывает вместе:
  ds-catalog.json      геометрия и hex из измеренного Lab (ds_build.py)
  ds-props.json        официальные имена и свойства (ds_props.py)
  ../authors/*/palette.json   наборы художников с дот-карт
  ../data.js           какие краски вообще нужны (MY + CANDIDATES)

В catalog.js попадают только те краски, на которые кто-то ссылается,
иначе файл раздувается всем ассортиментом DS без пользы.

Запуск: python3 build_catalog.py   → ../catalog.js
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

GRAN = {"Granulating": 1, "Non-Granulating": 0}


def load_catalog():
    data = json.load(open(os.path.join(HERE, "ds-catalog.json")))
    return {c["sku"]: c for c in data["colors"] if c["sku"]}


def load_props():
    return json.load(open(os.path.join(HERE, "ds-props.json")))


def load_authors():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "authors", "*", "palette.json"))):
        d = json.load(open(p))
        d["dir"] = "authors/" + os.path.basename(os.path.dirname(p))
        out.append(d)
    return out


def skus_from_data_js():
    """Какие артикулы упоминает рукописный data.js."""
    src = open(os.path.join(ROOT, "data.js")).read()
    return set(re.findall(r'sku:\s*"(\d{9})"', src))


def js(v):
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return "[" + ",".join(js(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(f"{k}:{js(x)}" for k, x in v.items()) + "}"
    raise TypeError(v)


def main():
    cat, props, authors = load_catalog(), load_props(), load_authors()

    need = skus_from_data_js()
    for a in authors:
        need |= {c["sku"] for c in a["colors"] if c.get("sku")}

    missing = sorted(s for s in need if s not in cat)
    lines = []
    for sku in sorted(need):
        c = cat.get(sku)
        p = props.get(sku, {})
        if not c:                       # нет измерений (линия Luminescent, эксклюзивы)
            e = {"n": p.get("n", "?"), "pig": p.get("pig", ""), "nodata": True}
        else:
            e = {"n": c["n"], "pig": c["pig"] or "натуральный минерал",
                 "a": c["a"], "c": c["c"], "hex": c["hex"]}
            if p.get("series"):
                e["ser"] = p["series"]
            if p.get("granulating") in GRAN:
                e["gran"] = GRAN[p["granulating"]]
            if p.get("transparency"):
                e["tr"] = p["transparency"]
        lines.append(f'  "{sku}": {js(e)},')

    au = []
    for a in authors:
        e = {"id": a["id"], "name": a["name"], "dir": a["dir"],
             "palette": a["palette"],
             "card": a["source"]["file"], "rev": a["source"]["rev"],
             "example": a["example"]["file"],
             "links": a.get("links", {}), "quote": a["quote"], "bio": a["bio"],
             "colors": [c["sku"] for c in a["colors"] if c.get("sku")]}
        if a.get("alias"):
            e["alias"] = a["alias"]
        au.append("  " + js(e) + ",")

    out = ["/* СГЕНЕРИРОВАНО scripts/build_catalog.py — руками не править.",
           "   Источники: карта CIELab danielsmith.com/color-map, справочник пигментов DS,",
           "   дот-карты художников из authors/*/palette.json.",
           "   Геометрия (a, c) и hex посчитаны из измеренного Lab: см. scripts/ds_build.py.",
           f"   Красок: {len(need)}   ·   наборов художников: {len(authors)} */",
           "", "const DS = {", *lines, "};", "",
           "/* Наборы художников. Источник — дот-карты Daniel Smith:",
           "   https://danielsmith.com/brand-ambassadors/ */",
           "const AUTHORS = [", *au, "];", ""]
    path = os.path.join(ROOT, "catalog.js")
    open(path, "w").write("\n".join(out))
    print(f"{path}: {len(need)} красок, {len(authors)} авторов, "
          f"{os.path.getsize(path)//1024} KB", file=sys.stderr)
    if missing:
        print("без измерений: " + ", ".join(
            f"{s} {props.get(s,{}).get('n','?')}" for s in missing), file=sys.stderr)


if __name__ == "__main__":
    main()
