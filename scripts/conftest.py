import json
import traceback
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from fastapi.testclient import TestClient


@pytest.fixture
def mock_module():
    """Create a mock module for testing."""
    from core.module_base import BaseModule, ModuleState

    class MockModule(BaseModule):
        def __init__(self, name):
            super().__init__(name)
            self._mock_process_data = None

        def start(self):
            self._state = ModuleState.RUNNING

        def stop(self):
            self._state = ModuleState.IDLE

        def _do_process(self, data):
            if self._mock_process_data:
                for key, value in self._mock_process_data.items():
                    setattr(data, key, value)
            return data

    return MockModule


@pytest.fixture
def mock_pipeline(mock_module):
    """Create a mock pipeline for testing."""
    from core.pipeline import Pipeline

    pipeline = Pipeline()

    module = mock_module("test_module")
    pipeline.register_module(module)

    pipeline._state = "running"
    pipeline._chunk_index = 0

    pipeline.input_source = MagicMock()
    pipeline.input_source.is_receiving.return_value = True
    pipeline.input_source.name = "srt"

    pipeline.output_sink = MagicMock()
    pipeline.output_sink.is_streaming.return_value = True
    pipeline.output_sink.name = "hls"

    return pipeline


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return {
        "server": {"host": "0.0.0.0", "port": 9999},
        "modules": {
            "transcriber": {"model": "tiny", "device": "cpu"},
            "translator": {"source_lang": "en", "target_lang": "es"},
        },
        "_start_time": 1000.0,
    }


@pytest.fixture
def client(mock_pipeline, mock_config):
    """Create a test client for API testing."""
    from server.app import create_app

    app = create_app(
        {
            "config": mock_config,
            "pipeline": mock_pipeline,
            "input_source": mock_pipeline.input_source,
            "log_broadcast": MagicMock(),
        }
    )

    return TestClient(app)


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
                    print(f"[FAIL] Failed to register failure with MCP server at {endpoint}: {response.status_code}")
            except requests.RequestException as e:
                print(f"[FAIL] Error connecting to MCP server at {endpoint}: {e}")

        if not success:
            print("[WARN] Could not register failure with any MCP server endpoint")
