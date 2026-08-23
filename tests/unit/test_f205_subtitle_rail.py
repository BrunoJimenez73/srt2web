"""F205 — Subtitle rail: /api/subtitles/recent + FragmentWriter.get_recent.

The client-side overlay renderer polls this JSON feed instead of relying on
HLS-native WebVTT delivery. Tests cover retention, shape, and route wiring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.subtitle_generator import SubtitleGenerator
from server.routes.subtitles import router as subtitles_router


def _make_gen(output_dir: str) -> SubtitleGenerator:
    gen = SubtitleGenerator(output_dir=output_dir)
    gen.configure({"chunk_duration": 10})
    gen.start()
    return gen


class TestFragmentWriterGetRecent:
    def test_empty_window(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        rail = gen._fragment_writer.get_recent(count=16)
        assert rail == {"base": 0, "chunks": []}

    def test_segments_retained_and_shaped(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        segs = [{"start": 1.5, "end": 4.0, "text": "hola"}]
        path = gen._fragment_writer.write_fragment(3, segs, 5.0)
        assert path
        gen._fragment_writer.add_fragment(3, 5.0, 30.0, path, segments=segs)
        rail: dict[str, Any] = gen._fragment_writer.get_recent(count=16)
        assert rail["base"] == 3
        assert len(rail["chunks"]) == 1
        chunk = rail["chunks"][0]
        assert chunk == {
            "idx": 3,
            "dur": 5.0,
            "segments": [{"s": 1.5, "e": 4.0, "text": "hola"}],
        }

    def test_count_limits_window(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        for idx in range(10):
            p = gen._fragment_writer.write_fragment(idx, [], 5.0)
            gen._fragment_writer.add_fragment(idx, 5.0, float(idx * 5), p)
        rail = gen._fragment_writer.get_recent(count=4)
        assert [c["idx"] for c in rail["chunks"]] == [6, 7, 8, 9]
        assert rail["base"] == 6

    def test_silent_chunk_yields_empty_segments(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        p = gen._fragment_writer.write_fragment(0, [], 5.0)
        gen._fragment_writer.add_fragment(0, 5.0, 0.0, p, segments=[])
        rail = gen._fragment_writer.get_recent()
        assert rail["chunks"][0]["segments"] == []


class TestSubtitlesRailRoute:
    def _app_with_module(self, gen: SubtitleGenerator | None) -> FastAPI:
        app = FastAPI()
        app.include_router(subtitles_router, prefix="/api")

        class _Pipeline:
            def get_module(self, name: str):
                return gen if name == "subtitle_generator" else None

        app.state.ctx = {"pipeline": _Pipeline()}  # type: ignore[dict-item]
        return app

    def test_returns_rail_json(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        segs = [{"start": 0.5, "end": 2.0, "text": "prueba"}]
        p = gen._fragment_writer.write_fragment(1, segs, 5.0)
        gen._fragment_writer.add_fragment(1, 5.0, 5.0, p, segments=segs)

        client = TestClient(self._app_with_module(gen))
        res = client.get("/api/subtitles/recent")
        assert res.status_code == 200
        body = res.json()
        assert body["base"] == 1
        assert body["chunks"][0]["segments"] == [{"s": 0.5, "e": 2.0, "text": "prueba"}]

    def test_respects_count_query_param(self, tmp_path: Path) -> None:
        gen = _make_gen(str(tmp_path))
        for idx in range(8):
            p = gen._fragment_writer.write_fragment(idx, [], 5.0)
            gen._fragment_writer.add_fragment(idx, 5.0, float(idx * 5), p)
        client = TestClient(self._app_with_module(gen))
        res = client.get("/api/subtitles/recent?count=3")
        assert [c["idx"] for c in res.json()["chunks"]] == [5, 6, 7]

    def test_missing_module_returns_empty_rail(self) -> None:
        client = TestClient(self._app_with_module(None))
        res = client.get("/api/subtitles/recent")
        assert res.status_code == 200
        assert res.json() == {"base": 0, "chunks": []}
