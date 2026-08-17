git add -A
git commit -m "feat: reorganize tests into unit/integration + GitHub Actions benchmark + mock tempfile

- Reorganize tests: unit/ (fast, mocked) vs integration/ (real I/O, models, binaries)
- Add pytest-benchmark to pyproject.toml + benchmark.yml workflow (nightly + PR comments)
- Update ci.yml: unit tests on PRs, integration tests nightly + benchmark
- Mock tempfile in conftest.py to use tests/temp/ (fixes WinError 5/32 in sandbox)
- Move slow/integration tests to tests/integration/
- Add pytest.ini configs for unit/ and integration/ with proper markers
- Move chunk clock real-file tests to integration/
- TTS integration test skips gracefully if Piper not installed
- Transcriber stop() only calls empty_cache() once

Files changed:
- .github/workflows/ci.yml (updated)
- .github/workflows/benchmark.yml (new)
- pyproject.toml (pytest-benchmark)
- tests/conftest.py (mock tempfile)
- tests/pytest.ini (unit config)
- tests/integration/pytest.ini (new, integration config)
- tests/integration/test_chunk_clock_integration.py (new)
- tests/integration/test_f183_f187_startup_races.py (moved)
- tests/integration/test_gpu_installer_restructure.py (moved)
- tests/integration/test_tts_integration.py (moved)
- tests/integration/test_whisper_integration.py (moved)
- tests/unit/test_chunk_clock.py (removed real-file tests)
- tests/conftest.py (mock tempfile)
- pytest.ini / tests/pytest.ini (unit config)
- tests/integration/pytest.ini (new, integration config)"