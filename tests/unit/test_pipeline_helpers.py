"""
Tests for pipeline helpers (core/pipeline/pipeline_helpers.py).
"""

from unittest.mock import MagicMock

from core.pipeline.pipeline_helpers import get_output_module_status


def make_sink(status_dict):
    """Helper to create a mock output sink."""
    sink = MagicMock()
    status_obj = MagicMock()
    status_obj.to_dict.return_value = status_dict
    sink.get_status.return_value = status_obj
    return sink


class TestGetOutputModuleStatus:
    def test_running_output_with_gpu(self):
        sink = make_sink(
            {
                "name": "hls_output",
                "state": "running",
                "enabled": True,
                "processed_chunks": 10,
                "last_process_time_ms": 500,
                "extra": {
                    "outputs": {
                        "web": {
                            "state": "running",
                            "enabled": True,
                            "processed_chunks": 10,
                            "last_process_time_ms": 500,
                            "extra": {"using_gpu": True, "encoder_mode": "h264_nvenc"},
                        }
                    }
                },
            }
        )

        output_status, muxer_status = get_output_module_status(
            is_running=True, output_sink=sink, module_map={}, chunks_processed=10
        )

        assert output_status["state"] == "running"
        assert output_status["processed_chunks"] == 10
        assert muxer_status is not None
        assert muxer_status["name"] == "video_muxer"
        assert muxer_status["state"] == "running"
        assert muxer_status["extra"]["using_gpu"] is True

    def test_idle_output(self):
        sink = make_sink(
            {
                "name": "hls_output",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0,
                "extra": {"outputs": {"web": {"state": "idle", "enabled": True, "extra": {}}}},
            }
        )

        output_status, muxer_status = get_output_module_status(
            is_running=False, output_sink=sink, module_map={}, chunks_processed=0
        )

        assert output_status["state"] == "idle"
        assert output_status["processed_chunks"] == 0
        assert muxer_status is not None

    def test_no_output_sink_fallback_to_module_map(self):
        mock_video_muxer = MagicMock()
        mock_video_muxer.get_status.return_value = MagicMock(
            to_dict=MagicMock(
                return_value={
                    "name": "video_muxer",
                    "state": "running",
                    "enabled": True,
                    "processed_chunks": 15,
                    "last_process_time_ms": 300,
                    "extra": {
                        "outputs": {
                            "hls": {
                                "state": "running",
                                "enabled": True,
                                "processed_chunks": 15,
                                "last_process_time_ms": 300,
                                "extra": {"using_gpu": False, "encoder_mode": "passthrough"},
                            }
                        }
                    },
                }
            )
        )

        output_status, muxer_status = get_output_module_status(
            is_running=True,
            output_sink=None,
            module_map={"video_muxer": mock_video_muxer},
            chunks_processed=15,
        )

        assert output_status["name"] == "output"
        assert output_status["state"] == "running"
        assert muxer_status is not None
        assert muxer_status["name"] == "video_muxer"

    def test_no_muxer_source_no_outputs(self):
        sink = make_sink(
            {
                "name": "some_output",
                "state": "running",
                "enabled": True,
                "processed_chunks": 8,
                "last_process_time_ms": 400,
                "extra": {"outputs": {}},
            }
        )

        output_status, muxer_status = get_output_module_status(
            is_running=True, output_sink=sink, module_map={}, chunks_processed=8
        )

        assert output_status["state"] == "running"
        assert muxer_status is None

    def test_no_sink_no_module_map(self):
        output_status, muxer_status = get_output_module_status(
            is_running=True, output_sink=None, module_map={}, chunks_processed=5
        )

        assert output_status["name"] == "output"
        assert output_status["state"] == "running"
        assert output_status["processed_chunks"] == 5
        assert muxer_status is None

    def test_sink_get_status_failure(self):
        sink = MagicMock()
        sink.get_status.side_effect = RuntimeError("status unavailable")

        output_status, muxer_status = get_output_module_status(
            is_running=True, output_sink=sink, module_map={}, chunks_processed=3
        )

        assert output_status["state"] == "running"
        assert output_status["processed_chunks"] == 3
        assert muxer_status is None

    def test_muxer_source_from_first_output_when_no_gpu_info(self):
        sink = make_sink(
            {
                "name": "hls_output",
                "state": "running",
                "enabled": True,
                "processed_chunks": 5,
                "last_process_time_ms": 200,
                "extra": {
                    "outputs": {
                        "hls": {
                            "state": "running",
                            "enabled": True,
                            "processed_chunks": 5,
                            "last_process_time_ms": 200,
                            "extra": {},
                        }
                    }
                },
            }
        )

        output_status, muxer_status = get_output_module_status(
            is_running=True, output_sink=sink, module_map={}, chunks_processed=5
        )

        assert output_status["state"] == "running"
        assert muxer_status is not None
        assert muxer_status["name"] == "video_muxer"

    def test_running_state_from_flag(self):
        output_status, _muxer_status = get_output_module_status(
            is_running=False, output_sink=None, module_map={}, chunks_processed=0
        )

        assert output_status["state"] == "idle"
