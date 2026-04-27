/**
 * Dashboard - Entry point for the SRT2Web frontend.
 *
 * This file handles user interactions, API calls, and config collection.
 * State management is delegated to signals (store/signals.ts).
 * DOM updates are handled automatically by effects (store/effects.ts).
 */

import { apiCall, getConfig, getStatus, startPipeline, stopPipeline, WSClient, getWebSocketUrl, updateChunkDuration } from './api';
import { copyToClipboard, showToast } from './utils';
import { formatTime } from './utils/format';
import { MESSAGES, DEFAULTS, INTERVALS, MODULE_TITLES } from './constants';
import {
  pipelineStatus,
  pipelineConfig,
  wsConnected,
  updateStatus,
  addLog,
  resetThroughput,
  startEffects,
  stopEffects,
  connectionMode,
} from './store/index';
import type { Config, Status } from './types';
import type { InputConfig, ModulesConfig, WebSocketMessage } from './api';

// ── Notification helper ────────────────────────────────────────────────────────

function showNotification(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
  showToast(message, type);
}

// ── Pipeline control ──────────────────────────────────────────────────────────

export async function handleStart(): Promise<void> {
  try {
    addLog('INFO', MESSAGES.PIPELINE_STARTING);
    await startPipeline();
    const status = await getStatus();
    updateStatus(status);
    addLog('INFO', MESSAGES.PIPELINE_STARTED);
  } catch (e) {
    addLog('ERROR', `Error: ${(e as Error).message}`);
  }
}

export async function handleStop(): Promise<void> {
  if (!confirm(MESSAGES.PIPELINE_CONFIRM_STOP)) {
    return;
  }

  try {
    addLog('INFO', MESSAGES.PIPELINE_STOPPING);
    await stopPipeline();
    const status = await getStatus();
    updateStatus(status);
    resetThroughput();
    addLog('INFO', MESSAGES.PIPELINE_STOPPED);
  } catch (e) {
    addLog('ERROR', `Error: ${(e as Error).message}`);
  }
}

export async function handleSaveConfig(): Promise<void> {
  try {
    const newConfig = collectConfigFromUI();
    
    // Extract chunk duration for sync endpoint
    const chunkDuration = parseInt(
      (document.getElementById('input-chunk-duration') as HTMLInputElement)?.value
      || (document.getElementById('input-rtmp-chunk') as HTMLInputElement)?.value
      || (document.getElementById('input-file-chunk') as HTMLInputElement)?.value
      || String(DEFAULTS.CHUNK_DURATION)
    );
    
    await apiCall('PUT', '/api/config', { config: newConfig });
    
    // Sync chunk duration to all pipeline modules
    try {
      await updateChunkDuration(chunkDuration);
      addLog('INFO', `Chunk synced: ${chunkDuration}s`);
    } catch (chunkError) {
      addLog('WARNING', `Chunk sync failed: ${(chunkError as Error).message}`);
    }
    
    const cfg = await getConfig();
    pipelineConfig.value = cfg;
    applyConfigToUI(cfg);
    showToast(MESSAGES.CONFIG_SAVED, 'success');
    addLog('INFO', 'Configuración guardada');
  } catch (e) {
    const msg = (e as Error).message;
    showToast(`${MESSAGES.CONFIG_SAVE_ERROR}: ${msg}`, 'error');
    addLog('ERROR', `Error al guardar: ${msg}`);
  }
}

// ── Config collection ─────────────────────────────────────────────────────────

export function collectConfigFromUI(): Partial<Config> {
  const inputType = (document.getElementById('input-type') as HTMLSelectElement)?.value || 'srt';
  const outputType = (document.getElementById('output-type') as HTMLSelectElement)?.value || 'webplayer';

  const chunkDuration = parseInt(
    (document.getElementById('input-chunk-duration') as HTMLInputElement)?.value
    || (document.getElementById('input-rtmp-chunk') as HTMLInputElement)?.value
    || (document.getElementById('input-file-chunk') as HTMLInputElement)?.value
    || String(DEFAULTS.CHUNK_DURATION)
  );

  const inputConfig: InputConfig = { type: inputType as InputConfig['type'] };

  if (inputType === 'srt') {
    inputConfig.srt = {
      listen_port: parseInt((document.getElementById('input-srt-port') as HTMLInputElement)?.value || '9000'),
      mode: ((document.getElementById('input-srt-mode') as HTMLSelectElement)?.value || 'listener') as 'listener' | 'caller',
      latency_ms: parseInt((document.getElementById('input-srt-latency') as HTMLInputElement)?.value || '200'),
      caller_address: '',
      chunk_duration_sec: chunkDuration,
    };
  } else if (inputType === 'rtmp') {
    inputConfig.rtmp = {
      url: (document.getElementById('input-rtmp-url') as HTMLInputElement)?.value || 'rtmp://localhost/live/stream',
      mode: ((document.getElementById('input-rtmp-mode') as HTMLSelectElement)?.value || 'pull') as 'listener' | 'pull',
      app: (document.getElementById('input-rtmp-app') as HTMLInputElement)?.value || 'live',
      listen_port: 1935,
      stream_key: '',
      chunk_duration_sec: chunkDuration,
    };
  } else if (inputType === 'file') {
    inputConfig.file = {
      path: (document.getElementById('input-file-path') as HTMLInputElement)?.value || '',
      loop: (document.getElementById('input-file-loop') as HTMLSelectElement)?.value === 'true',
      speed: parseFloat((document.getElementById('input-file-speed') as HTMLInputElement)?.value || String(DEFAULTS.TTS_SPEED)),
      chunk_duration_sec: chunkDuration,
    };
  }

  const configModules: ModulesConfig = {
    audio_extractor: {
      enabled: true,
    },
    transcriber: {
      enabled: (document.getElementById('whisper-enabled') as HTMLInputElement)?.checked ?? true,
      model: ((document.getElementById('whisper-model') as HTMLSelectElement)?.value || DEFAULTS.WHISPER_MODEL) as any,
      language: ((document.getElementById('whisper-lang') as HTMLSelectElement)?.value || DEFAULTS.WHISPER_LANGUAGE) as any,
      device: ((document.getElementById('whisper-device') as HTMLSelectElement)?.value || 'auto') as any,
      beam_size: 2,
    },
    translator: {
      enabled: (document.getElementById('translator-enabled') as HTMLInputElement)?.checked ?? true,
      source_lang: ((document.getElementById('translator-source') as HTMLSelectElement)?.value || DEFAULTS.WHISPER_LANGUAGE) as any,
      target_lang: ((document.getElementById('translator-target') as HTMLSelectElement)?.value || DEFAULTS.TRANSLATE_TARGET) as any,
    },
    tts_engine: {
      enabled: (document.getElementById('tts-enabled') as HTMLInputElement)?.checked ?? true,
      engine: ((document.getElementById('tts-engine') as HTMLSelectElement)?.value || 'edge-tts') as any,
      voice: (document.getElementById('tts-engine') as HTMLSelectElement)?.value === 'piper'
        ? ((document.getElementById('tts-voice-piper') as HTMLSelectElement)?.value || 'es_ES-sharvard-medium')
        : ((document.getElementById('tts-voice-edge') as HTMLSelectElement)?.value || 'es-ES-ElviraNeural'),
      speed: parseFloat((document.getElementById('tts-speed') as HTMLInputElement)?.value || String(DEFAULTS.TTS_SPEED)),
      device: ((document.getElementById('tts-device') as HTMLSelectElement)?.value || 'auto') as any,
    },
    subtitle_generator: {
      enabled: (document.getElementById('subtitle-enabled') as HTMLInputElement)?.checked ?? true,
      format: ((document.getElementById('subtitle-format') as HTMLSelectElement)?.value || DEFAULTS.SUBTITLE_FORMAT) as any,
      use_translated: (document.getElementById('subtitle-use-translated') as HTMLSelectElement)?.value === 'true',
      chunk_duration: chunkDuration,
    },
    audio_mixer: {
      enabled: (document.getElementById('audio-mixer-enabled') as HTMLInputElement)?.checked ?? false,
      original_volume: parseFloat((document.getElementById('audio-mixer-original-volume') as HTMLInputElement)?.value || String(DEFAULTS.ORIGINAL_VOLUME)),
      tts_volume: parseFloat((document.getElementById('audio-mixer-dubbed-volume') as HTMLInputElement)?.value || String(DEFAULTS.TTS_VOLUME)),
      dubbed_volume: parseFloat((document.getElementById('audio-mixer-dubbed-volume') as HTMLInputElement)?.value || String(DEFAULTS.TTS_VOLUME)),
    },
    video_muxer: {
      enabled: (document.getElementById('muxer-enabled') as HTMLInputElement)?.checked ?? true,
      engine: ((document.getElementById('video-muxer-engine') as HTMLSelectElement)?.value || 'hls') as 'hls' | 'webrtc',
      hls_segment_duration: parseInt((document.getElementById('hls-segment') as HTMLInputElement)?.value || String(DEFAULTS.SEGMENT_DURATION)),
      hls_list_size: parseInt((document.getElementById('hls-list') as HTMLInputElement)?.value || String(DEFAULTS.LIST_SIZE)),
      audio_offset_ms: parseInt((document.getElementById('hls-audio-offset') as HTMLInputElement)?.value || String(DEFAULTS.AUDIO_OFFSET)),
      encoder_mode: ((document.getElementById('hls-encoder') as HTMLSelectElement)?.value || 'auto') as any,
      video_quality: 'medium',
      video_crf: parseInt((document.getElementById('hls-crf') as HTMLInputElement)?.value || String(DEFAULTS.CRF)),
      audio_codec: ((document.getElementById('video-muxer-engine') as HTMLSelectElement)?.value === 'webrtc'
        ? (document.getElementById('webrtc-audio-codec') as HTMLSelectElement)?.value
        : (document.getElementById('hls-audio-codec') as HTMLSelectElement)?.value) as any || 'aac',
      audio_bitrate: (document.getElementById('hls-audio-bitrate') as HTMLSelectElement)?.value || '192k',
      audio_samplerate: '48000',
      video_codec: ((document.getElementById('webrtc-video-codec') as HTMLSelectElement)?.value as any),
      video_bitrate: (document.getElementById('webrtc-video-bitrate') as HTMLSelectElement)?.value,
      video_fps: (document.getElementById('webrtc-video-fps') as HTMLSelectElement)
        ? parseInt((document.getElementById('webrtc-video-fps') as HTMLSelectElement).value)
        : undefined,
      audio_sample_rate: (document.getElementById('webrtc-audio-sample-rate') as HTMLSelectElement)
        ? parseInt((document.getElementById('webrtc-audio-sample-rate') as HTMLSelectElement).value)
        : undefined,
      ...((): { video_width?: number; video_height?: number } => {
        const resEl = document.getElementById('webrtc-video-resolution') as HTMLSelectElement;
        if (resEl?.value) {
          const [w, h] = resEl.value.split('x').map(Number);
          return { video_width: w, video_height: h };
        }
        return {};
      })(),
    },
  };

  return {
    input: inputConfig,
    pipeline: { 
      chunk_duration_sec: chunkDuration,
      mode: 'sequential',
      max_concurrent_chunks: 2,
      buffer_size: 10,
      retry_attempts: 3,
      retry_delay: 1000,
    },
    modules: configModules,
  };
}

// ── Config application ─────────────────────────────────────────────────────────

export function applyConfigToUI(cfg: Config): void {
  const inputTypeSelect = document.getElementById('input-type') as HTMLSelectElement;
  const outputTypeSelect = document.getElementById('output-type') as HTMLSelectElement;

  const whisperEnabled = document.getElementById('whisper-enabled') as HTMLInputElement;
  const whisperModel = document.getElementById('whisper-model') as HTMLSelectElement;
  const whisperLang = document.getElementById('whisper-lang') as HTMLSelectElement;
  const whisperDevice = document.getElementById('whisper-device') as HTMLSelectElement;
  const translatorEnabled = document.getElementById('translator-enabled') as HTMLInputElement;
  const translatorSource = document.getElementById('translator-source') as HTMLSelectElement;
  const translatorTarget = document.getElementById('translator-target') as HTMLSelectElement;
  const ttsEnabled = document.getElementById('tts-enabled') as HTMLInputElement;
  const ttsEngine = document.getElementById('tts-engine') as HTMLSelectElement;
  const ttsDevice = document.getElementById('tts-device') as HTMLSelectElement;
  const ttsDeviceGroup = document.getElementById('tts-device-group') as HTMLDivElement;
  const ttsVoiceEdge = document.getElementById('tts-voice-edge') as HTMLSelectElement;
  const ttsVoicePiper = document.getElementById('tts-voice-piper') as HTMLSelectElement;
  const ttsVoiceEdgeGroup = document.getElementById('tts-voice-edge-group') as HTMLDivElement;
  const ttsVoicePiperGroup = document.getElementById('tts-voice-piper-group') as HTMLDivElement;
  const ttsSpeed = document.getElementById('tts-speed') as HTMLInputElement;
  const subtitleEnabled = document.getElementById('subtitle-enabled') as HTMLInputElement;
  const subtitleFormat = document.getElementById('subtitle-format') as HTMLSelectElement;
  const subtitleUseTranslated = document.getElementById('subtitle-use-translated') as HTMLSelectElement;
  const muxerEnabled = document.getElementById('muxer-enabled') as HTMLInputElement;
  const videoMuxerEngine = document.getElementById('video-muxer-engine') as HTMLSelectElement;
  const hlsSegment = document.getElementById('hls-segment') as HTMLInputElement;
  const hlsList = document.getElementById('hls-list') as HTMLInputElement;
  const hlsEncoder = document.getElementById('hls-encoder') as HTMLSelectElement;
  const hlsCrf = document.getElementById('hls-crf') as HTMLInputElement;
  const hlsAudioOffset = document.getElementById('hls-audio-offset') as HTMLInputElement;
  const hlsAudioCodec = document.getElementById('hls-audio-codec') as HTMLSelectElement;
  const hlsAudioBitrate = document.getElementById('hls-audio-bitrate') as HTMLSelectElement;

  const inputType = cfg.input?.type || 'srt';
  if (inputTypeSelect) {
    inputTypeSelect.value = inputType;
    updateInputFields();
  }

  // SRT config
  const srtPortInput = document.getElementById('input-srt-port') as HTMLInputElement;
  const srtModeSelect = document.getElementById('input-srt-mode') as HTMLSelectElement;
  const srtLatencyInput = document.getElementById('input-srt-latency') as HTMLInputElement;
  const inputSrtConfig = cfg.input?.srt;
  if (srtPortInput && inputSrtConfig?.listen_port) srtPortInput.value = String(inputSrtConfig.listen_port);
  if (srtModeSelect && inputSrtConfig?.mode) srtModeSelect.value = inputSrtConfig.mode;
  if (srtLatencyInput && inputSrtConfig?.latency_ms) srtLatencyInput.value = String(inputSrtConfig.latency_ms);

  // Chunk duration
  const srtChunkInput = document.getElementById('input-chunk-duration') as HTMLInputElement;
  const rtmpChunkInput = document.getElementById('input-rtmp-chunk') as HTMLInputElement;
  const fileChunkInput = document.getElementById('input-file-chunk') as HTMLInputElement;
  const pipelineChunkDuration = cfg.pipeline?.chunk_duration_sec || DEFAULTS.CHUNK_DURATION;
  const chunkDuration = pipelineChunkDuration;

  if (srtChunkInput) {
    srtChunkInput.value = String(inputSrtConfig?.chunk_duration_sec || chunkDuration);
  }
  const inputRtmpConfig = cfg.input?.rtmp;
  const inputFileConfig = cfg.input?.file;
  if (rtmpChunkInput) {
    rtmpChunkInput.value = String(inputRtmpConfig?.chunk_duration_sec || chunkDuration);
  }

  // RTMP config
  const rtmpUrlInput = document.getElementById('input-rtmp-url') as HTMLInputElement;
  const rtmpModeSelect2 = document.getElementById('input-rtmp-mode') as HTMLSelectElement;
  const rtmpAppInput = document.getElementById('input-rtmp-app') as HTMLInputElement;
  if (rtmpUrlInput && inputRtmpConfig?.url) rtmpUrlInput.value = inputRtmpConfig.url;
  if (rtmpModeSelect2 && inputRtmpConfig?.mode) rtmpModeSelect2.value = inputRtmpConfig.mode;
  if (rtmpAppInput && inputRtmpConfig?.app) rtmpAppInput.value = inputRtmpConfig.app;

  // File config
  const filePathInput = document.getElementById('input-file-path') as HTMLInputElement;
  const fileLoopSelect = document.getElementById('input-file-loop') as HTMLSelectElement;
  const fileSpeedInput = document.getElementById('input-file-speed') as HTMLInputElement;
  if (filePathInput && inputFileConfig?.path) filePathInput.value = inputFileConfig.path;
  if (fileLoopSelect && inputFileConfig?.loop !== undefined) fileLoopSelect.value = inputFileConfig.loop ? 'true' : 'false';
  if (fileSpeedInput && inputFileConfig?.speed) fileSpeedInput.value = String(inputFileConfig.speed);
  if (fileChunkInput) {
    fileChunkInput.value = String(inputFileConfig?.chunk_duration_sec || chunkDuration);
  }

  // Output type
  const outputType = cfg.output?.type === 'web' ? 'webplayer' : (cfg.output?.type || 'webplayer');
  if (outputTypeSelect) {
    outputTypeSelect.value = outputType;
    updateOutputFields();
  }

  if (whisperEnabled) whisperEnabled.checked = cfg.modules.transcriber.enabled;
  if (whisperModel) whisperModel.value = cfg.modules.transcriber.model;
  if (whisperLang) whisperLang.value = cfg.modules.transcriber.language;
  if (whisperDevice) whisperDevice.value = cfg.modules.transcriber.device;
  if (translatorEnabled) translatorEnabled.checked = cfg.modules.translator.enabled;
  if (translatorSource) translatorSource.value = cfg.modules.translator.source_lang;
  if (translatorTarget) translatorTarget.value = cfg.modules.translator.target_lang;
  if (ttsEnabled) ttsEnabled.checked = cfg.modules.tts_engine.enabled;
  if (ttsEngine) {
    ttsEngine.value = cfg.modules.tts_engine.engine || 'edge-tts';
    if (ttsDeviceGroup) ttsDeviceGroup.style.display = ttsEngine.value === 'piper' ? 'block' : 'none';
    if (ttsVoiceEdgeGroup && ttsVoicePiperGroup) {
      const isEdge = ttsEngine.value === 'edge-tts';
      ttsVoiceEdgeGroup.style.display = isEdge ? 'block' : 'none';
      ttsVoicePiperGroup.style.display = isEdge ? 'none' : 'block';
    }
  }
  if (ttsDevice) ttsDevice.value = cfg.modules.tts_engine.device || 'auto';
  if (ttsVoiceEdge) ttsVoiceEdge.value = cfg.modules.tts_engine.voice || 'es-ES-AlvaroNeural';
  if (ttsVoicePiper) ttsVoicePiper.value = cfg.modules.tts_engine.voice || 'es_ES-sharvard-medium';
  if (ttsSpeed) ttsSpeed.value = String(cfg.modules.tts_engine.speed);
  if (subtitleEnabled) subtitleEnabled.checked = cfg.modules.subtitle_generator.enabled;
  if (subtitleFormat) subtitleFormat.value = cfg.modules.subtitle_generator.format;
  if (subtitleUseTranslated) subtitleUseTranslated.value = String(cfg.modules.subtitle_generator.use_translated);
  if (muxerEnabled) muxerEnabled.checked = cfg.modules.video_muxer.enabled;
  if (videoMuxerEngine) {
    videoMuxerEngine.value = cfg.modules.video_muxer.engine || 'hls';
  }
  const audioMixerEnabled = document.getElementById('audio-mixer-enabled') as HTMLInputElement;
  if (audioMixerEnabled) audioMixerEnabled.checked = cfg.modules.audio_mixer?.enabled ?? false;

  const originalVolume = document.getElementById('audio-mixer-original-volume') as HTMLInputElement;
  if (originalVolume) originalVolume.value = String(cfg.modules.audio_mixer?.original_volume ?? 0.3);
  const originalValue = document.getElementById('audio-mixer-original-value') as HTMLSpanElement;
  if (originalValue) originalValue.textContent = String(cfg.modules.audio_mixer?.original_volume ?? 0.3);

  const ttsVolume = document.getElementById('audio-mixer-dubbed-volume') as HTMLInputElement;
  if (ttsVolume) ttsVolume.value = String(cfg.modules.audio_mixer?.tts_volume ?? cfg.modules.audio_mixer?.dubbed_volume ?? 1.0);
  const ttsValue = document.getElementById('audio-mixer-dubbed-value') as HTMLSpanElement;
  if (ttsValue) ttsValue.textContent = String(cfg.modules.audio_mixer?.tts_volume ?? cfg.modules.audio_mixer?.dubbed_volume ?? 1.0);

  if (hlsSegment) hlsSegment.value = String(cfg.modules.video_muxer.hls_segment_duration);
  if (hlsList) hlsList.value = String(cfg.modules.video_muxer.hls_list_size);
  if (hlsEncoder) hlsEncoder.value = cfg.modules.video_muxer.encoder_mode;
  if (hlsCrf) hlsCrf.value = String(cfg.modules.video_muxer.video_crf);
  if (hlsAudioOffset) hlsAudioOffset.value = String(cfg.modules.video_muxer.audio_offset_ms || 0);
  if (hlsAudioCodec) hlsAudioCodec.value = cfg.modules.video_muxer.audio_codec || 'aac';
  if (hlsAudioBitrate) hlsAudioBitrate.value = cfg.modules.video_muxer.audio_bitrate || '192k';

  // WebRTC
  const webrtcEncoder = document.getElementById('webrtc-encoder') as HTMLSelectElement;
  const webrtcVideoCodec = document.getElementById('webrtc-video-codec') as HTMLSelectElement;
  const webrtcVideoBitrate = document.getElementById('webrtc-video-bitrate') as HTMLSelectElement;
  const webrtcVideoResolution = document.getElementById('webrtc-video-resolution') as HTMLSelectElement;
  const webrtcVideoFPS = document.getElementById('webrtc-video-fps') as HTMLSelectElement;
  const webrtcAudioCodec = document.getElementById('webrtc-audio-codec') as HTMLSelectElement;
  const webrtcAudioBitrate = document.getElementById('webrtc-audio-bitrate') as HTMLSelectElement;
  const webrtcAudioSampleRate = document.getElementById('webrtc-audio-sample-rate') as HTMLSelectElement;

  if (webrtcEncoder) webrtcEncoder.value = cfg.modules.video_muxer.encoder_mode || 'auto';
  if (webrtcVideoCodec) webrtcVideoCodec.value = cfg.modules.video_muxer.video_codec || 'h264';
  if (webrtcVideoBitrate) webrtcVideoBitrate.value = cfg.modules.video_muxer.video_bitrate || '1000k';
  if (webrtcVideoResolution && cfg.modules.video_muxer.video_width && cfg.modules.video_muxer.video_height) {
    webrtcVideoResolution.value = `${cfg.modules.video_muxer.video_width}x${cfg.modules.video_muxer.video_height}`;
  }
  if (webrtcVideoFPS && cfg.modules.video_muxer.video_fps) {
    webrtcVideoFPS.value = String(cfg.modules.video_muxer.video_fps);
  }
  if (webrtcAudioCodec) webrtcAudioCodec.value = cfg.modules.video_muxer.audio_codec || 'opus';
  if (webrtcAudioBitrate) webrtcAudioBitrate.value = cfg.modules.video_muxer.webrtc_audio_bitrate || cfg.modules.video_muxer.audio_bitrate || '64k';
  if (webrtcAudioSampleRate && cfg.modules.video_muxer.audio_sample_rate) {
    webrtcAudioSampleRate.value = String(cfg.modules.video_muxer.audio_sample_rate);
  }
}

// ── Form visibility helpers ───────────────────────────────────────────────────

export function updateInputFields(): void {
  const inputTypeSelect = document.getElementById('input-type') as HTMLSelectElement;
  if (inputTypeSelect) {
    inputTypeSelect.value = inputTypeSelect.value as 'srt' | 'rtmp' | 'file';
  }
}

export function updateOutputFields(): void {
  const outputTypeSelect = document.getElementById('output-type') as HTMLSelectElement;
  if (outputTypeSelect) {
    outputTypeSelect.value = outputTypeSelect.value as 'webplayer' | 'srt' | 'rtmp' | 'file';
  }
}

export function handleTtsEngineChange(engine: string): void {
  const ttsEngineSelect = document.getElementById('tts-engine') as HTMLSelectElement;
  if (ttsEngineSelect) {
    ttsEngineSelect.value = engine;
  }
}

export function handleInputTypeChange(type: string): void {
  updateInputFields();

  if (type === 'rtmp') updateRtmpUrl();

  if (type === 'file') {
    const filePathInput = document.getElementById('input-file-path') as HTMLInputElement;
    const playerControls = document.getElementById('file-player-controls');
    if (filePathInput && filePathInput.value && playerControls) {
      playerControls.style.display = 'flex';
      setupFilePlayerControls();
    }
  }

  const inputTitle = document.getElementById('input-process-title');
  if (inputTitle) {
    const titles: Record<string, string> = {
      srt: `${MODULE_TITLES.input} (SRT)`,
      rtmp: `${MODULE_TITLES.input} (RTMP)`,
      file: `${MODULE_TITLES.input} (File)`,
    };
    inputTitle.textContent = titles[type] || '📥 INPUT';
  }

  updateConnectionInfoDisplay();
}

export function handleOutputFormatChange(_format: string): void {
  // Reserved for future output format changes
}

// ── RTMP helpers ──────────────────────────────────────────────────────────────

export function updateRtmpUrl(): void {
  const rtmpUrlInput = document.getElementById('input-rtmp-url') as HTMLInputElement;
  if (!rtmpUrlInput) return;

  const portInput = document.getElementById('input-rtmp-port') as HTMLInputElement;
  const appInput = document.getElementById('input-rtmp-app') as HTMLInputElement;
  const keyInput = document.getElementById('input-rtmp-key') as HTMLInputElement;

  const port = portInput?.value || '1935';
  const app = appInput?.value || 'live';
  const key = keyInput?.value || 'stream';

  rtmpUrlInput.value = `rtmp://127.0.0.1:${port}/${app}/${key}`;
  updateConnectionInfoDisplay();
}

export function copyRtmpUrl(): void {
  const rtmpUrlInput = document.getElementById('input-rtmp-url') as HTMLInputElement;
  if (!rtmpUrlInput?.value) return;

  navigator.clipboard.writeText(rtmpUrlInput.value).then(() => {
    showToast(MESSAGES.URL_COPIED, 'success');
  }).catch(() => {
    showToast(MESSAGES.URL_COPY_ERROR, 'error');
  });
}

// ── Connection info display ──────────────────────────────────────────────────

export function updateConnectionInfoDisplay(): void {
  // Connection URL display is now handled by the connectionUrls effect
  // This function is kept for backwards compatibility but does nothing
  // The effect reads from connectionUrls.value and updates the DOM
}

// ── File input controls ──────────────────────────────────────────────────────

export function handleFileSelect(input: HTMLInputElement): void {
  const filePathInput = document.getElementById('input-file-path') as HTMLInputElement;
  if (!filePathInput || !input.files?.length) return;

  const fileName = input.files[0].name;
  filePathInput.placeholder = `Ej: C:\\Users\\bruno\\Desktop\\${fileName}`;
    showToast(MESSAGES.INPUT_FILE_SELECTED, 'info');
  filePathInput.focus();

  const playerControls = document.getElementById('file-player-controls');
  if (playerControls) playerControls.style.display = 'flex';
  setupFilePlayerControls();
}

export async function fileInputPlay(): Promise<void> {
  try {
    await apiCall('POST', 'input/control/play');
    showToast(MESSAGES.INPUT_FILE_PLAY, 'success');
  } catch (e) {
    showToast(`Error al reproducir: ${(e as Error).message}`, 'error');
  }
}

export async function fileInputPause(): Promise<void> {
  try {
    await apiCall('POST', 'input/control/pause');
    showToast(MESSAGES.INPUT_FILE_PAUSE, 'success');
  } catch (e) {
    showToast(`Error al pausar: ${(e as Error).message}`, 'error');
  }
}

export async function fileInputSeek(position: number): Promise<void> {
  try {
    await apiCall('POST', 'input/control/seek', { position });
  } catch (e) {
    showToast(`Error al buscar posición: ${(e as Error).message}`, 'error');
  }
}

async function fetchFileInfo(): Promise<{ duration: number; position: number; is_playing: boolean } | null> {
  try {
    const response = await fetch(`${window.location.origin}/api/input-info`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) return null;
    const data = await response.json();
    if (data.type === 'file') {
      return {
        duration: data.duration || 0,
        position: data.position || 0,
        is_playing: data.is_playing || false,
      };
    }
    return null;
  } catch {
    return null;
  }
}

let filePollingInterval: ReturnType<typeof setInterval> | null = null;

function startFileInfoPolling(): void {
  if (filePollingInterval) clearInterval(filePollingInterval);

  const positionSlider = document.getElementById('input-file-position') as HTMLInputElement | null;
  const currentDisplay = document.getElementById('file-time-current') as HTMLSpanElement | null;
  const totalDisplay = document.getElementById('file-time-total') as HTMLSpanElement | null;
  const playBtn = document.getElementById('btn-file-play') as HTMLButtonElement | null;
  const pauseBtn = document.getElementById('btn-file-pause') as HTMLButtonElement | null;

  filePollingInterval = setInterval(() => {
    fetchFileInfo().then(info => {
      if (!info) return;

      if (positionSlider && info.duration > 0) {
        positionSlider.value = ((info.position / info.duration) * 100).toString();
      }
      if (currentDisplay) currentDisplay.textContent = formatTime(info.position);
      if (totalDisplay) totalDisplay.textContent = formatTime(info.duration);

      if (playBtn && pauseBtn) {
        if (info.is_playing) {
          playBtn.style.display = 'none';
          pauseBtn.style.display = 'inline';
        } else {
          playBtn.style.display = 'inline';
          pauseBtn.style.display = 'none';
        }
      }
    });
  }, INTERVALS.FILE_POLL);
}

export function stopFileInfoPolling(): void {
  if (filePollingInterval) {
    clearInterval(filePollingInterval);
    filePollingInterval = null;
  }
}

export function setupFilePlayerControls(): void {
  const playBtn = document.getElementById('btn-file-play') as HTMLButtonElement | null;
  const pauseBtn = document.getElementById('btn-file-pause') as HTMLButtonElement | null;
  const restartBtn = document.getElementById('btn-file-restart') as HTMLButtonElement | null;
  const positionSlider = document.getElementById('input-file-position') as HTMLInputElement | null;

  if (!playBtn || !pauseBtn || !restartBtn || !positionSlider) return;

  playBtn.style.display = 'inline';
  pauseBtn.style.display = 'none';

  playBtn.addEventListener('click', () => {
    fileInputPlay().then(() => {
      playBtn.style.display = 'none';
      pauseBtn.style.display = 'inline';
    });
  });

  pauseBtn.addEventListener('click', () => {
    fileInputPause().then(() => {
      pauseBtn.style.display = 'none';
      playBtn.style.display = 'inline';
    });
  });

  restartBtn.addEventListener('click', () => {
    fileInputSeek(0).then(() => {
      positionSlider.value = '0';
      fileInputPlay().then(() => {
        playBtn.style.display = 'none';
        pauseBtn.style.display = 'inline';
      });
    });
  });

  let seekTimeout: ReturnType<typeof setTimeout> | null = null;
  positionSlider.addEventListener('input', () => {
    if (seekTimeout) clearTimeout(seekTimeout);
    const percent = parseInt(positionSlider.value);

    seekTimeout = setTimeout(() => {
      fetchFileInfo().then(info => {
        if (info?.duration) {
          fileInputSeek((percent / 100) * info.duration);
        }
      });
    }, INTERVALS.SEEK_DEBOUNCE);
  });

  startFileInfoPolling();
}

// ── Event setup ───────────────────────────────────────────────────────────────

export function setupEventListeners(): void {
  document.getElementById('btn-start')?.addEventListener('click', handleStart);
  document.getElementById('btn-stop')?.addEventListener('click', handleStop);
}

function setupCopyButtons(): void {
  document.getElementById('btn-copy-emision')?.addEventListener('click', () => {
    const urlEl = document.getElementById('url-emision');
    if (urlEl?.textContent) {
      copyToClipboard(urlEl.textContent).then(() => showNotification('URL de emisión copiada', 'success')).catch(() => showNotification('Error al copiar URL', 'error'));
    }
  });

  document.getElementById('btn-copy-stream')?.addEventListener('click', () => {
    const urlEl = document.getElementById('url-stream');
    if (urlEl?.textContent) {
      copyToClipboard(urlEl.textContent).then(() => showNotification('URL del stream copiada', 'success')).catch(() => showNotification('Error al copiar URL', 'error'));
    }
  });

  document.getElementById('btn-copy-player')?.addEventListener('click', () => {
    const urlEl = document.getElementById('url-player');
    if (urlEl) {
      const url = urlEl.getAttribute('href') || urlEl.textContent;
      if (url) copyToClipboard(url).then(() => showNotification('URL del player copiada', 'success')).catch(() => showNotification('Error al copiar URL', 'error'));
    }
  });
}

// ── Initialization ────────────────────────────────────────────────────────────

let wsClient: WSClient | null = null;
let statusPollInterval: ReturnType<typeof setInterval> | null = null;

export async function initDashboard(): Promise<void> {
  addLog('INFO', MESSAGES.LOADING);

  try {
    // Load config and apply to UI
    const cfg = await getConfig();
    pipelineConfig.value = cfg;
    applyConfigToUI(cfg);

    // Initialize RTMP URL if needed
    const inputTypeSelect = document.getElementById('input-type') as HTMLSelectElement;
    if (inputTypeSelect?.value === 'rtmp') updateRtmpUrl();
    if (inputTypeSelect?.value === 'file') {
      const filePathInput = document.getElementById('input-file-path') as HTMLInputElement;
      if (filePathInput?.value) setupFilePlayerControls();
    }

    // Load initial status
    const initialStatus = await apiCall<Status>('GET', 'api/status');
    updateStatus(initialStatus);

    // Connection info display
    updateConnectionInfoDisplay();

    // Start effects (reactive DOM updates)
    startEffects();

    // WebSocket connection for logs + status
    const wsUrl = getWebSocketUrl('/ws/logs');
    wsClient = new WSClient(wsUrl);
    wsClient.onMessage((data: WebSocketMessage) => {
      if (data.type === 'log') {
        addLog(data.level ?? 'INFO', data.message ?? '');
      } else if (data.type === 'status' && data.status) {
        updateStatus(data.status);
      }
    });
    wsClient.onError(() => {
      addLog('ERROR', MESSAGES.WS_ERROR);
    });
    wsClient.onClose(() => {
      wsConnected.value = false;
      addLog('ERROR', MESSAGES.WS_DISCONNECTED);
    });
    wsClient.connect();

    // Fallback HTTP polling
    statusPollInterval = setInterval(async () => {
      try {
        const s = await apiCall<Status>('GET', 'api/status');
        updateStatus(s);
      } catch {
        // Silently fail on poll errors
      }
    }, INTERVALS.STATUS_POLL);

    addLog('INFO', MESSAGES.SUCCESS);
  } catch (e) {
    addLog('ERROR', `Error de inicialización: ${(e as Error).message}`);
  }
}

// ── Window exposure ───────────────────────────────────────────────────────────

function exposeWindow(): void {
  (window as any).toggleModule = toggleModule;
  (window as any).updateInputFields = updateInputFields;
  (window as any).updateOutputFields = updateOutputFields;
  (window as any).handleTtsEngineChange = handleTtsEngineChange;
  (window as any).handleInputTypeChange = handleInputTypeChange;
  (window as any).updateRtmpUrl = updateRtmpUrl;
  (window as any).copyRtmpUrl = copyRtmpUrl;
  (window as any).handleOutputFormatChange = handleOutputFormatChange;
  (window as any).saveConfig = handleSaveConfig;
  (window as any).init = initDashboard;
}

async function toggleModule(moduleName: string, enabled: boolean): Promise<void> {
  try {
    await apiCall('PUT', `modules/${moduleName}/toggle`, { enabled });
  } catch (e) {
    showToast(`Failed to toggle ${moduleName}: ${(e as Error).message}`, 'error');
  }
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

// Also run a direct status fetch on load to ensure metrics display
async function refreshMetrics() {
  try {
    const res = await fetch('/api/status');
    const status = await res.json();
    const s = status.system || {};
    
    // Direct DOM update as fallback (in case signals don't work)
    const cpuEl = document.getElementById('metric-cpu-value');
    const cpuBar = document.getElementById('metric-cpu-bar');
    const memEl = document.getElementById('metric-memory-value');
    const memPercent = document.getElementById('metric-memory-percent');
    const memBar = document.getElementById('metric-memory-bar');
    const gpuEl = document.getElementById('metric-gpu-value');
    const gpuBar = document.getElementById('metric-gpu-bar');
    
    if (cpuEl) cpuEl.textContent = (s.cpu_percent || s.cpu_usage || 0) + '%';
    if (cpuBar) cpuBar.style.width = (s.cpu_percent || s.cpu_usage || 0) + '%';
    if (memEl) memEl.textContent = (s.memory_mb || 0).toFixed(0) + ' MB';
    if (memPercent) memPercent.textContent = (s.memory_percent || s.memory_usage || 0) + '%';
    if (memBar) memBar.style.width = (s.memory_percent || s.memory_usage || 0) + '%';
    if (gpuEl) gpuEl.textContent = (s.gpu_usage || 0) + '%';
    if (gpuBar) gpuBar.style.width = (s.gpu_usage || 0) + '%';
  } catch(e) {
    console.error('Metrics refresh failed:', e);
  }
}

// Initialize on both DOMContentLoaded and load events for robustness
function bootstrap() {
  setupEventListeners();
  setupCopyButtons();
  exposeWindow();
  // Small delay to ensure DOM is fully rendered
  setTimeout(() => {
    initDashboard();
    // Direct metrics refresh as additional fallback
    refreshMetrics();
  }, 100);
}

document.addEventListener('DOMContentLoaded', bootstrap);
document.addEventListener('load', () => {
  // Also try on load as fallback
  setTimeout(() => {
    initDashboard();
    refreshMetrics();
  }, 500);
});
