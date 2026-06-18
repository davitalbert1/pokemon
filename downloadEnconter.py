import json
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://pokeapi.co/api/v2"
ROOT = Path("encounter_methods")
CACHE = {}

def get(url):
    if url in CACHE:
        return CACHE[url]

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    data = r.json()
    CACHE[url] = data

    return data

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    return None

def get_names(data):
    return [
        {
            "idioma": entry["language"]["name"],
            "nome": entry["name"]
        }
        for entry in data.get("names", [])
    ]

def build_encounter_method(name):
    print(f"> Obtendo encounter-method: {name}")

    data = get(f"{BASE}/encounter-method/{name}")

    return {
        "id": data["id"],
        "nome": data["name"],
        "ordem": data["order"],
        "nomes": get_names(data)
    }

def complete(path):
    if not path.exists():
        return False

    try:
        data = load_json(path)

        required = [
            "id",
            "nome",
            "ordem",
            "nomes"
        ]

        return all(field in data for field in required)

    except Exception:
        return False

def process_method(item, idx, total):
    name = item["name"]

    json_path = ROOT / f"{name}.json"

    print(f"\n[{idx}/{total}] {name}")

    if complete(json_path):
        print(f"[{idx}] {name}: CACHE OK")
        return

    try:
        data = build_encounter_method(name)
        save_json(json_path, data)

        print(f"[{idx}] {name}: salvo")

    except Exception as e:
        print(f"[{idx}] {name}: erro -> {e}")

def main():
    ROOT.mkdir(exist_ok=True)

    methods = get(f"{BASE}/encounter-method?limit=10000")["results"]
    total = len(methods)

    print(f"Encounter Methods encontrados: {total}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                process_method,
                item,
                idx,
                total
            )
            for idx, item in enumerate(methods, start=1)
        ]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print("Erro:", e)

if __name__ == "__main__":
    main()