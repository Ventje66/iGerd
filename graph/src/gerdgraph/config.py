"""Where things live and which engine to talk to."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "schema" / "migrations"
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DOC = PROJECT_ROOT / "schema" / "model.md"


@dataclass(frozen=True)
class Settings:
    dialect: str
    kuzu_path: Path
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            dialect=os.environ.get("GRAPH_BACKEND", "kuzu"),
            kuzu_path=Path(os.environ.get("KUZU_PATH", PROJECT_ROOT / ".kuzu" / "gerd.kz")),
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "gerdgraph"),
            neo4j_database=os.environ.get("NEO4J_DATABASE", "neo4j"),
        )

    def backend_kwargs(self) -> dict[str, object]:
        if self.dialect == "kuzu":
            return {"db_path": self.kuzu_path}
        return {
            "uri": self.neo4j_uri,
            "user": self.neo4j_user,
            "password": self.neo4j_password,
            "database": self.neo4j_database,
        }
