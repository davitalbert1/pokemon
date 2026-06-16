import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib

SESSION = requests.Session()
BASE = "https://pokeapi.co/api/v2"
ROOT = Path("natures")
NATURE_JSON = "nature.json"
MANIFEST = "manifest.json"

@lru_cache(maxsize=None)
def get(url):
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f: return json.load(f)
    return None

def hash_data(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

def build_nature(name):
    n = get(f"{BASE}/nature/{name}")

    data = {
        "nome": n["name"],
        "id": n["id"],
        "stat_changes": {
            "aumenta": next((s["pokeathlon_stat"]["name"] for s in n.get("pokeathlon_stat_changes", [])), None)
        },
        "increase_stat": n["increased_stat"]["name"] if n.get("increased_stat") else None,
        "decreased_stat": n["decreased_stat"]["name"] if n.get("decreased_stat") else None,
        "likes_flavor": n["likes_flavor"]["name"] if n.get("likes_flavor") else None,
        "hates_flavor": n["hates_flavor"]["name"] if n.get("hates_flavor") else None,
        "pokeathlon_stat_changes": [
            {
                "max_change": s["max_change"],
                "pokeathlon_stat": s["pokeathlon_stat"]["name"]
            }
            for s in n.get("pokeathlon_stat_changes", [])
        ],
        "moves_battle_style_preferences": [
            {
                "low_hp_preference": m["low_hp_preference"],
                "high_hp_preference": m["high_hp_preference"],
                "move_battle_style": m["move_battle_style"]["name"]
            }
            for m in n.get("move_battle_style_preferences", [])
        ]
    }

    return data

def process_nature(item, idx, total):
    name = item["name"]
    json_path = ROOT / f"{name}.json"

    print(f"\n[{idx}/{total}] Nature: {name}")

    if json_path.exists():
        print("✔ já existe, pulando JSON")
        return

    data = build_nature(name)
    save_json(json_path, data)
    print(f"✔ salvo: {name}")

def main():
    ROOT.mkdir(exist_ok=True)

    data = get(f"{BASE}/nature?limit=10000")
    all_natures = data["results"]

    total = len(all_natures)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_nature, item, i, total) for i, item in enumerate(all_natures, start=1)]

        for f in as_completed(futures):
            try: f.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()