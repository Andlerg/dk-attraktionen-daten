#!/usr/bin/env python3
"""Baut data/attractions.json für das WordPress-Plugin "Dänemark Attraktionen-Karte".

Eingabe:  GeoJSON, das `osmium export` aus dem gefilterten Dänemark-Auszug erzeugt hat.
Ausgabe:  JSON im Format, das das Plugin erwartet:
          {"generated": ..., "source": ..., "items": [{id, n, la, lo, c, w?, d?, s?, o?}, ...]}

Die Aufbereitung entspricht der des Plugins (Kategorien, Webadressen, Beschreibungen).
Aufruf:   build_attractions.py EINGABE.geojson AUSGABE.json [--min-items 300]
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

# Reihenfolge = Vorrang. Ein Objekt landet in der ersten passenden Kategorie.
CATEGORIES = [
    ("museum", [("tourism", "museum")]),
    ("freizeitpark", [("tourism", "theme_park"), ("leisure", "water_park")]),
    ("zoo", [("tourism", "zoo"), ("tourism", "aquarium")]),
    ("burg", [("historic", "castle"), ("historic", "fort"), ("historic", "manor")]),
    # Die allgemeine Kategorie "Attraktion" enthält viel Unbedeutendes: nur mit Webseite.
    ("sehenswert", [("tourism", "attraction")]),
]
NEEDS_WEBSITE = {"sehenswert"}
ORDER = {key: i for i, (key, _) in enumerate(CATEGORIES)}

# Plausibler Bereich für Dänemark (inkl. Bornholm); alles außerhalb wird verworfen.
LAT_RANGE = (54.4, 58.0)
LON_RANGE = (7.5, 15.5)

SOURCE_TEXT = "OpenStreetMap-Mitwirkende (ODbL), Auszug von Geofabrik"


def clean_url(url):
    """Gültige http(s)-Adresse oder ''. (Entspricht dkak_clean_url im Plugin.)"""
    url = str(url or "").strip()
    if ";" in url:
        url = url.split(";")[0].strip()
    if not url or re.search(r"\s", url):
        return ""
    if not re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
        url = "https://" + url
    try:
        parts = urlparse(url)
    except ValueError:
        return ""
    if parts.scheme.lower() not in ("http", "https"):
        return ""
    if not parts.hostname or "." not in parts.hostname:
        return ""
    return url


def shorten(text, limit=280):
    """Kürzt ohne mitten im Wort abzuschneiden. (Entspricht dkak_shorten im Plugin.)"""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    pos = cut.rfind(" ")
    if pos > limit * 0.6:
        cut = cut[:pos]
    return cut.rstrip(" ,;:-") + "…"


def first_tag(tags, names):
    for name in names:
        value = tags.get(name)
        if value:
            return value
    return ""


def website_of(tags):
    for name in ("website", "contact:website", "url"):
        if tags.get(name):
            url = clean_url(tags[name])
            if url:
                return url
    return ""


def category_of(tags):
    for key, filters in CATEGORIES:
        if any(tags.get(k) == v for k, v in filters):
            if key in NEEDS_WEBSITE and not website_of(tags):
                continue
            return key
    return None


def iter_coords(node):
    """Alle [lon, lat]-Paare einer GeoJSON-Geometrie."""
    if isinstance(node, (list, tuple)):
        if len(node) >= 2 and all(isinstance(v, (int, float)) for v in node[:2]):
            yield node[0], node[1]
        else:
            for child in node:
                yield from iter_coords(child)


def center_of(geometry):
    """Mittelpunkt (lat, lon) der Umgebungsbox; für Punkte der Punkt selbst."""
    if not geometry:
        return None
    if geometry.get("type") == "GeometryCollection":
        coords = [c for g in geometry.get("geometries", []) for c in iter_coords(g.get("coordinates"))]
    else:
        coords = list(iter_coords(geometry.get("coordinates")))
    if not coords:
        return None
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2


def osm_id(feature, name, lat, lon):
    """Kennung im Format des Plugins ("node/123"). Flächen ("a…") werden auf way/relation zurückgeführt."""
    raw = feature.get("id")
    if raw is None:
        raw = (feature.get("properties") or {}).get("@id")
    match = re.fullmatch(r"([nwra])(\d+)", str(raw)) if raw is not None else None
    if match:
        kind, number = match.group(1), int(match.group(2))
        if kind == "a":  # osmium: Fläche aus Weg = 2*id, aus Relation = 2*id+1
            return "%s/%d" % ("relation" if number % 2 else "way", number // 2)
        return "%s/%d" % ({"n": "node", "w": "way", "r": "relation"}[kind], number)
    digest = hashlib.sha1(("%s|%.5f|%.5f" % (name, lat, lon)).encode("utf-8")).hexdigest()[:12]
    return "x/" + digest


def normalize(feature):
    """Ein GeoJSON-Feature -> Eintrag im Plugin-Format oder None."""
    tags = feature.get("properties") or {}
    name = tags.get("name:de") or tags.get("name")
    if not name:
        return None
    category = category_of(tags)
    if not category:
        return None
    center = center_of(feature.get("geometry"))
    if not center:
        return None
    lat, lon = center
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]):
        return None

    item = {
        "id": osm_id(feature, name, lat, lon),
        "n": str(name),
        "la": round(lat, 5),
        "lo": round(lon, 5),
        "c": category,
    }
    web = website_of(tags)
    if web:
        item["w"] = web
    desc = first_tag(tags, ("description:de", "description", "description:en", "description:da"))
    if desc:
        item["d"] = shorten(desc, 280)
    city = first_tag(tags, ("addr:city", "addr:town", "addr:village"))
    if city:
        item["s"] = str(city)
    if tags.get("opening_hours"):
        item["o"] = shorten(tags["opening_hours"], 200)
    return item


def dedupe(items):
    """Gleicher Name an nahezu gleicher Stelle: den Eintrag mit mehr Angaben behalten."""
    unique = {}
    for item in items:
        key = "%s|%.3f|%.3f" % (item["n"].lower(), item["la"], item["lo"])
        if key not in unique or len(item) > len(unique[key]):
            unique[key] = item
    return list(unique.values())


def load_features(path):
    """Liest FeatureCollection (osmium export -f geojson) oder GeoJSON-Sequenz (-f geojsonseq)."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    stripped = text.lstrip("\x1e \t\r\n")
    try:
        data = json.loads(stripped)
        if isinstance(data, dict) and "features" in data:
            return data["features"]
        if isinstance(data, dict) and data.get("type") == "Feature":
            return [data]
    except json.JSONDecodeError:
        pass
    features = []
    for line in text.splitlines():
        line = line.strip("\x1e \t\r\n")
        if line:
            features.append(json.loads(line))
    return features


def build(features):
    items = []
    seen_ids = set()
    for feature in features:
        item = normalize(feature)
        if item and item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            items.append(item)
    items = dedupe(items)
    items.sort(key=lambda i: (ORDER[i["c"]], i["n"].lower(), i["id"]))
    return items


def write_output(path, items):
    """Ein Eintrag pro Zeile, damit Änderungen in Git gut lesbar bleiben."""
    header = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "source": SOURCE_TEXT,
    }
    lines = [json.dumps(i, ensure_ascii=False, separators=(",", ":")) for i in items]
    head = json.dumps(header, ensure_ascii=False, separators=(",", ":"))[:-1]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(head + ',"items":[\n' + ",\n".join(lines) + "\n]}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("eingabe")
    parser.add_argument("ausgabe")
    parser.add_argument("--min-items", type=int, default=300,
                        help="Abbruch, wenn weniger Einträge herauskommen (Schutz vor leeren Dateien)")
    args = parser.parse_args(argv)

    items = build(load_features(args.eingabe))
    counts = {}
    for item in items:
        counts[item["c"]] = counts.get(item["c"], 0) + 1
    print("Einträge gesamt: %d  %s" % (len(items), json.dumps(counts, ensure_ascii=False)))
    if len(items) < args.min_items:
        print("FEHLER: weniger als %d Einträge. Datei wird nicht geschrieben." % args.min_items, file=sys.stderr)
        return 1
    write_output(args.ausgabe, items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
