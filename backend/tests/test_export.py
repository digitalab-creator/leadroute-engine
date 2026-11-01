"""The exported week stays honest: unknown is a word, and the CRO note is short."""

from app.db import apply_schema, connect
from app.kpi.markdown import CRO_WORD_LIMIT, cro_note, render_pack
from app.logging_config import configure_logging
from app.service import load_seed, pack_from_connection
from app.visibility.brief import open_visibility
from tests.conftest import DATA_DIR


def test_seed_pack_renders_unknown_and_a_short_cro_note(tmp_path) -> None:
    configure_logging(tmp_path / "logs")
    connection = connect(tmp_path / "revops.sqlite")
    apply_schema(connection)
    load_seed(connection, DATA_DIR, None)
    pack = pack_from_connection(connection)
    gaps, _brief = open_visibility(DATA_DIR, None)
    top = gaps[0]
    note = cro_note(
        pack,
        prompt=top.prompt,
        engines_missing=top.miss_count,
        engine_count=len(top.engines),
    )
    text = render_pack(pack, note)
    assert len(note.split()) <= CRO_WORD_LIMIT
    assert "historical-reactivation" in text
    assert "| historical-reactivation | unknown |" in text
    assert "Note to the CRO" in text
    assert top.prompt in note
    assert "not zero" in note
    connection.close()
