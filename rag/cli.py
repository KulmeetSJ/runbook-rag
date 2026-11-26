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


@app.command("eval-answers")
def eval_answers(
    model: Annotated[str, typer.Option(help="answer model")] = "ollama:qwen3:8b",
    judge_model: Annotated[str, typer.Option(help="judge model; 'none' skips the correctness judge")] = "ollama:qwen3:8b",
    config: Annotated[list[str], typer.Option(help="prompt-only | defended; repeatable")] = ["prompt-only", "defended"],
    replay: Annotated[bool, typer.Option(help="use cached completions only (CI); fails if a prompt changed")] = False,
    out: str = "",
):
    """Answer every golden question and score abstention, citations, injection and (judged) correctness."""
    import datetime
    import json

    from . import answer_evals, evals
    from .llm import CachedLLM, OllamaLLM, get_llm
    inner = None if replay else get_llm(model)
    llm = CachedLLM(inner, answer_evals.CACHE, replay_only=replay, name=model)
    judge = None
    if judge_model != "none":
        jinner = None
        if not replay:
            jinner = OllamaLLM(judge_model.split(":", 1)[1], json_format=True) if judge_model.startswith("ollama:") \
                else get_llm(judge_model)
        judge = CachedLLM(jinner, answer_evals.CACHE, replay_only=replay, name=f"judge:{judge_model}")
    golden = evals.load_golden()
    res = answer_evals.run(store.connect(), golden, llm, judge, config, progress=typer.echo)
    hdr = f"{'config':12} | answered cites-gold | correct dev   holdout     | abstain ok | injection leaks | withheld | p50 ms"
    typer.echo(hdr)
    for name, r in res.items():
        s = r["summary"]
        typer.echo(f"{name:12} | {s['answered']:.2f}     {s['cites_gold']:.2f}      | "
                   f"{s.get('correctness_dev', float('nan')):.2f} ({s.get('correct_dev', '-')}) "
                   f"{s.get('correctness_holdout', float('nan')):.2f} ({s.get('correct_holdout', '-')}) | "
                   f"{s['abstain_ok']:.2f}       | {s['injection_violations']}/{s['injection_n']}             | "
                   f"{s['withheld_answerable']:8} | {s['p50_ms']}")
    typer.echo(f"model calls: answers {llm.misses} new / {llm.hits} cached"
               + (f", judge {judge.misses} new / {judge.hits} cached" if judge else ""))
    date = datetime.date.today().isoformat()
    payload = {"date": date, "model": model, "judge": judge_model, "fingerprint": answer_evals.fingerprint(),
               "configs": res}
    path = out or f"evals/results/answers-{model.replace(':', '_').replace('/', '_')}-{date}.json"
    if not replay:
        Path(path).write_text(json.dumps(payload, indent=1, ensure_ascii=False))
        typer.echo(f"saved {path}")
    return payload


@app.command()
def gate(thresholds: str = "evals/gate.json"):
    """CI gate: live retrieval eval + committed answer-eval results, checked against thresholds.

    Fails when retrieval drops below its floor, when the committed answer results are stale (prompts, golden
    set, corpus or retrieval code changed since they were produced), when they miss a threshold, or when the
    current output guard no longer blocks a recorded unsafe raw answer."""
    import json

    from . import answer_evals, evals, guard
    cfg = json.loads(Path(thresholds).read_text())
    failures: list[str] = []

    def check(name, value, op, limit):
        ok = value is not None and (value >= limit if op == ">=" else value <= limit)
        typer.echo(f"  {'PASS' if ok else 'FAIL'}  {name}: {value} (need {op} {limit})")
        if not ok:
            failures.append(name)

    typer.echo("retrieval (live):")
    conn = store.connect()
    golden = evals.load_golden()
    scored = [g for g in golden if g["type"] in ("answerable", "multi-doc")]
    r = cfg["retrieval"]
    res = evals.eval_config(conn, r["index"], r["mode"], scored)
    for split in ("dev", "holdout"):
        for metric, limit in r[split].items():
            check(f"{split} {metric}", res[split][metric], ">=", limit)

    a = cfg["answers"]
    data = json.loads(Path(a["results"]).read_text())
    typer.echo(f"answers ({a['results']}):")
    fp = answer_evals.fingerprint()
    check("results are fresh (fingerprint matches)", int(data.get("fingerprint") == fp), ">=", 1)
    golden_by_id = {g["id"]: g for g in golden}
    for conf, limits in a["configs"].items():
        s = data["configs"][conf]["summary"]
        for metric, (op, limit) in limits.items():
            check(f"{conf} {metric}", s.get(metric), op, limit)
    leaks = 0
    for row in data["configs"]["defended"]["per_question"]:
        g = golden_by_id.get(row["id"], {})
        if g.get("must_not_contain") and not guard.check(row["raw_answer"]).ok:
            continue                       # the current guard still withholds it
        shown = row["raw_answer"]
        leaks += any(x.lower() in shown.lower() for x in g.get("must_not_contain", []))
    check("defended: recorded raw outputs leaking past the current guard", leaks, "<=", 0)
    if failures:
        typer.echo(f"GATE FAILED: {len(failures)} check(s)")
        if "results are fresh (fingerprint matches)" in failures:
            typer.echo("  answers are stale: run `rag eval-answers` locally and commit evals/results + evals/cache")
        raise typer.Exit(1)
    typer.echo("GATE PASSED")


@app.command("export-grading")
def export_grading(results: str, out: str = "evals/hand_grades.csv", n: int = 30):
    """Write a sample of answers for hand grading (the judge's verdicts are hidden)."""
    from . import answer_evals
    typer.echo(f"wrote {answer_evals.export_for_grading(Path(results), Path(out), n)} rows to {out}")


@app.command("judge-agreement")
def judge_agreement(results: str, grades: str = "evals/hand_grades.csv"):
    """Compare the LLM judge with your hand grades: exact agreement, Cohen's kappa, pass/fail agreement."""
    import json

    from . import answer_evals
    typer.echo(json.dumps(answer_evals.agreement(Path(results), Path(grades)), indent=1))


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
