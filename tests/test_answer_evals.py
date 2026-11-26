import csv
import json

from rag import answer_evals


def row(i, typ="answerable", split="dev", **kw):
    base = {"id": i, "type": typ, "split": split, "answer": "", "raw_answer": "", "abstained": False,
            "withheld": False, "citations": [], "invalid_citations": [], "ms": 10}
    return base | kw


def test_summary_counts_each_check_on_the_right_items():
    rows = [row("a", answered=True, cites_gold=True, verdict="correct"),
            row("b", answered=True, cites_gold=False, verdict="partial", split="holdout"),
            row("c", "unanswerable", abstain_ok=True),
            row("d", "injection", violations=["--to-latest"], abstain_ok=False)]
    s = answer_evals.summarise(rows)
    assert s["answered"] == 1.0 and s["cites_gold"] == 0.5
    assert s["correctness_dev"] == 1.0 and s["correctness_holdout"] == 0.5
    assert s["abstain_ok"] == 0.5 and s["injection_violations"] == 1 and s["injection_n"] == 1


def test_judge_agreement_and_kappa(tmp_path):
    verdicts = ["correct", "correct", "partial", "incorrect"]
    res = {"configs": {"defended": {"per_question": [{"id": f"q{i}", "verdict": v} for i, v in enumerate(verdicts)]}}}
    rf = tmp_path / "r.json"
    rf.write_text(json.dumps(res))
    gf = tmp_path / "g.csv"
    with gf.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "question", "reference", "answer", "human_verdict (correct/partial/incorrect)"])
        for i, h in enumerate(["correct", "partial", "partial", "incorrect"]):
            w.writerow([f"q{i}", "", "", "", h])
    a = answer_evals.agreement(rf, gf)
    assert a["n"] == 4 and a["exact_agreement"] == 0.75 and a["judge_too_generous"] == ["q1"]
    assert 0 < a["cohens_kappa"] < 1 and a["pass_fail_agreement"] == 1.0


def test_fingerprint_is_stable():
    assert answer_evals.fingerprint() == answer_evals.fingerprint()
