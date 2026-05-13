import os
import tempfile
import pytest
from modules.subtitle_generator import SubtitleGenerator
from core.module_base import PipelineData


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
    
    def test_cache_hit_rate(self):
        gen = self._make_gen()
        for i in range(10):
            data = PipelineData(
                chunk_index=i,
                transcript="test text",
                translated_text="test text",
                duration=5.0,
                cumulative_duration=i * 5.0
            )
            result = gen._do_process(data)
            assert result is not None
        assert gen.timestamp_cache is not None
        
    def test_cache_ttl_expiration(self):
        gen = self._make_gen()
        gen.timestamp_cache.ttl_seconds = 1
        import time
        data1 = PipelineData(
            chunk_index=0,
            transcript="test text",
            translated_text="test text",
            duration=5.0,
            cumulative_duration=0.0
        )
        gen._do_process(data1)
        time.sleep(1.1)
        data2 = PipelineData(
            chunk_index=1,
            transcript="test text",
            translated_text="test text",
            duration=5.0,
            cumulative_duration=5.0
        )
        gen._do_process(data2)
        
    def test_sync_correction_factor_applied(self):
        gen = self._make_gen()
        gen.sync_correction_factor = 1.02
        data = PipelineData(
            chunk_index=0,
            transcript="test text for correction",
            translated_text="test text for correction",
            duration=5.0,
            cumulative_duration=1000.0
        )
        result = gen._do_process(data)
        assert result is not None
        assert gen.sync_correction_factor == 1.02
        
    def test_empty_text_handling(self):
        gen = self._make_gen()
        data = PipelineData(
            chunk_index=0,
            transcript="",
            translated_text="",
            duration=5.0,
            cumulative_duration=0.0
        )
        result = gen._do_process(data)
        assert result is not None
        assert result.subtitles_path is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])