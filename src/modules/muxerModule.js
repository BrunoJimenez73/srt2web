const { spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');
const BaseModule = require('./baseModule');

class MuxerModule extends BaseModule {
  constructor() {
    super();
    this.ffmpegProcess = null;
    this.outputDir = null;
    this.hlsPlaylist = null;
  }

  async process(input, config) {
    const { videoFile, dubbedAudioFile, vttFile } = input;
    const { 
      outputDir, 
      hlsTime = 2, 
      hlsListSize = 20,
      hlsInitTime = 1,
      hlsMaxMuxingQueueSize = 2048
    } = config;

    this.outputDir = outputDir || path.join(os.tmpdir(), `hls_output_${Date.now()}`);
    
    const mkdir = require('util').promisify(fs.mkdir);
    await mkdir(this.outputDir, { recursive: true });

    this.hlsPlaylist = path.join(this.outputDir, 'stream.m3u8');

    const ffmpegStatic = require('ffmpeg-static');
    
    const args = [
      '-hide_banner',
      '-loglevel', 'warning',
      '-re',
      '-i', videoFile,
      '-i', dubbedAudioFile,
      '-i', vttFile,
      '-map', '0:v',
      '-map', '1:a',
      '-map', '2:s',
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-c:s', 'webvtt',
      '-f', 'hls',
      '-hls_time', hlsTime.toString(),
      '-hls_list_size', hlsListSize.toString(),
      '-hls_init_time', hlsInitTime.toString(),
      '-hls_max_muxing_queue_size', hlsMaxMuxingQueueSize.toString(),
      '-hls_flags', 'delete_segments+append_list+omit_endlist',
      '-hls_segment_filename', path.join(this.outputDir, 'segment_%03d.ts'),
      '-streaming', '1',
      '-movflags', '+faststart',
      this.hlsPlaylist
    ];

    console.log('[Muxer] Starting FFmpeg with args:', args.join(' '));

    this.ffmpegProcess = spawn(ffmpegStatic, args, {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stderr = '';
    
    this.ffmpegProcess.stderr.on('data', (data) => {
      stderr += data;
      process.stderr.write(data);
    });

    this.ffmpegProcess.on('close', (code) => {
      console.log(`[Muxer] FFmpeg closed with code ${code}`);
    });

    this.ffmpegProcess.on('error', (err) => {
      console.error(`[Muxer] FFmpeg error: ${err.message}`);
    });

    await this._waitForPlaylist();

    console.log('[Muxer] HLS stream ready');
    
    return { 
      hlsPlaylist: this.hlsPlaylist,
      outputDir: this.outputDir
    };
  }

  async _waitForPlaylist() {
    const maxWait = 30000;
    const startTime = Date.now();
    
    while (Date.now() - startTime < maxWait) {
      if (fs.existsSync(this.hlsPlaylist)) {
        const stats = fs.statSync(this.hlsPlaylist);
        if (stats.size > 0) {
          const content = fs.readFileSync(this.hlsPlaylist, 'utf8');
          if (content.includes('#EXTM3U') && content.includes('.ts')) {
            return true;
          }
        }
      }
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    throw new Error('Timeout waiting for HLS playlist');
  }

  async cleanup(moduleInstance) {
    if (this.ffmpegProcess) {
      console.log('[Muxer] Killing FFmpeg process');
      this.ffmpegProcess.kill('SIGTERM');
      
      setTimeout(() => {
        if (!this.ffmpegProcess.killed) {
          this.ffmpegProcess.kill('SIGKILL');
        }
      }, 3000);
      
      this.ffmpegProcess = null;
    }
  }
}

module.exports = MuxerModule;
