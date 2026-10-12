#!/usr/bin/env python3
"""Print unique digest-pinned container images referenced in orchestration manifests."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_RE = re.compile(
    r"^\s*image:\s*([^\s\"']+@sha256:[a-f0-9]{64})\s*$",
    re.MULTILINE,
)
SCAN_PATHS = (
    ROOT / "docker-compose.yml",
    *sorted((ROOT / "k8s" / "base").glob("*.yaml")),
)


def main() -> None:
    images: set[str] = set()
    for path in SCAN_PATHS:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        images.update(IMAGE_RE.findall(text))
    for image in sorted(images):
        print(image)


if __name__ == "__main__":
    main()
