from pathlib import Path

ROOT = Path("pokemon")
cardsInfo = "cards_manifest.json"
cards_folder_name = "cards"

def is_folder_empty(folder: Path):
    return not any(folder.iterdir())

def delete_cards_manifests_and_empty_cards():
    if not ROOT.exists():
        print("ROOT não existe")
        return

    deleted_manifests = 0
    deleted_empty_folders = 0

    for folder in ROOT.iterdir():
        if not folder.is_dir(): continue

        manifest_path = folder / cardsInfo
        cards_folder = folder / cards_folder_name

        if manifest_path.exists():
            manifest_path.unlink()
            print(f"Removido manifest: {manifest_path}")
            deleted_manifests += 1

        if cards_folder.exists() and cards_folder.is_dir():
            if is_folder_empty(cards_folder):
                cards_folder.rmdir()
                print(f"Removida pasta vazia: {cards_folder}")
                deleted_empty_folders += 1

    print("\nResumo:")
    print(f"- Manifests removidos: {deleted_manifests}")
    print(f"- Pastas cards vazias removidas: {deleted_empty_folders}")

if __name__ == "__main__":
    delete_cards_manifests_and_empty_cards()