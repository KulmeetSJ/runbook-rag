"""Load the markdown corpus: YAML front matter + body."""
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import CORPUS_DIR


@dataclass(frozen=True)
class Doc:
    doc_id: str
    title: str
    service: str
    version: int
    path: str
    body: str
    poisoned: bool = False


def parse(path: Path, root: Path = CORPUS_DIR) -> Doc:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")
    _, front, body = text.split("---\n", 2)
    meta = yaml.safe_load(front)
    return Doc(
        doc_id=meta["id"],
        title=meta["title"],
        service=meta.get("service", "unknown"),
        version=int(meta.get("version", 1)),
        path=str(path.relative_to(root)),
        body=body.strip(),
        poisoned=bool(meta.get("poisoned", False)),
    )


def load(root: Path = CORPUS_DIR) -> list[Doc]:
    docs = [parse(p, root) for p in sorted(root.rglob("*.md"))]
    ids = [d.doc_id for d in docs]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate doc ids: {sorted(dupes)}")
    return docs
