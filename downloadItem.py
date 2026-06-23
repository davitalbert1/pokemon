import os
import json
import hashlib
import requests
import traceback
from threading import Semaphore
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
ROOT = Path("items")
ITEM_INFO = "item.json"
SPRITES_DIR = "sprites"
SPRITES_INFO = "sprites_manifest.json"
CACHE = {}
DOWNLOAD_LIMIT = 5
download_semaphore = Semaphore(DOWNLOAD_LIMIT)

def get(url):
    if url in CACHE: return CACHE[url]

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    data = r.json()

    CACHE[url] = data

    return data

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if not path.exists(): return None

    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except json.JSONDecodeError:
        print(f"JSON inválido removido: {path}")

        try: path.unlink()
        except Exception: pass

        return None

def hash_map(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

def download_file(url, path):
    if not url: return
    if path.exists(): return

    with download_semaphore:
        path.parent.mkdir(parents=True, exist_ok=True)

        r = requests.get(url, timeout=60)
        r.raise_for_status()

        with open(path, "wb") as f: f.write(r.content)

        print(f"Sprite salvo: {path}")

def flatten_sprites(obj, prefix=""):
    result = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            current = f"{prefix}/{key}" if prefix else key
            if isinstance(value, str) and value.startswith("http"): result[current] = value
            elif isinstance(value, (dict, list)): result.update(flatten_sprites(value, current))
    elif isinstance(obj, list):
        for i, value in enumerate(obj): result.update(flatten_sprites(value, f"{prefix}/{i}"))

    return result

def sprites_complete(folder, sprite_map):
    for key, url in sprite_map.items():
        filename = key.replace("/", "_") + os.path.splitext(url)[1]
        if not (folder / SPRITES_DIR / filename).exists(): return False

    return True

def get_english_effect(item):
    for entry in item.get("effect_entries", []):
        if entry["language"]["name"] == "en": return {"effect": entry.get("effect"), "short_effect": entry.get("short_effect")}

    return {"effect": None, "short_effect": None}

def get_flavor_texts(item):
    texts = []

    for entry in item.get("flavor_text_entries", []):
        if entry["language"]["name"] == "en":
            texts.append(entry["text"].replace("\n", " ").replace("\f", " "))

    return list(dict.fromkeys(texts))

def build_item(name):
    print(f"> Obtendo item: {name}")

    item = get(f"{BASE}/item/{name}")
    effect = get_english_effect(item)
    baby_trigger = item.get("baby_trigger_for")
    baby_trigger_name = None

    if baby_trigger and baby_trigger.get("url"):
        chain = get(baby_trigger["url"])
        trigger_item = chain.get("baby_trigger_item")

        if trigger_item: baby_trigger_name = trigger_item.get("name")

    data = {
        "id": item["id"],
        "nome": item["name"],
        "custo": item["cost"],
        "categoria": item["category"]["name"] if item.get("category") else None,
        "atributo": item["attribute"]["name"] if item.get("attribute") else None,
        "effect": effect["effect"],
        "short_effect": effect["short_effect"],
        "flavor_texts": get_flavor_texts(item),
        "fling_power": item.get("fling_power"),
        "fling_effect":item["fling_effect"]["name"] if item.get("fling_effect") else None,
        "baby_trigger_for": baby_trigger_name,
        "held_by_pokemon": [{
                "pokemon": p["pokemon"]["name"],
                "versions": [v["version"]["name"] for v in p.get("version_details", [])]
            }
            for p in item.get("held_by_pokemon", [])
        ],
        "game_indices": [{"generation": g["generation"]["name"], "index": g["game_index"]} for g in item.get("game_indices", [])]
    }

    sprite_map = flatten_sprites(item.get("sprites", {}))

    return data, sprite_map

def complete(folder):
    path = folder / ITEM_INFO

    if not path.exists(): return False

    try:
        data = load_json(path)
        required = ["id", "nome", "custo", "categoria", "effect", "short_effect", "flavor_texts"]

        return all(field in data for field in required)
    except Exception:
        return False

def process_item(item_info, idx, total):
    name = item_info["name"]

    folder = ROOT / name

    print(f"\n[{idx}/{total}] {name}")

    manifest_path = folder / SPRITES_INFO
    json_path = folder / ITEM_INFO

    manifest = (load_json(manifest_path) if manifest_path.exists() else None)

    if json_path.exists() and manifest:
        sprite_map = manifest.get("sprites", {})

        if (complete(folder) and sprites_complete(folder, sprite_map)):
            print(f"[{idx}] {name}: CACHE OK (SKIP)")
            return

    if (not json_path.exists() or not manifest or not complete(folder)):
        data, sprite_map = build_item(name)
        save_json(folder / ITEM_INFO, data)

        manifest = {"hash": hash_map(sprite_map), "sprites": sprite_map}
        save_json(folder / SPRITES_INFO, manifest)

    manifest = load_json(folder / SPRITES_INFO)
    sprite_map = manifest.get("sprites", {})

    if sprites_complete(folder, sprite_map):
        print(f"- Sprites completos: {name}")
        return

    for key, url in sprite_map.items():
        filename = key.replace("/", "_") + os.path.splitext(url)[1]
        download_file(url, folder / SPRITES_DIR / filename)

    print(f"Concluído: {name}")

def main():
    ROOT.mkdir(exist_ok=True)

    items = get(f"{BASE}/item?limit=10000")["results"]
    total = len(items)

    print(f"Itens encontrados: {total}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_item, item, idx, total) for idx, item in enumerate(items, start=1)]

        for future in as_completed(futures):
            try: future.result()
            except: traceback.print_exc()

if __name__ == "__main__":
    main()