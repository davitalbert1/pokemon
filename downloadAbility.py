import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
ROOT = Path("abilities")
CACHE = {}

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
    if path.exists():
        with open(path, encoding="utf-8") as f: return json.load(f)
    return None

def get_english_effect(data):
    for entry in data.get("effect_entries", []):
        if entry["language"]["name"] == "en": return {"effect": entry.get("effect"), "short_effect": entry.get("short_effect")}

    return {"effect": None, "short_effect": None}

def get_english_flavor_texts(data):
    texts = []

    for entry in data.get("flavor_text_entries", []):
        if entry["language"]["name"] == "en": texts.append(entry["flavor_text"].replace("\n", " ").replace("\f", " "))

    return list(dict.fromkeys(texts))

def build_ability(name):
    print(f"> Obtendo ability: {name}")
    data = get(f"{BASE}/ability/{name}")
    effect_data = get_english_effect(data)

    return {
        "id": data["id"],
        "nome": data["name"],
        "geracao": data["generation"]["name"] if data.get("generation") else None,
        "principal_series": data.get("is_main_series"),
        "effect": effect_data["effect"],
        "short_effect": effect_data["short_effect"],
        "flavor_texts": get_english_flavor_texts(data),
        "pokemon": [{"nome": p["pokemon"]["name"], "hidden": p["is_hidden"], "slot": p["slot"]} for p in data.get("pokemon", [])]
    }

def complete(path):
    if not path.exists(): return False

    try:
        data = load_json(path)
        required = ["id", "nome", "geracao", "principal_series", "effect", "short_effect", "flavor_texts", "pokemon"]
        return all(field in data for field in required)
    except Exception:
        return False

def process_ability(item, idx, total):
    name = item["name"]

    json_path = ROOT / f"{name}.json"

    print(f"\n[{idx}/{total}] {name}")

    if complete(json_path):
        print(f"[{idx}] {name}: CACHE OK")
        return

    try:
        data = build_ability(name)
        save_json(json_path, data)
        print(f"[{idx}] {name}: salvo")
    except Exception as e:
        print(f"[{idx}] {name}: erro -> {e}")

def main():
    ROOT.mkdir(exist_ok=True)

    abilities = get(f"{BASE}/ability?limit=10000")["results"]
    total = len(abilities)

    print(f"Abilities encontradas: {total}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_ability, item, idx, total) for idx, item in enumerate(abilities, start=1)]

        for future in as_completed(futures):
            try: future.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()