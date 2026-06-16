import json
from pathlib import Path
from datetime import datetime

ROOT = Path("pokemon")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = Path(f"{timestamp}.json")

items = []

for pokemon_dir in ROOT.iterdir():
    if not pokemon_dir.is_dir():
        continue

    json_file = pokemon_dir / "pokemon.json"

    if not json_file.exists():
        continue

    size = json_file.stat().st_size

    items.append({
        "pokemon": pokemon_dir.name,
        "size_bytes": size
    })

count = len(items)

sizes = [item["size_bytes"] for item in items]

report = {
    "timestamp": timestamp,
    "total_jsons": count,
    "average_size_bytes": round(sum(sizes) / count, 2) if count else 0,
    "total_size_bytes": sum(sizes),
    "smallest_size_bytes": min(sizes) if sizes else 0,
    "largest_size_bytes": max(sizes) if sizes else 0,
    "files": items
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"Relatório salvo em: {output_file}")
print(f"JSONs encontrados: {count}")
print(f"Tamanho médio: {report['average_size_bytes']:.2f} bytes")
print(f"Tamanho total: {report['total_size_bytes']} bytes")