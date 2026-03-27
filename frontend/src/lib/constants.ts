// Player configuration constants
export const PLAYER_CONFIG = {
  // Hls.js configuration
  HLS: {
    enableWorker: true,
    lowLatencyMode: false,
    backBufferLength: 90,
    subtitlesEnabled: true,
    manifestLoadingTimeOut: 15000, // Reduced from 20000
    manifestLoadingMaxRetry: 3,
    manifestLoadingRetryDelay: 2000, // Reduced from 3000
    levelLoadingTimeOut: 15000, // Reduced from 20000
    levelLoadingMaxRetry: 3,
    levelLoadingRetryDelay: 2000, // Reduced from 3000
    fragLoadingTimeOut: 15000, // Reduced from 20000
    fragLoadingMaxRetry: 3,
    fragLoadingRetryDelay: 2000, // Reduced from 3000
  },
  // VTT subtitle refresh interval (ms)
  VTT_REFRESH_INTERVAL: 10000,
  // Error retry thresholds
  ERROR_THRESHOLDS: {
    networkErrorRetry: 5,
    manifestLoadErrorRetry: 3,
    genericErrorRetry: 3,
  },
};

// Encoder display labels for GPU badge
export const ENCODER_LABELS: Record<string, string> = {
  'auto': 'Auto',
  'cpu': 'CPU',
  'gpu': 'GPU',
  'gpu_nvenc': 'NVENC',
  'gpu_amf': 'AMF',
  'gpu_qsv': 'QSV',
  'gpu_vaapi': 'VAAPI',
  'gpu_videotoolbox': 'VideoToolbox',
};
