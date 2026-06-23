import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
ROOT = Path("locations")
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

def get_name(data):
    for name in data.get("names", []):
        if name["language"]["name"] == "en": return name["name"]

    return data["name"]

def build_location(name):
    print(f"> Obtendo location: {name}")

    data = get(f"{BASE}/location/{name}")

    return {
        "id": data["id"],
        "nome": data["name"],
        "nome_en": get_name(data),
        "regiao": data["region"]["name"] if data.get("region") else None,
        "areas": [area["name"] for area in data.get("areas", [])],
        "game_indices": [{"generation": gi["generation"]["name"], "indice": gi["game_index"]} for gi in data.get("game_indices", [])]
    }

def complete(path):
    if not path.exists(): return False

    try:
        data = load_json(path)
        required = ["id", "nome", "nome_en", "regiao", "areas", "game_indices"]
        return all(field in data for field in required)
    except Exception:
        return False

def process_location(item, idx, total):
    name = item["name"]

    json_path = ROOT / f"{name}.json"

    print(f"\n[{idx}/{total}] {name}")

    if complete(json_path):
        print(f"[{idx}] {name}: CACHE OK")
        return

    try:
        data = build_location(name)
        save_json(json_path, data)
        print(f"[{idx}] {name}: salvo")
    except Exception as e:
        print(f"[{idx}] {name}: erro -> {e}")

def main():
    ROOT.mkdir(exist_ok=True)

    locations = get(f"{BASE}/location?limit=10000")["results"]
    total = len(locations)

    print(f"Locations encontradas: {total}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_location, item, idx, total) for idx, item in enumerate(locations, start=1)]

        for future in as_completed(futures):
            try: future.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()