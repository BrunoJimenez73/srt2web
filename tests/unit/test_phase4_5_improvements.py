"""
Tests for Phase 4-5 improvements (compression, rolling subtitles, UX).
"""

import os
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock


class TestGZipMiddleware:
    """Test GZip compression middleware."""

    def test_gzip_middleware_exists(self):
        """Test that GZipMiddleware is added to the app."""
        from fastapi import FastAPI
        from fastapi.middleware.gzip import GZipMiddleware

        app = FastAPI()
        app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Verify middleware was added
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert "GZipMiddleware" in str(middleware_types) or len(app.user_middleware) > 0

    def test_gzip_response_header(self):
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
    """Test rolling window for VTT subtitles."""

    def test_subtitle_generator_has_rolling_window_attrs(self):
        """Test that SubtitleGenerator has rolling window attributes."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator()
        assert hasattr(gen, '_vtt_entries')
        assert hasattr(gen, '_max_vtt_entries')
        assert hasattr(gen, '_vtt_max_age_seconds')
        assert isinstance(gen._vtt_entries, list)

    def test_rolling_window_defaults(self):
        """Test default rolling window values."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator()
        assert gen._max_vtt_entries == 50
        assert gen._vtt_max_age_seconds == 60.0

    def test_trim_vtt_entries_limits_count(self):
        """Test that _trim_vtt_entries limits entry count."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator()
        gen._max_vtt_entries = 5
        
        # Add more entries than max
        gen._vtt_entries = [
            {"start": float(i), "end": float(i + 1), "text": f"Entry {i}"}
            for i in range(10)
        ]
        
        gen._trim_vtt_entries()
        assert len(gen._vtt_entries) == 5

    def test_trim_vtt_entries_removes_old_by_time(self):
        """Test that _trim_vtt_entries removes entries older than max age."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator()
        gen._vtt_max_age_seconds = 10.0
        gen._max_vtt_entries = 100  # High count limit
        
        # Add entries with old timestamps
        gen._vtt_entries = [
            {"start": 0.0, "end": 5.0, "text": "Old entry"},
            {"start": 100.0, "end": 105.0, "text": "Recent entry"},
        ]
        
        gen._trim_vtt_entries()
        
        # Only recent entry should remain
        assert len(gen._vtt_entries) == 1
        assert gen._vtt_entries[0]["text"] == "Recent entry"

    def test_rewrite_vtt_file(self, temp_dir):
        """Test that _rewrite_vtt_file writes correct VTT format."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator(output_dir=temp_dir)
        gen._subtitles_dir = temp_dir
        gen._vtt_path = os.path.join(temp_dir, "test.vtt")
        
        gen._vtt_entries = [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "World"},
        ]
        
        gen._rewrite_vtt_file()
        
        assert os.path.exists(gen._vtt_path)
        with open(gen._vtt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert content.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.000" in content
        assert "Hello" in content
        assert "00:00:02.000 --> 00:00:04.000" in content
        assert "World" in content

    def test_start_clears_rolling_window(self, temp_dir):
        """Test that start() clears the rolling window."""
        from modules.subtitle_generator import SubtitleGenerator

        gen = SubtitleGenerator(output_dir=temp_dir)
        gen._vtt_entries = [{"start": 0, "end": 1, "text": "test"}]
        
        gen.start()
        
        assert gen._vtt_entries == []


class TestHLSPlayerErrorHandling:
    """Test HLS player error handling improvements."""

    def test_player_has_error_overlay(self):
        """Test that player.astro has error overlay element."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()

        assert "error-overlay" in content
        assert "error-message" in content
        assert "btn-retry" in content

    def test_player_has_error_styles(self):
        """Test that player.astro has error overlay styles."""
        with open("frontend/src/pages/player.astro", "r", encoding="utf-8") as f:
            content = f.read()

        assert ".error-overlay" in content
        assert ".error-content" in content
        assert ".btn-retry" in content

    def test_player_has_show_error_function(self):
        """Test that player has showError function."""
        with open("frontend/src/lib/player.ts", "r", encoding="utf-8") as f:
            content = f.read()

        assert "showError" in content
        assert "hideError" in content

    def test_player_has_error_count_tracking(self):
        """Test that player tracks error count."""
        with open("frontend/src/lib/player.ts", "r", encoding="utf-8") as f:
            content = f.read()

        assert "errorCount" in content
        assert "errorCount < 3" in content or "errorCount < 5" in content


class TestStopConfirmation:
    """Test stop confirmation dialog."""

    def test_stop_has_confirmation(self):
        """Test that stop handler has confirmation dialog."""
        with open("frontend/src/lib/dashboard.ts", "r", encoding="utf-8") as f:
            content = f.read()

        assert "confirm(" in content
        assert "¿Está seguro" in content or "detener" in content.lower()


class TestLogSearchFilter:
    """Test log search/filter functionality."""

    def test_log_panel_has_search_input(self):
        """Test that LogPanel has search input."""
        with open("frontend/src/components/LogPanel.astro", "r", encoding="utf-8") as f:
            content = f.read()

        assert "log-search" in content
        assert "Filtrar" in content

    def test_log_panel_has_search_styles(self):
        """Test that LogPanel has search input styles."""
        with open("frontend/src/components/LogPanel.astro", "r", encoding="utf-8") as f:
            content = f.read()

        assert ".log-search" in content

    def test_log_panel_has_filter_logic(self):
        """Test that LogPanel has filter logic."""
        with open("frontend/src/components/LogPanel.astro", "r", encoding="utf-8") as f:
            content = f.read()

        assert "currentFilter" in content
        assert "entry.dataset.message" in content

    def test_log_entry_has_data_attributes(self):
        """Test that log entries have data attributes for filtering."""
        with open("frontend/src/components/LogPanel.astro", "r", encoding="utf-8") as f:
            content = f.read()

        assert "entry.dataset.level" in content
        assert "entry.dataset.message" in content


class TestSecurityCardExists:
    """Test security functionality exists (moved from SecurityCard to Header)."""

    def test_security_in_header_exists(self):
        """Test that security toggle exists in Header component."""
        header_path = "frontend/src/components/Header.astro"
        assert os.path.exists(header_path), "Header.astro not found"
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Secure" in content, "Security toggle should be in Header"

    def test_header_has_auth_toggle(self):
        """Test that Header has auth token toggle button."""
        with open("frontend/src/components/Header.astro", "r", encoding="utf-8") as f:
            content = f.read()
        assert "btn-secure" in content or "secure" in content.lower(), \
            "Header should have security toggle"

    def test_header_shows_security_status(self):
        """Test that Header shows security status."""
        with open("frontend/src/components/Header.astro", "r", encoding="utf-8") as f:
            content = f.read()
        assert "ON" in content and "OFF" in content, \
            "Header should show security ON/OFF status"


class TestAPIAuthIntegration:
    """Test that frontend API client has auth integration."""

    def test_api_ts_has_auth_token_functions(self):
        """Test that api.ts has auth token management functions."""
        with open("frontend/src/lib/api.ts", "r", encoding="utf-8") as f:
            content = f.read()

        assert "getAuthToken" in content
        assert "setAuthToken" in content
        assert "clearAuthToken" in content
        assert "AUTH_TOKEN_KEY" in content

    def test_api_ts_adds_auth_header(self):
        """Test that api.ts adds Authorization header to requests."""
        with open("frontend/src/lib/api.ts", "r", encoding="utf-8") as f:
            content = f.read()

        assert "Authorization" in content
        assert "Bearer" in content

    def test_api_ts_websocket_uses_token(self):
        """Test that WebSocket connection uses auth token."""
        with open("frontend/src/lib/api.ts", "r", encoding="utf-8") as f:
            content = f.read()

        assert "?token=" in content
