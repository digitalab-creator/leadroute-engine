"""Write var/hubspot_dry_run.json from stored qualifications.

Run from the repo root:

    py -3 -m app.export_hubspot
"""

import json
import os
from pathlib import Path

from app import repo
from app.db import apply_schema, connect
from app.integrations.hubspot_dry_run import build_hubspot_dry_run
from app.logging_config import configure_logging, get_logger
from app.main import load_local_env, repo_root
from app.service import load_seed

logger = get_logger()


def write_hubspot_dry_run(root: Path | None = None) -> Path:
    repo_dir = root or repo_root()
    load_local_env(repo_dir / ".env")
    database = Path(os.environ.get("LEADROUTE_DB_PATH", repo_dir / "var" / "revops.sqlite"))
    data_dir = Path(os.environ.get("LEADROUTE_DATA_DIR", repo_dir / "data"))
    logs = Path(os.environ.get("LEADROUTE_LOG_DIR", repo_dir / "logs"))
    configure_logging(logs)
    connection = connect(database)
    apply_schema(connection)
    if repo.count_persons(connection) == 0:
        load_seed(connection, data_dir, None)
    payload = build_hubspot_dry_run(connection)
    destination = repo_dir / "var" / "hubspot_dry_run.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("hubspot_dry_run_written count=%s", len(payload["requests"]))
    connection.close()
    return destination


def main() -> None:
    path = write_hubspot_dry_run()
    print(path)


if __name__ == "__main__":
    main()
