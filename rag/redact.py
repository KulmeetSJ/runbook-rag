"""PII redaction before indexing. Three layers, in order of reliability:

1. Patterns (Presidio + regex): emails and phone numbers, including UK formats Presidio misses.
2. Directory deny-list (redaction/people.txt): known staff names, redacted in any phrasing.
3. NER backstop (Presidio + spaCy en_core_web_md) for names not in the directory.

NER alone is not reliable here. The small model tagged tool names as PERSON ("Kafka" 10x, "Prometheus",
"Git", "Argo Rollouts") and read "Call Grace Adeyemi" as an ORGANIZATION; the medium model still missed
"Ping Priya Raman". So an NER PERSON span is kept only where it contains a full-name shape (2-3 capitalised
words, none a known tech term). A lone first name ("ask Aisha") is not redacted. Recall of the NER layer on
names outside the directory is measured by `rag redaction-eval`.
"""
import re
from functools import lru_cache
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

PLACEHOLDERS = {"PERSON": "<PERSON>", "EMAIL_ADDRESS": "<EMAIL>", "PHONE_NUMBER": "<PHONE>"}

PHONE_PATTERNS = [
    Pattern("intl", r"\+\d{1,3}(?:[ -]?\d{2,4}){2,4}\b", 0.6),          # +44 7700 900123, +1 415 555 0142
    Pattern("uk_mobile", r"\b07\d{3} ?\d{6}\b", 0.6),                     # 07700 900456
    Pattern("uk_landline", r"\b0\d{2,4} ?\d{3,4} ?\d{4}\b", 0.5),         # 020 7946 0958
]

# Words that make a capitalised "name" a product or concept, not a person.
TECH_TERMS = {
    w.lower() for w in """
    Argo Rollouts Kafka Spring Grafana Explore Prometheus Docker Git Kyverno Terraform Conftest Loki Tempo
    Postgres PostgreSQL Java Kubernetes Helm Trivy Syft Sealed Secrets Cloud Actions GitHub Alertmanager
    Consumer Processor Gateway Ledger Drill Draft Freeze Releases Replaying Tuning Poison Alert Pull Rego
    Malformed Payments Platform Incident Database Shadow Observer Communications Contacts Owner Area
    Desktop Tempo Postmortem Explore Rotation Severity Escalation
    """.split()
}
_WORD = r"[A-Z][a-zà-öø-ÿ'’-]+"
NAME_SHAPE = re.compile(rf"^{_WORD}(?: {_WORD}){{1,2}}$")
NAME_INSIDE = re.compile(rf"{_WORD}(?: {_WORD}){{1,2}}")
DIRECTORY = Path(__file__).resolve().parent.parent / "redaction" / "people.txt"


def looks_like_person(text: str) -> bool:
    if not NAME_SHAPE.match(text):
        return False
    words = [w.lower().removesuffix("'s").removesuffix("’s") for w in text.split()]
    return not any(w in TECH_TERMS for w in words)


def directory_names(path: Path = DIRECTORY) -> list[str]:
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]


@lru_cache(maxsize=1)
def analyzer() -> AnalyzerEngine:
    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_md"}],
    }).create_engine()
    engine = AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])
    engine.registry.add_recognizer(PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=PHONE_PATTERNS))
    if names := directory_names():
        engine.registry.add_recognizer(PatternRecognizer(
            supported_entity="PERSON", name="directory",
            patterns=[Pattern("directory", r"\b(?:" + "|".join(map(re.escape, names)) + r")\b", 1.0)]))
    return engine


def find_pii(text: str) -> list[RecognizerResult]:
    results = analyzer().analyze(text, language="en", entities=list(PLACEHOLDERS), score_threshold=0.35)
    keep = []
    for r in results:
        if r.entity_type != "PERSON" or r.score >= 1.0:          # patterns and directory hits: keep as is
            keep.append(r)
            continue
        span = text[r.start:r.end]                                 # NER: keep only full-name shapes inside it
        for m in NAME_INSIDE.finditer(span):
            if looks_like_person(m.group()):
                keep.append(RecognizerResult("PERSON", r.start + m.start(), r.start + m.end(), r.score))
    # Resolve overlaps: longest span first, then highest score.
    keep.sort(key=lambda r: (-(r.end - r.start), -r.score))
    chosen: list[RecognizerResult] = []
    for r in keep:
        if all(r.end <= c.start or r.start >= c.end for c in chosen):
            chosen.append(r)
    return sorted(chosen, key=lambda r: r.start)


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Returns the redacted text and a count per entity type."""
    counts: dict[str, int] = {}
    out, last = [], 0
    for r in find_pii(text):
        out.append(text[last:r.start])
        out.append(PLACEHOLDERS[r.entity_type])
        counts[r.entity_type] = counts.get(r.entity_type, 0) + 1
        last = r.end
    out.append(text[last:])
    return "".join(out), counts
