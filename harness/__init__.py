"""harness — Feature & session management backed by SQLite.

Usage:
    python -m harness list --status=pending
    python -m harness show 106
    python -m harness stats
    python -m harness migrate          # JSON → DB
    python -m harness export           # DB → JSON
    python -m harness health           # validate everything
"""

__version__ = "1.0.0"
