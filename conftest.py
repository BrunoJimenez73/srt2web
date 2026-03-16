import json
import requests
from pathlib import Path
import pytest
import traceback


def pytest_sessionstart(session):
    """Called after the Session object has been created and before tests are collected."""
    print("Starting test session with MCP integration")


def pytest_runtest_makereport(item, call):
    """Called when a test completes to build a report for the test."""
    if call.when == "call" and call.excinfo:
        tb_str = "".join(traceback.format_exception(*call.excinfo._excinfo))

        locals_dict = {}
        if call.excinfo.traceback:
            tb = call.excinfo.traceback[-1]
            if hasattr(tb, "locals"):
                locals_dict = tb.locals

        filtered_locals = {}
        for key, value in locals_dict.items():
            try:
                json.dumps({key: str(value)})
                filtered_locals[key] = str(value)
            except (TypeError, OverflowError, ValueError):
                filtered_locals[key] = f"<non-serializable: {type(value).__name__}>"

        line_number = item.function.__code__.co_firstlineno
        if call.excinfo.traceback:
            line_number = call.excinfo.traceback[-1].lineno

        failure_data = {
            "test_name": item.name,
            "file_path": str(Path(item.fspath).resolve()),
            "line_number": line_number,
            "error_message": str(call.excinfo.value),
            "traceback": tb_str,
            "locals": filtered_locals,
        }

        print("\n===== MCP Test Failure Registration =====")
        print(f"Test: {failure_data['test_name']}")
        print(f"File: {failure_data['file_path']}")
        print(f"Line: {failure_data['line_number']}")
        print(f"Error: {failure_data['error_message']}")

        endpoints = [
            "http://localhost:3000/api/failures",
            "http://localhost:3001/mcp/failures",
        ]

        success = False
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json=failure_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"[OK] Failure registered with MCP server at {endpoint}")
                    print(f"[ID] Failure ID: {result.get('failureId')}")
                    print(f"[ID] Session ID: {result.get('sessionId')}")
                    success = True
                    break
                else:
                    print(
                        f"[FAIL] Failed to register failure with MCP server at {endpoint}: {response.status_code}"
                    )
            except requests.RequestException as e:
                print(f"[FAIL] Error connecting to MCP server at {endpoint}: {e}")

        if not success:
            print("[WARN] Could not register failure with any MCP server endpoint")
