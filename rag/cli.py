"""rag: command-line interface."""
import textwrap
from pathlib import Path
from typing import Annotated

import typer

from . import ingest as ingest_mod
from . import retrieval, store
from .chunking import STRATEGIES
from .embeddings import EMBEDDERS

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def ingest(
    strategy: Annotated[list[str], typer.Option(help=f"one of {sorted(STRATEGIES)}; repeatable")] = ["heading"],
    embedder: Annotated[list[str], typer.Option(help=f"one of {sorted(EMBEDDERS)}; repeatable")] = ["bge-small"],
):
    """Redact, chunk, embed and index the corpus (one index per strategy x embedder)."""
    conn = store.connect()
    for s in strategy:
        for e in embedder:
            r = ingest_mod.run(conn, s, e)
            red = ", ".join(f"{k} {v}" for k, v in sorted(r.redacted.items()))
            typer.echo(f"{r.index_name:22} {r.docs} docs -> {r.chunks} chunks in {r.seconds:.1f}s; redacted: {red}")


@app.command()
def search(
    query: str,
    k: int = 5,
    mode: Annotated[str, typer.Option(help="vector | lexical | hybrid")] = "hybrid",
    index: Annotated[str, typer.Option(help="strategy:embedder")] = "heading:bge-small",
    full: bool = False,
):
    """Show the top-k chunks for a question."""
    conn = store.connect()
    for i, h in enumerate(retrieval.search(conn, index, query, k, mode), start=1):
        flag = "  [UNTRUSTED]" if h.poisoned else ""
        typer.echo(f"{i}. {h.chunk_id}  ({h.score:.4f}){flag}\n   {h.title} > {h.section or '-'}")
        body = h.content if full else textwrap.shorten(h.content, 180)
        typer.echo(textwrap.indent(body, "   ") + "\n")


@app.command()
def ask(
    question: str,
    model: Annotated[str, typer.Option(help="ollama:<model> or anthropic:<model>")] = "ollama:qwen3:8b",
    k: int = 5,
    mode: Annotated[str, typer.Option(help="vector | lexical | hybrid")] = "hybrid",
    index: Annotated[str, typer.Option(help="strategy:embedder")] = "heading:bge-small",
    show_context: bool = False,
    allow_unreviewed: Annotated[bool, typer.Option(help="also retrieve documents flagged as unreviewed")] = False,
    guard: Annotated[bool, typer.Option(help="withhold answers that recommend commands absent from reviewed runbooks")] = True,
):
    """Answer a question from the runbooks, citing the documents used."""
    from . import answer as answer_mod
    from .llm import get_llm
    a = answer_mod.ask(store.connect(), question, get_llm(model), index, mode, k,
                      allow_unreviewed=allow_unreviewed, use_guard=guard)
    if show_context:
        typer.echo(answer_mod.build_context(a.hits) + "\n" + "-" * 60)
    typer.echo(a.text + "\n")
    retrieved = ", ".join(dict.fromkeys(h.doc_id + (" [UNTRUSTED]" if h.poisoned else "") for h in a.hits))
    typer.echo(f"retrieved: {retrieved}")
    if a.withheld:
        typer.echo(f"guard: blocked {len(a.blocked)} token(s) not found in reviewed runbooks")
    if a.unknown_citations:
        typer.echo(f"WARNING: cited documents that were not retrieved: {', '.join(a.unknown_citations)}")
    c = a.completion
    typer.echo(f"{c.model}: {c.input_tokens} in / {c.output_tokens} out tokens, {c.ms} ms")


@app.command()
def stats():
    """List the indexes in the store."""
    for name, chunks, docs in store.indexes(store.connect()):
        typer.echo(f"{name:22} {chunks:4} chunks  {docs:3} docs")


@app.command("redaction-eval")
def redaction_eval(path: str = "redaction/ner_holdout.jsonl"):
    """Recall/precision of name redaction on sentences whose names are NOT in the directory."""
    import json

    from . import redact
    tp = fn = fp = 0
    for line in open(path, encoding="utf-8"):
        item = json.loads(line)
        out, _ = redact.redact(item["text"])
        found = [n for n in item["names"] if n not in out]
        tp += len(found)
        fn += len(item["names"]) - len(found)
        missed = [n for n in item["names"] if n in out]
        extra = out.count("<PERSON>") - len(found)
        fp += max(extra, 0)
        if missed or extra > 0:
            typer.echo(f"  {'MISS ' + ', '.join(missed) if missed else 'FALSE POSITIVE'}: {out}")
    recall = tp / (tp + fn) if tp + fn else 1.0
    precision = tp / (tp + fp) if tp + fp else 1.0
    typer.echo(f"names: {tp + fn}, redacted {tp}, missed {fn}, false positives {fp}")
    typer.echo(f"recall {recall:.2f}, precision {precision:.2f}")


@app.command("eval-retrieval")
def eval_retrieval(
    index: Annotated[list[str], typer.Option(help="strategy:embedder; repeatable")] = ["fixed512:bge-small", "fixed128:bge-small", "heading:bge-small"],
    mode: Annotated[list[str], typer.Option(help="repeatable")] = ["vector", "lexical", "hybrid"],
    out: str = "",
):
    """Recall@k and MRR for every index x mode on the golden set; writes JSON with per-question rows."""
    import datetime
    import json

    from . import evals
    conn = store.connect()
    golden = evals.load_golden()
    scored = [g for g in golden if g["type"] in ("answerable", "multi-doc")]
    results = {"date": datetime.date.today().isoformat(), "n_scored": len(scored), "configs": [], "abstention": []}
    typer.echo(f"{'index':20} {'mode':8} | dev R@1  R@3  R@5  MRR  | holdout R@5  MRR  | multi R@5 | p50 ms")
    for ix in index:
        for m in mode:
            r = evals.eval_config(conn, ix, m, scored)
            results["configs"].append(r)
            d, h, md = r["dev"], r["holdout"], r["multi_doc"]
            typer.echo(f"{ix:20} {m:8} |  {d['recall@1']:.2f} {d['recall@3']:.2f} {d['recall@5']:.2f} {d['mrr']:.2f} |"
                       f"      {h['recall@5']:.2f} {h['mrr']:.2f} |   {md['recall@5']:.2f}  | {r['p50_ms']}")
        results["abstention"].append(evals.abstention(conn, ix, golden))
    for a in results["abstention"]:
        typer.echo(f"abstention {a['index']}: answerable top-1 sim min {a['answerable_min']} (p10 {a['answerable_p10']}), "
                   f"unanswerable max {a['unanswerable_max']}; best threshold {a['best_threshold']} -> accuracy {a['best_accuracy']}")
    path = out or f"evals/results/retrieval-{results['date']}.json"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(results, indent=1))
    typer.echo(f"saved {path}")
