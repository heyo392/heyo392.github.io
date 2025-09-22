from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


FRONTMATTER_PATTERN = re.compile(r"^---\n([\s\S]*?)\n---\n", re.MULTILINE)


@dataclass
class BlogPostMeta:
    slug: str
    file: str
    title: str
    date: str
    summary: str
    tags: List[str]


def parse_frontmatter(text: str) -> dict:
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise SystemExit("Missing YAML frontmatter delimited by --- at the top of the file")
    body = match.group(1)
    # Extremely small YAML parser to avoid dependencies: handle key: value and tags: [a, b]
    data: dict = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            raise SystemExit(f"Invalid frontmatter line: {line}")
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        if value.startswith('[') and value.endswith(']'):
            inner = value[1:-1].strip()
            if not inner:
                data[key] = []
            else:
                data[key] = [v.strip().strip('"\'') for v in inner.split(',')]
        else:
            # strip surrounding quotes if any
            if (value.startswith('"') and value.endswith('"')) or (value.startswith('\'') and value.endswith('\'')):
                value = value[1:-1]
            data[key] = value
    return data


def extract_meta(md_path: Path) -> BlogPostMeta:
    text = md_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)

    title = fm.get('title')
    date = fm.get('date')
    summary = fm.get('summary', '')
    tags = fm.get('tags', [])

    if not isinstance(title, str) or not title:
        raise SystemExit(f"Missing or invalid 'title' in {md_path}")
    if not isinstance(date, str) or not date:
        raise SystemExit(f"Missing or invalid 'date' in {md_path}")
    if not isinstance(summary, str):
        raise SystemExit(f"Invalid 'summary' in {md_path}")
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        raise SystemExit(f"Invalid 'tags' in {md_path}")

    slug = md_path.stem.lower().strip()
    return BlogPostMeta(
        slug=slug,
        file=md_path.name,
        title=title,
        date=date,
        summary=summary,
        tags=tags,
    )


def discover_posts(blog_dir: Path) -> List[Path]:
    if not blog_dir.exists():
        raise SystemExit(f"Blog directory does not exist: {blog_dir}")
    files = [p for p in blog_dir.iterdir() if p.is_file() and p.suffix.lower() == '.md']
    return sorted(files, key=lambda p: p.name.lower())


def write_json_atomic(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    blog_dir = repo_root / "assets" / "blog"
    manifest_path = blog_dir / "manifest.json"

    posts = [extract_meta(p) for p in discover_posts(blog_dir)]
    # Sort reverse-chronological by date string; enforce ISO date format for stable sort
    posts_sorted = sorted(posts, key=lambda m: m.date, reverse=True)
    write_json_atomic(manifest_path, [asdict(p) for p in posts_sorted])
    print(f"Wrote {manifest_path} with {len(posts_sorted)} posts")
    return 0


if __name__ == "__main__":
    sys.exit(main())


