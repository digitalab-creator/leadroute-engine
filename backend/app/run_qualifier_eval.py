"""Run the labelled QL eval set and write var/qualifier_eval_report.json.

    py -3 -m app.run_qualifier_eval
"""

import json
import os
import sys
from pathlib import Path

from app.eval.qualifier_eval import run_qualifier_eval
from app.logging_config import configure_logging, get_logger
from app.main import load_local_env, repo_root

logger = get_logger()


def main() -> None:
    root = repo_root()
    load_local_env(root / ".env")
    data_dir = Path(os.environ.get("LEADROUTE_DATA_DIR", root / "data"))
    logs = Path(os.environ.get("LEADROUTE_LOG_DIR", root / "logs"))
    configure_logging(logs)
    report = run_qualifier_eval(data_dir)
    destination = root / "var" / "qualifier_eval_report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "qualifier_eval_report written passed=%s total=%s",
        report["passed"],
        report["total"],
    )
    print(
        f"Qualifier eval: {report['passed']}/{report['total']} "
        f"({report['accuracy_pct']}%) → {destination}"
    )
    if not report["all_pass"]:
        for row in report["results"]:
            if not row["pass"]:
                print(
                    f"  FAIL {row['id']}: expected {row['expected_status']} "
                    f"got {row['actual_status']}",
                    file=sys.stderr,
                )
        sys.exit(1)


if __name__ == "__main__":
    main()
