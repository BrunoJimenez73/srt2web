"""Migrate feature_list.json -> harness.db."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .db import HarnessDB
from .models import Feature


def migrate(json_path: str | Path = "feature_list.json", db_path: str | Path | None = None) -> dict:
    """Migrate feature_list.json into the SQLite database.

    Returns a summary dict with counts.
    """
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Feature list not found: {json_path}")

    raw_text = json_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        depth = 0
        end_pos = 0
        for i, ch in enumerate(raw_text):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_pos = i + 1
                    break
        if end_pos > 0:
            data = json.loads(raw_text[:end_pos])
        else:
            raise

    raw_features = data.get("features", [])
    db = HarnessDB(db_path)
    db.connect()

    imported = 0
    skipped = 0
    errors: list[str] = []

    for raw in raw_features:
        try:
            feature = Feature.from_json_dict(raw)
            db.upsert_feature(feature, agent="migrate")
            imported += 1
        except Exception as e:
            errors.append(f"Feature {raw.get('id', '?')}: {e}")
            skipped += 1

    db.close()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "total_in_json": len(raw_features),
    }


if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "feature_list.json"
    result = migrate(json_file)
    print(f"Migrated: {result['imported']} features")
    if result["skipped"]:
        print(f"Skipped: {result['skipped']} features")
    for err in result["errors"]:
        print(f"  ERROR: {err}")
