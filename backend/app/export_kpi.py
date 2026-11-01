"""Write KPI_PACK.md from stored decisions and the top visibility gap.

Run from the repo root with the backend on the path:

    py -3 -m app.export_kpi
"""

import os
from pathlib import Path

from app import repo
from app.db import apply_schema, connect
from app.kpi.markdown import cro_note, render_pack
from app.logging_config import configure_logging, get_logger
from app.main import load_local_env, repo_root
from app.service import load_seed, pack_from_connection
from app.visibility.brief import open_visibility

logger = get_logger()


def write_pack(root: Path | None = None) -> Path:
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
    pack = pack_from_connection(connection)
    # The pack counts stored rows. The gap score does not need a model call.
    gaps, _brief = open_visibility(data_dir, None)
    top = gaps[0]
    note = cro_note(
        pack,
        prompt=top.prompt,
        engines_missing=top.miss_count,
        engine_count=len(top.engines),
    )
    destination = repo_dir / "KPI_PACK.md"
    destination.write_text(render_pack(pack, note), encoding="utf-8")
    logger.info("kpi_pack_written")
    connection.close()
    return destination


def main() -> None:
    write_pack()


if __name__ == "__main__":
    main()
