import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
ROOT = Path("super_contest_effects")
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

def get_flavor_texts(data):
    return [{"texto": entry["flavor_text"], "idioma": entry["language"]["name"]}
        for entry in data.get("flavor_text_entries", [])]

def build_super_contest_effect(effect_id):
    print(f"> Obtendo super-contest-effect: {effect_id}")

    data = get(f"{BASE}/super-contest-effect/{effect_id}")

    return {"id": data["id"], "appeal": data["appeal"], "flavor_texts": get_flavor_texts(data), "moves": [move["name"] for move in data.get("moves", [])]}

def complete(path):
    if not path.exists(): return False

    try:
        data = load_json(path)
        required = ["id", "appeal", "flavor_texts", "moves"]

        return all(field in data for field in required)
    except Exception:
        return False

def process_effect(item, idx, total):
    effect_id = item["url"].rstrip("/").split("/")[-1]

    json_path = ROOT / f"{effect_id}.json"

    print(f"\n[{idx}/{total}] {effect_id}")

    if complete(json_path):
        print(f"[{idx}] {effect_id}: CACHE OK")
        return

    try:
        data = build_super_contest_effect(effect_id)
        save_json(json_path, data)

        print(f"[{idx}] {effect_id}: salvo")

    except Exception as e:
        print(f"[{idx}] {effect_id}: erro -> {e}")

def main():
    ROOT.mkdir(exist_ok=True)

    effects = get(f"{BASE}/super-contest-effect?limit=10000")["results"]
    total = len(effects)

    print(f"Super Contest Effects encontrados: {total}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(process_effect, item, idx, total)
            for idx, item in enumerate(effects, start=1)
        ]

        for future in as_completed(futures):
            try: future.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()