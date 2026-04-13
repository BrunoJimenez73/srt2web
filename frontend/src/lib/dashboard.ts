import { apiCall, getConfig, startPipeline, stopPipeline, WSClient } from './api';
import { getSRTUrl, getStreamUrl, getPlayerUrl, isLocalhost, copyToClipboard, showToast, startClockUpdates } from './utils';
import { ENCODER_LABELS } from './utils';
import { dashboardStore } from './store';
import type { Config, Status, LogMessage, ModuleName } from './types';

// Import toast from modules
function showNotification(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
  showToast(message, type);
}

export const moduleToCard: Record<string, string> = {
  srt_input: 'card-input',
  rtmp_input: 'card-input',
  file_input: 'card-input',
  audio_extractor: 'card-input',
  transcriber: 'card-whisper',
  translator: 'card-translate',
  tts_engine: 'card-tts',
  subtitle_generator: 'card-subtitle',
  audio_mixer: 'card-audio-mixer',
  video_muxer: 'card-video-muxer',
  output: 'card-video-muxer', // OutputSink se muestra como video_muxer
  webplayer_output: 'card-output',
  srt_output: 'card-output',
  rtmp_output: 'card-output',
  file_output: 'card-output'
};

export const moduleToIndicator: Record<string, string> = {
  srt_input: 'indicator-input',
  rtmp_input: 'indicator-input',
  file_input: 'indicator-input',
  audio_extractor: 'indicator-input',
  transcriber: 'indicator-whisper',
  translator: 'indicator-translate',
  tts_engine: 'indicator-tts',
  subtitle_generator: 'indicator-subtitle',
  audio_mixer: 'indicator-audio-mixer',
  video_muxer: 'indicator-video-muxer',
  output: 'indicator-video-muxer', // OutputSink se muestra como video_muxer
  webplayer_output: 'indicator-output',
  srt_output: 'indicator-output',
  rtmp_output: 'indicator-output',
  file_output: 'indicator-output'
};

let config: Config | null = null;
let status: Status | null = null;
let wsClient: WSClient | null = null;
let localMode: 'local' | 'remote' = 'local';
let statusPollInterval: ReturnType<typeof setInterval> | null = null;

export function addLog(level: LogMessage['level'], message: string): void {
  const fn = (window as unknown as { addLog: (l: string, m: string) => void }).addLog;
  if (fn) fn(level, message);
}

export function updatePipelineUI(state: Status['state']): void {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  const startBtn = document.getElementById('btn-start') as HTMLButtonElement;
  const stopBtn = document.getElementById('btn-stop') as HTMLButtonElement;

  if (dot) dot.classList.toggle('running', state === 'running');
  if (text) text.textContent = state === 'running' ? 'ACTIVO' : 'APAGADO';
  if (startBtn) startBtn.disabled = state === 'running';
  if (stopBtn) stopBtn.disabled = state !== 'running';
}

export function updateUrls(localIp?: string): void {
  if (!config) return;
  
  const ip = localIp || '127.0.0.1';
  const useIp = isLocalhost(ip) ? '127.0.0.1' : ip;
  
  const srtPort = config.input?.srt?.listen_port || 9000;
  
  const urlSrt = document.getElementById('url-srt');
  const urlStream = document.getElementById('url-stream');
  const urlPlayer = document.getElementById('url-player');
  
  if (urlSrt) {
    const srtUrl = getSRTUrl(useIp, srtPort);
    urlSrt.textContent = srtUrl;
  }
  
  if (urlStream) {
    const streamUrl = getStreamUrl(useIp);
    urlStream.textContent = streamUrl;
  }
  
  if (urlPlayer) {
    const playerUrl = getPlayerUrl(useIp);
    urlPlayer.textContent = playerUrl;
    // Only set href if element is an anchor
    if (urlPlayer instanceof HTMLAnchorElement) {
      urlPlayer.href = playerUrl;
    }
  }
  
  // Also update the player URL in OutputCard based on engine mode
  const outputPlayerDisplay = document.getElementById('url-player-display');
  if (outputPlayerDisplay) {
    const engine = config.modules.video_muxer?.engine || 'hls';
    if (engine === 'webrtc') {
      // WebRTC player URL
      outputPlayerDisplay.textContent = `${window.location.origin}/webrtc-player`;
    } else {
      // HLS player URL
      outputPlayerDisplay.textContent = getPlayerUrl(useIp);
    }
  }
}

export function updateModuleStatus(status: Status): void {
  if (!status.modules) return;
  
  const isRunning = status.state === 'running';

  status.modules.forEach((module) => {
    const indicatorId = moduleToIndicator[module.name];
    if (indicatorId) {
      const indicator = document.getElementById(indicatorId);
      if (indicator) {
        indicator.classList.toggle('active', isRunning && module.enabled);
      }
    }
  });

  const inputIndicator = document.getElementById('indicator-input');
  if (inputIndicator && status.input_receiving !== undefined) {
    const receiving = status.input_receiving === true;
    inputIndicator.classList.toggle('active', receiving);
  }

  const outputIndicator = document.getElementById('indicator-output');
  if (outputIndicator) {
    // Output indicator: active if streaming or pipeline is running
    const streaming = status.output_info?.streaming === true;
    const chunksProcessed = status.chunks_processed ?? 0;
    outputIndicator.classList.toggle('active', streaming || (isRunning && chunksProcessed > 0));
  }

  // Video muxer indicator: active if pipeline is running and processing chunks
  const videoMuxerIndicator = document.getElementById('indicator-video-muxer');
  if (videoMuxerIndicator) {
    const videoMuxerModule = status.modules.find(m => m.name === 'video_muxer');
    if (videoMuxerModule) {
      videoMuxerIndicator.classList.toggle('active', isRunning && videoMuxerModule.enabled);
    } else {
      // Video muxer is an OutputSink, not a module - use pipeline state as proxy
      const chunksProcessed = status.chunks_processed ?? 0;
      videoMuxerIndicator.classList.toggle('active', isRunning && chunksProcessed > 0);
    }
  }

  const statChunks = document.getElementById('stat-chunks');
  const statState = document.getElementById('stat-state');
  if (statChunks) statChunks.textContent = String(status.chunks_processed ?? 0);
  if (statState) statState.textContent = status.state;
  
  updateSystemMetrics(status);
  updateModulePerformanceMetrics(status.modules);
  
  // Note: Input metrics are updated via updateModulePerformanceMetrics using module-time-input and module-chunks-input
  // The input indicator is updated above based on input_receiving status
}

let lastChunksProcessed = 0;
let throughputHistory: number[] = [];

export function updateSystemMetrics(status: Status): void {
  const system = status.system;
  
  const cpuBar = document.getElementById('metric-cpu-bar');
  const cpuValue = document.getElementById('metric-cpu-value');
  const cpuItem = document.getElementById('metric-cpu');
  if (cpuBar && cpuValue && cpuItem && system?.cpu_percent !== undefined) {
    const cpu = system.cpu_percent;
    cpuBar.style.width = `${Math.min(cpu, 100)}%`;
    cpuValue.textContent = `${cpu.toFixed(1)}%`;
    
    cpuBar.className = 'metric-bar';
    if (cpu < 50) cpuBar.classList.add('low');
    else if (cpu < 80) cpuBar.classList.add('medium');
    else cpuBar.classList.add('high');
    
    cpuItem.className = cpu > 90 ? 'metric-item critical' : cpu > 70 ? 'metric-item warning' : 'metric-item';
  }
  
  const memBar = document.getElementById('metric-memory-bar');
  const memValue = document.getElementById('metric-memory-value');
  const memPercent = document.getElementById('metric-memory-percent');
  const memItem = document.getElementById('metric-memory');
  if (memBar && memValue && memPercent && memItem && system?.memory_percent !== undefined) {
    const memMb = system.memory_mb;
    const memPct = system.memory_percent;
    memBar.style.width = `${Math.min(memPct, 100)}%`;
    memValue.textContent = `${memMb.toFixed(0)} MB`;
    memPercent.textContent = `${memPct.toFixed(1)}%`;
    
    memBar.className = 'metric-bar';
    if (memPct < 50) memBar.classList.add('low');
    else if (memPct < 80) memBar.classList.add('medium');
    else memBar.classList.add('high');
    
    memItem.className = memPct > 90 ? 'metric-item critical' : memPct > 70 ? 'metric-item warning' : 'metric-item';
  }
  
  const gpuBar = document.getElementById('metric-gpu-bar');
  const gpuValue = document.getElementById('metric-gpu-value');
  const gpuMemory = document.getElementById('metric-gpu-memory');
  const gpuItem = document.getElementById('metric-gpu');
  if (gpuBar && gpuValue && gpuMemory && gpuItem) {
    if (system?.gpu_available) {
      const gpuPct = system.gpu_percent;
      const gpuMemMb = system.gpu_memory_mb;
      gpuBar.style.width = `${Math.min(gpuPct, 100)}%`;
      gpuValue.textContent = `${gpuPct.toFixed(1)}%`;
      gpuMemory.textContent = `${gpuMemMb.toFixed(0)} MB`;
      
      gpuBar.className = 'metric-bar';
      if (gpuPct < 50) gpuBar.classList.add('low');
      else if (gpuPct < 80) gpuBar.classList.add('medium');
      else gpuBar.classList.add('high');
      
       gpuItem.className = gpuPct > 90 ? 'metric-item critical' : gpuPct > 70 ? 'metric-item warning' : 'metric-item';
    } else {
      gpuBar.style.width = '0%';
      gpuValue.textContent = 'N/A';
      gpuMemory.textContent = 'N/A';
      gpuItem.className = 'metric-item';
    }
  }
  
  const throughputBar = document.getElementById('metric-throughput-bar');
  const throughputValue = document.getElementById('metric-throughput-value');
  if (throughputBar && throughputValue) {
    const currentChunks = status.chunks_processed ?? 0;
    const chunkDiff = currentChunks - lastChunksProcessed;
    lastChunksProcessed = currentChunks;
    
    throughputHistory.push(chunkDiff);
    if (throughputHistory.length > 5) throughputHistory.shift();
    
    const avgThroughput = throughputHistory.reduce((a, b) => a + b, 0) / throughputHistory.length;
    throughputValue.textContent = `${avgThroughput.toFixed(1)}/s`;
    
    const throughputPct = Math.min((avgThroughput / 10) * 100, 100);
    throughputBar.style.width = `${throughputPct}%`;
  }
}

export function updateModulePerformanceMetrics(modules: any[]): void {
  // Update input metrics separately (input is not in modules list)
  // Find input module in modules array for timing info
  const inputModule = modules?.find(m => 
    m.name === 'input' || m.name === 'srt_input' || 
    m.name === 'rtmp_input' || m.name === 'file_input'
  );
  
  const inputTimeEl = document.getElementById('module-time-input');
  const inputChunksEl = document.getElementById('module-chunks-input');
  const inputGpuBadge = document.getElementById('input-gpu-badge');
  const inputEncoderEl = document.getElementById('module-encoder-input');
  
  // Use input module's timing if available, otherwise use global status
  const moduleStatus = inputModule || status;
  const isProcessing = moduleStatus?.state === 'running' && (moduleStatus?.chunks_processed ?? 0) > 0;
  
  // Update INPUT metrics
  if (inputTimeEl && moduleStatus) {
    if (!moduleStatus.enabled) {
      inputTimeEl.textContent = 'DISABLED';
      inputTimeEl.style.color = 'var(--text-dim)';
    } else if (moduleStatus.state === 'running') {
      // Use the module's last_process_time_ms if available
      if (inputModule?.last_process_time_ms > 0) {
        inputTimeEl.textContent = `${inputModule.last_process_time_ms.toFixed(1)}ms`;
        inputTimeEl.style.color = 'var(--success)';
      } else if (throughputHistory.length > 0) {
        const avgThroughput = throughputHistory.reduce((a, b) => a + b, 0) / throughputHistory.length;
        const avgTimeMs = avgThroughput > 0 ? (1000 / avgThroughput).toFixed(0) : '--';
        inputTimeEl.textContent = `${avgTimeMs}ms`;
        inputTimeEl.style.color = 'var(--success)';
      } else {
        inputTimeEl.textContent = '--';
        inputTimeEl.style.color = 'var(--text-sec)';
      }
    } else if (moduleStatus.state === 'error') {
      inputTimeEl.textContent = 'ERROR';
      inputTimeEl.style.color = 'var(--error)';
    } else {
      inputTimeEl.textContent = 'IDLE';
      inputTimeEl.style.color = 'var(--text-sec)';
    }
  }
  if (inputChunksEl && moduleStatus) {
    inputChunksEl.textContent = String(moduleStatus.processed_chunks ?? 0);
  }
  
  // Update INPUT GPU badge - show green when actively processing input chunks
  if (inputGpuBadge && inputModule) {
    const isGpuActive = inputModule.extra?.using_gpu === true;
    const isActiveProcessing = moduleStatus?.state === 'running' && (inputModule.processed_chunks ?? 0) > 0;
    if (inputModule.enabled && isGpuActive) {
      inputGpuBadge.style.display = 'inline';
      inputGpuBadge.classList.toggle('active', isActiveProcessing);
      inputGpuBadge.textContent = isGpuActive ? 'GPU' : 'CPU';
    } else {
      inputGpuBadge.style.display = 'none';
    }
  }
  if (inputEncoderEl && inputModule) {
    const label = inputModule.extra?.encoder_label || (inputModule.extra?.using_gpu ? 'GPU' : 'CPU');
    inputEncoderEl.textContent = label;
  }

  // Update video muxer metrics separately (video_muxer is an OutputSink, not in modules list)
  const videoMuxerTimeEl = document.getElementById('module-time-video_muxer');
  const videoMuxerChunksEl = document.getElementById('module-chunks-video_muxer');
  if (videoMuxerTimeEl && status) {
    if (status.state === 'running' && throughputHistory.length > 0) {
      const avgThroughput = throughputHistory.reduce((a, b) => a + b, 0) / throughputHistory.length;
      const avgTimeMs = avgThroughput > 0 ? (1000 / avgThroughput).toFixed(0) : '--';
      videoMuxerTimeEl.textContent = `${avgTimeMs}ms`;
      videoMuxerTimeEl.style.color = 'var(--success)';
    } else {
      videoMuxerTimeEl.textContent = 'IDLE';
      videoMuxerTimeEl.style.color = 'var(--text-sec)';
    }
  }
  if (videoMuxerChunksEl && status) {
    videoMuxerChunksEl.textContent = String(status.chunks_processed ?? 0);
  }

  // Update output metrics (output is also an OutputSink)
  const outputTimeEl = document.getElementById('module-time-output');
  const outputChunksEl = document.getElementById('module-chunks-output');
  const outputFormatEl = document.getElementById('module-format-output');
  if (outputTimeEl && status) {
    if (status.state === 'running' && throughputHistory.length > 0) {
      const avgThroughput = throughputHistory.reduce((a, b) => a + b, 0) / throughputHistory.length;
      const avgTimeMs = avgThroughput > 0 ? (1000 / avgThroughput).toFixed(0) : '--';
      outputTimeEl.textContent = `${avgTimeMs}ms`;
      outputTimeEl.style.color = 'var(--success)';
    } else {
      outputTimeEl.textContent = 'IDLE';
      outputTimeEl.style.color = 'var(--text-sec)';
    }
  }
  if (outputChunksEl && status) {
    outputChunksEl.textContent = String(status.chunks_processed ?? 0);
  }
  if (outputFormatEl && config) {
    const outputType = config.output?.type === 'web' ? 'Web' : (config.output?.type || 'Web').toUpperCase();
    outputFormatEl.textContent = outputType;
  }

  modules.forEach(module => {
    // Skip INPUT modules - they are handled separately in this function
    if (module.name === 'input' || module.name === 'srt_input' || 
        module.name === 'rtmp_input' || module.name === 'file_input') {
      return;
    }
    
    // Update main module metrics
    const timeEl = document.getElementById(`module-time-${module.name}`);
    if (timeEl) {
      if (!module.enabled) {
        timeEl.textContent = 'DISABLED';
        timeEl.style.color = 'var(--text-dim)';
      } else if (module.state === 'running') {
        const lastProcessTime = module.last_process_time_ms > 0 ? `${module.last_process_time_ms.toFixed(1)}ms` : '--';
        timeEl.textContent = lastProcessTime;
        timeEl.style.color = 'var(--success)';
      } else if (module.state === 'error') {
        timeEl.textContent = 'ERROR';
        timeEl.style.color = 'var(--error)';
      } else {
        timeEl.textContent = 'IDLE';
        timeEl.style.color = 'var(--text-sec)';
      }
    }
    
    const memoryEl = document.getElementById(`module-memory-${module.name}`);
    if (memoryEl && module.memory_mb !== undefined) {
      memoryEl.textContent = `${module.memory_mb.toFixed(1)} MB`;
    }
    
    const chunksEl = document.getElementById(`module-chunks-${module.name}`);
    if (chunksEl && module.processed_chunks !== undefined) {
      chunksEl.textContent = String(module.processed_chunks);
    }

    if (module.extra) {
      const isProcessing = module.enabled && module.state === 'running' && module.processed_chunks > 0;

      if (module.name === 'transcriber') {
        const gpuBadge = document.getElementById('whisper-gpu-badge');
        const deviceEl = document.getElementById('module-device-transcriber');
        if (gpuBadge) {
          if (module.extra.using_gpu) {
            gpuBadge.style.display = 'inline';
            gpuBadge.classList.toggle('active', isProcessing);
          } else {
            gpuBadge.style.display = 'none';
          }
        }
        if (deviceEl) {
          deviceEl.textContent = module.extra.device ? module.extra.device.toUpperCase() : '--';
        }
      }

      if (module.name === 'tts_engine') {
        const gpuBadge = document.getElementById('tts-gpu-badge');
        const deviceEl = document.getElementById('module-device-tts_engine');
        if (gpuBadge) {
          if (module.extra.using_gpu) {
            gpuBadge.style.display = 'inline';
            gpuBadge.classList.toggle('active', isProcessing);
          } else {
            gpuBadge.style.display = 'none';
          }
        }
        if (deviceEl) {
          deviceEl.textContent = module.extra.device ? module.extra.device.toUpperCase() : '--';
        }
      }

      // Actualizar badge GPU tanto para video_muxer como para output
      // Ambos representan el mismo componente en la UI
      if (module.name === 'video_muxer' || module.name === 'output') {
        const gpuBadge = document.getElementById('hls-gpu-badge');
        const encoderEl = document.getElementById('module-encoder-video_muxer');
        
        if (gpuBadge) {
          if (module.enabled) {
            gpuBadge.style.display = 'inline';
            // Estado ABSOLUTAMENTE ESTABLE: no cambia por cada actualización
            const isGpuActive = module.extra.using_gpu === true;
            gpuBadge.classList.toggle('active', isProcessing && isGpuActive);
            gpuBadge.textContent = isGpuActive ? 'GPU' : 'CPU';
          } else {
            gpuBadge.style.display = 'none';
          }
        }
        
        if (encoderEl) {
          // Usar label del backend (nunca cambia aleatoriamente)
          const label = module.extra.encoder_label || (module.extra.using_gpu ? 'GPU' : 'CPU');
          encoderEl.textContent = label;
        }
      }
      
      // Actualizar métricas del módulo OUTPUT
      if (module.name === 'output') {
        const outputTimeEl = document.getElementById('module-time-output');
        if (outputTimeEl) {
          if (!module.enabled) {
            outputTimeEl.textContent = 'DISABLED';
            outputTimeEl.style.color = 'var(--text-dim)';
          } else if (module.state === 'running') {
            const lastProcessTime = module.last_process_time_ms > 0 
              ? `${module.last_process_time_ms.toFixed(1)}ms` 
              : '--';
            outputTimeEl.textContent = lastProcessTime;
            outputTimeEl.style.color = 'var(--success)';
          } else if (module.state === 'error') {
            outputTimeEl.textContent = 'ERROR';
            outputTimeEl.style.color = 'var(--error)';
          } else {
            outputTimeEl.textContent = 'IDLE';
            outputTimeEl.style.color = 'var(--text-sec)';
          }
        }
        
        // OUTPUT GPU badge
        const outputGpuBadge = document.getElementById('output-gpu-badge');
        const outputEncoderEl = document.getElementById('module-encoder-output');
        
        if (outputGpuBadge) {
          const isGpuActive = module.extra?.using_gpu === true;
          if (module.enabled && isGpuActive) {
            outputGpuBadge.style.display = 'inline';
            outputGpuBadge.classList.toggle('active', isProcessing);
            outputGpuBadge.textContent = isGpuActive ? 'GPU' : 'CPU';
          } else {
            outputGpuBadge.style.display = 'none';
          }
        }
        
        if (outputEncoderEl) {
          const label = module.extra?.encoder_label || (module.extra?.using_gpu ? 'GPU' : 'CPU');
          outputEncoderEl.textContent = label;
        }
        
        // No hacemos nada más para output
        return;
      }
      
      // INPUT GPU badge - show when using hardware acceleration
      if (module.name === 'input' || module.name === 'srt_input' || module.name === 'rtmp_input' || module.name === 'file_input') {
        const inputGpuBadge = document.getElementById('input-gpu-badge');
        const inputEncoderEl = document.getElementById('module-encoder-input');
        
        if (inputGpuBadge) {
          const isGpuActive = module.extra?.using_gpu === true;
          if (module.enabled && isGpuActive) {
            inputGpuBadge.style.display = 'inline';
            inputGpuBadge.classList.toggle('active', isProcessing);
            inputGpuBadge.textContent = isGpuActive ? 'GPU' : 'CPU';
          } else {
            inputGpuBadge.style.display = 'none';
          }
        }
        
        if (inputEncoderEl) {
          const label = module.extra?.encoder_label || (module.extra?.using_gpu ? 'GPU' : 'CPU');
          inputEncoderEl.textContent = label;
        }
      }
    }
  });
}

export async function toggleModule(moduleName: string, enabled: boolean): Promise<void> {
  try {
    if (moduleName === 'input') {
      await apiCall('PUT', 'input/toggle', { enabled });
      await apiCall('PUT', 'output/toggle', { enabled });
      await apiCall('PUT', `modules/${moduleName}/toggle`, { enabled });
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showToast(`Failed to toggle ${moduleName}: ${msg}`, 'error');
  }
}

export function updateInputFields(): void {
  const inputType = (document.getElementById('input-type') as HTMLSelectElement)?.value || 'srt';
  
  const srtConfig = document.getElementById('input-srt-config');
  const rtmpConfig = document.getElementById('input-rtmp-config');
  const fileConfig = document.getElementById('input-file-config');
  
  if (srtConfig) srtConfig.style.display = inputType === 'srt' ? 'flex' : 'none';
  if (rtmpConfig) rtmpConfig.style.display = inputType === 'rtmp' ? 'flex' : 'none';
  if (fileConfig) fileConfig.style.display = inputType === 'file' ? 'flex' : 'none';
}

export function updateOutputFields(): void {
  const outputType = (document.getElementById('output-type') as HTMLSelectElement)?.value || 'webplayer';
  
  const webplayerConfig = document.getElementById('output-webplayer-config');
  const srtConfig = document.getElementById('output-srt-config');
  const rtmpConfig = document.getElementById('output-rtmp-config');
  const fileConfig = document.getElementById('output-file-config');
  
  if (webplayerConfig) webplayerConfig.style.display = outputType === 'webplayer' ? 'flex' : 'none';
  if (srtConfig) srtConfig.style.display = outputType === 'srt' ? 'flex' : 'none';
  if (rtmpConfig) rtmpConfig.style.display = outputType === 'rtmp' ? 'flex' : 'none';
  if (fileConfig) fileConfig.style.display = outputType === 'file' ? 'flex' : 'none';
}

export function handleTtsEngineChange(engine: string): void {
  const ttsDeviceGroup = document.getElementById('tts-device-group');
  const ttsVoiceEdgeGroup = document.getElementById('tts-voice-edge-group');
  const ttsVoicePiperGroup = document.getElementById('tts-voice-piper-group');
  
  if (ttsDeviceGroup) {
    ttsDeviceGroup.style.display = engine === 'piper' ? 'block' : 'none';
  }
  
  if (ttsVoiceEdgeGroup && ttsVoicePiperGroup) {
    const isEdge = engine === 'edge-tts';
    ttsVoiceEdgeGroup.style.display = isEdge ? 'block' : 'none';
    ttsVoicePiperGroup.style.display = isEdge ? 'none' : 'block';
  }
}

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

  const inputType = cfg.input?.type || 'srt';
  if (inputTypeSelect) {
    inputTypeSelect.value = inputType;
    updateInputFields();
  }
  
  // Load chunk duration from config - use pipeline.chunk_duration_sec as fallback
  const srtChunkInput = document.getElementById('input-chunk-duration') as HTMLInputElement;
  const rtmpChunkInput = document.getElementById('input-rtmp-chunk') as HTMLInputElement;
  const fileChunkInput = document.getElementById('input-file-chunk') as HTMLInputElement;
  
  const inputSrtConfig = cfg.input?.srt;
  const inputRtmpConfig = cfg.input?.rtmp;
  const inputFileConfig = cfg.input?.file;
  const pipelineChunkDuration = cfg.pipeline?.chunk_duration_sec;
  
  console.log('[DEBUG] applyConfigToUI - cfg.input:', cfg.input);
  console.log('[DEBUG] applyConfigToUI - pipeline.chunk_duration_sec:', pipelineChunkDuration);
  
  // Use input-specific chunk_duration, fallback to pipeline value
  const chunkDuration = pipelineChunkDuration || 5;
  
  if (srtChunkInput) {
    const srtChunk = inputSrtConfig?.chunk_duration_sec;
    if (srtChunk) {
      srtChunkInput.value = String(srtChunk);
      console.log('[DEBUG] Set SRT chunk to input-specific:', srtChunk);
    } else {
      srtChunkInput.value = String(chunkDuration);
      console.log('[DEBUG] Set SRT chunk to pipeline fallback:', chunkDuration);
    }
  }
  if (rtmpChunkInput) {
    const rtmpChunk = inputRtmpConfig?.chunk_duration_sec;
    if (rtmpChunk) {
      rtmpChunkInput.value = String(rtmpChunk);
    } else {
      rtmpChunkInput.value = String(chunkDuration);
    }
  }
  if (fileChunkInput) {
    const fileChunk = inputFileConfig?.chunk_duration_sec;
    if (fileChunk) {
      fileChunkInput.value = String(fileChunk);
    } else {
      fileChunkInput.value = String(chunkDuration);
    }
  }

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
    if (ttsDeviceGroup) {
      ttsDeviceGroup.style.display = ttsEngine.value === 'piper' ? 'block' : 'none';
    }
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
    // Trigger engine change to show/hide appropriate settings
    if (window.handleEngineChange) {
      window.handleEngineChange(videoMuxerEngine.value);
    }
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
  
  // Apply HLS audio settings
  const hlsAudioOffset = document.getElementById('hls-audio-offset') as HTMLInputElement;
  const hlsAudioCodec = document.getElementById('hls-audio-codec') as HTMLSelectElement;
  const hlsAudioBitrate = document.getElementById('hls-audio-bitrate') as HTMLSelectElement;
  if (hlsAudioOffset) hlsAudioOffset.value = String(cfg.modules.video_muxer.audio_offset_ms || 0);
  if (hlsAudioCodec) hlsAudioCodec.value = cfg.modules.video_muxer.audio_codec || 'aac';
  if (hlsAudioBitrate) hlsAudioBitrate.value = cfg.modules.video_muxer.audio_bitrate || '192k';
  
   // Apply WebRTC settings
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

export async function handleStart(): Promise<void> {
  const btnStart = document.getElementById('btn-start') as HTMLButtonElement;
  const btnStop = document.getElementById('btn-stop') as HTMLButtonElement;
  
  try {
    btnStart.disabled = true;
    btnStart.classList.add('loading');
    btnStop.disabled = true;
    
    addLog('info', 'Iniciando pipeline...');
    const result = await startPipeline();
    status = result;
    updatePipelineUI(result.state);
    addLog('success', 'Pipeline iniciado');
  } catch (e) {
    addLog('error', `Error: ${(e as Error).message}`);
    btnStart.disabled = false;
  } finally {
    btnStart.classList.remove('loading');
  }
}

export async function handleStop(): Promise<void> {
  const btnStart = document.getElementById('btn-start') as HTMLButtonElement;
  const btnStop = document.getElementById('btn-stop') as HTMLButtonElement;
  
  if (!confirm('¿Está seguro que desea detener el pipeline?')) {
    return;
  }
  
  try {
    btnStop.disabled = true;
    btnStop.classList.add('loading');
    btnStart.disabled = true;
    
    addLog('info', 'Deteniendo pipeline...');
    const result = await stopPipeline();
    status = result;
    updatePipelineUI(result.state);
    addLog('info', 'Pipeline detenido');
  } catch (e) {
    addLog('error', `Error: ${(e as Error).message}`);
    btnStop.disabled = false;
  } finally {
    btnStop.classList.remove('loading');
  }
}

export async function handleSaveConfig(): Promise<void> {
  const btnSave = document.getElementById('btn-save-config') as HTMLButtonElement;
  
  try {
    if (btnSave) {
      btnSave.disabled = true;
      btnSave.classList.add('loading');
    }
    
    const newConfig = collectConfigFromUI();
    await apiCall('PUT', 'config', { config: newConfig });
    config = await getConfig();
    dashboardStore.setConfig(config);  // Update centralized store
    applyConfigToUI(config);
    showToast('Configuración guardada', 'success');
    addLog('info', 'Configuración guardada');
  } catch (e) {
    const msg = (e as Error).message;
    showToast(`Error: ${msg}`, 'error');
    addLog('error', `Error al guardar: ${msg}`);
  } finally {
    if (btnSave) {
      btnSave.disabled = false;
      btnSave.classList.remove('loading');
    }
  }
}

export function collectConfigFromUI(): Partial<Config> {
  const inputType = (document.getElementById('input-type') as HTMLSelectElement)?.value || 'srt';
  const outputType = (document.getElementById('output-type') as HTMLSelectElement)?.value || 'webplayer';
  
  const inputConfig: Record<string, any> = {
    type: inputType,
  };
  
  if (inputType === 'srt') {
    inputConfig.srt = {
      listen_port: parseInt((document.getElementById('input-srt-port') as HTMLInputElement)?.value || '9000'),
      mode: (document.getElementById('input-srt-mode') as HTMLSelectElement)?.value || 'listener',
      latency_ms: parseInt((document.getElementById('input-srt-latency') as HTMLInputElement)?.value || '1000'),
      chunk_duration_sec: parseInt((document.getElementById('input-chunk-duration') as HTMLInputElement)?.value || '10'),
    };
  } else if (inputType === 'rtmp') {
    inputConfig.rtmp = {
      url: (document.getElementById('input-rtmp-url') as HTMLInputElement)?.value || 'rtmp://localhost/live/stream',
      mode: (document.getElementById('input-rtmp-mode') as HTMLSelectElement)?.value || 'pull',
      chunk_duration_sec: parseInt((document.getElementById('input-rtmp-chunk') as HTMLInputElement)?.value || '10'),
    };
  } else if (inputType === 'file') {
    inputConfig.file = {
      path: (document.getElementById('input-file-path') as HTMLInputElement)?.value || '',
      loop: (document.getElementById('input-file-loop') as HTMLSelectElement)?.value === 'true',
      speed: parseFloat((document.getElementById('input-file-speed') as HTMLInputElement)?.value || '1.0'),
      chunk_duration_sec: parseInt((document.getElementById('input-file-chunk') as HTMLInputElement)?.value || '10'),
    };
  }
  
  const outputConfig: Record<string, any> = {
    type: outputType === 'webplayer' ? 'web' : outputType,
  };
  
  if (outputType === 'webplayer') {
    outputConfig.web = {
      segment_duration: parseInt((document.getElementById('output-hls-duration') as HTMLInputElement)?.value || '4'),
      list_size: parseInt((document.getElementById('output-hls-list') as HTMLInputElement)?.value || '6'),
      encoder_mode: (document.getElementById('output-encoder-mode') as HTMLSelectElement)?.value || 'auto',
    };
  }
  
  const configModules: any = {
      transcriber: {
        enabled: (document.getElementById('whisper-enabled') as HTMLInputElement)?.checked ?? true,
        model: (document.getElementById('whisper-model') as HTMLSelectElement)?.value || 'tiny',
        language: (document.getElementById('whisper-lang') as HTMLSelectElement)?.value || 'auto',
        device: (document.getElementById('whisper-device') as HTMLSelectElement)?.value || 'auto'
      },
      translator: {
        enabled: (document.getElementById('translator-enabled') as HTMLInputElement)?.checked ?? true,
        source_lang: (document.getElementById('translator-source') as HTMLSelectElement)?.value || 'auto',
        target_lang: (document.getElementById('translator-target') as HTMLSelectElement)?.value || 'es'
      },
      tts_engine: {
        enabled: (document.getElementById('tts-enabled') as HTMLInputElement)?.checked ?? true,
        engine: (document.getElementById('tts-engine') as HTMLSelectElement)?.value || 'edge-tts',
        voice: (document.getElementById('tts-engine') as HTMLSelectElement)?.value === 'piper'
          ? (document.getElementById('tts-voice-piper') as HTMLSelectElement)?.value || 'es_ES-sharvard-medium'
          : (document.getElementById('tts-voice-edge') as HTMLSelectElement)?.value || 'es-ES-ElviraNeural',
        speed: parseFloat((document.getElementById('tts-speed') as HTMLInputElement)?.value || '1.0'),
        device: (document.getElementById('tts-device') as HTMLSelectElement)?.value || 'auto'
      },
      subtitle_generator: {
        enabled: (document.getElementById('subtitle-enabled') as HTMLInputElement)?.checked ?? true,
        format: (document.getElementById('subtitle-format') as HTMLSelectElement)?.value || 'webvtt',
        use_translated: (document.getElementById('subtitle-use-translated') as HTMLSelectElement)?.value === 'true'
      },
      audio_mixer: {
        enabled: (document.getElementById('audio-mixer-enabled') as HTMLInputElement)?.checked ?? false,
        original_volume: parseFloat((document.getElementById('audio-mixer-original-volume') as HTMLInputElement)?.value || '0.3'),
        dubbed_volume: parseFloat((document.getElementById('audio-mixer-dubbed-volume') as HTMLInputElement)?.value || '1.0')
      },
      video_muxer: {
        enabled: (document.getElementById('muxer-enabled') as HTMLInputElement)?.checked ?? true,
        engine: (document.getElementById('video-muxer-engine') as HTMLSelectElement)?.value || 'hls',
        hls_segment_duration: parseInt((document.getElementById('hls-segment') as HTMLInputElement)?.value || '10'),
        hls_list_size: parseInt((document.getElementById('hls-list') as HTMLInputElement)?.value || '6'),
        audio_offset_ms: parseInt((document.getElementById('hls-audio-offset') as HTMLInputElement)?.value || '0'),
        encoder_mode: (document.getElementById('hls-encoder') as HTMLSelectElement)?.value || 'auto',
        video_quality: 'medium',
        video_crf: parseInt((document.getElementById('hls-crf') as HTMLInputElement)?.value || '18'),
        audio_codec: (document.getElementById('video-muxer-engine') as HTMLSelectElement)?.value === 'webrtc' 
          ? (document.getElementById('webrtc-audio-codec') as HTMLSelectElement)?.value || 'opus'
          : (document.getElementById('hls-audio-codec') as HTMLSelectElement)?.value || 'aac',
        audio_bitrate: (document.getElementById('hls-audio-bitrate') as HTMLSelectElement)?.value || '192k',
        audio_samplerate: '48000',
        // WebRTC specific settings
        video_codec: (document.getElementById('webrtc-video-codec') as HTMLSelectElement)?.value,
        video_bitrate: (document.getElementById('webrtc-video-bitrate') as HTMLSelectElement)?.value,
        video_fps: (document.getElementById('webrtc-video-fps') as HTMLSelectElement) 
          ? parseInt((document.getElementById('webrtc-video-fps') as HTMLSelectElement).value) 
          : undefined,
        audio_sample_rate: (document.getElementById('webrtc-audio-sample-rate') as HTMLSelectElement)
          ? parseInt((document.getElementById('webrtc-audio-sample-rate') as HTMLSelectElement).value)
          : undefined,
        // Parse resolution from webrtc-video-resolution (format: "WIDTHxHEIGHT")
        ...((): { video_width?: number; video_height?: number } => {
          const resEl = document.getElementById('webrtc-video-resolution') as HTMLSelectElement;
          if (resEl?.value) {
            const [w, h] = resEl.value.split('x').map(Number);
            return { video_width: w, video_height: h };
          }
          return {};
        })()
      }
    };

  return {
    input: inputConfig,
    output: outputConfig,
    modules: configModules,
  };
}

export function setupEventListeners(): void {
  document.getElementById('btn-start')?.addEventListener('click', handleStart);
  document.getElementById('btn-stop')?.addEventListener('click', handleStop);
  
  (window as unknown as { saveConfig: () => void }).saveConfig = handleSaveConfig;
  (window as unknown as { updateInputFields: () => void }).updateInputFields = updateInputFields;
  (window as unknown as { updateOutputFields: () => void }).updateOutputFields = updateOutputFields;
}

export async function initDashboard(): Promise<void> {
  addLog('info', 'Inicializando...');

  try {
    config = await getConfig();
    dashboardStore.setConfig(config);  // Update centralized store
    applyConfigToUI(config);

    status = await apiCall<Status>('GET', 'status');
    updatePipelineUI(status.state);
    updateModuleStatus(status);
    dashboardStore.setStatus(status);  // Update centralized store

    if (status.network?.local_ip) {
      updateUrls(status.network.local_ip);
    }

    wsClient = new WSClient({
      onLog: (msg: LogMessage) => addLog(msg.level, msg.message),
      onConnectionChange: (connected: boolean) => {
        dashboardStore.setWsConnected(connected);
        if (!connected) addLog('error', 'WebSocket desconectado');
      },
      onStatus: (newStatus: Status) => {
        status = newStatus;
        dashboardStore.setStatus(newStatus);  // Update store
        updatePipelineUI(newStatus.state);
        updateModuleStatus(newStatus);
      }
    });
    wsClient.connect();

    statusPollInterval = setInterval(async () => {
      try {
        status = await apiCall<Status>('GET', 'status');
        dashboardStore.setStatus(status);  // Update store on poll
        updatePipelineUI(status.state);
        updateModuleStatus(status);
        
        if (status?.network?.local_ip) {
          updateUrls(status.network.local_ip);
        }
      } catch {
        // Silently fail on poll errors
      }
    }, 2000);

    addLog('success', 'Dashboard inicializado');
  } catch (e) {
    addLog('error', `Error de inicialización: ${(e as Error).message}`);
  }
}

export function initWebSocket(): void {
  setupEventListeners();
  initDashboard();
  startClockUpdates();
}

(window as unknown as { toggleModule: typeof toggleModule }).toggleModule = toggleModule;
(window as unknown as { updateInputFields: typeof updateInputFields }).updateInputFields = updateInputFields;
(window as unknown as { updateOutputFields: typeof updateOutputFields }).updateOutputFields = updateOutputFields;
(window as unknown as { handleTtsEngineChange: typeof handleTtsEngineChange }).handleTtsEngineChange = handleTtsEngineChange;

// Copy URL functionality
function setupCopyButtons(): void {
  // SRT URL copy button
  document.getElementById('btn-copy-srt')?.addEventListener('click', () => {
    const urlEl = document.getElementById('url-srt');
    if (urlEl && urlEl.textContent) {
      copyToClipboard(urlEl.textContent).then(() => {
        showNotification('URL SRT copiada', 'success');
      }).catch(() => {
        showNotification('Error al copiar URL', 'error');
      });
    }
  });

  // Stream URL copy button
  document.getElementById('btn-copy-stream')?.addEventListener('click', () => {
    const urlEl = document.getElementById('url-stream');
    if (urlEl && urlEl.textContent) {
      copyToClipboard(urlEl.textContent).then(() => {
        showNotification('URL del stream copiada', 'success');
      }).catch(() => {
        showNotification('Error al copiar URL', 'error');
      });
    }
  });

  // Player URL copy button
  document.getElementById('btn-copy-player')?.addEventListener('click', () => {
    const urlEl = document.getElementById('url-player');
    if (urlEl) {
      const url = urlEl.getAttribute('href') || urlEl.textContent;
      if (url) {
        copyToClipboard(url).then(() => {
          showNotification('URL del player copiada', 'success');
        }).catch(() => {
          showNotification('Error al copiar URL', 'error');
        });
      }
    }
  });
}

// Override init to include copy buttons setup
export function handleInputTypeChange(type: string): void {
  console.log('Input type changed:', type);
}

export function handleOutputFormatChange(format: string): void {
  console.log('Output format changed:', format);
}

(window as any).init = function() {
  setupEventListeners();
  setupCopyButtons();
  initDashboard();
  startClockUpdates();
};

document.addEventListener('DOMContentLoaded', () => {
  (window as any).init();
});
