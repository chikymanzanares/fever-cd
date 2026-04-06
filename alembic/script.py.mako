"""
Basic Alembic template for migration files.
"""

from __future__ import annotations

from alembic import util


def generate_revision_py(ident: str, message: str) -> str:
    # Not used in this challenge (migrations are committed as files).
    # Keeping this template avoids missing-file errors if someone runs alembic commands.
    raise NotImplementedError

