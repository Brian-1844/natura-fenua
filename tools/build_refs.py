"""Natura Fenua - prépare la reconnaissance à partir des photos.

Pour chaque section (plantes, nuages, oiseaux, insectes, champignons), lit les photos rangées ainsi :
    photos/<section>/<id de l'espèce>/*.jpg
    photos/<section>/autre/*.jpg   (photos « rien de tout ça », conseillé)
et calcule une « empreinte » de chaque photo avec le modèle MobileNet V3 (le même que dans l'app).
Résultat : refs/<section>.json, que l'app compare à la photo prise (méthode des plus proches voisins).

Usage : python tools/build_refs.py --model models/mobilenet_v3_large.tflite
"""
import argparse, base64, json, os, sys
import numpy as np
from PIL import Image, ImageOps
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

SECTIONS = ["plantes", "nuages", "oiseaux", "insectes", "champignons"]
EXT = (".jpg", ".jpeg", ".png", ".webp")
OTHER = "autre"


def quantize(v):
    """Même calcul que dans l'app : vecteur normalisé -> octets signés (-127..127)."""
    v = np.asarray(v, dtype=np.float32)
    v = v / (np.linalg.norm(v) or 1.0)
    return np.clip(np.round(v * 127), -127, 127).astype(np.int8)


DUP = 0.97      # deux photos plus ressemblantes que ça = doublon (rafale), on n'en garde qu'une
SESSION = 0.90  # photos d'une même « séance » (même plante, même moment) : testées ensemble
CAP = 60        # au plus 60 photos par espèce (les plus variées) : l'app reste rapide
M = 3           # score d'une espèce = moyenne de ses 3 photos les plus proches


def load(path):
    """Même préparation que dans l'app : orientation, fond blanc, carré central 256 x 256."""
    im = ImageOps.exif_transpose(Image.open(path))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    im.draft("RGB", (512, 512))
    return ImageOps.fit(im, (256, 256), Image.BICUBIC)


def embed1(embedder, im):
    arr = np.ascontiguousarray(np.asarray(im, dtype=np.uint8))
    r = embedder.embed(mp.Image(image_format=mp.ImageFormat.SRGB, data=arr))
    v = np.asarray(r.embeddings[0].embedding, dtype=np.float32)
    return v / (np.linalg.norm(v) or 1.0)


def embed(embedder, im):
    """Photo + photo retournée, moyennées : un seul vecteur, plus stable (l'app fait pareil)."""
    return quantize(embed1(embedder, im) + embed1(embedder, ImageOps.mirror(im)))


def scores(q, mats, labels, skip=()):
    """Score par espèce (moyenne des M photos les plus proches) : une espèce avec beaucoup de photos n'écrase pas les autres."""
    sims = (mats @ q.astype(np.int32)) / 16129.0
    by = {}
    for i, c in enumerate(labels):
        if i in skip:
            continue
        by.setdefault(c, []).append(sims[i])
    out = {c: float(np.mean(sorted(v, reverse=True)[:M])) for c, v in by.items()}
    return sorted(out.items(), key=lambda x: -x[1])


def thresholds(pos, neg):
    """Seuils « sûr » / « peut-être » : le score à partir duquel au moins 95 % / 80 % des réponses sont justes."""
    if len(pos) < 10:
        return None
    pts = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg], reverse=True)
    out, good, tot = {}, 0, 0
    for s, ok in pts:
        good += ok; tot += 1
        p = good / tot
        if p >= 0.95: out["sure"] = s
        if p >= 0.80: out["maybe"] = s
    if "sure" in out: out["sure"] = round(max(out["sure"], 0.70), 3)
    if "maybe" in out: out["maybe"] = round(max(out["maybe"], 0.55), 3)
    return out or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--photos", default="photos")
    ap.add_argument("--out", default="refs")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    opts = vision.ImageEmbedderOptions(
        base_options=mpt.BaseOptions(model_asset_path=a.model), l2_normalize=True, quantize=False)
    embedder = vision.ImageEmbedder.create_from_options(opts)
    report = {}
    for sec in SECTIONS:
        root = os.path.join(a.photos, sec)
        labels, vecs, group, counts, raw = [], [], [], {}, {}
        gid = 0
        if os.path.isdir(root):
            for cls in sorted(os.listdir(root)):
                d = os.path.join(root, cls)
                if not os.path.isdir(d):
                    continue
                files = sorted(f for f in os.listdir(d) if f.lower().endswith(EXT))
                kept, heads, cls_items = [], [], []
                for f in files:
                    try:
                        v = embed(embedder, load(os.path.join(d, f)))
                    except Exception as e:  # photo illisible : on la saute
                        print(f"  ! {sec}/{cls}/{f} illisible ({e})")
                        continue
                    raw[cls] = raw.get(cls, 0) + 1
                    vi = v.astype(np.int32)
                    if any(vi @ k.astype(np.int32) > DUP * 16129 for k in kept):
                        continue  # doublon de rafale
                    kept.append(v)
                    g = next((h[1] for h in heads if vi @ h[0].astype(np.int32) > SESSION * 16129), None)
                    if g is None:
                        g = gid; gid += 1; heads.append((v, g))
                    cls_items.append((v, g))
                if len(cls_items) > CAP:  # garder les plus variées (échantillonnage le plus éloigné)
                    V = np.stack([v for v, _ in cls_items]).astype(np.int32)
                    sel = [0]; dmax = V @ V[0]
                    while len(sel) < CAP:
                        i = int(np.argmin(dmax)); sel.append(i); dmax = np.maximum(dmax, V @ V[i])
                    cls_items = [cls_items[i] for i in sel]
                for v, g in cls_items:
                    labels.append(cls); vecs.append(v); group.append(g)
                if cls_items:
                    counts[cls] = len(cls_items)
        out = os.path.join(a.out, f"{sec}.json")
        if not vecs:
            if os.path.exists(out):
                os.remove(out)
            print(f"{sec} : aucune photo")
            continue
        mats = np.stack(vecs).astype(np.int32)
        # Test honnête : chaque photo est reconnue SANS les photos de la même séance.
        acc, thr = None, None
        species = [c for c in counts if c != OTHER]
        if len(counts) >= 2:
            good = tot = 0
            pos, neg = [], []
            for i in range(len(vecs)):
                skip = {j for j in range(len(vecs)) if group[j] == group[i]}
                sc = scores(mats[i], mats, labels, skip)
                if not sc:
                    continue
                if labels[i] == OTHER:
                    best = next((s for c, s in sc if c != OTHER), None)
                    if best is not None: neg.append(best)
                    continue
                tot += 1
                good += sc[0][0] == labels[i]
                if sc[0][0] == labels[i]: pos.append(sc[0][1])
                else: neg.append(sc[0][1])
            acc = round(good / tot, 3) if tot else None
            thr = thresholds(pos, neg)
        data = {"model": os.path.basename(a.model), "dim": int(mats.shape[1]), "m": M, "counts": counts,
                "thr": thr, "items": [[c, base64.b64encode(v.tobytes()).decode()] for c, v in zip(labels, vecs)]}
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        report[sec] = {"photos_recues": raw, "photos_gardees": counts, "seances": len(set(group)),
                       "precision_test": acc, "seuils": thr}
        print(f"{sec} : {sum(raw.values())} photos ({sum(counts.values())} gardées sans doublons, {len(set(group))} séances), "
              f"{len(species)} espèces, précision test = {acc}, seuils = {thr}")
    with open(os.path.join(a.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
