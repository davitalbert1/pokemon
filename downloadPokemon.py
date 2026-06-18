import os
import json
import requests
import time
import hashlib
import re
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
cardsData = "cards_data.json"

def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    name = name.strip().strip(".")
    return name or "invalid"

@lru_cache(maxsize=None)
def get(url):
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

def sprites_complete(folder, sprite_map):
    for category, items in sprite_map.items():
        if not isinstance(items, dict): continue

        for key, url in items.items():
            if not url: continue

            filename = safe_filename(f"{category}_{key}") + os.path.splitext(url)[1]
            if not (folder / sprites / filename).exists(): return False

    return True

TCG_BASE = "https://api.pokemontcg.io/v2"

@lru_cache(maxsize=None)
def get_cards_api_cached(url, query_string):
    r = SESSION.get(
        url,
        params={"q": query_string},
        timeout=(10, 90)
    )
    r.raise_for_status()
    return r.json()

def cards_complete(folder, manifest):
    cards_folder = folder / "cards"
    if not cards_folder.exists(): return False
    expected = manifest.get("cards", [])
    if not expected: return False

    for card in expected:
        file_path = cards_folder / f"{card['id']}.jpg"
        if not file_path.exists(): return False

    return True

@lru_cache(maxsize=None)
def fetch_cards(name, retries=3):
    for attempt in range(retries):
        try:
            data = get_cards_api_cached(f"{TCG_BASE}/cards", f'name:"{name}"')
            return data.get("data", [])
        except Exception as e:
            print(f"Erro fetch_cards {name} tentativa {attempt+1}: {e}")
            time.sleep(2 ** attempt)

    return []

def download_cards_parallel(cards, folder):
    cards_folder = folder / "cards"
    cards_folder.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []

        for card in cards:
            img_url = get_best_image(card)
            card_id = card["id"]
            card_name = card.get("name", "unknown")

            file_path = cards_folder / f"{safe_filename(card_id)}.jpg"

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

    try:
        r = SESSION.get(url, timeout=60)

        if r.status_code != 200:
            print(f"Erro HTTP {r.status_code} -> {url}")
            return

        if len(r.content) < 500:
            print(f"Imagem suspeita (muito pequena): {url}")
            return

        with open(path, "wb") as f: f.write(r.content)

        print(f"Salvo em: {path}")

    except Exception as e:
        print(f"Erro ao baixar {url}: {e}")

def extract_sprites(pokemon_data):
    sprites = pokemon_data.get("sprites", {})

    result = {"normal": {}, "shiny": {}, "female": {}, "official_artwork": {}, "animated": {}, "icons": {}}

    def add(category, key, url):
        if url: result[category][key] = url

    base = [
        ("front_default", "normal", "front_default"),
        ("back_default", "normal", "back_default"),
        ("front_shiny", "shiny", "front_shiny"),
        ("back_shiny", "shiny", "back_shiny"),
        ("front_female", "female", "front_female"),
        ("back_female", "female", "back_female"),
    ]

    for key, cat, name in base: add(cat, key, sprites.get(key))

    artwork = sprites.get("other", {}).get("official-artwork", {})
    for k, v in artwork.items(): add("official_artwork", k, v)
    dream = sprites.get("other", {}).get("dream_world", {})
    for k, v in dream.items(): add("icons", f"dream_{k}", v)
    home = sprites.get("other", {}).get("home", {})
    for k, v in home.items(): add("icons", f"home_{k}", v)
    showdown = sprites.get("other", {}).get("showdown", {})
    for k, v in showdown.items(): add("animated", f"showdown_{k}", v)

    versions = sprites.get("versions", {})

    for gen, data in versions.items():
        for game, values in data.items():
            for k, v in values.items():
                if isinstance(v, str): add("icons", f"{gen}_{game}_{k}", v)

    return result

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

def cards_data_complete(folder):
    cards_json_path = folder / cardsData

    if not cards_json_path.exists():
        return False

    try:
        data = load_json(cards_json_path)

        if not isinstance(data, dict):
            return False

        if "total" not in data:
            return False

        cards = data.get("cards")

        if not isinstance(cards, list):
            return False

        if len(cards) == 0:
            return False

        required_fields = [
            "id",
            "name",
            "supertype",
            "set"
        ]

        for card in cards:
            if not all(field in card for field in required_fields):
                return False

            if "images" in card:
                return False

        return True

    except Exception:
        return False

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

def url_exists(url: str) -> bool:
    try:
        r = SESSION.head(url, timeout=10, allow_redirects=True)
        return r.status_code == 200
    except:
        return False

def get_best_image(card):
    return (
        card.get("images", {}).get("large")
        or card.get("images", {}).get("small")
    )

def get_best_image(card):
    urls = [card.get("images", {}).get("large"), card.get("images", {}).get("small")]

    for url in urls:
        if not url: continue

        try:
            r = SESSION.head(url, timeout=10)
            if r.status_code == 200: return url
        except:
            pass

    return None

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

        sprite_map = extract_sprites(sprite_data)
        manifest = {"hash": hash_map(sprite_map), "sprites": {k: v if isinstance(v, dict) else {} for k, v in sprite_map.items()}}
        save_json(manifest_path, manifest)

    sprite_map = manifest.get("sprites", {})

    safe_map = {}

    for k, v in sprite_map.items():
        if isinstance(v, dict): safe_map[k] = v
        else: safe_map[k] = {}

    sprite_map = safe_map

    if not sprites_complete(folder, sprite_map):
        print("> Baixando sprites faltantes")

        with ThreadPoolExecutor(max_workers=8) as sprite_executor:
            futures = []

            for category, items in sprite_map.items():
                if not isinstance(items, dict): continue

                for key, url in items.items():
                    if not url: continue

                    filename = safe_filename(f"{category}_{key}") + os.path.splitext(url)[1]
                    path = folder / sprites / filename

                    futures.append(sprite_executor.submit(download_file, url, path))

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

    if not cards_data_complete(folder):
        cards = fetch_cards(name)

        cards_json_path = folder / cardsData

        save_json(cards_json_path, {
            "total": len(cards),
            "cards": [
                {k: v for k, v in card.items() if k != "images"}
                for card in cards
            ]
        })

    print(f"Concluído: {name}")

def main():
    ROOT.mkdir(exist_ok=True)

    all_pokemon = get(f"{BASE}/pokemon?limit=2000")["results"]
    total = len(all_pokemon)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_pokemon, item, i, total) for i, item in enumerate(all_pokemon, start=1)]

        for f in as_completed(futures):
            try: f.result()
            except Exception as e: print("Erro:", e)

if __name__ == "__main__":
    main()
