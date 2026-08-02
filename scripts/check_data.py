#!/usr/bin/env python3
"""Проверка данных страницы без браузера.

JS-рантайма в системе нет, а страница молча ничего не теряет только
потому, что в ней есть свой валидатор. Этот скрипт делает то же самое
из командной строки: вытаскивает из catalog.js и data.js всё, на что
можно сослаться, и проверяет, что ссылки ведут в существующие краски.

Запуск: python3 check_data.py   (код возврата 1, если что-то не сходится)
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def main():
    cat, data = read("catalog.js"), read("data.js")

    ds = set(re.findall(r'^\s*"(\d{9})":', cat, re.M))
    authors = [(m.group(1), re.findall(r'"(\d{9})"', m.group(2)))
               for m in re.finditer(r'name:"([^"]+)".*?colors:\[([^\]]*)\]', cat)]

    # MY и CANDIDATES: имя -> артикул
    def entries(block):
        out = []
        for m in re.finditer(r'\{\s*sku:"(\d{9})",\s*n:"([^"]+)"', block):
            out.append((m.group(2), m.group(1)))
        return out

    my_block = data[data.index("const MY"):data.index("const ACTIVE")]
    cand_block = data[data.index("const CANDIDATES"):data.index("const PAIRS")]
    my = entries(my_block)
    cands = entries(cand_block)
    sku_of = {n: s for n, s in my + cands}
    mine = {s for _, s in my}

    active = re.findall(r'^\s*"([^"]+)",\s*$',
                        data[data.index("const ACTIVE"):data.index("/* КАНДИДАТЫ")],
                        re.M)
    pairs_block = data[data.index("const PAIRS"):data.index("const RECIPES")]
    pair_names = re.findall(r'\["([^"]+)",\s*"([^"]+)"', pairs_block)
    rec_block = data[data.index("const RECIPES"):data.index("const THEORY_RINGS")]
    rec_mix = [re.findall(r'"([^"]+)"', m.group(1))
               for m in re.finditer(r'mix:\[([^\]]*)\]', rec_block)]
    sub_names = [re.findall(r'"([^"]+)"', m.group(1))
                 for m in re.finditer(r'sub:\[([^\]]*)\]', cand_block)]

    bad = []

    def check(n, where):
        s = sku_of.get(n)
        if s is None:
            bad.append(f'{where}: имени «{n}» нет ни в MY, ни в CANDIDATES')
        elif s not in mine:
            bad.append(f'{where}: «{n}» — кандидат, а нужна своя краска')

    for n in active:
        check(n, "ACTIVE")
    for a, b in pair_names:
        check(a, "PAIRS"); check(b, "PAIRS")
    for mix in rec_mix:
        for n in mix:
            check(n, "RECIPES")
    for sub in sub_names:
        for n in sub:
            check(n, "CANDIDATES.sub")

    for n, s in my + cands:
        if s not in ds:
            bad.append(f'«{n}»: артикула {s} нет в catalog.js')
    for name, cols in authors:
        for s in cols:
            if s not in ds:
                bad.append(f'{name}: артикула {s} нет в catalog.js')

    dup = {n for n, _ in my} & {n for n, _ in cands}
    for n in dup:
        bad.append(f'«{n}» числится и в MY, и в CANDIDATES')

    nodata = sorted(re.findall(r'^\s*"(\d{9})": \{n:"([^"]+)"[^}]*nodata:true', cat, re.M))
    print(f"каталог: {len(ds)} красок   ·   авторов: {len(authors)}")
    print(f"MY: {len(my)}   ACTIVE: {len(active)}   CANDIDATES: {len(cands)}   "
          f"PAIRS: {len(pair_names)}   замесов: {len(rec_mix)}")
    for name, cols in authors:
        print(f"  {name:24} {len(cols)} красок, "
              f"общих с тобой: {len(set(cols) & mine)}")
    if nodata:
        print("без измерений: " + ", ".join(f"{n} ({s[-3:]})" for s, n in nodata))
    print("\nПРОБЛЕМЫ: " + ("\n  " + "\n  ".join(bad) if bad else "нет"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
