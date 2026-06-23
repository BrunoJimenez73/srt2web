try:
    from harness.web.server import run_server, WEB_DIR, DB_PATH, HarnessHandler

    print(f"WEB_DIR: {WEB_DIR}")
    print(f"DB_PATH: {DB_PATH}")
    print(f"DB exists: {DB_PATH.exists()}")
    print(f"Index exists: {(WEB_DIR / 'index.html').exists()}")
    print("Import OK")
except Exception as e:
    print(f"Error: {e}")
