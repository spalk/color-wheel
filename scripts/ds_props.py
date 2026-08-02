#!/usr/bin/env python3
"""Точные имена и свойства красок DS из официального PDF.

Источник: https://danielsmith.com/wp-content/uploads/2021/05/DS-Watercolor-pigment-characteristics.pdf
(лежит рядом как ds-pigment-characteristics.pdf).

Запуск: python3 ds_props.py > ds-props.json
Даёт по артикулу: точное имя, серию, пигменты, светостойкость,
прозрачность, staining, гранулацию.
"""
import json, os, re, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "ds-pigment-characteristics.pdf")


def pdf_text(path):
    """Грубое извлечение текста: распаковать потоки, собрать Tj/TJ."""
    data = open(path, "rb").read()
    streams = []
    for m in re.finditer(rb"stream\r?\n", data):
        s = m.end()
        e = data.find(b"endstream", s)
        try:
            streams.append(zlib.decompress(data[s:e]))
        except Exception:
            pass
    blob = b"\n".join(streams).decode("latin1")
    chunks = []
    for m in re.finditer(r"\[(.*?)\]\s*TJ|\((.*?)\)\s*Tj", blob, re.S):
        if m.group(1) is not None:
            chunks.append("".join(re.findall(r"\((.*?)(?<!\\)\)", m.group(1))))
        else:
            chunks.append(m.group(2))
    return re.sub(r"\s+", " ", " ".join(chunks))


# Строки идут сплошным потоком, поэтому режем по артикулу и разбираем кусок:
# 284600010 Burnt Sienna Series 1 Burnt Sienna PBr 7 I Excellent 1 Non-Staining Granulating
# У genuine-минералов кодов пигментов нет вовсе.
ROW = re.compile(
    r"^(.+?)\s+Series\s+(\d)\s+"                             # имя, серия
    r"(.*?)\s*"                                              # пигменты словами + коды
    r"(I{1,3}|IV|V)\s+"                                      # светостойкость
    r"(Excellent|Very Good|Good|Fair|Poor)\s+"               # оценка
    r"(\d)\s+"                                               # прозрачность (код)
    r"((?:Non-|Low |Medium |High )?Staining)\s+"             # staining
    r"((?:Non-)?Granulating)\b"                              # гранулация
)
# PBr 7, PBk 9, PB 15:3 — вторая буква бывает строчной;
# PV 23(RS) и PR 170 F5RK — у части кодов есть уточняющий хвост.
CODES = re.compile(
    r"((?:P[A-Za-z]{1,2}\s*\d+(?::\d+)?"
    r"(?:\(\w+\))?"                          # PV 23(RS)
    r"(?:\s+(?=[A-Z0-9]*\d)[A-Z0-9]{2,6})?"  # PR 170 F5RK
    r"(?:\s*\|\s*)?)+)\s*$"
)


def split_pigments(s):
    """'Cerulean Blue - Chromium PB 36' -> ('Cerulean Blue - Chromium', 'PB36')"""
    m = CODES.search(s)
    if not m:
        return s.strip(), ""
    codes = " ".join(re.sub(r"\s+", "", p) for p in m.group(1).split("|"))
    return s[: m.start()].strip(), codes


def main():
    if not os.path.exists(PDF):
        sys.exit(f"нет файла {PDF}")
    text = pdf_text(PDF)
    unesc = lambda s: s.replace("\\(", "(").replace("\\)", ")").strip()

    # режем поток на куски «артикул … до следующего артикула»
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"\b(284\d{6})\b", text)]
    out = {}
    for i, (pos, sku) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        chunk = text[pos + len(sku): end].strip()
        m = ROW.match(chunk)
        if not m:
            continue                       # вторая страница — переводы имён, там нет свойств
        name, series, pigs, lf, lfw, transp, stain, gran = m.groups()
        words, codes = split_pigments(unesc(pigs))
        out[sku] = {
            "sku": sku,
            "n": unesc(name),
            "series": int(series),
            "pig": codes,
            "pig_words": words,
            "lightfast": lf,
            "lightfast_word": lfw,
            "transparency": int(transp),
            "staining": stain,
            "granulating": gran,
        }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"\n<!-- красок: {len(out)} -->", file=sys.stderr)


if __name__ == "__main__":
    main()
