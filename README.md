# Runbook RAG

A runbook assistant for an on-call engineer: ask "consumer lag is growing on payments.initiated" and get the
relevant runbook sections, later a cited answer. The point of the project is the **evaluation suite**:
retrieval and answer quality measured on a hand-labelled golden set, plus safety tests for PII and prompt injection.

> **All data is synthetic.** The corpus is 44 short runbooks and incident notes written for this repo, based on
> the failure modes of my other portfolio projects ([payflow-sim](https://github.com/KulmeetSJ/payflow-sim),
> [gitops-demo-platform](https://github.com/KulmeetSJ/gitops-demo-platform),
> [tf-drift-detector](https://github.com/KulmeetSJ/tf-drift-detector)). Names, emails and phone numbers in it are
> fake and seeded on purpose, to test redaction. Every number is a personal-project benchmark on a laptop.

## Status
- [x] Corpus: 44 docs (payflow, GitOps, Terraform drift, incident notes, policies), 3 of them poisoned with prompt injection
- [x] Ingestion: PII redaction → two chunking strategies → local embeddings → pgvector
- [x] Retrieval: vector, lexical (PostgreSQL full-text), hybrid (reciprocal rank fusion)
- [x] Retrieval evals: recall@1/3/5 and MRR on an 83-item golden set with a held-out split
- [x] Golden set human review (83 items, `reviewed: true`)
- [ ] Cited answers with Claude (`rag ask`), MCP server
- [ ] Answer evals: faithfulness (LLM judge, calibrated on hand grades), citation accuracy, abstention, injection
- [ ] CI eval gate on PRs

## Pipeline
```mermaid
flowchart LR
  c[corpus/*.md] --> r["redact<br/>patterns + directory + NER"] --> ch["chunk<br/>fixed | heading-aware"] --> e["embed<br/>bge-small, local"] --> pg[(PostgreSQL + pgvector)]
  q[question] --> v[vector] & l[lexical] --> f["RRF fusion"] --> k[top-k chunks]
  pg --- v & l
```

## Run it
```bash
cp .env.example .env            # set POSTGRES_PASSWORD
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m spacy download en_core_web_md
docker compose up -d --wait
.venv/bin/rag ingest --strategy heading --strategy fixed512 --strategy fixed128
.venv/bin/rag search "consumer lag is growing on payments.initiated"
.venv/bin/rag eval-retrieval
.venv/bin/pytest
```

## PII redaction (before anything is embedded or stored)
Three layers, because NER alone was not good enough:
1. **Patterns** for emails and phone numbers, including UK formats that Presidio's phone recogniser missed (`+44 7700 900123`).
2. **A staff directory deny-list** ([redaction/people.txt](redaction/people.txt)), so known names are redacted in any phrasing.
3. **NER backstop** (Presidio + spaCy `en_core_web_md`) for names not in the directory, filtered to full-name shapes.

Why: spaCy's small model tagged tool names as people ("Kafka" 10 times, "Prometheus", "Git", "Argo Rollouts"), and read
"Call Grace Adeyemi" as an organisation. The medium model still missed "Ping Priya Raman".

| Check | Result |
|---|---|
| Seeded PII in the corpus (12 names, 9 emails, 8 phones) | **29 / 29 redacted**, 0 false positives in the other 40 docs |
| Seeded PII strings in the vector store | **0** (integration test) |
| NER backstop on 24 held-out sentences, names not in the directory ([ner_holdout.jsonl](redaction/ner_holdout.jsonl)) | recall **0.94** (16/17, missed "Chloe Dubois"), precision 1.00 on 9 sentences full of tool names. Measured once, not tuned against |

## Retrieval results (first run, 2026-11-24)
71 scored questions (answerable + multi-doc; 52 dev, 19 holdout; holdout q083 was added after this run). Relevance is labelled per document, so all chunking
strategies are scored on the same labels. Embeddings: `BAAI/bge-small-en-v1.5` (384 d, local ONNX).

| Chunking | Mode | R@1 | R@3 | R@5 | MRR | multi-doc R@5 |
|---|---|---|---|---|---|---|
| fixed 512 tokens (= whole doc) | vector | 0.66 | 0.89 | 0.92 | 0.86 | 0.83 |
| fixed 512 tokens (= whole doc) | hybrid | 0.67 | 0.88 | 0.93 | 0.87 | 0.89 |
| fixed 128 tokens | vector | 0.68 | 0.79 | 0.89 | 0.84 | 0.80 |
| fixed 128 tokens | hybrid | 0.66 | 0.80 | 0.84 | 0.83 | 0.70 |
| heading-aware | vector | **0.73** | 0.85 | **0.93** | **0.90** | 0.80 |
| heading-aware | hybrid | 0.69 | **0.89** | **0.93** | 0.88 | 0.80 |

Dev split shown; full output in [evals/results/](evals/results/). Early observations, to be tested in the experiments grid:
- At equal chunk size, heading-aware beats structure-blind windows (R@3 0.85 vs 0.79, vector).
- Hybrid is not a free win: it helps whole-doc chunks and hurts small fixed chunks, where lexical search is weak.
- The comparison with whole-doc chunks is not yet fair: 5 whole docs carry ~3x the text of 5 heading chunks. The grid will compare at an equal token budget.
- Small sample: 0.04 on 52 dev questions is about 2 questions.
- **The poisoned doc reaches the top 3** for "how do I reset consumer offsets to fix lag" (vector). Retrieval cannot keep injected text out, so the answer prompt has to treat retrieved text as untrusted data.

## License
MIT
