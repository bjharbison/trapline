"""Synthetic SQLite migration and integrity tests; no user data or network."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from trapline_api.database import make_engine, session_factory
from trapline_api.models import Document, Entity, Evidence, Investigation, Relationship

BACKEND = Path(__file__).resolve().parents[1]


def migrate(db: Path, revision: str = "head") -> None:
    env = {**os.environ, "TRAPLINE_DATABASE_URL": f"sqlite:///{db}"}
    subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", revision], cwd=BACKEND, env=env, check=True, capture_output=True, text=True)


def test_migration_persists_across_restart_and_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "case.db"
    migrate(db)
    migrate(db)
    engine = make_engine(f"sqlite:///{db}")
    assert {"investigations", "documents", "entities", "relationships", "evidence", "alembic_version"} <= set(inspect(engine).get_table_names())
    with session_factory(engine)() as session:
        case = Investigation(title="Synthetic test case")
        session.add(case)
        session.commit()
        case_id = case.id
    engine.dispose()
    reopened = make_engine(f"sqlite:///{db}")
    with session_factory(reopened)() as session:
        assert session.get(Investigation, case_id).title == "Synthetic test case"
    reopened.dispose()


def test_foreign_keys_enforced(tmp_path: Path) -> None:
    db = tmp_path / "case.db"
    migrate(db)
    engine = make_engine(f"sqlite:///{db}")
    with session_factory(engine)() as session:
        session.add(Document(investigation_id="missing", filename="fiction.txt", sha256="0" * 64, content_type="text/plain", byte_size=2))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    engine.dispose()


def test_relationship_and_evidence_survive_reopen(tmp_path: Path) -> None:
    db = tmp_path / "case.db"
    migrate(db)
    engine = make_engine(f"sqlite:///{db}")
    with session_factory(engine)() as session:
        inv = Investigation(title="Fictional investigation")
        session.add(inv)
        session.flush()
        doc = Document(investigation_id=inv.id, filename="fiction.txt", sha256="a" * 64, content_type="text/plain", byte_size=25, extracted_text="A met B in a fictional town")
        a = Entity(investigation_id=inv.id, name="A", entity_type="PERSON")
        b = Entity(investigation_id=inv.id, name="B", entity_type="PERSON")
        session.add_all([doc, a, b])
        session.flush()
        rel = Relationship(investigation_id=inv.id, source_entity_id=a.id, target_entity_id=b.id, label="met")
        session.add(rel)
        session.flush()
        evidence = Evidence(relationship_id=rel.id, document_id=doc.id, quote="A met B", start_offset=0, end_offset=7)
        session.add(evidence)
        session.commit()
        evidence_id = evidence.id
    engine.dispose()
    engine = make_engine(f"sqlite:///{db}")
    with session_factory(engine)() as session:
        assert session.get(Evidence, evidence_id).quote == "A met B"
    engine.dispose()
