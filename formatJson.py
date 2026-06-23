import json
from pathlib import Path
from tqdm import tqdm

ROOT = Path(__file__).parent

def format_json(obj, indent=0):
    space = "  " * indent

    if isinstance(obj, dict):
        simple = all(not isinstance(v, (dict, list)) for v in obj.values())

        if simple and len(json.dumps(obj, ensure_ascii=False)) < 120:  return json.dumps(obj, ensure_ascii=False)

        lines = ["{"]
        items = list(obj.items())

        for i, (k, v) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            formatted = format_json(v, indent + 1)

            lines.append(f'{"  " * (indent + 1)}"{k}": {formatted}{comma}')

        lines.append(f"{space}")
        return "\n".join(lines)

    elif isinstance(obj, list):
        if not obj: return "[]"

        if all(not isinstance(i, (dict, list)) for i in obj):
            content = json.dumps(obj, ensure_ascii=False)
            if len(content) <= 120: return content

        lines = ["["]

        for i, item in enumerate(obj):
            comma = "," if i < len(obj) - 1 else ""
            formatted = format_json(item, indent + 1)

            lines.append(f'{"  " * (indent + 1)}{formatted}{comma}')

        lines.append(f"{space}]")
        return "\n".join(lines)

    return json.dumps(obj, ensure_ascii=False)

def process_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f: original = f.read()

        data = json.loads(original)
        formatted = format_json(data)

        if original == formatted: return "skipped", file_path

        with open(file_path, "w", encoding="utf-8") as f: f.write(formatted)

        return "formatted", file_path
    except Exception as e:
        return "error", file_path, str(e)

def main():
    json_files = list(ROOT.rglob("*.json"))

    formatted_count = 0
    skipped_count = 0
    error_count = 0

    for json_file in tqdm(json_files, desc="Formatando JSONs", unit="arquivo"):
        result = process_json_file(json_file)

        match result[0]:
            case "formatted": formatted_count += 1
            case "skipped": skipped_count += 1
            case "error":
                error_count += 1
                tqdm.write(f"✖ Erro em {result[1]}: {result[2]}")

    tqdm.write(f"✔ Formatados: {formatted_count} | " f"⏭ Ignorados: {skipped_count} | " f"✖ Erros: {error_count}")

if __name__ == "__main__":
    main()