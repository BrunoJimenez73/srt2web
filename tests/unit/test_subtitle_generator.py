import tempfile

import pytest

from core.module_base import PipelineData
from modules.subtitle_generator import SubtitleGenerator


class TestSubtitleGenerator:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp(prefix="srt2web_test_")
        yield
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_gen(self):
        gen = SubtitleGenerator(output_dir=self.temp_dir)
        gen.configure({"chunk_duration": 5})
        gen.start()
        return gen

    def test_vtt_entries_generated_per_chunk(self):
        gen = self._make_gen()
        for i in range(5):
            data = PipelineData(
                chunk_index=i,
                transcript="test text",
                translated_text="test text",
                duration=5.0,
                cumulative_duration=i * 5.0,
            )
            result = gen._do_process(data)
            assert result is not None
        assert len(gen._vtt_entries) >= 5

    def test_empty_text_handling(self):
        gen = self._make_gen()
        data = PipelineData(chunk_index=0, transcript="", translated_text="", duration=5.0, cumulative_duration=0.0)
        result = gen._do_process(data)
        assert result is not None
        assert result.subtitles_path is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
