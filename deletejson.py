from pathlib import Path

ROOT = Path("pokemon")
MANIFEST_NAME = "sprites_manifest.json"

def delete_sprite_manifests():
    if not ROOT.exists():
        print("Pasta pokemon não existe.")
        return

    deleted = 0

    for folder in ROOT.iterdir():
        if not folder.is_dir(): continue

        manifest_path = folder / MANIFEST_NAME

        if manifest_path.exists():
            try:
                manifest_path.unlink()
                print(f"Deletado: {manifest_path}")
                deleted += 1
            except Exception as e:
                print(f"Erro ao deletar {manifest_path}: {e}")

    print(f"\nTotal removidos: {deleted}")

if __name__ == "__main__":
    delete_sprite_manifests()