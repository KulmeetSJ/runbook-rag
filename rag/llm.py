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

    def __init__(self, model: str, host: str | None = None, think: bool = False, timeout: float = 600):
        self.model = model
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


def get_llm(spec: str) -> LLM:
    provider, _, model = spec.partition(":")
    if provider == "ollama" and model:
        return OllamaLLM(model)
    if provider == "anthropic" and model:
        return AnthropicLLM(model)
    raise SystemExit(f"Unknown model {spec!r}; use ollama:<model> or anthropic:<model>")
