const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const ffmpegStatic = require('ffmpeg-static');
const BaseModule = require('./baseModule');
const { cleanupTempFiles } = require('../utils');

class SrtInputModule extends BaseModule {
  constructor() {
    super();
    this.tempFiles = [];
    this.tempDir = null;
  }

  /**
   * @param {Object} config - Configuration object
   * @param {string} config.srtUri - The SRT URI to listen on (e.g., 'srt://0.0.0.0:8080?mode=listener')
   * @param {number} [config.timeout=300000] - Timeout in ms for FFmpeg (default 5 min)
   * @returns {Promise<{videoFile: string, audioFile: string, _videoProcess: ChildProcess, _audioProcess: ChildProcess}>}
   */
  async process(input, config) {
    const { srtUri } = config;
    const timeout = config.timeout || 300000;

    this.tempDir = path.join(os.tmpdir(), `srt_to_web_${Date.now()}`);
    const { promisify } = require('util');
    const mkdir = promisify(require('fs').mkdir);
    await mkdir(this.tempDir, { recursive: true });

    const videoFile = path.join(this.tempDir, 'input.mkv');
    const audioFile = path.join(this.tempDir, 'input_audio.wav');

    this.tempFiles.push(videoFile, audioFile);

    const ffmpegOptions = ['-hide_banner', '-loglevel', 'error'];

    const videoProc = spawn(ffmpegStatic, [
      ...ffmpegOptions,
      '-i', srtUri,
      '-c', 'copy',
      videoFile
    ]);

    const audioProc = spawn(ffmpegStatic, [
      ...ffmpegOptions,
      '-i', srtUri,
      '-vn',
      '-acodec', 'pcm_s16le',
      '-ar', '16000',
      '-ac', '1',
      audioFile
    ]);

    let videoError = '';
    let audioError = '';

    videoProc.stderr.on('data', (data) => {
      videoError += data;
      console.error(`SRT Input (Video) FFmpeg: ${data}`);
    });

    audioProc.stderr.on('data', (data) => {
      audioError += data;
      console.error(`SRT Input (Audio) FFmpeg: ${data}`);
    });

    const waitForFile = (filePath, proc) => {
      return new Promise((resolve, reject) => {
        const checkInterval = setInterval(() => {
          const fs = require('fs');
          if (fs.existsSync(filePath)) {
            clearInterval(checkInterval);
            resolve(true);
          }
        }, 500);

        const timeoutId = setTimeout(() => {
          clearInterval(checkInterval);
          if (!proc.killed) {
            proc.kill();
          }
          reject(new Error(`Timeout waiting for ${filePath} after ${timeout}ms`));
        }, timeout);

        proc.on('close', (code) => {
          clearInterval(checkInterval);
          clearTimeout(timeoutId);
          if (code !== 0 && code !== null) {
            console.error(`FFmpeg exited with code ${code}: ${videoError || audioError}`);
          }
        });
      });
    };

    await Promise.all([
      waitForFile(videoFile, videoProc),
      waitForFile(audioFile, audioProc)
    ]);

    return {
      videoFile,
      audioFile,
      _videoProcess: videoProc,
      _audioProcess: audioProc,
      _tempDir: this.tempDir
    };
  }

  async cleanup(moduleInstance) {
    if (moduleInstance._videoProcess) {
      moduleInstance._videoProcess.kill('SIGTERM');
      setTimeout(() => {
        if (!moduleInstance._videoProcess.killed) {
          moduleInstance._videoProcess.kill('SIGKILL');
        }
      }, 3000);
    }
    if (moduleInstance._audioProcess) {
      moduleInstance._audioProcess.kill('SIGTERM');
      setTimeout(() => {
        if (!moduleInstance._audioProcess.killed) {
          moduleInstance._audioProcess.kill('SIGKILL');
        }
      }, 3000);
    }

    cleanupTempFiles(this.tempFiles);

    if (this.tempDir) {
      try {
        const fs = require('fs');
        if (fs.existsSync(this.tempDir)) {
          fs.rmSync(this.tempDir, { recursive: true, force: true });
        }
      } catch (err) {
        console.warn(`Failed to delete temp dir ${this.tempDir}:`, err.message);
      }
    }
  }
}

module.exports = SrtInputModule;
