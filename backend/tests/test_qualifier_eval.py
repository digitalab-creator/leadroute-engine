"""Labelled qualifier eval set — all bundled cases must pass."""

from app.eval.qualifier_eval import load_eval_file, run_case, run_qualifier_eval
from tests.conftest import DATA_DIR


def test_qualifier_eval_file_loads() -> None:
    path = DATA_DIR / "qualifier_eval.json"
    document = load_eval_file(path)
    assert document.version == 1
    assert len(document.cases) >= 10


def test_qualifier_eval_all_pass() -> None:
    report = run_qualifier_eval(DATA_DIR)
    assert report["all_pass"] is True
    assert report["failed"] == 0
    assert report["accuracy_pct"] == 100.0


def test_each_case_has_standard_ref() -> None:
    document = load_eval_file(DATA_DIR / "qualifier_eval.json")
    for case in document.cases:
        assert case.standard.startswith("§")
        result = run_case(case)
        assert result["pass"] is True, result
