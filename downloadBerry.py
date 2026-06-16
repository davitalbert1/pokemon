import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
ROOT = Path("berries")
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

def complete(path):
    if not path.exists(): return False

    try:
        data = load_json(path)
        required = ["id", "nome", "growth_time", "max_harvest", "natural_gift_power", "size", "smoothness",
            "soil_dryness", "item", "firmness", "natural_gift_type", "flavors"]

        return all(field in data for field in required)
    except Exception:
        return False

def build_berry(name):
    print(f"> Obtendo berry: {name}")

    berry = get(f"{BASE}/berry/{name}")

    return {
        "id": berry["id"],
        "nome": berry["name"],
        "growth_time": berry["growth_time"],
        "max_harvest": berry["max_harvest"],
        "natural_gift_power": berry["natural_gift_power"],
        "size": berry["size"],
        "smoothness": berry["smoothness"],
        "soil_dryness": berry["soil_dryness"],
        "item": berry["item"]["name"] if berry.get("item") else None,
        "firmness": berry["firmness"]["name"] if berry.get("firmness") else None,
        "natural_gift_type": (berry["natural_gift_type"]["name"] if berry.get("natural_gift_type") else None),
        "flavors": [{ "flavor": flavor["flavor"]["name"], "potency": flavor["potency"]}
            for flavor in berry.get("flavors", [])
        ]
    }

def process_berry(item, idx, total):
    name = item["name"]
    json_path = ROOT / f"{name}.json"

    print(f"\n[{idx}/{total}] {name}")

    if complete(json_path):
        print(f"[{idx}] {name}: CACHE OK")
        return

    try:
        data = build_berry(name)
        save_json(json_path, data)
        print(f"[{idx}] {name}: salvo")
    except Exception as e:
        print(f"[{idx}] {name}: erro -> {e}")

def main():
    ROOT.mkdir(exist_ok=True)

    berries = get(f"{BASE}/berry?limit=1000")["results"]

    total = len(berries)

    print(f"Berries encontradas: {total}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_berry, item, idx, total) for idx, item in enumerate(berries, start=1)]

        for future in as_completed(futures):
            try: future.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()