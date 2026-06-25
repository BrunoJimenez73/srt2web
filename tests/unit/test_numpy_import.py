"""
F111 — Smoke test for numpy import.

Catches the Windows-specific failure documented in
``docs/troubleshooting-windows.md``:

    ImportError: DLL load failed while importing _multiarray_umath:
    Una directiva de Control de aplicaciones bloqueó este archivo.

If numpy is not installed at all (rare, since it's a core dep), the test
is skipped so it doesn't fail the suite on minimal installs. If numpy is
installed but the C extensions can't load (the actual reported bug), the
test fails with a clear, actionable error message pointing to the
troubleshooting docs.

Run: ``pytest tests/unit/test_numpy_import.py -v``
"""

from __future__ import annotations

import importlib
import sys

import pytest


def _try_import_numpy() -> tuple[bool, str]:
    """Try to import numpy and return (success, version_or_error)."""
    try:
        import numpy as np

        return True, np.__version__
    except ImportError as e:
        return False, f"ImportError: {e}"
    except Exception as e:  # pragma: no cover — defensive
        return False, f"{type(e).__name__}: {e}"


class TestNumpyImport:
    """Verify numpy can be imported and its C extensions are loadable."""

    def test_numpy_importable(self) -> None:
        """numpy must be importable for the pipeline to function."""
        success, detail = _try_import_numpy()
        if not success and "No module named" in detail:
            pytest.skip(f"numpy not installed: {detail}")
        if not success:
            # Detect the specific Windows DLL-blocked case from F111 audit.
            if "_multiarray_umath" in detail or "Control de aplicaciones" in detail:
                pytest.fail(
                    "F111 detected: numpy C extensions are blocked from loading.\n"
                    "\n"
                    "This is the Windows-specific failure documented in\n"
                    "docs/troubleshooting-windows.md, section 'numpy DLL load failed'.\n"
                    "\n"
                    f"Original error: {detail}\n"
                    "\n"
                    "Quick fix:\n"
                    "  1. venv\\Scripts\\python.exe -m pip uninstall numpy -y\n"
                    "  2. venv\\Scripts\\python.exe -m pip install numpy --only-binary=:all:\n"
                    "\n"
                    "If that doesn't work, see docs/troubleshooting-windows.md for the\n"
                    "6-step escalation (SmartScreen → AppLocker → EDR → admin).",
                )
            pytest.fail(f"numpy import failed unexpectedly: {detail}")

    def test_numpy_array_creation(self) -> None:
        """numpy.array() must work — this is the C extension path that fails on Windows."""
        if "numpy" not in sys.modules:
            success, _ = _try_import_numpy()
            if not success:
                pytest.skip("numpy not importable")
        np = importlib.import_module("numpy")
        arr = np.array([1, 2, 3])
        assert arr.sum() == 6
        assert arr.dtype.kind == "i"  # int

    def test_numpy_multiarray_umath_loadable(self) -> None:
        """Direct import of the C extension module — this is what fails on Windows.

        ``_multiarray_umath`` is the compiled C extension that numpy uses
        for low-level array operations. The DLL load failure manifests here
        first, so we test it explicitly.
        """
        if "numpy" not in sys.modules:
            success, _ = _try_import_numpy()
            if not success:
                pytest.skip("numpy not importable")
        try:
            importlib.import_module("numpy._core._multiarray_umath")
        except ImportError as e:
            if "_multiarray_umath" in str(e) or "DLL load failed" in str(e):
                pytest.fail(
                    "F111 detected: _multiarray_umath.pyd blocked by Windows policy.\n"
                    f"Error: {e}\n"
                    "See docs/troubleshooting-windows.md for the fix.",
                )
            raise
