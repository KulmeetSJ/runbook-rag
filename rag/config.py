import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"


def _load_dotenv() -> None:
    """Minimal .env loader (KEY=VALUE lines); real environment variables win."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def db_url() -> str:
    if url := os.environ.get("RAG_DB_URL"):
        return url
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise SystemExit("Set POSTGRES_PASSWORD in .env (see .env.example) or RAG_DB_URL")
    return f"postgresql://rag:{password}@localhost:5433/rag"
