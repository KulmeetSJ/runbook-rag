from pathlib import Path

import pytest

from rag import corpus, redact

SEEDS = [l for l in (Path(__file__).parent / "fixtures/seeded_pii.txt").read_text().splitlines()
         if l and not l.startswith("#")]


def test_every_seeded_pii_string_is_in_the_raw_corpus():
    raw = "\n".join(d.body for d in corpus.load())
    missing = [s for s in SEEDS if s not in raw]
    assert not missing, f"fixture out of date: {missing}"


def test_redaction_removes_every_seeded_pii_string():
    leaks = [(d.doc_id, s) for d in corpus.load() for s in SEEDS if s in redact.redact(d.body)[0]]
    assert not leaks


def test_no_false_positives_outside_the_documents_that_contain_pii():
    with_pii = {d.doc_id for d in corpus.load() if any(s in d.body for s in SEEDS)}
    flagged = {d.doc_id for d in corpus.load() if redact.redact(d.body)[1]}
    assert flagged == with_pii


@pytest.mark.parametrize("text", ["Kafka", "Argo Rollouts", "Spring Kafka's", "Grafana Explore", "Prometheus UI"])
def test_tech_terms_are_not_people(text):
    assert not redact.looks_like_person(text)


@pytest.mark.parametrize("text", ["Priya Raman", "Mei Lin Chen", "Tomás Herrera"])
def test_full_names_are_people(text):
    assert redact.looks_like_person(text)


def test_placeholders():
    out, counts = redact.redact("Call Grace Adeyemi on 07700 900456 or grace@example.org.")
    assert out == "Call <PERSON> on <PHONE> or <EMAIL>."
    assert counts == {"PERSON": 1, "PHONE_NUMBER": 1, "EMAIL_ADDRESS": 1}


@pytest.mark.parametrize("sentence", [
    "Ping Priya Raman about the canary.",      # en_core_web_md misses this one; the directory catches it
    "priya: Priya Raman owns it",
    "Escalate to Tomás Herrera if Kafka is down.",
])
def test_directory_names_are_redacted_in_any_phrasing(sentence):
    out, _ = redact.redact(sentence)
    assert "Priya Raman" not in out and "Tomás Herrera" not in out
    assert "Kafka" in out or "Kafka" not in sentence
