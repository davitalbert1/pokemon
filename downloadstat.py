import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
ROOT = Path("stats")
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

def get_names(data):
    return {entry["language"]["name"]: entry["name"] for entry in data.get("names", [])}

def build_stat(name):
    print(f"> Obtendo stat: {name}")

    data = get(f"{BASE}/stat/{name}")

    return {
        "id": data["id"],
        "nome": data["name"],
        "battle_only": data.get("is_battle_only"),
        "game_index": data.get("game_index"),
        "move_damage_class": (data["move_damage_class"]["name"] if data.get("move_damage_class") else None),
        "nomes": get_names(data),

        "affecting_moves": {
            "increase": [{"move": item["move"]["name"], "change": item["change"]}
                for item in data.get("affecting_moves", {}).get("increase", [])],
            "decrease": [{"move": item["move"]["name"], "change": item["change"]}
                for item in data.get("affecting_moves", {}).get("decrease", [])]
        },
        "affecting_natures": {
            "increase": [nature["name"] for nature in data.get("affecting_natures", {}).get("increase", [])],
            "decrease": [nature["name"] for nature in data.get("affecting_natures", {}).get("decrease", [])]
        }
    }

def complete(path):
    if not path.exists(): return False

    try:
        data = load_json(path)
        required = ["id", "nome", "battle_only", "game_index", "move_damage_class", "nomes", "affecting_moves", "affecting_natures"]

        return all(field in data for field in required)

    except Exception:
        return False

def process_stat(item, idx, total):
    name = item["name"]

    json_path = ROOT / f"{name}.json"

    print(f"\n[{idx}/{total}] {name}")

    if complete(json_path):
        print(f"[{idx}] {name}: CACHE OK")
        return

    try:
        data = build_stat(name)
        save_json(json_path, data)

        print(f"[{idx}] {name}: salvo")

    except Exception as e:
        print(f"[{idx}] {name}: erro -> {e}")

def main():
    ROOT.mkdir(exist_ok=True)

    stats = get(f"{BASE}/stat?limit=10000")["results"]
    total = len(stats)

    print(f"Stats encontradas: {total}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(process_stat, item, idx, total)
            for idx, item in enumerate(stats, start=1)
        ]

        for future in as_completed(futures):
            try: future.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()