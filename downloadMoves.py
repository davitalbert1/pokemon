import json
import requests
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
SESSION = requests.Session()
MOVES_DIR = Path("movimentos")

@lru_cache(maxsize=None)
def get(url):
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f: return json.load(f)
    return None

def build_move(move_url):
    data = get(move_url)

    return {
        "id": data["id"],
        "nome": data["name"],
        "tipo": data["type"]["name"] if data.get("type") else None,
        "classe": data["damage_class"]["name"] if data.get("damage_class") else None,
        "power": data.get("power"),
        "pp": data.get("pp"),
        "accuracy": data.get("accuracy"),
        "priority": data.get("priority"),
        "efeito": next((e["effect"] for e in data.get("effect_entries", []) if e["language"]["name"] == "en"), None),
        "efeito_curto": next((
                e["short_effect"]
                for e in data.get("effect_entries", [])
                if e["language"]["name"] == "en"
            ), None),
        "chance_efeito": data.get("effect_chance"),
        "estatisticas": [{"stat": s["stat"]["name"], "change": s["change"]} for s in data.get("stat_changes", [])],
    }

def process_move(move):
    name = move["name"]
    url = move["url"]

    path = MOVES_DIR / f"{name}.json"

    if path.exists():
        print(f"[SKIP] {name}")
        return

    print(f"[MOVE] baixando {name}")

    data = build_move(url)

    save_json(path, data)

def fetch_all_moves():
    data = get(f"{BASE}/move?limit=100000")
    return data["results"]

def run(limit=None):
    MOVES_DIR.mkdir(exist_ok=True)

    moves = fetch_all_moves()

    if limit: moves = moves[:limit]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_move, m) for m in moves]
        for f in as_completed(futures): f.result()

if __name__ == "__main__":
    run()