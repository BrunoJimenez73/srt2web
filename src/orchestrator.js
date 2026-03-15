const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

class Orchestrator {
  constructor(config) {
    this.config = config;
    this.server = null;
    this.outputDir = null;
    this.ffmpegProcess = null;
    this.isRunning = false;
  }

  async start() {
    if (this.isRunning) throw new Error('Already running');

    const port = this.config.serverPort || 3000;
    
    const srtUri = this.config.srtUri;
    const rtmpUrl = this.config.rtmpUrl;
    const streamUri = srtUri || rtmpUrl;
    
    if (!streamUri) {
      throw new Error('No stream URI provided');
    }
    
    const isSrt = streamUri.startsWith('srt://');
    
    this.outputDir = path.join(os.tmpdir(), `hls_${Date.now()}`);
    fs.mkdirSync(this.outputDir, { recursive: true });
    
    this._updateStatus(isSrt ? 'Starting SRT to HLS...' : 'Starting RTMP to HLS...');
    console.log('[Orchestrator] Stream URI:', streamUri);

    const ffmpegStatic = require('ffmpeg-static');

    const args = [
      '-hide_banner',
      '-loglevel', 'error',
      '-re',
      '-fflags', '+genpts+discardcorrupt',
      '-i', streamUri,
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-b:a', '96k',
      '-ar', '44100',
      '-f', 'hls',
      '-hls_time', '2',
      '-hls_list_size', '15',
      '-hls_flags', 'append_list+omit_endlist+discont_start',
      '-hls_segment_filename', path.join(this.outputDir, 'seg_%03d.ts'),
      '-hls_allow_cache', '0',
      '-muxdelay', '0',
      '-muxpreload', '0',
      '-max_delay', '500000',
      path.join(this.outputDir, 'stream.m3u8')
    ];

    console.log('[Orchestrator] FFmpeg:', ffmpegStatic);
    console.log('[Orchestrator] Input:', streamUri);

    this.ffmpegProcess = spawn(ffmpegStatic, args, { stdio: ['pipe', 'pipe', 'pipe'] });

    this.ffmpegProcess.stderr.on('data', d => {
      process.stderr.write(d.toString());
    });

    this.ffmpegProcess.on('close', c => {
      console.log('[Orchestrator] FFmpeg closed:', c);
      if (this.isRunning) {
        this._updateStatus(`FFmpeg ended (${c})`);
      }
    });

    this.ffmpegProcess.on('error', e => {
      console.error('[Orchestrator] FFmpeg error:', e.message);
    });

    await this._waitForSegments(3);

    this.server = http.createServer((req, res) => {
      let urlPath = req.url.split('?')[0];
      if (urlPath === '/') urlPath = '/stream.html';
      
      const filePath = path.join(this.outputDir, urlPath);
      const normPath = path.normalize(filePath).replace(/\\/g, '/');
      const normDir = path.normalize(this.outputDir).replace(/\\/g, '/');
      
      if (!normPath.startsWith(normDir)) {
        res.writeHead(403); res.end(); return;
      }

      fs.stat(filePath, (err, stats) => {
        if (err || !stats.isFile()) {
          if (urlPath === '/stream.html') {
            this._servePlayer(res, port);
          } else {
            res.writeHead(404); res.end();
          }
          return;
        }

        const ext = path.extname(urlPath).toLowerCase();
        
        if (ext === '.ts' && req.headers.range) {
          const range = req.headers.range;
          const parts = range.replace(/bytes=/, '').split('-');
          const start = parseInt(parts[0]) || 0;
          const end = parseInt(parts[1]) || stats.size - 1;
          
          res.writeHead(206, {
            'Content-Range': `bytes ${start}-${end}/${stats.size}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': end - start + 1,
            'Content-Type': 'video/mp2t',
            'Access-Control-Allow-Origin': '*'
          });
          fs.createReadStream(filePath, { start, end }).pipe(res);
          return;
        }

        const types = { '.m3u8': 'application/vnd.apple.mpegurl', '.ts': 'video/mp2t', '.html': 'text/html' };
        
        fs.readFile(filePath, (err, data) => {
          if (err) { res.writeHead(500); res.end(); return; }
          res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream', 'Access-Control-Allow-Origin': '*' });
          res.end(data);
        });
      });
    });

    this.server.listen(port, () => {
      const url = `http://localhost:${port}/stream.html`;
      this._updateStatus(`Server: ${url}`);
      console.log('[Orchestrator] Server ready:', url);
      this._servePlayerHtml(port);
    });

    this.isRunning = true;
    return `http://localhost:${port}/stream.html`;
  }

  async _waitForSegments(min) {
    const playlistPath = path.join(this.outputDir, 'stream.m3u8');
    const timeout = 30000;
    const start = Date.now();
    
    while (Date.now() - start < timeout) {
      try {
        if (fs.existsSync(playlistPath)) {
          const segs = fs.readdirSync(this.outputDir).filter(f => f.endsWith('.ts'));
          console.log(`[Orchestrator] Segments: ${segs.length}`);
          if (segs.length >= min) {
            await new Promise(r => setTimeout(r, 1000));
            return true;
          }
        }
      } catch (e) {
        console.log('[Orchestrator] Waiting for segments...');
      }
      await new Promise(r => setTimeout(r, 500));
    }
    throw new Error('Timeout waiting for HLS segments');
  }

  _servePlayer(res, port) {
    res.writeHead(200, { 'Content-Type': 'text/html', 'Access-Control-Allow-Origin': '*' });
    res.end(`<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>SRT Stream</title>
<link href="https://vjs.zencdn.net/8.12.0/video-js.css" rel="stylesheet">
<style>body{margin:0;background:#000;display:flex;align-items:center;justify-content:center;min-height:100vh}video{width:100%;max-width:900px}</style></head>
<body><video id="v" class="video-js" controls playsinline preload="auto" width="900" height="506">
<source src="http://localhost:${port}/stream.m3u8" type="application/x-mpegURL"></video>
<script src="https://vjs.zencdn.net/8.12.0/video.min.js"></script>
<script>videojs('v')</script></body></html>`);
  }

  _servePlayerHtml(port) {
    const html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>SRT to Web</title>
<link href="https://vjs.zencdn.net/8.12.0/video-js.css" rel="stylesheet">
<style>body{margin:0;background:#000;display:flex;align-items:center;justify-content:center;min-height:100vh}video{width:100%;max-width:900px}</style></head>
<body><video id="v" class="video-js" controls playsinline preload="auto" width="900" height="506">
<source src="http://localhost:${port}/stream.m3u8" type="application/x-mpegURL"></video>
<script src="https://vjs.zencdn.net/8.12.0/video.min.js"></script>
<script>videojs('v')</script></body></html>`;
    fs.writeFileSync(path.join(this.outputDir, 'stream.html'), html);
  }

  async stop() {
    if (!this.isRunning) return;
    this.isRunning = false;
    this._updateStatus('Stopping...');

    if (this.ffmpegProcess) {
      this.ffmpegProcess.kill('SIGTERM');
      setTimeout(() => { if (!this.ffmpegProcess.killed) this.ffmpegProcess.kill('SIGKILL'); }, 2000);
    }
    if (this.server) this.server.close();
    if (this.outputDir && fs.existsSync(this.outputDir)) {
      try { fs.rmSync(this.outputDir, { recursive: true, force: true }); } catch(e) {}
    }
    this._updateStatus('Stopped');
  }

  _updateStatus(msg) {
    console.log(`[Orchestrator] ${msg}`);
    if (this.config.onStatusChange) this.config.onStatusChange(msg);
  }
}

module.exports = { Orchestrator };
