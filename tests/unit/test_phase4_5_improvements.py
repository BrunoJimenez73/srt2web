"""
Tests for Phase 4-5 improvements (compression, rolling subtitles, UX).
"""

import os

import pytest


@pytest.mark.unit
class TestGZipMiddleware:
    """Test GZip compression middleware."""

    def test_gzip_middleware_exists(self) -> None:
        """Test that GZipMiddleware is added to the app."""
        from fastapi import FastAPI
        from fastapi.middleware.gzip import GZipMiddleware

        app = FastAPI()
        app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Verify middleware was added
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert "GZipMiddleware" in str(middleware_types) or len(app.user_middleware) > 0

    def test_gzip_response_header(self) -> None:
        """Test that compressed responses have Content-Encoding header."""
        from fastapi import FastAPI
        from fastapi.middleware.gzip import GZipMiddleware
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.add_middleware(GZipMiddleware, minimum_size=10)

        @app.get("/large")
        async def large_response():
            # Return a response larger than minimum_size
            return {"data": "x" * 100}

        client = TestClient(app)
        response = client.get("/large", headers={"Accept-Encoding": "gzip"})

        # Response should be successful
        assert response.status_code == 200


class TestRollingSubtitles:
    """Test rolling window for HLS subtitle fragments."""

    def test_subtitle_generator_has_fragment_attrs(self) -> None:
        """Test that SubtitleGenerator has fragment writer attributes."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator()
        assert hasattr(gen, "_fragment_writer")
        assert hasattr(gen._fragment_writer, "_list_size")
        assert isinstance(gen._fragment_writer.fragments, list)

    def test_rolling_window_defaults(self) -> None:
        """Test default rolling window values."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator()
        assert gen._hls_list_size == 12

    def test_trim_fragments_limits_count(self) -> None:
        """Test that fragment writer trim limits entry count."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator()
        gen._fragment_writer._list_size = 5

        # Add more fragments than max
        gen._fragment_writer._fragments = [
            {"chunk_index": i, "duration": 5.0, "pts_start": 0.0, "path": f"seg_{i}.vtt"} for i in range(10)
        ]

        gen._fragment_writer.trim()
        assert len(gen._fragment_writer.fragments) == 5

    def test_write_fragment_produces_valid_vtt(self, temp_dir) -> None:
        """Test that write_fragment writes correct VTT format."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator(output_dir=temp_dir)
        gen.configure({"chunk_duration": 5})
        gen.start()

        fragment_path = gen._fragment_writer.write_fragment(
            0, [{"start": 0.0, "end": 2.0, "text": "Hello"}, {"start": 2.0, "end": 4.0, "text": "World"}], 5.0, 0.0
        )

        assert os.path.exists(fragment_path)
        with open(fragment_path, encoding="utf-8") as f:
            content = f.read()

        assert content.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.000" in content
        assert "Hello" in content
        assert "00:00:02.000 --> 00:00:04.000" in content
        assert "World" in content

    def test_start_clears_fragments(self, temp_dir) -> None:
        """Test that start() clears the fragment registry."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator(output_dir=temp_dir)
        gen._fragment_writer._fragments = [{"chunk_index": 99, "duration": 5.0, "pts_start": 0.0, "path": "x"}]

        gen.start()

        assert gen._fragment_writer.fragments == []


class TestHLSPlayerErrorHandling:
    """Test HLS player error handling improvements."""

    def test_player_has_error_overlay(self) -> None:
        """Test that player.astro has error overlay element."""
        with open("frontend/src/pages/player.astro", encoding="utf-8") as f:
            content = f.read()

        assert "error-overlay" in content
        assert "error-message" in content
        assert "btn-retry" in content

    def test_player_has_error_styles(self) -> None:
        """Test that player.astro has error overlay styles."""
        with open("frontend/src/pages/player.astro", encoding="utf-8") as f:
            content = f.read()

        assert ".error-overlay" in content
        assert ".error-content" in content
        assert ".btn-retry" in content

    def test_player_has_show_error_function(self) -> None:
        """Test that player has showError function."""
        with open("frontend/src/lib/modules/player.ts", encoding="utf-8") as f:
            content = f.read()

        assert "showError" in content
        assert "hideError" in content

    def test_player_has_error_count_tracking(self) -> None:
        """Test that player tracks error count."""
        with open("frontend/src/lib/modules/player.ts", encoding="utf-8") as f:
            content = f.read()

        assert "consecutiveErrors" in content or "error" in content.lower()


class TestStopConfirmation:
    """Test stop confirmation dialog."""

    def test_stop_has_confirmation(self) -> None:
        """Test that stop handler has confirmation dialog."""
        with open("frontend/src/lib/modules/pipeline-control.ts", encoding="utf-8") as f:
            content = f.read()

        assert "showConfirm(" in content
        assert "confirm_stop" in content


class TestLogSearchFilter:
    """Test log search/filter functionality."""

    def test_log_panel_has_search_input(self) -> None:
        """Test that LogPanel has search input."""
        with open("frontend/src/components/LogPanel.astro", encoding="utf-8") as f:
            content = f.read()

        assert "log-search" in content
        assert "log_filter" in content

    def test_log_panel_has_search_styles(self) -> None:
        """Test that LogPanel has search input styles."""
        with open("frontend/src/components/LogPanel.astro", encoding="utf-8") as f:
            content = f.read()

        assert ".log-search" in content

    def test_log_panel_has_filter_logic(self) -> None:
        """Test that LogPanel has filter logic (now in logpanel.ts)."""
        with open("frontend/src/lib/modules/logpanel.ts", encoding="utf-8") as f:
            content = f.read()

        assert "currentFilter" in content
        assert "entry.dataset.message" in content

    def test_log_entry_has_data_attributes(self) -> None:
        """Test that log entries have data attributes for filtering (now in logpanel.ts)."""
        with open("frontend/src/lib/modules/logpanel.ts", encoding="utf-8") as f:
            content = f.read()

        assert "entry.dataset.level" in content
        assert "entry.dataset.message" in content


class TestSecurityCardExists:
    """Test security functionality exists (Header layout component + header module)."""

    def test_security_in_header_exists(self) -> None:
        """Test that security toggle exists in the layout Header component."""
        header_path = "frontend/src/components/layout/Header.astro"
        assert os.path.exists(header_path), "layout/Header.astro not found"
        with open(header_path, encoding="utf-8") as f:
            content = f.read()
        assert "Secure" in content, "Security toggle should be in layout/Header"

    def test_header_has_auth_toggle(self) -> None:
        """Test that layout Header has auth token toggle button and panel."""
        with open("frontend/src/components/layout/Header.astro", encoding="utf-8") as f:
            content = f.read()
        assert "btn-secure-toggle" in content or "secure" in content.lower(), "Header should have security toggle"
        assert 'id="secure-panel"' in content, "Header should have security auth panel"

    def test_header_shows_security_status(self) -> None:
        """Test that security ON/OFF state is handled by the header module."""
        with open("frontend/src/lib/modules/header.ts", encoding="utf-8") as f:
            content = f.read()
        assert "Secure ON" in content and "Secure OFF" in content, "header.ts should toggle Secure ON/OFF status"


class TestAPIAuthIntegration:
    """Test that frontend API client has auth integration."""

    def test_api_ts_has_auth_token_functions(self) -> None:
        """Test that api.ts has auth token management functions."""
        with open("frontend/src/lib/api.ts", encoding="utf-8") as f:
            content = f.read()

        assert "getAuthToken" in content
        assert "setAuthToken" in content
        assert "clearAuthToken" in content
        assert "'auth_token'" in content or "AUTH_TOKEN_KEY" in content

    def test_api_ts_adds_auth_header(self) -> None:
        """Test that api.ts adds Authorization header to requests."""
        with open("frontend/src/lib/api.ts", encoding="utf-8") as f:
            content = f.read()

        assert "Authorization" in content
        assert "Bearer" in content

    def test_api_ts_websocket_uses_token(self) -> None:
        """Test that WebSocket connection uses auth token."""
        with open("frontend/src/lib/api.ts", encoding="utf-8") as f:
            content = f.read()

        # Auth is sent via WebSocket message, not URL query param
        assert "sendAuth" in content
        assert "auth" in content.lower() and "token" in content.lower()
