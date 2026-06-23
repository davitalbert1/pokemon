from pathlib import Path

ROOT = Path("pokemon")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp",}

def analyze_images():
    pokemon_stats = []

    if not ROOT.exists():
        print("Pasta ROOT não encontrada")
        return

    for pokemon_dir in ROOT.iterdir():
        if not pokemon_dir.is_dir(): continue

        image_files = [f for f in pokemon_dir.rglob("*") if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]

        count = len(image_files)
        total_size = sum(f.stat().st_size for f in image_files)
        avg_size = total_size / count if count else 0

        pokemon_stats.append({"pokemon": pokemon_dir.name, "count": count, "total_size": total_size, "avg_size": avg_size,})

    if not pokemon_stats:
        print("Nenhuma imagem encontrada.")
        return

    total_images = sum(x["count"] for x in pokemon_stats)
    total_size = sum(x["total_size"] for x in pokemon_stats)

    avg_images_per_pokemon = total_images / len(pokemon_stats)
    avg_size_per_pokemon = total_size / len(pokemon_stats)

    print("\n=== IMAGENS POR POKÉMON ===")
    for item in sorted(pokemon_stats, key=lambda x: x["count"], reverse=True):
        print(
            f"{item['pokemon']}: "
            f"{item['count']} imagens | "
            f"{item['total_size'] / 1024:.2f} KB | "
            f"média {item['avg_size'] / 1024:.2f} KB/imagem"
        )

    print("\n=== ESTATÍSTICAS GERAIS ===")
    print(f"Pokémon analisados: {len(pokemon_stats)}")
    print(f"Total de imagens: {total_images}")
    print(f"Total de dados: {total_size / (1024 * 1024):.2f} MB")
    print(f"Média de imagens por Pokémon: {avg_images_per_pokemon:.2f}")
    print(f"Média de tamanho por Pokémon: {avg_size_per_pokemon / 1024:.2f} KB")

if __name__ == "__main__":
    analyze_images()