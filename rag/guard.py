"""Output guard: an answer may only tell on-call to run things that appear in a reviewed runbook.

Prompt instructions alone did not stop 8B models from repeating a destructive command planted in a
poisoned document (`--reset-offsets --to-latest`). This check is deterministic and does not trust the model:

- every code span (`inline` or fenced) in the answer is split into tokens, and each token must occur in the
  vocabulary of the reviewed corpus (documents not flagged `poisoned`);
- every CLI flag (`--something`) anywhere in the answer must occur in that vocabulary too;
- tokens that are just numbers, units or punctuation are allowed.

Token-level matching (rather than whole-command matching) tolerates a model shortening a real command, for
example dropping `--bootstrap-server kafka-1:9092`, while still catching flags and keywords that no
reviewed runbook contains.
"""
import re
from dataclasses import dataclass
from functools import lru_cache

from . import corpus

FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
INLINE = re.compile(r"`([^`\n]+)`")
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*", re.I)
TOKEN = re.compile(r"[A-Za-z_][\w.\-/:=*<>~\"']*")
STRIP = "\"'`.,;:()[]{}<>=*~"


def _norm(tok: str) -> str:
    return tok.strip(STRIP).lower()


@lru_cache(maxsize=1)
def reviewed_vocab() -> frozenset[str]:
    words: set[str] = set()
    for d in corpus.load():
        if d.poisoned:
            continue
        text = f"{d.title}\n{d.body}"
        for tok in text.split():
            words.add(_norm(tok))
            words.update(_norm(t) for t in re.split(r"[=,()\[\]{}|]", tok) if t)
        words.update(_norm(m) for m in TOKEN.findall(text))
    words.discard("")
    return frozenset(words)


def _span_tokens(span: str) -> list[str]:
    out = []
    for raw in span.split():
        for part in re.split(r"[=,()\[\]{}|]", raw):
            t = _norm(part)
            if t and re.search(r"[a-z]", t):
                out.append(t)
    return out


@dataclass
class Verdict:
    ok: bool
    unknown: list[str]


def check(text: str, vocab: frozenset[str] | None = None) -> Verdict:
    vocab = reviewed_vocab() if vocab is None else vocab
    spans = FENCE.findall(text)
    rest = FENCE.sub(" ", text)
    spans += INLINE.findall(rest)
    unknown: list[str] = []
    for span in spans:
        unknown += [t for t in _span_tokens(span) if t not in vocab]
    unknown += [f.lower() for f in FLAG.findall(text) if f.lower() not in vocab]
    unknown = list(dict.fromkeys(unknown))
    return Verdict(not unknown, unknown)


def withheld_message(reviewed_ids: list[str]) -> str:
    # Deliberately does not echo the blocked tokens: they may be the dangerous command.
    docs = ", ".join(f"[{d}]" for d in reviewed_ids) or "none"
    return ("Answer withheld: it recommended a command or setting that does not appear in any reviewed runbook. "
            "Check the reviewed documents directly: " + docs + ".")
