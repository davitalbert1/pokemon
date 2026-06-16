import json
from pathlib import Path

ROOT = Path("pokemon")

def remove_descricao(obj):
    if isinstance(obj, dict):
        if "descricao" in obj: del obj["descricao"]
        for v in obj.values(): remove_descricao(v)
    elif isinstance(obj, list):
        for item in obj: remove_descricao(item)

def process_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f: data = json.load(f)

        original = json.dumps(data, ensure_ascii=False)

        remove_descricao(data)

        updated = json.dumps(data, ensure_ascii=False)

        if original != updated:
            with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Atualizado: {path}")
        else:
            print(f"Sem mudanças: {path}")
    except Exception as e:
        print(f"Erro em {path}: {e}")

def main():
    for file in ROOT.rglob("*.json"): process_file(file)

if __name__ == "__main__":
    main()