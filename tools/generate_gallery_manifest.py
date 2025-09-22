from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Union


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".heic", ".heif"}


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def load_existing_manifest(manifest_path: Path) -> Dict[str, str]:
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {manifest_path}: {exc}")
    existing: Dict[str, str] = {}
    if isinstance(data, dict):
        # Ungrouped
        ungrouped = data.get("ungrouped", [])
        if isinstance(ungrouped, list):
            for item in ungrouped:
                if isinstance(item, dict) and isinstance(item.get("file"), str):
                    f = item["file"]
                    c = item.get("caption")
                    existing[f] = c if isinstance(c, str) else ""
        # Albums
        albums = data.get("albums", [])
        if isinstance(albums, list):
            for album in albums:
                if not isinstance(album, dict):
                    continue
                folder = album.get("folder")
                photos = album.get("photos", [])
                if isinstance(folder, str) and isinstance(photos, list):
                    for item in photos:
                        if isinstance(item, dict) and isinstance(item.get("file"), str):
                            f = item["file"]
                            key = f"{folder}/{f}"
                            c = item.get("caption")
                            existing[key] = c if isinstance(c, str) else ""
        return existing
    raise SystemExit("manifest.json must be either an array (old) or an object with 'albums' and 'ungrouped' (new)")

def split_gallery(gallery_dir: Path) -> Tuple[List[Path], List[Path]]:
    dirs: List[Path] = []
    files: List[Path] = []
    for p in gallery_dir.iterdir():
        if p.is_dir():
            dirs.append(p)
        elif is_image_file(p):
            files.append(p)
    return sorted(dirs, key=lambda d: d.name.lower()), sorted(files, key=lambda f: f.name.lower())


def list_album_images(album_dir: Path) -> List[Path]:
    return sorted([p for p in album_dir.iterdir() if is_image_file(p)], key=lambda f: f.name.lower())


def build_albums_manifest(gallery_dir: Path, existing: Dict[str, str]) -> Dict[str, Union[List[Dict[str, Union[str, List[Dict[str, str]]]]], List[Dict[str, str]]]]:
    subdirs, root_files = split_gallery(gallery_dir)

    # Build albums
    albums: List[Dict[str, Union[str, List[Dict[str, str]]]]] = []
    for subdir in subdirs:
        images = list_album_images(subdir)
        if not images:
            continue
        cover = images[0].name
        photos: List[Dict[str, str]] = []
        for img in images:
            key = f"{subdir.name}/{img.name}"
            caption = existing.get(key, "")
            photos.append({"file": img.name, "caption": caption})
        albums.append({
            "title": subdir.name,
            "folder": subdir.name,
            "cover": cover,
            "photos": photos,
        })

    # Ungrouped
    ungrouped: List[Dict[str, str]] = []
    for f in root_files:
        caption = existing.get(f.name, "")
        ungrouped.append({"file": f.name, "caption": caption})

    return {"albums": albums, "ungrouped": ungrouped}


def write_json_atomic(path: Path, data) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    gallery_dir = repo_root / "assets" / "gallery"
    manifest_path = gallery_dir / "manifest.json"

    if not gallery_dir.exists():
        raise SystemExit(f"Gallery directory does not exist: {gallery_dir}")

    existing = load_existing_manifest(manifest_path)
    manifest = build_albums_manifest(gallery_dir, existing)
    write_json_atomic(manifest_path, manifest)

    print(f"Wrote {manifest_path} with {len(manifest)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())


