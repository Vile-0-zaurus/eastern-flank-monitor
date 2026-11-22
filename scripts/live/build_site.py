"""Build a static site folder. The admin page is never copied. No network."""
from __future__ import annotations

import shutil
from pathlib import Path


SKIP = {"admin"}


def build_site(frontend: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for path in frontend.iterdir():
        if path.name in SKIP or path.name.startswith("."):
            continue
        target = dest / path.name
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)
    return dest
