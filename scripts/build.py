"""Turns the PNGs in source/ into the sticker files Pesu downloads (out/).

Run by GitHub on every push (see .github/workflows/build.yml), or by hand:
    pip install pillow
    python scripts/build.py

- A PNG in source/ that isn't in stickers.json yet gets a line added for it: the id is the
  number at the start of the file name (005a = a version of 005), the caption comes from the
  rest of the name, and the category is copied from the base number (or "Everyday").
  Fix the caption in stickers.json afterwards if it needs punctuation.
- Every sticker is trimmed, fitted into 512x512 and saved as WebP under 100 KB, with the
  WhatsApp sticker details (Pesu Keyboard / BK) inside.
- out/index.json lists every sticker with a checksum, so the app downloads only what changed.
"""
import hashlib
import json
import os
import re
import struct
import time

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
OUT = os.path.join(ROOT, "out")
META = os.path.join(ROOT, "stickers.json")
NAME = re.compile(r"^(c?\d{3}[a-z]?)_(.+)\.png$", re.I)


def exif(category):
    data = json.dumps({
        "sticker-pack-id": "dev.bkar81.pesu.stickers",
        "sticker-pack-name": f"Pesu Keyboard · {category}",
        "sticker-pack-publisher": "BK · Pesu Keyboard",
        "emojis": ["😊"],
    }, ensure_ascii=False).encode()
    return b"II*\x00\x08\x00\x00\x00\x01\x00" + struct.pack("<HHII", 0x5741, 7, len(data), 0x16) + data


def background_kind(path):
    """None if the picture is already see-through; otherwise "white", "black" or "painted"
    (a drawn checkerboard or shaded background)."""
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = [im.getpixel(p) for p in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]]
    if all(p[3] < 10 for p in px):
        return None
    if all(min(p[:3]) >= 240 and p[3] >= 250 for p in px):
        return "white"
    if all(max(p[:3]) <= 20 for p in px):
        return "black"
    return "painted"


def needs_cutout(path):
    return background_kind(path) is not None


def _disk(r):
    import numpy as np
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def cut_black(im):
    """Removes a plain black background (a see-through picture saved without transparency)."""
    import numpy as np
    from scipy import ndimage
    a = np.asarray(im.convert("RGB")).astype(float)
    sat = a.max(2) - a.min(2)
    sm = ndimage.gaussian_filter(a.mean(2), 1.0)
    grad = np.hypot(ndimage.sobel(sm, 0), ndimage.sobel(sm, 1)) / 8
    cand = (sat < 22) & (grad < 6) & (a.max(2) < 60)
    lab, _ = ndimage.label(cand)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    shape = ~np.isin(lab, edge[edge > 0])
    shape = ndimage.binary_opening(shape, structure=_disk(max(3, round(min(im.size) / 120))))
    lab, n = ndimage.label(shape)
    if n > 1:
        sizes = ndimage.sum(shape, lab, range(1, n + 1))
        shape = np.isin(lab, [i + 1 for i, v in enumerate(sizes) if v >= sizes.max() * 0.002])
    shape = ndimage.binary_fill_holes(shape)
    alpha = np.clip((ndimage.gaussian_filter(shape.astype(float), 0.8) - 0.2) / 0.6, 0, 1) * 255
    return Image.fromarray(np.dstack([a, alpha]).clip(0, 255).astype(np.uint8), "RGBA")


def rebuild_border(im):
    """For a sticker on a painted background (e.g. a drawn checkerboard): finds the drawing
    itself, then draws a fresh white die-cut border with a thin grey edge line around it."""
    import numpy as np
    from scipy import ndimage
    a = np.asarray(im.convert("RGB")).astype(float)
    W = a.shape[1]
    sat = a.max(2) - a.min(2)
    content = (sat > 18) | (a.mean(2) < 150)
    content = ndimage.binary_opening(content, structure=_disk(2))
    k = max(4, round(W / 120))
    content = ndimage.binary_closing(np.pad(content, k + 2), structure=_disk(k))[k + 2:-k - 2, k + 2:-k - 2]
    content = ndimage.binary_fill_holes(content)
    lab, n = ndimage.label(content)
    if n > 1:
        sizes = ndimage.sum(content, lab, range(1, n + 1))
        content = np.isin(lab, [i + 1 for i, v in enumerate(sizes) if v >= sizes.max() * 0.003])
    border = ndimage.binary_fill_holes(ndimage.binary_dilation(content, structure=_disk(max(8, round(W * 0.022)))))
    ring = border & ~ndimage.binary_erosion(border, structure=_disk(2))
    a[border & ~content] = 255
    a[ring] = [214, 220, 226]
    alpha = np.clip((ndimage.gaussian_filter(border.astype(float), 0.9) - 0.2) / 0.6, 0, 1) * 255
    return Image.fromarray(np.dstack([a, alpha]).clip(0, 255).astype(np.uint8), "RGBA")


def cut_out(im):
    """Makes the white background see-through. The sticker's thin grey edge line marks its
    outline: everything that isn't near-white is joined up (small gaps in the line closed),
    the inside is filled, and the white outside is removed with a soft one-pixel edge."""
    import numpy as np
    from scipy import ndimage
    a = np.asarray(im.convert("RGBA")).astype(np.int16)
    rgb = a[..., :3]
    ink = rgb.min(axis=2) < 238
    r = max(3, round(min(im.size) / 100))          # about 12 px on a 1254 px picture
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    disk = x * x + y * y <= r * r
    pad = r + 2
    shape = np.pad(ink, pad)
    shape = ndimage.binary_closing(shape, structure=disk)[pad:-pad, pad:-pad]
    shape = ndimage.binary_fill_holes(shape)
    lab, n = ndimage.label(shape)
    if n > 1:                                        # drop specks away from the sticker
        sizes = ndimage.sum(shape, lab, range(1, n + 1))
        shape = np.isin(lab, [i + 1 for i, v in enumerate(sizes) if v >= sizes.max() * 0.002])
    soft = ndimage.gaussian_filter(shape.astype(float), 0.8)
    alpha = np.minimum(a[..., 3] / 255.0, np.clip((soft - 0.2) / 0.6, 0, 1))
    out = np.dstack([rgb, (alpha * 255).round()]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def fit(path):
    im = Image.open(path).convert("RGBA")
    kind = background_kind(path)
    if kind == "white":
        im = cut_out(im)
    elif kind == "black":
        im = cut_black(im)
    elif kind == "painted":
        im = rebuild_border(im)
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if box:
        im = im.crop(box)
    s = 480 / max(im.size)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.paste(im, ((512 - im.width) // 2, (512 - im.height) // 2), im)
    return canvas


def main():
    meta = json.load(open(META, encoding="utf-8"))
    stickers = meta["stickers"]
    by_id = {s["id"]: s for s in stickers}
    by_file = {s["file"]: s for s in stickers}

    # New PNGs get a line in stickers.json.
    for f in sorted(os.listdir(SRC)):
        m = NAME.match(f)
        if not m or f in by_file:
            continue
        sid = m.group(1).lower()
        caption = m.group(2).replace("_", " ").strip().title()
        base = sid[:-1] if sid[-1].isalpha() else None
        entry = {"id": sid, "file": f, "caption": caption,
                 "category": by_id[base]["category"] if base and base in by_id else "Everyday"}
        if base:
            entry["base"] = base
        if sid in by_id:          # same number, new file: replace the old line's file
            by_id[sid]["file"] = f
        else:
            stickers.append(entry)
            by_id[sid] = entry
        print("added", sid, f)

    os.makedirs(OUT, exist_ok=True)
    old = {}
    idx_path = os.path.join(OUT, "index.json")
    if os.path.exists(idx_path):
        old = {s["id"]: s for s in json.load(open(idx_path, encoding="utf-8")).get("stickers", [])}

    items = []
    for s in stickers:
        src = os.path.join(SRC, s["file"])
        if not os.path.exists(src):
            print("missing file, skipped:", s["file"])
            continue
        src_hash = hashlib.sha1(open(src, "rb").read() + s["category"].encode()
                                + {"white": b"cutout2", "black": b"cutblack1", "painted": b"rebuild1"}.get(background_kind(src), b"")).hexdigest()
        out_name = f"s{s['id']}.webp"
        out_path = os.path.join(OUT, out_name)
        prev = old.get(s["id"])
        if not (prev and prev.get("src") == src_hash and os.path.exists(out_path)):
            im = fit(src)
            for q in (80, 75, 70, 65, 60):
                im.save(out_path, "WEBP", quality=q, method=4, exif=exif(s["category"]))
                if os.path.getsize(out_path) < 100_000:
                    break
            print("made", out_name, os.path.getsize(out_path) // 1024, "KB")
        item = {k: s[k] for k in ("id", "caption", "category") }
        for k in ("base", "tags"):
            if s.get(k):
                item[k] = s[k]
        item["file"] = out_name
        item["sha1"] = hashlib.sha1(open(out_path, "rb").read()).hexdigest()
        item["src"] = src_hash
        items.append(item)

    keep = {i["file"] for i in items}
    for f in os.listdir(OUT):
        if f.endswith(".webp") and f not in keep:
            os.remove(os.path.join(OUT, f))
            print("removed", f)

    index = {
        "version": int(time.time()),
        "stickers": items,
        "hidden": meta.get("hidden", []),
    }
    unchanged = old and [ {k: v for k, v in i.items()} for i in items ] == list(old.values()) \
        and json.load(open(idx_path, encoding="utf-8")).get("hidden", []) == index["hidden"]
    if not unchanged:
        json.dump(index, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # A plain list of every sticker's number, for keeping the original PNGs in step.
    import csv
    with open(os.path.join(ROOT, "numbers.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Number", "Caption", "Page", "File"])
        for s in sorted(stickers, key=lambda x: x["id"]):
            if s["id"] not in index["hidden"]:
                w.writerow([s["id"], s["caption"], s["category"], s["file"]])
    print(len(items), "stickers,", len(index["hidden"]), "hidden")


if __name__ == "__main__":
    main()
