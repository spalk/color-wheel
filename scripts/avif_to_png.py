#!/usr/bin/env python3
"""AVIF -> PNG через системную libheif (ctypes), без внешних зависимостей.

В системе стоит libheif1 с плагином aomdec, но без CLI-утилиты, а pip и PIL
недоступны. Дот-карты авторов приходят в .avif, поэтому конвертер свой.

Запуск: python3 avif_to_png.py вход.avif [выход.png] [--max N]
        --max N  ужать длинную сторону до N пикселей (грубо, по выборке)
"""
import ctypes, ctypes.util, os, struct, sys, zlib

# --- enum'ы libheif ---
COLORSPACE_RGB = 1
CHROMA_INTERLEAVED_RGB = 10
CHANNEL_INTERLEAVED = 10


class HeifError(ctypes.Structure):
    _fields_ = [("code", ctypes.c_int),
                ("subcode", ctypes.c_int),
                ("message", ctypes.c_char_p)]


def load_lib():
    for cand in ("libheif.so.1", ctypes.util.find_library("heif"), "libheif.so"):
        if not cand:
            continue
        try:
            return ctypes.CDLL(cand)
        except OSError:
            continue
    sys.exit("libheif не найдена")


def check(err, what):
    if err.code != 0:
        msg = err.message.decode("utf-8", "replace") if err.message else "?"
        sys.exit(f"libheif: {what}: {msg}")


def decode(path):
    lib = load_lib()
    lib.heif_context_alloc.restype = ctypes.c_void_p
    lib.heif_context_read_from_file.restype = HeifError
    lib.heif_context_read_from_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                ctypes.c_void_p]
    lib.heif_context_get_primary_image_handle.restype = HeifError
    lib.heif_context_get_primary_image_handle.argtypes = [ctypes.c_void_p,
                                                          ctypes.POINTER(ctypes.c_void_p)]
    lib.heif_decode_image.restype = HeifError
    lib.heif_decode_image.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                                      ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    lib.heif_image_get_width.restype = ctypes.c_int
    lib.heif_image_get_width.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.heif_image_get_height.restype = ctypes.c_int
    lib.heif_image_get_height.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.heif_image_get_plane_readonly.restype = ctypes.POINTER(ctypes.c_ubyte)
    lib.heif_image_get_plane_readonly.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                                  ctypes.POINTER(ctypes.c_int)]

    ctx = ctypes.c_void_p(lib.heif_context_alloc())
    check(lib.heif_context_read_from_file(ctx, path.encode(), None), "чтение файла")
    handle = ctypes.c_void_p()
    check(lib.heif_context_get_primary_image_handle(ctx, ctypes.byref(handle)),
          "primary image")
    img = ctypes.c_void_p()
    check(lib.heif_decode_image(handle, ctypes.byref(img), COLORSPACE_RGB,
                                CHROMA_INTERLEAVED_RGB, None), "декодирование")
    w = lib.heif_image_get_width(img, CHANNEL_INTERLEAVED)
    h = lib.heif_image_get_height(img, CHANNEL_INTERLEAVED)
    stride = ctypes.c_int()
    ptr = lib.heif_image_get_plane_readonly(img, CHANNEL_INTERLEAVED,
                                            ctypes.byref(stride))
    if not ptr:
        sys.exit("не удалось получить пиксели")
    buf = ctypes.string_at(ptr, stride.value * h)
    return w, h, stride.value, buf


def shrink(w, h, stride, buf, maxside):
    """Грубое прореживание — для чтения текста хватает, а файл лёгкий."""
    step = max(1, (max(w, h) + maxside - 1) // maxside)
    if step == 1:
        return w, h, stride, buf
    nw, nh = w // step, h // step
    out = bytearray(nw * nh * 3)
    for y in range(nh):
        src = y * step * stride
        dst = y * nw * 3
        for x in range(nw):
            s = src + x * step * 3
            out[dst + x * 3: dst + x * 3 + 3] = buf[s:s + 3]
    return nw, nh, nw * 3, bytes(out)


def write_png(path, w, h, stride, buf):
    raw = bytearray()
    for y in range(h):
        raw.append(0)                        # фильтр none
        raw += buf[y * stride: y * stride + w * 3]
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + chunk(b"IEND", b""))
    open(path, "wb").write(png)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    maxside = 0
    if "--max" in sys.argv:
        maxside = int(sys.argv[sys.argv.index("--max") + 1])
        args = [a for a in args if a != str(maxside)]
    if not args:
        sys.exit(__doc__)
    src = args[0]
    dst = args[1] if len(args) > 1 else os.path.splitext(src)[0] + ".png"
    w, h, stride, buf = decode(src)
    print(f"{os.path.basename(src)}: {w}x{h}", file=sys.stderr)
    if maxside:
        w, h, stride, buf = shrink(w, h, stride, buf, maxside)
        print(f"  ужато до {w}x{h}", file=sys.stderr)
    write_png(dst, w, h, stride, buf)
    print(f"-> {dst} ({os.path.getsize(dst) // 1024} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
