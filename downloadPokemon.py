import os
import json
import requests
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path

SESSION = requests.Session()
BASE = "https://pokeapi.co/api/v2"
ROOT = Path("pokemon")
ONLY_JSONS = False
separator = 60
pokemonInfo = "pokemon.json"
sprites = "sprites"
sprintesInfo = "sprites_manifest.json"
cardsInfo = "cards_manifest.json"

@lru_cache(maxsize=None)
def get(url):
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

def sprites_complete(folder, sprite_map):
    for key, url in sprite_map.items():
        filename = key.replace("/", "_") + os.path.splitext(url)[1]
        if not (folder / sprites / filename).exists(): return False
    return True

TCG_BASE = "https://api.pokemontcg.io/v2"

@lru_cache(maxsize=None)
def get_cards_api(url, params_str=""):
    params = json.loads(params_str) if params_str else None
    r = SESSION.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def cards_complete(folder, manifest):
    cards_folder = folder / "cards"

    if not cards_folder.exists(): return False

    expected = manifest.get("cards", [])

    for card in expected:
        file_path = cards_folder / f"{card['id']}.jpg"
        if not file_path.exists(): return False

    return True

def fetch_cards(name, retries=3):
    for attempt in range(retries):
        try: return get_cards_api(f"{TCG_BASE}/cards", json.dumps({"q": f'name:"{name}"'})).get("data", [])
        except requests.exceptions.Timeout: print(f"Timeout {name}, tentativa {attempt+1}")

    return []

def download_cards_parallel(cards, folder):
    cards_folder = folder / "cards"
    cards_folder.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []

        for card in cards:
            img_url = card["images"]["large"]
            card_id = card["id"]
            card_name = card.get("name", "unknown")

            file_path = cards_folder / f"{card_id}.jpg"

            print(f"> Baixando card: {card_name} ({card_id})")

            futures.append(executor.submit(download_file, img_url, file_path))

        for f in as_completed(futures): f.result()

def hash_map(d):
    return hashlib.md5(json.dumps(d, sort_keys=True).encode()).hexdigest()

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"> Salvando JSON em: {path}")
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    if path.exists():
        with open(path, encoding="utf-8") as f: return json.load(f)
    return None

def download_file(url, path):
    if not url:
        print("- URL vazia, ignorando.")
        return

    if path.exists():
        print(f"- Já existe: {path.name}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    r = SESSION.get(url, timeout=60)

    if r.ok:
        with open(path, "wb") as f: f.write(r.content)
        print(f"Salvo em: {path}")
    else:
        print(f"Erro HTTP {r.status_code}")

def flatten_sprites(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}/{k}" if prefix else k
            if isinstance(v, str) and v.startswith("http"): out[p] = v
            elif isinstance(v, (dict, list)): out.update(flatten_sprites(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj): out.update(flatten_sprites(v, f"{prefix}/{i}"))
    return out

@lru_cache(maxsize=None)
def get_type_data(type_name):
    return get(f"{BASE}/type/{type_name}")

def type_relations(types):
    mult = {}

    for t in types:
        data = get_type_data(t)

        for rel, factor in [("double_damage_from", 2), ("half_damage_from", 0.5), ("no_damage_from", 0)]:
            for item in data["damage_relations"][rel]:
                name = item["name"]
                if name not in mult: mult[name] = 1
                mult[name] *= factor

    return {
        "fraquezas": [k for k, v in mult.items() if v > 1],
        "resistencias": [k for k, v in mult.items() if 0 < v < 1],
        "imunidades": [k for k, v in mult.items() if v == 0]
    }

@lru_cache(maxsize=None)
def get_evolution_chain(url):
    return get(url)

@lru_cache(maxsize=None)
def get_growth(url):
    return get(url)

def evolution_chain(url, current_name):
    chain = get_evolution_chain(url)["chain"]

    result = []

    def walk(node, prev=None):
        name = node["species"]["name"]
        next_names = [e["species"]["name"] for e in node["evolves_to"]]

        if name == current_name:
            result.append({
                "pokemon": name,
                "anterior": prev,
                "proximo": next_names,
                "conditions": clean_evolution_details(node["evolution_details"])
            })

        for e in node["evolves_to"]:
            walk(e, name)

    walk(chain)

    return result

def get_flavor_text(species):
    for entry in species["flavor_text_entries"]:
        if entry["language"]["name"] == "en": return entry["flavor_text"].replace("\n", " ")
    return None

def build_pokemon(pid):
    print("> Obtendo informações da espécie")

    p = get(f"{BASE}/pokemon/{pid}")
    species = get(p["species"]["url"])
    growth = get_growth(species["growth_rate"]["url"])
    types = [t["type"]["name"] for t in p.get("types", [])]

    data = {
        "nome": p["name"],
        "numero_pokedex": p["id"],
        "altura": p["height"],
        "peso": p["weight"],
        "experiencia_base": p["base_experience"],
        "ordem": p["order"],
        "lendario": species.get("is_legendary"),
        "mitico": species.get("is_mythical"),
        "bebe": species.get("is_baby"),
        "has_gender_differences": species.get("has_gender_differences"),
        "generation": species["generation"]["name"] if species.get("generation") else None,
        "color": species["color"]["name"] if species.get("color") else None,
        "habitat": species["habitat"]["name"] if species.get("habitat") else None,
        "growth_rate": species["growth_rate"]["name"] if species.get("growth_rate") else None,
        "experiencia_por_nivel": {
            "formula": growth.get("formula"),
            "levels": [{ "level": l["level"], "experience": l["experience"]} for l in growth.get("levels", [])]
        },
        "capture_rate": species.get("capture_rate"),
        "base_happiness": species.get("base_happiness"),
        "tempo_ovo": species.get("hatch_counter"),
        "genus": next((g["genus"] for g in species.get("genera", []) if g["language"]["name"] == "en"), None),
        "flavor_texts": list(dict.fromkeys([
            entry["flavor_text"].replace("\n", " ")
            for entry in species.get("flavor_text_entries", [])
            if entry["language"]["name"] == "en"
        ])),
        "egg_groups": [g["name"] for g in species.get("egg_groups", [])],
        "habilidades": [{"nome": a["ability"]["name"], "hidden": a["is_hidden"], "slot": a["slot"]} for a in p.get("abilities", [])],
        "tipos": types,
        "relacoes_tipos": type_relations(types),
        "estatisticas": {s["stat"]["name"]: s["base_stat"] for s in p.get("stats", [])},
        "evolucoes": evolution_chain(species["evolution_chain"]["url"], p["name"]),
    }

    return data, p[sprites], p["name"]

def clean_evolution_details(details):
    cleaned = []

    for d in details:
        cleaned.append({
            "trigger": d["trigger"]["name"] if d.get("trigger") else None,
            "min_level": d.get("min_level"),
            "item": d["item"]["name"] if d.get("item") else None,
            "location": d["location"]["name"] if d.get("location") else None
        })

    return cleaned

def complete(folder):
    cards_folder = folder / "cards"
    if not cards_folder.exists(): return False
    cards_files = list(cards_folder.glob("*.jpg"))
    if len(cards_files) == 0: return False

    sprites_folder = folder / "sprites"
    if not sprites_folder.exists(): return False

    path = folder / pokemonInfo
    if not path.exists(): return False

    try:
        data = load_json(path)

        required = [
            "nome", "numero_pokedex", "altura", "peso", "experiencia_base",
            "ordem", "lendario", "mitico", "bebe",
            "has_gender_differences", "generation", "color", "habitat",
            "growth_rate", "capture_rate", "base_happiness",
            "tempo_ovo", "genus", "flavor_texts", "egg_groups",
            "habilidades", "tipos", "relacoes_tipos",
            "estatisticas", "evolucoes", "experiencia_por_nivel"
        ]

        if not all(field in data for field in required): return False

        rel = data.get("relacoes_tipos", {})
        if "fraquezas" not in rel: return False
        if "resistencias" not in rel: return False
        if "imunidades" not in rel: return False

        return True
    except Exception:
        return False

def process_pokemon(item, idx, total):
    name = item["name"]
    folder = ROOT / name

    json_path = folder / pokemonInfo
    manifest_path = folder / sprintesInfo

    print(f"\n[{idx}/{total}] {name}")

    sprite_data = None

    if json_path.exists():
        if complete(folder):
            print("> Dataset completo (CACHE OK)")
        else:
            print("> JSON inválido — regenerando")
            data, sprite_data, _ = build_pokemon(name)
            save_json(json_path, data)
    else:
        print("> JSON ausente")
        data, sprite_data, _ = build_pokemon(name)
        save_json(json_path, data)

    manifest = load_json(manifest_path)

    if manifest is None:
        print("> Manifest ausente")

        if sprite_data is None: _, sprite_data, _ = build_pokemon(name)

        sprite_map = flatten_sprites(sprite_data)
        manifest = {"hash": hash_map(sprite_map), "sprites": sprite_map}
        save_json(manifest_path, manifest)

    sprite_map = manifest.get("sprites", {})

    if not sprites_complete(folder, sprite_map):
        print("> Baixando sprites faltantes")

        with ThreadPoolExecutor(max_workers=20) as sprite_executor:
            futures = []

            for key, url in sprite_map.items():
                filename = key.replace("/", "_") + os.path.splitext(url)[1]
                futures.append(sprite_executor.submit(download_file, url, folder / sprites / filename))

            for f in as_completed(futures): f.result()
    else:
        print("> Sprites OK")

    print("> Baixando cards")

    cards_manifest_path = folder / cardsInfo
    cards_manifest = load_json(cards_manifest_path)

    if cards_manifest is None:
        print("> Obtendo lista de cards")

        cards = fetch_cards(name)

        cards_manifest = {
            "total": len(cards),
            "cards": [{"id": card["id"], "name": card["name"], "image": card["images"]["large"]} for card in cards]
        }

        save_json(cards_manifest_path, cards_manifest)
    else:
        print("> Manifest de cards OK")

        cards = [{
                "id": card["id"],
                "name": card["name"],
                "images": {"large": card["image"]}
            } for card in cards_manifest.get("cards", [])]

    if not cards_complete(folder, cards_manifest): download_cards_parallel(cards, folder)
    else: print("> Cards OK")

    print(f"Concluído: {name}")

def main():
    ROOT.mkdir(exist_ok=True)

    all_pokemon = get(f"{BASE}/pokemon?limit=100000")["results"]
    total = len(all_pokemon)

    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(process_pokemon, item, i, total) for i, item in enumerate(all_pokemon, start=1)]

        for f in as_completed(futures):
            try: f.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()
