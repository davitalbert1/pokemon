from pathlib import Path

ROOT = Path("pokemon")

def count_sprites():
    totals = {}
    all_counts = []

    if not ROOT.exists():
        print("Pasta ROOT não encontrada")
        return

    for pokemon_dir in ROOT.iterdir():
        if not pokemon_dir.is_dir():
            continue

        sprites_dir = pokemon_dir / "sprites"
        if not sprites_dir.exists():
            continue

        sprite_files = list(sprites_dir.glob("*.*"))
        count = len(sprite_files)

        totals[pokemon_dir.name] = count
        all_counts.append(count)

    if not all_counts:
        print("Nenhum sprite encontrado.")
        return

    media = sum(all_counts) / len(all_counts)

    print("\n=== SPRITES POR POKÉMON ===")
    for name, count in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        print(f"{name}: {count}")

    print("\n=== ESTATÍSTICAS ===")
    print(f"Pokémon analisados: {len(all_counts)}")
    print(f"Total de sprites: {sum(all_counts)}")
    print(f"Média de sprites por Pokémon: {media:.2f}")


if __name__ == "__main__":
    count_sprites()