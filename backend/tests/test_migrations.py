"""The Alembic migration must produce exactly the schema the models describe.

This is the guard against the failure mode that shipped once already: the
hand-written DDL drifted from the ORM models, every SQLite-backed test stayed
green because SQLite builds its schema *from* those models, and the mismatch
only appeared against real PostgreSQL. Running the migration and diffing the
result against the metadata closes that gap.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_VERSION_TABLE = "alembic_version"


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture
def migrated_url(tmp_path: Path) -> str:
    """A throwaway SQLite database with every migration applied."""
    url = f"sqlite+pysqlite:///{tmp_path / 'migrated.sqlite'}"
    command.upgrade(_alembic_config(url), "head")
    return url


class TestMigrations:
    def test_creates_every_table_the_models_declare(self, migrated_url: str) -> None:
        inspector = inspect(create_engine(migrated_url))

        migrated = set(inspector.get_table_names()) - {ALEMBIC_VERSION_TABLE}

        assert migrated == set(Base.metadata.tables)

    def test_every_table_has_the_columns_the_models_declare(self, migrated_url: str) -> None:
        inspector = inspect(create_engine(migrated_url))

        for name, table in Base.metadata.tables.items():
            migrated = {column["name"] for column in inspector.get_columns(name)}
            expected = {column.name for column in table.columns}

            assert migrated == expected, f"{name}: {expected ^ migrated}"

    @pytest.mark.parametrize(
        ("table", "allowed", "rejected"),
        [
            ("users", "'user'", "'USER'"),
            ("documents", "'pdf'", "'PDF'"),
            ("summary_requests", "'medium'", "'MEDIUM'"),
            ("usage_metrics", "'login'", "'LOGIN'"),
        ],
    )
    def test_enum_checks_use_lowercase_values(
        self, migrated_url: str, table: str, allowed: str, rejected: str
    ) -> None:
        # The specific regression: 'USER' would be written into a column whose
        # CHECK constraint only permits 'user'. Read the emitted DDL directly,
        # because SQLite does not reflect these constraints through the
        # inspector.
        engine = create_engine(migrated_url)
        with engine.connect() as connection:
            ddl = connection.execute(
                text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table},
            ).scalar_one()

        assert allowed in ddl, ddl
        assert rejected not in ddl, ddl

    def test_downgrade_removes_everything(self, migrated_url: str) -> None:
        command.downgrade(_alembic_config(migrated_url), "base")
        inspector = inspect(create_engine(migrated_url))

        assert set(inspector.get_table_names()) - {ALEMBIC_VERSION_TABLE} == set()
