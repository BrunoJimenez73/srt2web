import sys

sys.stdout.reconfigure(encoding="utf-8")
try:
    from harness.web.server import WEB_DIR, DB_PATH, HarnessHandler

    print(f"WEB_DIR: {WEB_DIR}")
    print(f"DB_PATH: {DB_PATH}")
    print(f"DB exists: {DB_PATH.exists()}")
    idx = WEB_DIR / "index.html"
    print(f"Index exists: {idx.exists()}")
    print(f"Index size: {idx.stat().st_size if idx.exists() else 'N/A'}")
    print("Import OK")
except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"Error: {e}")
