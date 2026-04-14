export * from './performance';
export * from './clock';

export function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleTimeString('en-US', { hour12: false });
}

export function getSRTUrl(ip: string, port: number): string {
  return `srt://${ip}:${port}?mode=listener`;
}

export function getRTMPUrl(ip: string, port: number, app: string = 'live', streamKey: string = 'stream'): string {
  return `rtmp://${ip}:${port}/${app}/${streamKey}`;
}

export function getStreamUrl(ip: string): string {
  return `http://${ip}:9999/hls/stream.m3u8`;
}

export function getPlayerUrl(ip: string): string {
  return `http://${ip}:9999/player`;
}

export function isLocalhost(host: string): boolean {
  return host === 'localhost' || host === '127.0.0.1' || host.startsWith('192.168.') || host.startsWith('10.');
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function showToast(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

export const ENCODER_LABELS: Record<string, string> = {
  'h264': 'H.264',
  'h264_nvenc': 'H.264 (NVIDIA)',
  'h265': 'H.265',
  'h265_nvenc': 'H.265 (NVIDIA)',
  'hevc_nvenc': 'HEVC (NVIDIA)',
  'vp9': 'VP9',
  'av1': 'AV1',
  'av1_nvenc': 'AV1 (NVIDIA)',
};