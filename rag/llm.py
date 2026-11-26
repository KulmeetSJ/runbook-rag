"""LLM backends behind one small interface.

A model is named "<provider>:<model>", for example "ollama:qwen3:8b" or "anthropic:claude-haiku-5-5".
Ollama runs locally at zero cost and is what the published benchmarks use. The Anthropic backend is
kept working (unit-tested with a stub client) so the same evals can run on Claude when credits exist.
"""
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    ms: int


class LLM(Protocol):
    name: str

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> Completion: ...


class OllamaLLM:
    """Ollama /api/chat. Greedy decoding so runs are repeatable; qwen3's thinking mode is off by default."""

    def __init__(self, model: str, host: str | None = None, think: bool = False, timeout: float = 600,
                 json_format: bool = False):
        self.model = model
        self.json_format = json_format
        self.name = f"ollama:{model}"
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        if not self.host.startswith("http"):
            self.host = "http://" + self.host
        self.think = think
        self.timeout = timeout

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> Completion:
        body = {
            "model": self.model,
            "stream": False,
            "think": self.think,
            "options": {"temperature": 0, "seed": 0, "num_predict": max_tokens, "num_ctx": 16384},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if self.json_format:
            body["format"] = "json"
        req = urllib.request.Request(f"{self.host}/api/chat", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        t = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                r = json.load(resp)
        except urllib.error.URLError as e:
            raise SystemExit(f"Ollama not reachable at {self.host} ({e}). Start the Ollama app or `ollama serve`.")
        return Completion(text=r["message"]["content"].strip(), model=self.name,
                          input_tokens=r.get("prompt_eval_count", 0), output_tokens=r.get("eval_count", 0),
                          ms=int((time.perf_counter() - t) * 1000))


class AnthropicLLM:
    """Claude via the official SDK. Current models reject non-default sampling params, so there is no
    temperature here; depth is controlled with output_config.effort."""

    def __init__(self, model: str, effort: str = "low", client=None):
        self.model = model
        self.name = f"anthropic:{model}"
        self.effort = effort
        if client is None:
            import anthropic  # optional dependency: pip install -e '.[anthropic]'
            client = anthropic.Anthropic()
        self.client = client

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> Completion:
        t = time.perf_counter()
        r = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": user}],
        )
        if r.stop_reason == "refusal":
            text = "[refused]"
        else:
            text = "".join(b.text for b in r.content if b.type == "text").strip()
        return Completion(text=text, model=self.name, input_tokens=r.usage.input_tokens,
                          output_tokens=r.usage.output_tokens, ms=int((time.perf_counter() - t) * 1000))


class CachedLLM:
    """Wraps an LLM with an append-only JSONL cache keyed by (model, system, user, max_tokens).

    Decoding is greedy, so a cache hit is what the model would say again. The cache is committed, which lets CI
    replay the last evaluated answers through the rule checks without running a model (replay_only=True).
    """

    def __init__(self, inner: LLM | None, path, replay_only: bool = False, name: str | None = None):
        import hashlib
        from pathlib import Path
        self.inner, self.path, self.replay_only = inner, Path(path), replay_only
        self.name = name or inner.name
        self._hash = hashlib.sha256
        self.hits = self.misses = 0
        self.entries: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    e = json.loads(line)
                    self.entries[e["key"]] = e

    def key(self, system: str, user: str, max_tokens: int) -> str:
        return self._hash(json.dumps([self.name, system, user, max_tokens]).encode()).hexdigest()[:32]

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> Completion:
        k = self.key(system, user, max_tokens)
        if k in self.entries:
            self.hits += 1
            e = self.entries[k]
            return Completion(e["text"], e["model"], e["input_tokens"], e["output_tokens"], e["ms"])
        if self.replay_only or self.inner is None:
            raise KeyError(f"no cached completion for {self.name} (prompt changed?); re-run the eval locally")
        self.misses += 1
        c = self.inner.complete(system, user, max_tokens)
        e = {"key": k, "text": c.text, "model": c.model, "input_tokens": c.input_tokens,
             "output_tokens": c.output_tokens, "ms": c.ms}
        self.entries[k] = e
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return c


def get_llm(spec: str) -> LLM:
    provider, _, model = spec.partition(":")
    if provider == "ollama" and model:
        return OllamaLLM(model)
    if provider == "anthropic" and model:
        return AnthropicLLM(model)
    raise SystemExit(f"Unknown model {spec!r}; use ollama:<model> or anthropic:<model>")
