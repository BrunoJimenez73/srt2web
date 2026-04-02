"""
Tests for latest features and critical fixes (April 2026 session).

This test file covers:
- PipelineData dataclass usage in SRT input (data flow fix)
- PiperSubprocessManager existence and usage
- TTS length_scale speed control (replaces FFmpeg atempo)
- AudioMixer numpy implementation
- Config values for low latency
- Pipeline reconfigure logic
- SRT input single-chunk processing behavior
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = str(PROJECT_ROOT / "config.yaml")


class TestPipelineDataFix:
    """Test that SRT input creates PipelineData correctly (dataclass syntax)."""

    def test_srt_input_uses_keyword_arguments(self):
        """Verify srt_input.py uses PipelineData with keyword arguments."""
        srt_input_path = PROJECT_ROOT / "modules" / "inputs" / "srt_input.py"
        with open(srt_input_path, "r") as f:
            content = f.read()
        
        assert "PipelineData(" in content
        assert "video_chunk_path=" in content
        assert "audio_chunk_path=" in content
        assert "chunk_index=" in content

    def test_srt_input_no_dict_positional_args(self):
        """Should not pass dicts as positional args to PipelineData."""
        srt_input_path = PROJECT_ROOT / "modules" / "inputs" / "srt_input.py"
        with open(srt_input_path, "r") as f:
            content = f.read()
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'PipelineData(' in line:
                after_paren = line.split('PipelineData(')[1]
                if after_paren.strip().startswith('{'):
                    pytest.fail(f"PipelineData uses dict as positional arg at line {i+1}")


class TestPiperSubprocessManager:
    """Test PiperSubprocessManager exists and is used."""

    def test_piper_loader_module_exists(self):
        """Test that piper_loader.py module exists."""
        piper_loader_path = PROJECT_ROOT / "modules" / "piper_loader.py"
        assert piper_loader_path.exists()

    def test_piper_subprocess_manager_class_exists(self):
        """Test PiperSubprocessManager class is defined."""
        from modules.piper_loader import PiperSubprocessManager
        assert hasattr(PiperSubprocessManager, '__init__')
        assert hasattr(PiperSubprocessManager, 'start')
        assert hasattr(PiperSubprocessManager, 'synthesize')
        assert hasattr(PiperSubprocessManager, 'stop')

    def test_piper_manager_used_in_tts_engine(self):
        """Test that TTS engine imports and uses PiperSubprocessManager."""
        tts_engine_path = PROJECT_ROOT / "modules" / "tts_engine.py"
        with open(tts_engine_path, "r") as f:
            content = f.read()
        
        assert "from modules.piper_loader import PiperSubprocessManager" in content
        assert "self._piper_manager = PiperSubprocessManager()" in content

    def test_piper_worker_uses_length_scale(self):
        """Test that the Piper worker script computes length_scale from speed."""
        piper_loader_path = PROJECT_ROOT / "modules" / "piper_loader.py"
        with open(piper_loader_path, "r") as f:
            content = f.read()
        
        assert "length_scale = 1.0 / speed" in content or "length_scale=1.0 / speed" in content
        assert "SynthesisConfig" in content
        assert "length_scale" in content

    def test_piper_worker_has_cuda_support(self):
        """Test that worker attempts CUDA load if available."""
        piper_loader_path = PROJECT_ROOT / "modules" / "piper_loader.py"
        with open(piper_loader_path, "r") as f:
            content = f.read()
        
        assert "CUDAExecutionProvider" in content or "cuda" in content.lower()


class TestAudioMixerNumpy:
    """Test AudioMixer uses numpy instead of FFmpeg for mixing."""

    def test_audio_mixer_imports_numpy(self):
        """Test that audio_mixer imports numpy."""
        from modules.audio_mixer import AudioMixer
        import inspect
        
        source = inspect.getsource(AudioMixer._do_process)
        assert "import numpy as np" in source or "from numpy" in source

    def test_audio_mixer_uses_numpy_operations(self):
        """Test that AudioMixer._do_process uses numpy arrays for mixing."""
        from modules.audio_mixer import AudioMixer
        import inspect
        
        source = inspect.getsource(AudioMixer._do_process)
        assert "np.frombuffer" in source or "numpy.frombuffer" in source
        assert "np.pad" in source or "numpy.pad" in source

    def test_audio_mixer_comment_mentions_numpy(self):
        """Test that code comment indicates numpy mixing."""
        from modules.audio_mixer import AudioMixer
        import inspect
        
        source = inspect.getsource(AudioMixer._do_process)
        assert "numpy" in source.lower() or "np." in source


class TestPipelineReconfigure:
    """Test pipeline reconfigure injects chunk_duration_sec."""

    def test_pipeline_has_reconfigure_method(self):
        """Test that pipeline has reconfigure implementation."""
        from core.pipeline import Pipeline
        assert hasattr(Pipeline, 'reconfigure')
        
        import inspect
        source = inspect.getsource(Pipeline.reconfigure)
        assert 'chunk_duration_sec' in source

    def test_pipeline_reconfigure_injects_chunk_duration(self):
        """Test that reconfigure injects chunk_duration into input config."""
        from core.pipeline import Pipeline
        import inspect
        
        source = inspect.getsource(Pipeline.reconfigure)
        # Should inject pipeline chunk_duration into input type_config
        assert 'pipeline_config' in source or 'chunk_duration_sec' in source
        assert 'type_config' in source


class TestConfigValues:
    """Test config.yaml has correct low-latency settings."""

    def test_chunk_duration_is_10_seconds(self):
        """Test pipeline.chunk_duration_sec = 10."""
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        assert config['pipeline']['chunk_duration_sec'] == 10

    def test_hls_segment_duration_is_10(self):
        """Test output.web.segment_duration = 10."""
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        assert config['output']['web']['segment_duration'] == 10

    def test_hls_list_size_is_2(self):
        """Test output.web.list_size = 2 (20s buffer)."""
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        assert config['output']['web']['list_size'] == 2

    def test_video_muxer_has_hls_settings(self):
        """Test video_muxer has hls_segment_duration and hls_list_size."""
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        vm = config['modules']['video_muxer']
        assert 'hls_segment_duration' in vm
        assert 'hls_list_size' in vm

    def test_audio_mixer_original_volume_exists(self):
        """Test modules.audio_mixer.original_volume exists."""
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        
        am = config['modules']['audio_mixer']
        assert 'original_volume' in am


class TestSRTInputBehavior:
    """Test SRT input processing logic."""

    def test_srt_input_has_buffer_for_previous_chunk(self):
        """Test SRT input maintains previous chunk for pairing."""
        srt_input_path = PROJECT_ROOT / "modules" / "inputs" / "srt_input.py"
        with open(srt_input_path, "r") as f:
            content = f.read()
        
        assert "_prev_chunk" in content or "_previous" in content or "_last_chunk" in content

    def test_srt_input_uses_idx_condition(self):
        """Test SRT input uses chunk index to decide when to process."""
        srt_input_path = PROJECT_ROOT / "modules" / "inputs" / "srt_input.py"
        with open(srt_input_path, "r") as f:
            content = f.read()
        
        assert "idx > 0" in content or "idx == 0" in content or "if idx" in content


class TestAudioMixerDurationCheck:
    """Test that AudioMixer includes duration verification."""

    def test_audio_mixer_sets_duration_in_output(self):
        """Test that AudioMixer._do_process sets data.duration."""
        from modules.audio_mixer import AudioMixer
        import inspect
        
        source = inspect.getsource(AudioMixer._do_process)
        assert "data.duration" in source
