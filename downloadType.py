import json
import requests
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
SESSION = requests.Session()
TYPES_DIR = Path("tipos")

@lru_cache(maxsize=None)
def get(url):
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def build_type(type_url):
    data = get(type_url)

    return {
        "id": data["id"],
        "nome": data["name"],
        "double_damage_to": [t["name"] for t in data["damage_relations"]["double_damage_to"]],
        "double_damage_from": [t["name"] for t in data["damage_relations"]["double_damage_from"]],
        "half_damage_to": [t["name"] for t in data["damage_relations"]["half_damage_to"]],
        "half_damage_from": [t["name"] for t in data["damage_relations"]["half_damage_from"]],
        "no_damage_to": [t["name"] for t in data["damage_relations"]["no_damage_to"]],
        "no_damage_from": [t["name"] for t in data["damage_relations"]["no_damage_from"]],
        "moves": [m["name"] for m in data.get("moves", [])],
    }

def process_type(t):
    name = t["name"]
    url = t["url"]

    path = TYPES_DIR / f"{name}.json"

    if path.exists():
        print(f"[SKIP] {name}")
        return

    print(f"[TYPE] baixando {name}")

    data = build_type(url)
    save_json(path, data)

def fetch_all_types():
    data = get(f"{BASE}/type?limit=1000")
    return data["results"]

def run(limit=None):
    TYPES_DIR.mkdir(exist_ok=True)

    types = fetch_all_types()
    types = [t for t in types if t["name"] not in ("unknown", "shadow")]

    if limit: types = types[:limit]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_type, t) for t in types]
        for f in as_completed(futures): f.result()

if __name__ == "__main__":
    run()