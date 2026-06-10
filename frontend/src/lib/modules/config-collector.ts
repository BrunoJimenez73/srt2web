/**
 * Config Collector - Maneja la recolección y aplicación de configuración desde/al UI.
 *
 * Este módulo centraliza toda la lógica relacionada con:
 * - Recolectar configuración desde los elementos del DOM
 * - Aplicar configuración recibida del servidor a los elementos del DOM
 */

import { DEFAULTS } from "../constants";
import type { Config } from "../types";
import type { InputConfig, ModulesConfig } from "../api";
import type {
  WhisperModel,
  Language,
  Device,
  TtsEngine,
  SubtitleFormat,
  EncoderMode,
  AudioCodec,
  VideoCodec,
} from "../types/api";

// ── Config Collection ─────────────────────────────────────────────────────────

/**
 * Recolecta toda la configuración desde la UI del dashboard.
 * Lee los valores de todos los inputs, selects y checkboxes.
 */
export function collectConfigFromUI(): Partial<Config> {
  const inputType =
    (document.getElementById("input-type") as HTMLSelectElement)?.value ||
    "srt";
  const outputType =
    (document.getElementById("output-type") as HTMLSelectElement)?.value ||
    "webplayer";

  const chunkDuration = parseInt(
    (document.getElementById("input-chunk-duration") as HTMLInputElement)
      ?.value ||
      (document.getElementById("input-rtmp-chunk") as HTMLInputElement)
        ?.value ||
      (document.getElementById("input-file-chunk") as HTMLInputElement)
        ?.value ||
      String(DEFAULTS.CHUNK_DURATION),
  );

  const inputConfig: InputConfig = { type: inputType as InputConfig["type"] };

  if (inputType === "srt") {
    inputConfig.srt = {
      listen_port: parseInt(
        (document.getElementById("input-srt-port") as HTMLInputElement)
          ?.value || "9000",
      ),
      mode: ((document.getElementById("input-srt-mode") as HTMLSelectElement)
        ?.value || "listener") as "listener" | "caller",
      latency_ms: parseInt(
        (document.getElementById("input-srt-latency") as HTMLInputElement)
          ?.value || "200",
      ),
      caller_address: "",
      chunk_duration_sec: chunkDuration,
    };
  } else if (inputType === "rtmp") {
    inputConfig.rtmp = {
      url:
        (document.getElementById("input-rtmp-url") as HTMLInputElement)
          ?.value || "rtmp://localhost/live/stream",
      mode: ((document.getElementById("input-rtmp-mode") as HTMLSelectElement)
        ?.value || "pull") as "listener" | "pull",
      app:
        (document.getElementById("input-rtmp-app") as HTMLInputElement)
          ?.value || "live",
      listen_port: 1935,
      stream_key: "",
      chunk_duration_sec: chunkDuration,
    };
  } else if (inputType === "file") {
    inputConfig.file = {
      path:
        (document.getElementById("input-file-path") as HTMLInputElement)
          ?.value || "",
      loop:
        (document.getElementById("input-file-loop") as HTMLSelectElement)
          ?.value === "true",
      speed: parseFloat(
        (document.getElementById("input-file-speed") as HTMLInputElement)
          ?.value || String(DEFAULTS.TTS_SPEED),
      ),
      chunk_duration_sec: chunkDuration,
    };
  }

  const configModules: ModulesConfig = {
    audio_extractor: {
      enabled: true,
    },
    transcriber: {
      enabled:
        (document.getElementById("whisper-enabled") as HTMLInputElement)
          ?.checked ?? true,
      model: ((document.getElementById("whisper-model") as HTMLSelectElement)
        ?.value || DEFAULTS.WHISPER_MODEL) as WhisperModel,
      language: ((document.getElementById("whisper-lang") as HTMLSelectElement)
        ?.value || DEFAULTS.WHISPER_LANGUAGE) as Language,
      device: ((document.getElementById("whisper-device") as HTMLSelectElement)
        ?.value || "auto") as Device,
      beam_size: 2,
    },
    translator: {
      enabled:
        (document.getElementById("translator-enabled") as HTMLInputElement)
          ?.checked ?? true,
      source_lang: ((
        document.getElementById("translator-source") as HTMLSelectElement
      )?.value || DEFAULTS.WHISPER_LANGUAGE) as Language,
      target_lang: ((
        document.getElementById("translator-target") as HTMLSelectElement
      )?.value || DEFAULTS.TRANSLATE_TARGET) as Language,
    },
    tts_engine: {
      enabled:
        (document.getElementById("tts-enabled") as HTMLInputElement)?.checked ??
        true,
      engine: ((document.getElementById("tts-engine") as HTMLSelectElement)
        ?.value || "edge-tts") as TtsEngine,
      voice:
        (document.getElementById("tts-engine") as HTMLSelectElement)?.value ===
        "piper"
          ? (document.getElementById("tts-voice-piper") as HTMLSelectElement)
              ?.value || "es_ES-sharvard-medium"
          : (document.getElementById("tts-voice-edge") as HTMLSelectElement)
              ?.value || "es-ES-ElviraNeural",
      speed: parseFloat(
        (document.getElementById("tts-speed") as HTMLInputElement)?.value ||
          String(DEFAULTS.TTS_SPEED),
      ),
      device: ((document.getElementById("tts-device") as HTMLSelectElement)
        ?.value || "auto") as Device,
    },
    subtitle_generator: {
      enabled:
        (document.getElementById("subtitle-enabled") as HTMLInputElement)
          ?.checked ?? true,
      format: ((document.getElementById("subtitle-format") as HTMLSelectElement)
        ?.value || DEFAULTS.SUBTITLE_FORMAT) as SubtitleFormat,
      use_translated:
        (
          document.getElementById(
            "subtitle-use-translated",
          ) as HTMLSelectElement
        )?.value === "true",
      chunk_duration: chunkDuration,
    },
    audio_mixer: {
      enabled:
        (document.getElementById("audio-mixer-enabled") as HTMLInputElement)
          ?.checked ?? false,
      original_volume: parseFloat(
        (
          document.getElementById(
            "audio-mixer-original-volume",
          ) as HTMLInputElement
        )?.value || String(DEFAULTS.ORIGINAL_VOLUME),
      ),
      tts_volume: parseFloat(
        (
          document.getElementById(
            "audio-mixer-dubbed-volume",
          ) as HTMLInputElement
        )?.value || String(DEFAULTS.TTS_VOLUME),
      ),
    },
    video_muxer: {
      enabled:
        (document.getElementById("muxer-enabled") as HTMLInputElement)
          ?.checked ?? true,
      engine: ((
        document.getElementById("video-muxer-engine") as HTMLSelectElement
      )?.value || "hls") as "hls" | "webrtc",
      hls_segment_duration: parseInt(
        (document.getElementById("hls-segment") as HTMLInputElement)?.value ||
          String(DEFAULTS.SEGMENT_DURATION),
      ),
      hls_list_size: parseInt(
        (document.getElementById("hls-list") as HTMLInputElement)?.value ||
          String(DEFAULTS.LIST_SIZE),
      ),
      audio_offset_ms: parseInt(
        (document.getElementById("hls-audio-offset") as HTMLInputElement)
          ?.value || String(DEFAULTS.AUDIO_OFFSET),
      ),
      encoder_mode: ((
        document.getElementById("hls-encoder") as HTMLSelectElement
      )?.value || "auto") as EncoderMode,
      video_quality: "medium",
      video_crf: parseInt(
        (document.getElementById("hls-crf") as HTMLInputElement)?.value ||
          String(DEFAULTS.CRF),
      ),
      audio_codec:
        (((document.getElementById("video-muxer-engine") as HTMLSelectElement)
          ?.value === "webrtc"
          ? (document.getElementById("webrtc-audio-codec") as HTMLSelectElement)
              ?.value
          : (document.getElementById("hls-audio-codec") as HTMLSelectElement)
              ?.value) as AudioCodec) || "aac",
      audio_bitrate:
        (document.getElementById("hls-audio-bitrate") as HTMLSelectElement)
          ?.value || "192k",
      audio_samplerate: "48000",
      video_codec: (
        document.getElementById("webrtc-video-codec") as HTMLSelectElement
      )?.value as VideoCodec | undefined,
      video_bitrate: (
        document.getElementById("webrtc-video-bitrate") as HTMLSelectElement
      )?.value,
      video_fps: (document.getElementById(
        "webrtc-video-fps",
      ) as HTMLSelectElement)
        ? parseInt(
            (document.getElementById("webrtc-video-fps") as HTMLSelectElement)
              .value,
          )
        : undefined,
      audio_sample_rate: (document.getElementById(
        "webrtc-audio-sample-rate",
      ) as HTMLSelectElement)
        ? parseInt(
            (
              document.getElementById(
                "webrtc-audio-sample-rate",
              ) as HTMLSelectElement
            ).value,
          )
        : undefined,
      ...((): { video_width?: number; video_height?: number } => {
        const resEl = document.getElementById(
          "webrtc-video-resolution",
        ) as HTMLSelectElement;
        if (resEl?.value) {
          const [w, h] = resEl.value.split("x").map(Number);
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
      mode: "sequential",
      max_concurrent_chunks: 2,
      buffer_size: 10,
      retry_attempts: 3,
      retry_delay: 1.0,
    },
    modules: configModules,
  };
}

// ── Config Application ─────────────────────────────────────────────────────────

/**
 * Aplica una configuración recibida del servidor a todos los elementos del UI.
 * Actualiza selects, inputs, checkboxes y visibilidad de secciones.
 */
export function applyConfigToUI(cfg: Config): void {
  const inputTypeSelect = document.getElementById(
    "input-type",
  ) as HTMLSelectElement;
  const outputTypeSelect = document.getElementById(
    "output-type",
  ) as HTMLSelectElement;

  const whisperEnabled = document.getElementById(
    "whisper-enabled",
  ) as HTMLInputElement;
  const whisperModel = document.getElementById(
    "whisper-model",
  ) as HTMLSelectElement;
  const whisperLang = document.getElementById(
    "whisper-lang",
  ) as HTMLSelectElement;
  const whisperDevice = document.getElementById(
    "whisper-device",
  ) as HTMLSelectElement;
  const translatorEnabled = document.getElementById(
    "translator-enabled",
  ) as HTMLInputElement;
  const translatorSource = document.getElementById(
    "translator-source",
  ) as HTMLSelectElement;
  const translatorTarget = document.getElementById(
    "translator-target",
  ) as HTMLSelectElement;
  const ttsEnabled = document.getElementById("tts-enabled") as HTMLInputElement;
  const ttsEngine = document.getElementById("tts-engine") as HTMLSelectElement;
  const ttsDevice = document.getElementById("tts-device") as HTMLSelectElement;
  const ttsDeviceGroup = document.getElementById(
    "tts-device-group",
  ) as HTMLDivElement;
  const ttsVoiceEdge = document.getElementById(
    "tts-voice-edge",
  ) as HTMLSelectElement;
  const ttsVoicePiper = document.getElementById(
    "tts-voice-piper",
  ) as HTMLSelectElement;
  const ttsVoiceEdgeGroup = document.getElementById(
    "tts-voice-edge-group",
  ) as HTMLDivElement;
  const ttsVoicePiperGroup = document.getElementById(
    "tts-voice-piper-group",
  ) as HTMLDivElement;
  const ttsSpeed = document.getElementById("tts-speed") as HTMLInputElement;
  const subtitleEnabled = document.getElementById(
    "subtitle-enabled",
  ) as HTMLInputElement;
  const subtitleFormat = document.getElementById(
    "subtitle-format",
  ) as HTMLSelectElement;
  const subtitleUseTranslated = document.getElementById(
    "subtitle-use-translated",
  ) as HTMLSelectElement;
  const muxerEnabled = document.getElementById(
    "muxer-enabled",
  ) as HTMLInputElement;
  const videoMuxerEngine = document.getElementById(
    "video-muxer-engine",
  ) as HTMLSelectElement;
  const hlsSegment = document.getElementById("hls-segment") as HTMLInputElement;
  const hlsList = document.getElementById("hls-list") as HTMLInputElement;
  const hlsEncoder = document.getElementById(
    "hls-encoder",
  ) as HTMLSelectElement;
  const hlsCrf = document.getElementById("hls-crf") as HTMLInputElement;
  const hlsAudioOffset = document.getElementById(
    "hls-audio-offset",
  ) as HTMLInputElement;
  const hlsAudioCodec = document.getElementById(
    "hls-audio-codec",
  ) as HTMLSelectElement;
  const hlsAudioBitrate = document.getElementById(
    "hls-audio-bitrate",
  ) as HTMLSelectElement;

  const inputType = cfg.input?.type || "srt";
  if (inputTypeSelect) {
    inputTypeSelect.value = inputType;
    updateInputFields();
  }

  // SRT config
  const srtPortInput = document.getElementById(
    "input-srt-port",
  ) as HTMLInputElement;
  const srtModeSelect = document.getElementById(
    "input-srt-mode",
  ) as HTMLSelectElement;
  const srtLatencyInput = document.getElementById(
    "input-srt-latency",
  ) as HTMLInputElement;
  const inputSrtConfig = cfg.input?.srt;
  if (srtPortInput && inputSrtConfig?.listen_port)
    srtPortInput.value = String(inputSrtConfig.listen_port);
  if (srtModeSelect && inputSrtConfig?.mode)
    srtModeSelect.value = inputSrtConfig.mode;
  if (srtLatencyInput && inputSrtConfig?.latency_ms)
    srtLatencyInput.value = String(inputSrtConfig.latency_ms);

  // Chunk duration
  const srtChunkInput = document.getElementById(
    "input-chunk-duration",
  ) as HTMLInputElement;
  const rtmpChunkInput = document.getElementById(
    "input-rtmp-chunk",
  ) as HTMLInputElement;
  const fileChunkInput = document.getElementById(
    "input-file-chunk",
  ) as HTMLInputElement;
  const pipelineChunkDuration =
    cfg.pipeline?.chunk_duration_sec || DEFAULTS.CHUNK_DURATION;
  const chunkDuration = pipelineChunkDuration;

  if (srtChunkInput) {
    srtChunkInput.value = String(
      inputSrtConfig?.chunk_duration_sec || chunkDuration,
    );
  }
  const inputRtmpConfig = cfg.input?.rtmp;
  const inputFileConfig = cfg.input?.file;
  if (rtmpChunkInput) {
    rtmpChunkInput.value = String(
      inputRtmpConfig?.chunk_duration_sec || chunkDuration,
    );
  }

  // RTMP config
  const rtmpUrlInput = document.getElementById(
    "input-rtmp-url",
  ) as HTMLInputElement;
  const rtmpModeSelect2 = document.getElementById(
    "input-rtmp-mode",
  ) as HTMLSelectElement;
  const rtmpAppInput = document.getElementById(
    "input-rtmp-app",
  ) as HTMLInputElement;
  if (rtmpUrlInput && inputRtmpConfig?.url)
    rtmpUrlInput.value = inputRtmpConfig.url;
  if (rtmpModeSelect2 && inputRtmpConfig?.mode)
    rtmpModeSelect2.value = inputRtmpConfig.mode;
  if (rtmpAppInput && inputRtmpConfig?.app)
    rtmpAppInput.value = inputRtmpConfig.app;

  // File config
  const filePathInput = document.getElementById(
    "input-file-path",
  ) as HTMLInputElement;
  const fileLoopSelect = document.getElementById(
    "input-file-loop",
  ) as HTMLSelectElement;
  const fileSpeedInput = document.getElementById(
    "input-file-speed",
  ) as HTMLInputElement;
  if (
    filePathInput &&
    inputFileConfig?.path !== undefined &&
    inputFileConfig?.path !== null
  )
    filePathInput.value = inputFileConfig.path;
  if (fileLoopSelect && inputFileConfig?.loop !== undefined)
    fileLoopSelect.value = inputFileConfig.loop ? "true" : "false";
  if (fileSpeedInput && inputFileConfig?.speed)
    fileSpeedInput.value = String(inputFileConfig.speed);
  if (fileChunkInput) {
    fileChunkInput.value = String(
      inputFileConfig?.chunk_duration_sec || chunkDuration,
    );
  }

  // Output type
  const outputType =
    cfg.output?.type === "web" ? "webplayer" : cfg.output?.type || "webplayer";
  if (outputTypeSelect) {
    outputTypeSelect.value = outputType;
    updateOutputFields();
  }

  if (whisperEnabled) whisperEnabled.checked = cfg.modules.transcriber.enabled;
  if (whisperModel) whisperModel.value = cfg.modules.transcriber.model;
  if (whisperLang) whisperLang.value = cfg.modules.transcriber.language;
  if (whisperDevice) whisperDevice.value = cfg.modules.transcriber.device;
  if (translatorEnabled)
    translatorEnabled.checked = cfg.modules.translator.enabled;
  if (translatorSource)
    translatorSource.value = cfg.modules.translator.source_lang;
  if (translatorTarget)
    translatorTarget.value = cfg.modules.translator.target_lang;
  if (ttsEnabled) ttsEnabled.checked = cfg.modules.tts_engine.enabled;
  if (ttsEngine) {
    ttsEngine.value = cfg.modules.tts_engine.engine || "edge-tts";
    if (ttsDeviceGroup)
      ttsDeviceGroup.style.display =
        ttsEngine.value === "piper" ? "block" : "none";
    if (ttsVoiceEdgeGroup && ttsVoicePiperGroup) {
      const isEdge = ttsEngine.value === "edge-tts";
      ttsVoiceEdgeGroup.style.display = isEdge ? "block" : "none";
      ttsVoicePiperGroup.style.display = isEdge ? "none" : "block";
    }
  }
  if (ttsDevice) ttsDevice.value = cfg.modules.tts_engine.device || "auto";
  if (ttsVoiceEdge)
    ttsVoiceEdge.value = cfg.modules.tts_engine.voice || "es-ES-AlvaroNeural";
  if (ttsVoicePiper)
    ttsVoicePiper.value =
      cfg.modules.tts_engine.voice || "es_ES-sharvard-medium";
  if (ttsSpeed) ttsSpeed.value = String(cfg.modules.tts_engine.speed);
  if (subtitleEnabled)
    subtitleEnabled.checked = cfg.modules.subtitle_generator.enabled;
  if (subtitleFormat)
    subtitleFormat.value = cfg.modules.subtitle_generator.format;
  if (subtitleUseTranslated)
    subtitleUseTranslated.value = String(
      cfg.modules.subtitle_generator.use_translated,
    );
  if (muxerEnabled) muxerEnabled.checked = cfg.modules.video_muxer.enabled;
  if (videoMuxerEngine) {
    videoMuxerEngine.value = cfg.modules.video_muxer.engine || "hls";
  }
  const audioMixerEnabled = document.getElementById(
    "audio-mixer-enabled",
  ) as HTMLInputElement;
  if (audioMixerEnabled)
    audioMixerEnabled.checked = cfg.modules.audio_mixer?.enabled ?? false;

  const originalVolume = document.getElementById(
    "audio-mixer-original-volume",
  ) as HTMLInputElement;
  if (originalVolume)
    originalVolume.value = String(
      cfg.modules.audio_mixer?.original_volume ?? 0.7,
    );
  const originalValue = document.getElementById(
    "audio-mixer-original-value",
  ) as HTMLSpanElement;
  if (originalValue)
    originalValue.textContent = String(
      cfg.modules.audio_mixer?.original_volume ?? 0.7,
    );

  const ttsVolume = document.getElementById(
    "audio-mixer-dubbed-volume",
  ) as HTMLInputElement;
  if (ttsVolume)
    ttsVolume.value = String(cfg.modules.audio_mixer?.tts_volume ?? 1.0);
  const ttsValue = document.getElementById(
    "audio-mixer-dubbed-value",
  ) as HTMLSpanElement;
  if (ttsValue)
    ttsValue.textContent = String(cfg.modules.audio_mixer?.tts_volume ?? 1.0);

  if (hlsSegment)
    hlsSegment.value = String(cfg.modules.video_muxer.hls_segment_duration);
  if (hlsList) hlsList.value = String(cfg.modules.video_muxer.hls_list_size);
  if (hlsEncoder) hlsEncoder.value = cfg.modules.video_muxer.encoder_mode;
  if (hlsCrf) hlsCrf.value = String(cfg.modules.video_muxer.video_crf);
  if (hlsAudioOffset)
    hlsAudioOffset.value = String(cfg.modules.video_muxer.audio_offset_ms || 0);
  if (hlsAudioCodec)
    hlsAudioCodec.value = cfg.modules.video_muxer.audio_codec || "aac";
  if (hlsAudioBitrate)
    hlsAudioBitrate.value = cfg.modules.video_muxer.audio_bitrate || "192k";

  // WebRTC
  const webrtcEncoder = document.getElementById(
    "webrtc-encoder",
  ) as HTMLSelectElement;
  const webrtcVideoCodec = document.getElementById(
    "webrtc-video-codec",
  ) as HTMLSelectElement;
  const webrtcVideoBitrate = document.getElementById(
    "webrtc-video-bitrate",
  ) as HTMLSelectElement;
  const webrtcVideoResolution = document.getElementById(
    "webrtc-video-resolution",
  ) as HTMLSelectElement;
  const webrtcVideoFPS = document.getElementById(
    "webrtc-video-fps",
  ) as HTMLSelectElement;
  const webrtcAudioCodec = document.getElementById(
    "webrtc-audio-codec",
  ) as HTMLSelectElement;
  const webrtcAudioBitrate = document.getElementById(
    "webrtc-audio-bitrate",
  ) as HTMLSelectElement;
  const webrtcAudioSampleRate = document.getElementById(
    "webrtc-audio-sample-rate",
  ) as HTMLSelectElement;

  if (webrtcEncoder)
    webrtcEncoder.value = cfg.modules.video_muxer.encoder_mode || "auto";
  if (webrtcVideoCodec)
    webrtcVideoCodec.value = cfg.modules.video_muxer.video_codec || "h264";
  if (webrtcVideoBitrate)
    webrtcVideoBitrate.value = cfg.modules.video_muxer.video_bitrate || "1000k";
  if (
    webrtcVideoResolution &&
    cfg.modules.video_muxer.video_width &&
    cfg.modules.video_muxer.video_height
  ) {
    webrtcVideoResolution.value = `${cfg.modules.video_muxer.video_width}x${cfg.modules.video_muxer.video_height}`;
  }
  if (webrtcVideoFPS && cfg.modules.video_muxer.video_fps) {
    webrtcVideoFPS.value = String(cfg.modules.video_muxer.video_fps);
  }
  if (webrtcAudioCodec)
    webrtcAudioCodec.value = cfg.modules.video_muxer.audio_codec || "opus";
  if (webrtcAudioBitrate)
    webrtcAudioBitrate.value =
      cfg.modules.video_muxer.webrtc_audio_bitrate ||
      cfg.modules.video_muxer.audio_bitrate ||
      "64k";
  if (webrtcAudioSampleRate && cfg.modules.video_muxer.audio_sample_rate) {
    webrtcAudioSampleRate.value = String(
      cfg.modules.video_muxer.audio_sample_rate,
    );
  }
}

// ── Form Visibility Helpers ───────────────────────────────────────────────────

export function updateInputFields(): void {
  const inputTypeSelect = document.getElementById(
    "input-type",
  ) as HTMLSelectElement;
  if (inputTypeSelect) {
    inputTypeSelect.value = inputTypeSelect.value as "srt" | "rtmp" | "file";
  }
}

export function updateOutputFields(): void {
  const outputTypeSelect = document.getElementById(
    "output-type",
  ) as HTMLSelectElement;
  if (outputTypeSelect) {
    outputTypeSelect.value = outputTypeSelect.value as
      | "webplayer"
      | "srt"
      | "rtmp"
      | "file";
  }
}
